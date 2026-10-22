"""Core of the workbook builder: ids, escaping, parameters, calcs, worksheets, dashboard zones.

XML patterns were checked against real Tableau workbooks (2025.1 and 2026.1): parameters, calc columns,
column instances (none / usr / attr / sum), formula table calcs with ordering-field, dual axes
written as (A + B) with one pane per axis, fixed axis ranges as axis 'space' encodings, palette maps
in the data source style, nav buttons, images, DZV wiring and parameter actions.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACK = ROOT / 'docs' / 'tableau-calc-pack.md'
PARAM_LISTS = ROOT / 'docs' / 'tableau-parameter-lists.md'
IMAGES = ROOT / 'tableau' / 'Image'

DS = 'federated.07vo3ft0hzn0yt1e7nb981upju80'
DS_CAPTION = 'Lineage Control Tower'
W, H = 1600, 1000

# ---------------------------------------------------------------- tokens (build plan 4.1 and 4.2)
NAVY, ACCENT, LIME = '#002c55', '#005fae', '#c7ffa4'
ACCENT_TINT, ACCENT_MID = '#e9f1f9', '#a9c8e6'
CANVAS, CARD, LINE, LINE_SOFT = '#f5f5f3', '#ffffff', '#e6e7e2', '#efefeb'
INK1, INK2, INK3, INK4 = '#16212e', '#4a5563', '#7a838e', '#a5acb4'
OUT_OF_WINDOW = '#d9dcd7'
GOOD, WARN, CRIT, NONE = '#2f9e6b', '#e8a33d', '#d2453f', '#a3adb8'
GOOD_INK, WARN_INK, CRIT_INK = '#1e7450', '#93600f', '#a92e29'
GOOD_TINT, WARN_TINT, CRIT_TINT, NONE_TINT = '#eaf6ef', '#fdf3e1', '#fbeae9', '#f1f2f4'
AI_INK = '#3d41a0'
PLAT = {'snowflake': '#005fae', 'databricks': '#4baee3', 'redshift': '#5b5fc7'}
# Arial family only (Gbolahan, 21 Oct): regular weight for text, bold for titles, BANs and emphasis.
# SEMI and BOLD are markers that run() and the button writer turn into Arial + bold='true'.
FONT = 'Arial'
BOOK = MEDIUM = FONT
SEMI = BOLD = 'Arial|bold'

FMT_PCT2 = 'p0.00%'
FMT_USD = 'c"$"#,##0;-"$"#,##0'
FMT_INT = 'n#,##0;-#,##0'


def stable_id(text: str, digits: int = 19) -> str:
    """Deterministic number from a name, so rebuilds give the same internal ids."""
    return str(int(hashlib.md5(text.encode()).hexdigest(), 16))[:digits]


def stable_uuid(text: str) -> str:
    return '{' + str(uuid.UUID(hashlib.md5(text.encode()).hexdigest())).upper() + '}'


def stable_guid(text: str) -> str:
    return str(uuid.UUID(hashlib.md5(('g:' + text).encode()).hexdigest()))


def esc(s: str) -> str:
    """Attribute and text escaping as Tableau writes it."""
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
             .replace('"', '&quot;').replace("'", '&apos;'))


def esc_formula(s: str) -> str:
    return esc(s).replace('\n', '&#13;&#10;')


# ================================================================ parameters (calc pack section 1)

def _list_from_doc(heading: str) -> list[tuple[str, str]]:
    sec = PARAM_LISTS.read_text().split(f'## {heading}', 1)[1]
    block = sec.split('```', 2)[1]
    return [tuple(line.split('\t', 1)) for line in block.strip('\n').splitlines() if '\t' in line]


PARAMS = [
    dict(name='p_period', datatype='integer', value='30', domain='list',
         members=[('7', 'Last 7 days'), ('30', 'Last 30 days'), ('90', 'Last 90 days')]),
    dict(name='p_platform', datatype='string', value='All', domain='list',
         members=[('All', 'All'), ('snowflake', 'Snowflake'), ('databricks', 'Databricks'), ('redshift', 'Redshift')]),
    dict(name='p_selected_exposure', datatype='string', value='exposure.acme_core.executive_revenue_dashboard',
         domain='list', members=_list_from_doc('p_selected_exposure')),
    # "" is the cleared state: a Health tile writes it so Lineage opens on the exposure itself
    dict(name='p_selected_node', datatype='string', value='model.acme_core.stg_netsuite__journal_lines',
         domain='list', members=[('', 'None selected')] + _list_from_doc('p_selected_node')),
    dict(name='p_selected_node_key', datatype='integer', value='35', domain='any'),
    dict(name='p_gantt_date', datatype='date', value='2026-10-19', domain='any'),
    dict(name='p_show_info', datatype='boolean', value='false', domain='list',
         members=[('true', 'Show'), ('false', 'Hide')]),
    dict(name='p_tile_view', datatype='string', value='All', domain='list',
         members=[('All', 'All'), ('Needs attention', 'Needs attention')]),
    dict(name='p_lineage_view', datatype='string', value='Graph', domain='list',
         members=[('Graph', 'Graph'), ('Table', 'Table')]),
    # The Lineage panel's pills, callout and sections are shown by dynamic zone visibility. A DZV calc that reads the
    # data kept its first value (v16, v17), while parameter-only calcs update at once, so every click that picks a
    # node also writes its status, type, platform and tags here (defaults: stg_netsuite__journal_lines).
    dict(name='p_panel_status', datatype='integer', value='3', domain='any'),
    dict(name='p_panel_type', datatype='string', value='model', domain='any'),
    dict(name='p_panel_platform', datatype='string', value='snowflake', domain='any'),
    dict(name='p_panel_tags', datatype='string', value='|', domain='any'),
    # Run & failures: the Gantt day as days before the as-of date + 0.5, the position of its bar on the daily
    # chart's axis (the dashed selected-day line reads it). Written with p_gantt_date by every day click.
    dict(name='p_gantt_back', datatype='real', value='0.5', domain='any'),
]
PARAM_ID = {p['name']: f'[Parameter {i + 1}]' for i, p in enumerate(PARAMS)}
PARAM_BY = {p['name']: p for p in PARAMS}
# What each node-picking click writes into the p_panel_* parameters (field -> parameter). Every clickable layer
# carries these fields on Detail so the parameter action has a value to send.
PANEL_WRITES = [('current_status_code', 'p_panel_status'), ('resource_type', 'p_panel_type'),
                ('platform_now', 'p_panel_platform'), ('Panel Tags Value', 'p_panel_tags')]


def _lit(p: dict, v: str) -> str:
    if p['datatype'] == 'string':
        return '"' + v + '"'
    if p['datatype'] == 'date':
        return '#' + v + '#'
    return v


def param_column(p: dict, ind: str = '      ') -> str:
    alias = dict(p.get('members', [])).get(p['value'])
    typ = 'quantitative' if p['datatype'] in ('integer', 'real', 'date') else 'nominal'
    attrs = ((f"alias='{esc(alias)}' " if alias else '')
             + f"caption='{p['name']}' datatype='{p['datatype']}' datatype-customized='true' "
             f"name='{PARAM_ID[p['name']]}' param-domain-type='{p['domain']}' role='measure' type='{typ}' "
             f"value='{esc(_lit(p, p['value']))}'")
    out = [f"{ind}<column {attrs}>", f"{ind}  <calculation class='tableau' formula='{esc(_lit(p, p['value']))}' />"]
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
    return ("    <datasource hasconnection='false' inline='true' name='Parameters' version='18.1'>\n"
            "      <aliases enabled='yes' />\n" + '\n'.join(param_column(p) for p in PARAMS) + '\n    </datasource>\n')


# ================================================================ calcs

def parse_pack() -> dict[str, str]:
    """Every calc in the pack: name -> full formula (comment header included)."""
    calcs = {}
    for block in re.findall(r'```\n(// .*?)```', PACK.read_text(), re.S):
        name = block.split('\n', 1)[0][3:].strip()
        calcs[name] = block.rstrip('\n')
    return calcs


class Calcs:
    """Calc registry. Tabs register new calcs, datatypes and table-calc addressing here."""

    def __init__(self):
        self.src = parse_pack()
        self.types: dict[str, tuple[str, str, str]] = {}
        self.table_calc: dict[str, str] = {}  # calc -> name of the field it computes along

    def add(self, formulas: dict[str, str] | None = None, types: dict | None = None, table_calc: dict | None = None):
        self.src.update(formulas or {})
        self.types.update(types or {})
        self.table_calc.update(table_calc or {})

    def cid(self, n: str) -> str:
        return f'Calculation_{stable_id(n)}'

    def refs(self, name: str):
        """Calcs, parameters and base fields a calc reads (comment lines ignored)."""
        body = '\n'.join(l for l in self.src[name].splitlines() if not l.lstrip().startswith('//'))
        calcs, params, fields = set(), set(), set()
        for tok in re.findall(r'\[([^\[\]]+)\]', body):
            (calcs if tok in self.src else params if tok in PARAM_ID else fields).add(tok)
        return calcs, params, fields

    def closure(self, names):
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
        def swap(m):
            tok = m.group(1)
            if tok in self.src:
                return f'[{self.cid(tok)}]'
            if tok in PARAM_ID:
                return f'[Parameters].{PARAM_ID[tok]}'
            return m.group(0)
        return '\n'.join(l if l.lstrip().startswith('//') else re.sub(r'\[([^\[\]]+)\]', swap, l)
                         for l in self.src[name].splitlines())

    def tc_xml(self, name: str) -> str:
        along = self.table_calc.get(name)
        if not along:
            return ''
        col = f'[{self.cid(along)}]' if along in self.src else f'[{along}]'
        return f"<table-calc ordering-field='[{DS}].{col}' ordering-type='Field' />"

    def column(self, name: str, ind: str = '      ') -> str:
        if name not in self.types:
            raise KeyError(f'no datatype registered for calc {name!r}')
        dt, role, typ = self.types[name]
        tc = self.tc_xml(name)
        calc = (f"{ind}  <calculation class='tableau' formula='{esc_formula(self.formula(name))}'"
                + (f">\n{ind}    {tc}\n{ind}  </calculation>" if tc else ' />'))
        return (f"{ind}<column caption='{esc(name)}' datatype='{dt}' name='[{self.cid(name)}]' role='{role}' type='{typ}'>\n"
                f"{calc}\n{ind}</column>")


CALCS = Calcs()

# Shorthands for type registration
S_DIM = ('string', 'dimension', 'nominal')
B_DIM = ('boolean', 'dimension', 'nominal')
I_DIM = ('integer', 'dimension', 'ordinal')
R_MEA = ('real', 'measure', 'quantitative')
I_MEA = ('integer', 'measure', 'quantitative')
S_MEA = ('string', 'measure', 'nominal')
SP_MEA = ('spatial', 'measure', 'nominal')  # MAKEPOINT calcs, used as COLLECT on a map layer


# ================================================================ field references

BASES: dict[str, dict] = {}  # internal name -> {datatype, role, type, xml}


def load_bases(twb: str) -> None:
    """Field definitions by internal name. Top-level <column> elements first; fields Tableau only lists in
    metadata-records (the spatial Exposure Tiles table) get a definition built from their local type."""
    for m in re.finditer(r"<metadata-record class='column'>(.*?)</metadata-record>", twb, re.S):
        body = m.group(1)
        name = re.search(r'<local-name>\[(.*?)\]</local-name>', body)
        lt = re.search(r'<local-type>(\w+)</local-type>', body)
        if not (name and lt):
            continue
        dt = lt.group(1)
        role, typ = (('dimension', 'nominal') if dt in ('string', 'boolean') else ('dimension', 'ordinal') if dt in ('date', 'datetime')
                     else ('measure', 'quantitative'))
        BASES.setdefault(name.group(1), dict(datatype=dt, role=role, type=typ,
                                             xml=f"<column datatype='{dt}' name='[{esc(name.group(1))}]' role='{role}' type='{typ}' />"))
    for m in re.finditer(r"<column caption='[^']*' datatype='([a-z]+)' (?:hidden='true' )?name='\[([^']+)\]' "
                         r"role='([a-z]+)' type='([a-z]+)'[^>]*/>", twb):
        BASES[m.group(2)] = dict(datatype=m.group(1), role=m.group(3), type=m.group(4), xml=m.group(0))  # top-level wins


SUFFIX_TYPE = {'ok': 'ordinal', 'nk': 'nominal', 'qk': 'quantitative'}
DERIV = {'clct': 'Collect', 'none': 'None', 'usr': 'User', 'attr': 'Attribute', 'sum': 'Sum', 'min': 'Min', 'max': 'Max', 'avg': 'Avg'}


class Ref:
    """A field as used on a sheet. `name` is a calc name or a base field's internal name.

    agg:  None (dimension, or a calc measure which becomes usr:), 'attr', 'sum', 'min', 'max', 'avg'
    kind: force the suffix: 'ok' discrete ordinal, 'nk' discrete nominal, 'qk' continuous
    """

    def __init__(self, name: str, agg: str | None = None, kind: str | None = None):
        self.name, self.agg, self.kind = name, agg, kind
        self.tc_order: list | None = None  # set by a sheet: addressing fields (first one is the level)
        self.is_calc = name in CALCS.src
        if self.is_calc:
            self.dt, self.role, self.typ = CALCS.types[name]
            self.col = CALCS.cid(name)
        else:
            b = BASES[name]
            self.dt, self.role, self.typ = b['datatype'], b['role'], b['type']
            self.col = name

    @property
    def prefix(self) -> str:
        if self.agg:
            return self.agg
        return 'usr' if (self.is_calc and self.role == 'measure') else 'none'

    @property
    def suffix(self) -> str:
        if self.kind:
            return self.kind
        if self.prefix in ('sum', 'min', 'max', 'avg'):
            return 'qk'
        if self.prefix == 'clct':
            return 'nk'
        if self.prefix == 'attr':
            return 'nk' if self.dt in ('string', 'boolean') else 'qk'
        if self.prefix == 'usr':
            return 'nk' if self.dt in ('string', 'boolean') else 'qk'
        return {'ordinal': 'ok', 'nominal': 'nk', 'quantitative': 'qk'}[self.typ]

    @property
    def inst(self) -> str:
        return f'[{self.prefix}:{self.col}:{self.suffix}]'

    @property
    def ref(self) -> str:
        return f'[{DS}].{self.inst}'

    def instance_xml(self, ind: str) -> str:
        tc = CALCS.tc_xml(self.name) if self.is_calc else ''
        if self.tc_order:
            cols = [f'[{DS}].[{r.col}]' for r in self.tc_order]
            tc = (f"<table-calc level-address='{cols[0]}' ordering-type='Field'>\n"
                  + ''.join(f"{ind}    <order field='{c}' />\n" for c in dict.fromkeys(cols)) + f"{ind}  </table-calc>")
        head = (f"{ind}<column-instance column='[{self.col}]' derivation='{DERIV[self.prefix]}' "
                f"name='{self.inst}' pivot='key' type='{SUFFIX_TYPE[self.suffix]}'")
        return head + (f">\n{ind}  {tc}\n{ind}</column-instance>" if tc else ' />')

    def __repr__(self):
        return self.inst


class Raw:
    """A shelf entry Tableau generates itself (map Latitude / Longitude). Not declared in dependencies."""
    def __init__(self, name):
        self.name, self.ref, self.inst = name, f'[{DS}].[{name}]', f'[{name}]'


LAT, LON = Raw('Latitude (generated)'), Raw('Longitude (generated)')


def R(name, agg=None, kind=None) -> Ref:
    return Ref(name, agg, kind)


NL = 'Æ&#10;'


def run(t, size=9, color=INK2, font=BOOK, align=None, **kw) -> dict:
    """A formatted-text run. Plain text is escaped; field inserts and line breaks pass through."""
    ref = None
    if isinstance(t, Ref):
        ref, t = t, f'&lt;{t.ref}&gt;'
    elif not (t.startswith('&lt;[') or set(t.split(NL)) == {''}):
        t = esc(t)
        if t[:1].isspace():
            # Tableau trims a run that starts with whitespace unless it is marked literal with a leading Æ
            # (as Tableau itself writes "Æ " for a plain space between two fields)
            t = 'Æ' + t
    bold = font.endswith('|bold')
    r = {'fontcolor': color, 'fontname': font.split('|')[0], 'fontsize': str(size), 't': t}
    if bold:
        r['bold'] = 'true'
    if align is not None:
        r['fontalignment'] = str(align)
    r.update(kw)
    if ref is not None:
        r['_ref'] = ref
    return r


def runs_xml(runs, ind) -> str:
    out = []
    for r in runs:
        at = ' '.join(f"{k}='{v}'" for k, v in r.items() if k != 't' and not k.startswith('_'))
        out.append(f"{ind}<run {at}>{r['t']}</run>")
    return '\n'.join(out)


# ================================================================ worksheets

class Pane:
    def __init__(self, mark='Automatic', *, color=None, text=(), lod=(), tooltip_fields=(), label=None,
                 tooltip=None, size=None, axis=None, align='left', valign='center', label_show=True, mark_color=None,
                 geometry=None, stroke=None, title=None, inert=False, path=None, cell_style=True,
                 transparency=None, pane_size=None, shape=None, shape_field=None, size_field=None, reflines=()):
        self.mark, self.color, self.text, self.lod = mark, color, list(text), list(lod)
        self.tooltip_fields, self.label, self.tooltip = list(tooltip_fields), label, tooltip
        self.size, self.axis, self.align, self.valign, self.label_show = size, axis, align, valign, label_show
        self.mark_color, self.geometry = mark_color, geometry  # geometry: name of a spatial base field
        self.stroke = stroke  # mark border colour (has-stroke + stroke-color, as Tableau writes it)
        self.title, self.inert, self.path = title, inert, path  # map layer name, no interaction, polygon path
        self.transparency = transparency  # mark-transparency 0 (clear) to 255 (solid)
        self.pane_size = pane_size        # (w, h) px: a fixed map pane size, as a Tableau-saved reference writes it
        self.shape, self.shape_field = shape, shape_field  # a fixed custom shape, or a field mapped to shapes
        self.size_field = size_field      # a constant measure on Size, so big shapes are allowed (OKRs reference)
        # reference lines, as Tableau writes them inside the pane (IronViz reference): dicts with id, axis (Ref),
        # param (a parameter name: the line follows it) and z (z-order). Their look goes in the sheet's refline rule.
        self.reflines = list(reflines)

    def refs(self):
        return ([self.color] if self.color else []) + self.text + self.lod + self.tooltip_fields + ([self.path] if self.path else []) \
            + [r for r in (self.shape_field, self.size_field) if r is not None]

    def run_refs(self):
        return [r['_ref'] for r in (self.label or []) + (self.tooltip or []) if '_ref' in r]

    def xml(self, pid=None, axis_attr='') -> str:
        ident = '' if pid is None else f"id='{pid}' "
        ax = f" {axis_attr}='{self.axis.ref}'" if self.axis is not None else ''
        enc = []
        if self.color:
            enc.append(f"              <color column='{self.color.ref}' />")
        if self.size_field is not None:
            enc.append(f"              <size column='{self.size_field.ref}' />")
        if self.shape_field is not None:
            enc.append(f"              <shape column='{self.shape_field.ref}' />")
        enc += [f"              <lod column='{r.ref}' />" for r in self.lod]
        enc += [f"              <text column='{r.ref}' />" for r in self.text]
        enc += [f"              <tooltip column='{r.ref}' />" for r in self.tooltip_fields]
        if self.geometry:
            enc.append(f"              <geometry column='[{DS}].[{self.geometry}]' />")
        if self.path:
            enc.append(f"              <path column='{self.path.ref}' />")
        refl = ''.join(
            f"            <reference-line axis-column='{rl['axis'].ref}' enable-instant-analytics='false' formula='constant' "
            f"id='{rl['id']}' label-type='none' scope='per-table' value-column='[Parameters].{PARAM_ID[rl['param']]}' "
            f"z-order='{rl.get('z', 1)}' />\n" for rl in self.reflines)
        tip = ('            <customized-tooltip>\n              <formatted-text>\n' + runs_xml(self.tooltip, '                ')
               + '\n              </formatted-text>\n            </customized-tooltip>\n') if self.tooltip else ''
        lab = ('            <customized-label>\n              <formatted-text>\n' + runs_xml(self.label, '                ')
               + '\n              </formatted-text>\n            </customized-label>\n') if self.label else ''
        mark_fmt = [f"                <format attr='mark-labels-show' value='{'true' if self.label_show and self.label else 'false'}' />",
                    "                <format attr='mark-labels-cull' value='false' />"]
        if self.size is not None:
            mark_fmt.append(f"                <format attr='size' value='{self.size}' />")
        if self.mark_color:
            mark_fmt.append(f"                <format attr='mark-color' value='{self.mark_color}' />")
        if self.shape:
            mark_fmt.append(f"                <format attr='shape' value='{esc(self.shape)}' />")
        if self.transparency is not None:
            mark_fmt.append(f"                <format attr='mark-transparency' value='{self.transparency}' />")
        if self.stroke:
            mark_fmt.append("                <format attr='has-stroke' value='true' />")
            mark_fmt.append(f"                <format attr='stroke-color' value='{self.stroke}' />")
        lay = (f"generated-title='{esc(self.title)}' " if self.title else '') + ident + ("inert='true' " if self.inert else '')
        return (f"          <pane {lay}selection-relaxation-option='selection-relaxation-allow'{ax}>\n"
                "            <view>\n              <breakdown value='auto' />\n            </view>\n"
                f"            <mark class='{self.mark}' />\n"
                + ("            <mark-sizing mark-sizing-setting='marks-scaling-off' />\n" if self.size is not None else '')
                + ("            <encodings>\n" + '\n'.join(enc) + '\n            </encodings>\n' if enc else '')
                + refl + tip + lab
                + "            <style>\n              <style-rule element='cell'>\n"
                f"                <format attr='text-align' value='{self.align}' />\n"
                f"                <format attr='vertical-align' value='{self.valign}' />\n              </style-rule>\n"
                "              <style-rule element='label'>\n"
                f"                <format attr='text-align' value='{self.align}' />\n"
                f"                <format attr='vertical-align' value='{self.valign}' />\n              </style-rule>\n"
                "              <style-rule element='mark'>\n" + '\n'.join(mark_fmt) + '\n              </style-rule>\n'
                + self._pane_rule() + "            </style>\n          </pane>\n")

    def _pane_rule(self) -> str:
        if not self.pane_size:
            return ''
        w, h = self.pane_size
        return ("              <style-rule element='pane'>\n"
                f"                <format attr='minwidth' value='{w}' />\n                <format attr='maxwidth' value='{w}' />\n"
                f"                <format attr='minheight' value='{h}' />\n                <format attr='maxheight' value='{h}' />\n"
                "                <format attr='aspect' value='0' />\n              </style-rule>\n")


HAIRLINE = 0.0099999997764825821  # the thinnest mark size Tableau stores


def label_pane(**kw) -> 'Pane':
    """A mark that only carries a label: a hairline Gantt bar, white at transparency 0 (GB's standard for every
    label-only mark, as set in Tableau on the v08 buttons). Label alignment places the label beside the mark."""
    return Pane('GanttBar', size=HAIRLINE, mark_color='#ffffff', transparency=0, **kw)


class Cross(list):
    """Fields crossed on one shelf, written (a * b * c): a grid of map panes is (row index * Latitude)."""


class Nest(list):
    """Fields nested on one shelf, written (a / b), the way Tableau re-saves a nested group inside a Cross."""


def shelf_item(it) -> str:
    """One shelf entry; a tuple is a dual axis (a + b). Entries can sit inside each other."""
    if isinstance(it, Cross):
        return '(' + ' * '.join(shelf_item(x) for x in it) + ')'
    if isinstance(it, Nest):
        return '(' + ' / '.join(shelf_item(x) for x in it) + ')'
    if isinstance(it, tuple):
        return '(' + ' + '.join(shelf_item(x) for x in it) + ')'
    return it.ref


def shelf(items) -> str:
    return ' / '.join(shelf_item(it) for it in items)


def shelf_flat(items) -> list:
    out = []
    for it in items:
        out += shelf_flat(it) if isinstance(it, (tuple, Cross, Nest)) else [it]
    return out


def has_dual(items) -> bool:
    return any(isinstance(it, tuple) or (isinstance(it, (Cross, Nest)) and has_dual(it)) for it in items)


class Sheet:
    """A worksheet built from a short spec.

    rows / cols: lists of Ref, or a tuple of Refs for a dual axis.
    panes: one Pane, or a list (the first is the 'all' pane; then one per measure on a dual axis).
    filters: boolean calcs kept at True.
    formats: {Ref: Tableau number format}
    hide: Refs whose axis or header is hidden. fixed: {Ref: (min, max)} axis ranges.
    """

    def __init__(self, name, *, rows=(), cols=(), panes=None, filters=(), formats=None, hide=(), fixed=None,
                 header_font=None, header_width=None, row_height=None, divider=False, tooltip=True, zoom='entire-view',
                 sync=(), map_washout=None, layers=False, no_basemap=False, extra=None, sorts=(), bands=None):
        self.name, self.rows, self.cols = name, list(rows), list(cols)
        self.panes = panes if isinstance(panes, list) else [panes or Pane()]
        self.filters, self.formats, self.hide = list(filters), formats or {}, list(hide)
        self.fixed, self.header_font, self.header_width = fixed or {}, header_font, header_width or {}
        self.row_height, self.divider, self.tooltip, self.zoom = row_height, divider, tooltip, zoom
        self.sync = list(sync)  # second measure of a dual axis whose axis is synchronised with the first
        self.map_washout = map_washout  # set on map sheets: 1.0 fades the base map out completely
        self.layers = layers            # marks layers: panes[0] is the base pane, the rest are layers, bottom to top
        self.no_basemap = no_basemap    # <mapsource name='' />: a map with no background map at all
        self.fixed_axes = []            # (Raw generated field, min, max, scope): fixed and hidden map axes
        self.dehighlight = False        # clickable sheet: clear the selection after a click (see DEHIGHLIGHT_GROUP)
        self.axis_heights = {}          # {Ref: px} height of a (hidden) continuous axis band
        self.extra = {k: list(v) for k, v in (extra or {}).items()}  # {style element: [format lines]} added as written
        self.sorts = list(sorts)        # (dimension Ref, 'ASC' / 'DESC', measure Ref): computed sorts
        if bands:                       # banded rows in this colour (as Tableau writes it: pane colour, table size)
            self.extra.setdefault('pane', []).append(f"            <format attr='band-color' scope='rows' value='{bands}' />")
            self.extra.setdefault('table', []).append("            <format attr='band-size' scope='rows' value='1' />")

    def _shelf_refs(self, items):
        return [r for r in shelf_flat(items) if not isinstance(r, Raw)]

    def all_refs(self):
        # a field used in a label or tooltip must be in the view: add it to that pane's tooltip encodings
        on_shelves = {r.inst for r in self._shelf_refs(self.rows) + self._shelf_refs(self.cols)}
        for p in self.panes:
            have = on_shelves | {r.inst for r in p.refs()}
            for r in p.run_refs():
                if r.inst not in have:
                    p.tooltip_fields.append(r)
                    have.add(r.inst)
        refs = self._shelf_refs(self.rows) + self._shelf_refs(self.cols) + self.filters
        for p in self.panes:
            refs += p.refs()
        refs += list(self.formats)
        refs += [u for _, _, u in self.sorts]
        uniq = {}
        for r in refs:
            uniq.setdefault(r.inst, r)
        return list(uniq.values())

    def scope(self, r) -> str:
        return 'rows' if r.inst in {x.inst for x in self._shelf_refs(self.rows)} else 'cols'

    def xml(self) -> str:
        if self.dehighlight:
            for p in self.panes:
                for n in ('Dehighlight True', 'Dehighlight False'):
                    if all(r.name != n for r in p.lod):
                        p.lod.append(R(n))
        refs = self.all_refs()
        calc_names = [r.name for r in refs if r.is_calc]
        order, params, fields = CALCS.closure(calc_names)
        params |= {rl['param'] for p in self.panes for rl in p.reflines}
        fields |= {r.name for r in refs if not r.is_calc}
        fields |= {p.geometry for p in self.panes if p.geometry}
        dep = []
        if params:
            dep.append("          <datasource-dependencies datasource='Parameters'>")
            dep += [param_column(PARAM_BY[p], '            ') for p in sorted(params, key=lambda n: PARAM_ID[n])]
            dep.append('          </datasource-dependencies>')
        dep.append(f"          <datasource-dependencies datasource='{DS}'>")
        dep += [CALCS.column(n, '            ') for n in order]
        dep += ['            ' + BASES[f]['xml'] for f in sorted(fields) if f in BASES]
        dep += [r.instance_xml('            ') for r in refs]
        dep.append('          </datasource-dependencies>')

        filt = ''.join(
            f"          <filter class='categorical' column='{r.ref}'>\n"
            f"            <groupfilter function='member' level='{r.inst}' member='true' "
            "user:ui-domain='database' user:ui-enumeration='inclusive' user:ui-marker='enumerate' />\n"
            "          </filter>\n" for r in self.filters)
        slice_cols = [r.ref for r in self.filters]
        if self.dehighlight:
            filt += (f"          <filter class='categorical' column='[{DS}].{DEHIGHLIGHT_GROUP}'>\n"
                     f"            <groupfilter function='level-members' level='[{CALCS.cid('Dehighlight False')}]' "
                     f"user:ui-action-filter='{dehighlight_action_name(self.name)}' user:ui-enumeration='all' user:ui-marker='enumerate' />\n"
                     "          </filter>\n")
            slice_cols.append(f'[{DS}].{DEHIGHLIGHT_GROUP}')
        filt += ''.join(f"          <computed-sort column='{d.ref}' direction='{dr}' using='{u.ref}' />\n" for d, dr, u in self.sorts)
        slices = ('          <slices>\n' + ''.join(f'            <column>{c}</column>\n' for c in slice_cols)
                  + '          </slices>\n') if slice_cols else ''
        ds_list = f"            <datasource caption='{DS_CAPTION}' name='{DS}' />\n"
        if params:
            ds_list += "            <datasource name='Parameters' />\n"

        # ---- worksheet style
        def space_extra(v):
            return ''.join(f" {k}='{x}'" for k, x in sorted((v[2] if len(v) > 2 else {}).items()))
        axis = [f"            <encoding attr='space' class='0' field='{r.ref}' field-type='quantitative' fold='true' "
                f"max='{v[1]}' min='{v[0]}' range-type='fixed'{space_extra(v)} scope='{self.scope(r)}' type='space' />"
                for r, v in self.fixed.items()]
        for raw, mn, mx, sc in self.fixed_axes:
            axis.append(f"            <format attr='display' class='0' field='{raw.ref}' scope='{sc}' value='false' />")
            axis.append(f"            <encoding attr='space' class='0' field='{raw.ref}' field-type='quantitative' max='{mx}' "
                        f"min='{mn}' range-type='fixed' scope='{sc}' type='space' />")
        axis += [f"            <encoding attr='space' class='0' field='{r.ref}' field-type='quantitative' fold='true' "
                 f"scope='{self.scope(r)}' synchronized='true' type='space' />" for r in self.sync]
        axis += [f"            <format attr='display' class='0' field='{r.ref}' scope='{self.scope(r)}' value='false' />"
                 for r in self.hide if r.suffix == 'qk']
        head = []
        # discrete headers are hidden through the label rule (as in a Tableau-saved reference workbook)
        hidden_headers = [f"            <format attr='display' field='{r.ref}' value='false' />"
                          for r in self.hide if r.suffix != 'qk']
        if self.header_font:
            head += [f"            <format attr='{k}' value='{v}' />" for k, v in self.header_font.items()]
        head += [f"            <format attr='width' field='{r.ref}' value='{px}' />" for r, px in self.header_width.items()]
        cell = [f"            <format attr='text-format' field='{r.ref}' value='{esc(f)}' />" for r, f in self.formats.items()]
        if self.row_height:
            r, px = self.row_height
            cell.append(f"            <format attr='height' field='{r.ref}' value='{px}' />")
        axis_h = [f"            <format attr='height' field='{r.ref}' value='{px}' />" for r, px in self.axis_heights.items()]
        label = [f"            <format attr='text-format' field='{r.ref}' value='{esc(f)}' />" for r, f in self.formats.items()]
        label += hidden_headers
        rules = []

        def rule(el, lines):
            lines = lines + self.extra.pop(el, [])
            if lines:
                rules.append(f"          <style-rule element='{el}'>\n" + '\n'.join(lines) + '\n          </style-rule>\n')
        rulers = (["            <format attr='line-visibility' value='off' />", "            <format attr='stroke-size' value='0' />"]
                  if self.no_basemap else [])  # map canvases: no axis rulers (faint lines under the v12 group headers)
        rule('axis', axis + ["            <format attr='tick-color' value='#00000000' />"] + rulers + axis_h)
        rule('cell', cell)
        rule('gridline', ["            <format attr='line-visibility' value='off' />"])
        rule('header', head)
        rule('label', label)
        if self.map_washout is not None or self.no_basemap:
            rule('map', [f"            <format attr='washout' value='{self.map_washout or 0}' />"])
        # no "N nulls" badge: the In / Out window halves of a trend are null by design
        if self.no_basemap:
            rule('pane', ["            <format attr='border-style' value='none' />", "            <format attr='border-width' value='0' />"])
        rule('table', ["            <format attr='show-null-value-warning' value='false' />",
                       "            <format attr='background-color' value='#00000000' />"])
        div = ['on', LINE] if self.divider else ['off', '#00000000']
        rule('table-div', [f"            <format attr='line-visibility' scope='{s}' value='{div[0]}' />" for s in ('rows', 'cols')]
             + [f"            <format attr='stroke-color' scope='{s}' value='{div[1]}' />" for s in ('rows', 'cols')]
             + [f"            <format attr='stroke-size' scope='{s}' value='1' />" for s in ('rows', 'cols')])
        rule('worksheet', ["            <format attr='display-field-labels' scope='cols' value='false' />",
                           "            <format attr='display-field-labels' scope='rows' value='false' />"])
        rule('zeroline', ["            <format attr='line-visibility' value='off' />"])
        for el in list(self.extra):  # elements no default rule covers (refline, ...)
            rule(el, [])

        # ---- panes: dual axis gets one pane per measure after the first
        dual = has_dual(self.rows + self.cols)
        panes_open = "        <panes>\n"
        if self.layers:
            panes_open = "        <panes customization-axis='layer'>\n"
            panes = self.panes[0].xml(1) + ''.join(p.xml(i) for i, p in enumerate(self.panes[1:], 2))
        elif dual and len(self.panes) > 1:
            axis_attr = 'y-axis-name' if has_dual(self.rows) else 'x-axis-name'
            panes = self.panes[0].xml() + ''.join(p.xml(i, axis_attr) for i, p in enumerate(self.panes[1:], 1))
        else:
            panes = self.panes[0].xml()

        return (f"    <worksheet name='{esc(self.name)}'>\n"
                "      <table>\n        <view>\n          <datasources>\n" + ds_list + '          </datasources>\n'
                + ((f"          <mapsources>\n            <mapsource name='{'' if self.no_basemap else 'Tableau'}' />\n          </mapsources>\n")
                   if (self.map_washout is not None or self.no_basemap) else '')
                + '\n'.join(dep) + '\n' + filt + slices
                + "          <aggregation value='true' />\n        </view>\n"
                "        <style>\n" + ''.join(rules) + "        </style>\n"
                + panes_open + panes + "        </panes>\n"
                f"        <rows>{shelf(self.rows)}</rows>\n"
                f"        <cols>{shelf(self.cols)}</cols>\n"
                + ("" if self.tooltip else "        <tooltip-style tooltip-mode='none' />\n")
                + "      </table>\n"
                f"      <simple-id uuid='{stable_uuid('ws:' + self.name)}' />\n    </worksheet>\n")


# Palette maps written to the data source style: {Ref: {bucket literal: colour}}
COLOR_MAPS: list[tuple[Ref, dict[str, str]]] = []


def color_map(ref: Ref, mapping: dict[str, str]) -> None:
    if all(r.inst != ref.inst for r, _ in COLOR_MAPS):
        COLOR_MAPS.append((ref, mapping))


# Shape maps written to the data source style: {Ref: {bucket literal: shape path}}
SHAPE_MAPS: list[tuple[Ref, dict[str, str]]] = []


def shape_map(ref: Ref, mapping: dict[str, str]) -> None:
    if all(r.inst != ref.inst for r, _ in SHAPE_MAPS):
        SHAPE_MAPS.append((ref, mapping))


def datasource_style() -> str:
    rules = []
    for ref, m in SHAPE_MAPS:
        rules.append(f"          <encoding attr='shape' field='{ref.inst}' type='shape'>")
        for b, sh in m.items():
            rules.append(f"            <map to='{esc(sh)}'>\n              <bucket>{esc(b)}</bucket>\n            </map>")
        rules.append('          </encoding>')
    for ref, m in COLOR_MAPS:
        rules.append(f"          <encoding attr='color' field='{ref.inst}' type='palette'>")
        for b, c in m.items():
            rules.append(f"            <map to='{c}'>\n              <bucket>{esc(b)}</bucket>\n            </map>")
        rules.append('          </encoding>')
    return ("      <style>\n        <style-rule element='mark'>\n" + '\n'.join(rules)
            + "\n        </style-rule>\n      </style>\n")


# ---------------------------------------------------------------- dehighlight (learned from the OKRs and IronViz references)
# A click on a mark selects it and greys every other mark. A filter action from the sheet onto itself that maps a
# TRUE calc to a FALSE calc clears the selection straight away, so parameter-action clicks leave the view as it was.
CALCS.add(formulas={
    'Dehighlight True': '// Dehighlight True\n// Source field of the dehighlight action (clicked marks are not left greyed out).\nTRUE',
    'Dehighlight False': '// Dehighlight False\n// Target field of the dehighlight action: matches no mark, so the selection clears at once.\nFALSE',
}, types={'Dehighlight True': ('boolean', 'dimension', 'nominal'), 'Dehighlight False': ('boolean', 'dimension', 'nominal')})
DEHIGHLIGHT_GROUP = '[Action (Dehighlight False)]'


def dehighlight_action_name(sheet: str) -> str:
    import hashlib
    return f'[Action9_{hashlib.md5(("dh:" + sheet).encode()).hexdigest().upper()}]'


def dehighlight_group_xml() -> str:
    return (f"      <group caption='Action (Dehighlight False)' hidden='true' name='{DEHIGHLIGHT_GROUP}' name-style='unqualified' "
            "user:auto-column='sheet_link'>\n        <groupfilter function='crossjoin'>\n"
            f"          <groupfilter function='level-members' level='[{CALCS.cid('Dehighlight False')}]' />\n"
            "        </groupfilter>\n      </group>\n")


def datasource_instances() -> str:
    """Data-source-level column instances for every coloured field. Tableau only applies a palette whose field
    instance is declared here (seen in a Tableau-saved reference workbook: every palette key has one)."""
    return ''.join(ref.instance_xml('      ') + '\n' for ref, _ in COLOR_MAPS + SHAPE_MAPS)


def datasource_param_deps(names) -> str:
    """The data source's own declaration of the parameters its calcs read (written after <semantic-values>)."""
    if not names:
        return ''
    return ("      <datasource-dependencies datasource='Parameters'>\n"
            + '\n'.join(param_column(PARAM_BY[n], '        ') for n in sorted(names, key=lambda n: PARAM_ID[n]))
            + "\n      </datasource-dependencies>\n")


# ================================================================ dashboard zones and layout

class Z:
    """A dashboard zone. `fixed` is its size in px along the parent's direction (margins included)."""
    _next = 3

    def __init__(self, kind, name=None, *, fixed=None, kids=(), style=None, friendly=None, text=None,
                 image=None, button=None, dzv=None, param=None, weight=1.0):
        self.kind, self.name, self.fixed, self.kids = kind, name, fixed, list(kids)
        self.style, self.friendly, self.text, self.image = dict(style or {}), friendly, text, image
        self.button, self.dzv, self.param, self.weight = button, dzv, param, weight
        self.id = Z._next
        Z._next += 1
        self.rect = (0, 0, 0, 0)

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
        # Tableau's fixed size excludes the zone's own outer margin on that axis (a v11 save showed a fixed 417 column
        # with margin-left 7 laid out 424 wide, and 38px nav buttons with margin-bottom 4 laid out 42 tall)
        sides = ('margin-left', 'margin-right') if self.kind == 'horz' else ('margin-top', 'margin-bottom')
        outer = lambda k: k.fixed + sum(int(k.style.get(sd, k.style.get('margin', 0))) for sd in sides)
        # zones hidden by dynamic zone visibility at first open take no space (Tableau lays out what is shown)
        shown = lambda k: not (k.dzv and k.dzv[1] is False)
        fixed = sum(outer(k) for k in self.kids if k.fixed is not None and shown(k))
        flex = [k for k in self.kids if k.fixed is None and shown(k)]
        free = max(main - fixed, 0)
        tw = sum(k.weight for k in flex) or 1
        pos = cx if self.kind == 'horz' else cy
        for k in self.kids:
            size = 0 if not shown(k) else outer(k) if k.fixed is not None else free * k.weight / tw
            if self.kind == 'horz':
                k.layout(pos, cy, size, ch)
            else:
                k.layout(cx, pos, cw, size)
            pos += size

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
            a['param'], a['type-v2'] = self.kind, 'layout-flow'
        elif self.kind == 'basic':
            a['type-v2'] = 'layout-basic'
        elif self.kind == 'empty':
            a['type-v2'] = 'empty'
        elif self.kind == 'text':
            a['type-v2'] = 'text'
            inner.append(f"{ind}  <formatted-text>\n" + runs_xml(self.text, ind + '    ') + f"\n{ind}  </formatted-text>")
        elif self.kind == 'bitmap':
            a['is-scaled'], a['param'], a['type-v2'] = '1', f'Image/{self.image}', 'bitmap'
        elif self.kind == 'paramctrl':
            a['mode'], a['param'], a['type-v2'] = 'compact', f'[Parameters].{PARAM_ID[self.param]}', 'paramctrl'
            a['show-title'] = 'false'  # the picker needs no 'p_selected_exposure' title above it
        elif self.kind == 'imgbutton':
            a['type-v2'] = 'dashboard-object'
            b = self.button
            inner.append(
                f"{ind}  <button action='tabdoc:goto-sheet window-id=&quot;{window_ids[b['target']]}&quot;'>\n"
                f"{ind}    <button-visual-state>\n{ind}      <image-path>Image/{b['image']}</image-path>\n"
                f"{ind}    </button-visual-state>\n{ind}  </button>")
        elif self.kind == 'button':
            a['type-v2'] = 'dashboard-object'
            b = self.button
            fmts = ''.join(f"{ind}      <format attr='{k}' value='{v}' />\n" for k, v in b['format'].items())
            inner.append(
                f"{ind}  <button action='tabdoc:goto-sheet window-id=&quot;{window_ids[b['target']]}&quot;' button-type='text'>\n"
                f"{ind}    <button-visual-state>\n{ind}      <caption>{esc(b['caption'])}</caption>\n"
                f"{ind}      <button-caption-font-style {'bold=' + chr(39) + 'true' + chr(39) + ' ' if b['font'].endswith('|bold') else ''}fontcolor='{b['color']}' fontname='{b['font'].split('|')[0]}' fontsize='{b['size']}' />\n"
                + fmts + f"{ind}    </button-visual-state>\n{ind}  </button>")
        elif self.kind == 'sheet':
            a['name'], a['show-title'] = self.name, 'false'
        order = ['fixed-size', 'friendly-name', 'h', 'hidden-by-user', 'id', 'is-fixed', 'is-scaled', 'mode', 'name',
                 'param', 'show-title', 'type-v2', 'w', 'x', 'y']
        attrs = ' '.join(f"{k}='{esc(str(a[k]))}'" for k in order if k in a)
        kids = ''.join(k.xml(ind + '  ', window_ids) for k in self.kids)
        return (f"{ind}<zone {attrs}>\n" + ''.join(i + '\n' for i in inner) + kids
                + zone_style(self.style, ind + '  ') + f"{ind}</zone>\n")

    def walk(self):
        yield self
        for k in self.kids:
            yield from k.walk()


def zone_style(s: dict, ind: str) -> str:
    st = {'border-color': '#000000', 'border-style': 'none', 'border-width': '0', 'margin': '0'}
    st.update(s)
    lines = [f"{ind}  <_.fcp.DashboardRoundedCorners.true...format attr='corner-radius' value='{v}' />" if k == 'corner-radius'
             else f"{ind}  <format attr='{k}' value='{v}' />" for k, v in st.items()]
    return f"{ind}<zone-style>\n" + '\n'.join(lines) + f"\n{ind}</zone-style>\n"


CARD_STYLE = {'background-color': CARD, 'border-color': LINE, 'border-style': 'solid', 'border-width': '1',
              'corner-radius': '10'}


def text(runs, fixed=None, **style) -> Z:
    return Z('text', fixed=fixed, text=runs, style=style)


def blank(fixed=None, color=None, **style) -> Z:
    st = dict(style)
    if color:
        st['background-color'] = color
    return Z('empty', fixed=fixed, style=st)


def sheet(name, fixed=None, **style) -> Z:
    return Z('sheet', name, fixed=fixed, style=style)


def card(friendly, kids, fixed=None, pad=(14, 16, 14, 16), margins=None, horz=False, **extra) -> Z:
    st = {**CARD_STYLE, 'padding-top': str(pad[0]), 'padding-right': str(pad[1]),
          'padding-bottom': str(pad[2]), 'padding-left': str(pad[3])}
    for side, v in (margins or {}).items():
        st[f'margin-{side}'] = str(v)
    st.update(extra)
    return Z('horz' if horz else 'vert', friendly=friendly, fixed=fixed, kids=kids, style=st)


def card_header(title, subtitle, fixed=44) -> Z:
    return text([run(title, 10, INK1, SEMI), run(NL, 8, INK3), run(subtitle, 8, INK3, BOOK)], fixed=fixed,
                **{'padding-bottom': '10'})


def legend(items, right=None, fixed=22) -> Z:
    rs = []
    for i, (label, colour) in enumerate(items):
        rs += [run('■ ', 8, colour), run(label + ('     ' if i < len(items) - 1 else ''), 8, INK2)]
    if right:
        rs += [run('          ' + right, 8, INK3, italic='true')]
    return text(rs, fixed=fixed, **{'padding-top': '8'})
