"""Exposure health, computed exactly as the spec defines it.

This is a Python reference implementation of the dashboard's core logic. The
Tableau build will do the same thing with LOD expressions; having it here lets
the validation charts check stories the way the dashboard will show them.

RAG at a moment in time, for one exposure, looking at everything upstream of it:
  Red    any upstream model errored in its latest prod run, OR
         any upstream source is in freshness error at its latest check, OR
         an upstream semantic object's latest refresh failed
  Amber  any upstream test is failing or warning in its latest execution, OR
         any upstream source is in freshness warn
  Green  everything else
  Grey   no runs at all (e.g. the exposure did not exist yet)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"


def load(name: str, dates=()) -> pd.DataFrame:
    return pd.read_csv(DATA / f"{name}.csv", parse_dates=list(dates))


class Health:
    def __init__(self):
        self.nodes = load("dim_nodes", ["created_date", "migration_date"])
        self.closure = load("fct_exposure_upstream")
        jobs = load("fct_job_runs", ["run_started_at"])
        prod = set(jobs.loc[jobs["environment"] == "prod", "job_run_id"])
        self.model_runs = load("fct_model_runs", ["run_started_at", "run_completed_at"])
        self.prod_runs = self.model_runs[self.model_runs["job_run_id"].isin(prod)]
        tests = load("fct_test_results", ["run_at"])
        self.prod_tests = tests[tests["job_run_id"].isin(prod)]
        self.fresh = load("fct_source_freshness", ["checked_at"])
        self.refresh = load("fct_semantic_refresh", ["refresh_started_at"])

    def status_at(self, ts) -> pd.DataFrame:
        ts = pd.Timestamp(ts)
        # Latest prod model run per node
        mr = self.prod_runs[self.prod_runs["run_completed_at"] <= ts]
        latest_model = mr.sort_values("run_completed_at").groupby("node_id")["status"].last()
        # Latest execution of each test
        tr = self.prod_tests[self.prod_tests["run_at"] <= ts]
        latest_test = tr.sort_values("run_at").groupby(["test_id", "node_id"])["status"].last().reset_index()
        bad_test_nodes = set(latest_test.loc[latest_test["status"].isin(["fail", "warn", "error"]), "node_id"])
        # Latest freshness check per source
        fr = self.fresh[self.fresh["checked_at"] <= ts]
        latest_fresh = fr.sort_values("checked_at").groupby("source_node_id")["status"].last()
        # Latest refresh per semantic object
        rf = self.refresh[self.refresh["refresh_started_at"] <= ts]
        latest_refresh = rf.sort_values("refresh_started_at").groupby("node_id")["status"].last()

        exps = self.nodes[self.nodes["resource_type"] == "exposure"]
        rows = []
        for e in exps.itertuples():
            ups = set(self.closure.loc[self.closure["exposure_id"] == e.node_id, "upstream_node_id"])
            reasons_red, reasons_amber = [], []
            if pd.Timestamp(e.created_date) > ts:
                rows.append(dict(exposure_id=e.node_id, display_name=e.display_name, status="grey", reasons=""))
                continue
            for u in ups:
                if latest_model.get(u) == "error":
                    reasons_red.append(f"model error: {u.split('.')[-1]}")
                if latest_fresh.get(u) == "error":
                    reasons_red.append(f"freshness error: {u.split('.', 2)[-1]}")
                if latest_refresh.get(u) == "failed":
                    reasons_red.append(f"refresh failed: {u.split('.')[-1]}")
                if u in bad_test_nodes:
                    reasons_amber.append(f"test failing: {u.split('.')[-1]}")
                if latest_fresh.get(u) == "warn":
                    reasons_amber.append(f"freshness warn: {u.split('.', 2)[-1]}")
            status = "red" if reasons_red else ("amber" if reasons_amber else "green")
            rows.append(dict(exposure_id=e.node_id, display_name=e.display_name, status=status,
                             reasons="; ".join(sorted(set(reasons_red or reasons_amber)))))
        return pd.DataFrame(rows)
