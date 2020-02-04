import asyncio
import aiohttp
from math import floor, ceil
import datetime
from io import BytesIO
from redbot import version_info, VersionInfo

class Neeko:

    def __init__(self, bot):
        self.url = "https://{}.api.riotgames.com"
        self.api = None
        self.bot = bot
        self.champlist = None
        self._session = aiohttp.ClientSession()
        self.regions = {
            "br": "br1",
            "eune": "eun1",
            "euw": "euw1",
            "jp": "jp1",
            "kr": "kr",
            "lan": "la1",
            "las": "la2",
            "na": "na1",
            "oce": "oc1",
            "tr": "tr1",
            "ru": "ru",
            "pbe": "pbe1"
        }

    async def __unload(self):
        asyncio.get_event_loop().create_task(self._session.close())

    async def _get_api_key(self):
        if not self.api:
            if version_info >= VersionInfo.from_str("3.2.0"):
                db = await ctx.bot.get_shared_api_tokens("league")
            else:
                db = await ctx.bot.db.api_tokens.get_raw("league", default=None)
            self.api = db['api_key']
            return self.api
        else:
            return self.api

    async def apistring(self):
        apikey = await self._get_api_key()
        if apikey is None:
            return False
        else:
            return "?api_key={}".format(apikey)


    async def get(self, url):
        async with self._session.get(url) as response:
            return await response.json()

    async def get_summoner_puuid(self, region, name):
        apistr = await self.apistring()
        if region not in self.regions:
            return False
        request = self.url.format(self.regions[region]) + "/lol/summoner/v4/summoners/by-name/{}".format(name) + apistr
        js = await self.get(request)
        return js["puuid"]

    async def get_account_id(self, region, name):
        apistr = await self.apistring()
        if region not in self.regions:
            return False
        request = self.url.format(self.regions[region]) + "/lol/summoner/v4/summoners/by-name/{}".format(name) + apistr
        js = await self.get(request)
        return js["accountId"]

    async def get_summoner_id(self, region, name):
        apistr = await self.apistring()
        if region not in self.regions:
            return False
        request = self.url.format(self.regions[region]) + "/lol/summoner/v4/summoners/by-name/{}".format(name) + apistr
        js = await self.get(request)
        return js["id"]

    async def top_champions_masteries(self, region, summoner):
        sumid = await self.get_summoner_id(region, summoner)
        apistr = await self.apistring()
        if region not in self.regions:
            return False
        request = self.url.format(self.regions[region]) + "/lol/champion-mastery/v4/champion-masteries/by-summoner/{}".format(sumid) + apistr
        js = await self.get(request)
        return js

    async def mastery_score(self, region, summoner):
        sumid = await self.get_summoner_id(region, summoner)
        apistr = await self.apistring()
        if region not in self.regions:
            return False
        request = self.url.format(self.regions[region]) + "/lol/champion-mastery/v4/scores/by-summoner/{}".format(sumid) + apistr
        js = await self.get(request)
        return js

    async def get_champion_name(self, idchamp):
        if self.champlist is None:
            await self.update_champlist()
        champ = self.champlist["data"]
        if idchamp == -1:
            return "Aucun"
        for i in champ:
            if champ[i]["key"] == idchamp:
                return champ[i]["name"]

    async def update_champlist(self):
        versionurl = "https://ddragon.leagueoflegends.com/api/versions.json"
        version = await self.get(versionurl)
        request = f"http://ddragon.leagueoflegends.com/cdn/{version[0]}/data/en_US/champion.json"
        self.champlist = await self.get(request)

    async def get_champion_pic(self, champname):
        versionurl = "https://ddragon.leagueoflegends.com/api/versions.json"
        version = await self.get(versionurl)
        req = f"http://ddragon.leagueoflegends.com/cdn/{version[0]}/img/champion/{champname if (' ' not in champname) else ''.join(champname.split(' '))}.png"
        return req

    async def get_champion_id(self, *name):
        if self.champlist is None:
            await self.update_champlist()
        champ = self.champlist["data"]
        for i in champ:
            if champ[i]["name"] == name:
                return champ[i]["key"]
        return "Unknown character"

    async def get_champion_desc(self, champ):
        if self.champlist is None:
            await self.update_champlist()
        data = self.champlist["data"]
        for i in data:
            if data[i]["name"] == champ:
                return data[i]["blurb"]
        return "Unknown character"

    async def get_champion_mastery(self, region, summoner, idchamp):
        sumid = await self.get_summoner_id(region, summoner)
        apistr = await self.apistring()
        if region not in self.regions:
            return False
        request = self.url.format(self.regions[region]) + "/lol/champion-mastery/v4/champion-masteries/by-summoner/{}/by-champion/{}".format(sumid, idchamp) + apistr
        js = await self.get(request)
        res = {}
        res["mastery"] = js["championLevel"]
        res["points"] = js["championPoints"]
        return res

    async def get_elo(self, region, summoner):
        sumid = await self.get_summoner_id(region, summoner)
        apistr = await self.apistring()
        if region not in self.regions:
            return False
        request = self.url.format(self.regions[region]) + "/lol/league/v4/entries/by-summoner/{}".format(sumid) + apistr
        js = await self.get(request)
        res = []
        if js != []:
            for i in js:
                res.append(i["queueType"] + " : " + i["tier"] + " " + i["rank"] + " " + str(i["leaguePoints"]) + "LP")
        else:
            res = "Unranked"
        return res

    async def game_info(self, region, summoner):
        sumid = await self.get_summoner_id(region, summoner)
        apistr = await self.apistring()
        if region not in self.regions:
            return False
        request = self.url.format(self.regions[region]) + "/lol/spectator/v4/active-games/by-summoner/{}".format(sumid) + apistr
        js = await self.get(request)
        ##try:
        if js["gameMode"] == "CLASSIC":
            if js["gameType"] == "MATCHED_GAME":
                gamemode = "Ranked 5v5"
            else:
                gamemode = "Normal 5v5"
        else:
            gamemode = " ".join([js["gameMode"], js["gameType"]])
        res = {}
        res["gamemode"] = "{} is currently playing {}".format(summoner, gamemode)
        res["team1"] = {}
        res["team2"] = {}
        res["team1"]["bans"] = {}
        res["team2"]["bans"] = {}
        res["team1"]["players"] = {}
        res["team2"]["players"] = {}
        for i in js["bannedChampions"]:
            name = await self.get_champion_name(str(i["championId"]))
            if name is None:
                name = "No ban"
            if i["teamId"] == 100:
                res["team1"]["bans"][name] = i["pickTurn"]
            else:
                res["team2"]["bans"][name] = i["pickTurn"]
        for i in js["participants"]:
            sumname = i["summonerName"]
            champ = await self.get_champion_name(str(i["championId"]))
            name = sumname + ": " + champ
            elo = await self.get_elo(region, sumname)
            if i["teamId"] == 100:
                res["team1"]["players"][name] = "\n".join(elo) if (type(elo) == list) else elo
            else:
                res["team2"]["players"][name] = "\n".join(elo) if (type(elo) == list) else elo
        return res
        ##except:
            ##return False

    async def get_match(self, region, matchid):
        apistr = await self.apistring()
        if region not in self.regions:
            return False
        request = self.url.format(self.regions[region]) + "/lol/match/v4/matches/{}".format(matchid) + apistr
        js = await self.get(request)
        return js

    async def get_history(self, cpt, region, summoner):
        #print(f"cpt: {cpt}\nregion: {region} ({self.regions[region]})\nsummoner: {summoner}")
        sumid = await self.get_account_id(region, summoner)
        if not sumid:
            return False
        apistr = await self.apistring()
        if region not in self.regions:
            return False
        request = self.url.format(self.regions[region]) + "/lol/match/v4/matchlists/by-account/{}".format(sumid) + apistr
        js = await self.get(request)
        clean = {}
        count = 0
        for i in js["matches"]:
            tmp = {}
            tmp["champ"] = await self.get_champion_name(str(i["champion"]))
            tmp["role"] = i["lane"]
            if tmp["role"].lower() == "none":
                tmp["role"] = i["role"]
            match = await self.get_match(region, i["gameId"])
            osef = floor(match["gameDuration"]/60)
            tmp["Durée"] = str(osef) + ":" + str(match["gameDuration"] - (osef*60))
            tmp["Gamemode"] = match["gameMode"]
            ts = i["timestamp"] /1000
            tmp["horo"] = datetime.datetime.fromtimestamp(ts).strftime('%d-%m-%Y %H:%M:%S')
            champid = i["champion"]
            for k in match["participants"]:
                if k["championId"] == champid:
                    tmpvar = k
                    team = k["teamId"]
                    break
            for p in match["teams"]:
                if p["teamId"] == team:
                    winlose = p["win"]
                    break
            if winlose == "win":
                tmp["resultat"] = winlose
            else:
                tmp["resultat"] = "loss"
            userstat = tmpvar["stats"]
            tmp["kda"] = str(userstat["kills"]) + " kills / " + str(userstat["deaths"]) + " deaths / " + str(userstat["assists"]) + " assists."
            tmp["stats"] = str(userstat["totalDamageDealt"]) + " total damages dealt / " + str(userstat["totalDamageTaken"]) + " damages taken."
            tmp["golds"] = str(userstat["goldEarned"]) + " golds earned"
            clean[count] = tmp
            count += 1
            if count == cpt:
                return clean
            await asyncio.sleep(0.5)
        return clean
