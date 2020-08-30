from redbot.core import Config, bank
from redbot.core.data_manager import bundled_data_path
from redbot.core.utils.chat_formatting import escape
import time
import bisect
import random
import asyncio
from operator import itemgetter
from ast import literal_eval


# Thanks stack overflow http://stackoverflow.com/questions/21872366/plural-string-formatting
class PluralDict(dict):
    def __missing__(self, key):
        if '(' in key and key.endswith(')'):
            key, rest = key.split('(', 1)
            value = super().__getitem__(key)
            suffix = rest.rstrip(')').split(',')
            if len(suffix) == 1:
                suffix.insert(0, '')
            return suffix[0] if value <= 1 else suffix[1]
        raise KeyError(key)

class Thief:

    def __init__(self):
        self.config = Config.get_conf(self, identifier=22572522, force_registration=True)
        default_guild = {
            "Config": {
                "Start": False,
                "Planned": False,
                "Cost": 100,
                "Wait": 20,
                "Hardcore": False,
                "Police": 60,
                "Alert": 0,
                "Sentence": 600,
                "Bail": 500,
                "Death": 86400,
                "Theme": "Heist",
                "Crew": "None",
                "Version": "a0.0.1",
                "Registered": False
            },
            "Theme": {
                "Jail": "jail",
                "OOB": "out on bail",
                "Police": "Police",
                "Bail": "bail",
                "Crew": "crew",
                "Sentence": "sentence",
                "Heist": "heist",
                "Vault": "vault"
            },
            "Players": {},
            "Crew": {},
            "Targets": {}
        }
        default_member = {
            "Status": "Free",
            "CrimLevel": 0,
            "JailC": 0,
            "DeathT": 0,
            "BailC": 0,
            "Sentence": 0,
            "TimeS": 0,
            "OOB": False,
            "Spree": 0,
            "TotalDeaths": 0,
            "TotalJails": 0,
            "Registered": False
        }
        self.config.register_guild(**default_guild)
        self.config.register_member(**default_member)

    async def reset_heist(self, guild):
        await self.config.guild(guild).Crew.set({})
        async with self.config.guild(guild).Config() as conf:
            conf["Planned"] = False
            conf["Start"] = False

    async def member_clear(self, member):
        await self.config.member(member).clear()

    async def get_guild_settings(self, guild):
        return await self.config.guild(guild).Config()

    async def get_guild_theme(self, guild):
        return await self.config.guild(guild).Theme()

    async def get_guild_targets(self, guild):
        return await self.config.guild(guild).Targets()

    async def get_member_status(self, member):
        return await self.config.member(member).Status()

    async def get_member_crimlevel(self, member):
        return await self.config.member(member).CrimLevel()

    async def get_member_jailcounter(self, member):
        return await self.config.member(member).JailC()

    async def get_member_deathtimer(self, member):
        return await self.config.member(member).DeathT()

    async def get_member_bailcost(self, member):
        return await self.config.member(member).BailC()

    async def get_member_sentence(self, member):
        return await self.config.member(member).Sentence()

    async def get_member_timeserved(self, member):
        return await self.config.member(member).TimeS()

    async def get_member_oob(self, member):
        return await self.config.member(member).OOB()

    async def get_member_spree(self, member):
        return await self.config.member(member).Spree()

    async def get_member_totaldeaths(self, member):
        return await self.config.member(member).TotalDeaths()

    async def get_member_totaljails(self, member):
        return await self.config.member(member).TotalJails()

    async def member_caught(self, member):
        cur = await self.config.member(member).TotalJails()
        await self.config.member(member).TotalJails.set(cur+1)

    async def member_died(self, member):
        cur = await self.config.member(member).TotalDeaths()
        await self.config.member(member).TotalDeaths.set(cur+1)

    async def set_member_free(self, member):
        return await self.config.member(member).Status.set("Free")

    async def set_member_oob(self, member, oob):
        return await self.config.member(member).OOB.set(oob)

    async def set_member_sentence(self, member, sentence):
        await self.config.member(member).Sentence.set(sentence)

    async def set_member_timeserved(self, member, times):
        await self.config.member(member).TimeS.set(times)

    async def save_targets(self, guild, targets):
        await self.config.guild(guild).Targets.set(targets)

    async def revive_member(self, member):
        await self.config.member(member).DeathT.set(0)

    async def get_guild_crew(self, guild):
        return await self.config.guild(guild).Crew()

    async def add_crew_member(self, member):
        cur = await self.config.guild(member.guild).Crew()
        cur[member.id] = {}
        await self.config.guild(member.guild).Crew.set(cur)
        return cur

    async def add_member_spree(self, member):
        cur = await self.config.member(member).Spree()
        cur += 1
        await self.config.member(member).Spree.set(cur)

    @staticmethod
    def time_format(seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        data = PluralDict({'hour': h, 'minute': m, 'second': s})
        if h > 0:
            fmt = "{hour} hour{hour(s)}"
            if data["minute"] > 0 and data["second"] > 0:
                fmt += ", {minute} minute{minute(s)}, and {second} second{second(s)}"
            if data["second"] > 0 == data["minute"]:
                fmt += ", and {second} second{second(s)}"
            msg = fmt.format_map(data)
        elif h == 0 and m > 0:
            if data["second"] == 0:
                fmt = "{minute} minute{minute(s)}"
            else:
                fmt = "{minute} minute{minute(s)}, and {second} second{second(s)}"
            msg = fmt.format_map(data)
        elif m == 0 and h == 0 and s > 0:
            fmt = "{second} second{second(s)}"
            msg = fmt.format_map(data)
        else:
            msg = "No Cooldown"
        return msg

    def cooldown_calculator(self, player_time, base_time):
        if abs(player_time - int(time.perf_counter())) >= base_time or player_time == 0:
            return "No Cooldown"
        else:
            s = abs(player_time - int(time.perf_counter()))
            seconds = abs(s - base_time)
            time_remaining = self.time_format(seconds)
            return time_remaining

    async def requirement_check(self, prefix, author, cost):
        # Theme variables
        config = await self.get_guild_settings(author.guild)
        theme = await self.get_guild_theme(author.guild)
        targets = await self.get_guild_targets(author.guild)
        crew = await self.config.guild(author.guild).Crew()

        t_jail = theme["Jail"]
        t_sentence = theme["Sentence"]
        t_police = theme["Police"]
        t_bail = theme["Bail"]
        t_crew = theme["Crew"]
        t_heist = theme["Heist"]

        alert, patrol_time = await self.police_alert(author.guild)
        if not list(targets):
            msg = ("Oh no! There are no targets! To start creating a target, use "
                   "{}heist createtarget.".format(prefix))
            return "Failed", msg
        elif config["Start"]:
            msg = ("A {0} is already underway. Wait for the current one to "
                   "end to plan another {0}.".format(t_heist))
            return "Failed", msg
        elif author.id in crew:
            msg = "You are already in the {}.".format(t_crew)
            return "Failed", msg
        elif await self.get_member_status(author) == "Apprehended":
            bail = await self.get_member_bailcost(author)
            sentence_raw = await self.get_member_sentence(author)
            time_served = await self.get_member_timeserved(author)
            remaining = self.cooldown_calculator(sentence_raw, time_served)
            sentence = self.time_format(sentence_raw)
            if remaining == "No Cooldown":
                msg = ("Looks like your {} is over, but you're still in {}! Get released "
                       "released by typing {}heist release .".format(t_sentence, t_jail, prefix))
            else:
                msg = ("You are in {0}. You are serving a {1} of {2}.\nYou can wait out "
                       "your remaining {1} of: {3} or pay {4} credits to finish your "
                       "{5}.".format(t_jail, t_sentence, sentence, remaining, bail, t_bail))
            return "Failed", msg
        elif await self.get_member_status(author) == "Dead":
            death_time = await self.get_member_deathtimer(author)
            base_timer = config["Death"]
            remaining = self.cooldown_calculator(death_time, base_timer)
            if remaining == "No Cooldown":
                msg = ("Looks like you are still dead, but you can revive at anytime by using the "
                       "command {}heist revive .".format(prefix))
            else:
                msg = ("You are dead. You can revive in:\n{}\nUse the command {}heist revive when "
                       "the timer has expired.".format(remaining, prefix))
            return "Failed", msg
        elif not await bank.get_balance(author) >= config["Cost"]:
            msg = ("You do not have enough credits to cover the costs of "
                   "entry. You need {} credits to participate.".format(cost))
            return "Failed", msg
        elif alert == "Hot":
            msg = ("The {} are on high alert after the last target. We should "
                   "wait for things to cool off before hitting another target.\n"
                   "Time Remaining: {}".format(t_police, patrol_time))
            return "Failed", msg
        else:
            return "Success", "Success"

    async def police_alert(self, guild):
        config = await self.get_guild_settings(guild)
        police_time = config["Police"]
        alert_time = config["Alert"]
        if config["Alert"] == 0:
            return "Clear", None
        elif abs(alert_time - int(time.perf_counter())) >= police_time:
            config["Alert"] = 0
            await self.config.guild(guild).Config.set(config)
            return "Clear", None
        else:
            s = abs(alert_time - int(time.perf_counter()))
            seconds = abs(s - police_time)
            remaining = self.time_format(seconds)
            return "Hot", remaining

    @staticmethod
    def heist_target(gtargets, guild, crew):
        groups = sorted([(x, y["Crew"]) for x, y in gtargets.items()], key=itemgetter(1))
        crew_sizes = [x[1] for x in groups]
        breakpoints = [x for x in crew_sizes if x != max(crew_sizes)]
        targets = [x[0] for x in groups]
        return targets[bisect.bisect_left(breakpoints, crew)]

    async def calculate_success(self, guild, target):
        targets = await self.config.guild(guild).Targets()
        crew = await self.config.guild(guild).Crew()
        success_rate = targets[target]["Success"]
        bonus = self.calculate_bonus(targets, crew, target)
        success_chance = int(success_rate) + bonus
        return success_chance

    @staticmethod
    def calculate_bonus(targets, crew, target):
        max_crew = targets[target]["Crew"]
        l_crew = len(crew)
        percent = int(100 * l_crew / max_crew)
        breakpoints = [20, 40, 60, 80, 100]
        bonus_amounts = [0, 1, 2, 3, 4, 5]
        return bonus_amounts[bisect.bisect_left(breakpoints, percent)]

    async def game_outcomes(self, guild, players, target):
        success_rate = await self.calculate_success(guild, target)
        crew = await self.config.guild(guild).Crew()
        config = await self.get_guild_settings(guild)
        good_out, bad_out = self.get_theme(config)
        results = []
        for player in players:
            chance = random.randint(1, 100)
            if chance <= success_rate:
                good_thing = random.choice(good_out)
                good_out.remove(good_thing)
                crew[player.id] = {"Name": escape(player.display_name, formatting=True), "Bonus": good_thing[1]}
                await self.config.guild(guild).Crew.set(crew)
                await self.add_member_spree(player)
                results.append(good_thing[0].format(escape(player.display_name, formatting=True)))
            else:
                bad_thing = random.choice(bad_out)
                dropout_msg = (bad_thing[0] + "```\n{0} dropped out of the game.```").format(escape(player.display_name, formatting=True))
                await self.failure_handler(player, bad_thing[1])
                del crew[str(player.id)]
                await self.config.guild(guild).Crew.set(crew)
                bad_out.remove(bad_thing)
                results.append(dropout_msg)
        return results

    def get_theme(self, config):
        theme = config["Theme"]
        with open(str(bundled_data_path(self)) + '/{}.txt'.format(theme)) as f:
            data = f.readlines()
            good = [list(literal_eval(line.replace("|Good| ", "")))
                    for line in data if line.startswith("|Good|")]
            bad = [list(literal_eval(line.replace("|Bad| ", "")))
                   for line in data if line.startswith("|Bad|")]
        return good, bad

    async def add_member_jail(self, member):
        cur = await self.config.member(member).JailC()
        cur += 1
        await self.config.member(member).JailC.set(cur)

    async def add_crim_level(self, member):
        cur = await self.config.member(member).CrimLevel()
        cur += 1
        await self.config.member(member).CrimLevel.set(cur)

    async def failure_handler(self, user, status):
        await self.config.member(user).Spree.set(0)
        config = await self.get_guild_settings(user.guild)

        if status == "Apprehended":
            await self.add_member_jail(user)
            bail_base = config["Bail"]
            offenses = await self.config.member(user).JailC()
            sentence_base = config["Sentence"]

            if offenses > 1:
                offenses = offenses - 1

            sentence = sentence_base * offenses
            bail = bail_base * offenses
            if await self.config.member(user).OOB():
                bail *= 3

            await self.config.member(user).Status.set("Apprehended")
            await self.config.member(user).BailC.set(bail)
            await self.config.member(user).Sentence.set(sentence)
            await self.config.member(user).TimeS.set(int(time.perf_counter()))
            await self.config.member(user).OOB.set(False)
            await self.add_member_jail(user)
            await self.add_crim_level(user)
        else:
            await self.run_death(user)


    async def run_death(self, user):
        await self.config.member(user).CrimLevel.set(0)
        await self.config.member(user).OOB.set(False)
        await self.config.member(user).BailC.set(0)
        await self.config.member(user).Sentence.set(0)
        await self.config.member(user).Status.set("Dead")
        await self.config.member(user).TotalDeaths.set(await self.config.member(user).TotalDeaths() +1)
        await self.config.member(user).JailC.set(0)
        await self.config.member(user).DeathT(int(time.perf_counter()))
        if (await self.config.guild(user.guild).Config())["Hardcore"]:
            await self.hardcore_handler(user)

    async def hardcore_handler(self, user):
        balance = await bank.get_balance(user)
        await bank.withdraw_credits(user, balance)

    async def message_handler(self, guild, crew, players):
        config = await self.get_guild_settings(guild)
        message_type = config["Crew"]
        if message_type == "Short":
            name_list = '\n'.join(escape(player.display_name, formatting=True) for player in players[:5])
            message = "{} crew members, including:```\n{}```".format(crew, name_list)
        elif message_type == "Long":
            name_list = '\n'.join(escape(player.display_name, formatting=True) for player in players)
            message = "{} crew members, including:```\n{}```".format(crew, name_list)
        else:
            message = "{} crew members".format(crew)
        return message

    async def show_results(self, ctx, guild, results):
        theme = await self.get_guild_theme(guild)
        t_heist = theme["Heist"]
        for result in results:
            await ctx.send(result)
            await asyncio.sleep(5)
        await ctx.send("The {} is now over. Distributing player spoils...".format(t_heist))
        await asyncio.sleep(5)

    async def calculate_credits(self, guild, players, target):
        crew = await self.config.guild(guild).Crew()
        targets = await self.get_guild_targets(guild)

        names = [escape(player.display_name, formatting=True) for player in players]
        bonuses = [subdict["Bonus"] for subdict in crew.values()]
        vault = targets[target]["Vault"]
        credits_stolen = int(int(vault) * 0.75 / len(crew))
        stolen_data = [credits_stolen] * len(crew)
        total_winnings = [x + y for x, y in zip(stolen_data, bonuses)]
        targets[target]["Vault"] -= credits_stolen * len(crew)
        credit_data = list(zip(names, stolen_data, bonuses, total_winnings))
        deposits = list(zip(players, total_winnings))
        await self.award_credits(deposits)
        return credit_data

    async def award_credits(self, deposits):
        for player in deposits:
            await bank.deposit_credits(player[0], player[1])

    async def check_server_settings(self, guild):
        cur = await self.config.guild(guild).Config()
        if not cur["Registered"]:
            cur["Registered"] = True
            await self.config.guild(guild).Config.set(cur)

    async def check_member_settings(self, member):
        if not await self.config.member(member).Registered():
            await self.config.member(member).Registered.set(True)

    @staticmethod
    def criminal_level(level):
        status = ["Greenhorn", "Renegade", "Veteran", "Commander", "War Chief", "Legend",
                  "Immortal"]
        breakpoints = [1, 10, 25, 50, 75, 100]
        return status[bisect.bisect_right(breakpoints, level)]

    async def theme_loader(self, guild, theme_name):
        config = await self.get_guild_settings(guild)
        keys = ["Jail", "OOB", "Police", "Bail", "Crew", "Sentence", "Heist", "Vault"]

        with open(str(bundled_data_path(self)) + '/{}.txt'.format(theme_name)) as f:
            data = f.readlines()
            theme = {k[:k.find('=')].strip(): k[k.find('=') + 1:].strip() for k in data if '=' in k}
            print(theme)

        if all(key in theme for key in keys):
            await self.config.guild(guild).Theme.set(theme)
            config["Theme"] = theme_name
            await self.config.guild(guild).Config.set(config)
            return "{} theme found. Heist will now use this for future games.".format(theme_name)
        else:
            return "Some keys were missing in your theme. Please check your txt file."

    async def vault_updater(self, bot):
        await bot.wait_until_ready()
        try:
            await asyncio.sleep(20)  # Start-up Time
            while True:
                servers = [x for x in bot.guilds if (await self.config.guild(x).Config())["Registered"]]
                for server in servers:
                    targets = await self.config.guild(server).Targets()
                    for target, settings in targets.items():
                        vault = settings["Vault"]
                        vault_max = settings["Vault Max"]
                        if vault < vault_max:
                            increment = int(vault_max * 0.04)
                            new_vault = min(vault + increment, vault_max)
                            targets[target]["Vault"] = new_vault
                    await self.config.guild(server).Targets.set_raw(value=targets)                        
                await asyncio.sleep(120)  # task runs every 120 seconds
        except asyncio.CancelledError:
            pass
