// Carrousel Instagram de petites vidéos (1080×1350, 30 i/s), comme les posts « Shot Flow » de graphsketball :
//   clip 1 : la fresque complète, puis un zoom et un panoramique de gauche à droite ;
//   clips 2 à 8 : une phase par clip, la colonne suivante se déroule et la caméra la suit.
// usage : node visuel_mbappe/render_collage_video.js [--only 3]   -> visuel_mbappe/collage/video_1..8.mp4
// Les images viennent du mode vidéo de fresque_interactive.html (?video=1, window.__frame(t)), rendues en ×2 puis réduites.
const path = require('path'), fs = require('fs'), os = require('os'), { execFileSync } = require('child_process');
const ROOT = path.resolve(__dirname, '..');
const puppeteer = require(path.join(ROOT, 'tools/node_modules/puppeteer-core'));
const { launchOptions } = require(path.join(ROOT, 'tools/browser'));
const args = Object.fromEntries(process.argv.slice(2).join(' ').split('--').filter(Boolean).map(s => { const [k, ...v] = s.trim().split(' '); return [k, v.join(' ') || true]; }));
const FPS = 30, OUT = path.join(__dirname, 'collage');

// clip d'une phase : 0,8 s d'arrêt sur l'état précédent, 2,5 s d'ouverture, 1,2 s de pause
const PHASE = { still: .8, rev: 2.5, hold: 1.2 };
// clip 1 : fresque entière, zoom vers la gauche, panoramique, pause
const ALL = { whole: 1.4, zoom: 1.3, pan: 4.2, hold: .8 };

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await puppeteer.launch(launchOptions(['--hide-scrollbars', '--font-render-hinting=none']));
  const page = await browser.newPage();
  page.on('pageerror', e => console.error('PAGE ERROR', e.message));
  await page.setViewport({ width: 1080, height: 1350, deviceScaleFactor: 2 });
  await page.goto('file://' + path.join(__dirname, 'fresque_interactive.html') + '?video=1', { waitUntil: 'networkidle0' });
  await page.waitForFunction(() => window.__ready === true);
  await page.addStyleTag({ content: ':root { --grid: transparent !important; }' });

  // __clip(c, ct) dessine l'image du clip c à l'instant ct (secondes)
  await page.evaluate((PHASE, ALL) => {
    const ease = p => p < .5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2, cl = v => Math.max(0, Math.min(1, v));
    window.__clipLen = c => c === 1 ? ALL.whole + ALL.zoom + ALL.pan + ALL.hold : PHASE.still + PHASE.rev + PHASE.hold;
    window.__clip = (c, ct) => {
      if (c === 1) {
        window.__frame(window.__duration);              // fresque complète, toutes les phases ouvertes
        const sf = VIEW_W / W, maxCam = W - VIEW_W / SC;
        const z = 1 - ease(cl((ct - ALL.whole) / ALL.zoom));
        const pan = ease(cl((ct - ALL.whole - ALL.zoom) / ALL.pan));
        const sc = SC + (sf - SC) * z, cam = maxCam * pan * (1 - z), ty = (VIEW_H - HH * sc) / 2 * z;
        svg.style.transform = `translate(${-cam * sc}px, ${ty}px) scale(${sc})`;
        document.getElementById('ph').textContent = 'Le parcours complet';
        return;
      }
      const k = c - 2, t0 = phaseStart(k);         // phase k (0 = zone) : même timeline que la vidéo, au ralenti
      const t = ct < PHASE.still ? t0
        : ct < PHASE.still + PHASE.rev ? t0 + (ct - PHASE.still) / PHASE.rev * TL.rev
        : t0 + TL.rev + Math.min(.9, (ct - PHASE.still - PHASE.rev) / PHASE.hold) * TL.hold;
      window.__frame(k === 0 ? Math.max(t, 0) : t);
    };
  }, PHASE, ALL);

  const clips = args.only ? [+args.only] : [1, 2, 3, 4, 5, 6, 7, 8];
  for (const c of clips) {
    const len = await page.evaluate(c => window.__clipLen(c), c), n = Math.round(len * FPS);
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'mbappe-clip-'));
    for (let i = 0; i < n; i++) {
      await page.evaluate((c, t) => window.__clip(c, t), c, i / FPS);
      await page.screenshot({ path: path.join(dir, `f${String(i).padStart(4, '0')}.png`) });
    }
    const out = path.join(OUT, `video_${c}.mp4`);
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', String(FPS), '-i', path.join(dir, 'f%04d.png'),
      '-vf', 'scale=1080:1350:flags=lanczos', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'slow',
      '-movflags', '+faststart', out]);
    fs.rmSync(dir, { recursive: true, force: true });
    console.log(`collage/video_${c}.mp4 : ${len.toFixed(1)} s`);
  }
  await browser.close();
})();
