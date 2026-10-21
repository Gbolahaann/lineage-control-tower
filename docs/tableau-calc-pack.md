# Lineage Control Tower: Tableau calc pack

Phase 4, step 1. Product style mode (portfolio). Source of truth for layout: `mockup/lineage-control-tower.html`. Data model: `docs/tableau-data-model.md`.

Status: **Shared calcs and Health overview, for review.** Lineage, Blast radius, Runs, Quality, Freshness, Performance, Usage and Governance follow after sign-off.

---

## 0. Conventions used in this pack

**Calc family.** `<Metric> - Focus / - Prior / - Change / - Change Good / - Change Bad / - Trend`. The skill's `- Change Colour` member is replaced by the Good / Bad pair, because the KPI change line is a text mark: Tableau can't colour part of a label from data, so each colour gets its own field and its own static colour in the label editor (the skill's +ve / -ve split).

**Field names.** Written exactly as the workbook names them today, with the CSV suffix on duplicated names, for example `[date (dim_date.csv)]` and `[node_id (dim_nodes.csv)]`. If you rename the logical tables first (data model step 6), paste the calcs before renaming and Tableau rewrites the references for you.

**Base tables.** A sheet may use one fact table plus the two shared dimensions (`dim_nodes`, `dim_date`) and `dim_owners`. A sheet that only uses `dim_nodes` (or only `dim_date`) has that dimension as its base. Every sheet below states its base, and none mixes two fact tables.

**Numbers reconciled.** Every Health formula below was checked in Python against `data/marts/` at 30 days and matches the hand-off: run success 99.85% (+0.10 pp), test pass 99.41%, freshness 99.87%, 50 failed runs, MTTR 4.87 h (shows 4.9 h), cost $4,189 vs $4,935 (-15.1%), 12 of 27 exposures at risk (4 critical, 8 warning).

**Colours** (from the hand-off):

| Use | Value |
|---|---|
| Healthy / Warning / Critical / No data | `#2F9E6B` / `#E8A33D` / `#D2453F` / `#A3ADB8` |
| Status tints (tile and alert fills) | Healthy `#FFFFFF` · Warning `#FDF3E1` · Critical `#FBEAE9` · No data `#F1F2F4` |
| Good / bad change text | `#1E7450` / `#A92E29`, grey tail `#7A838E` |
| Trend bars | in window `#005FAE` (at-risk card: `#E8A33D`), outside window `#D9DCD7` |
| Platforms | Snowflake `#005FAE` · Databricks `#4BAEE3` · Redshift `#5B5FC7` |

---

## 1. Parameters

Parameters can't hold comments, so this table is their documentation (copy it to the About / Documentation page).

| Parameter | Type | Allowable values | Default | Set by | Used for |
|---|---|---|---|---|---|
| `p_period` | Integer | List: 7 "Last 7 days", 30 "Last 30 days", 90 "Last 90 days" | 30 | GL Period Buttons | Every Focus / Prior window |
| `p_platform` | String | List: All "All", snowflake "Snowflake", databricks "Databricks", redshift "Redshift" | All | GL Platform Buttons | Platform match calcs |
| `p_selected_exposure` | String | All | `exposure.acme_core.executive_revenue_dashboard` | Health tiles, Usage table, Blast radius rows | Lineage scope, selection highlight |
| `p_selected_node` | String | All | `model.acme_core.stg_netsuite__journal_lines` | Lineage nodes, Health alert list, risk table | Blast radius scope, node panel |
| `p_selected_node_key` | Integer | All | 35 (the node above) | Same actions as `p_selected_node` | Lineage path highlight |
| `p_gantt_date` | Date | Range 22 Jul to 19 Oct 2026 | 19 Oct 2026 | Runs daily failures chart | Runs Gantt |
| `p_show_info` | Boolean | True / False, aliases "Show" / "Hide" | False | GL Info Button | DZV on the info panel |
| `p_tile_view` | String | List: All "All", Needs attention "Needs attention" | All | HO Tile View buttons | Health tile filter. **New, not in the data model doc** |

---

## 2. Shared calcs (every dashboard)

### 2.1 Period window

```
// In Period
// TRUE for days inside the selected window: the last 7, 30 or 90 days up to 19 Oct.
// Used by every "- Focus" measure and to colour the window on trend bars.
[days_before_as_of] < [p_period]
```

```
// In Prior Period
// TRUE for the same-length window just before the selected one.
// Matches no rows at 90 days (the data starts 22 Jul), so every "- Prior" measure returns NULL there.
[days_before_as_of] >= [p_period]
AND [days_before_as_of] < 2 * [p_period]
```

```
// Has Prior Period
// FALSE at 90 days, when there is no earlier window in the data.
// Drives the "no earlier period" wording. Measures don't need it: their Prior is NULL anyway.
2 * [p_period] <= { MAX([day_index]) } + 1
```

```
// Period Label
// "Last 30 days". Used in titles and tooltips.
"Last " + STR([p_period]) + " days"
```

```
// Compare Label
// Grey tail of every KPI change line: "vs prior 30d", or "-  no earlier period" at 90 days.
IF [Has Prior Period]
    THEN "vs prior " + STR([p_period]) + "d"
ELSE "-  no earlier period"
END
```

```
// Period Hint Label
// Hint text at the right of the filter band, as in the prototype.
IF [Has Prior Period]
    THEN "Changes compare with the " + STR([p_period]) + " days before"
ELSE "No earlier period in the data to compare with"
END
```

```
// Data Updated Label
// Header stamp. The data runs to the end of the last day (data_as_of = 23:59 UTC).
// Dynamic from dim_date, so it moves when the generator is rerun with new dates.
"Data updated on "
+ STR(DAY({ MAX([date (dim_date.csv)]) })) + " "
+ LEFT(DATENAME('month', { MAX([date (dim_date.csv)]) }), 3) + " "
+ STR(YEAR({ MAX([date (dim_date.csv)]) }))
+ ", 23:59"
```

```
// History Label
// Second line of the header stamp: "90 days of history from 22 Jul 2026".
STR({ COUNTD([date (dim_date.csv)]) }) + " days of history from "
+ STR(DAY({ MIN([date (dim_date.csv)]) })) + " "
+ LEFT(DATENAME('month', { MIN([date (dim_date.csv)]) }), 3) + " "
+ STR(YEAR({ MIN([date (dim_date.csv)]) }))
```

### 2.2 Platform match

```
// Is Platform Match Node
// Node-level platform filter (dim_nodes). A migrated node matches both Redshift and Snowflake,
// so it still shows when someone looks at Redshift history.
[p_platform] = "All"
OR CONTAINS([platform_filter_values], "|" + [p_platform] + "|")
```

```
// Is Platform Match Day
// Day-level platform filter for Node Daily. Migrated models count against Redshift before
// their move and Snowflake after, so daily KPIs and cost split correctly by platform.
[p_platform] = "All"
OR [platform_on_day] = [p_platform]
```

```
// Is Platform Match Day (Episodes)
// Same rule for Recovery Episodes: the platform the node was on when the failure started.
[p_platform] = "All"
OR [platform_on_day (mart_recovery_episodes.csv)] = [p_platform]
```

Job Runs and Run Errors get their own version in the Runs pack, because each has its own `platform` column.

### 2.3 Status label, icon and colour keys (dim_nodes, current snapshot)

```
// Status Label
// One status vocabulary for every sheet. Assign the palette once on this field:
// Healthy #2F9E6B, Warning #E8A33D, Critical #D2453F, No data #A3ADB8.
CASE [current_status_code]
WHEN 3 THEN "Critical"
WHEN 2 THEN "Warning"
WHEN 1 THEN "Healthy"
ELSE "No data"
END
```

```
// Status Icon
// Shape-free icon so colour is never the only signal (spec rule). Pairs with Status Label.
CASE [current_status_code]
WHEN 3 THEN "✕"
WHEN 2 THEN "▲"
WHEN 1 THEN "✓"
ELSE "–"
END
```

```
// Status Tint Key
// Same values as Status Label, kept as a separate field so it can carry the light tint palette
// for tile and alert backgrounds: Healthy #FFFFFF, Warning #FDF3E1, Critical #FBEAE9, No data #F1F2F4.
[Status Label]
```

```
// Status Severity Sort
// Worst first, for lists: Critical 1, Warning 2, Healthy 3, No data 4.
CASE [current_status_code]
WHEN 3 THEN 1
WHEN 2 THEN 2
WHEN 1 THEN 3
ELSE 4
END
```

```
// Status Stack Order
// Healthy first, for stacked bars, as in the prototype's layer health strip: Healthy, Warning, Critical, No data.
CASE [current_status_code]
WHEN 1 THEN 1
WHEN 2 THEN 2
WHEN 3 THEN 3
ELSE 4
END
```

```
// Is At Risk Now
// Warning or Critical in the current snapshot. Shared by Health, Blast radius and Governance.
[current_status_code] >= 2
```

### 2.4 Selection

```
// Is Selected Exposure
// TRUE for the exposure chosen on any tab (tile, usage row, blast row). Drives highlight and scope.
[node_id (dim_nodes.csv)] = [p_selected_exposure]
```

```
// Is Selected Node
// TRUE for the node chosen on any tab (lineage node, alert row, risk row).
[node_id (dim_nodes.csv)] = [p_selected_node]
```

```
// Is Selected Node Key
// Integer twin of Is Selected Node, for the lineage path highlight (reach_keys hold node_keys).
[node_key] = [p_selected_node_key]
```

```
// Selected Exposure Name
// Display name of the selected exposure, for titles and the selection chip.
{ MAX(IF [node_id (dim_nodes.csv)] = [p_selected_exposure]
    THEN [display_name] END) }
```

```
// Selected Node Name
// Display name of the selected node, for titles and the selection chip.
{ MAX(IF [node_id (dim_nodes.csv)] = [p_selected_node]
    THEN [display_name] END) }
```

```
// Clear Node Value
// Empty string a parameter action can write into p_selected_node, to clear it (prototype: opening an exposure clears the node).
""
```

```
// Clear Node Key Value
// Companion to Clear Node Value for p_selected_node_key. -1 matches no node.
-1
```

### 2.5 Display helpers (dim_nodes)

```
// Layer Name
// Prototype column names for the lineage layers.
CASE [layer]
WHEN "source"       THEN "Sources"
WHEN "staging"      THEN "Staging"
WHEN "intermediate" THEN "Intermediate"
WHEN "mart"         THEN "Marts"
WHEN "semantic"     THEN "BI semantic layer"
WHEN "exposure"     THEN "Exposures"
END
```

```
// Platform Name
// Display casing for the current platform.
CASE [platform_now]
WHEN "snowflake"  THEN "Snowflake"
WHEN "databricks" THEN "Databricks"
WHEN "redshift"   THEN "Redshift"
END
```

```
// Consumer Type Label
// Tile meta line: the BI tool for dashboards, otherwise the consumer type.
IF NOT ISNULL([bi_tool]) THEN
    CASE [bi_tool]
    WHEN "tableau"  THEN "Tableau"
    WHEN "sigma"    THEN "Sigma"
    WHEN "power_bi" THEN "Power BI"
    END
ELSE
    CASE [exposure_type]
    WHEN "dashboard" THEN "Dashboard"
    WHEN "notebook"  THEN "Notebook"
    WHEN "ml"        THEN "ML model"
    WHEN "data_app"  THEN "Data app"
    WHEN "agent"     THEN "AI agent"
    WHEN "data_hub"  THEN "Data hub"
    END
END
```

```
// Node Count
// Number of nodes in the view. dim_nodes has one row per node.
COUNTD([node_id (dim_nodes.csv)])
```

### 2.6 Global filter band and info button (dim_date scaffold)

The period and platform buttons need a field with 3 and 4 values. There is none, so these calcs borrow the first rows of `dim_date` as a scaffold. Each button sheet uses Dates only.

```
// Period Option
// Scaffold: turns the first 3 days of dim_date into the 3 period buttons. Filter to non-null.
CASE [day_index]
WHEN 0 THEN 7
WHEN 1 THEN 30
WHEN 2 THEN 90
END
```

```
// Period Option Label
// Button text, as in the prototype.
"Last " + STR([Period Option]) + " days"
```

```
// Is Active Period Option
// Colours the selected period button (Navy fill, white text) against the rest.
[Period Option] = [p_period]
```

```
// Platform Option
// Scaffold: turns the first 4 days of dim_date into the 4 platform buttons. Filter to non-null.
CASE [day_index]
WHEN 0 THEN "All"
WHEN 1 THEN "snowflake"
WHEN 2 THEN "databricks"
WHEN 3 THEN "redshift"
END
```

```
// Platform Option Label
// Button text, as in the prototype.
CASE [Platform Option]
WHEN "All"        THEN "All"
WHEN "snowflake"  THEN "Snowflake"
WHEN "databricks" THEN "Databricks"
WHEN "redshift"   THEN "Redshift"
END
```

```
// Is Active Platform Option
// Colours the selected platform button.
[Platform Option] = [p_platform]
```

```
// Info Toggle Value
// The value the info button writes into p_show_info: the opposite of the current state.
NOT [p_show_info]
```

### 2.7 Shared sheets (on every dashboard)

| Sheet | Base table | Marks | Notes |
|---|---|---|---|
| GL Period Buttons | dim_date | Text on a Square, Columns: Period Option Label | Filter Period Option non-null. Colour: Is Active Period Option (True `#002C55`, False `#FFFFFF`). Tooltip off |
| GL Platform Buttons | dim_date | Same pattern, Platform Option Label | Platform dot: a second Circle mark coloured by platform |
| GL Period Hint | dim_date | Text: Period Hint Label | `#7A838E`, 10pt |
| GL Data Updated | dim_date | Text: Data Updated Label, History Label | Right-aligned in the header |
| GL Info Button | dim_date | Text "ⓘ" (one mark: filter day_index = 0) | Parameter action sets p_show_info from Info Toggle Value |

Shared actions (repeat on every dashboard):

| Action | Type | Source | Target | Field | Run on |
|---|---|---|---|---|---|
| GL Set Period | Parameter | GL Period Buttons | p_period | Period Option | Select |
| GL Set Platform | Parameter | GL Platform Buttons | p_platform | Platform Option | Select |
| GL Toggle Info | Parameter | GL Info Button | p_show_info | Info Toggle Value | Select |
| GL Clear Button Selection | Highlight with a blank `Highlight` field, or Disable highlighting on each button sheet | | | | |

---

## 3. Health overview (`HO`)

Title "Is anything on fire right now?". Layout from the prototype: a row of 6 KPI cards (128 px), then the exposure status card (left) beside a 410 px column holding Needs attention now (top) and Health by layer (bottom).

### 3.1 Sheet list and base tables

| # | Sheet | Base table | Also uses (shared) | What it shows |
|---|---|---|---|---|
| 1 | HO Run Success KPI | Node Daily | Dates, Nodes | BAN + change line |
| 2 | HO Run Success KPI Trend | Node Daily | Dates | Failed model runs per day, 90 days |
| 3 | HO Test Pass KPI | Node Daily | Dates | BAN + change line |
| 4 | HO Test Pass KPI Trend | Node Daily | Dates | Failing or warning tests per day |
| 5 | HO Freshness SLA KPI | Node Daily | Dates | BAN + change line |
| 6 | HO Freshness SLA KPI Trend | Node Daily | Dates | Late source checks per day |
| 7 | HO Exposures At Risk KPI | Nodes | | "12 of 27 now", "4 critical · 8 warning" |
| 8 | HO Exposures At Risk KPI Trend | Exposure Daily | Dates, Nodes | Exposures at risk at end of each day |
| 9 | HO MTTR KPI | Recovery Episodes | Dates | BAN + change line (inverse) |
| 10 | HO MTTR KPI Trend | Recovery Episodes | Dates | Mean recovery time per day |
| 11 | HO Warehouse Cost KPI | Node Daily | Dates | BAN + change line (inverse) |
| 12 | HO Warehouse Cost KPI Trend | Node Daily | Dates | Daily cost |
| 13 | HO Exposure Status Tiles | Nodes | | 27 tiles in 4 groups, 5 per row |
| 14 | HO Tile View Buttons | Dates | | All / Needs attention (scaffold, as in 2.6) |
| 15 | HO Needs Attention List | Nodes | | Failing, late or warning upstream nodes |
| 16 | HO Layer Health Bar | Nodes | | Stacked status share per layer, with counts |

No sheet mixes two fact tables. Sheets 7, 13, 15 and 16 are dim_nodes only. Sheet 8 is the only one that reads Exposure Daily, and it uses Nodes only for the platform filter (a shared dimension, so that is allowed).

**Filters on every Node Daily KPI and trend sheet:** Is Platform Match Day = True. **On Episodes sheets:** Is Platform Match Day (Episodes) = True. **On Nodes and Exposure Daily sheets:** Is Platform Match Node = True. KPI sheets don't filter on In Period; the window lives inside the measures, so the Prior window stays in the data. Trend sheets show all 90 days and colour the window with In Period.

### 3.2 KPI 1: Run success (Node Daily)

```
// Run Success - Focus
// Successful model runs / all model runs in the window. The mart's runs column already excludes skipped runs.
// 30d check: 99.85%.
SUM(IF [In Period] THEN [runs] - [runs_failed] END)
/
SUM(IF [In Period] THEN [runs] END)
```

```
// Run Success - Prior
// Same rate for the window before. NULL at 90 days.
SUM(IF [In Prior Period] THEN [runs] - [runs_failed] END)
/
SUM(IF [In Prior Period] THEN [runs] END)
```

```
// Run Success - Change
// Rate metric, so the change is in percentage points. 30d check: +0.10 pp.
([Run Success - Focus] - [Run Success - Prior]) * 100
```

```
// Run Success - Change Good
// Green part of the change line. Higher is better, so a rise (or no change) lands here.
// Format: ▲ 0.00 pp;▼ 0.00 pp;● 0 pp
IF [Run Success - Change] >= 0 THEN [Run Success - Change] END
```

```
// Run Success - Change Bad
// Red part of the change line: a fall in run success. Same number format as Change Good.
IF [Run Success - Change] < 0 THEN [Run Success - Change] END
```

```
// Run Success - Trend
// Bars under the card: failed model runs per day (the prototype never plots a rate on a cut baseline).
SUM([runs_failed])
```

BAN format `0.00%`. Card caption: "Bars: failed runs per day".

### 3.3 KPI 2: Test pass rate (Node Daily)

```
// Test Pass - Focus
// Passing tests / all tests run in the window. Warnings count as not passing. 30d check: 99.41%.
SUM(IF [In Period] THEN [tests_pass] END)
/
SUM(IF [In Period] THEN [tests_pass] + [tests_warn] + [tests_fail] END)
```

```
// Test Pass - Prior
// Same rate for the window before. NULL at 90 days.
SUM(IF [In Prior Period] THEN [tests_pass] END)
/
SUM(IF [In Prior Period] THEN [tests_pass] + [tests_warn] + [tests_fail] END)
```

```
// Test Pass - Change
// Rate metric, percentage points.
([Test Pass - Focus] - [Test Pass - Prior]) * 100
```

```
// Test Pass - Change Good
// Higher is better. Format: ▲ 0.00 pp;▼ 0.00 pp;● 0 pp
IF [Test Pass - Change] >= 0 THEN [Test Pass - Change] END
```

```
// Test Pass - Change Bad
// A fall in the pass rate. Same number format.
IF [Test Pass - Change] < 0 THEN [Test Pass - Change] END
```

```
// Test Pass - Trend
// Bars: failing or warning test executions per day. The Monday spikes are story 2.
SUM([tests_warn] + [tests_fail])
```

### 3.4 KPI 3: Freshness SLA (Node Daily)

```
// Freshness SLA - Focus
// Hourly source freshness checks that passed / all checks in the window. 30d check: 99.87%.
SUM(IF [In Period] THEN [fresh_checks_pass] END)
/
SUM(IF [In Period] THEN [fresh_checks_pass] + [fresh_checks_warn] + [fresh_checks_error] END)
```

```
// Freshness SLA - Prior
// Same rate for the window before. NULL at 90 days.
SUM(IF [In Prior Period] THEN [fresh_checks_pass] END)
/
SUM(IF [In Prior Period] THEN [fresh_checks_pass] + [fresh_checks_warn] + [fresh_checks_error] END)
```

```
// Freshness SLA - Change
// Rate metric, percentage points.
([Freshness SLA - Focus] - [Freshness SLA - Prior]) * 100
```

```
// Freshness SLA - Change Good
// Higher is better. Format: ▲ 0.00 pp;▼ 0.00 pp;● 0 pp
IF [Freshness SLA - Change] >= 0 THEN [Freshness SLA - Change] END
```

```
// Freshness SLA - Change Bad
// A fall in freshness compliance. Same number format.
IF [Freshness SLA - Change] < 0 THEN [Freshness SLA - Change] END
```

```
// Freshness SLA - Trend
// Bars: late source checks (warn or error) per day. The 1 Oct spike is the Stripe outage (story 5).
SUM([fresh_checks_warn] + [fresh_checks_error])
```

### 3.5 KPI 4: Exposures at risk

KPI sheet, base Nodes:

```
// Exposures At Risk Now
// Exposures whose upstream chain is Warning or Critical in the current snapshot. Check: 12.
ZN(SUM(IF [resource_type] = "exposure" AND [Is At Risk Now] THEN 1 END))
```

```
// Exposures In Scope
// All exposures for the selected platform, including unregistered ones. Check: 27.
ZN(SUM(IF [resource_type] = "exposure" THEN 1 END))
```

```
// Exposures At Risk Of Label
// Small grey suffix after the BAN: "of 27 now".
"of " + STR([Exposures In Scope]) + " now"
```

```
// Exposures Critical Now
// Change-line lead, in red: "4 critical". Format: 0 "critical"
ZN(SUM(IF [resource_type] = "exposure" AND [current_status_code] = 3 THEN 1 END))
```

```
// Exposures Warning Now
// Change-line tail, in grey: "· 8 warning". Format: "· "0" warning"
ZN(SUM(IF [resource_type] = "exposure" AND [current_status_code] = 2 THEN 1 END))
```

Trend sheet, base Exposure Daily:

```
// Exposures At Risk - Trend
// Exposures Warning or Critical at the end of each day. One row per exposure per day, so this counts exposures.
SUM(IF [status_eod_code] >= 2 THEN 1 ELSE 0 END)
```

The window colour on this card is Warning `#E8A33D`, not the accent, as in the prototype. No change line: the card compares critical with warning instead.

### 3.6 KPI 5: Mean time to recover (Recovery Episodes)

```
// MTTR - Focus
// Mean hours from a node's first failure to its next success, for episodes that started in the window and have recovered.
// Covers model runs, source freshness and BI refreshes. 30d check: 4.87 h.
AVG(IF [In Period] AND NOT [is_open] THEN [hours_to_recover] END)
```

```
// MTTR - Prior
// Same average for episodes that started in the window before. NULL at 90 days.
AVG(IF [In Prior Period] AND NOT [is_open] THEN [hours_to_recover] END)
```

```
// MTTR - Change
// Percentage change. Inverse metric: a rise is bad.
IF [MTTR - Prior] = 0 OR ISNULL([MTTR - Prior]) THEN NULL
ELSE [MTTR - Focus] / [MTTR - Prior] - 1
END
```

```
// MTTR - Change Good
// Inverse metric, so a fall (or no change) is good and shows in green. Format: ▲ 0.0%;▼ 0.0%;● 0%
IF [MTTR - Change] <= 0 THEN [MTTR - Change] END
```

```
// MTTR - Change Bad
// A rise in recovery time, in red. Same number format.
IF [MTTR - Change] > 0 THEN [MTTR - Change] END
```

```
// MTTR - Focus Label
// BAN text, matching the prototype: minutes under an hour, otherwise hours to 1 decimal. "-" when nothing recovered.
IF ISNULL([MTTR - Focus]) THEN "-"
ELSEIF [MTTR - Focus] < 1
    THEN STR(ROUND([MTTR - Focus] * 60)) + " min"
ELSE STR(ROUND([MTTR - Focus], 1)) + " h"
END
```

```
// MTTR - Trend
// Bars: mean recovery time of episodes that started each day. Days with no episodes stay empty.
AVG(IF NOT [is_open] THEN [hours_to_recover] END)
```

### 3.7 KPI 6: Warehouse cost (Node Daily)

```
// Warehouse Cost - Focus
// dbt build cost plus direct consumer query cost, USD, in the window. 30d check: $4,189.
SUM(IF [In Period] THEN [build_cost_usd] + [consumer_query_cost_usd] END)
```

```
// Warehouse Cost - Prior
// Same total for the window before. 30d check: $4,935. NULL at 90 days.
SUM(IF [In Prior Period] THEN [build_cost_usd] + [consumer_query_cost_usd] END)
```

```
// Warehouse Cost - Change
// Percentage change. Inverse metric: a rise is bad. 30d check: -15.1%.
IF [Warehouse Cost - Prior] = 0 OR ISNULL([Warehouse Cost - Prior]) THEN NULL
ELSE [Warehouse Cost - Focus] / [Warehouse Cost - Prior] - 1
END
```

```
// Warehouse Cost - Change Good
// A fall in cost, in green. Format: ▲ 0.0%;▼ 0.0%;● 0%
IF [Warehouse Cost - Change] <= 0 THEN [Warehouse Cost - Change] END
```

```
// Warehouse Cost - Change Bad
// A rise in cost, in red. Same number format.
IF [Warehouse Cost - Change] > 0 THEN [Warehouse Cost - Change] END
```

```
// Warehouse Cost - Trend
// Bars: daily cost. The early-October drop is fct_sessions going incremental (story 1).
SUM([build_cost_usd] + [consumer_query_cost_usd])
```

BAN format `$#,##0`.

### 3.8 KPI card build (same for all 6)

- **KPI sheet:** Text mark, no fields on Rows or Columns. Label: line 1 the BAN (Focus measure, or MTTR - Focus Label, or Exposures At Risk Now + Exposures At Risk Of Label), line 2 Change Good (`#1E7450`, semibold) + Change Bad (`#A92E29`, semibold) + Compare Label (`#7A838E`). Only one of Good / Bad is ever non-null. Left-aligned. BAN Tableau Semibold 18pt `#002C55` (prototype 24 px at a 1600 canvas). Change line 8pt.
- **Title:** dashboard text object above the sheet: caps, 8pt, `#7A838E`, letter-spaced, plus the ⓘ. The definition goes in the KPI sheet's tooltip (the prototype's info hover text), in the skill's tooltip style: ALL CAPS label, value semibold.
- **Trend sheet:** Columns: `[date (dim_date.csv)]` as continuous exact date. Rows: the Trend measure. Bar mark, size just under the full cell. Colour: In Period (True = accent or `#E8A33D`, False = `#D9DCD7`). Hide axes, gridlines, zero line. Height 30 px. Tooltip: date, then the measure with the card's caption label.
- **Card container:** vertical, white, 1px `#E6E7E2` border, padding 12 / 14 / 10, outer padding 7 (14 px gap). Name it `HO KPI <Metric> Card`.

### 3.9 Exposure status tiles (Nodes)

```
// Is Exposure
// Keeps exposure rows only. Put on Filters (True).
[resource_type] = "exposure"
```

```
// Show Exposure Tile
// The All / Needs attention switch above the grid.
[p_tile_view] = "All"
OR [Is At Risk Now]
```

```
// Exposure Group Sort
// Prototype group order: BI dashboards, Apps ML and notebooks, AI agents and data hubs, Unregistered.
CASE [exposure_group]
WHEN "BI dashboards"                        THEN 1
WHEN "Apps, ML and notebooks"               THEN 2
WHEN "AI agents and data hubs"              THEN 3
WHEN "Unregistered, found in query history" THEN 4
END
```

```
// Exposure Group Label
// Group header with its tile count, for example "BI DASHBOARDS   17".
// The count is FIXED with the platform and tile-view rules inside it, so no context filters are needed.
UPPER([exposure_group]) + "   "
+ STR({ FIXED [exposure_group] :
    SUM(IF [Is Exposure] AND [Is Platform Match Node] AND [Show Exposure Tile]
        THEN 1 END) })
```

```
// Tile Sort Key
// Worst first, then name, inside each group: "6..." Critical, "7..." Warning, "8..." Healthy.
// Used as the custom sort (MIN, ascending) of the tile INDEX.
STR(9 - [current_status_code]) + [display_name]
```

```
// Tile Column
// Column 1 to 5 in the tile grid (the prototype shows 5 tiles per row).
// Table calc: Specific dimensions = exposure_group, node_id (dim_nodes.csv); restart every exposure_group;
// sort by Tile Sort Key, MIN, ascending. Make it discrete.
(INDEX() - 1) % 5 + 1
```

```
// Tile Row
// Row inside each group. Same compute-using and sort as Tile Column. Make it discrete.
INT((INDEX() - 1) / 5) + 1
```

```
// Tile Owner Text
// Owner on the tile meta line, grey. Empty when there is no owner (the red version takes over).
IF [owner_name] <> "No owner" THEN [owner_name] ELSE "" END
```

```
// Tile Owner Missing Text
// "No owner" in red bold on the meta line (story 8 and the unregistered consumers).
IF [owner_name] = "No owner" THEN "No owner" ELSE "" END
```

```
// Tile Trust Critical
// Trust badge with its icon, shown in red. Only one of the three trust fields is filled for a tile.
IF [current_status_code] = 3 THEN "✕ " + [trust_badge] ELSE "" END
```

```
// Tile Trust Warning
// Trust badge with its icon, shown in the warning text colour #93600F.
IF [current_status_code] = 2 THEN "▲ " + [trust_badge] ELSE "" END
```

```
// Tile Trust Healthy
// Trust badge with its icon, shown in the healthy text colour #1E7450.
IF [current_status_code] = 1 THEN "✓ " + [trust_badge] ELSE "" END
```

```
// Tile AI Tag
// "AI-built" chip text for ai_assisted exposures (story 10 and the agents).
IF [build_method] = "ai_assisted" THEN "AI-built" ELSE "" END
```

```
// Tile Tooltip Why
// Tooltip "Why" block: the upstream nodes behind the status, or a reassurance line.
IF [culprit_count] > 0 THEN [culprit_nodes]
ELSE "Every upstream step is healthy"
END
```

Build: Rows `Exposure Group Sort` (hidden), `Exposure Group Label`, `Tile Row`; Columns `Tile Column`. Square mark, size near the full cell, colour **Status Tint Key** (tint palette), 1px `#E6E7E2` cell borders. Label, left-aligned top: `display_name` (Semibold 9pt `#16212E`) / `Consumer Type Label` + " · " + `Tile Owner Text` (`#7A838E`) + `Tile Owner Missing Text` (`#A92E29` bold) / the three trust fields (each in its status text colour) + `Tile AI Tag` + `health_score_now` (format `0.0`, right-aligned is not possible inside one label, so it follows the badge). Filters: Is Exposure, Is Platform Match Node, Show Exposure Tile. Tooltip: display_name, STATUS trust_badge, HEALTH SCORE (7D) health_score_now, OWNER owner_name, WHY Tile Tooltip Why, "Click to open lineage".

```
// Tile View Option
// Scaffold for the All / Needs attention buttons (first 2 days of dim_date). Filter to non-null.
CASE [day_index]
WHEN 0 THEN "All"
WHEN 1 THEN "Needs attention"
END
```

```
// Is Active Tile View
// Colours the selected tile-view button.
[Tile View Option] = [p_tile_view]
```

### 3.10 Needs attention now (Nodes)

```
// Is Attention Node
// Upstream nodes (not exposures) that are Warning or Critical right now. Today: 3 nodes.
[resource_type] <> "exposure"
AND [Is At Risk Now]
```

```
// Attention Sort
// Worst first, then the node that feeds the most exposures. Sort Rows by this, descending.
[current_status_code] * 1000 + [exposures_fed]
```

```
// Attention Reason
// Second line of the alert: what is wrong. Failed models get the time of the failure, as in the prototype.
[status_reason]
+ IF [last_run_status] = "error" AND NOT ISNULL([last_event_at])
    THEN " at " + STR(DAY([last_event_at])) + " "
        + LEFT(DATENAME('month', [last_event_at]), 3) + ", "
        + RIGHT("0" + STR(DATEPART('hour', [last_event_at])), 2) + ":"
        + RIGHT("0" + STR(DATEPART('minute', [last_event_at])), 2)
  ELSE ""
  END
```

```
// Attention Meta
// Third line: where it sits and what it affects, for example "Staging · Snowflake · affects 4 exposures".
[Layer Name] + " · " + [Platform Name] + " · affects "
+ STR([exposures_fed])
+ IF [exposures_fed] = 1 THEN " exposure" ELSE " exposures" END
```

```
// Attention Incident Tag
// Incident chip next to the node name, for example "INC-008". Empty when there is no open incident.
IFNULL([open_incident_id], "")
```

Build: Rows `Attention Sort` (discrete, sorted descending, hidden), `node_id (dim_nodes.csv)` (hidden); Gantt bar or Square mark full width, colour **Status Tint Key**. Label: `Status Icon` (coloured per status through three split fields, as for the tiles, or a separate Shape column coloured by Status Label) / `display_name` (Semibold) + `Attention Incident Tag` / `Attention Reason` / `Attention Meta` (with the "affects N exposures" part bold, which needs it in its own field if you want the weight change). Filters: Is Attention Node, Is Platform Match Node. Empty state: a text object "Nothing needs attention right now." behind the sheet.

### 3.11 Health by layer (Nodes)

```
// Layer Share
// Each status's share of the layer, so every bar spans the full width.
// Table calc: compute using Status Label (along the bar).
[Node Count] / TOTAL([Node Count])
```

```
// Layer Total
// Nodes in the layer for the selected platform. FIXED with the platform rule inside, so no context filter is needed.
{ FIXED [layer] : SUM(IF [Is Platform Match Node] THEN 1 END) }
```

```
// Layer Issues
// Nodes in the layer that are Warning or Critical right now, for the selected platform.
{ FIXED [layer] : SUM(IF [Is Platform Match Node] AND [Is At Risk Now] THEN 1 ELSE 0 END) }
```

```
// Layer Has Critical
// TRUE when any node in the layer is Critical, so the issue count shows in red rather than amber.
{ FIXED [layer] : MAX(IF [Is Platform Match Node] AND [current_status_code] = 3 THEN 1 ELSE 0 END) } = 1
```

```
// Layer Issues Critical Text
// "1 / " in red, shown when the layer has a Critical node.
IF [Layer Issues] > 0 AND [Layer Has Critical]
    THEN STR([Layer Issues]) + " / "
ELSE ""
END
```

```
// Layer Issues Warning Text
// "1 / " in amber ink #93600F, when the layer has issues but none Critical.
IF [Layer Issues] > 0 AND NOT [Layer Has Critical]
    THEN STR([Layer Issues]) + " / "
ELSE ""
END
```

```
// Layer Total Text
// The layer total, in grey after the issue count: "1 / 30" or just "21".
STR([Layer Total])
```

Build: Rows `layer_column` (hidden, sorted ascending), `Layer Name`. Columns: `Layer Share` (bar, stacked) and, on a dual axis, `MIN(1.06)` as a Text mark carrying Layer Issues Critical Text (`#A92E29` bold) + Layer Issues Warning Text (`#93600F` bold) + Layer Total Text (`#7A838E`). Bar colour: Status Label (main palette), sorted by Status Stack Order. Fix the axis 0 to 1.15 and hide it. Filter: Is Platform Match Node. Tooltip on bars: layer, STATUS, "n of N".

### 3.12 Health actions

| Action | Type | Source sheet | Target | Field | Run on |
|---|---|---|---|---|---|
| HO Tile Select Exposure | Parameter | HO Exposure Status Tiles | p_selected_exposure | node_id (dim_nodes.csv) | Select |
| HO Tile Clear Node | Parameter | HO Exposure Status Tiles | p_selected_node | Clear Node Value | Select |
| HO Tile Clear Node Key | Parameter | HO Exposure Status Tiles | p_selected_node_key | Clear Node Key Value | Select |
| HO Tile Open Lineage | Go to sheet | HO Exposure Status Tiles | Lineage dashboard | | Select |
| HO Alert Select Node | Parameter | HO Needs Attention List | p_selected_node | node_id (dim_nodes.csv) | Select |
| HO Alert Select Node Key | Parameter | HO Needs Attention List | p_selected_node_key | node_key | Select |
| HO Alert Open Blast Radius | Go to sheet | HO Needs Attention List | Blast radius dashboard | | Select |
| HO Set Tile View | Parameter | HO Tile View Buttons | p_tile_view | Tile View Option | Select |
| GL actions | see 2.7 | | | | |

The source fields for the parameter actions (node_id, node_key, Clear Node Value, Clear Node Key Value) must sit on Detail of the source sheet. Turn tooltips off on the button sheets, and use the blank `Highlight` field or disable highlighting so a click doesn't fade the other tiles.

### 3.13 Container names (Health)

`HO Root` (tiled) › `HO Nav` (232, shared nav) › `HO Main` (vertical) › `HO Header` (70) · `HO Filter Band` (52) · `HO Content` (padding 20 / 28) › `HO KPI Row` (6 × `HO KPI <Metric> Card`) · `HO Body` (horizontal) › `HO Exposure Card` · `HO Right Column` (410) › `HO Attention Card` · `HO Layer Card`. Plus `GL Info Panel` (floating, DZV on p_show_info).

---

## 4. Open points for review

1. **New parameter `p_tile_view`** for the All / Needs attention switch. It isn't in the data model doc's parameter table.
2. **"Open since" on the alert list.** The prototype shows "open since 19 Oct" next to an incident, but the incident start time only lives in `fct_incidents`, which a Nodes sheet can't read. Options: add `open_incident_started_at` to `dim_nodes` in `generator/marts.py` (one line, recommended), or drop the phrase.
3. **Nav count badges** (the red and amber counts in the left nav) can't be data-driven on Tableau navigation buttons. Options: leave them out, or build the nav as a sheet. Recommend leaving them out on Health and revisiting with the shared nav.
4. **Text-typed number fields** in the data source, which matter from the Runs and Performance tabs onward: `avg_runtime_sec`, `runtime_7d_avg_sec`, `runtime_prior28d_avg_sec`, `runtime_trend_pct`, `avg_refresh_sec` (Node Daily) and `metrics_called`, `failed_calls` (Exposure Daily). Set them to Number (decimal) in the data source before pasting the later packs.
5. **Zero change** shows as green "● 0 pp" (Good includes zero). The prototype shows a grey "● 0". Exact zero is very rare at two decimals; flag if you want a third, grey field.
6. **Scaffold buttons** borrow the first rows of `dim_date` (`day_index` 0 to 3). It's a standard trick, but if you prefer, a 4-row `dim_buttons.csv` in the marts would be cleaner.
