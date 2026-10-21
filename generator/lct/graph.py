"""Graph logic: dependency order, the closure table and the lineage layout.

All of this is precomputed so Tableau never has to do recursion. Tableau is great
at drawing and filtering rows, and bad at walking graphs, so we hand it rows.
"""

from __future__ import annotations

from collections import deque

import numpy as np
import pandas as pd

from .catalog import World


def topo_order(node_ids: list[str], parents: dict) -> list[str]:
    """Order nodes so every parent comes before its children (Kahn's algorithm).

    This is the same order dbt uses to decide what to build first. If the graph
    had a cycle (A depends on B depends on A) dbt would refuse to run, and so do we.
    """
    node_set = set(node_ids)
    indegree = {n: sum(p in node_set for p in parents.get(n, [])) for n in node_ids}
    children = {n: [] for n in node_ids}
    for n in node_ids:
        for p in parents.get(n, []):
            if p in node_set:
                children[p].append(n)
    queue = deque(sorted(n for n, d in indegree.items() if d == 0))
    order = []
    while queue:
        n = queue.popleft()
        order.append(n)
        for c in sorted(children[n]):
            indegree[c] -= 1
            if indegree[c] == 0:
                queue.append(c)
    if len(order) != len(node_ids):
        raise ValueError("Cycle detected in the lineage graph")
    return order


def upstream_with_depth(start: str, parents: dict) -> dict:
    """Every node upstream of `start`, with the shortest number of hops to reach it."""
    depth = {}
    queue = deque([(start, 0)])
    while queue:
        node, d = queue.popleft()
        for p in parents.get(node, []):
            if p not in depth:          # BFS, so the first visit is the shortest path
                depth[p] = d + 1
                queue.append((p, d + 1))
    return depth


def build_closure(w: World) -> pd.DataFrame:
    """fct_exposure_upstream: one row per exposure and every node upstream of it.

    Read one way: "what feeds this dashboard?" (filter on exposure_id).
    Read the other way: "what does this node feed?" (filter on upstream_node_id),
    which is exactly what the Blast Radius tab needs.
    """
    rows = []
    for exp in w.nodes.loc[w.nodes["resource_type"] == "exposure", "node_id"]:
        for up, d in sorted(upstream_with_depth(exp, w.parents).items(), key=lambda kv: (kv[1], kv[0])):
            rows.append((exp, up, d))
    return pd.DataFrame(rows, columns=["exposure_id", "upstream_node_id", "depth"])


# --------------------------------------------------------------------------- layout

def _positions(node_ids: list[str], parents: dict, layer_order: dict, sort_key: dict, cfg: dict) -> dict:
    """Place nodes in columns by layer and order each column to reduce crossing lines.

    x: the layer (source = 0 ... exposure = 5). A mart that reads another mart is
       nudged a little to the right of it, so the line between them is visible.
    y: position within the column. We use the barycenter heuristic: repeatedly
       sort each column by the average height of its neighbours in the column
       before (or after). Simple, fast, and good enough for ~150 nodes.
    """
    lcfg = cfg["layout"]
    node_set = set(node_ids)
    order = topo_order(node_ids, parents)
    par = {n: [p for p in parents.get(n, []) if p in node_set] for n in node_ids}
    chi = {n: [] for n in node_ids}
    for n, ps in par.items():
        for p in ps:
            chi[p].append(n)

    # Depth within the same layer (mart -> mart chains)
    within = {}
    for n in order:
        same = [within[p] + 1 for p in par[n] if layer_order[p] == layer_order[n]]
        within[n] = max(same, default=0)
    x = {n: layer_order[n] + lcfg["sub_column_offset"] * within[n] for n in node_ids}

    # Vertical ranking is done per layer, not per sub-column, so a nudged mart
    # gets its own row instead of sitting on top of its neighbour.
    columns = sorted(set(layer_order[n] for n in node_ids))
    col_nodes = {c: sorted([n for n in node_ids if layer_order[n] == c], key=lambda n: sort_key[n]) for c in columns}

    def assign_y():
        y = {}
        for c in columns:
            k = len(col_nodes[c])
            for rank, n in enumerate(col_nodes[c]):
                y[n] = (k - 1) / 2 - rank          # centred, first node at the top
        return y

    y = assign_y()
    for sweep in range(lcfg["barycenter_sweeps"]):
        forward = sweep % 2 == 0
        seq = columns[1:] if forward else columns[-2::-1]
        for c in seq:
            def bary(n):
                nbrs = par[n] if forward else chi[n]
                return np.mean([y[m] for m in nbrs]) if nbrs else y[n]
            col_nodes[c].sort(key=lambda n: (-bary(n), sort_key[n]))
            y = assign_y()
    return {n: (round(x[n], 3), round(y[n], 3)) for n in node_ids}


def _edge_path(x1, y1, x2, y2, points: int):
    """Points along a smooth S-curve from parent to child (smoothstep easing)."""
    t = np.linspace(0, 1, points)
    ease = 3 * t**2 - 2 * t**3
    return x1 + (x2 - x1) * t, y1 + (y2 - y1) * ease


def build_layout(w: World) -> pd.DataFrame:
    """fct_lineage_layout: node positions and edge paths, for a global and per-exposure view."""
    nodes = w.nodes
    layer_order = dict(zip(nodes["node_id"], nodes["layer_order"]))
    # Initial order inside a column: group by platform, then domain, then name
    sort_key = {r.node_id: (r.platform, r.domain or "", r.node_name) for r in nodes.itertuples()}
    points = w.cfg["layout"]["edge_points"]

    scopes = {"global": list(nodes["node_id"])}
    for exp in nodes.loc[nodes["resource_type"] == "exposure", "node_id"]:
        scopes[exp] = [exp] + list(upstream_with_depth(exp, w.parents))

    rows = []
    for scope, ids in scopes.items():
        pos = _positions(ids, w.parents, layer_order, sort_key, w.cfg)
        for n, (x, y) in pos.items():
            rows.append(dict(layout_scope=scope, row_type="node", node_id=n, edge_id=None,
                             parent_node_id=None, child_node_id=None, point_order=None, x=x, y=y))
        id_set = set(ids)
        sub = w.edges[w.edges["parent_node_id"].isin(id_set) & w.edges["child_node_id"].isin(id_set)]
        for e in sub.itertuples():
            (x1, y1), (x2, y2) = pos[e.parent_node_id], pos[e.child_node_id]
            xs, ys = _edge_path(x1, y1, x2, y2, points)
            for i, (px, py) in enumerate(zip(xs, ys), start=1):
                rows.append(dict(layout_scope=scope, row_type="edge", node_id=None, edge_id=e.edge_id,
                                 parent_node_id=e.parent_node_id, child_node_id=e.child_node_id,
                                 point_order=i, x=round(px, 4), y=round(py, 4)))
    out = pd.DataFrame(rows)
    out["point_order"] = out["point_order"].astype("Int64")
    return out
