# Visuel Mbappé : le parcours de ses tirs

Sankey « Shot Flow » des tirs de Kylian Mbappé au Real Madrid (Liga + Ligue des champions, 2024-25 → 2026-27), inspiré
des visuels basket de graphsketball (captures `IMG_4104` à `IMG_4107`).

Parcours d'un tir : **zone → situation → surface → résultat**, puis pour les buts seulement
**passeur → comment il a marqué → phase du but**. Bleu = but, rouge = raté.

## Chaîne complète

```
MotherDuck (foot.bronze.events + match_status)
   │  requete_motherduck.sql          -> export CSV
   ▼
export.csv                            (478 tirs, 92 buts, 97 matchs)
   │  python3 visuel_mbappe/build_fresque.py
   ▼
fresque_mbappe.html                   fresque complète (statique, export PNG possible)
fresque_interactive.html              même parcours, déroulé phase par phase au clic
   │  node visuel_mbappe/render_video.js
   ▼
parcours_tirs_mbappe.mp4 / .gif       vidéo 1080×1350 (22 s) et GIF 600 px pour les réseaux
```

## 1. Données : `requete_motherduck.sql`

La requête lancée sur MotherDuck pour extraire les tirs :

- **source** : `foot.bronze.events`, filtré sur `teamName = 'Real Madrid'`, `name = 'Kylian Mbappé'`, `isShot = TRUE` ;
- **contexte du match** : jointure sur `foot.bronze.match_status` pour l'équipe à domicile, l'équipe à l'extérieur,
  la date (`fm_utcTime`) et `fm_started` ;
- **nom du passeur** : `relatedPlayerId` du tir joint à un référentiel `player_lookup` (les joueurs du Real Madrid
  vus dans les événements), qui donne `shot_related_player_name`.

Le résultat est exporté tel quel dans `export.csv`.

Points d'attention :

- `player_lookup` fait un `DISTINCT playerId, name`. Si un joueur apparaît sous deux orthographes, ses tirs seraient
  dupliqués. Ce n'est pas le cas dans l'export actuel : aucun doublon sur `match_id + eventId`.
- Le passeur n'est cherché que parmi les joueurs du Real Madrid, ce qui suffit pour les passes de ses coéquipiers.
- `relatedPlayerId` est renseigné pour 385 tirs sur 478, buts **et** tirs ratés : c'est le joueur associé à la
  dernière passe. Les visuels ne l'utilisent que pour les buts (colonne Passeur), comme le « Assist » du visuel basket.

## 2. Préparation : `build_fresque.py`

Lit `export.csv`, prépare les champs utiles et écrit deux pages autonomes, avec les données et la photo
(`assets/players/701154.png`) intégrées. Elles s'ouvrent sans serveur.

| Champ du visuel | Colonne(s) du CSV | Traitement |
|---|---|---|
| Zone | `x`, `y`, `situation` | **recalculée** : la colonne `Zone` du CSV vaut `Center` pour 474 tirs sur 478. Les zones viennent de la géométrie WhoScored (x × 1,05, y × 0,68) : surface de but, surface axe / gauche / droite, point de penalty (`situation = Penalty`), hors surface. Y haut = côté gauche de l'attaquant. |
| Situation, Phase du but | `situation` | traduite (RegularPlay → Jeu placé, FastBreak → Contre-attaque, FromCorner → Corner, FreeKick → Coup franc direct, SetPiece et ThrowInSetPiece → Autre CPA, IndividualPlay → Action individuelle) |
| Surface, Comment il a marqué | `shot_type` | RightFoot / LeftFoot / Header → Pied droit / Pied gauche / Tête |
| Résultat | `type` | `Goal` → But ; SavedShot / MissedShots / ShotOnPost → Raté (détail : arrêtés, hors cadre, poteaux) |
| Passeur | `shot_related_player_name` | buts seulement ; les 7 passeurs les plus fréquents, le reste dans « Autres », « Sans passeur » si vide (dont les penalties) |
| « en une touche » | `FirstTouch` | compté dans la colonne Comment il a marqué |
| xG | `xg` | xG cumulé affiché sous « But » |

```bash
python3 visuel_mbappe/build_fresque.py
```

Gabarits : `fresque_template.html` (fresque statique) et `interactive_template.html` (page interactive et mode vidéo).

## 3. Les pages

**`fresque_mbappe.html`** : les 7 colonnes d'un coup, avec la carte des tirs et des filtres par saison et par
compétition. Avec `?render=1`, les boutons sont masqués pour l'export d'image.

**`fresque_interactive.html`** :

- **Toute la phase** (par défaut) : un clic sur un bloc de la dernière colonne ouvre toute la phase suivante (tous
  les flux). Un clic sur une colonne précédente referme ce qui suit. Le bloc cliqué passe en jaune et ses flux sont
  mis en avant.
- **Ma sélection** : seul le bloc cliqué se déroule, en entonnoir. Recliquer dessus le referme.
- Le panneau donne le chemin, les tirs, buts, ratés, la réussite et l’xG de la sélection. Au survol, chaque point de la carte affiche son tir (adversaire, date, saison, xG, surface, zone, phase, passeur). La carte des tirs suit la
  sélection et ses zones sont cliquables. Il y a aussi « ← Retour », « Recommencer » et la touche Échap.
- Adaptée au mobile : textes agrandis, Sankey qui défile vers la phase ouverte, pas d'infobulle au toucher.
- Adresses directes : `?depth=4` (4 phases ouvertes), `?path=Hors surface|Jeu placé` (mode sélection),
  `?video=1&t=5` (image de la vidéo à 5 s).

## 4. Vidéo / GIF : `render_video.js`

```bash
npm install --prefix tools            # une fois (puppeteer-core)
node visuel_mbappe/render_video.js    # -> parcours_tirs_mbappe.mp4 + parcours_tirs_mbappe.gif
node visuel_mbappe/render_video.js --to 5 --out visuel_mbappe/apercu_5s.mp4   # aperçu des 5 premières secondes
```

La page `?video=1` expose `window.__frame(t)`, qui dessine l'image de l'instant `t`. Le script capture 30 images par
seconde sans dépendre de l'horloge réelle, donc l'animation reste fluide. ffmpeg en fait ensuite un MP4 H.264
(1080×1350, 4:5) et un GIF en boucle (15 i/s, 600 px de large).

Déroulé (22 s) : chaque phase s'ouvre en 1,5 s puis reste 1 s à l'écran, avec une caméra qui suit la colonne
ouverte. La fin recule pour montrer toute la fresque. Les durées se règlent dans `TL`, dans `interactive_template.html`.

## 5. Publication sur data-workers.com : `deploy.sh`

```bash
./visuel_mbappe/deploy.sh            # régénère et publie les deux versions + la vignette
./visuel_mbappe/deploy.sh --index    # publie aussi la page /projet/ (site/projet_index.html)
```

- **Version sombre** (`site/index.html` → `/projet/mbappe_tirs/`) : couleurs du site (`site_theme.css`), sans la grille.
- **Version claire** (`site/clair/index.html` → `/projet/mbappe_tirs/clair/`) : le thème local, même fond beige, sans
  la grille (`site_theme_clair.css`).
- Un bouton « Version claire » / « Version sombre » dans la barre de navigation passe de l'une à l'autre.

## 6. Carrousel Instagram / TikTok : `render_collage.js`

```bash
node visuel_mbappe/render_collage.js   # -> collage/instagram_1..8.png (1080×1350) et collage/tiktok_1..8.png (1080×1920)
```

Visuel 1 : la fresque complète. Visuels 2 à 8 : une phase par image (zone, situation, surface, résultat, passeur,
comment il a marqué, phase du but). Les images viennent du mode vidéo (`?video=1`), rendues en ×2 puis réduites,
sans la grille. La version TikTok reprend la même image avec des bandes beiges en haut et en bas.

« CPA* » = coup de pied arrêté (coup franc indirect, touche…) : la note est en bas des pages et des visuels.
