# Lineage Control Tower

A reference design for monitoring a modern data team's data products (BI dashboards, Databricks apps, AI agents and Claude-built data hubs), traced back through dbt models to the raw sources that feed them, across Snowflake, Databricks and Redshift.

**The data model is the product. The BI layer is interchangeable.**

This repo holds the synthetic dataset, the generator that builds it, the Tableau-ready mart layer, the approved HTML mockup and the Tableau workbook. The flagship dashboard is a Tableau Public workbook, with a Claude-built data hub as the second build. The full design is in [docs/spec.md](docs/spec.md).

> Acme Retail Co. is fictional. Every name, email, number and URL in this repo is synthetic. No real company, client or employer data is used anywhere.

## Quick start

```bash
pip install -r generator/requirements.txt
python generator/generate.py          # writes data/*.csv and docs/data_dictionary.md (~15s)
python validation/check_world.py      # sanity checks on the lineage graph + layout previews
python validation/check_stories.py    # proves all 11 planted stories are in the data
```

The seed is fixed, so every run produces byte-identical CSVs. `python generator/generate.py --no-stories` gives the same company with every planted story switched off, which is handy for before/after comparisons.

## What's inside

```
generator/
  config.yaml        seed, dates, job schedules, failure rates, usage rhythm, prices, thresholds, all 11 stories
  world.yaml         the company: teams, owners, sources, dbt models, BI semantic objects, exposures
  generate.py        entry point
  lct/               one module per concern (catalog, graph, runs, freshness, semantic, consumption, cost, incidents, stories)
  aggregate.py       rolls the raw tables up into the shared logic behind the mockup and the marts
  marts.py           writes the Tableau-ready mart layer (the dbt_ops layer a real team would build)
data/                15 raw CSVs (see the dictionary)
  marts/             14 Tableau-ready tables the workbook connects to
mockup/
  lineage-control-tower.html   the approved clickable prototype of all 9 tabs (open in a browser)
  src/               mockup source, assembled by src/build.py
  data/lct_agg.json  the aggregate the mockup and marts are built from
tableau/
  Lineage_Control_Tower_Project_Dashboard.twb   the workbook, data source connected (multi-fact model)
docs/
  spec.md            the project spec
  data_dictionary.md every raw table and column, what it means and where it comes from in a real company
  tableau-data-model.md  the Tableau data model: relationships, mart grains, parameters, hard charts
  phase4_handoff.md  where the Tableau build stands and what comes next
validation/
  check_world.py     graph sanity checks
  check_stories.py   one pass/fail check and one chart per story
  health.py          the exposure RAG logic from the spec, in Python
  story_results.md   latest results
  charts/            validation charts
```

### From raw data to Tableau

```bash
python generator/aggregate.py data mockup/data/lct_agg.json          # shared logic
python generator/marts.py data mockup/data/lct_agg.json data/marts    # Tableau-ready marts
python mockup/src/build.py mockup/src mockup/data/lct_agg.json mockup/lineage-control-tower.html
```

Tableau connects to `data/marts/`, not the raw tables. A multi-fact model cannot mix a dimension from one fact table with a measure from another, so the cross-table graph logic (exposure status, upstream culprits, reachability, lineage layout) is computed in the mart layer, the way a `dbt_ops` project would do it. See [docs/tableau-data-model.md](docs/tableau-data-model.md).

## The company

| | |
|---|---|
| Window | 22 Jul to 19 Oct 2026 (90 days, UTC) |
| Platforms | Snowflake (acme_core), Databricks (acme_product), Redshift (acme_marketing, migrating to Snowflake) |
| Nodes | 27 sources, 82 dbt models (30 staging, 20 intermediate, 32 marts), 12 BI semantic objects, 27 exposures |
| Exposures | 19 declared (12 BI dashboards, 1 ML model, 1 notebook, 2 data apps, 2 agents, 1 Claude hub) + 5 AI-assisted sprawl dashboards + 3 undeclared consumers |
| Teams | 15 owners across 6 domain teams and Data Platform |
| dbt jobs | hourly, every 2h, every 4h, daily, weekly full refresh, plus slim CI on pull requests |

## How the data is generated

The generator is a small simulation, not random rows:

1. **Build the world** from `world.yaml`: nodes, edges, owners, tests.
2. **Precompute the graph tables** Tableau needs: the closure table (`fct_exposure_upstream`) and x/y layouts (`fct_lineage_layout`) for a global view and one per exposure.
3. **Lay down source loads**, including outages, so freshness is a consequence of real gaps.
4. **Replay 90 days of dbt Cloud**, job run by job run, models in dependency order. A failed model makes its children skip; tests run after models.
5. **Check freshness hourly**, and **refresh BI extracts** (a refresh waits if a parent mart failed).
6. **Generate usage** (reported) and **warehouse access** (observed), then **cost** from runtimes and queries.
7. **Read the incident log back out** of everything above.

Exposure health (red / amber / green) is never written into the data. It is derived from upstream state, exactly as the dashboard will derive it. See `validation/health.py`.

## The 11 planted stories

| # | Story | When |
|---|---|---|
| 1 | Slow creep: fct_sessions doubles in runtime and cost, then is made incremental | 20 Aug to 1 Oct, fixed 4 Oct |
| 2 | Recurring Monday failure: unique test on dim_customers | Every Monday from 10 Aug |
| 3 | Platform migration: marketing models move from Redshift to Snowflake | 1 to 15 Sep |
| 4 | Schema change: a column rename in raw_hubspot breaks 3 models and 4 dashboards | 7 Sep |
| 5 | Freshness cascade: raw_stripe.payments stops loading into month-end close | 30 Sep to 1 Oct |
| 6 | Green dbt, broken dashboard: a Tableau extract fails for two days | 12 to 13 Oct |
| 7 | Zombie dashboard: Web Funnel Analysis, expensive and unused | Whole period |
| 8 | Orphan exposure: Pricing Experiment Analysis has no owner | Whole period |
| 9 | Live issues today: Monday test failure plus a freshness warn | 19 Oct |
| 10 | Dashboard sprawl: 5 AI-assisted near-duplicates with fading usage | 7 Sep onward |
| 11 | Undeclared consumers: an unregistered agent, a notebook and a personal hub | 21 Sep onward |

Each story can be switched off in `config.yaml`. Results and charts: [validation/story_results.md](validation/story_results.md).

## Rebuilding this on real data

Every table maps to an artifact or system table a data team already has: dbt's `manifest.json`, `run_results.json` and `sources.json`; warehouse query history and billing tables; the BI tools' metadata and activity APIs. The data dictionary lists the production source for every table.
