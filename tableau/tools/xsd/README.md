# Tableau workbook schema (2026.1)

`twb_2026.1.0.xsd` (with `user.xsd` and `xml.xsd`) is Tableau's published workbook schema for version 2026.1,
copied from [tableau-dashboard-creator-skill](https://github.com/laviDrori0702/tableau-dashboard-creator-skill)
(MIT License, Copyright (c) 2026 Lavi Drori).

`build_workbook.py` validates every build against it (`validate_twb.py`), so a workbook Tableau would refuse to
open (wrong element order, unknown attribute) fails the build instead of reaching Tableau. It would have caught both
broken v19 builds (nav-actions in the wrong place in `<actions>`).
