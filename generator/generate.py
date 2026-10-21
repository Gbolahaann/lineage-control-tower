"""Generate the Lineage Control Tower synthetic dataset.

Usage:
    python generator/generate.py

Reads generator/config.yaml and generator/world.yaml, writes CSVs to data/.
The order matters: the world first, then the graph tables, then the simulation
(runs, tests, freshness, refreshes), then cost and usage, so failures can
propagate downstream before anything reads them.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lct.calendar import build_dim_date  # noqa: E402
from lct.catalog import build_world  # noqa: E402
from lct.graph import build_closure, build_layout  # noqa: E402
from lct.io import load_yaml, write_csv  # noqa: E402


def main() -> None:
    t0 = time.time()
    cfg = load_yaml("config.yaml")
    spec = load_yaml("world.yaml")

    tables = {}

    # 1. The world: who owns what, and what feeds what
    world = build_world(cfg, spec)
    tables["dim_owners"] = world.owners
    tables["dim_date"] = build_dim_date(cfg)
    tables["dim_nodes"] = world.nodes
    tables["fct_lineage_edges"] = world.edges

    # 2. Graph tables Tableau can use without recursion
    tables["fct_exposure_upstream"] = build_closure(world)
    tables["fct_lineage_layout"] = build_layout(world)

    for name, df in tables.items():
        write_csv(df, name)
        print(f"  {name:<24} {len(df):>9,} rows")
    print(f"Done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
