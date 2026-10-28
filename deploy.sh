#!/usr/bin/env bash
# Publie la page interactive sur https://data-workers.com/projet/mbappe_tirs/ (serveur o2switch, par SSH).
#   ./visuel_mbappe/deploy.sh           page du projet (sombre + /clair/) + vignette
#   ./visuel_mbappe/deploy.sh --index   aussi la page /projet/ (site/projet_index.html, avec la carte du projet)
# Avant d'écraser /projet/index.html, la version en ligne est sauvegardée à côté (index.html.bak-<date>).
set -euo pipefail
cd "$(dirname "$0")"
HOST=mjzg4129@109.234.164.61
DEST=data-workers.com/projet

python3 build_fresque.py
ssh -p 22 "$HOST" "mkdir -p $DEST/mbappe_tirs/clair $DEST/assets"
scp -P 22 site/index.html "$HOST:$DEST/mbappe_tirs/index.html"
scp -P 22 site/clair/index.html "$HOST:$DEST/mbappe_tirs/clair/index.html"
scp -P 22 site/mbappe_tirs.jpg "$HOST:$DEST/assets/mbappe_tirs.jpg"
if [[ "${1:-}" == "--index" ]]; then
  ssh -p 22 "$HOST" "cp -p $DEST/index.html $DEST/index.html.bak-\$(date +%Y%m%d-%H%M%S)"
  scp -P 22 site/projet_index.html "$HOST:$DEST/index.html"
fi
echo "en ligne : https://data-workers.com/projet/mbappe_tirs/ et https://data-workers.com/projet/mbappe_tirs/clair/"
