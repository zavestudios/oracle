-- 001_init.sql
-- Oracle Worker Schema Initialization
-- Execution Contract v1 Enforcement Layer

CREATE SCHEMA IF NOT EXISTS oracle;

DO $$
BEGIN
  CREATE TYPE oracle_job_state AS ENUM (
    'PENDING',
    'RUNNING',
    'SUCCEEDED',
    'FAILED_RETRYABLE',
    'FAILED_TERMINAL',
    'CANCELLED'
  );
EXCEPTION
  WHEN duplicate_object THEN NULL;
END
$$;

CREATE TABLE IF NOT EXISTS oracle.jobs (
  job_id              UUID PRIMARY KEY,
  idempotency_key     TEXT NOT NULL UNIQUE,
  job_type            TEXT NOT NULL,
  state               oracle_job_state NOT NULL DEFAULT 'PENDING',

  input_payload       JSONB NOT NULL,
  policy_flags        JSONB NOT NULL DEFAULT '{}'::jsonb,

  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

  lease_expires_at    TIMESTAMPTZ,
  current_attempt_id  UUID,

  completed_at        TIMESTAMPTZ,

  CONSTRAINT completed_requires_timestamp
    CHECK (
      (state != 'SUCCEEDED')
      OR (completed_at IS NOT NULL)
    ),

  CONSTRAINT lease_only_when_running
    CHECK (
      (state = 'RUNNING' AND lease_expires_at IS NOT NULL)
      OR (state != 'RUNNING' AND lease_expires_at IS NULL)
    )
);

CREATE TABLE IF NOT EXISTS oracle.attempts (
  attempt_id      UUID PRIMARY KEY,
  job_id          UUID NOT NULL REFERENCES oracle.jobs(job_id) ON DELETE CASCADE,

  worker_id       TEXT NOT NULL,
  status          TEXT NOT NULL,
  error_message   TEXT,

  started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  ended_at        TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS oracle.results (
  job_id                UUID PRIMARY KEY REFERENCES oracle.jobs(job_id) ON DELETE CASCADE,

  result_payload        JSONB NOT NULL,
  result_schema_version INTEGER NOT NULL DEFAULT 1,

  content_hash          TEXT NOT NULL,
  model_metadata        JSONB,

  created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS oracle.artifacts (
  artifact_id      UUID PRIMARY KEY,
  attempt_id       UUID NOT NULL REFERENCES oracle.attempts(attempt_id) ON DELETE CASCADE,

  artifact_type    TEXT NOT NULL,
  artifact_payload JSONB NOT NULL,

  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
