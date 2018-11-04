# -*- coding: utf-8 -*-

from redbot.core import checks, Config
import discord
from redbot.core import commands
from redbot.core.utils import mod
from redbot.core.data_manager import cog_data_path
import asyncio
import datetime
from .userprofile import UserProfile
from PIL import Image, ImageDraw, ImageFont
from math import floor, ceil
import os
import urllib
import aiohttp
from random import randint

class Leveler(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.profiles = UserProfile()
        self.loop = self.bot.loop.create_task(self.start())
        self.restart = True


    __version__ = "1.0.0"
    __author__ = "Malarne#1418"
    __info__ = {
        "bot_version": "3.0.0rc2",
        "description": (
            "A leveler cog for Red V3\n",
            "Inspired by Stevy's v2 leveler cog\n",
            "Please consult the docs at ayrobot.netlify.com for setup informations.\n",
            "Thanks for using my cog !"
        ),
        "hidden": False,
        "install_msg": (
            "Thank you for installing this leveler !\n",
            "Please consult the docs at ayrobot.netlify.com for setup informations."
        ),
        "required_cogs": [],
        "requirements": ["pillow"],
        "short": "Leveler tool, better than MEE6",
        "tags": ["leveler", "pillow", "fun"]
    }


    def __unload(self):
        self.loop.cancel()


    async def start(self):
        await self.bot.wait_until_ready()
        while True:
            if not self.restart:
                guilds = self.bot.guilds
                for i in guilds:
                    profils = await self.profiles.data.all_members(i)
                    for j in profils.keys():
                        member = i.get_member(j)
                        if member is None:
                            member = namedtuple("Member", "id guild")
                            await self.config.member(member(j, i.id)).clear()
                        else:
                            await self.profiles.data.member(member).today.set(0)
                self.restart = True
            if datetime.date.today().strftime('%H:%M') in ["05:00", "05:01", "05:02", "05:03", "05:04", "05:05"]:
                self.restart = False
            await asyncio.sleep(30)

    @commands.command()
    @checks.is_owner()
    async def testreset(self, ctx):
        self.restart = False
        await ctx.send("Reset dans max 30 secondes", delete_after=30)

    async def makebar(self, prc):
        emp = "□"
        full = "■"
        res = ""
        temp = 40
        for i in range(ceil(prc/2.5)):
            res += full
            temp -= 1
        while temp != 0:
            res += emp
            temp -= 1
        return res

    @commands.command()
    async def profile(self, ctx, user : discord.Member = None):
        if user is None:
            user = ctx.author
        img = Image.new('RGBA', (800, 200))
        font = ImageFont.truetype("/home/admin/venv/arial.ttf", 32)
        draw = ImageDraw.Draw(img)
        usercolor = user.color.to_rgb()
        draw.ellipse([(-400, -100), (1200, 600)], fill=usercolor, outline=usercolor)
        draw.ellipse([(250, -50), (550, 250)], fill='white', outline='white')
        img_w, img_h = img.size
        async with aiohttp.ClientSession() as session:
            async with session.get(user.avatar_url_as(format="png", size=1024)) as f:
                rand = randint(0, 99999)
                path = cog_data_path(self)
                with open(f"{path}\\temp_{rand}.png", "wb") as r:
                    r.write(await f.content.read())
        avatar = Image.open(f"{path}\\temp_{rand}.png")
        avatar_size = 128, 128
        avatar.thumbnail(avatar_size)
        avatar_w, avatar_h = avatar.size
        offset = ((img_w - avatar_w) // 2, ((img_h - avatar_h) // 2) -30)
        img.paste(avatar, offset)
        if await self.profiles._is_registered(user):
            draw.rectangle([(50, 160), (750, 180)], fill=None, outline='black')
            xp = await self.profiles._get_exp(user)
            nxp = await self.profiles._get_level_exp(user)
            lvl = await self.profiles._get_level(user)
            if lvl != 1:
                minone = await self.profiles._get_xp_for_level(lvl -1)
            else:
                minone = 0
            lxp = xp - minone
            lnxp = nxp - minone
            prc = floor(xp / (nxp / 100))
            lprc = floor(lxp / (lnxp / 100))
            b_offset = 800 - (lprc*7)
            draw.rectangle([(50, 160), (800 - b_offset, 180)], fill='black', outline=None)
            draw.text((20, 20), f"Niveau: {lvl}", fill='black', font=font)
            sp = ""
            for _ in range(len(str(xp))+2):
                sp += " "
            draw.text((600, 10), f"XP: ({lprc}%)\n{lxp} / {lnxp} ", fill='black', font=font)
            draw.text((570, 90), f"{sp}Total:\n{xp} / {nxp} ", fill='black', font=font)
            roles = await self.profiles._get_guild_roles(ctx.guild)
            ln = lvl // 10
            if ln == 0:
                elo = "Nouveau"
            elif ln >= 7:
                ln = 7
                elo = roles[ln - 1]
            draw.text((20, 90), f"Elo: {elo}", fill='black', font=font)
        img.save(f'{path}\\temp.jpg', "PNG")
        await ctx.send(file=discord.File(f"{path}\\temp.jpg"))
        try:
            os.remove(f"{path}\\temp.jpg")
            os.remove(f"{path}\\temp_{rand}.png")
        except:
            pass

    async def on_message(self, message):
        if type(message.channel) != discord.channel.TextChannel:
            return
        elif message.channel.id not in await self.profiles._get_guild_channels(message.author.guild):
            return
        elif await self.profiles._is_registered(message.author):
            if message.content[0] in await self.bot.get_prefix(message):
                return
            else:
                mots = len(message.content.split(" "))
                if mots <= 10:
                    xp = 1
                elif mots > 10:
                    xp = 2
                await self.profiles._today_addone(message.author)
                await self.profiles._give_exp(message.author, xp)
                lvl = await self.profiles._get_level(message.author)
                roles = await self.profiles._get_guild_roles(message.guild)
                ln = lvl//10
                if ln == 0:
                    return
                elif ln >= len(roles):
                    ln = len(roles) -1
                grade = discord.utils.get(message.guild.roles, id=roles[ln-1])
                if not grade in message.author.roles:
                    for i in roles:
                        role = discord.utils.get(message.guild.roles, id=i)
                        await message.author.remove_roles(role)
                    await message.author.add_roles(grade)

    @commands.command()
    async def register(self, ctx):
        if await self.profiles._is_registered(ctx.author):
            await ctx.send("Vous êtes déjà enregistré !")
            return
        else:
            await self.profiles._register_user(ctx.author)
            await ctx.send("Vous avez été enregistré avec succès !")
            return

    @commands.command()
    async def toplevel(self, ctx):
        ld = await self.profiles._get_leaderboard(ctx.guild)
        emb = discord.Embed(title="Le classement des PGM !")
        for i in range(len(ld)):
            cur = ld[i]
            user = ctx.guild.get_member(cur["id"])
            txt = "Niveau {} | {} XP | {} Messages aujourd'hui !".format(cur["lvl"], cur["xp"], cur["today"])
            emb.add_field(name="{}".format(user.display_name), value=txt)
        await ctx.send(embed=emb)

    @commands.group()
    async def levelerset(self, ctx):
        pass

    @levelerset.group()
    async def channel(self, ctx):
        pass

    @levelerset.group()
    async def roles(self, ctx):
        pass

    @roles.command()
    async def add(self, ctx, role : discord.Role):
        if role:
            await self.profiles._add_guild_role(ctx.guild, role.id)
            await ctx.send("Role configuré")
        else:
            await ctx.send("Role inconnu")

    @roles.command()
    async def remove(self, ctx, role : discord.Role):
        if role:
            if role.id in await self.profiles._get_guild_roles(ctx.guild):
                await self.profiles._remove_guild_role(ctx.guild, role.id)
                await ctx.send("Role supprimé")
            else:
                await ctx.send("Role inconnu dans la config")
        else:
            await ctx.send("Role inconnu")

    @roles.command()
    async def move(self, ctx, role : discord.Role, position : int):
        if role:
            if role.id in await self.profiles._get_guild_roles(ctx.guild):
                await self.profiles._move_guild_role(ctx.guild, role.id, position-1)
                await ctx.send("Role déplacé")
            else:
                await ctx.send("Role inconnu dans la config")
        else:
            await ctx.send("Role inconnu")

    @roles.command()
    async def show(self, ctx):
        emb = discord.Embed(title="Liste des roles configurés pour le leveler de ce serveur.", description="Garanti 100% presque pas bugué.")
        roles = await self.profiles._get_guild_roles(ctx.guild)
        counter = 1
        for x in roles:
            emb.add_field(name=counter, value=discord.utils.get(ctx.guild.roles, id=x).name)
            counter += 1
        await ctx.send(embed=emb)

    @channel.command(name="add")
    async def _add(self, ctx, channel : discord.TextChannel):
        if channel:
            if channel.id not in await self.profiles._get_guild_channels(ctx.guild):
                await self.profiles._add_guild_channel(ctx.guild, channel.id)
                await ctx.send("Channel ajouté")
            else:
                await ctx.send("Channel déjà enregistré")
        else:
            await ctx.send("Channel inconnu")

    @channel.command(name="remove")
    async def _remove(self, ctx, channel : discord.TextChannel):
        if channel:
            if channel.id not in await self.profiles._get_guild_channels(ctx.guild):
                await ctx.send("Ce channel n'est pas dans la liste configurée.")
            else:
                await self.profiles._remove_guild_channel(ctx.guild, channel)
                await ctx.send("Channel supprimé")
        else:
            await ctx.send("Channel inconnu")

    @channel.command(name="show")
    async def _show(self, ctx):
        emb = discord.Embed(title="Liste des channels autorisés a faire gagner de l'experience sur ce serveur.", description="A une vache prés, c'pas une science exacte")
        channels = await self.profiles._get_guild_channels(ctx.guild)
        emb.add_field(name="Channels:", value="\n".join([discord.utils.get(ctx.guild.text_channels, id=x).mention for x in channels]))
        await ctx.send(embed=emb)
