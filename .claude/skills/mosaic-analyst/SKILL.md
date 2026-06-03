---
name: mosaic-analyst
description: |
  Role-specific context for a Mosaic Platforms intern doing internal tooling, research, and data analytics.
  Auto-load when user asks about data analysis, Python, SQL, market data, building tools, dashboards,
  research tasks, trade analytics, TCA, or internship work at Mosaic.
---

# Mosaic Intern — Tooling, Research & Data Analytics

## Your Role in Context

At an early-stage ATS, an intern in this function sits at the intersection of:
- **Market data** — raw trade and quote data, order flow, venue statistics
- **Research** — quantitative analysis supporting the MERIT model and business decisions
- **Internal tooling** — dashboards, pipelines, scripts that traders and leadership actually use

Everything you build will be seen by people who have run Goldman Sachs-level operations. Quality and precision matter more than quantity.

---

## Data You Will Likely Encounter

### Market Data Types
| Data | Description | Common Source |
|---|---|---|
| TAQ (Trade and Quote) | Every trade and NBBO quote in U.S. equities, millisecond resolution | NYSE, Nasdaq, SIP |
| OPRA | Options quote data | OPRA feed |
| Order book (L2/L3) | Full depth of market at each venue | Direct feeds |
| FIX messages | Order lifecycle events (new, cancel, fill) | Internal OMS/EMS |
| IOI | Indications of Interest; pre-trade signals | Broker networks |
| Post-trade reports | FINRA/TRF trade reports | FINRA |

### Key Data Concepts
- **SIP vs. direct feed** — SIP is consolidated (slower, cheaper); direct feeds are faster but expensive. ATS analytics use direct feeds.
- **Latency** — in microseconds at the venue level; nanoseconds for HFT. Know which matters for each analysis.
- **Timestamps** — always check which clock. Exchange timestamp ≠ received timestamp ≠ processed timestamp.
- **Symbol mapping** — tickers change; use CUSIP or FIGI for stable identifiers across time.
- **Corporate actions** — splits, dividends, spinoffs corrupt price series. Adjust prices before any analysis.

---

## Tech Stack Likely at a KX-Powered ATS

**KX / kdb+** is the core platform (confirmed by Mosaic's partnership with KX). It's the industry standard for time-series market data at hedge funds and banks.

- **kdb+** — columnar in-memory database optimized for time-series; handles billions of rows in memory
- **q** — the query language for kdb+; terse, array-oriented, unfamiliar at first but powerful
- **Python** — used alongside kdb+ via PyKX or qpython; your primary language for analytics
- **SQL** — you'll use it, but kdb+ q is more common for market data queries

### Python Libraries You Should Know
```
pandas          — core data manipulation; know it cold
numpy           — array math; used in every quant pipeline
polars          — faster pandas alternative; increasingly common
matplotlib/plotly — charting; plotly for interactive dashboards
scipy/statsmodels — statistical analysis
pyarrow         — columnar data, parquet files
jupyterlab      — standard research environment
```

### Data Formats
- **Parquet** — columnar format; fast for large datasets. Prefer over CSV.
- **HDF5** — common for historical tick data storage
- **FIX protocol** — message format for order/execution communication
- **JSON/REST** — internal APIs, config, lightweight tooling

---

## Analytics You'll Likely Build or Support

### TCA (Transaction Cost Analysis)
The primary way buy-side clients will evaluate Mosaic's value. You may build or maintain TCA pipelines.

Key metrics to compute:
- **Arrival price slippage** — (execution price − arrival price) / arrival price × 10,000 bps
- **VWAP slippage** — vs. interval VWAP
- **Market impact** — price move attributable to the order
- **Fill rate** — shares filled / shares submitted
- **Time to fill** — order submission to completion

```python
# Slippage in bps (buy side)
slippage_bps = (exec_price - arrival_price) / arrival_price * 10_000
```

### MERIT Score Analysis
- Cohort analysis: how do investor vs. risk-provider MERIT scores distribute?
- Correlation: MERIT score vs. realized slippage for matched trades
- Backtesting: would historical order flow have scored differently under proposed model changes?

### Venue / Flow Analysis
- Market share by venue (ATS, exchange, internalizer) over time
- Fill rate by order size bucket
- Time-of-day liquidity patterns
- Spread analysis (quoted vs. effective vs. realized)

### Research Support
- Lit review synthesis on market microstructure papers (adverse selection, price discovery)
- Competitive analysis: IEX, Luminex, BIDS, Liquidnet, Instinet — how do their models compare to MERIT?
- SEC EDGAR filings: read Form ATS-N disclosures for competitors

---

## Internal Tooling Patterns

### Dashboard Principles (for trading-floor tools)
- **Real-time first.** Traders want live data, not T+1 reports.
- **Bps everywhere.** Display costs in basis points, not dollars — normalizes across order sizes.
- **Drill-down.** Summary → symbol → time → individual order. Every metric should be explorable.
- **Color conventions.** Green = favorable (price improvement, low slippage). Red = adverse. Stick to industry norms.

### Data Pipeline Best Practices
```python
# Always validate timestamps are in UTC
assert df['timestamp'].dt.tz is not None

# Always adjust for corporate actions before price analysis
# Never compare raw prices across a split date

# Filter out auction prints for intraday analysis
df = df[df['condition'].isin(['@', ' '])]  # Regular trades only (TAQ condition codes)

# Effective spread = 2 * |exec_price - midpoint| * side_sign
midpoint = (bid + ask) / 2
effective_spread_bps = 2 * abs(exec_price - midpoint) / midpoint * 10_000
```

### Git / Version Control for Research
- Commit notebooks in `.py` format (use `jupytext`) — diffs are readable
- Pin library versions in `requirements.txt` or `pyproject.toml`
- Separate data ingestion, transformation, and analysis into distinct scripts

---

## Research Mindset

**Be skeptical of your own results.** In market data analysis:
- Check for survivorship bias (only analyzing stocks that still exist)
- Check for look-ahead bias (using future data to make past decisions)
- Check for selection bias (cherry-picked time periods)
- Validate on out-of-sample data before presenting findings

**Know the relevant academic literature:**
- Glosten-Milgrom (1985) — foundational adverse selection model
- Kyle (1985) — informed trading and market depth
- Amihud (2002) — illiquidity measure
- Easley et al. — VPIN toxicity measure (directly relevant to MERIT)
- Angel, Harris, Spatt (2010, 2015) — equity market structure analysis

**When presenting to leadership (Cosenza/Wald):**
- Lead with the answer, not the methodology
- Show the data, not just the conclusion
- Know the limitations of your analysis before they ask
- Quantify in bps — they think in those terms

---

## Quick Reference — Useful Commands

```python
# Resample tick data to 1-min OHLCV
ohlcv = df.set_index('timestamp').resample('1min')['price'].ogg(['first','max','min','last','sum'])

# Compute VWAP
vwap = (df['price'] * df['size']).sum() / df['size'].sum()

# Rolling realized volatility (annualized, from 5-min returns)
returns = df['mid'].pct_change()
realized_vol = returns.rolling(window=78).std() * (252 * 78) ** 0.5  # 78 5-min bars/day
```
