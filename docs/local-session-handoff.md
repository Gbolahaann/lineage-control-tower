# Handoff: continue the Tableau build in a session on the Mac

Paste the message below into a new Claude session that runs **on your Mac** (Claude Desktop app, or
`claude remote-control` in Terminal), opened in your local copy of this repo.

---

We're building the Lineage Control Tower Tableau workbook from this repo. Read these first:
`tableau/versions/CHANGELOG.md`, `docs/tableau-build-plan.md`, `docs/tableau-calc-pack.md`, and the builder in
`tableau/tools/build_workbook.py` plus `tableau/tools/lct_build/` (core engine, shell, one module per tab).
Use my tableau-style skill in product mode.

How we work from now on:
1. Change the builder, never the master workbook (`tableau/Lineage_Control_Tower_Project_Dashboard.twb`).
2. Build with `python3 tableau/tools/build_workbook.py --tag vNN-<name>`. It writes `tableau/build/` and keeps a copy in
   `tableau/versions/`. Add a row to `tableau/versions/CHANGELOG.md` for every version.
3. Open the new `.twbx` in Tableau yourself (`open tableau/versions/vNN-<name>.twbx`), and with Computer use
   take screenshots of each dashboard you changed. Compare them with the prototype screenshots in `docs/img/` and fix
   what's off before showing me.
4. Commit and push after each version.

Where we are: v01-shell and v02-health are built but have never been opened in Tableau. Start by opening
v02-health, check it opens without errors, then check the list under "Known things to check" in the changelog
(KPI values at Last 30 days, tiles filling their cells, nav text alignment, Period/Platform buttons, the ⓘ panel).
Fix anything in the builder as v03, then carry on with the remaining tabs in the order in the build plan (5.2).
