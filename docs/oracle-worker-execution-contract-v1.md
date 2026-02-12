# Oracle Worker Execution Contract v1

## Purpose

Define deterministic execution semantics for AI-native workloads
running inside the ZaveStudios Kubernetes platform.

This contract ensures:

- Restart safety
- Idempotent results
- Single authoritative output
- Lease-based concurrency control
- Tenant isolation
- Explicit failure handling

---

## Core Principle

PostgreSQL is the authoritative coordination plane.
Kubernetes pods are disposable compute units.

No durable state may exist only in memory.

---

## Minimal Use Case (Validated)

Task: Summarize text into structured bullet points.

One Job = one transformation:
(text input) → (structured summary output)

This is:

- Retry-safe
- Side-effect free
- Parallelizable
- Auditable
- Stateless at compute layer

---

## Job Lifecycle

States:

- PENDING
- RUNNING
- SUCCEEDED
- FAILED_RETRYABLE
- FAILED_TERMINAL
- CANCELLED

Rules:

- Only one authoritative result per Job.
- Results written atomically with state transition.
- RUNNING requires active lease.
- Expired leases may be reclaimed.
- SUCCEEDED is terminal and immutable.

---

## Idempotency Model

Each Job has:

- job_id (UUID)
- idempotency_key (unique constraint)

results.job_id is PRIMARY KEY to enforce single-writer semantics.

Duplicate execution cannot create duplicate results.

---

## Retry Semantics

Retryable failures:
- Timeouts
- Network errors
- Transient LLM failures

Terminal failures:
- Invalid schema
- Policy violations
- Unsupported job_type

Retry policy is bounded and explicit.

---

## Side Effects

External side effects must:

- Use idempotency keys
- Be recorded in database before execution
- Never be fire-and-forget

If idempotency cannot be guaranteed,
the action must be split into plan/commit phases.

---

## Forbidden Patterns

- Durable in-memory state
- Implicit conversational memory
- Overwriting authoritative results
- Arbitrary uncontrolled network calls
- Cross-tenant reads/writes

---

## Architectural Outcome

AI workloads become:

- Just another Kubernetes Deployment
- Backed by Postgres
- GitOps controlled
- Horizontally scalable
- Operationally boring

This contract is versioned and enforceable via schema constraints.
