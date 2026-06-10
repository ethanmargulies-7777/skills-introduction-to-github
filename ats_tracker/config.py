"""
config.py — API keys (from env vars), constants, and ATS→ticker mapping.
"""

import os

# --- API Keys ---
POLYGON_API_KEY: str = os.getenv("POLYGON_API_KEY", "")

# --- Base URLs ---
EDGAR_BASE: str = "https://efts.sec.gov/LATEST/search-index"
FINRA_ATS_BASE: str = "https://otctransparency.finra.org"
POLYGON_BASE: str = "https://api.polygon.io"

# --- Database ---
DB_PATH: str = os.getenv("DB_PATH", "ats_tracker.db")

# --- Symbols to track for SIP/TRF data ---
TRACKED_SYMBOLS: list[str] = [
    "SPY", "AAPL", "MSFT", "NVDA", "AMZN",
    "GOOGL", "META", "JPM", "GS", "MS",
]

# --- ATS Registry: CIK → operator details ---
ATS_REGISTRY: dict[str, dict] = {
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

# EDGAR ATS-N form types
ATS_N_FORM_TYPES: list[str] = [
    "ATS-N",
    "ATS-N/UA",
    "ATS-N/CA",
    "ATS-N/MA",
    "ATS-N/OFA",
    "ATS-N/W",
]

# HTTP request timeout (seconds)
REQUEST_TIMEOUT: int = 30

# Retry settings for rate-limited APIs
MAX_RETRIES: int = 5
BACKOFF_BASE: float = 2.0  # seconds
