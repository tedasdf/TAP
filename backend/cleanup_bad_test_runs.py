from app.db import get_db

with get_db() as conn:
    conn.execute(
        """
        DELETE FROM runs
        WHERE run_id LIKE 'test-bg-json-fail-%'
        """
    )

print("Deleted bad JSON background test runs.")