"""
Fetch recent ATS-N filings from SEC EDGAR full-text search API (EFTS).
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

import requests

logger = logging.getLogger(__name__)

EDGAR_EFTS = (
    "https://efts.sec.gov/LATEST/search-index"
    "?forms=ATS-N%2FUA,ATS-N,ATS-N%2FCA,ATS-N%2FMA,ATS-N%2FOFA,ATS-N%2FW"
    "&dateRange=custom&startdt={start}&enddt={end}"
    "&_source=file_date,entity_name,file_num,period_of_report,form_type,biz_location,inc_states"
    "&hits.hits._source=period_of_report,biz_location,inc_states"
    "&hits.hits.total=true"
)

EDGAR_FILING_BASE = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=ATS-N&dateb=&owner=include&count=10&search_text="

# Known ATS operators: CIK → metadata
ATS_REGISTRY: dict[str, dict[str, Any]] = {
    "0001368727": {
        "operator": "BIDS Trading L.P.",
        "ats_name": "BIDS ATS",
        "mpid": "BIDS",
        "parent_ticker": None,
    },
    "0001110644": {
        "operator": "Liquidnet, Inc.",
        "ats_name": "H2O ATS / Negotiation ATS",
        "mpid": "LQNT",
        "parent_ticker": None,
    },
    "0000042352": {
        "operator": "Goldman Sachs & Co. LLC",
        "ats_name": "Sigma X2",
        "mpid": "SGMT",
        "parent_ticker": "GS",
    },
    "0000782124": {
        "operator": "J.P. Morgan Securities LLC",
        "ats_name": "JPBX",
        "mpid": "JPBX",
        "parent_ticker": "JPM",
    },
    "0000230611": {
        "operator": "UBS Securities LLC",
        "ats_name": "UBS ATS",
        "mpid": "UBSA",
        "parent_ticker": "UBS",
    },
    "0000068136": {
        "operator": "Morgan Stanley & Co. LLC",
        "ats_name": "MS Pool",
        "mpid": "MSPL",
        "parent_ticker": "MS",
    },
    "0001457716": {
        "operator": "Virtu Americas LLC",
        "ats_name": "POSIT / MatchIt",
        "mpid": "VIRT",
        "parent_ticker": "VIRT",
    },
    "0000310607": {
        "operator": "Instinet LLC",
        "ats_name": "CBX",
        "mpid": "INCA",
        "parent_ticker": None,
    },
    "0001609177": {
        "operator": "LeveL Markets LLC",
        "ats_name": "LeveL ATS / Luminex ATS",
        "mpid": "LEVL",
        "parent_ticker": None,
    },
    "0001692652": {
        "operator": "OneChronos Markets LLC",
        "ats_name": "OneChronos ATS",
        "mpid": "ONEC",
        "parent_ticker": None,
    },
    "0000753835": {
        "operator": "BNP Paribas Securities Corp.",
        "ats_name": "BNPP Cortex ATS",
        "mpid": "BNPP",
        "parent_ticker": "BNP.PA",
    },
    "0002065275": {
        "operator": "Mosaic ATS LLC",
        "ats_name": "Mosaic ATS",
        "mpid": "MOSA",
        "parent_ticker": None,
    },
}

HEADERS = {
    "User-Agent": "ats-tracker research@example.com",
    "Accept-Encoding": "gzip, deflate",
}


def _normalize_cik(raw: str) -> str:
    """Zero-pad CIK to 10 digits."""
    return raw.strip().zfill(10)


def _filing_url(accession_raw: str, cik: str) -> str:
    """Build the EDGAR filing index URL from raw accession number."""
    acc = accession_raw.replace("-", "")
    cik_clean = cik.lstrip("0")
    return f"https://www.sec.gov/Archives/edgar/data/{cik_clean}/{acc}/{accession_raw}-index.htm"


def fetch_recent_filings(lookback_days: int = 30) -> list[dict[str, Any]]:
    """
    Query EFTS for ATS-N filings filed in the past *lookback_days* days.

    Returns a list of dicts with keys:
        cik, entity_name, form_type, filed_date, period_of_report,
        filing_url, description, operator_name, ats_name, ats_mpid, parent_ticker
    """
    today = date.today()
    start = today - timedelta(days=lookback_days)

    url = EDGAR_EFTS.format(start=start.isoformat(), end=today.isoformat())
    logger.info("Fetching EDGAR ATS-N filings from %s to %s", start, today)

    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("EDGAR request failed: %s", exc)
        return []

    data = resp.json()
    hits: list[dict[str, Any]] = data.get("hits", {}).get("hits", [])
    logger.info("EDGAR returned %d hits", len(hits))

    results: list[dict[str, Any]] = []
    for hit in hits:
        src: dict[str, Any] = hit.get("_source", {})
        entity_name: str = src.get("entity_name", "")
        form_type: str = src.get("form_type", "")
        filed_date: str = src.get("file_date", "")
        period_of_report: str | None = src.get("period_of_report") or None

        # CIK can live in different fields depending on EFTS version
        raw_cik: str = str(
            src.get("entity_id")
            or src.get("ciks", [""])[0]
            or hit.get("_id", "").split(":")[0]
            or ""
        )
        cik = _normalize_cik(raw_cik) if raw_cik else ""

        # Build accession number from hit _id (format: cik:accession)
        hit_id: str = hit.get("_id", "")
        accession = ""
        if ":" in hit_id:
            accession = hit_id.split(":", 1)[1]

        filing_url = _filing_url(accession, cik) if accession and cik else ""

        # Enrich from registry if available
        registry_entry = ATS_REGISTRY.get(cik, {})
        operator_name: str = registry_entry.get("operator", entity_name)
        ats_name: str = registry_entry.get("ats_name", "")
        ats_mpid: str | None = registry_entry.get("mpid")
        parent_ticker: str | None = registry_entry.get("parent_ticker")

        # Description from filing title/snippet
        description: str | None = hit.get("highlight", {}).get("period_of_report", [None])[0]

        results.append(
            {
                "cik": cik,
                "entity_name": entity_name,
                "operator_name": operator_name,
                "ats_name": ats_name,
                "ats_mpid": ats_mpid,
                "parent_ticker": parent_ticker,
                "form_type": form_type,
                "filed_date": filed_date,
                "period_of_report": period_of_report,
                "filing_url": filing_url,
                "description": description,
            }
        )

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    filings = fetch_recent_filings()
    for f in filings:
        print(
            f"{f['filed_date']}  {f['form_type']:12s}  {f['operator_name']}  "
            f"CIK={f['cik']}  {f['filing_url']}"
        )
    print(f"\nTotal: {len(filings)} filings")
