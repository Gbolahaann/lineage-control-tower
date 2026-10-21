"""Generate the Lineage Control Tower synthetic dataset.

Usage:
    python generator/generate.py               # full dataset, all stories on
    python generator/generate.py --no-stories  # baseline only, handy for comparisons

Reads generator/config.yaml and generator/world.yaml, writes CSVs to data/.
The order matters: the world first, then the graph tables, then the simulation
(loads, runs, tests, freshness, refreshes), then cost and usage, so failures can
propagate downstream before anything reads them.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lct.calendar import build_dim_date  # noqa: E402
from lct.catalog import build_world  # noqa: E402
from lct.freshness import build_load_timeline, build_source_freshness  # noqa: E402
from lct.graph import build_closure, build_layout  # noqa: E402
from lct.io import load_yaml, write_csv  # noqa: E402
from lct.runs import simulate_runs  # noqa: E402
from lct.stories import Stories  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-stories", action="store_true", help="switch every planted story off")
    args = parser.parse_args()

    t0 = time.time()
    cfg = load_yaml("config.yaml")
    spec = load_yaml("world.yaml")
    if args.no_stories:
        for story in cfg["stories"].values():
            story["enabled"] = False
    stories = Stories(cfg)

    tables = {}

    # 1. The world: who owns what, and what feeds what
    world = build_world(cfg, spec)
    dim_date = build_dim_date(cfg)
    tables["dim_owners"] = world.owners
    tables["dim_date"] = dim_date
    # base_daily_* are knobs for the usage simulation, not catalog facts, so they stay internal
    tables["dim_nodes"] = world.nodes.drop(columns=["base_daily_events", "base_daily_consumers"])
    tables["fct_lineage_edges"] = world.edges

    # 2. Graph tables Tableau can use without recursion
    tables["fct_exposure_upstream"] = build_closure(world)
    tables["fct_lineage_layout"] = build_layout(world)

    # 3. When raw data actually landed, then 90 days of dbt runs and tests on top of it
    timeline = build_load_timeline(world, stories)
    job_runs, model_runs, test_results = simulate_runs(world, dim_date, stories, timeline)
    tables["fct_job_runs"] = job_runs
    tables["fct_model_runs"] = model_runs
    tables["fct_test_results"] = test_results

    # 4. Source freshness checks
    tables["fct_source_freshness"] = build_source_freshness(world, timeline)

    for name, df in tables.items():
        write_csv(df, name)
        print(f"  {name:<24} {len(df):>9,} rows")
    print(f"Done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
