from redbot.core import checks, Config
import discord
from redbot.core import commands
import asyncio
import datetime
from redbot.core.i18n import Translator, cog_i18n

_ = Translator("Anarchy", __file__)

def anarcheck():
    async def predicate(ctx):
        if ctx.guild.id == 133049272517001216:
            return True ## Let's make an exception for #testing ? :)
        perm = ctx.me.guild_permissions
        if perm.kick_members:
            return True
        else:
            await ctx.send(_("You need to give me permissions to kick members before using this cog."))
            return False
    return commands.check(predicate)

def can_vote():
    async def predicate(ctx):
        ts_lastvote = await ctx.cog.config.member(ctx.author).last_vote()
        if ts_lastvote is None:
            now = datetime.datetime.now()
            await ctx.cog.config.member(ctx.author).last_vote.set(datetime.datetime.timestamp(now))
            return True
        lastvote = datetime.datetime.fromtimestamp(ts_lastvote)
        now = datetime.datetime.now()
        delt = now - lastvote
        if delt.days >= 1:
            await ctx.cog.config.member(ctx.author).last_vote.set(datetime.datetime.timestamp(datetime.datetime.now()))
            return True
        else:
            await ctx.send(_("You can't vote again yet ! Please wait {}.").format(ctx.cog.strfdelta(delt)))
            return False
    return commands.check(predicate)

@cog_i18n(_)
class Anarchy(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=971109711499104121)
        default_member = {
            "votes": 0,
            "messages": 0,
            "last_vote": None,
            "cooldown": 0
        }
        default_guild = {
            "cooldown": 2,
            "threshold": 100 #Note that i have no idea on how much i should put by default, so better modify that depending on your needs
        }
        default_channel = {
            "ignored": False
        }
        self.config.register_member(**default_member)
        self.config.register_guild(**default_guild)
        self.config.register_channel(**default_channel)

    def strfdelta(self, tdelta):
        hours, rem = divmod(tdelta.seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        return f"{hours} hours, {minutes} minutes and {seconds} seconds"

    async def get_power(self, member):
        ### 3 next lines taken from Aikaterna's joinleave cog
        join_date = datetime.datetime.strptime(str(member.created_at), "%Y-%m-%d %H:%M:%S.%f")
        now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        since_join = now - join_date
        days = since_join.days
        months = days%30
        msgs = await self.config.member(member).messages()
        ratio = msgs /1000
        if months == 0:
            return 0.5 * ratio
        elif months <= 2:
            return 1 * ratio
        elif months <= 6:
            return 2 * ratio
        else:
            return 3 * ratio

    @commands.group()
    @anarcheck()
    async def anarchy(self, ctx):
        """Commands for anarchy cog."""
        pass

    @anarchy.group(name="set")
    @checks.mod()
    @anarcheck()
    async def anarchyset(self, ctx):
        """Configuration command for the anarchy cog."""
        pass

    @anarchyset.command(name="threshold")
    @checks.mod()
    @anarcheck()
    async def set_threshold(self, ctx, threshold : int):
        """Modify the threshold needed to get mod role."""
        await self.config.guild(ctx.guild).modrole.set(threshold)
        await ctx.send(_("Server threshold successfully set to {} points.").format(threshold))

    @anarchyset.command(name="cooldown")
    @checks.mod()
    @anarcheck()
    async def set_cooldown(self, ctx, cooldown : int = 1):
        """Modify the cooldown between 2 counted messages.
        This settings is meant to not allow spammers to get any advantage.
        Default to 2 messages."""
        await self.config.guild(ctx.guild).cooldown.set(cooldown)
        await ctx.send(_("Cooldown successfully set to {} seconds.").format(cooldown))

    @anarchyset.command(name="ignore")
    @checks.mod()
    @anarcheck()
    async def ignore_channel(self, ctx, channels : commands.Greedy[discord.TextChannel]):
        """Make the cog ignore channels.
        Messages won't be counted in those channels."""
        for i in channels:
            await self.config.channel(i).ignore.set(True)
        await ctx.send(_("Channels {} successfully ignored.").format(" ".join([x.mention for x in channels])))

    @anarchy.command(name="vote")
    @anarcheck()
    @can_vote()
    async def anarchy_vote(self, ctx, member : discord.Member):
        """Vote for a member !"""
        if ctx.author == member:
            return await ctx.send(_("You can't vote for yourself ..."))
        cur = await self.config.member(member).votes()
        amount = await self.get_power(ctx.author)
        await self.config.member(member).votes.set(cur+amount)
        await ctx.send(_("You have voted for {} !").format(member.mention))

    @anarchy.command(name="kick")
    @anarcheck()
    @commands.cooldown(1, 60, commands.BucketType.member)
    async def anarchy_kick(self, ctx, member : discord.Member, *, reason : str = "Anarchy abuse"):
        """Kicks another user.
        You can only kick another user if you have more votes than him.
        Beware to not abuse this power !"""
        authorp = await self.config.member(ctx.author).votes()
        threshold = await self.config.guild(ctx.guild).threshold()
        if authorp < threshold:
            return await ctx.send(_("You don't have enough votes yet !"))
        userp = await self.config.member(member).votes()
        if userp >= authorp:
            return await ctx.send(_("You can't kick someone with more or same number of votes than you !"))
        else:
            await ctx.send(_("You have kicked {} !").format(member.mention))
            await member.kick(reason=reason)

    @anarchy.command(name="profile")
    @anarcheck()
    async def anarchy_profile(self, ctx, member : discord.Member = None):
        """Show how much votes you - or someone else - have."""
        if member is None:
            member = ctx.author
        votes = await self.config.member(member).votes()
        return await ctx.send(_("```You currently have {} votes !```").format(votes))

    @commands.Cog.listener(name="on_message")
    async def on_message(self, message):
        if await self.config.channel(message.channel).ignored():
            return
        if message.author.bot:
            return
        cd = int(await self.config.member(message.author).cooldown())
        if cd != 0:
            await self.config.member(message.author).cooldown.set(str(cd - 1))
        else:
            await self.config.member(message.author).cooldown.set(await self.config.guild(message.guild).cooldown())
            new = (await self.config.member(message.author).messages()) +1
            await self.config.member(message.author).messages.set(new)
