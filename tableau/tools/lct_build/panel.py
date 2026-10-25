"""Lineage side panel: the status pills and the "what is wrong" callouts, drawn from the node's own data (v49).

Until v48 these were dynamic zone visibility on the p_panel_* parameters, which only a click writes. A node picked
from a dropdown (Blast radius "Node to trace") left them on the last click's values: GB saw fct_experiment_results,
Healthy in the table, under a Critical pill with an empty pink box. Now:

- Pills: one canvas sheet. Each pill is a rounded shape on one scaffold model's 90 Node Daily rows (as the Blast radius
  pills); which pills a node has, their text, colours and widths are worked out by the build per node and keyed by
  [Panel Node Id], so they always match the node the panel shows.
- Callouts: the containers keep their place (shown or hidden by p_panel_status, so the sections move up for healthy
  nodes), but the tinted box and its text are a canvas drawn only when the node really is Critical (or Warning) and
  has a reason. A stale parameter can leave white space; it can no longer show a wrong pill or an empty box.
"""

from __future__ import annotations

from . import shapes as SH
from .core import (AI_INK, B_DIM, CRIT_INK, CRIT_TINT, GOOD_INK, I_DIM, INK2, LAT, LINE, LON, NONE_TINT, S_DIM, SEMI, SP_MEA,
                   WARN_INK, WARN_TINT, CALCS, Pane, R, Sheet, color_map, label_pane, run)
from .lineage import NODES, PANEL_INNER_W, PLAT_COL, _event_label, _grid, _q, _wrap
from .usage import _calc, _case, _rounded

W7 = lambda s, b=False: SH.text_width(s, 7, b)
W8 = lambda s, b=False: SH.text_width(s, 8, b)
BY_ID = {r['node_id']: r for r in NODES}
MODELS = sorted(k for k, r in BY_ID.items() if r['resource_type'] == 'model')
PILL_CARRIERS = MODELS[-5:]                       # one scaffold model per pill slot
CALLOUT_CARRIER = MODELS[-6]
IDX = '[Node Path Index]'

PANE_W = PANEL_INNER_W - SH.MAP_SLACK              # 294
PILL_H, PILL_GAP = 20, 4
PILL_PANE = (PANE_W, PILL_H + 2)
CALLOUT_PANE = (PANE_W, 100)

# pill kinds: (ink, fill, edge, bold)
STYLE = {'Crit': (CRIT_INK, CRIT_TINT, '#f2cdca', True), 'Warn': (WARN_INK, WARN_TINT, '#f3e0be', True),
         'Good': (GOOD_INK, '#eaf6ef', '#cfe8da', True), 'None': (INK2, NONE_TINT, LINE, True),
         **{f'Plat {p}': (c, '#f5f5f3', LINE, True) for p, c in PLAT_COL.items()},
         'Moved': (INK2, '#f5f5f3', LINE, False), 'AI': (AI_INK, '#eef0fb', '#d9dcf4', True),
         'Unreg': (WARN_INK, WARN_TINT, '#f3ddb4', True)}


def _pills(r):
    """The pills a node shows, in the panel's order (as the v48 DZV row): status (trust for exposures), platform,
    moved, AI-built, not registered."""
    code = int(r['current_status_code'] or 0)
    if r['resource_type'] == 'exposure':
        out = [('✕  Do not use', 'Crit') if code == 3 else ('▲  Use with caution', 'Warn') if code == 2 else ('✓  Trusted', 'Good')]
    else:
        out = [{3: ('✕  Critical', 'Crit'), 2: ('▲  Warning', 'Warn'), 1: ('✓  Healthy', 'Good')}.get(code, ('–  No data', 'None'))]
    plat = r['platform_now'].title()
    if plat in PLAT_COL:
        out.append((f'■  {plat}', f'Plat {plat}'))
    if r['migrated_from_platform']:
        d = r['migration_date'][:10]
        import datetime as dt
        day = dt.date.fromisoformat(d)
        out.append((f'moved from {r["migrated_from_platform"].title()} on {day.day} {day.strftime("%b")}', 'Moved'))
    if r['build_method'] == 'ai_assisted':
        out.append(('AI-built', 'AI'))
    if r['is_declared'] != 'True':
        out.append(('Not registered', 'Unreg'))
    return out


def _pill_layout():
    """{node: [(text, kind, x0, w)]}, laid left to right with the v48 gaps."""
    lay = {}
    for k, r in sorted(BY_ID.items()):
        x, row = 0, []
        for t, kind in _pills(r):
            w = round(W7(t, STYLE[kind][3]) + 10)
            row.append((t, kind, x, w))
            x += w + PILL_GAP
        assert x - PILL_GAP <= PANE_W, f'panel pills for {k}: {x - PILL_GAP:.0f} of {PANE_W} px'
        assert len(row) <= len(PILL_CARRIERS), k
        lay[k] = row
    return lay


PILLS = _pill_layout()


def _callouts():
    """{status: {node: [(style, line)]}} for nodes that are Warning or Critical and have a reason (v48's text)."""
    maxw = PANE_W - 2 * 12
    out = {3: {}, 2: {}}
    for k, r in sorted(BY_ID.items()):
        code = int(r['current_status_code'] or 0)
        if code not in out:
            continue
        if r['resource_type'] == 'exposure':
            reason, err = r['culprit_nodes'] or r['status_reason'], ''
        else:
            reason = r['status_reason'] + (f' at {_event_label(r["last_event_at"])}' if r['last_run_status'] == 'error' and r['last_event_at'] else '')
            err = r['last_error_message']
        if not reason:
            continue                               # no reason, no box (GB, v48)
        lines = [('Reason', s) for s in _wrap(reason, maxw, 8)] + [('Error', s) for s in (_wrap(err, maxw, 7) if err else [])]
        out[code][k] = lines
    return out


CALLOUTS = _callouts()


def calcs():
    f = {}
    slot = '[LIN Pill Slot]'
    f['LIN Pill Slot'] = _calc('LIN Pill Slot', 'Which pill a scaffold model\'s Node Daily rows draw (0 = the first pill).',
                               _case('[node_id (dim_nodes.csv)]', {k: str(i) for i, k in enumerate(PILL_CARRIERS)}, quote=False))
    f['Is LIN Pill Carrier'] = _calc('Is LIN Pill Carrier', 'The five scaffold models of the panel pills. Put on Filters (True).', f'NOT ISNULL({slot})')
    key = f'[Panel Node Id] + "|" + STR({slot})'
    items = {f'{k}|{i}': p for k, row in PILLS.items() for i, p in enumerate(row)}
    f['LIN Pill Key'] = _calc('LIN Pill Key', 'Pill fill: its kind, from the panel node\'s own data (written by the build per node).',
                              _case(key, {k: p[1] for k, p in items.items()}))
    f['LIN Pill Edge Key'] = _calc('LIN Pill Edge Key', 'Pill outline colour (same kinds, own palette).', '[LIN Pill Key]')
    x0 = _case(key, {k: str(p[2]) for k, p in items.items()}, quote=False)
    w = _case(key, {k: str(p[3]) for k, p in items.items()}, quote=False)
    f['LIN Pill Edge Point'] = _calc('LIN Pill Edge Point', 'Pill outline, fully rounded, rows 0 to 87.', _rounded(IDX, x0, w, 1, 1 + PILL_H, PILL_H / 2, PILL_PANE))
    f['LIN Pill Fill Point'] = _calc('LIN Pill Fill Point', 'Pill fill, 1 px inside.', _rounded(IDX, f'({x0}) + 1', f'({w}) - 2', 2, PILL_H, PILL_H / 2 - 1, PILL_PANE))
    groups = {'Crit': ['Crit'], 'Warn': ['Warn', 'Unreg'], 'Good': ['Good'], 'Grey': ['None'], 'Moved': ['Moved'], 'AI': ['AI'],
              **{f'Plat {p}': [f'Plat {p}'] for p in PLAT_COL}}
    for g, kinds in groups.items():
        f[f'LIN Pill Text {g}'] = _calc(f'LIN Pill Text {g}', f'Pill text in the {g.lower()} ink (row 0 of its pill).',
                                        f'IF {IDX} = 0 THEN ' + _case(key, {k: p[0] for k, p in items.items() if p[1] in kinds}) + ' END')
    at = lambda x, y, pane: f'MAKEPOINT({(pane[1] / 2 - y) / 100:.4f}, {(x - pane[0] / 2) / 100:.4f})'
    f['LIN Pill Text Point'] = _calc('LIN Pill Text Point', 'Middle of the pill.',
                                     f'IF {IDX} = 0 THEN ' + _case(key, {k: at(p[2] + p[3] / 2, 1 + PILL_H / 2, PILL_PANE) for k, p in items.items()}, quote=False) + ' END')
    # callouts
    f['Is LIN Callout Carrier'] = _calc('Is LIN Callout Carrier', 'The scaffold model whose rows draw the panel callout. Put on Filters (True).',
                                        f'[node_id (dim_nodes.csv)] = {_q(CALLOUT_CARRIER)}')
    for code, kind in ((3, 'Critical'), (2, 'Warning')):
        nodes = CALLOUTS[code]
        f[f'LIN Callout {kind} Point'] = _calc(f'LIN Callout {kind} Point', f'The {kind.lower()} box: only for a node that is {kind} now and has a reason.',
                                               f'IF ' + _case('[Panel Node Id]', {k: 'TRUE' for k in nodes}, 'FALSE', False) + ' THEN '
                                               + _rounded(IDX, 1, PANE_W - 2, 1, CALLOUT_PANE[1] - 1, 7, CALLOUT_PANE) + ' END')
        f[f'LIN Callout {kind} Edge Point'] = _calc(f'LIN Callout {kind} Edge Point', 'Its 1 px outline (drawn under the box).',
                                                    f'IF ' + _case('[Panel Node Id]', {k: 'TRUE' for k in nodes}, 'FALSE', False) + ' THEN '
                                                    + _rounded(IDX, 0, PANE_W, 0, CALLOUT_PANE[1], 8, CALLOUT_PANE) + ' END')
        texts, pts = {'Reason': {}, 'Error': {}}, {'Reason': {}, 'Error': {}}
        for k, lines in nodes.items():
            y = 12
            for i, (st, s) in enumerate(lines):
                if st == 'Error' and i and lines[i - 1][0] == 'Reason':
                    y += 4
                pt, step = (8, 13) if st == 'Reason' else (7, 12)
                texts[st][f'{k}|{i}'] = s
                pts[st][f'{k}|{i}'] = at(12 + SH.text_width(s, pt) / 2, y + step / 2 - 2, CALLOUT_PANE)
                y += step
        lk = f'[Panel Node Id] + "|" + STR({IDX})'
        for st in ('Reason', 'Error'):
            f[f'LIN Callout {kind} {st} Text'] = _calc(f'LIN Callout {kind} {st} Text', f'{st} lines, one row each (wrapped by the build).',
                                                      _case(lk, texts[st]))
            f[f'LIN Callout {kind} {st} Point'] = _calc(f'LIN Callout {kind} {st} Point', 'Left in the box (centred at half its measured width).',
                                                       _case(lk, pts[st], quote=False))
    t = {n: (SP_MEA if n.endswith('Point') else B_DIM if n.startswith('Is ') else I_DIM if n == 'LIN Pill Slot' else S_DIM) for n in f}
    return f, t


_f, _t = calcs()
CALCS.add(formulas=_f, types=_t)


def sheets() -> list[Sheet]:
    path, idx = R('Node Path Index', kind='ok'), R('Node Path Index')
    color_map(R('LIN Pill Key'), {f'"{k}"': v[1] for k, v in STYLE.items()})
    color_map(R('LIN Pill Edge Key'), {f'"{k}"': v[2] for k, v in STYLE.items()})
    slot = R('LIN Pill Slot')
    ink = {'Crit': (CRIT_INK, True), 'Warn': (WARN_INK, True), 'Good': (GOOD_INK, True), 'Grey': (INK2, True), 'Moved': (INK2, False),
           'AI': (AI_INK, True), **{f'Plat {p}': (c, True) for p, c in PLAT_COL.items()}}
    runs = [run(R(f'LIN Pill Text {g}', 'attr'), 7, c, SEMI if b else 'Arial') for g, (c, b) in ink.items()]
    pills = _grid(Sheet('LIN Panel Pills', rows=[LAT], cols=[LON], filters=[R('Is LIN Pill Carrier')], layers=True, no_basemap=True,
                        zoom=None, tooltip=False, panes=[
                            Pane('Automatic', pane_size=PILL_PANE),
                            Pane('Polygon', title='Edge', inert=True, color=R('LIN Pill Edge Key'), path=path, label_show=False,
                                 lod=[R('LIN Pill Edge Point', 'clct'), slot], pane_size=PILL_PANE),
                            Pane('Polygon', title='Fill', inert=True, color=R('LIN Pill Key'), path=path, label_show=False,
                                 lod=[R('LIN Pill Fill Point', 'clct'), slot], pane_size=PILL_PANE),
                            label_pane(title='Text', inert=True, text=[r['_ref'] for r in runs], label=runs, align='center', valign='center',
                                       lod=[R('LIN Pill Text Point', 'clct'), slot, idx], pane_size=PILL_PANE)]), PILL_PANE)
    out = [pills]
    for kind, inkc, fill, edge in (('Critical', CRIT_INK, CRIT_TINT, '#f2cdca'), ('Warning', WARN_INK, WARN_TINT, '#f3e0be')):
        out.append(_grid(Sheet(f'LIN Panel Callout {kind}', rows=[LAT], cols=[LON], filters=[R('Is LIN Callout Carrier')], layers=True,
                               no_basemap=True, zoom=None, tooltip=False, panes=[
                                   Pane('Automatic', pane_size=CALLOUT_PANE),
                                   Pane('Polygon', title='Edge', inert=True, mark_color=edge, path=path, label_show=False,
                                        lod=[R(f'LIN Callout {kind} Edge Point', 'clct')], pane_size=CALLOUT_PANE),
                                   Pane('Polygon', title='Box', inert=True, mark_color=fill, path=path, label_show=False,
                                        lod=[R(f'LIN Callout {kind} Point', 'clct')], pane_size=CALLOUT_PANE),
                                   label_pane(title='Reason', inert=True, text=[R(f'LIN Callout {kind} Reason Text', 'attr')],
                                              label=[run(R(f'LIN Callout {kind} Reason Text', 'attr'), 8, inkc)], align='center',
                                              lod=[R(f'LIN Callout {kind} Reason Point', 'clct'), idx], pane_size=CALLOUT_PANE),
                                   label_pane(title='Error', inert=True, text=[R(f'LIN Callout {kind} Error Text', 'attr')],
                                              label=[run(R(f'LIN Callout {kind} Error Text', 'attr'), 7, inkc)], align='center',
                                              lod=[R(f'LIN Callout {kind} Error Point', 'clct'), idx], pane_size=CALLOUT_PANE)]), CALLOUT_PANE))
    return out
