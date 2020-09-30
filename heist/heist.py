import re
import asyncio
import datetime
import bisect
import os
import random
import string
import time
from ast import literal_eval
from operator import itemgetter
from redbot.core import checks, Config, bank
import discord
from redbot.core import commands
from redbot.core.data_manager import bundled_data_path
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import escape
from .thief import Thief, PluralDict

from tabulate import tabulate

_ = Translator("Heist", __file__)

@cog_i18n(_)
class Heist(commands.Cog):
    """Heist system inspired by Deepbot.
    Cog originally made by RedJumpMan for Red v2."""

    def __init__(self, bot):
        self.bot = bot
        self.thief = Thief()
        self.version = "b0.3.1"
        self.redver = "3.3.9"
        self.cycle_task = bot.loop.create_task(self.thief.vault_updater(bot))

    @commands.group(no_pm=True)
    async def heist(self, ctx):
        pass

    @heist.command(name="reset")
    @checks.admin_or_permissions(manage_guild=True)
    async def _reset_heist(self, ctx):
        """Resets heist in case it hangs"""
        guild = ctx.guild
        await self.thief.reset_heist(guild)
        await ctx.send("```Heist has been reset```")

    @heist.command(name="clear")
    @checks.admin_or_permissions(manage_guild=True)
    async def _clear_heist(self, ctx, user: discord.Member):
        """Clears a member of jail and death statuses."""
        author = ctx.message.author
        await self.thief.member_clear(user)
        await ctx.send("```{} administratively cleared {}```".format(escape(author.display_name, formatting=True), escape(user.display_name, formatting=True)))

    @heist.command(name="version")
    @checks.admin_or_permissions(manage_guild=True)
    async def _version_heist(self, ctx):
        """Shows the version of heist you are running"""
        await ctx.send("You are running v3 Heist version {}.".format(self.version))

    @heist.command(name="targets")
    async def _targets_heist(self, ctx):
        """Shows a list of targets"""
        guild = ctx.guild
        theme = await self.thief.get_guild_theme(guild)
        targets = await self.thief.get_guild_targets(guild)
        t_vault = theme["Vault"]

        if len(targets.keys()) < 0:
            msg = ("There aren't any targets! To create a target use {}heist "
                   "createtarget .".format(ctx.prefix))
        else:
            target_names = [x for x in targets]
            crews = [int(subdict["Crew"]) for subdict in targets.values()]
            success = [str(subdict["Success"]) + "%" for subdict in targets.values()]
            vaults = [subdict["Vault"] for subdict in targets.values()]
            data = list(zip(target_names, crews, vaults, success))
            table_data = sorted(data, key=itemgetter(1), reverse=True)
            table = tabulate(table_data, headers=["Target", "Max Crew", t_vault, "Success Rate"])
            msg = "```C\n{}```".format(table)

        await ctx.send(msg)

    @heist.command(name="bailout")
    async def _bailout_heist(self, ctx, user: discord.Member=None):
        """Specify who you want to pay for release. Defaults to you."""
        author = ctx.message.author
        theme = await self.thief.get_guild_theme(ctx.guild)

        t_bail = theme["Bail"]
        t_sentence = theme["Sentence"]

        if user is None:
            player = author
        else:
            player = user

        if await self.thief.get_member_status(player) != "Apprehended":
            return await ctx.send("{} is not in jail.".format(escape(player.display_name, formatting=True)))

        cost = await self.thief.get_member_bailcost(player)
        if not await bank.get_balance(player) >= cost:
            await ctx.send("You do not have enough to afford the {} amount.".format(t_bail))
            return

        if player.id == author.id:
            msg = ("Do you want to make a {0} amount? It will cost {1} credits. If you are "
                   "caught again, your next {2} and {0} amount will triple. "
                   "Do you still wish to pay the {0} amount?".format(t_bail, cost, t_sentence))
        else:
            msg = ("You are about pay a {2} amount for {0} and it will cost you {1} credits. "
                   "Are you sure you wish to pay {1} for {0}?".format(escape(player.display_name, formatting=True), cost, t_bail))

        await ctx.send(msg)
        try:
            response = await self.bot.wait_for("message", timeout=15, check=lambda x: x.author == author)
        except asyncio.TimeoutError:
            await ctx.send("You took too long. canceling transaction.")
            return

        if "yes" in response.content.lower():
            msg = ("Congratulations {}, you are free! Enjoy your freedom while it "
                   "lasts...".format(escape(player.display_name, formatting=True)))
            await bank.withdraw_credits(author, cost)
            await self.thief.set_member_free(author)
            await self.thief.set_member_oob(author, False)
        elif "no" in response.content.lower():
            msg = "Canceling transaction."
        else:
            msg = "Incorrect response, canceling transaction."

        await ctx.send(msg)

    @heist.command(name="createtarget")
    @checks.admin_or_permissions(manage_guild=True)
    async def _targetadd_heist(self, ctx):
        """Add a target to heist"""

        author = ctx.message.author
        guild = ctx.guild
        cancel = ctx.prefix + "cancel"
        check = lambda m: m.author == author and (m.content.isdigit() and int(m.content) > 0 or m.content == cancel)
        start = ("This will walk-through the target creation process. You may cancel this process "
                 "at anytime by typing {}cancel. Let's begin with the first question.\nWhat is the "
                 "name of this target?".format(ctx.prefix))

        await ctx.send(start)
        try:
            name = await self.bot.wait_for("message", timeout=35, check=lambda x: x.author == author)
        except asyncio.TimeoutError:
            await ctx.send("You took too long. canceling target creation.")
            return

        if name.content == cancel:
            await ctx.send("Target creation cancelled.")
            return

        targets = await self.thief.get_guild_targets(guild)
        if string.capwords(name.content) in targets:
            await ctx.send("A target with that name already exists. canceling target "
                               "creation.")
            return

        await ctx.send("What is the max crew size for this target? Cannot be the same as "
                           "other targets.\n*Crews over this size will go to the next "
                           "largest bank.*")
        try:
            crew = await self.bot.wait_for("message", timeout=35, check=check)
        except asyncio.TimeoutError:
            await ctx.send("You took too long. canceling target creation.")
            return

        if crew.content == cancel:
            await ctx.send("Target creation cancelled.")
            return

        if int(crew.content) in [subdict["Crew"] for subdict in targets.values()]:
            await ctx.send("Group size conflicts with another target. Canceling target creation.")
            return

        await ctx.send("How many starting credits does this target have?")
        try:
            vault = await self.bot.wait_for("message", timeout=35, check=check)
        except asyncio.TimeoutError:
            await ctx.send("You took too long. canceling target creation.")
            return

        if vault.content == cancel:
            await ctx.send("Target creation cancelled.")
            return

        await ctx.send("What is the maximum number of credits this target can hold?")
        try:
            vault_max = await self.bot.wait_for("message", timeout=35, check=check)
        except asyncio.TimeoutError:
            await ctx.send("You took too long. canceling target creation.")
            return
        
        if vault_max.content == cancel:
            await ctx.send("Target creation cancelled.")
            return
        
        if vault_max.content.isdigit() and int(vault_max.content) >= ((2**64)-1):
            return await ctx.send("Number is too high, canceling target creation.")

        await ctx.send("What is the individual chance of success for this target? 1-100")
        #check = lambda m: m.content.isdigit() and 0 < int(m.content) <= 100 or m.content == cancel # <--- missing author check here?
        check = lambda m: m.author == author and (m.content.isdigit() and 0 < int(m.content) <= 100 or m.content == cancel)
        
        try:
            success = await self.bot.wait_for("message", timeout=35, check=check)
        except asyncio.TimeoutError:
            await ctx.send("You took too long. canceling target creation.")
            return

        if success.content == cancel:
            await ctx.send("Target creation cancelled.")
            return
        else:
            msg = ("Target Created.\n```Name:       {}\nGroup:      {}\nVault:      {}\nVault Max: "
                   " {}\nSuccess:    {}%```".format(string.capwords(name.content), crew.content,
                                                    vault.content, vault_max.content,
                                                    success.content)
                   )
            target_fmt = {"Crew": int(crew.content), "Vault": int(vault.content),
                          "Vault Max": int(vault_max.content), "Success": int(success.content)}
            targets[string.capwords(name.content)] = target_fmt
            await self.thief.save_targets(guild, targets)
            await ctx.send(msg)

    @heist.command(name="edittarget")
    @checks.admin_or_permissions(manage_guild=True)
    async def _edittarget_heist(self, ctx, *, target: str):
        """Edits a heist target"""
        author = ctx.message.author
        guild = ctx.guild
        target = string.capwords(target)
        targets = await self.thief.get_guild_targets(guild)

        if target not in targets:
            return await ctx.send("That target does not exist.")

        keys = [x for x in targets[target]]
        keys.append("Name")
        check = lambda m: m.content.title() in keys and m.author == author

        await ctx.send("Which property of {} would you like to edit?\n"
                           "{}".format(target, ", ".join(keys)))
        
        try:
            response = await self.bot.wait_for("message", timeout=15, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Canceling removal. You took too long.")
            return

        if response.content.title() == "Name":
            await ctx.send("What would you like to rename the target to?\n*Cannot be a name "
                               "currently in use.*")
            check2 = lambda m: string.capwords(m.content) not in targets and m.author == author

        elif response.content.title() in ["Vault", "Vault Max"]:
            await ctx.send("What would you like to set the {} "
                               "to?".format(response.content.title()))
            check2 = lambda m: m.content.isdigit() and int(m.content) > 0 and m.author == author

        elif response.content.title() == "Success":
            await ctx.send("What would you like to change the success rate to?")
            check2 = lambda m: m.content.isdigit() and 0 < int(m.content) <= 100 and m.author == author

        elif response.content.title() == "Crew":
            await ctx.send("What would you like to change the max crew size to?\n Cannot be "
                               "the same as another target and will be the maximum number of "
                               "players for that target.")
            crew_sizes = [subdict["Crew"] for subdict in targets.values()]
            check2 = lambda m: m.content.isdigit() and int(m.content) not in crew_sizes and m.author == author
            
        try:
            choice = await self.bot.wait_for("message", timeout=15, check=check2)
        except asyncio.TimeoutError:
            await ctx.send("Canceling removal. You took too long.")
            return

        if response.content.title() == "Name":
            new_name = string.capwords(choice.content)
            targets[new_name] = targets.pop(target)
            await self.thief.save_targets(guild, targets)
            await ctx.send("Changed {}'s {} to {}.".format(target, response.content,
                                                               choice.content))
        else:
            targets[target][response.content.title()] = int(choice.content)
            await self.thief.save_targets(guild, targets)
            await ctx.send("Changed {}'s {} to {}.".format(target, response.content,
                                                               choice.content))

    @heist.command(name="remove")
    @checks.admin_or_permissions(manage_guild=True)
    async def _remove_heist(self, ctx, *, target: str):
        """Remove a target from the heist list"""
        author = ctx.message.author
        guild = ctx.guild
        targets = await self.thief.get_guild_targets(guild)
        if string.capwords(target) in targets:
            await ctx.send("Are you sure you want to remove {} from the list of "
                               "targets?".format(string.capwords(target)))
            try:
                response = await self.bot.wait_for("message", timeout=15, check=lambda x: x.author == author)
            except asyncio.TimeoutError:
                await ctx.send("Canceling removal. You took too long.")
                return
            if response.content.title() == "Yes":
                targets.pop(string.capwords(target))
                await self.thief.save_targets(guild, targets)
                msg = "{} was removed from the list of targets.".format(string.capwords(target))
            else:
                msg = "Canceling target removal."
        else:
            msg = "That target does not exist."
        await ctx.send(msg)

    @heist.command(name="info")
    async def _info_heist(self, ctx):
        """Shows the Heist settings for this server."""
        guild = ctx.guild
        config = await self.thief.get_guild_settings(guild)
        themes = await self.thief.get_guild_theme(guild)

        if config["Hardcore"]:
            hardcore = "ON"
        else:
            hardcore = "OFF"

        # Theme variables
        theme = config["Theme"]
        t_jail = themes["Jail"]
        t_sentence = themes["Sentence"]
        t_police = themes["Police"]
        t_bail = themes["Bail"]

        time_values = [config["Wait"], config["Police"],
                       config["Sentence"], config["Death"]]
        timers = list(map(self.thief.time_format, time_values))
        description = ["Heist Version {}".format(self.version), "Theme: {}".format(theme)]
        footer = "Heist was developed by Redjumpman for Red Bot v2.\nUpdated to v3 by Malarne"

        embed = discord.Embed(colour=0x0066FF, description="\n".join(description))
        embed.title = "{} Heist Settings".format(guild.name)
        embed.add_field(name="Heist Cost", value=config["Cost"])
        embed.add_field(name="Base {} Cost".format(t_bail), value=config["Bail"])
        embed.add_field(name="Crew Gather Time", value=timers[0])
        embed.add_field(name="{} Timer".format(t_police), value=timers[1])
        embed.add_field(name="Base {} {}".format(t_jail, t_sentence), value=timers[2])
        embed.add_field(name="Death Timer", value=timers[3])
        embed.add_field(name="Hardcore Mode", value=hardcore)
        embed.set_footer(text=footer)

        await ctx.send(embed=embed)

    @heist.command(name="release")
    async def _release_heist(self, ctx):
        """Removes you from jail or clears bail status if sentence served."""
        author = ctx.message.author
        guild = ctx.guild
        player_time = await self.thief.get_member_timeserved(author)
        base_time = await self.thief.get_member_sentence(author)
        oob = await self.thief.get_member_oob(author)

        # Theme variables
        theme = await self.thief.get_guild_theme(guild)
        t_jail = theme["Jail"]
        t_sentence = theme["Sentence"]

        if await self.thief.get_member_status(author) != "Apprehended" or oob:
            await ctx.send("I can't remove you from {0} if you're not "
                               "*in* {0}.".format(t_jail))
            return

        remaining = self.thief.cooldown_calculator(player_time, base_time)
        if remaining != "No Cooldown":
            await ctx.send("You still have time on your {}. You still need to wait:\n"
                               "```{}```".format(t_sentence, remaining))
            return

        msg = "You served your time. Enjoy the fresh air of freedom while you can."

        if oob:
            msg = "You are no longer on probation! 3x penalty removed."
            await self.thief.set_member_oob(author, False)

        await self.thief.set_member_sentence(author, 0)
        await self.thief.set_member_timeserved(author, 0)
        await self.thief.set_member_free(author)

        await ctx.send(msg)

    @heist.command(name="revive")
    async def _revive_heist(self, ctx):
        """Revive from the dead!"""
        author = ctx.message.author
        config = await self.thief.get_guild_settings(ctx.guild)
        player_time = await self.thief.get_member_deathtimer(author)
        base_time = config["Death"]

        if await self.thief.get_member_status(author) == "Dead":
            remainder = self.thief.cooldown_calculator(player_time, base_time)
            if remainder == "No Cooldown":
                await self.thief.revive_member(author)
                await self.thief.set_member_free(author)
                msg = "You have risen from the dead!"
            else:
                msg = ("You can't revive yet. You still need to wait:\n"
                       "```{}```".format(remainder))
        else:
            msg = "You still have a pulse. I can't revive someone who isn't dead."
        await ctx.send(msg)

    @heist.command(name="stats")
    async def _stats_heist(self, ctx):
        """Shows your Heist stats"""
        author = ctx.message.author
        avatar = ctx.message.author.avatar_url
        guild = ctx.guild
        config = await self.thief.get_guild_settings(guild)
        theme = await self.thief.get_guild_theme(guild)

        await self.thief.check_member_settings(author)

        # Theme variables
        sentencing = "{} {}".format(theme["Jail"], theme["Sentence"])
        t_bail = "{} Cost".format(theme["Bail"])

        # Sentence Time Remaining
        sentence = await self.thief.get_member_sentence(author)
        time_served = await self.thief.get_member_timeserved(author)
        jail_fmt = self.thief.cooldown_calculator(time_served, sentence)

        # Death Time Remaining
        death_timer = await self.thief.get_member_deathtimer(author)
        base_death_timer = config["Death"]
        death_fmt = self.thief.cooldown_calculator(death_timer, base_death_timer)

        rank = self.thief.criminal_level(await self.thief.get_member_crimlevel(author))

        embed = discord.Embed(colour=0x0066FF, description=rank)
        embed.title = author.name
        embed.set_thumbnail(url=avatar)
        embed.add_field(name="Status", value=await self.thief.get_member_status(author))
        embed.add_field(name="Spree", value=await self.thief.get_member_spree(author))
        embed.add_field(name=t_bail, value=await self.thief.get_member_bailcost(author))
        embed.add_field(name=theme["OOB"], value=await self.thief.get_member_oob(author))
        embed.add_field(name=sentencing, value=jail_fmt)
        embed.add_field(name="Apprehended", value=await self.thief.get_member_jailcounter(author))
        embed.add_field(name="Death Timer", value=death_fmt)
        embed.add_field(name="Total Deaths", value=await self.thief.get_member_totaldeaths(author))
        embed.add_field(name="Lifetime Apprehensions", value=await self.thief.get_member_totaljails(author))

        await ctx.send(embed=embed)

    @heist.command(name="play")
    async def _play_heist(self, ctx):
        """This begins a Heist"""
        author = ctx.message.author
        guild = ctx.guild
        config = await self.thief.get_guild_settings(guild)
        theme = await self.thief.get_guild_theme(guild)
        crew = await self.thief.config.guild(guild).Crew()

        await self.thief.check_server_settings(guild)
        await self.thief.check_member_settings(author)

        cost = config["Cost"]
        wait_time = config["Wait"]
        prefix = ctx.prefix

        # Theme Variables
        t_crew = theme["Crew"]
        t_heist = theme["Heist"]
        t_vault = theme["Vault"]

        outcome, msg = await self.thief.requirement_check(prefix, author, cost)

        if outcome == "Failed":
            return await ctx.send(msg)

        if not config["Planned"]:
            await bank.withdraw_credits(author, cost)
            config["Planned"] = True
            await self.thief.config.guild(guild).Config.set(config)
            crew = await self.thief.add_crew_member(author)
            await ctx.send("A {4} is being planned by {0}\nThe {4} "
                               "will begin in {1} seconds. Type {2}heist play to join their "
                               "{3}.".format(escape(author.display_name, formatting=True), wait_time, ctx.prefix, t_crew, t_heist))
            await asyncio.sleep(wait_time)
            
            crew = await self.thief.config.guild(guild).Crew()

            if len(crew) <= 1:
                await ctx.send("You tried to rally a {}, but no one wanted to follow you. The "
                                   "{} has been cancelled.".format(t_crew, t_heist))
                await self.thief.reset_heist(guild)
            else:
                await self.heist_game(ctx, guild, t_heist, t_crew, t_vault)

        else:
            await bank.withdraw_credits(author, cost)
            crew = await self.thief.add_crew_member(author)
            crew_size = len(crew)
            await ctx.send("{0} has joined the {2}.\nThe {2} now has {1} "
                               "members.".format(escape(author.display_name, formatting=True), crew_size, t_crew))

    async def heist_game(self, ctx, guild, t_heist, t_crew, t_vault):
        config = await self.thief.get_guild_settings(guild)
        targets = await self.thief.get_guild_targets(guild)
        curcrew = await self.thief.get_guild_crew(guild)
        crew = len(curcrew)
        target = self.thief.heist_target(targets, guild, crew)
        config["Start"] = True
        await self.thief.config.guild(guild).Config.set(config)
        players = [guild.get_member(int(x)) for x in curcrew]
        results = await self.thief.game_outcomes(guild, players, target)
        start_output = await self.thief.message_handler(guild, crew, players)
        await ctx.send("Get ready! The {} is starting with {}\nThe {} has decided to "
                           "hit **{}**.".format(t_heist, start_output, t_crew, target))
        await asyncio.sleep(2)
        await self.thief.show_results(ctx, guild, results)
        curcrew = await self.thief.get_guild_crew(guild)
        if len(curcrew) != 0:
            players = [guild.get_member(int(x)) for x in curcrew]
            data = await self.thief.calculate_credits(guild, players, target)
            headers = ["Players", "Credits Obtained", "Bonuses", "Total"]
            t = tabulate(data, headers=headers)
            msg = ("The credits collected from the {} was split among the winners:\n```"
                   "C\n{}```".format(t_vault, t))
        else:
            msg = "No one made it out safe."
        config["Alert"] = int(time.perf_counter())
        await self.thief.config.guild(guild).Config.set(config)
        await self.thief.reset_heist(guild)
        await ctx.send(msg)

    @heist.command(name="listthemes")
    @checks.admin_or_permissions(manage_guild=True)
    async def _themelist_heist(self, ctx):
        """Lists available themes for heist."""
        themes = [os.path.join(x).replace('.txt', '')
                  for x in os.listdir(str(bundled_data_path(self))) if x.endswith(".txt")]
        if len(themes) > 30:
            themes = themes[:30]
        await ctx.send("Available Themes:```\n{}```".format('\n'.join(themes)))

    @heist.command(name="theme")
    @checks.admin_or_permissions(manage_guild=True)
    async def _theme_heist(self, ctx, theme):
        """Sets the theme for heist"""
        theme = theme.title()
        guild = ctx.guild

        if not os.path.exists(str(bundled_data_path(self)) + "/{}.txt".format(theme)):
            themes = [os.path.join(x).replace('.txt', '')
                      for x in os.listdir(str(bundled_data_path(self))) if x.endswith(".txt")]
            msg = ("I could not find a theme with that name. Available Themes:"
                   "```\n{}```".format('\n'.join(themes)))
        else:
            msg = await self.thief.theme_loader(guild, theme)

        await ctx.send(msg)



    @commands.group(no_pm=True)
    async def setheist(self, ctx):
        """Set different options in the heist config"""

        pass

    @setheist.command(name="output")
    @checks.admin_or_permissions(manage_guild=True)
    async def _output_setheist(self, ctx, output: str):
        """Change how detailed the starting output is.
        None: Displays just the number of crew members.

        Short: Displays five participants and truncates the rest.

        Long: Shows entire crew list. WARNING Not suitable for
              really big crews.
        """
        guild = ctx.guild
        settings = await self.thief.get_guild_settings(guild)
        if output.title() not in ["None", "Short", "Long"]:
            return await ctx.send("You must choose \'None\', \'Short\', or \'Long\'.")

        settings["Crew"] = output.title()
        await self.thief.config.guild(guild).Config.set(settings)
        await ctx.send("Now setting the message output type to {}.".format(output))

    @setheist.command(name="sentence")
    @checks.admin_or_permissions(manage_guild=True)
    async def _sentence_setheist(self, ctx, seconds: int):
        """Set the base apprehension time when caught"""
        guild = ctx.guild
        config = await self.thief.get_guild_settings(guild)
        theme = await self.thief.config.guild(guild).Theme()
        t_jail = theme["Jail"]
        t_sentence =theme["Sentence"]

        if seconds > 0:
            config["Sentence"] = seconds
            await self.thief.config.guild(guild).Config.set(config)
            time_fmt = self.thief.time_format(seconds)
            msg = "Setting base {} {} to {}.".format(t_jail, t_sentence, time_fmt)
        else:
            msg = "Need a number higher than 0."
        await ctx.send(msg)

    @setheist.command(name="cost")
    @checks.admin_or_permissions(manage_guild=True)
    async def _cost_setheist(self, ctx, cost: int):
        """Set the cost to play heist"""
        guild = ctx.guild
        config = await self.thief.get_guild_settings(guild)

        if cost >= 0:
            config["Cost"] = cost
            await self.thief.config.guild(guild).Config.set(config)
            msg = "Setting heist cost to {}.".format(cost)
        else:
            msg = "Need a number higher than -1."
        await ctx.send(msg)

    @setheist.command(name="authorities")
    @checks.admin_or_permissions(manage_guild=True)
    async def _authorities_setheist(self, ctx, seconds: int):
        """Set the time authorities will prevent heists"""
        guild = ctx.guild
        config = await self.thief.get_guild_settings(guild)
        theme = await self.thief.config.guild(guild).Theme()
        t_police = theme["Police"]

        if seconds > 0:
            config["Police"] = seconds
            await self.thief.config.guild(guild).Config.set(config)
            time_fmt = self.thief.time_format(seconds)
            msg = "Setting {} alert time to {}.".format(t_police, time_fmt)
        else:
            msg = "Need a number higher than 0."
        await ctx.send(msg)

    @setheist.command(name="bail")
    @checks.admin_or_permissions(manage_guild=True)
    async def _bail_setheist(self, ctx, cost: int):
        """Set the base cost of bail"""
        guild = ctx.guild
        config = await self.thief.get_guild_settings(guild)
        theme = await self.thief.config.guild(guild).Theme()
        t_bail = theme["Bail"]
        if cost >= 0:
            config["Bail Base"] = cost
            await self.thief.config.guild(guild).Config.set(config)
            msg = "Setting base {} cost to {}.".format(t_bail, cost)
        else:
            msg = "Need a number higher than -1."
        await ctx.send(msg)

    @setheist.command(name="death")
    @checks.admin_or_permissions(manage_guild=True)
    async def _death_setheist(self, ctx, seconds: int):
        """Set how long players are dead"""
        guild = ctx.guild
        config = await self.thief.get_guild_settings(guild)

        if seconds > 0:
            config["Death"] = seconds
            await self.thief.config.guild(guild).Config.set(config)
            time_fmt = self.thief.time_format(seconds)
            msg = "Setting death timer to {}.".format(time_fmt)
        else:
            msg = "Need a number higher than 0."
        await ctx.send(msg)

    @setheist.command(name="hardcore")
    @checks.admin_or_permissions(manage_guild=True)
    async def _hardcore_setheist(self, ctx):
        """Set game to hardcore mode. Deaths will wipe credits and chips."""
        guild = ctx.guild
        config = await self.thief.get_guild_settings(guild)

        if config["Hardcore"]:
            config["Hardcore"] = False
            msg = "Hardcore mode now OFF."
        else:
            config["Hardcore"] = True
            msg = "Hardcore mode now ON! **Warning** death will result in credit **and chip wipe**."
        await self.thief.config.guild(guild).Config.set(config)
        await ctx.send(msg)

    @setheist.command(name="wait")
    @checks.admin_or_permissions(manage_guild=True)
    async def _wait_setheist(self, ctx, seconds: int):
        """Set how long a player can gather players"""
        guild = ctx.guild
        config = await self.thief.get_guild_settings(guild)
        theme = await self.thief.config.guild(guild).Theme()
        t_crew = theme["Crew"]

        if seconds > 0:
            config["Wait"] = seconds
            await self.thief.config.guild(guild).Config.set(config)
            time_fmt = self.thief.time_format(seconds)
            msg = "Setting {} gather time to {}.".format(t_crew, time_fmt)
        else:
            msg = "Need a number higher than 0."
        await ctx.send(msg)
