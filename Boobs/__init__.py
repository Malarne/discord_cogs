from .oboobs import OboobsC

def setup(bot):
    n = OboobsC(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.boob_knowlegde())
