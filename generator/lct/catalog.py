"""The catalog: every node in the lineage graph, the edges between them, owners and tests.

In a real company this is what you get by parsing dbt's manifest.json (sources,
models, tests, exposures and the parent/child map) and then adding the BI layer
from the Tableau, Sigma and Power BI metadata APIs.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .io import rng_for

LAYER_ORDER = {"source": 0, "staging": 1, "intermediate": 2, "mart": 3, "semantic": 4, "exposure": 5}

# How each consumer type uses data, for fct_consumption.consumption_type
CONSUMPTION_TYPE = {
    "dashboard": "view", "data_hub": "view", "notebook": "query", "analysis": "query",
    "ml": "query", "data_app": "app_session", "agent": "agent_call",
}

BI_SERVICE_PRINCIPAL = {"tableau": "svc_tableau_server", "sigma": "svc_sigma", "power_bi": "svc_powerbi_gateway"}


def model_layer(name: str) -> str:
    if name.startswith("stg_"):
        return "staging"
    if name.startswith("int_"):
        return "intermediate"
    return "mart"


def primary_key(model_name: str) -> str:
    """Guess a model's primary key column from its name, the way a human would."""
    if model_name in ("dim_customer_360", "fct_churn_features", "dim_customer_behavior"):
        return "customer_id"
    base = model_name.split("__")[-1] if "__" in model_name else model_name.split("_", 1)[1]
    if base.endswith("_daily") or base.endswith("daily"):
        return "date_day"
    if base.endswith("ies"):
        base = base[:-3] + "y"
    elif base.endswith("s") and not base.endswith("ss"):
        base = base[:-1]
    return f"{base}_id"


@dataclass
class World:
    """Everything the rest of the generator needs to know about Acme's data stack."""

    cfg: dict
    spec: dict
    nodes: pd.DataFrame = None            # dim_nodes
    edges: pd.DataFrame = None            # fct_lineage_edges
    owners: pd.DataFrame = None           # dim_owners
    tests: pd.DataFrame = None            # test definitions (one row per dbt test)
    parents: dict = field(default_factory=dict)    # node_id -> [parent node_ids]
    children: dict = field(default_factory=dict)   # node_id -> [child node_ids]
    id_of: dict = field(default_factory=dict)      # short name -> node_id
    model_meta: dict = field(default_factory=dict)  # node_id -> runtime / rows / job etc.

    def node(self, node_id: str) -> pd.Series:
        return self.nodes.set_index("node_id").loc[node_id]


def build_world(cfg: dict, spec: dict) -> World:
    rng = rng_for(cfg["seed"], "catalog")
    w = World(cfg=cfg, spec=spec)
    stories = cfg["stories"]

    # ------------------------------------------------------------------ owners
    owners = pd.DataFrame(spec["owners"])
    owners["owner_name"] = owners["name"]
    owners["owner_team"] = owners["team"]
    owners["email"] = (
        owners["name"].str.lower().str.replace(" ", ".", regex=False) + "@" + spec["email_domain"]
    )
    owners["slack_channel"] = owners["team"].map(lambda t: spec["teams"][t]["slack"])
    owners["on_call_rotation"] = owners["on_call"].map(lambda v: "yes" if v else "no")
    w.owners = owners[["owner_name", "owner_team", "email", "slack_channel", "on_call_rotation"]]
    team_of = dict(zip(owners["owner_name"], owners["owner_team"]))
    members = owners.groupby("owner_team")["owner_name"].apply(list).to_dict()

    # ------------------------------------------------- migration lookup (story 3)
    migrated = {}
    if stories["s03_platform_migration"]["enabled"]:
        s3 = stories["s03_platform_migration"]
        for wave in s3["waves"]:
            for name in wave["sources"] + wave["models"]:
                migrated[name] = (s3["from_platform"], pd.Timestamp(wave["migration_date"]))

    projects = spec["dbt_projects"]
    platforms = spec["platforms"]
    rows = []

    def created(lo: str, hi: str) -> pd.Timestamp:
        lo, hi = pd.Timestamp(lo), pd.Timestamp(hi)
        return lo + pd.Timedelta(days=int(rng.integers(0, (hi - lo).days + 1)))

    # ------------------------------------------------------------------ sources
    for name, s in spec["sources"].items():
        project = s["project"]
        platform = projects[project]["platform"]
        mig_from, mig_date = migrated.get(name, (None, None))
        if mig_from:
            platform = "snowflake"
        team = s.get("team", "Data Platform")
        node_id = f"source.{project}.{name}"
        w.id_of[name] = node_id
        schema, table = name.split(".")
        rows.append(dict(
            node_id=node_id, node_name=name, display_name=name, resource_type="source", layer="source",
            platform=platform, dbt_project=project,
            database_name=platforms[platform]["raw_database"], schema_name=schema,
            materialization=None, domain=s["domain"], owner_team=team,
            owner_name=members[team][int(rng.integers(len(members[team])))],
            tags=f"source|{s['domain'].lower()}|{schema}",
            has_description=bool(rng.random() < 0.9),
            created_date=created("2023-01-01", "2025-06-30") if project != "acme_marketing" else created("2021-03-01", "2022-12-31"),
            migrated_from_platform=mig_from, migration_date=mig_date,
            load_every_minutes=s["load_every"], warn_after_minutes=s["warn"], error_after_minutes=s["error"],
        ))

    # ------------------------------------------------------------------- models
    for name, m in spec["models"].items():
        project = m["project"]
        layer = model_layer(name)
        platform = projects[project]["platform"]
        mig_from, mig_date = migrated.get(name, (None, None))
        if mig_from:
            platform = "snowflake"
        team = m.get("team") or ("Data Platform" if layer == "staging" else spec["domain_teams"][m["domain"]])
        mat = m.get("mat", "view")
        # Views cost almost nothing to "build": dbt just re-issues CREATE VIEW
        runtime = m.get("runtime", 4 if layer == "staging" else 6)
        node_id = f"model.{project}.{name}"
        w.id_of[name] = node_id
        job = m.get("job", spec["default_jobs"][project])
        w.model_meta[node_id] = dict(
            name=name, project=project, job=job, mat=mat, runtime=runtime,
            rows=m.get("rows"), original_platform=projects[project]["platform"],
            migration_date=mig_date,
        )
        domain_schema = "staging" if layer == "staging" else ("intermediate" if layer == "intermediate" else f"marts_{m['domain'].lower()}")
        tags = [layer, m["domain"].lower(), job]
        if any(k in name for k in ("customer", "contact")):
            tags.append("pii")
        rows.append(dict(
            node_id=node_id, node_name=name, display_name=name, resource_type="model", layer=layer,
            platform=platform, dbt_project=project,
            database_name=platforms[platform]["database"], schema_name=domain_schema,
            materialization=mat, domain=m["domain"], owner_team=team,
            owner_name=members[team][int(rng.integers(len(members[team])))],
            tags="|".join(tags),
            has_description=bool(rng.random() < spec["teams"][team]["hygiene"]["docs"]),
            created_date=created("2023-01-01", "2026-05-31") if project != "acme_marketing" else created("2021-03-01", "2023-06-30"),
            migrated_from_platform=mig_from, migration_date=mig_date, dbt_job=job,
        ))

    # Parent links for sources and models (straight from the "SQL")
    edge_rows = []

    def link(parent_name: str, child_id: str, source: str):
        edge_rows.append((w.id_of[parent_name], child_id, source))

    for name, m in spec["models"].items():
        for p in m["parents"]:
            link(p, w.id_of[name], "manifest")

    platform_of = {r["node_id"]: r["platform"] for r in rows}
    project_of = {r["node_id"]: r["dbt_project"] for r in rows}

    # --------------------------------------------------------- semantic objects
    for name, s in spec["semantic_objects"].items():
        node_id = f"semantic.{s['bi_tool']}.{name}"
        w.id_of[name] = node_id
        parent_ids = [w.id_of[p] for p in s["parents"]]
        platform = Counter(platform_of[p] for p in parent_ids).most_common(1)[0][0]
        project = Counter(project_of[p] for p in parent_ids).most_common(1)[0][0]
        platform_of[node_id], project_of[node_id] = platform, project
        rows.append(dict(
            node_id=node_id, node_name=name, display_name=name, resource_type="semantic", layer="semantic",
            platform=platform, dbt_project=None, database_name=None, schema_name=None,
            materialization=None, domain=s["domain"], owner_name=s["owner"], owner_team=team_of[s["owner"]],
            tags=f"semantic|{s['bi_tool']}|{s['domain'].lower()}",
            has_description=bool(rng.random() < 0.85),
            created_date=created("2024-01-01", "2026-04-30"),
            semantic_object_type=s["type"], connection_type=s["connection"], bi_tool=s["bi_tool"],
            service_principal=BI_SERVICE_PRINCIPAL[s["bi_tool"]],
            refreshes_per_day=s.get("refreshes_per_day"),
            close_window_refreshes_per_day=s.get("close_window_refreshes_per_day"),
        ))
        for p in s["parents"]:
            link(p, node_id, "bi_metadata")

    # ---------------------------------------------------------------- exposures
    sprawl_cfg = stories["s10_dashboard_sprawl"]
    sprawl_dates = [pd.Timestamp(d) for d in sprawl_cfg["created"]] if sprawl_cfg["enabled"] else []
    undeclared_cfg = {c["exposure"]: c for c in stories["s11_undeclared_consumers"]["consumers"]} \
        if stories["s11_undeclared_consumers"]["enabled"] else {}
    sprawl_i = 0

    for name, e in spec["exposures"].items():
        declared = e.get("declared", True)
        is_sprawl = e.get("sprawl", False)
        # Switched-off stories remove their consumers from the world entirely
        if is_sprawl:
            if sprawl_i >= len(sprawl_dates):
                continue
            created_on = sprawl_dates[sprawl_i]
            sprawl_i += 1
        elif not declared:
            if name not in undeclared_cfg:
                continue
            created_on = pd.Timestamp(undeclared_cfg[name]["first_seen"])
        elif e["type"] in ("agent", "data_hub", "data_app") and e.get("build") == "ai_assisted":
            created_on = created("2026-04-01", "2026-07-01")
        else:
            created_on = created("2024-02-01", "2026-05-31")

        owner = e.get("owner")
        if name == stories["s08_orphan_exposure"]["exposure"] and not stories["s08_orphan_exposure"]["enabled"]:
            owner = "Hannah Weber"   # story off: the notebook gets a normal owner

        parent_ids = [w.id_of[p] for p in e["parents"]]
        # The dbt models behind this exposure: direct parents, or the models
        # under its semantic objects. Their majority platform becomes the exposure's.
        model_ids = [p for p in parent_ids if p.startswith("model.")]
        model_ids += [x for (x, c, _) in edge_rows if c in parent_ids and x.startswith("model.")]
        # An exposure can name its platform outright (useful when its parents are split evenly)
        platform = e.get("platform") or Counter(platform_of[m] for m in model_ids).most_common(1)[0][0]
        project = Counter(project_of[m] for m in model_ids if platform_of[m] == platform).most_common(1)[0][0]
        node_id = f"exposure.{project if declared else 'observed'}.{name}"
        w.id_of[name] = node_id

        bi_tool = e.get("bi_tool")
        access_path = e.get("access_path", "bi_semantic_layer")
        if not declared:
            principal = undeclared_cfg[name]["principal"]
        else:
            principal = e.get("principal") or BI_SERVICE_PRINCIPAL.get(bi_tool)

        rows.append(dict(
            node_id=node_id, node_name=name, display_name=e["label"], resource_type="exposure", layer="exposure",
            platform=platform, dbt_project=project if declared else None,
            database_name=None, schema_name=None, materialization=None,
            domain=e["domain"], owner_name=owner, owner_team=team_of.get(owner),
            tags="|".join(["exposure", e["type"], e["domain"].lower()]),
            has_description=bool(rng.random() < (0.3 if is_sprawl else 0.9)) if declared else False,
            created_date=created_on,
            exposure_type=e["type"], bi_tool=bi_tool,
            exposure_url=exposure_url(name, e, spec["email_domain"]) if declared else None,
            maturity=e["maturity"], access_path=access_path, build_method=e["build"],
            is_declared=declared, service_principal=principal,
            consumption_type=CONSUMPTION_TYPE[e["type"]],
            base_daily_events=e.get("events"), base_daily_consumers=e.get("consumers"),
        ))
        for p in e["parents"]:
            src = "query_history" if not declared else ("bi_metadata" if access_path == "bi_semantic_layer" else "manifest")
            link(p, node_id, src)

    # ------------------------------------------------------------- assemble
    nodes = pd.DataFrame(rows)
    nodes["layer_order"] = nodes["layer"].map(LAYER_ORDER)
    nodes["is_declared"] = nodes["is_declared"].fillna(True).astype(bool)
    for col in ("created_date", "migration_date"):
        nodes[col] = pd.to_datetime(nodes[col])

    edges = pd.DataFrame(edge_rows, columns=["parent_node_id", "child_node_id", "edge_source"])
    edges = edges.drop_duplicates(["parent_node_id", "child_node_id"]).reset_index(drop=True)
    edges.insert(0, "edge_id", [f"E{i:04d}" for i in range(1, len(edges) + 1)])
    plat = dict(zip(nodes["node_id"], nodes["platform"]))
    edges["crosses_platform"] = [plat[p] != plat[c] for p, c in zip(edges["parent_node_id"], edges["child_node_id"])]

    w.edges = edges
    for p, c in zip(edges["parent_node_id"], edges["child_node_id"]):
        w.parents.setdefault(c, []).append(p)
        w.children.setdefault(p, []).append(c)

    # ------------------------------------------------------------------ tests
    w.tests = build_tests(w, nodes, spec, cfg, rng)
    test_counts = w.tests.groupby("node_id").size()
    nodes["test_count"] = nodes["node_id"].map(test_counts).fillna(0).astype(int)

    column_order = [
        "node_id", "node_name", "display_name", "resource_type", "layer", "layer_order",
        "platform", "dbt_project", "dbt_job", "database_name", "schema_name", "materialization",
        "domain", "owner_name", "owner_team", "tags", "has_description", "test_count", "created_date",
        "migrated_from_platform", "migration_date",
        "load_every_minutes", "warn_after_minutes", "error_after_minutes",
        "semantic_object_type", "connection_type", "refreshes_per_day", "close_window_refreshes_per_day",
        "exposure_type", "bi_tool", "exposure_url", "maturity", "access_path", "build_method",
        "is_declared", "service_principal", "consumption_type", "base_daily_events", "base_daily_consumers",
    ]
    w.nodes = nodes[column_order]
    return w


def exposure_url(name: str, e: dict, domain: str) -> str:
    tool = e.get("bi_tool")
    label = e["label"].replace(" ", "").replace("&", "And").replace("(", "").replace(")", "")
    if tool == "tableau":
        return f"https://tableau.{domain}/#/views/{label}/Overview"
    if tool == "sigma":
        return f"https://sigma.{domain}/workbook/{name}"
    if tool == "power_bi":
        return f"https://powerbi.{domain}/reports/{name}"
    return f"https://apps.{domain}/{name}"


def build_tests(w: World, nodes: pd.DataFrame, spec: dict, cfg: dict, rng: np.random.Generator) -> pd.DataFrame:
    """Give each model a realistic set of dbt tests, more or fewer depending on team hygiene."""
    s2 = cfg["stories"]["s02_monday_test_failure"]
    out = []
    extra_pool = [
        ("accepted_values", "status"),
        ("relationships", "customer_id"),
        ("relationships", "product_id"),
        ("not_null", "created_at"),
        ("not_null", "updated_at"),
        ("custom", "amount"),
    ]
    for r in nodes[nodes["resource_type"] == "model"].itertuples():
        hygiene = spec["teams"][r.owner_team]["hygiene"]["tests"]
        must_have = r.node_name == s2["model"]
        if not must_have and rng.random() >= hygiene:
            continue
        pk = primary_key(r.node_name)
        if r.layer == "staging":
            n = 2
        elif r.layer == "intermediate":
            n = int(rng.integers(1, 3))
        else:
            n = int(rng.integers(2, 6))
        chosen = [("unique", pk), ("not_null", pk)][:n]
        picks = rng.choice(len(extra_pool), size=max(0, n - 2), replace=False) if n > 2 else []
        chosen += [extra_pool[i] for i in picks]
        for test_type, col in chosen:
            if test_type == "custom":
                tname = f"assert_{r.node_name}_{col}_non_negative"
            else:
                tname = f"{test_type}_{r.node_name}_{col}"
            out.append(dict(
                test_id=f"test.{r.dbt_project}.{tname}", test_name=tname, test_type=test_type,
                node_id=r.node_id, column_name=col,
                severity="warn" if (test_type in ("accepted_values", "custom") and rng.random() < 0.4) else "error",
            ))
    tests = pd.DataFrame(out).drop_duplicates("test_id").reset_index(drop=True)
    assert (tests["test_name"] == s2["test"]).any(), "story 2 test missing"
    return tests
