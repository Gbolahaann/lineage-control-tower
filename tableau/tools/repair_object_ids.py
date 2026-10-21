"""Repair metadata-record object-ids in the master workbook.

Each <metadata-record class='column'> names its table twice: <parent-name> (the relation, e.g. [mart_job_runs.csv])
and <object-id> (the logical table, e.g. [mart_job_runs.csv_4E7C...]). After Exposure Tiles was added, the object-ids
from Job Runs onward were shifted by one table, so Tableau looked for fields in the wrong table and failed with
"Logical Query missing field [node_id (mart_test_daily.csv)] from relationOp [mart_exposure_tiles.geojson]".

This sets every record's object-id to the logical table of its own parent relation. Edits are text-only, so every
other byte stays as Tableau wrote it (CRLF kept).

    python tableau/tools/repair_object_ids.py tableau/Lineage_Control_Tower_Project_Dashboard.twb
"""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def object_ids(t: str) -> dict[str, str]:
    """Relation name -> logical table object id. The id itself names its relation: 'mart_job_runs.csv_4E7C...'."""
    return {oid.rsplit('_', 1)[0]: oid for oid in re.findall(r"<object caption='[^']*' id='([^']+)'>", t)}


def graph_mismatches(t: str) -> list[tuple[str, str]]:
    """Objects whose <relation> is not the table their id names."""
    return [(oid, rel) for oid, rel in re.findall(
        r"<object caption='[^']*' id='([^']+)'>\s*<properties[^>]*>\s*<relation [^>]*name='([^']+)'", t)
        if oid.rsplit('_', 1)[0] != rel]


def repair_graph(t: str) -> str:
    """Give every logical table back its own relation block (the <properties> under <object>)."""
    pat = re.compile(r"(<object caption='[^']*' id='([^']+)'>\n)(\s*<properties.*?</properties>\n)", re.S)
    blocks = {re.search(r"<relation [^>]*name='([^']+)'", m.group(3)).group(1): m.group(3) for m in pat.finditer(t)}
    return pat.sub(lambda m: m.group(1) + blocks[m.group(2).rsplit('_', 1)[0]], t)


def mismatches(t: str) -> list[tuple[str, str, str]]:
    ids = object_ids(t)
    bad = []
    for m in re.finditer(r"<metadata-record class='column'>(.*?)</metadata-record>", t, re.S):
        body = m.group(1)
        parent = re.search(r'<parent-name>\[(.*?)\]</parent-name>', body)
        oid = re.search(r'<object-id>\[(.*?)\]</object-id>', body)
        if parent and oid and parent.group(1) in ids and oid.group(1) != ids[parent.group(1)]:
            bad.append((re.search(r'<local-name>(.*?)</local-name>', body).group(1), parent.group(1), oid.group(1)))
    return bad


def repair(t: str) -> tuple[str, int]:
    ids = object_ids(t)
    fixed = 0

    def fix(m):
        nonlocal fixed
        body = m.group(0)
        parent = re.search(r'<parent-name>\[(.*?)\]</parent-name>', body)
        if not parent or parent.group(1) not in ids:
            return body
        want = f'<object-id>[{ids[parent.group(1)]}]</object-id>'
        new = re.sub(r'<object-id>\[[^\]]*\]</object-id>', want, body)
        fixed += new != body
        return new
    return re.sub(r"<metadata-record class='column'>.*?</metadata-record>", fix, t, flags=re.S), fixed


def main(path: str) -> None:
    p = Path(path)
    raw = p.read_bytes().decode('utf-8')
    crlf = '\r\n' in raw
    t = raw.replace('\r\n', '\n')
    print(f'{len(graph_mismatches(t))} tables hold another table\'s file; {len(mismatches(t))} field records point at the wrong table')
    t = repair_graph(t)
    assert not graph_mismatches(t), 'object graph still mismatched'
    t, n = repair(t)
    assert not mismatches(t), 'records still mismatched after repair'
    ET.fromstring(t.encode('utf-8'))
    if crlf:
        t = t.replace('\n', '\r\n')
    p.write_bytes(t.encode('utf-8'))
    print(f'repaired {n} records in {p}')


if __name__ == '__main__':
    main(sys.argv[1])
