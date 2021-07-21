# -*- coding: utf-8 -*-
import re
from redbot.core import checks, Config
import discord
from redbot.core import commands
from redbot.core.data_manager import bundled_data_path
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
import asyncio
import datetime
from .userprofile import UserProfile
from PIL import Image, ImageDraw, ImageFont
from math import floor, ceil
import os
import aiohttp
from redbot.core.i18n import Translator, cog_i18n
from io import BytesIO
import functools
import textwrap


_ = Translator("Leveler", __file__)


@cog_i18n(_)
class Leveler(commands.Cog):
    """A leveler cog !"""

    def __init__(self, bot):
        self.bot = bot
        self.profiles = UserProfile()
        self.loop = self.bot.loop.create_task(self.start())
        self.restart = True
        self.defaultrole = _("New")
        self._session = aiohttp.ClientSession()

    __version__ = "1.0.0"
    __author__ = "Malarne#1418"
    __info__ = {
        "bot_version": "3.0.0rc2",
        "description": (
            "A leveler cog for Red V3\n",
            "Inspired by Stevy's v2 leveler cog\n",
            "Please consult the docs at ayrobot.netlify.com for setup informations.\n",
            "Thanks for using my cog !",
        ),
        "hidden": False,
        "install_msg": (
            "Thank you for installing this leveler !\n",
            "Please consult the docs at ayrobot.netlify.com for setup informations.",
        ),
        "required_cogs": [],
        "requirements": ["pillow"],
        "short": "Leveler tool, better than MEE6",
        "tags": ["leveler", "pillow", "fun"],
    }

    def cog_unload(self):
        self.bot.remove_listener(self.listener)
        asyncio.get_event_loop().create_task(self._session.close())
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
                            await self._reset_member(i, j)
                        else:
                            await self.profiles.data.member(member).today.set(0)
                self.restart = True
            if datetime.datetime.now().strftime("%H:%M") in [
                "05:00",
                "05:01",
                "05:02",
                "05:03",
                "05:04",
                "05:05",
            ]:
                self.restart = False
            await asyncio.sleep(30)

    async def _reset_member(self, guild, memberid):
        try:
            base = self.profiles.data._get_base_group(self.profiles.data.MEMBER)
            await base.clear_raw(str(guild.id), memberid)
        except:
            pass

    @commands.command(hidden=True)
    @checks.is_owner()
    async def testreset(self, ctx):
        self.restart = False
        await ctx.send(_("Resets in 30 seconds max"), delete_after=30)

    async def get_avatar(self, user):
        try:
            res = BytesIO()
            await user.avatar_url_as(format="png", size=1024).save(res, seek_begin=True)
            return res
        except:
            async with self._session.get(user.avatar_url_as(format="png", size=1024)) as r:
                img = await r.content.read()
                return BytesIO(img)

    async def get_background(self, url):
        async with self._session.get(url) as f:
            data = await f.read()
            return Image.open(BytesIO(data))

    def round_corner(self, radius):
        """Draw a round corner"""
        corner = Image.new("L", (radius, radius), 0)
        draw = ImageDraw.Draw(corner)
        draw.pieslice((0, 0, radius * 2, radius * 2), 180, 270, fill=255)
        return corner

    def add_corners(self, im, rad):
        # https://stackoverflow.com/questions/7787375/python-imaging-library-pil-drawing-rounded-rectangle-with-gradient
        width, height = im.size
        alpha = Image.new("L", im.size, 255)
        origCorner = self.round_corner(rad)
        corner = origCorner
        alpha.paste(corner, (0, 0))
        corner = origCorner.rotate(90)
        alpha.paste(corner, (0, height - rad))
        corner = origCorner.rotate(180)
        alpha.paste(corner, (width - rad, height - rad))
        corner = origCorner.rotate(270)
        alpha.paste(corner, (width - rad, 0))
        im.putalpha(alpha)
        return im

    def make_full_profile(self, avatar_data, user, xp, nxp, lvl, minone, elo, ldb, desc, bg=None):
        img = Image.new("RGBA", (340, 390), (17, 17, 17, 255))
        if bg is not None:
            bg_width, bg_height = bg.size
            ratio = bg_height / 390
            bg = bg.resize((int(bg_width / (ratio)), int(bg_height / ratio)))
            if bg.size[0] < 340:
                ratio = bg_width / 340
                bg = bg.resize((int(bg_width / (ratio)), int(bg_height / ratio)))
            bg = bg.convert("RGBA")
            bg.putalpha(128)
            offset = 0
            if bg.size[0] >= 340:
                offset = (int((-(bg.size[0] - 340) / 2)), 0)
            if bg.size[0] < 340:
                offset = (0, int((-(bg.size[1] - 390) / 2)))

            img.paste(bg, offset, bg)
        img = self.add_corners(img, 10)
        draw = ImageDraw.Draw(img)
        usercolor = (255, 255, 0)  # user.color.to_rgb()
        aviholder = self.add_corners(Image.new("RGBA", (140, 140), (255, 255, 255, 255)), 10)
        nameplate = self.add_corners(Image.new("RGBA", (180, 60), (0, 0, 0, 255)), 10)
        xptot = self.add_corners(Image.new("RGBA", (310, 20), (215, 215, 215, 255)), 10)
        img.paste(aviholder, (10, 10), aviholder)
        img.paste(nameplate, (155, 10), nameplate)
        img.paste(xptot, (15, 340), xptot)

        fontpath = str(bundled_data_path(self) / "cambria.ttc")

        font1 = ImageFont.truetype(fontpath, 18)
        font2 = ImageFont.truetype(fontpath, 22)
        font3 = ImageFont.truetype(fontpath, 32)

        avatar = Image.open(avatar_data)
        avatar_size = 130, 130
        avatar.thumbnail(avatar_size)
        img.paste(avatar, (15, 15))
        lxp = xp - minone
        lnxp = nxp - minone
        lprc = ceil(lxp / (lnxp / 100))
        b_offset = floor(lprc * 3.1)
        xpbar = self.add_corners(Image.new("RGBA", (b_offset, 20), usercolor), 10)
        img.paste(xpbar, (12, 340), xpbar)

        lvl_str = _("Level:")
        ldb_str = _("Ranking:")
        rank_str = _("Role:")
        prog_str = _("Progress:")

        draw.text((10, 180), lvl_str, fill="white", font=font3)
        draw.text((10, 220), ldb_str, fill="white", font=font3)
        draw.text((10, 260), rank_str, fill="white", font=font3)
        nick = user.display_name
        if font2.getsize(nick)[0] > 150:
            nick = nick[:15] + "..."

        draw.text((154, 316), f"{lprc}%", fill=usercolor, font=font1)
        draw.text((100, 360), (prog_str + f" {xp}/{nxp}"), fill=usercolor, font=font1)
        draw.text(((font3.getsize(lvl_str)[0] + 20), 180), f"{lvl}", fill=usercolor, font=font3)
        draw.text(((font3.getsize(ldb_str)[0] + 20), 220), f"{ldb}", fill=usercolor, font=font3)
        draw.text(((font3.getsize(rank_str)[0] + 20), 260), f"{elo}", fill=usercolor, font=font3)

        draw.text((162, 14), f"{nick}", fill=usercolor, font=font2)
        draw.text((162, 40), f"{user.name}#{user.discriminator}", fill=usercolor, font=font1)
        margin = 162
        offset = 70
        count = 0
        for line in textwrap.wrap(desc, width=20):
            count += 1
            if count == 6:
                draw.text((margin, offset), f"{line}...", fill=usercolor, font=font1)
                break
            draw.text((margin, offset), f"{line}", fill=usercolor, font=font1)
            offset += font1.getsize(line)[1]
        temp = BytesIO()
        img.save(temp, format="PNG")
        temp.name = "profile.png"
        return temp

    async def profile_data(self, user):
        """Async get user profile data to pass to image creator"""
        avatar = await self.get_avatar(user)
        try:
            bg = await self.get_background(await self.profiles._get_background(user))
        except:
            bg = None
        default = await self.profiles.data.guild(user.guild).defaultrole()
        data = {
            "avatar_data": avatar,
            "user": user,
            "xp": 0,
            "nxp": 100,
            "lvl": 1,
            "minone": 0,
            "elo": default if default else _("New"),
            "ldb": 0,
            "desc": "",
            "bg": bg,
        }
        if not await self.profiles._is_registered(user):
            return data
        else:
            data["xp"] = await self.profiles._get_exp(user)
            data["nxp"] = await self.profiles._get_level_exp(user)
            data["lvl"] = lvl = await self.profiles._get_level(user)
            data["ldb"] = await self.profiles._get_leaderboard_pos(user.guild, user)
            data["desc"] = await self.profiles._get_description(user)
            if data["lvl"] != 1:
                data["minone"] = await self.profiles._get_xp_for_level(lvl - 1)
            else:
                data["minone"] = 0
            roles = await self.profiles._get_guild_roles(user.guild)
            if len(roles) == 0:
                default = await self.profiles.data.guild(user.guild).defaultrole()
                data["elo"] = default if default else self.defaultrole
            else:
                if str(lvl) in roles.keys():
                    data["elo"] = discord.utils.get(user.guild.roles, id=roles[str(lvl)]).name
                else:
                    tmp = 0
                    for k, v in roles.items():
                        if int(k) < lvl:
                            tmp = int(v)
                            pass
                    if tmp == 0:
                        data["elo"] = default if default else self.defaultrole
                    else:
                        rl = discord.utils.get(user.guild.roles, id=tmp)
                        data["elo"] = rl.name
        return data

    @commands.command()
    @commands.guild_only()
    async def profile(self, ctx, user: discord.Member = None):
        """Show your leveler progress. Default to yourself."""
        if user is None:
            user = ctx.author
        data = await self.profile_data(user)

        task = functools.partial(self.make_full_profile, **data)
        task = self.bot.loop.run_in_executor(None, task)
        try:
            img = await asyncio.wait_for(task, timeout=60)
        except asyncio.TimeoutError:
            return

        img.seek(0)
        await ctx.send(file=discord.File(img))

    async def listener(self, message):
        if type(message.author) != discord.Member:
            # throws an error when webhooks talk, this fixes it
            return
        if type(message.channel) != discord.channel.TextChannel:
            return
        if message.author.bot:
            return
        if await self.profiles.data.guild(message.guild).whitelist():
            if message.channel.id not in await self.profiles._get_guild_channels(
                message.author.guild
            ):
                return
        elif await self.profiles.data.guild(message.guild).blacklist():
            if message.channel.id in await self.profiles._get_guild_blchannels(
                message.author.guild
            ):
                return

        if not await self.profiles._is_registered(message.author):
            if await self.profiles._get_auto_register(message.guild):
                await self.profiles._register_user(message.author)
                return

        elif await self.profiles._is_registered(message.author):
            if message.content:
                if message.content[0] in await self.bot.get_prefix(message):
                    return
            timenow = datetime.datetime.now().timestamp()
            lastmessage = await self.profiles._get_user_lastmessage(message.author)
            cooldown = await self.profiles._get_cooldown(message.guild)
            if timenow - lastmessage < cooldown:
                # check if we've passed the cooldown
                # return None if messages are sent too soon
                return
            mots = len(message.content.split(" "))
            if mots <= 10:
                xp = 1
            elif mots > 10:
                xp = 2
            oldlvl = await self.profiles._get_level(message.author)
            await self.profiles._today_addone(message.author)
            await self.profiles._give_exp(message.author, xp)
            await self.profiles._set_user_lastmessage(message.author, timenow)
            lvl = await self.profiles._get_level(message.author)
            if (
                lvl == oldlvl + 1
                and await self.profiles.data.guild(message.guild).lvlup_announce()
            ):
                await message.channel.send(
                    _("{} is now level {} !".format(message.author.mention, lvl))
                )
            await self.profiles._check_exp(message.author)
            await self.profiles._check_role_member(message.author)

    @commands.command()
    @commands.guild_only()
    async def register(self, ctx):
        """Allow you to start earning experience !"""
        if await self.profiles._is_registered(ctx.author):
            await ctx.send(_("You are already registered !"))
            return
        else:
            await self.profiles._register_user(ctx.author)
            await ctx.send(_("You have been successfully registered !"))
            return

    @commands.command()
    @commands.guild_only()
    async def toplevel(self, ctx):
        """Show the server leaderboard !"""
        ld = await self.profiles._get_leaderboard(ctx.guild)
        emb = discord.Embed(title=_("Ranking"))
        for i in range(len(ld)):
            cur = ld[i]
            user = ctx.guild.get_member(cur["id"])
            if user is None:
                await self._reset_member(ctx.guild, cur["id"])
            else:
                txt = (
                    _("Level:")
                    + " {} | {} XP | {} ".format(cur["lvl"], cur["xp"], cur["today"])
                    + _("Messages Today!")
                )
                emb.add_field(name="{}".format(user.display_name), value=txt)
        await ctx.send(embed=emb)

    @commands.group()
    @checks.mod_or_permissions(manage_messages=True)
    @commands.guild_only()
    async def levelerset(self, ctx):
        """Configuration commands."""
        pass

    @levelerset.group()
    @checks.mod_or_permissions(manage_messages=True)
    @commands.guild_only()
    async def channel(self, ctx):
        """Configure channels whitelist/blacklist."""
        pass

    @channel.group()
    @checks.mod_or_permissions(manage_messages=True)
    @commands.guild_only()
    async def whitelist(self, ctx):
        """Whitelist configuration."""
        pass

    @channel.group()
    @checks.mod_or_permissions(manage_messages=True)
    @commands.guild_only()
    async def blacklist(self, ctx):
        """Blacklist configuration."""
        pass

    @levelerset.group()
    @checks.mod_or_permissions(manage_messages=True)
    @commands.guild_only()
    async def roles(self, ctx):
        """Configuration of roles obtainable from experience."""
        pass

    @commands.group()
    @commands.guild_only()
    async def profileset(self, ctx):
        """Change settings of your profile."""
        pass

    @profileset.command()
    @commands.guild_only()
    async def background(self, ctx, *, link: str = None):
        """Change background image of your profile."""
        await self.profiles._set_background(ctx.author, link)
        await ctx.send(_("Background image is now:") + str(link))

    @profileset.command()
    @commands.guild_only()
    async def description(self, ctx, *, description: str = ""):
        """Change your profile description"""
        await self.profiles._set_description(ctx.author, description)
        if description == "":
            await ctx.send(_("Cleared profile description!"))
        else:
            await ctx.send(_("Profile description set to: ") + str(description))

    @roles.command()
    @checks.mod_or_permissions(manage_messages=True)
    @commands.guild_only()
    async def add(self, ctx, level: int, role: discord.Role):
        """Add a role to be given at chosen level."""
        await self.profiles._add_guild_role(ctx.guild, level, role.id)
        await ctx.send(_("Role configured"))

    @roles.command()
    @checks.mod_or_permissions(manage_messages=True)
    @commands.guild_only()
    async def remove(self, ctx, role: discord.Role):
        """Remove a role from the config."""
        if role.id in (await self.profiles._get_guild_roles(ctx.guild)).values():
            await self.profiles._remove_guild_role(ctx.guild, role)
            await ctx.send(_("Role deleted."))
        else:
            await ctx.send(_("Removed a role from the list."))

    @roles.command()
    @checks.mod_or_permissions(manage_messages=True)
    @commands.guild_only()
    async def show(self, ctx):
        """Show the list of roles in the order which you get them from experience."""
        emb = discord.Embed()
        emb.title = _("List of roles configured for this server.")
        emb.description = _("Guaranteed 100% almost no bugs.")
        tmp = 0
        emblist = []
        roles = await self.profiles._get_guild_roles(ctx.guild)
        if len(roles) == 0:
            await ctx.send(_("No roles yet configured for this guild !"))
            return
        for k, v in roles.items():
            try:
                emb.add_field(name=str(k), value=discord.utils.get(ctx.guild.roles, id=v).name)
                tmp += 1
                if tmp == 25:
                    emblist.append(emb)
                    emb = discord.Embed()
                    tmp = 0
            except:
                # role no longer exists
                pass
        emblist.append(emb) if emb else emblist
        await menu(ctx, emblist, DEFAULT_CONTROLS)

    @whitelist.command(name="add")
    @checks.mod_or_permissions(manage_messages=True)
    @commands.guild_only()
    async def _add(self, ctx, channel: discord.TextChannel = None):
        """Add a channel to the whitelist."""
        if channel is None:
            channel = ctx.channel
        if channel.id not in await self.profiles._get_guild_channels(ctx.guild):
            await self.profiles._add_guild_channel(ctx.guild, channel.id)
            await ctx.send(_("Channel added"))
        else:
            await ctx.send(_("Channel already whitelisted"))

    @whitelist.command(name="toggle")
    @checks.mod_or_permissions(manage_messages=True)
    @commands.guild_only()
    async def toggle(self, ctx):
        """Toggle whitelist on/off."""
        new = await self.profiles._toggle_whitelist(ctx.guild)
        verb = _("activated.") if new else _("deactivated.")
        await ctx.send(_("Whitelist is {verb}").format(verb=verb))

    @whitelist.command(name="remove")
    @checks.mod_or_permissions(manage_messages=True)
    @commands.guild_only()
    async def _remove(self, ctx, channel: discord.TextChannel = None):
        """Delete a channel from the whitelist."""
        if channel is None:
            channel = ctx.channel
        if channel.id not in await self.profiles._get_guild_channels(ctx.guild):
            await ctx.send(_("This channel isn't whitelisted."))
        else:
            await self.profiles._remove_guild_channel(ctx.guild, channel.id)
            await ctx.send(_("Channel deleted"))

    @whitelist.command(name="show")
    @checks.mod_or_permissions(manage_messages=True)
    @commands.guild_only()
    async def _show(self, ctx):
        """Show the list of channels configured to allow earning experience."""
        emb = discord.Embed()
        emb.title = _("List of channels configured to allow earning experience on this server.")
        emb.description = _("More or less, it's not an exact science")
        channels = await self.profiles._get_guild_channels(ctx.guild)
        if not len(channels):
            return await ctx.send(_("No channels configured"))
        emb.add_field(
            name="Channels:", value="\n".join([ctx.guild.get_channel(x).mention if ctx.guild.get_channel(x) else str(await self.profiles._remove_guild_channel(ctx.guild, x)) for x in channels])
        )
        await ctx.send(embed=emb)

    @blacklist.command(name="add")
    @checks.mod_or_permissions(manage_messages=True)
    @commands.guild_only()
    async def __add(self, ctx, channel: discord.TextChannel = None):
        """Add a channel to the blacklist."""
        if channel is None:
            channel = ctx.channel
        if channel.id not in await self.profiles._get_guild_blchannels(ctx.guild):
            await self.profiles._add_guild_blacklist(ctx.guild, channel.id)
            await ctx.send(_("Channel blacklisted"))
        else:
            await ctx.send(_("Channel already blacklisted"))

    @blacklist.command(name="toggle")
    @checks.mod_or_permissions(manage_messages=True)
    @commands.guild_only()
    async def _toggle(self, ctx):
        """Toggle blacklist on/off."""
        new = await self.profiles._toggle_blacklist(ctx.guild)
        verb = _("activated.") if new else _("deactivated.")
        await ctx.send(_("Blacklist is {verb}").format(verb=verb))

    @blacklist.command(name="remove")
    @checks.mod_or_permissions(manage_messages=True)
    @commands.guild_only()
    async def __remove(self, ctx, channel: discord.TextChannel = None):
        """Remove a channel from the blacklist."""
        if channel is None:
            channel = ctx.channel
        if channel.id not in await self.profiles._get_guild_blchannels(ctx.guild):
            await ctx.send(_("This channel isn't whitelisted."))
        else:
            await self.profiles._remove_guild_blacklist(ctx.guild, channel.id)
            await ctx.send(_("Channel deleted"))

    @blacklist.command(name="show")
    @checks.mod_or_permissions(manage_messages=True)
    @commands.guild_only()
    async def __show(self, ctx):
        """Show the list of blacklisted channels."""
        emb = discord.Embed()
        emb.title = _("List of blacklisted channels on this server.")
        emb.description = _("More or less, it's not an exact science")
        channels = await self.profiles._get_guild_blchannels(ctx.guild)
        if not len(channels):
            return await ctx.send(_("No channels configured"))
        emb.add_field(
            name="Channels:", value="\n".join([ctx.guild.get_channel(x).mention if ctx.guild.get_channel(x) else str(await self.profiles._remove_guild_blacklist(ctx.guild, x)) for x in channels])
        )
        await ctx.send(embed=emb)

    @levelerset.command()
    @commands.guild_only()
    async def autoregister(self, ctx):
        """Toggle auto register of users"""
        if await self.profiles._get_auto_register(ctx.guild):
            await self.profiles._set_auto_register(ctx.guild, False)
            await ctx.send(_("Auto register turned off"))
        else:
            await self.profiles._set_auto_register(ctx.guild, True)
            await ctx.send(_("Auto register turned on"))

    @levelerset.command()
    @commands.guild_only()
    async def cooldown(self, ctx, cooldown: float):
        """Modify the cooldown of xp gain, default to 60 seconds"""
        await self.profiles._set_cooldown(ctx.guild, cooldown)
        await ctx.send(_("Cooldown is now: ") + str(cooldown))

    @levelerset.command()
    @checks.is_owner()
    @commands.guild_only()
    async def setlevel(self, ctx, level: int, member: discord.Member = None):
        """Modify an user's level"""
        if member is None:
            member = ctx.message.author
        if await self.profiles._is_registered(member):
            await self.profiles._set_exp(member, 5 * ((level - 1) ** 2) + (50 * (level - 1)) + 100)
        else:
            await ctx.send(_("That user is not registered."))
        await ctx.send(member.name + _(" Level set to ") + str(level))

    @levelerset.command()
    @checks.is_owner()
    @commands.guild_only()
    async def setxp(self, ctx, xp: int, member: discord.Member = None):
        """Modify an user's xp."""
        if member is None:
            member = ctx.message.author
        if await self.profiles._is_registered(member):
            await self.profiles._set_exp(member, xp)
        else:
            await ctx.send(_("That user is not registered."))
        await ctx.send(member.name + _("'s XP set to ") + str(xp))

    @levelerset.command()
    @checks.mod_or_permissions(manage_messages=True)
    @commands.guild_only()
    async def defaultbackground(self, ctx, url):
        """Allow you to set a default background for your server members."""
        bg = re.findall(r"(?:http\:|https\:)?\/\/.*\.(?:png|jpg|gif)", url)
        if not bg:
            await ctx.send(_("Please give a direct link to an image on format png, jpg or gif !"))
        else:
            background = bg[0]
            await self.profiles._set_guild_background(ctx.guild, background)
            await ctx.send(f"Default background set to {background}.")

    @roles.command(name="defaultrole")
    @checks.mod_or_permissions(manage_messages=True)
    @commands.guild_only()
    async def default_role(self, ctx, *, name):
        """Allow you to rename default role for your guild."""
        await self.profiles.data.guild(ctx.author.guild).defaultrole.set(name)
        await ctx.send(_(f"Default role name set to {name}"))

    @levelerset.command()
    @checks.mod_or_permissions(manage_messages=True)
    @commands.guild_only()
    async def announce(self, ctx, status: bool):
        """Toggle whether the bot will announce levelups.
        args are True/False."""
        await self.profiles.data.guild(ctx.guild).lvlup_announce.set(status)
        await ctx.send(
            _("Levelup announce is now {}.").format(_("enabled") if status else _("disabled"))
        )
