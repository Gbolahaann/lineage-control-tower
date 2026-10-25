"""Tab 3, Freshness & SLAs (FR): calc pack section 8, build plan 3.6.

GB's choices (24 Oct): the source bullets and "Late right now" as pixel canvases matching the prototype, the
compliance lines and the calendar native, today's calendar square outlined navy (the border technique from
Run & failures).

- Bullets: one 611 x 19 px map pane per source (like the Lineage table), zones and lag bar as polygons from the
  source's 90 Node Daily rows, each on its own scale (0 to the larger of 1.25 x the error threshold or 1.05 x the
  lag, as the prototype draws it), name and lag value placed at widths measured by the build.
- Compliance: the shared reversed day axis of Run & failures, the window band as back bars, one line per platform
  with its name at the line end, an incident strip above (freshness incidents) and a date strip below.
- Late right now: "now" is fixed at the as-of date, so the build lays the card out (pill, name, reason, wrapped
  chips) and draws it on the 90-row date table: 8 rows per rounded shape, one row per text. The platform filter
  still applies (each part checks the source's platform). Clicking a chip opens that data product in Lineage.
"""

from __future__ import annotations

import csv

from . import shapes as SH
from .core import (ACCENT, B_DIM, BOOK, CALCS, CARD, CRIT, CRIT_INK, CRIT_TINT, GOOD, GOOD_TINT, I_DIM, I_MEA, INK1, INK2,
                   INK3, LAT, LINE, LON, MEASURE_NAMES, NAVY, NL, PLAT, R_MEA, S_DIM, S_MEA, SEMI, SP_MEA, WARN, WARN_INK,
                   WARN_TINT, Cross, Nest, Pane, R, Sheet, Z, blank, card, card_header, color_map, label_pane, run, sheet,
                   text)
from .lineage import _fit, _grid, _q, _wrap
from .run import BAND, _axis_style
from .shell import CONTENT_H, CONTENT_PAD

P = 'FR'
DATE = 'date (dim_date.csv)'
ROOT = SH.ROOT
NODES = list(csv.DictReader(open(ROOT / 'data' / 'marts' / 'dim_nodes.csv', encoding='utf-8')))
BY_ID = {r['node_id']: r for r in NODES}
SOURCES = [r for r in NODES if r['resource_type'] == 'source']
BLAST = list(csv.DictReader(open(ROOT / 'data' / 'marts' / 'mart_blast_radius.csv', encoding='utf-8')))
PLAT_NAME = {'snowflake': 'Snowflake', 'databricks': 'Databricks', 'redshift': 'Redshift'}

# ---------------------------------------------------------------- geometry (content 1312 x CONTENT_H)
RIGHT_W = 649                                   # right column; 7 px margin-left outside
LEFT_W = 1312 - RIGHT_W - 7 - 7                 # 649: bullets card, 7 px margin-right outside
BW = LEFT_W - 2 * 16 - 2 - SH.MAP_SLACK        # 603: bullet canvas width
ROW = (BW, 22)                                  # one pane per source: 27 rows fill about 594 px (GB: about 607, v29)
NAME_W, VALUE_W, GAP = 200, 64, 10              # prototype .brow: 200px | bullet | 64px, gap 10
BX0, BX1 = NAME_W + GAP, BW - VALUE_W - GAP     # 210 .. 537: the bullet
BY0, BY1, LY0, LY1 = 4, 18, 8.5, 13.5           # bullet band 14 px, lag bar 5 px centred in it
COMP_H = 411                                    # compliance card; the bottom row takes the rest
CAL_OUT = 320                                   # calendar card 313 px with its 7 px margin (GB, Pre-Final; v30 was 289)
LATE_W = RIGHT_W - CAL_OUT - 7                  # 322: late-now card takes the rest (its 7 px margin outside)
LW = LATE_W - 2 * 16 - 2 - SH.MAP_SLACK         # 276: late-now canvas; v48's 8 px spare still drew a scroll bar
LH_AVAIL = (CONTENT_H - COMP_H - 7 - 7) - 28 - 2 - 44 - 12   # room inside the card; the canvas is only as tall as its content
X_AXIS = (0, 90, {'reverse': 'true'})           # Days Back Mid, as on Run & failures
# 7-day rolling compliance never drops below 99.4 %, so the axis is 99 % to 100 % (GB, v30: the daily spikes on 0 % to
# 100 % were unreadable). Ticks automatic: decimal tick settings broke the axis ("nan", v29).
Y0, Y1 = 0.99, 1.0
PCT_Y = (Y0, Y1)
PCT = 'p0.0%'
CHIP_BG, CHIP_LINE = '#f5f5f3', LINE
PILL = {2: ('▲  Warning', WARN_INK, WARN_TINT, '#f3e0be'), 3: ('✕  Critical', CRIT_INK, CRIT_TINT, '#f2cdca')}


def _hrs(m):
    """The prototype's fHrs: minutes under an hour, otherwise hours with one decimal."""
    m = float(m or 0)
    return f'{round(m)} min' if m < 60 else f'{m / 60:.1f} h'


def _case(field, values, default='NULL', quote=True):
    body = '\n'.join(f'WHEN {_q(k)} THEN {_q(v) if quote else v}' for k, v in values.items())
    return f'CASE [{field}]\n{body}\nELSE {default}\nEND'


# ================================================================ bullets (Node Daily rows, one pane per source)

def _bx(frac):
    return f'({BX0} + ({BX1 - BX0}) * ({frac}))'


def _rect(x0, x1, y0, y1):
    """Rectangle from the Node Path Index (0 to 87): the four corners, 22 points each."""
    lon = lambda x: f'(({x}) - {BW / 2:g}) / 100'
    lat = lambda y: f'{(ROW[1] / 2 - y) / 100:.4f}'
    k = 'INT([Node Path Index] / 22)'
    return (f'MAKEPOINT(\n    CASE {k} WHEN 0 THEN {lat(y0)} WHEN 1 THEN {lat(y0)} WHEN 2 THEN {lat(y1)} ELSE {lat(y1)} END,\n'
            f'    CASE {k} WHEN 0 THEN {lon(x0)} WHEN 1 THEN {lon(x1)} WHEN 2 THEN {lon(x1)} ELSE {lon(x0)} END\n)')


def bullet_calcs():
    scale = 'MAX([error_after_minutes] * 1.25, ZN([freshness_lag_min]) * 1.05)'
    names = {r['node_id']: _fit(r['display_name'], NAME_W - 4, 8) for r in SOURCES}
    values = {r['node_id']: _hrs(r['freshness_lag_min']) for r in SOURCES}
    f = {
        'Bullet Scale': ('// Bullet Scale\n// Each source on its own scale, as the prototype: to 1.25 x its error threshold, or past its lag.\n' + scale),
        'Bullet Order': ('// Bullet Order\n// Latest relative to its SLA first (Lag Sort turned around, so the natural order is the right one).\n'
                         '-[Lag Sort]'),
        'Bullet Good Zone Point': ('// Bullet Good Zone Point\n// On-time zone, 0 to the warn threshold (green tint).\n'
                                   + _rect(_bx('0'), _bx('[warn_after_minutes] / [Bullet Scale]'), BY0, BY1)),
        'Bullet Warn Zone Point': ('// Bullet Warn Zone Point\n// Warn zone, warn to error threshold (amber tint).\n'
                                   + _rect(_bx('[warn_after_minutes] / [Bullet Scale]'), _bx('[error_after_minutes] / [Bullet Scale]'), BY0, BY1)),
        'Bullet Error Zone Point': ('// Bullet Error Zone Point\n// Past the error threshold (red tint), to the end of the scale.\n'
                                    + _rect(_bx('[error_after_minutes] / [Bullet Scale]'), _bx('1'), BY0, BY1)),
        'Bullet Lag Bar Point': ('// Bullet Lag Bar Point\n// The lag now, a 4 px bar in the status colour (at least 0.5 % long, as the prototype).\n'
                                 + _rect(_bx('0'), _bx('MAX(0.005, ZN([freshness_lag_min]) / [Bullet Scale])'), LY0, LY1)),
        'Bullet Name Text': ('// Bullet Name Text\n// Source name, cut by the build to its 200 px column.\n' + _case('node_id (dim_nodes.csv)', names)),
        'Bullet Value Text': ('// Bullet Value Text\n// Lag now as the prototype writes it: "44 min", "6.0 h" (written by the build from dim_nodes).\n'
                              + _case('node_id (dim_nodes.csv)', values)),
        'Bullet Value Critical': '// Bullet Value Critical\n// Lag value, red bold.\nIF [current_status_code] = 3 THEN [Bullet Value Text] END',
        'Bullet Value Warning': '// Bullet Value Warning\n// Lag value, amber bold.\nIF [current_status_code] = 2 THEN [Bullet Value Text] END',
        'Bullet Value Normal': '// Bullet Value Normal\n// Lag value, grey, on time.\nIF [current_status_code] < 2 THEN [Bullet Value Text] END',
        'Bullet Name Point': ('// Bullet Name Point\n// Name, left-aligned: centred half its measured width in from the left edge.\n'
                              'MAKEPOINT(0, (' + _case('node_id (dim_nodes.csv)', {k: f'{SH.text_width(v, 8) / 2:.1f}' for k, v in names.items()}, '0', False)
                              + f' - {BW / 2:g}) / 100)'),
        'Bullet Value Point': ('// Bullet Value Point\n// Value, right-aligned: centred half its measured width in from the right edge.\n'
                               f'MAKEPOINT(0, ({BW / 2:g} - '
                               + _case('node_id (dim_nodes.csv)', {k: f'{SH.text_width(v, 8, True) / 2:.1f}' for k, v in values.items()}, '0', False)
                               + ') / 100)'),
        'Bullet Lag Tip': '// Bullet Lag Tip\n// LAG NOW in the tooltip.\n[Bullet Value Text]',
        'Bullet Warn Tip': ('// Bullet Warn Tip\n// WARN AFTER in the tooltip.\n'
                            + _case('node_id (dim_nodes.csv)', {r['node_id']: _hrs(r['warn_after_minutes']) for r in SOURCES})),
        'Bullet Error Tip': ('// Bullet Error Tip\n// ERROR AFTER in the tooltip.\n'
                             + _case('node_id (dim_nodes.csv)', {r['node_id']: _hrs(r['error_after_minutes']) for r in SOURCES})),
    }
    t = {n: SP_MEA for n in f if n.endswith('Point')}
    t.update({n: S_DIM for n in f if n.endswith(('Text', 'Critical', 'Warning', 'Normal', 'Tip'))})
    t.update({'Bullet Scale': R_MEA, 'Bullet Order': ('real', 'dimension', 'ordinal')})
    return f, t


# ================================================================ late right now (laid out by the build)

def _late_layout():
    """Blocks for the late sources, as the prototype: pill and name, reason, then the waiting data products as
    chips wrapped to the card. Returns shapes [(kind, x0, y0, x1, y1, source, exposure)] and texts
    [(style, text, cx, cy, source)]."""
    late = sorted([r for r in SOURCES if r['current_status_code'] in ('2', '3')],
                  key=lambda r: -float(r['freshness_lag_min'] or 0) / float(r['error_after_minutes']))
    shapes, texts, y = [], [], 6
    for r in late:
        s = int(r['current_status_code'])
        label = PILL[s][0]
        pw = SH.text_width(label, 7, True) + 16
        shapes.append((f'pill{s}', 0, y, pw, y + 16, r['node_id'], None))
        texts.append(('pill', label, pw / 2, y + 8, r['node_id']))
        nm = _fit(r['display_name'], LW - pw - 8, 8, True)
        texts.append(('name', nm, pw + 8 + SH.text_width(nm, 8, True) / 2, y + 8, r['node_id']))
        y += 16 + 4
        for line in _wrap(r['status_reason'], LW, 8):
            texts.append(('reason', line, SH.text_width(line, 8) / 2, y + 7, r['node_id']))
            y += 14
        y += 4
        x = 0
        for b in [b for b in BLAST if b['node_id'] == r['node_id']]:
            t = _fit(b['exposure_name'], LW - 12, 7)
            w = SH.text_width(t, 7) + 12
            if x and x + w > LW:
                x, y = 0, y + 16 + 4
            shapes.append(('chip', x, y, x + w, y + 16, r['node_id'], b['exposure_id']))
            texts.append(('chip', t, x + w / 2, y + 8, r['node_id']))
            x += w + 4
        y += 16 + 14
    y -= 14
    assert len(shapes) <= 11, f'Late right now: {len(shapes)} shapes, the 90-row scaffold holds 11 (8 rows each)'
    assert len(texts) <= 90 and y <= LH_AVAIL, f'Late right now: {len(texts)} texts, {y:.0f} of {LH_AVAIL} px'
    return late, shapes, texts, y


_LATE = _late_layout()
LH = int(_LATE[3]) + 4                          # the canvas fits its content (v29 was the card's full height: scroll bars)


def _platform_ok(source_id):
    p = BY_ID[source_id]['platform_now']
    return f'([p_platform] = "All" OR [p_platform] = {_q(p)})'


def _chamfer(x0, y0, x1, y1, r):
    """8 points round a rectangle with 45-degree corners of r px (2 per corner): reads as rounded at chip size."""
    return [(x0 + r, y0), (x1 - r, y0), (x1, y0 + r), (x1, y1 - r), (x1 - r, y1), (x0 + r, y1), (x0, y1 - r), (x0, y0 + r)]


def late_calcs():
    late, shapes, texts, _y = _LATE
    lat = lambda y: f'{(LH / 2 - y) / 100:.4f}'
    lon = lambda x: f'{(x - LW / 2) / 100:.4f}'

    def shape_points(kinds, inset):
        rows = []
        for i, (kind, x0, y0, x1, y1, src, _) in enumerate(shapes):
            if not kind.startswith(kinds):
                continue
            for j, (x, y) in enumerate(_chamfer(x0 + inset, y0 + inset, x1 - inset, y1 - inset, 3 - inset)):
                rows.append(f'WHEN {i * 8 + j} THEN IIF({_platform_ok(src)}, MAKEPOINT({lat(y)}, {lon(x)}), NULL)')
        return 'CASE [day_index]\n' + '\n'.join(rows) + '\nEND'
    f = {
        'Late Shape Id': '// Late Shape Id\n// Which pill or chip a scaffold row draws (8 rows each).\nINT([day_index] / 8)',
        'Late Shape Point Order': '// Late Shape Point Order\n// Point 0 to 7 round the shape (path).\n[day_index] % 8',
        'Late Pill Border Point': '// Late Pill Border Point\n// Status pill outline (written by the build).\n' + shape_points('pill', 0),
        'Late Pill Fill Point': '// Late Pill Fill Point\n// Status pill fill, 1 px inside.\n' + shape_points('pill', 1),
        'Late Chip Border Point': '// Late Chip Border Point\n// Data product chip outline.\n' + shape_points('chip', 0),
        'Late Chip Fill Point': '// Late Chip Fill Point\n// Data product chip fill, 1 px inside (takes the click).\n' + shape_points('chip', 1),
        'Late Pill Key': ('// Late Pill Key\n// Pill colours by status.\nCASE INT([day_index] / 8)\n'
                          + '\n'.join(f'WHEN {i} THEN {_q("Critical" if k == "pill3" else "Warning")}' for i, (k, *_r) in enumerate(shapes) if k.startswith('pill'))
                          + '\nEND'),
    }
    chips = {i: e for i, (k, _a, _b, _c, _d, _s, e) in enumerate(shapes) if k == 'chip'}
    ex = lambda e, col: BY_ID[e][col]
    tags = lambda e: '|' + ('moved|' if ex(e, 'migrated_from_platform') else '') + ('ai|' if ex(e, 'build_method') == 'ai_assisted' else '') \
        + ('unregistered|' if ex(e, 'is_declared') != 'True' else '')
    for name, why, val, quote in (('Late Chip Exposure', 'The data product a chip opens (p_selected_exposure).', lambda e: e, True),
                                  ('Late Chip Status', 'Its status code, for the Lineage panel (p_panel_status).', lambda e: ex(e, 'current_status_code'), False),
                                  ('Late Chip Type', 'Its type, for the Lineage panel (p_panel_type).', lambda e: ex(e, 'resource_type'), True),
                                  ('Late Chip Platform', 'Its platform, for the Lineage panel (p_panel_platform).', lambda e: ex(e, 'platform_now'), True),
                                  ('Late Chip Tags', 'Its tags, for the Lineage panel (p_panel_tags).', tags, True)):
        f[name] = (f'// {name}\n// {why}\nCASE INT([day_index] / 8)\n'
                   + '\n'.join(f'WHEN {i} THEN {_q(val(e)) if quote else val(e)}' for i, e in chips.items()) + '\nEND')
    rows = '\n'.join(f'WHEN {t} THEN IIF({_platform_ok(src)}, MAKEPOINT({lat(cy)}, {lon(cx)}), NULL)' for t, (_s, _x, cx, cy, src) in enumerate(texts))
    f['Late Text Point'] = '// Late Text Point\n// Every text on the card, one scaffold row each (centred at half its measured width).\nCASE [day_index]\n' + rows + '\nEND'
    for style in ('pill', 'name', 'reason', 'chip'):
        n = f'Late {style.title()} Text'
        f[n] = (f'// {n}\n// The {style} texts (written by the build).\nCASE [day_index]\n'
                + '\n'.join(f'WHEN {t} THEN {_q(x)}' for t, (st, x, *_r) in enumerate(texts) if st == style) + '\nEND')
    shown = ' OR '.join(_platform_ok(r['node_id']) for r in late) or 'FALSE'
    f['Late Empty Point'] = ('// Late Empty Point\n// "Every source is on time." when no late source is in the platform filter.\n'
                             f'IF [day_index] = 0 AND NOT ({shown}) THEN MAKEPOINT({lat(14)}, {lon(SH.text_width("Every source is on time.", 8) / 2)}) END')
    f['Late Empty Text'] = '// Late Empty Text\n// The empty state.\n"Every source is on time."'
    t = {n: SP_MEA for n in f if n.endswith('Point')}
    t.update({'Late Shape Id': I_DIM, 'Late Shape Point Order': I_DIM, 'Late Chip Status': I_DIM})
    t.update({n: S_DIM for n in f if n not in t})
    return f, t


# ================================================================ native charts and the calendar

def chart_calcs():
    f = {
        'Compliance Band': ('// Compliance Band\n// The window band: a Gantt bar from the bottom of the axis (99%) on days in the window. A bar from\n'
                            '// zero made Tableau show 0 % to 100 % (v30).\n'
                            'IF MAX(IIF([In Period], 1, 0)) = 1 THEN 0.99 END'),
        'Compliance Band Length': '// Compliance Band Length\n// The band\'s length: the whole axis.\nMIN(0.0100)',
        'Freshness Pass Rate 7 Day': ('// Freshness Pass Rate 7 Day\n// Share of hourly checks on time over the 7 days up to each day, per platform (GB, v30: a\n'
                                      '// trend rather than daily spikes). Table calc along Days Back Mid: the 6 days before are +1 to +6.\n'
                                      'WINDOW_SUM(SUM([fresh_checks_pass]), 0, 6)\n/\n'
                                      'WINDOW_SUM(SUM([fresh_checks_pass] + [fresh_checks_warn] + [fresh_checks_error]), 0, 6)'),
        'Freshness Incident Tick': ('// Freshness Incident Tick\n// Tick under a freshness incident\'s label (INC 6, INC 8): a Gantt bar from the axis bottom.\n'
                                    'IF COUNT(IF [category] = "freshness" THEN [incident_id] END) > 0 THEN 0.99 END'),
        'Freshness Incident Tick Length': '// Freshness Incident Tick Length\n// How far the tick reaches up the strip.\nMIN(0.00420)',
        'Freshness Incident Anchor': ('// Freshness Incident Anchor\n// Point the label sits above.\n'
                                      'IF COUNT(IF [category] = "freshness" THEN [incident_id] END) > 0 THEN 0.99460 END'),
        'Freshness Incident Label': ('// Freshness Incident Label\n// "INC 6" over freshness incidents only (the prototype filters to them).\n'
                                     'IF [category] = "freshness" THEN [Incident Marker Label] END'),
        'Compliance Axis Anchor': ('// Compliance Axis Anchor\n// Date labels under the compliance chart (its 90 % to 100 % scale).\n'
                                   'IF NOT ISNULL(MIN([Axis Date Label])) THEN 0.9950 END'),
        'Calendar Day Short': '// Calendar Day Short\n// "Mon" ... "Sun" down the calendar.\nLEFT([day_name], 3)',
        'Calendar Cell': '// Calendar Cell\n// Every day\'s square sits at 0 on a hidden axis.\nMIN(0.0)',
        'Calendar Today': ('// Calendar Today\n// The navy square behind today\'s (a little larger): its outline, as in the prototype.\n'
                           'IF MIN([days_before_as_of]) = 0 THEN 0.0 END'),
        'Late Checks Text': '// Late Checks Text\n// The number in a calendar square, blank on days with none.\nIF [Late Checks (Daily)] > 0 THEN STR([Late Checks (Daily)]) END',
    }
    t = {'Compliance Band': R_MEA, 'Compliance Band Length': R_MEA, 'Freshness Pass Rate 7 Day': R_MEA,
         'Freshness Incident Tick Length': R_MEA, 'Freshness Incident Tick': R_MEA, 'Freshness Incident Anchor': R_MEA,
         'Freshness Incident Label': S_DIM, 'Compliance Axis Anchor': R_MEA, 'Calendar Day Short': S_DIM,
         'Calendar Cell': R_MEA, 'Calendar Today': R_MEA, 'Late Checks Text': S_MEA}
    return f, t


PACK_TYPES = {  # calc pack section 8 (and 2) calcs this tab reads
    'Is Source': B_DIM, 'Lag Sort': R_MEA, 'Latest Check Label': S_MEA, 'Freshness Pass Rate (Daily)': R_MEA,
    'Late Checks (Daily)': I_MEA, 'Late Day Key': S_MEA, 'Platform On Day Name': S_DIM,
}
PACK_TYPES['Lag Sort'] = ('real', 'dimension', 'ordinal')

_f = {}
_t = dict(PACK_TYPES)
for fn in (bullet_calcs, late_calcs, chart_calcs):
    a, b = fn()
    _f.update(a)
    _t.update(b)
CALCS.add(formulas=_f, types=_t, table_calc={'Freshness Pass Rate 7 Day': 'Days Back Mid'})


# ================================================================ sheets

def bullet_sheet() -> Sheet:
    key, order = R('node_id (dim_nodes.csv)'), R('Bullet Order')
    path = R('Node Path Index', kind='ok')
    a = lambda n: R(n, 'attr')
    tip = [run(a('display_name'), 9, INK1, SEMI), run(NL, 7, INK3),
           run('LAG NOW   ', 7, INK3, SEMI), run(a('Bullet Lag Tip'), 9, NAVY, SEMI), run(NL, 7, INK3),
           run('WARN AFTER   ', 7, INK3, SEMI), run(a('Bullet Warn Tip'), 9, NAVY, SEMI), run(NL, 7, INK3),
           run('ERROR AFTER   ', 7, INK3, SEMI), run(a('Bullet Error Tip'), 9, NAVY, SEMI), run(NL, 7, INK3),
           run('CHECKED   ', 7, INK3, SEMI), run(a('Last Event Label'), 9, NAVY, SEMI), run(NL, 7, INK3),
           run('PLATFORM   ', 7, INK3, SEMI), run(a('Platform Name'), 9, NAVY, SEMI), run(NL, 7, INK3),
           run('FEEDS   ', 7, INK3, SEMI), run(R('exposures_fed', 'sum'), 9, NAVY, SEMI), run(' exposures', 9, INK3)]

    def zone(title, point, colour=None, mark=None, inert=True, tooltip=None):
        return Pane('Polygon', title=title, inert=inert, color=colour, mark_color=mark, path=path, label_show=False,
                    lod=[R(point, 'clct'), key], pane_size=ROW, tooltip=tooltip)

    def words(title, point, runs, tooltip=None):
        return label_pane(title=title, inert=tooltip is None, text=[r['_ref'] for r in runs if '_ref' in r], label=runs,
                          align='center', valign='center', lod=[R(point, 'clct'), key], pane_size=ROW, tooltip=tooltip)
    layers = [
        zone('Good zone', 'Bullet Good Zone Point', mark=GOOD_TINT),
        zone('Warn zone', 'Bullet Warn Zone Point', mark=WARN_TINT),
        zone('Error zone', 'Bullet Error Zone Point', mark=CRIT_TINT),
        zone('Lag', 'Bullet Lag Bar Point', colour=R('Status Label'), inert=False, tooltip=tip),
        words('Name', 'Bullet Name Point', [run(R('Bullet Name Text'), 8, INK1)]),
        words('Value', 'Bullet Value Point', [run(R('Bullet Value Critical'), 8, CRIT, SEMI), run(R('Bullet Value Warning'), 8, WARN, SEMI),
                                              run(R('Bullet Value Normal'), 8, INK2)], tooltip=tip),
    ]
    return _grid(Sheet('FR Source Lag Bullets', rows=[Cross([Nest([order, key]), LAT])], cols=[LON],
                       filters=[R('Is Source'), R('Is Platform Match Node')], hide=[order, key], layers=True,
                       no_basemap=True, zoom=None, panes=[Pane('Automatic', lod=[key], pane_size=ROW), *layers]), ROW)


def latest_check_sheet() -> Sheet:
    return Sheet('FR Latest Check Label', filters=[R('Is Source'), R('Is Platform Match Node')], tooltip=False,
                 panes=label_pane(text=[R('Latest Check Label')], label=[run(R('Latest Check Label'), 8, INK3)]))


def compliance_sheets() -> list[Sheet]:
    x, band, rate = R('Days Back Mid'), R('Compliance Band'), R('Freshness Pass Rate 7 Day')
    plat = R('Platform On Day Name')
    color_map(plat, {f'"{v}"': PLAT[k] for k, v in PLAT_NAME.items()})
    tip = [run(R('Tooltip Day Text'), 9, INK1, SEMI), run(NL, 7, INK3), run(R(plat.name, 'attr'), 7, INK3, SEMI), run('   ', 7, INK3),
           run(rate, 9, NAVY, SEMI), run(' of checks on time, last 7 days', 9, INK3)]
    chart = Sheet('FR Compliance by Platform Line', cols=[x], rows=[(band, rate)], filters=[R('Is Platform Match Day')],
                  hide=[x, rate], sync=[rate], fixed={x: X_AXIS, band: PCT_Y}, formats={band: PCT, rate: 'p0.00%'},
                  extra={'axis': _axis_style(band, fmt=PCT)},
                  panes=[Pane('Bar', label_show=False),
                         Pane('GanttBar', axis=band, mark_color=BAND, size=1.9890055656433105, label_show=False,
                              size_field=R('Compliance Band Length')),
                         # no line-end labels: all three lines end at 100 % and the names piled up (v29); legend in the header
                         Pane('Line', axis=rate, color=plat, size=0.207901, label_show=False, tooltip=tip)])  # line size GB, v31
    tick, anchor, lab = R('Freshness Incident Tick'), R('Freshness Incident Anchor'), R('Freshness Incident Label', 'attr')
    itip = [run(R('Incident Marker Label', 'attr'), 9, INK1, SEMI), run(NL, 7, INK3), run(R('title', 'attr'), 9, INK1)]
    incidents = Sheet('FR Incident Markers', cols=[x], rows=[(tick, anchor)], hide=[x, anchor], sync=[anchor],
                      fixed={x: X_AXIS, tick: PCT_Y}, formats={tick: PCT}, extra={'axis': _axis_style(tick, False, PCT)},
                      panes=[Pane('Bar', label_show=False),
                             Pane('GanttBar', axis=tick, size=0.02, mark_color='#a5acb4', label_show=False, tooltip=itip,
                                  size_field=R('Freshness Incident Tick Length')),
                             label_pane(axis=anchor, text=[lab], label=[run(lab, 7, INK2, SEMI)], align='center', valign='top',
                                        tooltip=itip)])
    ax = R('Compliance Axis Anchor')
    dates = Sheet('FR Compliance Axis', cols=[x], rows=[ax], hide=[x], fixed={x: X_AXIS, ax: PCT_Y}, tooltip=False,
                  formats={ax: PCT}, extra={'axis': _axis_style(ax, False, PCT)},
                  panes=label_pane(text=[R('Axis Date Label')], label=[run(R('Axis Date Label'), 8, INK3)], align='center'))
    return [incidents, chart, dates]


def calendar_sheet() -> Sheet:
    dow, day, week = R('day_of_week', kind='ok'), R('Calendar Day Short'), R('week_start', kind='ok')
    cell, today, key = R('Calendar Cell'), R('Calendar Today'), R('Late Day Key')
    color_map(key, {'"Error"': CRIT, '"Warn"': WARN, '"On time"': '#e3f2e9', '"Earlier"': '#eef0ee'})
    tip = [run(R(DATE, 'attr'), 9, INK1, SEMI), run(NL, 7, INK3), run('LATE CHECKS   ', 7, INK3, SEMI),
           run(R('Late Checks (Daily)'), 9, NAVY, SEMI), run(NL, 7, INK3), run('PAST ERROR THRESHOLD   ', 7, INK3, SEMI),
           run(R('fresh_checks_error', 'sum'), 9, CRIT_INK, SEMI)]
    label = [f"            <format attr='font-size' field='{day.ref}' value='7' />",
             f"            <format attr='color' field='{day.ref}' value='{INK3}' />"]
    num = R('Late Checks Text')
    return Sheet('FR Late Checks Calendar', rows=[dow, day], cols=[week, (today, cell)], filters=[R('Is Platform Match Day')],
                 hide=[dow, week, today, cell], sync=[cell], fixed={today: (-1, 1)}, header_width={day: 30},
                 formats={R(DATE, 'attr'): '*ddd d mmm'}, extra={'label': label},
                 panes=[Pane('Square', label_show=False),
                        Pane('Square', axis=today, mark_color=NAVY, size=1.45, label_show=False),
                        Pane('Square', axis=cell, color=key, size=1.2, text=[num], label=[run(num, 7, '#ffffff', SEMI)],
                             align='center', tooltip=tip)])


def late_sheet() -> Sheet:
    pane = (LW, LH)
    order = R('Late Shape Point Order', kind='ok')
    sid = R('Late Shape Id')
    clicks = [R(n) for n in ('Late Chip Exposure', 'Late Chip Status', 'Late Chip Type', 'Late Chip Platform', 'Late Chip Tags',
                             'Clear Node Value', 'Clear Node Key Value')]
    color_map(R('Late Pill Key'), {'"Warning"': WARN_TINT, '"Critical"': CRIT_TINT})
    tip = [run(R('Late Chip Text', 'attr'), 9, INK1, SEMI), run(NL, 7, INK3), run('CLICK TO OPEN ITS LINEAGE', 7, INK3, SEMI)]

    def shape(title, point, colour=None, mark=None, inert=True, lod=(), tooltip=None):
        return Pane('Polygon', title=title, inert=inert, color=colour, mark_color=mark, path=order, label_show=False,
                    lod=[R(point, 'clct'), sid, *lod], pane_size=pane, tooltip=tooltip)

    def words(title, point, field, size, colour, font=BOOK):
        t = R(field)
        return label_pane(title=title, inert=True, text=[t], label=[run(t, size, colour, SEMI if font == 'bold' else BOOK)],
                          align='center', lod=[R(point, 'clct'), R('day_index')], pane_size=pane)
    pill_line = '#f3e0be'
    layers = [
        shape('Pill border', 'Late Pill Border Point', mark=pill_line),
        shape('Pill fill', 'Late Pill Fill Point', colour=R('Late Pill Key')),
        shape('Chip border', 'Late Chip Border Point', mark=CHIP_LINE),
        shape('Chip fill', 'Late Chip Fill Point', mark=CHIP_BG, inert=False, lod=clicks, tooltip=tip),
        words('Pill text', 'Late Text Point', 'Late Pill Text', 7, WARN_INK, 'bold'),
        words('Name', 'Late Text Point', 'Late Name Text', 8, INK1, 'bold'),
        words('Reason', 'Late Text Point', 'Late Reason Text', 8, INK3),
        words('Chip text', 'Late Text Point', 'Late Chip Text', 7, INK2),
        words('Empty', 'Late Empty Point', 'Late Empty Text', 8, INK3),
    ]
    return _grid(Sheet('FR Late Right Now', rows=[LAT], cols=[LON], layers=True, no_basemap=True, zoom=None,
                       panes=[Pane('Automatic', pane_size=pane), *layers]), pane)


def sheets() -> list[Sheet]:
    return [bullet_sheet(), latest_check_sheet(), *compliance_sheets(), calendar_sheet(), late_sheet()]


# ================================================================ dashboard content (build plan 3.6)

def _legend(items):
    rs = []
    for i, (label, colour) in enumerate(items):
        rs += [run('■ ', 8, colour), run(label + ('     ' if i < len(items) - 1 else ''), 8, INK2)]
    return rs


def content() -> Z:
    bullets = card('FR Bullets Card', margins={'right': 7}, kids=[
        card_header('How late is each source right now?',
                    'Lag since last load against its SLA. Green zone is on time, amber is past the warn threshold, red is '
                    'past the error threshold.', 44),
        sheet('FR Latest Check Label', 20),
        sheet('FR Source Lag Bullets')])
    compliance = card('FR Compliance Card', fixed=COMP_H, margins={'bottom': 7}, kids=[
        Z('horz', friendly='FR Compliance Header', fixed=44, kids=[
            card_header('Freshness SLA compliance by platform', 'Share of hourly checks on time over the last 7 days. The axis starts at 99%.',
                        None),
            text(_legend([(v, PLAT[k]) for k, v in PLAT_NAME.items()]), fixed=230)]),
        sheet('FR Incident Markers', 18),
        sheet('FR Compliance by Platform Line'),
        sheet('FR Compliance Axis', 16)])
    calendar = card('FR Calendar Card', fixed=CAL_OUT - 7, margins={'right': 7}, kids=[
        card_header('Late checks by day', 'Number shows late checks. Outlined day is today.'),
        sheet('FR Late Checks Calendar', 7 * 21),  # compact at the top, as the prototype (7 rows of about 18 px squares)
        blank(),
        text(_legend([('Warn', WARN), ('Error', CRIT), ('On time', '#e3f2e9')]), fixed=22, **{'padding-top': '6'})])
    # GB set 393 in Pre-Final; Tableau fits it to the 329 the column has left, which is what "the rest" gives here
    late = card('FR Late Now Card', margins={'left': 7}, kids=[
        card_header('Late right now', 'And the data products waiting on them'),
        sheet('FR Late Right Now', 158)])   # GB, Pre-Final
    right = Z('vert', friendly='FR Right Column', fixed=RIGHT_W, style={'margin-left': '7'}, kids=[
        compliance,
        # the last row is flexible, so it always reaches the bottom padding (skill: sizing)
        Z('horz', friendly='FR Bottom Row', style={'margin-top': '7'}, kids=[calendar, late])])
    return Z('horz', friendly='FR Content', style=CONTENT_PAD, kids=[bullets, right])


def check_fit(zones) -> None:
    by = {(z.name or z.friendly): z.rect for z in zones}
    _, _, zw, zh = by['FR Source Lag Bullets']
    need = (BW, ROW[1] * len(SOURCES))
    assert need[0] <= zw and need[1] <= zh, f'FR Source Lag Bullets: needs {need}, zone is {zw:.0f} x {zh:.0f}'
    _, _, zw, zh = by['FR Late Right Now']
    assert LW <= zw and LH <= zh, f'FR Late Right Now: needs {LW} x {LH}, zone is {zw:.0f} x {zh:.0f}'


ACTIONS = [  # (sheet, source Ref factory, parameter, caption)
    ('FR Late Right Now', lambda: R('Late Chip Exposure'), 'p_selected_exposure', 'FR Late Select Exposure'),
    ('FR Late Right Now', lambda: R('Clear Node Value'), 'p_selected_node', 'FR Late Clear Node'),
    ('FR Late Right Now', lambda: R('Clear Node Key Value'), 'p_selected_node_key', 'FR Late Clear Node Key'),
    ('FR Late Right Now', lambda: R('Late Chip Status'), 'p_panel_status', 'FR Late Set p_panel_status'),
    ('FR Late Right Now', lambda: R('Late Chip Type'), 'p_panel_type', 'FR Late Set p_panel_type'),
    ('FR Late Right Now', lambda: R('Late Chip Platform'), 'p_panel_platform', 'FR Late Set p_panel_platform'),
    ('FR Late Right Now', lambda: R('Late Chip Tags'), 'p_panel_tags', 'FR Late Set p_panel_tags'),
]
NAV_ACTIONS = [('FR Late Right Now', 'Lineage explorer', 'Go to Lineage from FR Late Right Now')]
DEHIGHLIGHT = ['FR Late Right Now']
