"""Tab 4, Lineage explorer (LIN): calc pack section 4, build plan 3.2.

The graph is one fixed-size map pane used as a pixel canvas (as on the Health cards): hidden Latitude /
Longitude axes run in px / 100 around the pane centre. Rows of the Lineage Layout mart give everything:

  node rows   x (layer column 0 to 5), y (row), one per node of the selected exposure's graph
  edge rows   12 points per edge (point_order 1 to 12), x / y along the curve, node_* = parent, child_* = child

Positions follow the prototype's drawLineage(): columns (W - 16) / 6 wide, boxes 0.8 of a column (where the
mart starts and ends every edge), box height 13 to 22 px from the graph's row count, rows stretched to fill the
height. Node boxes are polygons drawn from the node's own outgoing edge rows (path point_order, 3 points per
corner); the exposure, which has no outgoing edge, is drawn from its incoming edge rows. Box names are centred
labels placed at the measured width (map-pane labels only centre reliably), so they read left-aligned.

The side panel is a stack of small sheets, one per source table, with pills and callouts as coloured
containers shown by dynamic zone visibility.
"""

from __future__ import annotations

import csv
import textwrap
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont

from . import cards, shapes as SH
from .core import (Cross, ACCENT, AI_INK, B_DIM, BOOK, CALCS, CANVAS, CARD, CARD_STYLE, CRIT, CRIT_INK, CRIT_TINT, GOOD,
                   GOOD_INK, I_DIM, I_MEA, IMAGES, INK1, INK2, INK3, INK4, LAT, LINE, LINE_SOFT, LON, NAVY, NL, NONE,
                   NONE_TINT, OUT_OF_WINDOW, R_MEA, S_DIM, S_MEA, SEMI, SP_MEA, WARN, WARN_INK, WARN_TINT, Nest, Pane, R,
                   Sheet, Z, blank, card, color_map, label_pane, run, sheet, text)
from .shell import CONTENT_PAD, segmented

P = 'LIN'
DATE = 'date (dim_date.csv)'
ROOT = SH.ROOT
NODES = list(csv.DictReader(open(ROOT / 'data' / 'marts' / 'dim_nodes.csv', encoding='utf-8')))
OWNERS = {r['owner_name']: r for r in csv.DictReader(open(ROOT / 'data' / 'marts' / 'dim_owners.csv', encoding='utf-8'))}
PLAT_COL = {'Snowflake': '#005fae', 'Databricks': '#4baee3', 'Redshift': '#5b5fc7'}

# ================================================================ geometry (px), build plan 3.2
GRAPH_CARD_W, PANEL_CARD_W = 965, 340            # graph card fixed; panel 340 plus a 7 px margin = 1312
GRAPH_INNER_W = GRAPH_CARD_W - 2 * 16 - 2        # 931
GRAPH_INNER_H = 836 - 14 - 10 - 2                # 810 (card padding 14 top, 10 bottom)
HEADER_H, GAP_H, LEGEND_H = 36, 8, 22
W = GRAPH_INNER_W - SH.SLACK                     # 927: the canvas, a few px inside its zone (no scroll bars)
H = GRAPH_INNER_H - HEADER_H - GAP_H - LEGEND_H - SH.SLACK   # 740
COLW = (W - 16) / 6                              # prototype: colW = (W - 16) / 6
NW = 0.8 * COLW                                  # box width: edges in the mart start at x + 0.8
PANEL_INNER_W = PANEL_CARD_W - 2 * 16 - 2        # 306
TABLE_ROW_H = 13                                 # 57 rows (the largest graph) fit the 740 px holder

NH = '[Lineage Box Height]'
YMIN, YMAX = '[Lineage Y Min]', '[Lineage Y Max]'


def _lon(xpx):
    return f'(({xpx}) - {W / 2:g}) / 100'


def _lat(ypx):
    return f'({H / 2:g} - ({ypx})) / 100'


def _ypx(y):
    """Centre of a row in px: the prototype maps the graph's y range onto 34 + nh/2 .. H - 8 - nh/2."""
    top, bottom = f'(34 + {NH} / 2)', f'({H:g} - 8 - {NH} / 2)'
    return f'(IF {YMAX} = {YMIN} THEN {H / 2:g} ELSE {top} + (({y}) - {YMIN}) / ({YMAX} - {YMIN}) * ({bottom} - {top}) END)'


def _xleft(x):
    return f'(8 + ({x}) * {COLW:.3f})'


def _rr12(cx, cy, w, h, r, p='[point_order]'):
    """Point point_order (1 to 12) of a rounded rectangle centred on cx, cy: 3 points per corner arc."""
    i = f'(INT({p}) - 1)'
    k = f'INT({i} / 3)'
    th = f'RADIANS({k} * 90 + ({i} % 3 + 0.5) * 30)'
    dx = f'((CASE {k} WHEN 1 THEN -1 WHEN 2 THEN -1 ELSE 1 END) * (({w}) / 2 - ({r})) + ({r}) * COS({th}))'
    dy = f'((IF {k} < 2 THEN 1 ELSE -1 END) * (({h}) / 2 - ({r})) + ({r}) * SIN({th}))'
    return f'({H / 2:g} - ({cy}) + {dy}) / 100', f'(({cx}) + {dx} - {W / 2:g}) / 100'


def _mp_if(name, why, cond, latlon):
    lat, lon = latlon
    return f'// {name}\n// {why}\nIF {cond} THEN MAKEPOINT(\n    {lat},\n    {lon}\n) END'


# ================================================================ text measured at build time

def _short(r):
    return r['display_short'] or r['display_name']


def _fit(s, maxw, pt, bold=False):
    if SH.text_width(s, pt, bold) <= maxw:
        return s
    while s and SH.text_width(s + '…', pt, bold) > maxw:
        s = s[:-1]
    return s + '…'


def _q(s):
    return '"' + s.replace('"', '""') + '"'


def _wrap(s, maxw, pt, bold=False):
    words, lines, cur = s.split(' '), [], ''
    for wd in words:
        cand = (cur + ' ' + wd).strip()
        if SH.text_width(cand, pt, bold) <= maxw or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def _lines_expr(lines):
    return ' + CHAR(10) + '.join(_q(x) for x in lines)


def _label_calcs():
    """Box label (shortened to fit the box) and its width, per node, measured from dim_nodes."""
    maxw = NW - 30
    lab, wid = [], []
    for r in sorted(NODES, key=lambda r: r['node_id']):
        bold = r['resource_type'] == 'exposure'
        s = _fit(_short(r), maxw, 8, bold)
        lab.append(f'WHEN {_q(r["node_id"])} THEN {_q(s)}')
        wid.append(f'WHEN {_q(r["node_id"])} THEN {SH.text_width(s, 8, bold):.1f}')
    head = '// {n}\n// {why}\nCASE [node_id (mart_lineage_layout.csv)]\n'
    return (head.format(n='Lineage Box Label', why='Box name, shortened to fit the box (measured in Arial 8pt by the build from dim_nodes).')
            + '\n'.join(lab) + '\nEND',
            head.format(n='Lineage Label Width', why='Width in px of Lineage Box Label, so the centred label reads left-aligned from the dot.')
            + '\n'.join(wid) + '\nELSE 60\nEND')


def _event_label(ts):
    if not ts:
        return ''
    d = datetime.fromisoformat(ts.replace('Z', ''))
    return f'{d.day} {d.strftime("%b")}, {d.strftime("%H:%M")}'


def _callout_calcs():
    """The panel callout, wrapped to the 274 px callout at build time (Tableau does not wrap mark labels)."""
    maxw = PANEL_INNER_W - 2 * 12 - 4
    reason, err = [], []
    for r in sorted(NODES, key=lambda r: r['node_id']):
        if r['current_status_code'] not in ('2', '3'):
            continue
        if r['resource_type'] == 'exposure':
            text_ = r['culprit_nodes'] or r['status_reason']
            e = ''
        else:
            text_ = r['status_reason'] + (f' at {_event_label(r["last_event_at"])}' if r['last_run_status'] == 'error' and r['last_event_at'] else '')
            e = r['last_error_message']
        if text_:
            reason.append(f'WHEN {_q(r["node_id"])} THEN {_lines_expr(_wrap(text_, maxw, 8))}')
        if e:
            err.append(f'WHEN {_q(r["node_id"])} THEN {_lines_expr(_wrap(e, maxw, 7))}')
    head = '// {n}\n// {why}\nCASE [node_id (dim_nodes.csv)]\n'
    return (head.format(n='Panel Callout Reason', why='What is wrong with the panel node, wrapped to the callout width by the build (from dim_nodes).')
            + '\n'.join(reason) + '\nEND',
            head.format(n='Panel Callout Error', why='The raw error message under the reason, wrapped by the build (from dim_nodes).')
            + '\n'.join(err) + '\nEND')


# ================================================================ calcs

def calcs():
    on_path = '[Is On Path Node]'
    nx, ny = '[Lineage Node X]', '[Lineage Node Y]'
    box_cx, box_cy = f'({_xleft(nx)} + {NW / 2:.3f})', _ypx(ny)
    ex_cx, ex_cy = f'({_xleft(5)} + {NW / 2:.3f})', _ypx('[Lineage Exposure Y]')
    r_box = f'MIN(6, {NH} / 2)'
    inset = 'IF [Is Selected Node Box] THEN 2 ELSE 1 END'
    ex_inset = 'IF [p_selected_node] = [layout_scope] THEN 2 ELSE 1 END'
    is_edge = '[row_type] = "edge"'
    into_ex = '[row_type] = "edge" AND [child_node_id] = [layout_scope]'
    label, width = _label_calcs()
    c_reason, c_error = _callout_calcs()
    # column dividers and headings come from the edge rows' point_order (1 to 12 on every graph), so all five
    # dividers and six headings show even when a layer has no node in this graph
    bucket = 'INT([point_order])'
    div_x = f'(8 + {bucket} * {COLW:.3f} - 6)'
    headings = ['SOURCES', 'STAGING', 'INTERMEDIATE', 'MARTS', 'BI SEMANTIC LAYER', 'EXPOSURE']
    head_x = 'CASE [Lineage Heading Bucket] ' + ' '.join(
        f'WHEN {k + 1} THEN {8 + k * COLW + 2 + SH.text_width(h_, 7, True) / 2:.1f}' for k, h_ in enumerate(headings)) + ' END'
    sel_exp = lambda f: f'{{ MAX(IF [node_id (dim_nodes.csv)] = [p_selected_exposure] THEN {f} END) }}'
    pan = lambda f: f'{{ MAX(IF [node_id (dim_nodes.csv)] = [Panel Node Id] THEN {f} END) }}'

    f = {
        # ---- graph geometry
        'Lineage Y Min': '// Lineage Y Min\n// Top row of the selected graph (y of its node rows).\n{ FIXED [layout_scope] : MIN(IF [row_type] = "node" THEN [y] END) }',
        'Lineage Y Max': '// Lineage Y Max\n// Bottom row of the selected graph.\n{ FIXED [layout_scope] : MAX(IF [row_type] = "node" THEN [y] END) }',
        'Lineage Box Height': (f'// Lineage Box Height\n// Box height in px, 13 to 22 from the number of rows (prototype drawLineage).\n'
                               f'MIN(22, MAX(13, ({H:g} - 50) / ({YMAX} - {YMIN} + 1.4) - 2))'),
        'Lineage Node X': ('// Lineage Node X\n// Layer column of a node, on every row that carries its node_key (its node row and its outgoing edges).\n'
                           '{ FIXED [layout_scope], [node_key (mart_lineage_layout.csv)] : MIN(IF [row_type] = "node" THEN [x] END) }'),
        'Lineage Node Y': ('// Lineage Node Y\n// Row of a node, on every row that carries its node_key.\n'
                           '{ FIXED [layout_scope], [node_key (mart_lineage_layout.csv)] : MIN(IF [row_type] = "node" THEN [y] END) }'),
        'Lineage Exposure Y': ('// Lineage Exposure Y\n// Row of the graph\'s exposure (its node_id is the layout scope).\n'
                               '{ FIXED [layout_scope] : MIN(IF [row_type] = "node" AND [node_id (mart_lineage_layout.csv)] = [layout_scope] THEN [y] END) }'),
        'Lineage Box Border Point': _mp_if('Lineage Box Border Point', 'Box outline of a node, drawn from its outgoing edge rows (path point_order).',
                                           is_edge, _rr12(box_cx, box_cy, NW, NH, r_box)),
        'Lineage Box Fill Point': _mp_if('Lineage Box Fill Point', 'Box fill, 1 px inside the border (2 px for the selected box).',
                                         is_edge, _rr12(box_cx, box_cy, f'{NW:.3f} - 2 * ({inset})', f'{NH} - 2 * ({inset})', f'{r_box} - ({inset})')),
        'Lineage Dot Point': _mp_if('Lineage Dot Point', 'Status dot, 3.2 px radius, 8 px in from the box edge.',
                                    is_edge, _rr12(f'({_xleft(nx)} + 8)', box_cy, 6.4, 6.4, 3.2)),
        'Lineage Stripe Point': _mp_if('Lineage Stripe Point', 'Platform stripe, 3 px wide, at the right end of the box.',
                                       is_edge, _rr12(f'({_xleft(nx)} + {NW - 5.5:.3f})', box_cy, 3, f'{NH} - 6', 1.5)),
        'Lineage Exposure Border Point': _mp_if('Lineage Exposure Border Point', 'The exposure\'s box, drawn from its incoming edge rows.',
                                                into_ex, _rr12(ex_cx, ex_cy, NW, NH, r_box)),
        'Lineage Exposure Fill Point': _mp_if('Lineage Exposure Fill Point', 'The exposure\'s box fill.',
                                              into_ex, _rr12(ex_cx, ex_cy, f'{NW:.3f} - 2 * ({ex_inset})', f'{NH} - 2 * ({ex_inset})', f'{r_box} - ({ex_inset})')),
        'Lineage Exposure Dot Point': _mp_if('Lineage Exposure Dot Point', 'The exposure\'s status dot.',
                                             into_ex, _rr12(f'({_xleft(5)} + 8)', ex_cy, 6.4, 6.4, 3.2)),
        'Lineage Exposure Stripe Point': _mp_if('Lineage Exposure Stripe Point', 'The exposure\'s platform stripe.',
                                                into_ex, _rr12(f'({_xleft(5)} + {NW - 5.5:.3f})', ex_cy, 3, f'{NH} - 6', 1.5)),
        'Lineage Edge Point': (f'// Lineage Edge Point\n// A point of an edge curve (the mart\'s x in layer columns, y in rows).\n'
                               f'IF {is_edge} THEN MAKEPOINT(\n    {_lat(_ypx("[y]"))},\n    {_lon(_xleft("[x]"))}\n) END'),
        'Lineage Label Point': (f'// Lineage Label Point\n// Middle of a box name: 16 px in from the box edge plus half the name\'s width.\n'
                                f'IF [row_type] = "node" THEN MAKEPOINT(\n    {_lat(_ypx("[y]"))},\n'
                                f'    {_lon(_xleft("[x]") + " + 16 + [Lineage Label Width] / 2")}\n) END'),
        'Lineage Divider Bucket': ('// Lineage Divider Bucket\n// Divider number 1 to 5 (before columns 1 to 5), taken from the edge rows\' point_order.\n'
                                   'IF [row_type] = "edge" AND INT([point_order]) <= 5 THEN INT([point_order]) END'),
        'Lineage Divider Point': (f'// Lineage Divider Point\n// A thin vertical line between layer columns: top at sources rows, bottom at every other row\n'
                                  f'// (drawn as a line with path layer_column, so it always spans the full height).\n'
                                  f'IF NOT ISNULL([Lineage Divider Bucket]) THEN MAKEPOINT(\n'
                                  f'    IF [layer_column] = 0 THEN {(H / 2 - 4) / 100:.4f} ELSE {-H / 2 / 100:.4f} END,\n'
                                  f'    {_lon("8 + [Lineage Divider Bucket] * " + format(COLW, ".3f") + " - 6")}\n) END'),
        'Lineage Heading Bucket': ('// Lineage Heading Bucket\n// Heading number 1 to 6, taken from the edge rows\' point_order.\n'
                                   'IF [row_type] = "edge" AND INT([point_order]) <= 6 THEN INT([point_order]) END'),
        'Lineage Heading Point': (f'// Lineage Heading Point\n// Middle of a layer column heading, which starts 2 px in from the column edge.\n'
                                  f'IF NOT ISNULL([Lineage Heading Bucket]) THEN MAKEPOINT({_lat(10)}, {_lon(head_x)}) END'),
        'Lineage Heading': ('// Lineage Heading\n// Layer column heading above the graph.\nCASE [Lineage Heading Bucket]\n'
                            + '\n'.join(f'WHEN {k + 1} THEN "{h_}"' for k, h_ in enumerate(headings)) + '\nEND'),
        'Lineage Box Label': label,
        'Lineage Label Width': width,
        'Lineage Label On Path': ('// Lineage Label On Path\n// Box name in ink, for boxes on the selected path (or every box when nothing is selected).\n'
                                  '// NULL (not "") on every other row: a box\'s name layer also holds its edge rows, and ATTR of a name\n'
                                  '// and "" shows "*" (v16).\n'
                                  'IF [row_type] = "node" AND [Is On Path Node] AND [node_id (mart_lineage_layout.csv)] <> [layout_scope]\n'
                                  '    THEN [Lineage Box Label] END'),
        'Lineage Label Faded': ('// Lineage Label Faded\n// Box name in pale grey, for boxes off the selected path.\n'
                                'IF [row_type] = "node" AND NOT [Is On Path Node] THEN [Lineage Box Label] END'),
        'Lineage Label Exposure': ('// Lineage Label Exposure\n// The exposure\'s own box name, in bold.\n'
                                   'IF [row_type] = "node" AND [node_id (mart_lineage_layout.csv)] = [layout_scope] THEN [Lineage Box Label] END'),
        # ---- graph colour keys (palettes below)
        'Lineage Box Border Key': ('// Lineage Box Border Key\n// Box border: navy for the selected box, the status colour for warning and critical, pale off the path.\n'
                                   'IF [Is Selected Node Box] THEN "Selected"\nELSEIF NOT [Is On Path Node] THEN "Faded"\n'
                                   'ELSEIF [current_status_code] = 3 THEN "Critical"\nELSEIF [current_status_code] = 2 THEN "Warning"\nELSE "Default"\nEND'),
        'Lineage Box Fill Key': ('// Lineage Box Fill Key\n// Box fill: the status tint, white when healthy, near white off the path.\n'
                                 'IF NOT [Is On Path Node] THEN "Faded"\nELSEIF [current_status_code] = 3 THEN "Critical"\n'
                                 'ELSEIF [current_status_code] = 2 THEN "Warning"\nELSE "Default"\nEND'),
        'Lineage Dot Key': '// Lineage Dot Key\n// Status dot colour, pale off the path.\nIF NOT [Is On Path Node] THEN "Faded" ELSE [Status Label] END',
        'Lineage Stripe Key': '// Lineage Stripe Key\n// Platform stripe colour, pale off the path.\nIF NOT [Is On Path Node] THEN "Faded" ELSE [Platform Name] END',
        'Lineage Exposure Status': '// Lineage Exposure Status\n// Status code of the selected exposure, on every row.\n' + sel_exp('[current_status_code]'),
        'Lineage Exposure Platform': '// Lineage Exposure Platform\n// Platform of the selected exposure, on every row.\n' + sel_exp('[Platform Name]'),
        'Lineage Exposure Border Key': ('// Lineage Exposure Border Key\n// The exposure box border.\n'
                                        'IF [p_selected_node] = [layout_scope] THEN "Selected"\nELSEIF [Lineage Exposure Status] = 3 THEN "Critical"\n'
                                        'ELSEIF [Lineage Exposure Status] = 2 THEN "Warning"\nELSE "Default"\nEND'),
        'Lineage Exposure Fill Key': ('// Lineage Exposure Fill Key\n// The exposure box fill.\n'
                                      'IF [Lineage Exposure Status] = 3 THEN "Critical"\nELSEIF [Lineage Exposure Status] = 2 THEN "Warning"\nELSE "Default"\nEND'),
        'Lineage Exposure Dot Key': ('// Lineage Exposure Dot Key\n// The exposure box status dot.\n'
                                     'CASE [Lineage Exposure Status] WHEN 3 THEN "Critical" WHEN 2 THEN "Warning" WHEN 1 THEN "Healthy" ELSE "No data" END'),
        'Lineage Exposure Stripe Key': '// Lineage Exposure Stripe Key\n// The exposure box platform stripe.\n[Lineage Exposure Platform]',
        # ---- view switch
        'Is Lineage View Button Row': '// Is Lineage View Button Row\n// Keeps the 2 scaffold rows that carry the Graph / Table buttons. Put on Filters (True).\nNOT ISNULL([Lineage View Option])',
        'Lineage View Label Active': '// Lineage View Label Active\n// Button text when this view is selected (Semibold Navy run).\nIF [Is Active Lineage View] THEN [Lineage View Option] ELSE "" END',
        'Lineage View Label Inactive': '// Lineage View Label Inactive\n// Button text when this view is not selected.\nIF NOT [Is Active Lineage View] THEN [Lineage View Option] ELSE "" END',
        # ---- header
        'Selected Exposure Trust': '// Selected Exposure Trust\n// Trust badge of the selected exposure, for the pill beside the picker (dynamic zone visibility).\n' + sel_exp('[trust_badge]'),
        'Show Trust Do Not Use': '// Show Trust Do Not Use\n// DZV: red "Do not use" pill beside the picker.\n[Selected Exposure Trust] = "Do not use"',
        'Show Trust Use With Caution': '// Show Trust Use With Caution\n// DZV: amber "Use with caution" pill.\n[Selected Exposure Trust] = "Use with caution"',
        'Show Trust Trusted': '// Show Trust Trusted\n// DZV: green "Trusted" pill.\n[Selected Exposure Trust] = "Trusted"',
        # ---- table
        # ---- panel
        'Panel Status Code': '// Panel Status Code\n// Status code of the panel node, on every row (for the pills and callout).\n' + pan('[current_status_code]'),
        'Panel Platform': '// Panel Platform\n// Platform of the panel node, on every row.\n' + pan('[platform_now]'),
        'Panel Migrated From': '// Panel Migrated From\n// Platform the panel node moved from, if any.\n' + pan('[migrated_from_platform]'),
        'Panel Build Method': '// Panel Build Method\n// Build method of the panel node (AI-built pill).\n' + pan('[build_method]'),
        'Panel Is Declared': '// Panel Is Declared\n// FALSE for consumers found only in query history (Not registered pill).\n' + pan('IIF([is_declared], 1, 0)'),
        'Show Panel Pill Critical': '// Show Panel Pill Critical\n// DZV: red status pill (not exposures).\n[Panel Status Code] = 3 AND [Panel Resource Type] <> "exposure"',
        'Show Panel Pill Warning': '// Show Panel Pill Warning\n// DZV: amber status pill.\n[Panel Status Code] = 2 AND [Panel Resource Type] <> "exposure"',
        'Show Panel Pill Healthy': '// Show Panel Pill Healthy\n// DZV: green status pill.\n[Panel Status Code] = 1 AND [Panel Resource Type] <> "exposure"',
        'Show Panel Pill No Data': '// Show Panel Pill No Data\n// DZV: grey status pill.\n[Panel Status Code] = 0 AND [Panel Resource Type] <> "exposure"',
        'Show Panel Trust Do Not Use': '// Show Panel Trust Do Not Use\n// DZV: exposures show their trust badge instead of a status.\n[Panel Resource Type] = "exposure" AND [Panel Status Code] = 3',
        'Show Panel Trust Use With Caution': '// Show Panel Trust Use With Caution\n// DZV: amber trust pill.\n[Panel Resource Type] = "exposure" AND [Panel Status Code] = 2',
        'Show Panel Trust Trusted': '// Show Panel Trust Trusted\n// DZV: green trust pill.\n[Panel Resource Type] = "exposure" AND [Panel Status Code] < 2',
        'Show Panel Platform Snowflake': '// Show Panel Platform Snowflake\n// DZV: platform pill.\n[Panel Platform] = "snowflake"',
        'Show Panel Platform Databricks': '// Show Panel Platform Databricks\n// DZV: platform pill.\n[Panel Platform] = "databricks"',
        'Show Panel Platform Redshift': '// Show Panel Platform Redshift\n// DZV: platform pill.\n[Panel Platform] = "redshift"',
        'Show Panel Moved': '// Show Panel Moved\n// DZV: "moved from ..." tag for migrated nodes.\nNOT ISNULL([Panel Migrated From])',
        'Show Panel AI Built': '// Show Panel AI Built\n// DZV: AI-built tag.\n[Panel Build Method] = "ai_assisted"',
        'Show Panel Not Registered': '// Show Panel Not Registered\n// DZV: Not registered tag.\n[Panel Is Declared] = 0',
        'Show Panel Callout Critical': '// Show Panel Callout Critical\n// DZV: red callout with what is wrong.\n[Panel Status Code] = 3',
        'Show Panel Callout Warning': '// Show Panel Callout Warning\n// DZV: amber callout.\n[Panel Status Code] = 2',
        'Show Panel Trace Button': '// Show Panel Trace Button\n// DZV: "Trace downstream impact" for every node except exposures.\n[Panel Resource Type] <> "exposure"',
        'Panel Callout Reason': c_reason,
        'Panel Callout Error': c_error,
        'Panel Name': '// Panel Name\n// Title of the panel: the node\'s full name.\n[display_name]',
        'Panel Owner Text': '// Panel Owner Text\n// Owner row; empty when there is no owner (the red version takes over).\nIF ISNULL([owner_name]) OR [owner_name] = "No owner" THEN "" ELSE [owner_name] END',
        'Panel Owner Missing': '// Panel Owner Missing\n// "No owner" in red.\nIF ISNULL([owner_name]) OR [owner_name] = "No owner" THEN "No owner" ELSE "" END',
        'Panel Team Text': '// Panel Team Text\n// Team row ("-" when there is none).\nIFNULL([owner_team], "-")',
        'Panel Slack Text': '// Panel Slack Text\n// Slack row, from Owners.\nIFNULL([slack_channel], "-")',
        'Panel Project Text': '// Panel Project Text\n// dbt project row.\nIFNULL([dbt_project], "-")',
        'Panel Schema Text': '// Panel Schema Text\n// Schema row.\nIFNULL([schema_name], "-")',
        'Panel Documented Good': '// Panel Documented Good\n// "Yes" in ink.\nIF [has_description] THEN "Yes" ELSE "" END',
        'Panel Documented Bad': '// Panel Documented Bad\n// "No description" in amber ink.\nIF NOT [has_description] THEN "No description" ELSE "" END',
        'Panel Tests Label': '// Panel Tests Label\n// Label of the last details row, models only.\nIF [resource_type] = "model" THEN "Tests defined" ELSE "" END',
        'Panel Tests Good': '// Panel Tests Good\n// Number of tests defined, models only.\nIF [resource_type] = "model" AND [test_count] > 0 THEN STR([test_count]) ELSE "" END',
        'Panel Tests None': '// Panel Tests None\n// "None" in amber ink for models without tests.\nIF [resource_type] = "model" AND [test_count] = 0 THEN "None" ELSE "" END',
        'Panel Last Run Text': '// Panel Last Run Text\n// Bold part of "Last run 1s at 19 Oct, 21:25".\nIF [Last Runtime Label] = "" THEN "-" ELSE [Last Runtime Label] END',
        'Runtime Change Up Text': ('// Runtime Change Up Text\n// "▲ 30%" in red: runtime up more than 25% (7 days against the 28 before).\n'
                                   'IF [Runtime Trend Now] > 0.25 THEN "▲ " + STR(ROUND([Runtime Trend Now] * 100)) + "%" END'),
        'Runtime Change Down Text': ('// Runtime Change Down Text\n// "▼ 30%" in green: runtime down more than 25%.\n'
                                     'IF [Runtime Trend Now] < -0.25 THEN "▼ " + STR(ROUND(-[Runtime Trend Now] * 100)) + "%" END'),
        'Runtime Change Flat Text': ('// Runtime Change Flat Text\n// "▲ 3%" in ink: within 25% either way.\n'
                                     'IF ABS([Runtime Trend Now]) <= 0.25\n'
                                     '    THEN IF [Runtime Trend Now] >= 0 THEN "▲ " ELSE "▼ " END + STR(ROUND(ABS([Runtime Trend Now]) * 100)) + "%" END'),
        'Runtime Change Text': ('// Runtime Change Text\n// "7d vs 28d" after the runtime change, grey.\nIF ISNULL([Runtime Trend Now]) THEN "" ELSE "  7d vs 28d" END'),
        'Failed Runs Bad Text': '// Failed Runs Bad Text\n// "1 failed" in red when any run failed in the period.\nIF [Failed Runs In Period] > 0 THEN STR([Failed Runs In Period]) + " failed" END',
        'Failed Runs Good Text': '// Failed Runs Good Text\n// "0 failed" in green.\nIF [Failed Runs In Period] = 0 THEN "0 failed" END',
        'Is Last 30 Days': '// Is Last 30 Days\n// The test strip shows the last 30 days. Put on Filters (True).\n[days_before_as_of] < 30',
        'Panel Test Key': '// Panel Test Key\n// Test strip colour (its own palette: strong green for All passed).\n[Worst Test Label]',
        'Panel Tests Latest Text': ('// Panel Tests Latest Text\n// "Latest: 2 passing, 1 warning" under the strip.\n'
                                    '"Latest: " + STR(ZN([tests_passing])) + " passing"\n+ IF [tests_warning] > 0 THEN ", " + STR([tests_warning]) + " warning" ELSE "" END'),
        'Panel Tests Failing Text': '// Panel Tests Failing Text\n// ", 1 failing" in red.\nIF [tests_failing] > 0 THEN ", " + STR([tests_failing]) + " failing" ELSE "" END',
        'Panel Warn After Label': ('// Panel Warn After Label\n// "warn after 3.0 h · error after 6.0 h" under the freshness bullet.\n'
                                   '"warn after " + STR(ROUND([warn_after_minutes] / 60, 1)) + " h · error after " + STR(ROUND([error_after_minutes] / 60, 1)) + " h"'),
        'Panel Refresh Ok Text': '// Panel Refresh Ok Text\n// Refresh summary line, start.\nSTR([Refreshes OK In Period]) + " succeeded · "',
        'Panel Refresh Failed Text': '// Panel Refresh Failed Text\n// Failed refreshes, red when above 0.\nSTR([Refreshes Failed In Period]) + " failed"',
        'Panel Refresh Rest Text': ('// Panel Refresh Rest Text\n// " · 2 skipped · extract connection".\n'
                                    '" · " + STR([Refreshes Skipped In Period]) + " skipped · " + IFNULL(ATTR([connection_type]), "live") + " connection"'),
        'Panel Score Now': '// Panel Score Now\n// "99.7" in "Now 99.7 / 100".\nIF ISNULL([health_score_now]) THEN "-" ELSE STR(ROUND([health_score_now], 1)) END',
        'Panel Uses Text': '// Panel Uses Text\n// Usage row: "1,234" before the unit.\nIF ISNULL([Product Uses (Period)]) THEN "0" ELSE STR([Product Uses (Period)]) END',
        # ---- trends: the selected window in the accent, the rest grey (as on the KPI cards)
        **{f'{k} In Period': (f'// {k} In Period\n// {k} inside the selected window.\nIF ATTR([In Period]) THEN {m} END')
           for k, m in (('Runtime Minutes', '[Runtime Minutes (Daily)]'), ('Worst Lag Hours', '[Worst Lag Hours (Daily)]'),
                        ('Health Score', 'AVG([health_score])'), ('Failed Refreshes', 'SUM([refresh_failed])'))},
        **{f'{k} Out Period': (f'// {k} Out Period\n// {k} outside the selected window (grey).\nIF NOT ATTR([In Period]) THEN {m} END')
           for k, m in (('Runtime Minutes', '[Runtime Minutes (Daily)]'), ('Worst Lag Hours', '[Worst Lag Hours (Daily)]'),
                        ('Health Score', 'AVG([health_score])'), ('Failed Refreshes', 'SUM([refresh_failed])'))},
    }
    # freshness bullet: zones and lag bar on a 306 x 14 px canvas, from the Node Daily path (sources only)
    bw, bh = PANEL_INNER_W - SH.SLACK, 14
    scale = f'({bw:g} / (1.25 * [error_after_minutes]))'
    idx = '[Node Path Index]'
    vtx = f'INT({idx} / 22)'

    def rect(x0, x1, y0, y1):
        lon = f'CASE {vtx} WHEN 0 THEN (({x0}) - {bw / 2:g}) / 100 WHEN 1 THEN (({x1}) - {bw / 2:g}) / 100 WHEN 2 THEN (({x1}) - {bw / 2:g}) / 100 ELSE (({x0}) - {bw / 2:g}) / 100 END'
        lat = f'CASE {vtx} WHEN 0 THEN {(bh / 2 - y0) / 100:.4f} WHEN 1 THEN {(bh / 2 - y0) / 100:.4f} WHEN 2 THEN {(bh / 2 - y1) / 100:.4f} ELSE {(bh / 2 - y1) / 100:.4f} END'
        return f'MAKEPOINT(\n    {lat},\n    {lon}\n)'
    f['Bullet Good Point'] = '// Bullet Good Point\n// Freshness bullet: on-time zone, 0 to warn.\n' + rect('0', f'[warn_after_minutes] * {scale}', 3, 11)
    f['Bullet Warn Point'] = '// Bullet Warn Point\n// Freshness bullet: warn zone.\n' + rect(f'[warn_after_minutes] * {scale}', f'[error_after_minutes] * {scale}', 3, 11)
    f['Bullet Error Point'] = '// Bullet Error Point\n// Freshness bullet: error zone, up to 1.25 x the error threshold.\n' + rect(f'[error_after_minutes] * {scale}', f'{bw:g}', 3, 11)
    f['Bullet Lag Point'] = ('// Bullet Lag Point\n// Freshness bullet: the lag now, as a bar in the status colour.\n'
                             + rect('0', f'MIN({bw:g}, ZN([freshness_lag_min]) * {scale})', 5, 9))

    types = {n: SP_MEA for n in f if n.endswith('Point')}
    types.update({
        'Lineage Y Min': R_MEA, 'Lineage Y Max': R_MEA, 'Lineage Box Height': R_MEA, 'Lineage Node X': R_MEA,
        'Lineage Node Y': R_MEA, 'Lineage Exposure Y': R_MEA, 'Lineage Label Width': R_MEA, 'Lineage Exposure Status': I_MEA,
        'Panel Status Code': I_MEA, 'Panel Is Declared': I_MEA,
        'Failed Runs Bad Text': S_MEA, 'Failed Runs Good Text': S_MEA, 'Panel Refresh Ok Text': S_MEA,
        'Panel Refresh Failed Text': S_MEA, 'Panel Refresh Rest Text': S_MEA, 'Panel Uses Text': S_MEA,
        'Runtime Change Text': S_MEA, 'Runtime Change Up Text': S_MEA, 'Runtime Change Down Text': S_MEA, 'Runtime Change Flat Text': S_MEA,
        **{n: R_MEA for n in f if n.endswith(' In Period') or n.endswith(' Out Period')},
        **{n: B_DIM for n in f if n.startswith('Show ') or n.startswith('Is ')},
        'Lineage Divider Bucket': I_DIM, 'Lineage Heading Bucket': I_DIM,
    })
    types.update({n: S_DIM for n in f if n not in types})
    return f, types


PACK_TYPES = {  # calc pack section 4 calcs this tab uses
    'Is Lineage Scope': B_DIM, 'Selected Reach Keys': S_DIM, 'Has Path Selection': B_DIM, 'Is On Path Node': B_DIM,
    'Is On Path Edge': B_DIM, 'Edge Colour Key': S_DIM, 'Is Selected Node Box': B_DIM, 'Node Platform Tooltip': S_DIM,
    'Lineage View Option': S_DIM, 'Is Active Lineage View': B_DIM, 'Show Lineage Graph': B_DIM, 'Show Lineage Table': B_DIM,
    'Is Selected Exposure Upstream Row': B_DIM, 'Runtime Or Lag Label': S_DIM, 'Tests Pass Text': S_DIM,
    'Tests Fail Text': S_DIM, 'Tests Warn Text': S_DIM, 'Exposure Access Line': S_DIM, 'Panel Node Id': S_DIM,
    'Is Panel Node': B_DIM, 'Is Panel Node Daily': B_DIM, 'Is Panel Exposure Daily': B_DIM, 'Panel Resource Type': S_DIM,
    'Show Panel Model': B_DIM, 'Show Panel Source': B_DIM, 'Show Panel Semantic': B_DIM, 'Show Panel Exposure': B_DIM,
    'Panel Kind Line': S_DIM, 'Panel Moved Tag': S_DIM, 'Documented Label': S_DIM, 'Tests Defined Label': S_DIM,
    'Runtime Trend Now': R_MEA, 'Runtime Trend Up': R_MEA, 'Runtime Trend Down': R_MEA, 'Runtime Trend Flat': R_MEA,
    'Runtime Minutes (Daily)': R_MEA, 'Runs In Period': R_MEA, 'Failed Runs In Period': R_MEA,
    'Worst Lag Hours (Daily)': R_MEA, 'Refreshes OK In Period': R_MEA, 'Refreshes Failed In Period': R_MEA,
    'Refreshes Skipped In Period': R_MEA, 'Product Uses (Period)': R_MEA, 'Product Cost (Period)': R_MEA,
    'Cost Per Use': R_MEA, 'Daily Consumers In Period': R_MEA, 'Uses Unit Label': S_DIM, 'Worst Test Label': S_DIM,
    'Last Runtime Label': S_DIM, 'Lag Now Label': S_DIM, 'Exposure Type Name': S_DIM, 'Access Path Label': S_DIM,
    'BI Tool Name': S_DIM, 'Is Selected Exposure': B_DIM,
}

_f, _t = calcs()
CALCS.add(formulas=_f, types={**PACK_TYPES, **_t})



# ================================================================ table mode (pixel canvas, prototype rows)
TABLE_W = GRAPH_INNER_W - 18 - SH.SLACK          # 909: room for the table's own vertical scroll bar
TABLE_ROW = (TABLE_W, 28)                        # one pane per row, 28 px (prototype rows, GB 22 Oct)
TCOL = {'node': 8, 'layer': 199, 'platform': 307, 'status': 401, 'hops': 520, 'last': 536, 'runtime': 726,
        'tests': 810, 'owner': 826}             # x px: left edge, or right edge for hops, runtime and tests
PLAT_PILL = {k: int(SH.text_width('■ ' + k, 7) + 14) for k in PLAT_COL}
STATUS_TEXT = {'Critical': '✕ Critical', 'Warning': '▲ Warning', 'Healthy': '✓ Healthy', 'No data': '– No data'}
STATUS_PILL = {k: int(SH.text_width(v, 7, True) + 16) for k, v in STATUS_TEXT.items()}
LAYER_NAME = {'source': 'Sources', 'staging': 'Staging', 'intermediate': 'Intermediate', 'mart': 'Marts',
              'semantic': 'BI semantic layer', 'exposure': 'Exposures'}


def _num(x):
    """Tableau STR(ROUND(x, 1)): half up, and no trailing .0."""
    v = float(x)
    v = int(v * 10 + (0.5 if v >= 0 else -0.5)) / 10
    return str(int(v)) if v == int(v) else f'{v:.1f}'


def _runtime_or_lag(r):
    """Mirror of Runtime Or Lag Label (calc pack 4.3), so the build can measure it."""
    if r['last_runtime_sec']:
        sec = float(r['last_runtime_sec'])
        if sec < 60:
            return str(int(sec + 0.5)) + 's'
        return _num(sec / 60) + ' min' if sec < 3600 else _num(sec / 3600) + ' h'
    if r['freshness_lag_min']:
        m = float(r['freshness_lag_min'])
        return 'lag ' + (str(int(m + 0.5)) + ' min' if m < 60 else _num(m / 60) + ' h')
    return ''


def _tests(r):
    p, f_, w = (r[k] for k in ('tests_passing', 'tests_failing', 'tests_warning'))
    pas = '' if not p else _num(p) + ' pass'
    fail = f' · {_num(f_)} fail' if f_ and float(f_) > 0 else ''
    warn = f' · {_num(w)} warn' if w and float(w) > 0 else ''
    return pas, fail, warn


def _table_calcs():
    rows = sorted([r for r in NODES if r['resource_type'] != 'exposure'], key=lambda r: r['node_id'])
    cols = {
        'Node': lambda r: (_fit(r['display_name'], TCOL['layer'] - TCOL['node'] - 12, 8), 8, False),
        'Layer': lambda r: (LAYER_NAME.get(r['layer'], ''), 8, False),
        'Last Run': lambda r: (_event_label(r['last_event_at']) or '-', 8, False),
        'Runtime': lambda r: (_runtime_or_lag(r), 8, False),
        'Tests Pass': lambda r: (_tests(r)[0], 8, False),
        'Tests Fail': lambda r: (_tests(r)[1], 8, False),
        'Tests Warn': lambda r: (_tests(r)[2], 8, False),
        'Owner': lambda r: (_fit(r['owner_name'] or 'No owner', TABLE_W - TCOL['owner'] - 4, 8), 8, False),
    }
    f = {}
    for col, get in cols.items():
        txt = '\n'.join(f'WHEN {_q(r["node_id"])} THEN {_q(get(r)[0])}' for r in rows)
        f[f'Table {col} Text'] = (f'// Table {col} Text\n// Table cell "{col}", written by the build from dim_nodes so it can be measured\n'
                                  f'// (map-pane labels only centre reliably, so each cell is placed at half its width).\n'
                                  f'CASE [node_id (mart_lineage_layout.csv)]\n{txt}\nEND')
        wid = '\n'.join(f'WHEN {_q(r["node_id"])} THEN {SH.text_width(get(r)[0], 8):.1f}' for r in rows)
        f[f'Table {col} Width'] = (f'// Table {col} Width\n// Width in px of Table {col} Text (Arial 8pt).\n'
                                   f'CASE [node_id (mart_lineage_layout.csv)]\n{wid}\nELSE 0\nEND')
    return f


def _table_point(name, why, x):
    return (f'// {name}\n// {why}\nIF [row_type] = "node" THEN MAKEPOINT(0, (({x}) - {TABLE_W / 2:g}) / 100) END')


def _table_rect(name, why, x0, x1, y0, y1, r=0):
    """A rectangle (r = 0) or pill on a table row, from the node's outgoing edge rows (point_order 1 to 12)."""
    cx, cy, w, h = f'(({x0}) + ({x1})) / 2', (y0 + y1) / 2, f'(({x1}) - ({x0}))', y1 - y0
    i = '(INT([point_order]) - 1)'
    k = f'INT({i} / 3)'
    th = f'RADIANS({k} * 90 + ({i} % 3 + 0.5) * 30)'
    dx = f'((CASE {k} WHEN 1 THEN -1 WHEN 2 THEN -1 ELSE 1 END) * ({w} / 2 - {r}) + {r} * COS({th}))'
    dy = f'((IF {k} < 2 THEN 1 ELSE -1 END) * ({h / 2 - r:g}) + {r} * SIN({th}))'
    lat = f'({TABLE_ROW[1] / 2 - cy:g} + {dy}) / 100'
    lon = f'({cx} + {dx} - {TABLE_W / 2:g}) / 100'
    return f'// {name}\n// {why}\nIF [row_type] = "edge" THEN MAKEPOINT(\n    {lat},\n    {lon}\n) END'


def table_calcs():
    f = _table_calcs()
    pw = 'CASE [Platform Name] ' + ' '.join(f'WHEN "{k}" THEN {v}' for k, v in PLAT_PILL.items()) + ' ELSE 0 END'
    sw = 'CASE [Status Label] ' + ' '.join(f'WHEN "{k}" THEN {v}' for k, v in STATUS_PILL.items()) + ' ELSE 0 END'
    digit = SH.text_width('0', 8)
    f.update({
        'Table Hops': ('// Table Hops\n// Hops from this node to the selected exposure (Blast Radius), on every row of the node.\n'
                       '{ FIXED [node_id (dim_nodes.csv)] : MIN(IF [exposure_id (mart_blast_radius.csv)] = [p_selected_exposure] THEN [hops] END) }'),
        'Table Hops Text': '// Table Hops Text\n// Hops as text for the right-aligned column.\nIF ISNULL([Table Hops]) THEN "" ELSE STR([Table Hops]) END',
        'Table Row Key': ('// Table Row Key\n// Highlights the selected node\'s row (light accent), as in the prototype.\n'
                          'IF [Is Selected Node Box] THEN "Selected" ELSE "Default" END'),
        'Table Platform Snowflake': '// Table Platform Snowflake\n// Coloured square in the platform pill.\nIF [platform_now] = "snowflake" THEN "■ " END',
        'Table Platform Databricks': '// Table Platform Databricks\n// Coloured square in the platform pill.\nIF [platform_now] = "databricks" THEN "■ " END',
        'Table Platform Redshift': '// Table Platform Redshift\n// Coloured square in the platform pill.\nIF [platform_now] = "redshift" THEN "■ " END',
        'Table Status Critical': '// Table Status Critical\n// Status pill text, red. One of the four status fields is filled per row.\nIF [current_status_code] = 3 THEN "✕ Critical" END',
        'Table Status Warning': '// Table Status Warning\n// Status pill text, amber ink.\nIF [current_status_code] = 2 THEN "▲ Warning" END',
        'Table Status Healthy': '// Table Status Healthy\n// Status pill text, green.\nIF [current_status_code] = 1 THEN "✓ Healthy" END',
        'Table Status No Data': '// Table Status No Data\n// Status pill text, grey.\nIF [current_status_code] = 0 THEN "– No data" END',
        'Table Status Key': '// Table Status Key\n// Status pill fill (status tint).\n[Status Label]',
        'Table Band Point': _table_rect('Table Band Point', 'Row background: light accent for the selected node, otherwise white.',
                                        0, TABLE_W, 0, TABLE_ROW[1] - 1),
        'Table Divider Point': _table_rect('Table Divider Point', 'The 1 px line under each row.', 0, TABLE_W, TABLE_ROW[1] - 1, TABLE_ROW[1]),
        'Table Platform Border Point': _table_rect('Table Platform Border Point', 'Platform pill outline (light grey, radius 4).',
                                                   TCOL['platform'], f'{TCOL["platform"]} + {pw}', 5, 23, 4),
        'Table Platform Fill Point': _table_rect('Table Platform Fill Point', 'Platform pill fill.',
                                                 TCOL['platform'] + 1, f'{TCOL["platform"]} + {pw} - 1', 6, 22, 3),
        'Table Status Pill Point': _table_rect('Table Status Pill Point', 'Status pill (tinted, fully rounded).',
                                               TCOL['status'], f'{TCOL["status"]} + {sw}', 5, 23, 9),
        'Table Node Point': _table_point('Table Node Point', 'Middle of the node name (left-aligned at its column).', f'{TCOL["node"]} + [Table Node Width] / 2'),
        'Table Layer Point': _table_point('Table Layer Point', 'Middle of the layer name.', f'{TCOL["layer"]} + [Table Layer Width] / 2'),
        'Table Platform Text Point': _table_point('Table Platform Text Point', 'Middle of the platform pill.', f'{TCOL["platform"]} + ({pw}) / 2'),
        'Table Status Text Point': _table_point('Table Status Text Point', 'Middle of the status pill.', f'{TCOL["status"]} + ({sw}) / 2'),
        'Table Hops Point': _table_point('Table Hops Point', 'Middle of the hops number (right-aligned).',
                                         f'{TCOL["hops"]} - LEN([Table Hops Text]) * {digit:.2f} / 2'),
        'Table Last Run Point': _table_point('Table Last Run Point', 'Middle of the last run or check time.', f'{TCOL["last"]} + [Table Last Run Width] / 2'),
        'Table Runtime Point': _table_point('Table Runtime Point', 'Middle of the runtime (right-aligned).', f'{TCOL["runtime"]} - [Table Runtime Width] / 2'),
        'Table Tests Point': _table_point('Table Tests Point', 'Middle of the tests text (right-aligned).',
                                          f'{TCOL["tests"]} - ([Table Tests Pass Width] + [Table Tests Fail Width] + [Table Tests Warn Width]) / 2'),
        'Table Owner Point': _table_point('Table Owner Point', 'Middle of the owner name.', f'{TCOL["owner"]} + [Table Owner Width] / 2'),
        'Is Table Row': '// Is Table Row\n// Every upstream node of the graph (the exposure itself is the graph\'s end, not a row).\n[node_id (mart_lineage_layout.csv)] <> [layout_scope]',
    })
    heads = [('NODE', TCOL['node'], 'l'), ('LAYER', TCOL['layer'], 'l'), ('PLATFORM', TCOL['platform'], 'l'),
             ('STATUS', TCOL['status'], 'l'), ('HOPS', TCOL['hops'], 'r'), ('LAST RUN OR CHECK', TCOL['last'], 'l'),
             ('RUNTIME', TCOL['runtime'], 'r'), ('TESTS', TCOL['tests'], 'r'), ('OWNER', TCOL['owner'], 'l')]
    hx = 'CASE [Table Heading Bucket] ' + ' '.join(
        f'WHEN {i + 1} THEN {(x + SH.text_width(h, 7, True) / 2) if a == "l" else (x - SH.text_width(h, 7, True) / 2):.1f}'
        for i, (h, x, a) in enumerate(heads)) + ' END'
    f['Table Heading Bucket'] = ('// Table Heading Bucket\n// Column title number 1 to 9, from the edge rows\' point_order.\n'
                                 'IF [row_type] = "edge" AND INT([point_order]) <= 9 THEN INT([point_order]) END')
    f['Table Heading'] = ('// Table Heading\n// Column title of the lineage table.\nCASE [Table Heading Bucket]\n'
                          + '\n'.join(f'WHEN {i + 1} THEN "{h}"' for i, (h, _, _) in enumerate(heads)) + '\nEND')
    f['Table Heading Point'] = (f'// Table Heading Point\n// Middle of a column title.\n'
                                f'IF NOT ISNULL([Table Heading Bucket]) THEN MAKEPOINT(0, (({hx}) - {TABLE_W / 2:g}) / 100) END')
    types = {n: SP_MEA for n in f if n.endswith('Point')}
    types.update({n: R_MEA for n in f if n.endswith('Width')})
    types.update({'Table Hops': R_MEA, 'Is Table Row': B_DIM, 'Table Heading Bucket': I_DIM})
    types.update({n: S_DIM for n in f if n not in types})
    return f, types


_tf, _tt = table_calcs()
CALCS.add(formulas=_tf, types=_tt)

def palettes():
    color_map(R('Edge Colour Key'), {'"Faded"': '#eef0f2', '"Critical"': CRIT, '"Warning"': WARN, '"On path"': ACCENT, '"Default"': '#cbd0d5'})
    color_map(R('Lineage Box Border Key'), {'"Selected"': NAVY, '"Critical"': CRIT, '"Warning"': WARN, '"Default"': LINE, '"Faded"': '#eef0f2'})
    color_map(R('Lineage Box Fill Key'), {'"Critical"': CRIT_TINT, '"Warning"': WARN_TINT, '"Default"': CARD, '"Faded"': '#fbfbfa'})
    color_map(R('Lineage Dot Key'), {'"Healthy"': GOOD, '"Warning"': WARN, '"Critical"': CRIT, '"No data"': NONE, '"Faded"': '#dfe2e6'})
    color_map(R('Lineage Stripe Key'), {**{f'"{k}"': v for k, v in PLAT_COL.items()}, '"Faded"': '#e3e6ea'})
    color_map(R('Lineage Exposure Border Key'), {'"Selected"': NAVY, '"Critical"': CRIT, '"Warning"': WARN, '"Default"': LINE})
    color_map(R('Lineage Exposure Fill Key'), {'"Critical"': CRIT_TINT, '"Warning"': WARN_TINT, '"Default"': CARD})
    color_map(R('Lineage Exposure Dot Key'), {'"Healthy"': GOOD, '"Warning"': WARN, '"Critical"': CRIT, '"No data"': NONE})
    color_map(R('Lineage Exposure Stripe Key'), {f'"{k}"': v for k, v in PLAT_COL.items()})
    color_map(R('Panel Test Key'), {'"No run"': LINE_SOFT, '"All passed"': GOOD, '"Warning"': WARN, '"Failed"': CRIT})
    color_map(R('Status Label'), {'"Healthy"': GOOD, '"Warning"': WARN, '"Critical"': CRIT, '"No data"': NONE})
    color_map(R('Is Active Lineage View'), {'true': CARD, 'false': CANVAS})
    color_map(R('Table Row Key'), {'"Selected"': '#eef4fb', '"Default"': CARD})
    color_map(R('Table Status Key'), {'"Healthy"': '#eaf6ef', '"Warning"': WARN_TINT, '"Critical"': CRIT_TINT, '"No data"': NONE_TINT})


# ================================================================ sheets

def _a(n):
    return R(n, 'attr')


def _grid(s, pane):
    w, h = pane
    s.fixed_axes = [(LAT, -h / 200, h / 200, 'rows'), (LON, -w / 200, w / 200, 'cols')]
    return s


def _poly(title, point, color=None, mark_color=None, lod=(), inert=True, tooltip=None, path=None, pane=(W, H)):
    return Pane('Polygon', title=title, inert=inert, color=color, mark_color=mark_color, path=path or R('point_order', kind='ok'),
                label_show=False, lod=[R(point, 'clct'), *lod], pane_size=pane, tooltip=tooltip)


def _centre_text(title, point, runs, lod=(), inert=True, tooltip=None, pane=(W, H)):
    return label_pane(title=title, inert=inert, text=[r['_ref'] for r in runs if '_ref' in r], label=runs, align='center',
                      valign='center', lod=[R(point, 'clct'), *lod], pane_size=pane, tooltip=tooltip)


def _node_tip():
    return [run(_a('display_name'), 9, INK1, SEMI), run(NL, 7, INK3),
            run('LAYER   ', 7, INK3, SEMI), run(_a('Layer Name'), 9, NAVY, SEMI), run(NL, 7, INK3),
            run('PLATFORM   ', 7, INK3, SEMI), run(_a('Node Platform Tooltip'), 9, NAVY, SEMI), run(NL, 7, INK3),
            run('STATUS   ', 7, INK3, SEMI), run(_a('Status Label'), 9, NAVY, SEMI), run(NL, 7, INK3),
            run('LAST RUNTIME   ', 7, INK3, SEMI), run(_a('Last Runtime Label'), 9, NAVY, SEMI), run(NL, 7, INK3),
            run('LAG NOW   ', 7, INK3, SEMI), run(_a('Lag Now Label'), 9, NAVY, SEMI), run(NL, 7, INK3),
            run('OWNER   ', 7, INK3, SEMI), run(_a('owner_name'), 9, NAVY, SEMI), run(NL, 7, INK3),
            run('CLICK FOR DETAILS', 7, INK3, SEMI)]


def graph_sheet() -> Sheet:
    key, nid = R('node_key (mart_lineage_layout.csv)'), R('node_id (mart_lineage_layout.csv)')
    ckey = R('child_key')
    col = R('layer_column')
    tip = _node_tip()
    layers = [
        Pane('Line', title='Dividers', inert=True, mark_color=LINE_SOFT, path=col, size=0.5, label_show=False,
             lod=[R('Lineage Divider Point', 'clct'), R('Lineage Divider Bucket')], pane_size=(W, H)),
        _centre_text('Headings', 'Lineage Heading Point', [run(_a('Lineage Heading'), 7, INK3, SEMI)], lod=[R('Lineage Heading Bucket')]),
        Pane('Line', title='Edges', inert=True, color=R('Edge Colour Key'), path=R('point_order', kind='ok'), size=1,
             label_show=False, lod=[R('Lineage Edge Point', 'clct'), R('edge_key')], pane_size=(W, H)),
        _poly('Box border', 'Lineage Box Border Point', color=R('Lineage Box Border Key'), lod=[key, nid], inert=False, tooltip=tip),
        _poly('Box fill', 'Lineage Box Fill Point', color=R('Lineage Box Fill Key'), lod=[key, nid], inert=False, tooltip=tip),
        _poly('Exposure border', 'Lineage Exposure Border Point', color=R('Lineage Exposure Border Key'), lod=[ckey]),
        _poly('Exposure fill', 'Lineage Exposure Fill Point', color=R('Lineage Exposure Fill Key'), lod=[ckey]),
        _poly('Dot', 'Lineage Dot Point', color=R('Lineage Dot Key'), lod=[key]),
        _poly('Stripe', 'Lineage Stripe Point', color=R('Lineage Stripe Key'), lod=[key]),
        _poly('Exposure dot', 'Lineage Exposure Dot Point', color=R('Lineage Exposure Dot Key'), lod=[ckey]),
        _poly('Exposure stripe', 'Lineage Exposure Stripe Point', color=R('Lineage Exposure Stripe Key'), lod=[ckey]),
        _centre_text('Names', 'Lineage Label Point', [run(_a('Lineage Label On Path'), 8, INK1),
                                                      run(_a('Lineage Label Faded'), 8, INK4),
                                                      run(_a('Lineage Label Exposure'), 8, INK1, SEMI)],
                     lod=[key, nid], inert=False, tooltip=tip),
    ]
    return _grid(Sheet('LIN Lineage Graph', rows=[LAT], cols=[LON], filters=[R('Is Lineage Scope')], layers=True,
                       no_basemap=True, zoom=None, panes=[Pane('Automatic', pane_size=(W, H)), *layers]), (W, H))


def table_sheets() -> list[Sheet]:
    """Table mode as a pixel canvas, one 909 x 28 px pane per row: row band, divider, platform and status pills and
    every cell placed at its measured width (left- or right-aligned like the prototype). The table scrolls inside
    its zone for graphs taller than the card (GB, 22 Oct)."""
    key, nid = R('node_key (mart_lineage_layout.csv)'), R('node_id (mart_lineage_layout.csv)')
    pane = TABLE_ROW
    order = [R('layer_column'), R('Status Severity Sort'), R('display_name'), key]
    tip = _node_tip()

    def cell(title, point, runs, lod=()):
        return _centre_text(title, point, runs, lod=[key, *lod], pane=pane)
    layers = [
        _poly('Band', 'Table Band Point', color=R('Table Row Key'), lod=[key, nid], inert=False, tooltip=tip, pane=pane),
        _poly('Divider', 'Table Divider Point', mark_color=LINE_SOFT, lod=[key], pane=pane),
        _poly('Platform border', 'Table Platform Border Point', mark_color=LINE, lod=[key], pane=pane),
        _poly('Platform fill', 'Table Platform Fill Point', mark_color='#f5f5f3', lod=[key], pane=pane),
        _poly('Status pill', 'Table Status Pill Point', color=R('Table Status Key'), lod=[key], pane=pane),
        cell('Node', 'Table Node Point', [run(_a('Table Node Text'), 8, INK1)]),
        cell('Layer', 'Table Layer Point', [run(_a('Table Layer Text'), 8, INK2)]),
        cell('Platform', 'Table Platform Text Point', [run(_a('Table Platform Snowflake'), 7, PLAT_COL['Snowflake']),
                                                       run(_a('Table Platform Databricks'), 7, PLAT_COL['Databricks']),
                                                       run(_a('Table Platform Redshift'), 7, PLAT_COL['Redshift']),
                                                       run(_a('Platform Name'), 7, INK2)]),
        cell('Status', 'Table Status Text Point', [run(_a('Table Status Critical'), 7, CRIT_INK, SEMI), run(_a('Table Status Warning'), 7, WARN_INK, SEMI),
                                                   run(_a('Table Status Healthy'), 7, GOOD_INK, SEMI), run(_a('Table Status No Data'), 7, INK2, SEMI)]),
        cell('Hops', 'Table Hops Point', [run(_a('Table Hops Text'), 8, INK1)]),
        cell('Last run', 'Table Last Run Point', [run(_a('Table Last Run Text'), 8, INK1)]),
        cell('Runtime', 'Table Runtime Point', [run(_a('Table Runtime Text'), 8, INK1)]),
        cell('Tests', 'Table Tests Point', [run(_a('Table Tests Pass Text'), 8, INK3), run(_a('Table Tests Fail Text'), 8, CRIT_INK, SEMI),
                                            run(_a('Table Tests Warn Text'), 8, WARN_INK, SEMI)]),
        cell('Owner', 'Table Owner Point', [run(_a('Table Owner Text'), 8, INK1)]),
    ]
    table = _grid(Sheet('LIN Lineage Table', rows=[Cross([Nest(order), LAT])], cols=[LON],
                        filters=[R('Is Lineage Scope'), R('Is Table Row')], hide=order, layers=True, no_basemap=True,
                        zoom=None, panes=[Pane('Automatic', lod=[key], pane_size=pane), *layers]), pane)
    hp = (TABLE_W, 22)
    header = _grid(Sheet('LIN Lineage Table Header', rows=[LAT], cols=[LON], filters=[R('Is Lineage Scope')], layers=True,
                         no_basemap=True, zoom=None, tooltip=False,
                         panes=[Pane('Automatic', pane_size=hp),
                                _centre_text('Titles', 'Table Heading Point', [run(_a('Table Heading'), 7, INK3, SEMI)],
                                             lod=[R('Table Heading Bucket')], pane=hp)]), hp)
    return [header, table]


def _line_trend(name, key, filt, colour=ACCENT, mark='Line'):
    date = R(DATE, kind='qk')
    tin, tout = R(f'{key} In Period'), R(f'{key} Out Period')
    return Sheet(name, cols=[date], rows=[(tin, tout)], filters=[filt], hide=[date, tin, tout], sync=[tout], tooltip=False,
                 formats={date: '*d mmm yyyy'},
                 panes=[Pane(mark, label_show=False),
                        Pane(mark, axis=tin, label_show=False, mark_color=colour, size=1 if mark == 'Line' else 0.5),
                        Pane(mark, axis=tout, label_show=False, mark_color=OUT_OF_WINDOW, size=1 if mark == 'Line' else 0.5)])


def _lines(name, runs, filt, align='left', valign='center', formats=None, lod=()):
    return Sheet(name, filters=[filt] if filt else [], tooltip=False, formats=formats or {},
                 panes=label_pane(text=[r['_ref'] for r in runs if '_ref' in r], label=runs, align=align, valign=valign, lod=list(lod)))


# Dynamic zone visibility read a stale value in v16 (the pills, callout, sections and trust pill kept the first
# node's state): each DZV calc now sits on Detail of a sheet on the dashboard, so Tableau re-queries it whenever
# the parameters change.
TRUST_DZV = ['Show Trust Do Not Use', 'Show Trust Use With Caution', 'Show Trust Trusted']
PANEL_DZV = ['Show Panel Pill Critical', 'Show Panel Pill Warning', 'Show Panel Pill Healthy', 'Show Panel Pill No Data',
             'Show Panel Trust Do Not Use', 'Show Panel Trust Use With Caution', 'Show Panel Trust Trusted',
             'Show Panel Platform Snowflake', 'Show Panel Platform Databricks', 'Show Panel Platform Redshift',
             'Show Panel Moved', 'Show Panel AI Built', 'Show Panel Not Registered', 'Show Panel Callout Critical',
             'Show Panel Callout Warning', 'Show Panel Trace Button', 'Show Panel Model', 'Show Panel Source',
             'Show Panel Semantic', 'Show Panel Exposure']


def panel_sheets() -> list[Sheet]:
    node, daily, exd = R('Is Panel Node'), R('Is Panel Node Daily'), R('Is Panel Exposure Daily')
    out = [
        _lines('LIN Exposure Header', [run(R('Exposure Access Line'), 8, INK3)], R('Is Selected Exposure'),
               lod=[R(n) for n in TRUST_DZV]),
        _lines('LIN Panel Header', [run(R('Panel Kind Line'), 8, INK3), run(NL, 8, INK3), run(R('Panel Name'), 11, INK1, SEMI)],
               node, valign='top', lod=[R(n) for n in PANEL_DZV]),
        _lines('LIN Panel Moved Tag', [run(R('Panel Moved Tag'), 7, INK2)], node, align='center'),
        _lines('LIN Panel Callout Critical', [run(R('Panel Callout Reason'), 8, CRIT_INK), run(NL, 6, CRIT_INK),
                                              run(R('Panel Callout Error'), 7, CRIT_INK)], node, valign='top'),
        _lines('LIN Panel Callout Warning', [run(R('Panel Callout Reason'), 8, WARN_INK), run(NL, 6, WARN_INK),
                                             run(R('Panel Callout Error'), 7, WARN_INK)], node, valign='top'),
        _lines('LIN Panel Detail Labels', [run('Owner', 8, INK3), run(NL, 8, INK3), run('Team', 8, INK3), run(NL, 8, INK3),
                                           run('Slack', 8, INK3), run(NL, 8, INK3), run('dbt project', 8, INK3), run(NL, 8, INK3),
                                           run('Schema', 8, INK3), run(NL, 8, INK3), run('Documented', 8, INK3), run(NL, 8, INK3),
                                           run(R('Panel Tests Label'), 8, INK3)], node, valign='top'),
        _lines('LIN Panel Details', [run(R('Panel Owner Text'), 8, INK1), run(R('Panel Owner Missing'), 8, CRIT_INK, SEMI), run(NL, 8, INK1),
                                     run(R('Panel Team Text'), 8, INK1), run(NL, 8, INK1),
                                     run(R('Panel Slack Text'), 8, INK1), run(NL, 8, INK1),
                                     run(R('Panel Project Text'), 8, INK1), run(NL, 8, INK1),
                                     run(R('Panel Schema Text'), 8, INK1), run(NL, 8, INK1),
                                     run(R('Panel Documented Good'), 8, INK1), run(R('Panel Documented Bad'), 8, WARN_INK, SEMI), run(NL, 8, INK1),
                                     run(R('Panel Tests Good'), 8, INK1), run(R('Panel Tests None'), 8, WARN_INK, SEMI)], node, valign='top'),
        # model
        _lines('LIN Panel Last Run', [run('Last run ', 8, INK2), run(R('Panel Last Run Text'), 8, INK1, SEMI), run(' at ', 8, INK2),
                                      run(R('Last Event Label'), 8, INK2)], node),
        _lines('LIN Panel Runtime Change', [run(R('Runtime Change Up Text'), 8, CRIT_INK, SEMI), run(R('Runtime Change Down Text'), 8, GOOD_INK, SEMI),
                                            run(R('Runtime Change Flat Text'), 8, INK1, SEMI), run(R('Runtime Change Text'), 8, INK3)],
               daily, align='right'),
        _line_trend('LIN Panel Runtime Trend', 'Runtime Minutes', daily),
        _lines('LIN Panel Runs Summary', [run(R('Runs In Period'), 8, INK1), run(' runs · ', 8, INK2),
                                          run(R('Failed Runs Bad Text'), 8, CRIT_INK, SEMI), run(R('Failed Runs Good Text'), 8, GOOD_INK, SEMI)],
               daily, formats={R('Runs In Period'): 'n#,##0'}),
        Sheet('LIN Panel Test Strip', cols=[R(DATE, kind='ok')], rows=[R('Full Bar')], filters=[daily, R('Is Last 30 Days')],
              hide=[R(DATE, kind='ok'), R('Full Bar')], fixed={R('Full Bar'): (0, 1)}, tooltip=False,
              panes=Pane('Bar', color=R('Panel Test Key'), size=1.6, label_show=False)),
        _lines('LIN Panel Tests Latest', [run(R('Panel Tests Latest Text'), 8, INK3), run(R('Panel Tests Failing Text'), 8, CRIT_INK, SEMI)], node),
        # source
        _lines('LIN Panel Lag Now', [run('Lag ', 8, INK3), run(R('Lag Now Label'), 8, INK1, SEMI)], node),
        _lines('LIN Panel Lag Thresholds', [run(R('Panel Warn After Label'), 8, INK3)], node, align='right'),
        _line_trend('LIN Panel Lag Trend', 'Worst Lag Hours', daily),
        # semantic
        _lines('LIN Panel Refresh Summary', [run(R('Panel Refresh Ok Text'), 8, INK1), run(R('Panel Refresh Failed Text'), 8, CRIT_INK, SEMI),
                                             run(R('Panel Refresh Rest Text'), 8, INK2)], daily),
        _line_trend('LIN Panel Refresh Failures', 'Failed Refreshes', daily, colour=CRIT, mark='Bar'),
        # exposure
        _lines('LIN Panel Score Now', [run('Now ', 8, INK2), run(R('Panel Score Now'), 8, INK1, SEMI), run(' / 100', 8, INK2)], node),
        _line_trend('LIN Panel Score Trend', 'Health Score', exd),
        _lines('LIN Panel Usage Labels', [run('Usage', 8, INK3), run(NL, 8, INK3), run('Daily consumers', 8, INK3), run(NL, 8, INK3),
                                          run('Est. cost', 8, INK3)], exd, valign='top'),
        _lines('LIN Panel Usage Values', [run(R('Panel Uses Text'), 8, INK1), run(' ', 8, INK1), run(_a('Uses Unit Label'), 8, INK1), run(NL, 8, INK1),
                                          run(R('Daily Consumers In Period'), 8, INK1), run(' on average', 8, INK1), run(NL, 8, INK1),
                                          run(R('Product Cost (Period)'), 8, INK1), run(' · ', 8, INK2), run(R('Cost Per Use'), 8, INK2),
                                          run(' per use', 8, INK2)], exd, valign='top',
               formats={R('Daily Consumers In Period'): 'n#,##0.0', R('Product Cost (Period)'): 'c"$"#,##0', R('Cost Per Use'): 'c"$"#,##0.00'}),
    ]
    # freshness bullet: a 302 x 14 px canvas
    bp = (PANEL_INNER_W - SH.SLACK, 14)
    date = R('date', kind='ok')
    bullet = Sheet('LIN Panel Freshness Bullet', rows=[LAT], cols=[LON], filters=[daily], layers=True, no_basemap=True, zoom=None,
                   tooltip=False, panes=[Pane('Automatic', pane_size=bp),
                                         _poly('Good zone', 'Bullet Good Point', mark_color='#eaf6ef', path=date, pane=bp),
                                         _poly('Warn zone', 'Bullet Warn Point', mark_color=WARN_TINT, path=date, pane=bp),
                                         _poly('Error zone', 'Bullet Error Point', mark_color=CRIT_TINT, path=date, pane=bp),
                                         _poly('Lag', 'Bullet Lag Point', color=R('Status Label'), path=date, pane=bp)])
    out.append(_grid(bullet, bp))
    return out


def sheets() -> list[Sheet]:
    palettes()
    cards.palettes()
    buttons = segmented('LIN View Buttons', 'Lineage View Option', 'Lineage View Option', 'Is Active Lineage View',
                        'Lineage View Label Active', 'Lineage View Label Inactive', 'Is Lineage View Button Row')
    return [graph_sheet(), buttons, *table_sheets(), *panel_sheets()]


# ================================================================ buttons (image buttons, like the nav)

BUTTONS = {  # image, label, has the target icon
    'trace': ('btn-trace.png', 'Trace downstream impact', True),
    'usage': ('btn-usage.png', 'See usage and cost', False),
}


def button_width(key) -> int:
    _, label, icon = BUTTONS[key]
    return int(14 + (22 if icon else 0) + SH.text_width(label, 9, True) + 14)


def draw_buttons():
    """Navy action buttons for the panel, drawn like the nav buttons at 2x (Liberation Sans is metric-compatible
    with Arial). Width = padding 14 + icon 22 + text at 9pt bold + padding 14."""
    font = ImageFont.truetype(SH.FONT_B, 24)
    for key, (name, label, icon) in BUTTONS.items():
        w, h = button_width(key) * 2, 30 * 2
        img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([0, 0, w - 1, h - 1], radius=12, fill=NAVY)
        x, cy = 28, h // 2
        if icon:
            d.ellipse([x, cy - 12, x + 24, cy + 12], outline='white', width=3)
            d.ellipse([x + 8, cy - 4, x + 16, cy + 4], outline='white', width=3)
            x += 44
        d.text((x, cy), label, font=font, fill='white', anchor='lm')
        img.save(IMAGES / name)


# ================================================================ dashboard content (build plan 3.2)

def _pill(text_, fg, bg, border, dzv, default=False, fixed=None):
    w = fixed or int(SH.text_width(text_, 7, True) + 18)
    return Z('horz', friendly=f'LIN Pill {text_}', fixed=w, dzv=(dzv, default), kids=[text([run(text_, 7, fg, SEMI)], **{'padding-top': '2'})],
             style={'background-color': bg, 'border-color': border, 'border-style': 'solid', 'border-width': '1',
                    'corner-radius': '10', 'padding-left': '8', 'padding-right': '6', 'margin-right': '6'})


def _section_label(t):
    return text([run(t, 7, INK3, SEMI)], fixed=24, **{'padding-top': '10'})


def content() -> Z:
    draw_buttons()
    graph_header = Z('horz', friendly='LIN Graph Header', fixed=HEADER_H, kids=[
        Z('paramctrl', param='p_selected_exposure', fixed=290, style={'padding-top': '4', 'padding-bottom': '4'}),
        blank(10),
        Z('horz', friendly='LIN Trust Pills', fixed=118, style={'padding-top': '8', 'padding-bottom': '8'}, kids=[
            _pill('✕  Do not use', CRIT_INK, CRIT_TINT, '#f2cdca', 'Show Trust Do Not Use', True),
            _pill('▲  Use with caution', WARN_INK, WARN_TINT, '#f3e0be', 'Show Trust Use With Caution'),
            _pill('✓  Trusted', GOOD_INK, '#eaf6ef', '#cfe8da', 'Show Trust Trusted')]),
        sheet('LIN Exposure Header'),
        Z('horz', friendly='LIN View Track', fixed=130, kids=[sheet('LIN View Buttons')], style={
            'background-color': CANVAS, 'border-color': LINE, 'border-style': 'solid', 'border-width': '1',
            'corner-radius': '8', 'padding': '2', 'margin-top': '2', 'margin-bottom': '2'})])
    leg = [('Healthy', GOOD), ('Warning', WARN), ('Critical', CRIT), ('Snowflake', PLAT_COL['Snowflake']),
           ('Databricks', PLAT_COL['Databricks']), ('Redshift (before migration)', PLAT_COL['Redshift'])]
    rs = []
    for i, (label, colour) in enumerate(leg):
        rs += [run('■ ', 8, colour), run(label + ('     ' if i < len(leg) - 1 else ''), 8, INK2)]
    rs += [run('               Click a node to trace its path and see its details', 8, INK3, italic='true')]
    graph_card = card('LIN Graph Card', fixed=GRAPH_CARD_W, pad=(14, 16, 10, 16), kids=[
        graph_header,
        blank(GAP_H),
        Z('vert', friendly='LIN Graph Holder', dzv=('Show Lineage Graph', True), kids=[sheet('LIN Lineage Graph')]),
        Z('vert', friendly='LIN Table Holder', dzv=('Show Lineage Table', False), kids=[
            sheet('LIN Lineage Table Header', 22), sheet('LIN Lineage Table')]),
        text(rs, fixed=LEGEND_H, **{'padding-top': '6'})])

    pills = Z('horz', friendly='LIN Panel Pills', fixed=22, style={'margin-bottom': '10'}, kids=[
        _pill('✕  Critical', CRIT_INK, CRIT_TINT, '#f2cdca', 'Show Panel Pill Critical', True),
        _pill('▲  Warning', WARN_INK, WARN_TINT, '#f3e0be', 'Show Panel Pill Warning'),
        _pill('✓  Healthy', GOOD_INK, '#eaf6ef', '#cfe8da', 'Show Panel Pill Healthy'),
        _pill('–  No data', INK2, NONE_TINT, LINE, 'Show Panel Pill No Data'),
        _pill('✕  Do not use', CRIT_INK, CRIT_TINT, '#f2cdca', 'Show Panel Trust Do Not Use'),
        _pill('▲  Use with caution', WARN_INK, WARN_TINT, '#f3e0be', 'Show Panel Trust Use With Caution'),
        _pill('✓  Trusted', GOOD_INK, '#eaf6ef', '#cfe8da', 'Show Panel Trust Trusted'),
        _pill('■  Snowflake', PLAT_COL['Snowflake'], '#f5f5f3', LINE, 'Show Panel Platform Snowflake', True),
        _pill('■  Databricks', PLAT_COL['Databricks'], '#f5f5f3', LINE, 'Show Panel Platform Databricks'),
        _pill('■  Redshift', PLAT_COL['Redshift'], '#f5f5f3', LINE, 'Show Panel Platform Redshift'),
        Z('horz', friendly='LIN Moved Tag', fixed=150, dzv=('Show Panel Moved', False), kids=[sheet('LIN Panel Moved Tag')],
          style={'background-color': '#f5f5f3', 'border-color': LINE, 'border-style': 'solid', 'border-width': '1',
                 'corner-radius': '4', 'margin-right': '6'}),
        _pill('AI-built', AI_INK, '#eef0fb', '#d9dcf4', 'Show Panel AI Built'),
        _pill('Not registered', WARN_INK, WARN_TINT, '#f3ddb4', 'Show Panel Not Registered'),
        blank()])

    def callout(kind, bg, border, default):
        return Z('vert', friendly=f'LIN Callout {kind}', fixed=104, dzv=(f'Show Panel Callout {kind}', default),
                 kids=[sheet(f'LIN Panel Callout {kind}')],
                 style={'background-color': bg, 'border-color': border, 'border-style': 'solid', 'border-width': '1',
                        'corner-radius': '8', 'padding': '10', 'margin-bottom': '12'})

    def two(left, right, h, lw=None):
        return Z('horz', fixed=h, kids=[sheet(left, lw), sheet(right)])

    model = Z('vert', friendly='LIN Panel Model Section', fixed=200, dzv=('Show Panel Model', True), kids=[
        _section_label('RUNTIME, 90 DAYS'),
        two('LIN Panel Last Run', 'LIN Panel Runtime Change', 18, 190),
        sheet('LIN Panel Runtime Trend', 46),
        _section_label('RUNS IN PERIOD'),
        sheet('LIN Panel Runs Summary', 18),
        _section_label('TESTS, LAST 30 DAYS'),
        sheet('LIN Panel Test Strip', 16),
        sheet('LIN Panel Tests Latest', 18)])
    source = Z('vert', friendly='LIN Panel Source Section', fixed=168, dzv=('Show Panel Source', False), kids=[
        _section_label('FRESHNESS NOW'),
        sheet('LIN Panel Freshness Bullet', 18),
        two('LIN Panel Lag Now', 'LIN Panel Lag Thresholds', 18, 100),
        _section_label('DAILY WORST LAG, 90 DAYS'),
        sheet('LIN Panel Lag Trend', 46)])
    semantic = Z('vert', friendly='LIN Panel Semantic Section', fixed=140, dzv=('Show Panel Semantic', False), kids=[
        _section_label('REFRESHES IN PERIOD'),
        sheet('LIN Panel Refresh Summary', 18),
        _section_label('FAILED REFRESHES PER DAY'),
        sheet('LIN Panel Refresh Failures', 46)])
    exposure = Z('vert', friendly='LIN Panel Exposure Section', fixed=180, dzv=('Show Panel Exposure', False), kids=[
        _section_label('HEALTH SCORE, 90 DAYS'),
        sheet('LIN Panel Score Now', 18),
        sheet('LIN Panel Score Trend', 46),
        _section_label('IN THIS PERIOD'),
        two('LIN Panel Usage Labels', 'LIN Panel Usage Values', 50, 106)])
    panel = card('LIN Panel Card', fixed=PANEL_CARD_W, pad=(16, 16, 16, 16), margins={'left': 7}, kids=[
        sheet('LIN Panel Header', 46),
        pills,
        callout('Critical', CRIT_TINT, '#f2cdca', True),
        callout('Warning', WARN_TINT, '#f3e0be', False),
        two('LIN Panel Detail Labels', 'LIN Panel Details', 120, 106),
        model, source, semantic, exposure,
        blank(),
        Z('horz', friendly='LIN Trace Holder', fixed=30, dzv=('Show Panel Trace Button', True), kids=[
            Z('imgbutton', friendly='LIN Trace Impact Button', fixed=button_width('trace'), button=dict(target='Blast radius', image='btn-trace.png')), blank()]),
        Z('horz', friendly='LIN Usage Holder', fixed=30, dzv=('Show Panel Exposure', False), kids=[
            Z('imgbutton', friendly='LIN See Usage Button', fixed=button_width('usage'), button=dict(target='Usage & adoption', image='btn-usage.png')), blank()])])
    return Z('horz', friendly='LIN Content', style=CONTENT_PAD, kids=[graph_card, panel])


ACTIONS = [  # (sheet, source Ref factory, parameter, caption)
    ('LIN Lineage Graph', lambda: R('node_id (mart_lineage_layout.csv)'), 'p_selected_node', 'LIN Select Node'),
    ('LIN Lineage Graph', lambda: R('node_key (mart_lineage_layout.csv)'), 'p_selected_node_key', 'LIN Select Node Key'),
    ('LIN Lineage Table', lambda: R('node_id (mart_lineage_layout.csv)'), 'p_selected_node', 'LIN Table Select Node'),
    ('LIN Lineage Table', lambda: R('node_key (mart_lineage_layout.csv)'), 'p_selected_node_key', 'LIN Table Select Node Key'),
    ('LIN View Buttons', lambda: R('Lineage View Option'), 'p_lineage_view', 'LIN Set View'),
]


def check_fit(zones) -> None:
    by = {z.name: z.rect for z in zones if z.kind == 'sheet'}
    _, _, zw, zh = by['LIN Lineage Graph']
    assert W <= zw and H <= zh, f'LIN Lineage Graph: needs {W} x {H} px, zone is {zw:.0f} x {zh:.0f} (scroll bar)'
