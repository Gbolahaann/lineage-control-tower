"""Custom shapes (build plan 3.1, v10): the card backgrounds and pills, drawn as PNGs in their final colours.

Each card PNG carries everything that sits at a fixed place on the card (fill, border, coloured top edge,
status dot or icon, chevron, AI-built pill), so one Shape mark draws the whole card and only the text is
placed by Tableau on top. Shapes are mapped to a status key field (encoding attr='shape' in the data source
style, as in the OKRs reference) and keep their own colours: no colour is put on these marks.

The PNGs are written to tableau/Shapes/LCT/ (copy that folder into My Tableau Repository/Shapes to edit
with them) and embedded in the workbook's <external><shapes>, so the .twb and .twbx open anywhere.

    python3 tableau/tools/lct_build/shapes.py      # redraw the PNGs
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'tableau' / 'Shapes' / 'LCT'
FOLDER = 'LCT'
FONT_R = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'  # metric-compatible with Arial
FONT_B = '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'

# Tableau draws text at 96 dpi: 9pt Arial is 12px (checked against a v09 screenshot: "Board KPI Pack" 89px).
PX = 4 / 3
# Shape mark size: about 10px per size unit for the longest side of the image (v09 status dot: size 0.35 drew
# about 3.5px; the OKRs reference draws a 33px toggle at 3.3). If the cards come out too big or small, change
# this one number and every shape follows.
PX_PER_SIZE = 10.0
LINE_H = 1.17  # Tableau line height for Arial, as a share of the font size in px

# prototype tokens
CARD, LINE, OFFWHITE = '#FFFFFF', '#E6E7E2', '#F5F5F3'
GOOD, WARN, CRIT, NONE = '#2F9E6B', '#E8A33D', '#D2453F', '#A3ADB8'
WARN_INK, INK3 = '#93600F', '#7A838E'
WARN_TINT, CRIT_TINT = '#FDF3E1', '#FBEAE9'
AI_BG, AI_LINE = '#EEF0FB', '#D9DCF4'

# ---------------------------------------------------------------- geometry (px)
TILE_W, TILE_H, TILE_GAP = 162, 62, 8          # prototype .xtile 161 x 62, gap 8, 5 per row
TILE_PANE = (TILE_W + TILE_GAP, TILE_H + TILE_GAP)
TILE_PAD = 10                                  # text starts 10px in (.xtile padding 8px 10px)
TILE_TEXT_TOP = 9
TILE_DOT = (147, 16, 4)                        # centre x, centre y, radius
TRUST_PT, AI_PT = 7, 7
TRUST_W = {'Do not use': 47.8, 'Use with caution': 73.5, 'Trusted': 33.4}

ALERT_W, ALERT_H, ALERT_GAP = 372, 80, 8       # prototype .alert 368 wide, 68 to 80 tall, gap 8
ALERT_PANE = (376, ALERT_H + ALERT_GAP)
ALERT_TEXT_X, ALERT_TEXT_TOP = 37, 10
TAG_W, TAG_H = 52, 16                          # .tag: 10px text, padding 1px 6px, radius 4
COUNT_W, COUNT_H = 24, 14                      # group count chip
HEADER_PANE = (TILE_PANE[0] * 5, 22)


def lines_h(*pts) -> float:
    return sum(p * PX * LINE_H for p in pts)


def trust_centre_y() -> float:
    """Card y (px from the top) of the middle of the third text line (trust badge) on a tile."""
    return TILE_TEXT_TOP + lines_h(9, 8) + 7 * PX * LINE_H / 2


def size_for(w, h) -> float:
    return round(max(w, h) / PX_PER_SIZE, 3)


# ---------------------------------------------------------------- drawing
S = 8  # supersampling while drawing; saved at 2x


def _canvas(w, h):
    return Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))


def _save(img, w, h, name):
    OUT.mkdir(parents=True, exist_ok=True)
    img.resize((w * 2, h * 2), Image.LANCZOS).save(OUT / name)


def _rgba(hex_, a=1.0):
    h = hex_.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (round(255 * a),)


def _mask(w, h, box, r):
    m = Image.new('L', (w * S, h * S), 0)
    ImageDraw.Draw(m).rounded_rectangle([v * S for v in box], radius=r * S, fill=255)
    return m


def _card(w, h, fill, border, top=None, r=8):
    img = _canvas(w, h)
    img.paste(_rgba(border), (0, 0), _mask(w, h, (0, 0, w, h), r))
    inner = _mask(w, h, (1, 1, w - 1, h - 1), r - 1)
    img.paste(_rgba(fill), (0, 0), inner)
    if top:
        band = Image.new('L', img.size, 0)
        ImageDraw.Draw(band).rectangle([0, 0, w * S, 4 * S], fill=255)
        from PIL import ImageChops
        img.paste(_rgba(top), (0, 0), ImageChops.multiply(inner, band))
    return img


def _pill(d, box, fill, border, r):
    x0, y0, x1, y1 = (v * S for v in box)
    d.rounded_rectangle([x0, y0, x1, y1], radius=r * S, fill=_rgba(border))
    d.rounded_rectangle([x0 + S, y0 + S, x1 - S, y1 - S], radius=(r - 1) * S, fill=_rgba(fill))


TILE_STYLES = {  # status key -> fill, border, top edge, dot
    'Healthy': (CARD, LINE, None, GOOD),
    'Warning': (CARD, '#F1DDB8', WARN_TINT, WARN),
    'Critical': (CRIT_TINT, '#EDC3C0', CRIT, CRIT),
    'No data': (CARD, LINE, None, NONE),
}
TRUST_OF = {'Healthy': 'Trusted', 'Warning': 'Use with caution', 'Critical': 'Do not use', 'No data': 'Trusted'}


def ai_pill_box(status):
    x0 = TILE_PAD + TRUST_W[TRUST_OF[status]] + 6
    yc = trust_centre_y()
    return (x0, yc - 8, x0 + 47, yc + 8)


def tile_shape(status, ai) -> str:
    return f'{FOLDER}/Tile {status}{" AI" if ai else ""}.png'


def draw_tiles():
    for status, (fill, border, top, dot) in TILE_STYLES.items():
        for ai in (False, True):
            img = _card(TILE_W, TILE_H, fill, border, top)
            d = ImageDraw.Draw(img)
            cx, cy, r = TILE_DOT
            d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], fill=_rgba(dot))
            if ai:
                _pill(d, ai_pill_box(status), AI_BG, AI_LINE, 4)
            _save(img, TILE_W, TILE_H, tile_shape(status, ai).split('/')[1])


ALERT_STYLES = {  # status key -> fill, border, icon kind, icon colour
    'Critical': (CRIT_TINT, '#F2CDCA', 'crit', CRIT),
    'Warning': (WARN_TINT, '#F3E0BE', 'warn', WARN_INK),
    'Healthy': (OFFWHITE, LINE, 'none', NONE),
    'No data': (OFFWHITE, LINE, 'none', NONE),
}


def alert_shape(status) -> str:
    return f'{FOLDER}/Alert {status}.png'


def _icon(img, kind, colour, x, y, size=16):
    """The prototype's 12-unit status icons (ICON.crit / ICON.warn), drawn at 16px with the top-left at x, y."""
    k = size / 12 * S
    p = lambda u, v: (x * S + u * k, y * S + v * k)
    layer = _canvas(*(v // S for v in img.size))
    d = ImageDraw.Draw(layer)
    w = round(1.5 * k)
    if kind == 'warn':
        d.polygon([p(6, 1.2), p(11, 10.4), p(1, 10.4)], fill=_rgba(colour, .2))
        d.line([p(6, 4.6), p(6, 7.2)], fill=_rgba(colour), width=w)
        cx, cy = p(6, 8.75)
        d.ellipse([cx - w / 2, cy - w / 2, cx + w / 2, cy + w / 2], fill=_rgba(colour))
        for q in (p(6, 4.6), p(6, 7.2)):
            d.ellipse([q[0] - w / 2, q[1] - w / 2, q[0] + w / 2, q[1] + w / 2], fill=_rgba(colour))
    else:
        c0, c1 = p(0.5, 0.5), p(11.5, 11.5)
        d.ellipse([*c0, *c1], fill=_rgba(colour, .18))
        segs = [(p(4, 4), p(8, 8)), (p(8, 4), p(4, 8))] if kind == 'crit' else [(p(3.8, 6), p(8.2, 6))]
        for a, b in segs:
            d.line([a, b], fill=_rgba(colour), width=w)
            for q in (a, b):
                d.ellipse([q[0] - w / 2, q[1] - w / 2, q[0] + w / 2, q[1] + w / 2], fill=_rgba(colour))
    img.alpha_composite(layer)


def draw_alerts():
    for status, (fill, border, kind, colour) in ALERT_STYLES.items():
        img = _card(ALERT_W, ALERT_H, fill, border)
        _icon(img, kind, colour, 11, 10)
        d = ImageDraw.Draw(img)
        x, y = ALERT_W - 20, ALERT_H / 2
        d.line([((x - 2.5) * S, (y - 4) * S), ((x + 1.5) * S, y * S), ((x - 2.5) * S, (y + 4) * S)],
               fill=_rgba(INK3), width=round(1.3 * S), joint='curve')
        _save(img, ALERT_W, ALERT_H, alert_shape(status).split('/')[1])


TAG_SHAPE = f'{FOLDER}/Tag.png'
COUNT_SHAPE = f'{FOLDER}/Count.png'
TRANSPARENT = f'{FOLDER}/Transparent.png'


def draw_small():
    img = _canvas(TAG_W, TAG_H)
    _pill(ImageDraw.Draw(img), (0, 0, TAG_W, TAG_H), OFFWHITE, LINE, 4)
    _save(img, TAG_W, TAG_H, 'Tag.png')
    img = _canvas(COUNT_W, COUNT_H)
    _pill(ImageDraw.Draw(img), (0, 0, COUNT_W, COUNT_H), OFFWHITE, LINE, 7)
    _save(img, COUNT_W, COUNT_H, 'Count.png')
    Image.new('RGBA', (8, 8), (255, 255, 255, 0)).save(OUT / 'Transparent.png')


def text_width(s, pt, bold=False) -> float:
    f = ImageFont.truetype(FONT_B if bold else FONT_R, round(pt * PX * 8))
    return f.getlength(s) / 8


def draw_all():
    draw_tiles()
    draw_alerts()
    draw_small()


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
