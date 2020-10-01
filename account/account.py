from redbot.core import checks, Config
from redbot.core.i18n import Translator, cog_i18n
import discord
from redbot.core import commands
from redbot.core.utils import mod
import asyncio
import datetime

class Account(commands.Cog):
    """The Account Cog"""

    def __init__(self, bot):
        self.bot = bot
        default_member = {
            "Age": None,
            "Site": None,
            "About": None,
            "Gender": None,
            "Job": None,
            "Email": None,
            "Other": None
        }
        default_guild = {
            "db": []
        }
        self.config = Config.get_conf(self, identifier=42)
        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)
    
    @commands.command(name="signup")
    @commands.guild_only()
    async def _reg(self, ctx):
        """Sign up to get your own account today!"""

        server = ctx.guild
        user = ctx.author
        db = await self.config.guild(server).db()
        if user.id not in db:
            db.append(user.id)
            await self.config.guild(server).db.set(db)
            data = discord.Embed(colour=user.colour)
            data.add_field(name="Congrats!:sparkles:", value="You have officially created your account for **{}**, {}.".format(server.name, user.mention))
            await ctx.send(embed=data)
        else: 
            data = discord.Embed(colour=user.colour)
            data.add_field(name="Error:warning:",value="Opps, it seems like you already have an account, {}.".format(user.mention))
            await ctx.send(embed=data)
        
    
    @commands.command(name="account")
    @commands.guild_only()
    async def _acc(self, ctx, user : discord.Member=None):
        """Your/Others Account"""
                    
        server = ctx.guild
        db = await self.config.guild(server).db()
        user = user if user else ctx.author
        userdata = await self.config.member(user).all()
        
        data = discord.Embed(description="{}".format(server), colour=user.colour)
        fields = [data.add_field(name=k, value=v) for k,v in userdata.items() if v]
        
        if user.avatar_url:
            name = str(user)
            name = " ~ ".join((name, user.nick)) if user.nick else name
            data.set_author(name=name, url=user.avatar_url)
            data.set_thumbnail(url=user.avatar_url)
        else:
            data.set_author(name=user.name)
        
        if len(fields) != 0:
            await ctx.send(embed=data)
        else:
            data = discord.Embed(colour=user.colour)
            data.add_field(name="Error:warning:",value="{} doesn't have an account at the moment, sorry.".format(user.mention))
            await ctx.send(embed=data)

    @commands.group(name="update")
    @commands.guild_only()
    async def update(self, ctx):
        """Update your TPC"""
        pass

    @update.command(pass_context=True)
    @commands.guild_only()
    async def about(self, ctx, *, about):
        """Tell us about yourself"""
        
        server = ctx.guild
        user = ctx.author
        prefix = ctx.prefix
        db = await self.config.guild(server).db()
        
        if user.id not in db:
            data = discord.Embed(colour=user.colour)
            data.add_field(name="Error:warning:",value="Sadly, this feature is only available for people who had registered for an account. \n\nYou can register for a account today for free. All you have to do is say `{}signup` and you'll be all set.".format(prefix))
            await ctx.send(embed=data)
        else:
            await self.config.member(user).About.set(about)
            data = discord.Embed(colour=user.colour)
            data.add_field(name="Congrats!:sparkles:",value="You have updated your About Me to {}".format(about))
            await ctx.send(embed=data)

    @update.command(pass_context=True)
    @commands.guild_only()
    async def website(self, ctx, *, site):
        """Do you have a website?"""
        
        server = ctx.guild
        user = ctx.message.author
        prefix = ctx.prefix
        db = await self.config.guild(server).db()

        if user.id not in db:
            data = discord.Embed(colour=user.colour)
            data.add_field(name="Error:warning:",value="Sadly, this feature is only available for people who had registered for an account. \n\nYou can register for a account today for free. All you have to do is say `{}signup` and you'll be all set.".format(prefix))
            await ctx.send(embed=data)
        else:
            await self.config.member(user).Site.set(site)
            data = discord.Embed(colour=user.colour)
            data.add_field(name="Congrats!:sparkles:",value="You have set your Website to {}".format(site))
            await ctx.send(embed=data)

    @update.command(pass_context=True)
    @commands.guild_only()
    async def age(self, ctx, *, age):
        """How old are you?"""
        
        server = ctx.guild
        user = ctx.author
        prefix = ctx.prefix
        db = await self.config.guild(server).db()

        if user.id not in db:
            data = discord.Embed(colour=user.colour)
            data.add_field(name="Error:warning:",value="Sadly, this feature is only available for people who had registered for an account. \n\nYou can register for a account today for free. All you have to do is say `{}signup` and you'll be all set.".format(prefix))
            await ctx.send(embed=data)
        else:
            await self.config.member(user).Age.set(age)
            data = discord.Embed(colour=user.colour)
            data.add_field(name="Congrats!:sparkles:",value="You have set your age to {}".format(age))
            await ctx.send(embed=data)

    @update.command(pass_context=True)
    @commands.guild_only()
    async def job(self, ctx, *, job):
        """Do you have a job?"""
        
        server = ctx.guild
        user = ctx.author
        prefix = ctx.prefix
        db = await self.config.guild(server).db()

        if user.id not in db:
            data = discord.Embed(colour=user.colour)
            data.add_field(name="Error:warning:",value="Sadly, this feature is only available for people who had registered for an account. \n\nYou can register for a account today for free. All you have to do is say `{}signup` and you'll be all set.".format(prefix))
            await ctx.send(embed=data)
        else:
            await self.config.member(user).Job.set(job)
            data = discord.Embed(colour=user.colour)
            data.add_field(name="Congrats!:sparkles:",value="You have set your Job to {}".format(job))
            await ctx.send(embed=data)
    
    @update.command(pass_context=True)
    @commands.guild_only()
    async def gender(self, ctx, *, gender):
        """What's your gender?"""

        server = ctx.guild
        user = ctx.author
        prefix = ctx.prefix
        db = await self.config.guild(server).db()

        if user.id not in db:
            data = discord.Embed(colour=user.colour)
            data.add_field(name="Error:warning:",value="Sadly, this feature is only available for people who had registered for an account. \n\nYou can register for a account today for free. All you have to do is say `{}signup` and you'll be all set.".format(prefix))
            await ctx.send(embed=data)
        else:
            await self.config.member(user).Gender.set(gender)
            data = discord.Embed(colour=user.colour)
            data.add_field(name="Congrats!:sparkles:",value="You have set your Gender to {}".format(gender))
            await ctx.send(embed=data)
 
    @update.command(pass_context=True)
    @commands.guild_only()
    async def email(self, ctx, *, email):
        """What's your email address?"""

        
        server = ctx.guild
        user = ctx.author
        prefix = ctx.prefix
        db = await self.config.guild(server).db()

        if user.id not in db:
            data = discord.Embed(colour=user.colour)
            data.add_field(name="Error:warning:",value="Sadly, this feature is only available for people who had registered for an account. \n\nYou can register for a account today for free. All you have to do is say `{}signup` and you'll be all set.".format(prefix))
            await ctx.send(embed=data)
        else:
            await self.config.member(user).Email.set(email)
            data = discord.Embed(colour=user.colour)
            data.add_field(name="Congrats!:sparkles:",value="You have set your Email to {}".format(email))
            await ctx.send(embed=data)

    @update.command(pass_context=True)
    @commands.guild_only()
    async def other(self, ctx, *, other):
        """Incase you want to add anything else..."""
        
        server = ctx.guild
        user = ctx.author
        prefix = ctx.prefix
        db = await self.config.guild(server).db()

        if user.id not in db:
            data = discord.Embed(colour=user.colour)
            data.add_field(name="Error:warning:",value="Sadly, this feature is only available for people who had registered for an account. \n\nYou can register for a account today for free. All you have to do is say `{}signup` and you'll be all set.".format(prefix))
            await ctx.send(embed=data)
        else:
            await self.config.member(user).Other.set(other)
            data = discord.Embed(colour=user.colour)
            data.add_field(name="Congrats!:sparkles:",value="You have set your Other to {}".format(other))
            await ctx.send(embed=data)
