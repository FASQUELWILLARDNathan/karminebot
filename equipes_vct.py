import psycopg
import requests
import os
import json
from collections import defaultdict
from project_code import settings
import time

# Charger les variables d'environnement
API_KEY = settings.API_KEY
DB_PASSWORD = settings.DB_PASSWORD
dbname = os.environ['dbname']
user = os.environ['user']
host = os.environ['host']

# URL de l'API Liquipedia
url = "https://api.liquipedia.net/api/v3/team"

# En-têtes pour la requête API
headers = {
    "Authorization": f"Apikey {API_KEY}",
    "Accept": "application/json",
    "User-Agent": "KarmineCorpBot/1.0 (Discord bot for Karmine Corp stats; neyznn.pro@gmail.com)"
}

# Paramètres pour récupérer les joueurs des équipes
params = {
    'wiki': 'valorant',
    'conditions': '[[pagename::Karmine_Corp]] OR [[pagename::Team_Liquid]] OR [[pagename::Natus_Vincere]] OR [[pagename::Gentle_Mates]] OR [[pagename::KOI]] OR [[pagename::BBL_Esports]] OR [[pagename::Apeks]] OR [[pagename::GIANTX]] OR [[pagename::Team_Vitality]] OR [[pagename::Fnatic]] OR [[pagename::FUT_Esports]] OR [[pagename::Team_Heretics]]',
    'limit' : 12,  # Limite par page
    'offset' : 0    # Offset initial
}

def update_teams():
    # Liste pour stocker les données des équipes
    teams_data = []

    # Pagination pour récupérer toutes les équipes
    while True:
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json().get("result", [])
            
            if not data:
                break  # Arrêter si plus de données
            
            teams_data.extend(data)  # Ajouter les nouvelles équipes récupérées

            params['offset'] += params['limit']  # Passer à la page suivante
        else:
            print(f"Erreur API : {response.status_code} - {response.text}")
            break

    # Connexion à la base PostgreSQL et insertion des équipes
    with psycopg.connect(f"dbname={dbname} user={user} password={DB_PASSWORD} host={host}") as conn:
        with conn.cursor() as cursor:
            for team in teams_data:

                cursor.execute("SELECT 1 FROM team WHERE pageid = %s;", (team.get("pageid"),))
                exists = cursor.fetchone()

                if exists:  # L'équipe existe déjà, on passe à la suivante
                    print(f"L'équipe {team.get('name')} existe déjà, on ne l'ajoute pas.")
                    continue  

                
                # Gestion des dates vides pour éviter des erreurs PostgreSQL
                createdate = team.get("createdate")
                if createdate == "0000-01-01":
                    createdate = None

                disbanddate = team.get("disbanddate")
                if disbanddate == "0000-01-01":
                    disbanddate = None

                query = """
                INSERT INTO team (
                    pageid, pagename, namespace, objectname, name, locations, region, logo, logourl, logodark, logodarkurl,
                    textlesslogourl, textlesslogodarkurl, status, createdate, disbanddate, earnings, earningsbyyear,
                    template, links, extradata
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                ) ON CONFLICT (pageid) DO NOTHING;
                """

                values = (
                    team.get("pageid"),
                    team.get("pagename"),
                    team.get("namespace"),
                    team.get("objectname"),
                    team.get("name"),
                    json.dumps(team.get("locations", [])),  # Stocker JSON
                    team.get("region"),
                    team.get("logo"),
                    team.get("logourl"),
                    team.get("logodark"),
                    team.get("logodarkurl"),
                    team.get("textlesslogourl"),
                    team.get("textlesslogodarkurl"),
                    team.get("status"),
                    createdate,
                    disbanddate,
                    team.get("earnings"),
                    json.dumps(team.get("earningsbyyear", {})),  # Stocker JSON
                    team.get("template"),
                    json.dumps(team.get("links", {})),  # Stocker JSON
                    json.dumps(team.get("extradata", {})),  # Stocker JSON
                )

                cursor.execute(query, values)
        
        conn.commit()
        print(f"Équipes insérées avec succès !")

# Boucle infinie pour exécuter la mise à jour une fois par mois
while True:
        
    # Attendre 1 mois avant de vérifier à nouveau
    update_teams()
    time.sleep(2629800)