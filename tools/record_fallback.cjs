// Record the patrol console replaying a recorded flight, and build the stage fallback video (demo/fallback.mp4).
//   node tools/record_fallback.cjs [--url http://127.0.0.1:8786/] [--run runs/s6-fallback-flight] [--out demo/fallback.mp4]
//        [--work runs/scratch/fallback-build] [--readback media/audio/clues_0.wav | none] [--remix]
// Usually run through tools/make_fallback.sh, which starts and stops the replay console (bin/patrol console --replay RUN --speed S).
//
// How it works (all measured, nothing guessed):
//  1. The replay console streams the run once as soon as it starts, before any page is open, and a page that joins late only
//     gets that history as silent "catch-up". So this script waits for that first replay to finish, opens the page, turns
//     "Sound on", and clicks "Play again": the server resets the page and streams the run again, live, from sim t=0.
//  2. Playwright records the page (recordVideo, 1280x800, no audio). A magenta page is shown first as a clock mark: the first
//     magenta frame in the video fixes the wall-clock time of video t=0. The cut is made at the page's own "reset" event.
//  3. An init script logs the wall time of every SSE event the page receives and of every audio clip the page starts to play
//     (HTMLMediaElement.play of a /run/... wav). The page queues clips one at a time, so these are exactly the moments the
//     live console would have spoken them. ffmpeg then places each flight WAV at that moment (adelay + amix, normalize=0)
//     and muxes H.264 + AAC. --remix redoes only this step from the saved raw.webm and timing.json.
//  4. One constructed addition: the CLI flight has no description read-back (only the console's push-to-talk flow says it).
//     If <run>/media/audio/clues_0.wav exists (tools/make_readback.py), it is fed to the page as a "speech" event right after
//     takeoff, so it gets the same caption and log line as a live one. --readback none leaves it out. timing.json lists it.
const fs = require('fs'), path = require('path'), os = require('os');
const { spawnSync } = require('child_process');

function findPlaywright() {
  if (process.env.PLAYWRIGHT_DIR) return require(process.env.PLAYWRIGHT_DIR);
  const base = path.join(os.homedir(), '.npm', '_npx');
  for (const d of fs.readdirSync(base)) {
    const p = path.join(base, d, 'node_modules', 'playwright');
    if (fs.existsSync(p)) return require(p);
  }
  throw new Error('playwright not found in ~/.npm/_npx; set PLAYWRIGHT_DIR');
}

const argv = process.argv.slice(2);
const arg = (name, dflt) => { const i = argv.indexOf('--' + name); return i >= 0 && i + 1 < argv.length ? argv[i + 1] : dflt; };
const ROOT = path.resolve(__dirname, '..');
const URL_ = arg('url', 'http://127.0.0.1:8786/');
const RUN = path.resolve(ROOT, arg('run', 'runs/s6-fallback-flight'));
const WORK = path.resolve(ROOT, arg('work', 'runs/scratch/fallback-build'));
const OUT = path.resolve(ROOT, arg('out', 'demo/fallback.mp4'));
const READBACK = arg('readback', 'media/audio/clues_0.wav');
const REMIX = argv.includes('--remix');
const VW = 1280, VH = 800, HOLD_S = 2.5, FPS = 25;
const AUDIO_LAG_MS = 0;       // extra voice delay. The page's alert banners show up in the video within 26-50 ms of their event times (s6 build), under one frame (40 ms) of the clip starts, so none is needed
const TARGET_LUFS = -18;      // the Kokoro clips are about -24 LUFS; one measured gain (max +10 dB) and a -1.5 dBFS limiter bring the mix up for the room
const sleep = ms => new Promise(r => setTimeout(r, ms));
const log = (...a) => console.log(new Date().toISOString().slice(11, 23), ...a);
const api = async p => (await fetch(new URL(p, URL_))).json();

async function record() {
  const { chromium } = findPlaywright();
  fs.mkdirSync(WORK, { recursive: true });
  const rawDir = path.join(WORK, 'raw');
  fs.rmSync(rawDir, { recursive: true, force: true });
  fs.mkdirSync(rawDir, { recursive: true });

  const summary = await api('run/summary.json');
  let st = await api('api/state');
  if (st.kind !== 'search') throw new Error('the console is not replaying a search run: ' + JSON.stringify(st));
  log('console', JSON.stringify(st), 'sim_s', summary.sim_s);

  // 1. wait for the replay the server starts by itself (no page is watching it)
  const budgetMs = (summary.sim_s / (st.speed || 1)) * 1000 * 1.3 + 90000;
  const t0 = Date.now();
  while (!(st.speed != null && st.running === false)) {
    if (Date.now() - t0 > budgetMs) throw new Error('the first replay did not finish in ' + Math.round(budgetMs / 1000) + ' s');
    await sleep(1000);
    st = await api('api/state');
  }
  log('first replay finished after', ((Date.now() - t0) / 1000).toFixed(1), 's of waiting; speed', st.speed);
  const speed = st.speed;

  const browser = await chromium.launch({ args: ['--mute-audio', '--autoplay-policy=no-user-gesture-required'] });
  const ctx = await browser.newContext({
    viewport: { width: VW, height: VH }, deviceScaleFactor: 1,
    recordVideo: { dir: rawDir, size: { width: VW, height: VH } },
  });
  const page = await ctx.newPage();
  const pageErrors = [], failed = [];
  page.on('pageerror', e => pageErrors.push('pageerror: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') pageErrors.push('console.error: ' + m.text()); });
  page.on('requestfailed', r => { if (!r.url().endsWith('/events')) failed.push(r.url()); });
  await page.addInitScript(() => {
    window.__timeline = []; window.__audioLog = [];
    const OrigES = window.EventSource;
    function ES(url, init) {
      const es = new OrigES(url, init);
      es.addEventListener('message', m => {
        try { const ev = JSON.parse(m.data); window.__timeline.push({ wall: Date.now(), type: ev.type, t: ev.t === undefined ? null : ev.t, id: ev.id === undefined ? null : ev.id }); } catch (e) {}
      });
      return es;
    }
    ES.prototype = OrigES.prototype; ES.CONNECTING = 0; ES.OPEN = 1; ES.CLOSED = 2;
    window.EventSource = ES;
    const origPlay = HTMLMediaElement.prototype.play;
    HTMLMediaElement.prototype.play = function () {
      const src = this.src || '';
      if (src && !src.startsWith('data:')) {
        const rec = { wall: Date.now(), src, ended: null, error: null };
        window.__audioLog.push(rec);
        this.addEventListener('ended', () => { rec.ended = Date.now(); }, { once: true });
        this.addEventListener('error', () => { rec.error = Date.now(); }, { once: true });
      }
      return origPlay.apply(this, arguments);
    };
  });

  // 2. the clock mark, then the console
  await page.setContent('<!doctype html><body style="margin:0;background:#f0f"></body>');
  const tFlash = Date.now();
  await sleep(900);
  await page.goto(URL_, { waitUntil: 'load' });
  await page.waitForFunction(() => window.__patrol && window.__patrol.S.summary && !document.getElementById('bReplay').disabled,
    null, { timeout: 60000, polling: 100 });
  await page.addStyleTag({ content: '#toast{display:none !important}' });      // no "replaying from the start" pop-up in the video
  await page.locator('#bSound').click();
  await page.waitForFunction(() => window.__patrol.voice.soundOn, null, { timeout: 5000 });
  await sleep(600);
  const tClick = Date.now();
  await page.locator('#bReplay').click();
  await page.waitForFunction(t => window.__timeline.some(e => e.type === 'reset' && e.wall >= t), tClick - 50, { timeout: 15000, polling: 20 });
  log('replay restarted; the page was reset');
  await page.waitForFunction(() => window.__patrol.S.path.length > 0, null, { timeout: 15000, polling: 20 });
  const resetWall = await page.evaluate(t => window.__timeline.filter(e => e.type === 'reset' && e.wall >= t).map(e => e.wall)[0], tClick - 50);
  await sleep(Math.max(0, resetWall + 400 - Date.now()));       // after the video cut (reset + 120 ms), so the clip is not cut off

  // the constructed read-back, if there is one
  let readback = null;
  const rbWav = path.join(RUN, READBACK), rbTxt = rbWav.replace(/\.wav$/, '.txt');
  if (READBACK !== 'none' && fs.existsSync(rbWav) && fs.existsSync(rbTxt)) {
    const text = fs.readFileSync(rbTxt, 'utf8').trim();
    readback = await page.evaluate(ev => { ev.t = window.__patrol.S.t; window.__patrol.ingest(ev); return { wall: Date.now(), t: ev.t }; },
      { type: 'speech', id: 'clues_0', text, audio: READBACK, tts_ms: null, audio_s: null, error: null });
    log('read-back fed to the page at sim t', readback.t);
  } else {
    log('no read-back (', READBACK, ')');
  }

  // 3. the replay, then the summary being spoken, then a short hold
  const endMs = (summary.sim_s / speed) * 1000 + 120000 + 40000;
  await page.waitForFunction(t => {
    const v = window.__patrol.voice;
    return !!window.__patrol.S.summary && window.__timeline.some(e => e.type === 'speech' && e.id === 'summary' && e.wall >= t) &&
      !v.speaking && v.queued === 0;
  }, tClick, { timeout: endMs, polling: 200 });
  await sleep(HOLD_S * 1000);
  const tEnd = Date.now();
  log('replay and speech finished after', ((tEnd - tClick) / 1000).toFixed(1), 's');

  const info = await page.evaluate(() => {
    const S = window.__patrol.S, v = window.__patrol.voice;
    return { state: S.state, alerts: S.alerts.length, spots: S.spots.size, t: S.t, hasChase: S.hasChase, nClef: S.nClef, nFb: S.nFb,
      playStats: v.playStats, speechLog: v.speechLog.map(s => ({ id: s.id, live: s.live, error: s.error, chars: s.text.length })),
      timeline: window.__timeline, audio: window.__audioLog };
  });
  await page.screenshot({ path: path.join(WORK, 'end.png') });
  const vpath = await page.video().path();
  await ctx.close();
  await browser.close();
  const tClose = Date.now();
  fs.renameSync(vpath, path.join(WORK, 'raw.webm'));
  const timing = {
    run: path.relative(ROOT, RUN), url: URL_, speed, sim_s: summary.sim_s, tFlash, tClick, tEnd, tClose, readback,
    reset: info.timeline.filter(e => e.type === 'reset' && e.wall >= tClick).map(e => e.wall)[0],
    timeline: info.timeline.filter(e => e.wall >= tClick), audio: info.audio.filter(a => a.wall >= tClick),
    final: { state: info.state, alerts: info.alerts, spots: info.spots, t: info.t, hasChase: info.hasChase, nClef: info.nClef, nFb: info.nFb },
    playStats: info.playStats, speechLog: info.speechLog, pageErrors, failedRequests: failed,
  };
  fs.writeFileSync(path.join(WORK, 'timing.json'), JSON.stringify(timing, null, 1));
  log('wrote', path.join(WORK, 'timing.json'), 'playStats', JSON.stringify(info.playStats), 'pageErrors', pageErrors.length);
}

function ff(cmd, args, opts = {}) {
  const r = spawnSync(cmd, args, { maxBuffer: 1 << 28, ...opts });
  if (r.status !== 0) throw new Error(cmd + ' failed: ' + (r.stderr ? r.stderr.toString().slice(-600) : r.status));
  return r.stdout;
}

function mix() {
  const T = JSON.parse(fs.readFileSync(path.join(WORK, 'timing.json'), 'utf8'));
  const raw = path.join(WORK, 'raw.webm');
  // the clock mark: the first magenta frame of the video is wall time T.tFlash
  const pts = ff('ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-show_entries', 'packet=pts_time', '-of', 'csv=p=0', raw])
    .toString().trim().split('\n').slice(0, 400).map(Number);
  const px = ff('ffmpeg', ['-v', 'error', '-i', raw, '-frames:v', '400', '-vf', `crop=8:8:${VW / 2 - 4}:${VH / 2 - 4},scale=1:1:flags=area,format=rgb24`,
    '-fps_mode', 'passthrough', '-f', 'rawvideo', '-']);
  let k = -1;
  for (let i = 0; i < Math.min(pts.length, px.length / 3); i++) {
    if (px[3 * i] > 180 && px[3 * i + 1] < 90 && px[3 * i + 2] > 180) { k = i; break; }
  }
  if (k < 0) throw new Error('clock mark (magenta frame) not found in ' + raw);
  const videoStartWall = T.tFlash - pts[k] * 1000;
  const startWall = T.reset + 120;                   // the cut: the page's reset, plus a few frames so no old frame is left
  const trimT = (startWall - videoStartWall) / 1000;
  const durS = (T.tEnd - startWall) / 1000;
  const rawDur = Number(ff('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', raw]).toString());
  if (trimT + durS > rawDur + 0.2) throw new Error(`raw video is ${rawDur}s, need ${trimT + durS}s`);

  const clips = T.audio.filter(a => !a.error).map(a => {
    const rel = decodeURIComponent(new URL(a.src).pathname).replace(/^\/run\//, '');
    return { rel, file: path.join(RUN, rel), delayMs: Math.round(a.wall - startWall), endedMs: a.ended ? Math.round(a.ended - startWall) : null };
  });
  const bad = T.audio.filter(a => a.error);
  if (bad.length) console.warn('WARNING: ' + bad.length + ' clip(s) failed to play in the page: ' + bad.map(b => b.src).join(', '));
  for (const c of clips) {
    if (c.delayMs < 0 && c.delayMs > -300) { console.warn(`WARNING: ${c.rel} started ${-c.delayMs} ms before the cut; placed at 0`); c.delayMs = 0; }
    if (c.delayMs < 0 || !fs.existsSync(c.file)) throw new Error('bad clip ' + JSON.stringify(c));
  }
  clips.forEach(c => log(`clip ${c.rel} at video ${(c.delayMs / 1000).toFixed(2)} s`));

  // the clips on one timeline (video time zero is the cut), at unity gain
  const mixWav = path.join(WORK, 'mix.wav');
  const dly = c => c.delayMs + AUDIO_LAG_MS;
  const fcMix = clips.map((c, i) => `[${i}:a]aresample=48000,pan=stereo|c0=c0|c1=c0,adelay=${dly(c)}|${dly(c)}[a${i}]`).join(';') + ';' +
    clips.map((c, i) => `[a${i}]`).join('') + `amix=inputs=${clips.length}:normalize=0:duration=longest,apad=whole_dur=${durS.toFixed(3)}[aout]`;
  const clipArgs = []; clips.forEach(c => clipArgs.push('-i', c.file));
  ff('ffmpeg', ['-y', '-v', 'error', ...clipArgs, '-filter_complex', fcMix, '-map', '[aout]', '-t', durS.toFixed(3), '-c:a', 'pcm_s16le', mixWav]);
  // one measured gain toward TARGET_LUFS, peaks held by a limiter
  const meas = spawnSync('ffmpeg', ['-hide_banner', '-nostats', '-i', mixWav, '-af', 'ebur128=peak=true', '-f', 'null', '-'], { encoding: 'utf8' }).stderr;
  const mI = /Integrated loudness:\s+I:\s+(-?[\d.]+) LUFS/.exec(meas), mP = /True peak:\s+Peak:\s+(-?[\d.]+) dBFS/.exec(meas);
  if (!mI) throw new Error('could not measure the mix loudness');
  const gainDb = Math.max(0, Math.min(10, TARGET_LUFS - Number(mI[1])));
  log(`mix loudness ${mI[1]} LUFS, true peak ${mP ? mP[1] : '?'} dBFS; gain +${gainDb.toFixed(1)} dB with a -1.5 dBFS limiter`);

  const args = ['-y', '-v', 'error', '-ss', trimT.toFixed(3), '-i', raw, '-i', mixWav,
    '-map', '0:v:0', '-map', '1:a:0', '-af', `volume=${gainDb.toFixed(1)}dB,alimiter=limit=0.84:level=disabled`, '-t', durS.toFixed(3),
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '23', '-pix_fmt', 'yuv420p', '-r', String(FPS),
    '-c:a', 'aac', '-b:a', '128k', '-ar', '48000', '-movflags', '+faststart', OUT];
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  ff('ffmpeg', args);
  const mixInfo = { out: path.relative(ROOT, OUT), video_s: durS, trim_s: trimT, clock_mark_video_s: pts[k], video_start_wall: videoStartWall,
    audio_lag_ms: AUDIO_LAG_MS, mix_lufs: Number(mI[1]), gain_db: gainDb, sim_to_video: `video_s = sim_t / ${T.speed} (+ small start offset, ~3 ms per event of sleep slack)`, clips };
  fs.writeFileSync(path.join(WORK, 'mix.json'), JSON.stringify(mixInfo, null, 1));
  log('wrote', OUT, 'duration', durS.toFixed(1), 's; clock mark at raw video', pts[k], 's; cut at', trimT.toFixed(2), 's');
}

(async () => {
  if (!REMIX) await record();
  mix();
})().catch(e => { console.error('FAILED:', e.message); process.exit(1); });
