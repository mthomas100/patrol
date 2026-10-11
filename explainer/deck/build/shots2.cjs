// Larger-label renders: diagram2 (geometry) with text scaled up, and the architecture diagram without its safety box.
const fs = require('fs'), path = require('path'), os = require('os');
const base = path.join(os.homedir(), '.npm', '_npx'); let pw;
for (const d of fs.readdirSync(base)) { const p = path.join(base, d, 'node_modules', 'playwright'); if (fs.existsSync(p)) { pw = require(p); break; } }
const BUMP = +(process.argv[2] || 1.3);
(async () => {
  const b = await pw.chromium.launch();
  const pg = await b.newPage({ viewport: { width: 1280, height: 900 }, colorScheme: 'light', deviceScaleFactor: 2 });
  await pg.goto('file://' + path.resolve(__dirname, '../../index.html'), { waitUntil: 'load' });
  await pg.waitForTimeout(500);
  const H = await pg.evaluate(() => document.body.scrollHeight);
  for (let y = 0; y < H; y += 600) { await pg.evaluate(y => window.scrollTo(0, y), y); await pg.waitForTimeout(100); }
  const info = await pg.evaluate((BUMP) => {
    const ds = document.querySelectorAll('.diagram');
    const out = {};
    const rep = t => t.replace(/aloud to you/g, 'aloud').replace(/or you say so/g, 'or the operator says so').replace(/you say “come home”/g, 'the operator says “come home”');
    ds[0].querySelectorAll('text').forEach(n => { if (n.children.length === 0) n.textContent = rep(n.textContent); });
    ds[1].querySelectorAll('text').forEach(n => { if (n.children.length === 0) n.textContent = rep(n.textContent); });
    const t = ds[2].querySelectorAll('text');
    out.sizes = [...t].map(n => getComputedStyle(n).fontSize);
    t.forEach(n => { n.style.fontSize = (parseFloat(getComputedStyle(n).fontSize) * BUMP) + 'px'; });
    return out;
  }, BUMP);
  console.log(JSON.stringify(info.sizes.slice(0, 40)));
  const ds = await pg.$$('.diagram');
  await ds[2].scrollIntoViewIfNeeded(); await pg.waitForTimeout(200);
  await ds[2].screenshot({ path: 'diagram2-big.png' });
  await ds[0].scrollIntoViewIfNeeded(); await pg.waitForTimeout(200);
  const bb = await ds[0].boundingBox();
  // arch: drop the safety box at the bottom (y > ~ 0.84 of height) and trim the top margin
  await pg.screenshot({ path: 'arch-main.png', clip: { x: bb.x, y: bb.y + bb.height * 0.055, width: bb.width, height: bb.height * 0.78 } });
  await b.close();
})();
