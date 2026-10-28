// Carrousel Instagram (1080×1440, format 3:4 des publications) et TikTok (1080×1920) : la fresque complète, puis une image par phase.
//   node src/render_collage.js <joueur>   -> sortie/<joueur>/collage/instagram_1..8.png, tiktok_1..8.png
//   écrit aussi sortie/<joueur>/fresque.png (fresque entière, 2960×1660) et site/<slug>.jpg (vignette 1280×720 du site)
// Les images viennent du mode vidéo de sortie/<joueur>/interactive.html (?video=1) : chaque phase à la fin de son ouverture,
// la fresque entière à la fin de la vidéo. Rendu en ×2 puis réduit, sans la grille du fond.
const path = require('path'), fs = require('fs'), { execFileSync } = require('child_process');
const puppeteer = require('puppeteer-core');
const { launchOptions } = require('./browser');
const { out: DIR, slug } = require('./joueur')();
const OUT = path.join(DIR, 'collage');

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await puppeteer.launch(launchOptions());
  const page = await browser.newPage();
  // fresque entière (image fixe) et vignette de la carte du site
  await page.setViewport({ width: 2960, height: 1660, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(DIR, 'fresque.html') + '?render=1', { waitUntil: 'networkidle0' });
  await page.evaluate(() => document.fonts.ready); await new Promise(r => setTimeout(r, 400));
  const png = path.join(DIR, 'fresque.png');
  await page.screenshot({ path: png, clip: { x: 0, y: 0, width: 2960, height: 1660 } });
  // vignette de la carte /projet/ : le Sankey de la page sombre, toutes les phases ouvertes
  await page.setViewport({ width: 1280, height: 720, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(DIR, 'site', 'index.html') + '?depth=7', { waitUntil: 'networkidle0' });
  await page.evaluate(() => document.fonts.ready); await new Promise(r => setTimeout(r, 1200));
  await page.evaluate(() => scrollTo(0, document.getElementById('wrap').getBoundingClientRect().top + scrollY - 10));
  await new Promise(r => setTimeout(r, 300));
  const thumb = path.join(DIR, 'site', `${slug}.png`);
  await page.screenshot({ path: thumb });
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', thumb, '-q:v', '3', thumb.replace(/\.png$/, '.jpg')]);
  fs.unlinkSync(thumb);

  await page.setViewport({ width: 1080, height: 1350, deviceScaleFactor: 2 });
  await page.goto('file://' + path.join(DIR, 'interactive.html') + '?video=1', { waitUntil: 'networkidle0' });
  await page.waitForFunction(() => window.__ready);
  await page.addStyleTag({ content: ':root { --grid: transparent !important; }' });
  const { times } = await page.evaluate(() => {
    const TLs = { intro: .5, rev: 1.5, hold: 1.0 }, n = 7;
    const ph = k => TLs.intro + k * (TLs.rev + TLs.hold) + TLs.rev + TLs.hold * .9;
    return { times: [window.__duration - .02, ...Array.from({ length: n }, (_, k) => ph(k))] };
  });
  for (let i = 0; i < times.length; i++) {
    await page.evaluate(t => window.__frame(t), times[i]);
    await new Promise(r => setTimeout(r, 120));
    const hd = path.join(OUT, `_hd_${i + 1}.png`);
    await page.screenshot({ path: hd });
    // Instagram 3:4 (1080×1440, sinon Instagram recadre), puis TikTok 9:16 (même image au centre, bandes beiges en haut et en bas)
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', hd, '-vf', 'scale=1080:1350:flags=lanczos,pad=1080:1440:0:45:color=0xebe7de', path.join(OUT, `instagram_${i + 1}.png`)]);
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', hd, '-vf', 'scale=1080:1350:flags=lanczos,pad=1080:1920:0:285:color=0xebe7de', path.join(OUT, `tiktok_${i + 1}.png`)]);
    fs.unlinkSync(hd);
  }
  console.log(`${times.length} visuels : 1 = fresque complète, 2 à ${times.length} = phase par phase`);
  await browser.close();
})();
