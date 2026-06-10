"""
generate_dashboard.py
---------------------
Reads from ats_tracker.db and writes a Bloomberg-terminal-aesthetic dashboard.

Usage:
    python ats_tracker/generate_dashboard.py
    DB_PATH=/path/to/ats_tracker.db python ats_tracker/generate_dashboard.py
"""

import json
import os
import shutil
import sqlite3
from datetime import date, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT   = SCRIPT_DIR.parent
# Check both the ats_tracker/ subfolder and the repo root for the db
_default_db = SCRIPT_DIR / "ats_tracker.db"
if not _default_db.exists():
    _default_db = REPO_ROOT / "ats_tracker" / "ats_tracker.db"
DB_PATH     = os.environ.get("DB_PATH", str(_default_db))
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


def query_filings_by_day(conn: sqlite3.Connection) -> list:
    """COUNT filings GROUP BY filed_date for past 30 days."""
    from datetime import timedelta
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    sql = """
        SELECT filed_date, COUNT(*) AS count
        FROM ats_filings
        WHERE filed_date >= ?
        GROUP BY filed_date
        ORDER BY filed_date ASC
    """
    try:
        return rows_to_dicts(conn.execute(sql, (cutoff,)).fetchall())
    except sqlite3.OperationalError:
        return []


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


def query_finra_wow_and_share(conn: sqlite3.Connection) -> dict:
    """
    For each (filer_id, symbol) pair, get the two most recent week_ending dates
    and compute WoW % change and market share.
    Returns a dict keyed by (ats_name, symbol, week_ending) -> {wow, mkt_share}.
    """
    # Get all volume data for the top-10 relevant ats+symbol combos
    sql_all = """
        SELECT
            af.ats_name,
            fv.filer_id,
            fv.symbol,
            fv.week_ending,
            fv.shares_traded
        FROM finra_ats_volume fv
        JOIN ats_filers af ON af.id = fv.filer_id
        ORDER BY fv.filer_id, fv.symbol, fv.week_ending DESC
    """
    # Total shares per week across all ATSs
    sql_total = """
        SELECT week_ending, SUM(shares_traded) AS total_shares
        FROM finra_ats_volume
        GROUP BY week_ending
    """
    result = {}
    try:
        rows = rows_to_dicts(conn.execute(sql_all).fetchall())
        totals = {r["week_ending"]: r["total_shares"] for r in rows_to_dicts(conn.execute(sql_total).fetchall())}

        # Group by (filer_id, symbol)
        from collections import defaultdict
        grouped = defaultdict(list)
        for r in rows:
            key = (r["filer_id"], r["symbol"])
            grouped[key].append(r)

        for key, rlist in grouped.items():
            # Already sorted DESC by week_ending
            if len(rlist) >= 2:
                current = rlist[0]
                prior = rlist[1]
                prior_shares = prior["shares_traded"] or 0
                cur_shares = current["shares_traded"] or 0
                if prior_shares and prior_shares != 0:
                    wow = (cur_shares - prior_shares) / prior_shares * 100
                else:
                    wow = None
            else:
                current = rlist[0]
                wow = None

            cur_shares = current["shares_traded"] or 0
            week = current["week_ending"]
            total = totals.get(week) or 0
            mkt_share = (cur_shares / total * 100) if total else None

            result_key = (current["ats_name"], current["symbol"], week)
            result[result_key] = {"wow": wow, "mkt_share": mkt_share}

    except sqlite3.OperationalError:
        pass
    return result


def query_filers_with_volume(conn: sqlite3.Connection) -> list:
    """
    Cross-reference: ATSs that filed an ATS-N in the past 30 days,
    joined to their most recent week of FINRA volume.
    """
    from datetime import timedelta
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    sql = """
        SELECT
            af.ats_name,
            af.ats_mpid,
            af.parent_ticker,
            COUNT(DISTINCT afl.id)          AS filings_30d,
            MAX(afl.filed_date)             AS latest_filing,
            MAX(afl.form_type)              AS latest_form_type,
            COALESCE(SUM(fv.shares_traded), 0) AS total_shares,
            COALESCE(SUM(fv.trades), 0)        AS total_trades,
            MAX(fv.week_ending)             AS latest_week
        FROM ats_filers af
        JOIN ats_filings afl ON afl.filer_id = af.id
            AND afl.filed_date >= ?
        LEFT JOIN finra_ats_volume fv ON fv.filer_id = af.id
            AND fv.week_ending = (
                SELECT MAX(fv2.week_ending)
                FROM finra_ats_volume fv2
                WHERE fv2.filer_id = af.id
            )
        GROUP BY af.id
        ORDER BY total_shares DESC
    """
    try:
        return rows_to_dicts(conn.execute(sql, (cutoff,)).fetchall())
    except sqlite3.OperationalError:
        return []


def query_filers_volume_wow_share(conn: sqlite3.Connection) -> dict:
    """
    For filers_with_volume cross-reference table: compute WoW and market share
    at the ATS level (aggregate across all symbols for that filer's latest week).
    Returns dict keyed by ats_name -> {wow, mkt_share}.
    """
    sql_by_filer_week = """
        SELECT
            af.ats_name,
            fv.filer_id,
            fv.week_ending,
            SUM(fv.shares_traded) AS shares
        FROM finra_ats_volume fv
        JOIN ats_filers af ON af.id = fv.filer_id
        GROUP BY fv.filer_id, fv.week_ending
        ORDER BY fv.filer_id, fv.week_ending DESC
    """
    sql_total = """
        SELECT week_ending, SUM(shares_traded) AS total_shares
        FROM finra_ats_volume
        GROUP BY week_ending
    """
    result = {}
    try:
        rows = rows_to_dicts(conn.execute(sql_by_filer_week).fetchall())
        totals = {r["week_ending"]: r["total_shares"] for r in rows_to_dicts(conn.execute(sql_total).fetchall())}

        from collections import defaultdict
        grouped = defaultdict(list)
        for r in rows:
            grouped[r["filer_id"]].append(r)

        for fid, rlist in grouped.items():
            if len(rlist) >= 2:
                current = rlist[0]
                prior = rlist[1]
                prior_s = prior["shares"] or 0
                cur_s = current["shares"] or 0
                wow = (cur_s - prior_s) / prior_s * 100 if prior_s else None
            else:
                current = rlist[0]
                wow = None
                cur_s = current["shares"] or 0

            week = current["week_ending"]
            total = totals.get(week) or 0
            mkt_share = (cur_s / total * 100) if total else None
            result[current["ats_name"]] = {"wow": wow, "mkt_share": mkt_share}
    except sqlite3.OperationalError:
        pass
    return result


def query_finra_count(conn: sqlite3.Connection) -> int:
    try:
        return conn.execute("SELECT COUNT(*) FROM finra_ats_volume").fetchone()[0]
    except sqlite3.OperationalError:
        return 0


def query_finra_bar_chart_data(conn: sqlite3.Connection) -> list:
    """Top 10 ATSs by total shares aggregated across all symbols/weeks."""
    sql = """
        SELECT
            af.ats_name,
            SUM(fv.shares_traded) AS total_shares
        FROM finra_ats_volume fv
        JOIN ats_filers af ON af.id = fv.filer_id
        GROUP BY fv.filer_id
        ORDER BY total_shares DESC
        LIMIT 10
    """
    try:
        return rows_to_dicts(conn.execute(sql).fetchall())
    except sqlite3.OperationalError:
        return []


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


def query_all_market_data(conn: sqlite3.Connection) -> list:
    """All rows for all tickers ordered by date (last 30 days)."""
    from datetime import timedelta
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    sql = """
        SELECT
            af.parent_ticker AS ticker,
            pmd.date,
            pmd.close
        FROM parent_market_data pmd
        JOIN ats_filers af ON af.id = pmd.filer_id
        WHERE af.parent_ticker IS NOT NULL
          AND pmd.date >= ?
        ORDER BY pmd.date ASC
    """
    try:
        return rows_to_dicts(conn.execute(sql, (cutoff,)).fetchall())
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


def fmt_wow(wow) -> str:
    """Format WoW % change as '+12.3%' or '-8.1%' or '—'."""
    if wow is None:
        return "—"
    sign = "+" if wow >= 0 else ""
    return f"{sign}{wow:.1f}%"


def wow_html(wow) -> str:
    """Return colored HTML span for WoW change."""
    if wow is None:
        return '<span style="color:var(--muted)">—</span>'
    text = fmt_wow(wow)
    cls = "pos" if wow >= 0 else "neg"
    return f'<span class="{cls}">{text}</span>'


def fmt_mkt_share(mkt_share) -> str:
    if mkt_share is None:
        return "—"
    return f"{mkt_share:.1f}%"


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


def build_finra_rows(rows: list, wow_share: dict) -> str:
    if not rows:
        return (
            '<tr><td colspan="7" class="empty-cell">'
            'No FINRA volume data available</td></tr>'
        )
    out = []
    highlight_ats = {"UBS ATS", "Sigma X2"}
    for r in rows:
        ats = r.get("ats_name") or "—"
        symbol = r.get("symbol") or "—"
        week = r.get("week_ending") or "—"
        style = ' style="border-left: 3px solid #00C6FF;"' if ats in highlight_ats else ""

        lookup_key = (ats, symbol, week)
        metrics = wow_share.get(lookup_key, {})
        wow = metrics.get("wow")
        mkt_share = metrics.get("mkt_share")

        out.append(f"""
          <tr{style}>
            <td class="td-name">{ats}</td>
            <td class="td-mono">{symbol}</td>
            <td class="td-mono">{week}</td>
            <td class="td-num">{fmt_shares(r.get('shares_traded'))}</td>
            <td class="td-num">{fmt_shares(r.get('trades'))}</td>
            <td class="td-num">{wow_html(wow)}</td>
            <td class="td-num">{fmt_mkt_share(mkt_share)}</td>
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


def build_filers_volume_rows(rows: list, filer_wow_share: dict) -> str:
    if not rows:
        return (
            '<tr><td colspan="9" class="empty-cell">'
            'No filing activity in the last 30 days</td></tr>'
        )
    out = []
    for r in rows:
        shares = r.get("total_shares") or 0
        trades = r.get("total_trades") or 0
        ticker = r.get("parent_ticker") or ""
        ats_name = r.get("ats_name") or "—"
        ticker_html = f'<span class="ticker-pill">{ticker}</span>' if ticker else "—"
        volume_html = fmt_shares(shares) if shares else '<span class="muted-cell">No FINRA data</span>'
        trades_html = fmt_shares(trades) if trades else "—"
        week_html   = r.get("latest_week") or "—"

        metrics = filer_wow_share.get(ats_name, {})
        wow = metrics.get("wow")
        mkt_share = metrics.get("mkt_share")

        out.append(f"""
          <tr>
            <td class="td-name">{ats_name}</td>
            <td><span class="mpid-badge">{r.get('ats_mpid') or '—'}</span></td>
            <td>{ticker_html}</td>
            <td style="text-align:center">{r.get('filings_30d') or 0}</td>
            <td class="td-mono">{r.get('latest_filing') or '—'}</td>
            <td class="td-num">{volume_html}</td>
            <td class="td-num">{trades_html}</td>
            <td class="td-num">{wow_html(wow)}</td>
            <td class="td-num">{fmt_mkt_share(mkt_share)}</td>
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
# Chart data builders
# ---------------------------------------------------------------------------

def build_finra_chart_json(bar_data: list) -> str:
    """Build JSON for horizontal bar chart (top 10 ATSs by total shares)."""
    labels = [r["ats_name"] for r in bar_data]
    values = [int(r["total_shares"] or 0) for r in bar_data]
    return json.dumps({"labels": labels, "values": values})


def build_price_chart_json(all_market: list) -> str:
    """Build JSON for multi-line price chart per ticker."""
    tickers = ["GS", "JPM", "MS", "UBS", "VIRT"]
    # Collect all dates
    date_set = sorted(set(r["date"] for r in all_market))
    # Build per-ticker series
    series = {}
    for t in tickers:
        price_map = {r["date"]: r["close"] for r in all_market if r["ticker"] == t}
        series[t] = [price_map.get(d) for d in date_set]
    return json.dumps({"dates": date_set, "series": series})


def build_filings_chart_json(filings_by_day: list) -> str:
    """Build JSON for vertical bar chart of filings per day."""
    labels = [r["filed_date"] for r in filings_by_day]
    values = [r["count"] for r in filings_by_day]
    return json.dumps({"labels": labels, "values": values})


# ---------------------------------------------------------------------------
# Full HTML
# ---------------------------------------------------------------------------

def build_html(
    filers: list,
    filings: list,
    finra_top10: list,
    market_data: list,
    filers_volume: list,
    stats: dict,
    generated_at: str,
    wow_share: dict,
    filer_wow_share: dict,
    finra_bar_data: list,
    all_market_data: list,
    filings_by_day: list,
) -> str:
    filings_rows       = build_filings_rows(filings)
    finra_rows         = build_finra_rows(finra_top10, wow_share)
    market_rows        = build_market_rows(market_data)
    filers_volume_rows = build_filers_volume_rows(filers_volume, filer_wow_share)
    registry_html      = build_registry_cards(filers)

    n_filers       = stats["n_filers"]
    n_filings      = stats["n_filings"]
    n_finra        = stats["n_finra"]
    n_market       = stats["n_market"]

    finra_chart_json    = build_finra_chart_json(finra_bar_data)
    price_chart_json    = build_price_chart_json(all_market_data)
    filings_chart_json  = build_filings_chart_json(filings_by_day)

    finra_chart_display    = "" if finra_bar_data else "display:none"
    price_chart_display    = "" if all_market_data else "display:none"
    filings_chart_display  = "" if filings_by_day else "display:none"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ATS Tracker — Mosaic Platforms</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.2/dist/chart.umd.min.js"></script>
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
.muted-cell {{ color: var(--muted); font-style: italic; }}

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

/* ===== CHART CARD ===== */
.chart-card {{
  background: #0f1e38;
  border: 1px solid #1e3060;
  border-radius: 6px;
  padding: 20px;
  margin-bottom: 14px;
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

  <!-- ===== EDGAR FILINGS SECTION ===== -->
  <div class="section">
    <div class="section-hdr">
      <h2>EDGAR Filings</h2>
      <div class="section-rule"></div>
      <div class="section-count">{len(filings)} rows &nbsp;/&nbsp; last 30 days</div>
    </div>

    <!-- Chart 3: Filing Activity by Day -->
    <div class="chart-card" id="filingsChartCard" style="{filings_chart_display}">
      <canvas id="filingsChart" height="180"></canvas>
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

  <!-- ===== FILERS × VOLUME CROSSREF ===== -->
  <div class="section">
    <div class="section-hdr">
      <h2>Recent Filers — Filing Activity vs. FINRA Volume</h2>
      <div class="section-rule"></div>
      <div class="section-count">30-day ATS-N filers only</div>
    </div>
    <div class="table-card">
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>ATS Name</th>
              <th>MPID</th>
              <th>Parent</th>
              <th style="text-align:center">Filings (30d)</th>
              <th>Latest Filing</th>
              <th style="text-align:right">Weekly Shares</th>
              <th style="text-align:right">Weekly Trades</th>
              <th style="text-align:right">WoW Change</th>
              <th style="text-align:right">Mkt Share %</th>
            </tr>
          </thead>
          <tbody>
{filers_volume_rows}
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

      <!-- Chart 1: FINRA Volume Bar Chart -->
      <div class="chart-card" id="finraChartCard" style="{finra_chart_display}">
        <canvas id="finraChart" height="280"></canvas>
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
                <th style="text-align:right">WoW Change</th>
                <th style="text-align:right">Mkt Share %</th>
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

      <!-- Chart 2: Parent Stock Price Lines -->
      <div class="chart-card" id="priceChartCard" style="{price_chart_display}">
        <canvas id="priceChart" height="220"></canvas>
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

<script>
// Chart.js global defaults
Chart.defaults.color = '#6b7fa8';
Chart.defaults.borderColor = '#1e3060';
Chart.defaults.backgroundColor = 'transparent';

// ---- Inline data ----
var finraData    = {finra_chart_json};
var priceData    = {price_chart_json};
var filingsData  = {filings_chart_json};

// ---- Helpers ----
function fmtKM(v) {{
  if (v === null || v === undefined) return '';
  if (v >= 1e9) return (v/1e9).toFixed(1) + 'B';
  if (v >= 1e6) return (v/1e6).toFixed(1) + 'M';
  if (v >= 1e3) return (v/1e3).toFixed(0) + 'K';
  return String(v);
}}

// ---- Chart 1: FINRA Volume Bar (horizontal) ----
(function() {{
  var card = document.getElementById('finraChartCard');
  if (!card || card.style.display === 'none') return;
  if (!finraData.labels || finraData.labels.length === 0) {{ card.style.display = 'none'; return; }}
  var ctx = document.getElementById('finraChart').getContext('2d');
  new Chart(ctx, {{
    type: 'bar',
    data: {{
      labels: finraData.labels,
      datasets: [{{
        label: 'Total Shares',
        data: finraData.values,
        backgroundColor: 'rgba(0, 198, 255, 0.7)',
        borderColor: 'rgba(0, 198, 255, 0.9)',
        borderWidth: 1
      }}]
    }},
    options: {{
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        legend: {{ display: false }},
        tooltip: {{
          callbacks: {{
            label: function(ctx) {{ return ' ' + fmtKM(ctx.raw); }}
          }}
        }}
      }},
      scales: {{
        x: {{
          grid: {{ color: '#1e3060' }},
          ticks: {{
            callback: function(v) {{ return fmtKM(v); }}
          }}
        }},
        y: {{
          grid: {{ color: '#1e3060' }}
        }}
      }}
    }}
  }});
}})();

// ---- Chart 2: Parent Stock Price Lines ----
(function() {{
  var card = document.getElementById('priceChartCard');
  if (!card || card.style.display === 'none') return;
  if (!priceData.dates || priceData.dates.length === 0) {{ card.style.display = 'none'; return; }}
  var colors = {{ GS: '#00C6FF', JPM: '#4e8df5', MS: '#00d68f', UBS: '#ffd32a', VIRT: '#ff6b81' }};
  var datasets = Object.keys(priceData.series).map(function(ticker) {{
    return {{
      label: ticker,
      data: priceData.series[ticker],
      borderColor: colors[ticker] || '#6b7fa8',
      backgroundColor: 'transparent',
      borderWidth: 2,
      pointRadius: 2,
      tension: 0.3,
      spanGaps: true
    }};
  }});
  var ctx = document.getElementById('priceChart').getContext('2d');
  new Chart(ctx, {{
    type: 'line',
    data: {{ labels: priceData.dates, datasets: datasets }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        legend: {{ position: 'top', labels: {{ boxWidth: 10, padding: 12 }} }},
        tooltip: {{
          callbacks: {{
            label: function(ctx) {{
              return ' ' + ctx.dataset.label + ': $' + (ctx.raw !== null ? ctx.raw.toFixed(2) : 'N/A');
            }}
          }}
        }}
      }},
      scales: {{
        x: {{
          grid: {{ color: '#1e3060' }},
          ticks: {{ maxTicksLimit: 8, maxRotation: 30 }}
        }},
        y: {{
          grid: {{ color: '#1e3060' }},
          ticks: {{
            callback: function(v) {{ return '$' + v; }}
          }}
        }}
      }}
    }}
  }});
}})();

// ---- Chart 3: Filing Activity by Day ----
(function() {{
  var card = document.getElementById('filingsChartCard');
  if (!card || card.style.display === 'none') return;
  if (!filingsData.labels || filingsData.labels.length === 0) {{ card.style.display = 'none'; return; }}
  var ctx = document.getElementById('filingsChart').getContext('2d');
  new Chart(ctx, {{
    type: 'bar',
    data: {{
      labels: filingsData.labels,
      datasets: [{{
        label: 'Filings',
        data: filingsData.values,
        backgroundColor: '#4e8df5',
        borderColor: '#4e8df5',
        borderWidth: 1
      }}]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      plugins: {{
        legend: {{ display: false }}
      }},
      scales: {{
        x: {{
          grid: {{ color: '#1e3060' }},
          ticks: {{ maxRotation: 45, maxTicksLimit: 12 }}
        }},
        y: {{
          grid: {{ color: '#1e3060' }},
          ticks: {{ stepSize: 1 }}
        }}
      }}
    }}
  }});
}})();
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

    if conn:
        filers         = query_filers(conn)
        filings        = query_filings_30d(conn)
        finra_top10    = query_finra_top10(conn)
        market_data    = query_market_data_latest(conn)
        filers_volume  = query_filers_with_volume(conn)
        n_filings      = query_filings_count_30d(conn)
        n_finra        = query_finra_count(conn)
        n_market       = query_market_data_count(conn)
        wow_share      = query_finra_wow_and_share(conn)
        filer_wow_share = query_filers_volume_wow_share(conn)
        finra_bar_data = query_finra_bar_chart_data(conn)
        all_market_data = query_all_market_data(conn)
        filings_by_day = query_filings_by_day(conn)
        conn.close()
    else:
        filers = filings = finra_top10 = market_data = filers_volume = []
        n_filings = n_finra = n_market = 0
        wow_share = {}
        filer_wow_share = {}
        finra_bar_data = []
        all_market_data = []
        filings_by_day = []

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
        filers_volume=filers_volume,
        stats=stats,
        generated_at=generated_at,
        wow_share=wow_share,
        filer_wow_share=filer_wow_share,
        finra_bar_data=finra_bar_data,
        all_market_data=all_market_data,
        filings_by_day=filings_by_day,
    )

    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"Dashboard written: {OUT_PATH}")

    ROOT_COPY.write_text(html, encoding="utf-8")
    print(f"Root copy written: {ROOT_COPY}")
    print("Success.")


if __name__ == "__main__":
    main()
