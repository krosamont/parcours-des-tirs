// Chrome sans fenêtre pour les rendus (images, clips, vidéo), sur un Mac ou un serveur Linux.
//   Chrome : $CHROME, sinon le Chrome for Testing le plus récent du cache puppeteer ($PUPPETEER_CACHE_DIR ou
//            ~/.cache/puppeteer, installé par `npx @puppeteer/browsers install chrome@stable`), sinon un Chrome système.
const fs = require('fs'), path = require('path'), os = require('os');

function chromePath() {
  if (process.env.CHROME) return process.env.CHROME;
  const cache = path.join(process.env.PUPPETEER_CACHE_DIR || path.join(os.homedir(), '.cache', 'puppeteer'), 'chrome');
  const inside = {
    darwin: ['chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing', 'chrome-mac-x64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'],
    linux: ['chrome-linux64/chrome'], win32: ['chrome-win64/chrome.exe'] }[process.platform] || [];
  if (fs.existsSync(cache)) {
    const dirs = fs.readdirSync(cache).sort((a, b) => b.localeCompare(a, undefined, { numeric: true }));   // plus récent d'abord
    for (const d of dirs) for (const rel of inside) { const p = path.join(cache, d, rel); if (fs.existsSync(p)) return p; }
  }
  const system = ['/usr/bin/google-chrome', '/usr/bin/google-chrome-stable', '/usr/bin/chromium', '/usr/bin/chromium-browser',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'];
  const found = system.find(p => fs.existsSync(p));
  if (found) return found;
  throw new Error('Chrome introuvable : npx @puppeteer/browsers install chrome@stable, ou CHROME=/chemin/vers/chrome');
}

function launchOptions(extraArgs = []) {
  const linux = process.platform === 'linux' ? ['--no-sandbox', '--disable-dev-shm-usage'] : [];
  return { executablePath: chromePath(), headless: true, args: [...linux, ...extraArgs], protocolTimeout: 600000 };
}

module.exports = { chromePath, launchOptions };
