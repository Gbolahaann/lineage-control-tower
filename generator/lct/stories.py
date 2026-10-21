"""The 11 planted stories, in one place.

Every other module asks this one questions like "should this model fail at this
time?" or "how slow is fct_sessions today?". Keeping all the drama here means
you can read one file to see exactly what was planted, and switch any story off
in config.yaml without touching the simulation code.
"""

from __future__ import annotations

import pandas as pd


def _ts(x) -> pd.Timestamp:
    return pd.Timestamp(x)


class Stories:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.s = cfg["stories"]

    def on(self, key: str) -> bool:
        return bool(self.s[key]["enabled"])

    # ------------------------------------------------------------------ story 1
    def runtime_multiplier(self, model_name: str, ts: pd.Timestamp) -> float:
        """fct_sessions creeps up as a full-refresh table, then drops when made incremental."""
        if not self.on("s01_slow_creep"):
            return 1.0
        s = self.s["s01_slow_creep"]
        if model_name != s["model"]:
            return 1.0
        start, peak, fixed = _ts(s["creep_start"]), _ts(s["creep_peak"]), _ts(s["fixed_on"])
        if ts >= fixed:
            return s["incremental_runtime_factor"]
        if ts <= start:
            return 1.0
        # Linear climb to the peak, then a plateau until the fix ships
        progress = min(1.0, (ts - start) / (peak - start))
        return 1.0 + (s["peak_multiplier"] - 1.0) * progress

    def is_full_refresh_table(self, model_name: str, ts: pd.Timestamp) -> bool:
        """Before the fix, fct_sessions rebuilt the whole table on every run."""
        s = self.s["s01_slow_creep"]
        return self.on("s01_slow_creep") and model_name == s["model"] and ts < _ts(s["fixed_on"])

    # ------------------------------------------------------------------ story 2
    def forced_test_result(self, test_name: str, ts: pd.Timestamp, rng):
        """The dim_customers unique test fails all day, every Monday, from 10 Aug."""
        if not self.on("s02_monday_test_failure"):
            return None
        s = self.s["s02_monday_test_failure"]
        if test_name == s["test"] and ts.dayofweek == 0 and ts.normalize() >= _ts(s["first_monday"]):
            lo, hi = s["failures_range"]
            return "fail", int(rng.integers(lo, hi + 1))
        return None

    # ------------------------------------------------------------------ story 3
    def migration_for(self, model_or_source: str):
        """(wave name, migration date) if this node migrates from Redshift to Snowflake."""
        if not self.on("s03_platform_migration"):
            return None
        for wave in self.s["s03_platform_migration"]["waves"]:
            if model_or_source in wave["models"] or model_or_source in wave["sources"]:
                return wave["name"], _ts(wave["migration_date"])
        return None

    def platform_at(self, name: str, original_platform: str, ts: pd.Timestamp) -> str:
        mig = self.migration_for(name)
        if mig and ts >= mig[1]:
            return self.s["s03_platform_migration"]["to_platform"]
        return original_platform

    def cutover_failure_rate(self, name: str, ts: pd.Timestamp) -> float:
        """On cutover day (and the day after) migrated models fail far more often."""
        mig = self.migration_for(name)
        if not mig:
            return 0.0
        s = self.s["s03_platform_migration"]
        day = ts.normalize()
        if mig[1] <= day < mig[1] + pd.Timedelta(days=s["cutover_days"]):
            return s["cutover_failure_rate"]
        return 0.0

    # ------------------------------------------------------------------ story 4
    def schema_change_error(self, model_name: str, ts: pd.Timestamp):
        if not self.on("s04_schema_change"):
            return None
        s = self.s["s04_schema_change"]
        day = _ts(s["date"])
        broken = _ts(f"{s['date']} {s['broken_from']}")
        fixed = _ts(f"{s['date']} {s['fixed_at']}")
        if model_name in s["broken_models"] and broken <= ts < fixed:
            old_col = s["renamed_column"].split("->")[0].strip().upper()
            return ("schema_change",
                    f"Database Error in model {model_name}: SQL compilation error: error line 4 at position 8 "
                    f"invalid identifier '{old_col}'. Upstream column renamed in {s['source']}.")
        return None

    def manual_reruns(self) -> list[dict]:
        """After the hotfix, an engineer re-runs the marketing job by hand."""
        if not self.on("s04_schema_change"):
            return []
        s = self.s["s04_schema_change"]
        fixed = _ts(f"{s['date']} {s['fixed_at']}")
        return [{"job_name": "marketing_every_4h", "start": fixed + pd.Timedelta(minutes=12), "triggered_by": "manual"}]

    # ------------------------------------------------------------- stories 5, 9
    def source_outages(self) -> dict:
        """Periods when a source stops loading: {source_name: [(start, end), ...]}."""
        out = {}
        if self.on("s05_freshness_cascade"):
            s = self.s["s05_freshness_cascade"]
            out.setdefault(s["source"], []).append((_ts(s["stops_loading_at"]), _ts(s["resumes_at"])))
        if self.on("s09_live_issues_today"):
            s = self.s["s09_live_issues_today"]
            out.setdefault(s["warn_source"], []).append(
                (_ts(s["delay_starts_at"]), _ts(self.cfg["dates"]["data_as_of"]) + pd.Timedelta(minutes=1)))
        return out

    # ------------------------------------------------------------------ story 6
    def semantic_refresh_failure(self, semantic_name: str, ts: pd.Timestamp):
        if not self.on("s06_green_dbt_broken_dashboard"):
            return None
        s = self.s["s06_green_dbt_broken_dashboard"]
        if semantic_name == s["semantic_object"] and _ts(s["failing_from"]) <= ts < _ts(s["fixed_at"]):
            return s["error"]
        return None
