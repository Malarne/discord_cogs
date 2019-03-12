from aiohttp import web
import json
import asyncio
import os
from shutil import copyfile
import discord


class WebServer:
    def __init__(self, bot):
        self.app = web.Application()
        self.bot = bot
        self.port = 6969
        self.handler = None
        self.runner = None
        self.site = None
        self.div = ""
        self.body = None
        self.var = 0

    def __unload(self):
        self.bot.loop.create_task(self.runner.cleanup())

    def get_body(self, path, reset: bool = False):
        if self.body is None or reset == True:
            folder = path[0]
            basic = os.path.join(folder, "index.html")
            body = open(basic, "r", encoding="utf-8").read()
            self.body = body
            return self.body
        else:
            return self.body

    async def make_webserver(self, path):
        cog = self.bot.get_cog("Leveler")
        stats = cog.profiles

        async def page(request):
            body = self.get_body(path, True)
            self.body = body
            return web.Response(text=body, content_type="text/html")

        # expects a { results: [ <server1>, <server2> ] } response
        # server object shape example - in frontend code
        async def list(requst):
            data = {}
            response = []
            for i in self.bot.guilds:
                data[i.id] = {}
                data[i.id] = await stats._get_leaderboard(i)
            for i in data:
                serverUsers = []
                for j in data[i]:
                    serverUsers.append(
                        {
                            "name": self.bot.get_user(j["id"]).display_name,
                            "xp": j["xp"],
                            "lvl": j["lvl"],
                        }
                    )

                response.append(
                    {"name": self.bot.get_guild(i).name, "users": serverUsers}
                )
            body = json.dumps({"results": response})
            return web.Response(text=body, content_type="application/json")

        # expects a { result: <userData> } or { error: <errorString> }
        # example object in the frontend code
        async def userinfo(request):
            usr = request.rel_url.query["name"]
            resp = {}
            srch = discord.utils.get(self.bot.get_all_members(), name=usr)
            if srch is None:
                srch = discord.utils.get(self.bot.get_all_members(), id=int(usr))
            if srch is None:
                resp["error"] = "Utilisateur inconnu"
            else:
                info = await cog.profile_data(srch)
                xp = info["xp"]
                nxp = info["nxp"]
                lvl = info["lvl"]
                ldb = info["ldb"]
                desc = info["desc"]
                roles = await stats._get_guild_roles(srch.guild)
                if len(roles) == 0:
                    default = await cog.profiles.data.guild(srch.guild).defaultrole()
                    elo = default if default else cog.defaultrole
                else:
                    if str(lvl) in roles.keys():
                        elo = discord.utils.get(
                            srch.guild.roles, id=roles[str(lvl)]
                        ).name
                    else:
                        tmp = 0
                        for k, v in roles.items():
                            if int(k) < lvl:
                                tmp = int(v)
                                pass
                        if tmp == 0:
                            elo = default if default else cog.defaultrole
                        else:
                            rl = discord.utils.get(srch.guild.roles, id=tmp)
                            elo = rl.name
                resp = {
                    "results": {
                        "lvl": lvl,
                        "xp": xp,
                        "nxp": nxp,
                        "elo": elo,
                        "ldb": ldb,
                        "desc": desc,
                    }
                }
            body = json.dumps(resp)
            return web.Response(text=body, content_type="application/json")

        await asyncio.sleep(3)
        self.app.router.add_get("/", page)
        self.app.router.add_get("/list", list)
        self.app.router.add_get("/info", userinfo)
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.handler = self.app.make_handler(debug=True)
        self.site = web.TCPSite(self.runner, "0.0.0.0", self.port)
        await self.site.start()
        print("WebTest started ...")

