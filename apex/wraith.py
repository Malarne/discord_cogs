import aiohttp
import asyncio
from redbot import version_info, VersionInfo

class Wraith:

    def __init__(self, bot):
        self.url = "https://public-api.tracker.gg/apex/v1/standard/profile/5/"
        self._session = aiohttp.ClientSession()
        self.api = None
        self.bot = bot

    async def __unload(self):
        asyncio.get_event_loop().create_task(self._session.close())

    async def _get_api_key(self):
        if not self.api:
            if version_info >= VersionInfo.from_str("3.2.0"):
                db = await self.bot.get_shared_api_tokens("apex")
            else:
                db = await self.bot.db.api_tokens.get_raw("apex", default=None)
            self.api = db['api_key']
            return self.api
        else:
            return self.api

    async def api_key(self):
        if not self.api:
            return await self._get_api_key()
        else:
            return self.api

    
    async def get(self, url):
        async with self._session.get(url, headers={"TRN-Api-Key": await self.api_key()}) as response:
            return await response.json()

    async def get_infos(self, username):
        req = await self.get(self.url + username)
        res = []
        try:
            for i in req['data']['children']:
                tmp = {}
                charinfo = i['metadata']
                tmp['legend'] = charinfo['legend_name']
                tmp['icon_url'] = charinfo['icon']
                stats = []
                for j in i['stats']:
                    infos = j['metadata']
                    stats.append({'name': infos['key'], 'value': j['displayValue']})
                tmp['stats'] = stats
                res.append(tmp)
            return res
        except:
            return None