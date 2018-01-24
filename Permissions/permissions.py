from redbot.core import checks, Config
import discord
from discord.ext import commands
from redbot.core.utils import mod
import asyncio
import datetime

class Permissions:

    def __init__(self, bot):
        self.bot = bot
        self.data = Config.get_conf(self, identifier=42)
        register_guild = {
            "commands_blocked" : [],
            "cogs_blocked" : []
        }
        register_channel = {
            "commands_allowed" : [],
            "commands_blocked" : [],
        }
        register_role = {
            "commands_allowed" : [],
            "commands_blocked" : [],
        }
        self.data.register_channel(**register_channel)
        self.data.register_role(**register_role)
        self.data.register_guild(**register_guild)


    async def __global_check(self, ctx):
        if ctx.author.id == self.bot.owner_id:
            return True
        command = ctx.command.name
        global_blacklist = await self.data.guild(ctx.guild).commands_blocked()
        global_cog = await self.data.guild(ctx.guild).cogs_blocked()
        if command in global_blacklist:
            return False
        else:
            for i in global_cog:
                if command in dir(self.bot.get_cog(i)):
                    return False
        chan_whitelist = await self.data.channel(ctx.channel).commands_allowed()
        chan_blacklist = await self.data.channel(ctx.channel).commands_blocked()
        if command in chan_whitelist:
            return True
        elif command in chan_blacklist:
            return False
        for i in ctx.author.roles:
            role_whitelist = await self.data.role(i).commands_allowed()
            role_blacklist = await self.data.role(i).commands_blocked()
            role_cog = await self.data.role(i).cogs_blocked()
            if command in role_whitelist:
                return True
            elif command in role_blacklist:
                return False
        return True

    @commands.group(invoke_without_command=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def perm(self, ctx):
        """Permissions manager"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @perm.group(invoke_without_command=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def cog(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @cog.command(name="deny")
    @checks.admin_or_permissions(manage_roles=True)
    async def deny_cog(self, ctx, cog : str):    
        if self.bot.get_cog(cog) is None:
            await ctx.send("Unknown cog")
        else:
            async with self.data.guild(ctx.guild).cogs_blocked() as bl:
                bl.append(cog)
                await ctx.send("Permission set")
                return

    @cog.command(name="reset")
    @checks.admin_or_permissions(manage_roles=True)
    async def reset_cog(self, ctx):
        await self.data.guild(ctx.guild).cogs_blocked.set([])
        await self.data.guild(ctx.guild).cogs_blocked.set([])
        await ctx.send("Successfully reset global cogs permissions")

    @perm.group(invoke_without_command=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def channel(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @channel.command(name="allow")
    @checks.admin_or_permissions(manage_roles=True)
    async def allow_channel(self, ctx, command : str, chan : discord.TextChannel):    
        if self.bot.get_command(command) is None:
            await ctx.send("Unknown command")
        else:
            bl = await self.data.channel(ctx.channel).commands_blocked()
            if command in bl:
                for i in range(len(bl)):
                    if bl[i] == command:
                        bl.pop(i)
                        await self.data.role(role).commands_blocked.set(bl)
                        return
                await self.data.channel(ctx.channel).commands_blocked.set(bl)
            async with self.data.channel(ctx.channel).commands_allowed() as wl:
                wl.append(command)
                await ctx.send("Permission set")
                return


    @channel.command(name="deny")
    @checks.admin_or_permissions(manage_roles=True)
    async def deny_channel(self, ctx, command : str, chan : discord.TextChannel):    
        if self.bot.get_command(command) is None:
            await ctx.send("Unknown command")
        else:
            wl = await self.data.channel(ctx.channel).commands_allowed()
            if command in wl:
                for i in range(len(wl)):
                    if wl[i] == command:
                        wl.pop(i)
                        await self.data.channel(ctx.channel).commands_allowed.set(bl)
                        return
            async with self.data.channel(ctx.channel).commands_blocked() as bl:
                bl.append(command)
                await ctx.send("Permission set")
                return

    @channel.command(name="reset")
    @checks.admin_or_permissions(manage_roles=True)
    async def reset_channel(self, ctx, chan : discord.TextChannel):
        await self.data.channel(chan).commands_allowed.set([])
        await self.data.channel(chan).commands_blocked.set([])
        await ctx.send("Successfully reset {} permissions".format(chan))


    @perm.group(invoke_without_command=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def role(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send_help()


    @role.command(name="allow")
    @checks.admin_or_permissions(manage_roles=True)
    async def allow_role(self, ctx, command : str, role : discord.Role):    
        if self.bot.get_command(command) is None:
            await ctx.send("Unknown command")
        else:
            bl = await self.data.role(role).commands_blocked()
            if command in bl:
                for i in range(len(bl)):
                    if bl[i] == command:
                        bl.pop(i)
                        await self.data.role(role).commands_blocked.set(bl)
                        return
            async with self.data.role(role).commands_allowed() as wl:
                wl.append(command)
                await ctx.send("Permission set")
                return


    @role.command(name="deny")
    @checks.admin_or_permissions(manage_roles=True)
    async def deny_role(self, ctx, command : str, role : discord.Role):    
        if self.bot.get_command(command) is None:
            await ctx.send("Unknown command")
        else:
            wl = await self.data.role(role).commands_allowed()
            if command in wl:
                for i in range(len(wl)):
                    if wl[i] == command:
                        wl.pop(i)
                        await self.data.role(role).commands_allowed.set(wl)
                        return
            async with self.data.role(role).commands_blocked() as bl:
                bl.append(command)
                await ctx.send("Permission set")
                return

    @role.command(name="reset")
    @checks.admin_or_permissions(manage_roles=True)
    async def reset_role(self, ctx, role : discord.Role):
        await self.data.role(role).commands_allowed.set([])
        await self.data.role(role).commands_blocked.set([])
        await ctx.send("Successfully reset {} permissions".format(role.mention))


        

    @perm.group(invoke_without_command=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def info(self, ctx):
        """Permissions infos:"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @info.command(name="role")
    @checks.admin_or_permissions(manage_roles=True)
    async def _role(self, ctx, role : discord.Role = None):
        if role is None:
            await ctx.send_help()
        elif role == None:
            await send_cmd_help(ctx)
            return
        else:
            msg = "```"
            async with self.data.role(role).commands_allowed() as wl:
                msg += "Allowed : \t" + ", ".join(wl) + "\n"
            async with self.data.role(role).commands_blocked() as bl:
                msg += "Blocked : \t" + ", ".join(bl)
            msg += "```"
            await ctx.send(msg)
            

    @info.command(name="channel")
    @checks.admin_or_permissions(manage_roles=True)
    async def _channel(self, ctx, chan : discord.TextChannel = None):
        if chan is None:
            await ctx.send_help()
        elif chan == None:
            await send_cmd_help(ctx)
            return
        else:
            msg = "```"
            async with self.data.channel(chan).commands_allowed() as wl:
                msg += "Allowed : \t" + ", ".join(wl) + "\n"
            async with self.data.channel(chan).commands_blocked() as bl:
                msg += "Blocked : \t" + ", ".join(bl)
            msg += "```"
            await ctx.send(msg)

    @info.command(name="cog")
    @checks.admin_or_permissions(manage_roles=True)
    async def _cog(self, ctx):
        msg = "```"
        async with self.data.guild(ctx.guild).cogs_blocked() as bl:
            msg += "Cogs Blocked : \t" + ", ".join(bl) + "\n"
        msg += "```"
        await ctx.send(msg)
            


    
            
