#!/usr/bin/env bash
# Publie la page interactive d'un joueur sur https://data-workers.com/projet/<slug>/ (dépôt du site, GitHub Actions).
#   ./deploy.sh <joueur>   pages du joueur (FR / EN, sombre / clair) + vignette, poussées dans le dépôt du site
#   (outils/github/site_depot.sh) : GitHub Actions les met en ligne. La grille /projet/liste/ : outils/github/mettre_en_ligne.sh.
set -euo pipefail
cd "$(dirname "$0")"
ID=${1:?usage : ./deploy.sh <joueur> [--index]}
SLUG=$(python3 -c "import json,sys; c=json.load(open('joueurs/$ID/joueur.json')); print(c.get('slug', '$ID' + '_tirs'))")
OUT=sortie/$ID

python3 src/build_fresque.py "$ID"
[[ -f "$OUT/site/$SLUG.jpg" ]] || { echo "vignette $OUT/site/$SLUG.jpg manquante : lancer node src/render_collage.js $ID"; exit 1; }
OUTIL="${OUTIL_SITE:-$HOME/Documents/dataScience/outils/github/site_depot.sh}"
# par le dépôt du site : GitHub Actions déploie à chaque push (pages FR / EN, sombre / clair, vignette)
"$OUTIL" "content: $ID shot flow pages updated" \
  "$OUT/site/index.html" "projet/$SLUG/index.html" "$OUT/site/clair/index.html" "projet/$SLUG/clair/index.html" \
  "$OUT/site/en/index.html" "en/projet/$SLUG/index.html" "$OUT/site/en/clair/index.html" "en/projet/$SLUG/clair/index.html" \
  "$OUT/site/$SLUG.jpg" "projet/assets/$SLUG.jpg"
if [[ "${2:-}" == "--index" ]]; then
  echo "--index n'est plus utilisé : la grille /projet/liste/ est dans le dépôt du site et régénérée par"
  echo "outils/github/mettre_en_ligne.sh (y ajouter la carte du joueur à la main, dans projet/liste/ du dépôt)."
fi
echo "en ligne dans quelques minutes : https://data-workers.com/projet/$SLUG/ (+ /clair/) et /en/projet/$SLUG/ (+ /clair/)"
