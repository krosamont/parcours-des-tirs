"""Fresque "Shot Flow" de Mbappé (inspirée des Shot Flow basket de graphsketball).

usage: python3 visuel_mbappe/build_fresque.py
  lit  visuel_mbappe/export.csv  (tirs WhoScored x FotMob)
  écrit visuel_mbappe/fresque_mbappe.html      (fresque complète, page autonome : données + photo embarquées)
        visuel_mbappe/fresque_interactive.html  (même parcours, déroulé colonne par colonne au clic)
        visuel_mbappe/site/index.html           (la page interactive aux couleurs de data-workers.com, à publier dans /projet/mbappe_tirs/)

Parcours d'un tir : ZONE -> SITUATION -> SURFACE -> RÉSULTAT -> (buts seulement) PASSEUR -> COMMENT IL A MARQUÉ
"""
import base64, json, math
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PHOTO = ROOT / 'assets/players/701154.png'   # id FotMob de Mbappé

# x en [0,105] vers le but adverse, y en [0,68] avec y haut = côté gauche de l'attaquant (coordonnées WhoScored x1.05 / x0.68)
BOX_X, SIX_X = 83 * 1.05, 94.2 * 1.05             # 87.15 m, 98.9 m
BOX_Y, SIX_Y = (21.1 * .68, 78.9 * .68), (36.8 * .68, 63.2 * .68)

SITUATION = {'RegularPlay': 'Jeu placé', 'FastBreak': 'Contre-attaque', 'Penalty': 'Penalty', 'FromCorner': 'Corner',
             'FreeKick': 'Coup franc direct', 'SetPiece': 'Autre CPA', 'ThrowInSetPiece': 'Autre CPA', 'IndividualPlay': 'Action individuelle'}
BODY = {'RightFoot': 'Pied droit', 'LeftFoot': 'Pied gauche', 'Header': 'Tête'}
TYPE = {'Goal': 'But', 'SavedShot': 'Arrêté', 'MissedShots': 'Hors cadre', 'ShotOnPost': 'Poteau'}
SHORT = {'Vinícius Júnior': 'Vinícius', 'Brahim Díaz': 'Brahim', 'Trent Alexander-Arnold': 'Alexander-Arnold', 'Arda Güler': 'Güler'}


def zone(r):
    # le champ Zone du CSV vaut 'Center' pour 474/478 tirs : on redécoupe à partir de x/y
    if r.situation == 'Penalty':
        return 'Point de penalty'
    if r.x >= SIX_X and SIX_Y[0] <= r.y <= SIX_Y[1]:
        return 'Surface de but'
    if r.x >= BOX_X and BOX_Y[0] <= r.y <= BOX_Y[1]:
        if SIX_Y[0] <= r.y <= SIX_Y[1]:
            return 'Surface · axe'
        return 'Surface · gauche' if r.y > SIX_Y[1] else 'Surface · droite'
    return 'Hors surface'


def short(name):
    if not isinstance(name, str):
        return None
    return SHORT.get(name, name.split()[-1])


def main():
    d = pd.read_csv(HERE / 'export.csv')
    shots = []
    for r in d.itertuples():
        goal = r.type == 'Goal'
        shots.append({
            'season': r.season, 'comp': r.competition,
            'zone': zone(r), 'sit': SITUATION.get(r.situation, r.situation), 'body': BODY.get(r.shot_type, r.shot_type),
            'goal': int(goal), 'type': TYPE.get(r.type, r.type),
            'ast': short(r.shot_related_player_name), 'ftouch': int(r.FirstTouch == True),
            'x': round(r.x, 1), 'y': round(r.y, 1), 'xg': None if pd.isna(r.xg) else round(r.xg, 3),
            'opp': r.ws_away_name if r.ws_home_name == 'Real Madrid' else r.ws_home_name,
            'date': r.fm_utcTime[:10], 'min': int(r.minute),
        })
    photo = 'data:image/png;base64,' + base64.b64encode(PHOTO.read_bytes()).decode()
    g = sum(s['goal'] for s in shots)
    for tpl, name, site in (('fresque_template.html', 'fresque_mbappe.html', False),
                            ('interactive_template.html', 'fresque_interactive.html', False),
                            ('interactive_template.html', 'site/index.html', True)):
        html = (HERE / tpl).read_text()
        html = html.replace('/*__SHOTS__*/[]', json.dumps(shots, ensure_ascii=False)).replace('__PHOTO__', photo)
        for key, value in (SITE if site else {}).items():
            html = html.replace(key, value)
        for key in ('<!--__HEAD__-->', '/*__THEME__*/', '<!--__NAV__-->', '<!--__FOOT__-->'):
            html = html.replace(key, '')
        out = HERE / name
        out.parent.mkdir(exist_ok=True)
        out.write_text(html)
        print(f'{out.relative_to(ROOT)}: {len(shots)} tirs, {g} buts')


# version publiée sur data-workers.com/projet/mbappe_tirs/ : couleurs, police et navigation du site
SITE_URL = 'https://data-workers.com/projet/mbappe_tirs/'
SITE = {
    '<title>Parcours des tirs Mbappé</title>': '<title>Kylian Mbappé, le parcours de ses tirs · Data Workers</title>',
    '<!--__HEAD__-->': f"""<meta name="description" content="Les 478 tirs de Kylian Mbappé au Real Madrid, de la zone de frappe jusqu'au passeur et à la phase du but : un Sankey interactif à dérouler phase par phase.">
<meta property="og:title" content="Kylian Mbappé, le parcours de ses tirs">
<meta property="og:description" content="Zone, situation, surface, résultat, passeur : le Sankey interactif des tirs de Mbappé au Real Madrid.">
<meta property="og:image" content="https://data-workers.com/projet/assets/mbappe_tirs.jpg">
<meta property="og:url" content="{SITE_URL}">
<link rel="icon" href="/assets/images/logo.ico">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">""",
    '/*__THEME__*/': (HERE / 'site_theme.css').read_text(),
    '<!--__NAV__-->': '<nav class="sitenav"><img src="/assets/images/logo.png" alt=""><a href="https://data-workers.com/">Data Workers</a><span>/</span><a href="/projet/">Projets</a></nav>',
    '<!--__FOOT__-->': '<footer class="sitefoot"><a href="https://data-workers.com/">data-workers.com</a> · Kevin Rosamont Prombo · Données WhoScored × FotMob</footer>',
    '<h1>Kylian Mbappé,<br>le parcours de ses tirs</h1>': '<h1>Kylian Mbappé,<br><em>le parcours de ses tirs</em></h1>',
}


if __name__ == '__main__':
    main()
