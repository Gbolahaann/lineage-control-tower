"""Write docs/data_dictionary.md from the generated CSVs plus the descriptions below.

Every column in every table must have a description here, or generation fails.
That keeps the dictionary honest as the generator evolves.
"""

from __future__ import annotations

import pandas as pd

from .io import DATA_DIR, DOCS_DIR

TABLES = {
    "dim_nodes": dict(
        group="Catalog",
        grain="One row per source, dbt model, BI semantic object or exposure",
        what="The catalog of everything in Acme's data supply chain, from raw tables to the dashboards, apps and agents "
             "that read them. Every other table joins to it on node_id.",
        source="dbt's manifest.json (sources, models, exposures, owners, materializations, tags, descriptions) plus the BI "
               "tools' metadata APIs for semantic objects (Tableau Metadata API, Power BI Scanner API, Sigma REST API). "
               "Undeclared consumers come from warehouse query history.",
        columns={
            "node_id": "Unique id in dbt's style: resource_type.project.name (e.g. model.acme_core.fct_orders). Exposures found only in query history use the project 'observed'.",
            "node_name": "Machine name (source as schema.table, model name, semantic object name, exposure name).",
            "display_name": "Human-friendly name for labels. Same as node_name except for exposures.",
            "resource_type": "source / model / semantic / exposure.",
            "layer": "Where the node sits in the chain: source, staging, intermediate, mart, semantic, exposure.",
            "layer_order": "0 to 5, left to right in the lineage graph.",
            "platform": "Warehouse the node lives on today (snowflake / databricks / redshift). Migrated marketing nodes say snowflake.",
            "dbt_project": "acme_core, acme_product or acme_marketing. Blank for semantic objects and undeclared consumers.",
            "dbt_job": "The dbt Cloud job that builds this model.",
            "database_name": "Database (Snowflake/Redshift) or catalog (Databricks).",
            "schema_name": "Schema: raw schema for sources, staging / intermediate / marts_<domain> for models.",
            "materialization": "view / table / incremental for models. This is the current state; fct_model_runs has it at run time.",
            "domain": "Business domain: Finance, Commerce, Marketing, Product, Operations, Customer.",
            "owner_name": "Owning person. Blank means no owner (story 8, and the undeclared consumers).",
            "owner_team": "Owning team. Staging models and sources belong to Data Platform.",
            "tags": "Pipe-separated dbt tags (layer, domain, job, pii). Split on the pipe character in Tableau.",
            "has_description": "Whether the node has a description in dbt / the BI tool. Feeds documentation coverage.",
            "test_count": "Number of dbt tests defined on the model. Feeds test coverage.",
            "created_date": "When the node first appeared. Sprawl dashboards and undeclared consumers appear inside the window.",
            "migrated_from_platform": "redshift for nodes moved to Snowflake in story 3, otherwise blank.",
            "migration_date": "Cutover date for migrated nodes.",
            "load_every_minutes": "Sources only: how often the loader (Fivetran, Airbyte...) syncs this table.",
            "warn_after_minutes": "Sources only: freshness warn threshold from the dbt source definition.",
            "error_after_minutes": "Sources only: freshness error threshold.",
            "semantic_object_type": "published_data_source / sigma_dataset / pbi_semantic_model.",
            "connection_type": "extract (keeps its own copy, refreshed on a schedule) or live (queries the warehouse each time).",
            "refreshes_per_day": "Extract refresh schedule for semantic objects.",
            "close_window_refreshes_per_day": "Extra refreshes during month-end close (Finance Close data source).",
            "exposure_type": "dashboard / notebook / ml / data_app / agent / data_hub.",
            "bi_tool": "tableau / sigma / power_bi for BI objects and dashboards.",
            "exposure_url": "Where the product lives (fictional .example URLs).",
            "maturity": "high / medium / low, as declared on the dbt exposure.",
            "access_path": "How the consumer reaches data: bi_semantic_layer, direct_warehouse, dbt_semantic_layer, mcp_server, extract.",
            "build_method": "hand_built or ai_assisted. Story 10's sprawl dashboards are ai_assisted.",
            "is_declared": "false for consumers found only in query history (story 11).",
            "service_principal": "The warehouse login the consumer queries with, used to match query history to exposures.",
            "consumption_type": "What one usage event means for this consumer: view, query, app_session or agent_call.",
        }),
    "dim_owners": dict(
        group="Catalog",
        grain="One row per owner",
        what="The people who own data assets, so the dashboard can turn 'this broke' into 'message this person in this channel'.",
        source="Owner blocks in manifest.json, joined to an HR or Slack directory for channels and on-call rotation.",
        columns={
            "owner_name": "Person's name (fictional).",
            "owner_team": "Team. Six domain teams plus Data Platform.",
            "email": "Fake email on the reserved .example domain.",
            "slack_channel": "Team channel to notify.",
            "on_call_rotation": "yes / no.",
        }),
    "dim_date": dict(
        group="Catalog",
        grain="One row per day, 22 Jul to 19 Oct 2026",
        what="A calendar with Acme's business rhythm built in, so Tableau can filter on close windows or weekends without date math.",
        source="Generated, usually as a dbt model in production.",
        columns={
            "date": "Calendar date.", "year": "Year.", "quarter": "Quarter number.", "month": "Month number.",
            "month_name": "Month name.", "iso_week": "ISO week number.", "week_start": "Monday of the week.",
            "day_of_week": "1 = Monday ... 7 = Sunday.", "day_name": "Day name.", "is_weekend": "Saturday or Sunday.",
            "is_month_end": "Last calendar day of the month.",
            "is_month_end_close_window": "Last 3 or first 3 business days of a month (public holidays ignored).",
            "is_board_prep_window": "The board meeting day and the 3 days before it.",
            "days_before_as_of": "0 on 19 Oct, 1 on 18 Oct, and so on. Handy for 'last N days' filters.",
        }),
    "fct_lineage_edges": dict(
        group="Lineage",
        grain="One row per parent to child link",
        what="The lineage graph itself: which node feeds which.",
        source="manifest.json parent_map / child_map for dbt nodes; BI metadata APIs for links into and out of semantic "
               "objects; warehouse query history for undeclared consumers.",
        columns={
            "edge_id": "Unique edge id.",
            "parent_node_id": "The upstream node.",
            "child_node_id": "The downstream node.",
            "edge_source": "Where the link is known from: manifest (declared in dbt), bi_metadata (BI APIs) or query_history (observed only).",
            "crosses_platform": "true when parent and child live on different warehouses today (e.g. Databricks to Snowflake for Customer 360).",
        }),
    "fct_exposure_upstream": dict(
        group="Lineage",
        grain="One row per exposure and each node upstream of it",
        what="The closure table. Filter on exposure_id to see everything that feeds a product; filter on upstream_node_id "
             "to see every product a node feeds (Blast Radius). Precomputed so Tableau never has to recurse.",
        source="Derived from the edges with a recursive CTE or a Python model in the dbt_ops project.",
        columns={
            "exposure_id": "The consumer.",
            "upstream_node_id": "Any node upstream of it, at any distance.",
            "depth": "Shortest number of hops from the exposure (1 = direct parent).",
        }),
    "fct_lineage_layout": dict(
        group="Lineage",
        grain="One row per node position, or per point along an edge, per layout scope",
        what="x/y coordinates for drawing the lineage graph in Tableau: circles for nodes, lines along the path shelf for edges.",
        source="Derived with a layered layout (layer as x, barycenter ordering for y).",
        columns={
            "layout_scope": "'global' for the full graph, or an exposure node_id for that exposure's own readable layout.",
            "row_type": "node or edge.",
            "node_id": "Node rows only.",
            "edge_id": "Edge rows only.",
            "parent_node_id": "Edge rows only, so set actions can highlight edges.",
            "child_node_id": "Edge rows only.",
            "point_order": "Edge rows only: order of points along the curve. Put it on Path in Tableau.",
            "x": "Horizontal position: layer, nudged right for marts that read other marts.",
            "y": "Vertical position within the layer, centred on 0; higher is nearer the top.",
        }),
    "fct_job_runs": dict(
        group="Runs and quality",
        grain="One row per dbt job run",
        what="Every scheduled, manual and CI run of a dbt Cloud job, with its outcome.",
        source="dbt Cloud Admin API (runs endpoint).",
        columns={
            "job_run_id": "Unique run id.",
            "job_name": "dbt Cloud job (core_hourly, product_every_2h, ci__acme_core ...).",
            "dbt_project": "Project the job belongs to.",
            "platform": "Platform most of the run's models ran on (mixed during the migration).",
            "schedule": "hourly / daily / weekly / on_pull_request.",
            "environment": "prod or ci. Health metrics use prod only.",
            "run_started_at": "Start time (UTC).",
            "run_completed_at": "End time, including the test step.",
            "duration_sec": "Wall-clock duration.",
            "status": "success / error / cancelled.",
            "models_run": "Models that executed (success or error).",
            "models_failed": "Models that errored.",
            "models_skipped": "Models skipped because a parent failed.",
            "tests_failed": "Tests that failed or errored.",
            "triggered_by": "schedule / manual / ci.",
        }),
    "fct_model_runs": dict(
        group="Runs and quality",
        grain="One row per model per job run",
        what="What happened to every model every time it was built. A failed model makes its children skip within the same run.",
        source="run_results.json from each dbt invocation (or Elementary's dbt_run_results table).",
        columns={
            "job_run_id": "The job run this belongs to. Join to fct_job_runs for environment.",
            "node_id": "The model.",
            "platform": "Platform at run time. Migrated models switch from redshift to snowflake mid-window.",
            "materialization": "Materialization at run time (fct_sessions is 'table' until the story 1 fix).",
            "run_started_at": "When the model started (after its parents finished).",
            "run_completed_at": "When it finished.",
            "execution_time_sec": "Runtime in seconds. 0 for skipped models.",
            "status": "success / error / skipped.",
            "rows_affected": "Rows written. Blank for views and failures. 0 for incremental models when the source is stale.",
            "error_category": "compilation / database / timeout / permission / schema_change, or upstream_skip for skipped rows.",
            "error_message": "The adapter's error message.",
        }),
    "fct_test_results": dict(
        group="Runs and quality",
        grain="One row per test execution",
        what="Every dbt test result. Tests run after models (dbt run then dbt test), so a failing test does not skip anything downstream.",
        source="run_results.json from the test step (or Elementary's test results table).",
        columns={
            "test_id": "Unique test id in dbt's style.",
            "test_name": "Test name, e.g. unique_dim_customers_customer_id.",
            "test_type": "not_null / unique / accepted_values / relationships / custom.",
            "node_id": "Model under test.",
            "column_name": "Column under test.",
            "job_run_id": "Job run the test executed in.",
            "run_at": "Execution time.",
            "status": "pass / warn / fail / error.",
            "failures_count": "Rows that failed the test.",
            "severity": "error or warn, as configured. A failing warn-severity test reports status warn.",
        }),
    "fct_source_freshness": dict(
        group="Runs and quality",
        grain="One row per source per hourly freshness check",
        what="How stale each raw table was at each check, against its thresholds.",
        source="sources.json from dbt source freshness.",
        columns={
            "source_node_id": "The source.",
            "checked_at": "Check time (on the hour).",
            "max_loaded_at": "Newest data landed before the check.",
            "lag_minutes": "checked_at minus max_loaded_at.",
            "warn_after_minutes": "Threshold for warn.",
            "error_after_minutes": "Threshold for error.",
            "status": "pass / warn / error.",
        }),
    "fct_semantic_refresh": dict(
        group="BI layer",
        grain="One row per extract refresh of a BI semantic object",
        what="Refreshes of Tableau extracts and Power BI import models. A failed refresh means stale dashboards even when dbt is green (story 6). Live objects have no refreshes.",
        source="Tableau Admin Insights job performance / REST API, Power BI refresh history, Sigma audit logs.",
        columns={
            "refresh_id": "Unique refresh id.",
            "node_id": "The semantic object.",
            "bi_tool": "tableau / power_bi.",
            "refresh_started_at": "Start time.",
            "duration_sec": "Duration.",
            "status": "success / failed / skipped_upstream (an upstream mart failed in its latest dbt run, so the refresh waited).",
            "rows_refreshed": "Rows in the extract after a successful refresh.",
            "error_message": "Why it failed or skipped.",
        }),
    "fct_consumption": dict(
        group="Usage and cost",
        grain="One row per declared consumer per day",
        what="Reported usage for every kind of consumer: dashboard views, app sessions, notebook and model queries, agent calls.",
        source="Tableau Admin Insights TS Events, Power BI activity log, Sigma audit logs; app and agent logs for the rest.",
        columns={
            "date": "Day.",
            "exposure_id": "The consumer.",
            "consumption_type": "view / query / app_session / agent_call.",
            "events": "Number of usage events that day.",
            "unique_consumers": "Distinct viewers, users or calling sessions.",
            "avg_latency_sec": "Average load or response time.",
            "metrics_called": "Agents only: metric lookups made.",
            "failed_calls": "Agents only: calls that errored.",
        }),
    "fct_observed_access": dict(
        group="Usage and cost",
        grain="One row per principal, node and day",
        what="The warehouse's own record of who read which table. A principal with no mapped exposure is an undeclared consumer (story 11).",
        source="Snowflake ACCOUNT_USAGE.ACCESS_HISTORY and QUERY_HISTORY, Databricks system.access.audit and system.query.history, by user, service principal or query tag.",
        columns={
            "date": "Day.",
            "principal": "Login or query tag. BI tools use one tag per semantic object (service:object).",
            "principal_type": "human / service / agent / app.",
            "node_id": "Model read.",
            "query_count": "Queries that day.",
            "bytes_scanned": "Bytes scanned.",
            "mapped_exposure_id": "Declared consumer this principal belongs to. For BI service accounts, the semantic object. Blank means undeclared.",
            "inferred_exposure_id": "Added column: the consumer this traffic belongs to, including the undeclared ones, so they can be shown in lineage.",
        }),
    "fct_warehouse_cost": dict(
        group="Usage and cost",
        grain="One row per node, day, cost type and principal",
        what="Compute cost per node per day, in native units and USD, for building models and for consumers querying them.",
        source="Snowflake QUERY_HISTORY + WAREHOUSE_METERING_HISTORY, Databricks system.billing.usage, Redshift SYS_QUERY_HISTORY, joined to node_id through dbt query tags.",
        columns={
            "date": "Day.",
            "node_id": "Model the cost is attributed to.",
            "platform": "Platform the cost was incurred on (switches for migrated models).",
            "warehouse_or_cluster": "Snowflake warehouse, Databricks cluster/SQL warehouse or Redshift workgroup.",
            "cost_type": "Added column: build (dbt building it) or consumer_query (a direct consumer reading it).",
            "principal": "Added column: for consumer_query rows, which login ran the queries.",
            "compute_units": "Snowflake credits, Databricks DBUs or Redshift RPU-hours.",
            "est_cost_usd": "Estimated cost at illustrative list prices (see config.yaml).",
            "bytes_scanned": "Indicative bytes scanned.",
        }),
    "fct_incidents": dict(
        group="Usage and cost",
        grain="One row per incident",
        what="The team's incident log, for annotations and MTTR. Timestamps are read back from the other tables, so they agree with the data.",
        source="PagerDuty, Jira, incident.io or a Slack incident channel.",
        columns={
            "incident_id": "Incident id.",
            "title": "What happened.",
            "root_node_id": "Node where it started.",
            "started_at": "First bad signal in the data.",
            "resolved_at": "First good signal after it. Blank means still open.",
            "severity": "low / medium / high / critical.",
            "exposures_affected": "Declared exposures downstream of the root.",
            "category": "freshness / schema_change / test / performance, plus migration and semantic_refresh (added).",
        }),
}

ORDER = ["dim_nodes", "dim_owners", "dim_date", "fct_lineage_edges", "fct_exposure_upstream", "fct_lineage_layout",
         "fct_job_runs", "fct_model_runs", "fct_test_results", "fct_source_freshness", "fct_semantic_refresh",
         "fct_consumption", "fct_observed_access", "fct_warehouse_cost", "fct_incidents"]


def _example(s: pd.Series) -> str:
    v = s.dropna()
    if v.empty:
        return ""
    text = str(v.iloc[len(v) // 2])
    return (text[:60] + "...") if len(text) > 60 else text


def write_dictionary(cfg: dict) -> None:
    lines = [
        "# Data dictionary",
        "",
        "Generated by `generator/generate.py`. Do not edit by hand.",
        "",
        f"Acme Retail Co. is fictional. All data is synthetic, from {cfg['dates']['start']} to {cfg['dates']['end']} "
        f"(UTC), seed {cfg['seed']}. Joins: everything keys on `node_id` (an exposure's id is also a node_id), plus a date "
        "or timestamp. Facts that carry `job_run_id` join to `fct_job_runs` for environment (prod / ci).",
        "",
        "| Table | Group | Grain | Rows |",
        "|---|---|---|---|",
    ]
    frames = {t: pd.read_csv(DATA_DIR / f"{t}.csv", low_memory=False) for t in ORDER}
    for t in ORDER:
        lines.append(f"| [{t}](#{t}) | {TABLES[t]['group']} | {TABLES[t]['grain']} | {len(frames[t]):,} |")

    for t in ORDER:
        meta, df = TABLES[t], frames[t]
        missing = [c for c in df.columns if c not in meta["columns"]]
        if missing:
            raise ValueError(f"Data dictionary is missing descriptions for {t}: {missing}")
        lines += ["", f"## {t}", "", f"**What it is.** {meta['what']}", "",
                  f"**Where it comes from in a real company.** {meta['source']}", "",
                  f"**Grain.** {meta['grain']}. **Rows:** {len(df):,}.", "",
                  "| Column | Type | Null % | Example | Description |", "|---|---|---|---|---|"]
        for c in df.columns:
            dtype = {"object": "text", "str": "text", "string": "text", "float64": "number", "int64": "integer",
                     "bool": "boolean"}.get(str(df[c].dtype), str(df[c].dtype))
            if df[c].dtype == object and df[c].dropna().astype(str).isin(["true", "false"]).all() and df[c].notna().any():
                dtype = "boolean"
            null_pct = f"{df[c].isna().mean() * 100:.0f}%"
            example = _example(df[c]).replace("|", "\\|")
            lines.append(f"| `{c}` | {dtype} | {null_pct} | {example} | {meta['columns'][c]} |")
    (DOCS_DIR / "data_dictionary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
