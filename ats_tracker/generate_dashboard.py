"""
generate_dashboard.py
---------------------
Reads from ats_tracker.db and writes a Bloomberg-terminal-aesthetic dashboard.

Usage:
    python ats_tracker/generate_dashboard.py
    DB_PATH=/path/to/ats_tracker.db python ats_tracker/generate_dashboard.py
"""

import os
import shutil
import sqlite3
from datetime import date, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT   = SCRIPT_DIR.parent
DB_PATH     = os.environ.get("DB_PATH", str(SCRIPT_DIR / "ats_tracker.db"))
OUT_PATH    = SCRIPT_DIR / "dashboard.html"
ROOT_COPY   = REPO_ROOT  / "ats_dashboard.html"


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def get_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def rows_to_dicts(rows) -> list:
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Query functions
# ---------------------------------------------------------------------------

def query_filers(conn: sqlite3.Connection) -> list:
    try:
        return rows_to_dicts(conn.execute(
            "SELECT * FROM ats_filers ORDER BY ats_name"
        ).fetchall())
    except sqlite3.OperationalError:
        return []


def query_filings_30d(conn: sqlite3.Connection) -> list:
    cutoff = (date.today().replace(day=1)).isoformat()  # month start, per spec "30d"
    # use actual 30 days
    from datetime import timedelta
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    sql = """
        SELECT
            af.ats_name,
            afl.form_type,
            afl.filed_date,
            afl.filing_url,
            afl.description
        FROM ats_filings afl
        JOIN ats_filers af ON af.id = afl.filer_id
        WHERE afl.filed_date >= ?
        ORDER BY afl.filed_date DESC
    """
    try:
        return rows_to_dicts(conn.execute(sql, (cutoff,)).fetchall())
    except sqlite3.OperationalError:
        return []


def query_filings_count_30d(conn: sqlite3.Connection) -> int:
    from datetime import timedelta
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    try:
        return conn.execute(
            "SELECT COUNT(*) FROM ats_filings WHERE filed_date >= ?", (cutoff,)
        ).fetchone()[0]
    except sqlite3.OperationalError:
        return 0


def query_finra_top10(conn: sqlite3.Connection) -> list:
    """Top 10 rows by shares_traded across all data."""
    sql = """
        SELECT
            af.ats_name,
            af.ats_mpid,
            fv.symbol,
            fv.week_ending,
            fv.shares_traded,
            fv.trades
        FROM finra_ats_volume fv
        JOIN ats_filers af ON af.id = fv.filer_id
        ORDER BY fv.shares_traded DESC
        LIMIT 10
    """
    try:
        return rows_to_dicts(conn.execute(sql).fetchall())
    except sqlite3.OperationalError:
        return []


def query_finra_count(conn: sqlite3.Connection) -> int:
    try:
        return conn.execute("SELECT COUNT(*) FROM finra_ats_volume").fetchone()[0]
    except sqlite3.OperationalError:
        return 0


def query_market_data_latest(conn: sqlite3.Connection) -> list:
    """Latest market data row per filer, with 30d-ago close for color coding."""
    sql_latest = """
        SELECT
            af.ats_name,
            af.parent_ticker AS ticker,
            pmd.date,
            pmd.close,
            pmd.volume,
            pmd.market_cap
        FROM parent_market_data pmd
        JOIN ats_filers af ON af.id = pmd.filer_id
        WHERE af.parent_ticker IS NOT NULL
          AND pmd.date = (
              SELECT MAX(p2.date) FROM parent_market_data p2
              WHERE p2.filer_id = pmd.filer_id
          )
        ORDER BY af.parent_ticker
    """
    # Prefer close from ~30 days ago; fall back to oldest available
    sql_30d = """
        SELECT af.parent_ticker AS ticker, pmd.close AS close_30d
        FROM parent_market_data pmd
        JOIN ats_filers af ON af.id = pmd.filer_id
        WHERE af.parent_ticker IS NOT NULL
          AND pmd.date = (
              SELECT COALESCE(
                  (SELECT p2.date FROM parent_market_data p2
                   WHERE p2.filer_id = pmd.filer_id
                     AND p2.date <= date('now', '-30 days')
                   ORDER BY p2.date DESC LIMIT 1),
                  (SELECT MIN(p3.date) FROM parent_market_data p3
                   WHERE p3.filer_id = pmd.filer_id)
              )
          )
        GROUP BY af.id
    """
    try:
        latest = rows_to_dicts(conn.execute(sql_latest).fetchall())
        # deduplicate by ticker (multiple filers may share a ticker)
        seen = {}
        deduped = []
        for r in latest:
            if r["ticker"] not in seen:
                seen[r["ticker"]] = True
                deduped.append(r)
        # attach 30d close
        old = {r["ticker"]: r["close_30d"] for r in rows_to_dicts(conn.execute(sql_30d).fetchall())}
        for r in deduped:
            r["close_30d"] = old.get(r["ticker"])
        return deduped
    except sqlite3.OperationalError:
        return []


def query_market_data_count(conn: sqlite3.Connection) -> int:
    try:
        return conn.execute("SELECT COUNT(*) FROM parent_market_data").fetchone()[0]
    except sqlite3.OperationalError:
        return 0


# ---------------------------------------------------------------------------
# Formatting helpers (Python side — used to build HTML strings)
# ---------------------------------------------------------------------------

def fmt_shares(n):
    if n is None:
        return "—"
    return f"{int(n):,}"


def fmt_mktcap(v):
    if v is None:
        return "—"
    v = float(v)
    if v >= 1e12:
        return f"${v/1e12:.2f}T"
    if v >= 1e9:
        return f"${v/1e9:.0f}B"
    if v >= 1e6:
        return f"${v/1e6:.0f}M"
    return f"${v:,.0f}"


def badge_form_type(ft: str) -> str:
    ft = ft.strip() if ft else ""
    display = ft if ft else "ATS-N/UA"
    ft_up = display.upper()
    if "/UA" in ft_up or ft_up == "ATS-N/UA":
        cls = "badge-blue"
    elif "/CA" in ft_up:
        cls = "badge-yellow"
    elif "/W" in ft_up:
        cls = "badge-red"
    elif ft_up == "ATS-N":
        cls = "badge-blue"
    else:
        cls = "badge-gray"
    return f'<span class="badge {cls}">{display}</span>'


def close_color_class(close, close_30d):
    if close is None or close_30d is None:
        return ""
    return "pos" if float(close) >= float(close_30d) else "neg"


def change_pct_str(close, close_30d):
    if close is None or close_30d is None or float(close_30d) == 0:
        return ""
    pct = (float(close) - float(close_30d)) / float(close_30d) * 100
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.1f}%"


# ---------------------------------------------------------------------------
# HTML builders
# ---------------------------------------------------------------------------

def build_filings_rows(filings: list) -> str:
    if not filings:
        return (
            '<tr><td colspan="4" class="empty-cell">'
            'No EDGAR filings in the last 30 days</td></tr>'
        )
    rows = []
    for f in filings:
        url = f.get("filing_url") or ""
        link = f'<a href="{url}" target="_blank" class="view-link">View →</a>' if url else "—"
        rows.append(f"""
          <tr>
            <td class="td-name">{f.get('ats_name') or '—'}</td>
            <td>{badge_form_type(f.get('form_type', ''))}</td>
            <td class="td-mono">{f.get('filed_date') or '—'}</td>
            <td>{link}</td>
          </tr>""")
    return "\n".join(rows)


def build_finra_rows(rows: list) -> str:
    if not rows:
        return (
            '<tr><td colspan="5" class="empty-cell">'
            'No FINRA volume data available</td></tr>'
        )
    out = []
    highlight_ats = {"UBS ATS", "Sigma X2"}
    for r in rows:
        ats = r.get("ats_name") or "—"
        style = ' style="border-left: 3px solid #00C6FF;"' if ats in highlight_ats else ""
        out.append(f"""
          <tr{style}>
            <td class="td-name">{ats}</td>
            <td class="td-mono">{r.get('symbol') or '—'}</td>
            <td class="td-mono">{r.get('week_ending') or '—'}</td>
            <td class="td-num">{fmt_shares(r.get('shares_traded'))}</td>
            <td class="td-num">{fmt_shares(r.get('trades'))}</td>
          </tr>""")
    return "\n".join(out)


def build_market_rows(rows: list) -> str:
    if not rows:
        return (
            '<tr><td colspan="6" class="empty-cell">'
            'No market data available</td></tr>'
        )
    out = []
    # map ticker to ATS name for display (use ats_name)
    for r in rows:
        close = r.get("close")
        close_30d = r.get("close_30d")
        cc = close_color_class(close, close_30d)
        chg = change_pct_str(close, close_30d)
        close_str = f"${float(close):.2f}" if close is not None else "—"
        if cc:
            price_html = f'<span class="{cc}">{close_str}</span>'
            if chg:
                price_html += f' <span class="chg {cc}">{chg}</span>'
        else:
            price_html = close_str

        vol_str = fmt_shares(r.get("volume"))
        mc_str  = fmt_mktcap(r.get("market_cap"))
        out.append(f"""
          <tr>
            <td class="td-name">{r.get('ats_name') or '—'}</td>
            <td><span class="ticker-pill">{r.get('ticker') or '—'}</span></td>
            <td class="td-mono">{r.get('date') or '—'}</td>
            <td class="td-num">{price_html}</td>
            <td class="td-num">{vol_str}</td>
            <td class="td-num">{mc_str}</td>
          </tr>""")
    return "\n".join(out)


def build_registry_cards(filers: list) -> str:
    cards = []
    for f in filers:
        name = f.get("ats_name") or "Unknown"
        mpid = f.get("ats_mpid") or ""
        ticker = f.get("parent_ticker") or ""
        is_mosaic = name.lower() == "mosaic ats"
        border_style = ' style="border-color:#00C6FF; box-shadow: 0 0 12px rgba(0,198,255,0.15);"' if is_mosaic else ""
        ticker_badge = f'<span class="ticker-pill" style="margin-left:6px">{ticker}</span>' if ticker else ""
        mpid_html = f'<span class="mpid-badge">{mpid}</span>' if mpid else ""
        mosaic_tag = '<div class="mosaic-tag">OUR ATS</div>' if is_mosaic else ""
        cards.append(f"""
        <div class="registry-card"{border_style}>
          {mosaic_tag}
          <div class="registry-name">{name}</div>
          <div class="registry-meta">{mpid_html}{ticker_badge}</div>
        </div>""")
    return "\n".join(cards)


# ---------------------------------------------------------------------------
# Full HTML
# ---------------------------------------------------------------------------

def build_html(
    filers: list,
    filings: list,
    finra_top10: list,
    market_data: list,
    stats: dict,
    generated_at: str,
) -> str:
    filings_rows  = build_filings_rows(filings)
    finra_rows    = build_finra_rows(finra_top10)
    market_rows   = build_market_rows(market_data)
    registry_html = build_registry_cards(filers)

    n_filers       = stats["n_filers"]
    n_filings      = stats["n_filings"]
    n_finra        = stats["n_finra"]
    n_market       = stats["n_market"]

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ATS Tracker — Mosaic Platforms</title>
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

:root {{
  --navy:    #0a1628;
  --card:    #0f1e38;
  --card2:   #111e35;
  --border:  #1e3060;
  --row-alt: #0d1b32;
  --cyan:    #00C6FF;
  --green:   #00d68f;
  --red:     #ff4757;
  --yellow:  #ffd32a;
  --blue:    #4e8df5;
  --text:    #d8e4f5;
  --muted:   #6b7fa8;
  --white:   #f0f5ff;
}}

body {{
  background: var(--navy);
  color: var(--text);
  font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
  font-size: 13px;
  line-height: 1.55;
  min-height: 100vh;
}}

/* ===== LAYOUT ===== */
.page {{
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 24px 48px;
}}

/* ===== HEADER ===== */
.header {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 0 18px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 24px;
}}
.hdr-left {{
  display: flex;
  align-items: center;
  gap: 14px;
}}
.hdr-logo {{
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 38px; height: 38px;
  background: linear-gradient(135deg, #0d2550, #0a3070);
  border: 1px solid var(--cyan);
  border-radius: 5px;
  font-size: 15px;
  font-weight: 800;
  color: var(--cyan);
  letter-spacing: -1px;
  line-height: 1;
  flex-shrink: 0;
}}
.hdr-title {{ font-size: 20px; font-weight: 700; color: var(--cyan); letter-spacing: 0.06em; }}
.hdr-sub {{ font-size: 10px; color: var(--muted); letter-spacing: 0.1em; text-transform: uppercase; margin-top: 1px; }}
.live-dot {{
  display: inline-block;
  width: 7px; height: 7px;
  background: var(--green);
  border-radius: 50%;
  box-shadow: 0 0 6px var(--green);
  margin-right: 5px;
  animation: blink 2s infinite;
}}
@keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:.3}} }}
.hdr-right {{ text-align: right; font-size: 11px; color: var(--muted); line-height: 1.7; }}
.hdr-right .ts {{ color: var(--cyan); font-variant-numeric: tabular-nums; }}
.hdr-right .badge-venues {{
  display: inline-block;
  background: rgba(0,198,255,.12);
  border: 1px solid rgba(0,198,255,.3);
  border-radius: 3px;
  padding: 1px 8px;
  color: var(--cyan);
  font-size: 11px;
  font-weight: 600;
}}

/* ===== STATS ROW ===== */
.stats-row {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
  margin-bottom: 28px;
}}
.stat-card {{
  background: var(--card);
  border: 1px solid var(--border);
  border-top: 2px solid var(--cyan);
  border-radius: 6px;
  padding: 16px 20px 14px;
  position: relative;
  overflow: hidden;
}}
.stat-card::after {{
  content: '';
  position: absolute;
  top: -20px; right: -20px;
  width: 80px; height: 80px;
  background: radial-gradient(circle, rgba(0,198,255,.07) 0%, transparent 70%);
  pointer-events: none;
}}
.stat-label {{
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--muted);
  margin-bottom: 8px;
}}
.stat-value {{
  font-size: 32px;
  font-weight: 700;
  color: var(--white);
  line-height: 1;
  font-variant-numeric: tabular-nums;
}}
.stat-sub {{
  font-size: 11px;
  color: var(--muted);
  margin-top: 6px;
}}

/* ===== SECTION ===== */
.section {{ margin-bottom: 32px; }}
.section-hdr {{
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}}
.section-hdr h2 {{
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: var(--cyan);
  white-space: nowrap;
}}
.section-rule {{ flex: 1; height: 1px; background: var(--border); }}
.section-count {{
  font-size: 10px;
  color: var(--muted);
  background: rgba(30,48,96,.6);
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 1px 7px;
  font-variant-numeric: tabular-nums;
}}

/* ===== TABLES ===== */
.table-card {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow: hidden;
}}
.table-scroll {{ overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; }}
thead th {{
  background: #0c1a30;
  padding: 9px 14px;
  text-align: left;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--muted);
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}}
tbody tr {{
  border-bottom: 1px solid rgba(30,48,96,.6);
  transition: background .12s;
}}
tbody tr:last-child {{ border-bottom: none; }}
tbody tr:nth-child(even) {{ background: var(--row-alt); }}
tbody tr:hover {{ background: rgba(0,198,255,.05); }}
tbody td {{ padding: 9px 14px; vertical-align: middle; }}
.td-name  {{ font-weight: 500; color: var(--white); }}
.td-mono  {{ font-variant-numeric: tabular-nums; color: var(--muted); font-size: 12px; }}
.td-num   {{ font-variant-numeric: tabular-nums; text-align: right; }}
.empty-cell {{
  text-align: center;
  color: var(--muted);
  font-style: italic;
  padding: 32px !important;
}}

/* ===== BADGES ===== */
.badge {{
  display: inline-block;
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  white-space: nowrap;
}}
.badge-blue   {{ background: rgba(78,141,245,.15);  color: var(--blue);   border: 1px solid rgba(78,141,245,.35); }}
.badge-yellow {{ background: rgba(255,211,42,.12);  color: var(--yellow); border: 1px solid rgba(255,211,42,.3); }}
.badge-red    {{ background: rgba(255,71,87,.12);   color: var(--red);    border: 1px solid rgba(255,71,87,.3); }}
.badge-gray   {{ background: rgba(107,127,168,.12); color: var(--muted);  border: 1px solid rgba(107,127,168,.25); }}
.mpid-badge {{
  display: inline-block;
  background: rgba(0,198,255,.12);
  border: 1px solid rgba(0,198,255,.3);
  border-radius: 3px;
  padding: 1px 7px;
  color: var(--cyan);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
}}
.ticker-pill {{
  display: inline-block;
  background: rgba(78,141,245,.12);
  border: 1px solid rgba(78,141,245,.28);
  border-radius: 3px;
  padding: 1px 7px;
  color: var(--blue);
  font-size: 11px;
  font-weight: 600;
}}

/* ===== LINKS ===== */
.view-link {{
  color: var(--cyan);
  text-decoration: none;
  font-size: 11px;
  font-weight: 600;
  opacity: .8;
  transition: opacity .15s;
}}
.view-link:hover {{ opacity: 1; text-decoration: underline; }}

/* ===== COLOR HELPERS ===== */
.pos {{ color: var(--green); }}
.neg {{ color: var(--red); }}
.chg {{
  font-size: 10px;
  font-weight: 600;
  margin-left: 4px;
  opacity: .85;
}}

/* ===== TWO-COL ROW ===== */
.two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 32px; }}

/* ===== REGISTRY GRID ===== */
.registry-grid {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}}
.registry-card {{
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 14px 16px;
  position: relative;
  transition: border-color .15s, box-shadow .15s;
}}
.registry-card:hover {{ border-color: rgba(0,198,255,.4); }}
.registry-name {{
  font-size: 14px;
  font-weight: 600;
  color: var(--white);
  margin-bottom: 8px;
  line-height: 1.3;
}}
.registry-meta {{ display: flex; align-items: center; flex-wrap: wrap; gap: 6px; }}
.mosaic-tag {{
  position: absolute;
  top: 10px; right: 10px;
  background: rgba(0,198,255,.15);
  border: 1px solid rgba(0,198,255,.4);
  border-radius: 3px;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: var(--cyan);
  padding: 1px 6px;
}}

/* ===== FOOTER ===== */
.footer {{
  margin-top: 40px;
  padding-top: 18px;
  border-top: 1px solid var(--border);
  text-align: center;
  font-size: 11px;
  color: var(--muted);
  line-height: 1.8;
}}
.footer a {{ color: var(--muted); text-decoration: none; }}
.footer a:hover {{ color: var(--cyan); }}

@media (max-width: 900px) {{
  .stats-row {{ grid-template-columns: repeat(2, 1fr); }}
  .two-col   {{ grid-template-columns: 1fr; }}
  .registry-grid {{ grid-template-columns: repeat(2, 1fr); }}
}}
</style>
</head>
<body>
<div class="page">

  <!-- ===== HEADER ===== -->
  <div class="header">
    <div class="hdr-left">
      <div class="hdr-logo">ATS</div>
      <div>
        <div class="hdr-title">ATS TRACKER</div>
        <div class="hdr-sub">Mosaic Platforms &nbsp;|&nbsp; Competitive Intelligence</div>
      </div>
    </div>
    <div class="hdr-right">
      <div><span class="live-dot"></span>Live &nbsp;&mdash;&nbsp; <span class="ts">Last updated: {generated_at}</span></div>
      <div><span class="badge-venues">{n_filers} venues tracked</span></div>
    </div>
  </div>

  <!-- ===== STATS ROW ===== -->
  <div class="stats-row">
    <div class="stat-card">
      <div class="stat-label">ATS Filers</div>
      <div class="stat-value">{n_filers}</div>
      <div class="stat-sub">registered operators</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">EDGAR Filings (30d)</div>
      <div class="stat-value">{n_filings}</div>
      <div class="stat-sub">SEC ATS-N submissions</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">FINRA Volume Rows</div>
      <div class="stat-value">{n_finra}</div>
      <div class="stat-sub">weekly trade data points</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Market Data Points</div>
      <div class="stat-value">{n_market}</div>
      <div class="stat-sub">daily OHLCV rows</div>
    </div>
  </div>

  <!-- ===== EDGAR FILINGS TABLE ===== -->
  <div class="section">
    <div class="section-hdr">
      <h2>EDGAR Filings</h2>
      <div class="section-rule"></div>
      <div class="section-count">{len(filings)} rows &nbsp;/&nbsp; last 30 days</div>
    </div>
    <div class="table-card">
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>ATS Name</th>
              <th>Form Type</th>
              <th>Filed Date</th>
              <th>SEC Filing</th>
            </tr>
          </thead>
          <tbody>
{filings_rows}
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- ===== TWO-COL: FINRA + MARKET DATA ===== -->
  <div class="two-col">

    <!-- FINRA Volume -->
    <div class="section" style="margin-bottom:0">
      <div class="section-hdr">
        <h2>FINRA Volume — Top 10 by Shares</h2>
        <div class="section-rule"></div>
      </div>
      <div class="table-card">
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>ATS</th>
                <th>Symbol</th>
                <th>Week Ending</th>
                <th style="text-align:right">Shares</th>
                <th style="text-align:right">Trades</th>
              </tr>
            </thead>
            <tbody>
{finra_rows}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Market Data -->
    <div class="section" style="margin-bottom:0">
      <div class="section-hdr">
        <h2>Parent Company Market Data</h2>
        <div class="section-rule"></div>
        <div class="section-count">latest close</div>
      </div>
      <div class="table-card">
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>ATS</th>
                <th>Ticker</th>
                <th>Date</th>
                <th style="text-align:right">Close</th>
                <th style="text-align:right">Volume</th>
                <th style="text-align:right">Mkt Cap</th>
              </tr>
            </thead>
            <tbody>
{market_rows}
            </tbody>
          </table>
        </div>
      </div>
    </div>

  </div><!-- /.two-col -->

  <!-- ===== ATS REGISTRY ===== -->
  <div class="section">
    <div class="section-hdr">
      <h2>ATS Registry</h2>
      <div class="section-rule"></div>
      <div class="section-count">{len(filers)} venues</div>
    </div>
    <div class="registry-grid">
{registry_html}
    </div>
  </div>

  <!-- ===== FOOTER ===== -->
  <div class="footer">
    ATS Tracker &nbsp;&bull;&nbsp; Mosaic Platforms &nbsp;&bull;&nbsp;
    Data: SEC EDGAR &middot; FINRA ATS Transparency &middot; Polygon.io<br>
    <span style="font-size:10px">INTERNAL USE ONLY &nbsp;&mdash;&nbsp; {generated_at}</span>
  </div>

</div><!-- /.page -->
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    db_path = DB_PATH
    print(f"Reading database: {db_path}")

    if not Path(db_path).exists():
        print(f"WARNING: {db_path} not found — generating dashboard with empty placeholders.")
        conn = None
    else:
        conn = get_conn(db_path)

    if conn:
        filers      = query_filers(conn)
        filings     = query_filings_30d(conn)
        finra_top10 = query_finra_top10(conn)
        market_data = query_market_data_latest(conn)
        n_filings   = query_filings_count_30d(conn)
        n_finra     = query_finra_count(conn)
        n_market    = query_market_data_count(conn)
        conn.close()
    else:
        filers = filings = finra_top10 = market_data = []
        n_filings = n_finra = n_market = 0

    stats = {
        "n_filers":  len(filers),
        "n_filings": n_filings,
        "n_finra":   n_finra,
        "n_market":  n_market,
    }

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = build_html(
        filers=filers,
        filings=filings,
        finra_top10=finra_top10,
        market_data=market_data,
        stats=stats,
        generated_at=generated_at,
    )

    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Dashboard written: {OUT_PATH}")

    ROOT_COPY.write_text(html, encoding="utf-8")
    print(f"Root copy written: {ROOT_COPY}")


if __name__ == "__main__":
    main()
