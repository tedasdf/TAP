import sqlite3

conn = sqlite3.connect("data/tap.db")

tables = [
    row[0]
    for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
    ).fetchall()
]

print("Tables:", tables)

runs_cols = [
    row[1]
    for row in conn.execute("PRAGMA table_info(runs);").fetchall()
]

print("runs columns:", runs_cols)

conn.close()