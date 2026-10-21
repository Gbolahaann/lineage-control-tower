"""dbt job runs, model runs and test results.

This replays 90 days of dbt Cloud, one job run at a time. Inside each job run,
models are built in dependency order (parents first), exactly like dbt does:

    a model whose parent errored or was skipped is SKIPPED
    otherwise it can ERROR (a story, a migration cutover, or random bad luck)
    otherwise it SUCCEEDS, and its tests run

Tests run after the models (the `dbt run` then `dbt test` pattern), so a failing
test is reported but does not stop downstream models from building.

In a real company:
    fct_job_runs      <- dbt Cloud Admin API (runs endpoint)
    fct_model_runs    <- run_results.json, one per job run
    fct_test_results  <- run_results.json from the test step
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from .catalog import World
from .freshness import stale_sources_at
from .graph import topo_order, upstream_with_depth
from .io import rng_for
from .stories import Stories

ERROR_MESSAGES = {
    "database": {
        "snowflake": "Database Error in model {m}: 100038 (22018): Numeric value 'N/A' is not recognized",
        "databricks": "Runtime Error in model {m}: [CAST_INVALID_INPUT] The value 'N/A' of the type \"STRING\" cannot be cast to \"DECIMAL(18,2)\"",
        "redshift": "Database Error in model {m}: Invalid digit, Value 'N', Pos 0, Type: Decimal",
    },
    "timeout": {
        "snowflake": "Database Error in model {m}: 000630 (57014): Statement reached its statement or warehouse timeout of 1800 second(s) and was canceled.",
        "databricks": "Runtime Error in model {m}: Query timed out after 1800 seconds",
        "redshift": "Database Error in model {m}: Query (1201445) cancelled by WLM abort action of Query Monitoring Rule 'max_runtime'",
    },
    "permission": {
        "snowflake": "Database Error in model {m}: 003001 (42501): SQL access control error: Insufficient privileges to operate on schema",
        "databricks": "Runtime Error in model {m}: [INSUFFICIENT_PERMISSIONS] User does not have USE SCHEMA on schema",
        "redshift": "Database Error in model {m}: permission denied for schema",
    },
    "compilation": {
        "_": "Compilation Error in model {m}: 'dict object' has no attribute 'currency_code'. This can happen when a macro argument is renamed.",
    },
}
TIMEOUT_SEC = 1800


def _message(category: str, model: str, platform: str) -> str:
    msgs = ERROR_MESSAGES[category]
    return msgs.get(platform, msgs.get("_", "")).format(m=model)


def schedule_job_runs(w: World, dim_date: pd.DataFrame, stories: Stories, rng) -> list[dict]:
    """Every scheduled, manual and CI job run in the window, in time order."""
    cfg = w.cfg
    as_of = pd.Timestamp(cfg["dates"]["data_as_of"])
    runs = []
    for d in dim_date.itertuples():
        day = pd.Timestamp(d.date)
        for name, j in cfg["jobs"].items():
            if j["schedule"] == "weekly" and day.dayofweek != j["weekday"]:
                continue
            if "every_hours" in j:
                hours = list(range(0, 24, j["every_hours"]))
            else:
                hours = list(j["hours"])
                if d.is_month_end_close_window:
                    hours += j.get("close_window_extra_hours", [])
            for h in sorted(hours):
                # dbt Cloud starts runs a few seconds to a minute after the cron tick
                start = day + pd.Timedelta(hours=h, minutes=j["start_minute"], seconds=int(rng.integers(3, 75)))
                if start <= as_of:
                    runs.append(dict(job_name=name, start=start, triggered_by="schedule", environment="prod"))

        # Slim CI: pull requests during the (mostly US) working day
        if cfg["ci"]["enabled"]:
            lo, hi = cfg["ci"]["runs_per_weekend_day" if d.is_weekend else "runs_per_weekday"]
            for _ in range(int(rng.integers(lo, hi + 1))):
                start = day + pd.Timedelta(hours=int(rng.integers(13, 23)), minutes=int(rng.integers(0, 60)))
                if start <= as_of:
                    project = str(rng.choice(list(w.spec["dbt_projects"].keys())[:3], p=[0.5, 0.3, 0.2]))
                    runs.append(dict(job_name=f"ci__{project}", start=start, triggered_by="ci",
                                     environment="ci", project=project))

    for r in stories.manual_reruns():
        runs.append(dict(job_name=r["job_name"], start=r["start"], triggered_by=r["triggered_by"], environment="prod"))
    return sorted(runs, key=lambda r: r["start"])


def simulate_runs(w: World, dim_date: pd.DataFrame, stories: Stories, timeline: dict):
    cfg = w.cfg
    rng = rng_for(cfg["seed"], "runs")
    base = cfg["baseline"]
    start_date = pd.Timestamp(cfg["dates"]["start"])
    as_of = pd.Timestamp(cfg["dates"]["data_as_of"])
    quiet_from = as_of - pd.Timedelta(hours=base["quiet_hours_before_as_of"])
    quiet_days = {pd.Timestamp(d) for d in base["no_random_noise_on"]}
    story_test = cfg["stories"]["s02_monday_test_failure"]["test"]

    meta = w.model_meta
    model_ids = list(meta)
    order = topo_order(model_ids, w.parents)
    position = {m: i for i, m in enumerate(order)}
    name_of = {m: meta[m]["name"] for m in model_ids}
    schema_of = dict(zip(w.nodes["node_id"], w.nodes["schema_name"]))

    # Models each job builds, already in dependency order
    job_models = defaultdict(list)
    for m in order:
        job_models[meta[m]["job"]].append(m)
    for name, j in cfg["jobs"].items():
        if j.get("runs") == "incremental_models_in_project":
            job_models[name] = [m for m in order if meta[m]["project"] == j["dbt_project"] and meta[m]["mat"] == "incremental"]
    interval_hours = {name: j.get("every_hours", 24 if j["schedule"] != "weekly" else 168) for name, j in cfg["jobs"].items()}

    # Raw sources behind each model, for the "stale source means no new rows" effect
    source_ids = set(w.nodes.loc[w.nodes["resource_type"] == "source", "node_id"])
    model_sources = {m: [u for u in upstream_with_depth(m, w.parents) if u in source_ids] for m in model_ids}

    tests_by_model = {k: g.to_dict("records") for k, g in w.tests.groupby("node_id")}

    error_cats = list(base["error_mix"])
    error_p = np.array(list(base["error_mix"].values()), dtype=float)
    error_p /= error_p.sum()

    def ci_models(project: str) -> list[str]:
        """A slim CI run: one changed model plus whatever depends on it in the same project."""
        candidates = [m for m in order if meta[m]["project"] == project]
        changed = candidates[int(rng.integers(len(candidates)))]
        chosen, frontier = {changed}, [changed]
        while frontier:
            n = frontier.pop()
            for c in w.children.get(n, []):
                if c in meta and meta[c]["project"] == project and c not in chosen:
                    chosen.add(c)
                    frontier.append(c)
        lo, hi = cfg["ci"]["models_per_run"]
        picked = sorted(chosen, key=position.get)[: int(rng.integers(lo, hi + 1))]
        return picked

    job_rows, model_rows, test_rows = [], [], []
    carry_over = defaultdict(dict)    # job -> {model: category} random failures that persist one more run

    schedule = schedule_job_runs(w, dim_date, stories, rng)
    for i, jr in enumerate(schedule, start=1):
        job_run_id = f"JR{i:06d}"
        jname, jstart, env = jr["job_name"], jr["start"], jr["environment"]
        is_ci = env == "ci"
        project = jr.get("project") or cfg["jobs"][jname]["dbt_project"]
        models = ci_models(project) if is_ci else job_models[jname]
        full_refresh = cfg["jobs"].get(jname, {}).get("runs") == "incremental_models_in_project"
        quiet = jstart >= quiet_from or jstart.normalize() in quiet_days

        # Which models will fail at random in this run?
        random_fail = {}
        if not is_ci and not quiet:
            random_fail.update(carry_over.pop(jname, {}))
            if rng.random() < base["job_failure_rate"]:
                k = 1 + int(rng.integers(0, base["extra_failed_models_max"] + 1))
                for m in rng.choice(models, size=min(k, len(models)), replace=False):
                    cat = str(rng.choice(error_cats, p=error_p))
                    random_fail[m] = cat
                    if rng.random() < base["persist_next_run_prob"]:
                        carry_over[jname][m] = cat
        else:
            carry_over.pop(jname, None)
        if is_ci and rng.random() < cfg["ci"]["failure_rate"]:
            m = models[int(rng.integers(len(models)))]
            random_fail[m] = "compilation" if rng.random() < 0.7 else "database"
        cancelled = is_ci and rng.random() < 0.06
        if cancelled:
            models = models[: max(1, len(models) // 2)]

        status, end_at = {}, {}
        run_platforms = []
        for m in models:
            name = name_of[m]
            mm = meta[m]
            parents_here = [p for p in w.parents.get(m, []) if p in status]
            started = max([jstart + pd.Timedelta(seconds=15)] + [end_at[p] for p in parents_here])
            platform = stories.platform_at(name, mm["original_platform"], started)
            run_platforms.append(platform)
            # What the model was at run time (fct_sessions was a table until story 1's fix)
            mat_now = "table" if stories.is_full_refresh_table(name, started) else mm["mat"]

            if any(status[p] in ("error", "skipped") for p in parents_here):
                status[m], end_at[m] = "skipped", started
                model_rows.append(dict(job_run_id=job_run_id, node_id=m, platform=platform, materialization=mat_now,
                                       run_started_at=started, run_completed_at=started, execution_time_sec=0.0,
                                       status="skipped", rows_affected=None, error_category="upstream_skip",
                                       error_message=f"Skipping {name} due to an upstream error"))
                continue

            # Decide whether it errors: planted story first, then cutover, then random
            err = None
            if not is_ci:
                err = stories.schema_change_error(name, started)
                if err is None and rng.random() < stories.cutover_failure_rate(name, started):
                    cat = "permission" if rng.random() < 0.5 else "database"
                    err = (cat, _message(cat, name, platform) + " (post-migration cutover)")
            if err is None and m in random_fail:
                cat = random_fail[m]
                err = (cat, _message(cat, name, platform))

            # Runtime: base x organic growth x story effects x platform x noise
            weeks = max(0.0, (started - start_date).days / 7)
            runtime = mm["runtime"] * (1 + base["weekly_growth"]) ** weeks
            runtime *= stories.runtime_multiplier(name, started)
            if full_refresh:
                runtime *= 6                       # rebuilding the whole table, not just new rows
            if platform != mm["original_platform"]:
                runtime *= cfg["pricing"]["migration_runtime_factor"]
            if is_ci:
                runtime *= 0.4                     # CI builds on a sample with --defer
            runtime *= float(np.exp(rng.normal(0, base["runtime_noise_sd"])))

            if err:
                cat, msg = err
                runtime = TIMEOUT_SEC if cat == "timeout" else runtime * float(rng.uniform(0.05, 0.6))
                if cat in ("compilation",):
                    runtime = float(rng.uniform(0.5, 3))
                if cat == "schema_change":
                    runtime = float(rng.uniform(1, 4))
            runtime = round(max(0.5, runtime), 2)
            done = started + pd.Timedelta(seconds=runtime)

            rows_affected = None
            if not err and mm["rows"]:
                growth = (1 + base["weekly_growth"]) ** weeks
                if mm["mat"] == "table" or full_refresh or stories.is_full_refresh_table(name, started):
                    rows_affected = int(mm["rows"] * growth * rng.uniform(0.995, 1.005))
                elif mm["mat"] == "incremental":
                    hours = interval_hours.get(jname, 24)
                    rows_affected = int(mm["rows"] * growth * hours / 26280 * rng.uniform(0.6, 1.4))
                    # A stale upstream source means there is nothing new to insert
                    if stale_sources_at(timeline, model_sources[m], started, w):
                        rows_affected = 0

            st = "error" if err else "success"
            status[m], end_at[m] = st, done
            model_rows.append(dict(job_run_id=job_run_id, node_id=m, platform=platform, materialization=mat_now,
                                   run_started_at=started, run_completed_at=done, execution_time_sec=runtime,
                                   status=st, rows_affected=rows_affected,
                                   error_category=err[0] if err else None, error_message=err[1] if err else None))

        # Tests, after all models in the job have finished
        tests_failed = 0
        last_end = max(end_at.values()) if end_at else jstart
        t_clock = last_end + pd.Timedelta(seconds=5)
        for m in models:
            if status.get(m) != "success":
                continue
            for t in tests_by_model.get(m, []):
                t_clock += pd.Timedelta(seconds=float(rng.uniform(0.4, 3.0)))
                forced = None if is_ci else stories.forced_test_result(t["test_name"], t_clock, rng)
                if forced:
                    st, failures = forced
                else:
                    r = rng.random()
                    # The story test is kept out of random noise so "every Monday" stays exactly true
                    if quiet or t["test_name"] == story_test or r >= base["test_random_fail_rate"] + base["test_random_warn_rate"]:
                        st, failures = "pass", 0
                    elif r < base["test_random_fail_rate"]:
                        st = "fail" if t["severity"] == "error" else "warn"
                        failures = int(rng.integers(1, 60))
                    else:
                        st, failures = "warn", int(rng.integers(1, 15))
                if st in ("fail", "error"):
                    tests_failed += 1
                test_rows.append(dict(test_id=t["test_id"], test_name=t["test_name"], test_type=t["test_type"],
                                      node_id=m, column_name=t["column_name"], job_run_id=job_run_id,
                                      run_at=t_clock, status=st, failures_count=failures, severity=t["severity"]))

        n_err = sum(s == "error" for s in status.values())
        n_skip = sum(s == "skipped" for s in status.values())
        finished = max(t_clock, last_end) + pd.Timedelta(seconds=int(rng.integers(8, 40)))
        job_rows.append(dict(
            job_run_id=job_run_id, job_name=jname, dbt_project=project,
            platform=max(set(run_platforms), key=run_platforms.count) if run_platforms else None,
            schedule="on_pull_request" if is_ci else cfg["jobs"][jname]["schedule"], environment=env,
            run_started_at=jstart, run_completed_at=finished,
            duration_sec=round((finished - jstart).total_seconds(), 1),
            status="cancelled" if cancelled else ("error" if n_err else "success"),
            models_run=len(status) - n_skip, models_failed=n_err, models_skipped=n_skip,
            tests_failed=tests_failed, triggered_by=jr["triggered_by"],
        ))

    job_runs = pd.DataFrame(job_rows)
    model_runs = pd.DataFrame(model_rows)
    model_runs["rows_affected"] = model_runs["rows_affected"].astype("Int64")
    test_results = pd.DataFrame(test_rows)
    return job_runs, model_runs, test_results
