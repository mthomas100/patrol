"""Static SVG diagrams and charts for the explainer, injected into index.html by build.py.

Each figure is a function returning an <svg> string. index.html holds matching markers:
    <!-- FIG:name --> ... <!-- /FIG:name -->
Colours come from the page's CSS tokens (var(--clef) and so on), so every figure follows the light and dark themes.
Chart numbers live in DATA below, each with the file it came from; change them there, then run build.py.
"""
from html import escape

FONT = "var(--font-display)"
MONO = "var(--font-mono)"


def _t(x, y, s, size=11, anchor="start", weight=400, fill="var(--ink-2)", family=FONT, extra=""):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}"{extra}>{escape(s)}</text>')


def _halo(x, y, s, size=10.5, anchor="middle", fill="var(--ink-2)", weight=400, family=FONT):
    return _t(x, y, s, size, anchor, weight, fill, family,
              ' stroke="var(--paper-2)" stroke-width="4" paint-order="stroke" stroke-linejoin="round"')


def _defs(*ids):
    out = ['<defs>']
    for mid, col in ids:
        out.append(f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
                   f'orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="{col}"/></marker>')
    out.append('</defs>')
    return ''.join(out)


def _path(d, col="var(--ink-3)", w=1.4, marker="ah", dash=None):
    da = f' stroke-dasharray="{dash}"' if dash else ''
    mk = f' marker-end="url(#{marker})"' if marker else ''
    return f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round"{da}{mk}/>'


# --------------------------------------------------------------------------------------------- architecture
ROLE = {  # stroke, fill, dot
    'person': ('var(--ink-2)', 'var(--paper-2)', 'var(--ink-2)'),
    'voice': ('var(--voice)', 'var(--paper-2)', 'var(--voice)'),
    'clef': ('var(--clef)', 'var(--paper-2)', 'var(--clef)'),
    'qwen': ('var(--qwen)', 'var(--paper-2)', 'var(--qwen)'),
    'finder': ('var(--finder)', 'var(--paper-2)', 'var(--finder)'),
    'code': ('var(--ink)', 'var(--paper-3)', 'var(--ink)'),
    'sensor': ('var(--ink-3)', 'var(--paper-2)', 'var(--ink-3)'),
    'data': ('var(--ink-3)', 'var(--paper-2)', None),
    'alert': ('var(--blaze)', 'var(--blaze-wash)', 'var(--blaze)'),
}


def _node(x, y, w, h, title, lines, role, title_size=12.5):
    st, fill, dot = ROLE[role]
    dash = ' stroke-dasharray="4 3"' if role == 'data' else ''
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" stroke="{st}" stroke-width="1.6"{dash}/>']
    tx = x + 12
    if dot:
        out.append(f'<circle cx="{x + 14}" cy="{y + 17}" r="4" fill="{dot}"/>')
        tx = x + 24
    out.append(_t(tx, y + 21.5, title, title_size, weight=700, fill="var(--ink)"))
    for i, ln in enumerate(lines):
        out.append(_t(x + 12, y + 39 + i * 14, ln, 10.5, fill="var(--ink-2)"))
    return ''.join(out)


def architecture():
    W, H = 1120, 600
    C = [10 + i * 160 for i in range(7)]   # column x
    w, h = 136, 66
    R1, R2, R3 = 56, 206, 360               # row tops
    cx = lambda i: C[i] + w / 2
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="How Patrol\'s models connect: voice and qwen38 turn the '
         f'description into clue cards before take-off; every 12 metres a photo goes through the CPU finder, Clef-Flash and a '
         f'code gate, with a closer look and a Clef-Flash confirm for maybes; alerts go to the radio, and qwen38 writes the '
         f'note, which Kokoro reads aloud, and a trail plan that code checks before the planner reorders the sectors. Code '
         f'owns safety throughout.">',
         _defs(('ah', 'var(--ink-3)'), ('ahb', 'var(--blaze)'), ('ahq', 'var(--qwen)'))]
    band = lambda y, label, sub: (_t(10, y - 14, label, 10.5, weight=600, fill="var(--ink)", family=MONO,
                                     extra=' letter-spacing="1.2"') + _t(10 + len(label) * 7.6 + 14, y - 14, sub, 10.5,
                                                                         fill="var(--ink-3)"))
    o.append(band(R1, 'BEFORE TAKE-OFF', 'words become a search'))
    o.append(band(R2, 'EVERY 12 METRES OF FLIGHT', 'the fast loop, about 0.3 s per look'))
    o.append(band(R3, 'A FEW TIMES A FLIGHT', 'the slow loop, seconds, never holds up the flying'))

    # row 1
    o.append(_node(C[0], R1, w, h, 'Operator', ['hold to talk at', 'the trailhead'], 'person'))
    o.append(_node(C[1], R1, w, h, 'Parakeet', ['speech to text', '20 to 90 ms'], 'voice'))
    o.append(_node(C[2], R1, w, h, 'Clef-Flash', ['description or', 'command?'], 'clef'))
    o.append(_node(C[3], R1, w, h, 'qwen38', ['writes how each clue', 'looks from above'], 'qwen'))
    o.append(_node(C[4], R1, w, h, 'Clue cards', ['words and a size', 'per clue'], 'data'))
    o.append('<g>' + _t(C[5] + 4, R1 + 20, '“a bag with shoulder straps', 10.5, fill="var(--ink-3)")
             + _t(C[5] + 4, R1 + 34, 'and pockets, about half a', 10.5, fill="var(--ink-3)")
             + _t(C[5] + 4, R1 + 48, 'metre long” · 0.55 m', 10.5, fill="var(--ink-3)") + '</g>')
    for i in range(4):
        o.append(_path(f'M{C[i] + w} {R1 + h / 2} H{C[i + 1] - 3}'))
    o.append(_halo((C[0] + w + C[1]) / 2, R1 + h / 2 - 7, 'voice', 9.5))
    o.append(_halo((C[1] + w + C[2]) / 2, R1 + h / 2 - 7, 'text', 9.5))
    o.append(_halo((C[2] + w + C[3]) / 2, R1 + h / 2 - 7, 'a description', 9.5))
    o.append(_halo((C[3] + w + C[4]) / 2, R1 + h / 2 - 7, 'cards', 9.5))

    # clue cards feed the planner (size) and both Clef questions (words)
    xc = cx(4) + 18
    o.append(_path(f'M{xc} {R1 + h} V150', marker=None))
    o.append(_path(f'M{xc} 150 H{cx(0) - 20} V{R2 - 3}'))
    o.append(_path(f'M{cx(3) + 10} 150 V{R2 - 3}'))
    o.append(_path(f'M{xc} 150 H{cx(6)} V{R2 - 3}'))
    o.append(_halo(cx(1) - 6, 146, 'smallest clue sets the sweep height', 9.5))
    o.append(_halo((xc + cx(6)) / 2 + 6, 146, 'clue words go into every question', 9.5))
    # spoken commands go to the code that flies
    o.append(_path(f'M{cx(2) - 10} {R1 + h} V182 H{cx(4) - 24} V{R2 - 3}', dash='5 3'))
    o.append(_halo((cx(2) + cx(4)) / 2 - 18, 178, 'a command: go back, come home', 9.5))

    # row 2
    o.append(_node(C[0], R2, w, h, 'Planner', ['lanes and sectors,', 'code'], 'code'))
    o.append(_node(C[1], R2, w, h, 'Camera', ['1280×960 photo,', 'straight down'], 'sensor'))
    o.append(_node(C[2], R2, w, h, 'Finder', ['rare colours, CPU,', 'top 3 odd spots'], 'finder'))
    o.append(_node(C[3], R2, w, h, 'Clef-Flash', ['is this crop a clue?', 'about 0.3 s each'], 'clef'))
    o.append(_node(C[4], R2, w, h, 'Gate', ['act on the odds?', 'code, with fallback'], 'code'))
    o.append(_node(C[5], R2, w, h, 'Closer look', ['fly over, 20 m, zoom;', '12 m if unsure'], 'code'))
    o.append(_node(C[6], R2, w, h, 'Clef-Flash', ['confirm or dismiss', 'the close-up'], 'clef'))
    labels2 = ['lanes', 'photo', '3 crops', 'odds', 'maybe', 'close-up']
    for i in range(6):
        o.append(_path(f'M{C[i] + w} {R2 + h / 2} H{C[i + 1] - 3}', col='var(--ink-3)', marker='ah'))
        o.append(_halo((C[i] + w + C[i + 1]) / 2, R2 + h / 2 - 7, labels2[i], 9.5))
    # continue loop and "no" loop
    o.append(_path(f'M{cx(4)} {R2 + h} V300 H{cx(1)} V{R2 + h + 3}'))
    o.append(_path(f'M{cx(6) - 30} {R2 + h} V300 H{cx(4)}', marker=None))
    o.append(_halo((cx(1) + cx(4)) / 2, 314, 'continue: most spots, and every dismissed close-up, go back to the lane', 9.5))
    # yes -> alert
    o.append(_path(f'M{cx(6) + 30} {R2 + h} V{R3 - 3}', col='var(--blaze)', w=1.8, marker='ahb'))
    o.append(_halo(cx(6) + 50, 296, 'yes', 10, fill="var(--blaze-ink)", weight=700))

    # row 3
    o.append(_node(C[6], R3, w, h, 'ALERT', ['position, photo,', 'confidence'], 'alert'))
    o.append(_node(C[3], R3, C[5] + w - C[3], h, 'qwen38, the slow thinker',
                   ['writes the radio note, plans where to look next,', 'gives a second opinion on a close call; 2 to 5 s a job'], 'qwen'))
    o.append(_node(C[2], R3, w, h, 'Kokoro', ['reads each note', 'aloud to you'], 'voice'))
    o.append(_node(C[1], R3, w, h, 'Code check', ['known sectors not', 'yet searched'], 'code'))
    o.append(_path(f'M{C[6]} {R3 + h / 2} H{C[5] + w + 3}', col='var(--qwen)', marker='ahq'))
    o.append(_path(f'M{C[3]} {R3 + 22} H{C[2] + w + 3}', col='var(--qwen)', marker='ahq'))
    o.append(_halo((C[2] + w + C[3]) / 2, R3 + 16, 'note', 9.5))
    o.append(_path(f'M{C[3] + 30} {R3 + h} V446 H{cx(1)} V{R3 + h + 3}', col='var(--qwen)', marker='ahq'))
    o.append(_halo((cx(1) + C[3] + 30) / 2, 442, 'trail plan', 9.5))
    o.append(_path(f'M{C[1]} {R3 + h / 2} H{cx(0)} V{R2 + h + 3}'))
    o.append(_halo(cx(0), R3 + h / 2 - 7, 'reorder', 9.5))
    # radio
    o.append(f'<rect x="{C[6]}" y="{R3 + h + 26}" width="{w}" height="30" rx="15" fill="var(--paper-2)" stroke="var(--ink-3)" stroke-width="1.2"/>')
    o.append(_t(cx(6), R3 + h + 45, 'radio + console', 11, anchor="middle", weight=600, fill="var(--ink)"))
    o.append(_path(f'M{cx(6)} {R3 + h} V{R3 + h + 23}', col='var(--blaze)', marker='ahb'))

    # safety bar
    y = 522
    o.append(f'<rect x="10" y="{y}" width="{C[6] + w - 10}" height="56" rx="8" fill="none" stroke="var(--ink)" stroke-width="1.6"/>')
    o.append(_t(24, y + 22, 'SAFETY · CODE, ALWAYS ON', 10.5, weight=600, fill="var(--ink)", family=MONO, extra=' letter-spacing="1.2"'))
    o.append(_t(24, y + 41, 'Height 8 to 70 m · stays within 25 m of the search area · keeps 10% battery for the trip home · '
                            'flies home when the area is done, the battery is low, or you say so · no model can override it.', 11,
                fill="var(--ink-2)"))
    o.append('</svg>')
    return ''.join(o)


# --------------------------------------------------------------------------------------------- altitude side view
def altitude():
    W, H = 1000, 400
    G = 340                       # ground line y
    m = 6.0                       # px per metre, both axes (true geometry)
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Side view, to scale. Left: two sweep lanes at 40 metres, 22.9 '
         f'metres apart; each photo sees 32.6 metres of ground across the lane, so neighbouring lanes overlap. Right: a closer '
         f'look, with the drone 12 metres short of the spot at 20 metres and the zoom framed to about 4 metres of ground, and a '
         f'second step at 12 metres only if the answer is unsure.">', _defs(('ah', 'var(--ink-3)'))]
    o.append(f'<line x1="0" y1="{G}" x2="{W}" y2="{G}" stroke="var(--ink-3)" stroke-width="1.4"/>')
    o.append(f'<rect x="0" y="{G}" width="{W}" height="{H - G}" fill="var(--paper-3)"/>')
    # height ruler
    for z in (0, 12, 20, 40):
        y = G - z * m
        o.append(f'<line x1="34" y1="{y}" x2="42" y2="{y}" stroke="var(--ink-3)" stroke-width="1"/>')
        o.append(_t(30, y + 3.5, f'{z} m', 9.5, anchor="end", fill="var(--ink-3)", family=MONO))
    o.append(f'<line x1="42" y1="{G}" x2="42" y2="{G - 40 * m}" stroke="var(--ink-3)" stroke-width="1"/>')

    def drone(x, y, col="var(--ink)"):
        return (f'<g><line x1="{x - 13}" y1="{y}" x2="{x + 13}" y2="{y}" stroke="{col}" stroke-width="2.2"/>'
                f'<circle cx="{x - 13}" cy="{y - 2}" r="4.2" fill="none" stroke="{col}" stroke-width="1.6"/>'
                f'<circle cx="{x + 13}" cy="{y - 2}" r="4.2" fill="none" stroke="{col}" stroke-width="1.6"/>'
                f'<rect x="{x - 5}" y="{y - 3}" width="10" height="7" rx="2" fill="{col}"/></g>')

    # left: two lanes at 40 m, across-track view (camera 44.4 degrees across, 32.6 m footprint)
    lane_gap, half = 22.86, 16.3
    xa = 150 + half * m - 30
    xb = xa + lane_gap * m
    yd = G - 40 * m
    for x, op in ((xa, '0.10'), (xb, '0.07')):
        o.append(f'<path d="M{x} {yd + 6} L{x - half * m} {G} L{x + half * m} {G} Z" fill="var(--clef)" fill-opacity="{op}" '
                 f'stroke="var(--clef)" stroke-opacity="0.5" stroke-width="1"/>')
        o.append(drone(x, yd))
    o.append(_t((xa + xb) / 2, yd - 18, 'two neighbouring lanes, seen end-on', 11.5, anchor="middle", weight=700, fill="var(--ink)"))
    # dimension: lane gap
    yy = yd - 4
    o.append(_path(f'M{xa + 20} {yy} H{xb - 20}', marker='ah'))
    o.append(_path(f'M{xb - 20} {yy} H{xa + 20}', marker='ah'))
    o.append(_halo((xa + xb) / 2, yy + 16, '22.9 m between lanes', 10))
    # dimension: footprint
    yf = G + 22
    o.append(_path(f'M{xa - half * m + 2} {yf} H{xa + half * m - 2}', marker='ah'))
    o.append(_path(f'M{xa + half * m - 2} {yf} H{xa - half * m + 2}', marker='ah'))
    o.append(_t(xa, yf + 16, '32.6 m of ground in each photo', 10.5, anchor="middle", fill="var(--ink-2)"))
    o.append(_t(xb + half * m - 6, G - 12, 'overlap', 10, anchor="end", fill="var(--ink-3)"))

    # right: the closer look (20 m, 12 m short; then 12 m, 7.2 m short)
    sx = 830
    o.append(f'<rect x="{sx - 1.65}" y="{G - 1.6}" width="3.3" height="1.6" fill="var(--blaze)"/>')
    o.append(f'<circle cx="{sx}" cy="{G}" r="5" fill="none" stroke="var(--blaze)" stroke-width="1.6"/>')
    for zh, back, op, lab in ((20, 12, 1, 'first look at 20 m'), (12, 7.2, 0.55, 'second step at 12 m, only if unsure')):
        dx, dy = sx - back * m, G - zh * m
        col = 'var(--blaze)' if op == 1 else 'var(--ink-3)'
        o.append(f'<path d="M{dx} {dy + 5} L{sx - 2 * m} {G} L{sx + 2 * m} {G} Z" fill="var(--blaze)" fill-opacity="{0.14 * op:.2f}" '
                 f'stroke="{col}" stroke-opacity="0.7" stroke-width="1"/>')
        o.append(drone(dx, dy, col))
        o.append(_t(dx - 22, dy + 4, lab, 10.5, anchor="end", fill="var(--ink-2)", weight=600 if op == 1 else 400))
    o.append(_t(sx, G - 40 * m - 18, 'a closer look at one spot', 11.5, anchor="middle", weight=700, fill="var(--ink)"))
    o.append(_t(sx + 20, G - 30 * m, 'hover 0.6 × the height', 10.5, fill="var(--ink-2)"))
    o.append(_t(sx + 20, G - 30 * m + 14, 'short of the spot, about', 10.5, fill="var(--ink-2)"))
    o.append(_t(sx + 20, G - 30 * m + 28, '31° off vertical; the zoom', 10.5, fill="var(--ink-2)"))
    o.append(_t(sx + 20, G - 30 * m + 42, 'frames about 4 m of ground', 10.5, fill="var(--ink-2)"))
    o.append(_t(sx, G + 22, 'backpack, 0.55 m', 10.5, anchor="middle", fill="var(--blaze-ink)", weight=600))
    o.append(_t(sx, G + 36, '(drawn to scale)', 9.5, anchor="middle", fill="var(--ink-3)"))
    o.append('</svg>')
    return ''.join(o)


FIGURES = {
    'arch': architecture,
    'alt': altitude,
}
