"""Build the Lineage Control Tower dashboards into the workbook.

Reads the master .twb (the data source as you saved it in Tableau), adds parameters, calcs, sheets,
actions and the 11 dashboards, and writes a new .twb plus a .twbx with the images inside.

    python tableau/tools/build_workbook.py                     # build into tableau/build/
    python tableau/tools/build_workbook.py --tag v02-health    # also keep a copy in tableau/versions/

The master file is never edited. Everything is written as text next to what Tableau wrote,
so the data source stays byte for byte as you saved it.

Sources of truth:
- calcs:   docs/tableau-calc-pack.md (parsed, comment headers kept), plus the new calcs in each tab module
- layout:  docs/tableau-build-plan.md sections 2 and 3
- format:  docs/tableau-build-plan.md section 4
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lct_build import core, health, shell  # noqa: E402
from lct_build.core import (CALCS, DS, H, PARAM_ID, R, W, Z, blank, datasource_style, esc, parameters_datasource,  # noqa: E402
                            stable_guid, stable_uuid)

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / 'tableau' / 'Lineage_Control_Tower_Project_Dashboard.twb'
OUT = ROOT / 'tableau' / 'build' / 'Lineage_Control_Tower.twb'
VERSIONS = ROOT / 'tableau' / 'versions'

CONTENT = {'HO': health.content}          # tab prefix -> content tree builder (others get the placeholder)
TAB_ACTIONS = {'HO': health.ACTIONS}


def dashboard(tab, window_ids):
    p, name = tab[0], tab[1]
    body = CONTENT[p]() if p in CONTENT else shell.content_placeholder(tab)
    main = Z('vert', friendly=f'{p} Main', kids=[shell.header(tab), blank(1, core.LINE), shell.filter_band(tab),
                                                 blank(1, core.LINE), body])
    root = Z('basic', kids=[Z('horz', friendly=f'{p} Root', kids=[shell.nav(p, name), blank(1, core.LINE), main])])
    root.layout(0, 0, W, H)
    panel = shell.info_panel(tab)
    panel.layout(1172, 130, 400, 420)
    zones = list(root.walk()) + list(panel.walk())
    xml = (f"    <dashboard enable-sort-zone-taborder='true' name='{esc(name)}'>\n"
           "      <style>\n        <style-rule element='table'>\n"
           f"          <format attr='background-color' value='{core.CANVAS}' />\n        </style-rule>\n      </style>\n"
           f"      <size maxheight='{H}' maxwidth='{W}' minheight='{H}' minwidth='{W}' sizing-mode='fixed' />\n"
           + param_ctrl_deps(zones)
           + "      <zones>\n" + root.xml('        ', window_ids) + panel.xml('        ', window_ids) + "      </zones>\n"
           f"      <simple-id uuid='{stable_uuid('db:' + name)}' />\n    </dashboard>\n")
    sheets = sorted({z.name for z in zones if z.kind == 'sheet'})
    dzv = [(z.id, z.dzv[0]) for z in zones if z.dzv]
    return xml, sheets, dzv


def param_ctrl_deps(zones) -> str:
    params = sorted({z.param for z in zones if z.kind == 'paramctrl'})
    if not params:
        return ''
    return ("      <datasources>\n        <datasource name='Parameters' />\n      </datasources>\n"
            "      <datasource-dependencies datasource='Parameters'>\n"
            + '\n'.join(core.param_column(core.PARAM_BY[p], '        ') for p in params)
            + "\n      </datasource-dependencies>\n")


def actions(dash_sheets) -> str:
    out = []

    def param_action(dname, ws, src, param, caption):
        out.append(
            f"    <edit-parameter-action caption='{esc(caption)}' name='[Action1_{hashlib.md5(caption.encode()).hexdigest().upper()}]'>\n"
            "      <activation type='on-select' />\n"
            f"      <source dashboard='{esc(dname)}' type='sheet' worksheet='{esc(ws)}' />\n"
            "      <agg-type type='attr' />\n      <clear-option type='do-nothing' value='s:LROOT:' />\n"
            f"      <params>\n        <param name='source-field' value='{src.ref}' />\n"
            f"        <param name='target-parameter' value='[Parameters].{PARAM_ID[param]}' />\n      </params>\n"
            "    </edit-parameter-action>\n")

    for tab in shell.TABS:
        dname = tab[1]
        for ws, field, param, cap in shell.SHELL_ACTIONS:
            if ws in dash_sheets[dname]:
                param_action(dname, ws, R(field), param, f'{cap} ({dname})')
        for ws, src, param, cap in TAB_ACTIONS.get(tab[0], []):
            param_action(dname, ws, src(), param, cap)
    return '  <actions>\n' + ''.join(out) + '  </actions>\n'


WORKSHEET_CARDS = """      <cards>
        <edge name='left'>
          <strip size='160'>
            <card type='pages' />
            <card type='filters' />
            <card type='marks' />
          </strip>
        </edge>
        <edge name='top'>
          <strip size='2147483647'>
            <card type='columns' />
          </strip>
          <strip size='2147483647'>
            <card type='rows' />
          </strip>
          <strip size='31'>
            <card type='title' />
          </strip>
        </edge>
      </cards>
"""


def windows(dash_sheets, window_ids, sheet_objs) -> str:
    zoom = {s.name: s.zoom for s in sheet_objs}
    out = ["  <windows source-height='30'>\n"]
    for i, (dname, sheets) in enumerate(dash_sheets.items()):
        vps = ''.join(f"        <viewpoint name='{esc(s)}'>\n          <zoom type='{zoom.get(s, 'entire-view')}' />\n"
                      "        </viewpoint>\n" for s in sheets)
        out.append(f"    <window class='dashboard'{' maximized=' + chr(39) + 'true' + chr(39) if i == 0 else ''} name='{esc(dname)}'>\n"
                   f"      <viewpoints>\n{vps}      </viewpoints>\n      <active id='-1' />\n"
                   f"      <simple-id uuid='{window_ids[dname]}' />\n    </window>\n")
    for s in sheet_objs:
        out.append(f"    <window class='worksheet' hidden='true' name='{esc(s.name)}'>\n" + WORKSHEET_CARDS
                   + f"      <simple-id uuid='{stable_uuid('win:' + s.name)}' />\n    </window>\n")
    out.append('  </windows>\n')
    return ''.join(out)


def datagraph(dzv_by_dash) -> str:
    nodes, edges, pairs, field_nodes = [], [], [], {}
    sub = stable_guid('subgraph')
    for dname, items in dzv_by_dash.items():
        for zid, calc in items:
            if calc not in field_nodes:
                ng, ig, og = (stable_guid(f'f:{calc}:{k}') for k in 'nio')
                field_nodes[calc] = og
                nodes.append(f"        <single-value-field-node fieldname='[{DS}].[{CALCS.cid(calc)}]' "
                             f"fieldname-input-guid='{ig}' node-guid='{ng}' value-output-guid='{og}' />")
                pairs.append(ng)
            ng, vg = stable_guid(f'z:{dname}:{zid}:n'), stable_guid(f'z:{dname}:{zid}:v')
            nodes.append(f"        <dashboard-zone-visibility-node dashboard-identifier='{stable_uuid('db:' + dname)}' "
                         f"node-guid='{ng}' visibility-input-guid='{vg}' zone-id='{zid}' />")
            pairs.append(ng)
            edges.append(f"        <edge from='{field_nodes[calc]}' to='{vg}' />")
    return ("  <datagraph>\n    <graph>\n      <properties>\n"
            f"        <default-execution-subgraph-guid value='{sub}' />\n      </properties>\n"
            "      <node-execution-subgraphs>\n"
            + ''.join(f"        <pair execution-subgraph-guid='{sub}' node-guid='{n}' />\n" for n in pairs)
            + "      </node-execution-subgraphs>\n      <nodes>\n" + '\n'.join(nodes) + "\n      </nodes>\n"
            "      <edges>\n" + '\n'.join(edges) + "\n      </edges>\n      <pin-values />\n    </graph>\n  </datagraph>\n")


MANIFEST_FLAGS = ['AccessibleZoneTabOrder', 'BasicButtonObject', 'BasicButtonObjectTextSupport', 'DatagraphCoreV1',
                  'DatagraphNodeDashboardZoneVisibilityV1', 'DatagraphNodeSingleValueFieldV1', 'ParameterAction',
                  'ParameterActionClearSelection', 'WorksheetBackgroundTransparency', 'ZoneBackgroundTransparency',
                  'ZoneFriendlyName', 'ZoneVisibilityControl']


def build(master: Path, out: Path) -> Path:
    raw = master.read_bytes().decode('utf-8')
    crlf = '\r\n' in raw
    t = raw.replace('\r\n', '\n')
    assert "name='Parameters'" not in t, 'master already has parameters: build from the Tableau-saved master'
    core.load_bases(t)

    flags = ''.join(f'    <{f} />\n' for f in MANIFEST_FLAGS if f'<{f} />' not in t)
    flags += '    <_.fcp.DashboardRoundedCorners.true...DashboardRoundedCorners />\n'
    t = t.replace('  </document-format-change-manifest>', flags + '  </document-format-change-manifest>', 1)
    t = t.replace('  <datasources>\n', '  <datasources>\n' + parameters_datasource(), 1)

    sheet_objs = shell.gl_sheets() + health.sheets()
    names = [r.name for s in sheet_objs for r in s.all_refs() if r.is_calc] + ['Show Info Panel', 'Info Toggle Value']
    order, _p, _f = CALCS.closure(list(dict.fromkeys(names)))
    calc_xml = '\n'.join(CALCS.column(n) for n in order) + '\n'
    anchor = "      <layout dim-ordering='alphabetic'"
    assert t.count(anchor) == 1
    t = t.replace(anchor, calc_xml + anchor, 1)
    t = re.sub(r"(      <layout dim-ordering='alphabetic'[^>]*/>\n)", lambda m: m.group(1) + datasource_style(), t, count=1)

    window_ids = {tab[1]: stable_uuid('win:' + tab[1]) for tab in shell.TABS}
    dash_xml, dash_sheets, dzv = [], {}, {}
    for tab in shell.TABS:
        x, s, d = dashboard(tab, window_ids)
        dash_xml.append(x)
        dash_sheets[tab[1]] = s
        dzv[tab[1]] = d
    unused = {s.name for s in sheet_objs} - {n for v in dash_sheets.values() for n in v}
    assert not unused, f'sheets not placed on any dashboard: {unused}'

    ws_xml = ''.join(s.xml() for s in sheet_objs)
    t = re.sub(r'  <worksheets>.*?  </worksheets>\n',
               lambda m: actions(dash_sheets) + '  <worksheets>\n' + ws_xml + '  </worksheets>\n'
               + '  <dashboards>\n' + ''.join(dash_xml) + '  </dashboards>\n', t, count=1, flags=re.S)
    t = re.sub(r'  <windows source-height=.*?  </windows>\n',
               lambda m: windows(dash_sheets, window_ids, sheet_objs), t, count=1, flags=re.S)
    t = re.sub(r'  <thumbnails>.*?  </thumbnails>\n', '', t, count=1, flags=re.S)
    t = t.replace('</workbook>', datagraph(dzv) + '</workbook>')

    check(t)
    if crlf:
        t = t.replace('\n', '\r\n')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(t.encode('utf-8'))
    twbx = out.with_suffix('.twbx')
    with zipfile.ZipFile(twbx, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(out, out.name)
        for img in sorted(core.IMAGES.glob('*.png')):
            z.write(img, f'Image/{img.name}')
    print(f'wrote {out.relative_to(ROOT)} and {twbx.relative_to(ROOT)}: {len(sheet_objs)} sheets, '
          f'{len(order)} calcs, {len(shell.TABS)} dashboards')
    return twbx


def check(t: str) -> None:
    """Cross-reference checks before anything is written."""
    root = ET.fromstring(t.encode('utf-8'))
    ws = {w.get('name'): w for w in root.iter('worksheet')}
    dbs = root.findall('./dashboards/dashboard')
    win = {w.find('simple-id').get('uuid') for w in root.findall('./windows/window')}
    for db in dbs:
        ids = [z.get('id') for z in db.iter('zone')]
        assert len(ids) == len(set(ids)), f"{db.get('name')}: duplicate zone ids"
        for z in db.iter('zone'):
            if z.get('name') and not z.get('type-v2'):
                assert z.get('name') in ws, f"unknown sheet {z.get('name')}"
        for b in db.iter('button'):
            wid = re.search(r'window-id="([^"]+)"', b.get('action')).group(1)
            assert wid in win, f'nav button to unknown window {wid}'
    names = {d.get('name') for d in dbs}
    for a in root.iter('edit-parameter-action'):
        src = a.find('source')
        assert src.get('dashboard') in names and src.get('worksheet') in ws, a.get('caption')
        field = a.find("./params/param[@name='source-field']").get('value')
        inst = field.split('].', 1)[1]
        sheet_xml = ET.tostring(ws[src.get('worksheet')], encoding='unicode')
        assert f"name='{inst}'" in sheet_xml or f'name="{inst}"' in sheet_xml, f"{a.get('caption')}: {inst} not on the sheet"
    zone_ids = {(d.find('simple-id').get('uuid'), z.get('id')) for d in dbs for z in d.iter('zone')}
    for n in root.iter('dashboard-zone-visibility-node'):
        assert (n.get('dashboard-identifier'), n.get('zone-id')) in zone_ids, 'DZV node points at no zone'
    known = set(re.findall(r"name='(\[[^']+\])'", t))
    for f in re.findall(r"formula='([^']*)'", t):
        body = '\n'.join(l for l in f.replace('&#13;&#10;', '\n').splitlines() if not l.lstrip().startswith('//'))
        for ref in re.findall(r'\[Calculation_\d+\]', body):
            assert ref in known, f'unresolved {ref}'
    for w in ws.values():  # every field a sheet shows is declared on that sheet
        sx = ET.tostring(w, encoding='unicode')
        declared = set(re.findall(r'column-instance [^>]*name="(\[[^"]+\])"', sx))
        used = set(re.findall(r'\[' + re.escape(DS) + r'\]\.(\[[a-z]+:[^\]]+:[onq]k\])', sx))
        assert used <= declared, f"{w.get('name')}: undeclared {used - declared}"


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--master', type=Path, default=MASTER)
    ap.add_argument('--out', type=Path, default=OUT)
    ap.add_argument('--tag', help='also copy the .twbx to tableau/versions/<tag>.twbx')
    args = ap.parse_args()
    twbx = build(args.master, args.out)
    if args.tag:
        VERSIONS.mkdir(parents=True, exist_ok=True)
        dest = VERSIONS / f'{args.tag}.twbx'
        shutil.copyfile(twbx, dest)
        print(f'kept {dest.relative_to(ROOT)}')
