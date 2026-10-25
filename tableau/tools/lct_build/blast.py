"""Tab 7, Blast radius (BR): calc pack section 5, build plan 3.3.

GB's choices (24 Oct): both tables and the downstream path as canvases like Usage, the incident message as an email
button (Tableau cannot write to the clipboard), and every "open in Lineage for now" click from Run & failures,
Performance & cost and Usage re-routed here.

Everything on the page follows p_selected_node (the dropdown, or a click on a riskiest node or on another tab). What a
node reaches does not change with the data's window, so the build works it out per node (and per period for the
consumer counts and unregistered readers) from the marts, the prototype's rules, and writes it as CASE calcs on the
parameters. Mark labels do not wrap in Tableau, so the build also wraps or cuts the long texts.

- Header: the node's status / platform / layer pills (a canvas), the impact sentence and issue line, five count chips
  and the email button.
- Who to tell: one canvas row per exposure the node feeds, on that exposure's own Exposure Daily rows, sorted by daily
  consumers; callouts for unregistered readers and exposures with no owner (dynamic zone visibility on parameters).
- Downstream path: three columns of chips (models, BI semantic layer, exposures), up to 12 each, drawn on three
  carrier models' Node Daily rows (exposures have no Node Daily rows of their own).
- Riskiest nodes: the 10 riskiest per period and platform (failure rate x daily downstream consumers), the selected
  node's row highlighted; a click traces that node.
"""

from __future__ import annotations

import collections
import csv
import datetime as dt

from . import shapes as SH
from .core import (PANEL_WRITES, ACCENT, B_DIM, CALCS, CARD, CRIT, CRIT_INK, CRIT_TINT, GOOD, GOOD_INK, GOOD_TINT, I_DIM,
                   INK1, INK2, INK3, INK4, LAT, LINE, LINE_SOFT, LON, NAVY, NL, NONE, NONE_TINT, PLAT, R_MEA, S_DIM, SEMI,
                   SP_MEA, WARN, WARN_INK, WARN_TINT, PARAM_BY, Cross, Nest, Pane, R, Sheet, Z, blank, button_label_pane, card,
                   card_header, color_map, label_pane, run, sheet, text)
from .lineage import _fit, _grid, _lines_expr, _q, _wrap
from .shell import CONTENT_H, CONTENT_PAD
from .usage import BI_NAME, ET_NAME, W7, W8, _at, _calc, _case, _rounded

P = 'BR'
ROOT = SH.ROOT
M = ROOT / 'data' / 'marts'
NODES = {r['node_id']: r for r in csv.DictReader(open(M / 'dim_nodes.csv', encoding='utf-8'))}
PERIODS, PLATFORMS = (7, 30, 90), ('All', 'snowflake', 'databricks', 'redshift')
ASOF = dt.date(2026, 10, 19)
SEL = '[p_selected_node]'
PSEL = 'STR([p_period]) + "|" + [p_selected_node]'
NODE = '[node_id (dim_nodes.csv)]'
PLAT_NAME = {'snowflake': 'Snowflake', 'databricks': 'Databricks', 'redshift': 'Redshift'}
LAYER_NAME = {'source': 'Sources', 'staging': 'Staging', 'intermediate': 'Intermediate', 'mart': 'Marts',
              'semantic': 'BI semantic layer', 'exposure': 'Exposures'}
STATUS = {'3': 'Critical', '2': 'Warning', '1': 'Healthy', '0': 'No data'}
STATUS_ICON = {'Critical': '✕', 'Warning': '▲', 'Healthy': '✓', 'No data': '–'}
STATUS_INK = {'Critical': CRIT_INK, 'Warning': WARN_INK, 'Healthy': GOOD_INK, 'No data': INK2}
STATUS_TINT = {'Critical': CRIT_TINT, 'Warning': WARN_TINT, 'Healthy': GOOD_TINT, 'No data': NONE_TINT}

# ---------------------------------------------------------------- geometry (content 1312 x CONTENT_H)
HEAD_H, MID_H = 150, 358
HALF = (1312 - 14) // 2                          # 649
PICK_W, MSG_W = 300, 190
SUM_W = 1312 - 2 - 36 - PICK_W - 24 - MSG_W      # 760: the impact sentence
PILL_PANE = (PICK_W - SH.SLACK, 24)
WHO_W = HALF - 2 * 16 - 2 - SH.SLACK - 18        # 593: who to tell, room for its scroll bar
WHO_ROW = 31
PATH_W = HALF - 2 * 16 - 2 - SH.MAP_SLACK        # 603: downstream path
COL_W, COL_GAP, CHIP_H, CHIP_STEP, CHIPS = 195, 13, 18, 21, 12
PATH_PANE = (PATH_W, 26 + CHIPS * CHIP_STEP)     # 278
RISK_W = 1312 - 2 * 16 - 2 - SH.SLACK - 18       # 1256: riskiest nodes, room for its scroll bar
RISK_ROW = 27
TOP_RISK = 10
COLHEAD_H = 22
CARRIERS = sorted(k for k, n in NODES.items() if n['resource_type'] == 'model')[:4]   # pills, then the 3 path columns


def _num(v):
    return None if v in ('', None) else float(v)


def _in_plat(n, plat):
    return plat == 'All' or f'|{plat}|' in n['platform_filter_values']


def _status(k):
    return STATUS.get(NODES[k]['current_status_code'], 'No data')


# ================================================================ the build's view of each node

def _load():
    blast = collections.defaultdict(list)
    for r in csv.DictReader(open(M / 'mart_blast_radius.csv', encoding='utf-8')):
        blast[r['node_id']].append(r)
    reach = collections.defaultdict(list)
    for r in csv.DictReader(open(M / 'mart_node_reach.csv', encoding='utf-8')):
        if r['direction'] == 'downstream':
            reach[r['node_id']].append(r)
    access = list(csv.DictReader(open(M / 'mart_observed_access.csv', encoding='utf-8')))
    days = collections.defaultdict(dict)
    for r in csv.DictReader(open(M / 'mart_node_daily.csv', encoding='utf-8')):
        days[r['node_id']][(ASOF - dt.date.fromisoformat(r['date'])).days] = r
    return blast, reach, access, days


BLAST, REACH, ACCESS, DAYS = _load()
SELECTABLE = [k for k, _ in PARAM_BY['p_selected_node']['members'] if k]


def _unregistered(per):
    """Principals with reads in the window but none mapped to a declared exposure, per node they read."""
    mapped = {r['principal'] for r in ACCESS if (ASOF - dt.date.fromisoformat(r['date'])).days < per and r['is_registered'] == 'True'}
    reads = collections.defaultdict(set)
    for r in ACCESS:
        if (ASOF - dt.date.fromisoformat(r['date'])).days < per and r['principal'] not in mapped and float(r['query_count'] or 0) > 0:
            reads[r['node_id']].add(r['principal'])
    return reads


UNREG_READS = {per: _unregistered(per) for per in PERIODS}


def _impact(k, per):
    rows = BLAST.get(k, [])
    cons = sum(_num(r[f'avg_daily_consumers_{per}d']) or 0 for r in rows)
    owners = {r['exposure_owner'] for r in rows if r['exposure_owner'] != 'No owner'}
    no_owner = [r for r in rows if r['exposure_owner'] == 'No owner']
    down = {r['related_node_id'] for r in REACH.get(k, [])}
    unreg = sorted(set().union(*[UNREG_READS[per].get(n, set()) for n in {k} | down]))
    return dict(exp=len(rows), cons=cons, owners=len(owners), no_owner=len(no_owner), unreg=unreg,
                models=sum(1 for r in REACH.get(k, []) if r['related_resource_type'] == 'model'),
                sems=sum(1 for r in REACH.get(k, []) if r['related_resource_type'] == 'semantic'))


IMPACT = {(per, k): _impact(k, per) for per in PERIODS for k in SELECTABLE}


# ================================================================ header calcs

def header_calcs():
    f, t = {}, {}
    lead = {k: f'If {NODES[k]["node_name"]} breaks, ' for k in SELECTABLE}
    by = lambda fn: {f'{per}|{k}': fn(IMPACT[(per, k)], k) for per in PERIODS for k in SELECTABLE}
    prod = by(lambda v, k: 'no data products' if not v['exp'] else f'{v["exp"]} data product' + ('' if v['exp'] == 1 else 's'))
    cons = by(lambda v, k: f'{round(v["cons"])} daily consumers' if v['exp'] else '')
    # 12 pt in the 760 px column: break before "are affected." when the sentence would run out of room
    whole = lambda per, k: W8(lead[k]) * 1.5 + W8(prod[f'{per}|{k}'], True) * 1.5 + W8(' and about ' + cons[f'{per}|{k}'], True) * 1.5 + W8(' are affected.') * 1.5
    tail = {f'{per}|{k}': ('\n' if whole(per, k) > SUM_W - 10 else ' ') + 'are affected.' for per in PERIODS for k in SELECTABLE}
    issue = {k: _fit(NODES[k]['status_reason'] if NODES[k]['current_status_code'] in ('2', '3') and NODES[k]['status_reason']
                     else 'Currently healthy. Use this view before changing or deprecating it.', SUM_W - 10, 8) for k in SELECTABLE}
    f['BR Lead Text'] = _calc('BR Lead Text', 'First run of the impact sentence (written by the build per node).', _case(SEL, lead))
    f['BR Products Text'] = _calc('BR Products Text', 'Bold: "4 data products".', _case(PSEL, prod))
    f['BR And Text'] = _calc('BR And Text', '" and about " when the node feeds anything.', _case(PSEL, {k: ' and about ' for k, v in cons.items() if v}, '""'))
    f['BR Consumers Text'] = _calc('BR Consumers Text', 'Bold: "42 daily consumers" (the fed exposures\' average in the period).', _case(PSEL, cons, '""'))
    f['BR Tail Text'] = _calc('BR Tail Text', '"are affected.", on a new line when the sentence would not fit.',
                              _case(PSEL, {k: ('CHAR(10) + "are affected."' if v.startswith('\n') else '" are affected."') for k, v in tail.items()},
                                    quote=False))
    f['BR Issue Text'] = _calc('BR Issue Text', 'What is wrong now, or a reminder (cut to the column by the build).', _case(SEL, issue))
    chips = {'Models': ('models', 'downstream models'), 'Semantic': ('sems', 'BI semantic objects'), 'Exposures': ('exp', 'exposures'),
             'Owners': ('owners', 'owners to notify')}
    for name, (field, label) in chips.items():
        f[f'BR Chip {name} Value'] = _calc(f'BR Chip {name} Value', f'Count chip: {label}.', _case(PSEL, by(lambda v, k, fl=field: str(v[fl]))))
        f[f'BR Chip {name} Label'] = f'// BR Chip {name} Label\n// Under the count.\n"{label}"'
    f['BR Chip Unregistered Red'] = _calc('BR Chip Unregistered Red', 'Unregistered readers, red when there are any.',
                                          _case(PSEL, {k: v for k, v in by(lambda v, k: str(len(v['unreg'])) if v['unreg'] else None).items() if v}))
    f['BR Chip Unregistered Plain'] = _calc('BR Chip Unregistered Plain', '"0" in navy otherwise.',
                                            _case(PSEL, {k: v for k, v in by(lambda v, k: None if v['unreg'] else '0').items() if v}))
    f['BR Chip Unregistered Label'] = '// BR Chip Unregistered Label\n// Under the count.\n"unregistered readers"'
    # callouts (dynamic zone visibility reads parameters only)
    unreg_txt = by(lambda v, k: ', '.join(v['unreg'][:3]) + (f' and {len(v["unreg"]) - 3} more' if len(v['unreg']) > 3 else '')
                   + ' also read this data but are not registered as an exposure, so nobody would be told. See Governance.' if v['unreg'] else None)
    lines = lambda s: _lines_expr(_wrap(s, HALF - 34 - 28, 8))   # line breaks as CHAR(10): mark labels do not wrap
    f['BR Unregistered Callout Text'] = _calc('BR Unregistered Callout Text', 'Amber callout under Who to tell, wrapped by the build.',
                                              _case(PSEL, {k: lines(v) for k, v in unreg_txt.items() if v}, quote=False))
    f['Show BR Unregistered Callout'] = _calc('Show BR Unregistered Callout', 'DZV: unregistered readers reach this node or anything built on it.',
                                              _case(PSEL, {k: 'TRUE' for k, v in unreg_txt.items() if v}, 'FALSE', False))
    no_owner = {k: f'{IMPACT[(30, k)]["no_owner"]} affected exposure' + ('' if IMPACT[(30, k)]['no_owner'] == 1 else 's')
                + ' ha' + ('s' if IMPACT[(30, k)]['no_owner'] == 1 else 've') + ' no owner to notify.' for k in SELECTABLE if IMPACT[(30, k)]['no_owner']}
    f['BR No Owner Callout Text'] = _calc('BR No Owner Callout Text', 'Red callout: fed exposures nobody owns.', _case(SEL, no_owner))
    f['Show BR No Owner Callout'] = _calc('Show BR No Owner Callout', 'DZV: the node feeds an exposure with no owner.',
                                          _case(SEL, {k: 'TRUE' for k in no_owner}, 'FALSE', False))
    # incident message for the email action
    def msg(per, k):
        n, v = NODES[k], IMPACT[(per, k)]
        issue_ = (f'has an issue: {n["status_reason"][0].lower() + n["status_reason"][1:]}' if n['current_status_code'] in ('2', '3') and n['status_reason']
                  else 'is being changed')
        return (f'Heads up: {n["node_name"]} ({LAYER_NAME.get(n["layer"], n["layer"]).lower()}, {PLAT_NAME.get(n["platform_now"], n["platform_now"])}) '
                f'{issue_}. It feeds {prod[f"{per}|{k}"]} used by about {round(v["cons"])} people, apps or agents a day. '
                'Treat these numbers with caution until we confirm the fix.')
    f['BR Incident Body'] = _calc('BR Incident Body', 'Ready-to-send message for the email action (calc pack 5.2, written by the build).',
                                  _case(PSEL, {f'{per}|{k}': msg(per, k) for per in PERIODS for k in SELECTABLE}))
    f['BR Incident Subject'] = _calc('BR Incident Subject', 'Email subject.', _case(SEL, {k: f'Heads up: {NODES[k]["node_name"]}' for k in SELECTABLE}))
    f['BR Email Glyph'] = '// BR Email Glyph\n// The button\'s text, beside the envelope icon (as the prototype\'s "Copy incident message").\nMIN("Email incident message")'
    f['BR Email Anchor'] = (f'// BR Email Anchor\n// Where the envelope sits on the button\'s 0 to 1 axis, so icon and text are centred together.\n'
                            f'MIN({(MSG_W - 2 - (16 + 6 + W8("Email incident message") * 9 / 8)) / 2 / (MSG_W - 2) + 8 / (MSG_W - 2):.3f})')
    t.update({n: S_DIM for n in f})
    t.update({'Show BR Unregistered Callout': B_DIM, 'Show BR No Owner Callout': B_DIM, 'BR Email Glyph': ('string', 'measure', 'nominal'),
              'BR Email Anchor': R_MEA})
    return f, t


def pill_calcs():
    """Status, platform and layer pills for the selected node, on the first carrier's Node Daily rows."""
    pane, f = PILL_PANE, {}
    st = {k: f'{STATUS_ICON[_status(k)]} {_status(k)}' for k in SELECTABLE}
    pl = {k: PLAT_NAME.get(NODES[k]['platform_now'], '') for k in SELECTABLE}
    ly = {k: LAYER_NAME.get(NODES[k]['layer'], '') for k in SELECTABLE}
    w1 = {k: round(W7(v, True) + 14) for k, v in st.items()}
    w2 = {k: round(W7('■ ' + v) + 14) for k, v in pl.items()}
    w3 = {k: round(W7(v) + 14) for k, v in ly.items()}
    x2 = {k: w1[k] + 6 for k in SELECTABLE}
    x3 = {k: w1[k] + 6 + w2[k] + 6 for k in SELECTABLE}
    case = lambda d: _case(SEL, d, '0', False)
    pill = lambda x, w: _rounded('[Node Path Index]', x, w, 3, 21, 4, pane)
    idx = '[Node Path Index]'
    f['BR Pill Status Point'] = _calc('BR Pill Status Point', 'Status pill (status tint), rows 0 to 87 of the first carrier.', pill('0', case(w1)))
    f['BR Pill Platform Point'] = _calc('BR Pill Platform Point', 'Platform pill (outline).', pill(case(x2), case(w2)))
    f['BR Pill Layer Point'] = _calc('BR Pill Layer Point', 'Layer pill (outline).', pill(case(x3), case(w3)))
    f['BR Pill Status Text'] = _calc('BR Pill Status Text', 'Status pill text.', _case(SEL, st))
    f['BR Pill Status Key'] = _calc('BR Pill Status Key', 'Status pill tint.', _case(SEL, {k: _status(k) for k in SELECTABLE}))
    f['BR Pill Platform Text'] = _calc('BR Pill Platform Text', 'Platform name.', _case(SEL, pl))
    for pk, pn in PLAT_NAME.items():
        f[f'BR Pill Square {pn}'] = _calc(f'BR Pill Square {pn}', f'The square before the platform name, in {pn}\'s colour.',
                                          f'IF {_case(SEL, {k: NODES[k]["platform_now"] for k in SELECTABLE})} = "{pk}" THEN "■ " END')
    f['BR Pill Platform Key'] = _calc('BR Pill Platform Key', 'Platform square colour.', _case(SEL, {k: NODES[k]['platform_now'] for k in SELECTABLE}))
    f['BR Pill Layer Text'] = _calc('BR Pill Layer Text', 'Layer name.', _case(SEL, ly))
    mid = lambda x, w: f'MAKEPOINT({(pane[1] / 2 - 12) / 100:.4f}, (({x}) + ({w}) / 2 - {pane[0] / 2:g}) / 100)'
    f['BR Pill Status Text Point'] = _calc('BR Pill Status Text Point', 'Middle of the status pill.', mid('0', case(w1)))
    f['BR Pill Platform Text Point'] = _calc('BR Pill Platform Text Point', 'Middle of the platform pill.', mid(case(x2), case(w2)))
    f['BR Pill Layer Text Point'] = _calc('BR Pill Layer Text Point', 'Middle of the layer pill.', mid(case(x3), case(w3)))
    f['Is BR Pill Carrier'] = _calc('Is BR Pill Carrier', 'The scaffold model whose rows draw the pills. Put on Filters (True).', f'{NODE} = {_q(CARRIERS[0])}')
    t = {n: (SP_MEA if n.endswith('Point') else B_DIM if n.startswith('Is ') else S_DIM) for n in f}
    return f, t


# ================================================================ who to tell (Exposure Daily rows)

def _who_rows():
    rows = {}
    for k in SELECTABLE:
        for r in BLAST.get(k, []):
            rows.setdefault(r['exposure_id'], r)
    return rows


WHO = _who_rows()
TRUST = {'Critical': '✕  ', 'Warning': '▲  ', 'Healthy': '✓  '}


def _who_type(r):
    return BI_NAME.get(r['bi_tool']) or ET_NAME.get(r['exposure_type'], '')


def _who_cols():
    """Columns from the widest text of each; the name column as wide as still lets the table fit its canvas."""
    pill_w = max(W7(TRUST.get(r['exposure_status'], '') + r['exposure_trust'], True) for r in WHO.values()) + 14
    for cap in range(170, 100, -2):
        names = {e: _fit(r['exposure_name'], cap, 8, True) for e, r in WHO.items()}
        x = {'name': 8}
        x['type'] = 8 + max(W8(v, True) for v in names.values()) + 8
        x['owner'] = x['type'] + max(W8(_who_type(r)) for r in WHO.values()) + 8
        x['slack'] = x['owner'] + max(W8(r['exposure_owner']) for r in WHO.values()) + 8
        x['cons'] = x['slack'] + max(W8(r['slack_channel'] or '-') for r in WHO.values()) + 8 + W7('CONSUMERS', True)
        x['status'] = x['cons'] + 10
        if x['status'] + pill_w <= WHO_W - 2:
            return names, x
    raise AssertionError('BR who to tell does not fit')


WHO_NAMES, WCOL = _who_cols()


def who_calcs():
    pane, f = (WHO_W, WHO_ROW), {}
    pairs = {f'{k}|{r["exposure_id"]}': 'TRUE' for k in SELECTABLE for r in BLAST.get(k, [])}
    f['Is BR Who Row'] = _calc('Is BR Who Row', 'The exposures the selected node feeds (written by the build from Blast Radius). Put on Filters (True).',
                               _case(f'{SEL} + "|" + {NODE}', pairs, 'FALSE', False))
    cons = {per: {e: _num(r[f'avg_daily_consumers_{per}d']) or 0 for e, r in WHO.items()} for per in PERIODS}
    order = {f'{per}|{e}': i + 1 for per in PERIODS for i, e in enumerate(sorted(WHO, key=lambda e: -cons[per][e]))}
    f['BR Who Order'] = _calc('BR Who Order', 'Most daily consumers first (per period).', _case(f'STR([p_period]) + "|" + {NODE}', order, quote=False))
    texts = {'Name': WHO_NAMES, 'Type': {e: _who_type(r) for e, r in WHO.items()},
             'Owner': {e: r['exposure_owner'] for e, r in WHO.items() if r['exposure_owner'] != 'No owner'},
             'No Owner': {e: 'No owner' for e, r in WHO.items() if r['exposure_owner'] == 'No owner'},
             'Slack': {e: r['slack_channel'] or '-' for e, r in WHO.items()}}
    for n, d in texts.items():
        f[f'BR Who {n} Text'] = _calc(f'BR Who {n} Text', f'{n} column (written by the build).', _case(NODE, d))
    left = lambda col, d, b=False: _case(NODE, {e: f'MAKEPOINT(0, ({WCOL[col] + W8(v, b) / 2:.1f} - {pane[0] / 2:g}) / 100)' for e, v in d.items()}, quote=False)
    f['BR Who Name Point'] = _calc('BR Who Name Point', 'Exposure name, left.', left('name', WHO_NAMES, True))
    f['BR Who Type Point'] = _calc('BR Who Type Point', 'Type, left.', left('type', texts['Type']))
    f['BR Who Owner Point'] = _calc('BR Who Owner Point', 'Owner, left.', left('owner', {**texts['Owner'], **texts['No Owner']}))
    f['BR Who Slack Point'] = _calc('BR Who Slack Point', 'Slack channel, left.', left('slack', texts['Slack']))
    ctext = {f'{per}|{e}': f'{cons[per][e]:.1f}' for per in PERIODS for e in WHO}
    f['BR Who Consumers Text'] = _calc('BR Who Consumers Text', 'Average daily consumers in the period.', _case(f'STR([p_period]) + "|" + {NODE}', ctext))
    f['BR Who Consumers Point'] = _calc('BR Who Consumers Point', 'Right-aligned at its column.',
                                        _case(f'STR([p_period]) + "|" + {NODE}', {k: f'MAKEPOINT(0, ({WCOL["cons"] - W8(v) / 2:.1f} - {pane[0] / 2:g}) / 100)'
                                                                                 for k, v in ctext.items()}, quote=False))
    trust = {e: TRUST.get(r['exposure_status'], '') + r['exposure_trust'] for e, r in WHO.items()}
    for s in ('Critical', 'Warning', 'Healthy'):
        f[f'BR Who Trust {s}'] = _calc(f'BR Who Trust {s}', f'Status pill text, {s.lower()} colour.',
                                       _case(NODE, {e: v for e, v in trust.items() if WHO[e]['exposure_status'] == s}))
    f['BR Who Trust Key'] = _calc('BR Who Trust Key', 'Status pill tint.', _case(NODE, {e: r['exposure_status'] for e, r in WHO.items()}))
    pw = {e: round(W7(v, True) + 14) for e, v in trust.items()}
    f['BR Who Pill Point'] = _calc('BR Who Pill Point', 'Status pill, fully rounded.',
                                   _rounded('[Exposure Path Index]', WCOL['status'], _case(NODE, pw, '0', False), 7, 24, 8, pane))
    f['BR Who Pill Text Point'] = _calc('BR Who Pill Text Point', 'Middle of the pill.',
                                        _case(NODE, {e: f'MAKEPOINT(0, ({WCOL["status"] + w / 2:.1f} - {pane[0] / 2:g}) / 100)' for e, w in pw.items()}, quote=False))
    f['BR Who Divider Point'] = _calc('BR Who Divider Point', 'Line under each row.', _rounded('[Exposure Path Index]', 0, WHO_W, WHO_ROW - 1, WHO_ROW, 0, pane))
    f['BR Who Row Point'] = _calc('BR Who Row Point', 'The row (takes the click).', _rounded('[Exposure Path Index]', 0, WHO_W, 0, WHO_ROW - 1, 0, pane))
    heads = [('EXPOSURE', WCOL['name'], 'l'), ('TYPE', WCOL['type'], 'l'), ('OWNER', WCOL['owner'], 'l'), ('SLACK', WCOL['slack'], 'l'),
             ('CONSUMERS', WCOL['cons'], 'r'), ('STATUS', WCOL['status'], 'l')]   # "daily" is in the card subtitle (room for the names)
    f.update(_headings('BR Who', heads, WHO_W))
    t = {n: (SP_MEA if n.endswith('Point') else S_DIM) for n in f}
    t.update({'Is BR Who Row': B_DIM, 'BR Who Order': I_DIM})
    return f, t


def _headings(prefix, heads, width):
    hx = {i: (x + W7(h, True) / 2) if a == 'l' else (x - W7(h, True) / 2) for i, (h, x, a) in enumerate(heads)}
    return {f'{prefix} Heading': _calc(f'{prefix} Heading', 'Column titles, one date row each.', _case('[day_index]', {i: h for i, (h, _, _) in enumerate(heads)})),
            f'{prefix} Heading Point': _calc(f'{prefix} Heading Point', 'Middle of a column title (measured by the build).',
                                             f'MAKEPOINT(0, ({_case("[day_index]", {i: f"{v:.1f}" for i, v in hx.items()}, "0", False)} - {width / 2:g}) / 100)')}


# ================================================================ downstream path (three carrier columns)

def path_calcs():
    pane, f = PATH_PANE, {}
    cols = [('model', 'MODELS'), ('semantic', 'BI SEMANTIC LAYER'), ('exposure', 'EXPOSURES')]
    carrier = {CARRIERS[i + 1]: i for i in range(3)}
    f['BR Path Column'] = _calc('BR Path Column', 'Which path column a carrier model\'s Node Daily rows draw (a scaffold).', _case(NODE, carrier, quote=False))
    items, counts = {}, {}
    for k in SELECTABLE:
        for c, (typ, _h) in enumerate(cols):
            rs = sorted((r for r in REACH.get(k, []) if r['related_resource_type'] == typ),
                        key=lambda r: (int(float(r['related_layer_column'] or 0)), r['related_name']))
            counts[f'{k}|{c}'] = len(rs)
            for i, r in enumerate(rs[:CHIPS]):
                items[f'{k}|{c}|{i}'] = r
    ckey = f'{SEL} + "|" + STR(INT([BR Path Column]))'
    f['BR Path Count'] = _calc('BR Path Count', 'Nodes in a column for the selected node.', _case(ckey, counts, '0', False))
    i_ = 'INT([Node Path Index] / 4)'
    x0 = f'([BR Path Column] * {COL_W + COL_GAP})'
    y0 = f'(26 + {i_} * {CHIP_STEP})'
    k_ = 'INT([Node Path Index] % 4)'
    lat = f'({pane[1] / 2:g} - (CASE {k_} WHEN 0 THEN {y0} WHEN 1 THEN {y0} ELSE {y0} + {CHIP_H} END)) / 100'
    lon = f'((CASE {k_} WHEN 0 THEN {x0} WHEN 3 THEN {x0} ELSE {x0} + {COL_W} END) - {pane[0] / 2:g}) / 100'
    f['BR Chip Point'] = _calc('BR Chip Point', 'A chip: 4 Node Path Index rows each (corners), as many as the column has, up to 12.',
                               f'IF {i_} < MIN([BR Path Count], {CHIPS}) THEN MAKEPOINT(\n    {lat},\n    {lon}\n) END')
    f['BR Chip Id'] = _calc('BR Chip Id', 'Which chip a row draws.', f'IF [Node Path Index] < {CHIPS * 4} THEN {i_} END')
    ikey = f'{ckey} + "|" + STR(INT([BR Chip Id]))'
    f['BR Chip Key'] = _calc('BR Chip Key', 'Chip tint by the node\'s status now.', _case(ikey, {k: r['related_status'] for k, r in items.items()}))
    tkey = f'{ckey} + "|" + STR(INT([Node Path Index]) - {CHIPS * 4})'
    names = {k: _fit(r['related_name'], COL_W - 26, 8) for k, r in items.items()}
    f['BR Chip Name'] = _calc('BR Chip Name', 'Chip text (rows 48 to 59).', _case(tkey, {k: '  ' + v for k, v in names.items()}))
    for s in ('Critical', 'Warning', 'Healthy', 'No data'):
        f[f'BR Chip Dot {s}'] = _calc(f'BR Chip Dot {s}', f'Status dot, {s.lower()}.', _case(tkey, {k: '●' for k, r in items.items() if r['related_status'] == s}))
    dot = W8('●')
    f['BR Chip Text Point'] = _calc('BR Chip Text Point', 'Dot and name, left in the chip (centred at half their measured width).',
                                    _case(tkey, {k: f'MAKEPOINT({(pane[1] / 2 - 26 - int(k.split("|")[2]) * CHIP_STEP - CHIP_H / 2) / 100:.4f}, '
                                                    f'({int(k.split("|")[1]) * (COL_W + COL_GAP) + 8 + (dot + W8("  " + v)) / 2:.1f} - {pane[0] / 2:g}) / 100)'
                                                 for k, v in names.items()}, quote=False))
    heads = {c: h for c, (_t, h) in enumerate(cols)}
    f['BR Path Head'] = _calc('BR Path Head', 'Column title (row 60).', f'IF [Node Path Index] = 60 THEN ' + _case('[BR Path Column]', heads) + ' END')
    f['BR Path Head Point'] = _calc('BR Path Head Point', 'Left at the column.',
                                    f'IF [Node Path Index] = 60 THEN MAKEPOINT({(pane[1] / 2 - 9) / 100:.4f}, ('
                                    + _case('[BR Path Column]', {c: f'{c * (COL_W + COL_GAP) + W7(h, True) / 2:.1f}' for c, h in heads.items()}, '0', False)
                                    + f' - {pane[0] / 2:g}) / 100) END')
    f['BR Path Head Count'] = _calc('BR Path Head Count', 'Column count (row 61).', f'IF [Node Path Index] = 61 THEN STR([BR Path Count]) END')
    f['BR Path Head Count Point'] = _calc('BR Path Head Count Point', 'Right at the column.',
                                          f'IF [Node Path Index] = 61 THEN MAKEPOINT({(pane[1] / 2 - 9) / 100:.4f}, '
                                          f'({x0} + {COL_W} - 4 - {pane[0] / 2:g}) / 100) END')
    lk = 'INT([Node Path Index]) - 62'
    f['BR Path Rule Point'] = _calc('BR Path Rule Point', 'The line under each column title (rows 62 to 65).',
                                    f'IF [Node Path Index] >= 62 AND [Node Path Index] <= 65 THEN MAKEPOINT(\n'
                                    f'    ({pane[1] / 2:g} - (CASE {lk} WHEN 0 THEN 18 WHEN 1 THEN 18 ELSE 19 END)) / 100,\n'
                                    f'    ((CASE {lk} WHEN 0 THEN {x0} WHEN 3 THEN {x0} ELSE {x0} + {COL_W} END) - {pane[0] / 2:g}) / 100\n) END')
    f['Is BR Path Carrier'] = _calc('Is BR Path Carrier', 'The three scaffold models. Put on Filters (True).', 'NOT ISNULL([BR Path Column])')
    t = {n: (SP_MEA if n.endswith('Point') else S_DIM) for n in f}
    t.update({'BR Path Column': I_DIM, 'BR Path Count': I_DIM, 'BR Chip Id': I_DIM, 'Is BR Path Carrier': B_DIM})
    return f, t


# ================================================================ riskiest nodes (Node Daily rows)

def _risk():
    vals, rows = {}, {}
    for per in PERIODS:
        for k, d in DAYS.items():
            n = NODES[k]
            t = n['resource_type']
            win = [d[b] for b in range(per) if b in d]
            s = lambda c: sum(_num(r[c]) or 0 for r in win)
            if t == 'model':
                fr = s('runs_failed') / s('runs') if s('runs') else 0
            elif t == 'source':
                checked = sum(1 for r in win if sum(_num(r[c]) or 0 for c in ('fresh_checks_pass', 'fresh_checks_warn', 'fresh_checks_error')) > 0)
                fr = sum(1 for r in win if (_num(r['fresh_checks_error']) or 0) > 0) / checked if checked else 0
            else:
                tot = s('refresh_ok') + s('refresh_failed')
                fr = s('refresh_failed') / tot if tot else 0
            cons = _num(n[f'downstream_consumers_{per}d']) or 0
            vals[(per, k)] = dict(fr=fr, cons=cons, risk=fr * cons)
        for plat in PLATFORMS:
            ks = [k for k in DAYS if _in_plat(NODES[k], plat) and vals[(per, k)]['risk'] > 0]
            rows[(per, plat)] = sorted(ks, key=lambda k: -vals[(per, k)]['risk'])[:TOP_RISK]
    return vals, rows


RISK, RISK_ROWS = _risk()
_S = RISK_W / 1278                                # the prototype's columns, scaled to this canvas
RCOL = {'rank': 8, 'node': round(48 * _S), 'layer': round(250 * _S), 'plat': round(368 * _S), 'fed': round(607 * _S),
        'cons': round(715 * _S), 'rate': round(820 * _S), 'bar0': round(837 * _S), 'bar1': round(1139 * _S),
        'score': round(1179 * _S), 'now': round(1195 * _S)}


def risk_calcs():
    pane, f = (RISK_W, RISK_ROW), {}
    shown = sorted({(per, k) for (per, _p), ks in RISK_ROWS.items() for k in ks})
    nodes = sorted({k for _p, k in shown})
    rank = {f'{per}|{pl}|{k}': i + 1 for (per, pl), ks in RISK_ROWS.items() for i, k in enumerate(ks)}
    f['BR Risk Rank'] = _calc('BR Risk Rank', 'Place among the 10 riskiest nodes in the period under the platform filter (risk = failure rate x\n'
                              '// average daily downstream consumers; written by the build, the prototype\'s rule).',
                              _case(f'STR([p_period]) + "|" + [p_platform] + "|" + {NODE}', rank, quote=False))
    f['Is BR Risk Row'] = _calc('Is BR Risk Row', 'Rows of the table. Put on Filters (True).', 'NOT ISNULL([BR Risk Rank])')
    f['BR Risk Row Key'] = _calc('BR Risk Row Key', 'The selected node\'s row in light blue.', f'IF {NODE} = {SEL} THEN "Selected" ELSE "Default" END')
    mx = {(per, pl): max((RISK[(per, k)]['risk'] for k in ks), default=1) for (per, pl), ks in RISK_ROWS.items()}
    pk = f'STR([p_period]) + "|" + {NODE}'
    rate = {f'{per}|{k}': f'{RISK[(per, k)]["fr"] * 100:.1f}%' for per, k in shown}
    cons = {f'{per}|{k}': f'{RISK[(per, k)]["cons"]:.0f}' for per, k in shown}
    score = {f'{per}|{k}': f'{RISK[(per, k)]["risk"]:.1f}' for per, k in shown}
    name = {k: _fit(NODES[k]['node_name'], RCOL['layer'] - RCOL['node'] - 10, 8) for k in nodes}
    layer = {k: LAYER_NAME.get(NODES[k]['layer'], '') for k in nodes}
    fed = {k: str(int(float(NODES[k]['exposures_fed'] or 0))) for k in nodes}
    plat = {k: PLAT_NAME.get(NODES[k]['platform_now'], '') for k in nodes}
    now = {k: f'{STATUS_ICON[_status(k)]} {_status(k)}' for k in nodes}
    for n, why, key, d in (('Rank', '"#1".', f'STR([p_period]) + "|" + [p_platform] + "|" + {NODE}', {k: f'#{v}' for k, v in rank.items()}),
                           ('Name', 'Node name.', NODE, name), ('Layer', 'Layer.', NODE, layer), ('Fed', 'Exposures fed.', NODE, fed),
                           ('Consumers', 'Average daily downstream consumers in the period.', pk, cons),
                           ('Rate', 'Failure rate in the period.', pk, rate), ('Score', 'Risk score.', pk, score),
                           ('Platform', 'Platform pill text.', NODE, plat), ('Now', 'Status now, pill text.', NODE, now)):
        f[f'BR Risk {n} Text'] = _calc(f'BR Risk {n} Text', why + ' Written by the build.', _case(key, d))
    f['BR Risk Now Key'] = _calc('BR Risk Now Key', 'Status pill tint.', _case(NODE, {k: _status(k) for k in nodes}))
    for pk_, pn in PLAT_NAME.items():
        f[f'BR Risk Square {pn}'] = _calc(f'BR Risk Square {pn}', f'Platform square in {pn}\'s colour.', f'IF [platform_now] = "{pk_}" THEN "■ " END')
    pt = lambda x: f'MAKEPOINT(0, ({x:.1f} - {pane[0] / 2:g}) / 100)'
    left = lambda col, d, b=False: _case(NODE, {k: pt(RCOL[col] + W8(v, b) / 2) for k, v in d.items()}, quote=False)
    right = lambda col, d, key=pk: _case(key, {k: pt(RCOL[col] - W8(v) / 2) for k, v in d.items()}, quote=False)
    rk = f'STR([p_period]) + "|" + [p_platform] + "|" + {NODE}'
    f['BR Risk Rank Point'] = _calc('BR Risk Rank Point', 'Rank, left.', _case(rk, {k: pt(RCOL['rank'] + W8(f'#{v}') / 2) for k, v in rank.items()}, quote=False))
    f['BR Risk Name Point'] = _calc('BR Risk Name Point', 'Name, left.', left('node', name))
    f['BR Risk Layer Point'] = _calc('BR Risk Layer Point', 'Layer, left.', left('layer', layer))
    f['BR Risk Fed Point'] = _calc('BR Risk Fed Point', 'Exposures fed, right.', _case(NODE, {k: pt(RCOL['fed'] - W8(v) / 2) for k, v in fed.items()}, quote=False))
    f['BR Risk Consumers Point'] = _calc('BR Risk Consumers Point', 'Consumers, right.', right('cons', cons))
    f['BR Risk Rate Point'] = _calc('BR Risk Rate Point', 'Failure rate, right.', right('rate', rate))
    f['BR Risk Score Point'] = _calc('BR Risk Score Point', 'Risk score, right.', right('score', score))
    idx = '[Node Path Index]'
    pw = {k: round(W7('■ ' + v) + 14) for k, v in plat.items()}
    nw = {k: round(W7(v, True) + 16) for k, v in now.items()}
    f['BR Risk Platform Pill Point'] = _calc('BR Risk Platform Pill Point', 'Platform pill outline.', _rounded(idx, RCOL['plat'], _case(NODE, pw, '0', False), 5, 22, 3, pane))
    f['BR Risk Platform Text Point'] = _calc('BR Risk Platform Text Point', 'Middle of the platform pill.', _case(NODE, {k: pt(RCOL['plat'] + w / 2) for k, w in pw.items()}, quote=False))
    f['BR Risk Now Pill Point'] = _calc('BR Risk Now Pill Point', 'Status pill.', _rounded(idx, RCOL['now'], _case(NODE, nw, '0', False), 5, 22, 8, pane))
    f['BR Risk Now Text Point'] = _calc('BR Risk Now Text Point', 'Middle of the status pill.', _case(NODE, {k: pt(RCOL['now'] + w / 2) for k, w in nw.items()}, quote=False))
    bw = {f'{per}|{pl}|{k}': max(2, (RCOL['bar1'] - RCOL['bar0']) * RISK[(per, k)]['risk'] / mx[(per, pl)])
          for (per, pl), ks in RISK_ROWS.items() for k in ks}
    f['BR Risk Track Point'] = _calc('BR Risk Track Point', 'Bar track.', _rounded(idx, RCOL['bar0'], RCOL['bar1'] - RCOL['bar0'], 11, 16, 2, pane))
    f['BR Risk Bar Point'] = _calc('BR Risk Bar Point', 'Risk bar, as long as its share of the riskiest node\'s score.',
                                   _rounded(idx, RCOL['bar0'], _case(f'STR([p_period]) + "|" + [p_platform] + "|" + {NODE}', {k: f'{v:.1f}' for k, v in bw.items()}, '0', False),
                                            11, 16, 2, pane))
    f['BR Risk Row Point'] = _calc('BR Risk Row Point', 'The row (takes the click; light blue when selected).', _rounded(idx, 0, RISK_W, 0, RISK_ROW - 1, 0, pane))
    f['BR Risk Divider Point'] = _calc('BR Risk Divider Point', 'Line under each row.', _rounded(idx, 0, RISK_W, RISK_ROW - 1, RISK_ROW, 0, pane))
    heads = [('#', RCOL['rank'], 'l'), ('NODE', RCOL['node'], 'l'), ('LAYER', RCOL['layer'], 'l'), ('PLATFORM', RCOL['plat'], 'l'),
             ('EXPOSURES FED', RCOL['fed'], 'r'), ('DAILY CONSUMERS', RCOL['cons'], 'r'), ('FAILURE RATE', RCOL['rate'], 'r'),
             ('RISK SCORE', RCOL['bar0'], 'l'), ('NOW', RCOL['now'], 'l')]
    f.update(_headings('BR Risk', heads, RISK_W))
    t = {n: (SP_MEA if n.endswith('Point') else S_DIM) for n in f}
    t.update({'BR Risk Rank': I_DIM, 'Is BR Risk Row': B_DIM})
    return f, t


_f, _t = {}, {}
for fn in (header_calcs, pill_calcs, who_calcs, path_calcs, risk_calcs):
    a, b = fn()
    _f.update(a)
    _t.update(b)
_f['Is BR Heading Row'] = '// Is BR Heading Row\n// One date row per column title. Put on Filters (True).\n[day_index] < 9'
_t['Is BR Heading Row'] = B_DIM
CALCS.add(formulas=_f, types=_t)


# ================================================================ sheets

def _a(n):
    return R(n, 'attr')


def _poly(title, point, pane, path, lod, colour=None, mark=None, inert=True, tooltip=None):
    return Pane('Polygon', title=title, inert=inert, color=colour, mark_color=mark, path=path, label_show=False,
                lod=[R(point, 'clct'), *lod], pane_size=pane, tooltip=tooltip)


def _words(title, point, runs, pane, lod, inert=True, tooltip=None):
    return label_pane(title=title, inert=inert, text=[r['_ref'] for r in runs if '_ref' in r], label=runs, align='center',
                      valign='center', lod=[R(point, 'clct'), *lod], pane_size=pane, tooltip=tooltip)


def _scaffold_label(name, runs, align='left', valign='top', tooltip=False):
    return Sheet(name, filters=[R('Is First Date Row')], tooltip=tooltip,
                 panes=label_pane(text=[r['_ref'] for r in runs if '_ref' in r], align=align, valign=valign, label=runs))


def header_sheets() -> list[Sheet]:
    out = [_scaffold_label('BR Impact Summary', [
        run(_a('BR Lead Text'), 12, INK1), run(_a('BR Products Text'), 12, NAVY, SEMI), run(_a('BR And Text'), 12, INK1),
        run(_a('BR Consumers Text'), 12, NAVY, SEMI), run(_a('BR Tail Text'), 12, INK1), run(NL, 6, INK3),
        run(_a('BR Issue Text'), 8, INK3)])]
    for name in ('Models', 'Semantic', 'Exposures', 'Owners'):
        out.append(_scaffold_label(f'BR Chip {name}', [run(_a(f'BR Chip {name} Value'), 14, NAVY, SEMI), run(NL, 7, INK3),
                                                        run(_a(f'BR Chip {name} Label'), 7, INK3)]))
    out.append(_scaffold_label('BR Chip Unregistered', [run(_a('BR Chip Unregistered Red'), 14, CRIT_INK, SEMI),
                                                         run(_a('BR Chip Unregistered Plain'), 14, NAVY, SEMI), run(NL, 7, INK3),
                                                         run(_a('BR Chip Unregistered Label'), 7, INK3)]))
    out.append(_scaffold_label('BR Unregistered Callout', [run(_a('BR Unregistered Callout Text'), 8, WARN_INK)], valign='center'))
    out.append(_scaffold_label('BR No Owner Callout', [run(_a('BR No Owner Callout Text'), 8, CRIT_INK, SEMI)], valign='center'))
    # the prototype's "Copy incident message" button, with an envelope: the envelope is a custom shape with the text to
    # its right, on one hidden axis (GB, v42: no click bar, axis rulers off); the holder draws the rounded border
    draw_email_icon()
    glyph, anchor = R('BR Email Glyph'), R('BR Email Anchor')
    lod = [R('BR Incident Subject'), R('BR Incident Body')]
    rulers = ["            <format attr='line-visibility' scope='cols' value='off' />",
              "            <format attr='line-visibility' scope='rows' value='off' />",
              "            <format attr='stroke-size' scope='cols' value='0' />",
              "            <format attr='stroke-size' scope='rows' value='0' />"]
    out.append(Sheet('BR Email Button', cols=[anchor], hide=[anchor], filters=[R('Is First Date Row')], fixed={anchor: (0, 1)}, tooltip=False,
                     # no pane border: Tableau's default line drew a second, square border inside the rounded holder (v41)
                     extra={'axis': rulers, 'pane': ["            <format attr='border-style' value='none' />",
                                                      "            <format attr='border-width' value='0' />"]},
                     panes=Pane('Shape', shape=f'{SH.FOLDER}/Email.png', size=1.2, lod=list(lod), text=[glyph],
                                label=[run(glyph, 9, INK1)], align='right')))
    # the selected node's pills
    pane, path = PILL_PANE, R('Node Path Index', kind='ok')
    color_map(R('BR Pill Status Key'), {f'"{k}"': v for k, v in STATUS_TINT.items()})
    layers = [_poly('Status', 'BR Pill Status Point', pane, path, [], colour=R('BR Pill Status Key')),
              _poly('Platform', 'BR Pill Platform Point', pane, path, [], mark=LINE),
              _poly('Layer', 'BR Pill Layer Point', pane, path, [], mark=LINE),
              _words('Status text', 'BR Pill Status Text Point', [run(_a('BR Pill Status Text'), 7, INK1, SEMI)], pane, []),
              _words('Platform text', 'BR Pill Platform Text Point', [*[run(_a(f'BR Pill Square {pn}'), 7, PLAT[pk]) for pk, pn in PLAT_NAME.items()],
                                                                       run(_a('BR Pill Platform Text'), 7, INK2)], pane, []),
              _words('Layer text', 'BR Pill Layer Text Point', [run(_a('BR Pill Layer Text'), 7, INK2)], pane, [])]
    out.append(_grid(Sheet('BR Node Header', rows=[LAT], cols=[LON], filters=[R('Is BR Pill Carrier')], layers=True, no_basemap=True,
                           zoom=None, tooltip=False, panes=[Pane('Automatic', pane_size=pane), *layers]), pane))
    return out


def draw_email_icon():
    """An envelope outline in ink 2, drawn at 4x for the email button's custom shape (embedded with the workbook)."""
    from PIL import Image, ImageDraw
    img = Image.new('RGBA', (64, 64), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    # edge to edge, so the shape's size is the envelope's (v40's padded icon came out much smaller than the text)
    d.rounded_rectangle([2, 10, 61, 53], radius=6, outline=INK2, width=6)
    d.line([(5, 14), (32, 35), (58, 14)], fill=INK2, width=6, joint='curve')
    SH.OUT.mkdir(parents=True, exist_ok=True)
    img.save(SH.OUT / 'Email.png')


def _header_canvas(name, prefix, width):
    hp = (width, COLHEAD_H)
    return _grid(Sheet(name, rows=[LAT], cols=[LON], filters=[R('Is BR Heading Row')], layers=True, no_basemap=True, zoom=None, tooltip=False,
                       panes=[Pane('Automatic', pane_size=hp),
                              label_pane(title='Titles', inert=True, text=[_a(f'{prefix} Heading')], label=[run(_a(f'{prefix} Heading'), 7, INK3, SEMI)],
                                         align='center', lod=[R(f'{prefix} Heading Point', 'clct'), R('day_index')], pane_size=hp)]), hp)


def who_sheets() -> list[Sheet]:
    key, order = R('node_id (dim_nodes.csv)'), R('BR Who Order', kind='ok')
    path, pane = R('Exposure Path Index', kind='ok'), (WHO_W, WHO_ROW)
    color_map(R('BR Who Trust Key'), {f'"{k}"': v for k, v in STATUS_TINT.items()})
    clicks = [R('Clear Node Value'), R('Clear Node Key Value'), *[R(f) for f, _ in PANEL_WRITES]]
    tip = [run(_a('BR Who Name Text'), 9, INK1, SEMI), run(NL, 7, INK3), run('CLICK TO OPEN ITS LINEAGE', 7, INK3, SEMI)]
    cell = lambda title, point, runs: _words(title, point, runs, pane, [key])
    layers = [
        _poly('Row', 'BR Who Row Point', pane, path, [key], mark=CARD, inert=False, tooltip=tip),
        _poly('Divider', 'BR Who Divider Point', pane, path, [key], mark=LINE_SOFT),
        _poly('Pill', 'BR Who Pill Point', pane, path, [key], colour=R('BR Who Trust Key')),
        cell('Name', 'BR Who Name Point', [run(_a('BR Who Name Text'), 8, INK1, SEMI)]),
        cell('Type', 'BR Who Type Point', [run(_a('BR Who Type Text'), 8, INK2)]),
        cell('Owner', 'BR Who Owner Point', [run(_a('BR Who Owner Text'), 8, INK2), run(_a('BR Who No Owner Text'), 8, CRIT_INK, SEMI)]),
        cell('Slack', 'BR Who Slack Point', [run(_a('BR Who Slack Text'), 8, INK2)]),
        cell('Consumers', 'BR Who Consumers Point', [run(_a('BR Who Consumers Text'), 8, INK1)]),
        cell('Status', 'BR Who Pill Text Point', [run(_a('BR Who Trust Critical'), 7, CRIT_INK, SEMI), run(_a('BR Who Trust Warning'), 7, WARN_INK, SEMI),
                                                  run(_a('BR Who Trust Healthy'), 7, GOOD_INK, SEMI)]),
    ]
    layers[0].lod += clicks
    table = _grid(Sheet('BR Who To Tell Table', rows=[Cross([Nest([order, key]), LAT])], cols=[LON], filters=[R('Is BR Who Row')],
                        hide=[order, key], layers=True, no_basemap=True, zoom=None,
                        panes=[Pane('Automatic', lod=[key], pane_size=pane), *layers]), pane)
    return [_header_canvas('BR Who To Tell Header', 'BR Who', WHO_W), table]


def path_sheet() -> Sheet:
    pane, path = PATH_PANE, R('Node Path Index', kind='ok')
    col, cid = R('BR Path Column'), R('BR Chip Id')
    color_map(R('BR Chip Key'), {'"Critical"': CRIT_TINT, '"Warning"': WARN_TINT, '"Healthy"': '#f5f5f3', '"No data"': '#f5f5f3'})
    layers = [
        _poly('Rule', 'BR Path Rule Point', pane, path, [col], mark=LINE),
        _poly('Chips', 'BR Chip Point', pane, path, [col, cid], colour=R('BR Chip Key')),
        _words('Names', 'BR Chip Text Point', [run(_a('BR Chip Dot Critical'), 8, CRIT), run(_a('BR Chip Dot Warning'), 8, WARN),
                                                run(_a('BR Chip Dot Healthy'), 8, GOOD), run(_a('BR Chip Dot No data'), 8, NONE),
                                                run(_a('BR Chip Name'), 8, INK1)], pane, [col, R('Node Path Index')]),
        _words('Heads', 'BR Path Head Point', [run(_a('BR Path Head'), 7, INK3, SEMI)], pane, [col, R('Node Path Index')]),
        label_pane(title='Counts', inert=True, text=[_a('BR Path Head Count')], label=[run(_a('BR Path Head Count'), 7, INK3, SEMI)],
                   align='right', lod=[R('BR Path Head Count Point', 'clct'), col, R('Node Path Index')], pane_size=pane),
    ]
    return _grid(Sheet('BR Downstream Path', rows=[LAT], cols=[LON], filters=[R('Is BR Path Carrier')], layers=True, no_basemap=True,
                       zoom=None, tooltip=False, panes=[Pane('Automatic', pane_size=pane), *layers]), pane)


def risk_sheets() -> list[Sheet]:
    key, order = R('node_id (dim_nodes.csv)'), R('BR Risk Rank', kind='ok')
    path, pane = R('Node Path Index', kind='ok'), (RISK_W, RISK_ROW)
    color_map(R('BR Risk Row Key'), {'"Selected"': '#eef4fb', '"Default"': CARD})
    color_map(R('BR Risk Now Key'), {f'"{k}"': v for k, v in STATUS_TINT.items()})
    clicks = [R('node_key'), *[R(f) for f, _ in PANEL_WRITES]]
    tip = [run(_a('BR Risk Name Text'), 9, INK1, SEMI), run(NL, 7, INK3), run('RISK SCORE   ', 7, INK3, SEMI), run(_a('BR Risk Score Text'), 9, NAVY, SEMI),
           run(NL, 7, INK3), run('CLICK TO TRACE IT', 7, INK3, SEMI)]
    cell = lambda title, point, runs: _words(title, point, runs, pane, [key])
    layers = [
        _poly('Row', 'BR Risk Row Point', pane, path, [key, *clicks], colour=R('BR Risk Row Key'), inert=False, tooltip=tip),
        _poly('Divider', 'BR Risk Divider Point', pane, path, [key], mark=LINE_SOFT),
        _poly('Platform pill', 'BR Risk Platform Pill Point', pane, path, [key], mark=LINE),
        _poly('Track', 'BR Risk Track Point', pane, path, [key], mark='#eef0ee'),
        _poly('Bar', 'BR Risk Bar Point', pane, path, [key], mark=ACCENT),
        _poly('Now pill', 'BR Risk Now Pill Point', pane, path, [key], colour=R('BR Risk Now Key')),
        cell('Rank', 'BR Risk Rank Point', [run(_a('BR Risk Rank Text'), 8, INK3)]),
        cell('Name', 'BR Risk Name Point', [run(_a('BR Risk Name Text'), 8, INK1)]),
        cell('Layer', 'BR Risk Layer Point', [run(_a('BR Risk Layer Text'), 8, INK2)]),
        cell('Platform', 'BR Risk Platform Text Point', [*[run(_a(f'BR Risk Square {pn}'), 7, PLAT[pk]) for pk, pn in PLAT_NAME.items()],
                                                         run(_a('BR Risk Platform Text'), 7, INK2)]),
        cell('Fed', 'BR Risk Fed Point', [run(_a('BR Risk Fed Text'), 8, INK1)]),
        cell('Consumers', 'BR Risk Consumers Point', [run(_a('BR Risk Consumers Text'), 8, INK1)]),
        cell('Rate', 'BR Risk Rate Point', [run(_a('BR Risk Rate Text'), 8, INK1)]),
        cell('Score', 'BR Risk Score Point', [run(_a('BR Risk Score Text'), 8, INK1)]),
        cell('Now', 'BR Risk Now Text Point', [run(_a('BR Risk Now Text'), 7, INK1, SEMI)]),
    ]
    table = _grid(Sheet('BR Riskiest Nodes Table', rows=[Cross([Nest([order, key]), LAT])], cols=[LON], filters=[R('Is BR Risk Row')],
                        hide=[order, key], layers=True, no_basemap=True, zoom=None,
                        panes=[Pane('Automatic', lod=[key], pane_size=pane), *layers]), pane)
    return [_header_canvas('BR Riskiest Nodes Header', 'BR Risk', RISK_W), table]


def sheets() -> list[Sheet]:
    return header_sheets() + who_sheets() + [path_sheet()] + risk_sheets()


# ================================================================ dashboard content (build plan 3.3)

def _chip(name, w):
    return Z('horz', friendly=f'BR Chip {name} Holder', fixed=w, kids=[sheet(f'BR Chip {name}')], style={
        'border-color': LINE, 'border-style': 'solid', 'border-width': '1', 'corner-radius': '8', 'margin-right': '8',
        'padding-top': '6', 'padding-left': '10', 'padding-right': '6'})


def _callout(name, dzv, bg, border, h):
    return Z('vert', friendly=f'{name} Holder', fixed=h, dzv=(dzv, False), style={'margin-top': '8'}, kids=[
        Z('vert', friendly=name + ' Box', kids=[sheet(name)], style={
            'background-color': bg, 'border-color': border, 'border-style': 'solid', 'border-width': '1', 'corner-radius': '8',
            'padding-left': '10', 'padding-right': '10'})])


def content() -> Z:
    picker = Z('vert', friendly='BR Picker Column', fixed=PICK_W, kids=[
        text([run('NODE TO TRACE', 7, INK3, SEMI)], fixed=20),
        Z('paramctrl', param='p_selected_node', fixed=34, style={'padding-bottom': '4'}),
        sheet('BR Node Header', 28)])
    chips = Z('horz', friendly='BR Chips Row', fixed=50, kids=[
        _chip('Models', 112), _chip('Semantic', 112), _chip('Exposures', 96), _chip('Owners', 96), _chip('Unregistered', 112), blank()])
    summary = Z('vert', friendly='BR Summary Column', kids=[sheet('BR Impact Summary', 66), chips])
    message = Z('vert', friendly='BR Message Holder', fixed=MSG_W, kids=[
        # the prototype's secondary button: white fill, 1 px line, radius 8, the sheet inset so the corners stay round
        Z('horz', friendly='BR Email Button Holder', fixed=34, kids=[sheet('BR Email Button')], style={
            'background-color': CARD, 'border-color': LINE, 'border-style': 'solid', 'border-width': '1', 'corner-radius': '8',
            'padding': '3'}),
        blank()])
    head = card('BR Header Card', fixed=HEAD_H, horz=True, pad=(14, 18, 14, 18), kids=[picker, blank(24), summary, message])
    who = card('BR Who Card', fixed=HALF, margins={'right': 7}, kids=[
        card_header('Who to tell', 'Affected exposures, their owners and how many consumers used them each day on average in this period'),
        sheet('BR Who To Tell Header', COLHEAD_H), blank(1, LINE), sheet('BR Who To Tell Table'),
        _callout('BR Unregistered Callout', 'Show BR Unregistered Callout', WARN_TINT, '#f3ddb4', 58),
        _callout('BR No Owner Callout', 'Show BR No Owner Callout', CRIT_TINT, '#f2cdca', 40)])
    path = card('BR Downstream Card', fixed=HALF, margins={'left': 7}, kids=[  # 649 (GB, v42)
        card_header('Downstream path', 'Everything built on this node, by layer'), sheet('BR Downstream Path')])
    risk = card('BR Risk Card', kids=[
        card_header('Riskiest nodes in this period', 'Risk = average daily consumers downstream × failure rate. Failure rate is failed runs '
                    'for models, days past the error threshold for sources, and failed refreshes for BI semantic objects. Click a row to trace it.'),
        sheet('BR Riskiest Nodes Header', COLHEAD_H), blank(1, LINE), sheet('BR Riskiest Nodes Table')])
    return Z('vert', friendly='BR Content', style=CONTENT_PAD, kids=[
        head,
        Z('horz', friendly='BR Middle Row', fixed=MID_H, style={'margin-top': '14'}, kids=[who, path]),
        # the last row is flexible, so it always reaches the bottom padding (skill: sizing)
        Z('horz', friendly='BR Bottom Row', style={'margin-top': '14'}, kids=[risk])])


def check_fit(zones) -> None:
    by = {(z.name or z.friendly): z.rect for z in zones}
    for name, (w, h) in (('BR Node Header', PILL_PANE), ('BR Downstream Path', PATH_PANE), ('BR Who To Tell Table', (WHO_W + 18, 0)),
                         ('BR Riskiest Nodes Table', (RISK_W + 18, 0)), ('BR Who To Tell Header', (WHO_W, COLHEAD_H)),
                         ('BR Riskiest Nodes Header', (RISK_W, COLHEAD_H))):
        _, _, zw, zh = by[name]
        assert w <= zw and h <= zh, f'{name}: needs {w} x {h}, zone is {zw:.0f} x {zh:.0f}'
    _, y, _, h = by['BR Bottom Row']
    end = 1000 - int(CONTENT_PAD['padding-bottom'])
    assert abs(y + h - end) < 0.5, f'BR rows end at {y + h:.0f}, content ends at {end}'


_EXPOSURE_CLICKS = [('p_selected_exposure', lambda: R('node_id (dim_nodes.csv)'), 'Select Exposure'),
                    ('p_selected_node', lambda: R('Clear Node Value'), 'Clear Node'),
                    ('p_selected_node_key', lambda: R('Clear Node Key Value'), 'Clear Node Key'),
                    *[(param, (lambda f=f: R(f)), f'Set {param}') for f, param in PANEL_WRITES]]
ACTIONS = [  # (sheet, source Ref factory, parameter, caption)
    *[('BR Who To Tell Table', ref, param, f'BR Who {cap}') for param, ref, cap in _EXPOSURE_CLICKS],
    ('BR Riskiest Nodes Table', lambda: R('node_id (dim_nodes.csv)'), 'p_selected_node', 'BR Pick Risk Node'),
    ('BR Riskiest Nodes Table', lambda: R('node_key'), 'p_selected_node_key', 'BR Pick Risk Node Key'),
    *[('BR Riskiest Nodes Table', (lambda f=f: R(f)), param, f'BR Risk Set {param}') for f, param in PANEL_WRITES],
]
NAV_ACTIONS = [('BR Who To Tell Table', 'Lineage explorer', 'Go to Lineage from BR Who To Tell Table')]
# mailto with the build's message: (sheet, caption, subject field, body field)
URL_ACTIONS = [('BR Email Button', 'BR Email Incident Message', 'BR Incident Subject', 'BR Incident Body')]
DEHIGHLIGHT = ['BR Who To Tell Table', 'BR Riskiest Nodes Table', 'BR Email Button']
