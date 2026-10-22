"""Health overview cards (build plan 3.1, v11): exposure tiles by group, group headers and Needs attention.

Each sheet is a grid of fixed-size map panes whose hidden Latitude / Longitude axes run in px / 100 around the
pane centre, so every calc below places things in pixels. Rounded rectangles are polygons (see shapes.py);
text is one clear custom shape per line. Layers, bottom to top:

  tile:   border, fill, coloured top edge, status dot, AI pill border and fill, name, meta, trust, AI text, score
  alert:  border, fill, icon, icon glyph, chevron, tag border and fill, tag text, name, reason, time, meta
  header: group name, count chip border and fill, count
"""

from __future__ import annotations

import csv

from . import shapes as SH
from .core import (LAT, LON, AI_INK, B_DIM, CALCS, CARD, CRIT, CRIT_INK, CRIT_TINT, GOOD, GOOD_INK, I_MEA, INK1,
                   INK2, INK3, LINE, NAVY, NL, NONE, NONE_TINT, R_MEA, S_DIM, SEMI, SP_MEA, WARN, WARN_INK, WARN_TINT,
                   I_DIM, Cross, Nest, Pane, R, Sheet, color_map, label_pane, run)

EXP_IDX, NODE_IDX = '[Exposure Path Index]', '[Node Path Index]'
GAP = SH.LABEL_GAP
TILE_PAD_SPACES, ALERT_PAD_SPACES = 3, 11  # from GB's v13 adjustments
OFFWHITE = '#f5f5f3'
AI_BG, AI_LINE = '#eef0fb', '#d9dcf4'


# ================================================================ point calcs

def _xy(x, y, pane):
    """Latitude / longitude expressions for a spot x, y px from the pane's top left (x may be an expression)."""
    pw, ph = pane
    lon = f'(({x}) - {pw / 2:g}) / 100' if isinstance(x, str) else f'{(x - pw / 2) / 100:.4f}'
    return f'{(ph / 2 - y) / 100:.4f}', lon


def _rr(idx, pane, cx, cy, w, h, r, show=None, top_band=None):
    """Latitude / longitude expressions of point idx (0 to 87) on a rounded rectangle centred on cx, cy.
    Points 0 to 87 walk the four corner arcs, 22 each, counter-clockwise from the top right.
    show: an expression that is 1 or 0; at 0 the shape shrinks to its centre and disappears.
    top_band: keep only the top band of this many px (the coloured top edge of a tile)."""
    pw, ph = pane
    k = f'INT({idx} / 22)'
    th = f'RADIANS({k} * 90 + ({idx} % 22 + 0.5) * 90 / 22)'
    dx = f'((CASE {k} WHEN 1 THEN -1 WHEN 2 THEN -1 ELSE 1 END) * {w / 2 - r:g} + {r:g} * COS({th}))'
    dy = f'((IF {k} < 2 THEN 1 ELSE -1 END) * {h / 2 - r:g} + {r:g} * SIN({th}))'
    if show:
        dx, dy = f'{show} * {dx}', f'{show} * {dy}'
    lon = f'(({cx}) - {pw / 2:g} + {dx}) / 100'
    lat = f'({ph / 2 - cy:g} + {dy}) / 100'
    if top_band is not None:
        lat = f'MAX({lat}, {(ph / 2 - (cy - h / 2 + top_band)) / 100:.4f})'
    return lat, lon


def _mp(name, why, latlon):
    lat, lon = latlon
    return f'// {name}\n// {why}\nMAKEPOINT(\n    {lat},\n    {lon}\n)'


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


TILE_GROUPS = [  # sort, sheet suffix, header text
    (1, 'BI Dashboards', 'BI DASHBOARDS'),
    (2, 'Apps ML Notebooks', 'APPS, ML AND NOTEBOOKS'),
    (3, 'AI Agents Data Hubs', 'AI AGENTS AND DATA HUBS'),
    (4, 'Unregistered', 'UNREGISTERED, FOUND IN QUERY HISTORY'),
]
TILE_ROWS = {1: 4, 2: 1, 3: 1, 4: 1}  # rows of 5 at All, so each group's zone is as tall as its grid


def calcs():
    tp, ap, hp = SH.TILE_PANE, SH.ALERT_PANE, SH.HEADER_PANE
    # card top-left inside its pane
    tx, ty = (tp[0] - SH.TILE_W) / 2, (tp[1] - SH.TILE_H) / 2
    ax, ay = (ap[0] - SH.ALERT_W) / 2, (ap[1] - SH.ALERT_H) / 2
    tcx, tcy = tx + SH.TILE_W / 2, ty + SH.TILE_H / 2
    acx, acy = ax + SH.ALERT_W / 2, ay + SH.ALERT_H / 2
    L, AL = SH.TILE_LINES, SH.ALERT_LINES
    is_ai = 'IIF(IFNULL([build_method], "") = "ai_assisted", 1, 0)'
    has_tag = 'IIF(IFNULL([open_incident_id], "") <> "", 1, 0)'
    ai_x = (f'{tx:g} + CASE [current_status_code] WHEN 3 THEN {SH.ai_pill_x("Critical"):.1f} '
            f'WHEN 2 THEN {SH.ai_pill_x("Warning"):.1f} ELSE {SH.ai_pill_x("Healthy"):.1f} END')
    tag_x = f'{ax + SH.ALERT_TEXT_X + 8 + SH.TAG[0] / 2:g} + [Attention Name Width]'
    pw, ph, pr = SH.AI_PILL
    gw, gh, gr = SH.TAG
    # warning icon: the prototype's triangle (12-unit box) at 16px; other statuses: a circle
    ix, iy, isz = SH.ALERT_ICON
    k = isz / 12
    tri = [(ax + ix - 8 + u * k, ay + iy - 8 + v * k) for u, v in ((6, 1.2), (11, 10.4), (1, 10.4))]
    v = f'INT({NODE_IDX} / 30)'
    tri_lat = f'CASE {v} ' + ' '.join(f'WHEN {i} THEN {(ap[1] / 2 - y) / 100:.4f}' for i, (_, y) in enumerate(tri[:2])) + \
        f' ELSE {(ap[1] / 2 - tri[2][1]) / 100:.4f} END'
    tri_lon = f'CASE {v} ' + ' '.join(f'WHEN {i} THEN {(x - ap[0] / 2) / 100:.4f}' for i, (x, _) in enumerate(tri[:2])) + \
        f' ELSE {(tri[2][0] - ap[0] / 2) / 100:.4f} END'
    c_lat, c_lon = _rr(NODE_IDX, ap, ax + ix, ay + iy, 14.67, 14.67, 7.33)
    has_time = ('[last_run_status] = "error" AND NOT ISNULL([last_event_at]) AND LEN([status_reason]) > 44')
    meta_y = f'IF {has_time} THEN {(ap[1] / 2 - ay - AL["meta4"]) / 100:.4f} ELSE {(ap[1] / 2 - ay - AL["meta3"]) / 100:.4f} END'

    f = {
        # paths
        'Exposure Path Index': ("// Exposure Path Index\n// Point number 0 to 87 along a card outline, from the 90 days of Exposure Daily.\n"
                                "MIN(DATEDIFF('day', { MIN([date (mart_exposure_daily.csv)]) }, [date (mart_exposure_daily.csv)]), 87)"),
        'Node Path Index': ("// Node Path Index\n// Point number 0 to 87 along a card outline, from the 90 days of Node Daily.\n"
                            "MIN(DATEDIFF('day', { MIN([date]) }, [date]), 87)"),
        # colour keys (palettes in the data source)
        'Tile Border Key': '// Tile Border Key\n// Tile border colour by status (#E6E7E2, warning #F1DDB8, critical #EDC3C0).\n[Status Label]',
        'Tile Fill Key': '// Tile Fill Key\n// Tile fill by status: white, critical #FBEAE9.\n[Status Label]',
        'Tile Edge Key': '// Tile Edge Key\n// The 3px top edge of a tile: critical #D2453F, warning #FDF3E1, otherwise the fill.\n[Status Label]',
        'Alert Border Key': '// Alert Border Key\n// Alert border colour by status (critical #F2CDCA, warning #F3E0BE).\n[Status Label]',
        'Alert Icon Key': '// Alert Icon Key\n// Alert icon background: the status colour at 18 to 20% over the alert fill.\n[Status Label]',
        # text
        'Tile Name Short': '// Tile Name Short\n// Tile title cut to fit the card beside the status dot: 17 characters, then "…".\nIF LEN([display_name]) > 18 THEN LEFT([display_name], 17) + "…" ELSE [display_name] END',
        'Tile Meta Text': ('// Tile Meta Text\n// Second tile line, grey: "Tableau · Priya Raman" (the red "No owner" follows when there is none).\n'
                           '[Consumer Type Label] + " · " + [Tile Owner Text]'),
        'Tile Trust Critical': '// Tile Trust Critical\n// Trust badge in red. Only one of the three trust fields is filled for a tile.\nIF [current_status_code] = 3 THEN [trust_badge] ELSE "" END',
        'Tile Trust Warning': '// Tile Trust Warning\n// Trust badge in the warning text colour #93600F.\nIF [current_status_code] = 2 THEN [trust_badge] ELSE "" END',
        'Tile Trust Healthy': '// Tile Trust Healthy\n// Trust badge in green.\nIF [current_status_code] < 2 THEN [trust_badge] ELSE "" END',
        'Tile Group Count': '// Tile Group Count\n// Tiles in this group after the Platform filter and the All / Needs attention switch.\nCOUNTD([node_id (dim_nodes.csv)])',
        'Is Attention Long Reason': f'// Is Attention Long Reason\n// A failed model whose reason plus time would be wider than the card: the time goes on its own line.\n{has_time}',
        'Attention Reason': ('// Attention Reason\n// Second line of the alert: what is wrong, with the time of a failed run when it fits.\n'
                             '[status_reason]\n+ IF [last_run_status] = "error" AND NOT ISNULL([last_event_at]) AND NOT [Is Attention Long Reason]\n'
                             '    THEN " at " + [Last Event Label] ELSE "" END'),
        'Attention Reason Time': ('// Attention Reason Time\n// Third line when the reason is long: "at 19 Oct, 21:25".\n'
                                  'IF [Is Attention Long Reason] THEN "at " + [Last Event Label] ELSE "" END'),
        'Attention Where': '// Attention Where\n// Start of the last alert line: "Staging · Snowflake · ".\n[Layer Name] + " · " + [Platform Name] + " · "',
        'Attention Affects': ('// Attention Affects\n// The bold part of the last alert line: "affects 4 exposures".\n'
                              '"affects " + STR([exposures_fed]) + IF [exposures_fed] = 1 THEN " exposure" ELSE " exposures" END'),
        'Attention Incident Tag': '// Attention Incident Tag\n// Incident tag text after the node name, for example "INC-008". Empty when there is no open incident.\nIFNULL([open_incident_id], "")',
        'Attention Glyph Critical': '// Attention Glyph Critical\n// The cross inside the critical icon.\nIF [current_status_code] = 3 THEN "✕" ELSE "" END',
        'Attention Glyph Warning': '// Attention Glyph Warning\n// The mark inside the warning triangle.\nIF [current_status_code] = 2 THEN "!" ELSE "" END',
        'Attention Name Width': _name_width_calc(),
        'Alert Chevron': '// Alert Chevron\n// The "›" at the right of each alert.\n"›"',
        # tile polygons
        'Tile Border Point': _mp('Tile Border Point', 'Tile outline, 162 x 62 px, radius 8.', _rr(EXP_IDX, tp, tcx, tcy, SH.TILE_W, SH.TILE_H, 8)),
        'Tile Fill Point': _mp('Tile Fill Point', 'Tile fill, 1px inside the border.', _rr(EXP_IDX, tp, tcx, tcy, SH.TILE_W - 2, SH.TILE_H - 2, 7)),
        'Tile Edge Point': _mp('Tile Edge Point', 'The coloured top edge: the fill cut to its top 3px.',
                               _rr(EXP_IDX, tp, tcx, tcy, SH.TILE_W - 2, SH.TILE_H - 2, 7, top_band=SH.TILE_EDGE)),
        'Tile Dot Point': _mp('Tile Dot Point', 'Status dot, 8px, top right.', _rr(EXP_IDX, tp, tx + SH.TILE_DOT[0], ty + SH.TILE_DOT[1], 8, 8, 4)),
        'Tile AI Border Point': _mp('Tile AI Border Point', 'AI-built pill outline after the trust badge; shrinks away when the tile is not AI-built.',
                                    _rr(EXP_IDX, tp, ai_x, ty + L['trust'], pw, ph, pr, show=is_ai)),
        'Tile AI Fill Point': _mp('Tile AI Fill Point', 'AI-built pill fill.', _rr(EXP_IDX, tp, ai_x, ty + L['trust'], pw - 2, ph - 2, pr - 1, show=is_ai)),
        # tile text
        'Tile Name Point': _mp('Tile Name Point', 'Start of the tile name.', _xy(tx + SH.TILE_PAD - GAP, ty + L['name'], tp)),
        'Tile Meta Point': _mp('Tile Meta Point', 'Start of the tool and owner line.', _xy(tx + SH.TILE_PAD - GAP, ty + L['meta'], tp)),
        'Tile Trust Point': _mp('Tile Trust Point', 'Start of the trust badge.', _xy(tx + SH.TILE_PAD - GAP, ty + L['trust'], tp)),
        'Tile AI Text Point': _mp('Tile AI Text Point', 'Middle of the AI-built pill.', _xy(ai_x, ty + L['trust'], tp)),
        'Tile Score Point': _mp('Tile Score Point', 'Right end of the score.', _xy(tx + SH.TILE_W - SH.TILE_PAD + GAP, ty + L['trust'], tp)),
        # alert polygons
        'Alert Border Point': _mp('Alert Border Point', 'Alert outline, 372 x 76 px, radius 8.', _rr(NODE_IDX, ap, acx, acy, SH.ALERT_W, SH.ALERT_H, 8)),
        'Alert Fill Point': _mp('Alert Fill Point', 'Alert fill, 1px inside the border.', _rr(NODE_IDX, ap, acx, acy, SH.ALERT_W - 2, SH.ALERT_H - 2, 7)),
        'Alert Icon Point': (f'// Alert Icon Point\n// Icon background: the warning triangle, or a circle for other statuses.\n'
                             f'MAKEPOINT(\n    IF [current_status_code] = 2 THEN {tri_lat} ELSE {c_lat} END,\n'
                             f'    IF [current_status_code] = 2 THEN {tri_lon} ELSE {c_lon} END\n)'),
        'Alert Tag Border Point': _mp('Alert Tag Border Point', 'Incident tag outline just after the name; shrinks away without an incident.',
                                      _rr(NODE_IDX, ap, tag_x, ay + AL['name'], gw, gh, gr, show=has_tag)),
        'Alert Tag Fill Point': _mp('Alert Tag Fill Point', 'Incident tag fill.', _rr(NODE_IDX, ap, tag_x, ay + AL['name'], gw - 2, gh - 2, gr - 1, show=has_tag)),
        # alert text
        'Alert Glyph Point': _mp('Alert Glyph Point', 'Middle of the icon.', _xy(ax + ix, ay + iy + 0.5, ap)),
        'Alert Chevron Point': _mp('Alert Chevron Point', 'The chevron, right side, middle.', _xy(ax + SH.ALERT_W - 20, acy, ap)),
        'Alert Tag Text Point': _mp('Alert Tag Text Point', 'Middle of the incident tag.', _xy(tag_x, ay + AL['name'], ap)),
        'Alert Name Point': _mp('Alert Name Point', 'Start of the node name.', _xy(ax + SH.ALERT_TEXT_X - GAP, ay + AL['name'], ap)),
        'Alert Reason Point': _mp('Alert Reason Point', 'Start of the reason line.', _xy(ax + SH.ALERT_TEXT_X - GAP, ay + AL['reason'], ap)),
        'Alert Time Point': _mp('Alert Time Point', 'Start of the time line (long reasons only).', _xy(ax + SH.ALERT_TEXT_X - GAP, ay + AL['time'], ap)),
        'Alert Meta Point': _mp('Alert Meta Point', 'Start of the where / affects line, one line lower when the time has its own line.',
                                (meta_y, _xy(ax + SH.ALERT_TEXT_X - GAP, 0, ap)[1])),
    }
    cw, ch, cr = SH.COUNT
    for g, _, title in TILE_GROUPS:
        x = 2 * SH.LABEL_GAP + SH.text_width(title, 7, True) + 6 + cw / 2   # title starts at 2 x gap
        f[f'Is Tile Group {g}'] = f'// Is Tile Group {g}\n// Keeps the tiles of one exposure group on its own sheet. Put on Filters (True).\n[Exposure Group Sort] = {g}'
        f[f'Tile Header Chip Border Point {g}'] = _mp(f'Tile Header Chip Border Point {g}', 'Count chip outline after the group name.',
                                                      _rr(EXP_IDX, hp, x, hp[1] / 2, cw, ch, cr))
        f[f'Tile Header Chip Fill Point {g}'] = _mp(f'Tile Header Chip Fill Point {g}', 'Count chip fill.',
                                                    _rr(EXP_IDX, hp, x, hp[1] / 2, cw - 2, ch - 2, cr - 1))
        f[f'Tile Header Count Point {g}'] = _mp(f'Tile Header Count Point {g}', 'Middle of the count chip.', _xy(x, hp[1] / 2, hp))
    f['Tile Header Title Point'] = _mp('Tile Header Title Point', 'Start of the group name.', _xy(SH.LABEL_GAP, hp[1] / 2, hp))

    types = {n: SP_MEA for n in f if n.endswith('Point') or ' Point ' in n}
    types.update({'Exposure Path Index': I_DIM, 'Node Path Index': I_DIM, 'Tile Group Count': I_MEA,
                  'Attention Name Width': R_MEA, 'Is Attention Long Reason': B_DIM,
                  **{f'Is Tile Group {g}': B_DIM for g, _, _ in TILE_GROUPS}})
    types.update({n: S_DIM for n in f if n not in types})
    return f, types


_f, _t = calcs()
CALCS.add(formulas=_f, types=_t)

def palettes():
    """Palettes for the polygons (data source style). Called when the sheets are built, once Health has typed
    the shared status fields."""
    color_map(R('Status Label'), {'"Healthy"': GOOD, '"Warning"': WARN, '"Critical"': CRIT, '"No data"': NONE})
    color_map(R('Status Tint Key'), {'"Healthy"': CARD, '"Warning"': WARN_TINT, '"Critical"': CRIT_TINT, '"No data"': NONE_TINT})
    color_map(R('Tile Border Key'), {'"Healthy"': LINE, '"Warning"': '#f1ddb8', '"Critical"': '#edc3c0', '"No data"': LINE})
    color_map(R('Tile Fill Key'), {'"Healthy"': CARD, '"Warning"': CARD, '"Critical"': CRIT_TINT, '"No data"': CARD})
    color_map(R('Tile Edge Key'), {'"Healthy"': CARD, '"Warning"': WARN_TINT, '"Critical"': CRIT, '"No data"': CARD})
    color_map(R('Alert Border Key'), {'"Critical"': '#f2cdca', '"Warning"': '#f3e0be', '"Healthy"': LINE, '"No data"': LINE})
    color_map(R('Alert Icon Key'), {'"Critical"': '#f4ccca', '"Warning"': '#e8d6b7', '"Healthy"': NONE_TINT, '"No data"': NONE_TINT})


# ================================================================ layers

def _a(n):
    return R(n, 'attr')


def _poly(title, point, path, pane, lod, *, color=None, mark_color=None, inert=True, tooltip=None):
    return Pane('Polygon', title=title, inert=inert, color=color, mark_color=mark_color, path=path, label_show=False,
                lod=[R(point, 'clct'), *lod], pane_size=pane, tooltip=tooltip)


def _line(title, point, runs, pane, lod=(), align='start', pad=0):
    """One line of text on a hairline Gantt at a point. align: start = the text starts at the point, end = it ends
    there, center = centred on it. On a map pane a Gantt label goes on the opposite side to its text-align
    (v12 screenshot: text-align right put the text left of its point, clamped to the pane edge), so start is
    written as left and end as right."""
    tableau_align = {'start': 'left', 'end': 'right', 'center': 'center'}[align]
    if pad:
        # leading spaces push the line in from the pane edge, as GB set it in Tableau on v13 (3 on tiles, 11 on alerts)
        runs = [run(' ' * pad, 9, INK1, SEMI)] + runs
    return label_pane(title=title, inert=True, text=[r['_ref'] for r in runs if '_ref' in r], label=runs,
                      align=tableau_align, valign='center', lod=[R(point, 'clct'), *lod], pane_size=pane)


def _grid(sheet_obj, pane):
    w, h = pane
    sheet_obj.fixed_axes = [(LAT, -h / 200, h / 200, 'rows'), (LON, -w / 200, w / 200, 'cols')]
    return sheet_obj


def tile_sheets() -> list[Sheet]:
    palettes()
    pane, hp = SH.TILE_PANE, SH.HEADER_PANE
    key, date = R('Tile Sort Key'), R('date (mart_exposure_daily.csv)', kind='ok')
    out = []
    for g, suffix, title in TILE_GROUPS:
        trow, tcol = R('Tile Row', kind='ok'), R('Tile Column', kind='ok')
        for r in (trow, tcol):
            r.tc_order = [key, R('Tile Border Key'), R('Tile Fill Key'), R('Tile Edge Key'), R('Status Label'), date]
        filters = [R('Is Exposure'), R('Is Platform Match Node'), R('Show Exposure Tile'), R(f'Is Tile Group {g}')]
        tip = [run(_a('display_name'), 9, INK1, SEMI), run(NL, 7, INK3),
               run('STATUS   ', 7, INK3, SEMI), run(_a('trust_badge'), 9, NAVY, SEMI), run(NL, 7, INK3),
               run('HEALTH SCORE (7D)   ', 7, INK3, SEMI), run(_a('Tile Score Text'), 9, NAVY, SEMI), run(NL, 7, INK3),
               run('OWNER   ', 7, INK3, SEMI), run(_a('owner_name'), 9, NAVY, SEMI), run(NL, 7, INK3),
               run('WHY   ', 7, INK3, SEMI), run(_a('Tile Tooltip Why'), 9, INK1), run(NL, 7, INK3),
               run('CLICK TO OPEN LINEAGE', 7, INK3, SEMI)]
        ids = [key, _a('node_id (dim_nodes.csv)'), _a('Clear Node Value'), _a('Clear Node Key Value')]
        layers = [
            _poly('Border', 'Tile Border Point', date, pane, ids, color=R('Tile Border Key'), inert=False, tooltip=tip),
            _poly('Fill', 'Tile Fill Point', date, pane, ids, color=R('Tile Fill Key'), inert=False, tooltip=tip),
            _poly('Top edge', 'Tile Edge Point', date, pane, [key], color=R('Tile Edge Key')),
            _poly('Dot', 'Tile Dot Point', date, pane, [key], color=R('Status Label')),
            _poly('AI pill border', 'Tile AI Border Point', date, pane, [key], mark_color=AI_LINE),
            _poly('AI pill fill', 'Tile AI Fill Point', date, pane, [key], mark_color=AI_BG),
            _line('Name', 'Tile Name Point', [run(_a('Tile Name Short'), 9, INK1, SEMI)], pane, [key], pad=TILE_PAD_SPACES),
            _line('Meta', 'Tile Meta Point', [run(_a('Tile Meta Text'), 8, INK3),
                                              run(_a('Tile Owner Missing Text'), 8, CRIT_INK, SEMI)], pane, [key], pad=TILE_PAD_SPACES),
            _line('Trust', 'Tile Trust Point', [run(_a('Tile Trust Critical'), 7, CRIT_INK, SEMI),
                                                run(_a('Tile Trust Warning'), 7, WARN_INK, SEMI),
                                                run(_a('Tile Trust Healthy'), 7, GOOD_INK, SEMI)], pane, [key], pad=TILE_PAD_SPACES),
            _line('AI text', 'Tile AI Text Point', [run(_a('Tile AI Tag'), 7, AI_INK)], pane, [key], align='center'),
            _line('Score', 'Tile Score Point', [run(_a('Tile Score Text'), 8, INK2, SEMI, align=1)], pane, [key], align='end'),
        ]
        out.append(_grid(Sheet(
            f'HO Tiles {suffix}', rows=[Cross([trow, LAT])], cols=[Cross([tcol, LON])], filters=filters,
            hide=[trow, tcol], layers=True, no_basemap=True, zoom=None,
            panes=[Pane('Automatic', lod=[key], pane_size=pane), *layers]), pane))
        out.append(_grid(Sheet(
            f'HO Tiles {suffix} Header', rows=[LAT], cols=[LON], filters=filters, layers=True, no_basemap=True,
            zoom=None, tooltip=False,
            panes=[Pane('Automatic', pane_size=hp),
                   _poly('Chip border', f'Tile Header Chip Border Point {g}', date, hp, [], mark_color=LINE),
                   _poly('Chip fill', f'Tile Header Chip Fill Point {g}', date, hp, [], mark_color=OFFWHITE),
                   _line('Title', 'Tile Header Title Point', [run(title, 7, INK3, SEMI)], hp),
                   _line('Count', f'Tile Header Count Point {g}', [run(R('Tile Group Count'), 7, INK2)], hp, align='center')]),
            hp))
    return out


def attention_sheet() -> Sheet:
    palettes()
    pane = SH.ALERT_PANE
    # ATTR, as on the tiles: display_name as a plain dimension on a polygon layer's tooltip came up invalid in v11
    order, nkey, name, date = R('Attention Order'), R('node_key'), _a('display_name'), R('date', kind='ok')
    ids = [R('node_id (dim_nodes.csv)'), nkey]
    tip = [run(name, 9, INK1, SEMI), run(NL, 7, INK3), run('CLICK TO SEE WHO IS AFFECTED', 7, INK3, SEMI)]
    layers = [
        _poly('Border', 'Alert Border Point', date, pane, ids, color=R('Alert Border Key'), inert=False, tooltip=tip),
        _poly('Fill', 'Alert Fill Point', date, pane, ids, color=R('Status Tint Key'), inert=False, tooltip=tip),
        _poly('Icon', 'Alert Icon Point', date, pane, ids, color=R('Alert Icon Key')),
        _poly('Tag border', 'Alert Tag Border Point', date, pane, ids, mark_color=LINE),
        _poly('Tag fill', 'Alert Tag Fill Point', date, pane, ids, mark_color=OFFWHITE),
        _line('Glyph', 'Alert Glyph Point', [run(R('Attention Glyph Critical'), 8, CRIT, SEMI),
                                             run(R('Attention Glyph Warning'), 8, WARN_INK, SEMI)], pane, ids, align='center'),
        _line('Chevron', 'Alert Chevron Point', [run(R('Alert Chevron'), 12, INK3)], pane, ids, align='center'),
        _line('Tag text', 'Alert Tag Text Point', [run(R('Attention Incident Tag'), 8, INK2)], pane, ids, align='center'),
        _line('Name', 'Alert Name Point', [run(name, 9, INK1, SEMI)], pane, ids, pad=ALERT_PAD_SPACES),
        _line('Reason', 'Alert Reason Point', [run(R('Attention Reason'), 8, INK2)], pane, ids, pad=ALERT_PAD_SPACES),
        _line('Time', 'Alert Time Point', [run(R('Attention Reason Time'), 8, INK2)], pane, ids, pad=ALERT_PAD_SPACES),
        _line('Meta', 'Alert Meta Point', [run(R('Attention Where'), 8, INK2), run(R('Attention Affects'), 8, INK1, SEMI),
                                           run(R('Attention Open Since'), 8, INK2)], pane, ids, pad=ALERT_PAD_SPACES),
    ]
    return _grid(Sheet(
        'HO Needs Attention List', rows=[Cross([Nest([order, nkey]), LAT])], cols=[LON],
        filters=[R('Is Attention Node'), R('Is Platform Match Node')], hide=[order, nkey],
        layers=True, no_basemap=True, zoom=None,
        panes=[Pane('Automatic', lod=ids, pane_size=pane), *layers]), pane)
