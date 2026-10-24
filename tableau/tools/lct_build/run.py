"""Tab 2, Run & failures (RUN): calc pack section 6, build plan 3.4.

Native Tableau charts where they already look like the prototype (daily bars, job Gantt, why-failed bars, MTTR
line) and a pixel canvas only for the Recent errors table (GB, 22 Oct: "Mixed").

The 90-day charts share one x axis: Days Back Mid (days before the as-of date + 0.5), fixed 0 to 90 and reversed,
so today is on the right and day d fills [d, d + 1]. The selected window is then simply "below p_period", which a
band of full-width back bars shades (light blue), and the clicked day gets a navy border: a wider navy bar behind its
stack, the technique of GB's border-highlight example (v24). The incident
strip above the bars and the date strip under them use the same axis, and the same fixed y axis with its labels
made clear, so all three line up to the pixel.
"""

from __future__ import annotations

import csv
from datetime import datetime

from . import shapes as SH
from .core import (PANEL_WRITES, ACCENT, ACCENT_TINT, B_DIM, CALCS, CRIT, CRIT_INK, I_DIM, I_MEA, INK1, INK2, INK3,
                   INK4, LAT, MEASURE_NAMES, MEASURE_VALUES, LINE, LON, NAVY, NL, R_MEA, S_DIM, S_MEA, SEMI, SP_MEA, WARN, Cross, Nest, Pane, R, Sheet, Z, blank,
                   button_label_pane, card, card_header, color_map, label_pane, run, sheet, text)
from .lineage import _fit, _grid, _q
from .shell import CONTENT_H, CONTENT_PAD

P = 'RUN'
DATE = 'date (dim_date.csv)'
ROOT = SH.ROOT
ERRORS = list(csv.DictReader(open(ROOT / 'data' / 'marts' / 'mart_run_errors.csv', encoding='utf-8')))
NODE_NAME = {r['node_id']: r['display_name'] for r in csv.DictReader(open(ROOT / 'data' / 'marts' / 'dim_nodes.csv', encoding='utf-8'))}

# ---------------------------------------------------------------- geometry (content 1312 x CONTENT_H)
SIDE_W = 380                                   # Why runs failed and MTTR cards; 7 px margin-left outside
MAIN_W = 1312 - SIDE_W - 7 - 7                 # 918: Gantt and errors cards, 7 px margin-right outside
DAILY_H, MID_H = 220, 352                       # card heights; the two lower rows sit 14 px below the one above
BOTTOM_H = CONTENT_H - DAILY_H - 14 - MID_H - 14  # 244: the bottom row takes the rest, so nothing is left below
TABLE_W = MAIN_W - 7 - 2 * 16 - 2 - 18 - SH.SLACK  # 855: the errors table inside its 877 px zone and scroll bar
ROW_H = 27                                     # prototype row height
# a native text table (v26): When, Model and Category are row headers of fixed width, the message is the text mark
# filling the rest, so the columns can never run into each other (the v25 canvas did under Fit width)
COL_W = {'When': 96, 'Model': 192, 'Category': 120}
MSG_W = TABLE_W - sum(COL_W.values())           # 447 px of message, cut with "…" by the build

DAYS = 90
BACK_AXIS = (0, DAYS, {'reverse': 'true'})    # Days Back Mid: today on the right
BAR_Y = (0, 54, {'major-origin': '0', 'major-spacing': '25'})     # busiest day: 47 failed + skipped; outline to 53.2
MTTR_Y = (0, 25, {'major-origin': '0', 'major-spacing': '10'})    # rolling MTTR peaks at 24 h (Databricks)
CLEAR = '#00000000'
SKIP_GREY, SUCCESS_BLUE, CANCEL_GREY = '#c3c9cf', '#9db9d6', '#c3c9cf'
# the prototype's chart colours on white: other days' bars at 55 % opacity, the window band accent at 5 %,
# the MTTR area accent at 8 % (mockup/src/core.js timeChart)
PALE_FAILED, PALE_SKIPPED, BAND, MTTR_AREA = '#e69995', '#dee1e5', '#f2f7fb', '#ebf2f8'


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
    """Every cell's text, written by the build (Liberation Sans = Arial metrics), so the model and message are cut
    with "…" to fit their column."""
    f = {}
    keys = {r['job_run_id'] + '|' + r['node_id']: r for r in ERRORS}
    cols = {
        'When': {k: _when(r['run_started_at']) for k, r in keys.items()},
        'Model': {k: _fit(NODE_NAME.get(r['node_id'], r['node_id']), COL_W['Model'] - 16, 8) for k, r in keys.items()},
        'Category': {k: CAT_NAME.get(r['error_category'], r['error_category']) for k, r in keys.items()},
        # Tableau pads a cell and wraps text that does not fit (v26 wrapped onto a second line): leave 40 px
        'Message': {k: _fit(r['error_message'], MSG_W - 40, 8) for k, r in keys.items()},
    }
    for c, vals in cols.items():
        f[f'Error {c} Text'] = _key_case(f'Error {c} Text', f'{c} cell of the Recent errors table, as the build wrote it.', vals)
    for c in ('When', 'Model', 'Category', 'Message'):
        f[f'Error Head {c}'] = f'// Error Head {c}\n// Column title over the Recent errors table.\n{_q(c.upper())}'
    return f


def calcs():
    hours = lambda m: f'{m} / 60'
    f = {
        # shared 90-day axis
        'Days Back Mid': ('// Days Back Mid\n// x of every 90-day chart on this tab: days before the as-of date + 0.5, on an axis fixed\n'
                          '// 0 to 90 and reversed, so day d fills [d, d + 1] and the window is everything below p_period.\n'
                          '[days_before_as_of] + 0.5'),
        'Is First Date Row': '// Is First Date Row\n// One-row scaffold (the first day) for the Gantt day buttons and label. Put on Filters (True).\n[day_index] = 0',
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
        'Axis Month Label': ('// Axis Month Label\n// "1 Aug", "1 Sep", "1 Oct" under the narrow MTTR chart (no "22 Jul": it ran into "1 Aug").\n'
                             'IF DAY([date (dim_date.csv)]) = 1\n'
                             'THEN "1 " + LEFT(DATENAME(\'month\', [date (dim_date.csv)]), 3)\nEND'),
        'Axis Label Anchor MTTR': '// Axis Label Anchor MTTR\n// Same, on the MTTR chart\'s 0 to 25 scale.\nIF NOT ISNULL(MIN([Axis Month Label])) THEN 12.5 END',
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
        # the back layer of the daily chart: the clicked day's border, else the selected window's band
        'Daily Is Selected': ('// Daily Is Selected\n// The day loaded in the Gantt (clicked, or stepped to with ‹ ›).\n'
                              'MAX(IIF([Is Gantt Day], 1, 0)) = 1'),
        'Daily Is In Window': '// Daily Is In Window\n// The day is inside the selected 7/30/90-day window.\nMAX(IIF([In Period], 1, 0)) = 1',
        # back axis: the clicked day's outline, else the window band (as GB's border-highlight example)
        'Daily Back Height': ('// Daily Back Height\n// Back bars: the clicked day navy to near the top (its edge shows round the bars and the filler as\n'
                              '// the prototype\'s outline), every other day in the window full height (the bars touch: the band).\n'
                              'IF [Daily Is Selected] THEN 53.2\nELSEIF [Daily Is In Window] THEN 54\nEND'),
        'Daily Back Key': ('// Daily Back Key\n// Colour of the back bars: Selected (navy outline) or Window (the band).\n'
                           'IF [Daily Is Selected] THEN "Selected"\nELSEIF [Daily Is In Window] THEN "Window"\nEND'),
        # front axis, stacked as Measure Values: full colour on the clicked day, pale (55 %) on the others
        'Daily Failed Selected': '// Daily Failed Selected\n// Failed runs on the clicked day (full red).\nIF [Daily Is Selected] THEN SUM([runs_failed]) END',
        'Daily Failed Other': '// Daily Failed Other\n// Failed runs on every other day (pale red).\nIF NOT [Daily Is Selected] THEN SUM([runs_failed]) END',
        'Daily Skipped Selected': '// Daily Skipped Selected\n// Skipped runs on the clicked day (full grey).\nIF [Daily Is Selected] THEN SUM([runs_skipped]) END',
        'Daily Skipped Other': '// Daily Skipped Other\n// Skipped runs on every other day (pale grey).\nIF NOT [Daily Is Selected] THEN SUM([runs_skipped]) END',
        'Daily Fill Window': ('// Daily Fill Window\n// Above the clicked day\'s stack, up to the outline\'s top edge, in the band colour: the outline\n'
                              '// stays hollow, as in the prototype.\nIF [Daily Is Selected] AND [Daily Is In Window] THEN 52.6 - [Daily Failed And Skipped] END'),
        'Daily Fill Plain': ('// Daily Fill Plain\n// The same filler in white when the clicked day is outside the window.\n'
                             'IF [Daily Is Selected] AND NOT [Daily Is In Window] THEN 52.6 - [Daily Failed And Skipped] END'),
        'Tooltip Day Text': ('// Tooltip Day Text\n// "Mon 12 Oct" in a 90-day chart\'s tooltip, as an aggregate so it never splits a line or area.\n'
                             'LEFT(DATENAME(\'weekday\', MIN([date (dim_date.csv)])), 3) + " " + STR(DAY(MIN([date (dim_date.csv)]))) + " "\n'
                             '+ LEFT(DATENAME(\'month\', MIN([date (dim_date.csv)])), 3)'),
        'Gantt Prev Glyph': '// Gantt Prev Glyph\n// ‹ on the previous-day button.\nMIN("‹")',
        'Gantt Next Glyph': '// Gantt Next Glyph\n// › on the next-day button.\nMIN("›")',
        # why runs failed and top models (Run Errors)
        'Why Track': ('// Why Track\n// Where each count label ends, right-aligned as in the mock: a little past the longest bar, so no\n'
                      '// bar runs through a number (v24 had them on the bar end). Table calc along Error Category Label.\n'
                      'WINDOW_MAX([Failed Model Runs]) * 1.14'),
        'Top Model Track': ('// Top Model Track\n// Same for the top-models bars. Table calc along display_name.\nWINDOW_MAX([Failed Model Runs]) * 1.14'),
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
    'Days Back Mid': R_DIM_Q, 'Is First Date Row': B_DIM,
    'Daily Failed Runs': R_MEA, 'Daily Skipped Runs': R_MEA, 'Daily Failed And Skipped': R_MEA,
    'Incident Tick': R_MEA, 'Incident Label Anchor': R_MEA, 'Axis Date Label': S_DIM, 'Axis Label Anchor': R_MEA,
    'Axis Label Anchor MTTR': R_MEA, 'Axis Month Label': S_DIM,
    'Gantt Start Hour': R_MEA, 'Gantt Duration Hours': R_MEA, 'Tests Failed Marker Hour': R_MEA,
    'Gantt Started Text': S_DIM, 'Gantt Duration Text': S_DIM, 'Job Platform Name': S_DIM,
    'Daily Back Height': R_MEA, 'Daily Back Key': S_MEA, 'Daily Is Selected': ('boolean', 'measure', 'nominal'),
    'Daily Is In Window': ('boolean', 'measure', 'nominal'), 'Daily Failed Selected': R_MEA, 'Daily Failed Other': R_MEA,
    'Daily Skipped Selected': R_MEA, 'Daily Skipped Other': R_MEA, 'Daily Fill Window': R_MEA, 'Daily Fill Plain': R_MEA, 'Is Gantt Day': B_DIM, 'Gantt Prev Glyph': S_MEA, 'Gantt Next Glyph': S_MEA,
    'Tooltip Day Text': S_MEA, 'Why Track': R_MEA, 'Top Model Track': R_MEA, 'Is Top Failing Model': ('boolean', 'measure', 'nominal'),
    'Error Key': S_DIM, 'Error Order': I_DIM,
    'MTTR Rolling 7 Day Line': R_MEA, 'MTTR Rolling 7 Day Area': R_MEA,

    # calc pack section 6 (and 2) calcs this tab reads
    'Is Platform Match Job': B_DIM, 'Is Platform Match Error': B_DIM, 'Job Run Outcome': S_DIM,
    'Job Schedule Label': S_DIM, 'Gantt Day Label': S_DIM, 'Gantt Prev Date': ('date', 'dimension', 'ordinal'),
    'Gantt Next Date': ('date', 'dimension', 'ordinal'), 'As Of Date': ('date', 'dimension', 'ordinal'),
    'Incident Marker Label': S_DIM, 'Failed Model Runs': I_MEA, 'Failed Runs Label': S_MEA,
    'Error Category Label': S_DIM, 'Error Time Label': S_DIM,
}
for c in ('When', 'Model', 'Category', 'Message'):
    TYPES[f'Error {c} Text'] = S_DIM
    TYPES[f'Error Head {c}'] = S_DIM

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


def _window_lines(axis):
    """The selected window: fill below a reference line on p_period, the line itself clear (MTTR chart)."""
    # The daily chart draws its window as a band of back bars (v24). Tableau re-saved this line as %null% in v22b,
    # so it waits for a Tableau-saved parameter reference line to copy.
    rl = [dict(id='refline0', axis=axis, param='p_period', z=1)]
    style = ["            <format attr='stroke-size' id='refline0' value='0' />",
             f"            <format attr='stroke-color' id='refline0' value='{CLEAR}' />",
             f"            <format attr='fill-above' id='refline0' value='{CLEAR}' />",
             f"            <format attr='fill-below' id='refline0' value='{BAND}' />"]
    return rl, style


def daily_sheet() -> Sheet:
    """Back axis: the window band and the clicked day's navy border (wide bars). Front axis: failed (red) and skipped
    (grey) stacked as Measure Values, narrower, so the back bar shows round the clicked day's stack."""
    x, date = R('Days Back Mid'), R(DATE)
    back, key, failed, skipped = R('Daily Back Height'), R('Daily Back Key'), R('Daily Failed Runs'), R('Daily Skipped Runs')
    color_map(key, {'"Selected"': NAVY, '"Window"': BAND})
    stack = [(R('Daily Failed Selected'), CRIT), (R('Daily Failed Other'), PALE_FAILED),
             (R('Daily Skipped Selected'), SKIP_GREY), (R('Daily Skipped Other'), PALE_SKIPPED),
             (R('Daily Fill Window'), BAND), (R('Daily Fill Plain'), '#ffffff')]
    tip = [run(R(DATE), 9, INK1, SEMI), run(NL, 7, INK3),
           run('FAILED   ', 7, INK3, SEMI), run(failed, 9, CRIT_INK, SEMI), run(NL, 7, INK3),
           run('SKIPPED   ', 7, INK3, SEMI), run(R('Daily Skipped Runs'), 9, NAVY, SEMI), run(NL, 7, INK3),
           run('CLICK TO LOAD ITS RUN TIMELINE', 7, INK3, SEMI)]
    mv = MEASURE_VALUES.ref
    axis = _axis_style(back) + [
        f"            <encoding attr='space' class='0' field='{mv}' field-type='quantitative' fold='true' scope='rows' synchronized='true' type='space' />",
        f"            <format attr='display' class='0' field='{mv}' scope='rows' value='false' />"]
    return Sheet('RUN Daily Failures Bar', cols=[x], rows=[(back, MEASURE_VALUES)], filters=[R('Is Platform Match Day')],
                 hide=[x], fixed={x: BACK_AXIS, back: BAR_Y}, measure_values=stack,
                 formats={R(DATE): '*d mmm yyyy', back: 'n#,##0;-#,##0'}, extra={'axis': axis},
                 panes=[Pane('Bar', size=1.2, label_show=False, lod=[date]),
                        Pane('Bar', axis=back, color=key, size=1.9890055656433105, label_show=False, lod=[date], tooltip=tip),
                        Pane('Bar', axis=MEASURE_VALUES, color=MEASURE_NAMES, size=1.65, label_show=False, lod=[date],
                             tooltip=tip, tooltip_fields=[failed, skipped])])


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


def axis_strip(name, y_fixed, anchor_name, label='Axis Date Label', fmt=None) -> Sheet:
    """Date labels under a 90-day chart, on the same reversed axis, with the chart's y axis in clear text (same range
    and format, so the clear axis is exactly as wide and the plots line up)."""
    x, anchor = R('Days Back Mid'), R(anchor_name)
    lab = R(label)
    return Sheet(name, cols=[x], rows=[anchor], hide=[x], fixed={x: BACK_AXIS, anchor: y_fixed}, tooltip=False,
                 formats={anchor: fmt} if fmt else {}, extra={'axis': _axis_style(anchor, False, fmt)},
                 panes=label_pane(text=[lab], label=[run(lab, 8, INK3)], align='center'))



def gantt_sheet() -> Sheet:
    job, sched = R('job_name'), R('Job Schedule Label')
    start, mark = R('Gantt Start Hour', 'min'), R('Tests Failed Marker Hour', 'min')
    outcome, rid = R('Job Run Outcome'), R('job_run_id (mart_job_runs.csv)')
    color_map(outcome, {'"Succeeded"': SUCCESS_BLUE, '"Failed"': CRIT, '"Cancelled"': CANCEL_GREY})
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

    def button(name, glyph, date_field):
        lod = [R(date_field)]
        return Sheet(name, cols=[(bar, anchor)], hide=[bar, anchor], filters=[first], fixed={bar: (0, 1), anchor: (0, 1)},
                     tooltip=False, panes=[Pane(lod=list(lod)),
                                           Pane('Bar', axis=bar, mark_color='#ffffff', lod=list(lod), size=1.9890055656433105, label_show=False),
                                           button_label_pane(axis=anchor, text=[R(glyph)], lod=list(lod), align='center',
                                                             label=[run(R(glyph), 12, INK2)])])
    return [button('RUN Gantt Prev Button', 'Gantt Prev Glyph', 'Gantt Prev Date'),
            button('RUN Gantt Next Button', 'Gantt Next Glyph', 'Gantt Next Date'),
            Sheet('RUN Gantt Day Label', filters=[first], tooltip=False,
                  panes=label_pane(text=[R('Gantt Day Label')], align='center',
                                   label=[run(R('Gantt Day Label'), 10, INK1, SEMI)]))]


def why_sheets() -> list[Sheet]:
    period, plat = R('In Period'), R('Is Platform Match Error')
    count = R('Failed Model Runs')

    def bars(name, dim, track_name, header_w, colour, extra_filters=()):
        track = R(track_name)
        label = [f"            <format attr='font-size' field='{dim.ref}' value='8' />",
                 f"            <format attr='color' field='{dim.ref}' value='{colour}' />",
                 f"            <format attr='text-align' field='{dim.ref}' value='left' />"]  # GB, v22b
        tip = [run(R(dim.name, 'attr'), 9, INK1, SEMI), run(NL, 7, INK3), run('FAILED RUNS   ', 7, INK3, SEMI),
               run(count, 9, CRIT_INK, SEMI)]
        # the count rides on a clear hairline mark just past the longest bar: text-align left ends the text at that
        # point, so the counts are right-aligned and no bar runs through them (GB, v22b and v24)
        return Sheet(name, rows=[dim], cols=[(count, track)], filters=[period, plat, *extra_filters], hide=[track, count],
                     sync=[track], header_width={dim: header_w}, sorts=[(dim, 'DESC', count)], extra={'label': label},
                     panes=[Pane('Bar', label_show=False),
                            Pane('Bar', axis=count, mark_color=CRIT, size=0.3, label_show=False, tooltip=tip),
                            label_pane(axis=track, text=[count], label=[run(count, 8, INK1, SEMI)], align='left',
                                       tooltip=tip)])
    return [
        Sheet('RUN Failed Count Label', filters=[period, plat], tooltip=False,
              panes=label_pane(text=[R('Failed Runs Label')], valign='top', label=[run(R('Failed Runs Label'), 8, INK3)])),
        bars('RUN Why Failed Bar', R('Error Category Label'), 'Why Track', 126, INK2),
        bars('RUN Top Failing Models Bar', R('display_name'), 'Top Model Track', 160, INK1, [R('Is Top Failing Model')]),
    ]


# a text table bands alternate rows grey by default (v26); the prototype has none
NO_BANDS = {el: [f"            <format attr='band-color' scope='{s}' value='#00000000' />" for s in ('rows', 'cols')]
            for el in ('pane', 'header')}


def errors_sheets() -> list[Sheet]:
    """A native text table: hidden order and key, then When / Model / Category as fixed-width row headers and the
    message as the text mark. The title row is the same structure on a one-row scaffold, so its columns line up."""
    key, order = R('Error Key'), R('Error Order')
    when, model, cat, msg = (R(f'Error {c} Text') for c in ('When', 'Model', 'Category', 'Message'))
    a = lambda n: R(n, 'attr')
    tip = [run(a('display_name'), 9, INK1, SEMI), run(NL, 7, INK3), run(a('error_message'), 8, INK1), run(NL, 7, INK3),
           run('JOB RUN   ', 7, INK3, SEMI), run(a('job_run_id'), 8, NAVY, SEMI), run(NL, 7, INK3),
           run('CLICK TO OPEN ITS LINEAGE', 7, INK3, SEMI)]
    clicks = [R('node_id (mart_run_errors.csv)'), R('node_key'), *[R(f) for f, _ in PANEL_WRITES]]

    def styles(fields, size, colour, bold=False):
        out = []
        for f in fields:
            out += [f"            <format attr='font-size' field='{f.ref}' value='{size}' />",
                    f"            <format attr='color' field='{f.ref}' value='{colour}' />",
                    f"            <format attr='text-align' field='{f.ref}' value='left' />",
                    f"            <format attr='vertical-align' field='{f.ref}' value='center' />"]
            if bold:
                out.append(f"            <format attr='font-weight' field='{f.ref}' value='bold' />")
        return out
    table = Sheet('RUN Recent Errors Table', rows=[order, key, when, model, cat], filters=[R('In Period'), R('Is Platform Match Error')],
                  hide=[order, key], header_width={when: COL_W['When'], model: COL_W['Model'], cat: COL_W['Category']},
                  row_height=(cat, ROW_H), zoom='fit-width', divider='rows', extra={'label': styles([when, model, cat], 8, INK1), **NO_BANDS},
                  panes=Pane('Text', text=[msg], label=[run(msg, 8, INK2)], lod=clicks, tooltip=tip, align='left'))
    heads = [R(f'Error Head {c}') for c in ('When', 'Model', 'Category', 'Message')]
    header = Sheet('RUN Recent Errors Header', rows=heads[:3], filters=[R('Is First Date Row')], tooltip=False,
                   header_width={heads[0]: COL_W['When'], heads[1]: COL_W['Model'], heads[2]: COL_W['Category']},
                   row_height=(heads[2], 22), zoom='fit-width', extra={'label': styles(heads[:3], 7, INK3, True), **NO_BANDS},
                   panes=Pane('Text', text=[heads[3]], label=[run(heads[3], 7, INK3, SEMI)], align='left'))
    return [header, table]


def mttr_sheet() -> Sheet:
    x = R('Days Back Mid')
    line, area = R('MTTR Rolling 7 Day Line'), R('MTTR Rolling 7 Day Area')
    date = R('Tooltip Day Text')   # an aggregate: a date dimension on Detail broke the area and line into pieces (v22b)
    rl, rstyle = _window_lines(x)
    fmt = 'n#,##0"h";-#,##0"h"'
    tip = [run(date, 9, INK1, SEMI), run(NL, 7, INK3), run('MEAN RECOVERY, 7 DAYS   ', 7, INK3, SEMI),
           run(line, 9, NAVY, SEMI)]
    return Sheet('RUN MTTR Rolling Line', cols=[x], rows=[(area, line)], filters=[R('Is Platform Match Day (Episodes)')],
                 hide=[x, line], sync=[line], fixed={x: BACK_AXIS, area: MTTR_Y},
                 formats={area: fmt, line: 'n#,##0.0"h";-#,##0.0"h"'},  # the axis follows the first measure: whole hours
                 extra={'axis': _axis_style(area, fmt=fmt), 'refline': rstyle},
                 panes=[Pane('Area', label_show=False),
                        Pane('Area', axis=area, mark_color=MTTR_AREA, label_show=False, tooltip=tip, reflines=rl),
                        Pane('Line', axis=line, mark_color=ACCENT, size=0.4, label_show=False, tooltip=tip)])


def sheets() -> list[Sheet]:
    return ([daily_sheet(), incident_sheet(), axis_strip('RUN Daily Axis', BAR_Y, 'Axis Label Anchor'), gantt_sheet()]
            + gantt_day_sheets() + why_sheets() + errors_sheets()
            + [mttr_sheet(), axis_strip('RUN MTTR Axis', MTTR_Y, 'Axis Label Anchor MTTR', 'Axis Month Label',
                                        'n#,##0"h";-#,##0"h"')])


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
    errors = card('RUN Errors Card', fixed=MAIN_W - 7, margins={'right': 7}, kids=[
        card_header('Recent errors', 'Newest first. Hover a message to read it in full. Click a row to open its lineage.'),
        sheet('RUN Recent Errors Header', 22),
        blank(1, LINE),  # the prototype's 1 px line under the column titles
        sheet('RUN Recent Errors Table')])
    mttr = card('RUN MTTR Card', margins={'left': 7}, kids=[
        card_header('Mean time to recover', 'Rolling 7-day average, in hours. Long tails come from issues that wait '
                    'for the next daily run.', 58),
        sheet('RUN MTTR Rolling Line'),
        sheet('RUN MTTR Axis', 16)])
    return Z('vert', friendly='RUN Content', style=CONTENT_PAD, kids=[
        daily,
        # a fixed size excludes the zone's own margin: 352 + 14 above (v22 to v25 counted the 14 twice: 864 px in 836)
        Z('horz', friendly='RUN Middle Row', fixed=MID_H, style={'margin-top': '14'}, kids=[gantt, why]),
        # the last row is flexible: it always runs down to the bottom padding, whatever Tableau makes of the fixed rows
        # above (v27: Tableau laid the middle row out about 30 px shorter and the slack became a gap at the bottom)
        Z('horz', friendly='RUN Bottom Row', style={'margin-top': '14'}, kids=[errors, mttr])])


def check_fit(zones) -> None:
    """The errors table fits its zone with room for the scroll bar, and the three rows end exactly where the content
    area does (v22 to v25 overflowed by 28 px and Tableau rebalanced, leaving space at the bottom)."""
    from .shell import CONTENT_PAD
    by = {(z.name or z.friendly): z.rect for z in zones}
    _, _, zw, _ = by['RUN Recent Errors Table']
    assert TABLE_W + 18 <= zw, f'RUN Recent Errors Table: needs {TABLE_W} + 18 px, zone is {zw:.0f}'
    _, y, _, h = by['RUN Bottom Row']
    end = 1000 - int(CONTENT_PAD['padding-bottom'])
    assert abs(y + h - end) < 0.5, f'RUN rows end at {y + h:.0f}, content ends at {end}'



ACTIONS = [  # (sheet, source Ref factory, parameter, caption)
    ('RUN Daily Failures Bar', lambda: R(DATE), 'p_gantt_date', 'RUN Pick Gantt Day'),
    ('RUN Gantt Prev Button', lambda: R('Gantt Prev Date'), 'p_gantt_date', 'RUN Gantt Prev'),
    ('RUN Gantt Next Button', lambda: R('Gantt Next Date'), 'p_gantt_date', 'RUN Gantt Next'),
    ('RUN Recent Errors Table', lambda: R('node_id (mart_run_errors.csv)'), 'p_selected_node', 'RUN Error Select Node'),
    ('RUN Recent Errors Table', lambda: R('node_key'), 'p_selected_node_key', 'RUN Error Select Node Key'),
    *[('RUN Recent Errors Table', (lambda f=f: R(f)), param, f'RUN Error Set {param}') for f, param in PANEL_WRITES],
]

# an error row opens the Lineage explorer for now; Blast radius once that tab exists (GB, 22 Oct)
NAV_ACTIONS = [('RUN Recent Errors Table', 'Lineage explorer', 'Go to Lineage from RUN Recent Errors Table')]

DEHIGHLIGHT = ['RUN Daily Failures Bar', 'RUN Gantt Prev Button', 'RUN Gantt Next Button', 'RUN Recent Errors Table']
