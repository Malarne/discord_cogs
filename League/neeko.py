import asyncio
import aiohttp
from math import floor, ceil
import datetime

class Neeko:

    def __init__(self, api):
        self.url = "https://euw1.api.riotgames.com"
        self.api = api
        self.apistring = "?api_key={}".format(self.api)
        self.champlist = None


    async def get(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.json()

    async def get_summoner_id(self, name):
        request = self.url + "/lol/summoner/v3/summoners/by-name/{}".format(name) + self.apistring
        js = await self.get(request)
        return js["id"]

    async def get_account_id(self, name):
        request = self.url + "/lol/summoner/v3/summoners/by-name/{}".format(name) + self.apistring
        js = await self.get(request)
        return js["accountId"]

    async def top_champions_masteries(self, summoner):
        sumid = await self.get_summoner_id(summoner)
        request = self.url + "/lol/champion-mastery/v3/champion-masteries/by-summoner/{}".format(sumid) + self.apistring
        js = await self.get(request)
        return js

    async def mastery_score(self, summoner):
        sumid = await self.get_summoner_id(summoner)
        request = self.url + "/lol/champion-mastery/v3/scores/by-summoner/{}".format(sumid) + self.apistring
        js = await self.get(request)
        return js

    async def get_champion_name(self, idchamp):
        if self.champlist is None:
            versionurl = "https://ddragon.leagueoflegends.com/api/versions.json"
            version = await self.get(versionurl)
            request = f"http://ddragon.leagueoflegends.com/cdn/{version[0]}/data/en_US/champion.json"
            self.champlist = await self.get(request)
        champ = self.champlist["data"]
        if idchamp == -1:
            return "Aucun"
        for i in champ:
            if champ[i]["key"] == idchamp:
                return champ[i]["name"]

    async def get_champion_id(self, name):
        if self.champlist is None:
            request = self.url + "/lol/static-data/v3/champions" + self.apistring
            self.champlist = await self.get(request)
        champ = self.champlist["data"]
        for i in champ:
            if champ[i]["name"] == name:
                return champ[i]["id"]
        return "Champion inconnu"

    async def get_champion_mastery(self, summoner, idchamp):
        sumid = await self.get_summoner_id(summoner)
        request = self.url + "/lol/champion-mastery/v3/champion-masteries/by-summoner/{}/by-champion/{}".format(sumid, idchamp) + self.apistring
        js = await self.get(request)
        res = {}
        res["mastery"] = js["championLevel"]
        res["points"] = js["championPoints"]
        return res

    async def get_elo(self, summoner):
        sumid = await self.get_summoner_id(summoner)
        request = self.url + "/lol/league/v3/positions/by-summoner/{}".format(sumid) + self.apistring
        js = await self.get(request)
        if js != []:
            dct = js[0]
            res = dct["tier"] + " " + dct["rank"] + " " + str(dct["leaguePoints"]) + " LP"
        else:
            res = "Unranked"
        return res

    async def game_info(self, summoner):
        sumid = await self.get_summoner_id(summoner)
        request = self.url + "/lol/spectator/v3/active-games/by-summoner/{}".format(sumid) + self.apistring
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
        res["gamemode"] = "{} est actuellement en {}".format(summoner, gamemode)
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
            elo = await self.get_elo(sumname)
            if i["teamId"] == 100:
                res["team1"]["players"][name] = elo
            else:
                res["team2"]["players"][name] = elo
        return res
        ##except:
            ##return False

    async def get_match(self, matchid):
        request = self.url + "/lol/match/v3/matches/{}".format(matchid) + self.apistring
        js = await self.get(request)
        return js

    async def get_history(self, summoner):
        sumid = await self.get_account_id(summoner)
        request = self.url + "/lol/match/v3/matchlists/by-account/{}".format(sumid) + self.apistring
        js = await self.get(request)
        clean = {}
        roles = {
            "DUO_CARRY": "ADC",
            "DUO_SUPPORT": "Support"
        }
        count = 0
        for i in js["matches"]:
            tmp = {}
            tmp["champ"] = await self.get_champion_name(str(i["champion"]))
            tmp["role"] = i["lane"]
            if tmp["role"].lower() == "none":
                tmp["role"] = i["role"]
            match = await self.get_match(i["gameId"])
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
                tmp["resultat"] = "loose"
            userstat = tmpvar["stats"]
            tmp["kda"] = str(userstat["kills"]) + " kills, " + str(userstat["deaths"]) + " morts et " + str(userstat["assists"]) + " assists."
            tmp["stats"] = str(userstat["totalDamageDealt"]) + " dégats totaux infligés pour " + str(userstat["totalDamageTaken"]) + " dégats subis."
            tmp["golds"] = str(userstat["goldEarned"]) + " golds gagnés"
            clean[count] = tmp
            count += 1
            await asyncio.sleep(0.5)
        return clean
