from redbot.core import checks, Config
import discord
from redbot.core import commands
from redbot.core.utils import mod
import asyncio
import datetime
import aiohttp
from .neeko import Neeko

class League(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.stats = Neeko("PUT YOUR API KEY HERE")

    @commands.command()
    async def elo(self, ctx, *, summoner):
        try:
            res = await self.stats.get_elo(summoner)
            await ctx.send(summoner + ": " + res)
            return
        except:
            await ctx.send("Le summoner que vous avez demandé n'existe pas.")

    @commands.command()
    async def masteries(self, ctx, *, summoner):
        try:
            elo = await self.stats.get_elo(summoner)
            emb = discord.Embed(title=summoner, description=elo)
            emb.add_field(name="Score de maitrises totales: ", value=await self.stats.mastery_score(summoner), inline=True)
            champs = await self.stats.top_champions_masteries(summoner)
            await ctx.send(embed=emb)
            emb = discord.Embed()
            tmp = 0
            for i in champs:
                champname = await self.stats.get_champion_name(str(i["championId"]))
                mastery = i["championLevel"]
                points = i["championPoints"]
                coffre = i["chestGranted"]
                master = "Mastery {}: {} points".format(mastery, points)
                emb.add_field(name=champname, value=master, inline=True)
                if coffre:
                    emb.add_field(name="Coffre obtenu", value="Oui", inline=True)
                else:
                    emb.add_field(name="Coffre obtenu", value="Non", inline=True)
                tmp += 1
                if tmp == 3:
                    await ctx.send(embed=emb)
                    emb = discord.Embed()
                if tmp >= 6:
                    break
                await asyncio.sleep(0.5)
            await ctx.send(embed=emb)
        except:
            await ctx.send("Summoner inconnu")

    @commands.command()
    async def game(self, ctx, *, summoner):
        try:
            infos = await self.stats.game_info(summoner)
            if infos is False:
                await ctx.send("Ce summoner n'est actuellement pas in-game.")
                return
            await ctx.send(infos["gamemode"])
            bans1 = discord.Embed(title="Bans de l'équipe 1")
            bans2 = discord.Embed(title="Bans de l'équipe 2")
            team1 = discord.Embed(title="Elo de l'équipe 1")
            team2 = discord.Embed(title="Elo de l'équipe 2")
            for i, j in infos["team1"]["bans"].items():
                bans1.add_field(name=j, value=i, inline=True)

            await ctx.send(embed=bans1)

            for i, j in infos["team2"]["bans"].items():
                bans2.add_field(name=j, value=i, inline=True)

            await ctx.send(embed=bans2)

            for i, j in infos["team1"]["players"].items():
                team1.add_field(name=i, value=j, inline=True)

            await ctx.send(embed=team1)

            for i, j in infos["team2"]["players"].items():
                team2.add_field(name=i, value=j, inline=True)

            await ctx.send(embed=team2)
        except Exception as e:
            await ctx.send("Ce summoner n'est actuellement pas in-game ou inconnu.")

    @commands.command()
    async def history(self, ctx, summoner, count : int = 5):
        async with ctx.typing():
            histo = await self.stats.get_history(summoner)
            tmp = 0
            emb = discord.Embed()
            for i in histo:
                cur = histo[i]
                champ = cur["champ"]
                horo = cur["horo"]
                role = cur["role"]
                duree = cur["Durée"]
                mode = cur["Gamemode"]
                res = cur["resultat"]
                kda = cur["kda"]
                stats = cur["stats"]
                golds = cur["golds"]
                emb.add_field(name=champ, value=mode + " : " + res, inline=True)
                emb.add_field(name=role, value=duree, inline=False)
                emb.add_field(name=golds, value=horo, inline=False)
                emb.add_field(name=kda, value=stats, inline=True)
                await ctx.send(embed=emb)
                emb = discord.Embed()
                tmp += 1
                if tmp == count:
                    break
            
            
                
        
