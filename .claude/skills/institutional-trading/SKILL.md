---
name: institutional-trading
description: |
  Expert context for institutional equity trading, market microstructure, and finance fundamentals.
  Auto-load when user asks about trading, markets, equities, order flow, execution, market structure,
  dark pools, algorithms, risk, portfolio management, or finance concepts for their internship.
---

# Institutional Trading — Expert Context

## Market Microstructure

The plumbing of how markets actually work — essential at any ATS or trading firm.

### Venues
| Venue | Type | Description |
|---|---|---|
| NYSE, Nasdaq | Lit exchange | Public quotes, visible order book |
| ATS / Dark pool | Off-exchange | No pre-trade transparency; trades reported post |
| Internalization | Off-exchange | Broker fills order against own inventory |
| SDP (Single-Dealer Platform) | Off-exchange | One broker's proprietary pool |

### Order Types
- **Market order** — execute immediately at best available price; high certainty, high market impact
- **Limit order** — execute only at specified price or better; lower impact, risk of non-fill
- **IOC** (Immediate-or-Cancel) — fill what you can now, cancel the rest
- **MOC/MOO** — Market-on-Close / Market-on-Open; important for index rebalances
- **VWAP/TWAP** — algorithmic execution benchmarks; minimize market impact over time

### Price Discovery
- **Bid-ask spread** — cost of immediacy; wider spread = less liquid
- **NBBO** — National Best Bid and Offer; the best publicly displayed price across all lit venues
- **Mid-point** — (bid + ask) / 2; dark pools often trade here to split the spread
- **Price improvement** — executing better than NBBO; key metric for ATS value proposition

## Adverse Selection & Toxicity

The core problem Mosaic is solving — understand this deeply.

**Adverse selection**: when a counterparty to your trade has better information than you, leading to unfavorable price movement after the trade.

- Institutional investor buys 500k shares → price moves up → they paid too much
- The counterparty (HFT/market maker) read the signal and positioned ahead
- **Toxicity** = measure of how often a flow source causes this outcome for market makers

**Why it matters for Mosaic**: MERIT scores participants by their toxicity profile. Low-toxicity investors get matched with willing risk providers. High-toxicity flow (e.g., aggressive HFT) is excluded or penalized.

**Related concepts:**
- **Information leakage** — your order revealing your intent before full execution
- **Market impact** — how much your order moves the price
- **Implementation shortfall** — total cost of execution vs. decision price; the benchmark for institutional traders
- **VPIN** (Volume-synchronized Probability of Informed trading) — academic measure of toxicity

## Execution Algorithms

How institutional orders are actually worked in the market:

- **VWAP algo** — slice order to match volume throughout the day; minimize market impact
- **TWAP algo** — slice order evenly over time; simpler, less adaptive
- **POV** (Percent of Volume) — participate at X% of market volume
- **Arrival Price / IS algo** — minimize implementation shortfall; trade aggressively if market moves against you
- **Dark aggregator** — routes to multiple dark pools and ATS to find liquidity without signaling

## Buy-Side vs. Sell-Side

| | Buy-Side | Sell-Side |
|---|---|---|
| Who | Asset managers, hedge funds, pension funds | Banks, broker-dealers |
| Role | Invest capital | Provide liquidity, execution, research |
| At Mosaic | "Investors" in MERIT framework | "Risk providers" in MERIT framework |
| P&L driver | Alpha generation, risk-adjusted returns | Spread capture, commissions, prop trading |

## Key Regulations (U.S. Equities)

- **Reg NMS (2005)** — mandates best execution, defines NBBO, governs order routing. Created the fragmented multi-venue market that dark pools thrive in.
- **Reg ATS** — governs alternative trading systems; requires Form ATS-N filing with SEC for equity ATS operators (Mosaic filed this)
- **Rule 605/606** — execution quality and order routing disclosure requirements; used by buy-side to evaluate brokers
- **Dodd-Frank** — post-2008 reform; mostly fixed income / derivatives, but shaped institutional market structure broadly
- **MiFID II** — European equivalent; important for global context; strict best execution and dark pool caps

## Essential Finance Vocabulary

| Term | Definition |
|---|---|
| Alpha | Return above benchmark; the goal of every buy-side firm |
| Beta | Sensitivity to market moves; systematic risk |
| Sharpe ratio | Risk-adjusted return = (return - risk free rate) / std dev |
| AUM | Assets under management |
| Basis point (bps) | 1/100th of 1%; execution costs are measured in bps |
| Fill rate | % of order that gets executed; key ATS metric |
| Liquidity | Ease of trading without moving price |
| Spread capture | How market makers profit from bid-ask spread |
| Short selling | Borrowing and selling shares, betting on price decline |
| Prime brokerage | Services (leverage, stock lending, clearing) for hedge funds |

## Thinking Like an Institutional Trader

- **Everything is in basis points.** A 5bps improvement in execution on $1B AUM = $500k/year.
- **Liquidity has a cost.** The faster you need to trade, the more you pay.
- **Anonymity is valuable.** Revealing your order = others trading against you.
- **Flow quality matters.** A dark pool that attracts toxic flow is worthless to long-only investors.
- **Risk is always bilateral.** Every trade has a buyer and seller; understanding the other side's motive is the edge.
- **Execution quality is auditable.** TCA (Transaction Cost Analysis) measures every trade; bad venues get cut.

## TCA — Transaction Cost Analysis

How institutional buy-side evaluates execution quality — and how Mosaic will be judged.

- **Benchmark**: arrival price, VWAP, TWAP, close price
- **Slippage**: actual execution price vs. benchmark
- **Market impact**: estimated price movement caused by your order
- **Spread cost**: half the bid-ask spread, paid on every trade
- Good ATS = consistently low slippage, high fill rate, minimal market impact
