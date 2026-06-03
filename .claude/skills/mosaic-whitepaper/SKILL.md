---
name: mosaic-whitepaper
description: |
  Deep research context from the Mosaic Platforms white paper research project.
  Covers market structure history, CRBs, HFT/AI, SEC rules, company timelines, and white paper recommendations.
  Auto-load when user asks about the white paper, market exhaust, CRBs, HFT, market structure history,
  execution problems, SEC compliance, or the research timeline project.
---

# Mosaic White Paper Research — Full Context

This skill captures original research compiled for the Mosaic Platforms white paper project.

---

## Core Thesis (White Paper Argument)

Markets evolved away from coordination. Mosaic restores it.

**The execution problem in one line:** CRBs centralized risk but fragmented liquidity — Mosaic operates upstream of this fault line to restore the coordination layer that disappeared post-2008.

**Market Exhaust** = the residual flow that spills into public lit markets after a broker's internal liquidity (CRB/internalization) is exhausted. This is where the worst bps occur — late in execution, after intent is already inferred.

---

## Master Market Structure Timeline (Key Events)

| Year | Event | Impact on Execution |
|---|---|---|
| 1975 | May Day — fixed commissions end | Kickstarts electronic competition, fragmentation |
| 1987 | Black Monday | Shows feedback-loop fragility |
| 1994 | Island ECN founded | Precursor to HFT; liquidity becomes speed-sensitive |
| 1997 | SEC Order Handling Rules | Shifts power from dealers to displayed markets |
| 1998 | Reg ATS adopted | Legal foundation for multi-venue competition |
| 2000 | Decimalization | Spreads compress; displayed size falls; slicing increases |
| 2001 | Maker-taker pricing | Routing decisions skew toward rebates, not completion quality |
| 2001 | Credit Suisse AES launch | Algo execution mainstream; child-order slicing accelerates |
| 2001 | Liquidnet founded | First anonymous institutional block network |
| 2005 | Reg NMS adopted | Trade-through protection + routing complexity increase |
| 2007 | Reg NMS Rule 611 live | Smart routing mandatory; latency arms race intensifies |
| 2008 | GFC / Lehman | Dealer balance sheets shrink; risk warehousing collapses |
| 2010 | Flash Crash | Liquidity withdrew across venues simultaneously; coordination failure exposed |
| 2010 | PFOF expands | Retail flow monetized; public liquidity becomes residual |
| 2011 | Market Access Rule (15c3-5) | CRBs become mandatory infrastructure |
| 2012 | Knight Capital collapse | Iconic automation failure; CRB controls become mission-critical |
| 2013 | IEX approved as ATS | Anti-latency-arb approach validated; "fair vs. speed" debate mainstreams |
| 2016 | IEX approved as exchange | Speed bump legitimized; doesn't solve coordination |
| 2018 | Passive > Active inflection | Execution cost becomes primary driver of net returns |
| 2019 | Commissions go to zero | Retail surge; internalization becomes more central |
| 2020 | COVID volume shock | Fragmentation stress-tested; spreads spike episodically |
| 2022 | Off-exchange ~50% of volume | "Curated liquidity" dominates; public markets absorb residual exhaust |
| 2024 | T+1 settlement goes live | Less time to fund/hedge; liquidity becomes more defensive |
| 2024 | ADV ~16bn shares/day | Record scale; more exhaust potential per parent order |
| 2026 | Mosaic ATS launches | Upstream coordination layer goes live |

---

## Central Risk Books (CRBs) — Full Reference

**Definition:** Firm-wide system that aggregates client and proprietary exposure across all desks, venues, and strategies. Required under Market Access Rule (Rule 15c3-5).

### How CRBs Work Against Execution Quality

| CRB Behavior | What Happens | Mosaic Response |
|---|---|---|
| Front-loaded liquidity | CRBs absorb early execution cheaply (risk initially low) | Creates false sense of progress |
| Back-loaded risk | Risk spikes late; limits hit | Mosaic flattens the impact curve |
| Market exhaust | Residual flow spills into lit markets | Mosaic minimizes exhaust |
| Liquidity withdrawal | CRBs throttle fills when risk limits approach | Mosaic reduces need for throttling |
| Defensive quoting | CRB signals widen spreads when size detected | Mosaic reduces inferable intent |
| No parent-order awareness | CRBs see child orders only, not full intent | Mosaic is parent-aware |
| Cannot coordinate across firms | No risk/intent sharing allowed | Mosaic coordinates outcomes, not risk |

**Key structural insight:** CRBs protect firms, not trades. They are reactive, firm-specific, and optimized for balance sheet — not execution outcomes. Mosaic operates upstream of this, before CRBs react.

**CRB Timeline milestones:**
- 2008: Post-GFC balance sheet retreat → CRBs dominate liquidity decisions
- 2011: Market Access Rule → CRBs become mandatory
- 2012: Knight Capital collapse → Kill-switches and limits hardened
- 2015: CRB + internalization coupling → market exhaust becomes structural
- 2025: CRB saturation acknowledged; risk centralized, liquidity fragmented
- 2026: Demand for upstream coordination layer → Mosaic

---

## HFT & AI — Full Reference

**Core dynamic:** Speed extracts value; coordination preserves it.

| HFT/AI Behavior | Market Impact | Mosaic Response |
|---|---|---|
| Order anticipation | Liquidity turns defensive when size detected | Mosaic removes inference incentives |
| Latency arbitrage | Extracts value without liquidity commitment | Mosaic competes on outcome, not speed |
| Quote flickering | Displayed depth becomes illusory | Mosaic rewards durable interaction |
| Adverse selection filtering | Size punished immediately | Mosaic aligns compatible liquidity |
| AI pattern recognition | Faster detection of execution signatures | Mosaic reduces detectable signals |
| AI adaptive updating | Markets react faster than humans | Mosaic stabilizes interaction |

**Key insights:**
- Mosaic is **not anti-HFT** — it does not ban speed traders; it realigns incentives
- HFT cannot absorb size — short-horizon liquidity only; Mosaic targets parent orders
- AI lowers alpha half-life — signals decay faster; execution cost dominates returns
- Machines punish detectable intent — Mosaic removes the need for inference

**Why speed is no longer the solution:** IEX's speed bump validated the critique of latency arbitrage but didn't solve the coordination gap. Speed is exclusionary and costly. Mosaic competes on a different axis: behavioral compatibility.

---

## SEC Rules — Mosaic Compliance Map

| Rule | Mosaic Risk Level | Key Requirement |
|---|---|---|
| Reg ATS (Rule 300–303) | **High** | Registration, disclosures, fair access; Mosaic must ensure non-discriminatory access |
| Reg NMS Rule 611 | **High** | Cannot bypass protected quotes; MERIT must complement price protection |
| Market Access Rule (15c3-5) | **High** | Must integrate with broker CRBs, not bypass them |
| Best Execution | **High** | Must demonstrate execution improvement without favoritism; measurable outcomes |
| MNPI Rules | **High** | Intent abstraction must not expose material non-public information or cross-participant signals |
| Fair Access (Rule 301(b)(5)) | **Medium-High** | MERIT scoring must not become de-facto exclusion |
| Reg SCI | **Medium-High** | Infrastructure uptime, testing, incident response standards |
| Rule 605/606 | **Medium** | Execution quality must be measurable and defensible |
| CAT | **Medium** | Accurate order lineage and timestamps required |
| Anti-Manipulation (10b-5) | **Medium** | Scoring must not appear exclusionary, discriminatory, or outcome-deterministic |
| Reg SHO | **Low** | Respect short-sale marking and locate mechanics |

**Regulatory narrative:** "Coordination Without Collusion" — Mosaic coordinates outcomes, not risk. No risk sharing, no intent disclosure, no bypass of existing controls.

---

## Competitive Company Timelines (Key)

| Company | Year | Event | Why It Matters |
|---|---|---|---|
| Goldman Sachs | 2015 | SIGMA X becomes top dark pool | Internal liquidity = core institutional channel |
| UBS | 2014 | Public CRB disclosure | Clearest formal definition of CRBs in practice |
| UBS | 2023 | Acquires Credit Suisse | Flow + CRB capacity consolidates materially |
| Liquidnet | 2001 | Founded | First response to information leakage |
| Liquidnet | 2019 | Acquired by TP ICAP | Block trading integrated into broader infrastructure |
| BIDS Trading | 2008 | Launches | Designed to minimize information leakage |
| PureStream | 2018 | Invitation-only ATS | Maximum counterparty control |
| OneChronos | 2018 | Micro-auction model | Alternative price discovery with contained info release |
| Clearpool | 2014 | Founding | Buy-side driven execution innovation (Joe Wald) |
| IEX | 2013/2016 | ATS → Exchange | Latency arbitrage critique validated |
| Instinet CBX | 2020 | Conditional block liquidity | Designed to reduce market exhaust (comparable to Mosaic's goal) |

---

## White Paper Recommendations (GPT Analysis)

### Structure
- Separate parent vs. child order performance — most readers conflate the two
- Include an "Impact vs. Time" visual — show non-linear impact
- Add a "Last 20% of the Order" section — this is where most execution pain lives
- Add a "Today vs. Mosaic" comparison diagram

### Narrative
- Define "Market Exhaust" explicitly upfront
- Frame Mosaic as a **missing coordination layer** — additive, not disruptive
- Use "alpha preservation" not "alpha generation" — avoids regulatory risk
- Avoid anti-HFT framing — emphasize incentive alignment, not exclusion
- End with **inevitability framing**: markets evolved away from coordination; Mosaic restores it

### Regulatory
- Add "Coordination Without Collusion" section — pre-empts SEC concern
- Map Mosaic to Best Execution outcomes — aligns with broker priorities
- Include Reg ATS / Rule 611 alignment note
- Reference CAT conceptually — shows institutional awareness

### Product
- Describe outcomes before mechanics — protects IP
- Keep scoring system abstract — "behavioral alignment," not "ranking"
- Emphasize opt-in and neutrality — participation is voluntary and symmetric
- Acknowledge failure modes briefly — builds credibility

### Evidence
- Use empirical anchors: 5–10% ADV thresholds, late-stage bps ranges
- Reference CAT conceptually without data

---

## Key Reference Sources (from research)
- SEC Market Structure: https://www.sec.gov/marketstructure
- Reg NMS: https://www.sec.gov/rules/final/34-51808.pdf
- Reg ATS: https://www.sec.gov/rules/final/34-40760.pdf
- SEC Algorithmic Trading Report: https://www.sec.gov/files/algorithmic-trading-report-2020.pdf
- FINRA Off-Exchange Data: https://www.finra.org/finra-data/market-transparency
- CFA Institute — Dark Pools & Internalization: https://www.cfainstitute.org/en/research/foundation/2015/dark-pools-internalization-and-equity-market-quality
- Cboe Volume Summary: https://www.cboe.com/insights/posts/us-equities-market-volume-summary/
