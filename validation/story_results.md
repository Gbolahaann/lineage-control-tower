# Story validation results

Generated from data as of 2026-10-19 23:59 UTC.

| # | Story | Result | Evidence | Chart |
|---|---|---|---|---|
| 1 | Slow creep | PASS | runtime x2.18 at peak, x0.17 after fix; cost tracks runtime | [story_01_slow_creep.png](charts/story_01_slow_creep.png) |
| 2 | Recurring Monday failure | PASS | fails on exactly the 11 Mondays from 2026-08-10 to 2026-10-19 | [story_02_monday_test_failure.png](charts/story_02_monday_test_failure.png) |
| 3 | Platform migration | PASS | Redshift $1,859 before / $0 after; cutover-day success 90% vs 99.7% | [story_03_platform_migration.png](charts/story_03_platform_migration.png) |
| 4 | Schema change incident | PASS | errored: stg_hubspot__companies, stg_hubspot__contacts, stg_hubspot__deals; red dashboards at 13:00: 4; recovered same day: True | [story_04_schema_change.png](charts/story_04_schema_change.png) |
| 5 | Freshness breach cascade | PASS | 8 error checks, all inside the outage; 8/8 finance exposures red at 06:00 on 1 Oct | [story_05_freshness_cascade.png](charts/story_05_freshness_cascade.png) |
| 6 | Green dbt, broken dashboard | PASS | 3 exposures red at 13 Oct 12:00 (Board KPI Pack, Executive Revenue Dashboard, Supply Chain Ops) with only a refresh failure; upstream dbt 100% green: True | [story_06_green_dbt_broken_dashboard.png](charts/story_06_green_dbt_broken_dashboard.png) |
| 7 | Zombie dashboard | PASS | max 3 views/month; $641/view vs next highest $1.20; only zombie flagged: ['Web Funnel Analysis'] | [story_07_zombie_dashboard.png](charts/story_07_zombie_dashboard.png) |
| 8 | Orphan exposure | PASS | unowned declared exposures: ['Pricing Experiment Analysis'] | [story_08_orphan_exposure.png](charts/story_08_orphan_exposure.png) |
| 9 | Live issues today | PASS | status at data_as_of: {'green': 15, 'amber': 9} | [story_09_live_issues_today.png](charts/story_09_live_issues_today.png) |
| 10 | Dashboard sprawl | PASS | 5 ai_assisted dashboards, all on pds_finance_revenue; usage falling for all: True | [story_10_dashboard_sprawl.png](charts/story_10_dashboard_sprawl.png) |
| 11 | Undeclared consumers | PASS | 3 unmapped principals (r.alvarez@acme-retail.example, svc_jobs_runner, svc_shared_analytics), first seen 21 Sep; agent = 66% of cost on its tables (28d) | [story_11_undeclared_consumers.png](charts/story_11_undeclared_consumers.png) |

## Thresholds

- `zombie_max_events_30d`: 10
- `zombie_min_cost_per_event_usd`: 5.0
- `incremental_min_rows`: 10000000
- Incremental candidates as of 20 Sep: fct_sessions (highest runtime trend among the rest: +15%)
- Incremental candidates as of 01 Oct: fct_sessions (highest runtime trend among the rest: +10%)
- Incremental candidates as of 19 Oct: none (highest runtime trend among the rest: +26%)
