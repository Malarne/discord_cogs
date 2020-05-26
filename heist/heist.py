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
        self.version = "a0.0.1"
        self.redver = "3.1.2"
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
        await ctx.send(f"```{author.name} administratively cleared {user.name}```")

    @heist.command(name="version")
    @checks.admin_or_permissions(manage_guild=True)
    async def _version_heist(self, ctx):
        """Shows the version of heist you are running"""
        await ctx.send(f"You are running v3 Heist version {self.version}.")

    @heist.command(name="targets")
    async def _targets_heist(self, ctx):
        """Shows a list of targets"""
        guild = ctx.guild
        theme = await self.thief.get_guild_theme(guild)
        targets = await self.thief.get_guild_targets(guild)
        t_vault = theme["Vault"]

        if len(targets.keys()) < 0:
            msg = (f"There aren't any targets! To create a target use ```{ctx.prefix}heist createtarget```.")
        else:
            target_names = [x for x in targets]
            crews = [int(subdict["Crew"]) for subdict in targets.values()]
            success = [str(subdict["Success"]) + "%" for subdict in targets.values()]
            vaults = [subdict["Vault"] for subdict in targets.values()]
            data = list(zip(target_names, crews, vaults, success))
            table_data = sorted(data, key=itemgetter(1), reverse=True)
            table = tabulate(table_data, headers=["Target", "Max Crew", t_vault, "Success Rate"])
            msg = f"```C\n{table}```"

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
            return await ctx.send(f"{player.display_name} is not in jail.")

        cost = await self.thief.get_member_bailcost(player)
        if not await bank.get_balance(player) >= cost:
            await ctx.send(f"You do not have enough to afford the {t_bail} amount.")
            return

        if player.id == author.id:
            msg = (f"Do you want to make a {t_bail} amount? It will cost {cost} credits. If you are "
                   f"caught again, your next {t_sentence} and {t_bail} amount will triple. "
                   f"Do you still wish to pay the {t_bail} amount?")
        else:
            msg = (f"You are about pay a {t_bail} amount for {player.name} and it will cost you {cost} credits. "
                   f"Are you sure you wish to pay {cost} for {player.name}?")

        await ctx.send(msg)
        response = await self.bot.wait_for('MESSAGE', timeout=15, check=lambda x: x.author == author)

        if response is None:
            await ctx.send("You took too long. canceling transaction.")
            return

        if "yes" in response.content.lower():
            msg = (f"Congratulations {player.display_name}, you are free! Enjoy your freedom while it "
                   f"lasts...")
            await bank.withdraw_credits(author, cost)
            await self.thief.set_member_free(author)
            await self.thief.set_member_oob(author, True)
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
        start = (f"This will walk-through the target creation process. You may cancel this process "
                 f"at anytime by typing ```{cancel}```. Let's begin with the first question.\nWhat is the "
                 f"name of this target?")

        await ctx.send(start)
        name = await self.bot.wait_for('MESSAGE', timeout=35, check=lambda x: x.author == author)

        if name is None:
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
        crew = await self.bot.wait_for('MESSAGE', timeout=35, check=check)

        if crew is None:
            await ctx.send("You took too long. canceling target creation.")
            return

        if crew.content == cancel:
            await ctx.send("Target creation cancelled.")
            return

        if int(crew.content) in [subdict["Crew"] for subdict in targets.values()]:
            await ctx.send("Group size conflicts with another target. Canceling target creation.")
            return

        await ctx.send("How many starting credits does this target have?")
        vault = await self.bot.wait_for('MESSAGE', timeout=35, check=check)

        if vault is None:
            await ctx.send("You took too long. canceling target creation.")
            return

        if vault.content == cancel:
            await ctx.send("Target creation cancelled.")
            return

        await ctx.send("What is the maximum number of credits this target can hold?")
        vault_max = await self.bot.wait_for('MESSAGE', timeout=35, check=check)

        if vault_max is None:
            await ctx.send("You took too long. canceling target creation.")
            return

        if vault_max.content == cancel:
            await ctx.send("Target creation cancelled.")
            return

        await ctx.send("What is the individual chance of success for this target? 1-100")
        check = lambda m: m.content.isdigit() and 0 < int(m.content) <= 100 or m.content == cancel
        success = await self.bot.wait_for('MESSAGE', timeout=35, check=check)

        if success is None:
            await ctx.send("You took too long. canceling target creation.")
            return

        if success.content == cancel:
            await ctx.send("Target creation cancelled.")
            return
        else:
            msg = (f"Target Created.\n```Name:       {string.capwords(name.content)}\nGroup:      {crew.content}\nVault:      {vault.content}\nVault Max: "
                   f" {vault_max.content}\nSuccess:    {success.content}%```")
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

        await ctx.send(f"Which property of {target} would you like to edit?\n"
                       f"{', '.join(keys)}")

        response = await self.bot.wait_for('MESSAGE', timeout=15, check=check)

        if response is None:
            return await ctx.send("Canceling removal. You took too long.")

        if response.content.title() == "Name":
            await ctx.send("What would you like to rename the target to?\n*Cannot be a name "
                               "currently in use.*")
            check2 = lambda m: string.capwords(m.content) not in targets and m.author == author

        elif response.content.title() in ["Vault", "Vault Max"]:
            await ctx.send(f"What would you like to set the {response.content.title()} to?")
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

        choice = await self.bot.wait_for('MESSAGE', timeout=15, check=check2)

        if choice is None:
            return await ctx.send("Canceling removal. You took too long.")

        if response.content.title() == "Name":
            new_name = string.capwords(choice.content)
            targets[new_name] = targets.pop(target)
            await self.thief.save_targets(guild, targets)
            await ctx.send(f"Changed {target}'s {response.content} to {choice.content}.")
        else:
            targets[target][response.content.title()] = int(choice.content)
            await self.thief.save_targets(guild, targets)
            await ctx.send(f"Changed {target}'s {response.content} to {choice.content}.")

    @heist.command(name="remove")
    @checks.admin_or_permissions(manage_guild=True)
    async def _remove_heist(self, ctx, *, target: str):
        """Remove a target from the heist list"""
        author = ctx.message.author
        guild = ctx.guild
        targets = await self.thief.get_guild_targets(guild)
        if string.capwords(target) in targets:
            await ctx.send(f"Are you sure you want to remove {string.capwords(target)} from the list of targets?")
            response = await self.bot.wait_for('MESSAGE', timeout=15, check=lambda x: x.author == author)
            if response is None:
                msg = "Canceling removal. You took too long."
            elif response.content.title() == "Yes":
                targets.pop(string.capwords(target))
                await self.thief.save_targets(guild, targets)
                msg = f"{string.capwords(target)} was removed from the list of targets."
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
        description = [f"Heist Version {self.version}", f"Theme: {theme}"]
        footer = "Heist was developed by Redjumpman for Red Bot v2.\nUpdated to v3 by Malarne"

        embed = discord.Embed(colour=0x0066FF, description="\n".join(description))
        embed.title = f"{guild.name} Heist Settings"
        embed.add_field(name="Heist Cost", value=config["Cost"])
        embed.add_field(name=f"Base {t_bail} Cost", value=config["Bail"])
        embed.add_field(name="Crew Gather Time", value=timers[0])
        embed.add_field(name=f"{t_police} Timer", value=timers[1])
        embed.add_field(name=f"Base {t_jail} {t_sentence}", value=timers[2])
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
            await ctx.send(f"I can't remove you from {t_jail} if you're not "
                           f"*in* {t_jail}.")
            return

        remaining = self.thief.cooldown_calculator(player_time, base_time)
        if remaining != "No Cooldown":
            await ctx.send(f"You still have time on your {t_sentence}. You still need to wait:\n"
                           f"```{remaining}```")
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
                msg = (f"You can't revive yet. You still need to wait:\n"
                       f"```{remainder}```")
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
        sentencing = f"{theme['Jail']} {theme['Sentence']}"
        t_bail = f"{theme['Bail']} Cost"

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

        unique_id = f'{author.name}:{author.id}'
        if not config["Planned"]:
            await bank.withdraw_credits(author, cost)
            config["Planned"] = True
            config["Heist author"] = unique_id
            await self.thief.config.guild(guild).Config.set(config)
            crew = await self.thief.add_crew_member(author)
            await ctx.send(f"A {t_heist} is being planned by {author.name}\nThe {t_heist} "
                           f"will begin in {wait_time} seconds. Type ```{ctx.prefix}heist play``` to join their "
                           f"{t_crew}.")
            await asyncio.sleep(wait_time)
            
            crew = await self.thief.config.guild(guild).Crew()

            if len(crew) <= 1:
                await ctx.send(f"You tried to rally a {t_crew}, but no one wanted to follow you. The "
                               f"{t_heist} has been cancelled.")
                await self.thief.reset_heist(guild)
            else:
                await self.heist_game(ctx, guild, t_heist, t_crew, t_vault)
        elif unique_id == config["Heist author"]:
                await ctx.send(f"Hey {author.name}! You are already in your own {t_crew} to perform your nefarious {t_heist}! Unless you are his evil twin!?")
        else:
            await bank.withdraw_credits(author, cost)
            crew = await self.thief.add_crew_member(author)
            crew_size = len(crew)
            await ctx.send(f"{author.display_name} has joined the {t_crew}.\nThe {t_crew} now has {crew_size} members.")

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
        await ctx.send(f"Get ready! The {t_heist} is starting with {start_output}\nThe {t_crew} has decided to "
                       f"hit **{target}**.")
        await asyncio.sleep(2)
        await self.thief.show_results(ctx, guild, results)
        curcrew = await self.thief.get_guild_crew(guild)
        if len(curcrew) != 0:
            players = [guild.get_member(int(x)) for x in curcrew]
            data = await self.thief.calculate_credits(guild, players, target)
            headers = ["Players", "Credits Obtained", "Bonuses", "Total"]
            t = tabulate(data, headers=headers)
            msg = (f"The credits collected from the {t_vault} was split among the winners:\n```"
                   f"C\n{t}```")
        else:
            msg = "No one made it out safe."
        config["Alert"] = int(time.time())
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
        theme_per_line = '\n'.join(themes) # because f-string cannot have backslashes
        await ctx.send(f"Available Themes:```\n{theme_per_line}```")

    @heist.command(name="theme")
    @checks.admin_or_permissions(manage_guild=True)
    async def _theme_heist(self, ctx, theme):
        """Sets the theme for heist"""
        theme = theme.title()
        guild = ctx.guild

        if not os.path.exists(str(bundled_data_path(self)) + f"/{theme}.txt"):
            themes = [os.path.join(x).replace('.txt', '')
                      for x in os.listdir(str(bundled_data_path(self))) if x.endswith(".txt")]
            theme_per_line = '\n'.join(themes) # because f-string cannot have backslashes
            msg = (f"I could not find a theme with that name. Available Themes:"
                   f"```\n{theme_per_line}```")
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
        await ctx.send(f"Now setting the message output type to {output}.")

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
            msg = f"Setting base {t_jail} {t_sentence} to {time_fmt}."
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
            msg = f"Setting heist cost to {cost}."
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
            msg = f"Setting {t_police} alert time to {time_fmt}."
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
            msg = f"Setting base {t_bail} cost to {cost}."
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
            msg = f"Setting death timer to {time_fmt}."
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
            msg = f"Setting {t_crew} gather time to {time_fmt}."
        else:
            msg = "Need a number higher than 0."
        await ctx.send(msg)
