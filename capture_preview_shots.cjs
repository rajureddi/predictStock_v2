const { chromium } = require('C:/Users/rajub/AppData/Local/npm-cache/_npx/e41f203b7505f1fb/node_modules/playwright');
const http = require('http');
const path = require('path');
const fs = require('fs');

async function testShots() {
  const server = http.createServer((req, res) => {
    let reqPath = req.url.split('?')[0];
    if (reqPath === '/') reqPath = '/marketmind-3d.html';
    const filePath = path.join(__dirname, reqPath);
    if (fs.existsSync(filePath)) {
      const ext = path.extname(filePath);
      const mimeTypes = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png' };
      res.writeHead(200, { 'Content-Type': mimeTypes[ext] || 'application/octet-stream' });
      fs.createReadStream(filePath).pipe(res);
    } else {
      res.writeHead(404);
      res.end('Not found');
    }
  });

  await new Promise((resolve) => server.listen(8766, '127.0.0.1', resolve));
  console.log('HTTP Server listening on http://127.0.0.1:8766');

  const browser = await chromium.launch({
    channel: 'msedge',
    headless: true,
    args: ['--enable-webgl', '--ignore-gpu-blocklist', '--use-gl=angle', '--use-angle=d3d11']
  });

  const page = await browser.newPage({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1
  });

  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', err => console.error('PAGE ERROR:', err.message));

  const url = 'http://127.0.0.1:8766/marketmind-3d.html?render=1';
  console.log('Navigating to:', url);
  await page.goto(url, { waitUntil: 'domcontentloaded' });

  await page.waitForFunction(() => window.isReady === true, { timeout: 20000 });
  console.log('Page ready!');

  const shots = [
    { name: 'marketmind_shot1_macro.png', t: 1.5 },
    { name: 'marketmind_shot2_dolly.png', t: 5.0 },
    { name: 'marketmind_shot3_crane.png', t: 8.3 },
    { name: 'marketmind_shot4_unhinge.png', t: 12.0 },
    { name: 'marketmind_shot5_signature.png', t: 15.5 },
    { name: 'marketmind_shot6_settle.png', t: 18.5 }
  ];

  for (const shot of shots) {
    await page.evaluate((t) => window.renderAtTime(t), shot.t);
    await page.waitForTimeout(100);
    const buf = await page.screenshot({ type: 'png' });
    fs.writeFileSync(path.join(__dirname, shot.name), buf);
    console.log(`Saved ${shot.name} at t=${shot.t}s (${buf.length} bytes)`);
  }

  await browser.close();
  server.close();
  console.log('Preview shots capture complete!');
}

testShots().catch(err => {
  console.error('Error:', err);
  process.exit(1);
});

