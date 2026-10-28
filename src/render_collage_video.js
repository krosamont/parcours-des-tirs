// Carrousel Instagram de petites vidéos (1080×1350, 30 i/s), comme les posts « Shot Flow » de graphsketball :
//   clip 1 : la fresque complète, puis un zoom et un panoramique de gauche à droite ;
//   clips 2 à 8 : une phase par clip, la colonne suivante se déroule et la caméra la suit.
// usage : node src/render_collage_video.js <joueur> [--only 3]   -> sortie/<joueur>/collage/video_1..8.mp4
//         node src/render_collage_video.js <joueur> --vertical   -> sortie/<joueur>/video_vertical.mp4 (1080×1920) :
//         les mêmes clips à la suite dans le haut de l'image (1120 px), le bas reste vide pour se filmer en train de parler
// Les images viennent du mode vidéo de sortie/<joueur>/interactive.html (?video=1, window.__frame(t)), rendues en ×2 puis réduites.
const path = require('path'), fs = require('fs'), os = require('os'), { execFileSync } = require('child_process');
const ROOT = path.resolve(__dirname, '..');
const puppeteer = require('puppeteer-core');
const { launchOptions } = require('./browser');
const { out: DIR, args } = require('./joueur')();
const FPS = 30, OUT = path.join(DIR, 'collage');

// clip d'une phase : 0,8 s d'arrêt sur l'état précédent, 2,5 s d'ouverture, 1,2 s de pause
const PHASE = { still: .8, rev: 2.5, hold: 1.2 };
// clip 1 : fresque entière, zoom vers la gauche, panoramique, pause
const ALL = { whole: 1.4, zoom: 1.3, pan: 4.2, hold: .8 };

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await puppeteer.launch(launchOptions(['--hide-scrollbars', '--font-render-hinting=none']));
  const page = await browser.newPage();
  page.on('pageerror', e => console.error('PAGE ERROR', e.message));
  const VERT = !!args.vertical, VH = VERT ? 1120 : 1350;
  await page.setViewport({ width: 1080, height: VH, deviceScaleFactor: 2 });
  await page.goto('file://' + path.join(DIR, 'interactive.html') + (VERT ? '?video=1&split=1' : '?video=1'), { waitUntil: 'networkidle0' });
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
  if (VERT) {
    // une seule vidéo : tous les clips à la suite, puis le bas complété par une zone vide couleur papier
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'shotflow-vertical-'));
    let f = 0, total = 0;
    for (const c of clips) {
      const len = await page.evaluate(c => window.__clipLen(c), c), n = Math.round(len * FPS);
      // après la fresque complète, la phase 1 démarre tout de suite (sinon 0,8 s de Sankey vide)
      const i0 = c === 2 && clips[0] === 1 ? Math.round(PHASE.still * FPS) : 0;
      for (let i = i0; i < n; i++, f++) {
        await page.evaluate((c, t) => window.__clip(c, t), c, i / FPS);
        await page.screenshot({ path: path.join(dir, `f${String(f).padStart(5, '0')}.png`) });
      }
      total += len - i0 / FPS;
      process.stdout.write(`\rclip ${c}/${clips.length}`);
    }
    const out = path.join(DIR, 'video_vertical.mp4');
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', String(FPS), '-i', path.join(dir, 'f%05d.png'),
      '-vf', 'scale=1080:1120:flags=lanczos,pad=1080:1920:0:0:color=0xebe7de', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
      '-crf', '18', '-preset', 'slow', '-movflags', '+faststart', out]);
    fs.rmSync(dir, { recursive: true, force: true });
    console.log(`\n${path.relative(ROOT, out)} : ${total.toFixed(1)} s, 1080×1920 (Sankey en haut, 800 px libres en bas)`);
    return browser.close();
  }
  for (const c of clips) {
    const len = await page.evaluate(c => window.__clipLen(c), c), n = Math.round(len * FPS);
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'shotflow-clip-'));
    for (let i = 0; i < n; i++) {
      await page.evaluate((c, t) => window.__clip(c, t), c, i / FPS);
      await page.screenshot({ path: path.join(dir, `f${String(i).padStart(4, '0')}.png`) });
    }
    const out = path.join(OUT, `video_${c}.mp4`);
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', String(FPS), '-i', path.join(dir, 'f%04d.png'),
      '-vf', 'scale=1080:1350:flags=lanczos', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'slow',
      '-movflags', '+faststart', out]);
    fs.rmSync(dir, { recursive: true, force: true });
    console.log(`${path.relative(ROOT, out)} : ${len.toFixed(1)} s`);
  }
  await browser.close();
})();
