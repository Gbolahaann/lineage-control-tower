"""Tab 1, Health overview (HO): calc pack section 3, build plan 3.1."""

from __future__ import annotations

import csv

from .core import (LAT, LON, SP_MEA, Cross, Nest, ACCENT, AI_INK, B_DIM, BOOK, CALCS, CARD, CANVAS, CRIT, CRIT_INK, CRIT_TINT, FMT_PCT2, FMT_USD,
                   GOOD, GOOD_INK, I_DIM, I_MEA, INK1, INK2, INK3, LINE, MEDIUM, NAVY, NL, NONE, NONE_TINT,
                   OUT_OF_WINDOW, R_MEA, S_DIM, S_MEA, SEMI, WARN, WARN_INK, WARN_TINT, Pane, R, Sheet, Z, blank,
                   card, card_header, color_map, legend, run, shape_map, sheet, text)
from . import shapes as SH
from .shell import CONTENT_PAD, segmented

P = 'HO'
DATE = 'date (dim_date.csv)'


def _pp(x: str) -> str:
    """Tableau expression: a percentage-point number with exactly 2 decimals, e.g. 0.10."""
    return (f'STR(INT(ROUND({x} * 100) / 100)) + "." + RIGHT("0" + STR(INT(ROUND({x} * 100)) % 100), 2)')


def _pct1(x: str) -> str:
    """Tableau expression: a percentage (already x100) with exactly 1 decimal, e.g. 15.1."""
    return f'STR(INT(ROUND({x} * 10) / 10)) + "." + STR(INT(ROUND({x} * 10)) % 10)'


def change_text_calcs():
    """Change-line text: the arrow, the number and the unit in one string per colour (calc pack 3.2 to 3.7)."""
    f = {}
    for k in ('Run Success', 'Test Pass', 'Freshness SLA'):
        g, b = f'[{k} - Change Good]', f'[{k} - Change Bad]'
        f[f'{k} - Change Good Text'] = (
            f'// {k} - Change Good Text\n// Green part of the change line as text: "▲ 0.10 pp", or "● 0 pp" when nothing changed.\n'
            f'// Blank when the change is bad or there is no earlier period. Two decimals, as on the BAN.\n'
            f'IF ISNULL({g}) THEN ""\nELSEIF {g} = 0 THEN "● 0 pp"\nELSE "▲ " + {_pp(g)} + " pp"\nEND')
        f[f'{k} - Change Bad Text'] = (
            f'// {k} - Change Bad Text\n// Red part of the change line as text: "▼ 0.03 pp". Blank otherwise.\n'
            f'IF ISNULL({b}) THEN ""\nELSE "▼ " + {_pp("ABS(" + b + ")")} + " pp"\nEND')
    for k in ('MTTR', 'Warehouse Cost'):
        g, b = f'[{k} - Change Good]', f'[{k} - Change Bad]'
        f[f'{k} - Change Good Text'] = (
            f'// {k} - Change Good Text\n// Inverse metric: a fall is good. Green text "▼ 10.8%", or "● 0%" when nothing changed.\n'
            f'IF ISNULL({g}) THEN ""\nELSEIF {g} = 0 THEN "● 0%"\nELSE "▼ " + {_pct1("ABS(" + g + ") * 100")} + "%"\nEND')
        f[f'{k} - Change Bad Text'] = (
            f'// {k} - Change Bad Text\n// Inverse metric: a rise is bad. Red text "▲ 4.2%". Blank otherwise.\n'
            f'IF ISNULL({b}) THEN ""\nELSE "▲ " + {_pct1(b + " * 100")} + "%"\nEND')
    return f


def window_split_calcs():
    """Each trend split into the selected window and the rest, so each half gets a fixed pane colour."""
    f = {}
    for k in ('Run Success', 'Test Pass', 'Freshness SLA', 'MTTR', 'Warehouse Cost', 'Exposures At Risk'):
        f[f'{k} - Trend In Period'] = (f'// {k} - Trend In Period\n// The trend bars inside the selected window (accent colour set on the pane).\n'
                                       f'IF ATTR([In Period]) THEN [{k} - Trend] END')
        f[f'{k} - Trend Out Period'] = (f'// {k} - Trend Out Period\n// The trend bars outside the selected window (grey #D9DCD7 set on the pane).\n'
                                        f'IF NOT ATTR([In Period]) THEN [{k} - Trend] END')
    return f


NEW = {
    **change_text_calcs(),
    **window_split_calcs(),
    'Tile Name Short': '// Tile Name Short\n// Tile title cut to fit a 163px tile: 22 characters, then "…". The tooltip has the full name.\nIF LEN([display_name]) > 23 THEN LEFT([display_name], 22) + "…" ELSE [display_name] END',
    'Tile Score Text': '// Tile Score Text\n// 7-day health score on the tile, one decimal: "99.7".\nIF ISNULL([health_score_now]) THEN ""\nELSE STR(INT(ROUND([health_score_now] * 10) / 10)) + "." + STR(INT(ROUND([health_score_now] * 10)) % 10)\nEND',
    'Is Tile View Button Row': '// Is Tile View Button Row\n// Keeps the 2 scaffold rows that carry the All / Needs attention buttons. Put on Filters (True).\nNOT ISNULL([Tile View Option])',
    'Tile View Label Active': '// Tile View Label Active\n// Button text when this tile view is selected (Semibold Navy run).\nIF [Is Active Tile View] THEN [Tile View Option] ELSE "" END',
    'Tile View Label Inactive': '// Tile View Label Inactive\n// Button text when this tile view is not selected (Book grey run).\nIF NOT [Is Active Tile View] THEN [Tile View Option] ELSE "" END',
    'Attention Order': '// Attention Order\n// Attention Sort turned around, so the natural ascending order of the rows is worst first.\n-[Attention Sort]',
    'Attention Icon Critical': '// Attention Icon Critical\n// "✕" in red before a Critical node. Split by status so each icon gets its own colour.\nIF [current_status_code] = 3 THEN "✕" ELSE "" END',
    'Attention Icon Warning': '// Attention Icon Warning\n// "▲" in the warning text colour before a Warning node.\nIF [current_status_code] = 2 THEN "▲" ELSE "" END',
    'Layer Stack Key': '// Layer Stack Key\n// Stack order for the layer bar, left to right: Healthy, Warning, Critical, No data.\n// Tableau stacks the highest value first, so Healthy gets the highest key.\n5 - [Status Stack Order]',
    'Layer Label Position': '// Layer Label Position\n// Where the "1 / 27" count sits on the layer bar: just past the end of the full bar (axis fixed 0 to 1.15).\nMIN(1.08)',
}

# ---------------------------------------------------------------- cards (v10): points in px on a fixed map pane

def _pt(name, why, x, y, pane, card=None):
    """MAKEPOINT for a spot on a card, x / y in px from the card's top left (x may be a Tableau expression).
    The pane's map axes run in px / 100 around its centre, and the card sits in the middle of the pane."""
    pw, ph = pane
    cw, ch = card or pane
    ox, oy = (pw - cw) / 2 - pw / 2, (ph - ch) / 2 - ph / 2
    lon = f'({x} + {ox:g}) / 100' if isinstance(x, str) else f'{(x + ox) / 100:.4f}'
    return f'// {name}\n// {why}\nMAKEPOINT({-(y + oy) / 100:.4f}, {lon})'


def _name_width_calc():
    """Width in px of each upstream node's name in Arial bold 9pt, measured at build time from dim_nodes, so the
    incident tag can sit right after the name (Tableau cannot measure text)."""
    rows = [r for r in csv.DictReader(open(SH.ROOT / 'data' / 'marts' / 'dim_nodes.csv', encoding='utf-8'))
            if r['resource_type'] != 'exposure']
    whens = '\n'.join(f'WHEN "{r["display_name"].replace(chr(34), chr(34) * 2)}" THEN {SH.text_width(r["display_name"], 9, True):.1f}'
                      for r in sorted(rows, key=lambda r: r['display_name']))
    return ('// Attention Name Width\n// Width in px of the node name in Arial bold 9pt, measured by the build from dim_nodes\n'
            '// (Liberation Sans, metric-compatible with Arial). Places the incident tag just after the name.\n'
            f'CASE [display_name]\n{whens}\nELSE LEN([display_name]) * 7\nEND')


def card_calcs():
    tp, tc = SH.TILE_PANE, (SH.TILE_W, SH.TILE_H)
    ap, ac = SH.ALERT_PANE, (SH.ALERT_W, SH.ALERT_H)
    hp = SH.HEADER_PANE
    ty = SH.trust_centre_y()
    ai_x = 'CASE [current_status_code] WHEN 3 THEN {c} WHEN 2 THEN {w} ELSE {h} END'.format(
        c=(SH.ai_pill_box('Critical')[0] + 23.5), w=(SH.ai_pill_box('Warning')[0] + 23.5), h=(SH.ai_pill_box('Healthy')[0] + 23.5))
    name_y = SH.ALERT_TEXT_TOP + 9 * SH.PX * SH.LINE_H / 2
    tag_x = f'{SH.ALERT_TEXT_X} + [Attention Name Width] + 8 + {SH.TAG_W / 2:g}'
    f = {
        'Shape Size': '// Shape Size\n// Constant on Size for the card and pill shapes, so they can be drawn larger than the size\n// slider allows on its own (as in the OKRs reference workbook).\nMIN(1)',
        'Tile Card Key': ('// Tile Card Key\n// Which card shape a tile gets: its status, plus " AI" when it carries the AI-built pill.\n'
                          '[Status Label] + IF [build_method] = "ai_assisted" THEN " AI" ELSE "" END'),
        'Alert Card Key': '// Alert Card Key\n// Which card shape an alert gets (status colours, icon and chevron are drawn in).\n[Status Label]',
        'Attention Tag Key': '// Attention Tag Key\n// Shows the incident tag box only when the node has an open incident.\nIF [open_incident_id] <> "" THEN "tag" ELSE "none" END',
        'Attention Where': '// Attention Where\n// Start of the third alert line: "Staging · Snowflake · ".\n[Layer Name] + " · " + [Platform Name] + " · "',
        'Attention Affects': ('// Attention Affects\n// The bold part of the third alert line: "affects 4 exposures".\n'
                              '"affects " + STR([exposures_fed]) + IF [exposures_fed] = 1 THEN " exposure" ELSE " exposures" END'),
        'Attention Reason': ('// Attention Reason\n// Second line of the alert: what is wrong. Failed models get the time of the failure, as in the\n'
                             '// prototype, on its own line when the whole line would be wider than the card.\n'
                             '[status_reason]\n+ IF [last_run_status] = "error" AND NOT ISNULL([last_event_at]) THEN\n'
                             '    IF LEN([status_reason]) > 44 THEN CHAR(10) + "at " ELSE " at " END + [Last Event Label]\n  ELSE ""\n  END'),
        'Attention Name Width': _name_width_calc(),
        'Tile Name Short': '// Tile Name Short\n// Tile title cut to fit the card beside the status dot: 17 characters, then "…".\nIF LEN([display_name]) > 18 THEN LEFT([display_name], 17) + "…" ELSE [display_name] END',
        'Tile Trust Critical': '// Tile Trust Critical\n// Trust badge in red. Only one of the three trust fields is filled for a tile.\nIF [current_status_code] = 3 THEN [trust_badge] ELSE "" END',
        'Tile Trust Warning': '// Tile Trust Warning\n// Trust badge in the warning text colour #93600F.\nIF [current_status_code] = 2 THEN [trust_badge] ELSE "" END',
        'Tile Trust Healthy': '// Tile Trust Healthy\n// Trust badge in green.\nIF [current_status_code] < 2 THEN [trust_badge] ELSE "" END',
        'Tile Group Count': '// Tile Group Count\n// Tiles in this group after the Platform filter and the All / Needs attention switch.\nCOUNTD([node_id (dim_nodes.csv)])',
        'Tile Card Point': _pt('Tile Card Point', 'Centre of the tile card shape.', SH.TILE_W / 2, SH.TILE_H / 2, tp, tc),
        'Tile Text Point': _pt('Tile Text Point', 'Top left of the tile text (label to the right of and below the point).', SH.TILE_PAD, SH.TILE_TEXT_TOP, tp, tc),
        'Tile Score Point': _pt('Tile Score Point', 'Right end of the score, on the trust line.', SH.TILE_W - SH.TILE_PAD, ty, tp, tc),
        'Tile AI Point': _pt('Tile AI Point', 'Middle of the AI-built pill, which sits just after the trust badge.', ai_x, ty, tp, tc),
        'Tile Header Title Point': _pt('Tile Header Title Point', 'Start of the group name.', 0, hp[1] / 2, hp),
        'Alert Card Point': _pt('Alert Card Point', 'Centre of the alert card shape.', SH.ALERT_W / 2, SH.ALERT_H / 2, ap, ac),
        'Alert Text Point': _pt('Alert Text Point', 'Top left of the alert text, right of the icon.', SH.ALERT_TEXT_X, SH.ALERT_TEXT_TOP, ap, ac),
        'Alert Tag Point': _pt('Alert Tag Point', 'Middle of the incident tag box, just after the node name.', tag_x, name_y, ap, ac),
        'Alert Tag Text Point': _pt('Alert Tag Text Point', 'Same spot as Alert Tag Point, for the tag text layer.', tag_x, name_y, ap, ac),
    }
    for g, _, title in TILE_GROUPS_TEXT:
        x = SH.text_width(title, 7, True) + 8 + SH.COUNT_W / 2
        f[f'Is Tile Group {g}'] = f'// Is Tile Group {g}\n// Keeps the tiles of one exposure group on its own sheet. Put on Filters (True).\n[Exposure Group Sort] = {g}'
        f[f'Tile Header Count Point {g}'] = _pt(f'Tile Header Count Point {g}', 'Middle of the count chip after the group name.', x, hp[1] / 2, hp)
        f[f'Tile Header Count Text Point {g}'] = _pt(f'Tile Header Count Text Point {g}', 'Same spot, for the count text.', x, hp[1] / 2, hp)
    return f


TILE_GROUPS_TEXT = [(1, '', 'BI DASHBOARDS'), (2, '', 'APPS, ML AND NOTEBOOKS'), (3, '', 'AI AGENTS AND DATA HUBS'),
                    (4, '', 'UNREGISTERED, FOUND IN QUERY HISTORY')]
NEW.update(card_calcs())

TYPES = {
    # shared (calc pack 2)
    'In Period': B_DIM, 'In Prior Period': B_DIM, 'Compare Label': S_DIM, 'Is Platform Match Node': B_DIM,
    'Is Platform Match Day': B_DIM, 'Is Platform Match Day (Episodes)': B_DIM, 'Status Label': S_DIM,
    'Status Icon': S_DIM, 'Status Tint Key': S_DIM, 'Status Severity Sort': I_DIM, 'Status Stack Order': I_DIM,
    'Is At Risk Now': B_DIM, 'Layer Name': S_DIM, 'Platform Name': S_DIM, 'Consumer Type Label': S_DIM,
    'Node Count': I_MEA, 'Clear Node Value': S_DIM, 'Clear Node Key Value': I_DIM, 'Last Event Label': S_DIM,
    # KPIs (3.2 to 3.7)
    'Exposures At Risk Now': I_MEA, 'Exposures In Scope': I_MEA, 'Exposures At Risk Of Label': S_MEA,
    'Exposures Critical Now': I_MEA, 'Exposures Warning Now': I_MEA, 'Exposures At Risk - Trend': I_MEA,
    'MTTR - Focus Label': S_MEA,
    # tiles (3.9)
    'Is Exposure': B_DIM, 'Show Exposure Tile': B_DIM, 'Exposure Group Sort': I_DIM, 'Exposure Group Label': S_DIM,
    'Tile Sort Key': S_DIM, 'Tile Column': I_MEA, 'Tile Row': I_MEA, 'Tile Owner Text': S_DIM,
    'Tile Owner Missing Text': S_DIM, 'Tile Trust Critical': S_DIM, 'Tile Trust Warning': S_DIM,
    'Tile Trust Healthy': S_DIM, 'Tile AI Tag': S_DIM, 'Tile Tooltip Why': S_DIM, 'Tile Name Short': S_DIM,
    'Tile Score Text': S_DIM, 'Tile View Option': S_DIM, 'Is Active Tile View': B_DIM,
    'Is Tile View Button Row': B_DIM, 'Tile View Label Active': S_DIM, 'Tile View Label Inactive': S_DIM,
    # attention (3.10)
    'Is Attention Node': B_DIM, 'Attention Sort': I_DIM, 'Attention Order': I_DIM, 'Attention Reason': S_DIM,
    'Attention Meta': S_DIM, 'Attention Incident Tag': S_DIM, 'Attention Open Since': S_DIM,
    'Attention Icon Critical': S_DIM, 'Attention Icon Warning': S_DIM,
    # layers (3.11)
    'Layer Share': R_MEA, 'Layer Total': I_MEA, 'Layer Issues': I_MEA, 'Layer Has Critical': B_DIM,
    'Layer Issues Critical Text': S_DIM, 'Layer Issues Warning Text': S_DIM, 'Layer Total Text': S_DIM,
    'Layer Label Position': R_MEA,
    'Layer Stack Key': I_DIM,
    'Shape Size': R_MEA, 'Tile Card Key': S_DIM, 'Alert Card Key': S_DIM, 'Attention Tag Key': S_DIM,
    'Attention Where': S_DIM, 'Attention Affects': S_DIM, 'Attention Name Width': R_MEA, 'Tile Group Count': I_MEA,
    **{n: SP_MEA for n in ('Tile Card Point', 'Tile Text Point', 'Tile Score Point', 'Tile AI Point', 'Tile Header Title Point',
                           'Alert Card Point', 'Alert Text Point', 'Alert Tag Point', 'Alert Tag Text Point')},
    **{f'{k} {g}': SP_MEA for g in (1, 2, 3, 4) for k in ('Tile Header Count Point', 'Tile Header Count Text Point')},
    **{f'Is Tile Group {g}': B_DIM for g in (1, 2, 3, 4)},
}
for k in ('Run Success', 'Test Pass', 'Freshness SLA', 'MTTR', 'Warehouse Cost'):
    for s in ('Focus', 'Prior', 'Change', 'Change Good', 'Change Bad', 'Trend'):
        TYPES[f'{k} - {s}'] = R_MEA
    TYPES[f'{k} - Change Good Text'] = S_MEA
for k in ('Run Success', 'Test Pass', 'Freshness SLA', 'MTTR', 'Warehouse Cost', 'Exposures At Risk'):
    TYPES[f'{k} - Trend In Period'] = R_MEA
    TYPES[f'{k} - Trend Out Period'] = R_MEA
    TYPES[f'{k} - Change Bad Text'] = S_MEA

CALCS.add(formulas=NEW, types=TYPES, table_calc={
    'Tile Column': 'Tile Sort Key', 'Tile Row': 'Tile Sort Key', 'Layer Share': 'Layer Stack Key'})


# ================================================================ sheets

KPIS = [  # key, title, base, platform filter, BAN field, BAN format, trend caption, trend format, definition
    ('Run Success', 'RUN SUCCESS', 'Is Platform Match Day', 'Run Success - Focus', FMT_PCT2, 'Failed model runs', 'n#,##0',
     'Successful model runs divided by all model runs, skipped runs excluded.'),
    ('Test Pass', 'TEST PASS RATE', 'Is Platform Match Day', 'Test Pass - Focus', FMT_PCT2, 'Tests not passing', 'n#,##0',
     'Passing tests divided by all tests run. Warnings count as not passing.'),
    ('Freshness SLA', 'FRESHNESS SLA', 'Is Platform Match Day', 'Freshness SLA - Focus', FMT_PCT2, 'Late source checks', 'n#,##0',
     'Hourly source freshness checks that passed, divided by all checks.'),
    ('MTTR', 'MEAN TIME TO RECOVER', 'Is Platform Match Day (Episodes)', 'MTTR - Focus Label', None, 'Mean recovery time (h)', 'n#,##0.0',
     'Average time from a node\'s first failure to its next success, across model runs, source freshness and BI refreshes.'),
    ('Warehouse Cost', 'WAREHOUSE COST', 'Is Platform Match Day', 'Warehouse Cost - Focus', FMT_USD, 'Daily cost', FMT_USD,
     'Estimated compute cost of dbt builds plus queries from data products, in USD.'),
]
SHEET_NAME = {'Run Success': 'Run Success', 'Test Pass': 'Test Pass', 'Freshness SLA': 'Freshness SLA',
              'MTTR': 'MTTR', 'Warehouse Cost': 'Warehouse Cost'}


def _definition_tip(title, definition):
    return [run(title, 7, INK3, SEMI), run(NL, 7, INK3), run(definition, 9, INK1, BOOK)]


def kpi_sheets() -> list[Sheet]:
    out = []
    for key, title, plat, ban, fmt, cap, tfmt, definition in KPIS:
        good, bad, comp = R(f'{key} - Change Good Text'), R(f'{key} - Change Bad Text'), R('Compare Label', 'attr')
        formats = {R(ban): fmt} if fmt else {}
        out.append(Sheet(f'HO {SHEET_NAME[key]} KPI', filters=[R(plat)], formats=formats,
                         panes=Pane('Text', text=[R(ban), good, bad, comp], valign='top', label=[
                             run(title + '  ⓘ', 8, INK3, SEMI), run(NL, 8, INK3),
                             run(R(ban), 18, NAVY, SEMI), run(NL, 8, INK3),
                             run(good, 8, GOOD_INK, SEMI), run(bad, 8, CRIT_INK, SEMI), run('  ', 8, INK3),
                             run(comp, 8, INK3, BOOK)],
                             tooltip=_definition_tip(title, definition))))
        date, trend = R(DATE, kind='qk'), R(f'{key} - Trend')
        out.append(trend_sheet(f'HO {SHEET_NAME[key]} KPI Trend', key, R(plat), ACCENT, cap, tfmt))
    # Exposures at risk (calc pack 3.5): Nodes for the BAN, Exposure Daily for the trend
    out.insert(6, Sheet('HO Exposures At Risk KPI', filters=[R('Is Platform Match Node')],
                        panes=Pane('Text', valign='top', text=[R('Exposures At Risk Now'), R('Exposures At Risk Of Label'),
                                                              R('Exposures Critical Now'), R('Exposures Warning Now')], label=[
                            run('EXPOSURES AT RISK  ⓘ', 8, INK3, SEMI), run(NL, 8, INK3),
                            run(R('Exposures At Risk Now'), 18, NAVY, SEMI), run(' ', 9, INK3),
                            run(R('Exposures At Risk Of Label'), 9, INK3, MEDIUM), run(NL, 8, INK3),
                            run(R('Exposures Critical Now'), 8, CRIT_INK, SEMI), run(' critical', 8, CRIT_INK, SEMI),
                            run('  ·  ', 8, INK3), run(R('Exposures Warning Now'), 8, INK3), run(' warning', 8, INK3)],
                            tooltip=_definition_tip('EXPOSURES AT RISK', 'Exposures whose upstream chain has a failing model, late source, failed refresh or failing test right now. Bars show the count at the end of each day.'))))
    out.insert(7, trend_sheet('HO Exposures At Risk KPI Trend', 'Exposures At Risk',
                              R('Is Platform Match Node'), WARN, 'At risk at end of day', 'n#,##0'))
    return out


TREND_BAR = 0.0099999997764825821  # the thinnest bar, as set in Tableau on v08


def trend_sheet(name, key, plat, in_colour, caption, fmt) -> Sheet:
    """90 daily bars, the selected window in the accent and the rest in grey: two measures on a synchronised
    dual axis, each pane with a fixed colour, so no palette is involved."""
    date = R(DATE, kind='qk')
    tin, tout = R(f'{key} - Trend In Period'), R(f'{key} - Trend Out Period')
    tip = lambda m: [run(R(DATE, kind='qk'), 9, INK1, SEMI), run(NL, 7, INK3),
                     run(caption.upper() + '   ', 7, INK3, SEMI), run(m, 9, NAVY, SEMI)]
    return Sheet(name, cols=[date], rows=[(tin, tout)], filters=[plat], hide=[date, tin, tout], sync=[tout],
                 formats={date: '*d mmm yyyy', tin: fmt, tout: fmt},
                 panes=[Pane('Bar', size=TREND_BAR, label_show=False),
                        Pane('Bar', axis=tin, size=TREND_BAR, label_show=False, mark_color=in_colour, tooltip=tip(tin)),
                        Pane('Bar', axis=tout, size=TREND_BAR, label_show=False, mark_color=OUT_OF_WINDOW, tooltip=tip(tout))])


def _a(n):
    return R(n, 'attr')


def _shape_layer(title, point, size_px, *, shape=None, shape_field=None, lod=(), inert=True, pane=None, **kw):
    """A card or pill drawn as a custom shape in its own colours, with a constant on Size (OKRs reference)."""
    return Pane('Shape', title=title, inert=inert, shape=shape, shape_field=shape_field, size_field=R('Shape Size'),
                size=SH.size_for(*size_px), label_show=False, lod=[R(point, 'clct'), *lod], pane_size=pane, **kw)


def _text_layer(title, point, label, *, align, valign='center', lod=(), pane=None):
    """Text placed at a point on a clear hairline shape (as set in Tableau on v09). Label alignment places the
    label beside the point: right = the text starts at the point, left = it ends there, bottom = below it."""
    texts = [r['_ref'] for r in label if '_ref' in r]
    return Pane('Shape', title=title, inert=True, shape=SH.TRANSPARENT, size=0.0099999997764825821,
                text=texts, label=label, align=align, valign=valign, lod=[R(point, 'clct'), *lod], pane_size=pane)


def _map_grid(sheet_obj, pane):
    """Fixed, hidden map axes in px / 100 around the pane centre: the pane is a little canvas in pixels."""
    w, h = pane
    sheet_obj.fixed_axes = [(LAT, -h / 200, h / 200, 'rows'), (LON, -w / 200, w / 200, 'cols')]
    return sheet_obj


TILE_GROUPS = [  # sort, sheet suffix, header text (exposure_group upper case)
    (1, 'BI Dashboards', 'BI DASHBOARDS'),
    (2, 'Apps ML Notebooks', 'APPS, ML AND NOTEBOOKS'),
    (3, 'AI Agents Data Hubs', 'AI AGENTS AND DATA HUBS'),
    (4, 'Unregistered', 'UNREGISTERED, FOUND IN QUERY HISTORY'),
]
TILE_ROWS = {1: 4, 2: 1, 3: 1, 4: 1}  # rows of 5 at All, so each group's zone is as tall as its grid


def tile_sheets() -> list[Sheet]:
    """Exposure tiles (calc pack 3.9), one sheet per group with its header sheet above, as in the prototype.

    Each tile sheet is a grid of fixed-size map panes (Tile Row x Latitude by Tile Column x Longitude, no base
    map, the pane a 170 x 70 px canvas). Marks layers, bottom to top: the card (one custom shape per status, with
    the fill, border, top edge, status dot and AI-built pill drawn in), the text (name, tool and owner, trust),
    the AI-built word on its pill, and the score.
    """
    pane = SH.TILE_PANE
    key, ckey = R('Tile Sort Key'), R('Tile Card Key')
    shape_map(ckey, {f'"{st}{" AI" if ai else ""}"': SH.tile_shape(st, ai)
                     for st in SH.TILE_STYLES for ai in (False, True)})
    out = []
    for g, suffix, title in TILE_GROUPS:
        trow, tcol = R('Tile Row', kind='ok'), R('Tile Column', kind='ok')
        for r in (trow, tcol):
            r.tc_order = [key, ckey]
        filters = [R('Is Exposure'), R('Is Platform Match Node'), R('Show Exposure Tile'), R(f'Is Tile Group {g}')]
        card_layer = _shape_layer(
            'Card', 'Tile Card Point', (SH.TILE_W, SH.TILE_H), shape_field=ckey, inert=False, pane=pane,
            lod=[key, _a('node_id (dim_nodes.csv)'), _a('Clear Node Value'), _a('Clear Node Key Value')],
            tooltip=[run(_a('display_name'), 9, INK1, SEMI), run(NL, 7, INK3),
                     run('STATUS   ', 7, INK3, SEMI), run(_a('trust_badge'), 9, NAVY, SEMI), run(NL, 7, INK3),
                     run('HEALTH SCORE (7D)   ', 7, INK3, SEMI), run(_a('Tile Score Text'), 9, NAVY, SEMI), run(NL, 7, INK3),
                     run('OWNER   ', 7, INK3, SEMI), run(_a('owner_name'), 9, NAVY, SEMI), run(NL, 7, INK3),
                     run('WHY   ', 7, INK3, SEMI), run(_a('Tile Tooltip Why'), 9, INK1), run(NL, 7, INK3),
                     run('CLICK TO OPEN LINEAGE', 7, INK3, SEMI)])
        words = _text_layer('Text', 'Tile Text Point', align='right', valign='bottom', lod=[key], pane=pane, label=[
            run(_a('Tile Name Short'), 9, INK1, SEMI), run(NL, 8, INK3),
            run(_a('Consumer Type Label'), 8, INK3), run(' · ', 8, INK3), run(_a('Tile Owner Text'), 8, INK3),
            run(_a('Tile Owner Missing Text'), 8, CRIT_INK, SEMI), run(NL, 8, INK3),
            run(_a('Tile Trust Critical'), 7, CRIT_INK, SEMI), run(_a('Tile Trust Warning'), 7, WARN_INK, SEMI),
            run(_a('Tile Trust Healthy'), 7, GOOD_INK, SEMI)])
        ai = _text_layer('AI tag', 'Tile AI Point', align='center', lod=[key], pane=pane,
                         label=[run(_a('Tile AI Tag'), 7, AI_INK)])
        score = _text_layer('Score', 'Tile Score Point', align='left', lod=[key], pane=pane,
                            label=[run(_a('Tile Score Text'), 8, INK2, SEMI)])
        out.append(_map_grid(Sheet(
            f'HO Tiles {suffix}', rows=[Cross([trow, LAT])], cols=[Cross([tcol, LON])], filters=filters,
            hide=[trow, tcol], layers=True, no_basemap=True, zoom=None,
            panes=[Pane('Automatic', lod=[key], pane_size=pane), card_layer, words, ai, score]), pane))
        # header: the group name, then its count on a chip, both from this group's filtered tiles
        hp = SH.HEADER_PANE
        out.append(_map_grid(Sheet(
            f'HO Tiles {suffix} Header', rows=[LAT], cols=[LON], filters=filters, layers=True, no_basemap=True,
            zoom=None, tooltip=False,
            panes=[Pane('Automatic', pane_size=hp),
                   _text_layer('Title', 'Tile Header Title Point', align='right', pane=hp,
                               label=[run(title, 7, INK3, SEMI)]),
                   _shape_layer('Count chip', f'Tile Header Count Point {g}', (SH.COUNT_W, SH.COUNT_H),
                                shape=SH.COUNT_SHAPE, pane=hp),
                   _text_layer('Count', f'Tile Header Count Text Point {g}', align='center', pane=hp,
                               label=[run(R('Tile Group Count'), 7, INK2)])]), hp))
    buttons = segmented('HO Tile View Buttons', 'Tile View Option', 'Tile View Option', 'Is Active Tile View',
                        'Tile View Label Active', 'Tile View Label Inactive', 'Is Tile View Button Row')
    return out + [buttons]


def attention_sheet() -> Sheet:
    """Needs attention now: one card per node, as in the prototype. Each row is a fixed 376 x 88 px map pane;
    layers: the card (custom shape per status with the icon and chevron drawn in), the text (name, what is wrong,
    where and what it affects), and the incident tag placed just after the name."""
    pane = SH.ALERT_PANE
    order, nkey, name = R('Attention Order'), R('node_key'), R('display_name')
    ckey, tkey = R('Alert Card Key'), R('Attention Tag Key')
    shape_map(ckey, {f'"{st}"': SH.alert_shape(st) for st in SH.ALERT_STYLES})
    shape_map(tkey, {'"tag"': SH.TAG_SHAPE, '"none"': SH.TRANSPARENT})
    ids = [R('node_id (dim_nodes.csv)'), nkey]
    tip = [run(name, 9, INK1, SEMI), run(NL, 7, INK3), run('CLICK TO SEE WHO IS AFFECTED', 7, INK3, SEMI)]
    return _map_grid(Sheet(
        'HO Needs Attention List', rows=[Cross([Nest([order, nkey]), LAT])], cols=[LON],
        filters=[R('Is Attention Node'), R('Is Platform Match Node')], hide=[order, nkey],
        layers=True, no_basemap=True, zoom=None,
        panes=[Pane('Automatic', lod=ids, pane_size=pane),
               _shape_layer('Card', 'Alert Card Point', (SH.ALERT_W, SH.ALERT_H), shape_field=ckey, inert=False,
                            lod=ids, pane=pane, tooltip=tip),
               _text_layer('Text', 'Alert Text Point', align='right', valign='bottom', lod=ids, pane=pane, label=[
                   run(name, 9, INK1, SEMI), run(NL, 8, INK2),
                   run(R('Attention Reason'), 8, INK2), run(NL, 8, INK2),
                   run(R('Attention Where'), 8, INK2), run(R('Attention Affects'), 8, INK1, SEMI),
                   run(R('Attention Open Since'), 8, INK2)]),
               _shape_layer('Tag', 'Alert Tag Point', (SH.TAG_W, SH.TAG_H), shape_field=tkey, lod=ids, pane=pane),
               _text_layer('Tag text', 'Alert Tag Text Point', align='center', lod=ids, pane=pane,
                           label=[run(R('Attention Incident Tag'), 8, INK2)])]), pane)


def layer_sheet() -> Sheet:
    color_map(R('Layer Stack Key'), {'4': GOOD, '3': WARN, '2': CRIT, '1': NONE})
    share, pos = R('Layer Share'), R('Layer Label Position')
    a = lambda n: R(n, 'attr')
    return Sheet(
        'HO Layer Health Bar', rows=[R('layer_column'), R('Layer Name')], cols=[(share, pos)],
        filters=[R('Is Platform Match Node')], hide=[R('layer_column'), share, pos],
        fixed={share: (0, 1.3), pos: (0, 1.3)},
        header_font={'font-size': '8', 'color': INK2}, header_width={R('Layer Name'): 112},
        panes=[Pane(),
               Pane('Bar', axis=share, color=R('Layer Stack Key'), size=0.75, label_show=False, stroke=CARD,
                    tooltip_fields=[a('Status Label'), R('Node Count'), a('Layer Total Text')],
                    tooltip=[run(a('Layer Name'), 9, INK1, SEMI), run(NL, 7, INK3),
                             run(a('Status Label'), 7, INK3, SEMI), run('   ', 7, INK3), run(R('Node Count'), 9, NAVY, SEMI),
                             run(' of ', 9, INK3), run(a('Layer Total Text'), 9, INK3)]),
               Pane('Text', axis=pos, text=[a('Layer Issues Critical Text'), a('Layer Issues Warning Text'), a('Layer Total Text')],
                    label=[run(a('Layer Issues Critical Text'), 8, CRIT_INK, SEMI),
                           run(a('Layer Issues Warning Text'), 8, WARN_INK, SEMI),
                           run(a('Layer Total Text'), 8, INK3)])])


def sheets() -> list[Sheet]:
    return kpi_sheets() + tile_sheets() + [attention_sheet(), layer_sheet()]


# ================================================================ dashboard content (build plan 3.1)

def _track(friendly, sheet_name, width):
    return Z('horz', friendly=friendly, fixed=width, kids=[sheet(sheet_name)], style={
        'background-color': CANVAS, 'border-color': LINE, 'border-style': 'solid', 'border-width': '1',
        'corner-radius': '8', 'padding': '2', 'margin-top': '2', 'margin-bottom': '14'})


def content() -> Z:
    widths = [215, 221, 221, 221, 220, 214]  # 6 cards of ~209 + 12px gaps = 1312
    names = ['Run Success', 'Test Pass', 'Freshness SLA', 'Exposures At Risk', 'MTTR', 'Warehouse Cost']
    kpis = []
    for i, (n, w) in enumerate(zip(names, widths)):
        margins = {}
        if i > 0:
            margins['left'] = 6
        if i < 5:
            margins['right'] = 6
        kpis.append(card(f'HO KPI {n} Card', [sheet(f'HO {n} KPI', 66), sheet(f'HO {n} KPI Trend', None, **{'padding-top': '8'})],
                         fixed=w, pad=(12, 14, 10, 14), margins=margins))
    groups = []
    for g, suffix, _ in TILE_GROUPS:
        groups += [sheet(f'HO Tiles {suffix} Header', SH.HEADER_PANE[1]),
                   sheet(f'HO Tiles {suffix}', SH.TILE_PANE[1] * TILE_ROWS[g])]
    exposure = card('HO Exposure Card', margins={'right': 7}, kids=[
        Z('horz', friendly='HO Exposure Card Header', fixed=58, kids=[
            card_header('Exposure status', 'Every data product, traced through its full upstream chain. Score is the '
                        '7-day health score (0 to 100). Click a tile to open its lineage.', None),
            blank(24),
            _track('HO Tile View Track', 'HO Tile View Buttons', 230)]),
        Z('vert', friendly='HO Tile Groups', kids=groups),
        legend([('Trusted', GOOD), ('Use with caution', WARN), ('Do not use', CRIT)],
               right='Trust badges can be surfaced inside each dashboard for business users')])
    right = Z('vert', friendly='HO Right Column', fixed=417, style={'margin-left': '7'}, kids=[
        card('HO Attention Card', margins={'bottom': 7}, kids=[
            card_header('Needs attention now', 'Upstream nodes that are failing, late or warning. Click one to see who '
                        'is affected.', 58),
            sheet('HO Needs Attention List')]),
        card('HO Layer Card', fixed=198, margins={'top': 7}, kids=[
            card_header('Health by layer', 'Where in the chain the trouble sits, right now'),
            sheet('HO Layer Health Bar')])])
    return Z('vert', friendly='HO Content', style=CONTENT_PAD, kids=[
        Z('horz', friendly='HO KPI Row', fixed=128, kids=kpis),
        Z('horz', friendly='HO Body', style={'margin-top': '14'}, kids=[exposure, right])])


ACTIONS = [  # (sheet, source Ref factory, parameter, caption)
    *[a for _, suffix, _ in TILE_GROUPS for a in (
        (f'HO Tiles {suffix}', lambda: R('node_id (dim_nodes.csv)', 'attr'), 'p_selected_exposure', f'HO Tile Select Exposure {suffix}'),
        (f'HO Tiles {suffix}', lambda: R('Clear Node Value', 'attr'), 'p_selected_node', f'HO Tile Clear Node {suffix}'),
        (f'HO Tiles {suffix}', lambda: R('Clear Node Key Value', 'attr'), 'p_selected_node_key', f'HO Tile Clear Node Key {suffix}'))],
    ('HO Needs Attention List', lambda: R('node_id (dim_nodes.csv)'), 'p_selected_node', 'HO Alert Select Node'),
    ('HO Needs Attention List', lambda: R('node_key'), 'p_selected_node_key', 'HO Alert Select Node Key'),
    ('HO Tile View Buttons', lambda: R('Tile View Option'), 'p_tile_view', 'HO Set Tile View'),
]
