# Lineage Control Tower: Phase 4 hand-off (Tableau build)

Owner: Gbolahan Adebayo. Status as of 21 Oct 2026: the spec, synthetic dataset and HTML mockup are done, and the Tableau data source is connected. Phase 4 is building the workbook in Tableau, starting with the calc pack.

Read in this order:

1. This file
2. `docs/tableau-data-model.md`: the data model, relationships, parameters and the hard-chart plan
3. `mockup/lineage-control-tower.html`: open it in a browser. **It is the approved prototype and the source of truth for layout and content**
4. `docs/spec.md` for the full design and `docs/data_dictionary.md` for the raw tables

Use the `tableau-style` skill in **product style mode** (portfolio).

---

## 1. What changed since Phase 3

| Area | Change |
|---|---|
| Mart layer | `generator/aggregate.py` + `generator/marts.py` turn the raw CSVs into 14 Tableau-ready tables in `data/marts/`. Tableau connects to these, not to `data/*.csv` |
| Why marts | Tableau's multi-fact model cannot mix a dimension from one fact table with a measure from another. Exposure status, lineage colours and blast radius all cross fact tables, so that logic is pre-computed (the `dbt_ops` mart layer a real team would build). About 37k rows instead of 400k |
| Workbook | `tableau/Lineage_Control_Tower_Project_Dashboard.twb`, Tableau 2026.3, multi-fact model: 14 tables, 19 relationships, all checked. Connection is Live while building; switch to Extract before the final save |
| Mockup | Built from `mockup/src/` with `mockup/data/lct_agg.json`. A separate earlier builder (`mockup/build_mockup_data.py` → `mockup_bundle.json`) also exists; the approved mockup uses `lct_agg.json` |
| Thresholds | Aligned to `generator/config.yaml`: retire (zombie) candidate = under 10 uses in 30 days AND over $5 per use; incremental candidate = table over 10M rows with runtime trend above +25%. Results: Web Funnel Analysis is the only zombie, fct_sessions the only incremental candidate (switched 4 Oct) |
| Lineage graph | Built **natively** from `mart_lineage_layout`. Self-built extensions do not run on Tableau Public (only approved Exchange extensions do), so no custom extension |

Rebuild everything from raw:

```
python generator/aggregate.py data mockup/data/lct_agg.json
python generator/marts.py data mockup/data/lct_agg.json data/marts
python mockup/src/build.py mockup/src mockup/data/lct_agg.json mockup/lineage-control-tower.html
```

Headline numbers to reconcile against, for the last 30 days (20 Sep to 19 Oct):

| Metric | Value |
|---|---|
| Run success | 99.85% (+0.10 pp vs prior 30d) |
| Test pass rate | 99.41% |
| Freshness SLA | 99.87% |
| Exposures at risk now | 12 of 27 (4 critical, 8 warning) |
| Mean time to recover | 4.9 h |
| Warehouse cost | $4,189 (−15.1% vs $4,935) |
| Failed model runs | 50 |

## 2. Design decisions made in the mockup (do not re-open unless asked)

| Topic | Decision |
|---|---|
| Canvas | Fixed 1600 × 1000. Left nav 232, header band 70, filter band 52, content padding 20 / 28 |
| Navigation | Left nav grouped Monitor (Health, Runs, Freshness), Investigate (Lineage, Blast radius, Quality), Optimise (Performance, Usage), Govern (Governance), plus About. Active item = Signal Lime fill with Navy text |
| Lime | Option A: Signal Lime in the chrome only (active nav), never inside a chart |
| Theme | Light only, because Tableau Public renders light |
| Font | Libre Franklin in the mockup stands in for **Tableau Book / Medium / Semibold**. Node and model names use a monospace in the mockup; use Tableau Book in the build unless a Public-safe mono is confirmed |
| Cards | White, 1px `#E6E7E2` border, radius 10, padding 14 to 16, 14px gaps, on `#F5F5F3` canvas |
| Brand | Navy `#002C55` (titles, primary button), Intelligence Blue `#005FAE` (accent, selection, window highlight), Sky `#83C7EB`, Lime `#C7FFA4`, Off White `#F5F5F3` |
| Text | Ink `#16212E`, secondary `#4A5563`, muted `#7A838E`, faint `#A5ACB4` |
| Status | Healthy `#2F9E6B` (tint `#EAF6EF`), Warning `#E8A33D` (tint `#FDF3E1`, text `#93600F`), Critical `#D2453F` (tint `#FBEAE9`, text `#A92E29`), No data `#A3ADB8`. Always paired with an icon or label |
| Platforms | Snowflake `#005FAE`, Databricks `#4BAEE3`, Redshift `#5B5FC7`. Validated for lightness, chroma and colourblind separation; the raw brand Navy and Sky failed as chart colours |
| Trust badge | Status 1/2/3 shows as Trusted / Use with caution / Do not use on exposure tiles |
| KPI cards | Title caps 10px, BAN about 24px Navy, change line vs prior period (▲▼, green/red, inverse for cost, MTTR and at-risk), 90-day bar trend with the selected window in the accent. Rate KPIs show **daily failures** as bars, never rates on a cut baseline |
| Period | 7 / 30 / 90 days. At 90 days there is no prior period: show "-" and "no earlier period" |
| Live issue today | `stg_netsuite__journal_lines` failed (compilation error, 19 Oct 21:25) and has not rerun, so 4 finance exposures are Critical right now. Keep it: it gives the Overview a real on-call story |
| Lineage | Columns Sources, Staging, Intermediate, Marts, BI semantic layer, Exposure. Nodes snapped to the layer column, labels without the `stg_`/`int_`/`raw_` prefix, same-layer links drawn as a bracket. Click a node to highlight its full path (parameter action, not hover). Graph / Table toggle replaces the Sankey idea |
| Blast radius copy button | Not possible in Tableau. Use a selectable text box plus a URL action (Slack or mailto) |

## 3. Next step: the calc pack

For each tab in this order: Health, Lineage, Blast radius, Runs, Quality, Freshness, Performance, Usage, Governance.

1. List the sheets, named to the standard (prefix per dashboard, for example `HO Run Success KPI`, `LIN Lineage Graph`)
2. Write every calculated field ready to paste: `// <exact name>` on line 1, a purpose line, one clause per line
3. State which base table each sheet uses, and confirm no sheet mixes two base tables
4. List the parameters and actions it needs

Start with the shared calcs (period window, prior period, platform match by node and by day, status colour and label, selected exposure and node), then Health overview. Stop after Health for review.

Still open: the "functional dashboards ideas list" has not been shared yet. The walkthrough video's narration needs smoothing later.
