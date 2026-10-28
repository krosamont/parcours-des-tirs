-- Tirs d'un joueur : requête MotherDuck qui produit joueurs/<joueur>/export.csv
-- Gabarit : Kylian Mbappé (nom dans foot.bronze.events) et Real Madrid (teamName) sont remplis depuis joueurs/<joueur>/joueur.json
--   python3 src/build_fresque.py <joueur> --sql   -> joueurs/<joueur>/requete.sql, prête à lancer
-- Source : foot.bronze.events (événements WhoScored, enrichis FotMob) + foot.bronze.match_status
-- Une ligne = un tir. Export : résultat de la requête -> CSV -> joueurs/<joueur>/export.csv

WITH match_info AS (
  SELECT
    match_id,
    ws_home_name,
    ws_away_name,
    fm_utcTime,
    fm_started
  FROM foot.bronze.match_status
),

-- Référentiel pour récupérer le nom du passeur via le relatedPlayerId
player_lookup AS (
  SELECT DISTINCT
    playerId,
    name AS player_name
  FROM foot.bronze.events
  WHERE teamName = 'Real Madrid'
)

SELECT
  -- Informations Match (date, heure, adversaire)
  s.match_id,
  mi.ws_home_name,
  mi.ws_away_name,
  mi.fm_utcTime,
  mi.fm_started,
  s.competition,
  s.season,

  -- Timing de l'action
  s.eventId,
  s.minute,
  s.second,

  -- Joueur & Équipe
  s.teamId,
  s.teamName,
  s.playerId,
  s.name AS player_name,

  -- Info sur la passe décisive / dernière passe
  s.relatedEventId,
  s.relatedPlayerId,
  pl.player_name AS shot_related_player_name, -- Nom du passeur

  -- Type et coordonnées
  s.type,
  s.x,
  s.y,
  s.endx,
  s.endy,
  CASE WHEN s.fm_goal_crossed_y IS NOT NULL THEN 105 ELSE NULL END AS fm_goal_crossed_x,
  s.fm_goal_crossed_y,
  CASE WHEN s.goalMouthY IS NOT NULL THEN 105 ELSE NULL END AS goalMouthX,
  s.goalMouthY,
  s.blockedX,
  s.blockedY,

  s.zone,
  s.zone_start,
  s.zone_end,
  s.length,

  -- Métriques avancées
  s.isShot,
  s.isgoal_x,
  s.xg,
  s.xgot,
  s.shot_type,
  s.situation,
  s.assisted,
  s.regularPlay,
  s.BigChance,
  s.LowCentre,
  s.FirstTouch

FROM foot.bronze.events s
LEFT JOIN match_info mi
  ON s.match_id = mi.match_id
LEFT JOIN player_lookup pl
  ON CAST(s.relatedPlayerId AS BIGINT) = pl.playerId

-- Filtre : uniquement les tirs du joueur
WHERE s.teamName = 'Real Madrid'
  AND s.name = 'Kylian Mbappé'
  AND s.isShot = TRUE

ORDER BY
  s.match_id,
  s.eventId ASC;
