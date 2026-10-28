// Vidéo « parcours des tirs » (1080×1350, 30 i/s) : chaque phase du Sankey s'ouvre l'une après l'autre.
// usage : node visuel_mbappe/render_video.js <joueur> [--fps 30] [--to 5] [--out chemin.mp4] [--gif-width 600]
//         -> sortie/<joueur>/video.mp4 + video.gif
// sort le MP4 et, à côté, le même parcours en GIF (15 i/s, 600 px de large, en boucle) pour les réseaux.
// La page sortie/<joueur>/interactive.html?video=1 expose window.__frame(t) : chaque image est dessinée pour un instant t
// précis (pas d'horloge réelle), donc l'animation reste fluide quelle que soit la vitesse de capture.
const path = require('path'), fs = require('fs'), os = require('os'), { execFileSync } = require('child_process');
const ROOT = path.resolve(__dirname, '..');
const puppeteer = require(path.join(ROOT, 'tools/node_modules/puppeteer-core'));
const { launchOptions } = require(path.join(ROOT, 'tools/browser'));
const { out: DIR, args } = require('./joueur')();
const FPS = +(args.fps || 30), OUT = args.out ? path.resolve(args.out) : path.join(DIR, 'video.mp4');

(async () => {
  const browser = await puppeteer.launch(launchOptions(['--hide-scrollbars', '--font-render-hinting=none']));
  const page = await browser.newPage();
  page.on('pageerror', e => console.error('PAGE ERROR', e.message));
  await page.setViewport({ width: 1080, height: 1350, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(DIR, 'interactive.html') + '?video=1', { waitUntil: 'networkidle0' });
  await page.waitForFunction(() => window.__ready === true);
  const duration = Math.min(+(args.to || Infinity), await page.evaluate(() => window.__duration));
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'shotflow-frames-'));
  const n = Math.round(duration * FPS);
  for (let i = 0; i < n; i++) {
    await page.evaluate(t => window.__frame(t), i / FPS);
    await page.screenshot({ path: path.join(dir, `f${String(i).padStart(5, '0')}.png`) });
    if (i % FPS === 0) process.stdout.write(`\r${(i / FPS).toFixed(0)}/${duration.toFixed(1)} s`);
  }
  await browser.close();
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', String(FPS), '-i', path.join(dir, 'f%05d.png'),
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'slow', '-movflags', '+faststart', OUT]);
  fs.rmSync(dir, { recursive: true, force: true });
  const GIF = OUT.replace(/\.mp4$/, '.gif'), gw = +(args['gif-width'] || 600);
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', OUT, '-vf',
    `fps=15,scale=${gw}:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle`,
    '-loop', '0', GIF]);
  console.log(`\n${path.relative(ROOT, OUT)} + ${path.basename(GIF)} : ${duration.toFixed(1)} s, ${n} images`);
})();
