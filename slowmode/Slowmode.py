from redbot.core import checks, Config
import discord
from discord.ext import commands
from redbot.core.utils import mod
import asyncio
import datetime
import time

class Slowmode:

    def __init__(self, bot):
        self.bot = bot
        self.data = Config.get_conf(self, identifier=42)
        default_channel = {
            "slow": None,
            "vote": False,
            "imageonly": False
        }
        default_member = {
            "lastmsg": None,
            "msgdel": 0
        }
        self.data.register_member(**default_member)
        self.data.register_channel(**default_channel)


    @commands.command()
    @checks.admin_or_permissions(kick_members=True)
    async def slowmode(self, ctx, delay: str):
        if await mod.is_mod_or_superior(self.bot, obj=ctx.author):
            await ctx.send("Vous n'avez pas l'autorisation de faire sa !")
            return
        elif not delay.isdigit():
            await ctx.send("Nombre invalide")
            return
        await self.data.channel(ctx.channel).slow.set(int(delay))
        await ctx.send("Ce channel a maintenant un slow mode. :snail: ({} seconds).".format(delay))

    @commands.command()
    @checks.admin_or_permissions(kick_members=True)
    async def slowoff(self, ctx):
        if await mod.is_mod_or_superior(self.bot, obj=ctx.author):
            await ctx.send("Vous n'avez pas l'autorisation de faire sa !")
            return
        await self.data.channel(ctx.channel).slow.set(None)
        await ctx.send("Ce channel n'est plus en slow mode. :snail:")

    async def timer(self, user, channel, duration):
        while duration != 0:
            await asyncio.sleep(1)
            duration -= 1
        if duration == 0:
            await self.umute(user, channel)

    @commands.command()
    @checks.admin_or_permissions(kick_members=True)
    async def vote(self, ctx):
        if await mod.is_mod_or_superior(self.bot, obj=ctx.author):
            await ctx.send("Vous n'avez pas l'autorisation de faire sa !")
            return
        if await self.data.channel(ctx.channel).vote():
            await self.data.channel(ctx.channel).vote.set(False)
            await ctx.send("Vote mode désactivé.")
        elif not await self.data.channel(ctx.channel).vote():
            await self.data.channel(ctx.channel).vote.set(True)
            await ctx.send("Vote mode activé.")
        else:
            await ctx.send("Roboto tout cassé.")

    @commands.command()
    @checks.admin_or_permissions(kick_members=True)
    async def imageonly(self, ctx):
        if await mod.is_mod_or_superior(self.bot, obj=ctx.author):
            await ctx.send("Vous n'avez pas l'autorisation de faire sa !")
            return
        if await self.data.channel(ctx.channel).imageonly():
            await self.data.channel(ctx.channel).imageonly.set(False)
            await ctx.send("Image only désactivé.")
        elif not await self.data.channel(ctx.channel).imageonly():
            await self.data.channel(ctx.channel).imageonly.set(True)
            await ctx.send("Image only activé.")
        else:
            await ctx.send("Roboto tout cassé.")

    async def mutee(self, user, channel):
        await channel.set_permissions(user, send_messages = False, reason="Slowmode spamming")

    async def umute(self, user, channel):
        await channel.set_permissions(user, send_messages = True, reason="Unmuted slowmode spam")
        self.temp.cancel()
    
    async def limiter(self, message):
        channel = message.channel
        author = message.author
        if self.can_bypass(author):
            return
        else:
            if await self.data.channel(channel).vote():
                await message.add_reaction('\U00002705')
                await message.add_reaction('\U0000274e')
            if await self.data.channel(channel).imageonly():
                if len(message.attachments) == 0:
                    await message.delete()
            if await self.data.channel(channel).slow() is None or await self.data.channel(channel).slow() == 0:
                return
            else:
                if await self.data.member(author).lastmsg() is None:
                    await self.data.member(author).lastmsg.set(time.time())
                    await self.data.member(author).msgdel.set(0)
                elif (time.time() - await self.data.member(author).lastmsg() <= await self.data.channel(channel).slow()):
                    await message.delete()
                    await self.data.member(author).lastmsg.set(time.time())
                    await self.data.member(author).msgdel.set(await self.data.member(author).msgdel() +1)
                else:
                    await self.data.member(author).lastmsg.set(time.time())
                if await self.data.member(author).msgdel() >= 10:
                    self.temp = self.bot.loop.create_task(self.timer(author, channel, 300))
                    await self.mutee(author, channel)
                    await self.data.member(author).msgdel.set(0)

    def can_bypass(self, user):
        try:
            if user.id == "99116871994859520" or self.bot.is_owner(user)
                return True
            settings = self.bot.db.guild(user.guild)
            idmod = await settings.mod_role()
            modrole = discord.utils.get(user.guild.roles, id=idmod)
            if user.top_role >= modrole:
                return True
            return False
        except:
            return False

                       
