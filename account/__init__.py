from .account import Account

def setup(bot):
    bot.add_cog(Account(bot))