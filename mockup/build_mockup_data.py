"""Build the compact dataset for the Phase 3 HTML mockup (and later the Claude-built data hub).

The full dataset is ~60 MB, mostly row-level run and test logs. A browser mockup
needs the same story at a coarser grain, so this script pre-aggregates each tab's
data, computes health status per exposure and per node at the end of every day
(so a mockup can offer a date slider), and writes:

    mockup/data/*.csv          one small CSV per table
    mockup/data/mockup_bundle.json   all of them in one columnar JSON file

Run after generate.py:
    python mockup/build_mockup_data.py
"""

from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "validation"))
from health import Health, load  # noqa: E402

OUT = REPO / "mockup" / "data"
warnings.filterwarnings("ignore", message="obj.round has no effect")   # .round() on frames that include dates
RANK = {"grey": 0, "green": 1, "amber": 2, "red": 3}
SAMPLE_HOURS = [2, 5, 8, 11, 14, 17, 20]     # plus 23:59: catches incidents that start and end within a day
H = Health()
nodes = H.nodes
AS_OF = H.fresh["checked_at"].max().normalize() + pd.Timedelta(hours=23, minutes=59)
DAYS = pd.date_range(H.fresh["checked_at"].min().normalize(), AS_OF.normalize())
EOD = [d + pd.Timedelta(hours=23, minutes=59) for d in DAYS]


def node_status_at(ts) -> pd.DataFrame:
    """Health of every node at ts: worst of its own run, tests, freshness and refresh."""
    mr = H.prod_runs[H.prod_runs["run_completed_at"] <= ts].sort_values("run_completed_at")
    run = mr.groupby("node_id")["status"].last()
    tr = H.prod_tests[H.prod_tests["run_at"] <= ts].sort_values("run_at")
    tl = tr.groupby(["test_id", "node_id"])["status"].last().reset_index()
    tests_bad = tl[tl["status"].isin(["fail", "warn", "error"])].groupby("node_id")["test_id"].count()
    fr = H.fresh[H.fresh["checked_at"] <= ts].sort_values("checked_at").groupby("source_node_id")["status"].last()
    rf = H.refresh[H.refresh["refresh_started_at"] <= ts].sort_values("refresh_started_at").groupby("node_id")["status"].last()
    rows = []
    for n in nodes.itertuples():
        if n.resource_type == "exposure":
            continue
        status, detail = "green", ""
        if n.resource_type == "model":
            r = run.get(n.node_id)
            if r is None:
                status = "grey"
            elif r == "error":
                status, detail = "red", "latest run errored"
            elif r == "skipped":
                status, detail = "grey", "skipped (upstream error)"
            elif tests_bad.get(n.node_id, 0):
                status, detail = "amber", f"{tests_bad[n.node_id]} test(s) failing or warning"
        elif n.resource_type == "source":
            f = fr.get(n.node_id)
            status = {"error": "red", "warn": "amber", "pass": "green"}.get(f, "grey")
            detail = f"freshness {f}" if f and f != "pass" else ""
        elif n.resource_type == "semantic":
            if n.connection_type == "live":
                status, detail = "green", "live connection"
            else:
                s = rf.get(n.node_id)
                status = {"failed": "red", "skipped_upstream": "amber", "success": "green"}.get(s, "grey")
                detail = f"latest refresh {s}" if s and s != "success" else ""
        rows.append((n.node_id, status, detail))
    return pd.DataFrame(rows, columns=["node_id", "status", "detail"])


def _daily(snaps: list, key: str, why: str, day) -> pd.DataFrame:
    """Combine intra-day snapshots into end-of-day status plus worst status of the day."""
    eod = snaps[-1].set_index(key)
    allsnaps = pd.concat(snaps)
    allsnaps["rank"] = allsnaps["status"].map(RANK)
    worst = allsnaps.sort_values("rank").groupby(key).tail(1).set_index(key)
    return pd.DataFrame({
        "date": day, key: eod.index,
        "status_eod": eod["status"].values, "detail_eod": eod[why].values,
        "worst_status": worst.loc[eod.index, "status"].values, "worst_detail": worst.loc[eod.index, why].values,
    })


def build() -> dict:
    t = {}
    keep = ["node_id", "node_name", "display_name", "resource_type", "layer", "layer_order", "platform", "dbt_project",
            "materialization", "domain", "owner_name", "owner_team", "has_description", "test_count", "created_date",
            "migrated_from_platform", "migration_date", "warn_after_minutes", "error_after_minutes",
            "semantic_object_type", "connection_type", "exposure_type", "bi_tool", "maturity", "access_path",
            "build_method", "is_declared", "service_principal", "consumption_type"]
    t["nodes"] = nodes[keep]
    t["owners"] = load("dim_owners")
    t["dates"] = load("dim_date")
    t["edges"] = load("fct_lineage_edges")
    t["closure"] = H.closure

    # Layout: keep every 2nd point on edges (12 -> 6 points still draws a smooth curve)
    lay = load("fct_lineage_layout")
    edge_rows = lay[lay["row_type"] == "edge"]
    lay = pd.concat([lay[lay["row_type"] == "node"], edge_rows[edge_rows["point_order"].isin([1, 3, 5, 8, 10, 12])]])
    t["layout"] = lay.drop(columns=["row_type"]).assign(
        row_type=np.where(lay["node_id"].notna(), "node", "edge"))

    # Health per day: status at end of day AND the worst status seen during the day.
    # End of day alone would hide incidents fixed the same morning (stories 4 and 5).
    print("  computing health snapshots every 3 hours (a few minutes)...")
    exp_daily, node_daily = [], []
    for d, eod in zip(DAYS, EOD):
        moments = [d + pd.Timedelta(hours=h) for h in SAMPLE_HOURS] + [eod]
        e_snaps = [H.status_at(ts) for ts in moments]
        n_snaps = [node_status_at(ts) for ts in moments]
        exp_daily.append(_daily(e_snaps, "exposure_id", "reasons", d))
        node_daily.append(_daily(n_snaps, "node_id", "detail", d))
    t["exposure_status_daily"] = pd.concat(exp_daily)
    t["node_status_daily"] = pd.concat(node_daily)

    # Exact snapshots at the peak of every incident, for "replay this incident" views
    inc = load("fct_incidents", ["started_at", "resolved_at"])
    snaps = []
    for r in inc.itertuples():
        # Midpoint of a resolved incident is its peak; open incidents are shown an hour in
        ts = r.started_at + (r.resolved_at - r.started_at) / 2 if pd.notna(r.resolved_at) else r.started_at + pd.Timedelta(hours=1)
        e = H.status_at(ts).rename(columns={"exposure_id": "node_id", "reasons": "detail"})
        nd = node_status_at(ts)
        snaps.append(pd.concat([e[["node_id", "status", "detail"]], nd]).assign(incident_id=r.incident_id, snapshot_at=ts))
    t["incident_snapshots"] = pd.concat(snaps)[["incident_id", "snapshot_at", "node_id", "status", "detail"]]

    # KPI tiles, one row per day
    jobs = load("fct_job_runs", ["run_started_at"])
    prod_jobs = jobs[jobs["environment"] == "prod"].assign(date=lambda d: d["run_started_at"].dt.normalize())
    mr = H.prod_runs.assign(date=lambda d: d["run_started_at"].dt.normalize())
    tr = H.prod_tests.assign(date=lambda d: d["run_at"].dt.normalize())
    fr = H.fresh.assign(date=lambda d: d["checked_at"].dt.normalize())
    rf = H.refresh.assign(date=lambda d: d["refresh_started_at"].dt.normalize())
    cost = load("fct_warehouse_cost", ["date"])
    executed = mr[mr["status"] != "skipped"]
    kpi = pd.DataFrame(index=DAYS)
    kpi["model_run_success_pct"] = executed.groupby("date")["status"].apply(lambda s: (s == "success").mean() * 100)
    kpi["job_success_pct"] = prod_jobs.groupby("date")["status"].apply(lambda s: (s == "success").mean() * 100)
    kpi["test_pass_pct"] = tr.groupby("date")["status"].apply(lambda s: (s == "pass").mean() * 100)
    kpi["freshness_pass_pct"] = fr.groupby("date")["status"].apply(lambda s: (s == "pass").mean() * 100)
    kpi["refresh_success_pct"] = rf.groupby("date")["status"].apply(lambda s: (s == "success").mean() * 100)
    kpi["model_errors"] = mr[mr["status"] == "error"].groupby("date").size()
    kpi["model_skips"] = mr[mr["status"] == "skipped"].groupby("date").size()
    kpi["test_failures"] = tr[tr["status"] == "fail"].groupby("date").size()
    for p in ["snowflake", "databricks", "redshift"]:
        kpi[f"cost_{p}_usd"] = cost[cost["platform"] == p].groupby("date")["est_cost_usd"].sum()
    kpi["cost_total_usd"] = cost.groupby("date")["est_cost_usd"].sum()
    es = t["exposure_status_daily"]
    declared = set(nodes.loc[(nodes["resource_type"] == "exposure") & nodes["is_declared"], "node_id"])
    at_risk = es[es["exposure_id"].isin(declared) & es["worst_status"].isin(["red", "amber"])].groupby("date").size()
    kpi["exposures_at_risk"] = at_risk
    kpi = kpi.fillna({c: 0 for c in kpi.columns if not c.endswith("_pct")}).round(2)
    t["kpi_daily"] = kpi.rename_axis("date").reset_index()

    # Per model per day (runtime, failures, cost)
    md = mr.groupby(["node_id", "date"]).agg(
        runs=("status", "size"), errors=("status", lambda s: (s == "error").sum()),
        skipped=("status", lambda s: (s == "skipped").sum()),
        avg_runtime_sec=("execution_time_sec", lambda s: s[s > 0].mean() if (s > 0).any() else 0),
        max_rows=("rows_affected", "max"), materialization=("materialization", "last"), platform=("platform", "last"),
    ).reset_index()
    bc = cost[cost["cost_type"] == "build"].groupby(["node_id", "date"])["est_cost_usd"].sum().rename("build_cost_usd")
    t["model_daily"] = md.merge(bc.reset_index(), on=["node_id", "date"], how="left").round(2)

    # Tests: per model per day, plus one summary row per test
    t["test_daily"] = tr.groupby(["node_id", "date"]).agg(
        tests_run=("status", "size"), fails=("status", lambda s: (s == "fail").sum()),
        warns=("status", lambda s: (s == "warn").sum())).reset_index()
    last30 = tr[tr["date"] > AS_OF.normalize() - pd.Timedelta(days=30)]
    ts = tr.sort_values("run_at").groupby(["test_id", "test_name", "test_type", "node_id", "severity"]).agg(
        executions=("status", "size"), fails=("status", lambda s: (s == "fail").sum()),
        warns=("status", lambda s: (s == "warn").sum()), last_status=("status", "last")).reset_index()
    fail_days = last30[last30["status"].isin(["fail", "warn"])].groupby("test_id")["date"].nunique()
    ts["failure_days_30d"] = ts["test_id"].map(fail_days).fillna(0).astype(int)
    t["test_summary"] = ts

    # Freshness: per source per day, plus the latest check
    t["freshness_daily"] = fr.groupby(["source_node_id", "date"]).agg(
        max_lag_minutes=("lag_minutes", "max"), warn_checks=("status", lambda s: (s == "warn").sum()),
        error_checks=("status", lambda s: (s == "error").sum()),
        warn_after_minutes=("warn_after_minutes", "first"), error_after_minutes=("error_after_minutes", "first"),
    ).reset_index()
    t["freshness_latest"] = H.fresh.sort_values("checked_at").groupby("source_node_id").tail(1)

    t["semantic_refresh"] = H.refresh
    t["consumption"] = load("fct_consumption", ["date"])
    t["observed_access"] = load("fct_observed_access", ["date"])
    t["cost_daily"] = cost.drop(columns=["bytes_scanned", "compute_units"])
    t["incidents"] = load("fct_incidents", ["started_at", "resolved_at"])

    # Run Monitor: the last 3 days of job runs (Gantt), every prod model error with its message
    t["job_runs_recent"] = jobs[jobs["run_started_at"] >= AS_OF.normalize() - pd.Timedelta(days=2)]
    t["job_daily"] = prod_jobs.groupby(["date", "job_name"]).agg(
        runs=("status", "size"), errors=("status", lambda s: (s == "error").sum()),
        avg_duration_sec=("duration_sec", "mean")).reset_index().round(1)
    t["model_errors"] = mr[mr["status"] == "error"][["run_started_at", "node_id", "platform", "error_category",
                                                     "error_message", "job_run_id"]]

    # Blast radius and risk per node (last 30 days)
    start30 = AS_OF.normalize() - pd.Timedelta(days=29)
    cons30 = t["consumption"][t["consumption"]["date"] >= start30].groupby("exposure_id")["unique_consumers"].sum()
    cl = H.closure[H.closure["exposure_id"].isin(declared)]
    ex30 = mr[(mr["date"] >= start30) & (mr["status"] != "skipped")]
    fail_rate = ex30.groupby("node_id")["status"].apply(lambda s: (s == "error").mean())
    und = t["observed_access"][t["observed_access"]["mapped_exposure_id"].isna()].groupby("node_id")["principal"].nunique()
    impact = cl.groupby("upstream_node_id").agg(downstream_exposures=("exposure_id", "nunique"),
                                                downstream_consumers_30d=("exposure_id", lambda e: int(cons30.reindex(e).sum())))
    impact["failure_rate_30d"] = impact.index.map(fail_rate).fillna(0)
    impact["risk_score"] = (impact["downstream_consumers_30d"] * impact["failure_rate_30d"]).round(2)
    impact["undeclared_consumers"] = impact.index.map(und).fillna(0).astype(int)
    t["node_impact"] = impact.rename_axis("node_id").reset_index().round(4)

    # Cost, usage and flags per exposure (last 30 days), using the spec's allocation rule
    fan = cl.groupby("upstream_node_id")["exposure_id"].nunique()
    c30 = cost[(cost["cost_type"] == "build") & (cost["date"] >= start30)].groupby("node_id")["est_cost_usd"].sum()
    alloc = cl.assign(share=cl["upstream_node_id"].map(c30).fillna(0) / cl["upstream_node_id"].map(fan))
    em = alloc.groupby("exposure_id")["share"].sum().rename("allocated_cost_30d_usd").to_frame()
    cc = t["consumption"][t["consumption"]["date"] >= start30].groupby("exposure_id")
    em["events_30d"] = cc["events"].sum()
    em["unique_consumers_30d"] = cc["unique_consumers"].sum()
    em["cost_per_event_usd"] = em["allocated_cost_30d_usd"] / em["events_30d"].replace(0, np.nan)
    em["zombie_flag"] = (em["events_30d"] < 10) & (em["cost_per_event_usd"] > 5)
    t["exposure_metrics_30d"] = em.rename_axis("exposure_id").reset_index().round(2)
    return t


def to_jsonable(df: pd.DataFrame) -> dict:
    """Columnar JSON: {columns: [...], rows: [[...], ...]} keeps the file small."""
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[c]):
            out[c] = out[c].dt.strftime("%Y-%m-%d %H:%M:%S").str.replace(" 00:00:00", "", regex=False)
    out = out.astype(object).where(out.notna(), None)
    return {"columns": list(out.columns), "rows": out.values.tolist()}


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    tables = build()
    bundle = {"meta": {"company": "Acme Retail Co. (fictional)", "data_as_of": str(AS_OF),
                       "window": [str(DAYS[0].date()), str(DAYS[-1].date())],
                       "note": "Synthetic data. Pre-aggregated from the full dataset for the HTML mockup."},
              "tables": {}}
    for name, df in tables.items():
        df.to_csv(OUT / f"{name}.csv", index=False)
        bundle["tables"][name] = to_jsonable(df)
        print(f"  {name:<24} {len(df):>7,} rows")
    path = OUT / "mockup_bundle.json"
    path.write_text(json.dumps(bundle, separators=(",", ":"), default=str))
    print(f"  mockup_bundle.json  {path.stat().st_size / 1e6:.1f} MB")
