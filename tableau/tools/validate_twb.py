"""Check a built .twb before it goes to Tableau.

1. Schema: validate against Tableau's 2026.1 XSD (tableau/tools/xsd). Feature-flagged names
   (`_.fcp.<Flag>.true...name`) are read as their plain names, as Tableau does when the flag is on.
2. Manifest: every feature the workbook uses must be declared in <document-format-change-manifest>, or Tableau
   stops with "no declaration found" (v07 without <Layers />, v19 without <NavigationAction />).

Usage: python3 tableau/tools/validate_twb.py <file.twb>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

XSD = Path(__file__).resolve().parent / 'xsd' / 'twb_2026.1.0.xsd'

# Known, harmless schema complaints about what Tableau itself writes on the master workbook
BASELINE = (
    re.compile(r"Element 'workbook', attribute '(author-id|creator-author-id|creator-license-type|creator-machine-id|license-type|machine-id)'"),
    re.compile(r"Element 'workbook': Missing child element\(s\)\. Expected is one of \( (thumbnails|external|referenced-extensions)"),
)

# element or attribute in use -> manifest flag Tableau needs before it accepts it
FEATURES = [
    (re.compile(r'<nav-action '), 'NavigationAction'),
    (re.compile(r'<computed-sort '), 'SortTagCleanup'),
    (re.compile(r'<computed-sort '), 'IntuitiveSorting'),
    (re.compile(r'<computed-sort '), 'IntuitiveSorting_SP2'),
    (re.compile(r"customization-axis='layer'"), 'Layers'),
    (re.compile(r'<edit-parameter-action '), 'ParameterAction'),
    (re.compile(r'<dashboard-zone-visibility-node '), 'DatagraphNodeDashboardZoneVisibilityV1'),
]


def check(path: str | Path) -> list[str]:
    return check_text(Path(path).read_text(encoding='utf-8'))


def check_text(t: str) -> list[str]:
    problems = []
    manifest = re.search(r'<document-format-change-manifest>(.*?)</document-format-change-manifest>', t, re.S)
    declared = set(re.findall(r'<([A-Za-z0-9_.]+) />', manifest.group(1))) if manifest else set()
    for pat, flag in FEATURES:
        if pat.search(t) and flag not in declared:
            problems.append(f'manifest: uses a feature that needs <{flag} />, which is not declared')
    try:
        from lxml import etree
    except ImportError:
        problems.append('schema: lxml not installed, schema check skipped')
        return problems
    schema = etree.XMLSchema(etree.parse(str(XSD)))
    plain = re.sub(r'_\.fcp\.[A-Za-z0-9]+\.(?:true|false)\.\.\.', '', t)
    schema.validate(etree.fromstring(plain.encode('utf-8')))
    lines = plain.split('\n')
    for e in schema.error_log:
        if any(b.search(e.message) for b in BASELINE):
            continue
        problems.append(f'schema line {e.line}: {e.message}\n    {lines[e.line - 1].strip()[:160]}')
    return problems


if __name__ == '__main__':
    found = check(sys.argv[1])
    print('\n'.join(found) or 'valid')
    sys.exit(1 if any(not p.startswith('schema: lxml') for p in found) else 0)
