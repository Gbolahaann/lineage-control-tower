# Lineage Control Tower: Phase 3 hand-off (HTML mockup)

Owner: Gbolahan Adebayo. Status as of 21 Oct 2026: Phase 1 (spec) and Phase 2 (synthetic dataset) are done. Phase 3 is a clickable HTML mockup of all 9 tabs plus About, built on the real generated data. This document is everything a fresh conversation needs to start Phase 3.

Read this first, then `spec.md` for the full design. `data_dictionary.md` describes the full dataset. The mockup uses the compact `mockup_bundle.json` described below.

---

## 1. What the project is (in two lines)

A reference design for monitoring a data team's data products (BI dashboards, Databricks apps, AI agents, Claude-built hubs), traced back through dbt models to raw sources across Snowflake, Databricks and Redshift. Flagship build: Tableau Public. Second build: a Claude-built data hub. Pitch: **the data model is the product, the BI layer is interchangeable.**

## 2. Decisions already made (do not re-open unless asked)

| Topic | Decision |
|---|---|
| Name | Lineage Control Tower |
| Company | Acme Retail Co. (fictional), 3 platforms, 3 dbt projects, 6 domains, 7 teams (6 domain + Data Platform), 15 owners |
| Window | 22 Jul to 19 Oct 2026, UTC. `data_as_of` = 2026-10-19 23:59 |
| Scale | 27 sources, 82 models (30 stg / 20 int / 32 marts), 12 BI semantic objects, 27 exposures (19 declared + 5 AI sprawl + 3 undeclared) |
| Baseline reliability | ~97.5% prod job success; model-level run success ~99.8% |
| Tests | Do not block downstream models (dbt run then dbt test). A failing test makes an exposure amber, not red |
| Migration | Two waves: HubSpot/Sales on 3 Sep, ads/marketing on 11 Sep. Models stay in acme_marketing but run on Snowflake |
| Undeclared consumers | Are rows in dim_nodes with `is_declared = false`; `mapped_exposure_id` is null in observed access; `inferred_exposure_id` links them |
| BI service accounts | In observed access, `mapped_exposure_id` holds the semantic object they refresh |
| Cost | `cost_type` = build or consumer_query; consumer rows carry the `principal` |
| Thresholds | Zombie: < 10 events in 30 days AND > $5 allocated cost per event. Incremental candidate: materialization table AND > 10M rows AND runtime trend > +25% |
| Design | Verata palette; Signal Lime in chrome only (option A, recommended in the spec, not formally confirmed); muted status set; platforms take the three blues |
| Random noise | Switched off on headline story days so each story reads on its own |

Still open from the spec: final name confirmation, lime option A vs B, Verata brand typeface for the mockup, how the Tableau build will be done in Claude Code. The dashboard-building skill (`tableau-style`) exists in Gbolahan's skills; the "functional dashboards ideas list" has not been shared yet and should be asked for.

## 3. The 11 planted stories (all validated)

| # | Story | When | Where it should show in the mockup |
|---|---|---|---|
| 1 | Slow creep: fct_sessions (Databricks) runtime 26 to 56 min and cost doubles, then made incremental (4.4 min) | 20 Aug to 1 Oct, fixed 4 Oct | Performance & Cost |
| 2 | unique_dim_customers_customer_id fails every Monday, still open | Mondays from 10 Aug, incl. 19 Oct | Data Quality, Health Overview |
| 3 | Marketing models migrate Redshift to Snowflake; Redshift cost to $0; cutover-day success ~90% | 1 to 15 Sep | Performance & Cost, Run Monitor |
| 4 | Column rename in raw_hubspot: 3 staging models error, downstream skips, 4 dashboards red; manual rerun 15:42 recovers | 7 Sep, 08:40 to 15:42 | Run Monitor, Blast Radius |
| 5 | raw_stripe.payments stops loading ~14h into month-end close; freshness error 02:00 to 09:00; all 8 finance exposures red | 30 Sep 20:00 to 1 Oct 10:00 | Freshness, Health Overview, Blast Radius |
| 6 | pds_commerce_sales extract fails (expired OAuth) while dbt is 100% green; 3 dashboards stale | 12 Oct 00:00 to 14 Oct ~14:00 | Lineage Explorer, Usage |
| 7 | Web Funnel Analysis: 1 view in 30 days, $641 per view | Whole period | Usage & Adoption, Performance |
| 8 | Pricing Experiment Analysis has no owner | Whole period | Governance |
| 9 | Today: Monday test failure + raw_wms.inventory freshness warn; no red, 10 amber, 17 green | 19 Oct | Health Overview |
| 10 | 5 AI-assisted near-duplicate dashboards on pds_finance_revenue, launch spikes then fade | 7 Sep onward | Usage & Adoption, Governance |
| 11 | Unregistered pricing agent (svc_shared_analytics) + scheduled notebook + personal Claude hub; agent = 66% of cost on fct_orders + dim_products | 21 Sep onward | Governance, Blast Radius, Usage |

Validation charts for each story are in `charts/` (story_01 ... story_11).

## 4. Health logic (the core calculation)

Status is never stored as a fact. It is derived from the latest upstream state at a moment in time:

- **Red:** any upstream model errored in its latest prod run, OR any upstream source in freshness error at its latest check, OR an upstream semantic object's latest refresh failed
- **Amber:** any upstream test failing/warning in its latest execution, OR any upstream source in freshness warn
- **Green:** everything else. **Grey:** exposure did not exist yet
- **Trust badge:** Green = Trusted, Amber = Use with caution, Red = Do not use
- **Health score:** 40% upstream run success + 30% upstream test pass rate + 30% upstream freshness compliance, last 7 days

The bundle precomputes this per day, so the mockup does not need to re-implement it.

## 5. The mockup data bundle

`mockup_bundle.json` (5.7 MB) = `{meta, tables: {name: {columns: [...], rows: [[...]]}}}`. The same tables are also in `mockup/data/*.csv` in the repo.

| Table | Rows | Grain | Used by |
|---|---|---|---|
| nodes | 148 | one per source / model / semantic object / exposure | all tabs |
| owners | 15 | one per owner (team, email, Slack, on call) | Blast Radius, Governance |
| dates | 90 | calendar with weekend, close window, board prep flags | filters |
| edges | 192 | parent to child links, with `edge_source` and `crosses_platform` | Lineage |
| closure | 543 | exposure x every upstream node, with depth | Lineage, Blast Radius |
| layout | 5,656 | x/y for nodes and 6-point edge curves; `layout_scope` = global or an exposure_id | Lineage Explorer graph |
| exposure_status_daily | 2,430 | exposure x day: `status_eod`, `detail_eod`, `worst_status`, `worst_detail` | Health Overview, date slider |
| node_status_daily | 10,890 | node x day, same columns, for colouring lineage nodes | Lineage Explorer |
| incident_snapshots | 1184 | status of every node and exposure at the peak of each incident | "replay incident" |
| kpi_daily | 90 | day: run/job/test/freshness/refresh success %, errors, skips, test failures, cost by platform, exposures at risk | KPI tiles + sparklines |
| model_daily | 7,380 | model x day: runs, errors, skipped, avg runtime, rows, materialization, platform, build cost | Run Monitor, Performance |
| test_daily | 6,112 | model x day: tests run, fails, warns | Data Quality heatmap |
| test_summary | 166 | one per test: executions, fails, warns, last status, failure days in 30d | Data Quality |
| freshness_daily | 2,430 | source x day: max lag, warn/error checks, thresholds | Freshness calendar |
| freshness_latest | 27 | latest check per source | Freshness bullet chart |
| semantic_refresh | 2,664 | every BI extract refresh with status and error | Lineage, Usage |
| consumption | 1,848 | declared consumer x day: events, unique consumers, latency, agent calls | Usage |
| observed_access | 3,979 | principal x node x day from query history; null `mapped_exposure_id` = undeclared | Governance, Blast Radius |
| cost_daily | 8,745 | node x day x cost_type (x principal): USD | Performance & Cost |
| incidents | 8 | incident log with start, resolve, severity, category | annotations, MTTR |
| job_runs_recent | 139 | every job run in the last 3 days | Run Monitor Gantt |
| job_daily | 463 | job x day: runs, errors, avg duration | Run Monitor |
| model_errors | 163 | every prod model error with message | Run Monitor table |
| node_impact | 121 | node: downstream exposures, consumers 30d, failure rate 30d, risk score, undeclared consumers | Blast Radius |
| exposure_metrics_30d | 24 | exposure: allocated cost 30d, events 30d, cost per event, zombie flag | Usage, Performance |

Joins: everything keys on `node_id` (exposure ids are node ids). Timestamps are UTC strings.

## 6. Design system

| Role | Colour |
|---|---|
| Navy Blue (nav, titles, Redshift) | #002C55 |
| Intelligence Blue (selection, links, Snowflake) | #005FAE |
| Sky Blue (secondary, Databricks) | #83C7EB |
| Signal Lime (active tab, chips; chrome only) | #C7FFA4 |
| Off White (page background) | #F5F5F3 |
| White (cards) | #FFFFFF |
| Healthy / Warning / Critical / No data | #2F9E6B / #E8A33D / #D2453F / #A3ADB8 |

Status colour always pairs with an icon or label. Desktop 1400 x 900, phone layout for Health Overview. Every tab: title as a question, one-line subtitle, data-last-refreshed stamp, info button. Shared selection model: a selected exposure and a selected node carry across tabs. Global filters: date range, platform, domain, owner team, environment, BI tool.

## 7. What Phase 3 should produce

- One clickable HTML mockup with all 9 tabs + About, in the build order 1, 2, 3, 4, 7, 8, 6, 5, 9, About
- Built on `mockup_bundle.json`, not placeholder numbers, so every story can be seen before any Tableau time is spent
- A date control (as-of day) driven by `exposure_status_daily` / `node_status_daily`, defaulting to 19 Oct
- Lineage graph drawn from `layout` (global and per-exposure scopes), nodes coloured from `node_status_daily`
- It should be able to grow into the Claude-built data hub in Phase 5, so structure it cleanly
- Sign-off gate: layout, colours and interactions agreed

## 8. Gotchas learned in Phase 2

1. Use `worst_status` for "was anything wrong today" and `status_eod` for "state at close of day". End-of-day alone hides stories 4 and 5.
2. Skipped models are a consequence, errors are the cause. Do not count skips as failures.
3. Runtime trends are skewed by the Sunday full-refresh job (e.g. fct_gl_journal shows +35%). Note it or exclude full-refresh runs.
4. The incremental-candidate flag is empty on 19 Oct because story 1 was fixed; it shows fct_sessions when the as-of date is 20 Sep to 3 Oct.
5. Environment matters: health uses prod only; CI runs exist in the full data.
6. Agent usage reporting is forward-looking; label it so in the About tab.

## 9. Kickoff prompt for the new conversation

> I'm building Lineage Control Tower, a portfolio project. Phases 1 (spec) and 2 (synthetic dataset) are done. Attached: phase3_handoff.md (read first), spec.md, data_dictionary.md, mockup_bundle.json and the story validation charts. Use my tableau-style skill. Phase 3 is a clickable HTML mockup of all 9 tabs plus About, built on the real data in mockup_bundle.json, with an as-of date control defaulting to 19 Oct 2026. Before building, confirm your understanding of the tabs and the data mapping in section 5, ask me about the open questions in section 2 (lime option, brand typeface, and my functional dashboards ideas list), and propose the layout for tab 1 first.
