# Lineage Control Tower: Project Spec

Oct 20, 2026 · @Gbolahan Adebayo

## Overview

**Lineage Control Tower** is a reference design for monitoring a modern data team's data products (BI dashboards, Databricks apps, AI agents and Claude-built data hubs) built first as a 9-tab Tableau dashboard. It traces every consumer back through dbt models to the raw sources that feed it, and tells a data team in one glance what is broken, who is affected, what is slow, what is expensive and what nobody uses.

**One-line pitch:** the data model is the product, the BI layer is interchangeable.

| Item | Decision |
| --- | --- |
| Working name | Lineage Control Tower (alternates still on the table: Exposure Ops Center, dbt Lineage Monitoring Dashboard) |
| Scope | All 9 tabs, designed together, built in sequence |
| Data | Fully synthetic, modeled on real dbt artifacts, warehouse query history, BI APIs and agent logs |
| Fictional company | Retail / e-commerce, placeholder name Acme Retail Co. |
| Primary build | Tableau, hosted on Tableau Public and shared openly as inspiration for any team, whatever tool they use |
| Template goal | Any data team can rebuild it on their own warehouse and dbt project, in whatever they build with: a BI tool, a Claude-built data hub, or an agent |
| Branding | Verata palette, mixed and extended for status and platform needs |
| Status | Spec stage. Next: synthetic dataset, then HTML mockup, then Tableau build |

The core idea is that dbt exposures are the bridge between the transformation layer and the BI layer. Most teams define exposures for dashboards only, and then never look at them again. Meanwhile the real consumers have multiplied: apps on Databricks, agents calling metrics, hubs built in Claude. This dashboard turns that metadata into a live control surface: every exposure gets a health status, an owner, a cost and a usage number, and every upstream failure can be traced forward to the people it affects.

## Why this exists

Data teams can usually tell you that a dbt job failed. They struggle to answer, quickly, what that failure means for the business.

The questions that take too long today:

- Which dashboards and data products does this failure break?
- Who owns those dashboards, and how many people are using them right now?
- Is the data behind a given dashboard fresh and tested today?
- Which models are getting slower or more expensive over time?
- Which dashboards cost a lot to keep running but barely get used?

### Why it matters now

There is a lot of noise in the data space right now about semantic layers, AI-built dashboards and "chat with your data." The conversation mostly stops at building things. Very little of it covers what happens after: when an organization has dozens or hundreds of dashboards, many of them generated quickly with Claude or similar tools, all sitting on Tableau published data sources or another BI semantic layer.

At that point the hard problems are operational:

- **Trust:** is the number on this dashboard safe to use today?
- **Sprawl:** which of these dashboards still matter, and which are zombies burning compute?
- **Accountability:** when something upstream breaks, who needs to know, and how fast?
- **Cost:** what does each data product actually cost to keep alive?

This dashboard is a working answer to those questions. It shows that the value of a semantic layer is not only consistent metrics, it is also a traceable, monitorable chain from raw data to the person reading the chart.

### The meta detail

The monitor is itself built on dbt and is itself an exposure in the lineage it monitors. That makes a good hook for the write-up: the dashboard watches its own supply chain.

## Audiences and personas

The build serves three audiences at once, and each one reads it differently.

| Audience | What they need from it | What that means for the build |
| --- | --- | --- |
| Portfolio (Tableau Public) | A polished, original piece that shows advanced Tableau technique and analytics engineering thinking | Lineage graph, set and parameter actions, LODs, clean design, About tab |
| Work (any data team) | Proof the idea solves real operational pain, not just a pretty demo | Realistic data model, metrics a platform lead would defend, production wiring notes |
| Wider data community | A clear argument in a noisy space about semantic layers and AI-built dashboards | Strong write-up, reusable template, cross-BI translation, open dataset and generator |

### Personas inside the fictional data team

| Persona | Main question | Primary tabs |
| --- | --- | --- |
| Analytics engineer on call | What broke, and who is affected? | Health Overview, Blast Radius, Run Monitor |
| Data platform lead | Where are we wasting compute, and what is getting slower? | Performance & Cost |
| BI developer / dashboard owner | Can I trust my dashboard today? | Lineage Explorer, Freshness |
| Head of data / leadership | Are we getting healthier, and are our data products used? | Health Overview, Usage & Adoption, Governance |
| Business stakeholder | Is this number safe to use? | Trust badge on each exposure tile |

The business stakeholder is a light-touch persona. They never need to open the dashboard. The idea is that the trust badge logic could be surfaced back inside the dashboards they already use.

## The company and its architecture

Acme Retail Co. runs its data across three warehouses, three dbt projects and three BI tools, which is messy in the same way most real companies are.

### The lineage chain

&#91;embedded content: lineage chain · 7 layers, each with its health signal\]

Each layer feeds the one below it. The dashed path shows notebooks, ML models and apps skipping the semantic layer and reading marts directly.

The BI semantic layer is new compared with the original brief. It reflects how most organizations actually work: dashboards rarely hit marts directly, they sit on a governed published data source. Making it its own layer lets the dashboard show that one broken published data source can take down five dashboards at once. Notebooks, ML models and apps skip it and read marts directly.

### Platforms and what lives where

| Platform | Domains | Example raw sources | dbt project | Notes |
| --- | --- | --- | --- | --- |
| Snowflake | Commerce, Finance, Operations | raw\_shopify.orders, raw\_stripe.payments, raw\_netsuite.gl\_entries, raw\_wms.inventory | acme\_core | The main warehouse. Receives migrated Redshift models mid-period |
| Databricks | Product, Customer (behavioral), ML | raw\_events.web\_sessions, raw\_events.app\_events, raw\_zendesk.tickets | acme\_product | Databricks to dbt to Databricks pattern: raw Delta tables in, dbt models out, ML model reads marts back |
| Redshift | Marketing, legacy Sales reporting | raw\_google\_ads.campaigns, raw\_meta\_ads.ad\_insights, raw\_hubspot.deals | acme\_marketing | Legacy. Several models migrate to Snowflake during the 90 days |

Cross-platform links: Customer 360 combines Snowflake order history with Databricks behavioral data. In a real company this would be a cross-project ref (dbt Mesh) or a shared mart. In the dataset it shows up as a lineage edge that crosses platforms.

### BI tools

| BI tool | Semantic layer object | Exposures it serves |
| --- | --- | --- |
| Tableau | Published data sources | Executive Revenue, Finance Close, Board KPI Pack, Web Funnel, Supply Chain Ops, Sales Pipeline, this monitor |
| Sigma | Datasets | Customer 360, Product Engagement |
| Power BI | Semantic models | Marketing Campaign Performance, Inventory Health, Support SLA Tracker |
| None (direct) | n/a | Churn Prediction Model, Pricing Experiment Analysis, Partner Revenue Share app |

### Consumers and how their metadata is collected

Acme's data is consumed by far more than BI dashboards, and every consumer is registered as an exposure, whatever kind it is.

| Consumer type | Examples at Acme | Access path | How it is tracked |
| --- | --- | --- | --- |
| BI dashboard | Executive Revenue (Tableau), Customer 360 (Sigma), Inventory Health (Power BI) | BI semantic layer | Declared via BI APIs, usage from activity logs |
| Notebook | Pricing Experiment Analysis | Direct warehouse | Declared, observed in query history |
| ML model | Churn Prediction Model | Direct warehouse (Databricks) | Declared, observed |
| Data app | Demand Forecast App (Databricks app), Partner Revenue Share | Direct warehouse | Declared, observed through its service principal |
| AI agent | Merchandising Copilot, Finance Q&A Agent | dbt semantic layer or MCP server | Declared, reported through call logs, observed |
| Claude-built data hub | Store Ops Hub | Extract or connector | Declared, reported |

&#91;embedded content: how consumer metadata reaches the monitor · 4 consumer types, 3 collection paths\]

Metadata reaches the store three ways, plus the dbt artifacts:

- **Declared:** teams register what they build. BI exposures can be generated automatically from BI APIs. Apps, agents and hubs get a short YAML entry
- **Observed:** every consumer that queries the warehouse leaves a trace in query history. This is how undeclared consumers are caught
- **Reported:** agents and apps log what they did, such as which metric they called and how often. This is their equivalent of a view count

The dashboard reads only from the ops store, which is what makes it rebuildable in any tool.

### Real-world caveats (for the write-up)

- **Name matching is the hardest part.** Tying a Tableau data source, an app's query and an agent's call back to the same dbt node takes deliberate naming or mapping tables. The synthetic data is clean here; real data will not be
- **Observed only works when consumers are identifiable.** Each app or agent needs its own service account or query tag
- **Reported usage for agents is not standard yet.** Showing it is forward-looking, and the write-up should say so
- **Claude-built hubs often read through a connector or extract**, so they are usually declared rather than observed

## Data model

Fourteen core tables plus one optional, all joining on `node_id` (an exposure's id is also a node\_id) plus a date or timestamp. Everything Tableau needs is precomputed, so there is no recursion or graph logic inside the workbook.

### Table summary

| Table | Grain | Approx. rows (90 days) | Production source |
| --- | --- | --- | --- |
| dim\_nodes | One row per source, model, semantic object or exposure | \~135 | manifest.json, BI metadata APIs |
| dim\_owners | One row per owner | \~15 | manifest.json owner blocks, HR or Slack directory |
| dim\_date | One row per day | 90 | Generated |
| fct\_lineage\_edges | One row per parent to child link | \~260 | manifest.json parent\_map / child\_map |
| fct\_exposure\_upstream | One row per exposure and upstream node | \~900 | Derived (graph closure) |
| fct\_lineage\_layout | One row per node position and edge point | \~650 | Derived (layout algorithm) |
| fct\_job\_runs | One row per dbt job run | \~3,000 | dbt Cloud Admin API |
| fct\_model\_runs | One row per model per job run | \~150k to 250k | run\_results.json |
| fct\_test\_results | One row per test per run | \~100k | run\_results.json |
| fct\_source\_freshness | One row per source per freshness check | \~50k | sources.json |
| fct\_semantic\_refresh | One row per BI semantic object refresh | \~4k | Tableau / Sigma / Power BI APIs |
| fct\_warehouse\_cost | One row per node per day | \~7k | Warehouse system tables |
| fct\_consumption | One row per consumer per day and consumption type | \~4k | BI activity logs, agent and app logs |
| fct\_observed\_access | One row per principal, node and day | \~6k | Warehouse query history, by user, service principal or query tag |
| fct\_incidents (optional) | One row per incident | \~10 | Incident tool (PagerDuty, Jira, Slack) |

### Column detail

**dim\_nodes**

- `node_id`, `node_name`, `resource_type` (source / model / seed / snapshot / semantic / exposure)
- `layer` (source / staging / intermediate / mart / semantic / exposure) and `layer_order` (0 to 5)
- `platform` (current platform), `dbt_project`, `database_name`, `schema_name`
- `materialization` (table / view / incremental / ephemeral; null for non-models)
- `domain`, `owner_name`, `owner_team`, `tags`
- `has_description`, `test_count`, `created_date`
- Migration fields: `migrated_from_platform`, `migration_date` (null unless the node moved)
- Semantic-only: `semantic_object_type` (published\_data\_source / sigma\_dataset / pbi\_semantic\_model), `connection_type` (extract / live)
- Exposure-only: `exposure_type` (dashboard / notebook / ml / data\_app / agent / data\_hub / analysis), `bi_tool`, `exposure_url`, `maturity` (high / medium / low), access\_path (bi\_semantic\_layer / direct\_warehouse / dbt\_semantic\_layer / mcp\_server / extract), build\_method (hand\_built / ai\_assisted), is\_declared (false for consumers found only in query history), service\_principal

**dim\_owners**

- `owner_name`, `owner_team`, `email` (fake), `slack_channel`, `on_call_rotation` (yes / no)

**dim\_date**

- Standard calendar columns plus `is_weekend`, `is_month_end`, `is_month_end_close_window` (last 3 and first 3 business days)

**fct\_lineage\_edges**

- `edge_id`, `parent_node_id`, `child_node_id`, `crosses_platform` (bool)

**fct\_exposure\_upstream** (the closure table)

- `exposure_id`, `upstream_node_id`, `depth` (hops from the exposure)
- Read the other way round, the same table gives downstream impact for any node, which powers Blast Radius with a simple filter

**fct\_lineage\_layout**

- Node rows: `node_id`, `x` (layer position), `y` (rank within layer), `layout_scope` (global or the exposure\_id it was laid out for)
- Edge path rows: `edge_id`, `point_order` (1 or 2, or more for curved paths), `x`, `y`, `layout_scope`
- Two scopes are needed: a global layout for the full graph, and a per-exposure layout so the Lineage Explorer stays readable when one exposure is selected

**fct\_job\_runs**

- `job_run_id`, `job_name`, `dbt_project`, `platform`, `schedule` (hourly / daily / weekly), `environment` (prod / ci)
- `run_started_at`, `run_completed_at`, `duration_sec`, `status` (success / error / cancelled)
- `models_run`, `models_failed`, `models_skipped`, `tests_failed`, `triggered_by` (schedule / manual / ci)

**fct\_model\_runs**

- `job_run_id`, `node_id`, `platform` (platform at run time, which matters for migrated models)
- `run_started_at`, `run_completed_at`, `execution_time_sec`, `status` (success / error / skipped), `rows_affected`
- `error_category` (compilation / database / timeout / permission / schema\_change / upstream\_skip), `error_message`

**fct\_test\_results**

- `test_id`, `test_name`, `test_type` (not\_null / unique / accepted\_values / relationships / custom)
- `node_id`, `column_name`, `job_run_id`, `run_at`, `status` (pass / warn / fail / error), `failures_count`, `severity`

**fct\_source\_freshness**

- `source_node_id`, `checked_at`, `max_loaded_at`, `lag_minutes`, `warn_after_minutes`, `error_after_minutes`, `status` (pass / warn / error)

**fct\_semantic\_refresh**

- `refresh_id`, `node_id` (the semantic object), `bi_tool`, `refresh_started_at`, `duration_sec`, `status` (success / failed / skipped\_upstream), `rows_refreshed`

**fct\_warehouse\_cost**

- `date`, `node_id`, `platform`, `warehouse_or_cluster`
- `compute_units` (Snowflake credits / Databricks DBUs / Redshift RPU-hours), `est_cost_usd`, `bytes_scanned`

**fct\_consumption** (replaces fct\_exposure\_usage, so every consumer type has a usage number)

- `date`, `exposure_id`, `consumption_type` (view / query / agent\_call / app\_session)
- `events`, `unique_consumers` (viewers, users or calling sessions), `avg_latency_sec`
- Agent-only: `metrics_called`, `failed_calls`

**fct\_observed\_access** (powers the declared vs observed gap)

- `date`, `principal` (user, service principal or query tag), `principal_type` (human / service / agent / app)
- `node_id` (the table or model queried), `query_count`, `bytes_scanned`
- `mapped_exposure_id` (null when no declared exposure accounts for this principal, which is what flags an undeclared consumer)

**fct\_incidents** (optional, but makes annotations and MTTR storytelling much easier)

- `incident_id`, `title`, `root_node_id`, `started_at`, `resolved_at`, `severity`, `exposures_affected`, `category` (freshness / schema\_change / test / performance)

### Changes from the original brief

- Added a `semantic` layer and `fct_semantic_refresh`. Extract refresh fields moved out of `fct_exposure_usage` into it, since refreshes belong to the published data source, not the dashboard
- Added `dbt_project` and migration fields to support the multi-project and Redshift to Snowflake stories
- Added `platform` on `fct_model_runs` so migrated models report cost and runtime against the right warehouse
- Added `layout_scope` to the layout table
- Added the optional `fct_incidents` table

Added after the second review:

- Exposure types widened to data apps, agents and Claude-built data hubs, with `access_path`, `build_method`, `is_declared` and `service_principal`
- `fct_exposure_usage` replaced by `fct_consumption`, which covers views, queries, app sessions and agent calls
- New `fct_observed_access` table from warehouse query history, used to find undeclared consumers

## Metrics and definitions

Every metric below is defined once here and reused across all tabs and all BI tools. These definitions are what the cross-BI cheat sheet will translate into Tableau calcs, Sigma formulas and DAX.

### Reliability

| Metric | Definition | Main tab |
| --- | --- | --- |
| Run success rate | Successful model runs / (all model runs minus skipped) | Health Overview, Run Monitor |
| Job success rate | Successful job runs / all job runs | Run Monitor |
| Test pass rate | Passing tests / all tests run (warn tracked separately) | Health Overview, Data Quality |
| Freshness SLA compliance | Freshness checks with status pass / all checks | Health Overview, Freshness |
| Semantic refresh success | Successful BI semantic object refreshes / all refreshes | Lineage Explorer, Usage |
| MTTR | Average time from a node's first failure to its next success | Health Overview, Run Monitor |
| Failure recurrence | Count of distinct days a node or test failed in the last 30 days | Data Quality, Blast Radius |

### Exposure health

| Metric | Definition |
| --- | --- |
| Exposure health status (RAG) | **Red:** any upstream model errored in its latest run, any upstream source is in freshness error, or the semantic object's latest refresh failed. **Amber:** any upstream test failing or warning, or any upstream freshness warn. **Green:** everything else. **Grey:** no runs in the period |
| Exposure health score (0 to 100) | 40% upstream run success + 30% upstream test pass rate + 30% upstream freshness compliance, all over the last 7 days |
| Trust badge | A simplified label from the RAG status for business users: Trusted / Use with caution / Do not use |

### Impact

| Metric | Definition |
| --- | --- |
| Blast radius (exposures) | Number of downstream exposures for a node |
| Blast radius (people) | Unique consumers (viewers, app users and calling agents) of those downstream exposures in the last 30 days |
| Risk score | Blast radius (people) multiplied by the node's failure rate over the last 30 days |

### Performance and cost

| Metric | Definition |
| --- | --- |
| Runtime trend | 7-day average runtime vs the prior 28-day average, as % change |
| Cost per exposure | Upstream model cost allocated to exposures. A shared model's cost is split evenly across the exposures it feeds |
| Cost per view | Cost per exposure / consumption events (views, queries, app sessions or agent calls) over the same period |
| Incremental candidate flag | Materialization is table AND rows above a threshold AND runtime trend above +25% |
| Zombie flag | Cost per view above a threshold AND fewer than N consumption events in the last 30 days |

### Governance

| Metric | Definition |
| --- | --- |
| Test coverage | Models with at least 1 test / all models |
| Documentation coverage | Models with a description / all models |
| Ownership coverage | Exposures with an owner / all exposures |
| Hygiene score (per team) | Average of the three coverage metrics for nodes the team owns |
| Declared coverage | Observed principals mapped to a declared exposure / all observed principals, last 30 days |
| Undeclared consumers | Principals in query history with no mapped exposure, counted per node and in total |

Thresholds for the zombie flag (N views, cost per view) and the incremental flag (row threshold) will be set once the dataset exists, so they sit sensibly against the generated numbers. Flagging this as a decision to make in the dataset phase.

## Synthetic data design

The dataset covers 90 days, from 22 July to 19 October 2026, and is generated by a Python script so anyone can regenerate or rescale it. Output is CSV, with an optional Hyper file for Tableau.

### Scale

| Element | Count | Notes |
| --- | --- | --- |
| Warehouses / platforms | 3 | Snowflake, Databricks, Redshift |
| dbt projects | 3 | acme\_core, acme\_product, acme\_marketing |
| Domains | 6 | Finance, Commerce, Marketing, Product, Operations, Customer |
| Raw sources | \~25 | Spread unevenly, Snowflake heaviest |
| dbt models | \~80 | Roughly 30 staging, 20 intermediate, 30 marts |
| BI semantic objects | \~12 | Published data sources, Sigma datasets, Power BI semantic models |
| Exposures | 19 declared (BI, notebooks, ML, apps, agents, a Claude hub) plus up to 5 from the sprawl story | The original 15 plus the 4 new consumers listed below |
| dbt jobs | 6 to 8 | Hourly, daily and weekly, prod and CI |
| Owners / teams | \~15 owners, 6 teams | One per domain plus a central data platform team |

**New consumers added to the original 15 exposures**

| Exposure | Type | Access path | Platform |
| --- | --- | --- | --- |
| Demand Forecast App | data\_app (Databricks app) | Direct warehouse | Databricks |
| Merchandising Copilot | agent | dbt semantic layer | Snowflake |
| Finance Q&A Agent | agent | MCP server | Snowflake |
| Store Ops Hub | data\_hub (built in Claude) | Extract | Snowflake |

Partner Revenue Share and Churn Prediction Model, already in the original list, are retyped as data\_app and ml respectively.

### Normal rhythm (the background noise)

- Weekday usage roughly 4 to 5 times weekend usage
- Finance dashboards spike in the month-end close window
- Board KPI Pack spikes once a month around board prep
- A baseline run success rate around 97 to 98%, with small random failures so nothing looks too perfect
- Gradual organic growth in row counts and runtime, around 1 to 2% a week

### Planted stories

| # | Story | Where it happens | When | Where it shows up |
| --- | --- | --- | --- | --- |
| 1 | **Slow creep.** fct\_sessions is a full-refresh table that should be incremental. Runtime and cost roughly double, then drop sharply when it is switched to incremental | Databricks | 20 Aug to 1 Oct, fixed 4 Oct | Performance & Cost |
| 2 | **Recurring Monday failure.** A unique test on dim\_customers fails every Monday because of a dedupe bug in the weekend backfill. Still unresolved | Snowflake | Every Monday from 10 Aug, including 19 Oct | Data Quality, Health Overview |
| 3 | **Platform migration.** Marketing models move from Redshift to Snowflake. Redshift cost falls, Snowflake cost rises, a brief dip in run success during cutover | Redshift to Snowflake | 1 to 15 Sep | Performance & Cost, Run Monitor |
| 4 | **Schema change incident.** An upstream column rename in raw\_hubspot breaks 3 models and 4 dashboards for one day, then a clean recovery | Snowflake (post-migration) | 7 Sep | Run Monitor, Blast Radius, MTTR |
| 5 | **Freshness breach cascade.** raw\_stripe.payments stops loading for about 14 hours, overnight into the first day of month-end close. Every finance exposure goes red | Snowflake | 30 Sep to 1 Oct | Freshness, Health Overview, Blast Radius |
| 6 | **Green dbt, broken dashboard.** A Tableau published data source extract fails for two days due to expired credentials. dbt is fully green but three dashboards serve stale data | Tableau semantic layer | 12 to 13 Oct | Lineage Explorer, Usage |
| 7 | **Zombie dashboard.** Web Funnel Analysis sits on the expensive fct\_sessions model but gets fewer than 5 views a month. Links nicely to story 1 | Databricks | Whole period | Usage & Adoption, Performance & Cost |
| 8 | **Orphan exposure.** Pricing Experiment Analysis has no owner | Databricks | Whole period | Governance |
| 9 | **Live issues today.** On the last day, the Monday test failure plus one source in freshness warn, so the Overview is not all green when someone opens it | Mixed | 19 Oct | Health Overview |
| 10 | **Dashboard sprawl.** Four or five AI-assisted dashboards appear in the last 6 weeks, mostly duplicating each other on the same published data source, with low and falling usage | Tableau | 7 Sep onward | Usage & Adoption, Governance |
| 11 | **Undeclared consumers.** A pricing agent starts reading fct\_orders and dim\_products through a shared service account without being registered. Two smaller ones join it: a scheduled notebook and a Claude hub on a personal login. They show up only in query history, and the agent adds visible Snowflake cost | Snowflake | 21 Sep onward | Governance, Blast Radius, Usage & Adoption |

&#91;embedded content: planted stories · 22 Jul to 19 Oct 2026\]

The stories are spaced so each one can be read on its own in a time series, and the Stripe breach is placed on month-end close for maximum finance impact.

Story 6 is the one that best supports the semantic layer argument: a team that only monitors dbt would see all green while users read stale numbers. Story 10 ties directly to the AI-built dashboards angle. It needs a small extra field on exposures (`build_method`: hand\_built or ai\_assisted). Confirmed. Story 11 extends the same argument to agents.

### Generator design notes

- One config file holds every count, date and story parameter, so the dataset can be rescaled or a story switched off
- A fixed random seed, so the published dataset is reproducible
- Nodes and edges generated first, then runs, then tests and freshness, then cost and usage, so failures propagate correctly downstream (a failed model makes its children skip)
- A data dictionary is generated alongside the CSVs

## Dashboard: global behaviour and the nine tabs

Nine tabs, one shared filter set and one shared selection model, so clicking an exposure or a node anywhere carries that context into every other tab.

### Global behaviour

- **Navigation bar** across the top, one button per tab, with the current tab highlighted
- **Global filters:** date range, platform, domain, owner team, environment (prod / CI), BI tool
- **Shared selections:** a selected exposure and a selected node, held in parameters and set by parameter actions from any tab
- **Every tab has:** a title phrased as the question it answers, a one-line subtitle, a data-last-refreshed stamp, and an info button
- **Status encoding:** colour always paired with an icon or label, never colour alone

### Tab list

| # | Tab | Question it answers | Primary persona | Stories it surfaces |
| --- | --- | --- | --- | --- |
| 1 | Health Overview | Is anything on fire right now? | On-call engineer, leadership | 2, 5, 9 |
| 2 | Lineage Explorer | What feeds this dashboard, and is every step healthy? | BI developer | 6 |
| 3 | Blast Radius | If this breaks, who do I need to tell? | On-call engineer | 4, 5, 11 |
| 4 | Run & Failure Monitor | What failed, when, why, and how fast did we recover? | On-call engineer | 3, 4 |
| 5 | Data Quality & Tests | Which tests keep failing, and where are we untested? | Analytics engineer | 2 |
| 6 | Freshness & SLAs | Is the data arriving on time? | BI developer, on-call | 5 |
| 7 | Performance & Cost | What is getting slower and more expensive? | Platform lead | 1, 3, 7 |
| 8 | Usage & Adoption | Which data products earn their keep? | Leadership | 7, 10, 11 |
| 9 | Governance | Is everything owned, documented, tested and declared? | Leadership, platform lead | 8, 10, 11 |

Plus an **About / How to use** tab explaining the data model, the metric definitions and that the data is synthetic.

### 1. Health Overview

- KPI tiles: run success rate, test pass rate, freshness compliance, exposures at risk (red plus amber), MTTR, cost month to date. Each with a sparkline and change vs prior period
- Exposure status grid: one tile per exposure, grouped by consumer type (dashboards, apps and ML, agents, hubs), RAG colour plus icon, owner, BI tool and trust badge. Clicking a tile sets the selected exposure and jumps to the Lineage Explorer
- Incidents in the last 24 hours list
- Layer health strip: a small bar per layer (source, staging, intermediate, mart, semantic, exposure) showing how many nodes are healthy, so you can see at a glance where in the chain the trouble sits

### 2. Lineage Explorer

- Pick an exposure and see every upstream node laid out in columns from sources to the exposure
- Nodes coloured by latest status, marked by platform
- Hover: last run, runtime, tests, owner, plus a viz-in-tooltip runtime sparkline
- Clicking a node opens a side panel (dynamic zone visibility) with runtime trend and recent test results
- Toggle between graph view and Sankey view

### 3. Blast Radius

- Pick a model, source or semantic object and see everything downstream
- Table of affected exposures: owner, Slack channel, unique consumers in the last 30 days, plus any undeclared consumers reading the node
- A ready-to-copy summary line for an incident message ("fct\_orders failure affects 4 dashboards and 212 viewers")
- Top 10 riskiest nodes ranked by risk score

### 4. Run & Failure Monitor

- Gantt timeline of job runs, bars coloured by status
- Failures by model and by error category
- Failure trend and MTTR trend over time, with incident annotations
- Table of recent errors with error messages

### 5. Data Quality & Tests

- Heatmap of models by day, coloured by test outcome
- Failures by test type
- Most frequently failing tests
- Test coverage by domain

### 6. Freshness & SLAs

- Current lag per source as a bullet chart against warn and error thresholds
- Freshness compliance by platform over time
- Calendar heatmap of breaches
- Sources currently late, with the exposures they affect

### 7. Performance & Cost

- Runtime trend for the slowest models
- Top 15 slowest and most expensive models
- Cost by platform over time, showing the migration
- Materialization breakdown and incremental candidates
- Cost per exposure

### 8. Usage & Adoption

- Consumption per exposure over time, split by type: views, app sessions, agent calls
- Cost vs views scatter with the zombie quadrant called out
- Semantic layer refresh success and average load time
- Most and least used data products, with filters for consumer type and build method

### 9. Governance

- Ownership, documentation and test coverage by domain
- Exposures without owners, models without descriptions or tests
- Exposure maturity breakdown
- Hygiene score by team. Declared vs observed: undeclared consumers by node, with principal and query volume

### Build order

All 9 tabs are in scope. I'd still build in this order, because tabs 1 to 4 share the hardest pieces (selection model, lineage layout, closure table) and everything after reuses them: 1, 2, 3, 4, then 7, 8, 6, 5, 9, then About.

## Design system

The Verata palette carries the brand (layout, navigation, platforms), and a separate, muted status set carries health, so the two never compete for meaning.

### Brand palette (from Verata)

| Name | Hex | Role in the dashboard |
| --- | --- | --- |
| Navy Blue | #002C55 | Navigation bar, titles, primary text, Redshift (see platforms) |
| Intelligence Blue | #005FAE | Selection and highlight state, links, Snowflake |
| Sky Blue | #83C7EB | Secondary marks, hover states, Databricks |
| Signal Lime | #C7FFA4 | Active tab indicator, "you are here" markers, callout chips. Chrome only, never inside a chart |
| Off White | #F5F5F3 | Page background |
| White | #FFFFFF | Card background (added, not in the palette) |

The palette also shows lighter tints of each colour. Those tints can serve as fills for low-emphasis states (for example unselected lineage nodes at reduced opacity).

### Status colours (added, outside the brand)

| Status | Proposed colour | Icon / label |
| --- | --- | --- |
| Healthy | Muted green, around #2F9E6B | Check mark, "Healthy" |
| Warning | Amber, around #E8A33D | Triangle, "Warning" |
| Critical | Red, around #D2453F | Cross or exclamation, "Critical" |
| Skipped / unknown | Grey, around #A3ADB8 | Dash, "No data" |

These hex values are starting points. They need a contrast check against Off White and a colourblind simulation once the mockup exists.

### The lime question

Signal Lime sits close to a "healthy green". If it appears inside charts, people will read it as status. Two options:

- **Option A (recommended):** lime stays in the chrome only (nav, active tab, small callout chips). Status uses the muted green above. Clean separation
- **Option B:** lime becomes the healthy colour, with a dark green outline or icon for contrast, and amber and red are added. More on-brand, but lime on off-white has weak contrast for small marks

### Platforms

Platforms take the three blues, light to dark: Databricks Sky Blue, Snowflake Intelligence Blue, Redshift Navy. Three blues of clearly different lightness stay distinguishable and on-brand, and they never collide with the status set. In the lineage graph, platform is also shown by a small label or shape, because node fill is reserved for status.

### Layout and type

- Fixed size 1400 x 900 for desktop, plus a phone layout for Health Overview
- Card-style tiles, white on Off White, generous spacing
- Tableau Public only renders web-safe and Tableau fonts reliably, so the build uses the Tableau font family (Book, Medium, Semibold) even if Verata uses a different brand typeface
- Every tab: title as a question, one-line subtitle, refreshed stamp, info button

## Tableau build techniques

The workbook leans on precomputed data so the hard logic lives in Python and dbt, and Tableau does what it is best at: interaction and visual encoding.

| Technique | Used for | Tab |
| --- | --- | --- |
| Precomputed x/y layout, line marks with point\_order, dual-axis circles | Lineage graph (Tableau has no native network graph) | Lineage Explorer |
| Sankey via data densification | Alternate lineage view, sources through layers to exposures | Lineage Explorer |
| Parameter actions | Selected exposure and selected node, shared across every tab | All |
| Set actions | Highlight upstream or downstream nodes on click | Lineage Explorer, Blast Radius |
| LOD expressions | Latest status per node, first failure and next success for MTTR, per-exposure rollups | All |
| Table calculations | Runtime trend (7-day vs prior 28-day), period-over-period on KPI tiles | Health Overview, Performance & Cost |
| Dynamic zone visibility | Node detail side panel, graph vs Sankey toggle, info overlays | Lineage Explorer, all |
| Gantt marks | Job run timeline from run\_started\_at and duration | Run & Failure Monitor |
| Calendar heatmaps | Test outcomes and freshness breaches by day | Data Quality, Freshness |
| Bullet charts | Source lag against warn and error thresholds | Freshness |
| Viz in tooltip | Runtime sparkline on node hover, upstream mini-list on exposure tiles | Lineage Explorer, Health Overview |
| Annotations from fct\_incidents | Marking stories on time series | Run Monitor, Performance & Cost |
| Navigation buttons | Tab bar | All |
| Relationships (logical layer) | Joining facts on node\_id and date without blowing up row counts | Data source |

### Example calculations

Latest run per node:

```
{ FIXED [node_id] : MAX([run_started_at]) }
```

Is this the latest run:

```
[run_started_at] = { FIXED [node_id] : MAX([run_started_at]) }
```

The full set of calculations, with Sigma and DAX equivalents, goes into the calculated field cheat sheet deliverable.

### Tableau Public constraints to design around

- No live connections, so the data is an extract (CSV or Hyper)
- Row and storage limits (around 15 million rows per data source and 10 GB of account storage, from memory, worth confirming) sit comfortably above this dataset
- Web-safe fonts only
- The "data last refreshed" stamp will show the generator's run date, which the About tab should explain

## Making it a template

Any team can rebuild this in four steps, because every table in the data model maps to an artifact or system table they already have.

### Production wiring

1. **Capture dbt artifacts after every run.** Push manifest.json, run\_results.json, sources.json and catalog.json into the warehouse using a dbt Cloud webhook, an on-run-end hook, or the Elementary package (which stores run and test results as tables for you)
2. **Model them with a small dbt project** (for example `dbt_ops`) that parses the artifacts into the tables in the data model section. The closure and layout tables are built here, in SQL or a Python model
3. **Pull warehouse and BI metadata on a schedule.** Cost and query history from warehouse system tables, usage and refresh history from the BI tool's API, landed in the same warehouse
4. **Point the dashboard at those tables** and refresh hourly. Register the dashboard itself as an exposure, so it appears in its own lineage

### Where each table comes from in production

| Table | dbt source | Warehouse source | BI source |
| --- | --- | --- | --- |
| dim\_nodes, fct\_lineage\_edges | manifest.json | n/a | Tableau Metadata API, Power BI Scanner API, Sigma REST API (for semantic objects) |
| fct\_job\_runs | dbt Cloud Admin API | n/a | n/a |
| fct\_model\_runs, fct\_test\_results | run\_results.json or Elementary | n/a | n/a |
| fct\_source\_freshness | sources.json | n/a | n/a |
| fct\_warehouse\_cost | n/a | Snowflake ACCOUNT\_USAGE.QUERY\_HISTORY and WAREHOUSE\_METERING\_HISTORY, Databricks system.query.history and system.billing.usage, Redshift SYS\_QUERY\_HISTORY | n/a |
| fct\_semantic\_refresh | n/a | n/a | Tableau Admin Insights job performance, Power BI refresh history, Sigma audit logs |
| fct\_exposure\_usage | n/a | n/a | Tableau Admin Insights TS Events, Power BI activity log, Sigma audit logs |

Cost attribution in production usually works by tagging dbt queries with the model name (a query tag or comment) and joining query history back to node\_id. Worth a short note in the write-up, because it is the part most teams have not set up.

### Example exposure YAML

The `meta` block carries the fields the dashboard needs that dbt does not have natively.

```yaml
exposures:
  - name: executive_revenue_dashboard
    label: Executive Revenue Dashboard
    type: dashboard
    maturity: high
    url: https://tableau.example.com/views/ExecRevenue
    description: Daily revenue, orders and margin for the leadership team.
    depends_on:
      - ref('fct_orders')
      - ref('fct_revenue_daily')
    owner:
      name: Finance Analytics
      email: finance-analytics@example.com
    meta:
      bi_tool: tableau
      semantic_object: pds_finance_revenue
      platform: snowflake
      domain: finance
      build_method: hand_built
```

### Cross-BI translation

The pitch: the data model is the product, the BI layer is interchangeable.

| Need | Tableau | Claude data hub | Sigma | Power BI | Looker |
| --- | --- | --- | --- | --- | --- |
| Selected exposure drives everything | Parameter actions | Shared page state and URL parameters | Controls plus cross-element filters | Slicers, field parameters | Dashboard filters, cross-filtering |
| Upstream / downstream highlight | Set actions | Click a node to trace up or down | Linked controls | Cross-highlighting | Cross-filtering |
| Lineage graph | Precomputed x/y plus dual axis | Native interactive graph | Precomputed x/y scatter plus lines | Custom network or Sankey visual | Custom visualization |
| Root-cause drill | Viz in tooltip, drill panels | A page per node with full history | Drill-down, expandable tables | Decomposition tree (a natural fit for "why is this red?") | Drill fields |
| Incident notes | Not native (extensions) | Notes saved in the page's shared storage | Input tables, so engineers log notes beside the failing model | Power Apps or translytical write-back | Actions to external tools |
| Live data | Live or extract | Exported tables or a connector | Live on warehouse (native strength) | DirectQuery or import | Live via LookML |
| Ask a question | Not native | Ask Claude about the data in place | Not native | Copilot | Not native |
| Alerts | Data-driven alerts | A scheduled task posts a summary | Alerts, scheduled exports | Data alerts, Power Automate | Alerts |

The second build is a Claude-built data hub, because it can do what Tableau cannot: write-back, node pages and asking questions in place. Sigma or Power BI would make a good third build.

## Build plan and workflow

Five phases, each ending in something you can look at and sign off before the next starts.

| Phase | What happens | Where | Output | Gate to move on |
| --- | --- | --- | --- | --- |
| 1. Spec | This document, reviewed and corrected | Claude (chat) | Signed-off spec | Open questions below answered |
| 2. Dataset | Python generator, CSVs, data dictionary, story checks | Claude (exact surface to confirm) | 13 CSVs plus optional Hyper, generator script, dictionary | Each planted story visibly appears in a quick check chart |
| 3. HTML mockup | Clickable mockup of all 9 tabs on the real dataset | Claude (chat) | Interactive HTML artifact | Layout, colours and interactions agreed |
| 4. Tableau build | Workbook built tab by tab in the build order | Claude Code plus Tableau | Published workbook on Tableau Public, shared openly as inspiration | All 9 tabs plus About, QA pass |
| 5. Extend | Second BI tool, write-up, repo | Mixed | Claude-built data hub version, then optionally Sigma or Power BI, plus blog / LinkedIn post and GitHub repo | Published |

### Deliverables

- [ ] Spec (this document)
- [ ] Python generator script and config
- [ ] Synthetic dataset (CSV, optional Hyper)
- [ ] Data dictionary
- [ ] Story validation charts (quick proof each story landed)
- [ ] Clickable HTML mockup
- [ ] Tableau workbook on Tableau Public
- [ ] Calculated field cheat sheet (Tableau, Sigma, DAX)
- [ ] Example `dbt_ops` project and exposure YAML
- [ ] Claude-built data hub version (second build), then optionally Sigma or Power BI
- [ ] Write-up for the blog, LinkedIn and community sessions
- [ ] GitHub repo with generator, dictionary and dbt\_ops sample

### Notes on the workflow

- The HTML mockup in phase 3 should run on the real generated CSVs, not placeholder numbers, so the stories can be checked visually before any Tableau time is spent. It can then grow into the Claude-built data hub in phase 5, so that work is not thrown away
- If the Tableau build in Claude Code means generating workbook XML or driving Tableau through an integration, the dataset folder structure should be set up for that from phase 2. Flagging this as an assumption until we confirm how you plan to work in Claude Code
- The skill and the ideas list from the original brief are still missing. They're most useful from phase 3 onward, so they need to come in before the mockup

## Assumptions and open questions

Everything below was inferred rather than confirmed. Each one is easy to change now and expensive to change after the dataset exists.

### Assumptions made in this spec

| # | Assumption | Section |
| --- | --- | --- |
| A1 | Working name is Lineage Control Tower | Overview |
| A2 | The BI semantic layer becomes its own layer in the lineage chain | Architecture, Data model |
| A3 | Three dbt projects (one per platform), with a cross-platform link for Customer 360 | Architecture |
| A4 | Snowflake holds Commerce, Finance, Operations; Databricks holds Product and ML; Redshift holds Marketing and legacy Sales | Architecture |
| A5 | The 90-day window runs 22 July to 19 October 2026 | Synthetic data |
| A6 | Story 6 (green dbt, broken dashboard) is added | Synthetic data |
| A7 | Confirmed: story 10 (AI-assisted dashboard sprawl) and story 11 (undeclared consumers) are in | Synthetic data |
| A8 | Signal Lime stays in the chrome only, with a separate muted status set | Design system |
| A9 | Platforms take the three Verata blues | Design system |
| A10 | Tableau fonts are used instead of a Verata brand typeface | Design system |
| A11 | Confirmed: Tableau is the flagship on Tableau Public, a Claude-built data hub is the second build. New: agent usage is modeled as if logged through a semantic layer or MCP server, which is forward-looking | Making it a template |

### Open questions

- [ ] Final name: Lineage Control Tower, Exposure Ops Center, or dbt Lineage Monitoring Dashboard?
- [ ] Are the names for the new consumers fine (Demand Forecast App, Merchandising Copilot, Finance Q&A Agent, Store Ops Hub)?
- [ ] Lime: option A (chrome only) or option B (lime as healthy)?
- [ ] Where will the dataset be generated: this chat, a new Claude chat, or Claude Code?
- [ ] How do you plan to build in Claude Code: generating Tableau workbook files, a Tableau integration, or using it as a pair while you build by hand?
- [ ] Please attach the dashboard-building skill and the functional dashboards ideas list before the mockup phase
- [ ] Does Verata have a brand typeface you'd want for the write-up and mockup, even if Tableau Public cannot use it?
- [ ] Any fictional company name you prefer over Acme Retail Co.?
