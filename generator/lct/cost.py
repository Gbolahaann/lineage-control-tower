"""fct_warehouse_cost: what each node costs per day, on the platform it ran on.

Two kinds of cost (cost_type):
  build           dbt building the model. In production you tag every dbt query
                  with the model name (a query tag or comment), then join
                  QUERY_HISTORY back to node_id. Most teams have not set this up.
  consumer_query  a direct consumer (app, agent, notebook, hub, or an undeclared
                  one) querying the model. Same mechanism, keyed on the principal.

Units differ by platform, so both raw units and USD are kept:
  Snowflake credits, Databricks DBUs, Redshift Serverless RPU-hours.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .catalog import World
from .io import rng_for

# Rough scan throughput used to turn bytes into warehouse seconds for consumer queries
SECONDS_PER_GB = 1.6
CONSUMER_WAREHOUSE = {"snowflake": ("ANALYTICS_WH", 2), "databricks": ("serverless-sql-wh", 12), "redshift": ("marketing-serverless", 128)}


def _usd(platform: str, units: float, pricing: dict) -> float:
    rate = {"snowflake": pricing["snowflake_usd_per_credit"], "databricks": pricing["databricks_usd_per_dbu"],
            "redshift": pricing["redshift_usd_per_rpu_hour"]}[platform]
    return units * rate


def build_warehouse_cost(w: World, model_runs: pd.DataFrame, job_runs: pd.DataFrame,
                         observed: pd.DataFrame) -> pd.DataFrame:
    cfg = w.cfg
    rng = rng_for(cfg["seed"], "cost")
    pricing = cfg["pricing"]
    projects = w.spec["dbt_projects"]

    # ---------------------------------------------------------------- build cost
    mr = model_runs[model_runs["status"] != "skipped"].copy()
    mr["date"] = mr["run_started_at"].dt.normalize()
    mr["project"] = mr["node_id"].map({k: v["project"] for k, v in w.model_meta.items()})

    def warehouse(project: str, platform: str):
        if project == "acme_marketing" and platform == "snowflake":
            p = projects["acme_marketing_on_snowflake"]
        else:
            p = projects[project]
        return p["warehouse"], p["compute_per_hour"]

    daily = mr.groupby(["date", "node_id", "platform", "project"], as_index=False)["execution_time_sec"].sum()
    rows = []
    for r in daily.itertuples():
        wh, per_hour = warehouse(r.project, r.platform)
        units = r.execution_time_sec / 3600 * per_hour
        # Throughput differs by engine; this only feeds bytes_scanned, which is indicative
        gb = r.execution_time_sec * float(rng.uniform(0.08, 0.2))
        rows.append(dict(date=r.date, node_id=r.node_id, platform=r.platform, warehouse_or_cluster=wh,
                         cost_type="build", principal=None, compute_units=round(units, 4),
                         est_cost_usd=round(_usd(r.platform, units, pricing), 2), bytes_scanned=int(gb * 1e9)))

    # ------------------------------------------------------- consumer query cost
    plat = dict(zip(w.nodes["node_id"], w.nodes["platform"]))
    migration = {k: v["migration_date"] for k, v in w.model_meta.items()}
    original = {k: v["original_platform"] for k, v in w.model_meta.items()}
    direct = observed[~observed["principal"].str.contains(":", regex=False)]   # BI query tags contain ':'
    for r in direct.itertuples():
        mig = migration.get(r.node_id)
        platform = plat[r.node_id] if (mig is None or pd.isna(mig) or r.date >= mig) else original[r.node_id]
        wh, per_hour = CONSUMER_WAREHOUSE[platform]
        seconds = r.bytes_scanned / 1e9 * SECONDS_PER_GB * float(np.exp(rng.normal(0, 0.1)))
        units = seconds / 3600 * per_hour
        rows.append(dict(date=r.date, node_id=r.node_id, platform=platform, warehouse_or_cluster=wh,
                         cost_type="consumer_query", principal=r.principal, compute_units=round(units, 4),
                         est_cost_usd=round(_usd(platform, units, pricing), 2), bytes_scanned=int(r.bytes_scanned)))

    return pd.DataFrame(rows).sort_values(["date", "node_id", "cost_type"]).reset_index(drop=True)
