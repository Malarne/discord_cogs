from .vrchat import VRChat

def setup(bot):
    bot.add_cog(VRChat(bot))