import sqlite3
import uuid
from datetime import datetime, timezone


DB_PATH = "data/tap.db"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


with sqlite3.connect(DB_PATH) as conn:
    conn.execute("PRAGMA foreign_keys = ON")

    # Ensure runs.last_checked_at exists
    run_columns = [
        row[1]
        for row in conn.execute("PRAGMA table_info(runs);").fetchall()
    ]

    if "last_checked_at" not in run_columns:
        conn.execute("ALTER TABLE runs ADD COLUMN last_checked_at TEXT")
        print("Added runs.last_checked_at")
    else:
        print("runs.last_checked_at already exists")

    # Ensure run_events exists
    conn.execute("""
    CREATE TABLE IF NOT EXISTS run_events (
        event_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        message TEXT NOT NULL,
        old_status TEXT,
        new_status TEXT,
        created_at TEXT NOT NULL,
        payload_json TEXT,
        FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
    )
    """)
    print("Ensured run_events table exists")

    # Backfill RUN_CREATED events for runs that do not have one
    runs = conn.execute("""
        SELECT run_id, name, status, created_at
        FROM runs
        WHERE run_id NOT IN (
            SELECT run_id
            FROM run_events
            WHERE event_type = 'RUN_CREATED'
        )
    """).fetchall()

    for run_id, name, status, created_at in runs:
        conn.execute(
            """
            INSERT INTO run_events (
                event_id,
                run_id,
                event_type,
                message,
                old_status,
                new_status,
                created_at,
                payload_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                run_id,
                "RUN_CREATED",
                "Backfilled run creation event",
                None,
                status,
                created_at or utc_now_iso(),
                f'{{"name": "{name}", "backfilled": true}}',
            ),
        )

    print(f"Backfilled {len(runs)} RUN_CREATED events")

    conn.commit()
