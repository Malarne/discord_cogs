from .webserver import WebServer
from redbot.core import checks, Config
import discord
from redbot.core import commands
import asyncio
from aiohttp import web
from . import __path__
import os


class WebLeveler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.web = WebServer(bot)
        self.bot.loop.create_task(self.web.make_webserver(__path__))

    def cog_unload(self):
        self.bot.loop.create_task(self.web.runner.cleanup())

