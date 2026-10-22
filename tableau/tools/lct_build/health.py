"""Tab 1, Health overview (HO): calc pack section 3, build plan 3.1."""

from __future__ import annotations

from .core import (PANEL_WRITES, LAT, LON, SP_MEA, Cross, Nest, ACCENT, AI_INK, B_DIM, BOOK, CALCS, CARD, CANVAS, CRIT, CRIT_INK, CRIT_TINT, FMT_PCT2, FMT_USD,
                   GOOD, GOOD_INK, I_DIM, I_MEA, INK1, INK2, INK3, LINE, MEDIUM, NAVY, NL, NONE, NONE_TINT,
                   OUT_OF_WINDOW, R_MEA, S_DIM, S_MEA, SEMI, WARN, WARN_INK, WARN_TINT, Pane, R, Sheet, Z, blank,
                   card, card_header, color_map, label_pane, legend, run, sheet, text)
from . import cards, shapes as SH
from .cards import TILE_GROUPS, TILE_ROWS
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
    'Tile Score Text': '// Tile Score Text\n// 7-day health score on the tile, one decimal: "99.7".\nIF ISNULL([health_score_now]) THEN ""\nELSE STR(INT(ROUND([health_score_now] * 10) / 10)) + "." + STR(INT(ROUND([health_score_now] * 10)) % 10)\nEND',
    'Is Tile View Button Row': '// Is Tile View Button Row\n// Keeps the 2 scaffold rows that carry the All / Needs attention buttons. Put on Filters (True).\nNOT ISNULL([Tile View Option])',
    'Tile View Label Active': '// Tile View Label Active\n// Button text when this tile view is selected (Semibold Navy run).\nIF [Is Active Tile View] THEN [Tile View Option] ELSE "" END',
    'Tile View Label Inactive': '// Tile View Label Inactive\n// Button text when this tile view is not selected (Book grey run).\nIF NOT [Is Active Tile View] THEN [Tile View Option] ELSE "" END',
    'Attention Order': '// Attention Order\n// Attention Sort turned around, so the natural ascending order of the rows is worst first.\n-[Attention Sort]',
    'Attention Icon Critical': '// Attention Icon Critical\n// "✕" in red before a Critical node. Split by status so each icon gets its own colour.\nIF [current_status_code] = 3 THEN "✕" ELSE "" END',
    'Attention Icon Warning': '// Attention Icon Warning\n// "▲" in the warning text colour before a Warning node.\nIF [current_status_code] = 2 THEN "▲" ELSE "" END',
    'Layer Stack Key': '// Layer Stack Key\n// Stack order for the layer bar, left to right: Healthy, Warning, Critical, No data.\n// Tableau stacks the highest value first, so Healthy gets the highest key.\n5 - [Status Stack Order]',
    'Layer Label Position': '// Layer Label Position\n// Where the "1 / 27" count starts: just past the end of the full bar (axis fixed 0 to 1.3).\n// The label sits to the right of this hairline Gantt mark.\nMIN(1.02)',
}

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
                         panes=label_pane(text=[R(ban), good, bad, comp], valign='top', label=[
                             run(title + '  ⓘ', 8, INK3, SEMI), run(NL, 8, INK3),
                             run(R(ban), 18, NAVY, SEMI), run(NL, 8, INK3),
                             run(good, 8, GOOD_INK, SEMI), run(bad, 8, CRIT_INK, SEMI), run('  ', 8, INK3),
                             run(comp, 8, INK3, BOOK)],
                             tooltip=_definition_tip(title, definition))))
        date, trend = R(DATE, kind='qk'), R(f'{key} - Trend')
        out.append(trend_sheet(f'HO {SHEET_NAME[key]} KPI Trend', key, R(plat), ACCENT, cap, tfmt))
    # Exposures at risk (calc pack 3.5): Nodes for the BAN, Exposure Daily for the trend
    out.insert(6, Sheet('HO Exposures At Risk KPI', filters=[R('Is Platform Match Node')],
                        panes=label_pane(valign='top', text=[R('Exposures At Risk Now'), R('Exposures At Risk Of Label'),
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


def tile_sheets() -> list[Sheet]:
    buttons = segmented('HO Tile View Buttons', 'Tile View Option', 'Tile View Option', 'Is Active Tile View',
                        'Tile View Label Active', 'Tile View Label Inactive', 'Is Tile View Button Row')
    return cards.tile_sheets() + [buttons]


def attention_sheet() -> Sheet:
    return cards.attention_sheet()


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
               label_pane(axis=pos, align='right', text=[a('Layer Issues Critical Text'), a('Layer Issues Warning Text'), a('Layer Total Text')],
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
    widths = [209, 208, 209, 209, 208, 209]  # card widths; the 6px margins (12px gaps) sit outside: 1252 + 60 = 1312
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
        # a little slack under each grid so Tableau never adds a scroll bar
        groups += [sheet(f'HO Tiles {suffix} Header', SH.HEADER_PANE[1]),
                   sheet(f'HO Tiles {suffix}', SH.TILE_PANE[1] * TILE_ROWS[g] + 6)]
    exposure = card('HO Exposure Card', fixed=SH.EXPOSURE_CARD_W, margins={'right': 7}, kids=[
        Z('horz', friendly='HO Exposure Card Header', fixed=58, kids=[
            card_header('Exposure status', 'Every data product, traced through its full upstream chain. Score is the '
                        '7-day health score (0 to 100). Click a tile to open its lineage.', None),
            blank(24),
            _track('HO Tile View Track', 'HO Tile View Buttons', 230)]),
        Z('vert', friendly='HO Tile Groups', kids=groups),
        legend([('Trusted', GOOD), ('Use with caution', WARN), ('Do not use', CRIT)],
               right='Trust badges can be surfaced inside each dashboard for business users')])
    right = Z('vert', friendly='HO Right Column', fixed=SH.RIGHT_COLUMN_W, style={'margin-left': '7'}, kids=[
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


def check_fit(zones) -> None:
    """Stop the build if a card grid would not fit its zone (Tableau would add a scroll bar)."""
    import csv
    by = {z.name: z.rect for z in zones if z.kind == 'sheet'}
    alerts = sum(1 for r in csv.DictReader(open(SH.ROOT / 'data' / 'marts' / 'dim_nodes.csv', encoding='utf-8'))
                 if r['resource_type'] != 'exposure' and r['current_status_code'] in ('2', '3'))
    need = {f'HO Tiles {suffix}': (SH.TILE_PANE[0] * 5, SH.TILE_PANE[1] * TILE_ROWS[g]) for g, suffix, _ in TILE_GROUPS}
    need.update({f'HO Tiles {suffix} Header': SH.HEADER_PANE for _, suffix, _ in TILE_GROUPS})
    need['HO Needs Attention List'] = (SH.ALERT_PANE[0], SH.ALERT_PANE[1] * alerts)
    for name, (w, h) in need.items():
        _, _, zw, zh = by[name]
        assert w <= zw and h <= zh, f'{name}: needs {w} x {h} px, zone is {zw:.0f} x {zh:.0f} (scroll bar)'


ACTIONS = [  # (sheet, source Ref factory, parameter, caption)
    *[a for _, suffix, _ in TILE_GROUPS for a in (
        (f'HO Tiles {suffix}', lambda: R('node_id (dim_nodes.csv)', 'attr'), 'p_selected_exposure', f'HO Tile Select Exposure {suffix}'),
        (f'HO Tiles {suffix}', lambda: R('Clear Node Value', 'attr'), 'p_selected_node', f'HO Tile Clear Node {suffix}'),
        (f'HO Tiles {suffix}', lambda: R('Clear Node Key Value', 'attr'), 'p_selected_node_key', f'HO Tile Clear Node Key {suffix}'))],
    ('HO Needs Attention List', lambda: R('node_id (dim_nodes.csv)'), 'p_selected_node', 'HO Alert Select Node'),
    ('HO Needs Attention List', lambda: R('node_key'), 'p_selected_node_key', 'HO Alert Select Node Key'),
    # every click that picks a node also tells the Lineage panel what to show (core.PANEL_WRITES)
    *[(f'HO Tiles {suffix}', (lambda f=f: R(f, 'attr')), param, f'HO Tile Set {param} {suffix}')
      for _, suffix, _ in TILE_GROUPS for f, param in PANEL_WRITES],
    *[('HO Needs Attention List', (lambda f=f: R(f)), param, f'HO Alert Set {param}') for f, param in PANEL_WRITES],
    ('HO Tile View Buttons', lambda: R('Tile View Option'), 'p_tile_view', 'HO Set Tile View'),
]
