from .leveler import Leveler


def setup(bot):
    bot.add_cog(Leveler(bot))
