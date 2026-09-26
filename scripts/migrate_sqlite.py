"""Apply lightweight, idempotent schema migrations for the SQLite dev database.

SQLite cannot ALTER a column type in place, so the numeric-timing migration
rebuilds the ``stage_results`` table. Safe to re-run: each migration is a
no-op when its precondition is already met.

Usage:  python -m scripts.migrate_sqlite
"""

from __future__ import annotations

import sqlite3

from backend.config import settings


def _column_type(conn: sqlite3.Connection, table: str, column: str) -> str | None:
    row = conn.execute(f"PRAGMA table_info({table})").fetchall()
    for _cid, name, col_type, *_ in row:
        if name == column:
            return col_type
    return None


def migrate_processing_time_ms(db_path: str) -> bool:
    """Convert stage_results.processing_time_ms VARCHAR -> INTEGER.

    Returns True if the migration was applied, False if already current.
    """
    conn = sqlite3.connect(db_path)
    try:
        if _column_type(conn, "stage_results", "processing_time_ms") == "INTEGER":
            return False

        conn.executescript("""
            BEGIN;
            ALTER TABLE stage_results RENAME TO stage_results_old;
            CREATE TABLE stage_results (
                id VARCHAR NOT NULL PRIMARY KEY,
                run_id VARCHAR NOT NULL REFERENCES screening_runs (id),
                stage VARCHAR NOT NULL,
                status VARCHAR NOT NULL,
                confidence VARCHAR,
                result JSON,
                meta JSON,
                errors TEXT,
                processing_time_ms INTEGER
            );
            INSERT INTO stage_results
                SELECT id, run_id, stage, status, confidence, result, meta, errors,
                       CAST(processing_time_ms AS INTEGER)
                FROM stage_results_old;
            DROP TABLE stage_results_old;
            COMMIT;
        """)
        return True
    finally:
        conn.close()


def main() -> None:
    db_url = settings.DATABASE_URL
    if not db_url.startswith("sqlite:///"):
        print(f"DATABASE_URL is {db_url!r}; nothing to migrate for SQLite-specific script.")
        return
    db_path = db_url.replace("sqlite:///", "", 1)
    applied = migrate_processing_time_ms(db_path)
    print("stage_results.processing_time_ms -> INTEGER:", "applied" if applied else "already current")


if __name__ == "__main__":
    main()
