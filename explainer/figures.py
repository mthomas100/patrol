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
    o.append(band(R3, 'A FEW TIMES A FLIGHT', 'the slow loop, seconds; only a second opinion makes the drone wait'))

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
    o.append(_t(cx(6), R3 + h + 45, 'console (radio-sized)', 11, anchor="middle", weight=600, fill="var(--ink)"))
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
    o = [f'<svg viewBox="0 64 {W} {H - 64}" role="img" aria-label="Side view, to scale. Left: two sweep lanes at 40 metres, 22.9 '
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


# --------------------------------------------------------------------------------------------- state machine
def _pill(x, y, w, h, title, sub=None, kind='state'):
    st = {'state': ('var(--ink)', 'var(--paper-2)'), 'key': ('var(--ink)', 'var(--paper-3)'),
          'alert': ('var(--blaze)', 'var(--blaze-wash)'), 'clef': ('var(--clef)', 'var(--paper-2)'),
          'qwen': ('var(--qwen)', 'var(--paper-2)'), 'end': ('var(--ink-3)', 'var(--paper-2)')}[kind]
    o = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{min(h / 2, 18)}" fill="{st[1]}" stroke="{st[0]}" stroke-width="1.7"/>']
    if sub:
        o.append(_t(x + w / 2, y + h / 2 - 3, title, 12, anchor="middle", weight=700, fill="var(--ink)", family=MONO))
        o.append(_t(x + w / 2, y + h / 2 + 12, sub, 10.5, anchor="middle", fill="var(--ink-2)"))
    else:
        o.append(_t(x + w / 2, y + h / 2 + 4, title, 12, anchor="middle", weight=700, fill="var(--ink)", family=MONO))
    return ''.join(o)


def states():
    W, H = 1100, 404
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="The search state machine. Take off, then sweep. When a crop '
         f'passes the gate the drone investigates at 20 metres; Clef-Flash confirms (alert), dismisses (resume) or is unsure '
         f'(step down to 12 metres and ask again; if still unsure, qwen38 gives a second opinion while the drone hovers). '
         f'After the last spot it resumes the lane where it left. When the area is covered, the battery is low, a safety '
         f'limit is hit or you say so, it returns home.">', _defs(('ah', 'var(--ink-3)'), ('ahb', 'var(--blaze)'), ('ahq', 'var(--qwen)'))]
    Y, h = 168, 52
    o.append(_pill(20, Y, 110, h, 'TAKEOFF', 'straight up', 'end'))
    o.append(_pill(180, Y, 140, h, 'SWEEP', '40 m, 6 m/s, a photo', 'key'))
    o.append(_t(250, Y + h + 15, 'every 12 m', 10.5, anchor="middle", fill="var(--ink-2)"))
    o.append(_pill(380, Y, 160, h, 'INVESTIGATE', 'fly to the spot, 20 m'))
    o.append(_pill(600, Y, 150, h, 'CLOSE-UP', 'Clef-Flash verdict', 'clef'))
    o.append(_pill(830, 52, 130, h, 'ALERT', 'position + photo', 'alert'))
    o.append(_pill(830, Y, 130, h, 'RESUME', 'back to the lane'))
    o.append(_pill(600, 300, 150, h, 'STEP DOWN', '12 m, ask again'))
    o.append(_pill(830, 300, 160, h, '2ND OPINION', 'qwen38, drone hovers', 'qwen'))
    o.append(_pill(990, 52, 96, h, 'RETURN', None, 'end'))
    o.append(_pill(990, Y, 96, h, 'DONE', None, 'end'))
    m = lambda x1, y1, x2, y2: _path(f'M{x1} {y1} H{x2 - 3}' if y1 == y2 else f'M{x1} {y1} V{y2 - 3}')
    o.append(m(130, Y + h / 2, 180, Y + h / 2))
    o.append(_path(f'M320 {Y + h / 2} H{377}', col='var(--blaze)', marker='ahb'))
    o.append(_halo(350, Y + h / 2 - 9, 'maybe', 9.5, fill='var(--blaze-ink)', weight=700))
    o.append(m(540, Y + h / 2, 600, Y + h / 2))
    o.append(_halo(570, Y + h / 2 - 9, 'zoom', 9.5))
    # verdicts
    o.append(_path(f'M700 {Y} V{52 + h / 2} H827', col='var(--blaze)', marker='ahb'))
    o.append(_halo(765, 52 + h / 2 - 9, 'confirm', 10, fill='var(--blaze-ink)', weight=700))
    o.append(_halo(765, 52 + h / 2 + 18, 'named clue ≥ 50%', 9.5))
    o.append(m(750, Y + h / 2, 830, Y + h / 2))
    o.append(_halo(790, Y + h / 2 - 9, 'dismiss', 10, weight=700))
    o.append(_halo(790, Y + h / 2 + 20, 'all clues < 20%', 9.5))
    o.append(_path(f'M650 {Y + h} V297'))
    o.append(_halo(650, 262, 'in between', 9.5))
    o.append(_t(675, 368, 'then confirm or dismiss as above', 10, anchor="middle", fill="var(--ink-3)"))
    o.append(m(750, 326, 830, 326))
    o.append(_halo(790, 318, 'still unsure', 9.5))
    o.append(_path(f'M940 300 V{Y + h + 3}', col='var(--qwen)', marker='ahq'))
    o.append(_path(f'M975 300 V{52 + h / 2 + 10} H963', col='var(--qwen)', marker='ahq'))
    o.append(_halo(985, 262, 'qwen38 ≥ 60% sure:', 9.5, anchor='start'))
    o.append(_halo(985, 275, 'alert', 9.5, anchor='start'))
    o.append(_halo(932, 262, 'otherwise dismiss', 9.5, anchor='end'))
    o.append(_path(f'M895 {52 + h} V{Y - 3}'))
    o.append(_halo(895, 138, 'next spot or lane', 9.5))
    # resume back to sweep (under everything)
    o.append(_path(f'M895 {Y + h} V{Y + h + 50} H250 V{Y + h + 22}'))
    o.append(_halo(470, Y + h + 46, 'rejoin the lane where it left off; photos start again 12 m on', 9.5))
    # sweep -> return -> done
    o.append(_path(f'M250 {Y} V24 H1038 V{52 - 3}'))
    o.append(_halo(560, 20, 'area covered, battery reserve reached, a safety limit, or you say “come home”', 9.5))
    o.append(m(1038, 52 + h, 1038, Y))
    o.append(_t(20, 392, 'Any state: SAFETY (height 8 to 70 m, 25 m boundary, 10% battery for the trip home) sends the drone to RETURN. '
                         '“Go back to the last alert” sends it to INVESTIGATE.', 11, fill="var(--ink-2)"))
    o.append('</svg>')
    return ''.join(o)


# --------------------------------------------------------------------------------------------- funnel (log scale)
DATA = {
    # runs/s5-live-owner/summary.json (the real-time flight)
    'funnel': [
        ('control ticks (half-second steps)', 1234, 'var(--ink-3)', 'code'),
        ('sweep photos', 125, 'var(--ink-3)', 'camera'),
        ('odd spots boxed', 375, 'var(--finder)', 'finder, CPU'),
        ('crops judged', 163, 'var(--clef)', 'Clef-Flash'),
        ('closer looks', 8, 'var(--ink)', 'code flies'),
        ('close-ups judged', 8, 'var(--clef)', 'Clef-Flash'),
        ('alerts', 3, 'var(--blaze)', 'code'),
        ('qwen38 jobs', 6, 'var(--qwen)', '3 notes, 3 plans'),
        ('spoken alerts', 3, 'var(--voice)', 'Kokoro'),
    ],
    # weights resident while flying; GB. qwen38: measured (69.74 GiB resident weights);
    # Clef server 11 GB (measured); voice 2.68 GiB (measured); sim footprint 1.7 GB measured 15:12.
    'memory': [('qwen38', 70, 'var(--qwen)'), ('Clef-Flash', 11, 'var(--clef)'), ('voice', 2.7, 'var(--voice)'),
               ('simulator, finder, console', 1.7, 'var(--ink-3)')],
}


def funnel():
    rows = DATA['funnel']
    W, top, rh = 760, 34, 30
    H = top + rh * len(rows) + 34
    x0, x1 = 250, 690
    import math
    X = lambda v: x0 + (math.log10(v) / math.log10(2000)) * (x1 - x0)
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="From one real-time flight, on a log scale: 1,234 control ticks, '
         f'125 photos, 375 odd spots, 163 crops judged by Clef-Flash, 8 closer looks, 8 close-ups judged, 3 alerts, 6 qwen38 jobs '
         f'and 3 spoken alerts.">']
    for v in (1, 10, 100, 1000):
        o.append(f'<line x1="{X(v):.1f}" y1="{top - 8}" x2="{X(v):.1f}" y2="{top + rh * len(rows)}" stroke="var(--grid)" stroke-width="1"/>')
        o.append(_t(X(v), top + rh * len(rows) + 16, f'{v:,}', 9.5, anchor="middle", fill="var(--ink-3)", family=MONO))
    o.append(_t(x1, top + rh * len(rows) + 30, 'count, log scale', 9.5, anchor="end", fill="var(--ink-3)"))
    for i, (lab, v, col, who) in enumerate(rows):
        y = top + i * rh
        o.append(_t(x0 - 12, y + 14, lab, 12, anchor="end", fill="var(--ink)", weight=600))
        o.append(_t(x0 - 12, y + 26, who, 9.5, anchor="end", fill="var(--ink-3)"))
        w = max(4, X(v) - x0)
        o.append(f'<path d="M{x0} {y + 6} h{w - 4} a4 4 0 0 1 4 4 v6 a4 4 0 0 1 -4 4 h-{w - 4} z" fill="{col}"><title>{escape(lab)}: {v:,}</title></path>')
        o.append(_t(x0 + w + 8, y + 18, f'{v:,}', 12, fill="var(--ink)", weight=700, family=MONO))
    o.append('</svg>')
    return ''.join(o)


def memory():
    rows = DATA['memory']
    W, H = 760, 96
    x0, x1 = 10, 750
    sc = (x1 - x0) / 128
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Model weights resident during a flight against 128 GB of memory: '
         f'qwen38 about 70 GB, Clef-Flash about 11, voice 2.7, simulator and console 1.7; about 43 GB left for everything else.">']
    o.append(f'<rect x="{x0}" y="22" width="{x1 - x0}" height="26" rx="4" fill="var(--paper-3)"/>')
    x = x0
    for lab, v, col in rows:
        w = v * sc
        o.append(f'<rect x="{x:.1f}" y="22" width="{max(w - 2, 1):.1f}" height="26" fill="{col}"><title>{escape(lab)}: about {v} GB</title></rect>')
        x += w
    used = sum(v for _, v, _ in rows)
    o.append(_t(x0, 14, '0', 9.5, fill="var(--ink-3)", family=MONO))
    o.append(_t(x1, 14, '128 GB unified memory', 9.5, anchor="end", fill="var(--ink-3)", family=MONO))
    o.append(_t(x0 + 70 * sc / 2, 39.5, 'qwen38 · 70 GB', 11.5, anchor="middle", weight=700, fill="#fff"))
    o.append(_t(x0 + 70 * sc + 5.5 * sc, 66, 'Clef-Flash 11', 10.5, anchor="middle", fill="var(--ink-2)"))
    o.append(_t(x0 + 81 * sc + 2, 82, 'voice 2.7 · sim 1.7', 10.5, fill="var(--ink-2)"))
    o.append(_t(x + (x1 - x) / 2, 39.5, f'about {128 - used:.0f} GB for macOS, apps, caches', 10.5, anchor="middle", fill="var(--ink-2)"))
    o.append('</svg>')
    return ''.join(o)


def deploy():
    W, H = 1000, 250
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Two ways to field it. A: a computer in the search team\'s truck runs '
         f'every model; the drone sends live video over a short local radio link. B: the drone carries the finder, Clef-Flash and '
         f'the flight code; the base keeps qwen38 and voice; only alerts, about 270 bytes plus a 20 kilobyte photo, cross a weak '
         f'radio link.">', _defs(('ah', 'var(--ink-3)'))]

    def box(x, y, w, h, title, lines, col='var(--ink)'):
        r = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="var(--paper-2)" stroke="{col}" stroke-width="1.6"/>',
             _t(x + 12, y + 22, title, 12.5, weight=700, fill="var(--ink)")]
        for i, ln in enumerate(lines):
            r.append(_t(x + 12, y + 40 + i * 15, ln, 10.5, fill="var(--ink-2)"))
        return ''.join(r)
    for ox, lab, sub in ((0, 'A · TRUCK COMPUTER', 'closest to what runs today'), (510, 'B · SPLIT ACROSS A WEAK LINK', 'the drone decides; the base thinks')):
        o.append(_t(ox + 10, 18, lab, 10.5, weight=600, fill="var(--ink)", family=MONO, extra=' letter-spacing="1.2"'))
        o.append(_t(ox + 10, 34, sub, 10.5, fill="var(--ink-3)"))
    o.append(box(10, 56, 170, 92, 'Drone', ['camera and flight', 'controller only']))
    o.append(box(300, 56, 180, 150, 'Truck computer', ['finder, Clef-Flash,', 'qwen38, Parakeet,', 'Kokoro, flight code,', 'console', '(this laptop today)']))
    o.append(_path('M180 92 H297'))
    o.append(_path('M297 120 H183'))
    o.append(_halo(239, 86, 'live video', 10))
    o.append(_halo(239, 138, 'velocity', 10))
    o.append(_t(10, 236, 'Needs a video link of several Mbit/s within line of sight.', 10.5, fill="var(--ink-3)"))
    o.append(box(520, 56, 190, 150, 'Drone computer', ['camera, finder,', 'Clef-Flash (9B),', 'flight code and safety', '(needs an edge board', 'with about 12 GB free)'], 'var(--clef)'))
    o.append(box(810, 56, 180, 120, 'Base', ['qwen38, Parakeet,', 'Kokoro, console', 'and the operator'], 'var(--qwen)'))
    o.append(_path('M710 92 H807'))
    o.append(_path('M807 136 H713'))
    o.append(_halo(759, 86, 'alerts', 10, fill="var(--blaze-ink)", weight=700))
    o.append(_halo(759, 104, '0.3 KB + photo', 9.5))
    o.append(_halo(759, 154, 'clues, plans,', 9.5))
    o.append(_halo(759, 167, 'commands', 9.5))
    o.append(_t(520, 236, 'qwen38\'s jobs are slow and need no video, so a weak radio or mesh link is enough.', 10.5, fill="var(--ink-3)"))
    o.append('</svg>')
    return ''.join(o)


# --------------------------------------------------------------------------------------------- evidence charts
DATA['s0'] = [  # runs/s0-altitude-1280/probe.jsonl via facts digest 1A and 1D: (label, backpack med, min, max, tarp med, min, max)
    ('grass · 256 px crop from 40 m', 0.85, 0.84, 0.87, 0.28, 0.16, 0.30),
    ('snow · 256 px crop from 40 m', 0.80, 0.73, 0.85, 0.07, 0.06, 0.09),
    ('grass · close-up at 20 m', 0.95, 0.94, 0.96, 0.04, 0.04, 0.05),
    ('snow · close-up at 20 m', 0.94, 0.91, 0.94, 0.03, 0.02, 0.04),
    ('grass · close-up at 12 m', 0.95, 0.94, 0.96, 0.03, 0.03, 0.04),
    ('snow · close-up at 12 m', 0.96, 0.96, 0.96, 0.02, 0.02, 0.03),
]
DATA['live_after'] = {'found': (14, 14), 'false': (0, 7), 'clef_calls': (1235, 4860)}   # runs/s6-live-vs-after
DATA['trail'] = [('seed 5', 93.5, 109.0), ('seed 6', 91.0, 134.5)]                      # runs/s3-trail-ab-lock


def _legend(x, y, items):
    o, cx = [], x
    for lab, col in items:
        o.append(f'<circle cx="{cx + 5}" cy="{y - 4}" r="5" fill="{col}"/>')
        o.append(_t(cx + 15, y, lab, 11, fill="var(--ink-2)"))
        cx += 24 + len(lab) * 6.4
    return ''.join(o)


def s0chart():
    rows = DATA['s0']
    W, top, rh = 760, 46, 30
    H = top + rh * len(rows) + 30
    x0, x1 = 230, 740
    X = lambda v: x0 + v * (x1 - x0)
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Clef-Flash\'s score for the blue backpack versus the blue tarp '
         f'decoy, by view. From 40 m the crop already separates them (0.80 to 0.85 against 0.07 to 0.28); on the close-ups at 20 '
         f'and 12 m the backpack scores 0.91 to 0.96 and the tarp 0.02 to 0.05.">']
    o.append(_legend(x0, 18, [('blue backpack (clue)', 'var(--blaze)'), ('blue tarp (decoy)', 'var(--ink-3)')]))
    for v in (0, 0.2, 0.5, 1.0):
        o.append(f'<line x1="{X(v):.1f}" y1="{top - 10}" x2="{X(v):.1f}" y2="{top + rh * len(rows) - 6}" stroke="{"var(--rule)" if v in (0.2, 0.5) else "var(--grid)"}" stroke-width="1"/>')
        o.append(_t(X(v), top + rh * len(rows) + 10, f'{v:g}', 9.5, anchor="middle", fill="var(--ink-3)", family=MONO))
    o.append(_t(X(0.5) + 4, top - 14, 'confirm bar 0.5', 9, fill="var(--ink-3)"))
    o.append(_t(X(0.2) - 4, top - 14, 'dismiss below 0.2', 9, anchor="end", fill="var(--ink-3)"))
    for i, (lab, bm, bl, bh, tm, tl, th) in enumerate(rows):
        y = top + i * rh + 8
        o.append(_t(x0 - 12, y + 4, lab, 11.5, anchor="end", fill="var(--ink)"))
        for m, lo, hi, col, nm in ((tm, tl, th, 'var(--ink-3)', 'tarp'), (bm, bl, bh, 'var(--blaze)', 'backpack')):
            o.append(f'<line x1="{X(lo):.1f}" y1="{y}" x2="{X(hi):.1f}" y2="{y}" stroke="{col}" stroke-width="3" stroke-linecap="round"/>')
            o.append(f'<circle cx="{X(m):.1f}" cy="{y}" r="5.5" fill="{col}" stroke="var(--paper-2)" stroke-width="2"><title>{escape(lab)}, {nm}: median {m:.2f} (range {lo:.2f} to {hi:.2f}, 5 views)</title></circle>')
    o.append('</svg>')
    return ''.join(o)


def live_after():
    d = DATA['live_after']
    W, H = 520, 230
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="The same six flights scored two ways. Clues found: 14 of 16 live, '
         f'14 of 16 after landing. False alerts: 0 live, 7 after landing. Clef-Flash calls: 1,235 live, 4,860 after landing.">']
    o.append(_legend(10, 16, [('live, with closer looks', 'var(--clef)'), ('after landing, sweep photos only', 'var(--ink-3)')]))
    panels = [('clues found (of 16)', d['found'], 16), ('false alerts', d['false'], 8), ('Clef-Flash calls', d['clef_calls'], 5000)]
    for j, (lab, (a, b), mx) in enumerate(panels):
        y = 44 + j * 62
        o.append(_t(10, y + 10, lab, 11.5, weight=600, fill="var(--ink)"))
        for k, (v, col) in enumerate(((a, 'var(--clef)'), (b, 'var(--ink-3)'))):
            yy = y + 18 + k * 18
            w = max(2, v / mx * 360)
            o.append(f'<rect x="10" y="{yy}" width="{w:.1f}" height="13" rx="3" fill="{col}"><title>{escape(lab)}: {v:,}</title></rect>')
            o.append(_t(10 + w + 8, yy + 11, f'{v:,}', 11, fill="var(--ink)", weight=700, family=MONO))
    o.append('</svg>')
    return ''.join(o)


def trail():
    rows = DATA['trail']
    W, H = 520, 200
    x0, sc = 70, 2.6
    o = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Seconds from the first find to the second, with and without '
         f'qwen38\'s trail plans: seed 5, 93.5 with against 109.0 without; seed 6, 91.0 with against 134.5 without.">']
    o.append(_legend(10, 16, [('with qwen38 trail plans', 'var(--qwen)'), ('without', 'var(--ink-3)')]))
    for j, (lab, a, b) in enumerate(rows):
        y = 46 + j * 66
        o.append(_t(x0 - 10, y + 22, lab, 11.5, anchor="end", weight=600, fill="var(--ink)"))
        for k, (v, col) in enumerate(((a, 'var(--qwen)'), (b, 'var(--ink-3)'))):
            yy = y + 6 + k * 20
            o.append(f'<rect x="{x0}" y="{yy}" width="{v * sc:.1f}" height="14" rx="3" fill="{col}"><title>{lab}: {v} s</title></rect>')
            o.append(_t(x0 + v * sc + 8, yy + 12, f'{v:g} s', 11, fill="var(--ink)", weight=700, family=MONO))
    o.append(_t(x0, 186, 'seconds from the first find to the second (lockstep, grass, clues along the trail)', 10, fill="var(--ink-3)"))
    o.append('</svg>')
    return ''.join(o)


FIGURES = {
    'arch': architecture,
    'alt': altitude,
    'states': states,
    'funnel': funnel,
    'memory': memory,
    'deploy': deploy,
    's0chart': s0chart,
    'live_after': live_after,
    'trail': trail,
}
