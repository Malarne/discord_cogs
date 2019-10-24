from redbot.core import checks, Config
from redbot.core import commands
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
import discord
try:
    from vrchat_api import VRChatAPI
    from vrchat_api.jsonObject import WorldLocation
    from vrchat_api.util import getInstanceNumberFromId
except:
    raise Exception("Please install vrchat_api module from the link bellow !\nhttps://github.com/y23586/vrchat-api-python")

def check_credentials():
    async def predicate(ctx):
        cog = ctx.bot.get_cog("VRChat")
        if await cog.data.user(ctx.author).username():
            if await cog.data.user(ctx.author).password():
                return True
            else:
                raise commands.UserFeedbackCheckFailure(message="No password saved !")
        else:
            raise commands.UserFeedbackCheckFailure(message="No username saved !")
    return commands.check(predicate)

class VRChat(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        default_user = {
            "username": None,
            "password": None,
            "favs": []
        }
        self.data = Config.get_conf(self, identifier=9786451)
        self.data.register_user(**default_user)

    @commands.group()
    async def vrset(self, ctx):
        """Base command for setting VRChat credentials."""
        pass

    @vrset.command()
    async def username(self, ctx, *, username):
        """Set your VRChat username."""
        await self.data.user(ctx.author).username.set(username)
        await ctx.send(f"{ctx.author.display_name} VRChat username successfully set to: {username} !")

    @vrset.command()
    async def password(self, ctx, *, password):
        """Set your VRChat password.
        Might be a good idea to use that in DMs."""
        await self.data.user(ctx.author).password.set(password)
        await ctx.send("Password saved.")

    @vrset.command()
    async def addfav(self, ctx, *, usernames):
        """Add one or more favourites."""
        users = usernames.split()
        cur = await self.data.user(ctx.author).favs()
        cur.extend(users)
        await self.data.user(ctx.author).favs.set(cur)
        await ctx.send("Updated favorite friends list !\nCurrent friends:\n{}".format('\n'.join(cur)))

    @vrset.command()
    async def infos(self, ctx):
        """DM you the informations you saved."""
        name = await self.data.user(ctx.author).username()
        password = await self.data.user(ctx.author).password()
        await ctx.author.send(f"VRChat informations known for {ctx.author.mention}:\n Username: {name}\n Password: {password}")

    async def getUserByName(self, ctx, username):
        name = await self.data.user(ctx.author).username()
        password = await self.data.user(ctx.author).password()
        a = VRChatAPI(name, password)
        a.authenticate()
        return a.getUserById(username + "/name")

    @commands.command()
    @check_credentials()
    async def vrfavs(self, ctx):
        """Shows the status of your favorite people !"""
        favs = await self.data.user(ctx.author).favs()
        if not favs:
            return ctx.send("You have no favourites ... :(")
        display_list = []
        for i in favs:
            user = await self.getUserByName(ctx, i)
            emb = discord.Embed(title="Current user:", description=user.displayName)
            emb.add_field(name="Status:", value=str(user.status).split("Status.")[1] + "\n" + user.statusDescription if user.statusDescription else "")
            emb.set_thumbnail(url=user.currentAvatarThumbnailImageUrl)
            display_list.append(emb)
        await menu(ctx, display_list, DEFAULT_CONTROLS)


    @commands.command()
    @check_credentials()
    async def vrfriends(self, ctx):
        """Shows your currently online friends and the world they're in."""
        name = await self.data.user(ctx.author).username()
        password = await self.data.user(ctx.author).password()
        display_list = []
        a = VRChatAPI(name, password)
        a.authenticate()
        friends = a.getFriends(offline=False)
        locations = set([x.location for x in friends]) - set([WorldLocation("offline"), WorldLocation("private")])
        worldIds = set([x.worldId for x in locations])
        worlds = dict([(x, a.getWorldById(x)) for x in worldIds]) ### I might have stolen some lines from an example of the api
        friendsInLocations = dict([(x, list(filter(lambda y: y.location == x, friends))) for x in locations])
        for location, users in sorted(friendsInLocations.items(), key=lambda x: len(x[1]), reverse=True): ### What the fuck is that sort ? no idea
            emb = discord.Embed(title="List of friend in:", description=worlds[location.worldId].name + str(getInstanceNumberFromId(location.instanceId)))
            emb.add_field(name="Friends in this location:", value="\n".join([x.displayName for x in users]))
            emb.set_thumbnail(url=location.thumbnailImageUrl)
            display_list.append(emb)
        if display_list:
            await menu(ctx, display_list, DEFAULT_CONTROLS)
        else:
            await ctx.send("No friend online ... :(")

