"""Phase 4 prep, steps 1 to 5: tidy the Lineage Control Tower data source inside the .twb.

Edits the workbook as text, not by re-serialising the XML, so everything Tableau wrote
(quoting, comments, fingerprints, ordering) stays byte for byte except the lines changed here.
Every edit asserts it matched the expected number of times, so a surprise fails loudly.

    python tableau/tools/prep_datasource.py tableau/Lineage_Control_Tower_Project_Dashboard.twb

What it does:
1. Adds the five dim_nodes columns added to the marts after the source was connected.
2. Retypes seven number columns that Tableau read as text, and turns integer keys,
   hop counts and layer positions into dimensions.
3. Renames the logical tables to plain names (and the field captions that carry them),
   and hides fields the build never uses.
4. Embeds the colour palettes from the hand-off.
(Workbook font is set separately once chosen.)
"""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

DIM_NODES_OBJ = "[dim_nodes.csv_273AA73B14884E2FB287033E49518972]"

NEW_DIM_NODES_COLS = [
    # name, datatype, remote-type, aggregation, caption, role, type
    ("open_incident_started_at", "datetime", 135, "Year", "Open Incident Started At", "dimension", "ordinal"),
    ("downstream_keys", "string", 129, "Count", "Downstream Keys", "dimension", "nominal"),
    ("downstream_consumers_7d", "real", 5, "Sum", "Downstream Consumers 7D", "measure", "quantitative"),
    ("downstream_consumers_30d", "real", 5, "Sum", "Downstream Consumers 30D", "measure", "quantitative"),
    ("downstream_consumers_90d", "real", 5, "Sum", "Downstream Consumers 90D", "measure", "quantitative"),
]

TEXT_TO_REAL = {  # remote column -> table it lives in
    "avg_runtime_sec": "mart_node_daily.csv",
    "runtime_7d_avg_sec": "mart_node_daily.csv",
    "runtime_prior28d_avg_sec": "mart_node_daily.csv",
    "runtime_trend_pct": "mart_node_daily.csv",
    "avg_refresh_sec": "mart_node_daily.csv",
    "metrics_called": "mart_exposure_daily.csv",
    "failed_calls": "mart_exposure_daily.csv",
}

MAKE_DIMENSION = ["[point_order]", "[hops]", "[hops (mart_node_reach.csv)]", "[day_index]",
                  "[days_before_as_of]", "[layer_column]", "[layer_order]", "[related_layer_column]"]

TABLE_NAMES = {
    "dim_date.csv": "Dates", "dim_nodes.csv": "Nodes", "dim_owners.csv": "Owners",
    "fct_incidents.csv": "Incidents", "mart_blast_radius.csv": "Blast Radius",
    "mart_exposure_daily.csv": "Exposure Daily", "mart_job_runs.csv": "Job Runs",
    "mart_lineage_layout.csv": "Lineage Layout", "mart_node_daily.csv": "Node Daily",
    "mart_node_reach.csv": "Node Reach", "mart_observed_access.csv": "Observed Access",
    "mart_recovery_episodes.csv": "Recovery Episodes", "mart_run_errors.csv": "Run Errors",
    "mart_test_daily.csv": "Test Daily",
}

HIDE = ["[edge_key]", "[x_label]", "[tags]", "[database_name]"]

PALETTES = [
    ("LCT Status", "regular", ["#2F9E6B", "#E8A33D", "#D2453F", "#A3ADB8"]),
    ("LCT Status Tints", "regular", ["#FFFFFF", "#FDF3E1", "#FBEAE9", "#F1F2F4", "#F7F8F6"]),
    ("LCT Platforms", "regular", ["#005FAE", "#4BAEE3", "#5B5FC7"]),
    ("LCT Brand", "regular", ["#002C55", "#005FAE", "#83C7EB", "#C7FFA4", "#F5F5F3",
                              "#16212E", "#4A5563", "#7A838E", "#A5ACB4"]),
    ("LCT Charts", "regular", ["#005FAE", "#D9DCD7", "#E8A33D", "#D2453F", "#C3C9CF",
                               "#9DB9D6", "#E9F1F9", "#CBD0D5", "#B9C0C7"]),
    ("LCT Coverage", "ordered-sequential", ["#FBEAE9", "#FDF3E1", "#EAF6EF"]),
]


def sub_exact(text: str, old: str, new: str, count: int, what: str) -> str:
    n = text.count(old)
    if n != count:
        raise SystemExit(f"{what}: expected {count} match(es), found {n}")
    return text.replace(old, new)


def main(path: str) -> None:
    p = Path(path)
    raw = p.read_bytes().decode("utf-8")
    crlf = "\r\n" in raw
    # Tableau writes CRLF line endings: edit with plain newlines, write the original endings back
    t = raw.replace("\r\n", "\n")

    # ---------------------------------------------------------------- 1. new dim_nodes columns
    if "open_incident_started_at" in t:
        raise SystemExit("New columns already present: this script has been run on this file")
    anchor = "<column datatype='real' name='avg_daily_consumers_90d' ordinal='68' />"
    indent = "\n              "
    rel_cols = "".join(f"{indent}<column datatype='{dt}' name='{n}' ordinal='{69 + i}' />"
                       for i, (n, dt, *_r) in enumerate(NEW_DIM_NODES_COLS))
    t = sub_exact(t, anchor, anchor + rel_cols, 2, "dim_nodes relation columns")

    anchor = "<map key='[avg_daily_consumers_90d]' value='[dim_nodes.csv].[avg_daily_consumers_90d]' />"
    maps = "".join(f"\n          <map key='[{n}]' value='[dim_nodes.csv].[{n}]' />" for n, *_r in NEW_DIM_NODES_COLS)
    t = sub_exact(t, anchor, anchor + maps, 1, "column map")

    max_ord = max(int(x) for x in re.findall(r"<ordinal>(\d+)</ordinal>", t))
    recs = []
    for i, (n, dt, rt, agg, *_r) in enumerate(NEW_DIM_NODES_COLS):
        extra = ("\n            <scale>1</scale>\n            <width>1073741823</width>" if dt == "string" else "")
        coll = ("\n            <collation flag='0' name='LEN_RUS' />" if dt == "string" else "")
        recs.append(
            f"\n          <metadata-record class='column'>"
            f"\n            <remote-name>{n}</remote-name>"
            f"\n            <remote-type>{rt}</remote-type>"
            f"\n            <local-name>[{n}]</local-name>"
            f"\n            <parent-name>[dim_nodes.csv]</parent-name>"
            f"\n            <remote-alias>{n}</remote-alias>"
            f"\n            <ordinal>{max_ord + 1 + i}</ordinal>"
            f"\n            <local-type>{dt}</local-type>"
            f"\n            <aggregation>{agg}</aggregation>{extra}"
            f"\n            <contains-null>true</contains-null>{coll}"
            f"\n            <object-id>{DIM_NODES_OBJ}</object-id>"
            f"\n          </metadata-record>")
    m = re.search(r"<metadata-record class='column'>\s*<remote-name>avg_daily_consumers_90d</remote-name>"
                  r"(?:(?!</metadata-record>).)*?<parent-name>\[dim_nodes\.csv\]</parent-name>.*?</metadata-record>", t, re.S)
    assert m, "dim_nodes avg_daily_consumers_90d metadata record not found"
    t = t[:m.end()] + "".join(recs) + t[m.end():]

    fields = "".join(f"\n      <column caption='{cap}' datatype='{dt}' name='[{n}]' role='{role}' type='{typ}' />"
                     for n, dt, _rt, _agg, cap, role, typ in NEW_DIM_NODES_COLS)
    t = sub_exact(t, "\n      <layout ", fields + "\n      <layout ", 1, "field definitions")

    # ---------------------------------------------------------------- 2. types and roles
    for col, table in TEXT_TO_REAL.items():
        old = f"<column datatype='string' name='{col}' ordinal="
        n = t.count(old)
        if n != 2:
            raise SystemExit(f"{col}: expected 2 relation entries, found {n}")
        t = t.replace(old, f"<column datatype='real' name='{col}' ordinal=")
        # Rebuild the metadata record as a number column
        pat = re.compile(r"(<metadata-record class='column'>\s*<remote-name>" + col + r"</remote-name>)(.*?)(</metadata-record>)", re.S)
        mm = [x for x in pat.finditer(t) if f"<parent-name>[{table}]</parent-name>" in x.group(2)]
        assert len(mm) == 1, f"{col}: metadata record not found once"
        body = mm[0].group(2)
        body = body.replace("<remote-type>129</remote-type>", "<remote-type>5</remote-type>")
        body = body.replace("<local-type>string</local-type>", "<local-type>real</local-type>")
        body = body.replace("<aggregation>Count</aggregation>", "<aggregation>Sum</aggregation>")
        body = re.sub(r"\s*<approx-count>\d+</approx-count>", "", body)
        body = re.sub(r"\s*<scale>\d+</scale>", "", body)
        body = re.sub(r"\s*<width>\d+</width>", "", body)
        body = re.sub(r"\s*<collation [^>]*/>", "", body)
        t = t[:mm[0].start(2)] + body + t[mm[0].end(2):]
        # Field definition: number, measure, continuous
        t = re.sub(r"(<column caption='[^']*' )datatype='string'( name='\[" + col + r"\]' )role='dimension' type='nominal'",
                   r"\1datatype='real'\2role='measure' type='quantitative'", t)
        assert f"datatype='real' name='[{col}]' role='measure' type='quantitative'" in t, f"{col}: field definition not updated"

    for name in MAKE_DIMENSION:
        pat = re.compile(r"(<column caption='[^']*' datatype='(?:integer|real)' name='" + re.escape(name) +
                         r"' )role='(?:measure|dimension)' type='(?:quantitative|ordinal)'")
        t, n = pat.subn(r"\1role='dimension' type='ordinal'", t)
        assert n == 1, f"{name}: expected one field definition, found {n}"

    # ---------------------------------------------------------------- 3. names and hidden fields
    for raw, nice in TABLE_NAMES.items():
        # logical table captions (object graph and table pseudo-fields)
        t = t.replace(f"<object caption='{raw}' ", f"<object caption='{nice}' ")
        t = t.replace(f"<column caption='{raw}' datatype='table' ", f"<column caption='{nice}' datatype='table' ")
        # field captions that carry the table name, e.g. "Node Id (Mart Blast Radius.Csv)"
        stem = raw[:-4].replace("_", " ").title() + ".Csv"
        t = t.replace(f" ({stem})'", f" ({nice})'")
    t = sub_exact(t, "caption='mart_node_daily+'", "caption='Lineage Control Tower'", 1, "data source caption")
    for name in HIDE:
        pat = re.compile(r"(<column caption='[^']*' datatype='[a-z]+' )(name='" + re.escape(name) + r"' )")
        t, n = pat.subn(r"\1hidden='true' \2", t)
        assert n == 1, f"{name}: expected one field definition to hide, found {n}"

    # ---------------------------------------------------------------- 4. palettes
    pal = "".join(
        f"\n    <color-palette name='{name}' type='{kind}'>" + "".join(f"\n      <color>{c}</color>" for c in cols)
        + "\n    </color-palette>" for name, kind, cols in PALETTES)
    t = sub_exact(t, "    <preference name='ui.shelf.height' value='26' />\n  </preferences>",
                  "    <preference name='ui.shelf.height' value='26' />" + pal + "\n  </preferences>", 1, "palettes")

    ET.fromstring(t.encode("utf-8"))  # must still parse
    if crlf:
        t = t.replace("\n", "\r\n")
    p.write_bytes(t.encode("utf-8"))
    print(f"updated {p}")


if __name__ == "__main__":
    main(sys.argv[1])
