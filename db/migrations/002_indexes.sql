-- 002_indexes.sql
-- Performance and concurrency indexes

CREATE INDEX IF NOT EXISTS idx_jobs_state_created
ON oracle.jobs(state, created_at);

CREATE INDEX IF NOT EXISTS idx_jobs_lease
ON oracle.jobs(lease_expires_at);

CREATE INDEX IF NOT EXISTS idx_attempts_job_id
ON oracle.attempts(job_id);

CREATE INDEX IF NOT EXISTS idx_artifacts_attempt
ON oracle.artifacts(attempt_id);
