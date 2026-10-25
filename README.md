# Lineage Control Tower

A reference design for monitoring a modern data team's data products (BI dashboards, Databricks apps, AI agents and Claude-built data hubs), traced back through dbt models to the raw sources that feed them, across Snowflake, Databricks and Redshift.

**The data model is the product. The BI layer is interchangeable.**

This repo holds the synthetic dataset, the generator that builds it, the Tableau-ready mart layer, the approved HTML mockup and the Tableau workbook (11 dashboards, built by code; latest version `tableau/versions/v51-linkedin.twbx`). The flagship dashboard is a Tableau Public workbook, with a Claude-built data hub as the second build. The full design is in [docs/spec.md](docs/spec.md).

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
  Lineage_Control_Tower_Project_Dashboard.twb   the master: Tableau-saved, data source connected (multi-fact model)
  tools/build_workbook.py  builds the whole workbook from the master (run it, open the .twbx)
  tools/lct_build/   one module per dashboard (health, run, fresh, lineage, blast, quality, perf, usage, gov, about)
                     plus the shared shell, cards, shapes and the Lineage side panel
  tools/twbdiff.py   diffs a Tableau-saved copy against a build (how review edits get folded back in)
  tools/validate_twb.py  checks a workbook against Tableau's schema and manifest rules before it is sent
  build/             the latest build
  versions/          every build ever sent (v01 to v51) and CHANGELOG.md: what changed in each and why
  Image/, Shapes/    nav buttons, icons and custom shapes the build embeds
docs/
  spec.md            the project spec
  data_dictionary.md every raw table and column, what it means and where it comes from in a real company
  tableau-data-model.md  the Tableau data model: relationships, mart grains, parameters, hard charts
  tableau-build-plan.md  the build plan: every dashboard's container tree, sizes and decisions
  tableau-calc-pack.md   every calculated field, with its comment header
  skill/tableau-style/   the Tableau style skill this was built with, and the build techniques it learned
  img/               prototype screenshots and the check images from each build
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

## The Tableau workbook

Eleven dashboards: Health overview, Run & failures, Freshness & SLAs, Lineage explorer, Blast radius, Data quality,
Performance & cost, Usage & adoption, Governance, About & how to use, and a Documentation page for developers.

```bash
python3 tableau/tools/build_workbook.py --tag my-version   # writes tableau/build/ and tableau/versions/my-version.twbx
```

Nothing is clicked together by hand. The builder writes the workbook XML from the master file: calculated fields
(every one with a `// name` comment header), sheets, dashboards, containers, parameters and actions. Each build is
checked against Tableau's schema, and every chart drawn in code is checked to fit its zone before the file is written,
so there are no scroll bars. Two builds of the same code are byte-identical.

### How the shapes are drawn: map layers as a drawing board

Tableau has no "draw a rounded box here" tool, so most of the custom visuals (the exposure tiles, alert cards, the
lineage graph, pills, chips and the tables with row lines) are drawn on a **map**.

- **The map is a blank canvas.** A map sheet with the background map switched off and its axes fixed to a set range
  becomes a sheet of paper exactly as many pixels wide and tall as its zone. One unit of latitude or longitude is
  100 px, so the builder can say "put this at x = 120 px, y = 40 px" and Tableau puts it there.
- **Every shape is a polygon.** `MAKEPOINT(y, x)` turns a pair of numbers into a point; a polygon mark joins points in
  the order of a "path" field. Four points make a rectangle. A rounded rectangle uses 88 points, 22 round each corner,
  worked out with sine and cosine in the calc, so pills and cards get real rounded corners.
- **Map layers stack like tracing paper.** Each layer is one kind of mark: an outline polygon, a fill polygon on top
  of it, then a layer of text, then an icon. A pill is two polygons (the outline 1 px bigger than the fill) and a word.
- **Rows of data are the points.** A polygon needs one data row per corner point. Where a table has enough rows (90 days
  of history per model, 90 dates), each row becomes a point. Where it does not, a "carrier" borrows the 90 daily rows of
  a few models just to have points to draw with.
- **Text is placed by measurement.** Tableau centres a label on its point and does not wrap it, so the builder measures
  every word with the same font at build time, places it at half its width from the edge it should line up with, and
  wraps long text into lines itself.
- **Values that depend only on the filters are worked out in advance.** For every period, platform and selection,
  the builder computes the numbers and positions and writes them as `CASE` calcs, so Tableau only switches between
  them. The numbers stay exact and the dashboards stay fast.

The full playbook, including what did not work, is in
[docs/skill/tableau-style/references/build-techniques.md](docs/skill/tableau-style/references/build-techniques.md).

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
