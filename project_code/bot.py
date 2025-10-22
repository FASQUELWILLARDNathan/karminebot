import os
import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import psycopg
import json
import asyncio
from discord.ui import View, Button
import settings
import locale
import traceback
from discord import app_commands, Interaction
from matches_detection.lfl import start_lfl_task
from matches_detection.gc import start_gc_task
from matches_detection.inter import start_inter_task
from matches_detection.lolval import start_lolval_task
from matches_detection.rl import start_rl_task
from matches_detection.francerl import start_france_task
import signal

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
token = settings.BOT_KEY
DB_PASSWORD = settings.DB_PASSWORD
dbname = settings.dbname
user = settings.user
host = settings.host

async def shutdown(reason="Raison indéterminée"):
    try:
        with psycopg.connect(f"dbname={dbname} user={user} password={DB_PASSWORD} host={host}") as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT guild_id, notifications_channel_id FROM guild_configs WHERE is_active = TRUE")
                guild_channels = cur.fetchall()

                for guild_id, channel_id in guild_channels:
                    channel = bot.get_channel(channel_id)
                    if channel:
                        try:
                            await channel.send(f"🛑 Arrêt du Bot. Raison : **{reason}**")
                        except discord.Forbidden:
                            print(f"Pas la permission d'envoyer dans {channel_id}. Marquage inactif.")
                            with psycopg.connect(f"dbname={dbname} user={user} password={DB_PASSWORD} host={host}") as conn2:
                                with conn2.cursor() as cur2:
                                    cur2.execute("UPDATE guild_configs SET is_active = FALSE WHERE notifications_channel_id = %s", (channel_id,))
                                    conn2.commit()
                        except Exception as send_err:
                            print(f"Erreur envoi message dans {channel_id}: {send_err}")
                    else:
                        print(f"Channel ID {channel_id} non trouvé ou inaccessible.")

                print("Arrêt du bot...")
                await bot.close()
    except Exception as e:
            print(f"Erreur : {e}")

# ---- Commande Discord pour arrêter avec raison ----
@bot.command()
@commands.is_owner()  # optionnel : limite l’usage à toi (le propriétaire du bot)
async def stop(ctx, *, reason="Arrêt manuel via commande"):
    await shutdown(reason)

def insert_test_match():
    # Création d’une date dans 47 minutes
    date_match = (datetime.utcnow() + timedelta(minutes=47)).strftime("%Y-%m-%d %H:%M:%S")

    fake_match = {
        "pageid": 9999999,
        "pagename": "TestMatchKC",
        "namespace": 0,
        "objectname": f"test-match-{int(datetime.utcnow().timestamp())}",
        "match2id": 123456,
        "match2bracketid": 0,
        "status": "upcoming",
        "winner": None,
        "walkover": None,
        "resulttype": None,
        "finished": False,
        "mode": None,
        "type": None,
        "section": "Test Section",
        "game": "League of Legends",
        "patch": "14.18",
        "links": {},
        "bestof": 1,
        "date": date_match,
        "dateexact": True,
        "stream": {},
        "vod": None,
        "tournament": "Test Tournament",
        "parent": None,
        "tickername": "KC vs TEST",
        "shortname": "KCorp vs Test",
        "series": "BO1",
        "icon": None,
        "iconurl": None,
        "icondark": None,
        "icondarkurl": None,
        "liquipediatier": "Test Tier",
        "liquipediatiertype": "Test Type",
        "publishertier": None,
        "extradata": {},
        "match2bracketdata": {},
        "match2games": {},
        "match2opponents": {
            "1": {"name": "Karmine Corp"},
            "2": {"name": "Test Opponent"}
        }
    }

    query = """
    INSERT INTO matches (
        pageid, pagename, namespace, objectname, match2id, match2bracketid,
        status, winner, walkover, resulttype, finished, mode, type, section,
        game, patch, links, bestof, date, dateexact, stream, vod, tournament,
        parent, tickername, shortname, series, icon, iconurl, icondark, icondarkurl,
        liquipediatier, liquipediatiertype, publishertier, extradata,
        match2bracketdata, match2games, match2opponents
    ) VALUES (
        %(pageid)s, %(pagename)s, %(namespace)s, %(objectname)s, %(match2id)s, %(match2bracketid)s,
        %(status)s, %(winner)s, %(walkover)s, %(resulttype)s, %(finished)s, %(mode)s, %(type)s, %(section)s,
        %(game)s, %(patch)s, %(links)s, %(bestof)s, %(date)s, %(dateexact)s, %(stream)s, %(vod)s, %(tournament)s,
        %(parent)s, %(tickername)s, %(shortname)s, %(series)s, %(icon)s, %(iconurl)s, %(icondark)s, %(icondarkurl)s,
        %(liquipediatier)s, %(liquipediatiertype)s, %(publishertier)s, %(extradata)s,
        %(match2bracketdata)s, %(match2games)s, %(match2opponents)s
    )
    ON CONFLICT (objectname) DO UPDATE SET
        status = EXCLUDED.status,
        date = EXCLUDED.date,
        dateexact = EXCLUDED.dateexact,
        match2opponents = EXCLUDED.match2opponents;
    """

    with psycopg.connect(f"dbname={dbname} user={user} password={DB_PASSWORD} host={host}") as conn:
        with conn.cursor() as cur:
            # JSON dump des champs dict
            fake_match["links"] = json.dumps(fake_match["links"])
            fake_match["stream"] = json.dumps(fake_match["stream"])
            fake_match["extradata"] = json.dumps(fake_match["extradata"])
            fake_match["match2bracketdata"] = json.dumps(fake_match["match2bracketdata"])
            fake_match["match2games"] = json.dumps(fake_match["match2games"])
            fake_match["match2opponents"] = json.dumps(fake_match["match2opponents"])

            cur.execute(query, fake_match)
            conn.commit()
            return date_match  # On retourne la date pour l’afficher dans Discord
        
def delete_test_match():
    with psycopg.connect(f"dbname={dbname} user={user} password={DB_PASSWORD} host={host}") as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM matches WHERE pageid = %s", ('9999999',))  # <-- attention aux quotes
            deleted_count = cur.rowcount  # <-- nombre de lignes supprimées
            conn.commit()
            return deleted_count
        

@bot.command(name="inserermatch")
@commands.is_owner()
async def inserer_match(ctx):
    date_match = insert_test_match()
    await ctx.send(f"✅ Match test inséré pour **{date_match} UTC**")

@bot.command(name="supprimermatch")
@commands.is_owner()
async def supprimer_match(ctx):
    count = delete_test_match()
    if count > 0:
        await ctx.send(f"🗑️ Match test supprimé ({count} ligne(s) supprimée(s)).")
    else:
        await ctx.send("⚠️ Aucun match test trouvé à supprimer.")

@bot.event
async def on_ready():
    start_lolval_task(bot, DB_PASSWORD)
    start_rl_task(bot, DB_PASSWORD)
    start_lfl_task(bot, DB_PASSWORD)
    start_gc_task(bot, DB_PASSWORD)
    start_inter_task(bot, DB_PASSWORD)
    start_france_task(bot, DB_PASSWORD)
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} slash commands synchronisées.")
    except Exception as e:
        print(f"❌ Erreur lors de la synchronisation des slash commands : {e}")

    print("Bot prêt et tâche de vérification lancée.")

async def split_and_send(ctx, content):
    max_length = 2000
    lines = content.split('\n')
    message = ""

    for line in lines:
        # +1 pour le retour à la ligne à ajouter entre les lignes
        if len(message) + len(line) + 1 > max_length:
            await ctx.send(message)
            message = line  # Commencer un nouveau message avec cette ligne
        else:
            if message:
                message += '\n' + line
            else:
                message = line

    if message:
        await ctx.send(message)


# Match Karmine Corp de la semaine courant
@bot.hybrid_command(name="weekmatches", description="Affiche les matchs de la Karmine cette semaine")
async def weekmatches(ctx):
    now = datetime.now()
    start_week = now - timedelta(days=now.weekday())  # Lundi de cette semaine
    end_week = start_week + timedelta(days=7)
    current_year = start_week.year


    query = """
    SELECT
    date, pagename, match2opponents, tournament, winner
    FROM matches
    WHERE
    date BETWEEN %s AND %s
    AND EXTRACT(YEAR FROM date) = %s
    AND (
        match2opponents::text ILIKE '%%Karmine Corp%%'
        OR match2opponents::text ILIKE '%%Karmine Corp Blue%%'
        OR match2opponents::text ILIKE '%%KC Blue Stars%%'
        OR match2opponents::text ILIKE '%%Karmine Corp GC%%'
        OR match2opponents::text ILIKE '%%France%%'
        )
    ORDER BY date ASC;
    """


    try:
        with psycopg.connect(f"dbname={dbname} user={user} password={DB_PASSWORD} host={host}") as conn:
            with conn.cursor() as cur:
                cur.execute(query, (start_week, end_week, current_year))
                results = cur.fetchall()

                if not results:
                    await ctx.send("Aucun match de la Karmine Corp cette semaine-ci.")
                    return

                message = "**Matchs de la Karmine cette semaine-ci :**\n"
                for match in results:
                    date, pagename, match2opponents, tournament, winner = match

                    # Récupérer les noms des équipes dans match2opponents
                    teams_query = """
                        SELECT jsonb_path_query_array(match2opponents, '$[*].teamtemplate.name') AS team_names
                        FROM matches
                        WHERE date = %s AND pagename = %s
                    """
                    cur.execute(teams_query, (date, pagename))
                    teams_result = cur.fetchone()

                    opponent = ""
                    result = "Inconnu"

                    if teams_result and isinstance(teams_result[0], list):
                        team_names = teams_result[0]

                        kc_aliases = ["Karmine Corp", "Karmine Corp Blue", "KC Blue Stars", "Karmine Corp GC", "France"]
                        kc_name = None

                        for name in team_names:
                            for alias in kc_aliases:
                                if alias.lower() in name.lower():
                                    kc_name = name  # On prend le nom réel tel qu'il apparaît dans team_names
                                    break
                            if kc_name:
                                break

                        if kc_name:
                            kc_index = team_names.index(kc_name)

                            if len(team_names) == 2:
                                opponent_index = 1 - kc_index
                                opponent = team_names[opponent_index]
                            else:
                                opponent = "Adversaire non déterminé"

                            if winner == "":
                                result = "À venir"
                            elif winner == str(kc_index + 1):
                                result = "Gagné"
                            else:
                                result = "Perdu"
                        else:
                            opponent = "Inconnu"
                            result = "Inconnu"
                    else:
                        opponent = "Inconnu"
                        result = "Inconnu"
                    
                    date = date + timedelta(hours=2)
                    message += f"📅 {date.strftime('%d/%m %H:%M')} - {tournament} vs {opponent} - {result}\n"


                await split_and_send(ctx, message)

    except Exception as e:
        traceback.print_exc()
        await ctx.send(f"Erreur lors de la récupération des matchs : {e}")


# Match Karmine Corp du mois courant
@bot.hybrid_command(name="monthmatches", description="Affiche les matchs de la Karmine ce mois-ci")
async def monthmatches(ctx):
    now = datetime.utcnow()
    start_month = now.replace(day=1)
    if now.month == 12:
        end_month = now.replace(year=now.year + 1, month=1, day=1)
    else:
        end_month = now.replace(month=now.month + 1, day=1)
    current_year = start_month.year

    query = """
        SELECT
            date, pagename, match2opponents, tournament, winner
        FROM matches
        WHERE
            date BETWEEN %s AND %s
            AND EXTRACT(YEAR FROM date) = %s
            AND (
                match2opponents::text ILIKE '%%Karmine Corp%%'
                OR match2opponents::text ILIKE '%%France%%'
            )
        ORDER BY date ASC;
    """

    try:
        with psycopg.connect(f"dbname={dbname} user={user} password={DB_PASSWORD} host={host}") as conn:
            with conn.cursor() as cur:
                cur.execute(query, (start_month, end_month, current_year))
                results = cur.fetchall()

                if not results:
                    await ctx.send("Aucun match de la Karmine Corp ce mois-ci.")
                    return

                message = "**Matchs de la Karmine ce mois-ci :**\n"
                for match in results:
                    date, pagename, match2opponents, tournament, winner = match

                    # Récupérer les noms des équipes dans match2opponents
                    teams_query = """
                        SELECT jsonb_path_query_array(match2opponents, '$[*].teamtemplate.name') AS team_names
                        FROM matches
                        WHERE date = %s AND pagename = %s
                    """
                    cur.execute(teams_query, (date, pagename))
                    teams_result = cur.fetchone()

                    opponent = ""
                    result = "Inconnu"

                    if teams_result and isinstance(teams_result[0], list):
                        team_names = teams_result[0]

                        kc_aliases = ["Karmine Corp", "Karmine Corp Blue", "KC Blue Stars", "Karmine Corp GC", "France"]
                        kc_name = None

                        for name in team_names:
                            for alias in kc_aliases:
                                if alias.lower() in name.lower():
                                    kc_name = name  # On prend le nom réel tel qu'il apparaît dans team_names
                                    break
                            if kc_name:
                                break

                        if kc_name:
                            kc_index = team_names.index(kc_name)

                            if len(team_names) == 2:
                                opponent_index = 1 - kc_index
                                opponent = team_names[opponent_index]
                            else:
                                opponent = "Adversaire non déterminé"

                            if winner == "":
                                result = "À venir"
                            elif winner == str(kc_index + 1):
                                result = "Gagné"
                            else:
                                result = "Perdu"
                        else:
                            opponent = "Inconnu"
                            result = "Inconnu"
                    else:
                        opponent = "Inconnu"
                        result = "Inconnu"
                    
                    date = date + timedelta(hours=2)
                    message += f"📅 {date.strftime('%d/%m %H:%M')} - {tournament} vs {opponent} - {result}\n"


                await split_and_send(ctx, message)

    except Exception as e:
        traceback.print_exc()
        await ctx.send(f"Erreur lors de la récupération des matchs : {e}")


# Retourne les statistiques de la Karmine depuis sa création
@bot.hybrid_command(name="stats", description="Statistiques de la Karmine en LEC, LFL, VCT, VCL, GC, RLCS")
async def stats(ctx):
    try:
        query = """
            SELECT
                match2opponents,
                winner,
                tournament,
                series
            FROM matches
            WHERE (match2opponents::text ILIKE '%%Karmine Corp%%')
            AND winner IS NOT NULL
            AND winner != '';
        """

        with psycopg.connect(f"dbname={dbname} user={user} password={DB_PASSWORD} host={host}") as conn:
            with conn.cursor() as cur:
                cur.execute(query)
                matches = cur.fetchall()
                stats_data = {
                    "LEC": {"wins": 0, "losses": 0},
                    "VCT": {"wins": 0, "losses": 0},
                    "RLCS": {"wins": 0, "losses": 0},
                    "LFL": {"wins": 0, "losses": 0},
                    "GC": {"wins": 0, "losses": 0},
                    "VCL": {"wins": 0, "losses": 0}
                }

                for match2opponents, winner, tournament, series in matches:
                    # Récupérer noms des équipes
                    cur.execute("""
                        SELECT jsonb_path_query_array(%s, '$[*].teamtemplate.name') AS team_names
                    """, (json.dumps(match2opponents),))
                    teams_result = cur.fetchone()

                    if teams_result and isinstance(teams_result[0], list):
                        team_names = teams_result[0]

                        if "Karmine Corp" in team_names or "Karmine Corp Blue" in team_names or "KC Blue Stars" in team_names or "Karmine Corp GC" in team_names:
                            if "Karmine Corp" in team_names:
                                kc_name = "Karmine Corp"
                            elif "Karmine Corp Blue" in team_names:
                                kc_name = "Karmine Corp Blue"
                            elif "KC Blue Stars" in team_names:
                                kc_name = "KC Blue Stars"
                            elif "Karmine Corp GC" in team_names:
                                kc_name = "Karmine Corp GC"

                            kc_index = team_names.index(kc_name)
                            opponent_index = 1 - kc_index  # 0 <-> 1
                            opponent = team_names[opponent_index]

                            if winner == "":
                                result = "À venir"
                            elif winner == str(kc_index + 1):  # winner est 1-based
                                result = "wins"
                            else:
                                result = "losses"

                        if "LEC" in series:
                            stats_data["LEC"][result] += 1
                        elif "LFL" in series:
                            stats_data["LFL"][result] += 1
                        elif "Champions Tour" in series:
                            stats_data["VCT"][result] += 1
                        elif "RLCS" in tournament:
                            stats_data["RLCS"][result] += 1
                        elif "LFL" in tournament:
                            stats_data["LFL"][result] += 1
                        elif "Game Changers" in series:
                            stats_data["GC"][result] += 1
                        elif "Challengers Leagues" in series:
                            stats_data["VCL"][result] += 1

                # Calculs finaux
                def format_stats(label, data):
                    total = data["wins"] + data["losses"]
                    winrate = f"{(data['wins'] / total * 100):.1f}%" if total > 0 else "N/A"
                    return f"**{label}**\n✅ Victoires : {data['wins']}\n❌ Défaites : {data['losses']}\n📊 Winrate : {winrate}\n"

                message = "**Statistiques de la Karmine :**\n\n"
                message += format_stats("LEC", stats_data["LEC"])
                message += "\n"
                message += format_stats("LFL", stats_data["LFL"])
                message += "\n"
                message += format_stats("VCT", stats_data["VCT"])
                message += "\n"
                message += format_stats("GC", stats_data["GC"])
                message += "\n"
                message += format_stats("VCL", stats_data["VCL"])
                message += "\n"
                message += format_stats("RLCS", stats_data["RLCS"])
                await ctx.send(message)

    except Exception as e:
        await ctx.send(f"Erreur lors du calcul des stats : {e}")

# Retourne les statistiques de la Karmine depuis l'année actuelle
@bot.hybrid_command(name="yearstats", description="Affiche les statistiques de la Karmine cette année")
async def yearstats(ctx):
    try:
        now = datetime.now()
        current_year = now.year

        query = """
            SELECT
                match2opponents,
                winner,
                tournament,
                series
            FROM matches
            WHERE (match2opponents::text ILIKE '%%Karmine Corp%%')
            AND winner IS NOT NULL
            AND winner != ''
            AND EXTRACT(YEAR FROM date) = %s;
        """

        with psycopg.connect(f"dbname={dbname} user={user} password={DB_PASSWORD} host={host}") as conn:
            with conn.cursor() as cur:
                cur.execute(query, (current_year,))
                matches = cur.fetchall()

                stats_data = {
                    "LEC": {"wins": 0, "losses": 0},
                    "VCT": {"wins": 0, "losses": 0},
                    "RLCS": {"wins": 0, "losses": 0},
                    "LFL": {"wins": 0, "losses": 0},
                    "VCL": {"wins": 0, "losses": 0},
                    "GC": {"wins":0, "losses": 0}
                }

                for match2opponents, winner, tournament, series in matches:
                    # Récupérer les noms des équipes
                    cur.execute(""" 
                        SELECT jsonb_path_query_array(%s, '$[*].teamtemplate.name') AS team_names 
                    """, (json.dumps(match2opponents),))
                    teams_result = cur.fetchone()

                    if teams_result and isinstance(teams_result[0], list):
                        team_names = teams_result[0]

                        if "Karmine Corp" in team_names or "Karmine Corp Blue" in team_names or "KC Blue Stars" in team_names or "Karmine Corp GC" in team_names:
                            if "Karmine Corp" in team_names:
                                kc_name = "Karmine Corp"
                            elif "Karmine Corp Blue" in team_names:
                                kc_name = "Karmine Corp Blue"
                            elif "KC Blue Stars" in team_names:
                                kc_name = "KC Blue Stars"
                            elif "Karmine Corp GC" in team_names:
                                kc_name = "Karmine Corp GC"

                            kc_index = team_names.index(kc_name)
                            opponent_index = 1 - kc_index  # 0 <-> 1
                            opponent = team_names[opponent_index]

                            if winner == "":
                                result = "À venir"
                            elif winner == str(kc_index + 1):  # winner est 1-based
                                result = "wins"
                            else:
                                result = "losses"

                        if "LEC" in series:
                            stats_data["LEC"][result] += 1
                        elif "LFL" in series:
                            stats_data["LFL"][result] += 1
                        elif "Champions Tour" in series:
                            stats_data["VCT"][result] += 1
                        elif "RLCS" in tournament:
                            stats_data["RLCS"][result] += 1
                        elif "LFL" in tournament:
                            stats_data["LFL"][result] += 1
                        elif "Game Changers" in series:
                            stats_data["GC"][result] += 1
                        elif "Challengers Leagues" in series:
                            stats_data["VCL"][result] += 1
                # Calculs finaux
                def format_stats(label, data):
                    total = data["wins"] + data["losses"]
                    winrate = f"{(data['wins'] / total * 100):.1f}%" if total > 0 else "N/A"
                    return f"**{label}**\n✅ Victoires : {data['wins']}\n❌ Défaites : {data['losses']}\n📊 Winrate : {winrate}\n"

                message = "**Statistiques de la Karmine pour l'année courante :**\n\n"
                message += format_stats("LEC", stats_data["LEC"])
                message += "\n"
                message += format_stats("LFL", stats_data["LFL"])
                message += "\n"
                message += format_stats("VCT", stats_data["VCT"])
                message += "\n"
                message += format_stats("GC", stats_data["GC"])
                message += "\n"
                message += format_stats("VCL", stats_data["VCL"])
                message += "\n"
                message += format_stats("RLCS", stats_data["RLCS"])
                await ctx.send(message)

    except Exception as e:
        await ctx.send(f"Erreur lors du calcul des stats : {e}")

def get_prediction_stats():
    try:
        with psycopg.connect(f"dbname={dbname} user={user} password={DB_PASSWORD} host={host}") as conn:
            with conn.cursor() as cur:
                # Sélectionner les prédictions, résultats, et heure du vote
                cur.execute("""
                    SELECT p.user_id, p.choix, m.winner, p.username, m.match2opponents, p.vote_time
                    FROM prediction p
                    JOIN matches m ON p.match_id = m.objectname
                    WHERE m.winner != ''  -- Seulement les matchs avec un résultat
                """)
                data = cur.fetchall()

                user_stats = {}

                for user_id, choice, winner, username, match2opponents, vote_time in data:
                    try:
                        # Extraire les IDs des équipes à partir du JSON
                        team_ids = [team["id"] for team in match2opponents]

                        # Identifier l'ID de Karmine Corp
                        kc_team_id = next((team_id for team_id in team_ids
                                           if "Karmine Corp" in next(team for team in match2opponents if team["id"] == team_id)["teamtemplate"]["name"]), None)

                        if not kc_team_id:
                            continue

                        # Identifier l’adversaire
                        opponent_team_id = next((team_id for team_id in team_ids if team_id != kc_team_id), None)
                        if not opponent_team_id:
                            continue

                        # Initialiser stats utilisateur si nécessaire
                        if user_id not in user_stats:
                            user_stats[user_id] = {
                                "good": 0,
                                "bad": 0,
                                "total": 0,
                                "username": username,
                                "last_vote_time": vote_time  # on enregistre le premier vote rencontré
                            }
                        else:
                            # Mettre à jour la date du dernier vote si plus récente
                            if vote_time > user_stats[user_id]["last_vote_time"]:
                                user_stats[user_id]["last_vote_time"] = vote_time

                        # Vérification de la prédiction
                        if choice == 1:  # Prédit victoire KC
                            if winner == str(kc_team_id):
                                user_stats[user_id]["good"] += 1
                            else:
                                user_stats[user_id]["bad"] += 1
                        elif choice == 2:  # Prédit défaite KC
                            if winner == str(opponent_team_id):
                                user_stats[user_id]["good"] += 1
                            else:
                                user_stats[user_id]["bad"] += 1

                        user_stats[user_id]["total"] += 1

                    except Exception as inner_e:
                        print(f"Erreur dans le traitement d’un match : {inner_e}")
                        continue

                # Calcul du pourcentage
                for stats in user_stats.values():
                    stats["percentage"] = (stats["good"] / stats["total"]) * 100 if stats["total"] > 0 else 0

                return user_stats

    except Exception as e:
        print(f"Erreur dans get_prediction_stats : {e}")
        return None


@bot.hybrid_command(name="predictionstatsglobal", description="Affiche les statistiques des prédictions des utilisateurs pour ce mois-ci")
@commands.is_owner()
async def predictionstatsglobal(ctx):
    try:
        # Récupérer les statistiques des prédictions
        stats = get_prediction_stats()

        if not stats:
            await ctx.send("Il n'y a pas de données de prédiction disponibles pour le moment.")
            return

        # Préparer le message à envoyer
        message = f"**Statistiques des prédictions**\n\n"

        for user_id, stats_data in stats.items():
            user = await bot.fetch_user(user_id)  # Récupérer l'utilisateur avec son ID
            message += f"**{user.name}** :\n"
            message += f"  ✔️ Prédictions correctes : {stats_data['good']}\n"
            message += f"  ❌ Prédictions incorrectes : {stats_data['bad']}\n"
            message += f"  📊 Total des prédictions : {stats_data['total']}\n"
            message += f"  💯 Pourcentage de bonnes prédictions : {stats_data['percentage']:.2f}%\n\n"

        # Envoyer le message
        await split_and_send(ctx, message)

    except Exception as e:
        print(f"Erreur dans la commande predictionstats : {e}")
        await ctx.send("Une erreur est survenue lors de la récupération des statistiques.")



@bot.hybrid_command(name="predictionstats", description="Affiche les statistiques des prédictions des utilisateurs pour ce mois-ci")
async def predictionstats(ctx):
    try:
        # Récupérer les statistiques des prédictions
        stats = get_prediction_stats()

        if not stats:
            await ctx.send("Il n'y a pas de données de prédiction disponibles pour le moment.")
            return

        # Préparer le message à envoyer
        message = f"**Statistiques des prédictions**\n\n"

        user_id = ctx.author.id  # Récupérer l'ID de l'utilisateur qui a appelé la commande

        if user_id in stats:
            stats_data = stats[user_id]
            message += f"**{ctx.author.name}** :\n"
            message += f"  ✔️ Prédictions correctes : {stats_data['good']}\n"
            message += f"  ❌ Prédictions incorrectes : {stats_data['bad']}\n"
            message += f"  📊 Total des prédictions : {stats_data['total']}\n"
            message += f"  💯 Pourcentage de bonnes prédictions : {stats_data['percentage']:.2f}%\n\n"
        else:
            message = "Vous n'avez pas encore de statistiques disponibles."

        # Envoyer le message
        await ctx.send(message)

    except Exception as e:
        print(f"Erreur dans la commande predictionstats : {e}")
        await ctx.send("Une erreur est survenue lors de la récupération des statistiques.")




async def main():
    await bot.load_extension("inscription")
    await bot.start(token)

asyncio.run(main())
