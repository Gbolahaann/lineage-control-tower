"""Tab 9, About & how to use (AB), build plan 3.10, and the Documentation page (DOC), build plan 3.11 (decision D5).

GB's choices (25 Oct): Documentation built with About and linked from its foot; the layer chain as a canvas with live
counts; the "Where the numbers come from" table as a canvas with row lines; the filter band keeps its controls with
the hint "Period and Platform apply to every other page".

- About: three cards. What this is (two paragraphs, the layer chain, how to use it, the synthetic-data callout and the
  link to Documentation), Where the numbers come from (table and "Built for any tool") and Metric definitions.
- Layer chain: six rounded chips, each on one scaffold model's 90 Node Daily rows (as the Blast radius pills); the
  counts are FIXED counts of dim_nodes, so they follow the data. v47 drew it as a date-table scene with the count LOD
  in it, and Tableau showed nothing at all: a dim_nodes LOD in a sheet on dim_date blanks the whole sheet.
- Sources table: a scene too, so rows can be as tall as their wrapped text, with the prototype's row lines.
- Documentation: text objects only (apart from GL Data Updated). The parameter and action lists are written from the
  builder's own action lists, so they can't drift from the workbook.
"""

from __future__ import annotations

import collections
import csv

from . import shapes as SH
from .core import (B_DIM, CALCS, CARD, I_DIM, INK1, INK2, INK3, LAT, LINE, LINE_SOFT, LON, NAVY, NL, PARAMS, SEMI, SP_MEA, S_DIM,
                   Pane, R, Sheet, Z, blank, card, card_header, label_pane, run, sheet, text)
from .gov import _scene_calcs, _scene_sheet
from .lineage import _grid, _wrap
from .usage import _calc, _case, _rounded
from .shell import CONTENT_H, CONTENT_PAD

P = 'AB'
DEVELOPER = 'Gbolahan Adebayo'
LINKEDIN = 'https://www.linkedin.com/in/gbolahan-adebayo/'   # GB, v50: the developer line opens his profile
LINK = '#005fae'
CHIP_FILL = '#f5f5f3'
W = lambda s, pt, b=False: SH.text_width(s, pt, b)

# ---------------------------------------------------------------- geometry (content 1312 x CONTENT_H)
# the prototype's 1.1fr : 1fr : 1fr: 456 / 414 / 414 visible (a fixed size leaves out the zone's own margins)
WHAT_CARD, SRC_CARD = 456, 414
WHAT_W = WHAT_CARD - 2 - 2 * 16 - SH.MAP_SLACK   # 410: the layer chain
SRC_W = SRC_CARD - 2 - 2 * 16 - SH.MAP_SLACK     # 368: the sources table


# ================================================================ layer chain

LAYERS = [('Raw sources', 'source'), ('Staging', 'staging'), ('Intermediate', 'intermediate'), ('Marts', 'mart'),
          ('BI semantic layer', 'semantic'), ('Exposures', 'exposure')]
CHIP_H, CHIP_GAP, ARROW = 38, 8, '→'


NODES = {r['node_id']: r for r in csv.DictReader(open(SH.ROOT / 'data' / 'marts' / 'dim_nodes.csv', encoding='utf-8'))}


def _layer_counts():
    return {lay: sum(1 for r in NODES.values() if r['layer'] == lay) for _, lay in LAYERS}


COUNTS = _layer_counts()                         # only to measure the count text; Tableau counts live


def chain_layout():
    """Chip boxes and arrows, wrapped like the prototype: [(x, y, w, label, layer)], [(x, y)] arrow centres."""
    chips, arrows = [], []
    x = y = 0
    aw = W(ARROW, 8) + 12
    for i, (label, lay) in enumerate(LAYERS):
        w = round(max(W(label, 8), W(str(COUNTS[lay]), 10, True)) + 18)
        if x + w > WHAT_W:
            x, y = 0, y + CHIP_H + CHIP_GAP
        chips.append((x, y, w, label, lay))
        x += w
        if i < len(LAYERS) - 1 and x + aw <= WHAT_W:
            arrows.append((x + aw / 2, y + CHIP_H / 2))
            x += aw
        else:
            arrows.append(None)
    return chips, arrows, (WHAT_W, y + CHIP_H + 1)


CHIPS, ARROWS, CHAIN_PANE = chain_layout()
# six scaffold models: each one's 90 Node Daily rows draw one chip (rounded, 22 points a corner, as the Blast radius
# pills), the way the v47 date-table scene could not: it came out blank in Tableau (GB, v47)
CHAIN_CARRIERS = sorted(k for k, n in NODES.items() if n['resource_type'] == 'model')[:len(LAYERS)]


# ================================================================ where the numbers come from

SOURCES = [('dim_nodes, lineage edges', 'dbt manifest.json + BI metadata APIs'),
           ('Model runs, tests', 'run_results.json or the Elementary package'),
           ('Source freshness', 'sources.json'),
           ('Job runs', 'dbt Cloud Admin API'),
           ('BI refreshes', 'Tableau Admin Insights, Power BI and Sigma APIs'),
           ('Warehouse cost', 'Snowflake ACCOUNT_USAGE, Databricks system.billing, Redshift SYS_QUERY_HISTORY'),
           ('Consumption', 'BI activity logs, app logs, agent call logs'),
           ('Observed access', 'Warehouse query history by principal')]
SRC_X, HEAD_H, LINE_H, PAD = 156, 24, 13, 7      # source column, title row, wrapped line step, row padding


def sources_scene():
    rects, texts = [], []
    texts += [('Head', 'TABLE', 8 + W('TABLE', 7, True) / 2, HEAD_H / 2), ('Head', 'PRODUCTION SOURCE', SRC_X + W('PRODUCTION SOURCE', 7, True) / 2, HEAD_H / 2)]
    rects.append((0, HEAD_H - 1, SRC_W, HEAD_H, 'Line'))
    y = HEAD_H
    for term, src in SOURCES:
        t_lines, s_lines = _wrap(term, SRC_X - 8 - 12, 8), _wrap(src, SRC_W - SRC_X - 4, 8)
        n = max(len(t_lines), len(s_lines))
        h = 2 * PAD + n * LINE_H
        for j, s in enumerate(t_lines):
            texts.append(('Term', s, 8 + W(s, 8) / 2, y + PAD + LINE_H / 2 + j * LINE_H))
        for j, s in enumerate(s_lines):
            texts.append(('Source', s, SRC_X + W(s, 8) / 2, y + PAD + LINE_H / 2 + j * LINE_H))
        y += h
        rects.append((0, y - 1, SRC_W, y, 'Soft'))
    return {'all': (rects, texts)}, (SRC_W, y)


SRC_SCENES, SRC_PANE = sources_scene()

# ---------------------------------------------------------------- calcs
_f, _t = {}, {}
a, b = _scene_calcs('AB Sources', SRC_SCENES, '"all"', SRC_PANE, ('Head', 'Term', 'Source'))
_f.update(a)
_t.update(b)


def _chain_calcs():
    pane, idx, f = CHAIN_PANE, '[Node Path Index]', {}
    chip = '[AB Chain Chip]'
    f['AB Chain Chip'] = _calc('AB Chain Chip', 'Which chip a scaffold model\'s Node Daily rows draw (0 to 5, raw sources first).',
                               _case('[node_id (dim_nodes.csv)]', {k: str(i) for i, k in enumerate(CHAIN_CARRIERS)}, quote=False))
    f['Is AB Chain Carrier'] = _calc('Is AB Chain Carrier', 'The six scaffold models. Put on Filters (True).', f'NOT ISNULL({chip})')
    edge = {i: _rounded(idx, x, w, y, y + CHIP_H, 6, pane) for i, (x, y, w, _l, _y) in enumerate(CHIPS)}
    fill = {i: _rounded(idx, x + 1, w - 2, y + 1, y + CHIP_H - 1, 5, pane) for i, (x, y, w, _l, _y) in enumerate(CHIPS)}
    f['AB Chain Edge Point'] = _calc('AB Chain Edge Point', 'Chip outline: a rounded box in the line colour, rows 0 to 87.', _case(chip, edge, quote=False))
    f['AB Chain Fill Point'] = _calc('AB Chain Fill Point', 'Chip fill, 1 px inside the outline.', _case(chip, fill, quote=False))
    at = lambda x, y: f'MAKEPOINT({(pane[1] / 2 - y) / 100:.4f}, {(x - pane[0] / 2) / 100:.4f})'
    f['AB Chain Label Text'] = _calc('AB Chain Label Text', 'Layer name (row 0 of its chip).',
                                     f'IF {idx} = 0 THEN ' + _case(chip, {i: c[3] for i, c in enumerate(CHIPS)}) + ' END')
    f['AB Chain Label Point'] = _calc('AB Chain Label Point', 'Left in the chip, top line (centred at half its measured width).',
                                      f'IF {idx} = 0 THEN ' + _case(chip, {i: at(x + 9 + W(lab, 8) / 2, y + 12) for i, (x, y, _w, lab, _l) in enumerate(CHIPS)},
                                                                    quote=False) + ' END')
    counts = {i: f'{{ FIXED : COUNTD(IF [layer] = "{lay}" THEN [node_id (dim_nodes.csv)] END) }}' for i, (*_r, lay) in enumerate(CHIPS)}
    f['AB Chain Count Text'] = _calc('AB Chain Count Text', 'Nodes in the layer, counted live from dim_nodes (row 1 of its chip).',
                                     f'IF {idx} = 1 THEN STR(' + _case(chip, counts, quote=False) + ') END')
    f['AB Chain Count Point'] = _calc('AB Chain Count Point', 'Left in the chip, under the name (measured from today\'s count).',
                                      f'IF {idx} = 1 THEN ' + _case(chip, {i: at(x + 9 + W(str(COUNTS[lay]), 10, True) / 2, y + 27)
                                                                           for i, (x, y, _w, _lab, lay) in enumerate(CHIPS)}, quote=False) + ' END')
    f['AB Chain Arrow Text'] = _calc('AB Chain Arrow Text', 'The arrow after a chip (row 2), not after the last.',
                                     f'IF {idx} = 2 THEN ' + _case(chip, {i: ARROW for i, a in enumerate(ARROWS) if a}) + ' END')
    f['AB Chain Arrow Point'] = _calc('AB Chain Arrow Point', 'Between two chips.',
                                      f'IF {idx} = 2 THEN ' + _case(chip, {i: at(*a) for i, a in enumerate(ARROWS) if a}, quote=False) + ' END')
    t = {n: (SP_MEA if n.endswith('Point') else B_DIM if n.startswith('Is ') else I_DIM if n == 'AB Chain Chip' else S_DIM) for n in f}
    return f, t


a, b = _chain_calcs()
_f.update(a)
_t.update(b)
CALCS.add(formulas=_f, types=_t)


CALCS.add(formulas={'AB Developer Name': f'// AB Developer Name\n// The developer line on About; a click opens his LinkedIn profile.\n"{DEVELOPER}"'},
          types={'AB Developer Name': S_DIM})
URL_ACTIONS = [('AB Developer', 'AB Open LinkedIn Profile', LINKEDIN)]   # (sheet, caption, url)
DEHIGHLIGHT = ['AB Developer']


def developer_sheet():
    name = R('AB Developer Name')
    return Sheet('AB Developer', filters=[R('Is First Date Row')], panes=label_pane(
        text=[name], valign='top', label=[run('DEVELOPER', 7, INK3, SEMI), run(NL, 7, INK3), run(name, 10, NAVY, SEMI)],
        tooltip=[run('Open LinkedIn profile', 8, INK2)]))


def sheets():
    pane, path, chip, idx = CHAIN_PANE, R('Node Path Index', kind='ok'), R('AB Chain Chip'), R('Node Path Index')
    poly = lambda title, point, colour: Pane('Polygon', title=title, inert=True, mark_color=colour, path=path, label_show=False,
                                             lod=[R(point, 'clct'), chip], pane_size=pane)
    words = lambda title, n, size, colour, bold: label_pane(title=title, inert=True, text=[R(f'AB Chain {n} Text', 'attr')],
                                                           label=[run(R(f'AB Chain {n} Text', 'attr'), size, colour, SEMI if bold else 'Arial')],
                                                           align='center', valign='center', lod=[R(f'AB Chain {n} Point', 'clct'), chip, idx],
                                                           pane_size=pane)
    chain = _grid(Sheet('AB Layer Chain', rows=[LAT], cols=[LON], filters=[R('Is AB Chain Carrier')], layers=True, no_basemap=True, zoom=None,
                        tooltip=False, panes=[Pane('Automatic', pane_size=pane), poly('Edge', 'AB Chain Edge Point', LINE),
                                              poly('Fill', 'AB Chain Fill Point', CHIP_FILL), words('Labels', 'Label', 8, INK1, False),
                                              words('Counts', 'Count', 10, NAVY, True), words('Arrows', 'Arrow', 8, INK3, False)]), pane)
    return [developer_sheet(), chain,
            _scene_sheet('AB Sources Table', 'AB Sources', SRC_PANE, {'Head': (7, INK3, True), 'Term': (8, INK1, False), 'Source': (8, INK2, False)},
                         {'Line': LINE, 'Soft': LINE_SOFT})]


# ================================================================ About content (build plan 3.10)

DEFINITIONS = [
    ('Run success', 'Successful model runs ÷ all model runs, skipped excluded'),
    ('Test pass rate', 'Passing tests ÷ all tests run. Warnings count as not passing'),
    ('Freshness SLA', 'Passing hourly freshness checks ÷ all checks'),
    ('Exposure status', 'Critical if anything upstream has failed, is past its freshness error threshold or failed to refresh. '
                        'Warning for failing tests, late sources or skipped refreshes'),
    ('Health score', '40% upstream run success + 30% test pass + 30% freshness, over 7 days'),
    ('Mean time to recover', 'First failure to next success, per node'),
    ('Risk score', 'Daily downstream consumers × failure rate'),
    ('Cost per exposure', 'Upstream build cost split evenly across exposures fed, plus own queries'),
    ('Retire candidate', 'Under 10 uses in 30 days and over $5 per use'),
    ('Incremental candidate', 'Table over 10M rows whose 7-day runtime is 25%+ above its 28-day average')]


def _para(*runs_, fixed=None, **style):
    return text(list(runs_), fixed=fixed, **style)


def content() -> Z:
    body = lambda s, b=False: run(s, 9, INK1 if b else INK2, SEMI if b else 'Arial')
    gap = run(NL, 6, INK2)
    what = card('AB What Card', fixed=WHAT_CARD, margins={'right': 7}, kids=[
        # GB, v47: his name as the developer, a small label line at the top of the card
        # a one-mark sheet that looks like the v48 text line, so a click can open his LinkedIn profile (URL action)
        sheet('AB Developer', 40),
        blank(1, LINE_SOFT), blank(10),
        text([run('What this is', 10, INK1, SEMI)], fixed=30),
        _para(body('Lineage Control Tower monitors every data product at Acme Retail Co. and traces each one back through dbt to the raw '
                   'tables that feed it. It answers one question per page: what broke, who is affected, what is slow, what is expensive, '
                   'and what nobody uses.'), run(NL, 9, INK2), gap,
              body('A data product here is anything that reads the warehouse: BI dashboards in Tableau, Sigma and Power BI, notebooks, '
                   'ML models, Databricks apps, AI agents and data hubs built in Claude. Each one is registered as a dbt exposure, so it '
                   'sits at the end of the lineage chain.'), fixed=196),
        blank(4), sheet('AB Layer Chain', CHAIN_PANE[1]), blank(12),
        _para(body('How to use it. ', True), body('Start on Health overview. Click any exposure tile to see its lineage, click any node to see '
                                                  'its history, then use Trace downstream impact to see who to tell. Period and Platform at '
                                                  'the top apply to every page.'), fixed=84),
        text([run('The data is synthetic. ', 9, NAVY, SEMI),
              run('Acme Retail Co. is fictional. 90 days of dbt runs, tests, freshness checks, BI refreshes, warehouse cost and usage were '
                  'generated in Python with eleven planted stories, such as a Monday test failure, a Stripe outage on month-end close and '
                  'an AI agent reading data nobody registered.', 9, NAVY)], fixed=128,
             **{'background-color': '#eef4fb', 'border-color': '#cfe0f1', 'border-style': 'solid', 'border-width': '1', 'corner-radius': '8',
                'padding-left': '12', 'padding-right': '12', 'padding-top': '8', 'margin-top': '4'}),
        blank(),
        # the D5 link: a text button (Tableau centres its caption, so the button is as wide as the text)
        Z('horz', friendly='AB Docs Link Row', fixed=28, kids=[
            # GB, v47: 192 wide, no padding, Tableau's own button border setting
            Z('button', fixed=192, style={'padding': '0'}, button=dict(
                target='Documentation', caption='Documentation for developers ›', color=LINK, font='Arial', size=8,
                format={'background-color': CARD})),
            blank()])])
    sources = card('AB Sources Card', fixed=SRC_CARD, margins={'left': 7, 'right': 7}, kids=[
        card_header('Where the numbers come from', 'In production, every table maps to something you already have'),
        sheet('AB Sources Table', SRC_PANE[1]),
        text([run('BUILT FOR ANY TOOL', 7, INK3, SEMI)], fixed=30, **{'padding-top': '14'}),
        blank(1, LINE_SOFT),
        text([run('The data model is the product. This view is built in Tableau, and the same tables can drive Sigma, Power BI, Looker, '
                  'a Claude-built data hub, or an agent that answers questions about data health.', 8, INK3)], fixed=70, **{'padding-top': '6'}),
        blank()])
    defs = [run('Metric definitions', 10, INK1, SEMI), run(NL, 8, INK3)]
    for term, d in DEFINITIONS:
        defs += [run(NL, 6, INK2), run(term, 9, INK1, SEMI), run(NL, 9, INK1), run(d, 8, INK2), run(NL, 8, INK2)]
    definitions = card('AB Definitions Card', margins={'left': 7}, kids=[text(defs)])
    return Z('horz', friendly='AB Content', style=CONTENT_PAD, kids=[what, sources, definitions])


def check_fit(zones) -> None:
    by = {(z.name or z.friendly): z.rect for z in zones}
    for name, (w, h) in (('AB Layer Chain', CHAIN_PANE), ('AB Sources Table', SRC_PANE)):
        _, _, zw, zh = by[name]
        assert w <= zw and h <= zh, f'{name}: needs {w:.0f} x {h:.0f}, zone is {zw:.0f} x {zh:.0f}'
    _, y, _, h = by['AB What Card']
    assert y + h <= 1000, 'AB What card runs off the page'


# ================================================================ Documentation (build plan 3.11, decision D5)

# the builder's own action lists, handed over by build_workbook so this page can't drift from the workbook
ACTION_LISTS: dict = {}
SHORT = {'HO': 'Health', 'RUN': 'Runs', 'FR': 'Freshness', 'LIN': 'Lineage', 'BR': 'Blast radius', 'QA': 'Data quality',
         'PF': 'Performance', 'US': 'Usage', 'GOV': 'Governance', 'AB': 'About', 'DOC': 'Documentation'}
CONTROLS = {'p_selected_exposure': 'LIN', 'p_selected_node': 'BR', 'p_us_sort': 'US'}   # dropdowns on a page
USED_FOR = {'p_period': 'Every period window and comparison', 'p_platform': 'Every platform match',
            'p_selected_exposure': 'Lineage scope, selection highlight', 'p_selected_node': 'Blast radius scope, node panel',
            'p_selected_node_key': 'Lineage path highlight', 'p_gantt_date': 'The day on the job Gantt',
            'p_show_info': 'The info panel (DZV)', 'p_tile_view': 'Health tiles: all or needing attention',
            'p_lineage_view': 'Lineage graph or table (DZV)', 'p_panel': 'Lineage panel pills and sections (DZV)',
            'p_us_sort': 'Usage ranked table order'}
PANEL = ('p_panel_status', 'p_panel_type', 'p_panel_platform', 'p_panel_tags')


def _set_by():
    pages = collections.defaultdict(list)
    for p, acts in ACTION_LISTS.get('TAB_ACTIONS', {}).items():
        for _ws, _src, param, _cap in acts:
            if p not in pages[param]:
                pages[param].append(p)
    for param, p in CONTROLS.items():
        if p not in pages[param]:
            pages[param].append(p)
    for _ws, _f, param, _cap in ACTION_LISTS.get('SHELL_ACTIONS', []):
        pages[param] = ['every']
    return pages


def _pages(ps):
    if ps == ['every']:
        return 'Buttons on every page'
    if not ps:
        return '-'
    names = [SHORT[p] for p in ps]
    return ', '.join(names) if len(names) <= 3 else f'{len(names)} pages'


def _default(p):
    v = p['value']
    if p['name'] == 'p_selected_exposure':
        return 'Executive Revenue Dashboard'
    if p['name'] == 'p_selected_node':
        return 'stg_netsuite__journal_lines'
    if p['datatype'] == 'date':
        return '19 Oct 2026'
    if p['datatype'] == 'boolean':
        return 'False (Hide)'
    return v if v != '|' else '"|" (no tags)'


def param_rows():
    by = _set_by()
    rows = []
    for p in PARAMS:
        n = p['name']
        if n in PANEL[1:]:
            continue
        if n == PANEL[0]:
            rows.append(('p_panel_status / type / platform / tags', 'Int / String', '3, model, snowflake, "|"',
                         _pages(by.get(n, [])), USED_FOR['p_panel']))
            continue
        rows.append((n, p['datatype'].title(), _default(p), _pages(by.get(n, [])), USED_FOR[n]))
    return rows


PCOLS = [('PARAMETER', 228), ('TYPE', 70), ('DEFAULT', 186), ('SET FROM', 152), ('USED FOR', None)]


def _columns(rows, cols, pt=8):
    """One text zone per column, a line per row, so the columns line up without tab stops (no wrapping: asserted)."""
    zones = []
    for c, (head, w) in enumerate(cols):
        rs = [run(head, 7, INK3, SEMI), run(NL, 7, INK3), run(NL, 5, INK3)]
        for i, r in enumerate(rows):
            rs += [run(r[c], pt, INK1 if c == 0 else INK2, SEMI if c == 0 else 'Arial'), run(NL, pt, INK2)]
            if w:
                assert W(r[c], pt, c == 0) <= w - 10, f'Documentation column {head}: "{r[c]}" is wider than {w}'
        zones.append(text(rs, fixed=w))
    return zones


def action_lines():
    al = ACTION_LISTS
    lines, total = [], 0
    for p, name in [(t[0], t[1]) for t in al.get('TABS', [])]:
        a, n, d = al['TAB_ACTIONS'].get(p, []), al['TAB_NAV'].get(p, []), al['DEHIGHLIGHT'].get(p, [])
        u = al['TAB_URL'].get(p, []) + al.get('TAB_LINK', {}).get(p, [])
        total += len(a) + len(n) + len(u) + len(d) + len(al['SHELL_ACTIONS'])
        if not (a or n or u or d):
            continue
        params = []
        for x in a:
            k = 'p_panel_*' if x[2] in PANEL else x[2]
            if k not in params:
                params.append(k)
        bits = [f'{len(a)} parameter writes ({", ".join(params)})'] if a else []
        if n:
            bits.append(f'{len(n)} go to {" / ".join(sorted({x[1] for x in n}))}')
        if u:
            bits.append(' and '.join(f'1 {"email" if len(x) == 4 else "web"} link' for x in u))
        if d:
            bits.append(f'{len(d)} highlight reset' + ('s' if len(d) > 1 else ''))
        lines.append((name, '; '.join(bits)))
    return lines, total


def doc_content() -> Z:
    lab = lambda s: text([run(s, 7, INK3, SEMI)], fixed=22, **{'padding-top': '6'})
    body = lambda s, fixed=None: text([run(s, 8, INK2)], fixed=fixed)
    purpose = card('DOC Purpose Card', fixed=435, margins={'right': 7}, kids=[
        lab('DATA UPDATED ON'), sheet('GL Data Updated', 40),
        lab('PURPOSE'),
        body('Lineage Control Tower monitors every data product at Acme Retail Co. (fictional) and traces it back through dbt to the '
             'raw tables that feed it, one question per page.', 48),
        lab('DATA SOURCES'),
        body('One data source, "Lineage Control Tower": 14 CSV tables from data/marts, related on node_id (dim_nodes) and date (dim_date), plus the exposure tile shapes (GeoJSON). '
             'Every number is synthetic, generated in Python.'),
    ])
    params = card('DOC Parameters Card', margins={'left': 7}, kids=[
        card_header('Parameters', 'Global, so a choice on one page carries to the next', 44),
        Z('horz', friendly='DOC Parameter Columns', kids=_columns(param_rows(), PCOLS))])
    lines, total = action_lines()
    acts = [run(f'{total} actions in all. Every page also has the Period, Platform and ⓘ buttons (p_period, p_platform, p_show_info).',
                8, INK3), run(NL, 8, INK3)]
    for name, s in lines:
        acts += [run(NL, 5, INK2), run(name, 8, INK1, SEMI), run(NL, 8, INK1), run(s, 8, INK2), run(NL, 8, INK2)]
    actions = card('DOC Actions Card', margins={'right': 7}, kids=[
        card_header('Actions', 'By dashboard, as the builder writes them', 44), text(acts)])
    notes = [('SHEET PREFIXES', 'GL shared on every page; HO, RUN, FR, LIN, BR, QA, PF, US, GOV, AB and DOC for each page.'),
             ('DYNAMIC ZONE VISIBILITY', 'Every DZV calc reads parameters only; one that read the data kept its first value.'),
             ('CANVASES', 'Tables, chips and lists are drawn on map layers with fixed axes, their text placed from widths measured '
                          'at build time.'),
             ('KNOWN COMPROMISES', 'Values that change with period and platform are worked out by the build and switched by '
                                   'parameters. Run & failures has no MTTR window shading.'),
             ('REBUILD', 'python3 tableau/tools/build_workbook.py --tag <version>. Every build is kept in tableau/versions '
                         'with a row in CHANGELOG.md.')]
    nk = []
    for head, s in notes:
        nk += [run(head, 7, INK3, SEMI), run(NL, 7, INK3), run(s, 8, INK2), run(NL, 8, INK2), run(NL, 6, INK2)]
    note_card = card('DOC Notes Card', fixed=435, margins={'left': 7}, kids=[
        card_header('Build notes', 'For whoever opens this workbook next', 44), text(nk)])
    return Z('vert', friendly='DOC Content', style=CONTENT_PAD, saved_fixed=900, kids=[   # GB, Pre-Final
        Z('horz', friendly='DOC Top Row', fixed=300, kids=[purpose, params]),
        Z('horz', friendly='DOC Bottom Row', fixed=512, style={'margin-top': '14'}, kids=[actions, note_card])])   # GB, v47
