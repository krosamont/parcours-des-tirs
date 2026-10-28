# Le parcours des tirs d'un joueur (Sankey « Shot Flow »)

Sankey « Shot Flow » des tirs d'un joueur, inspiré des visuels basket de graphsketball (`docs/inspiration/`). Premier joueur : Kylian Mbappé au Real Madrid (`joueurs/mbappe/`).

Parcours d'un tir : **zone → situation → surface → résultat**, puis pour les buts seulement
**passeur → comment il a marqué → phase du but**. Bleu = but, rouge = raté (turquoise / corail sur le site).

## Installation

```bash
pip install -r requirements.txt                 # pandas
npm install                                      # puppeteer-core (rendus d'images et de vidéos)
npx @puppeteer/browsers install chrome@stable    # si aucun Chrome n'est installé (ou CHROME=/chemin/vers/chrome)
```

ffmpeg doit être dans le PATH (`brew install ffmpeg`).

## Organisation

```
faire_joueur.sh          tout produire pour un joueur (pages, images, clips, vidéo)
deploy.sh                publier un joueur sur data-workers.com
joueurs/<joueur>/        une fiche par joueur : joueur.json, photo.png, export.csv, requete.sql
sql/                     gabarit de la requête MotherDuck
src/                     build_fresque.py (données -> pages) et les scripts de rendu (render_*.js)
templates/               gabarits HTML : fresque.html (statique) et interactive.html (clic, mode vidéo)
themes/                  thèmes du site : site_sombre.css, site_clair.css
site/                    copie locale de la page /projet/ du site, où s'ajoutent les cartes
docs/inspiration/        les visuels basket de graphsketball qui ont servi de modèle
sortie/<joueur>/         tout ce qui est généré (non versionné)
```

## Ajouter un joueur

```bash
# 1. sa fiche et sa photo (PNG carré, par exemple celle de FotMob)
mkdir joueurs/haaland
cat > joueurs/haaland/joueur.json <<'EOF'
{ "nom": "Erling Haaland", "equipe": "Manchester City" }
EOF
cp ~/Downloads/haaland.png joueurs/haaland/photo.png

# 2. ses tirs : la requête prête à lancer sur MotherDuck, puis exporter le résultat en CSV
python3 src/build_fresque.py haaland --sql      # -> joueurs/haaland/requete.sql
#    résultat MotherDuck -> joueurs/haaland/export.csv

# 3. tout produire : pages, fresque, vignette, carrousels d'images et de vidéos, vidéo complète + GIF (~6 min)
./faire_joueur.sh haaland                   # --rapide : sans les vidéos

# 4. publier sur data-workers.com (/projet/<slug>/ et /clair/), avec sa carte sur /projet/
python3 src/build_fresque.py haaland --carte    # ajoute la carte dans site/projet_index.html
./deploy.sh haaland --index
```

### `joueur.json`

| Champ | Obligatoire | Rôle |
|---|---|---|
| `nom` | oui | nom affiché (titre, partage, carte du site) |
| `equipe` | oui | `teamName` dans `foot.bronze.events` (filtre de la requête, sous-titre) |
| `photo` | non | photo du joueur dans son dossier ; par défaut `photo.png` |
| `nom_events` | non | nom dans `foot.bronze.events` s'il diffère de `nom` |
| `nom_court` | non | pour la carte et le partage (« Mbappé, le parcours de ses tirs ») ; par défaut le dernier mot de `nom` |
| `slug` | non | adresse sur le site, `/projet/<slug>/` ; par défaut `<joueur>_tirs` |
| `noms_courts` | non | noms des passeurs à raccourcir (`"Vinícius Júnior": "Vinícius"`) ; par défaut leur dernier mot |

Le reste se déduit de l'export : saisons, compétitions (libellés dans `COMPETITIONS` de `src/build_fresque.py`, à
compléter pour une nouvelle compétition), adversaires, nombre de tirs et de buts.

## Chaîne complète

```
MotherDuck (foot.bronze.events + match_status)
   │  sql/requete_motherduck.sql (gabarit {{joueur}} / {{equipe}})  ->  joueurs/<joueur>/requete.sql
   ▼
joueurs/<joueur>/export.csv + joueur.json + photo.png
   │  python3 src/build_fresque.py <joueur>
   ▼
sortie/<joueur>/fresque.html           fresque complète (statique)
sortie/<joueur>/interactive.html       déroulé phase par phase au clic, mode vidéo ?video=1
sortie/<joueur>/site/index.html        version du site (sombre), et site/clair/index.html
   │  node src/render_collage.js <joueur>
   ▼
sortie/<joueur>/fresque.png            fresque entière 2960×1660
sortie/<joueur>/site/<slug>.jpg        vignette 1280×720 de la carte /projet/
sortie/<joueur>/collage/instagram_1..8.png (1080×1440) et tiktok_1..8.png (1080×1920)
   │  node src/render_collage_video.js <joueur>
   ▼
sortie/<joueur>/collage/video_1..8.mp4 carrousel de petites vidéos Instagram (1080×1350)
   │  node src/render_video.js <joueur>
   ▼
sortie/<joueur>/video.mp4 / video.gif  vidéo complète 1080×1350 (22 s) et GIF 600 px
```

`sortie/` n'est pas versionné : tout se régénère avec `faire_joueur.sh <joueur>`.

## 1. Données : `sql/requete_motherduck.sql`

Gabarit de la requête MotherDuck ; `build_fresque.py <joueur> --sql` le remplit dans `joueurs/<joueur>/requete.sql`.

- **source** : `foot.bronze.events`, filtré sur `teamName = {{equipe}}`, `name = {{joueur}}`, `isShot = TRUE` ;
- **contexte du match** : jointure sur `foot.bronze.match_status` pour l'équipe à domicile, l'équipe à l'extérieur,
  la date (`fm_utcTime`) et `fm_started` ;
- **nom du passeur** : `relatedPlayerId` du tir joint à un référentiel `player_lookup` (les joueurs de l'équipe vus
  dans les événements), qui donne `shot_related_player_name`.

Points d'attention :

- `player_lookup` fait un `DISTINCT playerId, name`. Si un joueur apparaît sous deux orthographes, ses tirs seraient
  dupliqués. Ce n'est pas le cas dans l'export de Mbappé : aucun doublon sur `match_id + eventId`.
- Le passeur n'est cherché que parmi les joueurs de l'équipe, ce qui suffit pour les passes de ses coéquipiers.
- Un joueur qui a changé de club : la requête ne prend qu'une équipe. L'adversaire est déduit match par match de
  `teamName`, donc deux exports concaténés (un par club) fonctionnent, avec `equipe` = le libellé du sous-titre.
- `relatedPlayerId` est renseigné pour les buts **et** les tirs ratés (385 tirs sur 478 pour Mbappé) : c'est le
  joueur associé à la dernière passe. Les visuels ne l'utilisent que pour les buts (colonne Passeur).

## 2. Préparation : `src/build_fresque.py <joueur>`

Lit `joueurs/<joueur>/export.csv`, prépare les champs utiles et écrit les pages autonomes (données et photo
intégrées, elles s'ouvrent sans serveur).

| Champ du visuel | Colonne(s) du CSV | Traitement |
|---|---|---|
| Zone | `x`, `y`, `situation` | **recalculée** : la colonne `Zone` du CSV vaut presque toujours `Center`. Les zones viennent de la géométrie WhoScored (x × 1,05, y × 0,68) : surface de but, surface axe / gauche / droite, point de penalty (`situation = Penalty`), hors surface. Y haut = côté gauche de l'attaquant. |
| Situation, Phase du but | `situation` | traduite (RegularPlay → Jeu placé, FastBreak → Contre-attaque, FromCorner → Corner, FreeKick → Coup franc direct, SetPiece et ThrowInSetPiece → Autre CPA*, IndividualPlay → Action individuelle) |
| Surface, Comment il a marqué | `shot_type` | RightFoot / LeftFoot / Header → Pied droit / Pied gauche / Tête |
| Résultat | `type` | `Goal` → But ; SavedShot / MissedShots / ShotOnPost → Raté (détail : arrêtés, hors cadre, poteaux) |
| Passeur | `shot_related_player_name` | buts seulement ; les 7 passeurs les plus fréquents, le reste dans « Autres », « Sans passeur » si vide (dont les penalties) |
| « en une touche » | `FirstTouch` | compté dans la colonne Comment il a marqué |
| xG | `xg` | xG cumulé affiché sous « But » |
| Saisons, compétitions | `season`, `competition` | boutons de filtre et sous-titre, déduits de l'export |

« CPA* » = coup de pied arrêté (coup franc indirect, touche…) : la note est en bas des pages et des visuels.

Gabarits : `templates/fresque.html` (fresque statique) et `templates/interactive.html` (page interactive et mode
vidéo). Ils ne contiennent rien de propre à un joueur : `__NOM__`, `__NOM_COURT__`, `__PHOTO__`, les tirs et `META`
(nom, équipe, saisons, compétitions) sont injectés par le script.

## 3. Les pages

**`fresque.html`** : les 7 colonnes d'un coup, avec la carte des tirs et des filtres par saison et par compétition.
Avec `?render=1`, les boutons sont masqués pour l'export d'image.

**`interactive.html`** :

- **Toute la phase** (par défaut) : un clic sur un bloc de la dernière colonne ouvre toute la phase suivante (tous
  les flux). Un clic sur une colonne précédente referme ce qui suit. Le bloc cliqué passe en jaune et ses flux sont
  mis en avant.
- **Ma sélection** : seul le bloc cliqué se déroule, en entonnoir. Recliquer dessus le referme.
- Le panneau donne le chemin, les tirs, buts, ratés, la réussite et l'xG de la sélection. Au survol, chaque point de
  la carte affiche son tir (adversaire, date, saison, xG, surface, zone, phase, passeur). La carte des tirs suit la
  sélection et ses zones sont cliquables. Il y a aussi « ← Retour », « Recommencer » et la touche Échap.
- Adaptée au mobile : textes agrandis, Sankey qui défile vers la phase ouverte, pas d'infobulle au toucher.
- Adresses directes : `?depth=4` (4 phases ouvertes), `?path=Hors surface|Jeu placé` (mode sélection),
  `?video=1&t=5` (image de la vidéo à 5 s).

## 4. Visuels pour les réseaux

```bash
node src/render_collage.js <joueur>                   # fresque.png, vignette, carrousel d'images
node src/render_collage_video.js <joueur> [--only 3]  # carrousel de petites vidéos (~4 min)
node src/render_video.js <joueur> [--to 5]            # vidéo complète + GIF
```


Tout vient du mode vidéo de `interactive.html` (`?video=1`), qui expose `window.__frame(t)` : chaque image est
dessinée pour un instant `t` précis, sans dépendre de l'horloge, donc l'animation reste fluide. Rendu en ×2 puis
réduit, sans la grille.

- **Carrousel d'images** : visuel 1 = la fresque complète, visuels 2 à 8 = une phase par image. Instagram en 3:4
  (1080×1440, sinon Instagram recadre) ; TikTok en 9:16, même image avec des bandes beiges.
- **Carrousel de vidéos** (dans l'esprit des posts « Shot Flow » de graphsketball), un clip par diapositive :
  clip 1 (7,7 s) = la fresque complète, puis un zoom à gauche et un panoramique jusqu'à la dernière colonne ;
  clips 2 à 8 (4,5 s) = une phase par clip : l'état précédent reste 0,8 s, la colonne s'ouvre en 2,5 s (caméra qui
  la suit), puis 1,2 s de pause. Durées réglables dans `PHASE` et `ALL`. Choisir le ratio 4:5 dans Instagram.
- **Vidéo complète** (22 s) : chaque phase s'ouvre en 1,5 s puis reste 1 s, la fin recule pour montrer toute la
  fresque. Durées dans `TL`, dans `templates/interactive.html`.

## 5. Publication sur data-workers.com : `deploy.sh <joueur>`

```bash
./deploy.sh mbappe            # régénère et publie les deux versions + la vignette
./deploy.sh mbappe --index    # publie aussi la page /projet/ (site/projet_index.html)
```

- **Version sombre** (`sortie/<joueur>/site/index.html` → `/projet/<slug>/`) : couleurs du site (`themes/site_sombre.css`).
- **Version claire** (`sortie/<joueur>/site/clair/index.html` → `/projet/<slug>/clair/`) : le thème local, même fond
  beige, sans la grille (`themes/site_clair.css`). Un bouton dans la barre de navigation passe de l'une à l'autre.
- **Carte sur /projet/** : `src/build_fresque.py <joueur> --carte` l'ajoute dans `site/projet_index.html` (copie locale
  de la page, partagée par tous les projets), après la dernière carte « parcours de ses tirs ». Relire le texte avant
  `--index`. Le serveur garde une sauvegarde `index.html.bak-<date>` à chaque publication.
