from .heist import Heist

def setup(bot):
    bot.add_cog(Heist(bot))