import psycopg
import requests
import os
import json
from project_code import settings
from datetime import datetime, timedelta
import time

# Charger les variables d'environnement
API_KEY = settings.API_KEY
DB_PASSWORD = settings.DB_PASSWORD
dbname = os.environ['dbname']
user = os.environ['user']
host = os.environ['host']

# URL de l'API Liquipedia
url = "https://api.liquipedia.net/api/v3/match"

# En-têtes pour la requête API
headers = {
    "Authorization": f"Apikey {API_KEY}",
    "Accept": "application/json",
    "User-Agent": "KarmineCorpBot/1.0 (Discord bot for Karmine Corp stats; neyznn.pro@gmail.com)"
}

def update_matches():
    # Paramètres pour récupérer les matchs
    params = {
    'wiki': 'leagueoflegends',
    'limit': 100,  # Limite par page
    'conditions': '([[opponent::Karmine Corp]] OR [[opponent::Karmine Corp Blue Stars]] OR [[opponent::Karmine Corp Blue]]) AND [[series::!LEC]] AND [[series::!LFL]] AND [[series::!LFL Division 2]]',
    'offset': 0  # Offset initial
    }


    # Liste pour stocker les données des matchs
    matches_data = []

    # Pagination pour récupérer tous les matchs
    while True:
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json().get("result", [])

            if not data:
                break  # Arrêter si plus de données

            matches_data.extend(data)  # Ajouter les nouveaux matchs récupérés
            print(f"Nombre de matchs récupérés : {len(data)}")
            params['offset'] += params['limit'] # Passer à la page suivante 
            print(f"Offset actuel : {params['offset']}")
        else:
            print(f"Erreur API : {response.status_code} - {response.text}")
            break

    # Connexion à la base PostgreSQL et insertion des matchs
    with psycopg.connect(f"dbname={dbname} user={user} password={DB_PASSWORD} host={host}") as conn:
        with conn.cursor() as cursor:
            for match in matches_data:

                # Gestion des champs optionnels pour éviter des erreurs PostgreSQL
                finished = match.get("finished")
                if finished is not None and not isinstance(finished, bool):
                    finished = False  # Mettre une valeur par défaut si ce n'est pas un booléen

                dateexact = match.get("dateexact")
                if dateexact is not None and not isinstance(dateexact, bool):
                    dateexact = False  # Mettre une valeur par défaut si ce n'est pas un booléen

                # Requête SQL d'insertion
                query = """
                INSERT INTO matches (
                    pageid, pagename, namespace, objectname, match2id, match2bracketid,
                    status, winner, walkover, resulttype, finished, mode, type, section, game, patch,
                    links, bestof, date, dateexact, stream, vod, tournament, parent, tickername, shortname,
                    series, icon, iconurl, icondark, icondarkurl, liquipediatier, liquipediatiertype,
                    publishertier, extradata, match2bracketdata, match2games, match2opponents
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (objectname) DO UPDATE SET
                    pageid = EXCLUDED.pageid,
                    pagename = EXCLUDED.pagename,
                    namespace = EXCLUDED.namespace,
                    match2id = EXCLUDED.match2id,
                    match2bracketid = EXCLUDED.match2bracketid,
                    status = EXCLUDED.status,
                    winner = EXCLUDED.winner,
                    walkover = EXCLUDED.walkover,
                    resulttype = EXCLUDED.resulttype,
                    finished = EXCLUDED.finished,
                    mode = EXCLUDED.mode,
                    type = EXCLUDED.type,
                    section = EXCLUDED.section,
		    game = EXCLUDED.game,
                    patch = EXCLUDED.patch,
                    links = EXCLUDED.links,
                    bestof = EXCLUDED.bestof,
                    date = EXCLUDED.date,
                    dateexact = EXCLUDED.dateexact,
                    stream = EXCLUDED.stream,
                    vod = EXCLUDED.vod,
                    tournament = EXCLUDED.tournament,
                    parent = EXCLUDED.parent,
                    tickername = EXCLUDED.tickername,
                    shortname = EXCLUDED.shortname,
                    series = EXCLUDED.series,
                    icon = EXCLUDED.icon,
                    iconurl = EXCLUDED.iconurl,
                    icondark = EXCLUDED.icondark,
                    icondarkurl = EXCLUDED.icondarkurl,
                    liquipediatier = EXCLUDED.liquipediatier,
                    liquipediatiertype = EXCLUDED.liquipediatiertype,
                    publishertier = EXCLUDED.publishertier,
                    extradata = EXCLUDED.extradata,
                    match2bracketdata = EXCLUDED.match2bracketdata,
                    match2games = EXCLUDED.match2games,
                    match2opponents = EXCLUDED.match2opponents;

                """


                # Remplir les valeurs avec des valeurs par défaut si nécessaire
                values = (
                    match.get("pageid"),
                    match.get("pagename"),
                    match.get("namespace"),
                    match.get("objectname"),
                    match.get("match2id"),
                    match.get("match2bracketid"),
                    match.get("status"),
                    match.get("winner"),
                    match.get("walkover"),
                    match.get("resulttype"),
                    finished,  # Valeur booléenne ou False
                    match.get("mode"),
                    match.get("type"),
                    match.get("section"),
                    match.get("game"),
                    match.get("patch"),
                    json.dumps(match.get("links", {})),  # Convertir en chaîne JSON
		            match.get("bestof"),
                    match.get("date"),
                    dateexact,  # Valeur booléenne ou False
                    json.dumps(match.get("stream", {})),  # Convertir en chaîne JSON
                    match.get("vod"),
                    match.get("tournament"),
                    match.get("parent"),
                    match.get("tickername"),
                    match.get("shortname"),
                    match.get("series"),
                    match.get("icon"),
                    match.get("iconurl"),
                    match.get("icondark"),
                    match.get("icondarkurl"),
                    match.get("liquipediatier"),
                    match.get("liquipediatiertype"),
                    match.get("publishertier"),
                    json.dumps(match.get("extradata", {})),  # Convertir en chaîne JSON
                    json.dumps(match.get("match2bracketdata", {})),  # Convertir en chaîne JSON
                    json.dumps(match.get("match2games", {})),  # Convertir en chaîne JSON
                    json.dumps(match.get("match2opponents", {})) # Convertir en chaîne JSON
                )

                # Exécution de la requête
                cursor.execute(query, values)

                # Log pour vérifier l'insertion
                cursor.execute("SELECT COUNT(*) FROM matches;")
                print(f"Nombre de matchs dans la base après insertion : {cursor.fetchone()[0]}")

        conn.commit()
        print(f"Matchs insérés avec succès !")

while True:

    # Attendre 1 heures avant de vérifier à nouveau
    update_matches()
    heure_locale = datetime.now() + timedelta(hours=2)
    print(f"update du {heure_locale.strftime('%Y-%m-%d %H:%M:%S')}")
    time.sleep(3600)
