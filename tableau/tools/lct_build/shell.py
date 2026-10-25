"""The shared shell (build plan section 2): nav, header, filter band, info panel and the GL sheets."""

from __future__ import annotations

from .core import (R_MEA, ACCENT, BOLD, BOOK, CALCS, CANVAS, CARD, CARD_STYLE, INK1, INK2, INK3, INK4, LIME, LINE,
                   LINE_SOFT, MEDIUM, NAVY, NL, PLAT, SEMI, B_DIM, I_DIM, S_DIM, Cross, Pane, R, Sheet, Z, blank,
                   color_map, button_label_pane, label_pane, run, sheet, text)

TABS = [  # prefix, dashboard name, nav group, question, nav icon (None = not in the nav)
    ('HO', 'Health overview', 'Monitor', 'Is anything on fire right now?', 'health'),
    ('RUN', 'Run & failures', 'Monitor', 'What failed, when, why, and how fast did we recover?', 'runs'),
    ('FR', 'Freshness & SLAs', 'Monitor', 'Is the data arriving on time?', 'fresh'),
    ('LIN', 'Lineage explorer', 'Investigate', 'What feeds this exposure, and is every step healthy?', 'lineage'),
    ('BR', 'Blast radius', 'Investigate', 'If this breaks, who do I need to tell?', 'blast'),
    ('QA', 'Data quality', 'Investigate', 'Which tests keep failing, and where are we untested?', 'quality'),
    ('PF', 'Performance & cost', 'Optimise', 'What is getting slower and more expensive?', 'perf'),
    ('US', 'Usage & adoption', 'Optimise', 'Which data products earn their keep?', 'usage'),
    ('GOV', 'Governance', 'Govern', 'Is everything owned, documented, tested and declared?', 'gov'),
    ('AB', 'About & how to use', 'Govern', 'What this is, where the numbers come from', 'about'),
    ('DOC', 'Documentation', 'About', 'Parameters, actions and build notes', None),
]

# ---------------------------------------------------------------- calcs the shell adds (calc pack 2.9)
CALCS.add(formulas={
    'Is Period Button Row': '// Is Period Button Row\n// Keeps the 3 scaffold rows that carry a period button. Put on Filters (True).\nNOT ISNULL([Period Option])',
    'Period Label Active': '// Period Label Active\n// Button text when this button is the selected period (Semibold Navy run).\nIF [Is Active Period Option] THEN [Period Option Label] ELSE "" END',
    'Period Label Inactive': '// Period Label Inactive\n// Button text when this button is not selected (Book grey run).\nIF NOT [Is Active Period Option] THEN [Period Option Label] ELSE "" END',
    'Is Platform Button Row': '// Is Platform Button Row\n// Keeps the 4 scaffold rows that carry a platform button. Put on Filters (True).\nNOT ISNULL([Platform Option])',
    'Platform Label Active': '// Platform Label Active\n// Button text when this button is the selected platform (Semibold Navy run).\nIF [Is Active Platform Option] THEN [Platform Option Label] ELSE "" END',
    'Platform Label Inactive': '// Platform Label Inactive\n// Button text when this button is not selected (Book grey run).\nIF NOT [Is Active Platform Option] THEN [Platform Option Label] ELSE "" END',
    'Platform Dot Snowflake': '// Platform Dot Snowflake\n// Coloured square before "Snowflake" on its button. Each platform has its own field so each gets its own run colour.\nIF [Platform Option] = "snowflake" THEN "■ " ELSE "" END',
    'Platform Dot Databricks': '// Platform Dot Databricks\n// Coloured square before "Databricks" on its button.\nIF [Platform Option] = "databricks" THEN "■ " ELSE "" END',
    'Platform Dot Redshift': '// Platform Dot Redshift\n// Coloured square before "Redshift" on its button.\nIF [Platform Option] = "redshift" THEN "■ " ELSE "" END',
    'Platform Option Order': '// Platform Option Order\n// Keeps the platform buttons in prototype order (All, Snowflake, Databricks, Redshift) instead of A to Z.\n[day_index]',
    'Is Info Button Row': '// Is Info Button Row\n// One scaffold row for the single-mark info button. Put on Filters (True).\n[day_index] = 0',
    'Info Button Glyph': '// Info Button Glyph\n// The header icon: "ⓘ" opens the info panel, "✕" closes it.\nIF [p_show_info] THEN "✕" ELSE "ⓘ" END',
    'Show Info Panel': '// Show Info Panel\n// DZV for GL Info Panel: shown while p_show_info is True.\n[p_show_info]',
    'Data Updated Date Text': '// Data Updated Date Text\n// The date part of the header stamp, shown bold after "Data updated on ".\nSTR(DAY({ MAX([date (dim_date.csv)]) })) + " "\n+ LEFT(DATENAME(\'month\', { MAX([date (dim_date.csv)]) }), 3) + " "\n+ STR(YEAR({ MAX([date (dim_date.csv)]) }))\n+ ", 23:59"',
}, types={
    'Has Prior Period': B_DIM, 'Period Option': I_DIM, 'Period Option Label': S_DIM, 'Is Active Period Option': B_DIM,
    'Platform Option': S_DIM, 'Platform Option Label': S_DIM, 'Is Active Platform Option': B_DIM,
    'Info Toggle Value': B_DIM, 'Period Hint Label': S_DIM, 'Data Updated Label': S_DIM, 'History Label': S_DIM,
    'Is Period Button Row': B_DIM, 'Period Label Active': S_DIM, 'Period Label Inactive': S_DIM,
    'Is Platform Button Row': B_DIM, 'Platform Label Active': S_DIM, 'Platform Label Inactive': S_DIM,
    'Platform Dot Snowflake': S_DIM, 'Platform Dot Databricks': S_DIM, 'Platform Dot Redshift': S_DIM,
    'Platform Option Order': I_DIM, 'Is Info Button Row': B_DIM, 'Info Button Glyph': S_DIM,
    'Show Info Panel': B_DIM, 'Data Updated Date Text': S_DIM,
})

# Full-width backgrounds: a bar from 0 to 1 on a fixed, hidden axis, with the text on a second axis.
# Square marks stay square, so they can't fill a rectangular button, row or tile.
CALCS.add(formulas={
    'Full Bar': '// Full Bar\n// Bar length for a full-width background (axis fixed 0 to 1 and hidden): buttons, alert rows.\nMIN(1.0)',
    'Text Anchor Centre': '// Text Anchor Centre\n// Where centred text sits on a full-width background bar.\nMIN(0.5)',
    'Text Anchor Left': '// Text Anchor Left\n// Where left-aligned text starts on a full-width background bar.\nMIN(0.03)',
}, types={'Full Bar': R_MEA, 'Text Anchor Centre': R_MEA, 'Text Anchor Left': R_MEA})


def segmented(name, order_field, option_field, active_field, act_label, inact_label, row_filter, extra_runs=()):
    """A segmented button sheet (build plan 2.4): the selected option is a white bar on the grey track,
    with the label as text on a second axis so it is never clipped by a mark."""
    color_map(R(active_field), {'true': CARD, 'false': CANVAS})
    texts = [R(n) for n, *_ in extra_runs] + [R(act_label), R(inact_label)]
    label = [run(R(n), size, col) for n, size, col in extra_runs] + [run(R(act_label), 9, NAVY, SEMI),
                                                                      run(R(inact_label), 9, INK2, BOOK)]
    lod = [R(option_field)] if option_field != order_field else []
    bar, anchor = R('Full Bar'), R('Text Anchor Centre')
    # As adjusted in Tableau on v08: the bar at full size fills the button, and the label rides on a clear,
    # hairline Gantt bar (a Text mark's own box would sit on top of the bar and shrink the white area)
    return Sheet(name, cols=[Cross([R(order_field), (bar, anchor)])], hide=[R(order_field), bar, anchor],
                 filters=[R(row_filter)], fixed={bar: (0, 1), anchor: (0, 1)}, tooltip=False,
                 panes=[Pane(),
                        Pane('Bar', axis=bar, color=R(active_field), lod=lod, size=1.9890055656433105, label_show=False),
                        button_label_pane(axis=anchor, text=texts, lod=lod, label=label, align='center')])


def gl_sheets() -> list[Sheet]:
    return [
        segmented('GL Period Buttons', 'Period Option', 'Period Option', 'Is Active Period Option',
                  'Period Label Active', 'Period Label Inactive', 'Is Period Button Row'),
        segmented('GL Platform Buttons', 'Platform Option Order', 'Platform Option', 'Is Active Platform Option',
                  'Platform Label Active', 'Platform Label Inactive', 'Is Platform Button Row',
                  extra_runs=[('Platform Dot Snowflake', 8, PLAT['snowflake']),
                              ('Platform Dot Databricks', 8, PLAT['databricks']),
                              ('Platform Dot Redshift', 8, PLAT['redshift'])]),
        Sheet('GL Period Hint', tooltip=False, panes=label_pane(text=[R('Period Hint Label')],
              label=[run(R('Period Hint Label'), 8, INK3, BOOK, italic='true')])),
        Sheet('GL Data Updated', tooltip=False, panes=label_pane(text=[R('Data Updated Date Text'), R('History Label')],
              align='right', label=[run('Data updated on ', 8, INK3), run(R('Data Updated Date Text'), 8, INK1, SEMI),
                                    run(NL, 8, INK3), run(R('History Label'), 8, INK3)])),
        Sheet('GL Nav Data Updated', tooltip=False, panes=label_pane(text=[R('Data Updated Date Text')], label=[
            run('Data updated on ', 8, INK3), run(R('Data Updated Date Text'), 8, INK1, SEMI)])),
        Sheet('GL Info Button', tooltip=False, filters=[R('Is Info Button Row')],
              panes=label_pane(text=[R('Info Button Glyph')], lod=[R('Info Toggle Value')], align='center',
                         label=[run(R('Info Button Glyph'), 12, INK2, BOOK)])),
    ]


SHELL_ACTIONS = [  # (sheet, source field, parameter, caption)
    ('GL Period Buttons', 'Period Option', 'p_period', 'GL Set Period'),
    ('GL Platform Buttons', 'Platform Option', 'p_platform', 'GL Set Platform'),
    ('GL Info Button', 'Info Toggle Value', 'p_show_info', 'GL Toggle Info'),
]

INFO_ROWS = {  # build plan 2.5: (bold lead, rest) x 4
    'HO': [('Read the cards left to right.', 'Run, test and freshness rates, data products at risk now, recovery time and cost. Bars show 90 days, with your period in blue.'),
           ('Each tile is a data product,', 'traced through every upstream step. Red means do not use, amber means use with caution.'),
           ('Click a tile', 'to open its lineage. Click an item under Needs attention to see who it affects.'),
           ('Period and Platform', 'at the top apply to every page.')],
    'RUN': [('The top chart', 'shows failed runs, and the runs skipped because something upstream failed. Dashed lines mark incidents.'),
            ('Click a day', 'to load its job timeline. Use ‹ › to step through days.'),
            ('Why runs failed', 'groups failures by error type, and lists the models that fail most.'),
            ('Click an error', 'to see what it affects downstream.')],
    'FR': [('Each bar', "is a source's lag since its last load. Green is on time, amber is past the warn threshold, red is past the error threshold."),
           ('The line chart', 'shows the share of hourly checks that passed each day, per platform.'),
           ('The calendar', 'counts late checks per day. Look for repeating weekdays.'),
           ('Late right now', 'lists the data products waiting on each late source.')],
    'LIN': [('Pick a data product', 'in the dropdown. The graph shows every upstream step, from raw sources on the left to the product on the right.'),
            ('Click a box', 'to see its owner, history and tests in the panel, and to highlight its path.'),
            ('Switch to Table', 'for a sortable list of every upstream node.'),
            ('Trace downstream impact', 'opens Blast radius for the selected node.')],
    'BR': [('Pick a node,', 'or click a row in Riskiest nodes.'),
           ('Who to tell', 'lists the data products it feeds, with owners and Slack channels.'),
           ('Riskiest nodes', 'ranks nodes by daily consumers downstream × failure rate.'),
           ('Email incident message', 'opens a ready-to-send message.')],
    'QA': [('The heatmap', 'shows the worst test result per model per day. Repeating columns point to a scheduled cause.'),
           ('Tests that keep failing', 'shows which weekdays failures land on.'),
           ('Coverage', 'shows the share of models with at least one test, by domain.'),
           ('Warnings', 'count as not passing in the pass rate.')],
    'PF': [('Cost', 'is estimated compute for dbt builds plus product queries, in USD.'),
           ('The runtime chart', 'highlights the model whose runtime changed most.'),
           ('"Make incremental"', 'flags full-refresh tables over 10M rows whose runtime grew more than 25%.'),
           ('Product cost', "splits each model's build cost evenly across the products it feeds.")],
    'US': [('Each dot', 'is a data product. Bottom right is expensive and little used: the candidates to retire.'),
           ('Each consumer type', "gets its own scale, because views, queries, sessions and agent calls aren't comparable."),
           ('The ranked table', 'compares use with the period before.'),
           ('Semantic layer refreshes', 'catch extracts that fail while dbt stays green.')],
    'GOV': [('Unregistered consumers', "read warehouse data but aren't declared as exposures, so nobody is told when it breaks."),
            ('AI-built sprawl', 'shows dashboards built with AI that overlap governed ones.'),
            ('Coverage cells', 'are green from 90% and amber from 70%.'),
            ('Gaps to close', 'are the quickest fixes for the next sprint.')],
    'AB': [('Start on Health overview.', ''),
           ('Click any tile', 'to see its lineage, then any node to see its history.'),
           ('Use Trace downstream impact', 'to see who to tell.'),
           ('The data is synthetic.', 'Acme Retail Co. is fictional.')],
    'DOC': [('This page is for developers.', 'It documents parameters, actions and build notes.'),
            ('Parameters', 'are global, so a selection on one page carries to the next.'),
            ('Every calc', 'has a comment header with its purpose.'),
            ('Rebuild', 'with tableau/tools/build_workbook.py.')],
}


def nav(prefix: str, active: str) -> Z:
    def item(tab):
        # one image button per page: icon + left-aligned Arial label baked in (Tableau centres button text)
        name, icon = tab[1], tab[4]
        state = 'on' if name == active else 'off'
        return Z('imgbutton', friendly=f'{prefix} Nav {name}', fixed=38, style={'margin-bottom': '4'},
                 button=dict(target=name, image=f'navbtn-{icon}-{state}.png'))

    def group(label):
        # 29px label + the 4px nav gap below it (prototype: Monitor at y 115, first item at y 148)
        return text([run(label.upper(), 7, INK4, SEMI)], fixed=33, **{'padding-top': '12', 'padding-left': '10'})

    kids = [
        Z('horz', friendly=f'{prefix} Nav Brand', fixed=78, kids=[
            Z('vert', fixed=44, kids=[Z('bitmap', fixed=34, image='brand-mark.png'), blank()],
              style={'padding-top': '13', 'padding-right': '10'}),
            text([run('Lineage Control Tower', 11, NAVY, BOLD), run(NL, 8, INK3),
                  run('Acme Retail Co. · Data Platform', 8, INK3)], **{'padding-top': '8'})]),
        blank(1, LINE_SOFT), blank(14)]
    for g in ('Monitor', 'Investigate', 'Optimise', 'Govern'):
        kids.append(group(g))
        kids += [item(t) for t in TABS if t[4] and t[2] == g]
    kids += [blank(), blank(1, LINE_SOFT), blank(12),
             sheet('GL Nav Data Updated', 20, **{'padding-left': '4'}),
             text([run('Refreshes hourly from dbt_ops', 8, INK3)], fixed=20, **{'padding-left': '8'}),
             text([run('●  Synthetic data, fictional company', 8, INK2)], fixed=26,
                  **{'padding-top': '6', 'padding-left': '8'})]
    return Z('vert', friendly=f'{prefix} Nav', fixed=231, kids=kids,
             style={'background-color': CARD, 'padding-top': '22', 'padding-right': '14',
                    'padding-bottom': '18', 'padding-left': '14'})


def header(tab) -> Z:
    p, name, group, q, _i = tab
    return Z('horz', friendly=f'{p} Header', fixed=69,
             style={'background-color': CARD, 'padding-left': '28', 'padding-right': '28'}, kids=[
        text([run(f'{group} / ', 8, INK3), run(name, 8, INK2, MEDIUM), run(NL, 8, INK3),
              run(name, 15, NAVY, SEMI), run('   ' + q, 11, INK3, BOOK)], **{'padding-top': '13'}),
        sheet('GL Data Updated', 220, **{'padding-top': '15'}),
        blank(16),
        Z('vert', friendly=f'{p} Info Button Holder', fixed=32, style={'padding-top': '18', 'padding-bottom': '18'}, kids=[
            sheet('GL Info Button', None, **{'border-color': LINE, 'border-style': 'solid', 'border-width': '1',
                                             'corner-radius': '8', 'background-color': CARD})]),
    ])


def track(friendly, sheet_name, width):
    return Z('horz', friendly=friendly, fixed=width, kids=[sheet(sheet_name)], style={
        'background-color': CANVAS, 'border-color': LINE, 'border-style': 'solid', 'border-width': '1',
        'corner-radius': '8', 'padding': '2', 'margin-top': '11', 'margin-bottom': '12'})


def filter_band(tab) -> Z:
    p = tab[0]
    label = lambda t, w: text([run(t, 7, INK3, SEMI)], fixed=w, **{'padding-top': '19'})
    return Z('horz', friendly=f'{p} Filter Band', fixed=51,
             style={'background-color': CARD, 'padding-left': '28', 'padding-right': '28'}, kids=[
        label('PERIOD', 51), track(f'{p} Period Track', 'GL Period Buttons', 265), blank(18),
        label('PLATFORM', 69), track(f'{p} Platform Track', 'GL Platform Buttons', 380), blank(18),
        # About and Documentation don't use them (build plan 3.10): the controls stay, the hint says so
        text([run('Period and Platform apply to every other page', 8, INK3, BOOK, italic='true')], **{'padding-top': '17'})
        if p in ('AB', 'DOC') else sheet('GL Period Hint', None, **{'padding-top': '4'})])


CONTENT_PAD = {'padding-top': '20', 'padding-right': '28', 'padding-bottom': '14', 'padding-left': '28'}
# content area under the header (69 + 1) and filter band (51 + 1): 1000 - 122 - 20 - 14 = 844 px high, 1312 wide.
# The bottom padding was the prototype's 22; GB asked for no unneeded space at the bottom (v25), so it matches the
# 14 px gap between cards.
CONTENT_H = 1000 - 122 - int(CONTENT_PAD['padding-top']) - int(CONTENT_PAD['padding-bottom'])


def content_placeholder(tab) -> Z:
    p, name = tab[0], tab[1]
    return Z('vert', friendly=f'{p} Content', style=CONTENT_PAD, kids=[
        text([run(f'{name}: content is built in a later step.', 9, INK4, BOOK, align=1)], **{'padding-top': '380'})])


def info_panel(tab) -> Z:
    p = tab[0]
    kids = [text([run('How to read this page', 10, INK1, SEMI)], fixed=30)]
    for i, (lead, rest) in enumerate(INFO_ROWS[p], 1):
        if i > 1:
            kids.append(Z('vert', fixed=13, kids=[blank(1, LINE_SOFT)], style={'padding-top': '6', 'padding-bottom': '6'}))
        kids.append(Z('horz', friendly=f'{p} Info Row {i}', fixed=70, kids=[
            text([run(str(i), 12, ACCENT, SEMI)], fixed=28),
            text([run(lead + ' ', 9, INK1, SEMI)] + ([run(rest, 9, INK2, BOOK)] if rest else []))]))
    kids += [blank(), text([run('Click ⓘ again to close.', 8, INK3, BOOK, italic='true')], fixed=22)]
    return Z('vert', friendly='GL Info Panel', kids=kids, dzv=('Show Info Panel', False), style={**CARD_STYLE, 'padding': '16'})
