"""Usage: what consumers report (fct_consumption) and what the warehouse sees (fct_observed_access).

These two tables are the "reported" and "observed" halves of the spec's
declared / observed / reported idea:

fct_consumption      reported usage, one row per declared consumer per day.
                     Dashboards report views (Tableau Admin Insights TS Events,
                     Power BI activity log, Sigma audit log). Apps report sessions,
                     agents report calls, notebooks and ML models report queries.

fct_observed_access  the warehouse's own record: who queried which table, how often.
                     Comes from Snowflake ACCOUNT_USAGE.ACCESS_HISTORY / QUERY_HISTORY,
                     Databricks system.access.audit and system.query.history.
                     A principal that no declared exposure accounts for is an
                     undeclared consumer (story 11).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .catalog import World
from .io import rng_for

# Typical latency per consumer type, in seconds (dashboard load, app response, agent answer)
LATENCY = {"dashboard": 3.5, "data_hub": 2.5, "notebook": 20.0, "ml": 45.0, "data_app": 1.8, "agent": 7.0}
# How many warehouse queries one consumption event triggers
QUERIES_PER_EVENT = {"dashboard": 0, "data_hub": 0, "notebook": 3.0, "ml": 1.0, "data_app": 2.0, "agent": 1.6}


def _day_factor(day: pd.Timestamp, d: dict, domain: str, name: str, cfg: dict) -> float:
    u = cfg["usage"]
    f = u["weekend_factor"] if d["is_weekend"] else 1.0
    if domain == "Finance" and d["is_month_end_close_window"]:
        f *= u["close_window_factor"]
    if name == "board_kpi_pack" and d["is_board_prep_window"]:
        f *= u["board_prep_factor"]
    return f


def build_consumption(w: World, dim_date: pd.DataFrame) -> pd.DataFrame:
    cfg = w.cfg
    rng = rng_for(cfg["seed"], "consumption")
    stories = cfg["stories"]
    zombie = stories["s07_zombie_dashboard"]
    sprawl = stories["s10_dashboard_sprawl"]
    start = pd.Timestamp(cfg["dates"]["start"])
    days = {pd.Timestamp(r["date"]): r for r in dim_date.to_dict("records")}

    exps = w.nodes[(w.nodes["resource_type"] == "exposure") & w.nodes["is_declared"]]
    sprawl_names = set(w.spec["exposures"]) & {n for n, e in w.spec["exposures"].items() if e.get("sprawl")}

    # Story 7: the zombie gets a handful of views a month, on random weekdays
    zombie_days = set()
    if zombie["enabled"]:
        for _, month in dim_date.groupby("month"):
            weekdays = month.loc[~month["is_weekend"], "date"].tolist()
            k = int(rng.integers(1, zombie["max_views_per_month"] + 1))
            zombie_days.update(pd.Timestamp(x) for x in rng.choice(weekdays, size=min(k, len(weekdays)), replace=False))

    rows = []
    for e in exps.itertuples():
        created = pd.Timestamp(e.created_date)
        launch_peak = float(rng.uniform(*sprawl["launch_views_per_day"])) if e.node_name in sprawl_names else None
        for day, d in days.items():
            if day < created:
                continue
            f = _day_factor(day, d, e.domain, e.node_name, cfg)
            weeks = (day - start).days / 7

            if e.node_name == zombie["exposure"] and zombie["enabled"]:
                events = 1 if day in zombie_days else 0
                consumers = events
            elif launch_peak is not None:
                # Story 10: a burst of curiosity at launch, then interest decays fast
                age = (day - created).days
                mean = launch_peak * 0.5 ** (age / sprawl["decay_half_life_days"]) * f
                events = int(rng.poisson(max(mean, 0.15)))
                consumers = min(events, int(np.ceil(events * rng.uniform(0.4, 0.8))))
            else:
                mean = e.base_daily_events * f * (1 + 0.004) ** weeks
                mean *= float(np.exp(rng.normal(0, cfg["usage"]["daily_noise_sd"])))
                events = int(rng.poisson(mean))
                base_c = e.base_daily_consumers * min(1.0, f ** 0.6)
                consumers = min(events, max(1 if events else 0, int(round(base_c * rng.uniform(0.8, 1.15)))))

            latency = LATENCY[e.exposure_type] * float(np.exp(rng.normal(0, 0.2)))
            if e.node_name == zombie["exposure"]:
                latency *= 3.2       # it sits on the giant fct_sessions extract, so it is slow too
            row = dict(date=day, exposure_id=e.node_id, consumption_type=e.consumption_type,
                       events=events, unique_consumers=consumers,
                       avg_latency_sec=round(latency, 2) if events else None,
                       metrics_called=None, failed_calls=None)
            if e.exposure_type == "agent":
                row["metrics_called"] = int(events * rng.uniform(1.3, 2.4))
                row["failed_calls"] = int(rng.binomial(events, 0.012))
            rows.append(row)
    df = pd.DataFrame(rows)
    for c in ("metrics_called", "failed_calls"):
        df[c] = df[c].astype("Int64")
    return df


def build_observed_access(w: World, consumption: pd.DataFrame, semantic_refresh: pd.DataFrame,
                          dim_date: pd.DataFrame) -> pd.DataFrame:
    cfg = w.cfg
    rng = rng_for(cfg["seed"], "observed")
    nodes = w.nodes.set_index("node_id")
    rows_of = {k: (v["rows"] or 50_000) for k, v in w.model_meta.items()}

    def gb_per_query(model_id: str) -> float:
        # Bigger tables scan more; clustering keeps it well below a full scan
        return max(0.02, rows_of.get(model_id, 50_000) * 180 / 1e9 * float(rng.uniform(0.05, 0.25)))

    out = []

    # 1. BI service accounts: one query tag per semantic object (extract refreshes and live queries)
    refresh_counts = (semantic_refresh.assign(date=semantic_refresh["refresh_started_at"].dt.normalize())
                      .groupby(["node_id", "date"]).size().to_dict())
    exp_views = consumption.groupby(["exposure_id", "date"])["events"].sum().to_dict()
    for s in nodes[nodes["resource_type"] == "semantic"].itertuples():
        models = [p for p in w.parents[s.Index] if p in w.model_meta]
        downstream = w.children.get(s.Index, [])
        for day in pd.to_datetime(dim_date["date"]):
            if s.connection_type == "extract":
                q = refresh_counts.get((s.Index, day), 0)
            else:   # live: every dashboard view fires a few queries
                q = int(sum(exp_views.get((x, day), 0) for x in downstream) * 3)
            if q == 0:
                continue
            for m in models:
                out.append(dict(date=day, principal=f"{s.service_principal}:{s.node_name}", principal_type="service",
                                node_id=m, query_count=q, bytes_scanned=int(q * gb_per_query(m) * 1e9),
                                mapped_exposure_id=s.Index, inferred_exposure_id=s.Index))

    # 2. Declared direct consumers (apps, ML, notebooks, agents, the Claude hub)
    direct = nodes[(nodes["resource_type"] == "exposure") & nodes["is_declared"]
                   & (nodes["access_path"] != "bi_semantic_layer")]
    cons = consumption.set_index(["exposure_id", "date"])["events"].to_dict()
    for e in direct.itertuples():
        models = [p for p in w.parents[e.Index] if p in w.model_meta]
        for day in pd.to_datetime(dim_date["date"]):
            ev = cons.get((e.Index, day))
            if ev is None:
                continue
            if e.exposure_type == "data_hub":
                q = int(rng.integers(1, 3))          # the hub pulls an extract once or twice a day
            else:
                q = int(round(ev * QUERIES_PER_EVENT[e.exposure_type]))
            if q == 0:
                continue
            ptype = {"agent": "agent", "data_app": "app"}.get(e.exposure_type, "service")
            for m in models:
                out.append(dict(date=day, principal=e.service_principal, principal_type=ptype, node_id=m,
                                query_count=q, bytes_scanned=int(q * gb_per_query(m) * 1e9),
                                mapped_exposure_id=e.Index, inferred_exposure_id=e.Index))

    # 3. Story 11: consumers nobody registered. Only the warehouse knows they exist.
    s11 = cfg["stories"]["s11_undeclared_consumers"]
    if s11["enabled"]:
        weekend = set(pd.to_datetime(dim_date.loc[dim_date["is_weekend"], "date"]))
        for c in s11["consumers"]:
            exp_id = w.id_of[c["exposure"]]
            first = pd.Timestamp(c["first_seen"])
            for day in pd.to_datetime(dim_date["date"]):
                if day < first:
                    continue
                # Agents run every day; people and scheduled notebooks mostly on weekdays
                if c["principal_type"] != "agent" and day in weekend and rng.random() < 0.8:
                    continue
                ramp = min(1.0, 0.35 + (day - first).days / 10)   # usage ramps up over the first ~week
                q = int(rng.integers(*c["queries_per_day"]) * ramp)
                for name in c["reads"]:
                    m = w.id_of[name]
                    gb = float(rng.uniform(*c["gb_scanned_per_query"]))
                    out.append(dict(date=day, principal=c["principal"], principal_type=c["principal_type"],
                                    node_id=m, query_count=q, bytes_scanned=int(q * gb * 1e9),
                                    mapped_exposure_id=None, inferred_exposure_id=exp_id))

    df = pd.DataFrame(out).sort_values(["date", "principal", "node_id"]).reset_index(drop=True)
    return df
