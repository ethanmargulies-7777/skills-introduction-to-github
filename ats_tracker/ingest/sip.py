"""
ingest/sip.py — Polygon.io SIP data: TRF off-exchange prints + NBBO.

Off-exchange trades route through FINRA's Trade Reporting Facilities (TRFs).
We identify them by exchange == 4 (FINRA/NYSE TRF) or exchange == 32
(FINRA/Nasdaq TRF) in Polygon's trade records.

Exchange IDs for TRFs in Polygon data:
  4  → FINRA/NYSE TRF (New York)
  32 → FINRA/Nasdaq TRF (Carteret)

API reference:
  GET https://api.polygon.io/v3/trades/{ticker}
  GET https://api.polygon.io/v3/quotes/{ticker}
"""

from __future__ import annotations

import json
import logging
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any

import requests

from ats_tracker.config import (
    BACKOFF_BASE,
    MAX_RETRIES,
    POLYGON_API_KEY,
    POLYGON_BASE,
    REQUEST_TIMEOUT,
)

logger = logging.getLogger(__name__)

# Polygon exchange IDs that represent FINRA TRF prints
TRF_EXCHANGE_IDS: set[int] = {4, 32}

TRADES_ENDPOINT = "/v3/trades/{ticker}"
QUOTES_ENDPOINT = "/v3/quotes/{ticker}"


def _get_with_backoff(url: str, params: dict[str, Any]) -> dict[str, Any]:
    """
    GET *url* with *params*, retrying on 429/5xx with exponential backoff.
    Raises requests.HTTPError on final failure.
    """
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 429:
                wait = BACKOFF_BASE ** attempt
                logger.warning("Rate limited by Polygon, sleeping %.1fs", wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()  # type: ignore[return-value]
        except requests.RequestException as exc:
            if attempt == MAX_RETRIES - 1:
                raise
            wait = BACKOFF_BASE ** attempt
            logger.warning("Polygon request error (%s), retry in %.1fs: %s", attempt + 1, wait, exc)
            time.sleep(wait)
    return {}


def _fetch_all_pages(
    endpoint: str,
    ticker: str,
    params: dict[str, Any],
    max_records: int = 50_000,
) -> list[dict[str, Any]]:
    """
    Iterate Polygon cursor-paginated results until *max_records* reached or
    no next_url is returned.
    """
    url = f"{POLYGON_BASE}{endpoint.format(ticker=ticker)}"
    records: list[dict[str, Any]] = []

    while url and len(records) < max_records:
        data = _get_with_backoff(url, params)
        results = data.get("results", [])
        records.extend(results)

        next_url = data.get("next_url")
        if next_url:
            # next_url already contains all query params including apiKey
            url = next_url
            params = {}  # params are embedded in next_url
        else:
            break

    return records[:max_records]


def _fetch_nbbo_at(ticker: str, timestamp_ns: int) -> tuple[float | None, float | None]:
    """
    Return (bid, ask) for *ticker* at *timestamp_ns* (nanoseconds since epoch).
    Uses Polygon's quotes endpoint with timestamp filter.
    Returns (None, None) on any failure.
    """
    params: dict[str, Any] = {
        "timestamp.lte": timestamp_ns,
        "order": "desc",
        "limit": 1,
        "apiKey": POLYGON_API_KEY,
    }
    url = f"{POLYGON_BASE}{QUOTES_ENDPOINT.format(ticker=ticker)}"
    try:
        data = _get_with_backoff(url, params)
    except requests.RequestException as exc:
        logger.debug("NBBO fetch failed for %s@%d: %s", ticker, timestamp_ns, exc)
        return None, None

    results = data.get("results", [])
    if not results:
        return None, None

    q = results[0]
    bid: float | None = q.get("bid_price") or q.get("bid")
    ask: float | None = q.get("ask_price") or q.get("ask")
    return bid, ask


def _effective_spread_bps(price: float, mid: float) -> float | None:
    """Compute effective spread in basis points: 2 * |price - mid| / mid * 10000."""
    if mid <= 0:
        return None
    return 2.0 * abs(price - mid) / mid * 10_000


def fetch_trf_prints(
    symbols: list[str],
    start: date | None = None,
    end: date | None = None,
    fetch_nbbo: bool = True,
) -> list[dict[str, Any]]:
    """
    Fetch TRF off-exchange prints for each symbol in *symbols* over [start, end].

    Defaults to the previous trading day (yesterday UTC).

    Returns list of dicts matching the `sip_trf_prints` schema:
        symbol, timestamp, price, size, trf_id, conditions,
        nbbo_bid, nbbo_ask, nbbo_mid, effective_spread_bps, fetched_at
    """
    if not POLYGON_API_KEY:
        logger.warning(
            "POLYGON_API_KEY not set — skipping SIP TRF ingest. "
            "Set the POLYGON_API_KEY environment variable."
        )
        return []

    if end is None:
        end = date.today() - timedelta(days=1)
    if start is None:
        start = end  # single day by default

    # Convert to nanosecond epoch boundaries
    start_dt = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)
    end_dt = datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=timezone.utc)
    start_ns = int(start_dt.timestamp() * 1e9)
    end_ns = int(end_dt.timestamp() * 1e9)

    fetched_at = datetime.utcnow().isoformat(timespec="seconds")
    all_records: list[dict[str, Any]] = []

    for symbol in symbols:
        logger.info("Fetching TRF prints for %s (%s → %s)", symbol, start, end)

        params: dict[str, Any] = {
            "timestamp.gte": start_ns,
            "timestamp.lte": end_ns,
            "order": "asc",
            "limit": 50_000,
            "apiKey": POLYGON_API_KEY,
        }

        try:
            trades = _fetch_all_pages(TRADES_ENDPOINT, symbol, params)
        except requests.RequestException as exc:
            logger.error("Failed to fetch trades for %s: %s", symbol, exc)
            continue

        trf_trades = [t for t in trades if t.get("exchange") in TRF_EXCHANGE_IDS]
        logger.info(
            "%s: %d total trades, %d TRF prints", symbol, len(trades), len(trf_trades)
        )

        for trade in trf_trades:
            ts_ns: int = trade.get("participant_timestamp") or trade.get("sip_timestamp") or 0
            price: float = float(trade.get("price", 0))
            size: int = int(trade.get("size", 0))
            exchange_id: int = int(trade.get("exchange", 0))

            # Map Polygon exchange ID to TRF identifier
            # 4 = FINRA/NYSE TRF, 32 = FINRA/Nasdaq TRF
            trf_id: int | None = None
            if exchange_id == 4:
                trf_id = 2  # FINRA/NYSE TRF
            elif exchange_id == 32:
                trf_id = 1  # FINRA/Nasdaq TRF

            raw_conditions = trade.get("conditions", [])
            conditions_json: str | None = json.dumps(raw_conditions) if raw_conditions else None

            ts_str = str(ts_ns)  # store nanoseconds as TEXT per schema

            nbbo_bid: float | None = None
            nbbo_ask: float | None = None
            nbbo_mid: float | None = None
            eff_spread: float | None = None

            if fetch_nbbo and ts_ns:
                nbbo_bid, nbbo_ask = _fetch_nbbo_at(symbol, ts_ns)
                if nbbo_bid is not None and nbbo_ask is not None:
                    nbbo_mid = (nbbo_bid + nbbo_ask) / 2.0
                    if nbbo_mid:
                        eff_spread = _effective_spread_bps(price, nbbo_mid)

            all_records.append(
                {
                    "symbol": symbol,
                    "timestamp": ts_str,
                    "price": price,
                    "size": size,
                    "trf_id": trf_id,
                    "conditions": conditions_json,
                    "nbbo_bid": nbbo_bid,
                    "nbbo_ask": nbbo_ask,
                    "nbbo_mid": nbbo_mid,
                    "effective_spread_bps": eff_spread,
                    "fetched_at": fetched_at,
                }
            )

    logger.info("Total TRF print records collected: %d", len(all_records))
    return all_records


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    syms = sys.argv[1:] if len(sys.argv) > 1 else ["SPY", "AAPL"]
    records = fetch_trf_prints(symbols=syms, fetch_nbbo=False)  # skip NBBO for quick test
    for r in records[:10]:
        print(
            f"{r['symbol']}  {r['timestamp']}  "
            f"px={r['price']:.4f}  sz={r['size']}  trf={r['trf_id']}"
        )
    print(f"\nTotal TRF prints: {len(records)}")
