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
from .predictionview import PredictionView

DB_PASSWORD = settings.DB_PASSWORD
dbname = settings.dbname
user = settings.user
host = settings.host

def start_vcl_task(bot, DB_PASSWORD):
    @tasks.loop(minutes=1)
    async def check_upcoming_matches_vcl():
        now = datetime.now()
        window_start = now + timedelta(minutes=59)
        window_end = now + timedelta(minutes=60)

        query = """
            SELECT objectname, tournament, date, game, match2opponents
            FROM matches
            WHERE match2opponents @> '[{"teamtemplate": {"name": "KC Blue Stars"}}]'
            AND date BETWEEN %s AND %s
            AND winner = ''
            ORDER BY date ASC
        """

        try:
            with psycopg.connect(f"dbname={dbname} user={user} password={DB_PASSWORD} host={host}") as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (window_start, window_end))
                    matches = cur.fetchall()

                    for match in matches:
                        objectname, tournament, date, game, match2opponents = match

                        # Ajouter 2 heures à la date extraite
                        date = date + timedelta(hours=2)

                        # Extraire les noms d'équipes directement depuis le JSON
                        teams = [team["teamtemplate"]["name"] for team in match2opponents]
                        ennemy_team = [team for team in teams if team != "KC Blue Stars"][0]

                        # Envoi
                        cur.execute("SELECT guild_id, notifications_channel_id FROM guild_configs WHERE is_active = TRUE")
                        guild_channels = cur.fetchall()

                        for guild_id, channel_id in guild_channels:
                            channel = bot.get_channel(channel_id)
                            if channel:
                                try:
                                    view = PredictionView(match_id=objectname, game=game)
                                    await channel.send(
                                        f"🔔 **Match à venir ({game})**\n"
                                        f"🏆 Tournoi : {tournament}\n"
                                        f"🕒 Heure : {date.strftime('%H:%M')}\n"
                                        f"🆚 Opposant : {ennemy_team}\n\n"
                                        f"Faites votre prédiction !",
                                        view=view)
                                except discord.Forbidden:
                                        print(f"Pas la permission d'envoyer dans le channel {channel_id}. Marquage inactif dans la BDD.")
                                        # Marquer le channel comme inactif
                                        with psycopg.connect(f"dbname={dbname} user={user} password={DB_PASSWORD} host={host}") as conn2:
                                            with conn2.cursor() as cur2:
                                                cur2.execute("UPDATE guild_configs SET is_active = FALSE WHERE notifications_channel_id = %s", (channel_id,))
                                                conn2.commit()
                                except Exception as send_err:
                                    print(f"Erreur lors de l'envoi du message dans le channel {channel_id}: {send_err}")
                            else:
                                print(f"Channel ID {channel_id} non trouvé ou pas accessible")

        except Exception as e:
            print(f"Erreur dans check_upcoming_matches : {e}")

    if not check_upcoming_matches_vcl.is_running():
        check_upcoming_matches_vcl.start()