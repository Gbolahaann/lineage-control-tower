"""fct_incidents: the incident log a team would keep in PagerDuty, Jira or a Slack channel.

Every timestamp here is read back out of the generated tables rather than copied
from config, so the incident log always agrees with what the data shows
(started = first bad signal, resolved = first good signal after it).
"""

from __future__ import annotations

import pandas as pd

from .catalog import World


def _downstream_exposures(w: World, closure: pd.DataFrame, node_ids: list[str]) -> int:
    declared = set(w.nodes.loc[(w.nodes["resource_type"] == "exposure") & w.nodes["is_declared"], "node_id"])
    hit = closure.loc[closure["upstream_node_id"].isin(node_ids), "exposure_id"]
    return int(len(set(hit) & declared))


def build_incidents(w: World, closure, job_runs, model_runs, tests, freshness, semantic) -> pd.DataFrame:
    cfg = w.cfg
    s = cfg["stories"]
    prod = set(job_runs.loc[job_runs["environment"] == "prod", "job_run_id"])
    mr = model_runs[model_runs["job_run_id"].isin(prod)]
    out = []

    def add(title, root, started, resolved, severity, category, affected_roots=None):
        out.append(dict(title=title, root_node_id=root, started_at=started, resolved_at=resolved, severity=severity,
                        exposures_affected=_downstream_exposures(w, closure, affected_roots or [root]),
                        category=category))

    if s["s01_slow_creep"]["enabled"]:
        m = w.id_of[s["s01_slow_creep"]["model"]]
        runs = mr[(mr["node_id"] == m) & (mr["status"] == "success")].set_index("run_started_at")["execution_time_sec"]
        baseline = runs[: s["s01_slow_creep"]["creep_start"]].mean()
        weekly = runs.rolling("7D").mean()
        breach = weekly[weekly > baseline * 1.5].index.min()      # when someone would notice: +50%
        fixed = runs[s["s01_slow_creep"]["fixed_on"]:].index.min()
        add("fct_sessions runtime and cost up 50%+ (full-refresh table that should be incremental)",
            m, breach, fixed, "medium", "performance")

    if s["s02_monday_test_failure"]["enabled"]:
        t = tests[(tests["test_name"] == s["s02_monday_test_failure"]["test"]) & (tests["status"] == "fail")]
        add("unique_dim_customers_customer_id fails every Monday (dedupe bug in weekend backfill)",
            w.id_of[s["s02_monday_test_failure"]["model"]], t["run_at"].min(), None, "low", "test")

    if s["s03_platform_migration"]["enabled"]:
        for wave in s["s03_platform_migration"]["waves"]:
            ids = [w.id_of[m] for m in wave["models"]]
            bad = mr[mr["node_id"].isin(ids) & (mr["status"] == "error")
                     & mr["error_message"].str.contains("cutover", na=False)]
            if bad.empty:
                continue
            after = mr[mr["node_id"].isin(ids) & (mr["run_started_at"] > bad["run_started_at"].max())]
            add(f"Redshift to Snowflake cutover errors ({wave['name']})", ids[0],
                bad["run_started_at"].min(), after["run_completed_at"].min(), "medium", "migration", ids)

    if s["s04_schema_change"]["enabled"]:
        ids = [w.id_of[m] for m in s["s04_schema_change"]["broken_models"]]
        bad = mr[mr["node_id"].isin(ids) & (mr["error_category"] == "schema_change")]
        ok = mr[mr["node_id"].isin(ids) & (mr["status"] == "success") & (mr["run_started_at"] > bad["run_started_at"].max())]
        add(f"Column rename in raw_hubspot ({s['s04_schema_change']['renamed_column']}) breaks HubSpot models",
            w.id_of["raw_hubspot.deals"], bad["run_started_at"].min(), ok["run_completed_at"].min(),
            "high", "schema_change", ids)

    def freshness_incident(source, title, severity):
        sid = w.id_of[source]
        f = freshness[freshness["source_node_id"] == sid].sort_values("checked_at")
        bad = f[f["status"] != "pass"]
        # The planted episode is the last run of non-pass checks for this source
        last_bad = bad["checked_at"].max()
        prior_pass = f[(f["checked_at"] < last_bad) & (f["status"] == "pass")]["checked_at"].max()
        start = bad[bad["checked_at"] > prior_pass]["checked_at"].min()
        after = f[(f["checked_at"] > last_bad) & (f["status"] == "pass")]["checked_at"].min()
        add(title, sid, start, None if pd.isna(after) else after, severity, "freshness")

    if s["s05_freshness_cascade"]["enabled"]:
        sid = w.id_of[s["s05_freshness_cascade"]["source"]]
        f = freshness[(freshness["source_node_id"] == sid)
                      & (freshness["checked_at"].between(pd.Timestamp(s["s05_freshness_cascade"]["stops_loading_at"]),
                                                         pd.Timestamp(s["s05_freshness_cascade"]["resumes_at"]) + pd.Timedelta(hours=2)))]
        bad = f[f["status"] != "pass"]
        add("raw_stripe.payments stopped loading overnight into month-end close", sid,
            bad["checked_at"].min(), f[(f["status"] == "pass") & (f["checked_at"] > bad["checked_at"].max())]["checked_at"].min(),
            "critical", "freshness")

    if s["s06_green_dbt_broken_dashboard"]["enabled"]:
        sid = w.id_of[s["s06_green_dbt_broken_dashboard"]["semantic_object"]]
        r = semantic[semantic["node_id"] == sid]
        bad = r[r["status"] == "failed"]
        bad = bad[bad["refresh_started_at"] >= pd.Timestamp(s["s06_green_dbt_broken_dashboard"]["failing_from"])]
        ok = r[(r["status"] == "success") & (r["refresh_started_at"] > bad["refresh_started_at"].max())]
        add("pds_commerce_sales extract failing (expired Snowflake OAuth token); dbt green, dashboards stale",
            sid, bad["refresh_started_at"].min(), ok["refresh_started_at"].min(), "high", "semantic_refresh")

    if s["s09_live_issues_today"]["enabled"]:
        freshness_incident(s["s09_live_issues_today"]["warn_source"],
                           "raw_wms.inventory loads delayed (freshness warn)", "low")

    df = pd.DataFrame(out).sort_values("started_at").reset_index(drop=True)
    df.insert(0, "incident_id", [f"INC-{i:03d}" for i in range(1, len(df) + 1)])
    return df
