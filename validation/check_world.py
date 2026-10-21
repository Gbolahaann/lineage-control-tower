"""Sanity checks on the world (nodes, edges, closure, layout) plus layout preview charts.

Run after generate.py:
    python validation/check_world.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data"
CHARTS = REPO / "validation" / "charts"

PLATFORM_COLORS = {"databricks": "#83C7EB", "snowflake": "#005FAE", "redshift": "#002C55"}
BG = "#F5F5F3"


def load(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA / f"{name}.csv")


def downstream_exposures(node_name: str, nodes, closure) -> list[str]:
    nid = nodes.loc[nodes["node_name"] == node_name, "node_id"].iloc[0]
    exp = closure.loc[closure["upstream_node_id"] == nid, "exposure_id"]
    return sorted(nodes.set_index("node_id").loc[exp, "display_name"])


def checks() -> list[tuple[str, bool, str]]:
    nodes, edges, closure = load("dim_nodes"), load("fct_lineage_edges"), load("fct_exposure_upstream")
    res = []
    by_res = nodes["resource_type"].value_counts().to_dict()
    res.append(("node counts", True, str(by_res)))

    models = nodes[nodes["resource_type"] == "model"]
    res.append(("models by layer", True, str(models["layer"].value_counts().to_dict())))
    res.append(("nodes by platform (current)", True, str(nodes["platform"].value_counts().to_dict())))

    has_parent = set(edges["child_node_id"])
    has_child = set(edges["parent_node_id"])
    orphans = nodes[(nodes["resource_type"] != "source") & ~nodes["node_id"].isin(has_parent)]
    res.append(("every non-source node has a parent", orphans.empty, ", ".join(orphans["node_name"])))
    dead = nodes[(nodes["resource_type"] != "exposure") & ~nodes["node_id"].isin(has_child)]
    res.append(("every non-exposure node feeds something", dead.empty, ", ".join(dead["node_name"])))

    src_ids = set(nodes.loc[nodes["resource_type"] == "source", "node_id"])
    no_src = [e for e, g in closure.groupby("exposure_id") if not set(g["upstream_node_id"]) & src_ids]
    res.append(("every exposure traces back to a raw source", not no_src, ", ".join(no_src)))

    cross = edges[edges["crosses_platform"]]
    res.append(("cross-platform edges", len(cross) > 0, f"{len(cross)} edges"))

    # Story wiring
    s5 = downstream_exposures("raw_stripe.payments", nodes, closure)
    res.append(("story 5: exposures downstream of raw_stripe.payments", len(s5) >= 5, "; ".join(s5)))

    hub = set()
    for m in ["stg_hubspot__deals", "stg_hubspot__contacts", "stg_hubspot__companies"]:
        hub.update(downstream_exposures(m, nodes, closure))
    dash = nodes[(nodes["display_name"].isin(hub)) & (nodes["exposure_type"] == "dashboard")]
    res.append(("story 4: dashboards downstream of the 3 hubspot models", len(dash) == 4,
                "; ".join(sorted(dash["display_name"]))))

    s6 = downstream_exposures("pds_commerce_sales", nodes, closure)
    res.append(("story 6: exposures on pds_commerce_sales", len(s6) == 3, "; ".join(s6)))

    s7 = downstream_exposures("fct_sessions", nodes, closure)
    res.append(("story 7: Web Funnel sits on fct_sessions", "Web Funnel Analysis" in s7, "; ".join(s7)))

    s2 = downstream_exposures("dim_customers", nodes, closure)
    res.append(("story 2: exposures downstream of dim_customers", len(s2) > 0, "; ".join(s2)))

    s9 = downstream_exposures("raw_wms.inventory", nodes, closure)
    res.append(("story 9: exposures downstream of raw_wms.inventory", len(s9) > 0, "; ".join(s9)))

    orphan_exp = nodes[(nodes["resource_type"] == "exposure") & nodes["owner_name"].isna() & nodes["is_declared"]]
    res.append(("story 8: declared exposures with no owner", list(orphan_exp["node_name"]) == ["pricing_experiment_analysis"],
                ", ".join(orphan_exp["node_name"])))
    return res


def plot_scope(scope: str, title: str, fname: str, label_layers=("exposure", "semantic", "mart", "source")) -> None:
    layout, nodes = load("fct_lineage_layout"), load("dim_nodes")
    lay = layout[layout["layout_scope"] == scope]
    info = nodes.set_index("node_id")
    n_nodes = (lay["row_type"] == "node").sum()
    fig_h = max(6, n_nodes * 0.075 if scope == "global" else n_nodes * 0.28)
    fig, ax = plt.subplots(figsize=(16, fig_h), facecolor=BG)
    ax.set_facecolor(BG)

    # Edges: one line per edge_id, points in point_order, exactly like Tableau's path shelf
    for _, e in lay[lay["row_type"] == "edge"].sort_values("point_order").groupby("edge_id"):
        ax.plot(e["x"], e["y"], color="#9AA6B2", lw=0.6, alpha=0.6, zorder=1)

    pts = lay[lay["row_type"] == "node"].copy()
    pts["platform"] = pts["node_id"].map(info["platform"])
    pts["layer"] = pts["node_id"].map(info["layer"])
    pts["label"] = pts["node_id"].map(info["display_name"])
    for plat, g in pts.groupby("platform"):
        ax.scatter(g["x"], g["y"], s=36 if scope == "global" else 70, color=PLATFORM_COLORS[plat],
                   edgecolor="white", lw=0.6, zorder=2, label=plat.title())
    for r in pts.itertuples():
        if scope != "global" or r.layer in label_layers:
            ha = "left" if r.layer != "source" else "right"
            dx = 0.06 if ha == "left" else -0.06
            ax.text(r.x + dx, r.y, r.label, fontsize=6 if scope == "global" else 8, va="center", ha=ha, color="#002C55")

    layers = ["Sources", "Staging", "Intermediate", "Marts", "BI semantic", "Exposures"]
    # Column headers pinned just above the plot area, whatever the data range
    for i, name in enumerate(layers):
        ax.text(i, 1.01, name, ha="center", va="bottom", fontsize=11, fontweight="bold",
                color="#002C55", transform=ax.get_xaxis_transform())
    ax.set_xlim(-1.4, 6.4)
    ax.axis("off")
    ax.legend(loc="lower left", frameon=False, title="Platform (current)")
    ax.set_title(title, loc="left", fontsize=14, color="#002C55", fontweight="bold", pad=40)
    CHARTS.mkdir(parents=True, exist_ok=True)
    fig.savefig(CHARTS / fname, dpi=130, bbox_inches="tight", facecolor=BG)
    plt.close(fig)


if __name__ == "__main__":
    ok = True
    for name, passed, detail in checks():
        ok &= passed
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
    plot_scope("global", "Acme Retail Co.: global lineage layout (from fct_lineage_layout)", "00_layout_global.png")
    plot_scope("exposure.acme_core.executive_revenue_dashboard",
               "Per-exposure layout: Executive Revenue Dashboard", "00_layout_executive_revenue.png")
    print("charts written to validation/charts/")
    raise SystemExit(0 if ok else 1)
