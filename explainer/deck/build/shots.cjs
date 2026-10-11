const fs = require('fs'), path = require('path'), os = require('os');
const base = path.join(os.homedir(), '.npm', '_npx'); let pw;
for (const d of fs.readdirSync(base)) { const p = path.join(base, d, 'node_modules', 'playwright'); if (fs.existsSync(p)) { pw = require(p); break; } }
(async () => {
  const b = await pw.chromium.launch();
  const pg = await b.newPage({ viewport: { width: 1280, height: 900 }, colorScheme: 'light', deviceScaleFactor: 2 });
  await pg.goto('file://' + path.resolve(__dirname, '../../index.html'), { waitUntil: 'load' });
  await pg.waitForTimeout(500);
  // scroll through to load lazy images
  const H = await pg.evaluate(() => document.body.scrollHeight);
  for (let y = 0; y < H; y += 600) { await pg.evaluate(y => window.scrollTo(0, y), y); await pg.waitForTimeout(120); }
  await pg.waitForTimeout(800);
  await pg.evaluate(() => {
    const rep = t => t.replace(/aloud to you/g,'aloud').replace(/or you say so/g,'or the operator says so').replace(/you say \u201Ccome home\u201D/g,'the operator says \u201Ccome home\u201D');
    document.querySelectorAll('.diagram svg text, .diagram svg tspan, .diagram text').forEach(n => { if (n.children.length === 0) n.textContent = rep(n.textContent); });
  });
  const dump = await pg.evaluate(() => [...document.querySelectorAll('.diagram')].map(d => d.textContent.replace(/\s+/g,' ')));
  fs.writeFileSync('diagram_text.txt', dump.join('\n---\n'));
  const items = [ ['m3dstrip', '#cast figure.wide']];
  const ds = await pg.$$('.diagram');
  for (let i = 0; i < ds.length; i++) items.push(['diagram' + i, null, ds[i]]);
  { const mw = await pg.$('.mapwrap'); await mw.scrollIntoViewIfNeeded(); await pg.waitForTimeout(300);
    const a = await mw.boundingBox(); const p = await (await pg.$('#profile')).boundingBox();
    await pg.screenshot({ path: 'map.png', clip: { x: a.x, y: a.y, width: a.width, height: p.y + p.height - a.y } });
    console.log('map', a.width, p.y + p.height - a.y); }
  for (const [name, sel, h] of items) {
    const el = h || await pg.$(sel);
    await el.scrollIntoViewIfNeeded(); await pg.waitForTimeout(250);
    const box = await el.boundingBox();
    await el.screenshot({ path: name + '.png' });
    console.log(name, Math.round(box.width), Math.round(box.height));
  }
  await b.close();
})();
