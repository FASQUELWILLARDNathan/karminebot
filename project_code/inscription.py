import os
import discord
from discord.ext import commands
from discord import app_commands, Interaction
import psycopg
import settings

DB_PASSWORD = settings.DB_PASSWORD
dbname = settings.dbname
user = settings.user
host = settings.host

class NotificationConfig(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setchannel", description="Définir le channel de notifications")
    @app_commands.checks.has_permissions(administrator=True)
    async def setchannel(self, interaction: Interaction, channel: discord.TextChannel):
        guild_id = interaction.guild.id
        channel_id = channel.id

        try:
            with psycopg.connect(f"dbname={dbname} user={user} password={DB_PASSWORD} host={host}") as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO guild_configs (guild_id, notifications_channel_id)
                        VALUES (%s, %s)
                        ON CONFLICT (guild_id) DO UPDATE SET notifications_channel_id = EXCLUDED.notifications_channel_id
                    """, (guild_id, channel_id))
            await interaction.response.send_message(
                f"✅ Le channel de notifications est défini sur {channel.mention}",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Erreur lors de l'enregistrement : {e}",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(NotificationConfig(bot))
