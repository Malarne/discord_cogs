from .anarchy import Anarchy

def setup(bot):
    n = Anarchy(bot)
    bot.add_cog(n)