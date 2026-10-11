// Headless check of the search console page (patrol/console/search.html), no GPU, no models.
//   node tools/check_console.cjs replay http://127.0.0.1:8781/ [outdir]   (server: bin/patrol console --replay runs/s2-live-b --speed 20 --port 8781)
//   node tools/check_console.cjs live   http://127.0.0.1:8782/ [outdir]   (server: bin/patrol console --search --clef-url http://127.0.0.1:9/v1/systemone --port 8782 --half 30)
//   node tools/check_console.cjs livefake http://127.0.0.1:8782/ [outdir]  (same, --clef-url pointing at a stand-in that answers by blue-pixel count)
//   node tools/check_console.cjs voice  http://127.0.0.1:8790/ [outdir]   (server: bin/patrol console --search --think --voice --speak --terrain grass --seed 26 --items blue_backpack,orange_tent,grey_dog,blue_tarp --clues blue_backpack,orange_tent,grey_dog --pace 8 --port 8790; needs Clef, qwen38 and the Parakeet+Kokoro worker, no GPU hold)
//     voice mode has no microphone: the spoken clips are POSTed from node, and a stand-in getUserMedia plays a fixture wav into the page's MediaRecorder.
// Playwright is taken from the npx cache (PLAYWRIGHT_DIR overrides). Screenshots go to outdir (png: git-ignored).
const fs = require('fs'), path = require('path'), os = require('os');

function findPlaywright() {
  if (process.env.PLAYWRIGHT_DIR) return require(process.env.PLAYWRIGHT_DIR);
  const base = path.join(os.homedir(), '.npm', '_npx');
  for (const d of fs.readdirSync(base)) {
    const p = path.join(base, d, 'node_modules', 'playwright');
    if (fs.existsSync(p)) return require(p);
  }
  throw new Error('playwright not found; set PLAYWRIGHT_DIR');
}
const { chromium } = findPlaywright();

const [mode, url, outArg] = process.argv.slice(2);
const out = path.resolve(outArg || path.join(__dirname, "..", "runs", "console-check"));   // screenshots stay git-ignored
fs.mkdirSync(out, { recursive: true });
const sleep = ms => new Promise(r => setTimeout(r, ms));
const results = [];
const check = (name, ok, detail) => { results.push({ name, ok: !!ok, detail }); console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail !== undefined ? '  ' + JSON.stringify(detail) : '')); };

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  const errors = [], failedReqs = [];
  page.on('pageerror', e => errors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('console.error: ' + m.text()); });
  page.on('requestfailed', r => { const u = r.url(); if (!u.endsWith('/events')) failedReqs.push(u); });
  const external = [];
  page.on('request', r => { const u = new URL(r.url()); if (!['127.0.0.1', 'localhost'].includes(u.hostname) && u.protocol.startsWith('http')) external.push(r.url()); });
  const S = (expr) => page.evaluate(`(() => { const S = window.__patrol.S; return (${expr}); })()`);
  const shot = async name => { const p = path.join(out, name); await page.screenshot({ path: p }); console.log('shot ' + p); };

  if (mode === 'voice') {
    // a stand-in microphone: getUserMedia returns a stream that stays silent until the test plays a fixture wav into it
    await page.addInitScript(() => {
      const AC = window.AudioContext || window.webkitAudioContext;
      let ac = null, dest = null, clip = null;
      const ensure = () => { ac = ac || new AC(); dest = dest || ac.createMediaStreamDestination(); };
      navigator.mediaDevices.getUserMedia = async () => { ensure(); if (ac.state === 'suspended') await ac.resume().catch(() => {}); return dest.stream; };
      window.__loadClip = async b64 => { ensure(); const u8 = Uint8Array.from(atob(b64), c => c.charCodeAt(0)); clip = await ac.decodeAudioData(u8.buffer); return clip.duration; };
      window.__playClip = () => { if (ac.state === 'suspended') ac.resume(); const src = ac.createBufferSource(); src.buffer = clip; src.connect(dest); src.start(); return clip.duration; };
    });
  }
  await page.goto(url, { waitUntil: 'load' });
  const t0 = Date.now();
  const apiUrl = p => new URL(p, url).toString();
  const waitFor = (fn, ms, arg) => page.waitForFunction(fn, arg, { timeout: ms }).then(() => true).catch(() => false);
  // wall-clock budget for one whole replay: the run's sim length over the playback speed, with slack (a 9-minute run at
  // speed 4 takes more than 2 minutes, so a fixed 60 s wait gave false FAILs)
  async function replayBudget() {
    let speed = null, simS = null;
    try { speed = (await (await fetch(apiUrl('api/state'))).json()).speed; } catch (e) {}
    if (!speed) speed = await S('S.speed').catch(() => null);
    try { simS = (await (await fetch(apiUrl('run/summary.json'))).json()).sim_s; } catch (e) {}
    if (!simS) {
      try {
        const lines = (await (await fetch(apiUrl('run/mission.jsonl'))).text()).trimEnd().split('\n');
        for (let i = lines.length - 1; i >= 0 && !simS; i--) { try { simS = JSON.parse(lines[i]).t || null; } catch (e) {} }
      } catch (e) {}
    }
    const ms = simS && speed ? Math.round((simS / speed) * 1500 + 45000) : 120000;
    return { speed, simS, ms: Math.max(60000, ms) };
  }

  if (mode === 'replay') {
    // the server replays once at start-up. If this page joined after the first alert (or after the end), wait for the
    // replay to finish and play it again, so the run is watched live and the alert moment is seen as it happens
    await sleep(1200);
    const RB = await replayBudget();
    console.log('replay budget', JSON.stringify(RB));
    if (!(await S('S.alerts.length === 0 && !S.summary'))) {
      console.log('joined mid-replay: waiting for it to finish, then Play again');
      await page.waitForFunction(() => !document.getElementById('bReplay').disabled, null, { timeout: RB.ms + 30000 });
      await page.locator('#bReplay').click();
      await page.waitForFunction(() => window.__patrol.S.alerts.length === 0 && !window.__patrol.S.summary, null, { timeout: 10000 }).catch(() => {});
    }
    // mid-run: the first investigation in flight
    await page.waitForFunction(() => window.__patrol && window.__patrol.S.spots.size > 0, null, { timeout: RB.ms }).catch(() => {});
    await sleep(1500);
    await shot('replay-1920x1080-investigating.png');
    // the first alert, or the run's own length at this speed
    const gotAlert = await page.waitForFunction(() => window.__patrol.S.alerts.length > 0, null, { timeout: RB.ms }).then(() => true).catch(() => false);
    check('replay produced an alert within the run time', gotAlert, { after_s: ((Date.now() - t0) / 1000).toFixed(1), budget_s: Math.round(RB.ms / 1000) });
    await sleep(900);
    check('alert banner shown on the camera at the alert', await page.locator('#banner span').isVisible(), await page.locator('#banner').textContent());
    await shot('replay-1920x1080-alert.png');
    await sleep(4000);
    await shot('replay-1920x1080-later.png');
    // wait for the summary: it ends the replay, however long the run is at this speed
    const done = await page.waitForFunction(() => !!window.__patrol.S.summary, null, { timeout: RB.ms }).then(() => true).catch(() => false);
    await sleep(1200);
    await shot('replay-1920x1080-end.png');
    check('replay reached the summary', done, { after_s: ((Date.now() - t0) / 1000).toFixed(1), budget_s: Math.round(RB.ms / 1000) });

    const info = await S(`({ state: S.state, path: S.path.length, frames: S.footprints.length, alerts: S.alerts.length, spots: S.spots.size,
      nClef: S.nClef, nFb: S.nFb, clues: S.clues.length, lanes: S.lanes.length, hasChase: S.hasChase, cov: S.coverage, mode: S.mode, t: S.t })`);
    console.log('state', JSON.stringify(info));
    check('track and footprints received', info.path > 50 && info.frames > 5, info);
    check('clue chips rendered', (await page.locator('.chip').count()) === info.clues && info.clues > 0);
    check('alert card rendered per alert', (await page.locator('.acard').count()) === info.alerts && info.alerts > 0);
    check('alert card images loaded', await page.evaluate(() => [...document.querySelectorAll('.acard img')].every(i => i.complete && i.naturalWidth > 0)));
    check('camera image loaded', await page.evaluate(() => { const i = document.getElementById('camImg'); return i.complete && i.naturalWidth > 0; }));
    check('chase panel hidden when no chase frames', !info.hasChase && !(await page.locator('#chasePanel').isVisible()));
    const sec = await S('({ sectors: S.sectors.length, cur: S.curSector, done: S.doneSectors.size, map: !!(S.spec && S.spec.map) })');
    console.log('sectors', JSON.stringify(sec));
    check('REPLAY label, no Start button', (await page.locator('#replayTag').isVisible()) && !(await page.locator('#ctl').isVisible()), await page.locator('#replayTag').textContent());
    check('log has entries', (await page.locator('#log .ev').count()) > 5);
    check('state badge shows DONE', (await page.locator('#stateBadge').textContent()) === 'DONE');
    check('SUMMARY entry in the log', (await page.locator('#log .ev .tg', { hasText: 'SUMMARY' }).count()) === 1);
    // the map has pixels: a non-background colour somewhere
    const mapInk = await page.evaluate(() => { const c = document.getElementById('map'), g = c.getContext('2d'); const d = g.getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 0; i < d.length; i += 4) if (d[i] > 60 || d[i + 1] > 60 || d[i + 2] > 60) n++; return n; });
    check('map canvas has content', mapInk > 2000, { lit_pixels: mapInk });
    const boxInk = await page.evaluate(() => { const c = document.getElementById('boxes'), g = c.getContext('2d'); if (!c.width) return 0; const d = g.getImageData(0, 0, c.width, c.height).data; let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i] > 0) n++; return n; });
    console.log('box overlay lit pixels', boxInk);

    // planted items toggle: off by default, scene.json fetched only when switched on
    check('planted items off by default', !(await page.locator('#togTruth').isChecked()) && (await S('S.truth === null')));
    await page.locator('#togTruth').check();
    await page.waitForFunction(() => window.__patrol.S.truth !== null, null, { timeout: 5000 }).catch(() => {});
    await sleep(400);
    const truthN = await S('S.truth ? S.truth.length : -1');
    check('planted items loaded on toggle', truthN > 0, { items: truthN });
    await shot('replay-1920x1080-planted.png');
    await page.locator('#togTruth').uncheck();

    // lightbox on the alert card
    await page.locator('.acard').first().click();
    await sleep(500);
    check('lightbox opens on card click', await page.locator('#lightbox').isVisible());
    await shot('replay-1920x1080-lightbox.png');
    await page.keyboard.press('Escape');
    check('lightbox closes on Esc', !(await page.locator('#lightbox').isVisible()));

    // smaller window
    await page.setViewportSize({ width: 1280, height: 800 });
    await sleep(900);
    await shot('replay-1280x800.png');
    const overflow = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, sh: document.documentElement.scrollHeight, ch: document.documentElement.clientHeight }));
    check('no page overflow at 1280x800', overflow.sw <= overflow.cw && overflow.sh <= overflow.ch, overflow);
    // a page reload mid-history rebuilds the same state
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.reload({ waitUntil: 'load' });
    await sleep(2500);
    const again = await S(`({ alerts: S.alerts.length, spots: S.spots.size, state: S.state, catchup: S.catchup })`);
    check('reload replays the history to the same state', again.alerts === info.alerts && again.spots === info.spots, again);
    await shot('replay-1920x1080-reloaded.png');
    // "Play again" restarts the replay: the page resets, then fills up again
    await page.waitForFunction(() => window.__patrol.S.summary, null, { timeout: 5000 }).catch(() => {});
    await page.waitForFunction(() => !document.getElementById('bReplay').disabled, null, { timeout: RB.ms }).catch(() => {});
    check('Play again enabled once the replay has finished', !(await page.locator('#bReplay').isDisabled()));
    await page.locator('#bReplay').click();
    const reset = await page.waitForFunction(() => window.__patrol.S.alerts.length === 0 && !window.__patrol.S.summary, null, { timeout: 10000 }).then(() => true).catch(() => false);
    check('Play again resets the page', reset);
    const again2 = await page.waitForFunction(() => window.__patrol.S.alerts.length > 0, null, { timeout: RB.ms + 30000 }).then(() => true).catch(() => false);
    check('second replay reaches the alert again, live (banner shows)', again2 && await page.locator('#banner span').isVisible().catch(() => false));
    await shot('replay-1920x1080-second-run.png');
  } else if (mode === 'live') {
    await sleep(800);
    check('Start button visible in live mode', await page.locator('#bStart').isVisible() && !(await page.locator('#replayTag').isVisible()));
    check('clue chips shown before takeoff', (await page.locator('.chip').count()) > 0);
    check('lanes known before takeoff', (await S('S.lanes.length')) > 0);
    await shot('live-before-start.png');
    await page.locator('#bStart').click();
    const gotFrames = await page.waitForFunction(() => window.__patrol.S.frame !== null && window.__patrol.S.path.length > 20, null, { timeout: 120000 }).then(() => true).catch(() => false);
    check('ticks and frames reached the page', gotFrames, await S(`({ ticks: S.path.length, state: S.state, t: S.t, frame: S.frame && S.frame.n, chase: S.chaseUrl })`));
    await sleep(2500);
    await shot('live-flying.png');
    const info = await S(`({ nClef: S.nClef, nFb: S.nFb, hasChase: S.hasChase, state: S.state, path: S.path.length, judged: S.strip.length, cov: S.coverage })`);
    console.log('state', JSON.stringify(info));
    check('Clef unreachable: every answer is FALLBACK', info.nFb > 0 && info.nClef === 0, info);
    check('chase panel visible, image loaded', (await page.locator('#chasePanel').isVisible()) && await page.evaluate(() => { const i = document.getElementById('chaseImg'); return i.complete && i.naturalWidth > 0; }));
    check('camera image loaded', await page.evaluate(() => { const i = document.getElementById('camImg'); return i.complete && i.naturalWidth > 0; }));
    check('Return home enabled while flying', !(await page.locator('#bHome').isDisabled()));
    await page.locator('#bHome').click();
    const home = await page.waitForFunction(() => window.__patrol.S.state === 'RETURN' || window.__patrol.S.state === 'DONE', null, { timeout: 30000 }).then(() => true).catch(() => false);
    check('Return home command reached the mission', home, await S('S.state'));
    await sleep(1500);
    await shot('live-returning.png');
    const ops = await page.locator('#log .ev .tg', { hasText: 'OPERATOR' }).count();
    check('operator entry in the log', ops > 0, ops);
    const done = await page.waitForFunction(() => window.__patrol.S.summary, null, { timeout: 90000 }).then(() => true).catch(() => false);
    check('flight ended with a summary', done, await S('S.state'));
    await sleep(2500);
    check('Start button offers "Fly again"', (await page.locator('#bStart').textContent()) === 'Fly again' && !(await page.locator('#bStart').isDisabled()), await page.locator('#bStart').textContent());
    await shot('live-done.png');
    await page.locator('#bStart').click();
    const fresh = await page.waitForFunction(() => window.__patrol.S.path.length > 5 && !window.__patrol.S.summary, null, { timeout: 60000 }).then(() => true).catch(() => false);
    check('second flight starts from a clean page', fresh, await S('({ ticks: S.path.length, state: S.state, run: S.run })'));
    await sleep(1500);
    await shot('live-second-flight.png');
  }

  if (mode === 'livefake') {
    // live flight against a stand-in for Clef that answers by blue-pixel count: investigate, confirm, alert, operator
    await sleep(800);
    await page.locator('#bStart').click();
    const gotAlert = await page.waitForFunction(() => window.__patrol.S.alerts.length > 0, null, { timeout: 180000 }).then(() => true).catch(() => false);
    check('live flight produced an alert', gotAlert, await S('({ t: S.t, state: S.state, spots: S.spots.size, nClef: S.nClef, nFb: S.nFb })'));
    await sleep(700);
    check('alert banner shown live', await page.locator('#banner span').isVisible().catch(() => false));
    await shot('livefake-alert.png');
    // a second page joining mid-flight rebuilds the same picture from the replayed history
    const page2 = await ctx.newPage();
    const errs2 = [];
    page2.on('pageerror', e => errs2.push(e.message));
    await page2.goto(url, { waitUntil: 'load' });
    await sleep(2500);
    const late = await page2.evaluate(() => ({ alerts: window.__patrol.S.alerts.length, catchup: window.__patrol.S.catchup, path: window.__patrol.S.path.length, spots: window.__patrol.S.spots.size }));
    const main = await S('({ alerts: S.alerts.length, spots: S.spots.size })');
    check('late-joining page catches up to the live state', late.alerts >= main.alerts && late.catchup === false && late.path > 20 && errs2.length === 0, { late, main, errs2 });
    await page2.screenshot({ path: path.join(out, 'livefake-late-joiner.png') });
    await page2.close();
    // operator: go back to the last alert once the drone is sweeping again
    const sweeping = await page.waitForFunction(() => ['SWEEP', 'RESUME'].includes(window.__patrol.S.state) && !document.getElementById('bLast').disabled, null, { timeout: 60000 }).then(() => true).catch(() => false);
    check('Go to last alert enabled while sweeping with an alert', sweeping, await S('S.state'));
    if (sweeping) {
      await page.locator('#bLast').click();
      const back = await page.waitForFunction(() => window.__patrol.S.state === 'INVESTIGATE', null, { timeout: 30000 }).then(() => true).catch(() => false);
      check('Go to last alert sent the drone back to investigate', back, await S('S.state'));
      await sleep(1500);
      await shot('livefake-revisit.png');
    }
    const finished = await page.waitForFunction(() => window.__patrol.S.summary, null, { timeout: 240000 }).then(() => true).catch(() => false);
    check('flight finished with a summary', finished, await S('({ state: S.state, t: S.t })'));
    await sleep(2000);
    await shot('livefake-end.png');
    const info = await S(`({ nClef: S.nClef, nFb: S.nFb, alerts: S.alerts.length, spots: S.spots.size, steps: Object.keys(S.steps).length, hasChase: S.hasChase, cov: S.coverage })`);
    console.log('state', JSON.stringify(info));
    check('answers came from Clef (stand-in), none from FALLBACK', info.nClef > 0 && info.nFb === 0, info);
    check('alert cards match alerts', (await page.locator('.acard').count()) === info.alerts && info.alerts > 0);
    check('operator entries in the log', (await page.locator('#log .ev .tg', { hasText: 'OPERATOR' }).count()) >= 1);
    check('chase panel visible', await page.locator('#chasePanel').isVisible());
    check('alert card images loaded', await page.evaluate(() => [...document.querySelectorAll('.acard img')].every(i => i.complete && i.naturalWidth > 0)));
  }

  if (mode === 'voice') {
    // Push-to-talk and spoken alerts against a console started with --voice --speak. No real microphone: the fixture
    // clips are POSTed from node, and the browser path (hold, record, send) is fed by the stand-in getUserMedia above.
    const fixDir = path.join(__dirname, '..', 'fixtures', 'voice');
    const clip = n => fs.readFileSync(path.join(fixDir, n));
    const postVoice = async (name) => {
      const r = await fetch(apiUrl('api/voice'), { method: 'POST', headers: { 'Content-Type': 'audio/wav' }, body: clip(name) });
      return { status: r.status, j: await r.json().catch(() => null) };
    };
    const nVoiceLines = async () => (await logTags()).filter(e => e.tag === 'VOICE').length;
    const logTags = () => page.evaluate(() => [...document.querySelectorAll('#log .ev')].map(e => ({ tag: e.querySelector('.tg').textContent, text: e.querySelector('.tx').textContent })));
    const speechLog = () => page.evaluate(() => window.__patrol.voice.speechLog.map(s => ({ id: s.id, url: s.url, error: s.error })));
    const audioOk = async u => {      // the clip the page would play: 200 and an audio/wav type
      const r = await fetch(apiUrl(u.replace(/^\//, '')));
      const buf = Buffer.from(await r.arrayBuffer());
      return { url: u, status: r.status, type: r.headers.get('content-type'), bytes: buf.length, riff: buf.slice(0, 4).toString() === 'RIFF' };
    };
    const isWav = a => a.status === 200 && /^audio\/(x-)?(wav|vnd\.wave|wave)/.test(a.type || '') && a.bytes > 1000 && a.riff;

    await sleep(1500);
    const v0 = await page.evaluate(() => window.__patrol.voice);
    check('push-to-talk button visible (ready event says voice)', v0.voiceOn && await page.locator('#bPtt').isVisible(), { voiceOn: v0.voiceOn, text: await page.locator('#bPtt').textContent() });
    check('Sound button visible, starts off', (await page.locator('#bSound').isVisible()) && (await page.locator('#bSound').textContent()) === 'Sound off');
    check('Start button visible before takeoff', await page.locator('#bStart').isVisible());
    const namesBefore = await S('S.clues.map(c => c.name)');
    const runBefore = await S('S.run');
    await shot('voice-1-before.png');

    // 1. a spoken description before takeoff: Parakeet, Clef routes it to "describe", qwen38 writes the clues
    const tD = Date.now();
    const d = await postVoice('describe_demo.wav');
    check('POST describe_demo.wav to /api/voice is routed to describe', d.status === 200 && d.j && d.j.route === 'describe' && d.j.accepted,
      { status: d.status, text: d.j && d.j.text, route: d.j && d.j.route, p: d.j && d.j.p, source: d.j && d.j.source, error: d.j && d.j.error, wall_s: ((Date.now() - tD) / 1000).toFixed(1) });
    const changed = await waitFor(before => JSON.stringify(window.__patrol.S.clues.map(c => c.name)) !== before, 60000, JSON.stringify(namesBefore));
    await sleep(700);
    const namesAfter = await S('S.clues.map(c => c.name)');
    const chips = await page.locator('.chip').allTextContents();
    check('page shows qwen38 clue chips (names changed, one is a dog)', changed && namesAfter.some(n => /dog/.test(n)) && chips.length === namesAfter.length && chips.some(t => /dog/i.test(t)),
      { before: namesBefore, after: namesAfter, chips: chips.length, run_before: runBefore, run_after: await S('S.run') });
    await shot('voice-2-clues.png');

    // 2. the spoken answer ("Looking for ...") reaches the page with an audio file the console serves
    const gotSpeech = await waitFor(() => window.__patrol.voice.speechLog.length > 0, 60000);
    const sp1 = await speechLog();
    check('a speech event arrived after the description', gotSpeech && sp1.length > 0, sp1);
    const au1 = sp1.filter(s => s.url).length ? await audioOk(sp1.filter(s => s.url)[0].url) : null;

    // 3. Sound on, then Start: the flight begins and speech is played, one clip at a time
    await page.locator('#bSound').click();
    check('Sound button turns on', (await page.locator('#bSound').textContent()) === 'Sound on' && (await page.evaluate(() => window.__patrol.voice.soundOn)));
    await page.locator('#bStart').click();
    const flying = await waitFor(() => window.__patrol.S.path.length > 5 && window.__patrol.S.state, 90000);
    check('pressing Start begins the flight', flying, await S('({ state: S.state, ticks: S.path.length, run: S.run })'));
    await sleep(1500);
    await shot('voice-3-flying.png');

    // 3b. a clip spoken from somewhere else (another page, a script) shows in this page's log from the event stream
    const nv0 = await nVoiceLines();
    const other = await postVoice('go_back_alert.wav');
    await sleep(1500);
    const lgo = (await logTags()).filter(e => e.tag === 'VOICE');
    check('a clip POSTed from elsewhere appears as one VOICE line (event stream)', other.status === 200 && lgo.length === nv0 + 1 && /go_back_to_last_alert/.test(lgo[0].text), lgo[0]);

    // 4. the browser path: hold the button, speak (a fixture clip into the stand-in microphone), release
    const dur = await page.evaluate(b64 => window.__loadClip(b64), clip('go_back_alert.wav').toString('base64'));
    const v1 = await nVoiceLines();
    const bb = await page.locator('#bPtt').boundingBox();
    await page.mouse.move(bb.x + bb.width / 2, bb.y + bb.height / 2);
    await page.mouse.down();
    await sleep(400);
    const recOn = await page.evaluate(() => ({ cls: document.getElementById('bPtt').className, text: document.getElementById('bPtt').textContent, rec: window.__patrol.voice.ptt.recording }));
    check('button shows Listening while held', /\bon\b/.test(recOn.cls) && /Listening/.test(recOn.text) && recOn.rec, recOn);
    const hdr = await page.evaluate(() => { const h = document.querySelector('header'), r = h.getBoundingClientRect(); return { header_h: Math.round(r.height), ptt_w: Math.round(document.getElementById('bPtt').getBoundingClientRect().width) }; });
    check('header stays one row while recording (no layout jump)', hdr.header_h < 90, hdr);
    await page.evaluate(() => window.__playClip());
    await sleep(dur * 1000 + 700);
    await shot('voice-4-recording.png');
    const sent0 = await page.evaluate(() => window.__patrol.voice.ptt.sent);
    await page.mouse.up();
    const sentOk = await waitFor(n => window.__patrol.voice.ptt.sent > n, 60000, sent0);
    await sleep(500);
    const lg = (await logTags()).filter(e => e.tag === 'VOICE');
    check('release POSTs the clip and the VOICE line lands in the log', sentOk && lg.length === v1 + 1, lg[0]);
    check('VOICE line carries transcript, route and source', lg.length > v1 && /“.+”/.test(lg[0].text) && /go_back_to_last_alert/.test(lg[0].text) && /Clef \d+%/.test(lg[0].text), lg[0] && lg[0].text);
    check('button back to Hold to talk', (await page.locator('#bPtt').textContent()) === 'Hold to talk');
    await shot('voice-5-after-release.png');

    // 5. the space bar does the same when focus is not in a field
    await page.evaluate(() => { if (document.activeElement && document.activeElement.blur) document.activeElement.blur(); });
    await page.keyboard.down('Space');
    await sleep(400);
    const recKey = await page.evaluate(() => window.__patrol.voice.ptt.recording);
    check('space bar held starts recording', recKey);
    await page.evaluate(() => window.__playClip());
    await sleep(dur * 1000 + 700);
    const sent1 = await page.evaluate(() => window.__patrol.voice.ptt.sent);
    await page.keyboard.up('Space');
    await waitFor(n => window.__patrol.voice.ptt.sent > n, 60000, sent1);
    await sleep(2500);
    check('space bar release also logs a VOICE line', (await nVoiceLines()) === v1 + 2, await nVoiceLines());

    // 6. spoken acknowledgements: speech events with audio, each served as wav, and the page plays them
    const gotAck = await waitFor(n => window.__patrol.voice.speechLog.filter(s => s.live && s.url).length > n, 90000, 0);
    const sp2 = (await speechLog()).filter(s => s.url);
    check('at least one speech event with an audio URL arrived during the flight', gotAck && sp2.length >= 2, sp2.map(s => s.id));
    const audios = [];
    for (const s of sp2) audios.push(await audioOk(s.url));
    check('speech audio URL returns 200 audio/wav from the console (at least one)', audios.some(isWav), audios.filter(isWav).map(a => ({ url: a.url, type: a.type, bytes: a.bytes })));
    check('every speech audio URL is served (the answer to the description too)', audios.length > 0 && audios.every(isWav) && au1 && isWav(au1), { describe_answer: au1, bad: audios.filter(a => !isWav(a)) });
    const played = await waitFor(() => window.__patrol.voice.playStats.ended >= 1, 30000);
    check('Sound on: the page played a spoken clip to the end', played, await page.evaluate(() => window.__patrol.voice.playStats));
    const drained = await waitFor(() => !window.__patrol.voice.speaking && window.__patrol.voice.queued === 0, 60000);
    const ps = await page.evaluate(() => ({ playStats: window.__patrol.voice.playStats, queued: window.__patrol.voice.queued, speaking: window.__patrol.voice.speaking }));
    check('speech queue drains, clips played one at a time to the end, no errors', drained && ps.playStats.errors === 0 && ps.playStats.ended === ps.playStats.started, ps);

    // 7. layout at a laptop size still fits
    await page.setViewportSize({ width: 1280, height: 800 });
    await sleep(900);
    await shot('voice-6-1280x800.png');
    const overflow = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, sh: document.documentElement.scrollHeight, ch: document.documentElement.clientHeight }));
    check('no page overflow at 1280x800 with the voice controls', overflow.sw <= overflow.cw && overflow.sh <= overflow.ch, overflow);
    const flog = await logTags();
    console.log('log tags', JSON.stringify(flog.slice(0, 12).map(e => e.tag + ': ' + e.text.slice(0, 90))));
  }

  check('no external requests (Wi-Fi off safe)', external.length === 0, external.slice(0, 3));
  check('no failed requests', failedReqs.length === 0, failedReqs.slice(0, 5));
  check('no JS errors in the console', errors.length === 0, errors.slice(0, 5));
  fs.writeFileSync(path.join(out, mode + '-results.json'), JSON.stringify({ mode, url, results, errors, failedReqs }, null, 1));
  await browser.close();
  process.exit(results.every(r => r.ok) ? 0 : 1);
})().catch(e => { console.error('check crashed:', e); process.exit(2); });
