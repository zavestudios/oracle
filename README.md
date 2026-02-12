# Oracle Worker

Oracle Worker is a Postgres-backed, lease-based job executor for AI-native workloads.
It implements the execution semantics described in `docs/oracle-worker-execution-contract-v1.md`.

## Responsibilities

- Claim jobs from `oracle.jobs`
- Execute `job_type` handlers
- Persist results atomically
- Support safe retries
- Stay stateless and restart-safe

## Design Principles

- PostgreSQL is the authoritative coordination plane
- Single-writer result semantics
- Lease-based concurrency control
- No durable in-memory state
- Kubernetes-disposable worker pods

## Repository Layout

| Path | Purpose |
| --- | --- |
| `oracle_worker/worker.py` | Main worker loop, claim/execute/complete/fail logic |
| `db/migrations/001_init.sql` | Core schema, enum states, constraints, and tables |
| `db/migrations/002_indexes.sql` | Performance/concurrency indexes |
| `docs/oracle-worker-execution-contract-v1.md` | Contract-level behavior and guarantees |
| `charts/oracle-worker/templates/deployment.yaml` | Kubernetes Deployment template |
| `charts/oracle-worker/values.yaml` | Helm values (`image`, `DATABASE_URL`) |
| `Dockerfile` | Container build and runtime entrypoint |
| `requirements.txt` | Python runtime dependency (`psycopg[binary]`) |

## Runtime Lifecycle

The worker runs a perpetual polling loop in `oracle_worker/worker.py`.

1. Connect to Postgres using `DATABASE_URL`.
2. Attempt to claim one eligible job via `claim_job(...)`.
3. Load the claimed job payload.
4. Execute the handler via `execute_job(...)`.
5. On success, persist result and mark job/attempt as succeeded.
6. On error, record failure and release lease for retry.

### Claim Semantics

`claim_job(...)` selects one job with:

- `state IN ('PENDING', 'FAILED_RETRYABLE')`, or
- `state = 'RUNNING'` and expired lease (`lease_expires_at < now()`)

It uses:

- `ORDER BY created_at`
- `FOR UPDATE SKIP LOCKED`
- `LIMIT 1`

After selecting a job, it:

- Sets job state to `RUNNING`
- Sets `lease_expires_at = now() + LEASE_SECONDS`
- Sets `current_attempt_id`
- Inserts an `oracle.attempts` row with status `RUNNING`

This supports safe horizontal scaling across multiple worker pods.

### Success Path

`complete_job(...)` runs in a DB transaction:

- Insert into `oracle.results` with `ON CONFLICT DO NOTHING`
- Update `oracle.jobs` to:
  - `state = 'SUCCEEDED'`
  - `completed_at = now()`
  - `lease_expires_at = NULL`
- Update `oracle.attempts` to:
  - `status = 'SUCCEEDED'`
  - `ended_at = now()`

### Failure Path

`fail_job(...)` runs in a DB transaction:

- Update matching job (via `current_attempt_id`) to:
  - `state = 'FAILED_RETRYABLE'` or `FAILED_TERMINAL`
  - `lease_expires_at = NULL`
- Update attempt to:
  - `status = 'FAILED'`
  - `error_message`
  - `ended_at = now()`

In current `main()` behavior, caught exceptions are marked retryable.

## Data Model and Contract Constraints

Defined in `db/migrations/001_init.sql`.

### Enum: `oracle_job_state`

- `PENDING`
- `RUNNING`
- `SUCCEEDED`
- `FAILED_RETRYABLE`
- `FAILED_TERMINAL`
- `CANCELLED`

### Table: `oracle.jobs`

Key fields:

- `job_id UUID PRIMARY KEY`
- `idempotency_key TEXT UNIQUE NOT NULL`
- `job_type TEXT NOT NULL`
- `state oracle_job_state NOT NULL DEFAULT 'PENDING'`
- `input_payload JSONB NOT NULL`
- lease metadata: `lease_expires_at`, `current_attempt_id`
- completion metadata: `completed_at`

Important constraints:

- `completed_requires_timestamp`: `SUCCEEDED` requires `completed_at`
- `lease_only_when_running`: only `RUNNING` may hold a lease

### Table: `oracle.attempts`

- One row per execution attempt
- Linked to `oracle.jobs(job_id)`
- Tracks `worker_id`, status, error, timing

### Table: `oracle.results`

- `job_id` is both FK and PK (single authoritative result per job)
- Stores `result_payload`, `content_hash`, schema version metadata

### Table: `oracle.artifacts`

- Optional attempt-scoped outputs linked to `attempt_id`

### Indexes

Defined in `db/migrations/002_indexes.sql`:

- `idx_jobs_state_created`
- `idx_jobs_lease`
- `idx_attempts_job_id`
- `idx_artifacts_attempt`

## Concurrency and Idempotency Model

- Concurrency control is DB-native via row locks and `SKIP LOCKED`.
- Expired leases are reclaimable, allowing crash recovery.
- Single-writer semantics are enforced at the results table (`results.job_id` PK).
- Job-level deduplication is enforced via `jobs.idempotency_key` unique constraint.

## Current Job Types

- `summarize_text` (stub)
  - Input: `input_payload.text`
  - Behavior: returns first 20 words as one bullet in `{"bullets": [...]}`

Unknown `job_type` values raise an exception.

## Configuration

### Required

- `DATABASE_URL`: PostgreSQL DSN

### Optional

- `LEASE_SECONDS` (default `60`)
- `WORKER_ID` (default generated UUID)

Polling interval is currently fixed in code at 3 seconds.

## Run Locally

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Ensure schema migrations are applied (`db/migrations/*.sql`) to your Postgres database.

3. Set environment:

```bash
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
export LEASE_SECONDS=60  # optional
export WORKER_ID="local-dev-worker-1"  # optional
```

4. Start worker:

```bash
python -m oracle_worker.worker
```

## Container and Deployment

- Docker entrypoint: `python -m oracle_worker.worker`
- Helm chart: `charts/oracle-worker`
- Deployment template injects `DATABASE_URL` from `values.yaml`

Set these Helm values at minimum:

- `image.repository`
- `image.tag`
- `env.DATABASE_URL`

## Known Limitations

- Exception handling currently classifies runtime failures as retryable by default.
- Logging is minimal (`print`-based) and lacks structured observability.
- No automated tests are included in this repository yet.
