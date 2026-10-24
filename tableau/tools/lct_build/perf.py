"""Tab 4, Performance & cost (PF): calc pack section 9, build plan 3.7.

GB's choices (24 Oct): the most expensive models as a pixel canvas like the prototype, the data product costs as the
Why runs failed bars, and a model row click opens it in the Lineage explorer (Blast radius once that tab exists).

- KPIs: Warehouse cost re-uses the Health sheet; average per day with its platform split, the slowest model and the
  incremental candidates are label sheets.
- Cost by platform: native stacked bars on the shared reversed day axis of Run & failures, the window band as back
  bars, and the three moves as constant reference lines (3 Sep HubSpot, 11 Sep Ads, 4 Oct fct_sessions fixed).
- Runtime of the six slowest models: one line each, the biggest change in the accent and the rest grey, names at the
  line ends in room the axis leaves to the right of today.
- Which models are the six slowest, the biggest change, the top 15 by cost and the incremental flags depend only on
  the period and platform, so the build works them out for all 12 combinations (the prototype's own rules) and
  writes them as CASE calcs on the parameters and the node. The numbers shown stay live Tableau aggregates.
- Both charts' value axes follow the data per platform (Redshift's costs and runtimes are small), so the band height
  is written per combination and the axis width is fixed, so the date strip below still lines up.
"""

from __future__ import annotations

import collections
import csv
import datetime as dt

from . import shapes as SH
from .core import (PANEL_WRITES, ACCENT, B_DIM, BOOK, CALCS, CARD, CRIT_INK, GOOD_INK, GOOD_TINT, I_DIM, I_MEA, INK1,
                   INK2, INK3, LAT, LINE, LINE_SOFT, LON, NAVY, NL, PLAT, R_MEA, S_DIM, S_MEA, SEMI, SP_MEA, WARN_INK,
                   WARN_TINT, Cross, Nest, Pane, R, Sheet, Z, blank, card, card_header, color_map, label_pane, run,
                   sheet, text)
from .lineage import _fit, _grid, _q
from .run import BAND, _axis_style
from .shell import CONTENT_H, CONTENT_PAD

P = 'PF'
ROOT = SH.ROOT
M = ROOT / 'data' / 'marts'
NODES = {r['node_id']: r for r in csv.DictReader(open(M / 'dim_nodes.csv', encoding='utf-8'))}
PLAT_NAME = {'snowflake': 'Snowflake', 'databricks': 'Databricks', 'redshift': 'Redshift'}
PERIODS, PLATFORMS = (7, 30, 90), ('All', 'snowflake', 'databricks', 'redshift')
DAYS = 90

# ---------------------------------------------------------------- geometry (content 1312 x CONTENT_H)
KPI_H, MID_H = 96, 290
SIDE_W = 530                                   # runtime and product cost cards: take the rest, 7 px margin-left outside
MAIN_W = 1312 - SIDE_W - 7 - 7                 # 768 fixed (775 with its margin, GB): cost and expensive cards line up
BOTTOM_H = CONTENT_H - KPI_H - 14 - MID_H - 14  # 430: the bottom row takes the rest
EW = MAIN_W - 2 * 16 - 2 - SH.SLACK            # 730: the expensive-models canvas
HEAD_H = 22
TOP_N = 15
# 15 rows fit the card without a scroll bar (GB: no scroll bars): prototype rows are 27 px, these about 21
ROW_H = (BOTTOM_H - 2 - 28 - 44 - HEAD_H - 1 - SH.SLACK) // TOP_N
ROW = (EW, ROW_H)
# prototype columns (.t, 734 px at 1600): left edges, or right edges for the numbers
# GB (v33b): more room between the columns; the numbers spread over 300 to 600 and the pill clear of the cost
COL = {'dot': 11, 'name': 23, 'built': 172, 'runtime': 360, 'trend': 432, 'rows': 532, 'cost': 596, 'pill': 614}
GAP = 4                                         # Tableau leaves about 4 px between a point and a label beside it
AXIS_W = 40                                     # value axis width on both charts and their (clear) date strips
COST_X = (0, DAYS, {'reverse': 'true'})         # Days Back Mid, as on Run & failures
RT_X = (-26, DAYS, {'reverse': 'true'})         # 26 days of room right of today for the line-end names
EVENTS = [('2026-09-03', 'HubSpot moves', INK3, 'left'), ('2026-09-11', 'Ads move', INK3, 'right'),
          ('2026-10-04', 'fct_sessions fixed', GOOD_INK, 'right')]
ASOF = dt.date(2026, 10, 19)
USD = 'c"$"#,##0;-"$"#,##0'
MINS = 'n#,##0"m";-#,##0"m"'


# ================================================================ the 12 combinations, worked out by the build

def _num(v):
    return None if v in ('', None) else float(v)


def _combos():
    """The prototype's rules (mockup/src/views-c.js RENDER.perf) for every period and platform: the six slowest
    models by mean daily runtime, the one with the biggest runtime change, the top 15 by build cost, and the
    incremental candidates (a full-refresh table over 10M rows whose runtime ran 25 % over its 28-day average on a
    day in the window) and whether each has been switched."""
    days = collections.defaultdict(dict)
    for r in csv.DictReader(open(M / 'mart_node_daily.csv', encoding='utf-8')):
        days[r['node_id']][(ASOF - dt.date.fromisoformat(r['date'])).days] = r
    out = {}
    for per in PERIODS:
        for plat in PLATFORMS:
            mods = []
            for nid, n in NODES.items():
                if n['resource_type'] != 'model' or (plat != 'All' and f'|{plat}|' not in n['platform_filter_values']):
                    continue
                d = days[nid]
                win = [d[b] for b in range(per) if b in d]
                rts = [_num(r['avg_runtime_sec']) for r in win if _num(r['avg_runtime_sec']) is not None]
                trends = [_num(r['runtime_trend_pct']) for r in win]
                cand = (_num(n['max_rows_built']) or 0) > 10e6 and any(
                    r['materialization_on_day'] == 'table' and (_num(r['runtime_trend_pct']) or 0) > 0.25 for r in win)
                fixed = cand and d[0]['materialization_on_day'] == 'incremental'
                first_incr = max(b for b in d if d[b]['materialization_on_day'] == 'incremental') if fixed else None
                mods.append(dict(id=nid, rt=sum(rts) / len(rts) if rts else 0,
                                 cost=sum(_num(r['build_cost_usd']) or 0 for r in win),
                                 peak=max([t if t is not None else -1 for t in trends] or [-1]),
                                 state='Switched' if fixed else 'Open' if cand else None,
                                 since=ASOF - dt.timedelta(days=first_incr) if fixed else None))
            slow = sorted(mods, key=lambda m: -m['rt'])[:6]
            biggest = slow[0]
            for m in slow:
                if abs(m['peak']) > abs(biggest['peak']):
                    biggest = m
            top = sorted(mods, key=lambda m: -m['cost'])[:TOP_N]
            # chart heights: the tallest stacked day under this platform filter, and the six models' longest run
            out[(per, plat)] = dict(slow=slow, biggest=biggest, top=top)
    return out, days


COMBOS, _DAYS = _combos()


def _nice(v, steps=(0.5, 1, 2, 5, 10, 20, 25, 50)):
    """A round axis top a little above v, so Tableau's automatic axis ends on it and the band fills the height."""
    for s in steps:
        if v / s <= 8:
            return (int(v * 1.04 / s) + 1) * s
    return v


def _cost_tops():
    per_day = {p: collections.defaultdict(float) for p in PLATFORMS}
    for nid, d in _DAYS.items():
        for b, r in d.items():
            c = (_num(r['build_cost_usd']) or 0) + (_num(r['consumer_query_cost_usd']) or 0)
            per_day['All'][b] += c
            if r['platform_on_day'] in per_day:
                per_day[r['platform_on_day']][b] += c
    return {p: _nice(max(v.values())) for p, v in per_day.items()}


def _runtime_tops():
    return {k: _nice(max((_num(r['avg_runtime_sec']) or 0) / 60 for m in c['slow'] for r in _DAYS[m['id']].values()))
            for k, c in COMBOS.items()}


COST_TOP, RT_TOP = _cost_tops(), _runtime_tops()
KEY = 'STR([p_period]) + "|" + [p_platform] + "|" + [node_id (dim_nodes.csv)]'
COMBO = 'STR([p_period]) + "|" + [p_platform]'
TABLE_NODES = sorted({m['id'] for c in COMBOS.values() for m in c['top']})
SHORT = lambda d: f'{d.day} {d:%b}'


def _case(expr, values, default='NULL', quote=True):
    body = '\n'.join(f'WHEN {_q(k)} THEN {_q(v) if quote else v}' for k, v in values.items())
    return f'CASE {expr}\n{body}\nELSE {default}\nEND'


def _combo_case(name, why, expr, values, default='NULL', quote=True):
    return f'// {name}\n// {why}\n' + _case(expr, values, default, quote)


def _key(c, nid):
    return f'{c[0]}|{c[1]}|{nid}'


NODE = '[node_id (dim_nodes.csv)]'


def _node_case(name, why, values, default='NULL', quote=True):
    return f'// {name}\n// {why}\n' + _case(NODE, values, default, quote)


def _pill_text(m):
    return f'✓  Switched {SHORT(m["since"])}' if m['state'] == 'Switched' else '▲  Make incremental'


def combo_calcs():
    ranks = {_key(k, m['id']): i + 1 for k, c in COMBOS.items() for i, m in enumerate(c['top'])}
    slow = {_key(k, m['id']): i + 1 for k, c in COMBOS.items() for i, m in enumerate(c['slow'])}
    big = {_key(k, c['biggest']['id']): 'Top change' for k, c in COMBOS.items()}
    flagged = {_key(k, m['id']): m for k, c in COMBOS.items() for m in c['top'] if m['state']}
    f = {
        'PF Cost Rank': _combo_case('PF Cost Rank', 'Place of a model among the 15 that cost most to build in the period, under the platform filter\n'
                                    '// (worked out by the build for every period and platform, as the prototype ranks them).', KEY, ranks, quote=False),
        'Is PF Top Cost Model': '// Is PF Top Cost Model\n// The 15 rows of the most expensive models table. Put on Filters (True).\nNOT ISNULL([PF Cost Rank])',
        'PF Slowest Rank': _combo_case('PF Slowest Rank', 'Place of a model among the six slowest (mean of its daily average successful run in the\n'
                                       '// period), under the platform filter. Written by the build.', KEY, slow, quote=False),
        'Is PF Slowest Six': '// Is PF Slowest Six\n// The six lines of the runtime chart. Put on Filters (True).\nNOT ISNULL([PF Slowest Rank])',
        'Is PF Slowest Model': '// Is PF Slowest Model\n// The slowest model, for the KPI. Put on Filters (True).\n[PF Slowest Rank] = 1',
        'PF Line Key': _combo_case('PF Line Key', 'Colour of a runtime line: the biggest runtime change among the six (its largest 7d vs 28d\n'
                                   '// change in the period) in the accent, the rest grey.', KEY, big, '"Other"'),
        'PF Pill State': _combo_case('PF Pill State', 'Incremental flag of a table row: Switched (green pill) or Open (amber pill).', KEY,
                                     {k: m['state'] for k, m in flagged.items()}),
        'PF Pill Text': _combo_case('PF Pill Text', 'The pill\'s text.', KEY, {k: _pill_text(m) for k, m in flagged.items()}),
        'PF Pill Good Text': '// PF Pill Good Text\n// Pill text in green.\nIF [PF Pill State] = "Switched" THEN [PF Pill Text] END',
        'PF Pill Warn Text': '// PF Pill Warn Text\n// Pill text in amber ink.\nIF [PF Pill State] = "Open" THEN [PF Pill Text] END',
        'PF Was Table Text': '// PF Was Table Text\n// "(was table)" after the built-as of a switched model.\nIF [PF Pill State] = "Switched" THEN "(was table)" END',
        'PF Cost Band': ('// PF Cost Band\n// The window band behind the cost bars: a bar to the top of the axis on days in the window. The axis\n'
                         '// follows the data, so the top is written per platform (a round number just above the busiest day).\n'
                         'IF MAX(IIF([In Period], 1, 0)) = 1 THEN\n'
                         + _case('[p_platform]', COST_TOP, quote=False) + '\nEND'),
        'PF Runtime Band': ('// PF Runtime Band\n// The window band behind the runtime lines, to the top of the axis (written per period and platform).\n'
                            'IF MAX(IIF([In Period], 1, 0)) = 1 THEN\n'
                            + _case(COMBO, {f'{k[0]}|{k[1]}': v for k, v in RT_TOP.items()}, quote=False) + '\nEND'),
        'Model Build Cost (Period)': ('// Model Build Cost (Period)\n// What a model cost to build in the window, USD (the prototype\'s model cost; its queries are\n'
                                     '// counted against the data products that run them).\nSUM(IF [In Period] THEN [build_cost_usd] END)'),
        'PF Runtime Line': '// PF Runtime Line\n// Average successful run that day, in minutes.\n[Runtime Minutes (Daily)]',
        'PF Axis Anchor': '// PF Axis Anchor\n// Point the date labels under the two charts are centred on (strip axis 0 to 1).\nIF NOT ISNULL(MIN([Axis Date Label])) THEN 0.5 END',
        'PF Dot Key': '// PF Dot Key\n// Platform dot colour on a table row.\n[platform_now]',
        'PF Runtime End Name': ('// PF Runtime End Name\n// The model\'s name on its line\'s last day (today), for the label to its right.\n'
                                'IF MIN([days_before_as_of]) = 0 THEN ATTR([node_name]) END'),
    }
    t = {'PF Cost Rank': I_DIM, 'Is PF Top Cost Model': B_DIM, 'PF Slowest Rank': I_DIM, 'Is PF Slowest Six': B_DIM,
         'Is PF Slowest Model': B_DIM, 'PF Line Key': S_DIM, 'PF Pill State': S_DIM, 'PF Pill Text': S_DIM,
         'PF Pill Good Text': S_DIM, 'PF Pill Warn Text': S_DIM, 'PF Was Table Text': S_DIM, 'PF Cost Band': R_MEA,
         'PF Runtime Band': R_MEA, 'Model Build Cost (Period)': R_MEA, 'PF Runtime Line': R_MEA, 'PF Axis Anchor': R_MEA,
         'PF Dot Key': S_DIM, 'PF Runtime End Name': S_MEA}
    return f, t


# ================================================================ KPI texts

def kpi_calcs():
    f, t = {}, {}
    for p, name in PLAT_NAME.items():
        shown = f'([p_platform] = "All" OR [p_platform] = "{p}")'
        f[f'PF {name} Name'] = f'// PF {name} Name\n// "{name}" in its colour on the average-per-day line, when the filter shows it.\nIF {shown} THEN "{name}" END'
        f[f'PF {name} Per Day Text'] = (f'// PF {name} Per Day Text\n// " $80" after the name: {name}\'s cost per day in the window ($0 when it had none).\n'
                                        f'IF {shown} THEN " $" + STR(INT(ROUND(ZN([Cost Per Day {name}])))) END')
        t[f'PF {name} Name'], t[f'PF {name} Per Day Text'] = S_DIM, S_MEA
    f['PF Platform Separator'] = '// PF Platform Separator\n// " · " between the platforms when all three are shown.\nIF [p_platform] = "All" THEN "  ·  " END'
    t['PF Platform Separator'] = S_DIM
    f['PF Slowest Trend Text'] = ('// PF Slowest Trend Text\n// "  ·  ▼ 88% 7d vs 28d" after the slowest model\'s average run.\n'
                                  'IF ISNULL([Runtime Trend Now]) THEN ""\n'
                                  'ELSE "  ·  " + (IF [Runtime Trend Now] > 0 THEN "▲ " ELSE "▼ " END)\n'
                                  '    + STR(INT(ROUND(ABS([Runtime Trend Now]) * 100))) + "% 7d vs 28d"\nEND')
    t['PF Slowest Trend Text'] = S_MEA
    f['PF Switched Text'] = '// PF Switched Text\n// Green: "fct_sessions switched 4 Oct".\nMAX([Switched Candidate Text])'
    f['PF Open Text'] = '// PF Open Text\n// Red: a candidate still to switch.\nMAX([Open Candidate Text])'
    f['PF No Candidates Text'] = ('// PF No Candidates Text\n// Grey, when no model qualified in the window.\n'
                                  'IF MAX(IIF([Is Incremental Candidate], 1, 0)) = 0 THEN "None in this period" END')
    t.update({'PF Switched Text': S_MEA, 'PF Open Text': S_MEA, 'PF No Candidates Text': S_MEA})
    return f, t


# ================================================================ the expensive-models canvas (Node Daily rows)

def _rect(x0, x1, y0, y1, pane=ROW):
    """Rectangle from the Node Path Index (0 to 87): the four corners, 22 points each."""
    pw, ph = pane
    lon = lambda x: f'(({x}) - {pw / 2:g}) / 100'
    lat = lambda y: f'{(ph / 2 - y) / 100:.4f}'
    k = 'INT([Node Path Index] / 22)'
    return (f'MAKEPOINT(\n    CASE {k} WHEN 0 THEN {lat(y0)} WHEN 1 THEN {lat(y0)} WHEN 2 THEN {lat(y1)} ELSE {lat(y1)} END,\n'
            f'    CASE {k} WHEN 0 THEN {lon(x0)} WHEN 1 THEN {lon(x1)} WHEN 2 THEN {lon(x1)} ELSE {lon(x0)} END\n)')


def _rounded(x0, w, y0, y1, r, pane=ROW):
    """Rounded rectangle from the Node Path Index: 22 points round each corner (build techniques, section 6).
    x0 and w may be expressions."""
    pw, ph = pane
    i, k = '[Node Path Index]', 'INT([Node Path Index] / 22)'
    th = f'RADIANS({k} * 90 + ({i} % 22 + 0.5) * 90 / 22)'
    cx, cy, h = f'(({x0}) + ({w}) / 2)', (y0 + y1) / 2, y1 - y0
    dx = f'((CASE {k} WHEN 1 THEN -1 WHEN 2 THEN -1 ELSE 1 END) * (({w}) / 2 - {r}) + {r} * COS({th}))'
    dy = f'((IF {k} < 2 THEN 1 ELSE -1 END) * {h / 2 - r:g} + {r} * SIN({th}))'
    return f'MAKEPOINT(\n    ({ph / 2 - cy:g} + {dy}) / 100,\n    ({cx} + {dx} - {pw / 2:g}) / 100\n)'


def _at(x, pane=ROW):
    return f'MAKEPOINT(0, ({x:.1f} - {pane[0] / 2:g}) / 100)'


def _rows_text(v):
    """The prototype's fK: 60.9M, 13.8K, 950."""
    v = _num(v)
    if not v:
        return '-'
    return f'{v / 1e6:.1f}M' if v >= 1e6 else f'{v / 1e3:.1f}K' if v >= 1e3 else str(round(v))


def table_calcs():
    nodes = {nid: NODES[nid] for nid in TABLE_NODES}
    names = {k: _fit(n['node_name'], COL['built'] - COL['name'] - 10, 8) for k, n in nodes.items()}
    built = {k: n['materialization_now'] or '-' for k, n in nodes.items()}
    rows = {k: _rows_text(n['max_rows_built']) for k, n in nodes.items()}
    pills = {_pill_text(m) for c in COMBOS.values() for m in c['top'] if m['state']}
    pill_w = {p: round(SH.text_width(p, 7, True) + 16) for p in pills}
    mid = ROW_H / 2
    f = {
        'PF Name Text': _node_case('PF Name Text', 'Model name, cut by the build to its column.', names),
        'PF Built As Text': '// PF Built As Text\n// How the model is built now.\n[materialization_now]',
        'PF Rows Text': _node_case('PF Rows Text', 'Largest build in rows, as the prototype writes it: "60.9M".', rows),
        # every left-aligned text sits at half its measured width from its column (map labels only centre reliably)
        'PF Name Point': ('// PF Name Point\n// Model name, left-aligned at its column.\nMAKEPOINT(0, ('
                          + _case(NODE, {k: f'{COL["name"] + SH.text_width(v, 8) / 2:.1f}' for k, v in names.items()}, '0', False)
                          + f' - {EW / 2:g}) / 100)'),
        'PF Built As Point': ('// PF Built As Point\n// Built as, left-aligned at its column.\nMAKEPOINT(0, ('
                              + _case(NODE, {k: f'{COL["built"] + SH.text_width(v, 8) / 2:.1f}' for k, v in built.items()}, '0', False)
                              + f' - {EW / 2:g}) / 100)'),
        'PF Was Table Point': ('// PF Was Table Point\n// "(was table)" just after the built-as.\nMAKEPOINT(0, ('
                               + _case(NODE, {k: f'{COL["built"] + SH.text_width(v, 8) + 4 + SH.text_width("(was table)", 8) / 2:.1f}'
                                                     for k, v in built.items()}, '0', False)
                               + f' - {EW / 2:g}) / 100)'),
        'PF Rows Point': ('// PF Rows Point\n// Largest build, right-aligned at its column.\nMAKEPOINT(0, ('
                          + _case(NODE, {k: f'{COL["rows"] - SH.text_width(v, 8) / 2:.1f}' for k, v in rows.items()}, '0', False)
                          + f' - {EW / 2:g}) / 100)'),
        # the live numbers end at their column's right edge (on a map pane, text-align right puts the label to the
        # left of the point, about 4 px off)
        'PF Runtime Point': '// PF Runtime Point\n// Average runtime: the label ends here.\n' + _at(COL['runtime'] + GAP),
        'PF Trend Point': '// PF Trend Point\n// 7d vs 28d: the label ends here.\n' + _at(COL['trend'] + GAP),
        'PF Cost Point': '// PF Cost Point\n// Cost: the label ends here.\n' + _at(COL['cost'] + GAP),
        'PF Band Point': '// PF Band Point\n// The row (white, takes the click).\n' + _rect(0, EW, 0, ROW_H - 1),
        'PF Divider Point': '// PF Divider Point\n// The 1 px line under each row.\n' + _rect(0, EW, ROW_H - 1, ROW_H),
        'PF Dot Point': '// PF Dot Point\n// Platform dot, 8 px, rounded.\n' + _rounded(COL['dot'] - 4, 8, mid - 4, mid + 4, 2),
        'PF Pill Point': ('// PF Pill Point\n// Incremental flag pill, fully rounded, only on flagged rows.\n'
                          'IF NOT ISNULL([PF Pill State]) THEN '
                          + _rounded(COL['pill'], 'CASE [PF Pill Text] ' + ' '.join(f'WHEN {_q(p)} THEN {w}' for p, w in pill_w.items()) + ' ELSE 0 END',
                                     mid - 8, mid + 8, 8) + ' END'),
        'PF Pill Text Point': ('// PF Pill Text Point\n// Middle of the pill.\nMAKEPOINT(0, ('
                               + str(COL['pill']) + ' + (CASE [PF Pill Text] '
                               + ' '.join(f'WHEN {_q(p)} THEN {w / 2:g}' for p, w in pill_w.items()) + f' ELSE 0 END) - {EW / 2:g}) / 100)'),
    }
    heads = [('MODEL', COL['name'] - 15, 'l'), ('BUILT AS', COL['built'], 'l'), ('AVG RUNTIME', COL['runtime'], 'r'),
             ('7D VS 28D', COL['trend'], 'r'), ('LARGEST BUILD', COL['rows'], 'r'), ('COST', COL['cost'], 'r')]
    hp = (EW, HEAD_H)
    f['PF Heading'] = ('// PF Heading\n// Column titles of the most expensive models table, one date row each.\nCASE [day_index]\n'
                       + '\n'.join(f'WHEN {i} THEN "{h}"' for i, (h, _, _) in enumerate(heads)) + '\nEND')
    f['PF Heading Point'] = ('// PF Heading Point\n// Middle of a column title (left or right-aligned, measured by the build).\nCASE [day_index]\n'
                             + '\n'.join(f'WHEN {i} THEN MAKEPOINT(0, ({(x + SH.text_width(h, 7, True) / 2) if a == "l" else (x - SH.text_width(h, 7, True) / 2):.1f}'
                                         f' - {hp[0] / 2:g}) / 100)' for i, (h, x, a) in enumerate(heads)) + '\nEND')
    t = {n: SP_MEA for n in f if n.endswith('Point')}
    t.update({n: S_DIM for n in f if n not in t})
    return f, t


PACK_TYPES = {  # calc pack section 9 calcs this tab reads
    'Average Cost Per Day': R_MEA, 'Cost Per Day Snowflake': R_MEA, 'Cost Per Day Databricks': R_MEA,
    'Cost Per Day Redshift': R_MEA, 'Model Avg Runtime (Period)': R_MEA, 'Model Runtime Label': S_MEA,
    'Model Cost (Period)': R_MEA, 'Is Model': B_DIM, 'Incremental Candidate Day': B_DIM, 'Is Incremental Candidate': B_DIM,
    'Is Switched Candidate': B_DIM, 'Switched On': ('date', 'dimension', 'ordinal'), 'Open Incremental Candidates': I_MEA,
    'Switched Candidate Text': S_DIM, 'Open Candidate Text': S_DIM, 'Product Cost Label Tag': S_DIM,
}
NEW = {
    'Product Cost Track': ('// Product Cost Track\n// Where each cost label starts, just past the longest bar (as the Why runs failed counts).\n'
                           '// Table calc along display_name and the unregistered tag.\nWINDOW_MAX([Product Cost (Period)]) * 1.14'),
    'Is Top Product Cost': ('// Is Top Product Cost\n// The 12 data products that cost most in the window. Table calc filter (True).\n'
                            'RANK_UNIQUE([Product Cost (Period)]) <= 12'),
}
_f, _t = dict(NEW), {**PACK_TYPES, 'Product Cost Track': R_MEA, 'Is Top Product Cost': ('boolean', 'measure', 'nominal')}
for fn in (combo_calcs, kpi_calcs, table_calcs):
    a, b = fn()
    _f.update(a)
    _t.update(b)
CALCS.add(formulas=_f, types=_t, table_calc={'Product Cost Track': 'display_name', 'Is Top Product Cost': 'display_name'})


# ================================================================ sheets

def _title(t):
    return [run(t, 8, INK3, SEMI), run(NL, 8, INK3)]


def kpi_sheets() -> list[Sheet]:
    day, node = R('Is Platform Match Day'), R('Is Platform Match Node')
    per_day = [run('AVERAGE PER DAY', 8, INK3, SEMI), run(NL, 8, INK3), run(R('Average Cost Per Day'), 18, NAVY, SEMI), run(NL, 8, INK3)]
    for i, p in enumerate(PLAT_NAME.values()):
        if i:
            per_day.append(run(R('PF Platform Separator', 'attr'), 8, INK3))
        per_day += [run(R(f'PF {p} Name', 'attr'), 8, PLAT[p.lower()], SEMI), run(R(f'PF {p} Per Day Text'), 8, INK3)]
    slow_name = R('node_name', 'attr')
    cands = [run('INCREMENTAL CANDIDATES', 8, INK3, SEMI), run(NL, 8, INK3),
             run(R('Open Incremental Candidates'), 18, NAVY, SEMI), run(' open', 9, INK3), run(NL, 8, INK3),
             run(R('PF Switched Text'), 8, GOOD_INK, SEMI), run(R('PF Open Text'), 8, CRIT_INK, SEMI),
             run(R('PF No Candidates Text'), 8, INK3)]
    tip = lambda t, d: [run(t, 7, INK3, SEMI), run(NL, 7, INK3), run(d, 9, INK1, BOOK)]
    return [
        Sheet('PF Average Per Day KPI', filters=[day], formats={R('Average Cost Per Day'): USD},
              panes=label_pane(text=[r['_ref'] for r in per_day if '_ref' in r], valign='top', label=per_day,
                               tooltip=tip('AVERAGE PER DAY', 'Warehouse cost in the window divided by its days, then by platform.'))),
        Sheet('PF Slowest Model KPI', filters=[R('Is Model'), R('Is PF Slowest Model')],
              panes=label_pane(valign='top', text=[slow_name, R('Model Runtime Label'), R('PF Slowest Trend Text')], label=[
                  run('SLOWEST MODEL', 8, INK3, SEMI), run(NL, 8, INK3), run(slow_name, 14, NAVY, SEMI), run(NL, 8, INK3),
                  run(R('Model Runtime Label'), 8, INK3), run(' average run', 8, INK3), run(R('PF Slowest Trend Text'), 8, INK3)],
                  tooltip=tip('SLOWEST MODEL', 'The model with the longest average successful run in the window, and its last 7 days against the 28 before.'))),
        Sheet('PF Incremental Candidates KPI', filters=[R('Is Model'), node],
              panes=label_pane(valign='top', text=[r['_ref'] for r in cands if '_ref' in r], label=cands,
                               tooltip=tip('INCREMENTAL CANDIDATES', 'Full-refresh tables over 10M rows whose runtime ran more than 25% above '
                                           'its 28-day average in the window. Open ones are still built as tables.'))),
    ]


def _axis_width(y):
    return [f"            <format attr='width' field='{y.ref}' value='{AXIS_W}' />"]


def _events(x):
    """The three moves as constant reference lines on the day axis, labelled at the top (IronViz reference)."""
    rl, style = [], []
    for i, (day, label, colour, side) in enumerate(EVENTS):
        rid = f'refline{i}'
        rl.append(dict(id=rid, axis=x, value=(ASOF - dt.date.fromisoformat(day)).days + 0.5, label=label, z=i + 1))
        style += [f"            <format attr='stroke-size' id='{rid}' value='1' />",
                  f"            <format attr='stroke-color' id='{rid}' value='{colour}' />",
                  f"            <format attr='color' id='{rid}' value='{colour}' />",
                  f"            <format attr='font-size' id='{rid}' value='7' />",
                  f"            <format attr='vertical-align' id='{rid}' value='top' />",
                  f"            <format attr='text-align' id='{rid}' value='{side}' />",
                  f"            <format attr='fill-above' id='{rid}' value='#00000000' />",
                  f"            <format attr='fill-below' id='{rid}' value='#00000000' />",
                  f"            <format attr='background-color' id='{rid}' value='#ffffff00' />"]
    return rl, style


def cost_sheet() -> Sheet:
    x, band, cost = R('Days Back Mid'), R('PF Cost Band'), R('Warehouse Cost - Trend')
    plat = R('Platform On Day Name')   # palette registered by the Freshness tab
    tip = [run(R('Tooltip Day Text'), 9, INK1, SEMI), run(NL, 7, INK3), run(R(plat.name, 'attr'), 7, INK3, SEMI), run('   ', 7, INK3),
           run(cost, 9, NAVY, SEMI)]
    rl, rstyle = _events(x)
    return Sheet('PF Cost by Platform Bar', cols=[x], rows=[(band, cost)], filters=[R('Is Platform Match Day')],
                 hide=[x, cost], sync=[cost], fixed={x: COST_X}, formats={band: USD, cost: USD},
                 extra={'axis': _axis_style(band, fmt=USD) + _axis_width(band), 'refline': rstyle},
                 panes=[Pane('Bar', label_show=False),
                        Pane('Bar', axis=band, mark_color=BAND, size=1.9890055656433105, label_show=False),
                        Pane('Bar', axis=cost, color=plat, size=1.25, label_show=False, tooltip=tip, reflines=rl)])


def runtime_sheet() -> Sheet:
    x, band, line = R('Days Back Mid'), R('PF Runtime Band'), R('PF Runtime Line')
    key, name, end = R('PF Line Key'), R('node_name'), R('PF Runtime End Name')
    color_map(key, {'"Top change"': ACCENT, '"Other"': '#b9c0c7'})
    tip = [run(R('node_name', 'attr'), 9, INK1, SEMI), run(NL, 7, INK3), run(R('Tooltip Day Text'), 7, INK3, SEMI), run('   ', 7, INK3),
           run(line, 9, NAVY, SEMI), run(' min average run', 9, INK3)]
    return Sheet('PF Slowest Models Runtime Line', cols=[x], rows=[(band, line)], filters=[R('Is PF Slowest Six')],
                 hide=[x, line], sync=[line], fixed={x: RT_X}, formats={band: MINS, line: 'n#,##0.0;-#,##0.0'},
                 extra={'axis': _axis_style(band, fmt=MINS) + _axis_width(band)},
                 panes=[Pane('Bar', label_show=False),
                        Pane('Bar', axis=band, mark_color=BAND, size=1.9890055656433105, label_show=False),
                        # the name only on today's point, to its right (v33b: line-end labels with line-first did
                        # not show); overlapping names are hidden, as the prototype shows three of six
                        Pane('Line', axis=line, color=key, size=0.4, lod=[name], text=[end], tooltip=tip, cull=True,
                             label=[run(end, 7, INK3)], align='right')])


def axis_strip(name, x_fixed, label='Axis Date Label') -> Sheet:
    """Date labels under a chart, on its day axis; the clear value axis has the chart's fixed width, so they line up."""
    x, anchor = R('Days Back Mid'), R('PF Axis Anchor')
    lab = R(label)
    return Sheet(name, cols=[x], rows=[anchor], hide=[x], fixed={x: x_fixed, anchor: (0, 1)}, tooltip=False,
                 extra={'axis': _axis_style(anchor, False) + _axis_width(anchor)},
                 panes=label_pane(text=[lab], label=[run(lab, 8, INK3)], align='center'))


def _a(n):
    return R(n, 'attr')


def table_sheets() -> list[Sheet]:
    """The prototype's table as a pixel canvas, one 730 x ROW_H pane per model in cost order: row, divider, platform
    dot, texts at measured widths, live numbers right-aligned at their columns, and the incremental pill."""
    key = R('node_id (dim_nodes.csv)')
    order = R('PF Cost Rank', kind='ok')
    path = R('Node Path Index', kind='ok')
    color_map(R('PF Dot Key'), {f'"{k}"': v for k, v in PLAT.items()})
    color_map(R('PF Pill State'), {'"Switched"': GOOD_TINT, '"Open"': WARN_TINT})
    clicks = [R('node_key'), *[R(f) for f, _ in PANEL_WRITES]]
    tip = [run(_a('node_name'), 9, INK1, SEMI), run(NL, 7, INK3),
           run('PLATFORM   ', 7, INK3, SEMI), run(_a('Platform Name'), 9, NAVY, SEMI), run(NL, 7, INK3),
           run('BUILT AS   ', 7, INK3, SEMI), run(_a('materialization_now'), 9, NAVY, SEMI), run(NL, 7, INK3),
           run('AVERAGE RUN   ', 7, INK3, SEMI), run(R('Model Runtime Label'), 9, NAVY, SEMI), run(NL, 7, INK3),
           run('BUILD COST IN PERIOD   ', 7, INK3, SEMI), run(R('Model Build Cost (Period)'), 9, NAVY, SEMI), run(NL, 7, INK3),
           run('CLICK TO OPEN ITS LINEAGE', 7, INK3, SEMI)]

    def poly(title, point, colour=None, mark=None, inert=True, lod=(), tooltip=None):
        return Pane('Polygon', title=title, inert=inert, color=colour, mark_color=mark, path=path, label_show=False,
                    lod=[R(point, 'clct'), key, *lod], pane_size=ROW, tooltip=tooltip)

    def cell(title, point, runs, align='center'):
        return label_pane(title=title, inert=True, text=[r['_ref'] for r in runs if '_ref' in r], label=runs, align=align,
                          valign='center', lod=[R(point, 'clct'), key], pane_size=ROW)
    cost = R('Model Build Cost (Period)')
    layers = [
        poly('Row', 'PF Band Point', mark=CARD, inert=False, lod=clicks, tooltip=tip),
        poly('Divider', 'PF Divider Point', mark=LINE_SOFT),
        poly('Dot', 'PF Dot Point', colour=R('PF Dot Key')),
        poly('Pill', 'PF Pill Point', colour=R('PF Pill State')),
        cell('Name', 'PF Name Point', [run(_a('PF Name Text'), 8, INK1)]),
        cell('Built as', 'PF Built As Point', [run(_a('PF Built As Text'), 8, INK2)]),
        cell('Was table', 'PF Was Table Point', [run(_a('PF Was Table Text'), 8, INK3)]),
        cell('Runtime', 'PF Runtime Point', [run(R('Model Runtime Label'), 8, INK1)], 'right'),
        cell('Trend', 'PF Trend Point', [run(R('Runtime Change Up Text'), 8, CRIT_INK, SEMI), run(R('Runtime Change Down Text'), 8, GOOD_INK, SEMI),
                                         run(R('Runtime Change Flat Text'), 8, INK2)], 'right'),
        cell('Rows', 'PF Rows Point', [run(_a('PF Rows Text'), 8, INK1)]),
        cell('Cost', 'PF Cost Point', [run(cost, 8, INK1, SEMI)], 'right'),
        cell('Pill text', 'PF Pill Text Point', [run(_a('PF Pill Good Text'), 7, GOOD_INK, SEMI), run(_a('PF Pill Warn Text'), 7, WARN_INK, SEMI)]),
    ]
    table = _grid(Sheet('PF Most Expensive Models Table', rows=[Cross([Nest([order, key]), LAT])], cols=[LON],
                        filters=[R('Is PF Top Cost Model')], hide=[order, key], layers=True, no_basemap=True, zoom=None,
                        formats={cost: USD}, panes=[Pane('Automatic', lod=[key], pane_size=ROW), *layers]), ROW)
    hp = (EW, HEAD_H)
    header = _grid(Sheet('PF Most Expensive Models Header', rows=[LAT], cols=[LON], filters=[R('Is PF Heading Row')],
                         layers=True, no_basemap=True, zoom=None, tooltip=False,
                         panes=[Pane('Automatic', pane_size=hp),
                                label_pane(title='Titles', inert=True, text=[_a('PF Heading')], label=[run(_a('PF Heading'), 7, INK3, SEMI)],
                                           align='center', lod=[R('PF Heading Point', 'clct'), R('day_index')], pane_size=hp)]), hp)
    return [header, table]


CALCS.add(formulas={'Is PF Heading Row': '// Is PF Heading Row\n// The first six days of the date table: one per column title. Put on Filters (True).\n[day_index] < 6'},
          types={'Is PF Heading Row': B_DIM})


def product_sheet() -> Sheet:
    name, tag = R('display_name'), R('Product Cost Label Tag')
    cost, track, top = R('Product Cost (Period)'), R('Product Cost Track'), R('Is Top Product Cost')
    for r in (track, top):
        r.tc_order = [name, tag]   # rank and track across both row fields, so the tag does not split them
    label = [f"            <format attr='font-size' field='{name.ref}' value='8' />",
             f"            <format attr='color' field='{name.ref}' value='{INK1}' />",
             f"            <format attr='text-align' field='{name.ref}' value='left' />",
             f"            <format attr='font-size' field='{tag.ref}' value='7' />",
             f"            <format attr='color' field='{tag.ref}' value='{WARN_INK}' />",
             f"            <format attr='text-align' field='{tag.ref}' value='left' />"]
    a = lambda n: R(n, 'attr')
    tip = [run(a('display_name'), 9, INK1, SEMI), run(NL, 7, INK3),
           run('COST IN PERIOD   ', 7, INK3, SEMI), run(cost, 9, NAVY, SEMI), run(NL, 7, INK3),
           run('USAGE   ', 7, INK3, SEMI), run(R('Product Uses (Period)'), 9, NAVY, SEMI), run(' ', 9, INK3), run(a('Uses Unit Label'), 9, INK3), run(NL, 7, INK3),
           run('COST PER USE   ', 7, INK3, SEMI), run(R('Cost Per Use'), 9, NAVY, SEMI)]
    return Sheet('PF Cost per Data Product Bar', rows=[name, tag], cols=[(cost, track)],
                 filters=[R('Is Platform Match Node'), top], hide=[track, cost], sync=[track],
                 header_width={name: 196, tag: 70}, sorts=[(name, 'DESC', cost)], extra={'label': label}, divider='rows',
                 formats={cost: USD, R('Product Uses (Period)'): 'n#,##0;-#,##0', R('Cost Per Use'): 'c"$"#,##0.00;-"$"#,##0.00'},
                 panes=[Pane('Bar', label_show=False),
                        Pane('Bar', axis=cost, mark_color=ACCENT, size=0.3, label_show=False, tooltip=tip),
                        # Middle Right at 9 pt, as the Why runs failed counts (GB, v27)
                        label_pane(axis=track, text=[cost], label=[run(cost, 9, INK1, SEMI)], align='right', tooltip=tip)])


def sheets() -> list[Sheet]:
    return (kpi_sheets() + [cost_sheet(), axis_strip('PF Cost Axis', COST_X), runtime_sheet(), axis_strip('PF Runtime Axis', RT_X, 'Axis Month Label')]
            + table_sheets() + [product_sheet()])


# ================================================================ dashboard content (build plan 3.7)

def _legend(items):
    rs = []
    for i, (label, colour) in enumerate(items):
        rs += [run('■ ', 8, colour), run(label + ('     ' if i < len(items) - 1 else ''), 8, INK2)]
    return rs


def content() -> Z:
    widths = [318, 317, 318, 317]   # card widths; the 7 px margins (14 px gaps) sit outside: 1270 + 42 = 1312
    names = [('Warehouse Cost', 'HO Warehouse Cost KPI'), ('Average Per Day', 'PF Average Per Day KPI'),
             ('Slowest Model', 'PF Slowest Model KPI'), ('Incremental Candidates', 'PF Incremental Candidates KPI')]
    kpis = []
    for i, ((n, ws), w) in enumerate(zip(names, widths)):
        margins = {}
        if i > 0:
            margins['left'] = 7
        if i < 3:
            margins['right'] = 7
        kpis.append(card(f'PF KPI {n} Card', [sheet(ws)], fixed=w, pad=(12, 14, 10, 14), margins=margins))
    cost = card('PF Cost Card', fixed=MAIN_W, margins={'right': 7}, kids=[
        Z('horz', friendly='PF Cost Header', fixed=44, kids=[
            card_header('Cost by platform, per day', 'Estimated USD. Redshift winds down as marketing models move to Snowflake.', None),
            text(_legend([(v, PLAT[k]) for k, v in PLAT_NAME.items()]), fixed=230, **{'text-align': 'right'})]),
        sheet('PF Cost by Platform Bar'),
        sheet('PF Cost Axis', 16)])
    runtime = card('PF Runtime Card', margins={'left': 7}, kids=[
        card_header('Runtime of the six slowest models', 'Average successful run per day. The highlighted line is the biggest change.'),
        sheet('PF Slowest Models Runtime Line'),
        sheet('PF Runtime Axis', 16)])
    expensive = card('PF Expensive Card', fixed=MAIN_W, margins={'right': 7}, kids=[
        card_header('Most expensive models in this period',
                    'Dot shows the platform. Flag shows full-refresh tables over 10M rows whose runtime grew more than 25%. '
                    'Click a row to open its lineage.'),
        sheet('PF Most Expensive Models Header', HEAD_H),
        blank(1, LINE),   # the prototype's line under the column titles
        sheet('PF Most Expensive Models Table')])
    product = card('PF Product Cost Card', margins={'left': 7}, kids=[
        card_header('What each data product costs to keep running',
                    'Upstream build cost split evenly across the exposures each model feeds, plus the product\'s own queries', 58),
        sheet('PF Cost per Data Product Bar')])
    return Z('vert', friendly='PF Content', style=CONTENT_PAD, kids=[
        Z('horz', friendly='PF KPI Row', fixed=KPI_H, kids=kpis),
        Z('horz', friendly='PF Middle Row', fixed=MID_H, style={'margin-top': '14'}, kids=[cost, runtime]),
        # the last row is flexible, so it always reaches the bottom padding (skill: sizing)
        Z('horz', friendly='PF Bottom Row', style={'margin-top': '14'}, kids=[expensive, product])])


def check_fit(zones) -> None:
    by = {(z.name or z.friendly): z.rect for z in zones}
    _, _, zw, zh = by['PF Most Expensive Models Table']
    need = (EW, ROW_H * TOP_N)
    assert need[0] <= zw and need[1] <= zh, f'PF Most Expensive Models Table: needs {need}, zone is {zw:.0f} x {zh:.0f}'
    _, _, zw, zh = by['PF Most Expensive Models Header']
    assert EW <= zw and HEAD_H <= zh, f'PF Most Expensive Models Header: needs {EW} x {HEAD_H}, zone is {zw:.0f} x {zh:.0f}'
    _, y, _, h = by['PF Bottom Row']
    end = 1000 - int(CONTENT_PAD['padding-bottom'])
    assert abs(y + h - end) < 0.5, f'PF rows end at {y + h:.0f}, content ends at {end}'


ACTIONS = [  # (sheet, source Ref factory, parameter, caption)
    ('PF Most Expensive Models Table', lambda: R('node_id (dim_nodes.csv)'), 'p_selected_node', 'PF Model Select Node'),
    ('PF Most Expensive Models Table', lambda: R('node_key'), 'p_selected_node_key', 'PF Model Select Node Key'),
    *[('PF Most Expensive Models Table', (lambda f=f: R(f)), param, f'PF Model Set {param}') for f, param in PANEL_WRITES],
]
# a model row opens the Lineage explorer for now; Blast radius once that tab exists (GB, 24 Oct)
NAV_ACTIONS = [('PF Most Expensive Models Table', 'Lineage explorer', 'Go to Lineage from PF Most Expensive Models Table')]
DEHIGHLIGHT = ['PF Most Expensive Models Table']
