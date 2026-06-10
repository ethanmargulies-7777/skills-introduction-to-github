"""
pipeline.py — Orchestrator for the ATS tracker data pipeline.

Steps:
  1. Init DB (create tables if not exist)
  2. EDGAR: fetch recent ATS-N filings → upsert ats_filers + ats_filings
  3. FINRA: fetch weekly ATS volume → insert finra_ats_volume
  4. Market: fetch parent company OHLCV → insert parent_market_data
  5. SIP: fetch TRF off-exchange prints → insert sip_trf_prints
  6. Print summary

Usage:
  python -m ats_tracker.pipeline [options]

  --edgar-only    Run only the EDGAR ingestor
  --finra-only    Run only the FINRA ingestor
  --market-only   Run only the market data ingestor
  --sip-only      Run only the SIP/TRF ingestor
  --dry-run       Fetch data but do not write to the database
  --db PATH       SQLite database path (overrides DB_PATH env var)
  --lookback N    Days to look back for EDGAR filings (default: 30)
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
from datetime import date, datetime
from typing import Any

from ats_tracker.config import DB_PATH, TRACKED_SYMBOLS
from ats_tracker.models import get_connection, init_db, upsert_filer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# DB write helpers
# ---------------------------------------------------------------------------

def _write_filings(conn: sqlite3.Connection, filings: list[dict[str, Any]]) -> int:
    """
    Upsert filers and insert filings. Returns number of new filing rows inserted.
    """
    today = date.today().isoformat()
    inserted = 0

    with conn:
        for f in filings:
            cik: str = f.get("cik", "").strip()
            if not cik:
                logger.debug("Skipping filing with empty CIK: %s", f)
                continue

            operator_name: str = f.get("operator_name") or f.get("entity_name") or "Unknown"
            ats_name: str = f.get("ats_name", "")
            ats_mpid: str | None = f.get("ats_mpid")
            parent_ticker: str | None = f.get("parent_ticker")

            filer_id = upsert_filer(
                conn,
                cik=cik,
                operator_name=operator_name,
                ats_name=ats_name,
                ats_mpid=ats_mpid,
                parent_ticker=parent_ticker,
                today=today,
            )

            filing_url: str = f.get("filing_url", "")
            form_type: str = f.get("form_type", "")
            filed_date: str = f.get("filed_date", "")
            period_of_report: str | None = f.get("period_of_report")
            description: str | None = f.get("description")
            fetched_at = datetime.utcnow().isoformat(timespec="seconds")

            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO ats_filings
                        (filer_id, form_type, filed_date, period_of_report,
                         filing_url, description, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        filer_id,
                        form_type,
                        filed_date,
                        period_of_report,
                        filing_url,
                        description,
                        fetched_at,
                    ),
                )
                if conn.execute("SELECT changes()").fetchone()[0] > 0:
                    inserted += 1
            except sqlite3.IntegrityError as exc:
                logger.debug("Duplicate filing skipped: %s", exc)

    return inserted


def _write_finra_volume(
    conn: sqlite3.Connection,
    records: list[dict[str, Any]],
    mpid_to_filer_id: dict[str, int],
) -> int:
    """
    Insert FINRA volume records. Records without a matching MPID are skipped.
    Returns number of rows inserted.
    """
    inserted = 0
    fetched_at = datetime.utcnow().isoformat(timespec="seconds")

    with conn:
        for rec in records:
            mpid: str = rec.get("mpid", "").strip().upper()
            filer_id = mpid_to_filer_id.get(mpid)
            if filer_id is None:
                logger.debug("No filer_id for MPID %s — skipping", mpid)
                continue

            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO finra_ats_volume
                        (filer_id, week_ending, symbol, tape,
                         shares_traded, trades, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        filer_id,
                        rec.get("week_ending", ""),
                        rec.get("symbol", ""),
                        rec.get("tape", ""),
                        rec.get("shares_traded"),
                        rec.get("trades"),
                        fetched_at,
                    ),
                )
                if conn.execute("SELECT changes()").fetchone()[0] > 0:
                    inserted += 1
            except sqlite3.IntegrityError as exc:
                logger.debug("Duplicate FINRA record skipped: %s", exc)

    return inserted


def _write_market_data(
    conn: sqlite3.Connection,
    records: list[dict[str, Any]],
    cik_to_filer_id: dict[str, int],
) -> int:
    """
    Insert parent market data. Returns rows inserted.
    """
    inserted = 0
    fetched_at = datetime.utcnow().isoformat(timespec="seconds")

    with conn:
        for rec in records:
            cik: str = rec.get("filer_cik", "").strip()
            filer_id = cik_to_filer_id.get(cik)
            if filer_id is None:
                logger.debug("No filer_id for CIK %s — skipping market data row", cik)
                continue

            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO parent_market_data
                        (filer_id, date, open, high, low, close,
                         volume, market_cap, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        filer_id,
                        rec.get("date", ""),
                        rec.get("open"),
                        rec.get("high"),
                        rec.get("low"),
                        rec.get("close"),
                        rec.get("volume"),
                        rec.get("market_cap"),
                        fetched_at,
                    ),
                )
                if conn.execute("SELECT changes()").fetchone()[0] > 0:
                    inserted += 1
            except sqlite3.IntegrityError as exc:
                logger.debug("Duplicate market data skipped: %s", exc)

    return inserted


def _write_sip_prints(
    conn: sqlite3.Connection,
    records: list[dict[str, Any]],
) -> int:
    """Insert SIP TRF print records. Returns rows inserted."""
    inserted = 0

    with conn:
        for rec in records:
            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO sip_trf_prints
                        (symbol, timestamp, price, size, trf_id, conditions,
                         nbbo_bid, nbbo_ask, nbbo_mid, effective_spread_bps, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        rec.get("symbol", ""),
                        rec.get("timestamp", ""),
                        rec.get("price"),
                        rec.get("size"),
                        rec.get("trf_id"),
                        rec.get("conditions"),
                        rec.get("nbbo_bid"),
                        rec.get("nbbo_ask"),
                        rec.get("nbbo_mid"),
                        rec.get("effective_spread_bps"),
                        rec.get("fetched_at", datetime.utcnow().isoformat(timespec="seconds")),
                    ),
                )
                if conn.execute("SELECT changes()").fetchone()[0] > 0:
                    inserted += 1
            except sqlite3.IntegrityError as exc:
                logger.debug("Duplicate SIP print skipped: %s", exc)

    return inserted


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------

def _load_mpid_to_filer_id(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute("SELECT id, ats_mpid FROM ats_filers WHERE ats_mpid IS NOT NULL").fetchall()
    return {row["ats_mpid"].strip().upper(): row["id"] for row in rows}


def _load_cik_to_filer_id(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute("SELECT id, cik FROM ats_filers").fetchall()
    return {row["cik"]: row["id"] for row in rows}


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run(
    db_path: str = DB_PATH,
    run_edgar: bool = True,
    run_finra: bool = True,
    run_market: bool = True,
    run_sip: bool = True,
    dry_run: bool = False,
    lookback_days: int = 30,
) -> None:
    """Execute the full (or partial) ingest pipeline."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    logger.info("=== ATS Tracker Pipeline starting ===")
    logger.info("DB path: %s | dry_run=%s", db_path, dry_run)

    # 1. Init DB
    if not dry_run:
        init_db(db_path)
        logger.info("Database initialised")

    conn = get_connection(db_path) if not dry_run else None

    summary: dict[str, int] = {
        "filings": 0,
        "volume_records": 0,
        "market_rows": 0,
        "trf_prints": 0,
    }

    # 2. EDGAR
    if run_edgar:
        from ats_tracker.ingest.edgar import fetch_recent_filings

        logger.info("--- EDGAR ingest ---")
        filings = fetch_recent_filings(lookback_days=lookback_days)
        summary["filings"] = len(filings)
        logger.info("EDGAR: %d filings fetched", len(filings))

        if not dry_run and conn and filings:
            inserted = _write_filings(conn, filings)
            logger.info("EDGAR: %d new filing rows written", inserted)

    # 3. FINRA
    if run_finra:
        from ats_tracker.ingest.finra import fetch_weekly_volume

        logger.info("--- FINRA ingest ---")
        volume_records = fetch_weekly_volume(weeks=2)
        summary["volume_records"] = len(volume_records)
        logger.info("FINRA: %d volume records fetched", len(volume_records))

        if not dry_run and conn and volume_records:
            mpid_map = _load_mpid_to_filer_id(conn)
            inserted = _write_finra_volume(conn, volume_records, mpid_map)
            logger.info("FINRA: %d new volume rows written", inserted)

    # 4. Market
    if run_market:
        from ats_tracker.ingest.market import fetch_parent_prices

        logger.info("--- Market data ingest ---")
        market_rows = fetch_parent_prices(period="1mo")
        summary["market_rows"] = len(market_rows)
        logger.info("Market: %d OHLCV rows fetched", len(market_rows))

        if not dry_run and conn and market_rows:
            cik_map = _load_cik_to_filer_id(conn)
            inserted = _write_market_data(conn, market_rows, cik_map)
            logger.info("Market: %d new rows written", inserted)

    # 5. SIP / TRF
    if run_sip:
        from ats_tracker.ingest.sip import fetch_trf_prints

        logger.info("--- SIP/TRF ingest ---")
        trf_prints = fetch_trf_prints(symbols=TRACKED_SYMBOLS)
        summary["trf_prints"] = len(trf_prints)
        logger.info("SIP: %d TRF prints fetched", len(trf_prints))

        if not dry_run and conn and trf_prints:
            inserted = _write_sip_prints(conn, trf_prints)
            logger.info("SIP: %d new TRF print rows written", inserted)

    if conn:
        conn.close()

    # 6. Summary
    print("\n=== Pipeline summary ===")
    print(f"  EDGAR filings fetched  : {summary['filings']}")
    print(f"  FINRA volume records   : {summary['volume_records']}")
    print(f"  Market OHLCV rows      : {summary['market_rows']}")
    print(f"  SIP TRF prints         : {summary['trf_prints']}")
    if dry_run:
        print("  (dry-run: nothing written to DB)")
    print("========================\n")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ATS Tracker data pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--db", default=DB_PATH, help="SQLite database path")
    parser.add_argument("--lookback", type=int, default=30, help="EDGAR lookback days")
    parser.add_argument("--dry-run", action="store_true", help="Fetch only; do not write to DB")

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--edgar-only", action="store_true", help="Run EDGAR ingestor only")
    group.add_argument("--finra-only", action="store_true", help="Run FINRA ingestor only")
    group.add_argument("--market-only", action="store_true", help="Run market data ingestor only")
    group.add_argument("--sip-only", action="store_true", help="Run SIP/TRF ingestor only")

    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    run_edgar = True
    run_finra = True
    run_market = True
    run_sip = True

    if args.edgar_only:
        run_finra = run_market = run_sip = False
    elif args.finra_only:
        run_edgar = run_market = run_sip = False
    elif args.market_only:
        run_edgar = run_finra = run_sip = False
    elif args.sip_only:
        run_edgar = run_finra = run_market = False

    run(
        db_path=args.db,
        run_edgar=run_edgar,
        run_finra=run_finra,
        run_market=run_market,
        run_sip=run_sip,
        dry_run=args.dry_run,
        lookback_days=args.lookback,
    )
