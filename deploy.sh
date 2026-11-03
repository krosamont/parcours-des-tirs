#!/usr/bin/env bash
# Publie la page interactive d'un joueur sur https://data-workers.com/projet/<slug>/ (serveur o2switch, par SSH).
#   ./deploy.sh <joueur>           page du joueur (sombre + /clair/) + vignette
#   ./deploy.sh <joueur> --index   aussi la page /projet/ (site/projet_index.html, avec les cartes) et sa version claire
#                                  /projet/clair/ (site/projet_index_clair.html)
# Avant d'écraser /projet/index.html, la version en ligne est sauvegardée à côté (index.html.bak-<date>).
set -euo pipefail
cd "$(dirname "$0")"
ID=${1:?usage : ./deploy.sh <joueur> [--index]}
HOST=mjzg4129@109.234.164.61
DEST=data-workers.com/projet
SLUG=$(python3 -c "import json,sys; c=json.load(open('joueurs/$ID/joueur.json')); print(c.get('slug', '$ID' + '_tirs'))")
OUT=sortie/$ID

python3 src/build_fresque.py "$ID"
[[ -f "$OUT/site/$SLUG.jpg" ]] || { echo "vignette $OUT/site/$SLUG.jpg manquante : lancer node src/render_collage.js $ID"; exit 1; }
ssh -p 22 "$HOST" "mkdir -p $DEST/$SLUG/clair $DEST/assets"
scp -P 22 "$OUT/site/index.html" "$HOST:$DEST/$SLUG/index.html"
scp -P 22 "$OUT/site/clair/index.html" "$HOST:$DEST/$SLUG/clair/index.html"
# version anglaise : /en/projet/<slug>/ et /clair/
ssh -p 22 "$HOST" "mkdir -p data-workers.com/en/projet/$SLUG/clair"
scp -P 22 "$OUT/site/en/index.html" "$HOST:data-workers.com/en/projet/$SLUG/index.html"
scp -P 22 "$OUT/site/en/clair/index.html" "$HOST:data-workers.com/en/projet/$SLUG/clair/index.html"
scp -P 22 "$OUT/site/$SLUG.jpg" "$HOST:$DEST/assets/$SLUG.jpg"
if [[ "${2:-}" == "--index" ]]; then
  # La grille des projets est sous /projet/liste/ (/projet/ raconte l'histoire, outils/html/histoire_site.py).
  # Après cet envoi, relancer outils/github/mettre_en_ligne.sh pour remettre la section « projets précédents » et le sélecteur.
  ssh -p 22 "$HOST" "mkdir -p $DEST/liste/clair && cp -p $DEST/liste/index.html $DEST/liste/index.html.bak-\$(date +%Y%m%d-%H%M%S)"
  scp -P 22 site/projet_index.html "$HOST:$DEST/liste/index.html"
  scp -P 22 site/projet_index_clair.html "$HOST:$DEST/liste/clair/index.html"
fi
echo "en ligne : https://data-workers.com/projet/$SLUG/ (+ /clair/) et https://data-workers.com/en/projet/$SLUG/ (+ /clair/)"
