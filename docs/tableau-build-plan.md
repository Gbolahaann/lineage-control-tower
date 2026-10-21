# Lineage Control Tower: Tableau build plan

Pre-build items 6 to 9, written before any dashboard goes into the workbook.

| Item | Section |
|---|---|
| 6. Prototype review against Tableau | 1 |
| 8. Shared shell (nav, header, filter band, info panel) | 2 |
| 7. Container trees for every dashboard | 3 |
| 9. Formatting spec | 4 |
| How I build it in the `.twb` | 5 |
| Decisions | 6 |

**Sources:** the prototype (`mockup/lineage-control-tower.html`), measured in headless Chromium at 1600 × 1000; `docs/tableau-calc-pack.md` for sheet names and calcs; the tableau-style skill (product mode) for padding, borders, tooltips and number formats.

**Screenshots** of every prototype tab are in `docs/img/proto-<tab>.png` (health, lineage, blast, runs, quality, fresh, perf, usage, gov, about). Every pixel value in this file was measured from those renders, not estimated.

**Units:** sizes are screen pixels on the 1600 × 1000 canvas. Font sizes are Tableau points (pt). The prototype is in CSS px, and 1pt = 1.333px, so 12px ≈ 9pt and 24px = 18pt.

---

## 1. Prototype review against Tableau (item 6)

The review follows the order of importance we agreed: information, chart choice, labels, gestalt, cohesion and white space, typography, flow, then feasibility and performance. Each finding says what to keep, change or drop.

### 1.1 Information

| # | Tab | Finding | Recommendation |
|---|---|---|---|
| I1 | Shell | "Data updated on 19 Oct 2026, 23:59" appears twice: in the header and in the nav foot. | Keep it in the header only, where the skill puts it. The nav foot keeps "Refreshes hourly from dbt_ops" and the synthetic data badge. |
| I2 | Lineage, Blast | The selection chip in the filter band ("Selected exposure: Executive Revenue Dashboard ×") repeats what the picker already shows in the card below it. | Drop the chip. The picker is the single place that shows and changes the selection. This also saves two sheets and a reset action. |
| I3 | Health | Nav count badges (12, 1, 2, 3) carry real signal. | Already dropped (decision 3 in the calc pack): Tableau navigation buttons can't show data. The Health KPI "Exposures at risk" and the tab content carry the same numbers. |
| I4 | Health | KPI hover definitions (the ⓘ next to each KPI title) explain each metric. | Keep: they become the tooltip on each BAN sheet. That's the one case where the skill keeps tooltips on a BAN sheet, because they extend the KPI. |
| I5 | Quality, Perf, Gov | The mini KPI cards are 84px tall inside a 96px row, so the gap to the cards below is 26px instead of 14px. | Make the cards fill the 96px row. The gap becomes 14px, the same as every other tab. |
| I6 | Quality | "Tests that keep failing" lists 8 tests but the card shows only 3 before it scrolls. | Show the top 5 and give the card 46px more height (taken from the two cards below it, which have spare space). |
| I7 | Gov | "Gaps to close" holds 33 rows (4 no owner, 14 no tests, 15 no description) in about 280px. | Show the top 5 of each list, followed by "and N more" in grey. The full lists already live on the Coverage by domain table and in Lineage. See decision D6. |
| I8 | Blast | The incident message can't go to the clipboard in Tableau. | A button sheet ("✉ Email incident message") opens a pre-filled email (URL action, on select), and its tooltip shows the full message. This changes calc pack 5.7 from Menu to Select. |
| I9 | About | The parameter table and actions list (developer documentation) have no home in the prototype. | Add an 11th dashboard, **Documentation**, left out of the nav and reached from a link at the foot of About. This follows the skill's documentation page template. See decision D5. |

### 1.2 Chart choice

| # | Tab | Chart | Verdict |
|---|---|---|---|
| C1 | Health | KPI bar trends (90 bars, the period in accent) | Keep. At 181px wide each bar is about 2px. That still reads as a texture, and the window colour change is the point. |
| C2 | Health | Exposure tiles (status grid) | Keep. This is the hero view. The open question is where the group labels go (decision D1). |
| C3 | Health | Health by layer (100% stacked bars) | Keep. |
| C4 | Lineage | Node-link graph | Keep. Edges are line marks on densified points, and nodes are Gantt bars on a dual axis (calc pack 4.2). |
| C5 | Runs | Failed and skipped bars, job Gantt, MTTR area line | Keep all three. |
| C6 | Quality | Heatmap of the worst test result per model per day | Keep. It's the best chart in the set for spotting the Monday pattern. |
| C7 | Quality | Weekday mini bars per failing test | Keep, as one sheet with Test Name on rows and Weekday on columns. |
| C8 | Freshness | Bullet bars (lag against warn and error zones) | Keep. Gantt bars for the three zones, plus a bar for lag on a dual axis. |
| C9 | Freshness | Compliance lines, axis 90% to 100% | Keep. The truncated axis is labelled ("The axis starts at 90%"), which is the honest way to show it. |
| C10 | Freshness | Late checks calendar | Keep. |
| C11 | Perf | Runtime of the six slowest models with end labels | Keep, but label only the highlighted line. The five grey lines sit on top of each other at the bottom, so their end labels collide (visible in the screenshot). The tooltip names them. |
| C12 | Usage | Log-log cost against usage scatter, with a retire zone | Keep. The diagonal edge of the zone is the known compromise (calc pack, compromise 4). |
| C13 | Usage | Inline "failures per day" bar sparkline inside the semantic refresh table | Tableau can't put a mini chart in a table cell without a second, row-aligned sheet, and that alignment breaks as soon as the row count changes. Recommend replacing it with two text columns: **Fail days** (count) and **Last failure** (date). See decision D3. |
| C14 | Gov | Maturity bar (High / Medium / Low split) | Keep. One stacked bar, labelled inside. |

### 1.3 Labels

| # | Finding | Recommendation |
|---|---|---|
| L1 | Tile and node names are cut with "…" by the browser. Tableau doesn't truncate a label to fit a mark; it either clips it or hides it. | New calc **Tile Name Short**: `LEFT([display_name], 22) + "…"` when the name is longer than 23 characters. The lineage graph has the same need (calc pack 4.2 already shortens names). |
| L2 | The MTTR chart's x labels overlap ("22 Jul Aug"). This is a prototype bug. | Tableau's date axis handles this. Use month starts, format `d mmm`. |
| L3 | The Usage scatter labels collide ("personal Claude hub" sits on "scheduled notebook"). | Label only the retire candidates and the unregistered products, with "Allow labels to overlap other marks" off. If two still collide, Tableau drops one and the tooltip still names it. |
| L4 | Card titles are short noun phrases and subtitles are one plain sentence. | Keep the pattern. It matches the skill's two-piece card title (title, then grey subtitle). |
| L5 | The interactive hints ("Click a tile to open its lineage") live inside the subtitles. | Keep them there. The skill's italic hint line is only used in the filter band (the period hint). |

### 1.4 Gestalt

| # | Finding | Recommendation |
|---|---|---|
| G1 | Purple `#5B5FC7` means Redshift on the platform legend, and "AI-built" on the Usage scatter. | It never appears on the same tab with both meanings, so I'd keep it. But the AI-built tag uses `#3D41A0` on `#EEF0FB`, so the scatter could use `#3D41A0` to tie the dot to the tag and free `#5B5FC7` for Redshift only. See decision D4. |
| G2 | Status colours are only used for status, and platform colours only for platforms. | Keep. This rule is written into section 4.6. |
| G3 | Each card is one enclosure, with a 1px border and a 10px radius. | Keep. Tableau 2025 and later support corner radius on zones (the workbook is on 2026.3). |

### 1.5 Cohesion and white space

| # | Finding | Recommendation |
|---|---|---|
| W1 | Gaps are 14px between cards and 12px between KPI cards. | Keep both. KPI cards use margin 6 on facing sides, other cards use margin 7. |
| W2 | Freshness bullets fill only about 60% of a full-height card. | Set the sheet to Fit: Entire view so the 27 rows spread to about 28px each. |
| W3 | Gov "AI-built dashboard sprawl": the callout is cut off at the bottom. | Fix the callout at 56px high and let the list above it take the rest. |
| W4 | Content padding is 20 top, 28 sides, 22 bottom on every tab. | Keep it identical on all 11 dashboards. It's set once in the shell (section 2). |

### 1.6 Typography

| # | Finding | Recommendation |
|---|---|---|
| T1 | The prototype uses Libre Franklin. | Already decided: Tableau Book, Medium and Semibold (set at workbook level in `c3a0fd4`). |
| T2 | Node names, schemas and Slack channels use JetBrains Mono, which Tableau Public can't render. | **Decided: Tableau family** for identifiers too (D2), in `#16212E`. |
| T3 | The prototype uses half-point steps (12.5px titles, 10.5px subtitles). | Tableau takes whole points. The scale in section 4.2 rounds each size to the nearest point, keeping the order of sizes. |
| T4 | Letter-spaced caps for section labels (`letter-spacing .1em`). | Tableau has no letter spacing. Caps in Tableau Semibold at 7pt still read as a label. |

### 1.7 Flow

| # | Finding | Recommendation |
|---|---|---|
| F1 | The journey runs Health → click a tile → Lineage → click a node → Trace downstream impact → Blast radius → Who to tell. | Keep. Every hop is a parameter action plus a go-to-sheet action. Parameters are global, so the selection carries over to the next dashboard. |
| F2 | The prototype's ⓘ button jumps to About. | Replace it with the floating "How to read this page" panel on every dashboard (section 2.5). About stays in the nav. |
| F3 | The Runs Gantt day can be changed with ‹ › or by clicking a bar. | Keep both (calc pack 6.6). |
| F4 | Clicking a Usage row opens Lineage; clicking a semantic row opens Blast radius. | Keep, as the calc pack lists. |

### 1.8 Feasibility and performance

**What Tableau can't do, and the stand-in:**

| Prototype behaviour | Tableau stand-in | Cost |
|---|---|---|
| Hover a lineage node to light up its path | Click a node to light up its path (calc pack compromise 1) | Low |
| Rounded tiles and pills inside a sheet | Square marks are square. The card around them is rounded, which is where the eye goes | Low |
| Hover states on tiles, rows and buttons | None. Tooltips carry the "Click to…" hints | Low |
| Copy incident message | Email button plus a tooltip (I8) | Low |
| Nav count badges | Dropped (I3) | Low |
| Inline sparkline in a table row | Replaced by text columns (C13) | Low |
| Group labels above tile groups | Decision D1 | Medium |
| Card shadows on hover | None needed. The prototype cards have no shadow at rest | None |

**Data volume:** the 14 marts hold about 36,000 rows (5.4 MB of CSV). The two largest are Lineage Layout (10,594 rows) and Node Daily (10,620). That's small for Tableau: no sheet will need more than a second, even live on the CSVs.

**Sheet count:** about 105 sheets across 11 dashboards. The 5 shared sheets (period, platform, hint, data updated, info) are reused on every dashboard rather than copied. Health has the most at 21 (16 of its own plus the 5 shared).

**Things that keep it fast:**

1. **Extract before publishing.** Tableau Public turns the source into an extract anyway. Make it yourself first (Data › Extract, "logical tables" kept), so what you test is what gets published.
2. **No filter actions.** Every interaction is a parameter action, so a click recomputes only the sheets that read that parameter.
3. **Dynamic zone visibility instead of hidden sheets.** Tableau skips sheets in hidden zones, so the Lineage panel only computes the section for the node type on show.
4. **FIXED calcs with no dimension** are evaluated once per data source, not per mark. The DZV calcs in the pack all use this pattern.
5. **Table calcs only where needed:** the tile grid (INDEX) and the layer share. Both run over fewer than 150 rows.
6. **Images travel inside the .twbx** (`Image/`), so nothing points at a folder on one machine (decision D7).

---

## 2. Shared shell (item 8)

The shell is everything outside the content area. It's identical on all 11 dashboards except for three things: the active nav button, the title block, and the info panel text. I build it once in code and stamp it into each dashboard (section 5).

### 2.1 Root and bands

```
<P> Root                     horizontal, tiled, 1600 × 1000, dashboard background #F5F5F3
├── <P> Nav                  vertical, fixed w 231, bg #FFFFFF            (2.2)
├── <P> Nav Edge             blank, fixed w 1, bg #E6E7E2, margin 0
└── <P> Main                 vertical, flex (1368), margin 0
    ├── <P> Header           horizontal, fixed h 69, bg #FFFFFF          (2.3)
    ├── <P> Header Rule      blank, fixed h 1, bg #E6E7E2
    ├── <P> Filter Band      horizontal, fixed h 51, bg #FFFFFF          (2.4)
    ├── <P> Filter Rule      blank, fixed h 1, bg #E6E7E2
    └── <P> Content          vertical or horizontal (per tab), flex 1368 × 878,
                             padding top 20, right 28, bottom 22, left 28, margin 0  (section 3)
GL Info Panel                floating, DZV on p_show_info                (2.5)
```

`<P>` is the tab prefix (HO, LIN, BR, RUN, QA, FR, PF, US, GOV, AB for About, DOC for Documentation). Every container gets its name as `friendly-name`, so the Item Hierarchy reads like this tree.

The content area always comes out at **1312 × 836**, with its top-left corner at (260, 142). That matches the prototype exactly.

### 2.2 Left nav (231 wide)

Padding: top 22, right 14, bottom 18, left 14. Inner width 203. All children have margin 0 unless noted.

```
<P> Nav  (vertical)
├── <P> Nav Brand            horizontal, fixed h 79
│   ├── <P> Nav Brand Mark   vertical, fixed w 44: Navy #002C55 square 34 × 34, radius 8, margin-right 10
│   │                        (text glyph for now, PNG logo later: decision D7)
│   └── <P> Nav Brand Text   text: "Lineage Control Tower" 11pt Tableau Bold #002C55
│                            ↵ "Acme Retail Co. · Data Platform" 8pt Tableau Book #7A838E
├── <P> Nav Brand Rule       blank, fixed h 1, bg #EFEFEB, margin-bottom 10
├── text "MONITOR"           fixed h 29, 7pt Tableau Semibold #A5ACB4, padding top 12, left 10
├── nav button "Health overview"     fixed h 38 (34 + margin-bottom 4)
├── nav button "Run & failures"      fixed h 38
├── nav button "Freshness & SLAs"    fixed h 38
├── text "INVESTIGATE"               fixed h 29
├── nav button "Lineage explorer"    fixed h 38
├── nav button "Blast radius"        fixed h 38
├── nav button "Data quality"        fixed h 38
├── text "OPTIMISE"                  fixed h 29
├── nav button "Performance & cost"  fixed h 38
├── nav button "Usage & adoption"    fixed h 38
├── text "GOVERN"                    fixed h 29
├── nav button "Governance"          fixed h 38
├── nav button "About & how to use"  fixed h 38
├── blank                            flex
├── <P> Nav Foot Rule                blank, fixed h 1, bg #EFEFEB
└── <P> Nav Foot                     text, fixed h 64, padding top 14, left 8
                                     "Refreshes hourly from dbt_ops" 8pt #7A838E
                                     ↵ "● Synthetic data, fictional company" 7.5 → 8pt #4A5563
```

The group and button positions match the prototype: Monitor at y 115, Health button at y 148, and each button is 34 tall with a 4px gap.

**Nav buttons** are Tableau navigation objects (text style, go to sheet):

| State | Fill | Text | Radius |
|---|---|---|---|
| Inactive | none | 9pt Tableau Medium `#4A5563`, left-aligned, padding-left 10 | 8 |
| Active (this dashboard) | `#C7FFA4` (Lime) | 9pt Tableau Semibold `#002C55` | 8 |

The active button points to its own dashboard, so clicking it does nothing, which is what you'd expect. Icons are left out of the first build (decision D7).

### 2.3 Header (69 high + 1px rule)

Padding: left 28, right 28.

```
<P> Header  (horizontal)
├── <P> Title Block          text, flex, padding-top 15
│     run 1: "Monitor / " 8pt Tableau Book #7A838E + "Health overview" 8pt Tableau Medium #4A5563
│     ↵
│     run 2: "Health overview" 15pt Tableau Semibold #002C55
│            + "   Is anything on fire right now?" 11pt Tableau Book #7A838E
├── GL Data Updated          sheet, fixed w 200, right-aligned, padding-top 19
│     "Data updated on " 8pt #7A838E + "19 Oct 2026, 23:59" 8pt Tableau Semibold #16212E
│     ↵ "90 days of history from 22 Jul 2026" 8pt #7A838E
├── blank                    fixed w 16
└── <P> Info Button Holder   vertical, fixed w 32, padding top 19, bottom 18
    └── GL Info Button       sheet, 32 × 32
```

The title and question for each tab:

| Prefix | Group | Title | Question |
|---|---|---|---|
| HO | Monitor | Health overview | Is anything on fire right now? |
| RUN | Monitor | Run & failures | What failed, when, why, and how fast did we recover? |
| FR | Monitor | Freshness & SLAs | Is the data arriving on time? |
| LIN | Investigate | Lineage explorer | What feeds this exposure, and is every step healthy? |
| BR | Investigate | Blast radius | If this breaks, who do I need to tell? |
| QA | Investigate | Data quality | Which tests keep failing, and where are we untested? |
| PF | Optimise | Performance & cost | What is getting slower and more expensive? |
| US | Optimise | Usage & adoption | Which data products earn their keep? |
| GOV | Govern | Governance | Is everything owned, documented, tested and declared? |
| AB | About | About & how to use | What this is, where the numbers come from |
| DOC | About | Documentation | Parameters, actions and build notes |

### 2.4 Filter band (51 high + 1px rule)

Padding: left 28, right 28. Everything is vertically centred with top and bottom padding inside each holder.

```
<P> Filter Band  (horizontal)
├── text "PERIOD"            fixed w 51, 7pt Tableau Semibold #7A838E, padding-top 20
├── <P> Period Track         horizontal, fixed w 265, margin top 11, bottom 12 (so 28 high)
│   │                        bg #F5F5F3, border 1px #E6E7E2, radius 8, padding 2
│   └── GL Period Buttons    sheet, flex
├── blank                    fixed w 18
├── text "PLATFORM"          fixed w 69
├── <P> Platform Track       horizontal, fixed w 302, same style as the period track
│   └── GL Platform Buttons  sheet, flex
├── blank                    fixed w 18
└── GL Period Hint           sheet, flex, padding-top 18
                             "Changes compare with the 30 days before" 8pt italic #7A838E
```

**Segmented button look** (this follows the prototype and replaces the colour note in calc pack 2.7):

| State | Square mark colour | Label |
|---|---|---|
| Active | `#FFFFFF` | 9pt Tableau Semibold `#002C55` |
| Inactive | `#F5F5F3` (same as the track, so it disappears into it) | 9pt Tableau Book `#4A5563` |

A label can't change colour per mark, so each button sheet carries two label fields: one filled only when active, and one filled only when inactive, each in its own colour. They're new calcs (section 5.3). The platform buttons add a small coloured square before the name (a second Square mark, size 8px, coloured by platform). "All" has no square.

### 2.5 Info panel

Floating at x 1172, y 130, size 400 × 420. It's hidden until `p_show_info` is True.

```
GL Info Panel  (vertical, floating, bg #FFFFFF, border 1px #E6E7E2, radius 10, padding 16)
├── text "How to read this page"     fixed h 30, 10pt Tableau Semibold #16212E
├── <P> Info Row 1                   horizontal, fixed h ~76
│   ├── text glyph                   fixed w 28, 12pt #005FAE  (1, 2, 3, 4)
│   └── text                         9pt Tableau Book #4A5563, the first words in Semibold #16212E
├── blank rule                       fixed h 1, bg #EFEFEB, margin 6 top and bottom
├── <P> Info Row 2 … Row 4           same pattern
└── text                             8pt italic #7A838E: "Click ⓘ again to close."
```

The header icon is the open and close control. A new calc **Info Button Glyph** shows "ⓘ" when the panel is closed and "✕" when it's open. The existing **GL Toggle Info** action flips the parameter, so the panel needs no close button of its own.

The panel text for each tab:

| Tab | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| Health | **Read the cards left to right.** Run, test and freshness rates, data products at risk now, recovery time and cost. Bars show 90 days, with your period in blue. | **Each tile is a data product**, traced through every upstream step. Red means do not use, amber means use with caution. | **Click a tile** to open its lineage. **Click an item under Needs attention** to see who it affects. | **Period and Platform** at the top apply to every page. |
| Runs | **The top chart** shows failed runs, and the runs skipped because something upstream failed. Dashed lines mark incidents. | **Click a day** to load its job timeline. Use ‹ › to step through days. | **Why runs failed** groups failures by error type, and lists the models that fail most. | **Click an error** to see what it affects downstream. |
| Freshness | **Each bar** is a source's lag since its last load. Green is on time, amber is past the warn threshold, red is past the error threshold. | **The line chart** shows the share of hourly checks that passed each day, per platform. | **The calendar** counts late checks per day. Look for repeating weekdays. | **Late right now** lists the data products waiting on each late source. |
| Lineage | **Pick a data product** in the dropdown. The graph shows every upstream step, from raw sources on the left to the product on the right. | **Click a box** to see its owner, history and tests in the panel, and to highlight its path. | **Switch to Table** for a sortable list of every upstream node. | **Trace downstream impact** opens Blast radius for the selected node. |
| Blast | **Pick a node**, or click a row in Riskiest nodes. | **Who to tell** lists the data products it feeds, with owners and Slack channels. | **Riskiest nodes** ranks nodes by daily consumers downstream × failure rate. | **Email incident message** opens a ready-to-send message. |
| Quality | **The heatmap** shows the worst test result per model per day. Repeating columns point to a scheduled cause. | **Tests that keep failing** shows which weekdays failures land on. | **Coverage** shows the share of models with at least one test, by domain. | **Warnings** count as not passing in the pass rate. |
| Perf | **Cost** is estimated compute for dbt builds plus product queries, in USD. | **The runtime chart** highlights the model whose runtime changed most. | **"Make incremental"** flags full-refresh tables over 10M rows whose runtime grew more than 25%. | **Product cost** splits each model's build cost evenly across the products it feeds. |
| Usage | **Each dot** is a data product. Bottom right is expensive and little used: the candidates to retire. | **Each consumer type** gets its own scale, because views, queries, sessions and agent calls aren't comparable. | **The ranked table** compares use with the period before. | **Semantic layer refreshes** catch extracts that fail while dbt stays green. |
| Gov | **Unregistered consumers** read warehouse data but aren't declared as exposures, so nobody is told when it breaks. | **AI-built sprawl** shows dashboards built with AI that overlap governed ones. | **Coverage cells** are green from 90% and amber from 70%. | **Gaps to close** are the quickest fixes for the next sprint. |
| About | **Start on Health overview.** | **Click any tile** to see its lineage, then any node to see its history. | **Use Trace downstream impact** to see who to tell. | **The data is synthetic.** Acme Retail Co. is fictional. |

### 2.6 How the shell becomes 11 dashboards

1. The builder script (section 5) writes the shell from one Python function, which takes the tab prefix, the active nav button and the title row from 2.3.
2. Zone ids are unique within each dashboard. The shared sheets keep their names, because one sheet can sit on many dashboards.
3. The navigation buttons need each dashboard's `window-id`, so all 11 dashboards are created empty first (shell only) and filled tab by tab. That way every nav button works from the first build, even before the other tabs have content.

---

## 3. Container trees (item 7)

**Notation:** `fixed h 220` is a fixed height in a vertical parent, and `fixed w 410` is a fixed width in a horizontal parent. Sizes include the outer margin, so `fixed w 417 (410 + 7)` means a 410 card with a 7px margin on its inner side.

**Card style** (every card unless noted): vertical container, bg `#FFFFFF`, border 1px solid `#E6E7E2`, radius 10. Padding is top 14, right 16, bottom 14, left 16. Gaps come from margins on facing sides: 7 for cards, 6 for KPI cards. Sheets inside cards have margin 0 and padding 0.

**Card header** (text object): title 10pt Tableau Semibold `#16212E`, then a line break, then the subtitle in 8pt Tableau Book `#7A838E`. It's fixed at **h 44** when the subtitle fits on one line, or **h 58** when it needs two. Both include a 10px bottom padding. Where the subtitle is dynamic, the header is the sheet title of the first sheet in the card instead of a text object.

**Legend text** (text object, h 22): "■ Healthy  ■ Warning  ■ Critical" in 8pt `#4A5563`, each ■ in its colour, with padding-top 8.

The prototype measurements are in brackets after each card: [x, y, w, h].

### 3.1 Health overview (HO), content vertical

```
HO Content                                  vertical, 1312 × 836
├── HO KPI Row                              horizontal, fixed h 128
│   ├── HO KPI Run Success Card             card, fixed w 215 (209 + 6), padding 12 / 14 / 10 / 14   [260,142,209,128]
│   │   ├── HO Run Success KPI              sheet, fixed h 66: CAPS title, BAN, change line
│   │   └── HO Run Success KPI Trend        sheet, flex (about 40), padding-top 8
│   ├── HO KPI Test Pass Card               same, fixed w 221 (6 + 209 + 6)                          [481,142,209,128]
│   ├── HO KPI Freshness SLA Card           same                                                       [701,142,209,128]
│   ├── HO KPI Exposures At Risk Card       same                                                       [922,142,209,128]
│   ├── HO KPI MTTR Card                    same                                                       [1143,142,209,128]
│   └── HO KPI Warehouse Cost Card          flex (6 + 209)                                             [1363,142,209,128]
└── HO Body                                 horizontal, flex (708 = 14 + 694), margin-top 14
    ├── HO Exposure Card                    card, flex (888 + 7)                                       [260,284,888,694]
    │   ├── HO Exposure Card Header         horizontal, fixed h 44
    │   │   ├── text "Exposure status" / "Every data product, traced through its full upstream
    │   │   │     chain. Score is the 7-day health score (0 to 100). Click a tile to open its lineage."
    │   │   └── HO Tile View Track          fixed w 150, same style as the period track
    │   │       └── HO Tile View Buttons    sheet
    │   ├── HO Exposure Status Tiles        sheet, flex (decision D1)
    │   └── HO Exposure Legend              legend text: Trusted / Use with caution / Do not use,
    │                                       right part "Trust badges can be surfaced inside each dashboard…" 8pt #7A838E
    └── HO Right Column                     vertical, fixed w 417 (7 + 410)
        ├── HO Attention Card               card, flex (489 + 7)                                      [1162,284,410,489]
        │   ├── text "Needs attention now" / 2-line subtitle      fixed h 58
        │   └── HO Needs Attention List     sheet, flex
        └── HO Layer Card                   card, fixed h 198 (7 + 191)                               [1162,787,410,191]
            ├── text "Health by layer" / "Where in the chain the trouble sits, right now"   fixed h 44
            └── HO Layer Health Bar         sheet, flex
```

Tile geometry: the grid is 856px wide (888 − 32 padding). Five tiles per row gives about 163px per tile with an 8px gutter, and 63px per tile row.

### 3.2 Lineage explorer (LIN), content horizontal

```
LIN Content                                 horizontal, 1312 × 836
├── LIN Graph Card                          card, flex (958 + 7), padding-bottom 10                    [260,142,958,836]
│   ├── LIN Graph Header                    horizontal, fixed h 36
│   │   ├── p_selected_exposure control     compact list, fixed w 260, title hidden
│   │   ├── LIN Exposure Header             sheet, flex: trust pill + access line
│   │   └── LIN View Track                  fixed w 110, track style
│   │       └── LIN View Buttons            sheet: Graph / Table
│   ├── LIN Layer Labels                    horizontal, fixed h 26, distribute evenly
│   │   └── 6 × text: SOURCES, STAGING, INTERMEDIATE, MARTS, BI SEMANTIC LAYER, EXPOSURE (7pt Semibold #7A838E)
│   ├── LIN Graph Holder                    vertical, flex, DZV Show Lineage Graph
│   │   └── LIN Lineage Graph               sheet
│   ├── LIN Table Holder                    vertical, flex, DZV Show Lineage Table
│   │   └── LIN Lineage Table               sheet
│   └── LIN Legend                          legend text: Healthy / Warning / Critical, then the three platforms,
│                                           right part "Click a node to trace its path and see its details" (italic)
└── LIN Panel Card                          card, fixed w 347 (7 + 340), padding 16                    [1232,142,340,836]
    ├── LIN Panel Header                    sheet, fixed h 130: kind line, name, pills, issue callout
    ├── LIN Panel Details                   sheet, fixed h 140: owner, team, Slack, project, schema, documented, tests
    ├── LIN Panel Model Section             vertical, fixed h 212, DZV Show Panel Model
    │   ├── text "RUNTIME, 90 DAYS"         fixed h 26 (section label style, 4.2)
    │   ├── LIN Panel Runtime Trend         sheet, fixed h 72
    │   ├── text "RUNS IN PERIOD"           fixed h 26
    │   ├── LIN Panel Runs Summary          sheet, fixed h 22
    │   ├── text "TESTS, LAST 30 DAYS"      fixed h 26
    │   └── LIN Panel Test Strip            sheet, flex (about 40)
    ├── LIN Panel Source Section            vertical, fixed h 176, DZV Show Panel Source
    │   ├── text "FRESHNESS NOW"            fixed h 26
    │   ├── LIN Panel Freshness Bullet      sheet, fixed h 50
    │   ├── text "DAILY WORST LAG, 90 DAYS" fixed h 26
    │   └── LIN Panel Lag Trend             sheet, flex
    ├── LIN Panel Semantic Section          vertical, fixed h 130, DZV Show Panel Semantic
    │   ├── text "REFRESHES IN PERIOD"      fixed h 26
    │   └── LIN Panel Refresh Summary       sheet, flex: counts line + failed refreshes per day
    ├── LIN Panel Exposure Section          vertical, fixed h 212, DZV Show Panel Exposure
    │   ├── text "HEALTH SCORE, 90 DAYS"    fixed h 26
    │   ├── LIN Panel Health Score Trend    sheet, fixed h 80
    │   ├── text "IN THIS PERIOD"           fixed h 26
    │   └── LIN Panel Usage Summary         sheet, flex
    ├── blank                               flex
    ├── LIN Trace Holder                    fixed h 36, DZV Show Trace Impact Button (new calc)
    │   └── LIN Trace Impact Button         sheet, fixed w 190
    └── LIN Usage Holder                    fixed h 36, DZV Show Panel Exposure
        └── LIN See Usage Button            sheet, fixed w 190
```

Only one of the four sections shows at a time. The tallest is 212, so the 804px inner panel always fits.

### 3.3 Blast radius (BR), content vertical

```
BR Content                                  vertical, 1312 × 836
├── BR Header Card                          card, horizontal, fixed h 150, padding 14 / 18            [260,142,1312,150]
│   ├── BR Picker Column                    vertical, fixed w 300
│   │   ├── text "NODE TO TRACE"            fixed h 20, section label style
│   │   ├── p_selected_node control         compact list, fixed h 32, title hidden
│   │   └── BR Node Header                  sheet, fixed h 28: status, platform and layer pills
│   ├── blank                               fixed w 24
│   ├── BR Summary Column                   vertical, flex
│   │   ├── BR Impact Summary               sheet, fixed h 66: sentence (12pt) + issue line (8pt)
│   │   └── BR Chips Row                    horizontal, fixed h 50
│   │       ├── BR Reach Counts             sheet, fixed w 232: 2 chips (models, BI semantic objects)
│   │       ├── BR Exposure Counts          sheet, fixed w 200: 2 chips (exposures, owners to notify)
│   │       └── BR Unregistered Count       sheet, fixed w 120: 1 chip, red when above 0
│   └── BR Message Holder                   vertical, fixed w 190
│       └── BR Incident Message             sheet, fixed h 32: "✉ Email incident message" button (I8)
├── BR Middle Row                           horizontal, fixed h 372 (14 + 358), margin-top 14
│   ├── BR Who Card                         card, flex (649 + 7)                                      [260,306,649,358]
│   │   ├── text "Who to tell" / subtitle   fixed h 44
│   │   ├── BR Who To Tell Table            sheet, flex
│   │   ├── BR Unregistered Holder          fixed h 58, DZV Show Unregistered Callout
│   │   │   └── BR Unregistered Callout     sheet, callout style warn (4.4)
│   │   └── BR No Owner Holder              fixed h 42, DZV Show No Owner Callout
│   │       └── BR No Owner Callout         sheet, callout style crit
│   └── BR Downstream Card                  card, flex (7 + 649)                                      [923,306,649,358]
│       ├── text "Downstream path" / "Everything built on this node, by layer"   fixed h 44
│       └── BR Downstream Path              sheet, flex
└── BR Risk Card                            card, fixed h 314 (14 + 300), margin-top 14               [260,678,1312,300]
    ├── text "Riskiest nodes in this period" / subtitle   fixed h 44
    └── BR Riskiest Nodes Table             sheet, flex
```

### 3.4 Run & failures (RUN), content vertical

```
RUN Content                                 vertical, 1312 × 836
├── RUN Daily Card                          card, fixed h 220                                          [260,142,1312,220]
│   ├── RUN Daily Header                    horizontal, fixed h 44
│   │   ├── text "Failed and skipped model runs per day" / subtitle
│   │   └── legend text, fixed w 260: ■ Failed  ■ Skipped because upstream failed
│   ├── RUN Incident Markers                sheet, fixed h 22: INC labels and dashed ticks, same date axis
│   └── RUN Daily Failures Bar              sheet, flex
├── RUN Middle Row                          horizontal, fixed h 366 (14 + 352), margin-top 14
│   ├── RUN Gantt Card                      card, flex (918 + 7)                                       [260,376,918,352]
│   │   ├── RUN Gantt Header                horizontal, fixed h 44
│   │   │   ├── text "Job run timeline" / "Every dbt job run on the selected day, coloured by outcome"
│   │   │   ├── RUN Gantt Prev Button       sheet, fixed w 32
│   │   │   ├── RUN Gantt Day Label         sheet, fixed w 130: "Mon 19 Oct 2026" 10pt Semibold
│   │   │   └── RUN Gantt Next Button       sheet, fixed w 32
│   │   ├── RUN Job Gantt                   sheet, flex
│   │   └── legend text                     Succeeded / Failed / Cancelled / ● Tests failed in run
│   └── RUN Why Card                        card, fixed w 387 (7 + 380)                                [1192,376,380,352]
│       ├── RUN Failed Count Label          sheet, fixed h 44: title "Why runs failed" + dynamic subtitle
│       ├── RUN Why Failed Bar              sheet, fixed h 130
│       ├── text "MODELS THAT FAILED MOST"  fixed h 26
│       └── RUN Top Failing Models Bar      sheet, flex
└── RUN Bottom Row                          horizontal, fixed h 250 (14 + 236), margin-top 14
    ├── RUN Errors Card                     card, flex (918 + 7)                                       [260,742,918,236]
    │   ├── text "Recent errors" / "Newest first. Hover a message to read it in full."   fixed h 44
    │   └── RUN Recent Errors Table         sheet, flex
    └── RUN MTTR Card                       card, fixed w 387 (7 + 380)                                [1192,742,380,236]
        ├── text "Mean time to recover" / 2-line subtitle   fixed h 58
        └── RUN MTTR Rolling Line           sheet, flex
```

RUN Incident Markers sits right above the bars with the same date range and no visible axis, so its ticks line up with the bar columns. Both sheets fix the x axis to 22 Jul to 19 Oct.

### 3.5 Data quality (QA), content vertical

```
QA Content                                  vertical, 1312 × 836
├── QA KPI Row                              horizontal, fixed h 96 (I5)
│   ├── QA KPI Test Pass Card               card, fixed w 325 (319 + 6), padding 12 / 16
│   │   └── QA Test Pass KPI                sheet
│   ├── QA KPI Failing Now Card             fixed w 331 (6 + 319 + 6)
│   │   └── QA Failing Now KPI              sheet
│   ├── QA KPI Tests Run Card               fixed w 331
│   │   ├── QA Tests Run KPI                sheet, fixed h 50
│   │   └── QA Tests Defined Label          sheet, flex: "166 distinct tests"
│   └── QA KPI Coverage Card                flex (6 + 319)
│       └── QA Test Coverage KPI            sheet
└── QA Body                                 horizontal, flex (740 = 14 + 726), margin-top 14
    ├── QA Heatmap Card                     card, flex (878 + 7)                                       [260,252,878,726]
    │   ├── QA Heatmap Header               horizontal, fixed h 58
    │   │   ├── text "Test outcomes by model and day" / 2-line subtitle
    │   │   └── legend text, fixed w 230: Passed / Warning / Failed / No run
    │   └── QA Test Heatmap                 sheet, flex
    └── QA Right Column                     vertical, fixed w 427 (7 + 420)
        ├── QA Keeps Failing Card           card, flex (about 274 + 7)        (prototype 228, I6)
        │   ├── text "Tests that keep failing" / subtitle   fixed h 44
        │   └── QA Keeps Failing Tests      sheet, flex: top 5
        ├── QA Issues Type Card             card, fixed h 204 (7 + 190 + 7)  (prototype 220)
        │   ├── text "Issues by test type" / "Failures and warnings in this period"   fixed h 44
        │   └── QA Issues by Type Bar       sheet, flex
        └── QA Coverage Card                card, fixed h 237 (7 + 230)      (prototype 251)
            ├── text "Test coverage by domain" / "Share of models with at least one test"   fixed h 44
            └── QA Coverage by Domain Bar   sheet, flex
```

### 3.6 Freshness & SLAs (FR), content horizontal

```
FR Content                                  horizontal, 1312 × 836
├── FR Bullets Card                         card, flex (649 + 7)                                       [260,142,649,836]
│   ├── text "How late is each source right now?" / 2-line subtitle   fixed h 50, padding-bottom 2
│   ├── FR Latest Check Label               sheet, fixed h 22: "Latest check 19 Oct, 23:00" 8pt #7A838E
│   └── FR Source Lag Bullets               sheet, flex, Fit: Entire view (W2)
└── FR Right Column                         vertical, fixed w 656 (7 + 649)
    ├── FR Compliance Card                  card, flex (411 + 7)                                       [923,142,649,411]
    │   ├── text "Freshness SLA compliance by platform" / subtitle   fixed h 44
    │   └── FR Compliance by Platform Line  sheet, flex
    └── FR Bottom Row                       horizontal, fixed h 418 (7 + 411)
        ├── FR Calendar Card                card, fixed w 325 (318 + 7)                                [923,567,318,411]
        │   ├── text "Late checks by day" / "Number shows late checks. Today's label is bold."   fixed h 44
        │   ├── FR Late Checks Calendar     sheet, flex
        │   └── legend text                 Warn / Error / On time
        └── FR Late Now Card                card, flex (7 + 318)                                       [1255,567,318,411]
            ├── text "Late right now" / "And the data products waiting on them"   fixed h 44
            └── FR Late Right Now           sheet, flex
```

### 3.7 Performance & cost (PF), content vertical

```
PF Content                                  vertical, 1312 × 836
├── PF KPI Row                              horizontal, fixed h 96: 4 KPI cards, widths as QA
│   ├── PF KPI Warehouse Cost Card    └── PF Warehouse Cost KPI
│   ├── PF KPI Average Per Day Card   └── PF Average Per Day KPI
│   ├── PF KPI Slowest Model Card     └── PF Slowest Model KPI
│   └── PF KPI Incremental Card       └── PF Incremental Candidates KPI
├── PF Middle Row                           horizontal, fixed h 304 (14 + 290), margin-top 14
│   ├── PF Cost Card                        card, flex (768 + 7)                                       [260,252,768,290]
│   │   ├── PF Cost Header                  horizontal, fixed h 44
│   │   │   ├── text "Cost by platform, per day" / subtitle
│   │   │   └── legend text, fixed w 230: Snowflake / Databricks / Redshift
│   │   └── PF Cost by Platform Bar         sheet, flex
│   └── PF Runtime Card                     card, fixed w 537 (7 + 530)                                [1042,252,530,290]
│       ├── text "Runtime of the six slowest models" / subtitle   fixed h 44
│       └── PF Slowest Models Runtime Line  sheet, flex
└── PF Bottom Row                           horizontal, flex (436 = 14 + 422), margin-top 14
    ├── PF Expensive Card                   card, flex (768 + 7)                                       [260,556,768,422]
    │   ├── text "Most expensive models in this period" / subtitle   fixed h 44
    │   └── PF Most Expensive Models Table  sheet, flex
    └── PF Product Cost Card                card, fixed w 537 (7 + 530)                                [1042,556,530,422]
        ├── text "What each data product costs to keep running" / 2-line subtitle   fixed h 58
        └── PF Cost per Data Product Bar    sheet, flex
```

### 3.8 Usage & adoption (US), content vertical

```
US Content                                  vertical, 1312 × 836
├── US Top Row                              horizontal, fixed h 330
│   ├── US Scatter Card                     card, flex (649 + 7)                                       [260,142,649,330]
│   │   ├── text "Cost against usage" / 2-line subtitle   fixed h 58
│   │   ├── US Cost vs Usage Scatter        sheet, flex
│   │   └── legend text                     Built by hand / AI-built / Unregistered / Retire candidate
│   └── US Consumption Card                 card, flex (7 + 649)                                       [923,142,649,330]
│       ├── text "Consumption by consumer type, per day" / subtitle   fixed h 44
│       └── US Multiples                    vertical, flex
│           ├── US Multiples Row 1          horizontal, distribute evenly
│           │   ├── US Views Small Multiple           sheet, margin-right 8, sheet title "Dashboard and hub views   12.3K"
│           │   └── US Queries Small Multiple         sheet, margin-left 8
│           └── US Multiples Row 2          horizontal, distribute evenly, margin-top 10
│               ├── US App Sessions Small Multiple    sheet
│               └── US Agent Calls Small Multiple     sheet
└── US Bottom Row                           horizontal, flex (506 = 14 + 492), margin-top 14
    ├── US Ranked Card                      card, flex (649 + 7)                                       [260,486,649,492]
    │   ├── text "Data products ranked by use" / subtitle   fixed h 44
    │   └── US Ranked Products Table        sheet, flex
    └── US Semantic Card                    card, flex (7 + 649)                                       [923,486,649,492]
        ├── text "BI semantic layer refreshes" / "dbt can be green while an extract fails. This is where that shows."   fixed h 44
        └── US Semantic Refresh Table       sheet, flex (C13)
```

The small multiples carry their total in the sheet title, so the title is dynamic. That's the one place where a sheet title is on in a card.

### 3.9 Governance (GOV), content vertical

```
GOV Content                                 vertical, 1312 × 836
├── GOV KPI Row                             horizontal, fixed h 96: 4 KPI cards, widths as QA
│   ├── GOV KPI Ownership Card        └── GOV Ownership KPI
│   ├── GOV KPI Documentation Card    └── GOV Documentation KPI
│   ├── GOV KPI Test Coverage Card    └── GOV Test Coverage KPI
│   └── GOV KPI Declared Card         └── GOV Declared Consumers KPI
├── GOV Middle Row                          horizontal, fixed h 370 (14 + 356), margin-top 14
│   ├── GOV Unregistered Card               card, flex (870 + 7)                                       [260,252,870,356]
│   │   ├── GOV Unregistered Header         horizontal, fixed h 58
│   │   │   ├── text "Unregistered consumers found in query history" / 2-line subtitle
│   │   │   └── text tag, fixed w 170: "From warehouse query history" 7pt, bg #F5F5F3, border #E6E7E2, radius 4
│   │   ├── GOV Unregistered Consumers Table   sheet, flex
│   │   └── text callout (info style)       fixed h 48: "Register each one as a dbt exposure with an owner…"
│   └── GOV Sprawl Card                     card, fixed w 435 (7 + 428)                                [1144,252,428,356]
│       ├── GOV AI Sprawl List              sheet, flex, sheet title: "AI-built dashboard sprawl" + dynamic subtitle
│       └── text callout (warn style)       fixed h 56 (W3, static text: calc pack compromise 5)
└── GOV Bottom Row                          horizontal, flex (370 = 14 + 356), margin-top 14
    ├── GOV Domain Card                     card, fixed w 435 (428 + 7)                                [260,622,428,356]
    │   ├── text "Coverage by domain" / "Green from 90%, amber from 70%"   fixed h 44
    │   └── GOV Coverage by Domain Table    sheet, flex
    ├── GOV Hygiene Card                    card, fixed w 442 (7 + 428 + 7)                            [702,622,428,356]
    │   ├── text "Hygiene score by team" / 2-line subtitle   fixed h 58
    │   ├── GOV Hygiene by Team Bar         sheet, flex
    │   ├── text "EXPOSURE MATURITY"        fixed h 26
    │   └── GOV Maturity Bar                sheet, fixed h 28
    └── GOV Gaps Card                       card, flex (7 + 428)                                       [1144,622,428,356]
        ├── text "Gaps to close" / "The quickest wins for the next sprint"   fixed h 44
        ├── text "NO OWNER"                 fixed h 24
        ├── GOV Gaps No Owner               sheet, fixed h 76 (top 4)
        ├── text "NO TESTS"                 fixed h 24
        ├── GOV Gaps No Tests               sheet, flex (top 5 + "and N more", D6)
        ├── text "NO DESCRIPTION"           fixed h 24
        └── GOV Gaps No Description         sheet, flex (top 5 + "and N more")
```

### 3.10 About (AB), content horizontal

```
AB Content                                  horizontal, 1312 × 836
├── AB What Card                            card, flex (456 + 7)                                       [260,142,456,836]
│   ├── text "What this is"                 fixed h 30
│   ├── text paragraphs 1 and 2             fixed h 210, 9pt #4A5563, line spacing about 1.5
│   ├── AB Layer Chain                      sheet, fixed h 60: Raw sources 27 → Staging 30 → … → Exposures 27
│   ├── text paragraph "How to use it"      fixed h 110
│   ├── text callout (info style)           fixed h 110: "The data is synthetic…"
│   ├── blank                               flex
│   └── DOC link                            navigation button (text style), fixed h 30:
│                                           "Documentation for developers ›" 8pt #005FAE (D5)
├── AB Sources Card                         card, fixed w 428 (7 + 414 + 7)                            [730,142,414,836]
│   ├── text "Where the numbers come from" / "In production, every table maps to something you already have"   fixed h 44
│   ├── text table                          fixed h 420: 8 rows, term in 8pt Semibold #16212E, source in 8pt #4A5563
│   ├── text "BUILT FOR ANY TOOL"           fixed h 26
│   └── text                                flex: "The data model is the product…"
└── AB Definitions Card                     card, flex (7 + 414)                                       [1158,142,414,836]
    ├── text "Metric definitions"           fixed h 30
    └── text                                flex: 10 terms, each 9pt Semibold #16212E ↵ 8pt #4A5563
```

About has no Period or Platform effect, so its filter band shows the controls but adds the hint "Period and Platform apply to every other page".

### 3.11 Documentation (DOC), content vertical (new, decision D5)

```
DOC Content                                 vertical, 1312 × 836
├── DOC Top Row                             horizontal, fixed h 300
│   ├── DOC Purpose Card                    card, fixed w 435: DATA UPDATED ON (GL Data Updated), PURPOSE, DATA SOURCES
│   └── DOC Parameters Card                 card, flex: the parameter table from calc pack section 1
└── DOC Bottom Row                          horizontal, flex, margin-top 14
    ├── DOC Actions Card                    card, flex: every action, by dashboard
    └── DOC Notes Card                      card, fixed w 435: sheet prefixes, DZV calcs, known compromises, change log
```

All text objects, no sheets apart from GL Data Updated.

---

## 4. Formatting spec (item 9)

### 4.1 Colours (tokens)

| Token | Hex | Used for |
|---|---|---|
| Navy | `#002C55` | Titles, BANs, active button text, tooltip values |
| Accent | `#005FAE` | Main data colour, the current period in trends, links |
| Accent tint | `#E9F1F9` | Info callouts, selected table row |
| Accent mid | `#A9C8E6` | Info callout border |
| Lime | `#C7FFA4` | Active nav button only (chrome, never data) |
| Sky | `#83C7EB` | Brand mark only |
| Canvas | `#F5F5F3` | Dashboard background, button track, tags |
| Card | `#FFFFFF` | Cards, bands, nav |
| Line | `#E6E7E2` | Card borders, band rules, table header rule |
| Line soft | `#EFEFEB` | Gridlines, nav rules, section label rules |
| Ink 1 | `#16212E` | Body text, table values |
| Ink 2 | `#4A5563` | Secondary text, nav items, table text |
| Ink 3 | `#7A838E` | Subtitles, axis labels, CAPS labels |
| Ink 4 | `#A5ACB4` | Nav group labels, faint hints |
| Out of window | `#D9DCD7` | Trend bars outside the selected period |

### 4.2 Type scale (Tableau Book family)

| Role | Prototype | Tableau | Face | Colour |
|---|---|---|---|---|
| Page title | 20px | 15pt | Tableau Semibold | `#002C55` |
| Page question | 14px | 11pt | Tableau Book | `#7A838E` |
| Crumb | 10.5px | 8pt | Book, Medium for the page name | `#7A838E`, `#4A5563` |
| Brand name | 14px | 11pt | Tableau Bold | `#002C55` |
| Nav item | 12.5px | 9pt | Medium (Semibold when active) | `#4A5563` (`#002C55` active) |
| Nav group / CAPS labels | 9.5px | 7pt | Tableau Semibold | `#A5ACB4` nav, `#7A838E` elsewhere |
| Card title | 12.5px | 10pt | Tableau Semibold | `#16212E` |
| Card subtitle | 10.5px | 8pt | Tableau Book | `#7A838E` |
| KPI title (CAPS) | 10px | 8pt | Tableau Semibold | `#7A838E` |
| BAN (Health) | 24px | 18pt | Tableau Semibold | `#002C55` |
| BAN (mini KPI) | 22px | 16pt | Tableau Semibold | `#002C55` |
| BAN suffix ("of 27 now") | 12px | 9pt | Tableau Medium | `#7A838E` |
| Change line | 10.5px | 8pt | Semibold for the delta, Book for "vs prior 30d" | good `#1E7450`, bad `#A92E29`, flat `#4A5563`, rest `#7A838E` |
| Table header | 9.5px | 7pt CAPS | Tableau Semibold | `#7A838E` |
| Table body | 11px | 8pt | Tableau Book | `#16212E` (names), `#4A5563` (others) |
| Mark labels | 10 to 11px | 8pt | Book, Semibold for values | `#16212E` |
| Axis labels | 9.5px | 7pt | Tableau Book | `#7A838E` |
| Tooltip title | 11px | 9pt | Tableau Semibold | `#16212E` |
| Tooltip labels | 9px CAPS | 7pt | Tableau Semibold | `#7A838E` |
| Tooltip values | 11px | 9pt | Tableau Semibold | `#002C55` |
| Filter band labels | 9.5px CAPS | 7pt | Tableau Semibold | `#7A838E` |
| Buttons | 11.5px | 9pt | Book (Semibold when active) | `#4A5563` (`#002C55` active) |
| Hint | 11px italic | 8pt italic | Tableau Book | `#7A838E` |
| Callout text | 11.5px | 9pt | Tableau Book | warn `#5E3D07`, crit `#6E1D19`, info `#002C55` |
| Pill text | 10px | 7pt | Tableau Semibold | status ink |

The workbook font rule (`all.font-family = Tableau Book`) is already in the file. Each sheet only overrides size, weight and colour.

### 4.3 Number and date formats

| What | Format code | Example |
|---|---|---|
| Rate BANs (run success, test pass, freshness) | `0.00%` | 99.85% |
| Other percentages on BANs | `0%` | 85% |
| Percentages in tables and labels | `0.0%` | 3.3% |
| Percentages on axes | `0%` | 95% |
| Point change | `"▲ "0.00" pp";"▼ "0.00" pp";"● 0 pp"` | ▲ 0.10 pp |
| Percent change | `"▲ "0.0%;"▼ "0.0%;"● 0%"` | ▼ 15.1% |
| Percent change in tables | `"▲ "0%;"▼ "0%;"● 0%"` | ▲ 7% |
| Currency | `"$"#,##0;-"$"#,##0` | $4,189 |
| Small currency (cost per use) | `"$"#,##0.00` | $0.42 |
| Currency axis | `"$"#,##0` | $200 |
| Counts | `#,##0` | 1,986 |
| Thousands | `#,##0.0,"K"` | 12.3K |
| Millions | `#,##0.0,,"M"` | 60.9M |
| Health score | `0.0` | 99.7 |
| Day | `d mmm` | 19 Oct |
| Day with weekday | `ddd d mmm yyyy` | Mon 19 Oct 2026 |
| Timestamp | `d mmm, hh:nn` | 19 Oct, 21:25 |
| Durations and lags | string calcs already in the pack (`Last Runtime Label`, `Lag Now Label`, MTTR label) | 4.9 h, 27.9 min |

**Why two decimals on the rate BANs:** every value sits between 99.4% and 99.9%. At one decimal (the skill default) Run success and Freshness both show 99.9% and the change line rounds to 0.1 pp, which hides the story. This is a deliberate exception, noted in decision D8.

**Nulls:** every number shows "-" when empty (`alternate-text "-"`, `display-alternate-text true`).

**The ▲ ▼ colour** comes from the Change Good / Change Bad split fields in the calc pack, each in its own label run colour. The number format only adds the arrow.

### 4.4 Borders, padding, radius and callouts

| Object | Fill | Border | Radius | Padding | Margin |
|---|---|---|---|---|---|
| Dashboard | `#F5F5F3` | none | 0 | 0 | 0 |
| Bands (header, filter) | `#FFFFFF` | 1px rule below, as a blank | 0 | left/right 28 | 0 |
| Nav | `#FFFFFF` | 1px edge on the right, as a blank | 0 | 22 / 14 / 18 / 14 | 0 |
| Content | none | none | 0 | 20 / 28 / 22 / 28 | 0 |
| Card | `#FFFFFF` | 1px `#E6E7E2` | 10 | 14 / 16 / 14 / 16 | 7 on facing sides |
| KPI card (Health) | `#FFFFFF` | 1px `#E6E7E2` | 10 | 12 / 14 / 10 / 14 | 6 on facing sides |
| Mini KPI card | `#FFFFFF` | 1px `#E6E7E2` | 10 | 12 / 16 | 6 on facing sides |
| Button track | `#F5F5F3` | 1px `#E6E7E2` | 8 | 2 | top 11, bottom 12 |
| Nav button | none / `#C7FFA4` | none | 8 | left 10 | bottom 4 |
| Info panel | `#FFFFFF` | 1px `#E6E7E2` | 10 | 16 | 0 |
| Callout, info | `#E9F1F9` | 1px `#A9C8E6` | 8 | 10 / 12 | top 10 |
| Callout, warn | `#FDF3E1` | 1px `#F3DDB4` | 8 | 10 / 12 | top 10 |
| Callout, crit | `#FBEAE9` | 1px `#F2C9C6` | 8 | 10 / 12 | top 8 |
| Tag | `#F5F5F3` | 1px `#E6E7E2` | 4 | 1 / 6 | 0 |
| Sheets inside cards | none | none | 0 | 0 | 0 |
| Text objects | none | none | 0 | as listed in the tree | 0 |
| Rules (dividers) | `#E6E7E2` structure, `#EFEFEB` inside cards | none | 0 | 0 | 0 |

These follow the skill's 2026 product values (1px solid borders only, radius 10 on cards, 1px dividers as blanks, margin 0 on structure) with the prototype's colours and paddings.

### 4.5 Lines, axes and table dividers

| Element | Rule |
|---|---|
| Axes | Hidden on every sheet, except the time charts and the scatter |
| Time chart axes | y axis: 3 ticks (0, middle, max), labels 7pt `#7A838E`, no title, no ruler, no ticks. x axis: dates, 7pt `#7A838E`, month starts on 90-day charts, Mondays on 30-day charts |
| Gridlines | Off, except y gridlines on time charts and both gridlines on the scatter: 1px solid `#EFEFEB` |
| Zero lines | Off |
| Reference lines | Incident markers: 1px dotted `#7A838E`, label 7pt Semibold `#4A5563`. Perf annotations: same style, "fct_sessions fixed" in `#1E7450` |
| Period band | The selected window on 90-day charts gets a reference band in `#005FAE` at 5% opacity (`#005FAE0D`) |
| Table header divider | 1px solid `#E6E7E2` below the header row |
| Table row dividers | 1px dotted `#E6E7E2` |
| Column dividers | None |
| Row banding | None (the Gantt uses `#FBFBFA` banding on alternate jobs) |
| Field labels | Hidden on all sheets |
| Row height in tables | About 27px (Health alerts and Who to tell about 31px) |

### 4.6 Colour assignments per field

Palettes embedded in the workbook were dropped on save (they weren't used yet), so each field gets its colours on the sheet where it's used. The builder writes these as `<color>` encodings with fixed members.

**Status** (never reused for categories):

| Field | Members → colour |
|---|---|
| Status Label | Healthy `#2F9E6B`, Warning `#E8A33D`, Critical `#D2453F`, No data `#A3ADB8` |
| Status Tint Key | Healthy `#FFFFFF`, Warning `#FDF3E1`, Critical `#FBEAE9`, No data `#F1F2F4` |
| Status text (labels) | Healthy `#1E7450`, Warning `#93600F`, Critical `#A92E29`, No data `#4A5563` |
| Trust badge | Trusted `#1E7450`, Use with caution `#93600F`, Do not use `#A92E29`, No recent runs `#7A838E` |

**Platforms:** Platform Name: Snowflake `#005FAE`, Databricks `#4BAEE3`, Redshift `#5B5FC7`.

**Charts:**

| Sheet / field | Members → colour |
|---|---|
| Every KPI trend: In Period | True `#005FAE` (Exposures at risk: `#E8A33D`), False `#D9DCD7` |
| RUN Daily Failures Bar: outcome | Failed `#D2453F`, Skipped `#C3C9CF` |
| RUN Job Gantt: Run Outcome | Succeeded `#9DB9D6`, Failed `#D2453F`, Cancelled `#C3C9CF`; tests-failed dot `#E8A33D` |
| RUN Why Failed Bar, Top Failing Models | single `#D2453F` |
| QA Test Heatmap: worst result | No run `#F1F2F0`, Passed `#E3F2E9`, Warning `#E8A33D`, Failed `#D2453F` |
| QA Issues by Type Bar | single `#E8A33D` |
| QA Coverage by Domain Bar, PF bars, US multiples | single `#005FAE` on a `#EFEFEB` track |
| FR Source Lag Bullets | zones `#EAF6EF` / `#FDF3E1` / `#FBEAE9`, lag bar by Status Label |
| FR Late Checks Calendar | Before period `#EEF0EE`, On time `#E3F2E9`, Warn `#E8A33D`, Error `#D2453F` |
| FR Compliance line | by Platform Name |
| PF Slowest Models Runtime Line | Biggest change `#005FAE` (2px), others `#B9C0C7` (1px) |
| US Cost vs Usage Scatter | By hand `#005FAE`, AI-built `#5B5FC7` or `#3D41A0` (D4), Unregistered `#E8A33D`, Retire candidate `#D2453F`; retire zone `#FBEAE9` |
| GOV coverage cells | ≥ 90% fill `#EAF6EF` text `#1E7450`; ≥ 70% `#FDF3E1` / `#93600F`; below `#FBEAE9` / `#A92E29` |
| GOV Hygiene by Team Bar | ≥ 90% `#2F9E6B`, ≥ 70% `#E8A33D`, below `#D2453F` |
| GOV Maturity Bar | High `#CFE1F2`, Medium `#E9F1F9`, Low `#F5F5F3`; text `#002C55` |
| Lineage edges | Healthy `#CBD0D5`, Warning `#E8A33D`, Critical `#D2453F`; highlighted path `#005FAE` |
| Lineage node box fill | Status Tint Key; selected node name in Semibold |
| AI-built tag | text `#3D41A0` |

### 4.7 Marks and sizes

| Mark | Size target | Notes |
|---|---|---|
| KPI trend bars | 90 bars over 181px, about 75% of the slot | Fixed y axis from 0, hidden |
| Exposure tiles | Square at the full cell (163 × 63) | 1px `#E6E7E2` mark border |
| Alert rows | Square at full width, about 64px high | Status Tint Key fill, 1px border by status |
| Layer bars | 10px high | Stacked, 2px white gaps from mark borders |
| Lineage node boxes | Gantt, 22px high max | Size scales with the number of rows (calc pack 4.2) |
| Lineage edges | Line, 1px (1.4px when the parent is warn or crit) | Path highlight 1.6px |
| Daily bars (Runs, Perf) | Bar, about 80% of the day slot | |
| Gantt runs | 56% of the row height | Min width 2.5px (calc pack 6.3) |
| Heatmap cells | Square, fit to cell, 1px white border | |
| Bullets | Zones 12px, lag bar 4px | Lag bar centred on the zones |
| Lines | Main 2px, context 1px, compliance 1.8px | End label on the main line only |
| Scatter dots | Circle 9px across, retire candidates 12px | White 1.5px border |
| Hbar lists | 6px bar on a 6px `#EFEFEB` track | Value at the right end of the label row |
| Weekday mini bars | 7px wide, up to 16px high | |
| Buttons | Square at full cell | Tooltip off, highlighting off |

### 4.8 Tooltips

**Template** (every sheet that keeps a tooltip):

```
<Title field>                              9pt Tableau Semibold #16212E
LABEL   <value>                            7pt Semibold CAPS #7A838E, then 9pt Semibold #002C55
LABEL   <value>
…
Click to <action>                          7pt CAPS #A5ACB4 (only on clickable sheets)
```

| Setting | Value |
|---|---|
| Command buttons | Off on every sheet |
| Tooltips off | BAN-only text sheets without a definition, button sheets, labels, section headers, legends as sheets, GL sheets |
| Tooltips on | Every chart, table and tile; KPI BAN sheets carry the metric definition (I4) |
| Width | Default (responsive) |
| Viz in tooltip | None in the first build |

The tooltip content for each sheet is in the calc pack build notes ("Tooltip:" lines). The builder writes it in this template.

### 4.9 Interaction hygiene

- Every parameter action uses `clear-option do-nothing`, so selections stick.
- Every button and tile sheet gets the Dehighlight pattern (a highlight action on a blank `Highlight` field), so a click doesn't fade the other marks.
- No filter actions, and no legends shown as cards.
- Worksheet tabs are hidden on publish. Only the 11 dashboards show.

---

## 5. How I build it in the `.twb`

### 5.1 Approach

1. **A builder script**, `tableau/tools/build_workbook.py`. It reads the current master `.twb`, adds the calcs, parameters, worksheets, dashboards and actions from a Python spec, and writes a new file. The master is never edited in place.
2. **Calcs** go in exactly as written in the calc pack (comment header included). The script parses the pack's code blocks, so the pack stays the single source of truth.
3. **Sheets** are written from a short spec per sheet: base table, rows, columns, mark type, encodings, filters, formats and tooltip. These follow the build notes in the pack.
4. **Dashboards** are written from the trees in section 3 and the shell in section 2.
5. **Checks** before I hand anything over:
   - The file parses as XML.
   - Every calc reference resolves to a field that exists.
   - Every zone id is unique per dashboard, and every DZV edge points at a real zone.
   - The skill's `profile_twb.py` confirms padding, borders, fonts and calc comments against this spec.
6. **Your check** in Tableau: open the file, refresh the data source, look at each dashboard at 1600 × 1000, and tell me what's off. I fix it in the builder, not by hand, so fixes survive the next build.

### 5.2 Order

1. Shell on all 11 dashboards (empty content), so the nav works end to end.
2. Health overview (Tab 1), then your review.
3. Lineage, Blast radius, Runs, Data quality, Freshness, Performance, Usage, Governance, About, Documentation. (This is the order 1, 2, 3, 4, 7, 8, 6, 5, 9 from before, plus the two text tabs.)

### 5.3 Calc pack changes this plan needs

These are small and follow from the review. I'll add them to the pack when I start the build, each with its comment header:

| Calc or change | Section | Why |
|---|---|---|
| Period Label Active / Period Label Inactive | 2.6 | Two label colours on the period buttons (2.4) |
| Platform Label Active / Platform Label Inactive | 2.6 | Same, for the platform buttons |
| Tile View Label Active / Inactive, Lineage View Label Active / Inactive | 3.9, 4.3 | Same pattern on the other segmented buttons |
| Info Button Glyph | 2.6 | "ⓘ" when closed, "✕" when open (2.5) |
| Tile Name Short | 3.9 | Truncate long names (L1) |
| Show Trace Impact Button | 4.5 | DZV for the button on every node type except exposures |
| Calc pack 2.7 colour note | 2.7 | Active button is white with Navy text on a grey track, as the prototype shows |
| Calc pack 5.7 run-on | 5.7 | Email action on Select instead of Menu (I8) |
| `p_lineage_view` row | 1 | Add it to the parameter table (it's only described in 4.x today) |
| US Semantic Refresh Table | 10.3 | Fail days and Last failure instead of the sparkline, if D3 is agreed |
| Gaps lists top 5 | 11.2 | Rank and "and N more" calcs, if D6 is agreed |

---

## 6. Decisions (all agreed 21 Oct)

My recommendation is listed first in each row.

| # | Decision | Options | My recommendation |
|---|---|---|---|
| D1 | Health tile group labels ("BI DASHBOARDS 17") | (a) one tile sheet, group label as a narrow row header on the left (about 110px), tiles about 146px wide; (b) four tile sheets, one per group, with the label as each sheet's title, exactly like the prototype | **Agreed (21 Oct): (a)**. It survives the Needs attention switch and platform changes without gaps. With (b), the fixed group heights leave holes when the tile count drops |
| D2 | Font for node names, schemas and Slack channels | **Decided (21 Oct): Tableau family** (Book, Medium, Semibold) for identifiers too, no monospace | Done |
| D3 | Semantic refresh table's sparkline column | (a) Fail days + Last failure text columns; (b) a second sheet aligned beside the table | **Agreed (21 Oct): (a)**. (b) drifts out of line whenever the row count changes |
| D4 | AI-built dot on the Usage scatter | (a) `#3D41A0` (matches the AI-built tag, leaves purple `#5B5FC7` to Redshift); (b) keep `#5B5FC7` as in the prototype | **Agreed (21 Oct): (a)** |
| D5 | Developer documentation | (a) an 11th dashboard, Documentation, linked from About; (b) put it at the bottom of About | **Agreed (21 Oct): (a)**, as the skill's documentation template suggests |
| D6 | Gaps to close lists | (a) top 5 per list + "and N more"; (b) full lists that scroll | **Agreed (21 Oct): (a)** |
| D7 | Icons and the brand mark | **Decided (21 Oct): icons now.** The build ships as a .twbx with the PNGs inside (`tableau/Image/`, rendered from the prototype's own SVGs) | Done |
| D8 | Decimals on the rate BANs (run success, tests, freshness) | (a) 2 decimals as in the prototype (99.85%); (b) 1 decimal as in the skill (99.9%) | **Agreed (21 Oct): (a)**. At 1 decimal, two of the three show 99.9% and the changes vanish |
