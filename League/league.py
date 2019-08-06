from redbot.core import checks, Config
from redbot.core.i18n import Translator, cog_i18n
import discord
from redbot.core import commands
from redbot.core.utils import mod
import asyncio
import datetime
import aiohttp
from .neeko import Neeko

_ = Translator("League", __file__)

## New season makes Riot Games have to update their API to include positionnal ranking and stuff
## So the cog is maybe broken atm, gonna have to fix that, maybe waiting for positionnal ranking to be released on EUW to test the cog with that functionality
## NB: i should also add a setting to switch region the cog gets infos, just had the idea while typing this aha

def apikeyset():
    async def predicate(ctx):
        key = await ctx.bot.db.api_tokens.get_raw("league", default=False)
        res = True if key["api_key"] else False
        if not res and ctx.invoked_with in dir(ctx.bot.get_cog('League')):
            await ctx.send("You need to set the API key using `[p]setapikey <api_key>` first !")
        return res
    return commands.check(predicate)

class League(commands.Cog):
    """League of legend cog"""

    def __init__(self, bot):
        self.bot = bot
        self.stats = Neeko(bot)

    @checks.mod()
    @commands.command()
    async def setapikey(self, ctx, *, apikey):
        """Set your Riot API key for that cog to work.
        Note that it is safer to use this command in DM."""
        await self.bot.db.api_tokens.set_raw("league", value={'api_key': apikey})
        await ctx.send("Done")

    @commands.command()
    @apikeyset()
    async def elo(self, ctx, region, *, summoner):
        """Show summoner ranking"""
        try:
            res = await self.stats.get_elo(region, summoner)
            await ctx.send(summoner + ": " + res)
            return
        except:
            await ctx.send(_("This summoner doesn't exist in that region."))

    @commands.command()
    @apikeyset()
    async def masteries(self, ctx, region, *, summoner):
        """Show top masteries champions of the summoner."""
        try:
            elo = await self.stats.get_elo(region, summoner)
            emb = discord.Embed(title=summoner, description=elo)
            emb.add_field(name=_("Total mastery points: "), value=await self.stats.mastery_score(region, summoner), inline=True)
            champs = await self.stats.top_champions_masteries(region, summoner)
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
                    emb.add_field(name=_("Chest earned"), value=_("Yes"), inline=True)
                else:
                    emb.add_field(name=_("Chest earned"), value=_("No"), inline=True)
                tmp += 1
                if tmp == 3:
                    await ctx.send(embed=emb)
                    emb = discord.Embed()
                if tmp >= 6:
                    break
                await asyncio.sleep(0.5)
            await ctx.send(embed=emb)
        except:
            await ctx.send(_("Unknown summoner"))

    @commands.command()
    @apikeyset()
    async def game(self, ctx, region, *, summoner):
        """Show information about current game of summoner"""
        try:
            infos = await self.stats.game_info(region, summoner)
            if infos is False:
                await ctx.send(_("This summoner isn't currently ingame."))
                return
            await ctx.send(infos["gamemode"])
            bans1 = discord.Embed(title=_("First team bans"))
            bans2 = discord.Embed(title=_("Second team bans"))
            team1 = discord.Embed(title=_("First team ranks"))
            team2 = discord.Embed(title=_("Second team ranks"))
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
        except:
            await ctx.send(_("This summoner isn't currently ingame or is unknown."))

    @commands.command()
    @apikeyset()
    async def history(self, ctx, region, summoner, count : int = 5):
        """Shows X last game of a summoner (default: 5).
        NB: if your summoner name contains spaces, use "" (eg: "My summoner name")"""
        async with ctx.typing():
            histo = await self.stats.get_history(count, region, summoner)
            if not histo:
                return await ctx.send("```Unknown region or summoner.\nList of league of legends regions:\n" + '\n'.join(self.stats.regions.keys()) + "```")
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
            
            
                
        
