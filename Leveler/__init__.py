from .leveler import Leveler


def setup(bot):
    n = Leveler(bot)
    bot.add_listener(n.listener, "on_message")
    bot.add_cog(n)
