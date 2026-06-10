"""
SQLite schema for the ATS tracker.
Uses stdlib sqlite3 — no ORM dependency.
"""

import sqlite3
from pathlib import Path


DDL = [
    """
    CREATE TABLE IF NOT EXISTS ats_filers (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        cik            TEXT UNIQUE NOT NULL,
        operator_name  TEXT NOT NULL,
        ats_name       TEXT NOT NULL,
        ats_mpid       TEXT,
        parent_ticker  TEXT,
        first_seen     DATE NOT NULL,
        last_updated   DATE NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ats_filings (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        filer_id         INTEGER NOT NULL REFERENCES ats_filers(id),
        form_type        TEXT NOT NULL,
        filed_date       DATE NOT NULL,
        period_of_report DATE,
        filing_url       TEXT NOT NULL,
        description      TEXT,
        fetched_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS finra_ats_volume (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        filer_id      INTEGER NOT NULL REFERENCES ats_filers(id),
        week_ending   DATE NOT NULL,
        symbol        TEXT NOT NULL,
        tape          TEXT,
        shares_traded INTEGER,
        trades        INTEGER,
        fetched_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sip_trf_prints (
        id                    INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol                TEXT NOT NULL,
        timestamp             TEXT NOT NULL,
        price                 REAL NOT NULL,
        size                  INTEGER NOT NULL,
        trf_id                INTEGER,
        conditions            TEXT,
        nbbo_bid              REAL,
        nbbo_ask              REAL,
        nbbo_mid              REAL,
        effective_spread_bps  REAL,
        fetched_at            TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS parent_market_data (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        filer_id    INTEGER NOT NULL REFERENCES ats_filers(id),
        date        DATE NOT NULL,
        open        REAL,
        high        REAL,
        low         REAL,
        close       REAL,
        volume      INTEGER,
        market_cap  REAL,
        fetched_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # Unique index to prevent duplicate filing inserts
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_ats_filings
        ON ats_filings(filer_id, form_type, filed_date, filing_url)
    """,
    # Unique index for FINRA volume
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_finra_volume
        ON finra_ats_volume(filer_id, week_ending, symbol)
    """,
    # Unique index for SIP prints
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_sip_prints
        ON sip_trf_prints(symbol, timestamp)
    """,
    # Unique index for market data
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_parent_market_data
        ON parent_market_data(filer_id, date)
    """,
]


def get_connection(db_path: str) -> sqlite3.Connection:
    """Return a sqlite3 connection with FK enforcement and WAL mode."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str) -> None:
    """Create all tables and indexes if they don't already exist."""
    conn = get_connection(db_path)
    with conn:
        for stmt in DDL:
            conn.execute(stmt)
    conn.close()


def upsert_filer(
    conn: sqlite3.Connection,
    cik: str,
    operator_name: str,
    ats_name: str,
    ats_mpid: str | None,
    parent_ticker: str | None,
    today: str,
) -> int:
    """
    Insert or update an ATS filer record.
    Returns the filer's primary key id.
    """
    cur = conn.execute("SELECT id FROM ats_filers WHERE cik = ?", (cik,))
    row = cur.fetchone()
    if row:
        conn.execute(
            """
            UPDATE ats_filers
               SET operator_name = ?, ats_name = ?, ats_mpid = ?,
                   parent_ticker = ?, last_updated = ?
             WHERE cik = ?
            """,
            (operator_name, ats_name, ats_mpid, parent_ticker, today, cik),
        )
        return row["id"]
    else:
        cur = conn.execute(
            """
            INSERT INTO ats_filers
                (cik, operator_name, ats_name, ats_mpid, parent_ticker, first_seen, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (cik, operator_name, ats_name, ats_mpid, parent_ticker, today, today),
        )
        return cur.lastrowid  # type: ignore[return-value]


if __name__ == "__main__":
    import sys

    db = sys.argv[1] if len(sys.argv) > 1 else "ats_tracker.db"
    init_db(db)
    print(f"Database initialised at {Path(db).resolve()}")
