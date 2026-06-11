---
name: mosaic-visual-design
description: |
  Visual design system for Mosaic Platforms marketing materials, combining David McCandless's
  information design methodology with Mosaic's brand identity and MERIT framework.
  Auto-load when user asks about: marketing design, infographics, pitch decks, one-pagers,
  data visualization, visual communication, charts, diagrams, or brand assets for Mosaic.
---

# Mosaic Visual Design System
## McCandless Method × Mosaic Platforms

---

## Core Philosophy

David McCandless's central thesis: **data has a natural shape — your job is to find it, not invent it.**

For Mosaic, the "data" is market microstructure. The natural shapes are:
- **Flow** (order routing, matching process) → Sankey diagrams, stepped flowcharts
- **Comparison** (Mosaic vs. traditional dark pools) → side-by-side matrix, radar/spider charts
- **Score/Rank** (MERIT scoring) → gradient bars, bubble placement, heat maps
- **Outcome over time** (slippage reduction, fill quality) → clean line charts with annotated inflection points

Never force a pie chart on flow data. Never use a bar chart when you're showing a system.

---

## The Four-Element Test (McCandless)

Before building any visual, verify all four elements are present:

| Element | Mosaic Application |
|---|---|
| **Information** | Source data is real — slippage bps, fill rates, MERIT score distributions, ATS market share |
| **Story** | One clear takeaway per visual — stated in the title as a conclusion, not a label |
| **Goal** | Who is this for? (buy-side PM, broker-dealer, regulator, press) — goal shifts per audience |
| **Visual Form** | Match the chart type to the data's natural structure (see Shape Library below) |

If a visual passes all four, publish it. If any element is weak, redesign before distributing.

---

## Mosaic Brand Voice in Visuals

Mosaic is institutional, credible, and quietly disruptive. Visual tone should match:

- **Not flashy** — no gradients, no 3D effects, no drop shadows
- **Precise** — axis labels, units, and data sources always visible
- **Confident** — titles state conclusions, not questions
- **Honest** — axes start at zero; no truncated scales that exaggerate movement

### Title Convention (McCandless Rule #1)
Write the insight, not the variable:

| Weak Title | Strong Title |
|---|---|
| "Slippage by Venue Type" | "Mosaic participants experience 40% less slippage vs. traditional dark pools" |
| "MERIT Score Distribution" | "High-MERIT counterparties generate 2.3x better fill quality" |
| "ATS Market Share Over Time" | "Compatibility-based matching is gaining share as toxicity costs mount" |

---

## Color System

Mosaic's palette should be minimal and meaningful. Every color earns its place.

### Primary Palette
| Role | Color | Hex | Usage |
|---|---|---|---|
| **Mosaic Blue** | Deep navy | `#0D1B2A` | Backgrounds, headers, primary brand |
| **Signal Teal** | Institutional teal | `#00B4A6` | Key metric, the "this is the point" color |
| **Neutral Stone** | Warm gray | `#8C8C8C` | Comparison data, secondary information |
| **White Space** | Pure white | `#FFFFFF` | Default background; breathing room |

### Semantic Colors (use consistently across all materials)
| Concept | Color | Hex |
|---|---|---|
| Investor (buy-side) | Deep blue | `#1A3A5C` |
| Risk Provider (broker-dealer) | Slate | `#4A6FA5` |
| Toxic flow / adverse outcome | Muted red | `#C0392B` |
| Compatible match / positive outcome | Signal teal | `#00B4A6` |
| MERIT score — high | Teal | `#00B4A6` |
| MERIT score — low | Warm amber | `#E67E22` |

**Rule:** Use Signal Teal for exactly one element per visual — the conclusion the viewer should land on. Everything else is supporting cast.

---

## Shape Library — Chart Types by Concept

### 1. The Matching Problem (Mosaic's core thesis)
**Concept:** Traditional dark pools match on price-time → information leakage  
**Form:** Two-column comparison matrix or a "before/after" split layout  
**McCandless parallel:** His "Left vs Right" political spectrum visuals — clear axis, opposing poles, reader locates themselves

```
TRADITIONAL DARK POOL          MOSAIC ATS
─────────────────────          ──────────────────
Price-time priority     →      Compatibility score
Anonymous counterparty  →      MERIT-vetted match
Toxic flow included     →      Segmented by role
Post-trade regret risk  →      Pre-match compatibility
```

### 2. MERIT Score Visualization
**Concept:** Each participant has a score; higher score = better counterparty  
**Form:** Horizontal ranked bar chart with color gradient (teal → amber for high → low)  
**McCandless parallel:** His "Most Dangerous" country rankings — ordered list, color encodes severity, no legend needed

Key design rule: show the *distribution*, not just the top. The shape of the distribution tells the story.

### 3. Order Flow Journey
**Concept:** How an order moves from buy-side intent → ATS → execution  
**Form:** Horizontal Sankey / stepped flowchart  
**McCandless parallel:** His Snake Oil visualization — linear left-to-right flow, width encodes volume/importance

Steps to show:
```
Buy-side order intent
  → ATS order submission
    → MERIT compatibility check
      → Matched with risk provider
        → Execution
          → Post-trade analytics → MERIT score update (feedback loop)
```

### 4. Slippage Comparison
**Concept:** Mosaic fills at better prices than alternatives  
**Form:** Dot plot or paired bar — one dot/bar per venue, Mosaic highlighted in teal  
**McCandless parallel:** His "Good Country Index" scatter — neutral grey for comparisons, one standout color

Annotation rule: label only the Mosaic bar and the industry average. Let the gap speak.

### 5. Market Structure Landscape
**Concept:** Where Mosaic sits among lit exchanges, traditional dark pools, IEX, etc.  
**Form:** 2×2 matrix — axes are (Transparency ↔ Opacity) × (Price-time ↔ Compatibility)  
**McCandless parallel:** His political compass / media bias charts — quadrant placement, named entities, clear axis labels

Mosaic should sit alone in the "high compatibility, selectively opaque" quadrant — that's the white space it occupies.

---

## Layout Principles

### The McCandless Hierarchy
Every visual has three reading depths. Design for all three:

1. **Glance (0–2 sec):** Title + dominant visual shape → viewer gets the point
2. **Read (5–15 sec):** Axis labels, annotations, key callouts → viewer understands the evidence
3. **Study (30+ sec):** Data source, methodology note, footnotes → viewer can verify and trust

For Mosaic marketing materials: pitch decks need Glance + Read. Whitepapers need all three.

### Whitespace as Signal
McCandless uses negative space to direct attention. For Mosaic:
- One visual per slide/section. No chart grids.
- 40%+ of slide area should be empty.
- The most important number on the page should be the largest element.

### Typography Rules
- **Headline:** Bold, large, states the conclusion — this is the most-read element
- **Subhead:** 60% the size of headline, provides context
- **Data labels:** Small, precise, monospaced font for numbers
- **Source line:** Always present, smallest text on page, bottom-left

---

## Audience-Specific Framing

Same data, different story emphasis per audience:

### Buy-Side (Asset Managers, Hedge Funds)
- Lead with: **slippage reduction, information protection, fill quality**
- Key visual: Slippage comparison dot plot, order flow journey
- Tone: "We protect your alpha"

### Sell-Side / Risk Providers (Broker-Dealers)
- Lead with: **flow quality, MERIT score benefits, volume opportunity**
- Key visual: MERIT score distribution, volume by score tier
- Tone: "Better counterparties, better economics"

### Press / General Market
- Lead with: **the problem (adverse selection), the mechanism (MERIT), the thesis (compatibility > price-time)**
- Key visual: Market structure 2×2, before/after matching comparison
- Tone: "The dark pool model is broken. Here's what replaces it."

### Regulators / Compliance
- Lead with: **transparency, fairness, Form ATS-N disclosure**
- Key visual: MERIT scoring methodology diagram, participant segmentation
- Tone: "Structured, disclosed, auditable"

---

## Anti-Patterns (What Not to Do)

Institutional clients — Mosaic's audience — will notice and distrust these:

| Anti-Pattern | Why It Fails |
|---|---|
| Truncated y-axis | Exaggerates differences; signals manipulation |
| Pie charts for flow data | Pies encode part-of-whole, not sequence or flow |
| Too many colors | Implies too many equally important points; dilutes signal |
| Unlabeled axes | Looks like you're hiding scale |
| "Our results" without methodology | Institutional analysts will ask; have the answer ready |
| Animation in static decks | Distracts from data; signals style over substance |
| 3D charts of any kind | Distorts proportions; never appropriate |

---

## Quick-Reference: Visual Checklist

Before finalizing any Mosaic marketing visual:

- [ ] Title states the conclusion, not the variable
- [ ] Signal Teal used for exactly one element (the point)
- [ ] Y-axis starts at zero (or clearly justified if not)
- [ ] Data source cited in small text
- [ ] Passes the Glance test — point is clear in 2 seconds
- [ ] No more than 3 colors used
- [ ] Whitespace > 40% of canvas
- [ ] Audience framing confirmed (buy-side / sell-side / press / regulator)
- [ ] McCandless four-element test: Information ✓ Story ✓ Goal ✓ Visual Form ✓
