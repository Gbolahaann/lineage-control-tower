"""Tab 2, Run & failures (RUN): calc pack section 6, build plan 3.4.

Native Tableau charts where they already look like the prototype (daily bars, job Gantt, why-failed bars, MTTR
line) and a pixel canvas only for the Recent errors table (GB, 22 Oct: "Mixed").

The 90-day charts share one x axis: Days Back Mid (days before the as-of date + 0.5), fixed 0 to 90 and reversed,
so today is on the right and day d fills [d, d + 1]. The selected window is then simply "below p_period", which a
reference line on p_period shades (fill-below), and the selected Gantt day is a line on p_gantt_back. The incident
strip above the bars and the date strip under them use the same axis, and the same fixed y axis with its labels
made clear, so all three line up to the pixel.
"""

from __future__ import annotations

import csv
from datetime import datetime

from . import shapes as SH
from .core import (PANEL_WRITES, ACCENT, ACCENT_TINT, B_DIM, CALCS, CRIT, CRIT_INK, I_DIM, I_MEA, INK1, INK2, INK3,
                   INK4, LAT, LINE, LON, NAVY, NL, R_MEA, S_DIM, S_MEA, SEMI, SP_MEA, WARN, Cross, Nest, Pane, R, Sheet, Z, blank,
                   card, card_header, color_map, label_pane, run, sheet, text)
from .lineage import _fit, _grid, _q
from .shell import CONTENT_PAD

P = 'RUN'
DATE = 'date (dim_date.csv)'
ROOT = SH.ROOT
ERRORS = list(csv.DictReader(open(ROOT / 'data' / 'marts' / 'mart_run_errors.csv', encoding='utf-8')))
NODE_NAME = {r['node_id']: r['display_name'] for r in csv.DictReader(open(ROOT / 'data' / 'marts' / 'dim_nodes.csv', encoding='utf-8'))}

# ---------------------------------------------------------------- geometry (content 1312 x 836)
SIDE_W = 380                                   # Why runs failed and MTTR cards; 7 px margin-left outside
MAIN_W = 1312 - SIDE_W - 7 - 7                 # 918: Gantt and errors cards, 7 px margin-right outside
DAILY_H, MID_H, BOTTOM_H = 220, 352, 236       # card heights; the two lower rows sit 14 px below the one above
TABLE_W = MAIN_W - 2 * 16 - 2 - 18 - SH.SLACK  # 862: errors canvas, room for its own scroll bar
TABLE_ROW = (TABLE_W, 27)                      # one pane per error, prototype row height
TCOL = {'when': 8, 'model': 104, 'category': 296, 'message': 416}
MSG_W = TABLE_W - TCOL['message'] - 8          # 438 px of message, cut with "…" by the build

DAYS = 90
BACK_AXIS = (0, DAYS, {'reverse': 'true'})    # Days Back Mid: today on the right
BAR_Y = (0, 52, {'major-origin': '0', 'major-spacing': '25'})     # busiest day: 47 failed + skipped
MTTR_Y = (0, 25, {'major-origin': '0', 'major-spacing': '10'})    # rolling MTTR peaks at 24 h (Databricks)
CLEAR = '#00000000'
SKIP_GREY, SUCCESS_BLUE, CANCEL_GREY = '#c3c9cf', '#9db9d6', '#c3c9cf'


# ================================================================ calcs

def _key_case(name, why, values, default='""', numeric=False):
    """CASE on the error's own key (job run | node), written by the build from Run Errors (179 rows)."""
    body = '\n'.join(f'WHEN {_q(k)} THEN {v if numeric else _q(v)}' for k, v in values.items())
    return f'// {name}\n// {why}\nCASE [Error Key]\n{body}\nELSE {default}\nEND'


def _when(ts):
    d = datetime.fromisoformat(ts)
    return f'{d.day} {d.strftime("%b")}, {d:%H:%M}'


CAT_NAME = {'database': 'Database error', 'compilation': 'Compilation error', 'permission': 'Permission denied',
            'timeout': 'Timeout', 'schema_change': 'Schema change'}


def _table_calcs():
    """Every cell's text and width, measured at build time (Liberation Sans = Arial metrics), so each label can be
    centred at half its width from its column's left edge: map-pane label alignment is not reliable."""
    f = {}
    keys = {r['job_run_id'] + '|' + r['node_id']: r for r in ERRORS}
    cols = {
        'When': {k: _when(r['run_started_at']) for k, r in keys.items()},
        'Model': {k: _fit(NODE_NAME.get(r['node_id'], r['node_id']), TCOL['category'] - TCOL['model'] - 12, 8) for k, r in keys.items()},
        'Category': {k: CAT_NAME.get(r['error_category'], r['error_category']) for k, r in keys.items()},
        'Message': {k: _fit(r['error_message'], MSG_W, 8) for k, r in keys.items()},
    }
    for c, vals in cols.items():
        f[f'Error {c} Text'] = _key_case(f'Error {c} Text', f'{c} cell of the Recent errors table, as the build wrote it.', vals)
        f[f'Error {c} Width'] = _key_case(f'Error {c} Width', f'Width of the {c} cell text in px (8 pt Arial), for centring.',
                                          {k: f'{SH.text_width(v, 8):.1f}' for k, v in vals.items()}, '0', numeric=True)
        x = TCOL[c.lower()]
        f[f'Error {c} Point'] = (f'// Error {c} Point\n// {c} cell: the label is centred, so the point sits half the text width '
                                 f'right of the column edge ({x} px).\n'
                                 f'MAKEPOINT(0, ({x} + [Error {c} Width] / 2 - {TABLE_W / 2:g}) / 100)')
    heads = ['WHEN', 'MODEL', 'CATEGORY', 'MESSAGE']
    xs = [TCOL[k] for k in ('when', 'model', 'category', 'message')]
    f['Error Heading'] = ('// Error Heading\n// Column titles of the Recent errors table, one per scaffold day (day_index 0 to 3).\n'
                          'CASE [day_index] ' + ' '.join(f'WHEN {i} THEN {_q(h)}' for i, h in enumerate(heads)) + ' END')
    mid = ' '.join(f'WHEN {i} THEN {x + SH.text_width(h, 7, True) / 2:.1f}' for i, (h, x) in enumerate(zip(heads, xs)))
    f['Error Heading Point'] = ('// Error Heading Point\n// Column title, centred at half its width from the column edge.\n'
                                f'MAKEPOINT(0, ((CASE [day_index] {mid} END) - {TABLE_W / 2:g}) / 100)')
    return f


def calcs():
    hours = lambda m: f'{m} / 60'
    f = {
        # shared 90-day axis
        'Days Back Mid': ('// Days Back Mid\n// x of every 90-day chart on this tab: days before the as-of date + 0.5, on an axis fixed\n'
                          '// 0 to 90 and reversed, so day d fills [d, d + 1] and the window is everything below p_period.\n'
                          '[days_before_as_of] + 0.5'),
        'Is First Date Row': '// Is First Date Row\n// One-row scaffold (the first day) for the Gantt day buttons and label. Put on Filters (True).\n[day_index] = 0',
        'Is Error Heading Row': '// Is Error Heading Row\n// The four scaffold days that carry the error table\'s column titles. Put on Filters (True).\n[day_index] < 4',
        # daily bars (Node Daily)
        'Daily Failed Runs': '// Daily Failed Runs\n// Red bars: failed model runs that day.\nSUM([runs_failed])',
        'Daily Skipped Runs': '// Daily Skipped Runs\n// Skipped because an upstream model failed (tooltip).\nSUM([runs_skipped])',
        'Daily Failed And Skipped': ('// Daily Failed And Skipped\n// Grey bars behind the red ones: failed + skipped, so the grey part above the red\n'
                                     '// is the skipped runs (an overlay, exact even on the 19 node-days that had both).\nSUM([runs_failed]) + SUM([runs_skipped])'),
        # incident strip and date strip
        'Incident Tick': '// Incident Tick\n// Grey tick under an incident label, on days an incident started.\nIF COUNT([incident_id]) > 0 THEN 22 END',
        'Incident Label Anchor': '// Incident Label Anchor\n// Point the "INC 4" label sits above (label vertical alignment top).\nIF COUNT([incident_id]) > 0 THEN 24 END',
        'Axis Date Label': ('// Axis Date Label\n// "22 Jul", "1 Aug" ... under the 90-day charts: the first day and every 1st of the month.\n'
                            'IF [day_index] = 0 OR DAY([date (dim_date.csv)]) = 1\n'
                            'THEN STR(DAY([date (dim_date.csv)])) + " " + LEFT(DATENAME(\'month\', [date (dim_date.csv)]), 3)\nEND'),
        'Axis Label Anchor': '// Axis Label Anchor\n// Point the date label is centred on (axis 0 to 52, the bars\' scale).\nIF NOT ISNULL(MIN([Axis Date Label])) THEN 26 END',
        'Axis Label Anchor MTTR': '// Axis Label Anchor MTTR\n// Same, on the MTTR chart\'s 0 to 25 scale.\nIF NOT ISNULL(MIN([Axis Date Label])) THEN 12.5 END',
        # Gantt (Job Runs): the selected day is in the position, not a filter, so all 9 jobs keep their rows
        'Gantt Start Hour': ('// Gantt Start Hour\n// Bar start in hours (axis 00:00 to 24:00) for runs on the selected day; other days have no mark.\n'
                             f'IF [run_date] = [p_gantt_date] THEN {hours("[start_minute_of_day]")} END'),
        'Gantt Duration Hours': '// Gantt Duration Hours\n// Bar length in hours, at least 3 minutes so very short runs stay visible.\nMAX([duration_min], 3) / 60',
        'Tests Failed Marker Hour': ('// Tests Failed Marker Hour\n// Amber dot just after a run whose tests failed. NULL (no mark) otherwise.\n'
                                     'IF [run_date] = [p_gantt_date] AND [tests_failed] > 0\n'
                                     'THEN ([start_minute_of_day] + MAX([duration_min], 3) + 4) / 60 END'),
        'Gantt Started Text': ('// Gantt Started Text\n// "05:16" in the tooltip.\n'
                               'RIGHT("0" + STR(INT([start_minute_of_day] / 60)), 2) + ":" + RIGHT("0" + STR([start_minute_of_day] % 60), 2)'),
        'Gantt Duration Text': ('// Gantt Duration Text\n// "5.8 min" or "1 h 25 min" in the tooltip.\n'
                                'IF [duration_min] < 60 THEN STR(ROUND([duration_min], 1)) + " min"\n'
                                'ELSE STR(INT([duration_min] / 60)) + " h " + STR(INT([duration_min]) % 60) + " min" END'),
        'Job Platform Name': ('// Job Platform Name\n// Platform the job ran on, as written in the legend.\n'
                              'CASE [platform (mart_job_runs.csv)] WHEN "snowflake" THEN "Snowflake" WHEN "databricks" THEN "Databricks"\n'
                              'WHEN "redshift" THEN "Redshift" ELSE [platform (mart_job_runs.csv)] END'),
        'Gantt Prev Back': ('// Gantt Prev Back\n// What the ‹ button writes into p_gantt_back (one day earlier = one more day back).\n'
                            'IF [p_gantt_back] < 89 THEN [p_gantt_back] + 1 ELSE [p_gantt_back] END'),
        'Gantt Next Back': ('// Gantt Next Back\n// What the › button writes into p_gantt_back. Stops at the last day.\n'
                            'IF [p_gantt_back] > 1 THEN [p_gantt_back] - 1 ELSE [p_gantt_back] END'),
        'Gantt Prev Glyph': '// Gantt Prev Glyph\n// ‹ on the previous-day button.\nMIN("‹")',
        'Gantt Next Glyph': '// Gantt Next Glyph\n// › on the next-day button.\nMIN("›")',
        # why runs failed and top models (Run Errors)
        'Why Track': ('// Why Track\n// Light grey track behind each red bar: the longest bar in the card.\n'
                      '// Table calc along Error Category Label.\nWINDOW_MAX([Failed Model Runs])'),
        'Top Model Track': ('// Top Model Track\n// Track behind the top-models bars. Table calc along display_name.\nWINDOW_MAX([Failed Model Runs])'),
        'Is Top Failing Model': ('// Is Top Failing Model\n// The 7 models that failed most. Table calc filter (True), along display_name.\n'
                                 'RANK_UNIQUE([Failed Model Runs]) <= 7'),
        # errors table
        'Error Key': '// Error Key\n// One row per failed model run: job run and node.\n[job_run_id] + "|" + [node_id (mart_run_errors.csv)]',
        'Error Order': ('// Error Order\n// Newest first: minutes before the end of 2026, so the natural ascending order is newest first.\n'
                        'DATEDIFF(\'minute\', [run_started_at], #2026-12-31#)'),
        # MTTR (Recovery Episodes), along Days Back Mid: earlier days are further back, so the window is 0 to +6
        'MTTR Rolling 7 Day Line': ('// MTTR Rolling 7 Day Line\n// Mean recovery time of episodes that started in the 7 days up to each day (episode-weighted).\n'
                                    '// Table calc along Days Back Mid (ascending = back in time, so the 6 days before are +1 to +6).\n'
                                    'WINDOW_SUM(SUM(IF NOT [is_open] THEN [hours_to_recover] END), 0, 6)\n/\n'
                                    'WINDOW_SUM(COUNT(IF NOT [is_open] THEN [hours_to_recover] END), 0, 6)'),
        'MTTR Rolling 7 Day Area': ('// MTTR Rolling 7 Day Area\n// The same value for the light area under the line (a second axis needs its own field).\n'
                                    'WINDOW_SUM(SUM(IF NOT [is_open] THEN [hours_to_recover] END), 0, 6)\n/\n'
                                    'WINDOW_SUM(COUNT(IF NOT [is_open] THEN [hours_to_recover] END), 0, 6)'),
        **_table_calcs(),
    }
    return f


R_DIM_Q = ('real', 'dimension', 'quantitative')   # continuous dimension (an axis, not a header)
TYPES = {
    'Days Back Mid': R_DIM_Q, 'Is First Date Row': B_DIM, 'Is Error Heading Row': B_DIM,
    'Daily Failed Runs': R_MEA, 'Daily Skipped Runs': R_MEA, 'Daily Failed And Skipped': R_MEA,
    'Incident Tick': R_MEA, 'Incident Label Anchor': R_MEA, 'Axis Date Label': S_DIM, 'Axis Label Anchor': R_MEA,
    'Axis Label Anchor MTTR': R_MEA,
    'Gantt Start Hour': R_MEA, 'Gantt Duration Hours': R_MEA, 'Tests Failed Marker Hour': R_MEA,
    'Gantt Started Text': S_DIM, 'Gantt Duration Text': S_DIM, 'Job Platform Name': S_DIM,
    'Gantt Prev Back': R_DIM_Q, 'Gantt Next Back': R_DIM_Q, 'Gantt Prev Glyph': S_MEA, 'Gantt Next Glyph': S_MEA,
    'Why Track': R_MEA, 'Top Model Track': R_MEA, 'Is Top Failing Model': ('boolean', 'measure', 'nominal'),
    'Error Key': S_DIM, 'Error Order': I_DIM,
    'MTTR Rolling 7 Day Line': R_MEA, 'MTTR Rolling 7 Day Area': R_MEA,
    'Error Heading': S_DIM, 'Error Heading Point': SP_MEA,
    # calc pack section 6 (and 2) calcs this tab reads
    'Is Platform Match Job': B_DIM, 'Is Platform Match Error': B_DIM, 'Job Run Outcome': S_DIM,
    'Job Schedule Label': S_DIM, 'Gantt Day Label': S_DIM, 'Gantt Prev Date': ('date', 'dimension', 'ordinal'),
    'Gantt Next Date': ('date', 'dimension', 'ordinal'), 'As Of Date': ('date', 'dimension', 'ordinal'),
    'Incident Marker Label': S_DIM, 'Failed Model Runs': I_MEA, 'Failed Runs Label': S_MEA,
    'Error Category Label': S_DIM, 'Error Time Label': S_DIM,
}
for c in ('When', 'Model', 'Category', 'Message'):
    TYPES[f'Error {c} Text'] = S_DIM
    TYPES[f'Error {c} Width'] = R_MEA
    TYPES[f'Error {c} Point'] = SP_MEA

CALCS.add(formulas=calcs(), types=TYPES, table_calc={
    'Why Track': 'Error Category Label', 'Top Model Track': 'display_name', 'Is Top Failing Model': 'display_name',
    'MTTR Rolling 7 Day Line': 'Days Back Mid', 'MTTR Rolling 7 Day Area': 'Days Back Mid'})


# ================================================================ sheets

def _axis_style(y, show_labels=True, fmt=None):
    """A visible y axis (8 pt grey, no title, no ruler or ticks); clear labels on the strips, so their axis takes the
    same width as the chart's and the plots line up."""
    lines = ["            <format attr='line-visibility' value='off' />",
             "            <format attr='font-size' value='8' />",
             f"            <format attr='color' value='{INK3 if show_labels else CLEAR}' />",
             f"            <format attr='title' class='0' field='{y.ref}' scope='rows' value='' />"]
    if fmt:
        lines.append(f"            <format attr='text-format' field='{y.ref}' value='{fmt}' />")
    return lines


def _window_lines(axis, selected=True):
    """The selected window (fill below the p_period line, the line itself clear) and the selected Gantt day."""
    rl = [dict(id='refline0', axis=axis, param='p_period', z=1)]
    style = ["            <format attr='stroke-size' id='refline0' value='0' />",
             f"            <format attr='stroke-color' id='refline0' value='{CLEAR}' />",
             f"            <format attr='fill-above' id='refline0' value='{CLEAR}' />",
             f"            <format attr='fill-below' id='refline0' value='{ACCENT_TINT}' />"]
    if selected:
        rl.append(dict(id='refline1', axis=axis, param='p_gantt_back', z=2))
        style += ["            <format attr='stroke-size' id='refline1' value='1' />",
                  f"            <format attr='stroke-color' id='refline1' value='{NAVY}' />",
                  f"            <format attr='fill-above' id='refline1' value='{CLEAR}' />",
                  f"            <format attr='fill-below' id='refline1' value='{CLEAR}' />"]
    return rl, style


def daily_sheet() -> Sheet:
    x, date = R('Days Back Mid'), R(DATE)
    total, failed = R('Daily Failed And Skipped'), R('Daily Failed Runs')
    rl, rstyle = _window_lines(x)
    tip = [run(R(DATE), 9, INK1, SEMI), run(NL, 7, INK3),
           run('FAILED   ', 7, INK3, SEMI), run(failed, 9, CRIT_INK, SEMI), run(NL, 7, INK3),
           run('SKIPPED   ', 7, INK3, SEMI), run(R('Daily Skipped Runs'), 9, NAVY, SEMI), run(NL, 7, INK3),
           run('CLICK TO LOAD ITS RUN TIMELINE', 7, INK3, SEMI)]
    return Sheet('RUN Daily Failures Bar', cols=[x], rows=[(total, failed)], filters=[R('Is Platform Match Day')],
                 hide=[x, failed], sync=[failed], fixed={x: BACK_AXIS, total: BAR_Y},
                 formats={R(DATE): '*d mmm yyyy', total: 'n#,##0;-#,##0'},
                 extra={'axis': _axis_style(total), 'refline': rstyle},
                 panes=[Pane('Bar', size=1.2, label_show=False),
                        Pane('Bar', axis=total, size=1.2, label_show=False, mark_color=SKIP_GREY, lod=[date],
                             tooltip=tip, reflines=rl),
                        Pane('Bar', axis=failed, size=1.2, label_show=False, mark_color=CRIT, lod=[date], tooltip=tip)])


def incident_sheet() -> Sheet:
    x, tick, anchor = R('Days Back Mid'), R('Incident Tick'), R('Incident Label Anchor')
    label = R('Incident Marker Label', 'attr')
    tip = [run(label, 9, INK1, SEMI), run(NL, 7, INK3), run(R('title', 'attr'), 9, INK1)]
    return Sheet('RUN Incident Markers', cols=[x], rows=[(tick, anchor)], hide=[x, anchor], sync=[anchor],
                 fixed={x: BACK_AXIS, tick: BAR_Y}, extra={'axis': _axis_style(tick, False)},
                 panes=[Pane('Bar', label_show=False),
                        Pane('Bar', axis=tick, size=0.02, mark_color=INK4, label_show=False, tooltip=tip),
                        label_pane(axis=anchor, text=[label], label=[run(label, 7, INK2, SEMI)], align='center',
                                   valign='top', tooltip=tip)])


def axis_strip(name, y_fixed, anchor_name) -> Sheet:
    """Date labels under a 90-day chart, on the same reversed axis, with the chart's y axis in clear text."""
    x, anchor = R('Days Back Mid'), R(anchor_name)
    lab = R('Axis Date Label')
    return Sheet(name, cols=[x], rows=[anchor], hide=[x], fixed={x: BACK_AXIS, anchor: y_fixed}, tooltip=False,
                 extra={'axis': _axis_style(anchor, False)},
                 panes=label_pane(text=[lab], label=[run(lab, 8, INK3)], align='center'))



def gantt_sheet() -> Sheet:
    job, sched = R('job_name'), R('Job Schedule Label')
    start, mark = R('Gantt Start Hour', 'min'), R('Tests Failed Marker Hour', 'min')
    outcome, rid = R('Job Run Outcome'), R('job_run_id (mart_job_runs.csv)')
    color_map(outcome, {'Succeeded': SUCCESS_BLUE, 'Failed': CRIT, 'Cancelled': CANCEL_GREY})
    a = lambda n: R(n, 'attr')
    tip = [run(a('job_name'), 9, INK1, SEMI), run(' · ', 9, INK3), run(a('Job Platform Name'), 9, INK3), run(NL, 7, INK3),
           run('STARTED   ', 7, INK3, SEMI), run(a('Gantt Started Text'), 9, NAVY, SEMI), run(NL, 7, INK3),
           run('DURATION   ', 7, INK3, SEMI), run(a('Gantt Duration Text'), 9, NAVY, SEMI), run(NL, 7, INK3),
           run('OUTCOME   ', 7, INK3, SEMI), run(a('Job Run Outcome'), 9, NAVY, SEMI), run(NL, 7, INK3),
           run('MODELS RUN / FAILED / SKIPPED   ', 7, INK3, SEMI), run(R('models_run', 'sum'), 9, NAVY, SEMI), run(' / ', 9, INK3),
           run(R('models_failed', 'sum'), 9, CRIT_INK, SEMI), run(' / ', 9, INK3), run(R('models_skipped', 'sum'), 9, NAVY, SEMI),
           run(NL, 7, INK3), run('TESTS FAILED   ', 7, INK3, SEMI), run(R('tests_failed', 'sum'), 9, NAVY, SEMI)]
    hours = (0, 24, {'major-origin': '0', 'major-spacing': '3'})
    clock = 'n00":00";-00":00"'
    axis = ["            <format attr='line-visibility' value='off' />", "            <format attr='font-size' value='8' />",
            f"            <format attr='color' value='{INK3}' />",
            f"            <format attr='title' class='0' field='{start.ref}' scope='cols' value='' />",
            f"            <format attr='text-format' field='{start.ref}' value='{clock}' />"]
    label = [f"            <format attr='font-size' field='{job.ref}' value='8' />",
             f"            <format attr='color' field='{job.ref}' value='{INK1}' />",
             f"            <format attr='font-size' field='{sched.ref}' value='7' />",
             f"            <format attr='color' field='{sched.ref}' value='{INK3}' />",
             f"            <format attr='text-align' field='{sched.ref}' value='right' />"]
    return Sheet('RUN Job Gantt', rows=[job, sched], cols=[(start, mark)], filters=[R('Is Platform Match Job')],
                 hide=[mark], sync=[mark], fixed={start: hours}, header_width={job: 150, sched: 52},
                 formats={start: clock}, bands='#fbfbfa', extra={'axis': axis, 'label': label},
                 panes=[Pane('GanttBar', label_show=False),
                        Pane('GanttBar', axis=start, color=outcome, size_field=R('Gantt Duration Hours', 'sum'),
                             lod=[rid], label_show=False, tooltip=tip),
                        Pane('Circle', axis=mark, mark_color=WARN, size=0.35, lod=[rid], label_show=False, tooltip=tip,
                             stroke='#ffffff')])


def gantt_day_sheets() -> list[Sheet]:
    first = R('Is First Date Row')
    bar, anchor = R('Full Bar'), R('Text Anchor Centre')

    def button(name, glyph, date_field, back_field):
        lod = [R(date_field), R(back_field)]
        return Sheet(name, cols=[(bar, anchor)], hide=[bar, anchor], filters=[first], fixed={bar: (0, 1), anchor: (0, 1)},
                     tooltip=False, panes=[Pane(),
                                           Pane('Bar', axis=bar, mark_color='#ffffff', lod=lod, size=1.9890055656433105, label_show=False),
                                           label_pane(axis=anchor, text=[R(glyph)], lod=lod, align='center',
                                                      label=[run(R(glyph), 12, INK2)])])
    return [button('RUN Gantt Prev Button', 'Gantt Prev Glyph', 'Gantt Prev Date', 'Gantt Prev Back'),
            button('RUN Gantt Next Button', 'Gantt Next Glyph', 'Gantt Next Date', 'Gantt Next Back'),
            Sheet('RUN Gantt Day Label', filters=[first], tooltip=False,
                  panes=label_pane(text=[R('Gantt Day Label')], align='center',
                                   label=[run(R('Gantt Day Label'), 10, INK1, SEMI)]))]


def why_sheets() -> list[Sheet]:
    period, plat = R('In Period'), R('Is Platform Match Error')
    count = R('Failed Model Runs')

    def bars(name, dim, track_name, header_w, colour, extra_filters=()):
        track = R(track_name)
        label = [f"            <format attr='font-size' field='{dim.ref}' value='8' />",
                 f"            <format attr='color' field='{dim.ref}' value='{colour}' />"]
        tip = [run(R(dim.name, 'attr'), 9, INK1, SEMI), run(NL, 7, INK3), run('FAILED RUNS   ', 7, INK3, SEMI),
               run(count, 9, CRIT_INK, SEMI)]
        return Sheet(name, rows=[dim], cols=[(track, count)], filters=[period, plat, *extra_filters], hide=[track, count],
                     sync=[count], header_width={dim: header_w}, sorts=[(dim, 'DESC', count)], extra={'label': label},
                     panes=[Pane('Bar', label_show=False),
                            Pane('Bar', axis=track, mark_color='#eef0ee', size=0.45, label_show=False, tooltip=tip),
                            Pane('Bar', axis=count, mark_color=CRIT, size=0.45, text=[count],
                                 label=[run(count, 8, INK1, SEMI)], tooltip=tip)])
    return [
        Sheet('RUN Failed Count Label', filters=[period, plat], tooltip=False,
              panes=label_pane(text=[R('Failed Runs Label')], valign='top', label=[run(R('Failed Runs Label'), 8, INK3)])),
        bars('RUN Why Failed Bar', R('Error Category Label'), 'Why Track', 126, INK2),
        bars('RUN Top Failing Models Bar', R('display_name'), 'Top Model Track', 160, INK1, [R('Is Top Failing Model')]),
    ]


def errors_sheets() -> list[Sheet]:
    key, order = R('Error Key'), R('Error Order')
    pane = TABLE_ROW
    a = lambda n: R(n, 'attr')
    tip = [run(a('display_name'), 9, INK1, SEMI), run(NL, 7, INK3), run(a('error_message'), 8, INK1), run(NL, 7, INK3),
           run('JOB RUN   ', 7, INK3, SEMI), run(a('job_run_id'), 8, NAVY, SEMI), run(NL, 7, INK3),
           run('CLICK TO OPEN ITS LINEAGE', 7, INK3, SEMI)]
    clicks = [R('node_id (mart_run_errors.csv)'), R('node_key'), *[R(f) for f, _ in PANEL_WRITES]]

    def cell(c, colour, inert=True):
        t = R(f'Error {c} Text')
        return label_pane(title=c, inert=inert, text=[t], label=[run(t, 8, colour)], align='center', valign='center',
                          lod=[R(f'Error {c} Point', 'clct'), key, *([] if inert else clicks)], pane_size=pane,
                          tooltip=None if inert else tip)
    table = _grid(Sheet('RUN Recent Errors Table', rows=[Cross([Nest([order, key]), LAT])], cols=[LON],
                        filters=[R('In Period'), R('Is Platform Match Error')], hide=[order, key], layers=True,
                        no_basemap=True, zoom=None, divider=True,
                        panes=[Pane('Automatic', lod=[key], pane_size=pane),
                               cell('When', INK1), cell('Model', INK1), cell('Category', INK1),
                               cell('Message', INK2, inert=False)]), pane)
    hp = (TABLE_W, 22)
    header = _grid(Sheet('RUN Recent Errors Header', rows=[LAT], cols=[LON], filters=[R('Is Error Heading Row')], layers=True,
                         no_basemap=True, zoom=None, tooltip=False,
                         panes=[Pane('Automatic', pane_size=hp),
                                label_pane(title='Titles', inert=True, text=[R('Error Heading')],
                                           label=[run(R('Error Heading'), 7, INK3, SEMI)], align='center',
                                           lod=[R('Error Heading Point', 'clct'), R('day_index')], pane_size=hp)]), hp)
    return [header, table]


def mttr_sheet() -> Sheet:
    x = R('Days Back Mid')
    line, area = R('MTTR Rolling 7 Day Line'), R('MTTR Rolling 7 Day Area')
    date = R(DATE)
    for r in (line, area):  # the date rides along on Detail for the tooltip, so address across both
        r.tc_order = [x, date]
    rl, rstyle = _window_lines(x, selected=False)
    fmt = 'n#,##0"h";-#,##0"h"'
    tip = [run(date, 9, INK1, SEMI), run(NL, 7, INK3), run('MEAN RECOVERY, 7 DAYS   ', 7, INK3, SEMI),
           run(line, 9, NAVY, SEMI)]
    return Sheet('RUN MTTR Rolling Line', cols=[x], rows=[(area, line)], filters=[R('Is Platform Match Day (Episodes)')],
                 hide=[x, line], sync=[line], fixed={x: BACK_AXIS, area: MTTR_Y},
                 formats={area: 'n#,##0.0"h";-#,##0.0"h"', line: 'n#,##0.0"h";-#,##0.0"h"', date: '*d mmm yyyy'},
                 extra={'axis': _axis_style(area, fmt=fmt), 'refline': rstyle},
                 panes=[Pane('Area', label_show=False),
                        Pane('Area', axis=area, mark_color=ACCENT, transparency=40, label_show=False, lod=[date], tooltip=tip,
                             reflines=rl),
                        Pane('Line', axis=line, mark_color=ACCENT, size=1, label_show=False, lod=[date], tooltip=tip)])


def sheets() -> list[Sheet]:
    return ([daily_sheet(), incident_sheet(), axis_strip('RUN Daily Axis', BAR_Y, 'Axis Label Anchor'), gantt_sheet()]
            + gantt_day_sheets() + why_sheets() + errors_sheets()
            + [mttr_sheet(), axis_strip('RUN MTTR Axis', MTTR_Y, 'Axis Label Anchor MTTR')])


# ================================================================ dashboard content (build plan 3.4)

def _legend(items, extra=()):
    rs = []
    for i, (label, colour, glyph) in enumerate(items):
        rs += [run(glyph + ' ', 8, colour), run(label + ('     ' if i < len(items) - 1 else ''), 8, INK2)]
    return rs + list(extra)


def _button(name, fixed):
    return Z('horz', friendly=f'{name} Holder', fixed=fixed, kids=[sheet(name)], style={
        'border-color': LINE, 'border-style': 'solid', 'border-width': '1', 'corner-radius': '8',
        'margin-top': '6', 'margin-bottom': '6', 'margin-left': '4', 'margin-right': '4'})


def content() -> Z:
    daily = card('RUN Daily Card', fixed=DAILY_H, kids=[
        Z('horz', friendly='RUN Daily Header', fixed=44, kids=[
            card_header('Failed and skipped model runs per day',
                        'A failed model makes everything downstream skip. Ticks mark incidents. Click a day to load its run timeline below.',
                        None),  # flex: in a horizontal row a fixed size is a width
            text(_legend([('Failed', CRIT, '■'), ('Skipped because upstream failed', SKIP_GREY, '■')]), fixed=270,
                 **{'text-align': 'right'})]),
        sheet('RUN Incident Markers', 18),
        sheet('RUN Daily Failures Bar'),
        sheet('RUN Daily Axis', 16)])
    gantt = card('RUN Gantt Card', margins={'right': 7}, kids=[
        Z('horz', friendly='RUN Gantt Header', fixed=44, kids=[
            card_header('Job run timeline', 'Every dbt job run on the selected day, coloured by outcome', None),
            _button('RUN Gantt Prev Button', 40),
            Z('horz', friendly='RUN Gantt Day Holder', fixed=140, kids=[sheet('RUN Gantt Day Label')]),
            _button('RUN Gantt Next Button', 40)]),
        sheet('RUN Job Gantt'),
        text(_legend([('Succeeded', SUCCESS_BLUE, '■'), ('Failed', CRIT, '■'), ('Cancelled', CANCEL_GREY, '■'),
                      ('Tests failed in run', WARN, '●')]), fixed=22, **{'padding-top': '6'})])
    why = card('RUN Why Card', fixed=SIDE_W + 7, margins={'left': 7}, kids=[
        text([run('Why runs failed', 10, INK1, SEMI)], fixed=20),
        sheet('RUN Failed Count Label', 24),
        sheet('RUN Why Failed Bar', 130),
        text([run('MODELS THAT FAILED MOST', 7, INK3, SEMI)], fixed=26, **{'padding-top': '10'}),
        sheet('RUN Top Failing Models Bar')])
    errors = card('RUN Errors Card', margins={'right': 7}, kids=[
        card_header('Recent errors', 'Newest first. Hover a message to read it in full. Click a row to open its lineage.'),
        sheet('RUN Recent Errors Header', 22),
        sheet('RUN Recent Errors Table')])
    mttr = card('RUN MTTR Card', fixed=SIDE_W + 7, margins={'left': 7}, kids=[
        card_header('Mean time to recover', 'Rolling 7-day average, in hours. Long tails come from issues that wait '
                    'for the next daily run.', 58),
        sheet('RUN MTTR Rolling Line'),
        sheet('RUN MTTR Axis', 16)])
    return Z('vert', friendly='RUN Content', style=CONTENT_PAD, kids=[
        daily,
        Z('horz', friendly='RUN Middle Row', fixed=MID_H + 14, style={'margin-top': '14'}, kids=[gantt, why]),
        Z('horz', friendly='RUN Bottom Row', fixed=BOTTOM_H + 14, style={'margin-top': '14'}, kids=[errors, mttr])])


def check_fit(zones) -> None:
    by = {z.name: z.rect for z in zones if z.kind == 'sheet'}
    for name, (w, h) in {'RUN Recent Errors Table': (TABLE_W, TABLE_ROW[1]), 'RUN Recent Errors Header': (TABLE_W, 22)}.items():
        _, _, zw, zh = by[name]
        assert w <= zw and h <= zh, f'{name}: needs {w} x {h} px, zone is {zw:.0f} x {zh:.0f}'


ACTIONS = [  # (sheet, source Ref factory, parameter, caption)
    ('RUN Daily Failures Bar', lambda: R(DATE), 'p_gantt_date', 'RUN Pick Gantt Day'),
    ('RUN Daily Failures Bar', lambda: R('Days Back Mid'), 'p_gantt_back', 'RUN Pick Gantt Day Back'),
    ('RUN Gantt Prev Button', lambda: R('Gantt Prev Date'), 'p_gantt_date', 'RUN Gantt Prev'),
    ('RUN Gantt Prev Button', lambda: R('Gantt Prev Back'), 'p_gantt_back', 'RUN Gantt Prev Back'),
    ('RUN Gantt Next Button', lambda: R('Gantt Next Date'), 'p_gantt_date', 'RUN Gantt Next'),
    ('RUN Gantt Next Button', lambda: R('Gantt Next Back'), 'p_gantt_back', 'RUN Gantt Next Back'),
    ('RUN Recent Errors Table', lambda: R('node_id (mart_run_errors.csv)'), 'p_selected_node', 'RUN Error Select Node'),
    ('RUN Recent Errors Table', lambda: R('node_key'), 'p_selected_node_key', 'RUN Error Select Node Key'),
    *[('RUN Recent Errors Table', (lambda f=f: R(f)), param, f'RUN Error Set {param}') for f, param in PANEL_WRITES],
]

# an error row opens the Lineage explorer for now; Blast radius once that tab exists (GB, 22 Oct)
NAV_ACTIONS = [('RUN Recent Errors Table', 'Lineage explorer', 'Go to Lineage from RUN Recent Errors Table')]

DEHIGHLIGHT = ['RUN Daily Failures Bar', 'RUN Gantt Prev Button', 'RUN Gantt Next Button', 'RUN Recent Errors Table']
