# Workbook versions

Every build sent for review is kept here as a `.twbx`, so any version can be opened again or
rolled back to. Open the `.twbx` (the icons are packaged inside). The files read the CSVs from
`data/marts` on your Mac, at the path saved in the master workbook.

To rebuild a version: check out its commit and run `python3 tableau/tools/build_workbook.py --tag <name>`.
The master workbook (`tableau/Lineage_Control_Tower_Project_Dashboard.twb`) is never edited by the builder.

| Version | Date | What changed | Status |
|---|---|---|---|
| v01-shell | 21 Oct 2026 | Shared shell on all 11 dashboards: nav with icons, header, filter band (Period and Platform buttons), info panel with DZV, 9 parameters, shell calcs, GL sheets, parameter actions. Content areas empty | Sent, not yet opened in Tableau |
| v02-health | 21 Oct 2026 | Tab 1, Health overview: 6 KPI cards (BAN, change line, 90-day trend bars), exposure status tiles in 4 groups with the All / Needs attention switch, Needs attention list, Health by layer bar. 16 sheets, 127 calcs. Parameter actions: tile sets the selected exposure and clears the node, alert sets the selected node. Go-to-sheet actions wait until Lineage and Blast radius exist | Sent, waiting for review |

## Known things to check in each version

- **v01 / v02:** nav button text alignment (set to left, Tableau may centre it); Square marks filling the button track; ⓘ toggling the panel.
- **v02:** KPI numbers should match the prototype at Last 30 days, All platforms: Run success 99.85% (▲ 0.10 pp), Test pass 99.41% (▲ 0.04 pp), Freshness 99.87% (▼ 0.03 pp), 12 of 27 exposures at risk (4 critical · 8 warning), MTTR 4.9 h (▼ 10.8%), cost $4,189 (▼ 15.1%). Tiles fill their cells, worst first in each group. Three nodes under Needs attention.
