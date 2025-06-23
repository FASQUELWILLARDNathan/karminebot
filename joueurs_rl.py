import psycopg
import requests
import os
import json
from collections import defaultdict
from project_code import settings
import datetime
import time

# Charger les variables d'environnement
API_KEY = settings.API_KEY
DB_PASSWORD = settings.DB_PASSWORD
dbname = os.environ['dbname']
user = os.environ['user']
host = os.environ['host']

# URL de l'API Liquipedia
url = "https://api.liquipedia.net/api/v3/player"

# En-têtes pour la requête API
headers = {
    "Authorization": f"Apikey {API_KEY}",
    "Accept": "application/json",
    "User-Agent": "KarmineCorpBot/1.0 (Discord bot for Karmine Corp stats; neyznn.pro@gmail.com)"
}

# Paramètres pour récupérer les joueurs des équipes
params = {
    'wiki': 'rocketleague',
    'conditions': '[[region::Europe]]',
    'limit': 1000,
    'offset': 0
}


def update_players():
    # Initialiser une liste pour stocker tous les joueurs
    all_players = defaultdict(list)

    # Pagination pour récupérer toutes les pages
    while True:
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json().get("result", [])

            if not data:
                break

            for player in data:
                if player.get("type") == "Player":
                    player_name = player.get("name")
                    team_name = player.get("teampagename")
                    all_players[team_name].append(player)


            params['offset'] += params['limit']
        else:
            print(f"Erreur API : {response.status_code} - {response.text}")
            break

    # Connexion à la base de données PostgreSQL
    with psycopg.connect(f"dbname={dbname} user={user} password={DB_PASSWORD} host={host}") as conn:
        with conn.cursor() as cursor:
            for team_name, players in all_players.items():

                for player in players:
                    birthdate = player.get("birthdate")
                    if birthdate == "0000-01-01":
                        birthdate = None
                    
                    deathdate = player.get("deathdate")
                    if deathdate == "0000-01-01":
                        deathdate = None

                    # Récupération du pageid de l'équipe avant insertion du joueur
                    cursor.execute("SELECT pageid FROM team WHERE pagename = %s", (player.get("teampagename"),))
                    team_pageid = cursor.fetchone()
                    team_pageid = team_pageid[0] if team_pageid else None

                    query = """
                    INSERT INTO players (
                        pageid, pagename, namespace, objectname, id, alternateid, name, localizedname, type, 
                        nationality, nationality2, nationality3, region, birthdate, deathdate, teampagename, 
                        pageidteam, teamtemplate, links, status, earnings, earningsbyyear, extradata, game
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) ON CONFLICT (pageid) DO UPDATE SET
                        teampagename = EXCLUDED.teampagename,
                        pageidteam = EXCLUDED.pageidteam;
                    """

                    values = (
                        player.get("pageid"),
                        player.get("pagename"),
                        player.get("namespace"),
                        player.get("objectname"),
                        player.get("id"),
                        player.get("alternateid"),
                        player.get("name"),
                        player.get("localizedname"),
                        player.get("type"),
                        player.get("nationality"),
                        player.get("nationality2"),
                        player.get("nationality3"),
                        player.get("region"),
                        birthdate,
                        deathdate,
                        player.get("teampagename"),
                        team_pageid,  # Associer le bon pageidteam
                        player.get("teamtemplate"),
                        json.dumps(player.get("links", {})),
                        player.get("status"),
                        player.get("earnings"),
                        json.dumps(player.get("earningsbyyear", {})),
                        json.dumps(player.get("extradata", {})),
                        "rocketleague"
                    )

                    cursor.execute(query, values)

            conn.commit()
            print("Joueurs insérés et pageidteam mis à jour avec succès !")

# Boucle infinie pour exécuter la mise à jour une fois par mois
while True:
    # Vérifier si c'est le 1er jour du mois
    if datetime.now().day == 1:
        update_players()

    # Attendre 24 heures avant de vérifier à nouveau
    time.sleep(86400)  # 86400 secondes = 1 jour