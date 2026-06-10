"""
Fetch FINRA ATS weekly transparency data (off-exchange volume by MPID/symbol).

FINRA publishes weekly ATS data via:
  https://otctransparency.finra.org/otctransparency/api/weekly?tier=T1&type=ATS&period=YYYYMMDD

The API returns JSON with a list of weekly records.
"""

from __future__ import annotations

import io
import logging
from datetime import date, timedelta
from typing import Any

import pandas as pd
import requests

logger = logging.getLogger(__name__)

FINRA_API_BASE = "https://otctransparency.finra.org/otctransparency/api/weekly"
# Fallback legacy CSV pattern (may or may not be active)
FINRA_CSV_PATTERN = (
    "https://www.finra.org/sites/default/files/finra-ats-tier{tier}-{date}.csv"
)

HEADERS = {
    "User-Agent": "ats-tracker research@example.com",
    "Accept": "application/json, text/csv, */*",
}


def _last_friday(ref: date | None = None) -> date:
    """Return the most recent Friday on or before *ref* (default: today)."""
    d = ref or date.today()
    # weekday(): Monday=0 … Friday=4
    days_back = (d.weekday() - 4) % 7
    return d - timedelta(days=days_back)


def _fetch_json(tier: str, period: str) -> list[dict[str, Any]]:
    """Try the FINRA OTC Transparency JSON API for one tier/period."""
    url = f"{FINRA_API_BASE}?tier={tier}&type=ATS&period={period}"
    logger.debug("GET %s", url)
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    # API returns either a list or {"data": [...]}
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return payload.get("data", payload.get("records", []))
    return []


def _fetch_csv_fallback(tier_num: int, period: str) -> list[dict[str, Any]]:
    """Fallback: download legacy CSV from FINRA website."""
    url = FINRA_CSV_PATTERN.format(tier=tier_num, date=period)
    logger.debug("Trying CSV fallback GET %s", url)
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    return df.to_dict(orient="records")


def _parse_records(
    raw: list[dict[str, Any]], week_ending_str: str
) -> list[dict[str, Any]]:
    """
    Normalise raw FINRA records into our schema fields.

    FINRA JSON columns vary by endpoint version; we handle common variants.
    """
    results = []
    for rec in raw:
        # Field names seen in different FINRA API versions
        mpid: str = str(
            rec.get("mpid")
            or rec.get("MPID")
            or rec.get("ATS MPID")
            or rec.get("marketParticipantId")
            or ""
        ).strip()

        symbol: str = str(
            rec.get("symbol")
            or rec.get("Symbol")
            or rec.get("issueSymbolIdentifier")
            or rec.get("SYMBOL")
            or ""
        ).strip()

        tape: str = str(
            rec.get("tape")
            or rec.get("Tape")
            or rec.get("tapeId")
            or rec.get("TAPE")
            or ""
        ).strip()

        def _int(val: Any) -> int | None:
            try:
                return int(float(str(val).replace(",", "")))
            except (ValueError, TypeError):
                return None

        shares_traded = _int(
            rec.get("shareQuantity")
            or rec.get("totalWeeklyShareQuantity")
            or rec.get("shares_traded")
            or rec.get("Shares Traded")
            or rec.get("SHARES TRADED")
        )
        trades = _int(
            rec.get("tradeCount")
            or rec.get("totalWeeklyTradeCount")
            or rec.get("trades")
            or rec.get("Trades")
            or rec.get("TRADES")
        )

        if not mpid or not symbol:
            continue

        results.append(
            {
                "mpid": mpid,
                "symbol": symbol,
                "tape": tape,
                "week_ending": week_ending_str,
                "shares_traded": shares_traded,
                "trades": trades,
            }
        )
    return results


def fetch_weekly_volume(
    weeks: int = 2,
) -> list[dict[str, Any]]:
    """
    Fetch *weeks* weeks of FINRA ATS transparency data (Tier 1 + Tier 2).

    Returns list of dicts with keys:
        mpid, symbol, tape, week_ending, shares_traded, trades
    """
    results: list[dict[str, Any]] = []
    ref_friday = _last_friday()

    for week_offset in range(weeks):
        target_date = ref_friday - timedelta(weeks=week_offset)
        period_str = target_date.strftime("%Y%m%d")
        week_ending_iso = target_date.isoformat()
        logger.info("Fetching FINRA ATS data for week ending %s", week_ending_iso)

        for tier_label, tier_num in [("T1", 1), ("T2", 2)]:
            raw: list[dict[str, Any]] = []
            # Try JSON API first
            try:
                raw = _fetch_json(tier_label, period_str)
                logger.info(
                    "FINRA JSON API (%s, %s): %d records", tier_label, period_str, len(raw)
                )
            except requests.RequestException as exc:
                logger.warning("FINRA JSON API failed (%s %s): %s", tier_label, period_str, exc)
                # Try CSV fallback
                try:
                    raw = _fetch_csv_fallback(tier_num, period_str)
                    logger.info(
                        "FINRA CSV fallback (%s, %s): %d records",
                        tier_label,
                        period_str,
                        len(raw),
                    )
                except requests.RequestException as exc2:
                    logger.warning(
                        "FINRA CSV fallback also failed (%s %s): %s",
                        tier_label,
                        period_str,
                        exc2,
                    )
                    continue

            parsed = _parse_records(raw, week_ending_iso)
            results.extend(parsed)

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    records = fetch_weekly_volume(weeks=1)
    if records:
        df = pd.DataFrame(records)
        print(df.head(20).to_string(index=False))
        print(f"\nTotal records: {len(records)}")
    else:
        print("No records returned.")
