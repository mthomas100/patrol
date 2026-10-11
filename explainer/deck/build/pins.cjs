const fs = require('fs'), path = require('path'), os = require('os');
const base = path.join(os.homedir(), '.npm', '_npx'); let pw;
for (const d of fs.readdirSync(base)) { const p = path.join(base, d, 'node_modules', 'playwright'); if (fs.existsSync(p)) { pw = require(p); break; } }
(async () => {
  const b = await pw.chromium.launch();
  const pg = await b.newPage({ viewport: { width: 1280, height: 900 } });
  await pg.goto('file://' + path.resolve(__dirname, '../../index.html'), { waitUntil: 'load' });
  const d = await pg.evaluate(() => ({
    pins: [...document.querySelectorAll('#glance .pin')].map(p => ({ n: p.textContent.trim(), left: p.style.left, top: p.style.top })),
    key: [...document.querySelectorAll('#glance .annot-key li')].map(li => li.innerText.replace(/\s+/g, ' ').trim()),
    img: document.querySelector('#glance img').getAttribute('src'),
  }));
  console.log(JSON.stringify(d, null, 1));
  await b.close();
})();
