from redbot.core import checks, Config
from redbot.core.i18n import Translator, cog_i18n
import discord
from redbot.core import commands
from redbot.core.utils import mod
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
import asyncio
import datetime
from .wraith import Wraith

class Apex(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.api = Wraith(bot)


    @checks.mod()
    @commands.command()
    async def setapexkey(self, ctx, *, apikey):
        """Set your Apex API key for that cog to work.
        Note that it is safer to use this command in DM."""
        await self.bot.db.api_tokens.set_raw("apex", value={'api_key': apikey})
        await ctx.send("Done")

    @commands.command()
    async def apex(self, ctx, *, username):
        res = await self.api.get_infos(username)
        ls = []
        for i in res:
            emb = discord.Embed(title=i['legend'])
            emb.set_thumbnail(url=i['icon_url'])
            for j in i['stats']:
                emb.add_field(name=j['name'], value=j['value'], inline=False)
            ls.append(emb)
        await menu(ctx, ls, DEFAULT_CONTROLS)