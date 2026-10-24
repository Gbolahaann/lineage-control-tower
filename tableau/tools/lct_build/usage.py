"""Tab 5, Usage & adoption (US): calc pack section 10, build plan 3.8.

GB's choices (24 Oct): the cost against usage scatter native on log axes, with the retire zone as an area layer; the
two tables as canvases sized to fit without a scroll bar; the failures-per-day sparklines kept, drawn on the canvas;
table numbers worked out by the build per period, so every one sits exactly at its column (the PF "$1,102" lesson).

- Scatter: Product Cost against Product Uses, both axes logarithmic, one dot per data product coloured by the
  prototype's key (built by hand, AI-built, unregistered, retire candidate). The retire zone (under 10 uses per 30
  days and over $5 per use) is an area through the products in cost order at min(10 uses, cost / 5), so its diagonal
  and flat edges are the prototype's; it spans the cheapest to the dearest product.
- Consumption by consumer type: four small multiples, declared products only, the window's days, each with its own
  axis and its total at the top right.
- Data products ranked by use: the 19 most used, then any retire candidate or unregistered product below them
  (GB: "Top 19 + pinned flags"), 20 px rows. Built tag and retire / not registered flags as polygons.
- BI semantic layer refreshes: most failures first; live objects (no Node Daily rows) at the end with "Live, no
  extract". The sparkline is a line through the day's failed refreshes (a canvas has one row per day, so a line, not
  bars), grey for the 90 days and red inside the window, each object on its own scale.
"""

from __future__ import annotations

import collections
import csv
import datetime as dt

from . import shapes as SH
from .core import (PANEL_WRITES, ACCENT, AI_INK, B_DIM, BOOK, CALCS, CARD, CRIT, CRIT_INK, CRIT_TINT, GOOD_INK, I_DIM,
                   I_MEA, INK1, INK2, INK3, LAT, LINE, LINE_SOFT, LON, NAVY, NL, R_MEA, S_DIM, S_MEA, SEMI, SP_MEA, WARN,
                   WARN_INK, WARN_TINT, Cross, Nest, Pane, R, Sheet, Z, blank, card, card_header, color_map, label_pane,
                   run, sheet, text)
from .lineage import _fit, _grid, _q
from .shell import CONTENT_H, CONTENT_PAD

P = 'US'
ROOT = SH.ROOT
M = ROOT / 'data' / 'marts'
NODES = {r['node_id']: r for r in csv.DictReader(open(M / 'dim_nodes.csv', encoding='utf-8'))}
ORDER = list(NODES)                                # dim_nodes order (the prototype's tie-break)
PERIODS, PLATFORMS = (7, 30, 90), ('All', 'snowflake', 'databricks', 'redshift')
ASOF = dt.date(2026, 10, 19)
DAYS = 90

# ---------------------------------------------------------------- geometry (content 1312 x CONTENT_H)
TOP_H = 330
HALF = (1312 - 14) // 2                         # 649: the top cards, a 7 px margin on the inner side
SEM_W = 643                                     # semantic card (GB, v36); 7 px margin-left outside
RANK_W = 1312 - SEM_W - 7 - 7                   # 655: the ranked card takes the rest
RCW = RANK_W - 2 * 16 - 2 - SH.SLACK - 18       # 599: ranked canvas, room for its own scroll bar (GB, v36)
SCW = SEM_W - 2 * 16 - 2 - SH.SLACK             # 605: semantic canvas
HEAD_H = 22
ROWS_AVAIL = CONTENT_H - TOP_H - 14 - 2 - 28 - 44 - HEAD_H - 1 - SH.SLACK   # height left for table rows
ROW_H = 27                                      # the prototype's rows; the ranked table scrolls (GB, v36)
GAP = 9                                         # between table columns
SORTS = ('Uses', 'Change', 'Cost per use', 'Daily consumers')
BY_HAND_BG, AI_BG, AI_LINE, OBS_LINE = '#f5f5f3', '#eef0fb', '#d9dcf4', '#f3ddb4'
ET_NAME = {'dashboard': 'Dashboard', 'notebook': 'Notebook', 'ml': 'ML model', 'data_app': 'Data app', 'agent': 'AI agent',
           'data_hub': 'Data hub'}
BI_NAME = {'tableau': 'Tableau', 'sigma': 'Sigma', 'power_bi': 'Power BI'}
UNIT = {'view': 'views', 'query': 'queries', 'app_session': 'sessions', 'agent_call': 'calls'}
TYPES = [('view', 'View', 'Dashboard and hub views'), ('query', 'Query', 'Notebook and model queries'),
         ('app_session', 'App Session', 'Data app sessions'), ('agent_call', 'Agent Call', 'AI agent calls')]
USD = 'c"$"#,##0;-"$"#,##0'


def _num(v):
    return None if v in ('', None) else float(v)


def _in_plat(n, plat):
    return plat == 'All' or f'|{plat}|' in n['platform_filter_values']


def _dur(s):
    """The prototype's fDur."""
    if s is None:
        return '-'
    return f'{s:.0f}s' if s < 60 else f'{s / 60:.1f} min' if s < 3600 else f'{s / 3600:.1f} h'


# ================================================================ the build's tables, per period and platform

def _ranked():
    """Uses, change, daily consumers and cost per use per product and period, and the rows per combination."""
    days = collections.defaultdict(dict)
    for r in csv.DictReader(open(M / 'mart_exposure_daily.csv', encoding='utf-8')):
        days[r['exposure_id']][(ASOF - dt.date.fromisoformat(r['date'])).days] = r
    vals, rows = {}, {}
    for per in PERIODS:
        for e, d in days.items():
            win = [d[b] for b in range(per) if b in d]
            prior = [d[b] for b in range(per, 2 * per) if b in d]
            ev = sum(_num(r['events']) or 0 for r in win)
            pev = sum(_num(r['events']) or 0 for r in prior) if 2 * per <= DAYS else None
            cost = sum(_num(r['allocated_cost_usd']) or 0 for r in win)
            uc = [_num(r['unique_consumers']) or 0 for r in win]
            n = NODES[e]
            cpu = cost / ev if ev else None
            retire = ev / per * 30 < 10 and (cpu is None or cpu > 5) and n['is_declared'] == 'True'
            vals[(per, e)] = dict(ev=ev, ch=(ev - pev) / pev if pev else None, cons=sum(uc) / len(uc) if uc else 0,
                                  cpu=cpu, retire=retire, unreg=n['is_declared'] != 'True')
        # every product, in the order p_us_sort asks for (ties and missing values by uses)
        order = {'Uses': lambda v: (0, -v['ev']),
                 'Change': lambda v: (v['ch'] is None, v['ch'] if v['ch'] is not None else 0, -v['ev']),   # biggest fall first
                 'Cost per use': lambda v: (v['cpu'] is None, -(v['cpu'] or 0), -v['ev']),
                 'Daily consumers': lambda v: (0, -v['cons'], -v['ev'])}
        for plat in PLATFORMS:
            es = [e for e in days if _in_plat(NODES[e], plat)]
            for srt, fn in order.items():
                rows[(per, plat, srt)] = sorted(es, key=lambda e: fn(vals[(per, e)]))
    return vals, rows


def _semantic():
    days = collections.defaultdict(dict)
    for r in csv.DictReader(open(M / 'mart_node_daily.csv', encoding='utf-8')):
        if NODES[r['node_id']]['resource_type'] == 'semantic':
            days[r['node_id']][(ASOF - dt.date.fromisoformat(r['date'])).days] = r
    sems = [k for k in ORDER if NODES[k]['resource_type'] == 'semantic']
    vals, rows = {}, {}
    for per in PERIODS:
        for k in sems:
            win = [days[k][b] for b in range(per) if b in days.get(k, {})]
            ok = sum(_num(r['refresh_ok']) or 0 for r in win)
            fl = sum(_num(r['refresh_failed']) or 0 for r in win)
            durs = [_num(r['avg_refresh_sec']) for r in win if _num(r['avg_refresh_sec']) is not None]
            vals[(per, k)] = dict(live=k not in days, rate=ok / (ok + fl) if ok + fl else None, fl=fl,
                                  dur=sum(durs) / len(durs) if durs else None)
        for plat in PLATFORMS:
            ks = [k for k in sems if _in_plat(NODES[k], plat)]
            ks.sort(key=lambda k: (-vals[(per, k)]['fl'], vals[(per, k)]['rate'] if vals[(per, k)]['rate'] is not None else 1))
            rows[(per, plat)] = ks
    return vals, rows


RANK_VALS, RANK_ROWS = _ranked()
SEM_VALS, SEM_ROWS = _semantic()
MAX_RANKED = max(len(v) for v in RANK_ROWS.values())
SEM_ROW_H = min(29, ROWS_AVAIL // max(len(v) for v in SEM_ROWS.values()))   # the prototype's 29 px
ROW, SEM_ROW = (RCW, ROW_H), (SCW, SEM_ROW_H)
KEY = 'STR([p_period]) + "|" + [p_platform] + "|" + [node_id (dim_nodes.csv)]'
RKEY = 'STR([p_period]) + "|" + [p_platform] + "|" + [p_us_sort] + "|" + [node_id (dim_nodes.csv)]'
COMBO = 'STR([p_period]) + "|" + [p_platform]'
PKEY = 'STR([p_period]) + "|" + [node_id (dim_nodes.csv)]'
NODE = '[node_id (dim_nodes.csv)]'


def _case(expr, values, default='NULL', quote=True):
    body = '\n'.join(f'WHEN {_q(k) if isinstance(k, str) else k} THEN {_q(v) if quote else v}' for k, v in values.items())
    return f'CASE {expr}\n{body}\nELSE {default}\nEND'


def _calc(name, why, body):
    return f'// {name}\n// {why}\n{body}'


# ---------------------------------------------------------------- texts and columns

def _uses(v, e):
    unit = UNIT.get(NODES[e]['consumption_type'], 'events')
    return f'{v["ev"]:,.0f}', ' ' + (unit[:-1] if v['ev'] == 1 else unit)


def _change(v):
    c = v['ch']
    if c is None:
        return 'flat', '-'
    t = ('▲ ' if c > 0 else '▼ ') + f'{abs(c) * 100:.0f}%'
    return ('up' if c > 0.1 else 'down' if c < -0.1 else 'flat'), t


def _type(e):
    n = NODES[e]
    return BI_NAME.get(n['bi_tool']) or ET_NAME.get(n['exposure_type'], '')


def _cpu(v):
    return '-' if v['cpu'] is None else f'${v["cpu"]:,.2f}'


def _flag(v):
    return '✕  Retire?' if v['retire'] else 'Unregistered' if v['unreg'] else None


W8 = lambda s, b=False: SH.text_width(s, 8, b)
W7 = lambda s, b=False: SH.text_width(s, 7, b)
SHOWN = sorted({(per, e) for (per, _p, _s), es in RANK_ROWS.items() for e in es})


def _names(cap):
    # "Unregistered: " is dropped from the name: the flag column says it (room for the full names)
    return {e: _fit(NODES[e]['display_name'].replace('Unregistered: ', ''), cap, 8, True) for e in {e for _p, e in SHOWN}}


def _ranked_cols(names):
    """Left edges (name, type, built tag, flag) and right edges (numbers), from the widest text of each column."""
    texts = {
        'uses': [W8(''.join(_uses(RANK_VALS[k], k[1]))) for k in SHOWN],
        'change': [W8(_change(RANK_VALS[k])[1], True) for k in SHOWN],
        'cons': [W8(f'{RANK_VALS[k]["cons"]:.1f}') for k in SHOWN],
        'cpu': [W8(_cpu(RANK_VALS[k])) for k in SHOWN],
    }
    # shorter titles than the prototype's (its table scrolled sideways): "Daily consumers" and "Cost per use" spelt out in the tooltip
    heads = {'uses': 'USES', 'change': 'CHANGE', 'cons': 'CONSUMERS', 'cpu': 'COST/USE'}
    x = {'name': 8, 'type': 8 + max(W8(t, True) for t in names.values()) + GAP}
    x['built'] = x['type'] + max(W8(_type(e)) for e in names) + GAP
    tag_w = max(W7(t) for t in ('AI-built', 'By hand')) + 12
    edge = x['built'] + tag_w
    for c in ('uses', 'change', 'cons', 'cpu'):
        edge += GAP + max(max(texts[c]), W7(heads[c], True))
        x[c] = edge
    x['flag'] = edge + GAP
    flag_w = max(W7(t, True) for t in ('✕  Retire?', 'Unregistered')) + 14
    return x, tag_w, heads, x['flag'] + flag_w


def _fit_names():
    """The widest name column that still lets the table fit its canvas."""
    for cap in range(170, 100, -2):
        names = _names(cap)
        x, tag_w, heads, end = _ranked_cols(names)
        if end <= RCW - 2:
            return names, x, tag_w, heads
    raise AssertionError('US ranked table does not fit')


NAMES, RCOL, TAG_W, RHEADS = _fit_names()


def _xmax():
    """Right edge of the scatter's cost axis per period and platform: the power of ten above the dearest product."""
    import math
    cost = collections.defaultdict(float)
    for r in csv.DictReader(open(M / 'mart_exposure_daily.csv', encoding='utf-8')):
        b = (ASOF - dt.date.fromisoformat(r['date'])).days
        for per in PERIODS:
            if b < per:
                cost[(per, r['exposure_id'])] += _num(r['allocated_cost_usd']) or 0
    out = {}
    for per in PERIODS:
        for plat in PLATFORMS:
            cs = [c for (p, e), c in cost.items() if p == per and _in_plat(NODES[e], plat) and RANK_VALS[(per, e)]['ev'] > 0 and c > 0]
            out[(per, plat)] = 10 ** math.ceil(math.log10(max(cs))) if cs else 1000
    return out


XMAX = _xmax()


def _sem_cols():
    sems = [k for k in ORDER if NODES[k]['resource_type'] == 'semantic']
    keys = [(p, k) for p in PERIODS for k in sems]
    x = {'name': 8}
    x['tool'] = 8 + max(W8(NODES[k]['node_name']) for k in sems) + GAP
    x['mode'] = x['tool'] + max(W8(BI_NAME[NODES[k]['bi_tool']]) for k in sems) + GAP
    edge = x['mode'] + max(W8(NODES[k]['connection_type']) for k in sems)
    heads = {'succ': 'SUCCESS', 'fail': 'FAILED', 'avg': 'AVG REFRESH'}
    cells = {'succ': [W8(_succ(SEM_VALS[q])[1], True) for q in keys], 'fail': [W8(f'{SEM_VALS[q]["fl"]:.0f}') for q in keys],
             'avg': [W8(_dur(SEM_VALS[q]['dur'])) for q in keys]}
    for c in ('succ', 'fail', 'avg'):
        edge += GAP + max(max(cells[c]), W7(heads[c], True))
        x[c] = edge
    x['spark'] = edge + GAP + 4
    x['spark_w'] = SCW - 6 - x['spark']
    assert x['spark_w'] >= 90, f'US semantic sparkline only {x["spark_w"]:.0f} px'
    return x, heads


def _succ(v):
    if v['rate'] is None:
        return 'normal', '-'
    t = f'{v["rate"] * 100:.1f}%'
    return ('low' if v['rate'] < 0.98 else 'normal'), t


SCOL, SHEADS = _sem_cols()


# ================================================================ calcs

def _at(x, pane):
    return f'MAKEPOINT(0, ({x:.1f} - {pane[0] / 2:g}) / 100)'


def _centre_case(expr, centres, pane):
    """A point per key, centred where the build measured the text."""
    return f'MAKEPOINT(0, ({_case(expr, {k: f"{c:.1f}" for k, c in centres.items()}, "0", False)} - {pane[0] / 2:g}) / 100)'


def _rounded(idx, x0, w, y0, y1, r, pane, cond=None):
    """Rounded rectangle from a 0 to 87 path index, 22 points round each corner (build techniques, section 6)."""
    pw, ph = pane
    k = f'INT({idx} / 22)'
    th = f'RADIANS({k} * 90 + ({idx} % 22 + 0.5) * 90 / 22)'
    cx, cy, h = f'(({x0}) + ({w}) / 2)', (y0 + y1) / 2, y1 - y0
    dx = f'((CASE {k} WHEN 1 THEN -1 WHEN 2 THEN -1 ELSE 1 END) * (({w}) / 2 - {r}) + {r} * COS({th}))'
    dy = f'((IF {k} < 2 THEN 1 ELSE -1 END) * {h / 2 - r:g} + {r} * SIN({th}))'
    pt = f'MAKEPOINT(\n    ({ph / 2 - cy:g} + {dy}) / 100,\n    ({cx} + {dx} - {pw / 2:g}) / 100\n)'
    return f'IF {cond} THEN {pt} END' if cond else pt


def ranked_calcs():
    f, t = {}, {}
    rank = {f'{p}|{pl}|{srt}|{e}': i + 1 for (p, pl, srt), es in RANK_ROWS.items() for i, e in enumerate(es)}
    f['US Use Rank'] = _calc('US Use Rank', 'Row of a data product in the ranked table, in the order p_us_sort asks for (uses, change with the\n'
                             '// biggest fall first, cost per use or daily consumers), worked out by the build per period and platform.',
                             _case(RKEY, rank, quote=False))
    f['Is US Ranked Row'] = _calc('Is US Ranked Row', 'Rows of the ranked table. Put on Filters (True).', 'NOT ISNULL([US Use Rank])')
    by = lambda fn: {f'{p}|{e}': fn(p, e) for p, e in SHOWN}
    by_text = lambda fn: {k: v for k, v in by(fn).items() if v is not None}
    pane, mid = ROW, ROW_H / 2
    texts = {
        'US Uses Number Text': ('Uses in the period, "63,682".', by(lambda p, e: _uses(RANK_VALS[(p, e)], e)[0])),
        'US Uses Unit Text': ('Its unit, grey: " calls".', by(lambda p, e: _uses(RANK_VALS[(p, e)], e)[1])),
        'US Change Up Text': ('Change against the period before, over +10%: green.',
                              by_text(lambda p, e: _change(RANK_VALS[(p, e)])[1] if _change(RANK_VALS[(p, e)])[0] == 'up' else None)),
        'US Change Down Text': ('Change below -10%: red.',
                                by_text(lambda p, e: _change(RANK_VALS[(p, e)])[1] if _change(RANK_VALS[(p, e)])[0] == 'down' else None)),
        'US Change Flat Text': ('Change within 10% either way, or "-" with no earlier period.',
                                by_text(lambda p, e: _change(RANK_VALS[(p, e)])[1] if _change(RANK_VALS[(p, e)])[0] == 'flat' else None)),
        'US Consumers Text': ('Mean daily unique consumers in the period.', by(lambda p, e: f'{RANK_VALS[(p, e)]["cons"]:.1f}')),
        'US Cost Per Use Text': ('Allocated cost / uses; "-" with no use.', by(lambda p, e: _cpu(RANK_VALS[(p, e)]))),
        'US Flag Retire Text': ('"✕  Retire?", red, on its red pill.', by_text(lambda p, e: _flag(RANK_VALS[(p, e)]) if RANK_VALS[(p, e)]['retire'] else None)),
        'US Flag Unregistered Text': ('"Unregistered", amber, on its amber tag.', by_text(lambda p, e: _flag(RANK_VALS[(p, e)]) if not RANK_VALS[(p, e)]['retire'] else None)),
    }
    for n, (why, vals) in texts.items():
        f[n] = _calc(n, why + ' Written by the build per period.', _case(PKEY, vals))
    f['US Flag Key'] = _calc('US Flag Key', 'Flag pill colour: Retire or Unregistered.',
                             _case(PKEY, by_text(lambda p, e: 'Retire' if RANK_VALS[(p, e)]['retire'] else 'Unregistered' if RANK_VALS[(p, e)]['unreg'] else None)))
    f['US Name Text'] = _calc('US Name Text', 'Data product name, cut by the build to its column.', _case(NODE, NAMES))
    f['US Type Text'] = _calc('US Type Text', 'The BI tool for dashboards, otherwise the kind of product.', _case(NODE, {e: _type(e) for e in NAMES}))
    f['US Built Text'] = _calc('US Built Text', 'Built tag: AI-built or By hand.',
                               _case(NODE, {e: 'AI-built' if NODES[e]['build_method'] == 'ai_assisted' else 'By hand' for e in NAMES}))
    f['US Built Key'] = '// US Built Key\n// Built tag colour.\n[US Built Text]'
    # points: left texts at half their measured width, numbers right-aligned at their column, all measured
    f['US Name Point'] = _calc('US Name Point', 'Name, left-aligned.', _centre_case(NODE, {e: RCOL['name'] + W8(v, True) / 2 for e, v in NAMES.items()}, pane))
    f['US Type Point'] = _calc('US Type Point', 'Type, left-aligned.', _centre_case(NODE, {e: RCOL['type'] + W8(_type(e)) / 2 for e in NAMES}, pane))
    f['US Built Text Point'] = _calc('US Built Text Point', 'Middle of the built tag.', _at(RCOL['built'] + TAG_W / 2, pane))
    right = lambda col, width: {f'{p}|{e}': RCOL[col] - width(p, e) / 2 for p, e in SHOWN}
    f['US Uses Point'] = _calc('US Uses Point', 'Uses and unit, right-aligned.',
                               _centre_case(PKEY, right('uses', lambda p, e: W8(''.join(_uses(RANK_VALS[(p, e)], e)))), pane))
    f['US Change Point'] = _calc('US Change Point', 'Change, right-aligned.',
                                 _centre_case(PKEY, right('change', lambda p, e: W8(_change(RANK_VALS[(p, e)])[1], _change(RANK_VALS[(p, e)])[0] != 'flat')), pane))
    f['US Consumers Point'] = _calc('US Consumers Point', 'Daily consumers, right-aligned.',
                                    _centre_case(PKEY, right('cons', lambda p, e: W8(f'{RANK_VALS[(p, e)]["cons"]:.1f}')), pane))
    f['US Cost Per Use Point'] = _calc('US Cost Per Use Point', 'Cost per use, right-aligned.',
                                       _centre_case(PKEY, right('cpu', lambda p, e: W8(_cpu(RANK_VALS[(p, e)]))), pane))
    fw = {k: W7(v, True) + 14 for k, v in by_text(lambda p, e: _flag(RANK_VALS[(p, e)])).items()}
    f['US Flag Text Point'] = _calc('US Flag Text Point', 'Middle of the flag.', _centre_case(PKEY, {k: RCOL['flag'] + w / 2 for k, w in fw.items()}, pane))
    idx = '[Exposure Path Index]'
    f['US Row Point'] = _calc('US Row Point', 'The row (white, takes the click).', _rounded(idx, 0, RCW, 0, ROW_H - 1, 0, pane))
    f['US Divider Point'] = _calc('US Divider Point', 'The 1 px line under each row.', _rounded(idx, 0, RCW, ROW_H - 1, ROW_H, 0, pane))
    f['US Built Border Point'] = _calc('US Built Border Point', 'Built tag outline (radius 4).', _rounded(idx, RCOL['built'], TAG_W, mid - 7, mid + 7, 4, pane))
    f['US Built Fill Point'] = _calc('US Built Fill Point', 'Built tag fill.', _rounded(idx, RCOL['built'] + 1, TAG_W - 2, mid - 6, mid + 6, 3, pane))
    fw_case = _case(PKEY, {k: f'{w:.0f}' for k, w in fw.items()}, '0', False)
    f['US Flag Point'] = _calc('US Flag Point', 'Flag: red tint for Retire?, amber tint for Not registered.',
                                      _rounded(idx, RCOL['flag'], fw_case, mid - 8, mid + 8, 4, pane, 'NOT ISNULL([US Flag Key])'))
    heads = [('DATA PRODUCT', RCOL['name'], 'l'), ('TYPE', RCOL['type'], 'l'), ('BUILT', RCOL['built'], 'l'),
             *[(RHEADS[c], RCOL[c], 'r') for c in ('uses', 'change', 'cons', 'cpu')]]
    f.update(_heading_calcs('US Ranked', heads, RCW))
    t.update({n: SP_MEA for n in f if n.endswith('Point')})
    t.update({'US Use Rank': I_DIM, 'Is US Ranked Row': B_DIM})
    t.update({n: S_DIM for n in f if n not in t})
    return f, t


def _heading_calcs(prefix, heads, pane_w):
    hx = {i: (x + W7(h, True) / 2) if a == 'l' else (x - W7(h, True) / 2) for i, (h, x, a) in enumerate(heads)}
    return {f'{prefix} Heading': _calc(f'{prefix} Heading', 'Column titles, one date row each.', _case('[day_index]', {i: h for i, (h, _, _) in enumerate(heads)})),
            f'{prefix} Heading Point': _calc(f'{prefix} Heading Point', 'Middle of a column title (measured by the build).',
                                             f'MAKEPOINT(0, ({_case("[day_index]", {i: f"{v:.1f}" for i, v in hx.items()}, "0", False)} - {pane_w / 2:g}) / 100)')}


def semantic_calcs():
    f, t = {}, {}
    rank = {f'{p}|{pl}|{k}': i + 1 for (p, pl), ks in SEM_ROWS.items() for i, k in enumerate(ks)}
    f['US Semantic Rank'] = _calc('US Semantic Rank', 'Row of a semantic object: most failed refreshes in the period first, then lowest success,\n'
                                  '// live objects (nothing to refresh) with the fully successful ones (the prototype\'s order).', _case(KEY, rank, quote=False))
    f['Is US Semantic Row'] = _calc('Is US Semantic Row', 'Rows of the refresh table. Put on Filters (True).', 'NOT ISNULL([US Semantic Rank])')
    sems = [k for k in ORDER if NODES[k]['resource_type'] == 'semantic']
    keys = [(p, k) for p in PERIODS for k in sems]
    pane = SEM_ROW
    by = lambda fn: {f'{p}|{k}': fn(SEM_VALS[(p, k)]) for p, k in keys}
    f['US Sem Success Low Text'] = _calc('US Sem Success Low Text', 'Success below 98%, red bold (written by the build per period).',
                                         _case(PKEY, {k: v for k, v in by(lambda v: _succ(v)[1] if _succ(v)[0] == 'low' else None).items() if v}))
    f['US Sem Success Text'] = _calc('US Sem Success Text', 'Success at 98% or above, or "-" for a live object.',
                                     _case(PKEY, {k: v for k, v in by(lambda v: _succ(v)[1] if _succ(v)[0] == 'normal' else None).items() if v}))
    f['US Sem Failed Text'] = _calc('US Sem Failed Text', 'Failed refreshes in the period.', _case(PKEY, by(lambda v: f'{v["fl"]:.0f}')))
    f['US Sem Avg Text'] = _calc('US Sem Avg Text', 'Average refresh time: "4.2 min", "19s".', _case(PKEY, by(lambda v: _dur(v['dur']))))
    f['US Sem Name Text'] = _calc('US Sem Name Text', 'Semantic object name.', _case(NODE, {k: NODES[k]['node_name'] for k in sems}))
    f['US Sem Tool Text'] = _calc('US Sem Tool Text', 'BI tool.', _case(NODE, {k: BI_NAME[NODES[k]['bi_tool']] for k in sems}))
    f['US Sem Mode Text'] = _calc('US Sem Mode Text', 'Connection: extract or live.', _case(NODE, {k: NODES[k]['connection_type'] for k in sems}))
    f['US Sem Live Text'] = _calc('US Sem Live Text', 'Where the sparkline would be, for a live object.',
                                  _case(NODE, {k: 'Live, no extract' for k in sems if NODES[k]['connection_type'] == 'live'}))
    left = lambda col, txt: _centre_case(NODE, {k: SCOL[col] + W8(txt(k)) / 2 for k in sems}, pane)
    f['US Sem Name Point'] = _calc('US Sem Name Point', 'Name, left-aligned.', left('name', lambda k: NODES[k]['node_name']))
    f['US Sem Tool Point'] = _calc('US Sem Tool Point', 'Tool, left-aligned.', left('tool', lambda k: BI_NAME[NODES[k]['bi_tool']]))
    f['US Sem Mode Point'] = _calc('US Sem Mode Point', 'Mode, left-aligned.', left('mode', lambda k: NODES[k]['connection_type']))
    f['US Sem Live Point'] = _calc('US Sem Live Point', '"Live, no extract", left-aligned in the sparkline column.',
                                   _at(SCOL['spark'] + W8('Live, no extract') / 2, pane))
    right = lambda col, txt, bold=lambda v: False: _centre_case(PKEY, {f'{p}|{k}': SCOL[col] - W8(txt(SEM_VALS[(p, k)]), bold(SEM_VALS[(p, k)])) / 2
                                                                       for p, k in keys}, pane)
    f['US Sem Success Point'] = _calc('US Sem Success Point', 'Success, right-aligned.',
                                      right('succ', lambda v: _succ(v)[1], lambda v: _succ(v)[0] == 'low'))
    f['US Sem Failed Point'] = _calc('US Sem Failed Point', 'Failed, right-aligned.', right('fail', lambda v: f'{v["fl"]:.0f}'))
    f['US Sem Avg Point'] = _calc('US Sem Avg Point', 'Average refresh, right-aligned.', right('avg', lambda v: _dur(v['dur'])))
    # sparkline: one point per Node Daily row (day), each object on its own scale; the window part drawn again in red
    x0, w, mid, sh = SCOL['spark'], SCOL['spark_w'], SEM_ROW_H / 2, 14
    spark = ('MAKEPOINT(\n'
             f'    ({pane[1] / 2 - (mid + sh / 2):g} + IIF({{ FIXED [node_id] : MAX([refresh_failed]) }} > 0,\n'
             f'        ZN([refresh_failed]) / {{ FIXED [node_id] : MAX([refresh_failed]) }}, 0) * {sh}) / 100,\n'
             f'    ({x0:.1f} + ([US Spark Index] + 0.5) * {w / DAYS:.4f} - {pane[0] / 2:g}) / 100\n)')
    f['US Spark Index'] = _calc('US Spark Index', 'Day 0 to 89 along a sparkline (path).', "DATEDIFF('day', { MIN([date]) }, [date])")
    f['US Spark Point'] = _calc('US Spark Point', 'Failed refreshes that day, scaled to the object\'s busiest day (grey, all 90 days).', spark)
    f['US Spark Window Point'] = _calc('US Spark Window Point', 'The same inside the selected window (red).',
                                       f"IF DATEDIFF('day', [date], {{ MAX([date]) }}) < [p_period] THEN {spark} END")
    heads = [('SEMANTIC OBJECT', SCOL['name'], 'l'), ('TOOL', SCOL['tool'], 'l'), ('MODE', SCOL['mode'], 'l'),
             *[(SHEADS[c], SCOL[c], 'r') for c in ('succ', 'fail', 'avg')], ('FAILURES PER DAY', SCOL['spark'], 'l')]
    f.update(_heading_calcs('US Semantic', heads, SCW))
    t.update({n: SP_MEA for n in f if n.endswith('Point')})
    t.update({'US Semantic Rank': I_DIM, 'Is US Semantic Row': B_DIM, 'US Spark Index': I_DIM})
    t.update({n: S_DIM for n in f if n not in t})
    return f, t


def chart_calcs():
    f = {
        # The retire zone is one polygon drawn on the scatter's own axes (GB, v36: "just like the prototype"). Its four
        # corners are four date rows (day_index 86 to 89, always inside the window): on those marks MIN = MAX of
        # day_index, while a product's dot spans all 90 days, so one x field gives either a corner or a product's cost.
        'US Scatter X': ('// US Scatter X\n// Cost axis of the scatter. A product: its cost in the period (NULL with no use or cost: a log axis\n'
                         '// cannot show 0). A retire-zone corner: $5 at the bottom left, $5 x the threshold at the bend, and the\n'
                         '// axis\'s right edge (a round power of ten above the dearest product, per period and platform).\n'
                         'IF MIN([day_index]) = MAX([day_index]) THEN\n'
                         '    CASE MIN([day_index]) WHEN 86 THEN 5 WHEN 87 THEN 5 * [Retire Uses Threshold]\n'
                         f'    ELSE {_case(COMBO, {f"{k[0]}|{k[1]}": v for k, v in XMAX.items()}, "1000", False)} END\n'
                         'ELSEIF [Product Uses (Period)] > 0 AND [Product Cost (Period)] > 0 THEN [Product Cost (Period)]\nEND'),
        'US Retire Zone': ('// US Retire Zone\n// Uses axis of the retire-zone corners: 1 (the axis floor), the threshold (10 uses per 30 days,\n'
                           '// scaled to the window) at the bend and the right edge, 1 again at the bottom right.\n'
                           'CASE MIN([day_index]) WHEN 86 THEN 1 WHEN 87 THEN [Retire Uses Threshold]\n'
                           'WHEN 88 THEN [Retire Uses Threshold] WHEN 89 THEN 1 END'),
        'US Scatter Uses': ('// US Scatter Uses\n// Uses axis of a product dot (NULL with no use or cost).\n'
                            'IF [Product Uses (Period)] > 0 AND [Product Cost (Period)] > 0 THEN [Product Uses (Period)] END'),
    }
    t = {'US Scatter X': R_MEA, 'US Retire Zone': R_MEA, 'US Scatter Uses': R_MEA}
    for code, name, _title in TYPES:
        f[f'Is Declared Consumer Type {name}'] = (f'// Is Declared Consumer Type {name}\n// Small multiple filter: declared products counted in {UNIT[code]}.\n'
                                                  f'[consumption_type (mart_exposure_daily.csv)] = "{code}"\nAND [is_declared]')
        t[f'Is Declared Consumer Type {name}'] = B_DIM
    f['US Type Total Text'] = ('// US Type Total Text\n// Total at the top right of a small multiple, as the prototype writes it: "12.3K", "418".\n'
                               'IF [Uses In Period (Type)] >= 1000 THEN STR(ROUND([Uses In Period (Type)] / 1000, 1)) + "K"\n'
                               'ELSE STR(INT([Uses In Period (Type)])) END')
    t['US Type Total Text'] = S_MEA
    return f, t


PACK_TYPES = {  # calc pack section 10 (and 4.5) calcs this tab reads
    'Product Uses (Period)': R_MEA, 'Product Cost (Period)': R_MEA, 'Cost Per Use': R_MEA, 'Uses Per 30 Days': R_MEA,
    'Is Retire Candidate': ('boolean', 'measure', 'nominal'), 'Scatter Colour Key': S_MEA, 'Retire Uses Threshold': R_MEA,
    'Scatter Label': S_MEA, 'Uses In Period (Type)': R_MEA, 'Uses Unit Label': S_DIM,
}
_f, _t = {}, dict(PACK_TYPES)
for fn in (ranked_calcs, semantic_calcs, chart_calcs):
    a, b = fn()
    _f.update(a)
    _t.update(b)
CALCS.add(formulas=_f, types=_t, table_calc={'Scatter Label': 'node_id (dim_nodes.csv)'})


# ================================================================ sheets

def _a(n):
    return R(n, 'attr')


def _clicks():
    return [R('Clear Node Value'), R('Clear Node Key Value'), *[R(f) for f, _ in PANEL_WRITES]]


def scatter_sheet() -> Sheet:
    x, y, zone = R('US Scatter X'), R('US Scatter Uses'), R('US Retire Zone')
    cost, uses, corner = R('Product Cost (Period)'), R('Product Uses (Period)'), R('day_index', kind='ok')
    key, colour, lab = R('node_id (dim_nodes.csv)'), R('Scatter Colour Key'), R('Scatter Label')
    color_map(colour, {'"Built by hand"': ACCENT, '"AI-built"': '#5b5fc7', '"Unregistered"': WARN, '"Retire candidate"': CRIT})
    tip = [run(_a('display_name'), 9, INK1, SEMI), run(NL, 7, INK3),
           run('COST   ', 7, INK3, SEMI), run(cost, 9, NAVY, SEMI), run(NL, 7, INK3),
           run('USES   ', 7, INK3, SEMI), run(uses, 9, NAVY, SEMI), run(' ', 9, INK3), run(_a('Uses Unit Label'), 9, INK3), run(NL, 7, INK3),
           run('COST PER USE   ', 7, INK3, SEMI), run(R('Cost Per Use'), 9, NAVY, SEMI), run(NL, 7, INK3),
           run('CLICK TO OPEN ITS LINEAGE', 7, INK3, SEMI)]
    log = lambda r, scope: (f"            <encoding attr='space' class='0' field='{r.ref}' field-type='quantitative' fold='true' "
                            f"scale='log' scope='{scope}' type='space' />")
    axis = ["            <format attr='line-visibility' value='off' />", "            <format attr='font-size' value='8' />",
            f"            <format attr='color' value='{INK3}' />",
            f"            <format attr='title' class='0' field='{zone.ref}' scope='rows' value='' />",
            f"            <format attr='title' class='0' field='{x.ref}' scope='cols' value='' />",
            log(x, 'cols'), log(zone, 'rows'),
            # the dots' axis follows the zone's, on the same log scale
            f"            <encoding attr='space' class='0' field='{y.ref}' field-type='quantitative' fold='true' scale='log' "
            "scope='rows' synchronized='true' type='space' />"]
    grid = ["            <format attr='line-visibility' scope='rows' value='on' />", f"            <format attr='stroke-color' scope='rows' value='{LINE_SOFT}' />",
            "            <format attr='line-visibility' scope='cols' value='on' />", f"            <format attr='stroke-color' scope='cols' value='{LINE_SOFT}' />"]
    s = Sheet('US Cost vs Usage Scatter', cols=[x], rows=[(zone, y)], filters=[R('Is Platform Match Node')],
              hide=[y], formats={x: USD, zone: 'n#,##0;-#,##0', y: 'n#,##0;-#,##0', cost: USD, uses: 'n#,##0;-#,##0',
                                 R('Cost Per Use'): 'c"$"#,##0.00;-"$"#,##0.00'},
              extra={'axis': axis, 'gridline': grid},
              # the retire zone: one polygon through its four corner rows (path = day_index), under the dots
              panes=[Pane('Automatic', label_show=False),
                     Pane('Polygon', axis=zone, path=corner, mark_color=CRIT_TINT, label_show=False),
                     Pane('Circle', axis=y, color=colour, size=0.55, lod=[key, *_clicks()], text=[lab], tooltip=tip, stroke='#ffffff',
                          label=[run(lab, 8, INK1)], align='right', cull=True)])
    return s


def multiple_sheets() -> list[Sheet]:
    date = R('date (mart_exposure_daily.csv)', kind='qk')
    out = []
    for code, name, title in TYPES:
        ev = R('events', 'sum')
        tip = [run(R('date (mart_exposure_daily.csv)', 'attr'), 9, INK1, SEMI), run(NL, 7, INK3), run(title.upper() + '   ', 7, INK3, SEMI), run(ev, 9, NAVY, SEMI)]
        axis = ["            <format attr='line-visibility' value='off' />", "            <format attr='font-size' value='7' />",
                f"            <format attr='color' value='{INK3}' />",
                f"            <format attr='title' class='0' field='{ev.ref}' scope='rows' value='' />",
                f"            <format attr='title' class='0' field='{date.ref}' scope='cols' value='' />"]
        filt = [R(f'Is Declared Consumer Type {name}'), R('Is Platform Match Node'), R('In Period')]
        out.append(Sheet(f'US {name} Small Multiple', cols=[date], rows=[ev], filters=filt,
                         formats={date: '*d mmm', ev: 'n#,##0;-#,##0', R('date (mart_exposure_daily.csv)', 'attr'): '*ddd d mmm'},
                         extra={'axis': axis},
                         panes=Pane('Bar', mark_color=ACCENT, size=0.55, label_show=False, tooltip=tip)))
        tot = R('US Type Total Text')
        out.append(Sheet(f'US {name} Total', filters=filt, tooltip=False,
                         panes=label_pane(text=[tot], align='right', label=[run(tot, 10, NAVY, SEMI)])))
    return out


def _poly(title, point, pane, path, key, colour=None, mark=None, inert=True, lod=(), tooltip=None):
    return Pane('Polygon', title=title, inert=inert, color=colour, mark_color=mark, path=path, label_show=False,
                lod=[R(point, 'clct'), key, *lod], pane_size=pane, tooltip=tooltip)


def _cell(title, point, runs, pane, lod):
    return label_pane(title=title, inert=True, text=[r['_ref'] for r in runs if '_ref' in r], label=runs, align='center',
                      valign='center', lod=[R(point, 'clct'), *lod], pane_size=pane)


def _header(name, prefix, width):
    hp = (width, HEAD_H)
    return _grid(Sheet(name, rows=[LAT], cols=[LON], filters=[R(f'Is {prefix} Heading Row')], layers=True, no_basemap=True,
                       zoom=None, tooltip=False,
                       panes=[Pane('Automatic', pane_size=hp),
                              label_pane(title='Titles', inert=True, text=[_a(f'{prefix} Heading')], label=[run(_a(f'{prefix} Heading'), 7, INK3, SEMI)],
                                         align='center', lod=[R(f'{prefix} Heading Point', 'clct'), R('day_index')], pane_size=hp)]), hp)


CALCS.add(formulas={'Is US Ranked Heading Row': '// Is US Ranked Heading Row\n// One date row per column title. Put on Filters (True).\n[day_index] < 7',
                    'Is US Semantic Heading Row': '// Is US Semantic Heading Row\n// One date row per column title. Put on Filters (True).\n[day_index] < 7'},
          types={'Is US Ranked Heading Row': B_DIM, 'Is US Semantic Heading Row': B_DIM})


def ranked_sheets() -> list[Sheet]:
    key, order = R('node_id (dim_nodes.csv)'), R('US Use Rank', kind='ok')
    path, pane = R('Exposure Path Index', kind='ok'), ROW
    color_map(R('US Built Key'), {'"AI-built"': AI_BG, '"By hand"': BY_HAND_BG})
    color_map(R('US Flag Key'), {'"Retire"': CRIT_TINT, '"Unregistered"': WARN_TINT})
    tip = [run(_a('display_name'), 9, INK1, SEMI), run(NL, 7, INK3), run('USES   ', 7, INK3, SEMI), run(_a('US Uses Number Text'), 9, NAVY, SEMI),
           run(_a('US Uses Unit Text'), 9, INK3), run(NL, 7, INK3),
           run('AVERAGE DAILY CONSUMERS   ', 7, INK3, SEMI), run(_a('US Consumers Text'), 9, NAVY, SEMI), run(NL, 7, INK3),
           run('COST PER USE   ', 7, INK3, SEMI), run(_a('US Cost Per Use Text'), 9, NAVY, SEMI), run(NL, 7, INK3),
           run('CLICK TO OPEN ITS LINEAGE', 7, INK3, SEMI)]
    cell = lambda title, point, runs: _cell(title, point, runs, pane, [key])
    layers = [
        _poly('Row', 'US Row Point', pane, path, key, mark=CARD, inert=False, lod=_clicks(), tooltip=tip),
        _poly('Divider', 'US Divider Point', pane, path, key, mark=LINE_SOFT),
        _poly('Built border', 'US Built Border Point', pane, path, key, colour=None, mark=LINE),
        _poly('Built fill', 'US Built Fill Point', pane, path, key, colour=R('US Built Key')),
        _poly('Flag', 'US Flag Point', pane, path, key, colour=R('US Flag Key')),
        cell('Name', 'US Name Point', [run(_a('US Name Text'), 8, INK1, SEMI)]),
        cell('Type', 'US Type Point', [run(_a('US Type Text'), 8, INK2)]),
        cell('Built', 'US Built Text Point', [run(_a('US Built Text'), 7, INK2)]),
        cell('Uses', 'US Uses Point', [run(_a('US Uses Number Text'), 8, INK1), run(_a('US Uses Unit Text'), 8, INK3)]),
        cell('Change', 'US Change Point', [run(_a('US Change Up Text'), 8, GOOD_INK, SEMI), run(_a('US Change Down Text'), 8, CRIT_INK, SEMI),
                                           run(_a('US Change Flat Text'), 8, INK2)]),
        cell('Consumers', 'US Consumers Point', [run(_a('US Consumers Text'), 8, INK1)]),
        cell('Cost per use', 'US Cost Per Use Point', [run(_a('US Cost Per Use Text'), 8, INK1)]),
        cell('Flag', 'US Flag Text Point', [run(_a('US Flag Retire Text'), 7, CRIT_INK, SEMI), run(_a('US Flag Unregistered Text'), 7, WARN_INK, SEMI)]),
    ]
    table = _grid(Sheet('US Ranked Products Table', rows=[Cross([Nest([order, key]), LAT])], cols=[LON], filters=[R('Is US Ranked Row')],
                        hide=[order, key], layers=True, no_basemap=True, zoom=None,
                        panes=[Pane('Automatic', lod=[key], pane_size=pane), *layers]), pane)
    return [_header('US Ranked Products Header', 'US Ranked', RCW), table]


def semantic_sheets() -> list[Sheet]:
    key, order = R('node_id (dim_nodes.csv)'), R('US Semantic Rank', kind='ok')
    path, pane = R('US Spark Index', kind='ok'), SEM_ROW
    clicks = [R('node_key'), *[R(f) for f, _ in PANEL_WRITES]]
    tip = [run(_a('node_name'), 9, INK1, SEMI), run(NL, 7, INK3), run('FAILED REFRESHES   ', 7, INK3, SEMI), run(_a('US Sem Failed Text'), 9, CRIT_INK, SEMI),
           run(NL, 7, INK3), run('CLICK TO OPEN ITS LINEAGE', 7, INK3, SEMI)]
    cell = lambda title, point, runs: _cell(title, point, runs, pane, [key])
    name = _cell('Name', 'US Sem Name Point', [run(_a('US Sem Name Text'), 8, INK1)], pane, [key, *clicks])
    name.inert, name.tooltip = False, tip
    layers = [
        Pane('Line', title='Sparkline', inert=True, mark_color='#d9dcd7', path=path, size=0.3, label_show=False,
             lod=[R('US Spark Point', 'clct'), key], pane_size=pane),
        Pane('Line', title='Sparkline window', inert=True, mark_color=CRIT, path=path, size=0.3, label_show=False,
             lod=[R('US Spark Window Point', 'clct'), key], pane_size=pane),
        name,
        cell('Tool', 'US Sem Tool Point', [run(_a('US Sem Tool Text'), 8, INK2)]),
        cell('Mode', 'US Sem Mode Point', [run(_a('US Sem Mode Text'), 8, INK2)]),
        cell('Success', 'US Sem Success Point', [run(_a('US Sem Success Low Text'), 8, CRIT_INK, SEMI), run(_a('US Sem Success Text'), 8, INK1)]),
        cell('Failed', 'US Sem Failed Point', [run(_a('US Sem Failed Text'), 8, INK1)]),
        cell('Avg refresh', 'US Sem Avg Point', [run(_a('US Sem Avg Text'), 8, INK1)]),
        cell('Live', 'US Sem Live Point', [run(_a('US Sem Live Text'), 8, INK3)]),
    ]
    table = _grid(Sheet('US Semantic Refresh Table', rows=[Cross([Nest([order, key]), LAT])], cols=[LON],
                        filters=[R('Is US Semantic Row')], hide=[order, key], layers=True, no_basemap=True, zoom=None, divider='rows',
                        panes=[Pane('Automatic', lod=[key], pane_size=pane), *layers]), pane)
    return [_header('US Semantic Refresh Header', 'US Semantic', SCW), table]


def sheets() -> list[Sheet]:
    return [scatter_sheet(), *multiple_sheets(), *ranked_sheets(), *semantic_sheets()]


# ================================================================ dashboard content (build plan 3.8)

def content() -> Z:
    dot = lambda c, label, last=False: [run('● ', 8, c), run(label + ('' if last else '      '), 8, INK2)]
    scatter = card('US Scatter Card', fixed=HALF, margins={'right': 7}, kids=[
        card_header('Cost against usage', 'Each dot is a data product. Shaded corner: under 10 uses in 30 days and over $5 per use, '
                    'the candidates to retire. Both axes are logarithmic.', 58),
        sheet('US Cost vs Usage Scatter'),
        text(dot(ACCENT, 'Built by hand') + dot('#5b5fc7', 'AI-built') + dot(WARN, 'Unregistered') + dot(CRIT, 'Retire candidate', True),
             fixed=22, **{'padding-top': '6'})])

    def multiple(code, name, title, margins):
        st = {f'margin-{k}': str(v) for k, v in margins.items()}
        return Z('vert', friendly=f'US {name} Holder', style=st, kids=[
            Z('horz', friendly=f'US {name} Head', fixed=20, kids=[text([run(title, 8, INK2)]), sheet(f'US {name} Total', 70)]),
            sheet(f'US {name} Small Multiple')])
    (c1, n1, t1), (c2, n2, t2), (c3, n3, t3), (c4, n4, t4) = TYPES
    consumption = card('US Consumption Card', margins={'left': 7}, kids=[
        card_header('Consumption by consumer type, per day', 'Each type is counted in its own unit, so each gets its own scale'),
        Z('horz', friendly='US Multiples Row 1', kids=[multiple(c1, n1, t1, {'right': 8}), multiple(c2, n2, t2, {'left': 8})]),
        Z('horz', friendly='US Multiples Row 2', style={'margin-top': '10'}, kids=[multiple(c3, n3, t3, {'right': 8}), multiple(c4, n4, t4, {'left': 8})])])
    ranked = card('US Ranked Card', margins={'right': 7}, kids=[
        Z('horz', friendly='US Ranked Header', fixed=44, kids=[
            # shorter than the prototype's subtitle, so it stays on one line beside the sort dropdown
            card_header('Data products ranked by use', 'Uses, change against the period before, cost per use. '
                        'Click a row to open its lineage.', None),
            # sort dropdown (GB, v36): the build writes the row order for each choice
            text([run('Sort by', 8, INK3)], fixed=46, **{'padding-top': '8', 'text-align': 'right'}),
            Z('paramctrl', param='p_us_sort', fixed=132, style={'padding-top': '4', 'padding-bottom': '14', 'padding-left': '6'})]),
        sheet('US Ranked Products Header', HEAD_H), blank(1, LINE), sheet('US Ranked Products Table')])
    semantic = card('US Semantic Card', fixed=SEM_W, margins={'left': 7}, kids=[  # 643 (GB, v36)
        card_header('BI semantic layer refreshes', 'dbt can be green while an extract fails. This is where that shows.'),
        sheet('US Semantic Refresh Header', HEAD_H), blank(1, LINE), sheet('US Semantic Refresh Table')])
    return Z('vert', friendly='US Content', style=CONTENT_PAD, kids=[
        Z('horz', friendly='US Top Row', fixed=TOP_H, kids=[scatter, consumption]),
        # the last row is flexible, so it always reaches the bottom padding (skill: sizing)
        Z('horz', friendly='US Bottom Row', style={'margin-top': '14'}, kids=[ranked, semantic])])


def check_fit(zones) -> None:
    by = {(z.name or z.friendly): z.rect for z in zones}
    # the ranked table scrolls (GB, v36): its width leaves room for the scroll bar, its height is free
    for name, (w, h) in (('US Ranked Products Table', (RCW + 18, 0)), ('US Ranked Products Header', (RCW, HEAD_H)),
                         ('US Semantic Refresh Table', (SCW, SEM_ROW_H * max(len(v) for v in SEM_ROWS.values()))),
                         ('US Semantic Refresh Header', (SCW, HEAD_H))):
        _, _, zw, zh = by[name]
        assert w <= zw and h <= zh, f'{name}: needs {w} x {h}, zone is {zw:.0f} x {zh:.0f}'
    _, y, _, h = by['US Bottom Row']
    end = 1000 - int(CONTENT_PAD['padding-bottom'])
    assert abs(y + h - end) < 0.5, f'US rows end at {y + h:.0f}, content ends at {end}'


_EXPOSURE_CLICKS = [('p_selected_exposure', lambda: R('node_id (dim_nodes.csv)'), 'Select Exposure'),
                    ('p_selected_node', lambda: R('Clear Node Value'), 'Clear Node'),
                    ('p_selected_node_key', lambda: R('Clear Node Key Value'), 'Clear Node Key'),
                    *[(param, (lambda f=f: R(f)), f'Set {param}') for f, param in PANEL_WRITES]]
ACTIONS = [  # (sheet, source Ref factory, parameter, caption)
    *[(ws, ref, param, f'US {tag} {cap}') for ws, tag in (('US Cost vs Usage Scatter', 'Scatter'), ('US Ranked Products Table', 'Ranked'))
      for param, ref, cap in _EXPOSURE_CLICKS],
    ('US Semantic Refresh Table', lambda: R('node_id (dim_nodes.csv)'), 'p_selected_node', 'US Semantic Select Node'),
    ('US Semantic Refresh Table', lambda: R('node_key'), 'p_selected_node_key', 'US Semantic Select Node Key'),
    *[('US Semantic Refresh Table', (lambda f=f: R(f)), param, f'US Semantic Set {param}') for f, param in PANEL_WRITES],
]
# a product opens in the Lineage explorer; a semantic object in Blast radius (GB, 24 Oct)
NAV_ACTIONS = [*[(ws, 'Lineage explorer', f'Go to Lineage from {ws}') for ws in ('US Cost vs Usage Scatter', 'US Ranked Products Table')],
               ('US Semantic Refresh Table', 'Blast radius', 'Go to Blast radius from US Semantic Refresh Table')]
DEHIGHLIGHT = ['US Cost vs Usage Scatter', 'US Ranked Products Table', 'US Semantic Refresh Table']
