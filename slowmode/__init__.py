from .Slowmode import Slowmode
from discord.ext import commands


def setup(bot: commands.Bot):
    n = Slowmode(bot)
    bot.add_listener(n.limiter, "on_message")
    bot.add_cog(n)
