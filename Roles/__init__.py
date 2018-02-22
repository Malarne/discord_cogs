from .roles import Roles


def setup(bot):
    n = Roles(bot)
    bot.add_cog(n)
