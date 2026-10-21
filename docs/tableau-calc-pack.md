# Lineage Control Tower: Tableau calc pack

Phase 4, step 1. Product style mode (portfolio). Source of truth for layout: `mockup/lineage-control-tower.html`. Data model: `docs/tableau-data-model.md`.

Status: **Complete for all 9 tabs plus About.** Health was reviewed on 21 Oct 2026; the decisions from that review are in section 13. Paste-ready parameter lists are in `docs/tableau-parameter-lists.md`.

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
| `p_lineage_view` | String | List: Graph "Graph", Table "Table" | Graph | LIN View Buttons | Lineage graph / table DZV |

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
| GL Period Buttons | dim_date | Text on a Square, Columns: Period Option Label | Filter Period Option non-null. Colour: Is Active Period Option (True `#FFFFFF`, False `#F5F5F3`, on a `#F5F5F3` track; text from Period Label Active / Inactive, see 2.9 and build plan 2.4). Tooltip off |
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

### 2.8 Shared helpers used from the Lineage tab onward

```
// As Of Date
// Last day in the data (19 Oct). Every "now" in the dashboard is measured against it.
{ MAX([date (dim_date.csv)]) }
```

```
// Window Start Date
// First day of the selected window. Used for reference bands that shade the window on date axes.
DATEADD('day', 1 - [p_period], [As Of Date])
```

```
// Exposure Type Name
// Display name for the consumer type.
CASE [exposure_type]
WHEN "dashboard" THEN "Dashboard"
WHEN "notebook"  THEN "Notebook"
WHEN "ml"        THEN "ML model"
WHEN "data_app"  THEN "Data app"
WHEN "agent"     THEN "AI agent"
WHEN "data_hub"  THEN "Data hub"
END
```

```
// BI Tool Name
// Display name for the BI tool.
CASE [bi_tool]
WHEN "tableau"  THEN "Tableau"
WHEN "sigma"    THEN "Sigma"
WHEN "power_bi" THEN "Power BI"
END
```

```
// Access Path Label
// How a consumer reaches the data, in the prototype's wording.
CASE [access_path]
WHEN "bi_semantic_layer"  THEN "via BI semantic layer"
WHEN "direct_warehouse"   THEN "direct to warehouse"
WHEN "dbt_semantic_layer" THEN "via dbt semantic layer"
WHEN "mcp_server"         THEN "via MCP server"
WHEN "extract"            THEN "via extract"
END
```

```
// Last Event Label
// The prototype's timestamp format: "19 Oct, 21:25". "-" when the node has never run or been checked.
IF ISNULL([last_event_at]) THEN "-"
ELSE STR(DAY([last_event_at])) + " "
    + LEFT(DATENAME('month', [last_event_at]), 3) + ", "
    + RIGHT("0" + STR(DATEPART('hour', [last_event_at])), 2) + ":"
    + RIGHT("0" + STR(DATEPART('minute', [last_event_at])), 2)
END
```

```
// Last Runtime Label
// Last model runtime in the prototype's duration format: "45s", "27.9 min" or "1.2 h".
IF ISNULL([last_runtime_sec]) THEN ""
ELSEIF [last_runtime_sec] < 60 THEN STR(ROUND([last_runtime_sec])) + "s"
ELSEIF [last_runtime_sec] < 3600 THEN STR(ROUND([last_runtime_sec] / 60, 1)) + " min"
ELSE STR(ROUND([last_runtime_sec] / 3600, 1)) + " h"
END
```

```
// Lag Now Label
// Current source lag: "45 min" under an hour, otherwise "6.0 h".
IF ISNULL([freshness_lag_min]) THEN ""
ELSEIF [freshness_lag_min] < 60 THEN STR(ROUND([freshness_lag_min])) + " min"
ELSE STR(ROUND([freshness_lag_min] / 60, 1)) + " h"
END
```

```
// Daily Consumers (Period)
// An exposure's average daily consumers for the selected period. Pre-computed per period in dim_nodes,
// because it is an exposure-level average needed inside node-level views.
CASE [p_period]
WHEN 7  THEN [avg_daily_consumers_7d]
WHEN 30 THEN [avg_daily_consumers_30d]
ELSE [avg_daily_consumers_90d]
END
```

```
// Downstream Consumers (Period)
// Average daily consumers of every exposure a node feeds, for the selected period. Added to dim_nodes for the risk score.
CASE [p_period]
WHEN 7  THEN [downstream_consumers_7d]
WHEN 30 THEN [downstream_consumers_30d]
ELSE [downstream_consumers_90d]
END
```

```
// Worst Test Label
// Worst test result of a model on a day (Node Daily). Palette: No run #EFEFEB, All passed #E3F2E9,
// Warning #E8A33D, Failed #D2453F. The Lineage panel strip uses the strong green #2F9E6B for All passed instead.
CASE [worst_test_code]
WHEN 3 THEN "Failed"
WHEN 2 THEN "Warning"
WHEN 1 THEN "All passed"
ELSE "No run"
END
```

```
// Platform On Day Name
// Display name of the platform a node was on that day (Node Daily). Colours: Snowflake #005FAE, Databricks #4BAEE3, Redshift #5B5FC7.
CASE [platform_on_day]
WHEN "snowflake"  THEN "Snowflake"
WHEN "databricks" THEN "Databricks"
WHEN "redshift"   THEN "Redshift"
END
```

---

### 2.9 Shell calcs added in the build (21 Oct)

Added by `tableau/tools/build_workbook.py` for the shared shell (build plan 2.4 and 2.5). The two label fields per button give the active and inactive text their own colours, because a label can't change colour per mark.

```
// Is Period Button Row
// Keeps the 3 scaffold rows that carry a period button. Put on Filters (True).
NOT ISNULL([Period Option])
```

```
// Period Label Active
// Button text when this button is the selected period (Semibold Navy run).
IF [Is Active Period Option] THEN [Period Option Label] ELSE "" END
```

```
// Period Label Inactive
// Button text when this button is not selected (Book grey run).
IF NOT [Is Active Period Option] THEN [Period Option Label] ELSE "" END
```

```
// Is Platform Button Row
// Keeps the 4 scaffold rows that carry a platform button. Put on Filters (True).
NOT ISNULL([Platform Option])
```

```
// Platform Label Active
// Button text when this button is the selected platform (Semibold Navy run).
IF [Is Active Platform Option] THEN [Platform Option Label] ELSE "" END
```

```
// Platform Label Inactive
// Button text when this button is not selected (Book grey run).
IF NOT [Is Active Platform Option] THEN [Platform Option Label] ELSE "" END
```

```
// Platform Dot Snowflake
// Coloured square before "Snowflake" on its button. Each platform has its own field so each gets its own run colour.
IF [Platform Option] = "snowflake" THEN "■  " ELSE "" END
```

```
// Platform Dot Databricks
// Coloured square before "Databricks" on its button.
IF [Platform Option] = "databricks" THEN "■  " ELSE "" END
```

```
// Platform Dot Redshift
// Coloured square before "Redshift" on its button.
IF [Platform Option] = "redshift" THEN "■  " ELSE "" END
```

```
// Platform Option Order
// Keeps the platform buttons in prototype order (All, Snowflake, Databricks, Redshift) instead of A to Z.
[day_index]
```

```
// Is Info Button Row
// One scaffold row for the single-mark info button. Put on Filters (True).
[day_index] = 0
```

```
// Info Button Glyph
// The header icon: "ⓘ" opens the info panel, "✕" closes it.
IF [p_show_info] THEN "✕" ELSE "ⓘ" END
```

```
// Show Info Panel
// DZV for GL Info Panel: shown while p_show_info is True.
[p_show_info]
```

```
// Data Updated Date Text
// The date part of the header stamp, shown bold after "Data updated on ".
STR(DAY({ MAX([date (dim_date.csv)]) })) + " "
+ LEFT(DATENAME('month', { MAX([date (dim_date.csv)]) }), 3) + " "
+ STR(YEAR({ MAX([date (dim_date.csv)]) }))
+ ", 23:59"
```

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
    THEN " at " + [Last Event Label]
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

```
// Attention Open Since
// Tail of the meta line: " · open since 19 Oct". Uses open_incident_started_at, added to dim_nodes for this.
IF ISNULL([open_incident_started_at]) THEN ""
ELSE " · open since " + STR(DAY([open_incident_started_at])) + " "
    + LEFT(DATENAME('month', [open_incident_started_at]), 3)
END
```

Build: Rows `Attention Sort` (discrete, sorted descending, hidden), `node_id (dim_nodes.csv)` (hidden); Gantt bar or Square mark full width, colour **Status Tint Key**. Label: `Status Icon` (coloured per status through three split fields, as for the tiles, or a separate Shape column coloured by Status Label) / `display_name` (Semibold) + `Attention Incident Tag` / `Attention Reason` / `Attention Meta` + `Attention Open Since` (with the "affects N exposures" part bold, which needs it in its own field if you want the weight change). Filters: Is Attention Node, Is Platform Match Node. Empty state: a text object "Nothing needs attention right now." behind the sheet.

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

## 4. Lineage explorer (`LIN`)

Title "What feeds this data product, and is every step healthy?". Layout: a graph card (left) with the exposure picker, trust pill, access line and a Graph / Table switch, and a 340 px node panel (right).

**Parameters:** p_selected_exposure (shown as a dropdown, values pasted from `docs/tableau-parameter-lists.md`), p_selected_node, p_selected_node_key, and new **`p_lineage_view`** (string, list Graph / Table, default Graph).

### 4.1 Sheets and base tables

| # | Sheet | Base table | Shows |
|---|---|---|---|
| 1 | LIN Exposure Header | Nodes | Trust pill and "Dashboard in Tableau, via BI semantic layer · 61 upstream nodes" |
| 2 | LIN View Buttons | Dates | Graph / Table switch (scaffold) |
| 3 | LIN Lineage Graph | Lineage Layout | Edges (line) and node boxes (Gantt), dual axis |
| 4 | LIN Lineage Table | Blast Radius | Table mode: every upstream node of the exposure |
| 5 | LIN Panel Header | Nodes | Layer · type, name, pills, callout |
| 6 | LIN Panel Details | Nodes (+ Owners) | Owner, team, Slack, project, schema, documented, tests defined |
| 7 | LIN Panel Runtime Trend | Node Daily | Models: runtime per day, 90 days, plus last run and 7d vs 28d |
| 8 | LIN Panel Runs Summary | Node Daily | Models: runs and failures in the period |
| 9 | LIN Panel Test Strip | Node Daily | Models: worst test result per day, last 30 days |
| 10 | LIN Panel Freshness Bullet | Nodes | Sources: lag now against warn and error |
| 11 | LIN Panel Lag Trend | Node Daily | Sources: worst lag per day |
| 12 | LIN Panel Refresh Summary | Node Daily | Semantic objects: refreshes in period and failures per day |
| 13 | LIN Panel Health Score Trend | Exposure Daily | Exposures: health score, 90 days |
| 14 | LIN Panel Usage Summary | Exposure Daily | Exposures: usage, daily consumers, cost, cost per use |
| 15 | LIN Trace Impact Button | Nodes | "Trace downstream impact" (non-exposures) |
| 16 | LIN See Usage Button | Nodes | "See usage and cost" (exposures) |

No sheet mixes two fact tables. The panel is split into one small sheet per source table, shown or hidden by node type.

### 4.2 Graph (Lineage Layout)

```
// Is Lineage Scope
// Keeps the per-exposure layout of the selected exposure. Put on Filters (True).
[layout_scope] = [p_selected_exposure]
```

```
// Node Y
// Vertical position of node boxes. Reverse this axis: smaller y sits at the top, as in the prototype.
IF [row_type] = "node" THEN [y] END
```

```
// Edge Y
// Vertical position of edge points. Same axis range as Node Y, so the two can be synchronised.
IF [row_type] = "edge" THEN [y] END
```

```
// Node Box Width
// Boxes span 0.8 of a layer column, which is where the mart starts and ends every edge. Put on Size of the Gantt card.
IF [row_type] = "node" THEN 0.8 END
```

```
// Selected Reach Keys
// |key|key| list of every node on the selected node's path (itself, everything upstream and downstream)
// in this exposure's layout. NULL when the selected node is not in this graph.
{ FIXED [layout_scope] :
    MAX(IF [row_type] = "node"
        AND [node_key (mart_lineage_layout.csv)] = [p_selected_node_key]
        THEN [reach_keys] END) }
```

```
// Has Path Selection
// TRUE when the clicked node is part of this exposure's graph. Otherwise nothing is faded.
NOT ISNULL([Selected Reach Keys])
```

```
// Is On Path Node
// TRUE for boxes on the selected path, or for every box when nothing is selected.
IF NOT [Has Path Selection] THEN TRUE
ELSE CONTAINS([Selected Reach Keys], "|" + STR([node_key (mart_lineage_layout.csv)]) + "|")
END
```

```
// Is On Path Edge
// TRUE when both ends of an edge are on the selected path. Like the prototype, an edge that jumps from an
// upstream node straight to a downstream node also lights up; that case is rare in this graph.
IF NOT [Has Path Selection] THEN TRUE
ELSE CONTAINS([Selected Reach Keys], "|" + STR([node_key (mart_lineage_layout.csv)]) + "|")
    AND CONTAINS([Selected Reach Keys], "|" + STR([child_key]) + "|")
END
```

```
// Edge Colour Key
// Edge rows carry the parent's node_id, so dim_nodes gives the parent's status: a failing parent turns its edges red or amber.
// Palette: Faded #EEF0F2, Critical #D2453F, Warning #E8A33D, On path #005FAE, Default #CBD0D5.
IF NOT [Is On Path Edge] THEN "Faded"
ELSEIF [current_status_code] = 3 THEN "Critical"
ELSEIF [current_status_code] = 2 THEN "Warning"
ELSEIF [Has Path Selection] THEN "On path"
ELSE "Default"
END
```

```
// Node Fill Key
// Box fill: the status tint, or a pale grey when the box is off the selected path.
// Palette: Healthy #FFFFFF, Warning #FDF3E1, Critical #FBEAE9, No data #F1F2F4, Faded #F7F8F6.
IF NOT [Is On Path Node] THEN "Faded"
ELSE [Status Label]
END
```

```
// Is Selected Node Box
// The clicked box, so its name can be bolded.
[node_key (mart_lineage_layout.csv)] = [p_selected_node_key]
```

```
// Node Dot Critical
// Status dot in the box label, in red. One of the four dot fields is filled per box.
IF [row_type] = "node" AND [current_status_code] = 3 THEN "●" ELSE "" END
```

```
// Node Dot Warning
// Status dot, amber.
IF [row_type] = "node" AND [current_status_code] = 2 THEN "●" ELSE "" END
```

```
// Node Dot Healthy
// Status dot, green.
IF [row_type] = "node" AND [current_status_code] = 1 THEN "●" ELSE "" END
```

```
// Node Dot No Data
// Status dot, grey (live semantic objects have nothing to refresh).
IF [row_type] = "node" AND [current_status_code] = 0 THEN "●" ELSE "" END
```

```
// Node Name Label
// Box label without the stg_/int_/raw_ prefix. Empty for the selected box, which uses Node Name Selected (bold).
IF [row_type] = "node" AND NOT [Is Selected Node Box] THEN [display_short] ELSE "" END
```

```
// Node Name Selected
// Bold name for the clicked box (the prototype draws a navy border, which Tableau can't do per mark).
IF [row_type] = "node" AND [Is Selected Node Box] THEN [display_short] ELSE "" END
```

```
// Node Platform Snowflake
// Platform marker at the end of the label, in the Snowflake colour (the prototype's coloured stripe).
IF [row_type] = "node" AND [platform_now] = "snowflake" THEN "▌" ELSE "" END
```

```
// Node Platform Databricks
// Platform marker in the Databricks colour.
IF [row_type] = "node" AND [platform_now] = "databricks" THEN "▌" ELSE "" END
```

```
// Node Platform Redshift
// Platform marker in the Redshift colour (only before the September migration, so empty today).
IF [row_type] = "node" AND [platform_now] = "redshift" THEN "▌" ELSE "" END
```

```
// Node Platform Tooltip
// "Snowflake (moved from Redshift on 3 Sep)" for migrated nodes.
[Platform Name]
+ IF ISNULL([migrated_from_platform]) THEN ""
  ELSE " (moved from " + PROPER([migrated_from_platform]) + " on "
      + STR(DAY([migration_date])) + " " + LEFT(DATENAME('month', [migration_date]), 3) + ")"
  END
```

Build: Columns `AVG([x])`. Rows `Edge Y` and `Node Y`, dual axis, synchronised, both reversed, hidden. Edge card: Line, Path `point_order`, Detail `edge_id`, Colour Edge Colour Key, size thin. Node card: Gantt, Size Node Box Width, Detail `node_id (mart_lineage_layout.csv)` and `node_key (mart_lineage_layout.csv)`, Colour Node Fill Key, mark border `#E6E7E2`. Label (left, middle): the four Node Dot fields (each in its status colour) + Node Name Label (`#16212E`) + Node Name Selected (bold) + the three Node Platform fields (each in its platform colour). Fix X from -0.1 to 5.9 so the six columns always line up with the column headers. The column headers (SOURCES … EXPOSURE) are text objects in a horizontal container above the sheet. Filter: Is Lineage Scope. Tooltip: display_name, LAYER Layer Name, PLATFORM Node Platform Tooltip, STATUS Status Label, LAST RUNTIME Last Runtime Label, LAG NOW Lag Now Label, OWNER owner_name. Turn the edge card's tooltip off.

### 4.3 Graph / Table switch and table mode

```
// Lineage View Option
// Scaffold for the Graph / Table buttons (first 2 days of dim_date). Filter to non-null.
CASE [day_index]
WHEN 0 THEN "Graph"
WHEN 1 THEN "Table"
END
```

```
// Is Active Lineage View
// Colours the selected view button.
[Lineage View Option] = [p_lineage_view]
```

```
// Show Lineage Graph
// DZV for the graph container.
[p_lineage_view] = "Graph"
```

```
// Show Lineage Table
// DZV for the table container.
[p_lineage_view] = "Table"
```

```
// Is Selected Exposure Upstream Row
// Table mode keeps the Blast Radius rows of the selected exposure: one row per upstream node, with its hop count.
[exposure_id (mart_blast_radius.csv)] = [p_selected_exposure]
```

```
// Runtime Or Lag Label
// Table column "Runtime": last runtime for models, current lag for sources.
IF NOT ISNULL([last_runtime_sec]) THEN [Last Runtime Label]
ELSEIF NOT ISNULL([freshness_lag_min]) THEN "lag " + [Lag Now Label]
ELSE ""
END
```

```
// Tests Pass Text
// "12 pass" in grey. Blank for nodes without tests.
IF ISNULL([tests_passing]) THEN "" ELSE STR([tests_passing]) + " pass" END
```

```
// Tests Fail Text
// " · 1 fail" in red.
IF [tests_failing] > 0 THEN " · " + STR([tests_failing]) + " fail" ELSE "" END
```

```
// Tests Warn Text
// " · 1 warn" in amber ink.
IF [tests_warning] > 0 THEN " · " + STR([tests_warning]) + " warn" ELSE "" END
```

Table build (base Blast Radius, filter Is Selected Exposure Upstream Row): Rows `layer_column` (hidden, ascending), `Status Severity Sort` (hidden), `node_name`, `Layer Name`, `Platform Name`, `Status Icon` + `Status Label`, `hops`, `Last Event Label`, `Runtime Or Lag Label`, then a text mark carrying the three Tests fields and `owner_name`. Every column is a discrete dimension, so it is a pure text table. Row click sets p_selected_node / p_selected_node_key, the same as the graph.

### 4.4 Exposure header (Nodes)

```
// Exposure Access Line
// Subtitle beside the picker: "Dashboard in Tableau, via BI semantic layer · 61 upstream nodes".
[Exposure Type Name]
+ IF ISNULL([bi_tool]) THEN "" ELSE " in " + [BI Tool Name] END
+ ", " + [Access Path Label]
+ " · " + STR([upstream_node_count]) + " upstream nodes"
```

Filter: Is Selected Exposure. Label: the Tile Trust fields from 3.9 (re-used) + Exposure Access Line.

### 4.5 Node panel

```
// Panel Node Id
// Node shown in the side panel: the clicked node, or the exposure itself until a node is clicked.
IF [p_selected_node] = "" THEN [p_selected_exposure]
ELSE [p_selected_node]
END
```

```
// Is Panel Node
// Filter for every Nodes-based panel sheet.
[node_id (dim_nodes.csv)] = [Panel Node Id]
```

```
// Is Panel Node Daily
// Filter for the Node Daily panel sheets (row-level compare on the fact's own key).
[node_id] = [Panel Node Id]
```

```
// Is Panel Exposure Daily
// Filter for the Exposure Daily panel sheets.
[exposure_id] = [Panel Node Id]
```

```
// Panel Resource Type
// The panel node's type, identical on every row, so dynamic zone visibility can read it.
{ MAX(IF [node_id (dim_nodes.csv)] = [Panel Node Id] THEN [resource_type] END) }
```

```
// Show Panel Model
// DZV: runtime, runs and test strip sections.
[Panel Resource Type] = "model"
```

```
// Show Panel Source
// DZV: freshness bullet and lag trend.
[Panel Resource Type] = "source"
```

```
// Show Panel Semantic
// DZV: refresh summary.
[Panel Resource Type] = "semantic"
```

```
// Show Panel Exposure
// DZV: health score and usage, plus the "See usage and cost" button instead of "Trace downstream impact".
[Panel Resource Type] = "exposure"
```

```
// Panel Kind Line
// Small line above the panel title: "Staging · view", "BI semantic layer · published_data_source", "Exposures · Dashboard".
[Layer Name] + " · "
+ IF [resource_type] = "exposure" THEN [Exposure Type Name]
  ELSE IFNULL([materialization], IFNULL([semantic_object_type], [resource_type]))
  END
```

```
// Panel Callout
// What is wrong, under the pills. Exposures list their culprit nodes; other nodes show the reason and the raw error.
IF [current_status_code] < 2 THEN ""
ELSEIF [resource_type] = "exposure" THEN [culprit_nodes]
ELSE [status_reason] + IF ISNULL([last_error_message]) THEN "" ELSE CHAR(10) + [last_error_message] END
END
```

```
// Panel Moved Tag
// "moved from Redshift on 3 Sep" pill text for migrated nodes.
IF ISNULL([migrated_from_platform]) THEN ""
ELSE "moved from " + PROPER([migrated_from_platform]) + " on "
    + STR(DAY([migration_date])) + " " + LEFT(DATENAME('month', [migration_date]), 3)
END
```

```
// Panel Registered Tag
// "Not registered" pill for consumers found only in query history.
IF [is_declared] THEN "" ELSE "Not registered" END
```

```
// Documented Label
// Panel row "Documented".
IF [has_description] THEN "Yes" ELSE "No description" END
```

```
// Tests Defined Label
// Panel row "Tests defined", models only. "None" is shown in amber ink.
IF [resource_type] <> "model" THEN ""
ELSEIF [test_count] = 0 THEN "None"
ELSE STR([test_count])
END
```

```
// Runtime Trend Now
// 7-day vs prior 28-day runtime change on the last day (19 Oct), as a fraction. Format ▲ 0%;▼ 0%.
// Needs runtime_trend_pct typed as Number (decimal) in the data source.
MAX(IF [days_before_as_of] = 0 THEN [runtime_trend_pct] END)
```

```
// Runtime Trend Up
// Runtime up more than 25%: red.
IF [Runtime Trend Now] > 0.25 THEN [Runtime Trend Now] END
```

```
// Runtime Trend Down
// Runtime down more than 25%: green.
IF [Runtime Trend Now] < -0.25 THEN [Runtime Trend Now] END
```

```
// Runtime Trend Flat
// Within ±25%: neutral ink.
IF [Runtime Trend Now] >= -0.25 AND [Runtime Trend Now] <= 0.25 THEN [Runtime Trend Now] END
```

```
// Runtime Minutes (Daily)
// Panel runtime line, in minutes. Needs avg_runtime_sec typed as Number.
AVG([avg_runtime_sec]) / 60
```

```
// Runs In Period
// Model runs in the window (skipped excluded, as in the mart).
SUM(IF [In Period] THEN [runs] END)
```

```
// Failed Runs In Period
// Failed model runs in the window. Shown red when above 0, green at 0.
ZN(SUM(IF [In Period] THEN [runs_failed] END))
```

```
// Worst Lag Hours (Daily)
// Source panel line: worst lag of the day, in hours.
MAX([max_lag_min]) / 60
```

```
// Refreshes OK In Period
// Successful extract refreshes in the window.
ZN(SUM(IF [In Period] THEN [refresh_ok] END))
```

```
// Refreshes Failed In Period
// Failed extract refreshes in the window.
ZN(SUM(IF [In Period] THEN [refresh_failed] END))
```

```
// Refreshes Skipped In Period
// Refreshes skipped because an upstream mart failed.
ZN(SUM(IF [In Period] THEN [refresh_skipped] END))
```

```
// Product Uses (Period)
// An exposure's consumption events in the window (views, queries, sessions or calls).
SUM(IF [In Period] THEN [events] END)
```

```
// Product Cost (Period)
// Allocated cost in the window: upstream build cost split across the exposures each model feeds, plus own queries.
SUM(IF [In Period] THEN [allocated_cost_usd] END)
```

```
// Cost Per Use
// Product Cost / Product Uses. NULL (shown "-") when there was no use.
IF [Product Uses (Period)] = 0 OR ISNULL([Product Uses (Period)]) THEN NULL
ELSE [Product Cost (Period)] / [Product Uses (Period)]
END
```

```
// Daily Consumers In Period
// Mean daily unique consumers over the window (one Exposure Daily row per day).
AVG(IF [In Period] THEN [unique_consumers] END)
```

```
// Uses Unit Label
// Unit after a usage number: views, queries, app sessions or agent calls (Exposure Daily).
CASE [consumption_type (mart_exposure_daily.csv)]
WHEN "view"        THEN "views"
WHEN "query"       THEN "queries"
WHEN "app_session" THEN "app sessions"
WHEN "agent_call"  THEN "agent calls"
END
```

Panel builds: every trend is 300 × 44, line or bar, with In Period on colour or a reference band from Window Start Date to As Of Date. The test strip is Node Daily filtered to `days_before_as_of < 30`, square marks on a continuous date axis, colour Worst Test Label (strong green for All passed here). The freshness bullet re-uses the Freshness tab calcs (8.1).

### 4.6 Lineage actions

| Action | Type | Source | Target | Field | Run on |
|---|---|---|---|---|---|
| LIN Select Node | Parameter | LIN Lineage Graph, LIN Lineage Table | p_selected_node | node_id (mart_lineage_layout.csv) / node_id (mart_blast_radius.csv) | Select, keep value on clear |
| LIN Select Node Key | Parameter | same | p_selected_node_key | node_key (mart_lineage_layout.csv) / node_key | Select |
| LIN Set View | Parameter | LIN View Buttons | p_lineage_view | Lineage View Option | Select |
| LIN Trace Impact | Go to sheet | LIN Trace Impact Button | Blast radius dashboard | | Select |
| LIN See Usage | Go to sheet | LIN See Usage Button | Usage dashboard | | Select |

The p_selected_exposure dropdown is a parameter control. Changing it does not clear p_selected_node (a control can't fire an action), so the panel keeps the last clicked node until another box is clicked. Clicking the exposure's own box brings the exposure back into the panel.

---

## 5. Blast radius (`BR`)

Title "If this breaks, who do I need to tell?". Layout: a header card across the top (node picker, pills, summary sentence, five count chips, incident message), then Who to tell (left) and Downstream path (right), then Riskiest nodes across the bottom (300 px).

**Parameters:** p_selected_node (dropdown, values from `docs/tableau-parameter-lists.md`), p_selected_node_key.

### 5.1 Sheets and base tables

| # | Sheet | Base table | Shows |
|---|---|---|---|
| 1 | BR Node Header | Nodes | Status, platform and layer pills for the selected node |
| 2 | BR Impact Summary | Blast Radius | "If X breaks, N data products and about M daily consumers are affected" + issue line |
| 3 | BR Reach Counts | Node Reach | Chips: downstream models, BI semantic objects |
| 4 | BR Exposure Counts | Blast Radius | Chips: exposures, owners to notify |
| 5 | BR Unregistered Count | Observed Access | Chip: unregistered readers (red when above 0) |
| 6 | BR Incident Message | Blast Radius | Selectable message text + email action |
| 7 | BR Who To Tell Table | Blast Radius | Affected exposures, owners, Slack, consumers, trust |
| 8 | BR Unregistered Callout | Observed Access | "Not on this list: svc_shared_analytics …" |
| 9 | BR No Owner Callout | Blast Radius | "1 affected exposure has no owner to notify" |
| 10 | BR Downstream Path | Node Reach | Models, BI semantic layer and Exposures columns |
| 11 | BR Riskiest Nodes Table | Node Daily | Top 10 by risk score, with a bar |

No sheet mixes two fact tables. The chips are three small sheets in one horizontal container, because they come from three tables.

### 5.2 Selected node impact (Blast Radius)

```
// Is Selected Node Impact Row
// Keeps the Blast Radius rows for the selected node: one row per exposure it feeds.
[node_id (mart_blast_radius.csv)] = [p_selected_node]
```

```
// Exposure Daily Consumers (Period)
// The fed exposure's average daily consumers for the selected period (pre-computed in the mart).
CASE [p_period]
WHEN 7  THEN [avg_daily_consumers_7d (mart_blast_radius.csv)]
WHEN 30 THEN [avg_daily_consumers_30d (mart_blast_radius.csv)]
ELSE [avg_daily_consumers_90d (mart_blast_radius.csv)]
END
```

```
// Impacted Exposures
// Data products the selected node feeds. Check: stg_netsuite__journal_lines feeds 4.
COUNTD([exposure_id (mart_blast_radius.csv)])
```

```
// Impacted Consumers
// Sum of the fed exposures' average daily consumers. Check (30d): stg_netsuite__journal_lines about 42.
SUM([Exposure Daily Consumers (Period)])
```

```
// Owners To Notify
// Distinct owners of the fed exposures, "No owner" excluded.
COUNTD(IF [exposure_owner] <> "No owner" THEN [exposure_owner] END)
```

```
// Impacted Exposures Without Owner
// Fed exposures nobody owns, for the red callout text ("1 affected exposure has no owner to notify").
// Named apart from Governance's Exposures Without Owner, which counts on dim_nodes.
COUNTD(IF [exposure_owner] = "No owner" THEN [exposure_id (mart_blast_radius.csv)] END)
```

```
// Impact Lead
// First run of the summary sentence: "If stg_netsuite__journal_lines breaks, ".
"If " + ATTR([node_name]) + " breaks, "
```

```
// Impact Products Text
// Bold run: "4 data products".
STR([Impacted Exposures])
+ IF [Impacted Exposures] = 1 THEN " data product" ELSE " data products" END
```

```
// Impact Consumers Text
// Bold run: "42 daily consumers". The label editor adds " and about " before it and " are affected." after it.
STR(ROUND([Impacted Consumers])) + " daily consumers"
```

```
// Impact Issue Line
// Grey line under the sentence: what is wrong now, or a reminder to use the view before a change.
IF MIN([current_status_code]) >= 2 THEN ATTR([status_reason])
ELSE "Currently healthy. Use this view before changing or deprecating it."
END
```

```
// Incident Message
// Ready-to-send text for the selectable box and the email action. Tableau can't write to the clipboard,
// so the full exposure list stays in the Who to tell table.
"Heads up: " + ATTR([node_name])
+ " (" + LOWER(ATTR([Layer Name])) + ", " + ATTR([Platform Name]) + ") "
+ IF MIN([current_status_code]) >= 2
    THEN "has an issue: " + LOWER(ATTR([status_reason]))
  ELSE "is being changed"
  END
+ ". It feeds " + [Impact Products Text]
+ " used by about " + STR(ROUND([Impacted Consumers]))
+ " people, apps or agents a day. Treat these numbers with caution until we confirm the fix."
```

URL action **BR Email Incident Message**: `mailto:?subject=Heads up: <ATTR(node_name)>&body=<Incident Message>`, with URL-encode data values on. Show the message in the sheet with selectable text (tooltip off).

### 5.3 Who to tell (Blast Radius)

```
// Impact Exposure Type
// Type column: the BI tool for dashboards, otherwise the consumer type.
IF NOT ISNULL([bi_tool (mart_blast_radius.csv)]) THEN
    CASE [bi_tool (mart_blast_radius.csv)]
    WHEN "tableau"  THEN "Tableau"
    WHEN "sigma"    THEN "Sigma"
    WHEN "power_bi" THEN "Power BI"
    END
ELSE
    CASE [exposure_type (mart_blast_radius.csv)]
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
// Impact Owner Text
// Owner column, grey. Empty when there is no owner.
IF [exposure_owner] <> "No owner" THEN [exposure_owner] ELSE "" END
```

```
// Impact Owner Missing Text
// "No owner" in red bold.
IF [exposure_owner] = "No owner" THEN "No owner" ELSE "" END
```

```
// Impact Slack Text
// Slack channel, or "-" when the exposure has no owner.
IFNULL([slack_channel (mart_blast_radius.csv)], "-")
```

```
// Impact Trust Critical
// Status column with icon, red.
IF [exposure_status] = "Critical" THEN "✕ " + [exposure_trust] ELSE "" END
```

```
// Impact Trust Warning
// Status column with icon, amber ink.
IF [exposure_status] = "Warning" THEN "▲ " + [exposure_trust] ELSE "" END
```

```
// Impact Trust Healthy
// Status column with icon, green ink.
IF [exposure_status] = "Healthy" THEN "✓ " + [exposure_trust] ELSE "" END
```

Build: Rows `exposure_name` (sorted by SUM of Exposure Daily Consumers (Period), descending), `Impact Exposure Type`, then a text mark with the owner fields, Impact Slack Text, Exposure Daily Consumers (Period) (format `0.0`) and the three trust fields. Filter: Is Selected Node Impact Row. Click: p_selected_exposure ← exposure_id (mart_blast_radius.csv), then go to Lineage.

### 5.4 Downstream path (Node Reach)

```
// Is Selected Node Downstream Row
// Everything built on the selected node.
[node_id (mart_node_reach.csv)] = [p_selected_node]
AND [direction] = "downstream"
```

```
// Downstream Models
// Chip: models downstream of the selected node.
COUNTD(IF [related_resource_type] = "model" THEN [related_node_id] END)
```

```
// Downstream Semantic Objects
// Chip: BI semantic objects downstream of the selected node.
COUNTD(IF [related_resource_type] = "semantic" THEN [related_node_id] END)
```

```
// Reach Column Label
// The three path columns.
CASE [related_resource_type]
WHEN "model"    THEN "Models"
WHEN "semantic" THEN "BI semantic layer"
WHEN "exposure" THEN "Exposures"
END
```

```
// Reach Column Header
// Column header with its count, for example "MODELS   23". FIXED on the selected node's rows, so it ignores row caps.
UPPER([Reach Column Label]) + "   "
+ STR({ FIXED [node_id (mart_node_reach.csv)], [direction], [related_resource_type] :
    COUNTD([related_node_id]) })
```

```
// Reach Row
// Row number inside each column, models in layer order then by name. Table calc: compute using related_name,
// restart every Reach Column Label, sort by MIN(related_layer_column) then related_name. Make it discrete.
INDEX()
```

```
// Reach Row Cap
// Shows the first 12 per column, as in the prototype. Table calc filter (True).
INDEX() <= 12
```

```
// Reach Dot Critical
// Status dot for the path list, red. Four split fields, as for the tiles.
IF [related_status] = "Critical" THEN "●" ELSE "" END
```

```
// Reach Dot Warning
// Status dot, amber.
IF [related_status] = "Warning" THEN "●" ELSE "" END
```

```
// Reach Dot Healthy
// Status dot, green.
IF [related_status] = "Healthy" THEN "●" ELSE "" END
```

```
// Reach Dot No Data
// Status dot, grey.
IF [related_status] = "No data" THEN "●" ELSE "" END
```

Build: Columns `Reach Column Header` (sorted Models, BI semantic layer, Exposures). Rows `Reach Row`. Text mark: the four dots + `related_name`. Filters: Is Selected Node Downstream Row, related_resource_type in model / semantic / exposure, Reach Row Cap.

### 5.5 Unregistered readers (Observed Access)

```
// Selected Downstream Keys
// Every node downstream of the selected node, from dim_nodes (downstream_keys was added to the mart for this).
{ MAX(IF [node_id (dim_nodes.csv)] = [p_selected_node] THEN [downstream_keys] END) }
```

```
// Reads Selected Or Downstream
// TRUE when a query-history row reads the selected node or anything built on it.
[node_id (mart_observed_access.csv)] = [p_selected_node]
OR CONTAINS([Selected Downstream Keys], "|" + STR([node_key]) + "|")
```

```
// Principal Has Mapping In Period
// TRUE when any of the principal's reads in the window is mapped to a declared exposure (or a BI semantic object).
{ FIXED [principal] : MAX(IF [In Period] AND [is_registered] THEN 1 ELSE 0 END) } = 1
```

```
// Is Unregistered Read In Period
// A read in the window by a principal no declared exposure accounts for.
[In Period]
AND NOT [Principal Has Mapping In Period]
AND [query_count] > 0
```

```
// Unregistered Readers
// Chip and callout: distinct unregistered principals reading the selected node or anything downstream of it.
COUNTD(IF [Is Unregistered Read In Period] AND [Reads Selected Or Downstream] THEN [principal] END)
```

The callout sheet lists `principal` (rows) with the same filters, followed by the text "also read this data but are not registered as an exposure, so nobody would be told. See Governance." Its container is hidden by the DZV calc below when the count is 0.

```
// Show Unregistered Callout
// DZV for the amber callout under Who to tell.
{ COUNTD(IF [Is Unregistered Read In Period] AND [Reads Selected Or Downstream]
    THEN [principal] END) } > 0
```

```
// Show No Owner Callout
// DZV for the red callout: shown when any fed exposure has no owner.
{ COUNTD(IF [node_id (mart_blast_radius.csv)] = [p_selected_node]
    AND [exposure_owner] = "No owner"
    THEN [exposure_id (mart_blast_radius.csv)] END) } > 0
```

### 5.6 Riskiest nodes (Node Daily)

```
// Is Risk Candidate Node
// Sources, models and BI semantic objects can fail; exposures can't, so they are left out.
[resource_type] IN ("source", "model", "semantic")
```

```
// Failure Rate (Period)
// Models: failed runs / runs. Sources: days past the error threshold / days checked.
// Semantic objects: failed refreshes / refreshes. As in the prototype.
IF ATTR([resource_type]) = "model" THEN
    SUM(IF [In Period] THEN [runs_failed] END)
    / SUM(IF [In Period] THEN [runs] END)
ELSEIF ATTR([resource_type]) = "source" THEN
    SUM(IF [In Period] AND [fresh_checks_error] > 0 THEN 1 END)
    / SUM(IF [In Period] AND [fresh_checks_pass] + [fresh_checks_warn] + [fresh_checks_error] > 0 THEN 1 END)
ELSEIF ATTR([resource_type]) = "semantic" THEN
    SUM(IF [In Period] THEN [refresh_failed] END)
    / SUM(IF [In Period] THEN [refresh_ok] + [refresh_failed] END)
END
```

```
// Risk Score
// Daily downstream consumers × failure rate. 30d check: pds_commerce_sales 3.25 (story 6), raw_stripe.payments 3.18 (story 5).
ZN([Failure Rate (Period)]) * MIN([Downstream Consumers (Period)])
```

```
// Risk Rank
// Rank by risk score. Table calc: compute using node_id, sort by Risk Score descending. Discrete, shown as "#1".
INDEX()
```

```
// Risk Top 10 Filter
// Keeps the 10 riskiest nodes with a score above 0. Table calc filter (True).
INDEX() <= 10 AND [Risk Score] > 0
```

Build: Rows `Risk Rank` (format `"#"0`), `node_name`, `Layer Name`, `Platform Name`, `exposures_fed`, `Downstream Consumers (Period)` (all discrete), `Failure Rate (Period)` as a discrete measure (format `0.0%`). Columns: Risk Score as a bar (accent `#005FAE`, label `0.0`), plus `Status Icon` / `Status Label` on a dual text axis for the "Now" column. Filters: Is Risk Candidate Node, Is Platform Match Node, Risk Top 10 Filter. Click: p_selected_node ← node_id, p_selected_node_key ← node_key (the table re-scopes the page, as in the prototype).

### 5.7 Blast radius actions

| Action | Type | Source | Target | Field | Run on |
|---|---|---|---|---|---|
| BR Pick Risk Node | Parameter | BR Riskiest Nodes Table | p_selected_node | node_id | Select |
| BR Pick Risk Node Key | Parameter | BR Riskiest Nodes Table | p_selected_node_key | node_key | Select |
| BR Open Exposure | Parameter | BR Who To Tell Table | p_selected_exposure | exposure_id (mart_blast_radius.csv) | Select |
| BR Open Lineage | Go to sheet | BR Who To Tell Table | Lineage dashboard | | Select |
| BR Email Incident Message | URL | BR Incident Message | mailto (see 5.2) | Incident Message | Menu |

---

## 6. Run & failures (`RUN`)

Title "What failed, when, why, and how fast did we recover?". Layout: daily failed and skipped bars across the top (220 px), then the job Gantt (left) and Why runs failed (right, 380 px), then Recent errors (left) and MTTR (right).

**Parameters:** p_gantt_date (date, default 19 Oct 2026).

### 6.1 Sheets and base tables

| # | Sheet | Base table | Shows |
|---|---|---|---|
| 1 | RUN Daily Failures Bar | Node Daily | Failed and skipped model runs per day, 90 days |
| 2 | RUN Incident Markers | Incidents | Incident labels on the same date axis |
| 3 | RUN Gantt Day Label | Dates | "Mon 19 Oct 2026" |
| 4 | RUN Gantt Prev Button | Dates | ‹ |
| 5 | RUN Gantt Next Button | Dates | › |
| 6 | RUN Job Gantt | Job Runs | Every job run on the selected day, by outcome |
| 7 | RUN Failed Count Label | Run Errors | "50 failed model runs in this period" |
| 8 | RUN Why Failed Bar | Run Errors | Failures by error category |
| 9 | RUN Top Failing Models Bar | Run Errors | Models that failed most (top 7) |
| 10 | RUN Recent Errors Table | Run Errors | Newest first: when, model, category, message |
| 11 | RUN MTTR Rolling Line | Recovery Episodes | Rolling 7-day mean time to recover |

### 6.2 Daily failures (Node Daily) and incident markers (Incidents)

```
// Skipped Runs (Daily)
// Grey stack: models skipped because a parent failed. Failed runs re-use Run Success - Trend.
SUM([runs_skipped])
```

```
// Is Gantt Day
// The bar for the day loaded in the Gantt (reference line on the date axis instead of a colour change).
[date (dim_date.csv)] = [p_gantt_date]
```

```
// Incident Marker Label
// "INC 4" above the day an incident started, as in the prototype.
REPLACE([incident_id], "INC-00", "INC ")
```

Build (bars): Columns `date (dim_date.csv)` continuous, fixed 22 Jul to 19 Oct. Rows Measure Values (Run Success - Trend as "Failed", Skipped Runs (Daily) as "Skipped"), stacked bars, colour Measure Names (Failed `#D2453F`, Skipped `#C3C9CF`). Reference band Window Start Date to As Of Date (fill `#E9F1F9`). Reference line on p_gantt_date (`#002C55`, dashed). Filter Is Platform Match Day. Tooltip: date, FAILED, SKIPPED. Click: p_gantt_date ← date (dim_date.csv).

Build (markers): base Incidents. Columns `date (dim_date.csv)` with the **same fixed range**, Text mark of Incident Marker Label at y = 0, height 18 px, placed directly above the bar sheet. Tooltip: incident_id, title.

### 6.3 Job Gantt (Job Runs)

```
// Is Gantt Run
// Job runs that started on the selected day.
[run_date] = [p_gantt_date]
```

```
// Is Platform Match Job
// Platform filter for Job Runs (each run carries the platform most of its models ran on).
[p_platform] = "All"
OR [platform (mart_job_runs.csv)] = [p_platform]
```

```
// Gantt Duration
// Bar length in minutes, at least 3 so very short runs stay visible.
MAX([duration_min], 3)
```

```
// Job Run Outcome
// Bar colour: Succeeded #9DB9D6, Failed #D2453F, Cancelled #C3C9CF.
CASE [status]
WHEN "error"     THEN "Failed"
WHEN "cancelled" THEN "Cancelled"
ELSE "Succeeded"
END
```

```
// Job Schedule Label
// Small grey header beside the job name: "hourly", "daily", "on PR".
REPLACE([schedule], "on_pull_request", "on PR")
```

```
// Tests Failed Marker
// Position of the amber dot just after a run whose tests failed. NULL (no mark) otherwise.
IF [tests_failed] > 0 THEN [start_minute_of_day] + [Gantt Duration] + 4 END
```

```
// Gantt Day Label
// Card header between the arrows: "Mon 19 Oct 2026".
LEFT(DATENAME('weekday', [p_gantt_date]), 3) + " "
+ STR(DAY([p_gantt_date])) + " "
+ LEFT(DATENAME('month', [p_gantt_date]), 3) + " "
+ STR(YEAR([p_gantt_date]))
```

```
// Gantt Prev Date
// Value the ‹ button writes into p_gantt_date. Stops at the first day.
IF [p_gantt_date] > { MIN([date (dim_date.csv)]) }
    THEN DATE(DATEADD('day', -1, [p_gantt_date]))
ELSE [p_gantt_date]
END
```

```
// Gantt Next Date
// Value the › button writes into p_gantt_date. Stops at the last day.
IF [p_gantt_date] < [As Of Date]
    THEN DATE(DATEADD('day', 1, [p_gantt_date]))
ELSE [p_gantt_date]
END
```

Build: Rows `job_name`, `Job Schedule Label`. Columns `start_minute_of_day` (axis fixed 0 to 1440, ticks every 180, custom labels via a format of `00":00"`-style or hide and add 00:00 … 24:00 text) and `Tests Failed Marker`, dual axis, synchronised. Card 1 Gantt, Size Gantt Duration, Colour Job Run Outcome. Card 2 Circle, colour `#E8A33D`, small. Banded rows `#FBFBFA`. Filters: Is Gantt Run, Is Platform Match Job. Tooltip: job_name, PLATFORM, STARTED, DURATION (duration_min), OUTCOME, MODELS RUN / FAILED / SKIPPED, TESTS FAILED. The prev / next button sheets: Dates filtered to day_index = 0, Gantt Prev Date / Gantt Next Date on Detail, text "‹" / "›".

### 6.4 Why runs failed and recent errors (Run Errors)

```
// Is Platform Match Error
// Platform filter for Run Errors: the platform the model ran on when it failed.
[p_platform] = "All"
OR [platform (mart_run_errors.csv)] = [p_platform]
```

```
// Failed Model Runs
// Count of failed model runs. 30d check: 50 (18 compilation, 17 database, 9 permission, 6 timeout).
COUNT([job_run_id])
```

```
// Failed Runs Label
// Card subtitle: "50 failed model runs in this period".
STR([Failed Model Runs]) + " failed model runs in this period"
```

```
// Error Category Label
// Prototype names for the error categories.
CASE [error_category]
WHEN "database"      THEN "Database error"
WHEN "compilation"   THEN "Compilation error"
WHEN "permission"    THEN "Permission denied"
WHEN "timeout"       THEN "Timeout"
WHEN "schema_change" THEN "Schema change"
ELSE [error_category]
END
```

```
// Error Time Label
// "19 Oct, 21:25" for the Recent errors table.
STR(DAY([run_started_at])) + " "
+ LEFT(DATENAME('month', [run_started_at]), 3) + ", "
+ RIGHT("0" + STR(DATEPART('hour', [run_started_at])), 2) + ":"
+ RIGHT("0" + STR(DATEPART('minute', [run_started_at])), 2)
```

```
// Error Message Short
// Message cut to fit one table row. The tooltip shows the full text.
IF LEN([error_message]) > 90 THEN LEFT([error_message], 90) + "…"
ELSE [error_message]
END
```

```
// Recent Error Rank
// Newest first. Table calc: compute using job_run_id and node_id, sorted by MAX(run_started_at) descending.
INDEX()
```

```
// Recent Errors Cap
// The 60 newest errors, as in the prototype. Table calc filter (True).
[Recent Error Rank] <= 60
```

Why failed: Rows Error Category Label (sorted by Failed Model Runs desc), bar Failed Model Runs (`#D2453F`, label). Top failing models: Rows `node_name` (dim_nodes), same bar, Top 7 by Failed Model Runs. Recent errors: Rows Recent Error Rank (hidden), Error Time Label, node_name, Error Category Label, Error Message Short; tooltip carries error_message, job_run_id and "click to trace impact". All three filter on In Period and Is Platform Match Error. Click: p_selected_node ← node_id (mart_run_errors.csv), p_selected_node_key ← node_key, go to Blast radius.

### 6.5 MTTR rolling line (Recovery Episodes)

```
// MTTR Rolling 7 Day
// Mean recovery time of episodes that started in the 7 days up to each day (episode-weighted, as in the prototype).
// Table calc: compute along date (dim_date.csv), with Show Missing Values on so the window counts days, not marks.
WINDOW_SUM(SUM(IF NOT [is_open] THEN [hours_to_recover] END), -6, 0)
/
WINDOW_SUM(COUNT(IF NOT [is_open] THEN [hours_to_recover] END), -6, 0)
```

Build: Columns `date (dim_date.csv)` continuous (Show Missing Values), Rows MTTR Rolling 7 Day, line with area `#005FAE`, reference band for the window, y format `0"h"`. Filter Is Platform Match Day (Episodes).

### 6.6 Run actions

| Action | Type | Source | Target | Field | Run on |
|---|---|---|---|---|---|
| RUN Pick Gantt Day | Parameter | RUN Daily Failures Bar | p_gantt_date | date (dim_date.csv) | Select |
| RUN Gantt Prev | Parameter | RUN Gantt Prev Button | p_gantt_date | Gantt Prev Date | Select |
| RUN Gantt Next | Parameter | RUN Gantt Next Button | p_gantt_date | Gantt Next Date | Select |
| RUN Error Select Node | Parameter | RUN Recent Errors Table | p_selected_node | node_id (mart_run_errors.csv) | Select |
| RUN Error Select Node Key | Parameter | RUN Recent Errors Table | p_selected_node_key | node_key | Select |
| RUN Error Open Blast Radius | Go to sheet | RUN Recent Errors Table | Blast radius dashboard | | Select |

---

## 7. Data quality & tests (`QA`)

Title "Which tests keep failing, and where are we untested?". Layout: four mini KPI cards (96 px), then the heatmap (left) beside a 420 px column: Tests that keep failing, Issues by test type, Test coverage by domain.

### 7.1 Sheets and base tables

| # | Sheet | Base table | Shows |
|---|---|---|---|
| 1 | QA Test Pass KPI | Node Daily | Re-uses Test Pass - Focus / Change from 3.3 |
| 2 | QA Failing Now KPI | Test Daily | Tests failing on the last day, with the first name |
| 3 | QA Tests Run KPI | Node Daily | Tests run in the window |
| 4 | QA Tests Defined Label | Nodes | "166 distinct tests" sub-line |
| 5 | QA Test Coverage KPI | Nodes | Model test coverage, models without tests |
| 6 | QA Test Heatmap | Node Daily | Worst result per model per day |
| 7 | QA Keeps Failing Tests | Test Daily | Top 8 tests with weekday mini bars |
| 8 | QA Issues by Type Bar | Test Daily | Failures and warnings by test type |
| 9 | QA Coverage by Domain Bar | Nodes | Share of models with a test, by domain |

### 7.2 KPI calcs

```
// Is Failing On Last Day
// A test with a failure on 19 Oct (Test Daily only holds non-pass days). Check: 2 tests, as in the prototype.
[days_before_as_of] = 0
AND [fails] > 0
```

```
// Tests Failing Now
// Mini KPI "Failing right now".
COUNTD(IF [Is Failing On Last Day] THEN [test_id] END)
```

```
// First Failing Test Name
// Red sub-line under the KPI: one failing test's name (alphabetical first).
MIN(IF [Is Failing On Last Day] THEN [test_name] END)
```

```
// Tests Run In Period
// Mini KPI "Tests run in period". Format: #,##0.0,"K"
SUM(IF [In Period] THEN [tests_pass] + [tests_warn] + [tests_fail] END)
```

```
// Tests Defined
// Sub-line "N distinct tests": every dbt test defined on a model.
SUM(IF [resource_type] = "model" THEN [test_count] END)
```

```
// Model Test Coverage
// Models with at least one test / all models. Check: 68 of 82 = 83%. Also used on Governance.
ZN(SUM(IF [resource_type] = "model" AND [test_count] > 0 THEN 1 END))
/
SUM(IF [resource_type] = "model" THEN 1 END)
```

```
// Models Without Tests
// Sub-line "14 of 82 models have no tests".
ZN(SUM(IF [resource_type] = "model" AND [test_count] = 0 THEN 1 END))
```

```
// Models In Scope
// Model count for the selected platform, for "of 82" sub-lines.
ZN(SUM(IF [resource_type] = "model" THEN 1 END))
```

### 7.3 Heatmap (Node Daily)

```
// Is In Heatmap Span
// The heatmap always shows at least 30 days, and the full window at 90.
[days_before_as_of] < IIF([p_period] > 30, [p_period], 30)
```

```
// Fail Days In Period
// Days in the window where the model's worst test failed. FIXED so it can filter and sort rows.
{ FIXED [node_id] : SUM(IF [In Period] AND [worst_test_code] = 3 THEN 1 ELSE 0 END) }
```

```
// Warn Days In Period
// Days in the window where the model's worst test only warned.
{ FIXED [node_id] : SUM(IF [In Period] AND [worst_test_code] = 2 THEN 1 ELSE 0 END) }
```

```
// Has Test Issue In Period
// Rows shown: models with any warning or failure in the window.
[Fail Days In Period] + [Warn Days In Period] > 0
```

```
// Heatmap Sort
// Most failure days first, then most warning days.
[Fail Days In Period] * 100 + [Warn Days In Period]
```

```
// Heatmap Fail Text
// Right-hand count in red: "11F".
IF [Fail Days In Period] > 0 THEN STR([Fail Days In Period]) + "F" ELSE "" END
```

```
// Heatmap Warn Text
// Right-hand count in amber ink: "2W".
IF [Warn Days In Period] > 0 THEN " " + STR([Warn Days In Period]) + "W" ELSE "" END
```

Build: Rows `Heatmap Sort` (hidden, descending), `node_name`; Columns `date (dim_date.csv)` continuous; Square marks; Colour Worst Test Label (palette in 2.8). Reference band Window Start Date to As Of Date (outline look: no fill, `#002C55` border), since the prototype outlines the window. Fail and Warn texts as a dual text axis at the right edge (or a second, aligned sheet). Filters: Is In Heatmap Span, Has Test Issue In Period, Is Platform Match Node, resource_type = model. Tooltip only on warning and failure cells: node_name, day, worst result.

### 7.4 Tests that keep failing, issues by type (Test Daily)

```
// Test Fail Days In Period
// Days in the window with a failure, per test.
{ FIXED [test_id] : SUM(IF [In Period] AND [fails] > 0 THEN 1 ELSE 0 END) }
```

```
// Test Warn Days In Period
// Days in the window with a warning (and no failure), per test.
{ FIXED [test_id] : SUM(IF [In Period] AND [fails] = 0 AND [warns] > 0 THEN 1 ELSE 0 END) }
```

```
// Keeps Failing Sort
// Most failure days first, then warnings.
[Test Fail Days In Period] * 100 + [Test Warn Days In Period]
```

```
// Weekday Weight
// Height of a weekday mini bar: 1 for a failure day, 0.5 for a warning day, as in the prototype.
IF [In Period] THEN
    IIF([fails] > 0, 1, 0) + IIF([warns] > 0, 0.5, 0)
END
```

```
// Weekday Initial
// Mini bar axis label: M T W T F S S. Sort by day_of_week from dim_date.
LEFT([day_name], 1)
```

```
// Test Bar Colour
// Red bars for tests that failed, amber for tests that only warned.
IF [Test Fail Days In Period] > 0 THEN "Fail" ELSE "Warn" END
```

```
// Test Fail Text
// "11 fail" in red.
IF [Test Fail Days In Period] > 0 THEN STR([Test Fail Days In Period]) + " fail" ELSE "" END
```

```
// Test Warn Text
// "2 warn" in amber ink, with a separator when both are present.
IF [Test Warn Days In Period] > 0
    THEN IIF([Test Fail Days In Period] > 0, " · ", "") + STR([Test Warn Days In Period]) + " warn"
ELSE ""
END
```

```
// Test Issues In Period
// Issues by test type: failures plus warnings in the window.
SUM(IF [In Period] THEN [fails] + [warns] END)
```

Keeps failing build: Rows `Keeps Failing Sort` (hidden, descending), `test_name`, Test Fail Text + Test Warn Text (headers, coloured), Columns `Weekday Initial` (sorted by day_of_week), bars SUM(Weekday Weight), colour Test Bar Colour. Filters: Top 8 by Keeps Failing Sort (index filter), In Period, Is Platform Match Node. Tooltip: test_name, MODEL node_name, TYPE test_type, COLUMN column_name, SEVERITY severity, FAIL DAYS, WARN DAYS.

Issues by type build: Rows test_type (sorted by Test Issues In Period desc), bar `#E8A33D`, label.

### 7.5 Coverage by domain (Nodes)

Rows `domain` (sorted by Model Test Coverage ascending), bar Model Test Coverage, axis fixed 0 to 1, label `0%`. Filter Is Platform Match Node. Tooltip: MODELS Models In Scope, WITH TESTS (Models In Scope minus Models Without Tests).

---

## 8. Freshness & SLAs (`FR`)

Title "Is the data arriving on time?". Layout: the source bullets fill the left column, Compliance by platform at top right, then Late checks by day and Late right now side by side underneath.

### 8.1 Sheets, base tables and calcs

| # | Sheet | Base table | Shows |
|---|---|---|---|
| 1 | FR Source Lag Bullets | Nodes | Lag now against warn and error, every source |
| 2 | FR Latest Check Label | Nodes | "Latest check 19 Oct, 23:00" in the subtitle |
| 3 | FR Compliance by Platform Line | Node Daily | Share of checks passed per day, per platform |
| 4 | FR Late Checks Calendar | Node Daily | Weekday × week calendar of late checks |
| 5 | FR Late Right Now | Blast Radius | Late sources and the exposures waiting on them |

```
// Is Source
// Keeps raw sources.
[resource_type] = "source"
```

```
// Lag Ratio
// Lag as a share of the source's own error threshold, so every bullet shares one 0 to 1.25 scale.
// Capped at 1.25 so a very late source doesn't squash the others.
MIN([freshness_lag_min] / [error_after_minutes], 1.25)
```

```
// Warn Ratio
// Where the amber zone starts on the shared scale.
[warn_after_minutes] / [error_after_minutes]
```

```
// Lag Sort
// Latest relative to its SLA first, as in the prototype.
[freshness_lag_min] / [error_after_minutes]
```

```
// Lag Value Critical
// Right-hand lag value, red bold.
IF [current_status_code] = 3 THEN [Lag Now Label] ELSE "" END
```

```
// Lag Value Warning
// Right-hand lag value, amber bold.
IF [current_status_code] = 2 THEN [Lag Now Label] ELSE "" END
```

```
// Lag Value Normal
// Right-hand lag value, grey, for sources on time.
IF [current_status_code] < 2 THEN [Lag Now Label] ELSE "" END
```

```
// Latest Check Label
// Subtitle tail: "Latest check 19 Oct, 23:00". Built from MAX of the timestamp, not of the text,
// because "9 Oct" sorts after "19 Oct" as text.
"Latest check "
+ STR(DAY(MAX([last_event_at]))) + " "
+ LEFT(DATENAME('month', MAX([last_event_at])), 3) + ", "
+ RIGHT("0" + STR(DATEPART('hour', MAX([last_event_at]))), 2) + ":"
+ RIGHT("0" + STR(DATEPART('minute', MAX([last_event_at]))), 2)
```

Bullets build: Rows `Lag Sort` (hidden, descending), `node_name`. Columns MIN(Lag Ratio), bar, thin, colour Status Label. Axis fixed 0 to 1.25, hidden. Reference bands per cell: 0 to MIN(Warn Ratio) `#EAF6EF`, MIN(Warn Ratio) to 1 `#FDF3E1`, 1 to 1.25 `#FBEAE9`. Lag Value fields as a dual text axis at 1.3. Filters: Is Source, Is Platform Match Node. Tooltip: LAG NOW, WARN AFTER (warn_after_minutes / 60 h), ERROR AFTER, CHECKED Last Event Label, PLATFORM, FEEDS exposures_fed exposures. The Lineage source panel re-uses this sheet filtered to Is Panel Node.

```
// Freshness Pass Rate (Daily)
// Share of hourly checks that passed that day, per platform. Axis 90% to 100%, as in the prototype.
SUM([fresh_checks_pass])
/
SUM([fresh_checks_pass] + [fresh_checks_warn] + [fresh_checks_error])
```

Compliance build: Columns date continuous, Rows Freshness Pass Rate (Daily), line, colour Platform On Day Name, end labels. Reference band for the window. Axis fixed 0.9 to 1. Filter Is Platform Match Day.

```
// Late Checks (Daily)
// Checks that came back warn or error that day. Shown as the number in each calendar cell.
SUM([fresh_checks_warn] + [fresh_checks_error])
```

```
// Late Checks Label
// Cell number, blank on days with no late checks.
IF [Late Checks (Daily)] > 0 THEN [Late Checks (Daily)] END
```

```
// Late Day Key
// Calendar colour: Error #D2453F, Warn #E8A33D, On time (in window) #E3F2E9, Earlier #EEF0EE.
IF SUM([fresh_checks_error]) > 0 THEN "Error"
ELSEIF SUM([fresh_checks_warn]) > 0 THEN "Warn"
ELSEIF MAX([days_before_as_of]) < [p_period] THEN "On time"
ELSE "Earlier"
END
```

Calendar build: Rows `day_name` sorted by day_of_week (dim_date), Columns `week_start` (discrete), Square marks, colour Late Day Key, label Late Checks Label. Filter Is Platform Match Day. Tooltip: DAY, LATE CHECKS, PAST ERROR THRESHOLD SUM(fresh_checks_error). The prototype outlines today's cell; in Tableau, bold the label on As Of Date instead (or skip).

```
// Is Late Source Row
// Late right now: Blast Radius rows whose upstream node is a source in Warning or Critical today.
[resource_type] = "source"
AND [current_status_code] >= 2
```

Late right now build: Rows `node_name`, `status_reason` (header lines), then `exposure_name` as the tag list (one row each). Filters: Is Late Source Row, Is Platform Match Node. Click an exposure: p_selected_exposure ← exposure_id (mart_blast_radius.csv), go to Lineage. Empty state: text object "Every source is on time."

---

## 9. Performance & cost (`PF`)

Title "What is getting slower and more expensive?". Layout: four mini KPIs (96 px), then Cost by platform (left, 1.45 fr) beside Runtime of the six slowest models (right), then Most expensive models (left) beside What each data product costs (right).

### 9.1 Sheets and base tables

| # | Sheet | Base table | Shows |
|---|---|---|---|
| 1 | PF Warehouse Cost KPI | Node Daily | Re-uses 3.7 |
| 2 | PF Average Per Day KPI | Node Daily | Cost per day, split by platform |
| 3 | PF Slowest Model KPI | Node Daily | Slowest model in the window, average run, 7d vs 28d |
| 4 | PF Incremental Candidates KPI | Node Daily | Open candidates, and the one switched |
| 5 | PF Cost by Platform Bar | Node Daily | Daily cost stacked by platform |
| 6 | PF Slowest Models Runtime Line | Node Daily | Six slowest models, biggest change highlighted |
| 7 | PF Most Expensive Models Table | Node Daily | Top 15 models by cost, with the incremental flag |
| 8 | PF Cost per Data Product Bar | Exposure Daily | Top 12 exposures by allocated cost |

### 9.2 Calcs

```
// Average Cost Per Day
// Mini KPI: window cost divided by the number of days in the window.
[Warehouse Cost - Focus] / [p_period]
```

```
// Cost Per Day Snowflake
// Sub-line part, in the Snowflake colour. NULL when another platform is selected.
SUM(IF [In Period] AND [platform_on_day] = "snowflake"
    THEN [build_cost_usd] + [consumer_query_cost_usd] END) / [p_period]
```

```
// Cost Per Day Databricks
// Sub-line part, in the Databricks colour.
SUM(IF [In Period] AND [platform_on_day] = "databricks"
    THEN [build_cost_usd] + [consumer_query_cost_usd] END) / [p_period]
```

```
// Cost Per Day Redshift
// Sub-line part, in the Redshift colour. NULL in the last 30 days (Redshift was retired on 15 Sep).
SUM(IF [In Period] AND [platform_on_day] = "redshift"
    THEN [build_cost_usd] + [consumer_query_cost_usd] END) / [p_period]
```

```
// Model Avg Runtime (Period)
// Mean of the daily average runtime over the window, in seconds. Needs avg_runtime_sec typed as Number.
// 30d check: fct_sessions about 1,673 s (27.9 min) is the slowest.
AVG(IF [In Period] THEN [avg_runtime_sec] END)
```

```
// Model Runtime Label
// Duration text for an aggregated runtime: "45s", "27.9 min", "1.2 h".
IF ISNULL([Model Avg Runtime (Period)]) THEN "-"
ELSEIF [Model Avg Runtime (Period)] < 60 THEN STR(ROUND([Model Avg Runtime (Period)])) + "s"
ELSEIF [Model Avg Runtime (Period)] < 3600 THEN STR(ROUND([Model Avg Runtime (Period)] / 60, 1)) + " min"
ELSE STR(ROUND([Model Avg Runtime (Period)] / 3600, 1)) + " h"
END
```

```
// Model Cost (Period)
// Build plus consumer query cost of a model in the window.
SUM(IF [In Period] THEN [build_cost_usd] + [consumer_query_cost_usd] END)
```

```
// Is Model
// Keeps dbt models.
[resource_type] = "model"
```

```
// Slowest Model Rank
// Rank by average runtime. Table calc: compute using node_id, sort by Model Avg Runtime (Period) descending.
// The KPI keeps rank 1; the runtime chart uses the PF Slowest 6 Models set instead.
INDEX()
```

```
// Incremental Candidate Day
// A day in the window where the model was a full-refresh table and its runtime trend was above +25%
// (thresholds from generator/config.yaml). Needs runtime_trend_pct typed as Number.
[In Period]
AND [materialization_on_day] = "table"
AND [runtime_trend_pct] > 0.25
```

```
// Is Incremental Candidate
// Candidate at any point in the window, and over 10M rows. Check: only fct_sessions (at 30 days).
{ FIXED [node_id] : MAX(IF [Incremental Candidate Day] THEN 1 ELSE 0 END) } = 1
AND [max_rows_built] > 10000000
```

```
// Is Switched Candidate
// A candidate that has since been made incremental (fct_sessions, 4 Oct).
[Is Incremental Candidate]
AND [materialization_now] = "incremental"
```

```
// Switched On
// First day the model ran as incremental. Only meaningful for switched candidates.
{ FIXED [node_id] : MIN(IF [materialization_on_day] = "incremental" THEN [date] END) }
```

```
// Open Incremental Candidates
// Mini KPI value: candidates not yet switched.
COUNTD(IF [Is Incremental Candidate] AND NOT [Is Switched Candidate] THEN [node_id] END)
```

```
// Switched Candidate Text
// Green sub-line: "fct_sessions switched 4 Oct". With more than one, the sheet lists one row each.
IF [Is Switched Candidate]
    THEN [node_name] + " switched " + STR(DAY([Switched On])) + " " + LEFT(DATENAME('month', [Switched On]), 3)
ELSE ""
END
```

```
// Open Candidate Text
// Red sub-line: candidates still to fix.
IF [Is Incremental Candidate] AND NOT [Is Switched Candidate] THEN [node_name] ELSE "" END
```

```
// Built As Label
// Table column "Built as": "incremental (was table)" for switched candidates.
[materialization_now] + IF [Is Switched Candidate] THEN " (was table)" ELSE "" END
```

```
// Incremental Flag Label
// Last column: "✓ Switched 4 Oct" (green pill) or "▲ Make incremental" (amber pill).
IF [Is Switched Candidate]
    THEN "✓ Switched " + STR(DAY([Switched On])) + " " + LEFT(DATENAME('month', [Switched On]), 3)
ELSEIF [Is Incremental Candidate] THEN "▲ Make incremental"
ELSE ""
END
```

```
// Peak Runtime Trend In Period
// Largest runtime change (either way) a model showed in the window.
{ FIXED [node_id] : MAX(IF [In Period] THEN ABS([runtime_trend_pct]) END) }
```

```
// Is Biggest Runtime Change
// The one line highlighted in accent blue among the six slowest; the rest are grey #B9C0C7.
[Peak Runtime Trend In Period]
= { MAX(IF [PF Slowest 6 Models] THEN [Peak Runtime Trend In Period] END) }
```

**Set PF Slowest 6 Models:** on `node_id (dim_nodes.csv)`, Top 6 by AVG(IF [In Period] THEN [avg_runtime_sec] END). Use it as a filter on the runtime chart.

Builds: cost bars stacked by Platform On Day Name per day, window band, three constant reference lines (3 Sep "HubSpot moves", 11 Sep "Ads move", 4 Oct "fct_sessions fixed" in `#1E7450`). Runtime lines: Runtime Minutes (Daily) by date, colour Is Biggest Runtime Change, size thicker for True, end labels with node_name. Expensive table: Rows (discrete) platform dot (Circle coloured by Platform Name), node_name, Built As Label, Model Runtime Label, Runtime Trend Now (with the Up / Down / Flat split from 4.5), max_rows_built (format `#,##0.0,,"M"`), Model Cost (Period) (bold), Incremental Flag Label; Top 15 by Model Cost (Period). All Node Daily sheets filter Is Platform Match Day, plus Is Model where relevant. Click a model row: p_selected_node, go to Blast radius.

```
// Product Cost Label Tag
// "unregistered" tag after an exposure name in the cost bars.
IF [is_declared] THEN "" ELSE "unregistered" END
```

Cost per data product build (Exposure Daily): Rows `display_name` + Product Cost Label Tag, bar Product Cost (Period) (from 4.5), Top 12. Filter Is Platform Match Node. Tooltip: COST IN PERIOD, USAGE Product Uses (Period) + Uses Unit Label, COST PER USE.

---

## 10. Usage & adoption (`US`)

Title "Which data products earn their keep?". Layout: the cost vs usage scatter (left) beside the consumption small multiples (right) on top (330 px), then the ranked table (left) beside BI semantic layer refreshes (right).

### 10.1 Sheets and base tables

| # | Sheet | Base table | Shows |
|---|---|---|---|
| 1 | US Cost vs Usage Scatter | Exposure Daily | Each data product, log-log, retire zone |
| 2 | US Views Small Multiple | Exposure Daily | Dashboard and hub views per day |
| 3 | US Queries Small Multiple | Exposure Daily | Notebook and model queries per day |
| 4 | US App Sessions Small Multiple | Exposure Daily | Data app sessions per day |
| 5 | US Agent Calls Small Multiple | Exposure Daily | AI agent calls per day |
| 6 | US Ranked Products Table | Exposure Daily | Uses, change, consumers, cost per use, retire flag |
| 7 | US Semantic Refresh Table | Node Daily | Success, failures, average refresh, failures per day |

### 10.2 Calcs

```
// Product Uses Prior
// Uses in the window before. NULL at 90 days.
SUM(IF [In Prior Period] THEN [events] END)
```

```
// Product Uses Change
// Percentage change in uses against the window before.
IF [Product Uses Prior] = 0 OR ISNULL([Product Uses Prior]) THEN NULL
ELSE [Product Uses (Period)] / [Product Uses Prior] - 1
END
```

```
// Uses Change Up
// Rise of more than 10%: green. Format ▲ 0%;▼ 0%.
IF [Product Uses Change] > 0.1 THEN [Product Uses Change] END
```

```
// Uses Change Down
// Fall of more than 10%: red.
IF [Product Uses Change] < -0.1 THEN [Product Uses Change] END
```

```
// Uses Change Flat
// Within ±10%: neutral ink.
IF [Product Uses Change] >= -0.1 AND [Product Uses Change] <= 0.1 THEN [Product Uses Change] END
```

```
// Uses Per 30 Days
// Uses scaled to 30 days, so the retire threshold reads the same at 7, 30 and 90 days.
[Product Uses (Period)] / [p_period] * 30
```

```
// Is Retire Candidate
// Under 10 uses per 30 days AND over $5 per use (or no use at all), declared products only
// (thresholds from generator/config.yaml). Check: only Web Funnel Analysis.
[Uses Per 30 Days] < 10
AND (ISNULL([Cost Per Use]) OR [Cost Per Use] > 5)
AND ATTR([is_declared])
```

```
// Scatter Colour Key
// Retire candidate #D2453F, Unregistered #E8A33D, AI-built #5B5FC7, Built by hand #005FAE.
IF [Is Retire Candidate] THEN "Retire candidate"
ELSEIF NOT ATTR([is_declared]) THEN "Unregistered"
ELSEIF ATTR([build_method]) = "ai_assisted" THEN "AI-built"
ELSE "Built by hand"
END
```

```
// Retire Uses Threshold
// Y position of the retire band's top edge: 10 uses per 30 days, scaled to the window.
10 * [p_period] / 30
```

```
// Scatter Label
// Labels only the retire candidates, unregistered readers and the most used product, as in the prototype.
// Table calc: compute using exposure_id.
IF [Is Retire Candidate]
    OR NOT ATTR([is_declared])
    OR [Product Uses (Period)] = WINDOW_MAX([Product Uses (Period)])
    THEN REPLACE(ATTR([display_name]), "Unregistered: ", "")
END
```

```
// Retire Pill
// Last table column: "✕ Retire?" (red pill) or "Not registered" (tag).
IF [Is Retire Candidate] THEN "✕ Retire?"
ELSEIF NOT ATTR([is_declared]) THEN "Not registered"
ELSE ""
END
```

```
// Built Tag
// "AI-built" or "By hand" tag in the table.
IF ATTR([build_method]) = "ai_assisted" THEN "AI-built" ELSE "By hand" END
```

```
// Is Declared Consumer Type View
// Small multiple filter: declared products counted in views. Make one per type
// ("query", "app_session", "agent_call") with the same pattern.
[consumption_type (mart_exposure_daily.csv)] = "view"
AND [is_declared]
```

```
// Uses In Period (Type)
// Total shown at the top right of each small multiple (put on Detail and reference it in the title).
SUM(IF [In Period] THEN [events] END)
```

Scatter build: Columns Product Cost (Period), Rows Product Uses (Period), both **logarithmic** axes. Detail `exposure_id`. Circle, colour Scatter Colour Key, size larger for retire candidates. Label Scatter Label. Reference band on Rows from the axis minimum to Retire Uses Threshold (`#FBEAE9`), as the "under 10 uses" part of the retire zone. The prototype's diagonal edge ("over $5 per use") is drawn as a reference line only if you add a 2-point helper table later; the red dot already marks the candidate. Filters: Product Uses (Period) > 0 and Product Cost (Period) > 0 (log axes can't show 0), Is Platform Match Node. Click: p_selected_exposure ← exposure_id, go to Lineage.

Small multiples: one sheet per type, bars SUM(events) per day, colour In Period, own axis each. Title "Dashboard and hub views   <Uses In Period (Type)>".

Ranked table build: Rows `display_name` (sorted by Product Uses (Period) desc), `Exposure Type Name` / `BI Tool Name` (as in 3.9 Consumer Type Label), `Built Tag`, then text: Product Uses (Period) + Uses Unit Label, the three Uses Change fields, Daily Consumers In Period (`0.0`), Cost Per Use (`$0.00`, "-" for NULL), Retire Pill. Filter Is Platform Match Node. Click: p_selected_exposure, go to Lineage.

### 10.3 BI semantic layer refreshes (Node Daily)

```
// Is Semantic Object
// Keeps BI semantic objects.
[resource_type] = "semantic"
```

```
// Semantic Success Rate (Period)
// Header column "Success": successful / all refreshes in the window. FIXED so it can sit on Rows as a header.
{ FIXED [node_id] :
    SUM(IF [In Period] THEN [refresh_ok] END)
    / SUM(IF [In Period] THEN [refresh_ok] + [refresh_failed] END) }
```

```
// Semantic Failed (Period)
// Header column "Failed".
{ FIXED [node_id] : SUM(IF [In Period] THEN [refresh_failed] ELSE 0 END) }
```

```
// Semantic Avg Refresh (Period)
// Header column "Avg refresh", seconds. Needs avg_refresh_sec typed as Number.
{ FIXED [node_id] : AVG(IF [In Period] THEN [avg_refresh_sec] END) }
```

```
// Semantic Success Low Text
// Success below 98%, in red bold.
IF [Semantic Success Rate (Period)] < 0.98 THEN STR(ROUND([Semantic Success Rate (Period)] * 100, 1)) + "%" ELSE "" END
```

```
// Semantic Success Text
// Success at 98% or above, normal ink. "-" for live objects with nothing to refresh.
IF ISNULL([Semantic Success Rate (Period)]) THEN "-"
ELSEIF [Semantic Success Rate (Period)] >= 0.98 THEN STR(ROUND([Semantic Success Rate (Period)] * 100, 1)) + "%"
ELSE ""
END
```

```
// Semantic Sort
// Most failures first, then lowest success.
[Semantic Failed (Period)] * 1000 - ZN([Semantic Success Rate (Period)]) * 100
```

```
// Semantic Mode Label
// Mode column, and the sparkline stand-in for live objects: "Live, no extract".
IF [connection_type] = "live" THEN "live · no extract" ELSE [connection_type] END
```

Build: Rows `Semantic Sort` (hidden, descending), `node_name`, `BI Tool Name`, `Semantic Mode Label`, the two Success texts, `Semantic Failed (Period)`, `Semantic Avg Refresh (Period)` (discrete, `0"s"`). Columns `date (dim_date.csv)` continuous, bars SUM(refresh_failed) in `#D2453F`, window band, axis hidden: this is the "failures per day" sparkline column, with the text columns as row headers. Filters: Is Semantic Object, Is Platform Match Node. Click a row: p_selected_node, go to Blast radius.

---

## 11. Governance (`GOV`)

Title "Is everything owned, documented, tested and declared?". Layout: four mini KPIs (96 px), then Unregistered consumers (two columns wide) beside AI-built dashboard sprawl, then Coverage by domain, Hygiene by team (with maturity) and Gaps to close.

### 11.1 Sheets and base tables

| # | Sheet | Base table | Shows |
|---|---|---|---|
| 1 | GOV Ownership KPI | Nodes | Ownership coverage, exposures with no owner |
| 2 | GOV Documentation KPI | Nodes | Documentation coverage, models with no description |
| 3 | GOV Test Coverage KPI | Nodes | Re-uses Model Test Coverage (7.2) |
| 4 | GOV Declared Consumers KPI | Observed Access | Share of readers registered, unregistered count |
| 5 | GOV Unregistered Consumers Table | Observed Access | Principal, kind, reads, queries, scanned, cost, first seen, likely what |
| 6 | GOV AI Sprawl List | Exposure Daily | AI-assisted dashboards: views, change, owner, created, maturity |
| 7 | GOV Coverage by Domain Table | Nodes | Models, docs, tests, owned per domain |
| 8 | GOV Hygiene by Team Bar | Nodes | Average of docs and tests coverage per team |
| 9 | GOV Maturity Bar | Nodes | Exposures by maturity |
| 10 | GOV Gaps No Owner | Nodes | Exposures with no owner |
| 11 | GOV Gaps No Tests | Nodes | Models with no tests |
| 12 | GOV Gaps No Description | Nodes | Models with no description |

### 11.2 Calcs

```
// Is Exposure Owned
// Exposures with a real owner ("No owner" is the mart's placeholder).
[owner_name] <> "No owner"
```

```
// Ownership Coverage
// Exposures with an owner / all exposures, unregistered included. Check: 23 of 27 = 85%.
ZN(SUM(IF [resource_type] = "exposure" AND [Is Exposure Owned] THEN 1 END))
/
SUM(IF [resource_type] = "exposure" THEN 1 END)
```

```
// Exposures Without Owner
// Sub-line "4 of 27 exposures have no owner".
ZN(SUM(IF [resource_type] = "exposure" AND NOT [Is Exposure Owned] THEN 1 END))
```

```
// Documentation Coverage
// Models with a description / all models. Check: 67 of 82 = 82%.
ZN(SUM(IF [resource_type] = "model" AND [has_description] THEN 1 END))
/
SUM(IF [resource_type] = "model" THEN 1 END)
```

```
// Models Without Description
// Sub-line "15 models have no description".
ZN(SUM(IF [resource_type] = "model" AND NOT [has_description] THEN 1 END))
```

```
// Declared Consumer Coverage
// Readers in query history that map to a declared exposure (or a BI object) / all readers in the window.
// Check (30d): 19 of 22 = 86%.
COUNTD(IF [In Period] AND [Principal Has Mapping In Period] THEN [principal] END)
/
COUNTD(IF [In Period] AND [query_count] > 0 THEN [principal] END)
```

```
// Unregistered Principals
// Sub-line "3 readers in query history not registered as exposures" (red when above 0).
COUNTD(IF [Is Unregistered Read In Period] THEN [principal] END)
```

```
// Principal Kind Label
// "Kind" column.
CASE [principal_type]
WHEN "service" THEN "Service account"
WHEN "human"   THEN "Personal login"
WHEN "agent"   THEN "Agent"
WHEN "app"     THEN "App"
END
```

```
// Principal Queries (Period)
// Queries in the window, per principal. FIXED so it shows once per principal while reads are listed per node.
{ FIXED [principal] : SUM(IF [In Period] THEN [query_count] END) }
```

```
// Principal Scanned GB (Period)
// GB scanned in the window, per principal.
{ FIXED [principal] : SUM(IF [In Period] THEN [bytes_scanned] END) } / 1e9
```

```
// Principal Cost (Period)
// Query cost in the window, per principal (the mart shares a principal's daily cost across the tables it read).
{ FIXED [principal] : SUM(IF [In Period] THEN [est_cost_usd] END) }
```

```
// Principal First Seen
// First day the principal appears in query history (whole history, not just the window).
{ FIXED [principal] : MIN([date (mart_observed_access.csv)]) }
```

```
// Likely Consumer
// "Likely what" column, from the mart's inferred exposure.
REPLACE([inferred_exposure_name], "Unregistered: ", "")
```

```
// Is AI Dashboard
// Story 10: AI-assisted dashboards.
[build_method] = "ai_assisted"
AND [exposure_type] = "dashboard"
```

```
// Sprawl Meta Line
// Grey line under each sprawl dashboard: "Liam Chen · created 7 Sep · maturity low".
[owner_name] + " · created "
+ STR(DAY([created_date])) + " " + LEFT(DATENAME('month', [created_date]), 3)
+ " · maturity " + [maturity]
```

```
// Is Hygiene Node
// Hygiene covers the sources and models a team owns.
[resource_type] IN ("model", "source")
```

```
// Team Doc Coverage
// Share of a team's sources and models with a description.
ZN(SUM(IF [Is Hygiene Node] AND [has_description] THEN 1 END))
/
SUM(IF [Is Hygiene Node] THEN 1 END)
```

```
// Team Test Coverage
// Share of a team's models with a test. Teams with sources only count as covered, as in the prototype.
IF ZN(SUM(IF [resource_type] = "model" THEN 1 END)) = 0 THEN 1
ELSE ZN(SUM(IF [resource_type] = "model" AND [test_count] > 0 THEN 1 END))
    / SUM(IF [resource_type] = "model" THEN 1 END)
END
```

```
// Hygiene Score
// Average of documentation and test coverage per team.
([Team Doc Coverage] + [Team Test Coverage]) / 2
```

```
// Hygiene Band
// Bar colour: Good (90%+) #2F9E6B, Fair (70%+) #E8A33D, Poor #D2453F.
IF [Hygiene Score] >= 0.9 THEN "Good"
ELSEIF [Hygiene Score] >= 0.7 THEN "Fair"
ELSE "Poor"
END
```

```
// Maturity Sort
// high, medium, low, left to right.
CASE [maturity] WHEN "high" THEN 1 WHEN "medium" THEN 2 WHEN "low" THEN 3 END
```

Unregistered table build (Observed Access): Rows `principal`, `Principal Kind Label`, `node_name` (dim_nodes, the reads, one line each), then discrete headers Principal Queries (Period), Principal Scanned GB (Period) (`#,##0" GB"`), Principal Cost (Period) (`$#,##0`), Principal First Seen (`d mmm`), Likely Consumer. Filters: Is Unregistered Read In Period, Is Platform Match Node. Sort by Principal Queries desc. Click: p_selected_exposure ← inferred_exposure_id, go to Lineage. Callout text under it is static.

AI sprawl build (Exposure Daily): Rows `display_name`, `Sprawl Meta Line`; text Product Uses (Period) "views" + the Uses Change fields. Filters: Is AI Dashboard, Is Platform Match Node. Subtitle: "5 AI-assisted dashboards, 5 of them on pds_finance_revenue". The overlap callout ("They read the same semantic object as Executive Revenue Dashboard…") is static text: the mart doesn't carry build_method for related nodes, so it can't be derived in Tableau without one more mart column (see section 12).

Coverage by domain build (Nodes): Rows `domain`, `Models In Scope`; Columns Measure Names (Documentation Coverage as "Docs", Model Test Coverage as "Tests", Ownership Coverage as "Owned"); Square marks with Measure Values on Colour as a **stepped 3-step palette from 0.5 to 1.1** (steps break at 0.7 and 0.9, matching the prototype's 70% and 90% bands: `#FBEAE9` / `#FDF3E1` / `#EAF6EF`), label Measure Values `0%`. NULL (domains without exposures) shows "-".

Hygiene build: Rows `owner_team` (sorted by Hygiene Score asc), bar Hygiene Score (axis 0 to 1), colour Hygiene Band. Tooltip: NODES OWNED, DOCUMENTED Team Doc Coverage, TESTED Team Test Coverage. Filter Is Platform Match Node.

Maturity build: Columns SUM of exposures (Node Count with resource_type = exposure filter), stacked by `maturity` sorted by Maturity Sort, label "high 7".

Gaps build: three list sheets (Nodes), each a single column of names with a dot: No owner (exposures, NOT Is Exposure Owned, red dot), No tests (models, test_count = 0, amber dot), No description (models, NOT has_description, amber dot). Empty state "None".

---

## 12. About

No calcs beyond counts. The chain line ("Raw sources 27 → Staging 30 → …") is one Nodes sheet: Columns Layer Name (sorted by layer_column), text Node Count. Everything else is static text objects. Copy the parameter table from section 1 onto this page as the documentation.

---

## 13. Decisions log and remaining notes

**Agreed after the Health review (21 Oct 2026):**

| # | Decision |
|---|---|
| 1 | New parameter `p_tile_view` (All / Needs attention) on Health. Also new: `p_lineage_view` (Graph / Table) on Lineage |
| 2 | "Open since" on the alert list: `open_incident_started_at` added to `dim_nodes` in `generator/marts.py` |
| 3 | Nav count badges left out (Tableau navigation buttons can't be data-driven) |
| 4 | The seven text-typed number fields will be set to Number (decimal) in the data source before the Runs and Performance sheets: `avg_runtime_sec`, `runtime_7d_avg_sec`, `runtime_prior28d_avg_sec`, `runtime_trend_pct`, `avg_refresh_sec`, `metrics_called`, `failed_calls` |
| 5 | Zero change on a KPI shows green "● 0 pp" (accepted) |

**Mart changes made while writing this pack** (all in `dim_nodes`, existing columns untouched, other marts byte-identical):

| Column | Why |
|---|---|
| `open_incident_started_at` | Health alert list "open since" |
| `downstream_keys` | Blast radius: unregistered readers of the node or anything downstream, from Observed Access |
| `downstream_consumers_7d / 30d / 90d` | Blast radius risk score on Node Daily (consumers × failure rate) |

**After pulling:** in Tableau, Data › Refresh the data source so the new `dim_nodes` columns appear, then paste the calcs.

**Known compromises against the prototype:**

1. Lineage: path highlight is on click, not hover (as planned in the data model doc). The selected box gets a bold name instead of a navy border. The platform stripe becomes a coloured "▌" at the end of the label.
2. Lineage: changing the exposure dropdown keeps the last clicked node in the panel until another box is clicked.
3. Blast radius: the incident message can't be copied to the clipboard. It shows as selectable text with a mailto action.
4. Usage: the retire zone shades the "under 10 uses" band. The diagonal "over $5 per use" edge would need a small helper table; the red dot already identifies the candidate.
5. Governance: the sprawl overlap callout is static text. Making it dynamic needs `related_build_method` in `mart_node_reach`.
6. Freshness: today's calendar cell can't get an outline; its label is bolded instead.
