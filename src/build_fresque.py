"""Fresque « Shot Flow » des tirs d'un joueur (inspirée des Shot Flow basket de graphsketball).

usage: python3 src/build_fresque.py <joueur> [--carte] [--sql]
  <joueur>  dossier joueurs/<joueur>/ : joueur.json (nom, équipe, slug du site) + photo.png + export.csv (requête MotherDuck)
  --sql     écrit seulement joueurs/<joueur>/requete.sql (sql/requete_motherduck.sql remplie pour ce joueur) et s'arrête
  --carte   ajoute aussi la carte du joueur dans site/projet_index.html (page /projet/ de data-workers.com)

écrit dans sortie/<joueur>/ :
  fresque.html             fresque complète (page autonome : données + photo embarquées)
  interactive.html         même parcours, déroulé phase par phase au clic (et mode vidéo ?video=1)
  site/index.html          page interactive aux couleurs de data-workers.com, publiée dans /projet/<slug>/
  site/clair/index.html    version claire, publiée dans /projet/<slug>/clair/
  site/en/index.html       version anglaise (sombre), publiée dans /en/projet/<slug>/ ; site/en/clair/ : claire

Parcours d'un tir : ZONE -> SITUATION -> SURFACE -> RÉSULTAT -> (buts seulement) PASSEUR -> COMMENT IL A MARQUÉ -> PHASE
"""
import argparse, base64, html, json, re
from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'outils' / 'html'))
try:  # aperçu des liens partagés (le logo Data Workers) : outil du site, absent d'un clone du dépôt seul
    from partage import avec_logo  # noqa: E402
except ImportError:
    def avec_logo(page):
        return page

ROOT = Path(__file__).resolve().parent.parent      # racine du projet

# x en [0,105] vers le but adverse, y en [0,68] avec y haut = côté gauche de l'attaquant (coordonnées WhoScored x1.05 / x0.68)
BOX_X, SIX_X = 83 * 1.05, 94.2 * 1.05             # 87.15 m, 98.9 m
BOX_Y, SIX_Y = (21.1 * .68, 78.9 * .68), (36.8 * .68, 63.2 * .68)

SITUATION = {'RegularPlay': 'Jeu placé', 'FastBreak': 'Contre-attaque', 'Penalty': 'Penalty', 'FromCorner': 'Corner',
             'FreeKick': 'Coup franc direct', 'SetPiece': 'Autre CPA*', 'ThrowInSetPiece': 'Autre CPA*', 'IndividualPlay': 'Action individuelle',
             'Unknown': 'Non renseignée'}
BODY = {'RightFoot': 'Pied droit', 'LeftFoot': 'Pied gauche', 'Header': 'Tête', 'OtherBodyPart': 'Autre', 'OtherBodyParts': 'Autre',
        'Foot': 'Pied (non précisé)'}
TYPE = {'Goal': 'But', 'SavedShot': 'Arrêté', 'MissedShots': 'Hors cadre', 'ShotOnPost': 'Poteau'}
# libellés des compétitions (colonne competition de foot.bronze.events), dans l'ordre d'affichage
COMPETITIONS = {'laliga': 'Liga', 'premier-league': 'Premier League', 'serie-a': 'Serie A', 'bundesliga': 'Bundesliga',
                'ligue-1': 'Ligue 1', 'champions-league': 'Ligue des champions', 'europa-league': 'Ligue Europa',
                'conference-league': 'Ligue Europa Conférence'}


def zone(r):
    # le champ Zone du CSV vaut presque toujours 'Center' : on redécoupe à partir de x/y
    if r.situation == 'Penalty':
        return 'Point de penalty'
    if r.x >= SIX_X and SIX_Y[0] <= r.y <= SIX_Y[1]:
        return 'Surface de but'
    if r.x >= BOX_X and BOX_Y[0] <= r.y <= BOX_Y[1]:
        if SIX_Y[0] <= r.y <= SIX_Y[1]:
            return 'Surface · axe'
        return 'Surface · gauche' if r.y > SIX_Y[1] else 'Surface · droite'
    return 'Hors surface'


def load(pid):
    folder = ROOT / 'joueurs' / pid
    if not (folder / 'joueur.json').exists():
        raise SystemExit(f'joueurs/{pid}/joueur.json introuvable (voir joueurs/mbappe/ pour un exemple)')
    cfg = json.loads((folder / 'joueur.json').read_text())
    cfg.setdefault('nom_court', cfg['nom'].split()[-1])
    cfg.setdefault('nom_events', cfg['nom'])
    cfg.setdefault('slug', re.sub(r'[^a-z0-9]+', '_', pid.lower()) + '_tirs')
    cfg.setdefault('noms_courts', {})
    cfg['id'], cfg['dir'], cfg['out'] = pid, folder, ROOT / 'sortie' / pid
    return cfg


def write_sql(cfg):
    q = (ROOT / 'sql' / 'requete_motherduck.sql').read_text()
    q = q.replace('{{joueur}}', cfg['nom_events'].replace("'", "''")).replace('{{equipe}}', cfg['equipe'].replace("'", "''"))
    (cfg['dir'] / 'requete.sql').write_text(q)
    print(f"joueurs/{cfg['id']}/requete.sql : à lancer sur MotherDuck, puis exporter le résultat dans joueurs/{cfg['id']}/export.csv")


def normalise(d):
    """Ramène un export au format de sql/requete_motherduck.sql. Deux formats sont reconnus :
    - celui de la requête (teamName, fm_utcTime, shot_related_player_name…) : rien à faire ;
    - l'export « tous les événements » (team_name, match_date, fixture, related_player_name, is_header, is_penalty…),
      comme joueurs/kane/export.csv : on garde les tirs et on renomme. Pour les matchs en ancienne convention, situation
      et shot_type sont vides : penalty et tête se déduisent de is_penalty / is_header, le reste devient « non renseigné »."""
    if 'teamName' in d.columns:
        return d
    d = d[d.type.isin(list(TYPE))].copy()
    d['situation'] = d.situation.where(d.situation.notna(), d.is_penalty.map({True: 'Penalty'})).fillna('Unknown')
    d['shot_type'] = d.shot_type.where(d.shot_type.notna(), d.is_header.map({True: 'Header'})).fillna('Foot')
    # passeur : le joueur de la passe qui précède le tir (pas un rebond sur un autre tir)
    d['shot_related_player_name'] = d.related_player_name.where(d.related_event_type == 'Pass')
    # penalties : le joueur qui a obtenu le penalty compte comme passeur (« Sans passeur » s'il l'a obtenu lui-même)
    if 'penalty_won_by_player_name' in d.columns:
        won = d.penalty_won_by_player_name.where(d.is_penalty == True)
        own = won == d.player_name
        won = won.where(~own)
        d['shot_related_player_name'] = won.where(won.notna(), d.shot_related_player_name).where(~own)
    teams = d.fixture.str.split(' - ', n=1, expand=True)
    d['ws_home_name'], d['ws_away_name'] = teams[0], teams[1]
    return d.rename(columns={'team_name': 'teamName', 'match_date': 'fm_utcTime'}).assign(FirstTouch=False)


def shots_of(cfg):
    d = normalise(pd.read_csv(cfg['dir'] / 'export.csv'))
    short = lambda n: cfg['noms_courts'].get(n, n.split()[-1]) if isinstance(n, str) else None
    shots = []
    for r in d.itertuples():
        goal = r.type == 'Goal'
        shots.append({
            'season': r.season, 'comp': r.competition,
            'zone': zone(r), 'sit': SITUATION.get(r.situation, r.situation), 'body': BODY.get(r.shot_type, r.shot_type),
            'goal': int(goal), 'type': TYPE.get(r.type, r.type),
            'ast': short(r.shot_related_player_name), 'ftouch': int(r.FirstTouch == True),
            'x': round(r.x, 1), 'y': round(r.y, 1), 'xg': None if pd.isna(r.xg) else round(r.xg, 3),
            'opp': r.ws_away_name if r.ws_home_name == r.teamName else r.ws_home_name,
            'date': r.fm_utcTime[:10], 'min': int(r.minute),
        })
    return shots


def meta_of(cfg, shots):
    seasons = sorted({s['season'] for s in shots})
    order = list(COMPETITIONS)
    comps = sorted({s['comp'] for s in shots}, key=lambda c: (order.index(c) if c in order else len(order), c))
    return {'nom': cfg['nom'], 'equipe': cfg['equipe'], 'etapes': cfg.get('etapes'), 'note': cfg.get('note', ''),
            'seasons': [[s, s[:5] + s[-2:] if re.fullmatch(r'\d{4}-\d{4}', s) else s] for s in seasons],
            'comps': [[c, COMPETITIONS.get(c, c.replace('-', ' ').title())] for c in comps]}


def site_replacements(cfg, shots, clair=False):
    """Version publiée sur data-workers.com/projet/<slug>/ : couleurs, police, navigation et partage du site."""
    nom, court, eq, n = html.escape(cfg['nom']), html.escape(cfg['nom_court']), html.escape(cfg['equipe']), len(shots)
    url = f"https://data-workers.com/projet/{cfg['slug']}/" + ('clair/' if clair else '')
    head = f"""<meta name="description" content="Les {n} tirs de {nom} ({eq}), de la zone de frappe jusqu'au passeur et à la phase du but : un Sankey interactif à dérouler phase par phase.">
<meta property="og:title" content="{nom}, le parcours de ses tirs">
<meta property="og:description" content="Zone, situation, surface, résultat, passeur : le Sankey interactif des tirs de {court} ({eq}).">
<meta property="og:image" content="https://data-workers.com/projet/assets/{cfg['slug']}.jpg">
<meta property="og:url" content="{url}">
<link rel="icon" href="/assets/images/logo.ico">"""
    switch = '<a class="switch theme-switch" href="../">Version sombre</a>' if clair else '<a class="switch theme-switch" href="clair/">Version claire</a>'
    accueil = '/clair/' if clair else '/'   # la version claire mène à l'accueil et aux projets clairs
    rep = {
        f'<title>Parcours des tirs {court}</title>': f'<title>{nom}, le parcours de ses tirs · Data Workers</title>',
        '<!--__HEAD__-->': head if clair else head + '\n<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">',
        '/*__THEME__*/': (ROOT / 'themes' / ('site_clair.css' if clair else 'site_sombre.css')).read_text(),
        '<!--__NAV__-->': f'<nav class="sitenav"><img src="/assets/images/{"logo_orange" if clair else "logo"}.png" alt=""><a href="{accueil}">Data Workers</a><span>/</span><a href="/projet/{"clair/" if clair else ""}">Projets</a>{switch}</nav>',
        '<!--__FOOT__-->': f'<footer class="sitefoot"><a href="{accueil}">data-workers.com</a> · Kevin Rosamont Prombo · Données WhoScored × FotMob</footer>',
    }
    if not clair:
        rep[f'<h1>{nom},<br>le parcours de ses tirs</h1>'] = f'<h1>{nom},<br><em>le parcours de ses tirs</em></h1>'
    return rep


def add_card(cfg, shots):
    """Ajoute la carte du joueur dans site/projet_index.html (copie locale de /projet/), juste après la dernière carte Sankey."""
    p = ROOT / 'site' / 'projet_index.html'
    page = p.read_text()
    href = f"/projet/{cfg['slug']}/"
    if f'href="{href}"' in page:
        print(f'site/projet_index.html : la carte {href} existe déjà')
        return
    g = sum(s['goal'] for s in shots)
    nom, court, eq = html.escape(cfg['nom']), html.escape(cfg['nom_court']), html.escape(cfg['equipe'])
    card = f"""    <a class="card" href="{href}">
      <div class="thumb" style="background-image:url('assets/{cfg['slug']}.jpg')" role="img" aria-label="Le Sankey des tirs de {nom} : zones, situations, surfaces, buts et ratés"></div>
      <div class="body">
        <span class="kind">Data visualisation · Football</span>
        <h2>{court}, le parcours de ses tirs</h2>
        <p>Les {len(shots)} tirs de {nom} ({eq}), dont {g} buts, suivis de bout en bout : d'où il frappe, dans quelle
          situation, de quel pied, si c'est but, puis qui lui a fait la passe et dans quelle phase de jeu. On ouvre le
          Sankey phase par phase, au clic.</p>
        <div class="tags"><span>Sankey interactif</span><span>WhoScored / Opta</span><span>FotMob</span><span>MotherDuck</span></div>
        <span class="go">Dérouler les tirs →</span>
      </div>
    </a>

"""
    # après la dernière carte « parcours de ses tirs » (slug en _tirs), sinon en tête de la grille
    ends = [m.end() for m in re.finditer(r'<a class="card" href="/projet/[^"]+_tirs/">.*?</a>\n\n', page, re.S)]
    at = ends[-1] if ends else page.index('<main class="grid">') + len('<main class="grid">\n')
    p.write_text(page[:at] + card + page[at:])
    print(f"site/projet_index.html : carte {href} ajoutée (à publier avec ./deploy.sh {cfg['id']} --index)")


# textes fixes du gabarit en anglais (la partie dynamique est traduite dans le gabarit, constante EN)
GABARIT_EN = {
    '<html lang="fr">': '<html lang="en">',
    'const EN = /*__EN__*/false;': 'const EN = true;',
    '<button id="back">← Retour</button>': '<button id="back">← Back</button>',
    '<button id="reset">Recommencer</button>': '<button id="reset">Start over</button>',
    'Voir la fresque complète</a>': 'See the full chart</a>',
    ('<p class="note">* CPA : coup de pied arrêté (coup franc indirect, touche, etc.). Les corners, les penalties et les coups francs directs '
     'sont comptés à part.<br>« Sans passeur » : buts sans passe décisive d\'un coéquipier (penalties, reprises, ballons récupérés, actions seul). '
     '« Autres » : les passeurs hors des 7 premiers, regroupés.</p>'):
    ('<p class="note">* Other set piece: indirect free kick, throw-in, etc. Corners, penalties and direct free kicks are counted '
     'separately.<br>"No assist": goals without an assist from a teammate (penalties, rebounds, won balls, solo efforts). '
     '"Others": assist providers outside the top 7, grouped together.</p>'),
    '<i style="background:var(--made)"></i>But</span>': '<i style="background:var(--made)"></i>Goal</span>',
    '<i style="background:var(--miss)"></i>Raté</span>': '<i style="background:var(--miss)"></i>Missed</span>',
    '<div class="src">* CPA : coup de pied arrêté · Données : WhoScored × FotMob</div>': '<div class="src">* set piece · Data: WhoScored × FotMob</div>',
}
SWITCH_LANGUE = {  # même bouton FR / EN que les autres pages de data-workers.com : sous le bouton clair / sombre
    False: "a.lang-switch { position: fixed; top: 56px; right: 14px; z-index: 1000; display: inline-flex; align-items: center; justify-content: center; min-width: 42px; padding: 8px 12px; font: 600 13px/1 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; letter-spacing: .04em; text-decoration: none; border: 1px solid rgba(255,255,255,.24); border-radius: 999px; background: rgba(7,11,21,.8); color: #e2e8f0; backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px); }\na.lang-switch:hover { border-color: #2dc4c2; color: #fff; }",
    True: "a.lang-switch { position: fixed; top: 56px; right: 14px; z-index: 1000; display: inline-flex; align-items: center; justify-content: center; min-width: 42px; padding: 8px 12px; font: 13px/1 'Arvo', Rockwell, Georgia, serif; text-decoration: none; border: 1.5px solid #1d1b19; border-radius: 2px; background: #ebe7de; color: #1d1b19; }\na.lang-switch:hover { background: #1d1b19; color: #ebe7de; }",
}


def bouton_langue(page, cfg, clair, en):
    sous = 'clair/' if clair else ''
    fr_url, en_url = f"/projet/{cfg['slug']}/{sous}", f"/en/projet/{cfg['slug']}/{sous}"
    cible, code, titre = (fr_url, 'fr', 'Version française') if en else (en_url, 'en', 'English version')
    tete = (f'<link rel="alternate" hreflang="fr" href="https://data-workers.com{fr_url}">\n'
            f'<link rel="alternate" hreflang="en" href="https://data-workers.com{en_url}">\n'
            f'<style id="lang-switch">\n{SWITCH_LANGUE[clair]}\n@media (max-width: 600px) {{ a.lang-switch {{ right: 10px; width: 38px; '
            f'height: 38px; min-width: 0; padding: 0; font-size: 12px; }} }}\n</style>\n')
    a = f'<a class="lang-switch" href="{cible}" hreflang="{code}" lang="{code}" title="{titre}">{code.upper()}</a>\n'
    page = page.replace('</head>', tete + '</head>', 1)
    return page.replace('<body>\n', '<body>\n' + a, 1)


def site_replacements_en(cfg, shots, clair=False):
    """Version anglaise publiée sur data-workers.com/en/projet/<slug>/."""
    nom, court, eq, n = html.escape(cfg['nom']), html.escape(cfg['nom_court']), html.escape(cfg['equipe']), len(shots)
    url = f"https://data-workers.com/en/projet/{cfg['slug']}/" + ('clair/' if clair else '')
    head = f"""<meta name="description" content="All {n} shots by {nom} ({eq}), from the shooting zone to the assist provider and the phase of the goal: an interactive Sankey to unfold phase by phase.">
<meta property="og:title" content="{nom}: shot flow">
<meta property="og:description" content="Zone, situation, body part, outcome, assist: the interactive Sankey of {court}'s shots ({eq}).">
<meta property="og:image" content="https://data-workers.com/projet/assets/{cfg['slug']}.jpg">
<meta property="og:url" content="{url}">
<link rel="icon" href="/assets/images/logo.ico">"""
    switch = '<a class="switch theme-switch" href="../">Dark version</a>' if clair else '<a class="switch theme-switch" href="clair/">Light version</a>'
    accueil = '/en/clair/' if clair else '/en/'
    rep = {
        f'<title>Parcours des tirs {court}</title>': f'<title>{nom}: shot flow · Data Workers</title>',
        '<!--__HEAD__-->': head if clair else head + '\n<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">',
        '/*__THEME__*/': (ROOT / 'themes' / ('site_clair.css' if clair else 'site_sombre.css')).read_text(),
        '<!--__NAV__-->': f'<nav class="sitenav"><img src="/assets/images/{"logo_orange" if clair else "logo"}.png" alt=""><a href="{accueil}">Data Workers</a><span>/</span><a href="/en/projet/{"clair/" if clair else ""}">Projects</a>{switch}</nav>',
        '<!--__FOOT__-->': f'<footer class="sitefoot"><a href="{accueil}">data-workers.com</a> · Kevin Rosamont Prombo · Data: WhoScored × FotMob</footer>',
        f'<h1>{nom},<br>le parcours de ses tirs</h1>': f'<h1>{nom},<br>{"his shot flow" if clair else "<em>his shot flow</em>"}</h1>',
        **GABARIT_EN,
    }
    return rep


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('joueur'); ap.add_argument('--carte', action='store_true'); ap.add_argument('--sql', action='store_true')
    a = ap.parse_args()
    cfg = load(a.joueur)
    if a.sql:
        return write_sql(cfg)
    if not (cfg['dir'] / 'export.csv').exists():
        write_sql(cfg)
        raise SystemExit(f"joueurs/{cfg['id']}/export.csv manquant")
    shots = shots_of(cfg)
    meta = meta_of(cfg, shots)
    photo = 'data:image/png;base64,' + base64.b64encode((cfg['dir'] / cfg.get('photo', 'photo.png')).read_bytes()).decode()
    g = sum(s['goal'] for s in shots)
    data = {'/*__SHOTS__*/[]': json.dumps(shots, ensure_ascii=False), '__PHOTO__': photo,
            "/*__META__*/{ nom: 'Joueur', equipe: 'Équipe', seasons: [], comps: [] }": json.dumps(meta, ensure_ascii=False)}
    for tpl, name, site in (('fresque.html', 'fresque.html', None),
                            ('interactive.html', 'interactive.html', None),
                            ('interactive.html', 'site/index.html', site_replacements(cfg, shots)),
                            ('interactive.html', 'site/clair/index.html', site_replacements(cfg, shots, clair=True)),
                            ('interactive.html', 'site/en/index.html', site_replacements_en(cfg, shots)),
                            ('interactive.html', 'site/en/clair/index.html', site_replacements_en(cfg, shots, clair=True))):
        page = (ROOT / 'templates' / tpl).read_text()
        page = page.replace('__NOM_COURT__', html.escape(cfg['nom_court'])).replace('__NOM__', html.escape(cfg['nom']))
        for key, value in {**(site or {}), **data}.items():
            page = page.replace(key, value)
        for key in ('<!--__HEAD__-->', '/*__THEME__*/', '<!--__NAV__-->', '<!--__FOOT__-->'):
            page = page.replace(key, '')
        if name.startswith('site/'):  # pages du site : la fresque complète n'y est pas publiée, pas de bouton vers elle
            page = re.sub(r'\s*<a class="btn full" href="fresque.html">[^<]*</a>', '', page)
        if name.startswith('site/'):  # pages du site : bouton FR / EN
            page = bouton_langue(page, cfg, clair=name.endswith('clair/index.html'), en=name.startswith('site/en/'))
            if name.startswith('site/en/') and ('<html lang="fr">' in page or 'const EN = true;' not in page):
                raise SystemExit(f'{name} : le gabarit a changé, mettre à jour GABARIT_EN')
        out = cfg['out'] / name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(avec_logo(page) if name.startswith('site/') else page)
        print(f'{out.relative_to(ROOT)}: {len(shots)} tirs, {g} buts')
    if a.carte:
        add_card(cfg, shots)


if __name__ == '__main__':
    main()
