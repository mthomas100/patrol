// Builds ../patrol-deck.pptx. Run: NODE_PATH=<dir with pptxgenjs> node build.cjs
const pptxgen = require('pptxgenjs');
const path = require('path');
const fs = require('fs');
const SKILL = process.env.PPTX_SKILL_DIR; // directory of the pptx skill (for apply_theme.js)
const { applyTheme } = require(path.join(SKILL, 'scripts/apply_theme.js'));

const ASSETS = path.resolve(__dirname, '../../assets');
const B = __dirname;
const a = f => path.join(ASSETS, f);
const b = f => path.join(B, f);

const HEAD = 'Arial', BODY = 'Georgia';
const INK = '15212B', PAPER = 'F3F5F2', WHITE = 'FFFFFF', MUTED = '5B6B76', BLAZE = 'E4570E';
const CLEF = '2A78D6', QWEN = '6250D6', VOICE = '13976A', AMBER = 'C98A00', CARD = 'FFFFFF', LINE = 'D5DBD6';
const THEME = {
  name: 'Patrol', headFontFace: HEAD, bodyFontFace: BODY,
  colors: { dk1: INK, lt1: WHITE, dk2: INK, lt2: PAPER, accent1: CLEF, accent2: QWEN, accent3: VOICE, accent4: BLAZE, accent5: MUTED, accent6: AMBER, hlink: CLEF, folHlink: QWEN },
};

const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.333 x 7.5
pres.theme = { headFontFace: HEAD, bodyFontFace: BODY };
pres.title = 'Patrol: a search drone that works from words, offline';
pres.author = 'Patrol';
const W = 13.333, MX = 0.55, CW = W - 2 * MX;

const titlePh = (color) => ({ options: { name: 'title', type: 'title', x: MX, y: 0.35, w: CW, h: 0.85, fontFace: HEAD, fontSize: 34, bold: true, color, margin: 0, valign: 'middle', align: 'left' }, text: 'Title' });
pres.defineSlideMaster({
  title: 'LIGHT', background: { color: PAPER },
  objects: [
    { text: { text: 'PATROL', options: { x: MX, y: 7.02, w: 3, h: 0.3, fontFace: HEAD, fontSize: 10, bold: true, color: MUTED, charSpacing: 3, margin: 0 } } },
    { placeholder: titlePh(INK) },
  ],
  slideNumber: { x: W - MX - 0.6, y: 7.02, w: 0.6, h: 0.3, fontFace: HEAD, fontSize: 10, color: MUTED, align: 'right' },
});
pres.defineSlideMaster({
  title: 'DARK', background: { color: INK },
  objects: [{ placeholder: titlePh(WHITE) }],
  slideNumber: { x: W - MX - 0.6, y: 7.02, w: 0.6, h: 0.3, fontFace: HEAD, fontSize: 10, color: 'A9B6BF', align: 'right' },
});

const shadow = () => ({ type: 'outer', color: '15212B', blur: 8, offset: 2, angle: 90, opacity: 0.12 });
const card = (s, x, y, w, h, o = {}) => s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: 0.08, fill: { color: o.fill || CARD }, line: { color: o.line || LINE, width: 0.75 }, shadow: o.noShadow ? undefined : shadow() });
const txt = (s, text, o) => s.addText(text, Object.assign({ isTextBox: true, fontFace: BODY, fontSize: 14, color: INK, margin: 0, valign: 'top' }, o));
const head = (s, text, o) => txt(s, text, Object.assign({ fontFace: HEAD, bold: true }, o));
const pill = (s, text, x, y, w, h, fill, o = {}) => {
  s.addShape(pres.ShapeType.roundRect, { x, y, w, h, rectRadius: h / 2, fill: { color: fill }, line: { color: fill, width: 0.5 } });
  txt(s, text, Object.assign({ x, y, w, h, fontFace: HEAD, bold: true, fontSize: 12, color: WHITE, align: 'center', valign: 'middle' }, o));
};
const points = (s, items, x, y, w, h, o = {}) => {
  const runs = items.map((t, i) => ({ text: t, options: { bullet: { indent: 16 }, breakLine: i < items.length - 1, paraSpaceAfter: o.gap ?? 10 } }));
  txt(s, runs, Object.assign({ x, y, w, h, fontSize: 16 }, o));
};
const img = (s, f, x, y, w, h, alt) => s.addImage({ path: f, x, y, w, h, altText: alt });
const arrow = (s, x, y, w, color = MUTED) => s.addShape(pres.ShapeType.rightArrow, { x, y, w, h: 0.28, fill: { color }, line: { color, width: 0.5 } });
const light = (title) => { const s = pres.addSlide({ masterName: 'LIGHT' }); s.addText(title, { placeholder: 'title' }); return s; };

// ---------- 1 Title (dark) ----------
{
  const s = pres.addSlide({ masterName: 'DARK' });
  s.addText('', { placeholder: 'title' });
  txt(s, 'MULTI MODEL HACKATHON  ·  SF TECH WEEK', { x: MX, y: 0.7, w: 6.4, h: 0.3, fontFace: HEAD, fontSize: 11, bold: true, color: 'A9B6BF', charSpacing: 3 });
  head(s, 'PATROL', { x: MX, y: 1.1, w: 6.4, h: 1.2, fontSize: 66, color: WHITE });
  txt(s, 'A search drone that looks for one missing person’s things, with no internet.', { x: MX, y: 2.45, w: 6.3, h: 1.5, fontSize: 26, color: WHITE });
  txt(s, '“The camper had a blue backpack, an orange tent, and a gray dog.”', { x: MX, y: 4.15, w: 6.2, h: 0.9, fontSize: 18, italic: true, color: 'A9B6BF' });
  head(s, '3 of 3', { x: MX, y: 5.35, w: 1.9, h: 0.75, fontSize: 40, color: BLAZE });
  txt(s, 'things found on a real-time flight, no false alerts', { x: MX, y: 6.1, w: 2.8, h: 0.6, fontSize: 12, color: 'D5DBD6' });
  head(s, '0.32 s', { x: 3.7, y: 5.35, w: 2.4, h: 0.75, fontSize: 40, color: WHITE });
  txt(s, 'median time to judge one odd-looking spot', { x: 3.7, y: 6.1, w: 2.7, h: 0.6, fontSize: 12, color: 'D5DBD6' });
  s.addShape(pres.ShapeType.roundRect, { x: 7.55, y: 0.4, w: 5.23, h: 6.3, rectRadius: 0.1, fill: { color: 'FAFAF8' }, line: { color: 'FAFAF8', width: 0.5 } });
  img(s, b('map-trim.png'), 7.62, 0.47, 5.09, 6.16 * 0 + 5.09 * 1094 / 902, 'Top-down map of the real-time flight: seven sweep lanes at 40 metres, eight closer looks, three alerts and one decoy dismissed');
  txt(s, 'Simulated flight, drawn from its own log', { x: 7.55, y: 6.74, w: 5.2, h: 0.25, fontFace: HEAD, fontSize: 10, color: 'A9B6BF', align: 'right' });
}

// ---------- 2 Dashboard at a glance ----------
{
  const s = light('Everything it sees, thinks and finds');
  const iw = 8.3, ih = iw / 1.6, ix = MX, iy = 1.4;
  img(s, a('console-alert.jpg'), ix, iy, iw, ih, 'The Patrol console at the moment of an alert: header, clue cards, zoom camera, decision trace, sector map, chase view, log and alert cards');
  const pins = [[63, 4.2], [2.6, 8.2], [16, 16.2], [14, 64], [45, 16.2], [47.5, 60.2], [44, 82], [72, 16.2]];
  const keys = [
    ['Header', 'state, area searched, battery, who decided'],
    ['Looking for', 'the clues, in qwen38’s words'],
    ['Camera', 'the sweep photo, then the close-up and verdict'],
    ['Decision trace', 'the crop Clef-Flash judged, and its odds'],
    ['Map', 'lanes, trail, spots checked, alerts, next sectors'],
    ['Chase view', 'for the audience; no model uses it'],
    ['Log', 'every decision, note and spoken line'],
    ['Alerts', 'sweep crop beside the confirming close-up'],
  ];
  const d = 0.3;
  pins.forEach((p, i) => {
    const px = ix + iw * p[0] / 100 - d / 2, py = iy + ih * p[1] / 100 - d / 2;
    s.addShape(pres.ShapeType.ellipse, { x: px, y: py, w: d, h: d, fill: { color: BLAZE }, line: { color: WHITE, width: 1.5 }, shadow: shadow() });
    head(s, String(i + 1), { x: px, y: py, w: d, h: d, fontSize: 11, color: WHITE, align: 'center', valign: 'middle' });
  });
  const kx = ix + iw + 0.35, kw = W - MX - kx, rowH = 0.64;
  keys.forEach((k, i) => {
    const y = iy + i * rowH;
    s.addShape(pres.ShapeType.ellipse, { x: kx, y: y + 0.04, w: d, h: d, fill: { color: BLAZE }, line: { color: BLAZE, width: 0.5 } });
    head(s, String(i + 1), { x: kx, y: y + 0.04, w: d, h: d, fontSize: 11, color: WHITE, align: 'center', valign: 'middle' });
    txt(s, [{ text: k[0] + '  ', options: { bold: true, fontFace: HEAD } }, { text: k[1] }], { x: kx + 0.45, y, w: kw - 0.45, h: rowH - 0.06, fontSize: 12.5 });
  });
  txt(s, 'The moment of an alert in the demo flight: Clef-Flash has just confirmed the blue backpack from 20 m.', { x: MX, y: iy + ih + 0.15, w: iw, h: 0.5, fontSize: 12, italic: true, color: MUTED });
}

// ---------- 3 Video ----------
{
  const s = light('Watch the whole flight');
  const vw = 8.6, vh = vw * 800 / 1280;
  s.addMedia({ type: 'video', path: a('demo-flight.mp4'), cover: 'data:image/jpeg;base64,' + fs.readFileSync(a('demo-flight-poster.jpg')).toString('base64'), x: MX, y: 1.4, w: vw, h: vh, altText: 'Recording of the demo flight in the console, replayed at 3.5 times speed with the alerts read aloud' });
  const x = MX + vw + 0.5;
  points(s, [
    '3 min 23 s, replayed at 3.5× with the alerts read aloud.',
    'Three finds, the tarp checked and dismissed, no false alerts.',
    'This recording is also the stage fallback.',
  ], x, 1.5, W - MX - x, 4.5, { fontSize: 17, gap: 18 });
}

// ---------- 2 Problem ----------
{
  const s = light('Searchers start with words, not photos');
  card(s, MX, 1.5, 6.9, 1.75);
  head(s, 'WHAT THE FAMILY SAYS', { x: MX + 0.3, y: 1.68, w: 5, h: 0.25, fontSize: 10, color: MUTED, charSpacing: 3 });
  txt(s, '“The camper had a blue backpack, an orange tent, and a gray dog.”', { x: MX + 0.3, y: 2.0, w: 6.3, h: 1.3, fontSize: 24, italic: true, color: INK });
  points(s, [
    'Nobody has trained a detector on this person’s blue backpack.',
    'No cell signal: an alert is about 270 bytes of text plus a 20 KB photo.',
    'Decide in the air. After landing, every “maybe” costs another flight.',
  ], MX, 3.65, 6.9, 2.9, { fontSize: 17, gap: 14 });
  img(s, a('alt-sweep-40m-detail.jpg'), 8.0, 1.5, 4.78, 3.585, 'Blue backpack enlarged from a 40 metre sweep photo');
  head(s, 'From 40 m, a backpack is a smudge', { x: 8.0, y: 5.25, w: 4.78, h: 0.35, fontSize: 16, color: INK });
  txt(s, 'About 22 pixels across: enough to look odd, not enough to be sure.', { x: 8.0, y: 5.62, w: 4.78, h: 0.7, fontSize: 14, color: MUTED });
}

// ---------- 3 Five moments ----------
{
  const s = light('A flight in five moments');
  const gap = 0.2, cw = (CW - 4 * gap) / 5, ch = 4.2, y0 = 1.55;
  const items = [
    { t: 'Say it', c: 'Parakeet writes it down. qwen38 turns each thing into a sentence about how it looks from above.' },
    { t: 'Sweep at 40 m', c: 'A photo every 12 m. The finder boxes odd spots; Clef-Flash says 61% backpack in about 0.3\u00A0s.', f: a('sweep-frame-boxes.jpg') },
    { t: 'Follow a lead', c: 'Down to 20 m for a close-up. The backpack scores 94.5%: confirmed.', f: a('find-blue_backpack-closeup.jpg') },
    { t: 'Alert', c: 'A position, a photo and a spoken note. The tent alert lands 0.24 m from the tent.', f: a('find-orange_tent-closeup.jpg'), alert: true },
    { t: 'Think ahead', c: 'qwen38 reorders the sectors. The second find came 29.5 s sooner, on average.', f: b('hero-chase43.jpg') },
  ];
  items.forEach((it, i) => {
    const x = MX + i * (cw + gap);
    card(s, x, y0, cw, ch);
    const ix = x + 0.12, iw = cw - 0.24, ih = iw * 0.75;
    if (it.f) img(s, it.f, ix, y0 + 0.12, iw, ih, it.t);
    else {
      s.addShape(pres.ShapeType.roundRect, { x: ix, y: y0 + 0.12, w: iw, h: ih, rectRadius: 0.06, fill: { color: VOICE }, line: { color: VOICE, width: 0.5 } });
      txt(s, '“...a blue backpack, an orange tent, and a gray dog.”', { x: ix + 0.14, y: y0 + 0.12, w: iw - 0.28, h: ih, fontSize: 14, italic: true, color: WHITE, valign: 'middle' });
    }
    if (it.alert) pill(s, 'ALERT', ix + 0.08, y0 + 0.2, 0.8, 0.28, BLAZE, { fontSize: 10 });
    s.addShape(pres.ShapeType.ellipse, { x: ix, y: y0 + ih + 0.3, w: 0.38, h: 0.38, fill: { color: it.alert ? BLAZE : INK }, line: { color: it.alert ? BLAZE : INK, width: 0.5 } });
    head(s, String(i + 1), { x: ix, y: y0 + ih + 0.3, w: 0.38, h: 0.38, fontSize: 14, color: WHITE, align: 'center', valign: 'middle' });
    head(s, it.t, { x: ix + 0.48, y: y0 + ih + 0.3, w: iw - 0.48, h: 0.38, fontSize: 14, valign: 'middle' });
    txt(s, it.c, { x: ix, y: y0 + ih + 0.85, w: iw, h: ch - ih - 1.0, fontSize: 14, color: INK });
  });
  txt(s, 'Real flights in the simulator, with the real models deciding.', { x: MX, y: 6.0, w: CW, h: 0.3, fontSize: 13, italic: true, color: MUTED });
}

// ---------- 4 Pairs ----------
{
  const s = light('A decoy dismissed, a backpack confirmed');
  const rows = [
    { sw: a('decoy-tarp-sweep.jpg'), cu: a('decoy-tarp-closeup.jpg'), p1: '17%', l1: 'blue tarp', p2: '4%', l2: 'A flat sheet. Best clue score 4%.', verdict: 'DISMISSED', col: MUTED, y: 1.35 },
    { sw: a('find-blue_backpack-sweep.jpg'), cu: a('find-blue_backpack-closeup.jpg'), p1: '61%', l1: 'blue backpack', p2: '94.5%', l2: 'Straps and pockets. Back in the lane with an alert.', verdict: 'CONFIRMED', col: BLAZE, y: 3.95 },
  ];
  rows.forEach(r => {
    const ih = 2.25;
    head(s, 'FROM 40 M', { x: MX, y: r.y, w: 2.3, h: 0.22, fontSize: 10, color: MUTED, charSpacing: 2 });
    head(s, 'CLOSE-UP AT 20 M', { x: 3.75, y: r.y, w: 3.2, h: 0.22, fontSize: 10, color: MUTED, charSpacing: 2 });
    img(s, r.sw, MX, r.y + 0.28, ih, ih, r.l1 + ' from 40 m');
    arrow(s, 3.0, r.y + 0.28 + ih / 2 - 0.14, 0.6, r.col);
    img(s, r.cu, 3.75, r.y + 0.28, ih * 4 / 3, ih, r.l1 + ' close-up at 20 m');
    pill(s, r.verdict, 7.35, r.y + 0.35, 1.7, 0.38, r.col, { fontSize: 13 });
    head(s, 'FROM 40 M', { x: 7.35, y: r.y + 0.9, w: 1.9, h: 0.22, fontSize: 10, color: MUTED, charSpacing: 2 });
    head(s, r.p1, { x: 7.35, y: r.y + 1.15, w: 1.9, h: 0.6, fontSize: 32, color: INK });
    txt(s, 'blue backpack?', { x: 7.35, y: r.y + 1.8, w: 2.0, h: 0.3, fontSize: 12, color: MUTED });
    head(s, 'AT 20 M', { x: 9.55, y: r.y + 0.9, w: 3.2, h: 0.22, fontSize: 10, color: MUTED, charSpacing: 2 });
    head(s, r.p2, { x: 9.55, y: r.y + 1.15, w: 3.2, h: 0.6, fontSize: 32, color: r.col === BLAZE ? BLAZE : INK });
    txt(s, r.l2, { x: 9.55, y: r.y + 1.8, w: 3.2, h: 0.6, fontSize: 12, color: MUTED });
  });
  txt(s, 'Scores are Clef-Flash’s probability that the spot is the blue backpack.', { x: MX, y: 6.62, w: 8, h: 0.25, fontSize: 11, italic: true, color: MUTED });
}

// ---------- 5 Cast + m3d ----------
{
  const s = light('Four models fly it, three built the props');
  const gap = 0.2, cw = (CW - 3 * gap) / 4, y0 = 1.4, ch = 1.75;
  const cast = [
    { n: 'Clef-Flash', r: 'The fast eyes', d: 'Judges each odd spot in about 0.3\u00A0s', c: CLEF },
    { n: 'qwen38', r: 'The slow thinker', d: 'Clue sentences, radio notes, trail plans, second opinions', c: QWEN },
    { n: 'Parakeet', r: 'The ears', d: 'Speech to text in 20 to 90 ms', c: VOICE },
    { n: 'Kokoro', r: 'The voice', d: 'Reads every alert aloud', c: VOICE },
  ];
  cast.forEach((m, i) => {
    const x = MX + i * (cw + gap);
    card(s, x, y0, cw, ch);
    s.addShape(pres.ShapeType.ellipse, { x: x + 0.2, y: y0 + 0.24, w: 0.2, h: 0.2, fill: { color: m.c }, line: { color: m.c, width: 0.5 } });
    head(s, m.n, { x: x + 0.5, y: y0 + 0.16, w: cw - 0.6, h: 0.36, fontSize: 18, color: m.c, valign: 'middle' });
    head(s, m.r.toUpperCase(), { x: x + 0.2, y: y0 + 0.62, w: cw - 0.4, h: 0.22, fontSize: 9.5, color: MUTED, charSpacing: 2 });
    txt(s, m.d, { x: x + 0.2, y: y0 + 0.9, w: cw - 0.4, h: 0.8, fontSize: 13 });
  });
  s.addShape(pres.ShapeType.roundRect, { x: MX, y: 3.35, w: CW, h: 0.45, rectRadius: 0.08, fill: { color: INK }, line: { color: INK, width: 0.5 } });
  txt(s, 'Plain code flies the drone and owns safety. Models advise; no model can override it.', { x: MX + 0.25, y: 3.35, w: CW - 0.5, h: 0.45, fontSize: 14, color: WHITE, valign: 'middle' });
  head(s, 'THREE MORE MODELS, CHAINED BY m3d, BUILT EVERY PROP FROM ONE SENTENCE', { x: MX, y: 4.05, w: CW, h: 0.25, fontSize: 10.5, color: MUTED, charSpacing: 2 });
  const gap2 = 0.55, sw = (CW - 4 * gap2) / 5, y1 = 4.4;
  const steps = [
    { t: 'The sentence', d: '“a royal blue hiking backpack”', q: true },
    { t: 'Z-Image Turbo', d: 'concept picture, 20 s', f: a('item-blue_backpack-concept.jpg') },
    { t: 'Apple Vision', d: 'cut-out, under a second', f: a('m3d-cutout.jpg') },
    { t: 'Hunyuan3D', d: 'shape and textures, 260 s', f: a('item-blue_backpack-mesh.jpg') },
    { t: 'In the simulator', d: 'photographed by the drone', f: a('find-blue_backpack-closeup.jpg'), wide: true },
  ];
  const isz = 1.45;
  steps.forEach((st, i) => {
    const x = MX + i * (sw + gap2);
    const w = isz;
    if (st.q) {
      s.addShape(pres.ShapeType.roundRect, { x, y: y1, w, h: isz, rectRadius: 0.06, fill: { color: CARD }, line: { color: MUTED, width: 1, dashType: 'dash' } });
      txt(s, '“a royal blue hiking backpack with black straps”', { x: x + 0.1, y: y1, w: w - 0.2, h: isz, fontSize: 12, italic: true, valign: 'middle' });
    } else if (st.wide) {
      img(s, st.f, x, y1, isz * 4 / 3, isz, 'Backpack close-up from the drone camera');
    } else img(s, st.f, x, y1, w, isz, st.t);
    head(s, st.t, { x, y: y1 + isz + 0.1, w: sw + 0.3, h: 0.28, fontSize: 12.5 });
    txt(s, st.d, { x, y: y1 + isz + 0.4, w: sw + 0.3, h: 0.5, fontSize: 11.5, color: MUTED });
    if (i < 4) arrow(s, x + (st.wide ? isz * 4 / 3 : isz) + 0.1, y1 + isz / 2 - 0.14, 0.34, MUTED);
  });
  txt(s, 'About 5 minutes per item, 8 items. All of it happens before the flight.', { x: MX, y: 6.7, w: CW - 1, h: 0.28, fontSize: 12, italic: true, color: MUTED });
}

// ---------- 6 Architecture ----------
{
  const s = light('Fast loop, slow thinker, code in charge');
  const w = CW, h = w * 826 / 1930;
  img(s, b('arch-main-trim.png'), MX, 1.3, w, h, 'Diagram of how the models fit together: voice and description before take-off, the fast Clef-Flash loop on every photo, the slow qwen38 loop a few times a flight');
  txt(s, [{ text: 'Clef-Flash', options: { bold: true, color: CLEF, fontFace: HEAD } }, { text: ' judges every photo in about 0.3\u00A0s.   ' }, { text: 'qwen38', options: { bold: true, color: QWEN, fontFace: HEAD } }, { text: ' does a few background jobs.   ' }, { text: 'Code', options: { bold: true, fontFace: HEAD } }, { text: ' checks every answer and owns safety.' }], { x: MX, y: 1.3 + h + 0.14, w: CW, h: 0.4, fontSize: 13, color: INK });
}

// ---------- 7 Altitude ladder ----------
{
  const s = light('Fly high, look close');
  const gap = 0.18, iw = (CW - 4 * gap) / 5, ih = iw * 0.75, y0 = 1.4;
  const lad = [
    ['alt-sweep-60m.jpg', 'sweep · 60 m', 'the finder misses it'],
    ['alt-sweep-40m.jpg', 'sweep · 40 m', 'the sweep height'],
    ['alt-sweep-20m.jpg', 'sweep · 20 m', 'easy, but twice the lanes'],
    ['alt-zoom-20m.jpg', 'zoom · 20 m', 'the first closer look'],
    ['alt-zoom-12m.jpg', 'zoom · 12 m', 'only if unsure'],
  ];
  lad.forEach((l, i) => {
    const x = MX + i * (iw + gap);
    img(s, a(l[0]), x, y0, iw, ih, 'The same blue backpack, ' + l[1]);
    head(s, l[1], { x, y: y0 + ih + 0.1, w: iw, h: 0.3, fontSize: 14, color: i === 1 ? INK : MUTED });
    txt(s, l[2], { x, y: y0 + ih + 0.42, w: iw, h: 0.5, fontSize: 13, color: MUTED });
  });
  const cy = 4.3, ch = 2.35, gw = (CW - 0.4) / 3;
  [
    ['1 of 10', 'views where the finder found the backpack from 60\u00A0m', INK],
    ['10 of 10', 'views where it found it from 40\u00A0m, so 40\u00A0m is the sweep height', INK],
    ['7 vs 13', 'lanes to cover the 160\u00A0m square from 40\u00A0m versus 20\u00A0m', INK],
  ].forEach((k, i) => {
    const x = MX + i * (gw + 0.2);
    card(s, x, cy, gw, ch);
    head(s, k[0], { x: x + 0.3, y: cy + 0.25, w: gw - 0.6, h: 0.9, fontSize: 40, color: k[2], valign: 'middle' });
    txt(s, k[1], { x: x + 0.3, y: cy + 1.3, w: gw - 0.6, h: 0.95, fontSize: 14 });
  });
}

// ---------- 8 Altitude geometry (native shapes, labels 14 pt) ----------
{
  const s = light('Higher means fewer lanes');
  const GY = 5.45, TOP = 2.15, SC = (GY - TOP) / 40; // inches per metre
  const MONO = 'Courier New', GROUND = 'E8ECE6', LBLUE = '2A78D6';
  s.addShape(pres.ShapeType.rect, { x: MX, y: GY, w: CW, h: 0.8, fill: { color: GROUND }, line: { color: GROUND, width: 0.5 } });
  s.addShape(pres.ShapeType.line, { x: MX, y: GY, w: CW, h: 0, line: { color: MUTED, width: 1 } });
  s.addShape(pres.ShapeType.line, { x: 1.2, y: TOP, w: 0, h: GY - TOP, line: { color: MUTED, width: 1.25 } });
  [[40, '40 m'], [20, '20 m'], [12, '12 m'], [0, '0 m']].forEach(([m, t]) => {
    const y = GY - m * SC;
    s.addShape(pres.ShapeType.line, { x: 1.12, y, w: 0.1, h: 0, line: { color: MUTED, width: 1 } });
    txt(s, t, { x: MX, y: y - 0.15 + (m === 0 ? 0.17 : 0), w: 0.55, h: 0.3, fontFace: MONO, fontSize: 14, color: MUTED, align: 'right', valign: 'middle' });
  });
  const drone = (cx, cy, col) => {
    s.addShape(pres.ShapeType.ellipse, { x: cx - 0.3, y: cy - 0.06, w: 0.12, h: 0.12, fill: { color: PAPER }, line: { color: col, width: 1.25 } });
    s.addShape(pres.ShapeType.ellipse, { x: cx + 0.18, y: cy - 0.06, w: 0.12, h: 0.12, fill: { color: PAPER }, line: { color: col, width: 1.25 } });
    s.addShape(pres.ShapeType.line, { x: cx - 0.18, y: cy, w: 0.36, h: 0, line: { color: col, width: 1.5 } });
    s.addShape(pres.ShapeType.roundRect, { x: cx - 0.1, y: cy - 0.06, w: 0.2, h: 0.12, rectRadius: 0.03, fill: { color: col }, line: { color: col, width: 0.5 } });
  };
  // left: two neighbouring lanes
  const base = 32.6 * SC, lane = 22.9 * SC, c1 = 2.9, c2 = c1 + lane;
  head(s, 'two neighbouring lanes, seen end-on', { x: 1.4, y: 1.3, w: 5.2, h: 0.35, fontSize: 15, color: INK, align: 'center' });
  [c1, c2].forEach((cx, i) => s.addShape(pres.ShapeType.triangle, { x: cx - base / 2, y: TOP + 0.06, w: base, h: GY - TOP - 0.06, fill: { color: LBLUE, transparency: i ? 88 : 82 }, line: { color: '8DB4E6', width: 0.75 } }));
  drone(c1, TOP, INK); drone(c2, TOP, INK);
  s.addShape(pres.ShapeType.line, { x: c1 + 0.2, y: 1.95, w: lane - 0.4, h: 0, line: { color: MUTED, width: 1.25, beginArrowType: 'triangle', endArrowType: 'triangle' } });
  txt(s, '22.9 m between lanes', { x: c1 - 0.2, y: 1.62, w: lane + 0.4, h: 0.3, fontSize: 14, color: INK, align: 'center' });
  txt(s, 'overlap', { x: c2 - base / 2 - 0.05, y: GY - 0.4, w: 1.0, h: 0.3, fontSize: 14, color: MUTED });
  s.addShape(pres.ShapeType.line, { x: c1 - base / 2, y: GY + 0.22, w: base, h: 0, line: { color: MUTED, width: 1.25, beginArrowType: 'triangle', endArrowType: 'triangle' } });
  txt(s, '32.6 m of ground in each photo', { x: c1 - base / 2 - 0.2, y: GY + 0.3, w: base + 0.4, h: 0.3, fontSize: 14, color: INK, align: 'center' });
  // right: a closer look
  const bx = 11.6;
  head(s, 'a closer look at one spot', { x: 8.2, y: 1.3, w: 4.58, h: 0.35, fontSize: 15, color: INK, align: 'center' });
  const d1 = [bx - 0.6 * 20 * SC, GY - 20 * SC], d2 = [bx - 0.6 * 12 * SC, GY - 12 * SC];
  const poly = (d, col, tr, half) => s.addShape(pres.ShapeType.custGeom, { x: d[0], y: d[1], w: bx - d[0] + half, h: GY - d[1], fill: { color: col, transparency: tr }, line: { color: col, width: 0.75 }, points: [{ x: 0, y: 0, moveTo: true }, { x: bx - d[0] - half, y: GY - d[1] }, { x: bx - d[0] + half, y: GY - d[1] }, { close: true }] });
  poly(d1, BLAZE, 78, 0.18); poly(d2, MUTED, 70, 0.1);
  drone(d1[0], d1[1], BLAZE); drone(d2[0], d2[1], MUTED);
  s.addShape(pres.ShapeType.ellipse, { x: bx - 0.08, y: GY - 0.08, w: 0.16, h: 0.16, fill: { color: PAPER }, line: { color: BLAZE, width: 1.5 } });
  head(s, 'first look at 20 m', { x: d1[0] - 2.5, y: d1[1] - 0.17, w: 2.1, h: 0.34, fontSize: 14, color: INK, align: 'right', valign: 'middle' });
  txt(s, 'second step at 12 m, only if unsure', { x: d2[0] - 3.9, y: d2[1] - 0.17, w: 3.5, h: 0.34, fontSize: 14, color: INK, align: 'right', valign: 'middle' });
  txt(s, 'hover 0.6 × the height short of the spot, about 31° off vertical; the zoom frames about 4 m of ground', { x: 9.1, y: 2.05, w: 3.68, h: 1.0, fontSize: 14, color: MUTED });
  head(s, 'backpack, 0.55 m', { x: bx - 1.3, y: GY + 0.12, w: 2.6, h: 0.3, fontSize: 14, color: BLAZE, align: 'center' });
  txt(s, '(drawn to scale)', { x: bx - 1.3, y: GY + 0.42, w: 2.6, h: 0.3, fontSize: 14, color: MUTED, align: 'center' });
  txt(s, 'At 40 m, 7 lanes cover the square. At 20 m it would take 13.', { x: MX, y: 6.45, w: CW, h: 0.4, fontSize: 16, italic: true, color: INK });
}

// ---------- 8 Funnel ----------
{
  const s = light('Each model sees only what it must');
  const dw = 8.2, dh = dw * 453 / 972;
  img(s, b('diagram4.png'), MX, 1.5, dw, dh, 'Log-scale bar chart of one flight: 1,234 control ticks, 125 sweep photos, 375 odd spots boxed by the finder, 163 crops judged by Clef-Flash, 8 closer looks, 8 close-ups judged, 3 alerts, 6 qwen38 jobs, 3 spoken alerts');
  txt(s, 'One flight: 683 s over a 160 × 160 m square. Clef-Flash’s 171 calls took about 56 s of model time; qwen38’s 6 jobs about 15 s, in the background.', { x: MX, y: 1.5 + dh + 0.2, w: dw, h: 0.8, fontSize: 13, color: MUTED });
  const x = 9.15, w = W - MX - x;
  [
    { n: '375', c: AMBER, t: 'odd spots boxed by the CPU finder, on every photo' },
    { n: '163', c: CLEF, t: 'crops judged by Clef-Flash, plus 8 close-ups' },
    { n: '6', c: QWEN, t: 'qwen38 jobs: 3 radio notes, 3 trail plans' },
  ].forEach((r, i) => {
    const y = 1.5 + i * 1.7;
    card(s, x, y, w, 1.5);
    head(s, r.n, { x: x + 0.25, y: y + 0.1, w: w - 0.5, h: 0.8, fontSize: 44, color: r.c, valign: 'middle' });
    txt(s, r.t, { x: x + 0.25, y: y + 0.9, w: w - 0.5, h: 0.55, fontSize: 12.5 });
  });
}

// ---------- 9 Talking ----------
{
  const s = light('Talking to it');
  const cols = [MX, 6.6, 9.95], ws = [5.7, 3.1, 2.85];
  ['THE OPERATOR SAYS', 'CLEF-FLASH ROUTES IT TO', 'WHAT HAPPENS'].forEach((t, i) => head(s, t, { x: cols[i], y: 1.4, w: ws[i], h: 0.25, fontSize: 10, color: MUTED, charSpacing: 2 }));
  const rows = [
    ['“Missing hiker. Blue backpack, orange tent, grey dog.”', 'describe', 'qwen38 writes the clue cards'],
    ['“Start the search.”', 'start_search', 'take off and sweep'],
    ['“Go back to the last alert.”', 'go_back_to_last_alert', 'fly back and look again'],
    ['“Stop searching and come home.”', 'return_home', 'straight home'],
  ];
  rows.forEach((r, i) => {
    const y = 1.75 + i * 0.95;
    s.addShape(pres.ShapeType.roundRect, { x: cols[0], y, w: ws[0], h: 0.78, rectRadius: 0.2, fill: { color: CARD }, line: { color: VOICE, width: 1.25 }, shadow: shadow() });
    txt(s, r[0], { x: cols[0] + 0.25, y, w: ws[0] - 0.5, h: 0.78, fontSize: 15, italic: true, valign: 'middle' });
    arrow(s, 6.3, y + 0.25, 0.27, MUTED);
    pill(s, r[1], cols[1], y + 0.14, ws[1], 0.5, CLEF, { fontFace: 'Courier New', fontSize: 12.5 });
    txt(s, r[2], { x: cols[2], y, w: ws[2], h: 0.78, fontSize: 14, valign: 'middle' });
  });
  const y = 5.75, gw = (CW - 0.4) / 3;
  [
    ['20 to 90 ms', 'Parakeet, speech to text'],
    ['45%', 'minimum Clef-Flash confidence to act on a command'],
    ['94.7%', 'confidence on the operator’s spoken description'],
  ].forEach((k, i) => {
    const x = MX + i * (gw + 0.2);
    head(s, k[0], { x, y, w: gw, h: 0.5, fontSize: 26, color: INK });
    txt(s, k[1], { x, y: y + 0.5, w: gw, h: 0.55, fontSize: 12, color: MUTED });
  });
}

// ---------- 11 Laptop ----------
{
  const s = light('One laptop, no internet');
  const dw = CW, dh = dw * 156 / 972;
  img(s, b('diagram5.png'), MX, 1.4, dw, dh, 'Bar of model weights in 128 GB of unified memory: qwen38 about 70 GB, Clef-Flash 11, voice 2.7, simulator 1.7, about 43 GB free for macOS');
  const y = 3.75, ch = 2.55, gw = (CW - 0.4) / 3;
  [
    ['128 GB', 'One MacBook Pro M5 Max', 'A 40-core GPU and 128 GB of unified memory run every model, the simulator and the console at once.'],
    ['No internet', 'Everything is local', 'Every model runs on the laptop and nothing in the code calls out.'],
    ['0.3 to 0.4 s', 'One GPU is the limit', 'Clef-Flash answers that fast when the GPU is free. With another job running, 2\u00A0to\u00A06\u00A0s.'],
  ].forEach((k, i) => {
    const x = MX + i * (gw + 0.2);
    card(s, x, y, gw, ch);
    head(s, k[0], { x: x + 0.3, y: y + 0.25, w: gw - 0.6, h: 0.7, fontSize: 32, color: INK, valign: 'middle' });
    head(s, k[1], { x: x + 0.3, y: y + 1.0, w: gw - 0.6, h: 0.35, fontSize: 15, color: MUTED });
    txt(s, k[2], { x: x + 0.3, y: y + 1.45, w: gw - 0.6, h: 1.0, fontSize: 14 });
  });
}

// ---------- 12 Proven ----------
{
  const s = light('It works end to end, in a simulator');
  const gap = 0.2, cw = (CW - 3 * gap) / 4, y0 = 1.4, ch = 2.35;
  [
    ['3 of 3', 'found on a real-time flight, 683\u00A0s, no false alerts', BLAZE],
    ['17 of 18', 'scenario flights pass, over three sets of fresh seeds', INK],
    ['0 in 45', 'false alerts across 45 flights and 95 alerts', INK],
    ['0 vs 7', 'false alerts, live versus reviewing photos after landing', INK],
  ].forEach((k, i) => {
    const x = MX + i * (cw + gap);
    card(s, x, y0, cw, ch);
    head(s, k[0], { x: x + 0.25, y: y0 + 0.25, w: cw - 0.5, h: 0.95, fontSize: 40, color: k[2], valign: 'middle' });
    txt(s, k[1], { x: x + 0.25, y: y0 + 1.3, w: cw - 0.5, h: 0.95, fontSize: 13 });
  });
  const iy = 4.05, ih = 2.1, iw = ih * 4 / 3, g2 = 0.2;
  ['find-grey_dog-closeup.jpg', 'find-yellow_helmet-closeup.jpg', 'find-green_sleeping_bag-closeup.jpg'].forEach((f, i) => {
    img(s, a(f), MX + i * (iw + g2), iy, iw, ih, ['Grey dog', 'Yellow helmet', 'Green sleeping bag'][i] + ' close-up');
  });
  const tx = MX + 3 * (iw + g2) + 0.15;
  head(s, 'Found from words alone', { x: tx, y: iy, w: W - MX - tx, h: 0.4, fontSize: 16 });
  txt(s, 'Dog, helmet (0.3 m) and sleeping bag: items never used for tuning.', { x: tx, y: iy + 0.5, w: W - MX - tx, h: 1.0, fontSize: 14 });
  txt(s, 'Read these as “this behaviour works”, not as real-world detection rates.', { x: MX, y: 6.45, w: CW - 1, h: 0.3, fontSize: 12.5, italic: true, color: MUTED });
}

// ---------- 13 Doesn't work yet ----------
{
  const s = light('What doesn’t work yet');
  const rows = [
    ['PASSED, NARROWLY', INK, 'The battery is the limit', 'The four-clue flight ran out of its simulated 20-minute battery in all three seed sets. The battery is now 30 minutes; re-runs pending.'],
    ['PARTLY', MUTED, 'New items lean on qwen38', 'Clef-Flash’s close-ups score 0.12 to 0.29 on held-out items. Two of four finds came via a second opinion.'],
    ['OPEN', MUTED, 'It has only seen a simulator', 'Flat ground, no wind, no GPS error. Real aerial imagery is untested.'],
    ['OPEN', MUTED, 'No radio, no Wi-Fi-off rehearsal', 'The alert is radio-sized, but no radio exists. Offline is by design, not yet by test.'],
    ['PARTLY', MUTED, 'Small numbers', 'Three seed sets per scenario, two seeds for the trail test, six flights for live versus after landing.'],
  ];
  rows.forEach((r, i) => {
    const y = 1.4 + i * 1.08, h = 0.92;
    card(s, MX, y, CW, h);
    pill(s, r[0], MX + 0.25, y + 0.3, 1.75, 0.32, r[1], { fontSize: 10 });
    head(s, r[2], { x: 2.8, y, w: 3.7, h, fontSize: 16, valign: 'middle' });
    txt(s, r[3], { x: 6.6, y, w: W - MX - 6.6 - 0.25, h, fontSize: 13, valign: 'middle' });
  });
}

// ---------- 14 Next (dark) ----------
{
  const s = pres.addSlide({ masterName: 'DARK' });
  s.addText('What’s next', { placeholder: 'title' });
  const gap = 0.2, cw = (CW - 4 * gap) / 5, y0 = 1.6, ch = 3.7;
  [
    ['Re-run on a 30\u2011minute battery', 'The four-clue flight ran out of 20 minutes in every seed set. Re-runs are under way.'],
    ['Wi-Fi-off rehearsal', 'Run the whole demo with the network actually off. About ten minutes.'],
    ['Real aerial photos', 'Replay HERIDAL, SARD or WiSARD imagery. Approved; dataset licences are being checked.'],
    ['Hybrid after-landing pass', 'Re-check saved photos, but only send a team to spots no close-up cleared. A day of work.'],
    ['Real flight software', 'PX4 in simulation, then a real drone. Weeks, and hardware.'],
  ].forEach((k, i) => {
    const x = MX + i * (cw + gap);
    s.addShape(pres.ShapeType.roundRect, { x, y: y0, w: cw, h: ch, rectRadius: 0.08, fill: { color: '1E2E3A' }, line: { color: '33454F', width: 0.75 } });
    head(s, String(i + 1), { x: x + 0.22, y: y0 + 0.2, w: 0.8, h: 0.8, fontSize: 40, color: 'A9B6BF' });
    head(s, k[0], { x: x + 0.22, y: y0 + 1.1, w: cw - 0.44, h: 0.95, fontSize: 16, color: WHITE });
    txt(s, k[1], { x: x + 0.22, y: y0 + 2.1, w: cw - 0.44, h: 1.9, fontSize: 13, color: 'D5DBD6' });
  });
  txt(s, 'From a convincing simulator to evidence that matters on real ground.', { x: MX, y: 5.7, w: CW, h: 0.5, fontSize: 18, italic: true, color: WHITE });
}

(async () => {
  const out = path.resolve(__dirname, '../patrol-deck.pptx');
  await pres.writeFile({ fileName: out });
  await applyTheme(out, THEME);
  console.log('wrote', out, fs.statSync(out).size);
})();
