// Lecture commune des scripts de rendu : node <script>.js <joueur> [--option valeur ...]
// <joueur> = dossier joueurs/<joueur>/ ; les pages viennent de sortie/<joueur>/ (python3 build_fresque.py <joueur>).
const path = require('path'), fs = require('fs');
const ROOT = path.resolve(__dirname, '..');   // racine du projet

module.exports = function joueur(argv = process.argv.slice(2)) {
  const id = argv[0] && !argv[0].startsWith('--') ? argv[0] : null;
  if (!id) { console.error('usage : node <script>.js <joueur> [--options]   (ex. mbappe)'); process.exit(1); }
  const cfg = JSON.parse(fs.readFileSync(path.join(ROOT, 'joueurs', id, 'joueur.json'), 'utf8'));
  const out = path.join(ROOT, 'sortie', id);
  if (!fs.existsSync(path.join(out, 'interactive.html'))) {
    console.error(`sortie/${id}/interactive.html manquant : lancer d'abord python3 src/build_fresque.py ${id}`); process.exit(1);
  }
  const args = Object.fromEntries(argv.slice(1).join(' ').split('--').filter(Boolean).map(s => { const [k, ...v] = s.trim().split(' '); return [k, v.join(' ') || true]; }));
  return { id, cfg, out, args, ROOT, slug: cfg.slug || `${id}_tirs` };
};
