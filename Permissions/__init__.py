from .permissions import Permissions


def setup(bot):
    n = Permissions(bot)
    bot.add_cog(n)
