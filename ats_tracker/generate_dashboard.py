"""
generate_dashboard.py
---------------------
Reads from ats_tracker.db and writes a self-contained dashboard.html
with all data embedded as JSON.

Usage:
    python ats_tracker/generate_dashboard.py
    DB_PATH=/path/to/ats_tracker.db python ats_tracker/generate_dashboard.py
"""

import json
import os
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).parent
DB_PATH = os.environ.get("DB_PATH", str(SCRIPT_DIR / "ats_tracker.db"))
OUT_PATH = SCRIPT_DIR / "dashboard.html"


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def get_conn(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def rows_to_dicts(rows) -> list[dict]:
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Query functions (all return plain Python structures)
# ---------------------------------------------------------------------------

def query_filings_this_month(conn: sqlite3.Connection) -> list[dict]:
    today = date.today()
    month_start = today.replace(day=1).isoformat()
    sql = """
        SELECT
            af.operator_name,
            af.ats_name,
            afl.form_type,
            afl.filed_date,
            afl.description
        FROM ats_filings afl
        JOIN ats_filers af ON af.id = afl.filer_id
        WHERE afl.filed_date >= ?
        ORDER BY afl.filed_date DESC
    """
    try:
        rows = conn.execute(sql, (month_start,)).fetchall()
        return rows_to_dicts(rows)
    except sqlite3.OperationalError:
        return []


def query_filing_counts_this_month(conn: sqlite3.Connection) -> int:
    today = date.today()
    month_start = today.replace(day=1).isoformat()
    sql = "SELECT COUNT(*) FROM ats_filings WHERE filed_date >= ?"
    try:
        return conn.execute(sql, (month_start,)).fetchone()[0]
    except sqlite3.OperationalError:
        return 0


def query_total_ats_tracked(conn: sqlite3.Connection) -> int:
    sql = "SELECT COUNT(*) FROM ats_filers"
    try:
        return conn.execute(sql).fetchone()[0]
    except sqlite3.OperationalError:
        return 0


def query_parent_market_data(conn: sqlite3.Connection) -> dict:
    """
    Returns {ticker: [{date, open, high, low, close, volume}, ...]} sorted oldest→newest.
    Only includes tickers that have data in the last 45 days.
    """
    sql = """
        SELECT
            af.parent_ticker AS ticker,
            pmd.date,
            pmd.open,
            pmd.high,
            pmd.low,
            pmd.close,
            pmd.volume
        FROM parent_market_data pmd
        JOIN ats_filers af ON af.id = pmd.filer_id
        WHERE af.parent_ticker IS NOT NULL
          AND pmd.date >= date('now', '-45 days')
        ORDER BY af.parent_ticker, pmd.date ASC
    """
    try:
        rows = conn.execute(sql).fetchall()
    except sqlite3.OperationalError:
        return {}

    by_ticker: dict = {}
    for r in rows:
        t = r["ticker"]
        if t not in by_ticker:
            by_ticker[t] = []
        by_ticker[t].append({
            "date": r["date"],
            "close": r["close"],
        })
    return by_ticker


def query_finra_volume(conn: sqlite3.Connection) -> list[dict]:
    """
    Aggregate total shares traded per ATS for the most recent week_ending date.
    Returns [{ats_name, mpid, total_shares}, ...] sorted descending.
    """
    sql_latest = "SELECT MAX(week_ending) FROM finra_ats_volume"
    sql_volume = """
        SELECT
            af.ats_name,
            af.ats_mpid AS mpid,
            SUM(fv.shares_traded) AS total_shares
        FROM finra_ats_volume fv
        JOIN ats_filers af ON af.id = fv.filer_id
        WHERE fv.week_ending = ?
        GROUP BY af.id
        ORDER BY total_shares DESC
    """
    try:
        latest_week = conn.execute(sql_latest).fetchone()[0]
        if not latest_week:
            return []
        rows = conn.execute(sql_volume, (latest_week,)).fetchall()
        result = rows_to_dicts(rows)
        for r in result:
            r["week_ending"] = latest_week
        return result
    except sqlite3.OperationalError:
        return []


def query_largest_volume_ats(conn: sqlite3.Connection) -> str:
    rows = query_finra_volume(conn)
    if not rows:
        return "N/A"
    return rows[0]["ats_name"]


# ---------------------------------------------------------------------------
# Build card data for parent companies
# ---------------------------------------------------------------------------
TRACKED_TICKERS = ["GS", "MS", "JPM", "UBS", "VIRT", "BNP.PA"]
TICKER_LABELS = {
    "GS": "Goldman Sachs",
    "MS": "Morgan Stanley",
    "JPM": "JPMorgan Chase",
    "UBS": "UBS Group",
    "VIRT": "Virtu Financial",
    "BNP.PA": "BNP Paribas",
}


def build_stock_cards(market_data: dict) -> list[dict]:
    cards = []
    for ticker in TRACKED_TICKERS:
        label = TICKER_LABELS.get(ticker, ticker)
        series = market_data.get(ticker, [])
        if not series:
            cards.append({
                "ticker": ticker,
                "label": label,
                "current_price": None,
                "change_30d_pct": None,
                "sparkline": [],
                "positive": None,
            })
            continue

        closes = [s["close"] for s in series if s["close"] is not None]
        dates = [s["date"] for s in series if s["close"] is not None]

        if not closes:
            cards.append({
                "ticker": ticker,
                "label": label,
                "current_price": None,
                "change_30d_pct": None,
                "sparkline": [],
                "positive": None,
            })
            continue

        current = closes[-1]
        # 30-day change: find the close ~30 days ago
        cutoff = None
        from datetime import date as dclass, timedelta
        target = (date.today() - timedelta(days=30)).isoformat()
        # find the closest date at or before target
        price_30d_ago = closes[0]  # default to oldest
        for i, d in enumerate(dates):
            if d <= target:
                price_30d_ago = closes[i]
            else:
                break

        change_pct = ((current - price_30d_ago) / price_30d_ago * 100) if price_30d_ago else None

        cards.append({
            "ticker": ticker,
            "label": label,
            "current_price": round(current, 2),
            "change_30d_pct": round(change_pct, 2) if change_pct is not None else None,
            "sparkline": [round(c, 2) for c in closes[-30:]],
            "positive": change_pct >= 0 if change_pct is not None else None,
        })
    return cards


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ATS Tracker Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --navy:      #0a1628;
    --navy2:     #0f1f3d;
    --navy3:     #162444;
    --navy4:     #1e2f52;
    --cyan:      #00C6FF;
    --cyan2:     #0099cc;
    --green:     #00d68f;
    --red:       #ff4757;
    --yellow:    #ffd32a;
    --blue:      #4e8df5;
    --text:      #e0e8f5;
    --muted:     #7a8fbb;
    --border:    #1e3060;
  }

  body {
    background: var(--navy);
    color: var(--text);
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    font-size: 13px;
    line-height: 1.5;
    min-height: 100vh;
  }

  /* ---- Layout ---- */
  .page-wrap {
    max-width: 1440px;
    margin: 0 auto;
    padding: 20px 24px 40px;
  }

  /* ---- Header ---- */
  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 0 20px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 24px;
  }
  .header-title {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .header-title .dot {
    width: 10px; height: 10px;
    border-radius: 50%;
    background: var(--cyan);
    box-shadow: 0 0 8px var(--cyan);
    animation: pulse 2s infinite;
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }
  .header-title h1 {
    font-size: 18px;
    font-weight: 600;
    letter-spacing: 0.05em;
    color: #fff;
  }
  .header-title .sub {
    font-size: 11px;
    color: var(--muted);
    letter-spacing: 0.08em;
    text-transform: uppercase;
  }
  .header-meta {
    font-size: 11px;
    color: var(--muted);
    text-align: right;
  }
  .header-meta .ts { color: var(--cyan); }

  /* ---- Summary stats row ---- */
  .stats-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin-bottom: 28px;
  }
  .stat-card {
    background: var(--navy2);
    border: 1px solid var(--border);
    border-top: 2px solid var(--cyan);
    border-radius: 6px;
    padding: 16px 18px;
  }
  .stat-card .label {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--muted);
    margin-bottom: 6px;
  }
  .stat-card .value {
    font-size: 26px;
    font-weight: 700;
    color: #fff;
    line-height: 1;
  }
  .stat-card .sub-value {
    font-size: 11px;
    color: var(--muted);
    margin-top: 4px;
  }

  /* ---- Section wrapper ---- */
  .section {
    margin-bottom: 28px;
  }
  .section-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 14px;
  }
  .section-header h2 {
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: var(--cyan);
  }
  .section-header .rule {
    flex: 1;
    height: 1px;
    background: var(--border);
  }

  /* ---- Filings table ---- */
  .table-wrap {
    background: var(--navy2);
    border: 1px solid var(--border);
    border-radius: 6px;
    overflow: hidden;
  }
  table {
    width: 100%;
    border-collapse: collapse;
  }
  thead th {
    background: var(--navy4);
    padding: 10px 14px;
    text-align: left;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--muted);
    border-bottom: 1px solid var(--border);
  }
  tbody tr {
    border-bottom: 1px solid var(--border);
    transition: background 0.15s;
  }
  tbody tr:last-child { border-bottom: none; }
  tbody tr:hover { background: var(--navy3); }
  tbody td {
    padding: 10px 14px;
    vertical-align: middle;
  }
  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }
  .badge-blue   { background: rgba(78,141,245,0.18); color: var(--blue);   border: 1px solid rgba(78,141,245,0.35); }
  .badge-yellow { background: rgba(255,211,42,0.15); color: var(--yellow); border: 1px solid rgba(255,211,42,0.3); }
  .badge-red    { background: rgba(255,71,87,0.15);  color: var(--red);    border: 1px solid rgba(255,71,87,0.3); }
  .badge-gray   { background: rgba(122,143,187,0.15); color: var(--muted); border: 1px solid rgba(122,143,187,0.25); }

  .empty-row td {
    text-align: center;
    color: var(--muted);
    padding: 32px;
    font-style: italic;
  }

  /* ---- Stock cards ---- */
  .stock-grid {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 14px;
  }
  .stock-card {
    background: var(--navy2);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 14px 16px 10px;
    position: relative;
    overflow: hidden;
  }
  .stock-card.positive { border-top: 2px solid var(--green); }
  .stock-card.negative { border-top: 2px solid var(--red); }
  .stock-card.no-data  { border-top: 2px solid var(--border); }
  .stock-card .ticker {
    font-size: 13px;
    font-weight: 700;
    color: #fff;
    letter-spacing: 0.05em;
  }
  .stock-card .company {
    font-size: 10px;
    color: var(--muted);
    margin-top: 1px;
    margin-bottom: 8px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .stock-card .price {
    font-size: 20px;
    font-weight: 700;
    color: #fff;
    line-height: 1;
  }
  .stock-card .change {
    font-size: 12px;
    font-weight: 600;
    margin-top: 3px;
  }
  .stock-card .change.pos { color: var(--green); }
  .stock-card .change.neg { color: var(--red); }
  .stock-card .change.na  { color: var(--muted); }
  .stock-card .sparkline-wrap {
    margin-top: 10px;
    height: 38px;
    position: relative;
  }
  .no-data-msg {
    color: var(--muted);
    font-style: italic;
    font-size: 11px;
    margin-top: 12px;
  }

  /* ---- FINRA volume bar chart ---- */
  .chart-wrap {
    background: var(--navy2);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 20px 24px;
  }
  .chart-container {
    position: relative;
    height: 280px;
  }
  .no-chart-msg {
    height: 280px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--muted);
    font-style: italic;
  }

  /* ---- Footer ---- */
  .footer {
    margin-top: 32px;
    padding-top: 16px;
    border-top: 1px solid var(--border);
    font-size: 11px;
    color: var(--muted);
    text-align: center;
  }
</style>
</head>
<body>
<div class="page-wrap">

  <!-- Header -->
  <div class="header">
    <div class="header-title">
      <div class="dot"></div>
      <div>
        <h1>ATS TRACKER</h1>
        <div class="sub">Alternative Trading System Intelligence Dashboard</div>
      </div>
    </div>
    <div class="header-meta">
      <div>MOSAIC PLATFORMS &mdash; INTERNAL USE ONLY</div>
      <div class="ts" id="ts-label">Last updated: __LAST_UPDATED__</div>
    </div>
  </div>

  <!-- Summary Stats -->
  <div class="stats-row">
    <div class="stat-card">
      <div class="label">ATS-N Filings This Month</div>
      <div class="value" id="stat-filings">__FILINGS_THIS_MONTH__</div>
      <div class="sub-value">SEC EDGAR submissions</div>
    </div>
    <div class="stat-card">
      <div class="label">Total ATSs Tracked</div>
      <div class="value" id="stat-total">__TOTAL_ATS__</div>
      <div class="sub-value">registered operators</div>
    </div>
    <div class="stat-card">
      <div class="label">Largest Volume ATS</div>
      <div class="value" style="font-size:16px; padding-top:5px" id="stat-largest">__LARGEST_VOLUME__</div>
      <div class="sub-value">by weekly shares (FINRA)</div>
    </div>
    <div class="stat-card">
      <div class="label">Data As Of</div>
      <div class="value" style="font-size:16px; padding-top:5px" id="stat-date">__TODAY__</div>
      <div class="sub-value">dashboard generated</div>
    </div>
  </div>

  <!-- Section 1: ATS Filing Activity -->
  <div class="section">
    <div class="section-header">
      <h2>ATS Filing Activity &mdash; This Month</h2>
      <div class="rule"></div>
    </div>
    <div class="table-wrap">
      <table id="filings-table">
        <thead>
          <tr>
            <th>Operator</th>
            <th>ATS Name</th>
            <th>Form Type</th>
            <th>Filed Date</th>
            <th>Description / What Changed</th>
          </tr>
        </thead>
        <tbody id="filings-tbody">
        </tbody>
      </table>
    </div>
  </div>

  <!-- Section 2: Parent Company Stock Performance -->
  <div class="section">
    <div class="section-header">
      <h2>Parent Company Stock Performance</h2>
      <div class="rule"></div>
    </div>
    <div class="stock-grid" id="stock-grid">
    </div>
  </div>

  <!-- Section 3: FINRA ATS Volume Rankings -->
  <div class="section">
    <div class="section-header">
      <h2>FINRA ATS Volume Rankings &mdash; Latest Week</h2>
      <div class="rule"></div>
    </div>
    <div class="chart-wrap">
      <div class="chart-container">
        <canvas id="volume-chart"></canvas>
        <div class="no-chart-msg" id="no-chart-msg" style="display:none">
          No FINRA volume data available yet &mdash; run the FINRA ingestor to populate.
        </div>
      </div>
    </div>
  </div>

  <div class="footer">
    ATS Tracker &bull; Mosaic Platforms &bull; Data sourced from SEC EDGAR, FINRA ATS Transparency, Polygon.io
  </div>
</div>

<script>
// ---- Embedded data ----
const DATA = __JSON_DATA__;

// ---- Form type badge helper ----
function formBadge(formType) {
  const f = (formType || '').toUpperCase();
  if (f.includes('/UA') || f === 'ATS-N/UA') return `<span class="badge badge-blue">${formType}</span>`;
  if (f.includes('/CA') || f === 'ATS-N/CA') return `<span class="badge badge-yellow">${formType}</span>`;
  if (f.includes('/W')  || f === 'ATS-N/W')  return `<span class="badge badge-red">${formType}</span>`;
  if (f === 'ATS-N')                          return `<span class="badge badge-blue">ATS-N</span>`;
  return `<span class="badge badge-gray">${formType}</span>`;
}

// ---- Section 1: Filings table ----
(function renderFilings() {
  const tbody = document.getElementById('filings-tbody');
  const rows = DATA.filings || [];
  if (!rows.length) {
    tbody.innerHTML = '<tr class="empty-row"><td colspan="5">No ATS-N filings found for this month yet.</td></tr>';
    return;
  }
  tbody.innerHTML = rows.map(r => `
    <tr>
      <td>${r.operator_name || '—'}</td>
      <td>${r.ats_name || '—'}</td>
      <td>${formBadge(r.form_type)}</td>
      <td>${r.filed_date || '—'}</td>
      <td style="color:var(--muted); max-width:360px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis">
        ${r.description || '—'}
      </td>
    </tr>
  `).join('');
})();

// ---- Section 2: Stock cards + sparklines ----
(function renderStockCards() {
  const grid = document.getElementById('stock-grid');
  const cards = DATA.stock_cards || [];
  const CYAN = '#00C6FF';
  const GREEN = '#00d68f';
  const RED = '#ff4757';
  const MUTED = '#7a8fbb';

  if (!cards.length) {
    grid.innerHTML = '<div style="color:var(--muted); font-style:italic; padding:20px">No market data available yet.</div>';
    return;
  }

  cards.forEach((card, idx) => {
    const div = document.createElement('div');
    const cls = card.positive === true ? 'positive' : card.positive === false ? 'negative' : 'no-data';
    div.className = `stock-card ${cls}`;

    const priceStr = card.current_price != null ? `$${card.current_price.toFixed(2)}` : '—';
    let changeStr = '—', changeClass = 'na';
    if (card.change_30d_pct != null) {
      const sign = card.change_30d_pct >= 0 ? '+' : '';
      changeStr = `${sign}${card.change_30d_pct.toFixed(2)}% (30d)`;
      changeClass = card.change_30d_pct >= 0 ? 'pos' : 'neg';
    }

    div.innerHTML = `
      <div class="ticker">${card.ticker}</div>
      <div class="company">${card.label}</div>
      <div class="price">${priceStr}</div>
      <div class="change ${changeClass}">${changeStr}</div>
      <div class="sparkline-wrap">
        <canvas id="spark-${idx}" width="200" height="38"></canvas>
        ${(!card.sparkline || !card.sparkline.length) ? '<div class="no-data-msg">No price history</div>' : ''}
      </div>
    `;
    grid.appendChild(div);

    // Draw sparkline after DOM insertion
    if (card.sparkline && card.sparkline.length > 1) {
      const color = card.positive === true ? GREEN : card.positive === false ? RED : MUTED;
      const ctx = document.getElementById(`spark-${idx}`).getContext('2d');
      new Chart(ctx, {
        type: 'line',
        data: {
          labels: card.sparkline.map((_, i) => i),
          datasets: [{
            data: card.sparkline,
            borderColor: color,
            borderWidth: 1.5,
            pointRadius: 0,
            tension: 0.3,
            fill: true,
            backgroundColor: (context) => {
              const chart = context.chart;
              const {ctx: c, chartArea} = chart;
              if (!chartArea) return 'transparent';
              const grad = c.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
              grad.addColorStop(0, color + '44');
              grad.addColorStop(1, color + '00');
              return grad;
            },
          }]
        },
        options: {
          animation: false,
          responsive: false,
          plugins: { legend: { display: false }, tooltip: { enabled: false } },
          scales: {
            x: { display: false },
            y: { display: false }
          }
        }
      });
    }
  });
})();

// ---- Section 3: FINRA Volume Bar Chart ----
(function renderVolumeChart() {
  const volumeData = DATA.finra_volume || [];
  const noMsg = document.getElementById('no-chart-msg');
  const canvas = document.getElementById('volume-chart');

  if (!volumeData.length) {
    canvas.style.display = 'none';
    noMsg.style.display = 'flex';
    return;
  }

  const MOSAIC_MPIDS = ['MOSA', 'MOSAIC'];
  const labels = volumeData.map(d => d.ats_name || d.mpid || '?');
  const values = volumeData.map(d => d.total_shares || 0);
  const colors = volumeData.map(d => {
    if (MOSAIC_MPIDS.includes((d.mpid || '').toUpperCase())) return '#00C6FF';
    return 'rgba(78,141,245,0.65)';
  });
  const borderColors = volumeData.map(d => {
    if (MOSAIC_MPIDS.includes((d.mpid || '').toUpperCase())) return '#00C6FF';
    return 'rgba(78,141,245,0.9)';
  });

  const ctx = canvas.getContext('2d');
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Shares Traded',
        data: values,
        backgroundColor: colors,
        borderColor: borderColors,
        borderWidth: 1,
        borderRadius: 3,
      }]
    },
    options: {
      animation: false,
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0f1f3d',
          borderColor: '#1e3060',
          borderWidth: 1,
          titleColor: '#00C6FF',
          bodyColor: '#e0e8f5',
          callbacks: {
            label: ctx => `${(ctx.parsed.y / 1e6).toFixed(2)}M shares`
          }
        }
      },
      scales: {
        x: {
          ticks: {
            color: '#7a8fbb',
            font: { size: 11 },
            maxRotation: 40,
          },
          grid: { color: 'rgba(30,48,96,0.5)' }
        },
        y: {
          ticks: {
            color: '#7a8fbb',
            font: { size: 11 },
            callback: v => (v / 1e6).toFixed(0) + 'M'
          },
          grid: { color: 'rgba(30,48,96,0.5)' },
          border: { color: 'transparent' }
        }
      }
    }
  });
})();
</script>
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

    # Gather data
    if conn:
        filings = query_filings_this_month(conn)
        filings_count = query_filing_counts_this_month(conn)
        total_ats = query_total_ats_tracked(conn)
        market_data = query_parent_market_data(conn)
        finra_volume = query_finra_volume(conn)
        largest_ats = query_largest_volume_ats(conn)
        conn.close()
    else:
        filings = []
        filings_count = 0
        total_ats = 0
        market_data = {}
        finra_volume = []
        largest_ats = "N/A"

    stock_cards = build_stock_cards(market_data)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today_str = date.today().strftime("%b %d, %Y")

    payload = {
        "filings": filings,
        "stock_cards": stock_cards,
        "finra_volume": finra_volume,
        "meta": {
            "filings_this_month": filings_count,
            "total_ats_tracked": total_ats,
            "largest_volume_ats": largest_ats,
            "generated_at": now,
        }
    }

    json_str = json.dumps(payload, default=str, ensure_ascii=False)

    html = HTML_TEMPLATE
    html = html.replace("__LAST_UPDATED__", now)
    html = html.replace("__FILINGS_THIS_MONTH__", str(filings_count))
    html = html.replace("__TOTAL_ATS__", str(total_ats))
    html = html.replace("__LARGEST_VOLUME__", largest_ats)
    html = html.replace("__TODAY__", today_str)
    html = html.replace("__JSON_DATA__", json_str)

    out = OUT_PATH
    out.write_text(html, encoding="utf-8")
    print(f"Dashboard generated: {out}")


if __name__ == "__main__":
    main()
