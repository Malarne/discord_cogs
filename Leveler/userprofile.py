from redbot.core import Config
import asyncio
import discord


class UserProfile:

    def __init__(self):
        self.data = Config.get_conf(self, identifier=1099710897114110101)
        default_guild = {
            "channels": [],
            "roles": [],
            "database": []
        }
        default_member = {
            "exp": 0,
            "level": 1,
            "today": 0
        }
        self.data.register_member(**default_member)
        self.data.register_guild(**default_guild)

    async def _give_exp(self, member, exp):
        current = await self.data.member(member).exp()
        await self.data.member(member).exp.set(current + exp)
        await self._check_exp(member)

    async def _is_registered(self, member):
        async with self.data.guild(member.guild).database() as db:
            return member.id in db

    async def _register_user(self, member):
        data = await self.data.guild(member.guild).database()
        if data is None:
            await self.data.guild(member.guild).database.set([])
        async with self.data.guild(member.guild).database() as db:
            db.append(member.id)
        await self.data.member(member).exp.set(0)

    async def _check_exp(self, member):
        lvl = await self.data.member(member).level()
        lvlup = 5*((lvl-1)**2)+(50*(lvl-1)) +100
        xp = await self.data.member(member).exp()
        if xp >= lvlup:
            await self.data.member(member).level.set(lvl+1)
            lvl = await self.data.member(member).level()
            lvlup = 5*((lvl-1)**2)+(50*(lvl-1)) +100
            xp = await self.data.member(member).exp()
            if xp >= lvlup:
                await self._check_exp(member)

    async def _check_role_member(self, member):
        roles = await self.data.guild(member.guild).roles()
        lvl = await self.data.member(member).level()
        level_role = roles[(lvl%10)-1]
        try:
            if level_role in [x.id for x in member.roles]:
                return True
            else:
                await member.add_roles(discord.utils.get(member.guild.roles, id=level_role))
                return True
        except:
            return False

    async def _add_guild_role(self, guild, roleid):
        role = discord.utils.get(guild.roles, id=roleid)
        if role is None:
            return False
        async with self.data.guild(guild).roles() as rolelist:
            rolelist.append(roleid)
            return True

    async def _move_guild_role(self, guild, role, new):
        async with self.data.guild(guild).roles() as rolelist:
            del rolelist[rolelist.index(role)]
            rolelist.insert(new, role)

    async def _remove_guild_role(self, guild, role):
        async with self.data.guild(guild).roles() as rolelist:
            rolelist.remove(role)

    async def _get_guild_roles(self, guild):
        return await self.data.guild(guild).roles()

    async def _add_guild_channel(self, guild, channel):
        async with self.data.guild(guild).channels() as chanlist:
            chanlist.append(channel)

    async def _remove_guild_channel(self, guild, channel):
        async with self.data.guild(guild).channels() as chanlist:
            chanlist.remove(channel)

    async def _get_guild_channels(self, guild):
        return await self.data.guild(guild).channels()

    async def _get_exp(self, member):
        return await self.data.member(member).exp()

    async def _get_level(self, member):
        return await self.data.member(member).level()

    async def _get_xp_for_level(self, lvl):
        return 5 * ((lvl - 1) ** 2) + (50 * (lvl - 1)) + 100

    async def _get_level_exp(self, member):
        lvl = await self.data.member(member).level()
        return await self._get_xp_for_level(lvl)

    async def _get_today(self, member):
        return await self.data.member(member).today()

    async def _today_addone(self, member):
        await self.data.member(member).today.set(await self._get_today(member) + 1)

    async def _get_leaderboard(self, guild):
        datas = await self.data.all_members(guild)
        infos = sorted(datas, key=lambda x: datas[x]["exp"], reverse=True)
        res = []
        count = 1
        for i in infos:
            tmp = {}
            tmp["id"] = i
            cur = datas[i]
            tmp["xp"] = cur["exp"]
            tmp["lvl"] = cur["level"]
            tmp["today"] = cur["today"]
            res.append(tmp)
            count += 1
            if count == 10:
                break
        return res