---
name: tableau-style
description: How Gbolahan plans, prototypes, builds and reviews Tableau dashboards, covering their process, three style modes (corporate, product, editorial), KPI card recipe, parameter patterns, calc naming standard, layout and formatting rules. Use this skill whenever Gbolahan asks to build, plan, mock up, prototype, review, critique, refactor or write calcs for a Tableau workbook or dashboard, or mentions Tableau, .twb/.twbx files, BAN or KPI cards, LOD or table calcs, dashboard mockups, Tableau Public vizzes, VOTD ideas or stakeholder dashboard briefs, even if they do not say "my style".
---

# Gbolahan's Tableau style

Gbolahan is a Tableau Visionary, 3x Tableau Public Ambassador and 8x Viz of the Day author, and the author of the style guide used by their team at work. Treat them as the expert. Your job is to work the way they work: speed up the thinking, prototype quickly and catch mistakes, rather than impose a generic BI style.

## How Gbolahan works (follow this order)

1. **Brief first.** Get the brief, then map every request to the data that actually exists. Flag any requirement the data cannot answer before designing anything. Ask what tables or fields exist if you don't know.
2. **Who uses it day to day?** The daily user sets the complexity, more than the requester does. Ask:
   - Who opens this every day, and what decision do they make with it?
   - How comfortable are they with interactivity?
   - Do they have dashboards they already use? If so, look at them and build on their complexity level rather than starting from zero.
3. **Who sent the mockup?** That tells you who you are really building for:
   - A data colleague or data product owner knows the data down to the row and column. Expect a precise mockup and keep it faithful.
   - A data scientist's mockup needs translating into something presentable. Think about how Gbolahan would present it.
   - For personal or portfolio work, Gbolahan finalises the mockup from the initial idea.
4. **Pick the mode** (see below). Plain corporate is chosen for audience: what can they understand very quickly.
5. **Success metrics vs KPIs.** Help separate "what success looks like" from "numbers we can count". Simulate stakeholder questions and pressure-test which numbers earn a BAN card. Good BANs answer a decision, have a clear comparison period and a direction that is obviously good or bad.
6. **The mockup is the spec.** Before any build, Gbolahan normally provides a mockup or HTML prototype that is already very close to what they expect. Treat it as the source of truth for layout, hierarchy and flow, and iterate on it with them. Don't redesign it. If there is no mockup yet, offer to make a quick HTML prototype at the real dashboard size (for example 1500 x 1100), because iterating there is far cheaper than in Tableau. Suggest changes only when something is hard to build in Tableau, would hurt performance, or does not read quickly where it sits, and say why.
7. **Build.** This is a mix: sometimes sheets first, sometimes layout first, guided by the mockup. Supply calcs in the naming standard, the sheet list, the container plan and the parameter and action plan.
8. **QA and document** (checklist below).

## Three style modes

| | Corporate (work default) | Product style (portfolio) | Editorial (portfolio) |
|---|---|---|---|
| Audience | Busy business users | Showcase, power users | Public storytelling |
| Interactivity | Simple, lots of quick and easy filters, few hidden tricks | Parameter switches, show/hide panels, nav bar, multiple views | Guided, one strong interaction |
| Layout | Tiled skeleton, 227px left nav; floating only for small overlays and drawers (0 to 3) | Tiled skeleton, floating info panels (1 to 8) | Heavily floating (12 to 49), poster canvas |
| Data | Published data sources | Embedded extracts | Embedded |
| Type | Arial family | Tableau Book/Bold, Lato, Trebuchet | Serif display (Georgia), letter-spaced caps |
| Colour | Brand palette, one primary blue | Greyscale plus one accent | Subject-led palette |
| Size | Fixed 1500x1100 or 1500x1250 (also 1500x1000, 1300x1000) | Fixed 1360x900, 1600x1000 | Fixed 1400x900 / 1600x900, or long 1400x1850 to 1200x3200 |
| Cards | White, 1px #F5F5F5 border, padding 10, 10px gutters, radius 10 (2026) | White, 1px #F5F5F5, padding 15 | Rarely carded |

Corporate still needs a clean, polished feel. It is "dumbed down for usability", never plain or careless. Even in corporate mode, offer multiple views through a dynamic switch or parameter when it saves building a second dashboard.

**Performance is the corporate rule for interactivity.** The dashboard must stay fast and keep its flow. Prefer simple quick filters, and use parameters where they are cheaper than filter logic. Avoid anything that slows rendering: stacks of complicated or context-dependent filters, heavy table calcs over large row counts, many sheets hidden behind DZV that still query, too many filter actions chained together. If a clever technique costs speed, choose the simple one and say so.

## Look and feel (every mode)

- **Clean formatting and flow.** The eye should move top-left to bottom-right through a clear story, with nothing competing.
- **Strong typography.** Use font size, weight and CAPS vs lowercase to set hierarchy rather than colour or boxes.
- **Moderate numbers.** BANs should be clear but not shouting. Avoid oversized numbers that dominate the card, and tiny labels that strain the eye. Work defaults: BAN 18pt, card title 11pt black, subtitle 8pt #898989, axis and labels 7 to 8pt #898989.
- **White space.** Give generous, consistent padding so the eye can pause between elements. When in doubt, add space rather than content.

## The KPI card (signature pattern)

This is used across almost every business dashboard:
- Metric name as a title (lighter weight).
- A big number (BAN), rounded to 1 decimal.
- A change line, for example "▲ 3.2% from last week" or "-78% from last month", in green or red.
- A faint sparkline or bar trend underneath, with the selected period highlighted in the accent colour.
- A white card on a light grey canvas, with an optional arrow or click-through to detail.

The calc set behind each card is described in `references/calc-patterns.md` (Focus / Prior / Change / Change Colour).

## Be exact, not approximate

When you build, prototype or review, use the measured values in `references/spec-measured.md` (pixel templates, padding, borders, colours, font sizes, line styles, control types). For example:
- Say "left nav fixed 227, bg #FCFBFC, padding-top 30 / right 10 / bottom 30", not "a narrow nav".
- Say "card: horizontal container, white, 1px solid #F5F5F5, inner padding 10, outer margin 5 on facing sides", not "a card with some padding".
- When reviewing, compare every value against the Default column and list each mismatch with the exact fix. `scripts/profile_twb.py` measures a workbook in seconds.
- When building an HTML prototype, use the same pixel values so the prototype is a faithful preview of the Tableau build.

## Non-negotiables

- **Calc naming and comments.** Follow the standard in `references/calc-patterns.md`:
  - **Every calc gets a comment, 100%, including one-liners.**
  - Line 1 is `// <exact calc name>`, kept in sync on rename.
  - Add a purpose or why line whenever anything is not self-evident.
  - Lay out the formula one clause per line, with `THEN` indented 4 spaces.
  - Never leave `(copy)` names or `Parameter 4` in delivered work. Rename parameters to say what they do, and document them on the Documentation page, since parameters can't hold comments.
- **Sheet and dashboard naming.** Never leave `Sheet 24` or `Truck info (2)`. Use patterns that describe the job:
  - `<Metric> KPI`, `<Metric> KPI Trend`, `<Metric> KPI Compare`
  - `<Metric> Bar`, `<Dimension> by <Metric>`, `<Metric> by <Dimension> Trend`
  - `<Page> Dashboard Title`, `<Thing> Selector`, `Buttons`, `Show information` / `Hide information`
  - In big workbooks, prefix each sheet with its dashboard (for example `EX` for Executive) so sheets group together.

  Dashboards get plain, user-facing names (`Overview`, `Channel KPI Overview`, `Landing Pages`).
- **Highlight with parameters.** For "selected item" behaviour, use a parameter plus `[Param] = [Field]` T/F calc, with highlight or parameter actions. In corporate mode, prefer quick filters when users just need to slice.
- **Name every container** in the Item Hierarchy, including floating and hidden ones.
- **Label-only marks are hairline Gantt bars** (size 0.01, white, transparency 0), never Text marks; **button labels are a clear custom shape** (embedded Transparent.png). No scroll bars on any dashboard: size every grid inside its zone, and leave no unneeded space under the last row (14 px, the card gap). See `references/build-techniques.md`.
- **Colours come from the prototype's code**, not a screenshot (opacities on white turned into exact hex).
- **Tooltips:** ALL CAPS labels, the key metric in semibold, one layer deeper than the view. Turn tooltips off on text and BAN sheets unless they add value. Always turn off command buttons.
- **Number formats** are in `references/layout-and-format.md`.
- Every dashboard has a "Data updated on" line, and signposts for how to use it, data notes and contact. Corporate work also gets a Documentation page.
- In any text written for Gbolahan, use plain English and no em dashes.

## How to help, depending on the ask

### "Build" or "work on" a workbook (the main case)

Gbolahan usually arrives with two inputs:
1. **An MD spec document** they have already worked on: the calculations they identified, the dashboard flow, and stakeholder feedback folded in.
2. **An HTML prototype** they have refined with Claude to show how it should look.

Your job has two parts.

**A. Review the prototype and spec before building.** Check, and report briefly in order of importance:
- **Information:** Is the information right and complete against the brief and spec? Do the numbers and KPIs answer the stakeholder's questions?
- **Chart choice:** Is the right chart used for each question? Flag anything that would read faster as another form.
- **Labels and titles:** Are they clear, consistent, two-line title pattern where it fits, units and periods stated?
- **Gestalt principles:**
  - proximity (related things grouped)
  - similarity (same metric, same colour and style)
  - enclosure (cards, bands)
  - alignment and continuity (shared edges, eye path)
  - figure and ground (one accent against greyscale)
- **Cohesion, balance and white space:** even padding, balanced visual weight left to right, nothing cramped.
- **Typography:** clear hierarchy, sizes from the type scale, no oversized or tiny numbers.
- **Flow and simplicity:** the web-app feel (clear header, navigation, cards, obvious next click), with every element earning its place.
- **Tableau feasibility and performance:** call out anything the prototype shows that is hard or slow in Tableau, and the closest fast alternative.

Keep the prototype's intent. Suggest, don't redesign.

**B. Then build.** Deliver:
- **Calcs ready to paste**, using the naming and comment standard.
- **A sheet list with proper names.**
- **The container tree** with container names.
- **The parameter and action plan.**
- **Sheet-by-sheet build steps:** marks, shelves, formatting, tooltips.

Write `.twb` XML only if asked, and always work from a copy. When building in XML (as on Lineage Control Tower):
- Validate every build before sending it (schema, manifest flags, fit checks; `references/build-techniques.md` section 2).
- Give every rebuild a new version name and log it in the versions changelog with what changed and why.
- When Gbolahan sends an adjusted copy, diff it completely (sheets, dashboards, calc formulas), ignore Tableau's re-save noise, fold every real change into the builder and say what you took.
- If unsure how Tableau writes a feature, ask for a one-sheet Tableau-saved example instead of guessing twice.
- Add every new finding to `references/build-techniques.md` as it is made.

**One-shot tab recipe** (what got Usage, Data quality and Blast radius right first time on Lineage Control Tower):
1. **Fold in Gbolahan's last adjusted copy first:** diff it, take every real change into the builder, say what you took.
2. **Study before asking:** the prototype screenshot, its render code (the real rules: sorting, thresholds, caps, ties),
   the calc pack section and the build plan's container tree.
3. **Ask the design forks in one go** (up to four questions, recommended option first): native vs canvas per part,
   rows that do not fit (scroll, cap, "N more"), how a prototype-only behaviour maps to Tableau (copy to clipboard,
   clicks), and any spec vs prototype conflict. Ask again when an answer is "something else" without a note.
4. **Reproduce the prototype's numbers from the marts in Python** before writing a sheet (30 days, all platforms, and
   the prototype's checks). Where the calc pack and the prototype disagree, match the prototype and say so.
5. **Write the module from the proven patterns** (`references/build-techniques.md`): build-measured canvases with
   exact alignment, per-parameter CASE calcs for anything that depends only on the filters or the selection, carrier
   rows when a canvas needs more points than its data has, DZV on parameter-only calcs, fit checks that assert every
   canvas fits its zone and the rows end at the content edge.
6. **Prove it before sending:** build (schema and manifest validation run inside), a layout preview of the dashboard,
   and a simulation that draws every canvas from its real formulas for the prototype's case and one edge case. Read
   the simulation against the prototype and fix what differs (a wrong CASE key, a wrong colour, text that does not fit).
7. **Ship:** a new version name, a changelog row (what, why, what differs from the prototype, what to check first),
   the skill updated and synced, commit and push, and the file sent with a short note: what is on the tab, what
   differs from the prototype, and the two or three new techniques to look at first.

### Other asks

- **"Plan" or "mock up" without a prototype:** go through steps 1 to 6, then offer a quick HTML prototype plus a build plan.
- **"Review" a workbook:** run `python3 -I scripts/profile_twb.py <file>` (it reads the XML only and never touches extract data), and use `references/xml-anatomy.md` to locate anything else. Check it against `references/spec-measured.md` and this skill: naming, comments, `(copy)` leftovers, padding consistency, fonts, colours outside the palette, tooltip settings, unnamed containers, floating objects in corporate mode beyond small overlays and drawers, and missing "Data updated on" or documentation. Report findings in order of importance, with the fix.
- **Calc help:** match the patterns in `references/calc-patterns.md` and explain the why in a comment.

## QA checklist before publishing

1. Numbers reconcile with a known source total for at least one period.
2. The period logic is correct at boundaries: January vs December prior month, week 1 vs week 53, year rollover.
3. Change colours point the right way, including inverse metrics (bounce rate, cost per lead, missed appointments).
4. Nulls and zero denominators show "-" or are hidden, never errors or misleading 0%.
5. All interactions are tested: every switch value, every show/hide, every nav button, and reset states.
6. Fonts, padding and colours are consistent. Sheet edges align.
7. Tooltips are formatted, and command buttons are off.
8. There are no `(copy)` names or unused calcs. **Every** calc has a `// <exact name>` header (run `scripts/profile_twb.py`; `hygiene.calc_missing_header` and `hygiene.calc_header_drift` must be empty).
9. "Data updated on" is dynamic. The Documentation page is current, including the change log.
10. The layout is checked at the published size. Corporate work is checked on Server or Cloud, not just Desktop.

## References

- `references/calc-patterns.md`: naming standard, period comparison pairs, switches, show/hide, highlighting, ranking, pagination and advanced techniques. Read it when writing or reviewing calcs.
- `references/layout-and-format.md`: container skeleton, padding, type scale, number formats, colour rules, tooltips, buttons, chart titles and the documentation template. Read it when designing, prototyping or reviewing layout.
- `references/spec-measured.md`: **exact measured values**. Pixel templates for the work, product and editorial layouts; padding, margins, borders, corner radius, dividers, nav and button sizes, fonts and sizes, sheet formatting, line styles, controls, tooltips, actions, hygiene benchmarks and how the style changed from 2022 to 2026. Read it before any build, prototype or review.
- `references/build-techniques.md`: proven build patterns from Lineage Control Tower: how to work with Gbolahan's adjusted files, validation and manifest flags, label marks and button labels, label alignment, pixel canvases of map panes, rounded polygons, zone sizing and content height, native and canvas tables, time charts that line up, the selected-bar border and window band, palettes, parameter-driven DZV, dehighlight and Go to Sheet actions, axis and number formats, and what did not work. Read it before building anything in Tableau XML.
- `references/xml-anatomy.md`: everything a `.twb` / `.twbx` contains, where every setting lives in the XML, coordinate maths, safe editing rules, and how the anatomy differs by mode. Read it when parsing, reviewing or editing workbook XML.
- `scripts/profile_twb.py`: measures one or more workbooks (or groups) against the spec. It prints every formatting value with frequencies, layout pixel measures and hygiene checks.
- `references/work-brand.md`: private work brand palette and logo rules. Read it only for work (corporate mode). Never copy its contents into public repos, Tableau Public or anything shared outside work.
