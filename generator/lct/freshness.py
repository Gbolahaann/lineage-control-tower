"""Source loads and freshness checks.

Two steps:
1. A load timeline: when did each raw table actually receive new data? This is
   what Fivetran / Airbyte logs would tell you. It is built before the dbt runs,
   because a model built on a stale source still "succeeds", it just has nothing new.
2. Freshness checks: every hour, `dbt source freshness` asks each source
   "when was your newest row loaded?" and compares the lag to warn/error thresholds.
   That is exactly what lands in sources.json.
"""

from __future__ import annotations

import bisect

import pandas as pd

from .catalog import World
from .io import rng_for
from .stories import Stories


def build_load_timeline(w: World, stories: Stories) -> dict:
    """{source node_id: sorted list of load timestamps}."""
    cfg = w.cfg
    rng = rng_for(cfg["seed"], "loads")
    fcfg = cfg["freshness"]
    # Start a day early so the first checks of the window have history behind them
    start = pd.Timestamp(cfg["dates"]["start"]) - pd.Timedelta(days=1)
    end = pd.Timestamp(cfg["dates"]["data_as_of"])
    outages = stories.source_outages()
    quiet_from = end - pd.Timedelta(hours=cfg["baseline"]["quiet_hours_before_as_of"])
    quiet_days = {pd.Timestamp(d) for d in cfg["baseline"]["no_random_noise_on"]}

    # Random connector outages, kept out of the quiet hours before data_as_of
    days = pd.date_range(cfg["dates"]["start"], cfg["dates"]["end"], freq="D")
    for name in w.nodes.loc[w.nodes["resource_type"] == "source", "node_name"]:
        for day in days:
            if rng.random() < fcfg["random_outage_per_day"]:
                o_start = day + pd.Timedelta(minutes=int(rng.integers(0, 24 * 60)))
                o_end = o_start + pd.Timedelta(minutes=int(rng.integers(*fcfg["random_outage_minutes"])))
                if o_end < quiet_from and day not in quiet_days and o_end.normalize() not in quiet_days:
                    outages.setdefault(name, []).append((o_start, o_end))

    timeline = {}
    for r in w.nodes[w.nodes["resource_type"] == "source"].itertuples():
        every = int(r.load_every_minutes)
        offset = int(rng.integers(0, every))          # each connector syncs at its own minute
        scheduled = pd.date_range(start + pd.Timedelta(minutes=offset), end, freq=f"{every}min")
        loads = []
        for t in scheduled:
            # Outages (planted or random): nothing lands until the outage ends, then one catch-up load
            blocked = False
            for o_start, o_end in outages.get(r.node_name, []):
                if o_start <= t < o_end:
                    blocked = True
            if not blocked:
                loads.append(t)
        for o_start, o_end in outages.get(r.node_name, []):
            if o_end <= end:
                loads.append(o_end)
        timeline[r.node_id] = sorted(set(loads))
    return timeline


def last_load_before(timeline: list, ts: pd.Timestamp):
    i = bisect.bisect_right(timeline, ts)
    return timeline[i - 1] if i else None


def build_source_freshness(w: World, timeline: dict) -> pd.DataFrame:
    """fct_source_freshness: one row per source per hourly check."""
    cfg = w.cfg
    fcfg = cfg["freshness"]
    start = pd.Timestamp(cfg["dates"]["start"])
    end = pd.Timestamp(cfg["dates"]["data_as_of"])
    checks = pd.date_range(start + pd.Timedelta(minutes=fcfg["check_minute"]), end, freq=f"{fcfg['check_every_minutes']}min")

    rows = []
    for r in w.nodes[w.nodes["resource_type"] == "source"].itertuples():
        loads = timeline[r.node_id]
        for t in checks:
            last = last_load_before(loads, t)
            lag = (t - last).total_seconds() / 60
            status = "error" if lag > r.error_after_minutes else ("warn" if lag > r.warn_after_minutes else "pass")
            rows.append((r.node_id, t, last, round(lag, 1), int(r.warn_after_minutes), int(r.error_after_minutes), status))
    return pd.DataFrame(rows, columns=["source_node_id", "checked_at", "max_loaded_at", "lag_minutes",
                                       "warn_after_minutes", "error_after_minutes", "status"])


_WARN_CACHE: dict = {}


def stale_sources_at(timeline: dict, source_ids: list, ts: pd.Timestamp, w: World) -> bool:
    """True if any of these sources is past its warn threshold at time ts."""
    if id(w) not in _WARN_CACHE:
        _WARN_CACHE[id(w)] = dict(zip(w.nodes["node_id"], w.nodes["warn_after_minutes"]))
    warn = _WARN_CACHE[id(w)]
    for s in source_ids:
        last = last_load_before(timeline[s], ts)
        if last is None or (ts - last).total_seconds() / 60 > warn[s]:
            return True
    return False

