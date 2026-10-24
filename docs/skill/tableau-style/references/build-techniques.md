# Build techniques (learned on Lineage Control Tower, Oct 2026)

Proven patterns for building product-style dashboards in Tableau, most of them written straight into `.twb` XML.
Each one was confirmed by opening the build in Tableau, or learned from a workbook Gbolahan (GB) adjusted and
re-saved, or from a Tableau-saved example GB shared. Version numbers (v12, v22b ...) point at the build where it was
learned; `tableau/versions/CHANGELOG.md` in the Lineage Control Tower repo has the full story. Read this before
building cards, buttons, tiles, tables, time charts or anything written into XML.

## Contents

1. Working with Gbolahan (process rules)
2. Before sending a build: validation and manifest flags
3. Label marks and button labels
4. Label alignment beside a mark
5. Cards on a pixel canvas (map layers)
6. Rounded rectangles as polygons
7. Sizing: zones, margins, content height, no scroll bars
8. Tables
9. Native time charts (bars, lines, Gantt) that line up
10. Selection: border highlight, window band, clicked-day colours
11. Colours and palettes
12. Interactivity: parameters, DZV, dehighlight, Go to Sheet
13. Headers, axes, number formats, nulls, spacing
14. Things that did not work

## 1. Working with Gbolahan (process rules)

- **The prototype is the spec, and its code beats its screenshot.** Read colours, opacities, paddings and stroke
  widths from the prototype source (`mockup/src/*.js`, `*.css`). Opacity on white becomes an exact hex, for
  example 55 % of #d2453f = #e69995, 5 % of #005fae = #f2f7fb, 8 % = #ebf2f8.
- **Ask, then build.** Before a new tab, list the prototype's parts and ask the few choices that change the build
  (canvas vs native, table scroll vs fit, where a click goes while its target tab does not exist).
- **Every rebuild gets a new version name** (`v22b`, `v23` ...). Reusing a name made GB reopen the old file and
  report its errors again (the line numbers gave it away: the fix had moved them by 3).
- **Fold in GB's adjusted files completely.** GB often fixes a build in Tableau and re-saves it. Diff the re-saved
  `.twb` against what was sent (`tableau/tools/twbdiff.py`): every worksheet, every dashboard, **and every calc
  formula** (a nudged MAKEPOINT lives in the data source, missed once on v13). Ignore Tableau's re-save noise:
  style-rule and filter order, floats written long (0.34000000000000002), `Æ` markers dropped from runs,
  `layout-cache`, `fold`, the fixed side of a two-zone row swapping, tooltip fields added to panes, DZV hidden
  states, parameter current values. Then fold every real change into the builder and say what you took.
- **When unsure how Tableau writes something, ask GB for a one-minute example** (one sheet, saved, sent back)
  rather than guessing twice. Go to Sheet, the selected-bar border and the computed sort all came right this way.
- **Report honestly:** what was checked (schema, formulas evaluated in Python, layout preview) and what was not
  (it has not been opened in Tableau).
- **Keep the skill current:** add every finding here when it is made, with the version it came from.

## 2. Before sending a build: validation and manifest flags

- `tableau/tools/validate_twb.py` (run by the builder on every build) validates against Tableau's 2026.1 XSD
  (`tableau/tools/xsd/`, MIT, from tableau-dashboard-creator-skill) and checks manifest flags. It catches wrong
  element order (both broken v19 builds) and missing flags it knows about.
- **Manifest flags gate elements.** Tableau rejects an element whose flag is missing from
  `<document-format-change-manifest>` with "no declaration found for element ...":
  - `<Layers />` for `customization-axis='layer'`, `generated-title`, `inert` (v07)
  - `<NavigationAction />` for `<nav-action>` (v19)
  - `<SortTagCleanup />`, `<IntuitiveSorting />`, `<IntuitiveSorting_SP2 />` for `<computed-sort>` (v22)
  Rule: before using an element for the first time, find it in a Tableau-saved file and copy that file's flags.
- **The XSD is 2026.1, GB runs a later version:** the user's error message lists the real content model, for example
  `(datasources?, mapsources?, datasource-dependencies*, filter, sort, perspectives, slices?, aggregation)`. Trust it
  over the XSD.
- **Order inside `<actions>`:** every filter `<action>`, then `<datasources>`, `<datasource-dependencies>`, then
  every `<nav-action>`, then every `<edit-parameter-action>`. Interleaving stops the workbook opening (v17, v19).
- Also checked before writing: one upstream table per map point, sheets placed, zone ids unique, every field a
  sheet shows declared on it, every grid inside its zone, the content rows ending at the content edge.

## 3. Label marks and button labels

Every mark whose only job is to carry a label (BANs, stamps, counts, card text) is a **hairline GanttBar**:

```xml
<mark class='GanttBar' />
<mark-sizing mark-sizing-setting='marks-scaling-off' />
<style-rule element='mark'>
  <format attr='mark-labels-show' value='true' />
  <format attr='mark-labels-cull' value='false' />
  <format attr='size' value='0.0099999997764825821' />
  <format attr='mark-color' value='#ffffff' />
  <format attr='mark-transparency' value='0' />
</style-rule>
```

A Text mark draws its own box, which sits over a background bar and shrinks it, and centres itself on its anchor
so left-aligned text gets cut off. A hairline clear Gantt carries the label without taking space.

**Button labels are a clear custom shape** (GB's preference since v22b): the same pane with `<mark class='Shape' />`
and `<format attr='shape' value='LCT/Transparent.png' />`, the transparent PNG embedded in the workbook so it does
not depend on anyone's shape folder. The button's action fields go on every pane, the base pane included.

## 4. Label alignment beside a mark

For a point-like mark (Gantt, shape, circle) on an ordinary axis, `text-align` places the label **beside** it:

| text-align | Where the label goes |
|---|---|
| `right` | to the right: the text **starts** at the point |
| `left` | to the left: the text **ends** at the point |
| `center` | centred on the point |

Tableau leaves about 4 px between the point and the label. Vertical alignment `top` is not reliable for lifting a
label above a thin bar (v23, v24): move the point instead.

- **Bar labels** with `text-align left` sit inside the start of the bar, so the bar runs through the number. Put
  counts on a clear hairline mark on the second axis, just past the longest bar
  (`WINDOW_MAX([count]) * 1.14`) with alignment **Middle Right** (text-align right, Arial 9 pt), as GB set it
  (v27), so nothing crosses them.
- **On a map pane Gantt labels go the other way:** `left` puts the text to the right of the point, `right` to
  the left. Keep the point a few px inside the pane, never on its edge (it gets dropped).
- **Indenting on a map pane (GB's v13 fix):** a leading run of spaces with Tableau's literal marker,
  `<run bold='true' fontcolor='#16212e'>Æ   </run>`, before the field run. 3 spaces on a tile line, 11 on an alert
  line. A right-hand value gets `fontalignment='1'` on its run.
- **One line per mark** on a canvas: with left or right alignment a multi-line label goes ragged.

## 5. Cards on a pixel canvas (map layers)

For cards with many parts (tiles, alert rows, headers, a lineage graph), use map panes as a pixel canvas, as the
OKRs reference does:

- Rows `(Row index * Latitude (generated))`, columns `(Column index * Longitude (generated))`. Row and column
  indexes are discrete INDEX table calcs addressed along the card key with `ordering-type='Field'`.
- No base map: `<mapsources><mapsource name='' /></mapsources>`, washout 0. Hide both axes and fix them to
  **px / 100 around the pane centre** (a 168 x 68 pane: Longitude -0.84 to 0.84, Latitude -0.34 to 0.34). Every
  MAKEPOINT is then in pixels: `MAKEPOINT((34 - y) / 100, (x - 84) / 100)`.
- Fix every pane's size (`minwidth = maxwidth`, `minheight = maxheight`, `aspect 0`) and keep the view at
  **Standard**. Fit width or Entire view scales the positions but not the text, so labels slide into each other
  (the v25 errors table).
- Each part is a marks layer (`<panes customization-axis='layer'>`, `generated-title`, `inert='true'` for layers
  that should not take clicks). Point calcs are spatial measures used as `[clct:...]` on Detail.
- Turn off axis rulers and pane borders (`axis`: `line-visibility off`, `stroke-size 0`; `pane`: `border-style none`).
- **A map point may read only one table besides the hub** (Nodes): "Column can have only one upstream base
  table". Write such values at build time keyed on the canvas table's own fields; the builder checks every point.
- **ATTR shows "*"** when a mark's rows disagree: make label calcs return NULL, not "", on rows that should not
  speak.

## 6. Rounded rectangles as polygons

Draw rounded rectangles (card, border, top edge, pill, chip, dot) as **polygons**, not custom shapes:

- Path from rows the mark already has: 88 daily rows (`Path Index = MIN(DATEDIFF('day', {MIN([date])}, [date]), 87)`,
  22 points per corner arc) or 12 edge rows (`point_order`, 3 points per corner).
- Corner k (0 to 3), angle `θ = RADIANS(k * 90 + (i % n + 0.5) * 90 / n)`:
  `x = cx + sx(k) * (w/2 - r) + r * COS(θ)`, `y = cy + sy(k) * (h/2 - r) + r * SIN(θ)`, `sx = 1, -1, -1, 1`,
  `sy = 1, 1, -1, -1`.
- Border = a full-size polygon in the border colour under a fill polygon 1 px smaller. A coloured top edge: the fill
  with its Latitude clamped to the top 3 px. Hide a part for some rows by multiplying its offsets by
  `IIF(condition, 1, 0)`.
- Colour each polygon with its own key field so each gets its own palette.

## 7. Sizing: zones, margins, content height, no scroll bars

- **A zone's fixed size excludes its own margin on that axis.** A fixed 417 column with margin-left 7 takes 424.
  Do not add the margin into the fixed size as well: v22 to v25 gave RUN's rows `352 + 14` *and* `margin-top 14`,
  864 px in 836, and Tableau rebalanced the rows and left space at the bottom.
- **Content height comes from one place:** 1000 - header 70 - filter band 52 - padding 20 top - 14 bottom = 844.
  The bottom padding is 14 (the card gap) since v26, not the prototype's 22 (GB: no unneeded space at the
  bottom). Tabs size their last row as "the rest", and the builder asserts the rows end at the content edge.
- **The last row of a content area is always flexible** (no fixed size). Tableau does its own arithmetic on fixed
  rows; with every row fixed, any difference became a grey gap under the bottom cards (RUN v27, about 30 px). Health
  and Lineage end in a flexible row and never showed it.
- **Matching columns across rows:** fix the wide card (918 including its 7 px margin, so fixed 911) and let the
  narrow card take the rest, in every row, so the right-hand cards (394) line up.
- **`card_header` in a horizontal row needs `fixed=None`:** its default 44 is a height in a column but a width in
  a row.
- **No scroll bars:** size every grid a few px inside its zone (`pane = (zone - 4) // columns`) and leave 18 px for
  a vertical scroll bar where a table scrolls. A canvas 7 px too wide gave horizontal scroll bars (v24).
- **No Entire view on card grids:** panes stretch, circles become ovals, text stops lining up with its card.
- **Measure text with Liberation Sans** (metric-compatible with Arial; 9 pt = 12 px at 96 dpi) and write width or
  truncation calcs at build time (`CASE [key] WHEN ... THEN <px>`, `_fit(text, px, pt)` with "…").

## 8. Tables

- **Plain text tables are native** (v26): hidden order and key headers, then fixed-width row headers (When 96,
  Model 192, Category 120) and the last column as the Text mark filling the rest, row height set on the last header
  (`cell` rule `height`). Columns can never run into each other. Texts that must fit are cut by the build.
- **Check a native table against the prototype's table CSS before sending** (v26 skipped it): Tableau text tables
  band alternate rows grey by default (set `band-color` clear on the `pane` and `header` rules), wrap text that
  does not fit the cell (cut it about 40 px short of the column), and have no row lines unless asked (row dividers
  only, `table-div` rows on, cols off; a 1 px line zone under the title row).
- **Title row:** the same structure on a one-row scaffold (constant calcs "WHEN", "MODEL" ...), same header widths,
  7 pt grey bold via the `label` rule, so it lines up with the table.
- **Tables with pills** are a canvas (section 5): one fixed pane per row, pills as polygons from the row's own
  multi-point rows, every cell placed as a centred label at half its measured width. Standard view only.
- No borders: cell `border-style none` on every sheet (GB: "cell line is none"), no `table-div` lines around a
  table (GB found the border disturbing).

## 9. Native time charts (bars, lines, Gantt) that line up

- **Shared reversed day axis:** `Days Back Mid = days_before_as_of + 0.5`, fixed 0 to 90 with `reverse='true'`:
  today on the right, day d fills [d, d + 1], the selected window is "below p_period".
- **Strips that line up with a chart** (incident labels above, dates below): same x field and range, and a y axis
  with the chart's fixed range, tick spacing **and number format** but clear label colour, so the clear axis takes
  the same width as the chart's.
- **Date labels:** first day and every 1st of the month on a wide chart; only the 1sts on a narrow one ("22 Jul"
  ran into "1 Aug" on MTTR).
- **Lines and areas:** never put a date dimension on Detail for the tooltip; it splits the line into dots and the
  area into strips. Use an aggregate text (`MIN([date])` formatted). Thin line: size 0.4.
- **Gantt:** start in hours on an axis fixed 0 to 24, `major-spacing 3`, format `n00":00";-00":00"`. Put the
  selected day in the position calc (`IF [run_date] = [p_gantt_date] THEN ...`), not a filter, so every job keeps its
  row. Banded rows: pane `band-color` + table `band-size`.
- **Stacked look on a dual axis without Measure Names:** overlay total (grey) and part (red), synchronised.
- **Sort by a measure:** `<computed-sort>` after the filters (flags in section 2). Top N: a table-calc filter
  `RANK_UNIQUE(...) <= 7` addressed along the dimension.
- **Reference lines on a parameter: unsolved.** `value-column='[Parameters].[Parameter N]' formula='constant'` loads,
  but Tableau re-saves it as `value='%null%'`. Draw bands with bars instead (section 10) until GB sends a
  Tableau-saved parameter reference line.

## 10. Selection: border highlight, window band, clicked-day colours

From GB's example (How to Use a Border to Highlight Selections in Tableau) and the prototype's chart code:

- **Border round a selected bar:** a wider bar behind (back axis), coloured only for the selected item; the normal
  bar in front. The edge that shows is the border.
- **Three or more layers on a dual axis:** stack the front as Measure Values: rows `(back + [Multiple Values])`,
  a `[:Measure Names]` member filter and `manual-sort` (stack order, first at the bottom), `<color
  column='[:Measure Names]'>`, palette in the data source style with buckets `"[ds].[usr:Calc:qk]"`.
- **Clicked day like the prototype:** front stack Failed Selected (full red), Failed Other (pale), Skipped Selected,
  Skipped Other, then a filler up to the outline top in the band colour (white outside the window), so the navy back
  bar shows only as a hollow outline. Back bar: the clicked day navy to near the top, every other window day full
  height and full width in the band colour (the bars touch: the window band).

### Freshness patterns (v29)

- **Bullets as a canvas row per item:** zones and value bar as polygons from the item's own daily rows, each on its
  own scale when the prototype does so; name and value placed at measured widths.
- **Static "right now" cards on a scaffold:** when the content is fixed at the as-of date (late sources and the
  products waiting on them), lay it out at build time (pills, wrapped chips) and draw it on the 90-row date table,
  8 rows per rounded shape (chamfered corners read as rounded at chip size) and one row per text. Keep filters
  live by wrapping each part in its parameter check. The build asserts the shapes fit (11 per 90 rows).
- **Calendar heatmap:** rows weekday (sorted by day number), columns week, Square marks; today outlined by a larger
  navy square on a second axis. Give the sheet a fixed height so the rows stay compact, as in the prototype.
- **Line-end labels:** `mark-labels-mode line-ends`, `mark-labels-line-last true`, and room on the right of the
  axis (the reversed day axis starts at -11).

## 11. Colours and palettes

- A palette only applies if the coloured field also has a data-source-level `<column-instance>`; otherwise Tableau
  falls back to its defaults. Same for shape maps.
- **Quote text buckets** (`'"Selected"'`); booleans stay `true` / `false`. Unquoted text buckets silently fall back
  to defaults (v24: an orange outline and a red band). The builder's `color_map` asserts it.
- Two-colour trend bars (window vs rest): two measures on a synchronised dual axis, each pane a fixed
  `mark-color`; no palette needed.

## 12. Interactivity: parameters, DZV, dehighlight, Go to Sheet

- The data source declares the parameters its calcs read (`<datasource-dependencies datasource='Parameters'>`
  after `</semantic-values>`), or calcs fail with "Invalid formula".
- **Dynamic zone visibility reads parameters only.** A DZV calc that read the data kept its first value (v16, v17).
  Write one parameter per thing a panel switches on (`p_panel_status`, `p_panel_type`, `p_panel_platform`,
  `p_panel_tags` as `"|moved|ai|"`) from every sheet whose click picks a node, those fields on Detail of the clickable
  layers (ATTR on INDEX-based grids), defaults set to the default node's values.
- **A status pill whose colour depends on the data** is easier as a tiny canvas sheet than one DZV container per state.
- **Dehighlight after a click** (OKRs and IronViz): `Dehighlight True` / `Dehighlight False` calcs on Detail, a hidden
  group `Action (Dehighlight False)` (`user:auto-column='sheet_link'`), a sheet filter on it with
  `user:ui-action-filter`, and a `tsc:tsl-filter` action onto itself
  (`tsl:<sheet>?[ds].[false]~s0=<[ds].[true]~na>`).
- **Go to Sheet:** `<nav-action>` with `<activation type='on-select' />`,
  `<source dashboard='<dashboard>' type='sheet' worksheet='...' />` (without the dashboard it never fires from the
  dashboard, v19) and `<params><param name='sheet' value='<target>' /></params>`. The same click runs the
  parameter actions first, so the target opens on the selection.

## 13. Headers, axes, number formats, nulls, spacing

- Hide discrete headers through the `label` rule (`display false`); per-field header font, colour and alignment go
  in the `label` rule too, widths in the `header` rule, row heights in the `cell` rule.
- Hide axes with `display false` (class 0); fix ranges on `<encoding attr='space' range-type='fixed' min max>`,
  ticks with `major-origin` / `major-spacing`; blank an axis title with `<format attr='title' class='0' field
  scope value='' />`.
- **A dual axis's visible axis takes the first measure's cell format:** give that measure the axis format ("20h")
  and the second the tooltip's ("20.4h").
- Number formats with a unit: `n#,##0"h";-#,##0"h"`; custom dates `*d mmm yyyy`. A format like `▲ 0%;▼ 0%` on a
  label did not apply: build the text in a calc.
- Hide the "N nulls" badge: `table` rule `show-null-value-warning false`.
- A text run that starts with whitespace needs the literal marker `Æ` (`Æ  `); `Æ&#10;` is a line break.

## 14. Things that did not work

- **Custom shape images for cards:** Shape marks have no fixed pixel scale; a constant on Size scales every shape to
  the pane. Use polygons for exact sizes; shapes only for small icons and clear button labels.
- **Text marks centred on an anchor** for left-aligned text: cut off.
- **Entire view / Fit width on a pixel canvas:** positions scale, text does not.
- **A geojson table added to the master** corrupted the logical-table graph; draw shapes from existing rows.
- **Parameter reference lines** written by hand (section 9).
- **DZV calcs that read data** (section 12).
