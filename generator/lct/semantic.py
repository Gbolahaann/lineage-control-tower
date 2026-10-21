"""fct_semantic_refresh: extract refreshes of BI semantic objects.

A Tableau published data source, a Power BI semantic model (in import mode) or a
Sigma dataset with materialization keeps its own copy of the data. That copy is
refreshed on a schedule. If the refresh fails, every dashboard on top of it shows
old numbers, even when every dbt model upstream is green. That is story 6.

Live connections (Sigma datasets here, and the monitor's own data source) query
the warehouse directly and have no refreshes, so they produce no rows.

In a real company:
    Tableau  -> Admin Insights "Job Performance" / REST API background jobs
    Power BI -> refresh history API
    Sigma    -> audit logs (materialization runs)
"""

from __future__ import annotations

import bisect
from collections import defaultdict

import numpy as np
import pandas as pd

from .catalog import World
from .io import rng_for
from .stories import Stories


class LatestStatus:
    """Answers "what was this model's latest prod status at time t?" quickly."""

    def __init__(self, model_runs: pd.DataFrame, job_runs: pd.DataFrame):
        prod = set(job_runs.loc[job_runs["environment"] == "prod", "job_run_id"])
        mr = model_runs[model_runs["job_run_id"].isin(prod)].sort_values("run_completed_at")
        self.times, self.status = defaultdict(list), defaultdict(list)
        for n, t, s in zip(mr["node_id"], mr["run_completed_at"], mr["status"]):
            self.times[n].append(t)
            self.status[n].append(s)

    def at(self, node_id: str, ts: pd.Timestamp):
        i = bisect.bisect_right(self.times[node_id], ts)
        return self.status[node_id][i - 1] if i else None


def build_semantic_refresh(w: World, stories: Stories, latest: LatestStatus, dim_date: pd.DataFrame) -> pd.DataFrame:
    cfg = w.cfg
    rng = rng_for(cfg["seed"], "semantic")
    as_of = pd.Timestamp(cfg["dates"]["data_as_of"])
    quiet_from = as_of - pd.Timedelta(hours=cfg["baseline"]["quiet_hours_before_as_of"])
    quiet_days = {pd.Timestamp(d) for d in cfg["baseline"]["no_random_noise_on"]}
    start_date = pd.Timestamp(cfg["dates"]["start"])
    close_days = set(pd.to_datetime(dim_date.loc[dim_date["is_month_end_close_window"], "date"]))
    rows_of = {k: (v["rows"] or 0) for k, v in w.model_meta.items()}

    sem = w.nodes[(w.nodes["resource_type"] == "semantic") & (w.nodes["connection_type"] == "extract")]
    out = []
    for r in sem.itertuples():
        parents = w.parents[r.node_id]
        first_hour = float(rng.uniform(0.5, 3.0))       # each object refreshes at its own time of day
        for day in pd.to_datetime(dim_date["date"]):
            n = int(r.close_window_refreshes_per_day) if (day in close_days and not pd.isna(r.close_window_refreshes_per_day)) \
                else int(r.refreshes_per_day)
            for k in range(n):
                t = day + pd.Timedelta(hours=first_hour + k * 24 / n, seconds=int(rng.integers(0, 120)))
                if t > as_of:
                    continue
                weeks = (t - start_date).days / 7
                rows = int(sum(rows_of.get(p, 0) for p in parents) * (1 + cfg["baseline"]["weekly_growth"]) ** weeks)
                duration = max(20.0, rows / 120_000 * float(np.exp(rng.normal(0, 0.15))))

                story_err = stories.semantic_refresh_failure(r.node_name, t)
                upstream_bad = [p for p in parents if latest.at(p, t) in ("error", "skipped")]
                quiet = t >= quiet_from or t.normalize() in quiet_days
                if story_err:
                    status, msg, rows_out = "failed", story_err, None
                    duration = float(rng.uniform(5, 25))
                elif upstream_bad:
                    # Orchestrated refreshes wait for dbt: if a parent mart failed, skip rather than publish half-built data
                    status, rows_out, duration = "skipped_upstream", None, 0.0
                    msg = "Skipped: upstream model failed in its latest dbt run (" + \
                          ", ".join(w.model_meta[p]["name"] for p in upstream_bad) + ")"
                elif not quiet and rng.random() < cfg["semantic_refresh"]["random_failure_rate"]:
                    status, rows_out = "failed", None
                    msg = str(rng.choice([
                        "Extract refresh failed: the query exceeded the 7200 second limit",
                        "Extract refresh failed: connection reset by peer",
                        "Backend error: insufficient memory on the refresh node",
                    ]))
                    duration *= float(rng.uniform(0.2, 0.8))
                else:
                    status, msg, rows_out = "success", None, rows
                out.append(dict(node_id=r.node_id, bi_tool=r.bi_tool, refresh_started_at=t,
                                duration_sec=round(duration, 1), status=status, rows_refreshed=rows_out,
                                error_message=msg))
    df = pd.DataFrame(out).sort_values("refresh_started_at").reset_index(drop=True)
    df.insert(0, "refresh_id", [f"RF{i:05d}" for i in range(1, len(df) + 1)])
    df["rows_refreshed"] = df["rows_refreshed"].astype("Int64")
    return df
