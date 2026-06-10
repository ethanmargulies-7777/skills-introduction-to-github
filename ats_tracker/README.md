# ATS Tracker

A Python data pipeline that tracks Alternative Trading System (ATS) companies
that have filed ATS-N forms with the SEC, correlates them with FINRA weekly
off-exchange volume data, Polygon.io SIP TRF prints, and parent-company market
data from Yahoo Finance.

---

## Project structure

```
ats_tracker/
├── models.py          SQLite schema (stdlib sqlite3)
├── config.py          API keys (env vars), constants, ATS registry
├── pipeline.py        Orchestrator: runs all ingestors, writes to DB
├── ingest/
│   ├── edgar.py       SEC EDGAR EFTS — ATS-N filings (past 30 days)
│   ├── finra.py       FINRA OTC Transparency — weekly ATS volume
│   ├── sip.py         Polygon.io SIP — TRF off-exchange prints + NBBO
│   └── market.py      yfinance — parent company daily OHLCV
└── README.md
```

---

## Setup

### 1. Install dependencies

```bash
pip install requests pandas yfinance
```

### 2. Set environment variables

| Variable | Required | Description |
|---|---|---|
| `POLYGON_API_KEY` | Yes (for SIP) | Polygon.io API key — [get one free](https://polygon.io) |
| `DB_PATH` | No | SQLite file path (default: `ats_tracker.db`) |

```bash
export POLYGON_API_KEY="your_key_here"
export DB_PATH="ats_tracker.db"   # optional
```

### 3. Initialise the database

```bash
python -m ats_tracker.models
```

---

## Running the pipeline

### Full pipeline (all sources)

```bash
python -m ats_tracker.pipeline
```

### Selective ingestors

```bash
python -m ats_tracker.pipeline --edgar-only
python -m ats_tracker.pipeline --finra-only
python -m ats_tracker.pipeline --market-only
python -m ats_tracker.pipeline --sip-only
```

### Dry-run (fetch but do not write to DB)

```bash
python -m ats_tracker.pipeline --dry-run
```

### Custom options

```bash
python -m ats_tracker.pipeline --db /data/ats.db --lookback 60
```

### Run individual ingestors directly

```bash
python -m ats_tracker.ingest.edgar
python -m ats_tracker.ingest.finra
python -m ats_tracker.ingest.market
python -m ats_tracker.ingest.sip SPY AAPL MSFT
```

---

## Database tables

| Table | Description |
|---|---|
| `ats_filers` | Registry of ATS operators that have filed ATS-N |
| `ats_filings` | Each individual ATS-N filing event |
| `finra_ats_volume` | Weekly FINRA ATS transparency data by MPID/symbol |
| `sip_trf_prints` | Off-exchange TRF trade prints with NBBO context |
| `parent_market_data` | Daily OHLCV for publicly traded parent companies |

---

## Data sources

- **SEC EDGAR EFTS** — `https://efts.sec.gov/LATEST/search-index` (no auth required)
- **FINRA OTC Transparency** — `https://otctransparency.finra.org` (no auth required)
- **Polygon.io SIP** — `https://api.polygon.io/v3/trades` (API key required)
- **Yahoo Finance** — via `yfinance` (no auth required)

---

## Notes

- The SIP ingestor skips gracefully if `POLYGON_API_KEY` is not set.
- FINRA volume records are matched to filers via MPID; unrecognised MPIDs are
  logged and skipped (they are not in the ATS_REGISTRY).
- All timestamps for SIP prints are stored as nanosecond epoch strings to
  preserve Polygon's nanosecond precision.
- Unique indexes prevent duplicate rows on re-runs (`INSERT OR IGNORE`).
