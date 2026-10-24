"""Tab 6, Data quality (QA): calc pack section 7, build plan 3.5.

GB's choices (24 Oct): the heatmap native (squares on a model x day grid) and scrolling, "Tests that keep failing" as a
canvas like the prototype, and the two bar lists in the prototype's style (name and value above a thin bar on a grey
track).

- KPIs: Test pass rate re-uses the Health sheet; failing right now, tests run (with the distinct tests under it) and
  model test coverage are label sheets.
- Heatmap: rows are models with a warning or failure in the window, most failure days first; columns are the span's
  days (at least 30, all 90 at 90). The F and W counts sit as row headers beside the names: in a scrolling sheet a
  second sheet on the right would not scroll with it. Dates above: a 30-day or a 90-day strip, shown by dynamic zone
  visibility on p_period, each on a fixed reversed day axis so its labels line up with the columns.
- Tests that keep failing: the 8 tests with most failure days, then warning days, per period and platform, worked out
  by the build. A canvas row per test needs about 84 rows to draw seven bars, more than a test's own rows, so each row
  is drawn on the Node Daily rows of a fixed "carrier" model (a scaffold, like the date table under Late right now).
- Issues by test type and coverage by domain: one canvas each on the 90-row date table (4 rows per bar), values per
  period and platform written by the build.
"""

from __future__ import annotations

import collections
import csv
import datetime as dt

from . import shapes as SH
from .core import (B_DIM, CALCS, CRIT, CRIT_INK, GOOD_INK, I_DIM, I_MEA, INK1, INK2, INK3, INK4, LAT, LINE, LINE_SOFT,
                   LON, NAVY, NL, R_MEA, S_DIM, S_MEA, SEMI, SP_MEA, WARN, WARN_INK, ACCENT, Cross, Pane, R, Sheet, Z,
                   blank, card, card_header, color_map, label_pane, run, sheet, text)
from .lineage import _fit, _grid, _q
from .shell import CONTENT_H, CONTENT_PAD

P = 'QA'
ROOT = SH.ROOT
M = ROOT / 'data' / 'marts'
NODES = {r['node_id']: r for r in csv.DictReader(open(M / 'dim_nodes.csv', encoding='utf-8'))}
PERIODS, PLATFORMS = (7, 30, 90), ('All', 'snowflake', 'databricks', 'redshift')
ASOF = dt.date(2026, 10, 19)
DATE = 'date (dim_date.csv)'

# ---------------------------------------------------------------- geometry (content 1312 x CONTENT_H)
KPI_H = 96
BODY_H = CONTENT_H - KPI_H - 14                  # 734
RIGHT_W = 420                                    # right column; 7 px margin-left outside
ISSUES_H, COVER_H = 220, 248                     # the prototype's cards (with their 7 px margins)
CANVAS_W = RIGHT_W - 2 * 16 - 2 - SH.SLACK       # 382: the bar lists
KF_W = CANVAS_W - 18                             # 364: tests that keep failing, room for its scroll bar
KF_ROW = (KF_W, 44)
# bar-list rows: as tall as each card allows (the prototype's are 29 px)
ISSUE_ROW = (ISSUES_H - 14 - 2 - 28 - 44 - SH.SLACK) // 5
COVER_ROW = (COVER_H - 7 - 2 - 28 - 44 - SH.SLACK) // 6
NAME_W, FAIL_W, WARN_W = 196, 26, 30             # heatmap row headers
HEAT_ROW = 13                                    # the prototype's 13 px rows; the heatmap scrolls (GB)
TOP_TESTS = 8
CARRIERS = sorted(k for k, n in NODES.items() if n['resource_type'] == 'model')[:TOP_TESTS]
TYPE_NAME = {'not_null': 'not_null', 'unique': 'unique', 'relationships': 'relationships',
             'accepted_values': 'accepted_values', 'custom': 'custom (singular)'}
WEEK = 'MTWTFSS'


def _num(v):
    return None if v in ('', None) else float(v)


def _in_plat(n, plat):
    return plat == 'All' or f'|{plat}|' in n['platform_filter_values']


def _case(expr, values, default='NULL', quote=True):
    body = '\n'.join(f'WHEN {_q(k) if isinstance(k, str) else k} THEN {_q(v) if quote else v}' for k, v in values.items())
    return f'CASE {expr}\n{body}\nELSE {default}\nEND'


def _calc(name, why, body):
    return f'// {name}\n// {why}\n{body}'


W8 = lambda s, b=False: SH.text_width(s, 8, b)
W7 = lambda s, b=False: SH.text_width(s, 7, b)
COMBO = 'STR([p_period]) + "|" + [p_platform]'


# ================================================================ the build's lists, per period and platform

def _tests():
    """Per combination: the 8 tests with most failure days (then warning days) and their weekday weights, and the
    failures plus warnings by test type."""
    rows = list(csv.DictReader(open(M / 'mart_test_daily.csv', encoding='utf-8')))
    kf, types = {}, {}
    for per in PERIODS:
        for plat in PLATFORMS:
            t = {}
            ty = collections.Counter()
            for r in rows:
                if not _in_plat(NODES[r['node_id']], plat):
                    continue
                d = dt.date.fromisoformat(r['date'])
                if (ASOF - d).days >= per:
                    continue
                x = t.setdefault(r['test_id'], dict(name=r['test_name'], node=r['node_id'], type=r['test_type'],
                                                     col=r['column_name'], sev=r['severity'], f=0, w=0, wd=[0.0] * 7))
                fails, warns = _num(r['fails']) or 0, _num(r['warns']) or 0
                if fails > 0:
                    x['f'] += 1
                elif warns > 0:
                    x['w'] += 1
                # the prototype's weekday weight: 1 for a failure day, 0.5 for a warning day
                x['wd'][d.weekday()] += (1 if fails > 0 else 0) + (0.5 if warns > 0 else 0)
                ty[r['test_type']] += fails + warns
            kf[(per, plat)] = sorted((x for x in t.values() if x['f'] + x['w']), key=lambda x: (-x['f'], -x['w'], x['name']))[:TOP_TESTS]
            types[(per, plat)] = sorted(ty.items(), key=lambda kv: -kv[1])
    return kf, types


def _coverage():
    out = {}
    for plat in PLATFORMS:
        doms = collections.defaultdict(lambda: [0, 0])
        for n in NODES.values():
            if n['resource_type'] == 'model' and _in_plat(n, plat):
                doms[n['domain']][0] += 1
                doms[n['domain']][1] += 1 if (_num(n['test_count']) or 0) > 0 else 0
        out[plat] = sorted(((d, w / m) for d, (m, w) in doms.items()), key=lambda kv: (kv[1], kv[0]))
    return out


KF, TYPES = _tests()
COVER = _coverage()


# ================================================================ calcs

PACK_TYPES = {  # calc pack section 7 calcs this tab reads
    'Is Failing On Last Day': B_DIM, 'Tests Failing Now': I_MEA, 'First Failing Test Name': S_MEA,
    'Tests Run In Period': R_MEA, 'Tests Defined': R_MEA, 'Model Test Coverage': R_MEA, 'Models Without Tests': R_MEA,
    'Models In Scope': R_MEA, 'Is In Heatmap Span': B_DIM, 'Fail Days In Period': I_DIM, 'Warn Days In Period': I_DIM,
    'Has Test Issue In Period': B_DIM, 'Heatmap Sort': I_DIM, 'Is Model': B_DIM,
}


def kpi_calcs():
    f = {
        'QA Failing Now Name': ('// QA Failing Now Name\n// Red sub-line: one test failing on the last day. MAX picks the same one as the prototype\n'
                                '// ("unique_dim_customers_customer_id").\nMAX(IF [Is Failing On Last Day] THEN [test_name] END)'),
        'QA All Passing Text': '// QA All Passing Text\n// Grey sub-line when nothing fails on the last day.\nIF [Tests Failing Now] = 0 THEN "All tests passing" END',
        'QA Tests Run Text': ('// QA Tests Run Text\n// "69.8K", as the prototype writes it.\n'
                              'IF [Tests Run In Period] >= 1000 THEN STR(ROUND([Tests Run In Period] / 1000, 1)) + "K"\n'
                              'ELSE STR(INT([Tests Run In Period])) END'),
        'QA Tests Defined Text': '// QA Tests Defined Text\n// "166 distinct tests".\nSTR(INT([Tests Defined])) + " distinct tests"',
        'QA No Tests Text': ('// QA No Tests Text\n// "14 of 82 models have no tests".\n'
                             'STR(INT([Models Without Tests])) + " of " + STR(INT([Models In Scope])) + " models have no tests"'),
        'Heat Order': '// Heat Order\n// Heatmap rows, most failure days first, then warning days (Heatmap Sort turned around).\n-[Heatmap Sort]',
        'Heat Fail Text': '// Heat Fail Text\n// "6F" in red beside the model name.\nIF [Fail Days In Period] > 0 THEN STR([Fail Days In Period]) + "F" END',
        'Heat Warn Text': '// Heat Warn Text\n// "8W" in amber ink.\nIF [Warn Days In Period] > 0 THEN STR([Warn Days In Period]) + "W" END',
        'Heat Cell Key': '// Heat Cell Key\n// Heatmap square colour (its own palette: pale green for passed).\n[Worst Test Label]',
        'QA Monday Label': ('// QA Monday Label\n// Date labels over the heatmap: Mondays, "Mon 21 Sep" on the 30-day strip.\n'
                            "IF DATEPART('weekday', [date (dim_date.csv)], 'monday') = 1\n"
                            "THEN STR(DAY([date (dim_date.csv)])) + \" \" + LEFT(DATENAME('month', [date (dim_date.csv)]), 3) END"),
        'QA Monday Label 30': '// QA Monday Label 30\n// With the weekday, as the prototype at 30 days.\nIF NOT ISNULL([QA Monday Label]) THEN "Mon " + [QA Monday Label] END',
        'QA Strip Header': '// QA Strip Header\n// An empty row header as wide as the heatmap\'s, so the date strip lines up with its columns.\n" "',
        'Show QA Dates 30': '// Show QA Dates 30\n// DZV: the 30-day date strip (7 and 30 days). Reads parameters only.\n[p_period] <= 30',
        'Show QA Dates 90': '// Show QA Dates 90\n// DZV: the 90-day date strip.\n[p_period] > 30',
    }
    t = {'QA Failing Now Name': S_MEA, 'QA All Passing Text': S_MEA, 'QA Tests Run Text': S_MEA, 'QA Tests Defined Text': S_MEA,
         'QA No Tests Text': S_MEA, 'Heat Order': I_DIM, 'Heat Fail Text': S_DIM, 'Heat Warn Text': S_DIM, 'Heat Cell Key': S_DIM,
         'QA Monday Label': S_DIM, 'QA Monday Label 30': S_DIM, 'QA Strip Header': S_DIM, 'Show QA Dates 30': B_DIM,
         'Show QA Dates 90': B_DIM}
    return f, t


def _rect(idx, k, x0, x1, y0, y1, pane):
    """Rectangle from 4 rows (k * 4 + 0..3) of a 0-based row index: one corner per row."""
    pw, ph = pane
    lat = lambda y: f'{(ph / 2 - y) / 100:.4f}'
    lon = lambda x: f'{(x - pw / 2) / 100:.4f}'
    return [(k * 4 + 0, lat(y0), lon(x0)), (k * 4 + 1, lat(y0), lon(x1)), (k * 4 + 2, lat(y1), lon(x1)), (k * 4 + 3, lat(y1), lon(x0))]


def barlist_calcs(prefix, items, key_expr, colour_note, row_h):
    """A prototype hbars list on the date table: per row a grey track and a coloured bar (4 rows each), the name left
    and the value right on the line above. items: {combo key: [(label, value text, fraction)]}."""
    n = max(len(v) for v in items.values())
    pane = (CANVAS_W, n * row_h)
    track, bar, texts = {}, {}, {}
    for key, rows in items.items():
        for i, (label, val, frac) in enumerate(rows):
            y0 = i * row_h + row_h - 9
            for idx, la, lo in _rect('[day_index]', i, 0, CANVAS_W, y0, y0 + 4, pane):
                track[f'{key}|{idx}'] = f'MAKEPOINT({la}, {lo})'
            for idx, la, lo in _rect('[day_index]', i, 0, max(2, CANVAS_W * frac), y0, y0 + 4, pane):
                bar[f'{key}|{idx}'] = f'MAKEPOINT({la}, {lo})'
            yt = i * row_h + row_h - 18
            texts[f'{key}|{i}'] = (label, val, f'MAKEPOINT({(pane[1] / 2 - yt) / 100:.4f}, {(W8(label) / 2 - CANVAS_W / 2) / 100:.4f})',
                                   f'MAKEPOINT({(pane[1] / 2 - yt) / 100:.4f}, {(CANVAS_W / 2 - W8(val, True) / 2) / 100:.4f})')
    row = f'{key_expr} + "|" + STR([day_index])'
    f = {
        f'{prefix} Track Point': _calc(f'{prefix} Track Point', 'The light grey track under each bar (written by the build).', _case(row, track, quote=False)),
        f'{prefix} Bar Point': _calc(f'{prefix} Bar Point', f'The bar, {colour_note}, as long as its share of the longest.', _case(row, bar, quote=False)),
        f'{prefix} Label Text': _calc(f'{prefix} Label Text', 'Row name, left.', _case(row, {k: v[0] for k, v in texts.items()})),
        f'{prefix} Value Text': _calc(f'{prefix} Value Text', 'Row value, right, bold.', _case(row, {k: v[1] for k, v in texts.items()})),
        f'{prefix} Label Point': _calc(f'{prefix} Label Point', 'Where the name sits (centred at half its measured width).', _case(row, {k: v[2] for k, v in texts.items()}, quote=False)),
        f'{prefix} Value Point': _calc(f'{prefix} Value Point', 'Where the value sits (right-aligned, measured).', _case(row, {k: v[3] for k, v in texts.items()}, quote=False)),
        f'{prefix} Shape Id': _calc(f'{prefix} Shape Id', 'Which bar a date row draws (4 rows each).', 'INT([day_index] / 4)'),
    }
    t = {k: (SP_MEA if k.endswith('Point') else I_DIM if k.endswith('Id') else S_DIM) for k in f}
    return f, t, pane


def issue_items():
    out = {}
    for (per, plat), rows in TYPES.items():
        mx = max((v for _k, v in rows), default=1) or 1
        out[f'{per}|{plat}'] = [(TYPE_NAME.get(k, k), f'{v:,.0f}', v / mx) for k, v in rows]
    return out


def cover_items():
    return {plat: [(d, f'{v * 100:.0f}%', v) for d, v in rows] for plat, rows in COVER.items()}


def kf_calcs():
    """Tests that keep failing on carrier rows: slot i is drawn on the Node Daily rows of CARRIERS[i]."""
    pane, f = KF_ROW, {}
    slot = {c: i for i, c in enumerate(CARRIERS)}
    f['QA KF Slot'] = _calc('QA KF Slot', 'Row of the list a carrier model\'s Node Daily rows draw (a scaffold: the content is the test\'s,\n'
                            '// written by the build per period and platform).', _case('[node_id (dim_nodes.csv)]', slot, quote=False))
    count = {f'{p}|{pl}': len(v) for (p, pl), v in KF.items()}
    f['Is QA KF Row'] = _calc('Is QA KF Row', 'Rows that have a test in this period and platform. Put on Filters (True).',
                              f'[QA KF Slot] < {_case(COMBO, count, "0", False)}')
    key = f'{COMBO} + "|" + STR(INT([QA KF Slot]))'
    item = {f'{p}|{pl}|{i}': x for (p, pl), xs in KF.items() for i, x in enumerate(xs)}
    names = {k: _fit(x['name'], KF_W - 4, 8) for k, x in item.items()}
    fail = {k: f'{x["f"]} fail' for k, x in item.items() if x['f']}
    warn = {k: (' · ' if x['f'] else '') + f'{x["w"]} warn' for k, x in item.items() if x['w']}
    f['QA KF Name Text'] = _calc('QA KF Name Text', 'Test name.', _case(key, names))
    f['QA KF Fail Text'] = _calc('QA KF Fail Text', 'Failure days in the period, red bold.', _case(key, fail))
    f['QA KF Warn Text'] = _calc('QA KF Warn Text', 'Warning days, amber.', _case(key, warn))
    f['QA KF Tip Text'] = _calc('QA KF Tip Text', 'Model, type, column and severity, for the tooltip.',
                                _case(key, {k: f'{NODES[x["node"]]["node_name"]} · {x["type"]} · {x["col"] or "-"} · {x["sev"]}' for k, x in item.items()}))
    pw, ph = pane
    at = lambda x, y: f'MAKEPOINT({(ph / 2 - y) / 100:.4f}, {(x - pw / 2) / 100:.4f})'
    f['QA KF Name Point'] = _calc('QA KF Name Point', 'Name, left, first line.', _case(key, {k: at(W8(v) / 2, 11) for k, v in names.items()}, quote=False))
    f['QA KF Fail Point'] = _calc('QA KF Fail Point', 'Failure days, left, second line.', _case(key, {k: at(W8(v, True) / 2, 30) for k, v in fail.items()}, quote=False))
    f['QA KF Warn Point'] = _calc('QA KF Warn Point', 'Warning days, after the failures.',
                                  _case(key, {k: at((W8(fail.get(k, ''), True)) + W8(v) / 2, 30) for k, v in warn.items()}, quote=False))
    # seven bars, right-aligned, 8 px wide and 6 apart; 12 rows of the Node Path Index each (3 per corner)
    bx = lambda k: KF_W - 4 - (7 - k) * 14
    bars, keys = {}, {}
    for k_, x in item.items():
        mx = max(x['wd']) or 1
        for b in range(7):
            h = max(2, x['wd'][b] / mx * 16)
            for c, (cx, cy) in enumerate(((bx(b), 33 - h), (bx(b) + 8, 33 - h), (bx(b) + 8, 33), (bx(b), 33))):
                bars[f'{k_}|{b * 4 + c}'] = at(cx, cy)
            keys[f'{k_}|{b}'] = ('Fail' if x['f'] else 'Warn') if x['wd'][b] else 'None'
    corner = 'INT([Node Path Index] / 12) * 4 + INT(([Node Path Index] % 12) / 3)'
    f['QA KF Bar Id'] = _calc('QA KF Bar Id', 'Which weekday bar a Node Daily row draws (12 rows each, up to 84).', 'IF [Node Path Index] < 84 THEN INT([Node Path Index] / 12) END')
    f['QA KF Bar Point'] = _calc('QA KF Bar Point', 'Weekday bar: height is the share of the test\'s busiest weekday (written by the build).',
                                 f'IF [Node Path Index] < 84 THEN\n' + _case(f'{key} + "|" + STR({corner})', bars, quote=False) + '\nEND')
    f['QA KF Bar Key'] = _calc('QA KF Bar Key', 'Bar colour: red for a test that failed, amber for one that only warned, grey with no issue that weekday.',
                               _case(f'{key} + "|" + STR([QA KF Bar Id])', keys))
    f['QA KF Day Text'] = _calc('QA KF Day Text', 'Weekday initials under the bars.', _case('[Node Path Index]', {i: WEEK[i] for i in range(7)}))
    f['QA KF Day Point'] = _calc('QA KF Day Point', 'Under each bar.', _case('[Node Path Index]', {i: at(bx(i) + 4, 40) for i in range(7)}, quote=False))
    t = {k: (SP_MEA if k.endswith('Point') else S_DIM) for k in f}
    t.update({'QA KF Slot': I_DIM, 'Is QA KF Row': B_DIM, 'QA KF Bar Id': I_DIM})
    return f, t


_f, _t = dict(), dict(PACK_TYPES)
for fn in (kpi_calcs, kf_calcs):
    a, b = fn()
    _f.update(a)
    _t.update(b)
_fi, _ti, ISSUE_PANE = barlist_calcs('QA Issues', issue_items(), COMBO, 'amber', ISSUE_ROW)
_fc, _tc, COVER_PANE = barlist_calcs('QA Cover', cover_items(), '[p_platform]', 'accent blue', COVER_ROW)
_f.update({**_fi, **_fc})
_t.update({**_ti, **_tc})
CALCS.add(formulas=_f, types=_t)


# ================================================================ sheets

def _a(n):
    return R(n, 'attr')


def _tip(title, text_):
    return [run(title, 7, INK3, SEMI), run(NL, 7, INK3), run(text_, 9, INK1)]


def kpi_sheets() -> list[Sheet]:
    node = R('Is Platform Match Node')
    fail = [run('FAILING RIGHT NOW', 8, INK3, SEMI), run(NL, 8, INK3), run(R('Tests Failing Now'), 18, NAVY, SEMI), run(' tests', 9, INK3),
            run(NL, 8, INK3), run(R('QA Failing Now Name'), 8, CRIT_INK, SEMI), run(R('QA All Passing Text'), 8, INK3)]
    ran = [run('TESTS RUN IN PERIOD', 8, INK3, SEMI), run(NL, 8, INK3), run(R('QA Tests Run Text'), 18, NAVY, SEMI)]
    cov = [run('MODEL TEST COVERAGE', 8, INK3, SEMI), run(NL, 8, INK3), run(R('Model Test Coverage'), 18, NAVY, SEMI), run(NL, 8, INK3),
           run(R('QA No Tests Text'), 8, INK3)]
    refs = lambda rs: [r['_ref'] for r in rs if '_ref' in r]
    return [
        Sheet('QA Failing Now KPI', filters=[node], panes=label_pane(text=refs(fail), valign='top', label=fail,
              tooltip=_tip('FAILING RIGHT NOW', 'Tests with a failure on the last day (19 Oct).'))),
        Sheet('QA Tests Run KPI', filters=[R('Is Platform Match Day')], panes=label_pane(text=refs(ran), valign='top', label=ran,
              tooltip=_tip('TESTS RUN IN PERIOD', 'Test executions in the window: passed, warned and failed.'))),
        Sheet('QA Tests Defined Label', filters=[node], tooltip=False,
              panes=label_pane(text=[R('QA Tests Defined Text')], valign='top', label=[run(R('QA Tests Defined Text'), 8, INK3)])),
        Sheet('QA Test Coverage KPI', filters=[node], formats={R('Model Test Coverage'): 'p0%'},
              panes=label_pane(text=refs(cov), valign='top', label=cov, tooltip=_tip('MODEL TEST COVERAGE', 'Models with at least one dbt test.'))),
    ]


def heatmap_sheet() -> Sheet:
    order, name, fail, warn = R('Heat Order'), R('node_name'), R('Heat Fail Text'), R('Heat Warn Text')
    day, key = R(DATE, kind='ok'), R('Heat Cell Key')
    color_map(key, {'"No run"': '#f1f2f0', '"All passed"': '#e3f2e9', '"Warning"': WARN, '"Failed"': CRIT})
    tip = [run(_a('node_name'), 9, INK1, SEMI), run(NL, 7, INK3), run(R(DATE, 'attr'), 7, INK3, SEMI), run('   ', 7, INK3),
           run(_a('Heat Cell Key'), 9, NAVY, SEMI)]
    label = []
    # model names left-aligned (GB, v38)
    for f_, size, colour, align, bold in ((name, 8, INK1, 'left', False), (fail, 8, CRIT_INK, 'right', True), (warn, 8, WARN_INK, 'right', True)):
        label += [f"            <format attr='font-size' field='{f_.ref}' value='{size}' />",
                  f"            <format attr='color' field='{f_.ref}' value='{colour}' />",
                  f"            <format attr='text-align' field='{f_.ref}' value='{align}' />"]
        if bold:
            label.append(f"            <format attr='font-weight' field='{f_.ref}' value='bold' />")
    no_bands = {el: [f"            <format attr='band-color' scope='{s}' value='#00000000' />" for s in ('rows', 'cols')] for el in ('pane', 'header')}
    return Sheet('QA Test Heatmap', rows=[order, name, fail, warn], cols=[day],
                 filters=[R('Is In Heatmap Span'), R('Has Test Issue In Period'), R('Is Platform Match Node'), R('Is Model')],
                 hide=[order, day], header_width={name: NAME_W, fail: FAIL_W, warn: WARN_W}, row_height=(warn, HEAT_ROW),
                 zoom='fit-width', formats={R(DATE, 'attr'): '*ddd d mmm'}, extra={'label': label, **no_bands},
                 panes=Pane('Square', color=key, size=1.8, label_show=False, tooltip=tip))


def date_strips() -> list[Sheet]:
    x, head = R('Days Back Mid'), R('QA Strip Header')
    out = []
    for span, lab in ((30, 'QA Monday Label 30'), (90, 'QA Monday Label')):
        lab_r = R(lab)
        out.append(Sheet(f'QA Heatmap Dates {span}', rows=[head], cols=[x], hide=[x], fixed={x: (0, span, {'reverse': 'true'})},
                         filters=[R('Is In Heatmap Span')], header_width={head: NAME_W + FAIL_W + WARN_W}, tooltip=False,
                         panes=label_pane(text=[lab_r], label=[run(lab_r, 7, INK3)], align='center')))
    return out


def _poly(title, point, pane, path, lod, colour=None, mark=None):
    return Pane('Polygon', title=title, inert=True, color=colour, mark_color=mark, path=path, label_show=False,
                lod=[R(point, 'clct'), *lod], pane_size=pane)


def _words(title, point, runs, pane, lod, tooltip=None):
    return label_pane(title=title, inert=tooltip is None, text=[r['_ref'] for r in runs if '_ref' in r], label=runs, align='center',
                      valign='center', lod=[R(point, 'clct'), *lod], pane_size=pane, tooltip=tooltip)


def kf_sheet() -> Sheet:
    slot, path = R('QA KF Slot', kind='ok'), R('Node Path Index', kind='ok')
    bar_id, pane = R('QA KF Bar Id'), KF_ROW
    color_map(R('QA KF Bar Key'), {'"Fail"': CRIT, '"Warn"': WARN, '"None"': LINE})
    tip = [run(_a('QA KF Name Text'), 9, INK1, SEMI), run(NL, 7, INK3), run(_a('QA KF Tip Text'), 8, INK2), run(NL, 7, INK3),
           run(_a('QA KF Fail Text'), 8, CRIT_INK, SEMI), run(_a('QA KF Warn Text'), 8, WARN_INK)]
    layers = [
        _poly('Bars', 'QA KF Bar Point', pane, path, [slot, bar_id], colour=R('QA KF Bar Key')),
        _words('Name', 'QA KF Name Point', [run(_a('QA KF Name Text'), 8, INK1)], pane, [slot], tooltip=tip),
        _words('Fail', 'QA KF Fail Point', [run(_a('QA KF Fail Text'), 8, CRIT_INK, SEMI)], pane, [slot]),
        _words('Warn', 'QA KF Warn Point', [run(_a('QA KF Warn Text'), 8, WARN_INK)], pane, [slot]),
        _words('Days', 'QA KF Day Point', [run(_a('QA KF Day Text'), 6, INK4)], pane, [slot, R('Node Path Index')]),
    ]
    return _grid(Sheet('QA Keeps Failing Tests', rows=[Cross([slot, LAT])], cols=[LON], filters=[R('Is QA KF Row')], hide=[slot],
                       layers=True, no_basemap=True, zoom=None, panes=[Pane('Automatic', lod=[slot], pane_size=pane), *layers]), pane)


def barlist_sheet(name, prefix, pane, colour) -> Sheet:
    sid, path = R(f'{prefix} Shape Id'), R('day_index', kind='ok')
    layers = [
        _poly('Track', f'{prefix} Track Point', pane, path, [sid], mark='#eef0ee'),
        _poly('Bar', f'{prefix} Bar Point', pane, path, [sid], mark=colour),
        _words('Name', f'{prefix} Label Point', [run(_a(f'{prefix} Label Text'), 8, INK1)], pane, [R('day_index')]),
        _words('Value', f'{prefix} Value Point', [run(_a(f'{prefix} Value Text'), 8, INK1, SEMI)], pane, [R('day_index')]),
    ]
    return _grid(Sheet(name, rows=[LAT], cols=[LON], layers=True, no_basemap=True, zoom=None, tooltip=False,
                       panes=[Pane('Automatic', pane_size=pane), *layers]), pane)


def sheets() -> list[Sheet]:
    return (kpi_sheets() + [heatmap_sheet(), *date_strips(), kf_sheet(),
                            barlist_sheet('QA Issues by Type Bar', 'QA Issues', ISSUE_PANE, WARN),
                            barlist_sheet('QA Coverage by Domain Bar', 'QA Cover', COVER_PANE, ACCENT)])


# ================================================================ dashboard content (build plan 3.5)

def content() -> Z:
    widths = [318, 317, 318, 317]
    names = [('Test Pass', ['HO Test Pass KPI']), ('Failing Now', ['QA Failing Now KPI']),
             ('Tests Run', ['QA Tests Run KPI', 'QA Tests Defined Label']), ('Coverage', ['QA Test Coverage KPI'])]
    kpis = []
    for i, ((n, ws), w) in enumerate(zip(names, widths)):
        margins = {}
        if i > 0:
            margins['left'] = 7
        if i < 3:
            margins['right'] = 7
        kids = [sheet(ws[0], 48 if len(ws) > 1 else None)] + [sheet(s) for s in ws[1:]]
        kpis.append(card(f'QA KPI {n} Card', kids, fixed=w, pad=(12, 14, 10, 14), margins=margins))
    sq = lambda c, label, last=False: [run('■ ', 8, c), run(label + ('' if last else '     '), 8, INK2)]
    heat = card('QA Heatmap Card', margins={'right': 7}, kids=[
        Z('horz', friendly='QA Heatmap Header', fixed=58, kids=[
            card_header('Test outcomes by model and day', 'Worst test result per model per day. Models with any warning or failure '
                        'in this period, most failures first. Look for repeating columns.', None),
            text(sq('#cfe8da', 'Passed') + sq(WARN, 'Warning') + sq(CRIT, 'Failed') + [run(NL, 8, INK2)] + sq('#e3e4e1', 'No run', True),
                 fixed=200)]),
        # the date strip for the span on show, with room on the right for the heatmap's scroll bar
        Z('horz', friendly='QA Dates 30 Holder', fixed=16, dzv=('Show QA Dates 30', True), style={'padding-right': '18'},
          kids=[sheet('QA Heatmap Dates 30')]),
        Z('horz', friendly='QA Dates 90 Holder', fixed=16, dzv=('Show QA Dates 90', False), style={'padding-right': '18'},
          kids=[sheet('QA Heatmap Dates 90')]),
        sheet('QA Test Heatmap')])
    right = Z('vert', friendly='QA Right Column', fixed=RIGHT_W, style={'margin-left': '7'}, kids=[
        card('QA Keeps Failing Card', margins={'bottom': 7}, kids=[
            card_header('Tests that keep failing', 'Days with a failure or warning in this period, and which weekdays they land on'),
            sheet('QA Keeps Failing Tests')]),
        card('QA Issues Type Card', fixed=ISSUES_H - 14, margins={'top': 7, 'bottom': 7}, kids=[
            card_header('Issues by test type', 'Failures and warnings in this period'),
            sheet('QA Issues by Type Bar')]),
        card('QA Coverage Card', fixed=COVER_H - 7, margins={'top': 7}, kids=[
            card_header('Test coverage by domain', 'Share of models with at least one test'),
            sheet('QA Coverage by Domain Bar')])])
    return Z('vert', friendly='QA Content', style=CONTENT_PAD, kids=[
        Z('horz', friendly='QA KPI Row', fixed=KPI_H, kids=kpis),
        # the last row is flexible, so it always reaches the bottom padding (skill: sizing)
        Z('horz', friendly='QA Body', style={'margin-top': '14'}, kids=[heat, right])])


def check_fit(zones) -> None:
    by = {(z.name or z.friendly): z.rect for z in zones}
    for name, (w, h) in (('QA Keeps Failing Tests', (KF_W + 18, 0)), ('QA Issues by Type Bar', ISSUE_PANE),
                         ('QA Coverage by Domain Bar', COVER_PANE)):
        _, _, zw, zh = by[name]
        assert w <= zw and h <= zh, f'{name}: needs {w} x {h}, zone is {zw:.0f} x {zh:.0f}'
    _, y, _, h = by['QA Body']
    end = 1000 - int(CONTENT_PAD['padding-bottom'])
    assert abs(y + h - end) < 0.5, f'QA rows end at {y + h:.0f}, content ends at {end}'


ACTIONS = []
NAV_ACTIONS = []
DEHIGHLIGHT = []
