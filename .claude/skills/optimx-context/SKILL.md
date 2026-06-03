---
name: optimx-context
description: |
  Company context for OptimX — a neutral pre-trade workflow platform for institutional equity trading.
  Auto-load when user mentions OptimX, David Barnett, bilateral liquidity, IOI aggregation,
  top of waterfall, OMS/EMS integration, or asks to compare OptimX and Mosaic.
---

# OptimX — Company Context

## What OptimX Is

OptimX is a **neutral technology platform** that sits *above* market structure — not a venue, not an ATS. Founded by David Barnett (CEO), it integrates directly with buy-side OMS and EMS systems to aggregate broker indications of interest (IOIs) and liquidity at the **top of the order initiation waterfall**, before any order goes to an algo or venue.

It does not hold risk, execute trades, or compete with its users.

## The Problem It Solves

Three structural failures in institutional equities:

1. **Fragmentation** — 47% of U.S. volume off-exchange; 30+ venues; execution size collapsed to 89 shares/trade average on ATSs
2. **Blotter-scraping decay** — platforms originally designed for buy-side-to-buy-side discovery (Liquidnet, etc.) now dominated by sell-side noise
3. **Commission leakage** — intermediaries extract value from both sides; brokers lose attribution, pay connectivity fees, earn shrinking spreads

## How OptimX Works

- Integrates with buy-side OMS/EMS (no months-long dev lift required)
- Consolidates high- and low-touch broker IOIs onto the trader's desktop in real time
- Named, bilateral, fully attributed — buy side knows exactly who is offering liquidity
- Brokers tier, customize, and segment indications client-by-client
- No orders routed without authorization; no liquidity surfaced without broker control
- Attribution and daily reporting built in

## Revenue Model

Brokers pay OptimX **on success only** — no infrastructure cost, no front-end build required. OptimX claims up to **3x the economics of a routed order** for brokers (full commission from client rather than sharing with venues).

## Market Trends Supporting OptimX

- OTC volume >35% of U.S. equities
- Citadel, Jane Street, Virtu ~20% of daily volume via market maker SDP platforms
- Trajectory ATSs (PureStream, LeveL) surging — passive liquidity seeking growing
- Hosted pools growing rapidly; brokers seeking tailored counterparty interaction
- In EMEA: systematic internalisers (Optiver, XTX) streaming prices bilaterally; Goldman, UBS, JPMorgan doing the same in U.S.

---

## OptimX vs Mosaic — Critical Comparison

| | OptimX | Mosaic |
|---|---|---|
| **Layer** | Above market structure (workflow) | Inside market structure (ATS/venue) |
| **When it acts** | Pre-trade — before order sent anywhere | At-trade — when order reaches ATS |
| **Counterparty model** | Named, bilateral, fully attributed | Anonymous, MERIT-scored compatibility |
| **What it does** | Aggregates broker IOIs onto buy-side desktop | Matches orders via compatibility scoring |
| **Regulatory status** | Technology vendor (not an ATS) | Registered ATS (SEC Form ATS-N) |
| **Competes with** | Liquidnet IOI layer, Iridium, Appital | Liquidnet dark pool, BIDS, Sigma X |
| **Trust mechanism** | Named counterparty + broker control | Anonymous + MERIT behavioral scoring |

**They are not direct competitors.** OptimX captures the discovery/relationship layer. Mosaic captures the execution layer. A trade could flow: OptimX discovery → Mosaic execution.

---

## Professional Critique

**Strengths:**
- "Top of waterfall" positioning is upstream of everything — strategically strong
- "Not a venue" sidesteps Reg ATS, Form ATS-N, and fair access obligations
- 3x economics claim is concrete and broker-motivating
- Bilateral trend section well-grounded in real market data

**Weaknesses:**
- No execution quality data — no fill rate or slippage improvement shown; all structural claims
- 3x economics claim has no methodology; it's a marketing assertion
- OMS/EMS onboarding called "fast" — in practice, buy-side/broker integration takes 6-18 months
- Anti-gaming risk unaddressed — if brokers tier by client, sophisticated buy-side will game the tiering
- EMEA regulatory exposure — named bilateral flow faces MiFID II transparency obligations not resolved in white paper

---

## The Same Problem, Two Philosophies

OptimX and Mosaic both address institutional execution dysfunction — but from opposite angles:

- **OptimX**: solve it with *transparency and named relationships* — you know your counterparty, trust is explicit
- **Mosaic**: solve it with *anonymity and behavioral scoring* — MERIT removes the need to know your counterparty; compatibility is algorithmically verified

These approaches suit different participants:
- Large, relationship-driven buy-side (pension funds, long-only) → OptimX
- Flow that needs anonymity or has no pre-existing broker relationship → Mosaic

## Key People
- **David Barnett** — Founder & CEO, OptimX
- **John Cosenza / Joe Wald** — Co-CEOs, Mosaic

## References (from white paper)
- ESMA Final Report on Equity Transparency under MiFID II, Dec 2024
- Ivy Schmerken, 'A New Era in Bilateral Liquidity', The TRADE, Sep 2024
- Ivy Schmerken, 'The Buy Side Seeks Liquidity in Hosted Pools', Tabb Forum, Apr 2025
- Tabb & Gutenplan, 'Venues Compete for Equity Trades', Bloomberg Intelligence, Oct 2024
- Tabb & Gutenplan, 'Fragmented Markets Are Biggest Challenge to US Buyside Traders', Bloomberg Intelligence, Feb 2025
