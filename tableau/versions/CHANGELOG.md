# Workbook versions

Every build sent for review is kept here as a `.twbx`, so any version can be opened again or
rolled back to. Open the `.twbx` (the icons are packaged inside). The files read the CSVs from
`data/marts` on your Mac, at the path saved in the master workbook.

To rebuild a version: check out its commit and run `python3 tableau/tools/build_workbook.py --tag <name>`.
The master workbook (`tableau/Lineage_Control_Tower_Project_Dashboard.twb`) is never edited by the builder.

| Version | Date | What changed | Status |
|---|---|---|---|
| v01-shell | 21 Oct 2026 | Shared shell on all 11 dashboards: nav with icons, header, filter band (Period and Platform buttons), info panel with DZV, 9 parameters, shell calcs, GL sheets, parameter actions. Content areas empty | Sent, not yet opened in Tableau |
| v02-health | 21 Oct 2026 | Tab 1, Health overview: 6 KPI cards (BAN, change line, 90-day trend bars), exposure status tiles in 4 groups with the All / Needs attention switch, Needs attention list, Health by layer bar. 16 sheets, 127 calcs. Parameter actions: tile sets the selected exposure and clears the node, alert sets the selected node. Go-to-sheet actions wait until Lineage and Blast radius exist | Reviewed by GB 21 Oct: numbers right, formatting poor (Tableau 10 colours, visible helper headers, clipped buttons, oversized marks, missing spaces) |
| v03-health-fixes | 21 Oct 2026 | Health review fixes. **Arial family** everywhere (workbook font, every text run, bold instead of semibold). **KPI trend colours** no longer use a palette: each trend is two measures on a synchronised dual axis (in window / out of window) with a fixed pane colour, #005FAE or #E8A33D for Exposures at risk, and #D9DCD7. Status tints and layer colours keep their brand palette. **Helper headers** hidden with the axis-style syntax (class 0): period 7/30/90, platform 0-3, tile row and column, group sort, attention sort, layer_column. **Marks** sized to their cells (no spill into empty cells). **Needs attention** rows keyed by display_name, node_id kept on detail for the action. **Text**: plain-space runs replaced with no-break spaces so "0.10 pp vs prior 30d" and "12 of 27 now" keep their gaps; stray "Æ" removed. **Nav** buttons are now image buttons with the icon and a left-aligned Arial label baked in, and the nav footer shows a dynamic "Data updated on 19 Oct 2026, 23:59". Exposure status subtitle on two lines, All / Needs attention toggle widened to 230px. Tiles are still the square-mark grid: the map-layer tiles wait for the master workbook with the geojson connection | Sent, waiting for review |

## Known things to check in each version

- **v01 / v02:** nav button text alignment (set to left, Tableau may centre it); Square marks filling the button track; ⓘ toggling the panel.
- **v03:** trend bars grey with the window in blue (amber on Exposures at risk); no index headers on any sheet; nav labels left-aligned beside their icons; tiles and alert rows stay inside their cells.
- **v02:** KPI numbers should match the prototype at Last 30 days, All platforms: Run success 99.85% (▲ 0.10 pp), Test pass 99.41% (▲ 0.04 pp), Freshness 99.87% (▼ 0.03 pp), 12 of 27 exposures at risk (4 critical · 8 warning), MTTR 4.9 h (▼ 10.8%), cost $4,189 (▼ 15.1%). Tiles fill their cells, worst first in each group. Three nodes under Needs attention.
