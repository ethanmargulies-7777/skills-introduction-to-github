"""
ingest/market.py — Fetch daily OHLCV + market cap for ATS parent companies
using yfinance.

Only tickers where parent_ticker is not None in ATS_REGISTRY are fetched.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import yfinance as yf

from ats_tracker.config import ATS_REGISTRY

logger = logging.getLogger(__name__)


def _get_parent_tickers() -> dict[str, str]:
    """
    Return {ticker: cik} for all entries in ATS_REGISTRY with a non-None parent_ticker.
    """
    mapping: dict[str, str] = {}
    for cik, meta in ATS_REGISTRY.items():
        ticker = meta.get("parent_ticker")
        if ticker:
            mapping[ticker] = cik
    return mapping


def fetch_parent_prices(period: str = "1mo") -> list[dict[str, Any]]:
    """
    Download daily OHLCV for all parent-company tickers and augment with
    market cap from fast_info.

    Args:
        period: yfinance period string, e.g. "1mo", "3mo", "1y".

    Returns:
        List of dicts with keys matching the `parent_market_data` schema:
            filer_cik, date, open, high, low, close, volume, market_cap, fetched_at
        (filer_cik is included so the pipeline can resolve filer_id via the DB)
    """
    ticker_to_cik = _get_parent_tickers()
    if not ticker_to_cik:
        logger.warning("No parent tickers found in ATS_REGISTRY")
        return []

    tickers = list(ticker_to_cik.keys())
    logger.info("Downloading yfinance data for: %s", tickers)

    fetched_at = datetime.utcnow().isoformat(timespec="seconds")

    # Bulk download OHLCV
    try:
        raw = yf.download(
            tickers=tickers,
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False,
            group_by="ticker",
            threads=True,
        )
    except Exception as exc:
        logger.error("yfinance download failed: %s", exc)
        return []

    if raw.empty:
        logger.warning("yfinance returned empty DataFrame")
        return []

    # Fetch market caps individually via fast_info (not available in bulk download)
    market_caps: dict[str, float | None] = {}
    for ticker in tickers:
        try:
            mc = yf.Ticker(ticker).fast_info.market_cap
            market_caps[ticker] = float(mc) if mc else None
        except Exception as exc:
            logger.debug("Could not fetch market cap for %s: %s", ticker, exc)
            market_caps[ticker] = None

    records: list[dict[str, Any]] = []

    for ticker in tickers:
        cik = ticker_to_cik[ticker]
        try:
            # Handle single-ticker vs multi-ticker DataFrame structure
            if len(tickers) == 1:
                ticker_df = raw
            else:
                ticker_df = raw[ticker] if ticker in raw.columns.get_level_values(0) else raw[ticker]
        except (KeyError, AttributeError) as exc:
            logger.warning("Could not extract data for %s: %s", ticker, exc)
            continue

        if ticker_df is None or ticker_df.empty:
            logger.warning("No data returned for %s", ticker)
            continue

        mc = market_caps.get(ticker)

        for idx_date, row in ticker_df.iterrows():
            try:
                date_str = idx_date.date().isoformat() if hasattr(idx_date, "date") else str(idx_date)[:10]
                records.append(
                    {
                        "filer_cik": cik,
                        "date": date_str,
                        "open": _safe_float(row.get("Open")),
                        "high": _safe_float(row.get("High")),
                        "low": _safe_float(row.get("Low")),
                        "close": _safe_float(row.get("Close")),
                        "volume": _safe_int(row.get("Volume")),
                        "market_cap": mc,
                        "fetched_at": fetched_at,
                    }
                )
            except Exception as exc:
                logger.debug("Skipping row for %s on %s: %s", ticker, idx_date, exc)

    logger.info("Collected %d market data records for %d tickers", len(records), len(tickers))
    return records


def _safe_float(val: Any) -> float | None:
    """Convert *val* to float, returning None on failure or NaN."""
    try:
        f = float(val)
        import math
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _safe_int(val: Any) -> int | None:
    """Convert *val* to int, returning None on failure."""
    try:
        f = float(val)
        import math
        return None if math.isnan(f) else int(f)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    period_arg = sys.argv[1] if len(sys.argv) > 1 else "1mo"
    rows = fetch_parent_prices(period=period_arg)
    for r in rows[:15]:
        print(
            f"CIK={r['filer_cik']}  {r['date']}  "
            f"O={r['open']:.2f}  H={r['high']:.2f}  L={r['low']:.2f}  "
            f"C={r['close']:.2f}  V={r['volume']}  MC={r['market_cap']}"
        )
    print(f"\nTotal rows: {len(rows)}")
