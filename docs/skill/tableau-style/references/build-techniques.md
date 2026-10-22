# Build techniques (learned on Lineage Control Tower, Oct 2026)

Proven patterns for building product-style dashboards in Tableau, most of them written straight into `.twb`
XML. Each one was confirmed by opening the build in Tableau, or learned from a workbook Gbolahan adjusted and
re-saved. Read this before building cards, buttons, tiles or any web-app-style component.

## Contents

1. Label marks: hairline Gantt bars, not Text
2. Label alignment beside a mark
3. Cards on a pixel canvas (map layers)
4. Rounded rectangles as polygons
5. Sizing cards to their zone (no scroll bars)
6. Segmented buttons
7. Colours, palettes and parameters in XML
8. Headers, axes, nulls and spacing
9. Things that did not work
10. Working with Gbolahan's adjustments

## 1. Label marks: hairline Gantt bars, not Text

Every mark whose only job is to carry a label (BANs, button text, stamps, counts, card text) is a **GanttBar**:

```xml
<mark class='GanttBar' />
<mark-sizing mark-sizing-setting='marks-scaling-off' />
...
<style-rule element='mark'>
  <format attr='mark-labels-show' value='true' />
  <format attr='mark-labels-cull' value='false' />
  <format attr='size' value='0.0099999997764825821' />
  <format attr='mark-color' value='#ffffff' />
  <format attr='mark-transparency' value='0' />
</style-rule>
```

Why: a Text mark draws its own box, which sits over a background bar and shrinks it, and centres itself on its
anchor so left-aligned text gets cut off. A hairline clear Gantt carries the label without taking space.

## 2. Label alignment beside a mark

For a point-like mark (Gantt, shape, circle) at a position on an axis or map, the label's `text-align` places
the label **beside** the mark, it does not justify it inside a box:

| text-align | Where the label goes |
|---|---|
| `right` | to the right: the text **starts** at the point |
| `left` | to the left: the text **ends** at the point |
| `center` | centred on the point |

Vertical alignment works the same way (`bottom` = the label hangs below the point). Tableau leaves about 4px
between the point and the label.

**One line per mark.** With `right` or `left`, a multi-line label is also justified that way, so lines go
ragged. Put each line of a card on its own layer.

## 3. Cards on a pixel canvas (map layers)

For cards with many parts (tiles, alert rows, headers), use a grid of map panes as a pixel canvas, as the OKRs
reference does:

- Rows `(Row index * Latitude (generated))`, columns `(Column index * Longitude (generated))`. Row and column
  indexes are discrete INDEX table calcs (`(INDEX()-1) % 5 + 1`, `INT((INDEX()-1)/5) + 1`), addressed along the
  card key with `ordering-type='Field'`.
- No base map: `<mapsources><mapsource name='' /></mapsources>` and washout 0. Hide both axes and fix them to
  **px / 100 around the pane centre** (a 168 x 68 pane: Longitude -0.84 to 0.84, Latitude -0.34 to 0.34).
  Every MAKEPOINT is then written in pixels: `MAKEPOINT((34 - y) / 100, (x - 84) / 100)`.
- Fix every pane's size and turn off aspect:
  `<style-rule element='pane'>` minwidth = maxwidth, minheight = maxheight, `aspect 0`.
- Each part is a marks layer (`<panes customization-axis='layer'>`, `generated-title`, `inert='true'` for
  layers that should not take clicks). Point calcs are spatial measures (`datatype='spatial' role='measure'`)
  used as `[clct:...]` on Detail.
- The manifest must declare `<Layers />`, or Tableau rejects `customization-axis`, `generated-title` and
  `inert`.
- Keep the view at **Standard** (no `<zoom>` in the dashboard viewpoint) so panes keep their pixel size.

## 4. Rounded rectangles as polygons

Draw rounded rectangles (card, border, top edge, pill, chip, dot) as **polygons**, not custom shapes:

- Path: a date that gives each node at least 88 rows (Exposure Daily, Node Daily: 90 days each).
  `Path Index = MIN(DATEDIFF('day', {MIN([date])}, [date]), 87)`.
- Points 0 to 87 walk the four corner arcs, 22 points each. With `k = INT(i / 22)` and
  `θ = RADIANS(k * 90 + (i % 22 + 0.5) * 90 / 22)`:
  `x = cx + sx(k) * (w/2 - r) + r * COS(θ)`, `y = cy + sy(k) * (h/2 - r) + r * SIN(θ)`, with `sx = 1, -1, -1, 1`
  and `sy = 1, 1, -1, -1` for `k = 0..3`.
- Border = a full-size polygon in the border colour under a fill polygon 1px smaller. A coloured top edge is the
  fill polygon with its Latitude clamped to the top 3px: `MAX(lat, top_lat - 0.03)`.
- To show a part only for some rows (AI pill, incident tag), multiply its offsets by `IIF(condition, 1, 0)`: at 0
  it shrinks to a point and disappears.
- A circle is the same calc with `w = h = 2r`. A triangle: `INT(i / 30)` picks one of three vertices.
- Colour each polygon with its own key field (a copy of the status field) so each gets its own palette.

## 5. Sizing cards to their zone (no scroll bars)

- **A zone's fixed size excludes its own margin on that axis.** A fixed 417 column with margin-left 7 takes 424;
  a 38px nav button with margin-bottom 4 takes 42.
- Compute each grid zone's real width, then size panes a few px inside it: `pane = (zone - 4) // columns`.
  Never let a grid exceed its zone, or Tableau adds scroll bars (Gbolahan does not want scroll bars).
- Do not use Entire View for card grids: panes stretch, so a group with 2 tiles gets 2 very wide cards, a full
  group gets squashed cards, circles become ovals, and text stops lining up with the card. Fixed cards that are
  left-aligned when a row is short is how the prototype behaves.
- Measure text with Liberation Sans (metric-compatible with Arial): Tableau draws Arial at 96 dpi, so 9pt is
  12px. Use it to place things after variable text (a tag after a name): generate a `CASE [name] WHEN ... THEN
  <px>` width calc at build time.

## 6. Segmented buttons

- Columns `(Option order * (Full Bar + Text Anchor))`, Full Bar `MIN(1.0)` and Text Anchor `MIN(0.5)` on
  axes fixed 0 to 1 and hidden.
- Bar pane: size `1.9890055656433105` (full), colour by `Is Active Option` (white `#ffffff` true, `#f5f5f3`
  false).
- Text pane: the hairline Gantt label (section 1), centred.

## 7. Colours, palettes and parameters in XML

- A palette in the data source `<style>` only applies if the coloured field **also** has a data-source-level
  `<column-instance>`. Without it Tableau falls back to Tableau 10. Register every coloured key field.
- Same for custom shape maps (`<encoding attr='shape' type='shape'>`).
- The data source must declare the parameters its calcs read in `<datasource-dependencies
  datasource='Parameters'>` after `</semantic-values>`, or calcs fail with "Invalid formula".
- Use ATTR() for a text field used in a tooltip or label on a polygon or map layer. A plain dimension there can
  come up as an invalid (red) pill.

## 8. Headers, axes, nulls and spacing

- Hide discrete headers with `<style-rule element='label'><format attr='display' field='...' value='false' />`.
- Hide axes with `<style-rule element='axis'><format attr='display' class='0' field scope value='false'>`; fix
  ranges with `<encoding attr='space' ... range-type='fixed' min max>`.
- Hide the "N nulls" badge: `<style-rule element='table'><format attr='show-null-value-warning' value='false' />`.
- A text run that starts with whitespace needs Tableau's literal marker: `Æ` + the text (`Æ  `). `Æ&#10;` is a
  line break.
- Trend bars in two colours (window vs rest): two measures (`IF ATTR([In Period]) THEN x END` and its opposite)
  on a synchronised dual axis, each pane with a fixed `mark-color`. No palette needed.

## 9. Things that did not work

- **Custom shape images for cards.** Shape marks have no fixed pixel scale. A constant on Size makes Tableau
  scale every shape to the pane, so cards come out huge and clipped. Use polygons for anything that must be an
  exact size; keep custom shapes for small icons only.
- **Text marks centred on an anchor** for left-aligned text: the box centres on the point and gets cut off.
- **Entire View** on fixed-geometry card grids (see section 5).
- **A geojson table added to the master** corrupted the logical-table object graph ("Logical Query missing field
  ... from relationOp"); repairing the XML did not fix it. Draw shapes from existing rows instead.

## 10. Working with Gbolahan's adjustments

Gbolahan often fixes a build in Tableau and re-saves it. Diff the re-saved `.twb` against the build, sheet by
sheet (ignore `datasource-dependencies` and run attribute order) and dashboard by dashboard (zone rects, fit,
viewpoints), then fold every change into the builder so the next build keeps it. Tableau's re-save also shows
the real laid-out zone sizes, which are the ground truth for card sizing.
