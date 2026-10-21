"""Build the Lineage Control Tower dashboards into the workbook.

Reads the master .twb (the data source as you saved it in Tableau), adds parameters, calcs, the shared
GL sheets, actions and the dashboards, and writes a new .twb. It also packages a .twbx with the images.

    python tableau/tools/build_workbook.py \
        tableau/Lineage_Control_Tower_Project_Dashboard.twb \
        tableau/build/Lineage_Control_Tower.twb

The master file is never edited. Every new piece is written as text next to what Tableau wrote,
so the data source stays byte for byte as you saved it.

Sources of truth:
- calcs:   docs/tableau-calc-pack.md (parsed, comment headers kept); new calcs are in NEW_CALCS below
- layout:  docs/tableau-build-plan.md sections 2 and 3
- format:  docs/tableau-build-plan.md section 4
XML patterns were checked against a real Tableau 2026.1 workbook (nav buttons, images, DZV,
parameter actions).
"""

from __future__ import annotations

import hashlib
import re
import sys
import uuid
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / 'docs' / 'tableau-calc-pack.md'
PARAM_LISTS = ROOT / 'docs' / 'tableau-parameter-lists.md'
IMAGES = ROOT / 'tableau' / 'Image'

DS = 'federated.07vo3ft0hzn0yt1e7nb981upju80'
DS_CAPTION = 'Lineage Control Tower'
W, H = 1600, 1000

# ---------------------------------------------------------------- colour and type tokens (plan 4.1, 4.2)
NAVY, ACCENT, LIME = '#002c55', '#005fae', '#c7ffa4'
CANVAS, CARD, LINE, LINE_SOFT = '#f5f5f3', '#ffffff', '#e6e7e2', '#efefeb'
INK1, INK2, INK3, INK4 = '#16212e', '#4a5563', '#7a838e', '#a5acb4'
PLAT = {'snowflake': '#005fae', 'databricks': '#4baee3', 'redshift': '#5b5fc7'}
BOOK, MEDIUM, SEMI, BOLD = 'Tableau Book', 'Tableau Medium', 'Tableau Semibold', 'Tableau Bold'


def stable_id(text: str, digits: int = 19) -> str:
    """Deterministic number from a name, so rebuilds give the same internal ids."""
    return str(int(hashlib.md5(text.encode()).hexdigest(), 16))[:digits]


def stable_uuid(text: str) -> str:
    return '{' + str(uuid.UUID(hashlib.md5(text.encode()).hexdigest())).upper() + '}'


def stable_guid(text: str) -> str:
    return str(uuid.UUID(hashlib.md5(('g:' + text).encode()).hexdigest()))


def esc(s: str) -> str:
    """Attribute / text escaping as Tableau writes it."""
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
             .replace('"', '&quot;').replace("'", '&apos;'))


def esc_formula(s: str) -> str:
    return esc(s).replace('\n', '&#13;&#10;')


# ================================================================ parameters (calc pack section 1)

def _list_from_doc(heading: str) -> list[tuple[str, str]]:
    text = PARAM_LISTS.read_text()
    sec = text.split(f'## {heading}', 1)[1]
    block = sec.split('```', 2)[1]
    return [tuple(line.split('\t', 1)) for line in block.strip('\n').splitlines() if '\t' in line]


def parameters() -> list[dict]:
    exp = _list_from_doc('p_selected_exposure')
    node = _list_from_doc('p_selected_node')
    return [
        dict(name='p_period', datatype='integer', value='30', domain='list',
             members=[('7', 'Last 7 days'), ('30', 'Last 30 days'), ('90', 'Last 90 days')]),
        dict(name='p_platform', datatype='string', value='All', domain='list',
             members=[('All', 'All'), ('snowflake', 'Snowflake'), ('databricks', 'Databricks'),
                      ('redshift', 'Redshift')]),
        dict(name='p_selected_exposure', datatype='string',
             value='exposure.acme_core.executive_revenue_dashboard', domain='list', members=exp),
        dict(name='p_selected_node', datatype='string',
             value='model.acme_core.stg_netsuite__journal_lines', domain='list', members=node),
        dict(name='p_selected_node_key', datatype='integer', value='35', domain='any'),
        dict(name='p_gantt_date', datatype='date', value='2026-10-19', domain='any'),
        dict(name='p_show_info', datatype='boolean', value='false', domain='list',
             members=[('true', 'Show'), ('false', 'Hide')]),
        dict(name='p_tile_view', datatype='string', value='All', domain='list',
             members=[('All', 'All'), ('Needs attention', 'Needs attention')]),
        dict(name='p_lineage_view', datatype='string', value='Graph', domain='list',
             members=[('Graph', 'Graph'), ('Table', 'Table')]),
    ]


PARAMS = parameters()
PARAM_ID = {p['name']: f'[Parameter {i + 1}]' for i, p in enumerate(PARAMS)}


def _lit(p: dict, v: str) -> str:
    """Parameter value as a Tableau literal."""
    if p['datatype'] == 'string':
        return '"' + v + '"'
    if p['datatype'] == 'date':
        return '#' + v + '#'
    return v


def param_column(p: dict, ind: str = '      ') -> str:
    alias = dict(p.get('members', [])).get(p['value'])
    role, typ = ('measure', 'quantitative') if p['datatype'] in ('integer', 'real', 'date') else ('measure', 'nominal')
    attrs = (f"{'alias=' + chr(39) + esc(alias) + chr(39) + ' ' if alias else ''}caption='{p['name']}' "
             f"datatype='{p['datatype']}' datatype-customized='true' name='{PARAM_ID[p['name']]}' "
             f"param-domain-type='{p['domain']}' role='{role}' type='{typ}' value='{esc(_lit(p, p['value']))}'")
    out = [f"{ind}<column {attrs}>",
           f"{ind}  <calculation class='tableau' formula='{esc(_lit(p, p['value']))}' />"]
    if p.get('members'):
        out.append(f'{ind}  <aliases>')
        out += [f"{ind}    <alias key='{esc(_lit(p, v))}' value='{esc(a)}' />" for v, a in p['members']]
        out.append(f'{ind}  </aliases>')
        out.append(f'{ind}  <members>')
        out += [f"{ind}    <member alias='{esc(a)}' value='{esc(_lit(p, v))}' />" for v, a in p['members']]
        out.append(f'{ind}  </members>')
    out.append(f'{ind}</column>')
    return '\n'.join(out)


def parameters_datasource() -> str:
    body = '\n'.join(param_column(p) for p in PARAMS)
    return ("    <datasource hasconnection='false' inline='true' name='Parameters' version='18.1'>\n"
            "      <aliases enabled='yes' />\n" + body + '\n    </datasource>\n')


# ================================================================ calcs

def parse_pack() -> dict[str, str]:
    """Every calc in the pack: name -> full formula (comment header included)."""
    calcs = {}
    for block in re.findall(r'```\n(// .*?)```', PACK.read_text(), re.S):
        name = block.split('\n', 1)[0][3:].strip()
        calcs[name] = block.rstrip('\n')
    return calcs


# New calcs this build needs (plan 5.3). They go into the pack too.
NEW_CALCS = {
    'Is Period Button Row': '// Is Period Button Row\n// Keeps the 3 scaffold rows that carry a period button. Put on Filters (True).\nNOT ISNULL([Period Option])',
    'Period Label Active': '// Period Label Active\n// Button text when this button is the selected period (Semibold Navy run).\nIF [Is Active Period Option] THEN [Period Option Label] ELSE "" END',
    'Period Label Inactive': '// Period Label Inactive\n// Button text when this button is not selected (Book grey run).\nIF NOT [Is Active Period Option] THEN [Period Option Label] ELSE "" END',
    'Is Platform Button Row': '// Is Platform Button Row\n// Keeps the 4 scaffold rows that carry a platform button. Put on Filters (True).\nNOT ISNULL([Platform Option])',
    'Platform Label Active': '// Platform Label Active\n// Button text when this button is the selected platform (Semibold Navy run).\nIF [Is Active Platform Option] THEN [Platform Option Label] ELSE "" END',
    'Platform Label Inactive': '// Platform Label Inactive\n// Button text when this button is not selected (Book grey run).\nIF NOT [Is Active Platform Option] THEN [Platform Option Label] ELSE "" END',
    'Platform Dot Snowflake': '// Platform Dot Snowflake\n// Coloured square before "Snowflake" on its button. Each platform has its own field so each gets its own run colour.\nIF [Platform Option] = "snowflake" THEN "■  " ELSE "" END',
    'Platform Dot Databricks': '// Platform Dot Databricks\n// Coloured square before "Databricks" on its button.\nIF [Platform Option] = "databricks" THEN "■  " ELSE "" END',
    'Platform Dot Redshift': '// Platform Dot Redshift\n// Coloured square before "Redshift" on its button.\nIF [Platform Option] = "redshift" THEN "■  " ELSE "" END',
    'Platform Option Order': '// Platform Option Order\n// Keeps the platform buttons in prototype order (All, Snowflake, Databricks, Redshift) instead of A to Z.\n[day_index]',
    'Is Info Button Row': '// Is Info Button Row\n// One scaffold row for the single-mark info button. Put on Filters (True).\n[day_index] = 0',
    'Info Button Glyph': '// Info Button Glyph\n// The header icon: "ⓘ" opens the info panel, "✕" closes it.\nIF [p_show_info] THEN "✕" ELSE "ⓘ" END',
    'Show Info Panel': '// Show Info Panel\n// DZV for GL Info Panel: shown while p_show_info is True.\n[p_show_info]',
    'Data Updated Date Text': '// Data Updated Date Text\n// The date part of the header stamp, shown bold after "Data updated on ".\nSTR(DAY({ MAX([date (dim_date.csv)]) })) + " "\n+ LEFT(DATENAME(\'month\', { MAX([date (dim_date.csv)]) }), 3) + " "\n+ STR(YEAR({ MAX([date (dim_date.csv)]) }))\n+ ", 23:59"',
}

# datatype, role, type for every calc this build adds
CALC_TYPES = {
    'Has Prior Period': ('boolean', 'dimension', 'nominal'),
    'Period Option': ('integer', 'dimension', 'ordinal'),
    'Period Option Label': ('string', 'dimension', 'nominal'),
    'Is Active Period Option': ('boolean', 'dimension', 'nominal'),
    'Platform Option': ('string', 'dimension', 'nominal'),
    'Platform Option Label': ('string', 'dimension', 'nominal'),
    'Is Active Platform Option': ('boolean', 'dimension', 'nominal'),
    'Info Toggle Value': ('boolean', 'dimension', 'nominal'),
    'Period Hint Label': ('string', 'dimension', 'nominal'),
    'Data Updated Label': ('string', 'dimension', 'nominal'),
    'History Label': ('string', 'dimension', 'nominal'),
    'Is Period Button Row': ('boolean', 'dimension', 'nominal'),
    'Period Label Active': ('string', 'dimension', 'nominal'),
    'Period Label Inactive': ('string', 'dimension', 'nominal'),
    'Is Platform Button Row': ('boolean', 'dimension', 'nominal'),
    'Platform Label Active': ('string', 'dimension', 'nominal'),
    'Platform Label Inactive': ('string', 'dimension', 'nominal'),
    'Platform Dot Snowflake': ('string', 'dimension', 'nominal'),
    'Platform Dot Databricks': ('string', 'dimension', 'nominal'),
    'Platform Dot Redshift': ('string', 'dimension', 'nominal'),
    'Platform Option Order': ('integer', 'dimension', 'ordinal'),
    'Is Info Button Row': ('boolean', 'dimension', 'nominal'),
    'Info Button Glyph': ('string', 'dimension', 'nominal'),
    'Show Info Panel': ('boolean', 'dimension', 'nominal'),
    'Data Updated Date Text': ('string', 'dimension', 'nominal'),
}


class Calcs:
    def __init__(self):
        self.src = parse_pack()
        self.src.update(NEW_CALCS)
        self.cid = {n: f'Calculation_{stable_id(n)}' for n in self.src}

    def refs(self, name: str) -> tuple[set[str], set[str], set[str]]:
        """Calcs, parameters and base fields a calc reads (ignoring comment lines)."""
        body = '\n'.join(l for l in self.src[name].splitlines() if not l.lstrip().startswith('//'))
        calcs, params, fields = set(), set(), set()
        for tok in re.findall(r'\[([^\[\]]+)\]', body):
            if tok in self.src:
                calcs.add(tok)
            elif tok in PARAM_ID:
                params.add(tok)
            else:
                fields.add(tok)
        return calcs, params, fields

    def closure(self, names) -> tuple[list[str], set[str], set[str]]:
        seen, order, params, fields = set(), [], set(), set()

        def visit(n):
            if n in seen:
                return
            seen.add(n)
            c, p, f = self.refs(n)
            for d in sorted(c):
                visit(d)
            params.update(p)
            fields.update(f)
            order.append(n)
        for n in names:
            visit(n)
        return order, params, fields

    def formula(self, name: str) -> str:
        out = []
        for line in self.src[name].splitlines():
            if not line.lstrip().startswith('//'):
                line = re.sub(r'\[([^\[\]]+)\]', self._swap, line)
            out.append(line)
        return '\n'.join(out)

    def _swap(self, m):
        tok = m.group(1)
        if tok in self.src:
            return f'[{self.cid[tok]}]'
        if tok in PARAM_ID:
            return f'[Parameters].{PARAM_ID[tok]}'
        return m.group(0)

    def column(self, name: str, indent: str = '      ') -> str:
        dt, role, typ = CALC_TYPES[name]
        return (f"{indent}<column caption='{esc(name)}' datatype='{dt}' name='[{self.cid[name]}]' role='{role}' type='{typ}'>\n"
                f"{indent}  <calculation class='tableau' formula='{esc_formula(self.formula(name))}' />\n"
                f"{indent}</column>")


CALCS = Calcs()


# ================================================================ worksheets

def base_columns(twb: str) -> dict[str, str]:
    """Top-level field definitions Tableau wrote for the data source, by internal name."""
    return {m.group(1): m.group(0) for m in
            re.finditer(r"<column caption='[^']*' datatype='[a-z]+' (?:hidden='true' )?name='(\[[^']+\])'[^>]*/>", twb)}


class Sheet:
    """A worksheet built from a short spec. Fields are calc names; shelves hold column-instance ids."""

    def __init__(self, name, *, cols=(), rows=(), mark='Automatic', color=None, text=(), lod=(),
                 label=None, filters=(), cell_align='center', table_bg='#00000000', hide_headers=(),
                 size=None, tooltip=False):
        self.name, self.cols, self.rows, self.mark = name, list(cols), list(rows), mark
        self.color, self.text, self.lod, self.label = color, list(text), list(lod), label
        self.filters, self.cell_align, self.table_bg = list(filters), cell_align, table_bg
        self.hide_headers, self.size, self.tooltip = list(hide_headers), size, tooltip

    def fields(self):
        f = self.cols + self.rows + self.text + self.lod + self.filters + ([self.color] if self.color else [])
        return list(dict.fromkeys(f))

    @staticmethod
    def inst(name: str) -> str:
        dt, role, typ = CALC_TYPES[name]
        k = {'ordinal': 'ok', 'nominal': 'nk', 'quantitative': 'qk'}[typ]
        return f'[none:{CALCS.cid[name]}:{k}]'

    def ref(self, name: str) -> str:
        return f'[{DS}].{self.inst(name)}'

    def xml(self, bases: dict[str, str]) -> str:
        order, params, fields = CALCS.closure(self.fields())
        dep = []
        if params:
            dep.append("          <datasource-dependencies datasource='Parameters'>")
            dep += [param_column(p, '            ') for p in PARAMS if p['name'] in params]
            dep.append('          </datasource-dependencies>')
        dep.append(f"          <datasource-dependencies datasource='{DS}'>")
        dep += [CALCS.column(n, '            ') for n in order]
        dep += ['            ' + bases[f'[{f}]'] for f in sorted(fields) if f'[{f}]' in bases]
        for n in self.fields():
            dt, role, typ = CALC_TYPES[n]
            dep.append(f"            <column-instance column='[{CALCS.cid[n]}]' derivation='None' "
                       f"name='{self.inst(n)}' pivot='key' type='{typ}' />")
        dep.append('          </datasource-dependencies>')

        filt = []
        for n in self.filters:
            filt.append(f"          <filter class='categorical' column='{self.ref(n)}'>\n"
                        f"            <groupfilter function='member' level='{self.inst(n)}' member='true' "
                        f"user:ui-domain='database' user:ui-enumeration='inclusive' user:ui-marker='enumerate' />\n"
                        f"          </filter>")
        slices = ''
        if self.filters:
            slices = ('          <slices>\n' + ''.join(f'            <column>{self.ref(n)}</column>\n' for n in self.filters)
                      + '          </slices>\n')

        ds_list = f"            <datasource caption='{DS_CAPTION}' name='{DS}' />\n"
        if params:
            ds_list += "            <datasource name='Parameters' />\n"

        enc = []
        if self.color:
            enc.append(f"              <color column='{self.ref(self.color)}' />")
        enc += [f"              <lod column='{self.ref(n)}' />" for n in self.lod]
        enc += [f"              <text column='{self.ref(n)}' />" for n in self.text]

        label = ''
        if self.label:
            runs = []
            for r in self.label:
                attrs = ' '.join(f"{k}='{v}'" for k, v in r.items() if k != 't')
                runs.append(f"                <run {attrs}>{r['t']}</run>")
            label = ('            <customized-label>\n              <formatted-text>\n' + '\n'.join(runs)
                     + '\n              </formatted-text>\n            </customized-label>\n')

        mark_fmt = ["                <format attr='mark-labels-show' value='true' />",
                    "                <format attr='mark-labels-cull' value='false' />"]
        if self.size is not None:
            mark_fmt.append(f"                <format attr='size' value='{self.size}' />")

        head = ''
        if self.hide_headers:
            head = ("          <style-rule element='header'>\n"
                    + ''.join(f"            <format attr='display' field='{self.ref(n)}' scope='cols' value='false' />\n"
                              for n in self.hide_headers if n in self.cols)
                    + ''.join(f"            <format attr='display' field='{self.ref(n)}' scope='rows' value='false' />\n"
                              for n in self.hide_headers if n in self.rows)
                    + '          </style-rule>\n')

        return (f"    <worksheet name='{esc(self.name)}'>\n"
                "      <table>\n        <view>\n          <datasources>\n" + ds_list + '          </datasources>\n'
                + '\n'.join(dep) + '\n' + ('\n'.join(filt) + '\n' if filt else '') + slices
                + "          <aggregation value='true' />\n        </view>\n"
                "        <style>\n" + head
                + f"          <style-rule element='table'>\n            <format attr='background-color' value='{self.table_bg}' />\n          </style-rule>\n"
                "          <style-rule element='worksheet'>\n            <format attr='display-field-labels' scope='cols' value='false' />\n"
                "            <format attr='display-field-labels' scope='rows' value='false' />\n          </style-rule>\n"
                "        </style>\n"
                "        <panes>\n          <pane selection-relaxation-option='selection-relaxation-allow'>\n"
                "            <view>\n              <breakdown value='auto' />\n            </view>\n"
                f"            <mark class='{self.mark}' />\n"
                + ("            <mark-sizing mark-sizing-setting='marks-scaling-off' />\n" if self.size is not None else '')
                + "            <encodings>\n" + '\n'.join(enc) + '\n            </encodings>\n'
                + label
                + "            <style>\n              <style-rule element='cell'>\n"
                f"                <format attr='text-align' value='{self.cell_align}' />\n"
                "                <format attr='vertical-align' value='center' />\n              </style-rule>\n"
                "              <style-rule element='mark'>\n" + '\n'.join(mark_fmt) + '\n              </style-rule>\n'
                "            </style>\n          </pane>\n        </panes>\n"
                f"        <rows>{' / '.join(self.ref(n) for n in self.rows)}</rows>\n"
                f"        <cols>{' / '.join(self.ref(n) for n in self.cols)}</cols>\n"
                + ("" if self.tooltip else "        <tooltip-style tooltip-mode='none' />\n")
                + "      </table>\n"
                f"      <simple-id uuid='{stable_uuid('ws:' + self.name)}' />\n    </worksheet>\n")


def F(name):
    """A label run that inserts a calc's value."""
    return f'&lt;{Sheet.ref(Sheet, name)}&gt;'


NL = 'Æ&#10;'


def run(t, size=9, color=INK2, font=BOOK, align=None, **kw):
    """A formatted-text run. Plain text is escaped; field inserts and line breaks pass through."""
    if not (t.startswith('&lt;[') or set(t.split(NL)) == {''}):
        t = esc(t)
    r = {'fontcolor': color, 'fontname': font, 'fontsize': str(size), 't': t}
    if align is not None:
        r['fontalignment'] = str(align)
    r.update(kw)
    return r


def gl_sheets() -> list[Sheet]:
    return [
        Sheet('GL Period Buttons', cols=['Period Option'], mark='Square', color='Is Active Period Option',
              text=['Period Label Active', 'Period Label Inactive'], filters=['Is Period Button Row'],
              hide_headers=['Period Option'], size=4,
              label=[run(F('Period Label Active'), 9, NAVY, SEMI), run(F('Period Label Inactive'), 9, INK2, BOOK)]),
        Sheet('GL Platform Buttons', cols=['Platform Option Order'], lod=['Platform Option'], mark='Square',
              color='Is Active Platform Option',
              text=['Platform Dot Snowflake', 'Platform Dot Databricks', 'Platform Dot Redshift',
                    'Platform Label Active', 'Platform Label Inactive'],
              filters=['Is Platform Button Row'], hide_headers=['Platform Option Order'], size=4,
              label=[run(F('Platform Dot Snowflake'), 8, PLAT['snowflake']),
                     run(F('Platform Dot Databricks'), 8, PLAT['databricks']),
                     run(F('Platform Dot Redshift'), 8, PLAT['redshift']),
                     run(F('Platform Label Active'), 9, NAVY, SEMI), run(F('Platform Label Inactive'), 9, INK2, BOOK)]),
        Sheet('GL Period Hint', text=['Period Hint Label'], cell_align='left',
              label=[run(F('Period Hint Label'), 8, INK3, BOOK, italic='true')]),
        Sheet('GL Data Updated', text=['Data Updated Date Text', 'History Label'], cell_align='right',
              label=[run('Data updated on ', 8, INK3), run(F('Data Updated Date Text'), 8, INK1, SEMI),
                     run(NL, 8, INK3), run(F('History Label'), 8, INK3)]),
        Sheet('GL Info Button', text=['Info Button Glyph'], lod=['Info Toggle Value'], filters=['Is Info Button Row'],
              label=[run(F('Info Button Glyph'), 12, INK2, BOOK)]),
    ]


COLOR_MAPS = {  # calc -> {bucket: colour}; written to the data source style (plan 4.6)
    'Is Active Period Option': {'true': CARD, 'false': CANVAS},
    'Is Active Platform Option': {'true': CARD, 'false': CANVAS},
}


def datasource_style() -> str:
    rules = []
    for name, m in COLOR_MAPS.items():
        rules.append(f"          <encoding attr='color' field='{Sheet.inst(name)}' type='palette'>")
        for b, c in m.items():
            rules.append(f"            <map to='{c}'>\n              <bucket>{b}</bucket>\n            </map>")
        rules.append('          </encoding>')
    return ("      <style>\n        <style-rule element='mark'>\n" + '\n'.join(rules)
            + "\n        </style-rule>\n      </style>\n")


# ================================================================ dashboards: layout engine

class Z:
    """A dashboard zone. `fixed` is its size in px along the parent's direction (margins included)."""
    _next = 3

    def __init__(self, kind, name=None, *, fixed=None, kids=(), style=None, friendly=None, text=None,
                 image=None, button=None, dzv=None, weight=1.0):
        self.kind, self.name, self.fixed, self.kids = kind, name, fixed, list(kids)
        self.style, self.friendly, self.text, self.image = style or {}, friendly, text, image
        self.button, self.dzv, self.weight = button, dzv, weight
        self.id = Z._next
        Z._next += 1
        self.rect = (0, 0, 0, 0)

    # ---------- layout
    def layout(self, x, y, w, h):
        self.rect = (x, y, w, h)
        if self.kind == 'basic':
            for k in self.kids:
                k.layout(x, y, w, h)
            return
        if self.kind not in ('vert', 'horz'):
            return
        s = self.style
        m = lambda k: int(s.get(k, s.get('margin', 0)))
        p = lambda k: int(s.get(k, s.get('padding', 0)))
        bw = int(s.get('border-width', 0)) if s.get('border-style') == 'solid' else 0
        cx = x + m('margin-left') + bw + p('padding-left')
        cy = y + m('margin-top') + bw + p('padding-top')
        cw = w - m('margin-left') - m('margin-right') - 2 * bw - p('padding-left') - p('padding-right')
        ch = h - m('margin-top') - m('margin-bottom') - 2 * bw - p('padding-top') - p('padding-bottom')
        main = cw if self.kind == 'horz' else ch
        fixed = sum(k.fixed for k in self.kids if k.fixed is not None)
        flex = [k for k in self.kids if k.fixed is None]
        free = max(main - fixed, 0)
        tw = sum(k.weight for k in flex) or 1
        pos = cx if self.kind == 'horz' else cy
        for k in self.kids:
            size = k.fixed if k.fixed is not None else free * k.weight / tw
            if self.kind == 'horz':
                k.layout(pos, cy, size, ch)
            else:
                k.layout(cx, pos, cw, size)
            pos += size

    # ---------- xml
    def xml(self, ind: str, window_ids: dict[str, str]) -> str:
        x, y, w, h = self.rect
        a = {'h': round(h * 100000 / H), 'id': self.id, 'w': round(w * 100000 / W),
             'x': round(x * 100000 / W), 'y': round(y * 100000 / H)}
        if self.fixed is not None:
            a['fixed-size'] = int(self.fixed)
            a['is-fixed'] = 'true'
        if self.friendly:
            a['friendly-name'] = self.friendly
        if self.dzv and self.dzv[1] is False:
            a['hidden-by-user'] = 'true'
        inner = []
        if self.kind in ('vert', 'horz'):
            a['param'] = self.kind
            a['type-v2'] = 'layout-flow'
        elif self.kind == 'basic':
            a['type-v2'] = 'layout-basic'
        elif self.kind == 'empty':
            a['type-v2'] = 'empty'
        elif self.kind == 'text':
            a['type-v2'] = 'text'
            runs = []
            for r in self.text:
                at = ' '.join(f"{k}='{v}'" for k, v in r.items() if k != 't')
                runs.append(f"{ind}    <run {at}>{r['t']}</run>")
            inner.append(f"{ind}  <formatted-text>\n" + '\n'.join(runs) + f"\n{ind}  </formatted-text>")
        elif self.kind == 'bitmap':
            a['is-scaled'] = '1'
            a['param'] = f'Image/{self.image}'
            a['type-v2'] = 'bitmap'
        elif self.kind == 'button':
            a['type-v2'] = 'dashboard-object'
            b = self.button
            fmts = ''.join(f"{ind}      <format attr='{k}' value='{v}' />\n" for k, v in b['format'].items())
            inner.append(
                f"{ind}  <button action='tabdoc:goto-sheet window-id=&quot;{window_ids[b['target']]}&quot;' button-type='text'>\n"
                f"{ind}    <button-visual-state>\n{ind}      <caption>{esc(b['caption'])}</caption>\n"
                f"{ind}      <button-caption-font-style fontcolor='{b['color']}' fontname='{b['font']}' fontsize='{b['size']}' />\n"
                + fmts + f"{ind}    </button-visual-state>\n{ind}  </button>")
        elif self.kind == 'sheet':
            a['name'] = self.name
            a['show-title'] = 'false'
        order = ['fixed-size', 'friendly-name', 'h', 'hidden-by-user', 'id', 'is-fixed', 'is-scaled', 'name',
                 'param', 'show-title', 'type-v2', 'w', 'x', 'y']
        attrs = ' '.join(f"{k}='{esc(str(a[k]))}'" for k in order if k in a)
        kids = [k.xml(ind + '  ', window_ids) for k in self.kids]
        return (f"{ind}<zone {attrs}>\n" + ''.join(i + '\n' for i in inner) + ''.join(kids)
                + zone_style(self.style, ind + '  ') + f"{ind}</zone>\n")

    def walk(self):
        yield self
        for k in self.kids:
            yield from k.walk()


def zone_style(s: dict, ind: str) -> str:
    st = {'border-color': '#000000', 'border-style': 'none', 'border-width': '0', 'margin': '0'}
    st.update({k: v for k, v in s.items()})
    lines = []
    for k, v in st.items():
        if k == 'corner-radius':
            lines.append(f"{ind}  <_.fcp.DashboardRoundedCorners.true...format attr='corner-radius' value='{v}' />")
        else:
            lines.append(f"{ind}  <format attr='{k}' value='{v}' />")
    return f"{ind}<zone-style>\n" + '\n'.join(lines) + f"\n{ind}</zone-style>\n"


# ================================================================ the shell (plan section 2)

TABS = [  # prefix, dashboard name, group, question, nav icon (None = not in nav)
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

INFO_ROWS = {  # plan 2.5: (bold lead, rest) x 4
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

CARD_STYLE = {'background-color': CARD, 'border-color': LINE, 'border-style': 'solid', 'border-width': '1',
              'corner-radius': '10'}


def text(runs, fixed=None, **style):
    return Z('text', fixed=fixed, text=runs, style=style)


def blank(fixed=None, color=None, **style):
    st = dict(style)
    if color:
        st['background-color'] = color
    return Z('empty', fixed=fixed, style=st)


def sheet(name, fixed=None, **style):
    return Z('sheet', name, fixed=fixed, style=style)


def nav(prefix: str, active: str) -> Z:
    def item(tab):
        p, name, _g, _q, icon = tab
        on = name == active
        bg = LIME if on else CARD
        btn = Z('button', fixed=None, button=dict(
            target=name, caption=name, color=NAVY if on else INK2, font=SEMI if on else MEDIUM, size=9,
            format={'background-color': bg, 'border-style': 'none', 'text-align': 'left'}))
        return Z('horz', friendly=f'{prefix} Nav {name}', fixed=38, kids=[
            Z('bitmap', fixed=26, image=f"nav-{icon}-{'on' if on else 'off'}.png"), btn],
            style={'background-color': bg, 'corner-radius': '8', 'padding-left': '10', 'margin-bottom': '4'})

    def group(label):
        # 29px label + the 4px nav gap below it, as in the prototype (Monitor at y 115, first item at 148)
        return text([run(label.upper(), 7, INK4, SEMI)], fixed=33, **{'padding-top': '12', 'padding-left': '10'})

    kids = [
        Z('horz', friendly=f'{prefix} Nav Brand', fixed=78, kids=[
            Z('vert', fixed=44, kids=[Z('bitmap', fixed=34, image='brand-mark.png'), blank()],
              style={'padding-top': '13', 'padding-right': '10'}),
            text([run('Lineage Control Tower', 11, NAVY, BOLD), run(NL, 8, INK3),
                  run('Acme Retail Co. · Data Platform', 8, INK3)], **{'padding-top': '8'})]),
        blank(1, LINE_SOFT),
        blank(14),
    ]
    by = {}
    for t in TABS:
        if t[4]:
            by.setdefault(t[2], []).append(t)
    for g in ('Monitor', 'Investigate', 'Optimise', 'Govern'):
        kids.append(group(g))
        kids += [item(t) for t in by[g]]
    kids += [blank(), blank(1, LINE_SOFT),
             text([run('Refreshes hourly from dbt_ops', 8, INK3), run(NL + NL, 8, INK3),
                   run('●  Synthetic data, fictional company', 8, INK2)], fixed=64,
                  **{'padding-top': '14', 'padding-left': '8'})]
    return Z('vert', friendly=f'{prefix} Nav', fixed=231, kids=kids,
             style={'background-color': CARD, 'padding-top': '22', 'padding-right': '14',
                    'padding-bottom': '18', 'padding-left': '14'})


def header(tab) -> Z:
    p, name, group, q, _i = tab
    return Z('horz', friendly=f'{p} Header', fixed=69, style={'background-color': CARD, 'padding-left': '28', 'padding-right': '28'}, kids=[
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
    return Z('horz', friendly=f'{p} Filter Band', fixed=51, style={'background-color': CARD, 'padding-left': '28', 'padding-right': '28'}, kids=[
        label('PERIOD', 51), track(f'{p} Period Track', 'GL Period Buttons', 265), blank(18),
        label('PLATFORM', 69), track(f'{p} Platform Track', 'GL Platform Buttons', 302), blank(18),
        sheet('GL Period Hint', None, **{'padding-top': '4'}),
    ])


def content_placeholder(tab) -> Z:
    """Empty content area until the tab is built: one quiet line so the shell reads as intentional."""
    p, name = tab[0], tab[1]
    return Z('vert', friendly=f'{p} Content', kids=[
        text([run(f'{name}: content is built in the next step.', 9, INK4, BOOK, align=1)],
             **{'padding-top': '380'})],
        style={'padding-top': '20', 'padding-right': '28', 'padding-bottom': '22', 'padding-left': '28'})


def info_panel(tab) -> Z:
    p = tab[0]
    kids = [text([run('How to read this page', 10, INK1, SEMI)], fixed=30)]
    for i, (lead, rest) in enumerate(INFO_ROWS[p], 1):
        if i > 1:
            kids.append(Z('vert', fixed=13, kids=[blank(1, LINE_SOFT)], style={'padding-top': '6', 'padding-bottom': '6'}))
        kids.append(Z('horz', friendly=f'{p} Info Row {i}', fixed=70, kids=[
            text([run(str(i), 12, ACCENT, SEMI)], fixed=28),
            text([run(lead + ' ', 9, INK1, SEMI), run(rest, 9, INK2, BOOK)])]))
    kids += [blank(), text([run('Click ⓘ again to close.', 8, INK3, BOOK, italic='true')], fixed=22)]
    z = Z('vert', friendly='GL Info Panel', kids=kids, dzv=('Show Info Panel', False),
          style={**CARD_STYLE, 'padding': '16'})
    return z


def dashboard(tab, window_ids, content=None) -> tuple[str, list[str], list[tuple[int, str]]]:
    p, name = tab[0], tab[1]
    main = Z('vert', friendly=f'{p} Main', kids=[
        header(tab), blank(1, LINE), filter_band(tab), blank(1, LINE), content or content_placeholder(tab)])
    root_flow = Z('horz', friendly=f'{p} Root', kids=[nav(p, name), blank(1, LINE), main])
    root = Z('basic', kids=[root_flow])
    root.layout(0, 0, W, H)
    panel = info_panel(tab)
    panel.layout(1172, 130, 400, 420)
    zones = root.xml('        ', window_ids) + panel.xml('        ', window_ids)
    sheets = sorted({z.name for z in list(root.walk()) + list(panel.walk()) if z.kind == 'sheet'})
    dzv = [(z.id, z.dzv[0]) for z in list(root.walk()) + list(panel.walk()) if z.dzv]
    xml = (f"    <dashboard enable-sort-zone-taborder='true' name='{esc(name)}'>\n"
           "      <style>\n        <style-rule element='table'>\n"
           f"          <format attr='background-color' value='{CANVAS}' />\n        </style-rule>\n      </style>\n"
           f"      <size maxheight='{H}' maxwidth='{W}' minheight='{H}' minwidth='{W}' sizing-mode='fixed' />\n"
           "      <zones>\n" + zones + "      </zones>\n"
           f"      <simple-id uuid='{stable_uuid('db:' + name)}' />\n    </dashboard>\n")
    return xml, sheets, dzv


# ================================================================ actions, windows, datagraph

def actions(dash_sheets: dict[str, list[str]]) -> str:
    out = []
    targets = [('GL Period Buttons', 'Period Option', 'p_period', 'Set Period'),
               ('GL Platform Buttons', 'Platform Option', 'p_platform', 'Set Platform'),
               ('GL Info Button', 'Info Toggle Value', 'p_show_info', 'Toggle Info')]
    for dname, sheets in dash_sheets.items():
        for ws, field, param, cap in targets:
            if ws not in sheets:
                continue
            caption = f'GL {cap} ({dname})'
            out.append(
                f"    <edit-parameter-action caption='{esc(caption)}' name='[Action1_{hashlib.md5(caption.encode()).hexdigest().upper()}]'>\n"
                "      <activation type='on-select' />\n"
                f"      <source dashboard='{esc(dname)}' type='sheet' worksheet='{esc(ws)}' />\n"
                "      <agg-type type='attr' />\n      <clear-option type='do-nothing' value='s:LROOT:' />\n"
                f"      <params>\n        <param name='source-field' value='[{DS}].{Sheet.inst(field)}' />\n"
                f"        <param name='target-parameter' value='[Parameters].{PARAM_ID[param]}' />\n      </params>\n"
                "    </edit-parameter-action>\n")
    return '  <actions>\n' + ''.join(out) + '  </actions>\n'


WORKSHEET_CARDS = """      <cards>
        <edge name='left'>
          <strip size='160'>
            <card type='pages' />
            <card type='filters' />
            <card type='marks' />
          </strip>
        </edge>
        <edge name='top'>
          <strip size='2147483647'>
            <card type='columns' />
          </strip>
          <strip size='2147483647'>
            <card type='rows' />
          </strip>
          <strip size='31'>
            <card type='title' />
          </strip>
        </edge>
      </cards>
"""


def windows(dash_sheets, window_ids, all_sheets) -> str:
    out = ["  <windows source-height='30'>\n"]
    for i, (dname, sheets) in enumerate(dash_sheets.items()):
        vps = ''.join(f"        <viewpoint name='{esc(s)}'>\n          <zoom type='entire-view' />\n        </viewpoint>\n"
                      for s in sheets)
        out.append(f"    <window class='dashboard'{' maximized=' + chr(39) + 'true' + chr(39) if i == 0 else ''} name='{esc(dname)}'>\n"
                   f"      <viewpoints>\n{vps}      </viewpoints>\n      <active id='-1' />\n"
                   f"      <simple-id uuid='{window_ids[dname]}' />\n    </window>\n")
    for s in all_sheets:
        out.append(f"    <window class='worksheet' hidden='true' name='{esc(s)}'>\n" + WORKSHEET_CARDS
                   + f"      <simple-id uuid='{stable_uuid('win:' + s)}' />\n    </window>\n")
    out.append('  </windows>\n')
    return ''.join(out)


def datagraph(dzv_by_dash: dict[str, list[tuple[int, str]]]) -> str:
    nodes, edges, pairs = [], [], []
    sub = stable_guid('subgraph')
    field_nodes = {}
    for dname, items in dzv_by_dash.items():
        for zid, calc in items:
            if calc not in field_nodes:
                ng, ig, og = (stable_guid(f'f:{calc}:{k}') for k in 'nio')
                field_nodes[calc] = og
                nodes.append(f"        <single-value-field-node fieldname='[{DS}].[{CALCS.cid[calc]}]' "
                             f"fieldname-input-guid='{ig}' node-guid='{ng}' value-output-guid='{og}' />")
                pairs.append(ng)
            ng, vg = stable_guid(f'z:{dname}:{zid}:n'), stable_guid(f'z:{dname}:{zid}:v')
            nodes.append(f"        <dashboard-zone-visibility-node dashboard-identifier='{stable_uuid('db:' + dname)}' "
                         f"node-guid='{ng}' visibility-input-guid='{vg}' zone-id='{zid}' />")
            pairs.append(ng)
            edges.append(f"        <edge from='{field_nodes[calc]}' to='{vg}' />")
    return ("  <datagraph>\n    <graph>\n      <properties>\n"
            f"        <default-execution-subgraph-guid value='{sub}' />\n      </properties>\n"
            "      <node-execution-subgraphs>\n"
            + ''.join(f"        <pair execution-subgraph-guid='{sub}' node-guid='{n}' />\n" for n in pairs)
            + "      </node-execution-subgraphs>\n      <nodes>\n" + '\n'.join(nodes) + "\n      </nodes>\n"
            "      <edges>\n" + '\n'.join(edges) + "\n      </edges>\n      <pin-values />\n    </graph>\n  </datagraph>\n")


MANIFEST_FLAGS = ['AccessibleZoneTabOrder', 'BasicButtonObject', 'BasicButtonObjectTextSupport', 'DatagraphCoreV1',
                  'DatagraphNodeDashboardZoneVisibilityV1', 'DatagraphNodeSingleValueFieldV1', 'ParameterAction',
                  'ParameterActionClearSelection', 'WorksheetBackgroundTransparency', 'ZoneBackgroundTransparency',
                  'ZoneFriendlyName', 'ZoneVisibilityControl']


# ================================================================ assemble

def build(master: Path, out: Path) -> None:
    raw = master.read_bytes().decode('utf-8')
    crlf = '\r\n' in raw
    t = raw.replace('\r\n', '\n')
    assert "name='Parameters'" not in t, 'master already has parameters: build from the Tableau-saved master'

    # manifest flags
    flags = ''.join(f'    <{f} />\n' for f in MANIFEST_FLAGS if f'<{f} />' not in t)
    flags += '    <_.fcp.DashboardRoundedCorners.true...DashboardRoundedCorners />\n'
    t = t.replace('  </document-format-change-manifest>', flags + '  </document-format-change-manifest>', 1)

    # parameters datasource before the federated one
    t = t.replace('  <datasources>\n', '  <datasources>\n' + parameters_datasource(), 1)

    bases = base_columns(t)
    sheets = gl_sheets()
    needed, _p, _f = CALCS.closure(list(dict.fromkeys(n for s in sheets for n in s.fields()))
                                   + ['Show Info Panel', 'Info Toggle Value'])
    missing = [n for n in needed if n not in CALC_TYPES]
    assert not missing, f'add datatypes for: {missing}'
    calc_xml = '\n'.join(CALCS.column(n) for n in needed) + '\n'
    anchor = "      <layout dim-ordering='alphabetic'"
    assert t.count(anchor) == 1
    t = t.replace(anchor, calc_xml + anchor, 1)
    # colour maps: data source style goes after <layout />
    t = re.sub(r"(      <layout dim-ordering='alphabetic'[^>]*/>\n)", lambda m: m.group(1) + datasource_style(), t, count=1)

    # dashboards
    window_ids = {tab[1]: stable_uuid('win:' + tab[1]) for tab in TABS}
    dash_xml, dash_sheets, dzv = [], {}, {}
    for tab in TABS:
        x, s, d = dashboard(tab, window_ids)
        dash_xml.append(x)
        dash_sheets[tab[1]] = s
        dzv[tab[1]] = d

    ws_xml = ''.join(s.xml(bases) for s in sheets)
    all_sheet_names = [s.name for s in sheets]

    # replace worksheets (drops the empty default Sheet 1), add actions and dashboards
    t = re.sub(r'  <worksheets>.*?  </worksheets>\n',
               lambda m: actions(dash_sheets) + '  <worksheets>\n' + ws_xml + '  </worksheets>\n'
               + '  <dashboards>\n' + ''.join(dash_xml) + '  </dashboards>\n', t, count=1, flags=re.S)
    t = re.sub(r'  <windows source-height=.*?  </windows>\n',
               lambda m: windows(dash_sheets, window_ids, all_sheet_names), t, count=1, flags=re.S)
    t = re.sub(r'  <thumbnails>.*?  </thumbnails>\n', '', t, count=1, flags=re.S)
    t = t.replace('</workbook>', datagraph(dzv) + '</workbook>')

    ET.fromstring(t.encode('utf-8'))  # must parse
    check(t)
    if crlf:
        t = t.replace('\n', '\r\n')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(t.encode('utf-8'))
    # .twbx: the workbook plus the images it references
    twbx = out.with_suffix('.twbx')
    with zipfile.ZipFile(twbx, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(out, out.name)
        for img in sorted(IMAGES.glob('*.png')):
            z.write(img, f'Image/{img.name}')
    print(f'wrote {out} and {twbx}')


def check(t: str) -> None:
    """Cross-reference checks: zone ids, sheet names, nav targets, action sources, DZV zones."""
    root = ET.fromstring(t.encode('utf-8'))
    ws = {w.get('name') for w in root.iter('worksheet')}
    dbs = root.findall('./dashboards/dashboard')
    win = {w.get('name'): w.find('simple-id').get('uuid') for w in root.findall('./windows/window')}
    for db in dbs:
        ids = [z.get('id') for z in db.iter('zone')]
        assert len(ids) == len(set(ids)), f"{db.get('name')}: duplicate zone ids"
        for z in db.iter('zone'):
            if z.get('name') and not z.get('type-v2'):
                assert z.get('name') in ws, f"unknown sheet {z.get('name')}"
        for b in db.iter('button'):
            wid = re.search(r'window-id="([^"]+)"', b.get('action')).group(1)
            assert wid in win.values(), f'nav button to unknown window {wid}'
    names = {d.get('name') for d in dbs}
    for a in root.iter('edit-parameter-action'):
        src = a.find('source')
        assert src.get('dashboard') in names and src.get('worksheet') in ws
    all_zone_ids = {(d.find('simple-id').get('uuid'), z.get('id')) for d in dbs for z in d.iter('zone')}
    for n in root.iter('dashboard-zone-visibility-node'):
        assert (n.get('dashboard-identifier'), n.get('zone-id')) in all_zone_ids, 'DZV node points at no zone'
    # every calc reference in every formula resolves
    known = set(re.findall(r"name='(\[[^']+\])'", t))
    for f in re.findall(r"formula='([^']*)'", t):
        body = '\n'.join(l for l in f.replace('&#13;&#10;', '\n').splitlines() if not l.lstrip().startswith('//'))
        for ref in re.findall(r'\[Calculation_\d+\]', body):
            assert ref in known, f'unresolved {ref}'


if __name__ == '__main__':
    build(Path(sys.argv[1]), Path(sys.argv[2]))
