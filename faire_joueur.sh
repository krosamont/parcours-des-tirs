#!/usr/bin/env bash
# Tout le parcours des tirs d'un joueur, de l'export MotherDuck aux visuels pour les réseaux.
#   ./visuel_mbappe/faire_joueur.sh <joueur>            pages + fresque.png + vignette + carrousels + clips + vidéo/GIF
#   ./visuel_mbappe/faire_joueur.sh <joueur> --rapide   sans les vidéos (pages, images et carrousel d'images seulement)
# Prérequis : joueurs/<joueur>/joueur.json et joueurs/<joueur>/export.csv (voir README, « Ajouter un joueur »).
# Pour publier ensuite : ./visuel_mbappe/deploy.sh <joueur> [--index]
set -euo pipefail
cd "$(dirname "$0")"
ID=${1:?usage : ./faire_joueur.sh <joueur> [--rapide]}

python3 build_fresque.py "$ID"
node render_collage.js "$ID"                 # fresque.png, vignette du site, carrousel d'images Instagram / TikTok
if [[ "${2:-}" != "--rapide" ]]; then
  node render_collage_video.js "$ID"         # carrousel de petites vidéos (un clip par phase)
  node render_video.js "$ID"                 # vidéo complète + GIF
fi
echo "terminé : visuel_mbappe/sortie/$ID/"
