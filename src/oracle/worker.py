import os
import time
import uuid
import hashlib
import json
import psycopg
from psycopg.rows import dict_row

DB_DSN = os.environ["DATABASE_URL"]
LEASE_SECONDS = int(os.getenv("LEASE_SECONDS", "60"))
WORKER_ID = os.getenv("WORKER_ID", str(uuid.uuid4()))
POLL_INTERVAL = 3


def claim_job(conn):
    with conn.transaction():
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT job_id
                FROM oracle.jobs
                WHERE state IN ('PENDING', 'FAILED_RETRYABLE')
                   OR (state = 'RUNNING' AND lease_expires_at < now())
                ORDER BY created_at
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            """)
            row = cur.fetchone()
            if not row:
                return None

            job_id = row["job_id"]
            attempt_id = str(uuid.uuid4())

            cur.execute("""
                UPDATE oracle.jobs
                SET state = 'RUNNING',
                    lease_expires_at = now() + interval %s,
                    current_attempt_id = %s,
                    updated_at = now()
                WHERE job_id = %s
            """, (f"{LEASE_SECONDS} seconds", attempt_id, job_id))

            cur.execute("""
                INSERT INTO oracle.attempts (attempt_id, job_id, worker_id, status)
                VALUES (%s, %s, %s, 'RUNNING')
            """, (attempt_id, job_id, WORKER_ID))

            return job_id, attempt_id


def execute_job(job):
    job_type = job["job_type"]
    payload = job["input_payload"]

    if job_type == "summarize_text":
        text = payload["text"]
        words = text.split()
        summary = " ".join(words[:20])
        return {"bullets": [summary]}

    raise ValueError(f"Unknown job_type: {job_type}")


def complete_job(conn, job_id, attempt_id, result):
    content_hash = hashlib.sha256(
        json.dumps(result, sort_keys=True).encode()
    ).hexdigest()

    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO oracle.results (job_id, result_payload, content_hash)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (job_id, json.dumps(result), content_hash))

            cur.execute("""
                UPDATE oracle.jobs
                SET state = 'SUCCEEDED',
                    completed_at = now(),
                    lease_expires_at = NULL,
                    updated_at = now()
                WHERE job_id = %s
            """, (job_id,))

            cur.execute("""
                UPDATE oracle.attempts
                SET status = 'SUCCEEDED',
                    ended_at = now()
                WHERE attempt_id = %s
            """, (attempt_id,))


def fail_job(conn, attempt_id, retryable=True, error=None):
    new_state = 'FAILED_RETRYABLE' if retryable else 'FAILED_TERMINAL'
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE oracle.jobs
                SET state = %s,
                    lease_expires_at = NULL,
                    updated_at = now()
                WHERE current_attempt_id = %s
            """, (new_state, attempt_id))

            cur.execute("""
                UPDATE oracle.attempts
                SET status = 'FAILED',
                    error_message = %s,
                    ended_at = now()
                WHERE attempt_id = %s
            """, (error, attempt_id))


def main():
    conn = psycopg.connect(DB_DSN, autocommit=False)

    while True:
        attempt_id = None
        try:
            claim = claim_job(conn)
            if not claim:
                time.sleep(POLL_INTERVAL)
                continue

            job_id, attempt_id = claim

            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute("SELECT * FROM oracle.jobs WHERE job_id = %s", (job_id,))
                job = cur.fetchone()

            result = execute_job(job)
            complete_job(conn, job_id, attempt_id, result)

        except Exception as e:
            print("Error:", e)
            if attempt_id:
                try:
                    fail_job(conn, attempt_id, retryable=True, error=str(e))
                except Exception:
                    pass
            time.sleep(2)


if __name__ == "__main__":
    main()
