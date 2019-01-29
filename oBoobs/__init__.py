from .oboobs import Oboobs

def setup(bot):
    n = Oboobs(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.boob_knowlegde())
