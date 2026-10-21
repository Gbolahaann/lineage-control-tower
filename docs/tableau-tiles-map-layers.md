# Health tiles as map layers (rounded tiles)

Decision (GB, 21 Oct): the exposure tiles on Health overview are drawn with **map layers**, so they get real rounded corners. This replaces the square-mark grid (`HO Exposure Status Tiles` built from `Tile Row` / `Tile Column`) and settles decision D1: group labels are drawn by the same sheet.

## The data: `data/marts/mart_exposure_tiles.geojson`

Built by `generator/marts.py` (section 14). It contains 47 features in a small lat/lon box just south of 0,0. Near the equator Web Mercator is almost linear (under 0.2% stretch across this box), so the shapes stay true.

| Property | Meaning |
|---|---|
| `feature_type` | `tile` (a rounded rectangle, one per exposure) or `header` (a group label anchor; its polygon is a tiny dot, don't draw it) |
| `layout` | `All` or `Needs attention`. Matches the values of `p_tile_view` exactly |
| `node_id` | the exposure's node_id, relates to dim_nodes. Null on header rows |
| `group_label`, `group_order`, `group_count` | BI dashboards / Apps, ML and notebooks / AI agents and data hubs / Unregistered, found in query history |
| `tile_row`, `tile_col` | position in the group, for sorting and QA only |
| `name_lat`, `name_lon` | anchor for the tile title (left aligned, top line) |
| `meta_lat`, `meta_lon` | anchor for "Tool · Owner" (second line) |
| `trust_lat`, `trust_lon` | anchor for the trust label (bottom left) |
| `score_lat`, `score_lon` | anchor for the 7-day score (bottom right, right aligned) |
| `dot_lat`, `dot_lon` | anchor for the status dot (top right) |
| `label_lat`, `label_lon` | header rows only: anchor for the group label |

Tile geometry: 1.0 wide × 0.34 high in degrees, gaps 0.06, corner radius 0.045, five per row. That is the same 163 × 55 px tile with an 8 to 10 px gutter as the build plan, once the sheet is fitted to the 856 px grid.

Two layouts are pre-computed so the grid is stable: tiles do not reflow when filtered.
- **All:** 27 tiles in 4 groups.
- **Needs attention:** the 12 at-risk tiles, in the same 4 groups.
- **Platform filter:** fades non-matching tiles rather than removing them.

## One-time data source step (GB, in Tableau, about 2 minutes)

Adding a spatial connection by editing XML is fragile, so add it by hand to the master workbook, then let the builder take over.

1. Data Source tab → **Add** (next to Connections) → **Spatial file** → `data/marts/mart_exposure_tiles.geojson`
2. Drag `mart_exposure_tiles.geojson` onto the canvas as a **new base table**
3. Relate it to **dim_nodes** on `node_id = node_id`. Header rows have no node_id and simply don't match, which is fine
4. Save the master `.twb`. Re-run `prep_datasource.py` if it needs to rename the table to **Exposure Tiles** and hide the anchor fields from the data pane

## Calculations (paste-ready, naming standard)

```
// Tile Dot Point
// Status dot anchor (top right of each tile) as a point for its own map layer.
MAKEPOINT([dot_lat], [dot_lon])
```
```
// Tile Name Point
// Tile title anchor (top line, left aligned) as a point for the title text layer.
MAKEPOINT([name_lat], [name_lon])
```
```
// Tile Meta Point
// "Tool · Owner" anchor (second line, left aligned) as a point.
MAKEPOINT([meta_lat], [meta_lon])
```
```
// Tile Trust Point
// Trust label anchor (bottom left) as a point.
MAKEPOINT([trust_lat], [trust_lon])
```
```
// Tile Score Point
// 7-day score anchor (bottom right, right aligned) as a point.
MAKEPOINT([score_lat], [score_lon])
```
```
// Tile Header Point
// Group label anchor, only on header rows. Null on tiles so the header layer draws once per group.
IF [feature_type] = "header"
    THEN MAKEPOINT([label_lat], [label_lon])
END
```
```
// Is Tile Layout Match
// Keeps the layout that matches the All / Needs attention buttons. Put on Filters (True).
[layout] = [p_tile_view]
```
```
// Tile Fill Key
// Fill for the rounded tile: status tint, or faded when the tile is outside the Platform filter.
IF [feature_type] <> "tile"
    THEN "None"
ELSEIF NOT [Is Platform Match Node]
    THEN "Faded"
ELSEIF [current_status_code] = 3
    THEN "Critical"
ELSEIF [current_status_code] = 2
    THEN "Warning"
ELSE "Healthy"
END
```
Colours: Healthy `#FFFFFF`, Warning `#FDF3E1`, Critical `#FBEAE9`, Faded `#F7F7F5`, None transparent (or filter out). Border: Colour → Border `#E6E7E2`. Critical tiles may take a `#EDC3C0` border via a second key if it reads better.

```
// Tile Dot Key
// Status dot colour, greyed when the tile is outside the Platform filter.
IF NOT [Is Platform Match Node]
    THEN "Faded"
ELSE [current_status]
END
```
Colours: Healthy `#2F9E6B`, Warning `#E8A33D`, Critical `#D2453F`, No data `#A3ADB8`, Faded `#D9DCD7`.

```
// Tile Header Text
// Group label in caps with its count, e.g. "BI DASHBOARDS  17".
UPPER([group_label]) + "  " + STR([group_count])
```

Reuse the existing text calcs on the text layers: `Tile Name Short`, `Consumer Type Label` + `Tile Owner Text` / `Tile Owner Missing Text`, the three `Tile Trust …` runs, `Tile AI Tag`, `Tile Score Text`. Text colour on faded tiles: `#A5ACB4` through a `Tile Text Key` built the same way as `Tile Dot Key`.

## Sheet: `HO Exposure Status Tiles` (replaces the square-mark version)

Base table: **Exposure Tiles** (plus dim_nodes, shared). Filters: `Is Tile Layout Match` = True.

Build each layer by dragging the geometry field onto the map as **Add a Marks Layer**. Order from bottom to top:

| # | Layer (rename it) | Geometry | Mark | Filter in layer | Colour / label |
|---|---|---|---|---|---|
| 1 | Tile | `Geometry` | Map (polygon) | feature_type = tile | Colour: Tile Fill Key, border `#E6E7E2`. Detail: node_id. Tooltip: the existing tile tooltip |
| 2 | Dot | Tile Dot Point | Circle, size small | feature_type = tile | Colour: Tile Dot Key |
| 3 | Title | Tile Name Point | Circle, size smallest, opacity 0 | tiles | Label: Tile Name Short, 9pt Semibold `#16212E`, **left aligned, middle**, allow overlap |
| 4 | Meta | Tile Meta Point | as 3 | tiles | Label: Consumer Type Label · owner runs, 8pt `#7A838E` |
| 5 | Trust | Tile Trust Point | as 3 | tiles | Label: the three trust runs, 7 to 8pt Semibold in their status inks, then Tile AI Tag |
| 6 | Score | Tile Score Point | as 3 | tiles | Label: Tile Score Text, 8pt Semibold `#4A5563`, **right aligned** |
| 7 | Group header | Tile Header Point | as 3 | feature_type = header | Label: Tile Header Text, 8pt Semibold `#7A838E`, letter spacing if available |

Map settings for the sheet:
- Map → Background Maps → **None**
- Map → Map Options: untick Allow pan and zoom, Show map search, Show view toolbar, Show map scale
- Map → Map Layers: no layers
- Turn off the latitude/longitude axes, gridlines and zero lines
- Let Tableau fit to the data extent once, then fix the sheet size in the dashboard (856 px wide)

**Interaction.** Use the existing parameter action (select on this sheet sets `p_selected_exposure` from `node_id`, and sets the node key), plus the go-to-sheet action to Lineage. Selecting a text layer must also work: keep `node_id` on Detail in every tile layer. Turn off "Highlight" on the sheet so a click doesn't dim the other tiles.

**Tooltips:** only on layer 1. Turn tooltips off on layers 2 to 7 (Tooltip → uncheck "Show tooltips"), so hovering a label shows the tile's tooltip, not a blank one.

## QA

1. **All:** 27 tiles, 4 group labels (17 / 4 / 3 / 3). **Needs attention:** 12 tiles (6 / 2 / 3 / 1)
2. Critical tiles (pink): Board KPI Pack, Executive Revenue Dashboard, Finance Close Tracker, Finance Q&A Agent
3. **Platform = Databricks:** the Snowflake tiles fade but stay in place
4. Clicking a tile, including its text, opens Lineage with that exposure selected
5. On Tableau Public (or a Public test publish), map layers render with no basemap and no map controls

**Fallback if a layer misbehaves on Public:** keep layer 1 (rounded polygons, coloured) on the map, and put the tile text on a transparent text sheet floated exactly on top. That loses some of the single-sheet neatness but keeps the rounded look.
