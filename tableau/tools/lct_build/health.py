"""Tab 1, Health overview (HO): calc pack section 3, build plan 3.1."""

from __future__ import annotations

from .core import (LAT, LON, SP_MEA, Cross, Nest, ACCENT, AI_INK, B_DIM, BOOK, CALCS, CARD, CANVAS, CRIT, CRIT_INK, CRIT_TINT, FMT_PCT2, FMT_USD,
                   GOOD, GOOD_INK, I_DIM, I_MEA, INK1, INK2, INK3, LINE, MEDIUM, NAVY, NL, NONE, NONE_TINT,
                   OUT_OF_WINDOW, R_MEA, S_DIM, S_MEA, SEMI, WARN, WARN_INK, WARN_TINT, Pane, R, Sheet, Z, blank,
                   card, card_header, color_map, legend, run, sheet, text)
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
    'Tile Shape Point': ('// Tile Shape Point\n'
        '// Outline of one rounded tile, drawn as a polygon on its own little map pane (the tile grid is\n'
        '// row index x Latitude by column index x Longitude, as in a Tableau-saved reference workbook).\n'
        '// Each of the 90 Exposure Daily rows of an exposure is one point of the outline: a superellipse\n'
        '// (exponent 8), which reads as a rectangle with rounded corners. Path: the Exposure Daily date.\n'
        'MAKEPOINT(\n'
        '    0.44 * SIGN(SIN(2 * PI() * DATEDIFF(\'day\', { MIN([date (mart_exposure_daily.csv)]) }, [date (mart_exposure_daily.csv)]) / 90))\n'
        '         * POWER(ABS(SIN(2 * PI() * DATEDIFF(\'day\', { MIN([date (mart_exposure_daily.csv)]) }, [date (mart_exposure_daily.csv)]) / 90)), 0.25),\n'
        '    0.97 * SIGN(COS(2 * PI() * DATEDIFF(\'day\', { MIN([date (mart_exposure_daily.csv)]) }, [date (mart_exposure_daily.csv)]) / 90))\n'
        '         * POWER(ABS(COS(2 * PI() * DATEDIFF(\'day\', { MIN([date (mart_exposure_daily.csv)]) }, [date (mart_exposure_daily.csv)]) / 90)), 0.25)\n'
        ')'),
    'Tile Text Point': '// Tile Text Point\n// Anchor of the tile text (name, tool and owner, trust badge), left side of the tile.\nMAKEPOINT(0.0, -0.86)',
    'Tile Score Point': '// Tile Score Point\n// Anchor of the 7-day score, bottom right of the tile.\nMAKEPOINT(-0.26, 0.86)',
    'Tile Dot Point': '// Tile Dot Point\n// Anchor of the status dot, top right of the tile.\nMAKEPOINT(0.27, 0.86)',
    'Layer Stack Key': '// Layer Stack Key\n// Stack order for the layer bar, left to right: Healthy, Warning, Critical, No data.\n// Tableau stacks the highest value first, so Healthy gets the highest key.\n5 - [Status Stack Order]',
    'Layer Label Position': '// Layer Label Position\n// Where the "1 / 27" count sits on the layer bar: just past the end of the full bar (axis fixed 0 to 1.15).\nMIN(1.08)',
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
    'Tile Shape Point': SP_MEA, 'Tile Text Point': SP_MEA, 'Tile Score Point': SP_MEA, 'Tile Dot Point': SP_MEA,
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
TILE_PANE = (151, 84)  # one tile cell in px: 5 across the card, a 143 x 76 tile plus an 8px gap (prototype .xgrid)


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
    """Exposure tiles as rounded cards (calc pack 3.9, rebuilt the way a Tableau-saved reference builds cards).

    A grid of small map panes: rows = group sort * group label * tile row * Latitude, columns = tile column *
    Longitude. Tile row and column are INDEX table calcs addressed along every dimension on the sheet except the
    group, so they restart per group. Four marks layers, bottom to top: the rounded outline (polygon from
    Exposure Daily, status tint, #E6E7E2 border, the tooltip), the status dot, the text, the score.
    """
    a = lambda n: R(n, 'attr')
    color_map(R('Status Tint Key'), {'"Healthy"': CARD, '"Warning"': WARN_TINT, '"Critical"': CRIT_TINT, '"No data"': NONE_TINT})
    color_map(R('Status Label'), {'"Healthy"': GOOD, '"Warning"': WARN, '"Critical"': CRIT, '"No data"': NONE})
    key, date = R('Tile Sort Key'), R('date (mart_exposure_daily.csv)', kind='ok')
    tint, status = R('Status Tint Key'), R('Status Label')
    trow, tcol = R('Tile Row', kind='ok'), R('Tile Column', kind='ok')
    for r in (trow, tcol):
        r.tc_order = [key, tint, status, date]   # addressing; the group fields partition, so the index restarts per group
    gsort, glabel = R('Exposure Group Sort'), R('Exposure Group Label')
    node = a('node_id (dim_nodes.csv)')
    tile = Pane('Polygon', title='Tile', color=tint, stroke=LINE, path=date, pane_size=TILE_PANE,
                lod=[R('Tile Shape Point', 'clct'), key, node, a('Clear Node Value'), a('Clear Node Key Value')],
                tooltip=[run(a('display_name'), 9, INK1, SEMI), run(NL, 7, INK3),
                         run('STATUS   ', 7, INK3, SEMI), run(a('trust_badge'), 9, NAVY, SEMI), run(NL, 7, INK3),
                         run('HEALTH SCORE (7D)   ', 7, INK3, SEMI), run(a('Tile Score Text'), 9, NAVY, SEMI), run(NL, 7, INK3),
                         run('OWNER   ', 7, INK3, SEMI), run(a('owner_name'), 9, NAVY, SEMI), run(NL, 7, INK3),
                         run('WHY   ', 7, INK3, SEMI), run(a('Tile Tooltip Why'), 9, INK1), run(NL, 7, INK3),
                         run('CLICK TO OPEN LINEAGE', 7, INK3, SEMI)])
    dot = Pane('Circle', title='Dot', inert=True, color=status, size=0.35, label_show=False, pane_size=TILE_PANE,
               lod=[R('Tile Dot Point', 'clct'), key])
    texts = [a('Tile Name Short'), a('Consumer Type Label'), a('Tile Owner Text'), a('Tile Owner Missing Text'),
             a('Tile Trust Critical'), a('Tile Trust Warning'), a('Tile Trust Healthy'), a('Tile AI Tag')]
    words = Pane('Circle', title='Text', inert=True, size=0.01, mark_color='#ffffff00', text=texts, align='left',
                 pane_size=TILE_PANE,
                 lod=[R('Tile Text Point', 'clct'), key],
                 label=[run(a('Tile Name Short'), 9, INK1, SEMI), run(NL, 8, INK3),
                        run(a('Consumer Type Label'), 8, INK3), run(' · ', 8, INK3), run(a('Tile Owner Text'), 8, INK3),
                        run(a('Tile Owner Missing Text'), 8, CRIT_INK, SEMI), run(NL, 8, INK3),
                        run(a('Tile Trust Critical'), 7, CRIT_INK, SEMI), run(a('Tile Trust Warning'), 7, WARN_INK, SEMI),
                        run(a('Tile Trust Healthy'), 7, GOOD_INK, SEMI), run('   ', 7, INK3), run(a('Tile AI Tag'), 7, AI_INK, SEMI)])
    score = Pane('Circle', title='Score', inert=True, size=0.01, mark_color='#ffffff00', text=[a('Tile Score Text')],
                 align='right', lod=[R('Tile Score Point', 'clct'), key], pane_size=TILE_PANE,
                 label=[run(a('Tile Score Text'), 8, INK2, SEMI)])
    tiles = Sheet(
        'HO Exposure Status Tiles', rows=[Cross([Nest([gsort, Nest([glabel, trow])]), LAT])], cols=[Cross([tcol, LON])],
        filters=[R('Is Exposure'), R('Is Platform Match Node'), R('Show Exposure Tile')],
        hide=[gsort, trow, tcol], header_font={'font-size': '7', 'color': INK3, 'font-family': 'Arial', 'font-weight': 'bold'},
        header_width={glabel: 110}, layers=True, no_basemap=True, zoom=None,
        panes=[Pane('Automatic', lod=[key], pane_size=TILE_PANE), tile, dot, words, score])
    # the outline reaches 0.44 / 0.97 from the centre: 76 of 84 px high, 143 of 151 px wide
    tiles.fixed_axes = [(LAT, -0.485, 0.485, 'rows'), (LON, -1.02, 1.02, 'cols')]
    buttons = segmented('HO Tile View Buttons', 'Tile View Option', 'Tile View Option', 'Is Active Tile View',
                        'Tile View Label Active', 'Tile View Label Inactive', 'Is Tile View Button Row')
    return [tiles, buttons]


def attention_sheet() -> Sheet:
    """Needs attention now: one tinted full-width row per node, the text as the bar's own label, left-aligned
    inside the bar. A Text mark centres its box on its anchor, so text placed near 0 was cut off on the left."""
    color_map(R('Status Tint Key'), {'"Healthy"': CARD, '"Warning"': WARN_TINT, '"Critical"': CRIT_TINT, '"No data"': NONE_TINT})
    name, bar, order = R('display_name'), R('Full Bar'), R('Attention Order')
    texts = [R('Attention Icon Critical'), R('Attention Icon Warning'), name, R('Attention Incident Tag'),
             R('Attention Reason'), R('Attention Meta'), R('Attention Open Since')]
    ids = [R('node_id (dim_nodes.csv)'), R('node_key')]
    sh = Sheet(
        'HO Needs Attention List', rows=[Nest([order, name])], cols=[bar],
        hide=[order, name, bar], fixed={bar: (0, 1)}, row_height=(name, ATTENTION_ROW),
        filters=[R('Is Attention Node'), R('Is Platform Match Node')],
        panes=Pane('Bar', color=R('Status Tint Key'), lod=ids, text=texts, size=1.65, align='left', valign='center',
                   label=[run(R('Attention Icon Critical'), 10, CRIT, SEMI), run(R('Attention Icon Warning'), 10, WARN, SEMI),
                          run('  ', 9, INK1), run(name, 9, INK1, SEMI), run('   ', 9, INK1),
                          run(R('Attention Incident Tag'), 7, INK2, SEMI), run(NL, 8, INK3),
                          run(R('Attention Reason'), 8, INK2), run(NL, 8, INK3),
                          run(R('Attention Meta'), 8, INK3), run(R('Attention Open Since'), 8, INK3)],
                   tooltip=[run(name, 9, INK1, SEMI), run(NL, 7, INK3), run('CLICK TO SEE WHO IS AFFECTED', 7, INK3, SEMI)]))
    sh.axis_heights = {bar: 25}
    return sh


ATTENTION_ROW = 50  # 3 lines of text (about 38px) plus the 8px gap between alerts in the prototype; v08 had 40


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
    exposure = card('HO Exposure Card', margins={'right': 7}, kids=[
        Z('horz', friendly='HO Exposure Card Header', fixed=58, kids=[
            card_header('Exposure status', 'Every data product, traced through its full upstream chain. Score is the '
                        '7-day health score (0 to 100). Click a tile to open its lineage.', None),
            blank(24),
            _track('HO Tile View Track', 'HO Tile View Buttons', 230)]),
        sheet('HO Exposure Status Tiles'),
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
    ('HO Exposure Status Tiles', lambda: R('node_id (dim_nodes.csv)', 'attr'), 'p_selected_exposure', 'HO Tile Select Exposure'),
    ('HO Exposure Status Tiles', lambda: R('Clear Node Value', 'attr'), 'p_selected_node', 'HO Tile Clear Node'),
    ('HO Exposure Status Tiles', lambda: R('Clear Node Key Value', 'attr'), 'p_selected_node_key', 'HO Tile Clear Node Key'),
    ('HO Needs Attention List', lambda: R('node_id (dim_nodes.csv)'), 'p_selected_node', 'HO Alert Select Node'),
    ('HO Needs Attention List', lambda: R('node_key'), 'p_selected_node_key', 'HO Alert Select Node Key'),
    ('HO Tile View Buttons', lambda: R('Tile View Option'), 'p_tile_view', 'HO Set Tile View'),
]
