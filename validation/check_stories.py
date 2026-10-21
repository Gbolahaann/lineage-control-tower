"""Prove each of the 11 planted stories is visible in the generated data.

Run after generate.py:
    python validation/check_stories.py

For every story this prints PASS or FAIL with the evidence, and saves one chart
to validation/charts/. It also computes the zombie and incremental-candidate
thresholds against the generated numbers, and writes everything to
validation/story_results.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from health import Health, load  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
CHARTS = REPO / "validation" / "charts"
CFG = yaml.safe_load(open(REPO / "generator" / "config.yaml"))
AS_OF = pd.Timestamp(CFG["dates"]["data_as_of"])

# Verata brand + the spec's muted status set
NAVY, BLUE, SKY, BG = "#002C55", "#005FAE", "#83C7EB", "#F5F5F3"
STATUS = {"green": "#2F9E6B", "amber": "#E8A33D", "red": "#D2453F", "grey": "#A3ADB8"}
PLATFORM = {"databricks": SKY, "snowflake": BLUE, "redshift": NAVY}
plt.rcParams.update({"axes.facecolor": BG, "figure.facecolor": BG, "axes.edgecolor": "#C9CED6",
                     "axes.labelcolor": NAVY, "xtick.color": NAVY, "ytick.color": NAVY,
                     "axes.spines.top": False, "axes.spines.right": False, "font.size": 10})

H = Health()
nodes = H.nodes
name_of = dict(zip(nodes["node_id"], nodes["node_name"]))
label_of = dict(zip(nodes["node_id"], nodes["display_name"]))
id_of = dict(zip(nodes["node_name"], nodes["node_id"]))
runs = H.prod_runs.assign(name=lambda d: d["node_id"].map(name_of), date=lambda d: d["run_started_at"].dt.normalize())
cost = load("fct_warehouse_cost", ["date"])
cons = load("fct_consumption", ["date"])
obs = load("fct_observed_access", ["date"])
closure = H.closure
results = []


def save(fig, fname: str, title: str, subtitle: str):
    # Title block sized in inches so it never collides with the plot, whatever the figure height
    h = fig.get_figheight()
    fig.text(0.01, 1 - 0.2 / h, title, ha="left", va="top", fontsize=14, fontweight="bold", color=NAVY)
    fig.text(0.01, 1 - 0.55 / h, subtitle.replace("$", r"\$"), ha="left", va="top", fontsize=10, color="#4A5A6A")
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.9 / h))
    fig.savefig(CHARTS / fname, dpi=130)
    plt.close(fig)


def record(n: int, name: str, passed: bool, evidence: str, chart: str):
    results.append(dict(story=n, name=name, passed=bool(passed), evidence=evidence, chart=chart))
    print(f"[{'PASS' if passed else 'FAIL'}] story {n:>2} {name}: {evidence}")


def date_axis(ax):
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=0, interval=2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))


def shade(ax, start, end, label=None):
    ax.axvspan(pd.Timestamp(start), pd.Timestamp(end), color=SKY, alpha=0.18, lw=0)
    if label:
        ax.text(pd.Timestamp(start), ax.get_ylim()[1] * 0.97, " " + label, va="top", fontsize=8, color=NAVY)


# ----------------------------------------------------------------------------- 1
def story_1():
    s = CFG["stories"]["s01_slow_creep"]
    r = runs[(runs["name"] == s["model"]) & (runs["status"] == "success")]
    daily = r.groupby("date")["execution_time_sec"].mean() / 60
    c = cost[(cost["node_id"] == id_of[s["model"]]) & (cost["cost_type"] == "build")].set_index("date")["est_cost_usd"]
    base = daily[: "2026-08-19"].mean()
    peak = daily["2026-09-25":"2026-10-03"].mean()
    post = daily["2026-10-05":].mean()
    passed = 1.7 <= peak / base <= 2.4 and post / base < 0.35
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(c.index, c.values, color=SKY, width=0.8, label="daily build cost (USD)")
    ax.set_ylabel("Daily build cost (USD)")
    ax2 = ax.twinx()
    ax2.plot(daily.index, daily.values, color=NAVY, lw=2, label="avg runtime per run (min)")
    ax2.set_ylabel("Avg runtime per run (minutes)")
    ax2.spines["right"].set_visible(True)
    shade(ax, s["creep_start"], s["creep_peak"], "creep: full-refresh table keeps growing")
    ax.axvline(pd.Timestamp(s["fixed_on"]), color=STATUS["green"], lw=1.5, ls="--")
    ax.text(pd.Timestamp(s["fixed_on"]), ax.get_ylim()[1] * 0.85, " switched to incremental", color=STATUS["green"], fontsize=9)
    date_axis(ax)
    save(fig, "story_01_slow_creep.png", "Story 1: fct_sessions slow creep, then the fix",
         f"Runtime {base:.0f} min to {peak:.0f} min ({peak / base:.1f}x) at the peak, then {post:.1f} min after 4 Oct")
    record(1, "Slow creep", passed, f"runtime x{peak / base:.2f} at peak, x{post / base:.2f} after fix; cost tracks runtime",
           "story_01_slow_creep.png")


# ----------------------------------------------------------------------------- 2
def story_2():
    s = CFG["stories"]["s02_monday_test_failure"]
    t = H.prod_tests[H.prod_tests["test_name"] == s["test"]].copy()
    t["date"] = t["run_at"].dt.normalize()
    fails = t[t["status"] == "fail"].groupby("date").size()
    mondays = set(pd.date_range(s["first_monday"], CFG["dates"]["end"], freq="W-MON"))
    passed = set(fails.index) == mondays
    days = pd.date_range(CFG["dates"]["start"], CFG["dates"]["end"])
    fails = fails.reindex(days, fill_value=0)
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.bar(fails.index, fails.values, color=[STATUS["red"] if v else STATUS["grey"] for v in fails.values], width=0.8)
    for d in mondays:
        ax.text(d, fails[d] + 0.4, "Mon", ha="center", fontsize=7, color=NAVY)
    ax.set_ylabel("Failed executions per day")
    date_axis(ax)
    save(fig, "story_02_monday_test_failure.png", "Story 2: unique_dim_customers_customer_id fails every Monday",
         f"Fails on {len(mondays)} of {len(mondays)} Mondays since {s['first_monday']}, including today, and never on any other day")
    record(2, "Recurring Monday failure", passed,
           f"fails on exactly the {len(mondays)} Mondays from {s['first_monday']} to {CFG['dates']['end']}",
           "story_02_monday_test_failure.png")


# ----------------------------------------------------------------------------- 3
def story_3():
    s = CFG["stories"]["s03_platform_migration"]
    weekly = cost.groupby([pd.Grouper(key="date", freq="W-MON", label="left"), "platform"])["est_cost_usd"].sum().unstack().fillna(0)
    red_after = cost[(cost["platform"] == "redshift") & (cost["date"] > pd.Timestamp(s["window_end"]))]["est_cost_usd"].sum()
    red_before = cost[(cost["platform"] == "redshift") & (cost["date"] < pd.Timestamp(s["window_start"]))]["est_cost_usd"].sum()
    mkt = runs[runs["node_id"].str.startswith("model.acme_marketing")]
    ok = mkt[mkt["status"] != "skipped"].assign(ok=lambda d: d["status"] == "success").groupby("date")["ok"].mean() * 100
    cut_days = [pd.Timestamp(w["migration_date"]) for w in s["waves"]]
    cut_rate = ok[ok.index.isin(cut_days)].mean()
    base_rate = ok[: pd.Timestamp(s["window_start"]) - pd.Timedelta(days=1)].mean()
    passed = red_after == 0 and red_before > 0 and cut_rate < base_rate - 5
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    bottom = np.zeros(len(weekly))
    for p in ["redshift", "snowflake", "databricks"]:
        if p in weekly:
            ax1.bar(weekly.index, weekly[p], bottom=bottom, width=6, color=PLATFORM[p], label=p.title(), align="edge")
            bottom += weekly[p].values
    ax1.set_ylabel("Weekly cost (USD)")
    ax1.legend(frameon=False, ncol=3, loc="upper left")
    ax2.plot(ok.index, ok.values, color=NAVY, lw=1.5)
    for d in cut_days:
        ax2.axvline(d, color=STATUS["red"], ls="--", lw=1)
    ax2.set_ylabel("Marketing model\nrun success %")
    ax2.set_ylim(max(0, ok.min() - 5), 101)
    shade(ax1, s["window_start"], s["window_end"], "migration window")
    date_axis(ax2)
    save(fig, "story_03_platform_migration.png", "Story 3: marketing models move from Redshift to Snowflake",
         f"Redshift spend goes to zero after {s['window_end']}; marketing run success dips to {cut_rate:.0f}% on cutover days (baseline {base_rate:.1f}%)")
    record(3, "Platform migration", passed,
           f"Redshift ${red_before:,.0f} before / ${red_after:,.0f} after; cutover-day success {cut_rate:.0f}% vs {base_rate:.1f}%",
           "story_03_platform_migration.png")


# ----------------------------------------------------------------------------- 4
def story_4():
    s = CFG["stories"]["s04_schema_change"]
    sc = runs[runs["error_category"] == "schema_change"]
    broken = sorted(sc["name"].unique())
    day = pd.Timestamp(s["date"])
    during = H.status_at(day + pd.Timedelta(hours=13))
    after = H.status_at(day + pd.Timedelta(hours=18))
    dash = nodes[nodes["exposure_type"] == "dashboard"].set_index("node_id")
    hub_red = during[during["reasons"].str.contains("hubspot|pipeline|marketing_roi|attribution|contacts|companies|board_kpis")
                     & (during["status"] == "red") & during["exposure_id"].isin(dash.index)]
    still = after[after["reasons"].str.contains("hubspot") & (after["status"] == "red")]
    passed = broken == sorted(s["broken_models"]) and sc["date"].nunique() == 1 and len(hub_red) == 4 and still.empty
    # Chart: every model run on the day for the hubspot lineage
    ids = set()
    for b in s["broken_models"]:
        bid = id_of[b]
        ids.add(bid)
        frontier = [bid]
        edges = load("fct_lineage_edges")
        kids = edges.groupby("parent_node_id")["child_node_id"].apply(list).to_dict()
        while frontier:
            n = frontier.pop()
            for c in kids.get(n, []):
                if c.startswith("model.") and c not in ids:
                    ids.add(c)
                    frontier.append(c)
    r = runs[runs["node_id"].isin(ids) & (runs["date"] == day)]
    order = sorted(r["name"].unique(), key=lambda n: (not n.startswith("stg"), not n.startswith("int"), n))
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = {"success": STATUS["green"], "error": STATUS["red"], "skipped": STATUS["grey"]}
    for st, g in r.groupby("status"):
        ax.scatter(g["run_started_at"], g["name"].map({n: i for i, n in enumerate(order)}), color=colors[st], s=60, label=st)
    ax.set_yticks(range(len(order)), order, fontsize=8)
    ax.invert_yaxis()
    ax.axvspan(day + pd.Timedelta(s["broken_from"] + ":00"), day + pd.Timedelta(s["fixed_at"] + ":00"), color=STATUS["red"], alpha=0.08)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.legend(frameon=False, loc="lower right")
    save(fig, "story_04_schema_change.png", "Story 4: a column rename in raw_hubspot breaks 3 models for one day",
         "3 staging models error and everything downstream skips; 4 dashboards are red at 13:00; a manual rerun after the hotfix recovers")
    record(4, "Schema change incident", passed,
           f"errored: {', '.join(broken)}; red dashboards at 13:00: {len(hub_red)}; recovered same day: {still.empty}",
           "story_04_schema_change.png")


# ----------------------------------------------------------------------------- 5
def story_5():
    s = CFG["stories"]["s05_freshness_cascade"]
    sid = id_of[s["source"]]
    f = H.fresh[H.fresh["source_node_id"] == sid].set_index("checked_at")
    errs = f[f["status"] == "error"]
    in_window = errs.index.to_series().between(pd.Timestamp(s["stops_loading_at"]), pd.Timestamp(s["resumes_at"])).all()
    snap = H.status_at("2026-10-01 06:00")
    fin = nodes[(nodes["domain"] == "Finance") & (nodes["resource_type"] == "exposure") & nodes["is_declared"]
                & (nodes["created_date"] <= "2026-10-01")]["node_id"]
    fin_status = snap[snap["exposure_id"].isin(fin)]
    passed = in_window and len(errs) > 0 and (fin_status["status"] == "red").all()
    win = f["2026-09-29 12:00":"2026-10-02 00:00"]
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), gridspec_kw={"width_ratios": [1.5, 1]})
    ax.plot(win.index, win["lag_minutes"] / 60, color=NAVY, lw=2)
    ax.axhline(win["warn_after_minutes"].iloc[0] / 60, color=STATUS["amber"], ls="--", lw=1)
    ax.axhline(win["error_after_minutes"].iloc[0] / 60, color=STATUS["red"], ls="--", lw=1)
    ax.text(win.index[0], win["warn_after_minutes"].iloc[0] / 60 + 0.2, "warn", color=STATUS["amber"])
    ax.text(win.index[0], win["error_after_minutes"].iloc[0] / 60 + 0.2, "error", color=STATUS["red"])
    ax.set_ylabel("Lag since last load (hours)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b %H:%M"))
    ax.tick_params(axis="x", rotation=30)
    ax2.axis("off")
    ax2.set_title("Finance exposures at 1 Oct 06:00", loc="left", color=NAVY, fontsize=11)
    for i, r in enumerate(fin_status.sort_values("display_name").itertuples()):
        ax2.add_patch(plt.Rectangle((0, 1 - (i + 1) * 0.1), 0.06, 0.08, color=STATUS[r.status], transform=ax2.transAxes))
        ax2.text(0.09, 1 - (i + 1) * 0.1 + 0.04, f"{r.display_name}  ({r.status.upper()})", transform=ax2.transAxes,
                 va="center", fontsize=9, color=NAVY)
    save(fig, "story_05_freshness_cascade.png", "Story 5: raw_stripe.payments stops loading into month-end close",
         f"About 14 hours without loads; freshness error from {errs.index.min():%d %b %H:%M} to {errs.index.max():%H:%M}; every finance exposure red")
    record(5, "Freshness breach cascade", passed,
           f"{len(errs)} error checks, all inside the outage; {(fin_status['status'] == 'red').sum()}/{len(fin_status)} finance exposures red at 06:00 on 1 Oct",
           "story_05_freshness_cascade.png")


# ----------------------------------------------------------------------------- 6
def story_6():
    s = CFG["stories"]["s06_green_dbt_broken_dashboard"]
    sid = id_of[s["semantic_object"]]
    snap = H.status_at("2026-10-13 12:00")
    on_pds = closure.loc[closure["upstream_node_id"] == sid, "exposure_id"]
    affected = snap[snap["exposure_id"].isin(on_pds)]
    only_refresh = affected["reasons"].str.contains("refresh failed").all() and not affected["reasons"].str.contains("model error").any()
    parents = load("fct_lineage_edges").query("child_node_id == @sid")["parent_node_id"]
    ups = closure.loc[closure["exposure_id"].isin(on_pds), "upstream_node_id"]
    upstream_models = set(ups[ups.str.startswith("model.")])
    window = runs[runs["node_id"].isin(upstream_models) & runs["date"].between("2026-10-12", "2026-10-13")]
    dbt_green = (window["status"] == "success").all()
    passed = (affected["status"] == "red").all() and only_refresh and dbt_green and len(affected) == 3
    rf = H.refresh[(H.refresh["node_id"] == sid) & H.refresh["refresh_started_at"].between("2026-10-08", "2026-10-17")]
    dr = runs[runs["node_id"].isin(set(parents)) & runs["date"].between("2026-10-08", "2026-10-16")]
    daily = dr.assign(ok=dr["status"] == "success").groupby("date")["ok"].mean() * 100
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 5.5), sharex=True)
    ax1.bar(daily.index, daily.values, color=STATUS["green"], width=0.7)
    ax1.set_ylim(0, 105)
    ax1.set_ylabel("dbt success %\n(parent marts)")
    col = {"success": STATUS["green"], "failed": STATUS["red"], "skipped_upstream": STATUS["grey"]}
    ax2.scatter(rf["refresh_started_at"], [1] * len(rf), c=rf["status"].map(col), s=90, marker="s")
    ax2.set_yticks([])
    ax2.set_ylabel("pds_commerce_sales\nextract refreshes")
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    save(fig, "story_06_green_dbt_broken_dashboard.png", "Story 6: dbt is green, but three dashboards serve stale data",
         "Every parent mart builds fine on 12-13 Oct, but the Tableau extract fails (expired OAuth token); a dbt-only monitor sees nothing")
    record(6, "Green dbt, broken dashboard", passed,
           f"{len(affected)} exposures red at 13 Oct 12:00 ({', '.join(sorted(affected['display_name']))}) with only a refresh failure; upstream dbt 100% green: {dbt_green}",
           "story_06_green_dbt_broken_dashboard.png")


# ----------------------------------------------------------------------------- 7 + thresholds
def cost_per_exposure(start, end) -> pd.DataFrame:
    """Spec: a shared model's build cost is split evenly across the declared exposures it feeds."""
    declared = set(nodes.loc[(nodes["resource_type"] == "exposure") & nodes["is_declared"], "node_id"])
    cl = closure[closure["exposure_id"].isin(declared)]
    fan_out = cl.groupby("upstream_node_id")["exposure_id"].nunique()
    c = cost[(cost["cost_type"] == "build") & cost["date"].between(start, end)].groupby("node_id")["est_cost_usd"].sum()
    alloc = cl.assign(share=lambda d: d["upstream_node_id"].map(c).fillna(0) / d["upstream_node_id"].map(fan_out))
    per_exp = alloc.groupby("exposure_id")["share"].sum().rename("cost_usd")
    ev = cons[cons["date"].between(start, end)].groupby("exposure_id")["events"].sum().rename("events")
    df = pd.concat([per_exp, ev], axis=1).fillna(0)
    df["cost_per_event"] = df["cost_usd"] / df["events"].replace(0, np.nan)
    df["display_name"] = df.index.map(label_of)
    df["exposure_type"] = df.index.map(dict(zip(nodes["node_id"], nodes["exposure_type"])))
    return df


THRESHOLDS = {}


def story_7():
    s = CFG["stories"]["s07_zombie_dashboard"]
    zid = id_of[s["exposure"]]
    monthly = cons[cons["exposure_id"] == zid].groupby(cons["date"].dt.to_period("M"))["events"].sum()
    end = AS_OF.normalize()
    df = cost_per_exposure(end - pd.Timedelta(days=29), end)
    others = df.drop(zid)
    # Zombie thresholds: fewer than N events in 30 days AND cost per event above $X.
    # N sits well above the zombie and well below the quietest real product;
    # X sits above every healthy product's cost per event.
    min_events_real = others[others["exposure_type"] == "dashboard"]["events"].min()
    THRESHOLDS["zombie_max_events_30d"] = 10
    THRESHOLDS["zombie_min_cost_per_event_usd"] = 5.0
    zombies = df[(df["events"] < 10) & (df["cost_per_event"] > 5.0)]
    passed = monthly.max() < 5 and list(zombies.index) == [zid]
    fig, ax = plt.subplots(figsize=(11, 6.5))
    ax.scatter(others["events"].clip(lower=0.8), others["cost_usd"], s=55, color=BLUE, alpha=0.75, label="other data products")
    z = df.loc[zid]
    ax.scatter([max(z["events"], 0.8)], [z["cost_usd"]], s=170, color=STATUS["red"], zorder=3, label="zombie")
    labelled = [zid] + list(others.sort_values("cost_usd", ascending=False).index[:3])
    for idx in labelled:
        r = df.loc[idx]
        ax.annotate(r["display_name"], (max(r["events"], 0.8), r["cost_usd"]), fontsize=8, color=NAVY,
                    xytext=(6, -12 if idx == zid else 4), textcoords="offset points")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.axvline(10, color=STATUS["grey"], ls="--", lw=1)
    ax.set_xlabel("Consumption events, last 30 days (log)")
    ax.set_ylabel("Allocated build cost, last 30 days, USD (log)")
    ax.axhspan(100, ax.get_ylim()[1], xmax=0.27, color=STATUS["red"], alpha=0.06, lw=0)
    ax.text(1.6, 130, "zombie quadrant:\nexpensive, nobody looks", color=STATUS["red"], fontsize=9)
    ax.legend(frameon=False, loc="lower right")
    save(fig, "story_07_zombie_dashboard.png", "Story 7: Web Funnel Analysis is a zombie",
         f"{int(z['events'])} view{'s' if z['events'] != 1 else ''} in 30 days for ${z['cost_usd']:,.0f} of allocated cost (${z['cost_per_event']:,.0f} per view); max {monthly.max()} views in any month")
    record(7, "Zombie dashboard", passed,
           f"max {monthly.max()} views/month; ${z['cost_per_event']:,.0f}/view vs next highest ${others['cost_per_event'].max():,.2f}; only zombie flagged: {list(zombies['display_name'])}",
           "story_07_zombie_dashboard.png")
    return df


# ----------------------------------------------------------------------------- 8
def story_8():
    exps = nodes[(nodes["resource_type"] == "exposure") & nodes["is_declared"]]
    orphans = exps[exps["owner_name"].isna()]
    passed = list(orphans["node_name"]) == [CFG["stories"]["s08_orphan_exposure"]["exposure"]]
    by_type = exps.assign(owned=exps["owner_name"].notna()).groupby(["exposure_type", "owned"]).size().unstack(fill_value=0)
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.barh(by_type.index, by_type.get(True, 0), color=STATUS["green"], label="has owner")
    ax.barh(by_type.index, by_type.get(False, 0), left=by_type.get(True, 0), color=STATUS["red"], label="no owner")
    ax.legend(frameon=False)
    ax.set_xlabel("Declared exposures")
    save(fig, "story_08_orphan_exposure.png", "Story 8: one declared data product has no owner",
         f"Ownership coverage {exps['owner_name'].notna().mean():.0%}; the orphan is {', '.join(orphans['display_name'])}")
    record(8, "Orphan exposure", passed, f"unowned declared exposures: {list(orphans['display_name'])}",
           "story_08_orphan_exposure.png")


# ----------------------------------------------------------------------------- 9
def story_9():
    snap = H.status_at(AS_OF)
    declared = set(nodes.loc[nodes["is_declared"] & (nodes["resource_type"] == "exposure"), "node_id"])
    snap = snap[(snap["status"] != "grey") & snap["exposure_id"].isin(declared)]   # the grid shows declared products
    s = CFG["stories"]["s09_live_issues_today"]
    test_amber = snap["reasons"].str.contains("test failing: dim_customers").any()
    fresh_amber = snap["reasons"].str.contains(f"freshness warn: {s['warn_source']}").any()
    passed = (snap["status"] != "red").all() and test_amber and fresh_amber
    snap = snap.merge(nodes[["node_id", "exposure_type", "is_declared"]], left_on="exposure_id", right_on="node_id")
    snap = snap.sort_values(["status", "display_name"])
    cols = 4
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.axis("off")
    for i, r in enumerate(snap.itertuples()):
        x, y = (i % cols) * 0.25, 1 - (i // cols + 1) * 0.13
        ax.add_patch(plt.Rectangle((x, y), 0.235, 0.11, color="white", transform=ax.transAxes))
        ax.add_patch(plt.Rectangle((x, y), 0.012, 0.11, color=STATUS[r.status], transform=ax.transAxes))
        ax.text(x + 0.02, y + 0.075, r.display_name, transform=ax.transAxes, fontsize=8.5, color=NAVY, fontweight="bold")
        why = r.reasons.split(";")[0] if r.reasons else "all upstream checks passing"
        ax.text(x + 0.02, y + 0.03, f"{r.status.upper()} · {why}", transform=ax.transAxes, fontsize=7, color="#4A5A6A")
    counts = snap["status"].value_counts().to_dict()
    save(fig, "story_09_live_issues_today.png", "Story 9: what the Health Overview shows on 19 Oct",
         f"No red, but not all green: {counts.get('amber', 0)} amber (Monday dim_customers test, raw_wms.inventory freshness warn), {counts.get('green', 0)} green")
    record(9, "Live issues today", passed, f"status at data_as_of: {counts}", "story_09_live_issues_today.png")


# ----------------------------------------------------------------------------- 10
def story_10():
    s = CFG["stories"]["s10_dashboard_sprawl"]
    sp = nodes[(nodes["build_method"] == "ai_assisted") & (nodes["exposure_type"] == "dashboard")]
    same_pds = closure[closure["exposure_id"].isin(sp["node_id"]) & (closure["depth"] == 1)]["upstream_node_id"].unique()
    falling = []
    fig, ax = plt.subplots(figsize=(12, 5))
    for i, r in enumerate(sp.sort_values("created_date").itertuples()):
        c = cons[cons["exposure_id"] == r.node_id].set_index("date")["events"]
        rolling = c.rolling(7, min_periods=3).mean()
        falling.append(rolling.iloc[-1] < rolling.max() * 0.6)    # last week well below its launch peak
        ax.plot(c.index, c.rolling(7, min_periods=1).mean(), lw=2, label=r.display_name,
                color=[NAVY, BLUE, SKY, "#5C7FA3", "#9AB8D6"][i % 5])
    ax.set_ylabel("Views per day (7-day average)")
    ax.legend(frameon=False, fontsize=8)
    date_axis(ax)
    passed = len(sp) == len(s["created"]) and len(same_pds) == 1 and all(falling) \
        and (sp["created_date"] >= pd.Timestamp(s["created"][0])).all()
    save(fig, "story_10_dashboard_sprawl.png", "Story 10: AI-assisted dashboard sprawl",
         f"{len(sp)} near-duplicate dashboards on {same_pds[0].split('.')[-1]} since {s['created'][0]}, each with a launch spike and fading usage")
    record(10, "Dashboard sprawl", passed,
           f"{len(sp)} ai_assisted dashboards, all on {', '.join(p.split('.')[-1] for p in same_pds)}; usage falling for all: {all(falling)}",
           "story_10_dashboard_sprawl.png")


# ----------------------------------------------------------------------------- 11
def story_11():
    s = CFG["stories"]["s11_undeclared_consumers"]
    und = obs[obs["mapped_exposure_id"].isna()]
    first_seen = und["date"].min()
    principals = sorted(und["principal"].unique())
    reads = {id_of[n] for n in s["consumers"][0]["reads"]}
    c = cost[cost["node_id"].isin(reads) & (cost["date"] >= "2026-09-01")]
    agent = s["consumers"][0]["principal"]
    c = c.assign(kind=np.where(c["cost_type"] == "build", "build",
                               np.where(c["principal"] == agent, "undeclared agent", "declared consumers")))
    daily = c.groupby(["date", "kind"])["est_cost_usd"].sum().unstack(fill_value=0)
    last28 = daily.loc[AS_OF.normalize() - pd.Timedelta(days=27):]
    agent_share = last28["undeclared agent"].sum() / last28.sum().sum()
    cov = obs.assign(mapped=obs["mapped_exposure_id"].notna()).groupby("date").apply(
        lambda g: g.loc[g["mapped"], "principal"].nunique() / g["principal"].nunique(), include_groups=False) * 100
    passed = first_seen == pd.Timestamp(s["consumers"][0]["first_seen"]) and len(principals) == 3 and agent_share > 0.25
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7), sharex=True, gridspec_kw={"height_ratios": [2, 1]})
    bottom = np.zeros(len(daily))
    for k, col in [("build", SKY), ("declared consumers", BLUE), ("undeclared agent", STATUS["red"])]:
        if k in daily:
            ax1.bar(daily.index, daily[k], bottom=bottom, color=col, width=0.85, label=k)
            bottom += daily[k].values
    ax1.set_ylabel("Daily Snowflake cost on\nfct_orders + dim_products (USD)")
    ax1.legend(frameon=False, loc="upper left")
    cov = cov[cov.index >= "2026-09-01"]
    ax2.plot(cov.index, cov.values, color=NAVY, lw=2)
    ax2.set_ylabel("Declared coverage %\n(observed principals)")
    date_axis(ax2)
    save(fig, "story_11_undeclared_consumers.png", "Story 11: consumers nobody registered",
         f"From {first_seen:%d %b} an unregistered pricing agent reads fct_orders and dim_products; it is {agent_share:.0%} of their cost over the last 28 days")
    record(11, "Undeclared consumers", passed,
           f"{len(principals)} unmapped principals ({', '.join(principals)}), first seen {first_seen:%d %b}; agent = {agent_share:.0%} of cost on its tables (28d)",
           "story_11_undeclared_consumers.png")


def incremental_threshold():
    """Incremental candidate: materialization table AND rows above X AND runtime trend above +25%."""
    mr = H.prod_runs[H.prod_runs["status"] == "success"].copy()
    mr["date"] = mr["run_started_at"].dt.normalize()
    out = []
    for as_of in [pd.Timestamp("2026-09-20"), pd.Timestamp("2026-10-01"), AS_OF.normalize()]:
        recent = mr[mr["date"].between(as_of - pd.Timedelta(days=6), as_of)]
        prior = mr[mr["date"].between(as_of - pd.Timedelta(days=34), as_of - pd.Timedelta(days=7))]
        trend = recent.groupby("node_id")["execution_time_sec"].mean() / prior.groupby("node_id")["execution_time_sec"].mean() - 1
        mat = recent.sort_values("run_started_at").groupby("node_id")["materialization"].last()
        rows = recent.groupby("node_id")["rows_affected"].max()
        df = pd.concat([trend.rename("trend"), mat, rows.rename("rows")], axis=1)
        flagged = df[(df["materialization"] == "table") & (df["rows"] > 10_000_000) & (df["trend"] > 0.25)]
        out.append((as_of, [name_of[n] for n in flagged.index], df["trend"].drop(flagged.index, errors="ignore").max()))
    THRESHOLDS["incremental_min_rows"] = 10_000_000
    return out


if __name__ == "__main__":
    CHARTS.mkdir(parents=True, exist_ok=True)
    for fn in [story_1, story_2, story_3, story_4, story_5, story_6, story_7, story_8, story_9, story_10, story_11]:
        fn()
    inc = incremental_threshold()
    print("\nThresholds:", THRESHOLDS)
    for as_of, flagged, max_other in inc:
        print(f"  incremental candidates as of {as_of:%d %b}: {flagged or 'none'} (highest other runtime trend {max_other:+.0%})")

    lines = ["# Story validation results", "", f"Generated from data as of {AS_OF:%Y-%m-%d %H:%M} UTC.", "",
             "| # | Story | Result | Evidence | Chart |", "|---|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r['story']} | {r['name']} | {'PASS' if r['passed'] else 'FAIL'} | {r['evidence']} | "
                     f"[{r['chart']}](charts/{r['chart']}) |")
    lines += ["", "## Thresholds", ""]
    for k, v in THRESHOLDS.items():
        lines.append(f"- `{k}`: {v}")
    for as_of, flagged, max_other in inc:
        lines.append(f"- Incremental candidates as of {as_of:%d %b}: {', '.join(flagged) or 'none'} "
                     f"(highest runtime trend among the rest: {max_other:+.0%})")
    (REPO / "validation" / "story_results.md").write_text("\n".join(lines) + "\n")
    n_pass = sum(r["passed"] for r in results)
    print(f"\n{n_pass}/{len(results)} stories pass")
    sys.exit(0 if n_pass == len(results) else 1)
