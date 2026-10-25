"""Card geometry (build plan 3.1, v11): exposure tiles, alert rows and group headers drawn on fixed map panes.

Every rounded rectangle (card border and fill, coloured top edge, status dot, pills, chips) is a polygon in the
pane's own pixel space, so it lands exactly where it is placed: the pane's Latitude / Longitude axes are fixed to
px / 100 around its centre. v10 drew cards as custom shape images, but Tableau rescales shape marks to the pane
when a field is on Size and has no fixed pixel scale without one, so the cards came out huge and clipped.

A polygon needs a path: the 90 days of Exposure Daily (tiles, headers) or Node Daily (alerts) give 90 points per
node; points 0 to 87 walk the four corner arcs (22 points each) and the straight edges join them.

Text sits on a hairline, clear Gantt bar at a point (GB's standard for label-only marks), one layer per line.
Label alignment places the label beside its point: right = the line starts at the point, left = it ends there,
center = it is centred on it. (A multi-line label is also justified by that alignment, hence one line per layer.)

    python3 tableau/tools/lct_build/shapes.py      # redraw Transparent.png
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageFont

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'tableau' / 'Shapes' / 'LCT'
FOLDER = 'LCT'
FONT_R = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'  # metric-compatible with Arial
FONT_B = '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
TRANSPARENT = f'{FOLDER}/Transparent.png'

PX = 4 / 3       # Tableau draws text at 96 dpi: 9pt Arial is 12px (v09 screenshot: "Board KPI Pack" 89px)
LABEL_GAP = 4    # Tableau leaves about 4px between a point and a label placed beside it (v10 screenshot)

# ---------------------------------------------------------------- geometry (px)
# Zone widths come from the dashboard layout (health.content, build plan 3.1): the exposure card is fixed at
# 881 px with 16 px padding and a 1 px border, the right column at 417 px. Grids are sized a few px inside their
# zone, so Tableau never adds a scroll bar; build_workbook checks this against the laid-out zones.
EXPOSURE_CARD_W, RIGHT_COLUMN_W = 881, 417
TILE_ZONE_W = EXPOSURE_CARD_W - 2 * 16 - 2          # 847
ALERT_ZONE_W = RIGHT_COLUMN_W - 2 * 16 - 2          # 383
SLACK = 4
# a map canvas needs this much spare width in its zone, or Tableau draws a horizontal scroll bar: v48 showed one at
# 4 and 8 px spare (Governance hygiene, Freshness late now, Usage ranked) and none at 14 (Governance domain)
MAP_SLACK = 12

TILE_PANE = ((TILE_ZONE_W - SLACK) // 5, 68)        # 168 x 68: 5 across, 6px between rows
TILE_W, TILE_H = TILE_PANE[0] - 8, 62               # 160 x 62 card, 8px between columns (prototype .xgrid)
TILE_PAD = 10                                       # .xtile padding 8px 10px
TILE_LINES = {'name': 16, 'meta': 32, 'trust': 48}  # line centres (y) on the card
TILE_DOT = (TILE_W - 15, 16, 4)                     # centre x, centre y, radius
TILE_EDGE = 3                                       # coloured top edge height
AI_PILL = (47, 16, 4)                               # w, h, radius (.tag.ai)
TRUST_W = {'Critical': 47.8, 'Warning': 73.5, 'Healthy': 33.4}   # trust text width, Arial bold 7pt

ALERT_PANE = (ALERT_ZONE_W - SLACK, 84)             # 379 x 84: 8px between alerts
ALERT_W, ALERT_H = ALERT_PANE[0] - 4, 76            # 375 x 76 card
ALERT_TEXT_X = 37
ALERT_ICON = (19, 18, 16)                           # icon centre x, y and size
ALERT_LINES = {'name': 17, 'reason': 32, 'time': 45, 'meta3': 45, 'meta4': 58}
TAG = (52, 16, 4)                                   # INC tag: .tag 10px text, padding 1px 6px, radius 4

HEADER_PANE = (TILE_PANE[0] * 5, 18)
COUNT = (24, 14, 7)                                 # group count chip


def text_width(s, pt, bold=False) -> float:
    f = ImageFont.truetype(FONT_B if bold else FONT_R, round(pt * PX * 8))
    return f.getlength(s) / 8


def ai_pill_x(status) -> float:
    """Centre x of the AI-built pill on a tile: just after the trust badge."""
    return TILE_PAD + TRUST_W[status] + 6 + AI_PILL[0] / 2


def draw_all():
    OUT.mkdir(parents=True, exist_ok=True)
    for p in OUT.glob('*.png'):
        p.unlink()
    Image.new('RGBA', (8, 8), (255, 255, 255, 0)).save(OUT / 'Transparent.png')


def embedded_xml() -> str:
    """<external><shapes> with every PNG in tableau/Shapes/LCT, base64 in 72-character lines as Tableau writes it."""
    import base64
    import textwrap
    out = ['  <external>', '    <shapes>']
    for p in sorted(OUT.glob('*.png')):
        b64 = base64.b64encode(p.read_bytes()).decode()
        out.append(f"      <shape name='{FOLDER}/{p.name}'>")
        out += ['        ' + line for line in textwrap.wrap(b64, 72)]
        out.append('      </shape>')
    out += ['    </shapes>', '  </external>']
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    draw_all()
    print('\n'.join(sorted(p.name for p in OUT.glob('*.png'))))
