from redbot.core import checks, Config
from redbot.core.i18n import Translator, cog_i18n
import discord
from redbot import version_info, VersionInfo
from redbot.core import commands
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS, start_adding_reactions
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
        if version_info >= VersionInfo.from_str("3.2.0"):
            key = await ctx.bot.get_shared_api_tokens("league")
        else:
            key = await ctx.bot.db.api_tokens.get_raw("league", default=None)
        try:
            res = True if key["api_key"] else False
        except:
            res = False
        if not res and ctx.invoked_with in dir(ctx.bot.get_cog('League')):
            raise commands.UserFeedbackCheckFailure(message="You need to set the API key using `[p]setapikey <api_key>` first !")
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
        if version_info >= VersionInfo.from_str("3.2.0"):
            key = await ctx.bot.set_shared_api_tokens("league", api_key=apikey)
        else:
            await self.bot.db.api_tokens.set_raw("league", value={'api_key': apikey})
        await ctx.send("Done")

    @commands.command()
    @apikeyset()
    async def elo(self, ctx, region, *, summoner):
        """Show summoner ranking"""
        ##try:
        region = region.lower()
        res = await self.stats.get_elo(region, summoner)
        if type(res) == list:
            await ctx.send(summoner + ": " + "\n".join(res))
        else:
            await ctx.send(summoner + ": " + res)
        return
        ##except:
        ##    await ctx.send(_("This summoner doesn't exist in that region."))

    @commands.command()
    @apikeyset()
    async def masteries(self, ctx, region, *, summoner):
        """Show top masteries champions of the summoner."""
        ##try:
        region = region.lower()
        elo = await self.stats.get_elo(region, summoner)
        if not elo:
            return await ctx.send("Unknown region or summoner.\nList of league of legends regions:" + '\n'.join(self.stats.regions.keys()))
        emb = discord.Embed(title=summoner, description="\n".join(elo)) if type(elo) is list else discord.Embed(title=summoner, description="\n" + elo)
        emb.add_field(name=_("Total mastery points: "), value=await self.stats.mastery_score(region, summoner), inline=True)
        champs = await self.stats.top_champions_masteries(region, summoner)
        await ctx.send(embed=emb)
        emb = discord.Embed()
        tmp = 0
        emblist = []
        for i in champs:
            champname = await self.stats.get_champion_name(str(i["championId"]))
            pic = await self.stats.get_champion_pic(champname)
            print(pic)
            mastery = i["championLevel"]
            points = i["championPoints"]
            coffre = i["chestGranted"]
            cdesc = await self.stats.get_champion_desc(champname)
            emb = discord.Embed(title=champname, description=cdesc)
            emb.set_thumbnail(url=pic)
            emb.add_field(name=f"Mastery {mastery}", value=f"{points} points !", inline=True)
            if coffre:
                emb.set_footer(text="Chest earned: Yes")
            else:
                emb.set_footer(text="Chest earned: No")
            emblist.append(emb)
            tmp += 1
            if tmp == 10:
                break
            await asyncio.sleep(0.5)
        await menu(ctx, emblist, DEFAULT_CONTROLS)
        ##except:
        ##    await ctx.send(_("Unknown summoner"))

    @commands.command()
    @apikeyset()
    async def game(self, ctx, region, *, summoner):
        """Show information about current game of summoner"""
        try:
            region = region.lower()
            infos = await self.stats.game_info(region, summoner)
            if infos is False:
                await ctx.send(_("This summoner isn't currently ingame or the region is invalid."))
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
        msg = await ctx.send(f"Loading last {count} games of {summoner} ...")
        region = region.lower()
        async with ctx.typing():
            histo = await self.stats.get_history(count, region, summoner)
            if not histo:
                return await ctx.send("Unknown region or summoner.\nList of league of legends regions:" + '\n'.join(self.stats.regions.keys()))
            emb = discord.Embed()
            emblist = []
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
                emblist.append(emb)
                emb = discord.Embed()
        start_adding_reactions(msg, DEFAULT_CONTROLS.keys())#, self.bot.loop)
        await menu(ctx=ctx, pages=emblist, controls=DEFAULT_CONTROLS, message=msg, page=0)
        await msg.edit(content="")

            
        
