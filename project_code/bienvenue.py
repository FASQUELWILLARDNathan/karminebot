import discord
from discord.ext import commands

class WelcomeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        welcome_message = """
🎮 **Bienvenue dans le salon de la Karmine Corp !** 🎮

Ce bot est ici pour enrichir votre expérience avec des informations à jour et des notifications à chaque match dans lequel vous pourrez voter sur la victoire ou la défaite de Karmine Corp ! (bien sûr, cliquez sur le bouton victoire)

Voici ce que vous **DEVEZ**/pouvez faire avec le bot :

1. **`/setchannel`** (Administrateur uniquement)  
   Définissez le channel où le bot enverra les notifications de matchs.  
   Exemple : `/setchannel #nom-du-salon`  
   ⚠️ Cette commande nécessite les permissions d'administrateur sur le serveur.

2. **`/predictionstats`**  
   Affiche vos **statistiques personnelles de prédiction** !  
   📊 Voir vos **prédictions correctes**, **incorrectes** et votre **pourcentage de réussite**.

3. **`/weekmatches` / `/monthmatches`**  
   Affiche les **matchs à venir de la Karmine Corp** pour la semaine ou le mois courant !  
   🏅 Suivez les matchs de votre **équipe préférée** et soyez prêts à prédire !

4. **`/stats` / `/yearstats`**  
   Affiche les **statistiques de la Karmine Corp** depuis sa création ou de cette année !  
   🌍 Gardez un œil sur les **performances** de votre équipe favorite tout au long de son parcours.
"""
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    await channel.send(welcome_message)
                    print(f"Message de bienvenue envoyé dans {guild.name} ({channel.name})")
                except Exception as e:
                    print(f"Erreur lors de l'envoi du message dans {guild.name} ({channel.name}): {e}")
                break
        else:
            print(f"Aucun canal dispo pour envoyer message dans {guild.name}.")

async def setup(bot):
    await bot.add_cog(WelcomeCog(bot))