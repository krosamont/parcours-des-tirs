// Carrousel Instagram (1080×1350) et TikTok (1080×1920) : la fresque complète, puis une image par phase.
//   node visuel_mbappe/render_collage.js   -> visuel_mbappe/collage/instagram_1..8.png, tiktok_1..8.png
// Les images viennent du mode vidéo de fresque_interactive.html (?video=1) : chaque phase à la fin de son ouverture,
// la fresque entière à la fin de la vidéo. Rendu en ×2 puis réduit, sans la grille du fond.
const path = require('path'), fs = require('fs'), { execFileSync } = require('child_process');
const puppeteer = require(path.join(__dirname, '../tools/node_modules/puppeteer-core'));
const { launchOptions } = require(path.join(__dirname, '../tools/browser.js'));
const OUT = path.join(__dirname, 'collage');

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await puppeteer.launch(launchOptions());
  const page = await browser.newPage();
  await page.setViewport({ width: 1080, height: 1350, deviceScaleFactor: 2 });
  await page.goto('file://' + path.join(__dirname, 'fresque_interactive.html?video=1'), { waitUntil: 'networkidle0' });
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
    // Instagram 4:5, puis TikTok 9:16 (même image au centre, bandes beiges en haut et en bas)
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', hd, '-vf', 'scale=1080:1350:flags=lanczos', path.join(OUT, `instagram_${i + 1}.png`)]);
    execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-i', hd, '-vf', 'scale=1080:1350:flags=lanczos,pad=1080:1920:0:285:color=0xebe7de', path.join(OUT, `tiktok_${i + 1}.png`)]);
    fs.unlinkSync(hd);
  }
  console.log(`${times.length} visuels : 1 = fresque complète, 2 à ${times.length} = phase par phase`);
  await browser.close();
})();
