#!/usr/bin/env bash
# Le parcours des tirs d'un joueur, de l'export MotherDuck aux visuels.
#   ./faire_joueur.sh <joueur>             pages (fresque, interactive, site) + fresque.png
#   ./faire_joueur.sh <joueur> --reseaux   en plus : vignette du site, carrousels d'images et de clips, vidéo verticale, vidéo
#   ./faire_joueur.sh <joueur> --gif       en plus : le GIF de la vidéo (implique --reseaux)
# Prérequis : joueurs/<joueur>/joueur.json et joueurs/<joueur>/export.csv (voir README, « Ajouter un joueur »).
# Pour publier ensuite : ./deploy.sh <joueur> [--index] (demande la vignette : lancer une fois avec --reseaux)
set -euo pipefail
cd "$(dirname "$0")"
ID=${1:?usage : ./faire_joueur.sh <joueur> [--reseaux|--gif]}
OPT=${2:-}

python3 src/build_fresque.py "$ID"
if [[ "$OPT" != "--reseaux" && "$OPT" != "--gif" ]]; then
  node src/render_collage.js "$ID" --fresque     # fresque.png seulement
else
  node src/render_collage.js "$ID"               # fresque.png, vignette du site, carrousel d'images Instagram / TikTok
  node src/render_collage_video.js "$ID"         # carrousel de petites vidéos (un clip par phase)
  node src/render_collage_video.js "$ID" --vertical   # vidéo verticale 1080×1920, bas libre pour se filmer
  if [[ "$OPT" == "--gif" ]]; then node src/render_video.js "$ID" --gif; else node src/render_video.js "$ID"; fi
fi
echo "terminé : sortie/$ID/"
