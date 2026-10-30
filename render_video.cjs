const { chromium } = require('C:/Users/rajub/AppData/Local/npm-cache/_npx/e41f203b7505f1fb/node_modules/playwright');
const http = require('http');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');

async function renderVideo() {
  const TOTAL_SECONDS = 20.0;
  const FPS = 30;
  const TOTAL_FRAMES = TOTAL_SECONDS * FPS; // 600 frames
  const OUTPUT_FILE = path.join(__dirname, 'marketmind-pro-3d.mp4');

  console.log(`Starting video render: ${TOTAL_FRAMES} frames @ ${FPS} FPS -> ${OUTPUT_FILE}`);

  // Static HTTP server
  const server = http.createServer((req, res) => {
    let p = req.url.split('?')[0];
    if (p === '/') p = '/marketmind-3d.html';
    const fp = path.join(__dirname, p);
    if (fs.existsSync(fp)) {
      const ext = path.extname(fp);
      const mime = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css' };
      res.writeHead(200, { 'Content-Type': mime[ext] || 'application/octet-stream' });
      fs.createReadStream(fp).pipe(res);
    } else {
      res.writeHead(404);
      res.end();
    }
  });

  await new Promise(r => server.listen(8770, '127.0.0.1', r));
  console.log('HTTP Server listening on 8770');

  // Spawn FFmpeg process
  const ffmpegArgs = [
    '-y',
    '-f', 'image2pipe',
    '-vcodec', 'mjpeg',
    '-r', String(FPS),
    '-i', '-',
    '-c:v', 'libx264',
    '-pix_fmt', 'yuv420p',
    '-crf', '18',
    '-preset', 'fast',
    OUTPUT_FILE
  ];

  const ffmpeg = spawn('ffmpeg', ffmpegArgs, { stdio: ['pipe', 'inherit', 'inherit'] });

  ffmpeg.on('error', (err) => {
    console.error('FFmpeg spawn error:', err);
  });

  const browser = await chromium.launch({
    channel: 'msedge',
    headless: true,
    args: ['--enable-webgl', '--ignore-gpu-blocklist', '--use-gl=angle', '--use-angle=d3d11']
  });

  const page = await browser.newPage({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1
  });

  page.on('pageerror', err => console.error('PAGE ERROR:', err.message));

  console.log('Loading page in render mode...');
  await page.goto('http://127.0.0.1:8770/marketmind-3d.html?render=1', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => window.isReady === true, { timeout: 30000 });
  console.log('Page ready. Beginning frame-by-frame capture...');

  const startTime = Date.now();

  for (let frame = 0; frame < TOTAL_FRAMES; frame++) {
    const tSec = frame / FPS;

    // Render exact frame deterministically
    await page.evaluate((t) => window.renderAtTime(t), tSec);

    // Capture JPEG buffer
    const buf = await page.screenshot({ type: 'jpeg', quality: 96 });

    // Pipe to FFmpeg stdin
    if (!ffmpeg.stdin.write(buf)) {
      await new Promise(r => ffmpeg.stdin.once('drain', r));
    }

    if (frame % 60 === 0 || frame === TOTAL_FRAMES - 1) {
      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
      const pct = ((frame / TOTAL_FRAMES) * 100).toFixed(0);
      console.log(`Frame ${frame}/${TOTAL_FRAMES} (${pct}%) — t=${tSec.toFixed(2)}s — elapsed ${elapsed}s`);
    }
  }

  ffmpeg.stdin.end();

  await new Promise((resolve, reject) => {
    ffmpeg.on('close', (code) => {
      if (code === 0) resolve();
      else reject(new Error(`FFmpeg exited with code ${code}`));
    });
  });

  await browser.close();
  server.close();

  const totalTime = ((Date.now() - startTime) / 1000).toFixed(1);
  const stats = fs.statSync(OUTPUT_FILE);
  console.log(`Video render complete in ${totalTime}s! File size: ${(stats.size / 1024 / 1024).toFixed(2)} MB`);
}

renderVideo().catch(err => {
  console.error('Render failed:', err);
  process.exit(1);
});

