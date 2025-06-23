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
DB_PASSWORD = settings.DB_PASSWORD
dbname = settings.dbname
user = settings.user
host = settings.host

class PredictionView(discord.ui.View):
    def __init__(self, match_id, game):
        super().__init__(timeout=None)
        self.match_id = match_id
        self.game = game

    @discord.ui.button(label="On gagne", style=discord.ButtonStyle.success)
    async def gagne(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.enregistrer_prediction(interaction, choix=1)

    @discord.ui.button(label="On perd", style=discord.ButtonStyle.danger)
    async def perd(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.enregistrer_prediction(interaction, choix=2)

    async def enregistrer_prediction(self, interaction, choix):
        try:
            with psycopg.connect(f"dbname={dbname} user={user} password={DB_PASSWORD} host={host}") as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO prediction (user_id, match_id, choix, jeu)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (user_id, match_id) DO UPDATE
                        SET choix = EXCLUDED.choix
                    """, (interaction.user.id, self.match_id, choix, self.game))
            await interaction.response.send_message("✅ Prédiction enregistrée !", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erreur : {e}", ephemeral=True)