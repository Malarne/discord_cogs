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
            "commands_locked" : [],
            "commands_blocked" : [],
            "cogs_blocked" : []
        }
        register_channel = {
            "commands_allowed" : [],
            "commands_blocked" : [],
            "cogs_blocked" : []
        }
        register_role = {
            "commands_allowed" : [],
            "commands_blocked" : [],
            "cogs_blocked" : []
        }
        self.data.register_channel(**register_channel)
        self.data.register_role(**register_role)
        self.data.register_guild(**register_guild)


    async def __global_check(self, ctx):
        if ctx.author.id == self.bot.owner_id:
            return True
        tmp = False
        command = ctx.command.name
        global_blacklist = await self.data.guild(ctx.guild).commands_blocked()
        global_cog = await self.data.guild(ctx.guild).cogs_blocked()
        lock = await self.data.guild(ctx.guild).commands_locked()
        chan_whitelist = await self.data.channel(ctx.channel).commands_allowed()
        chan_blacklist = await self.data.channel(ctx.channel).commands_blocked()
        for i in ctx.author.roles:
            if i.name == "@everyone":
                pass
            else:
                role_whitelist = await self.data.role(i).commands_allowed()
                role_blacklist = await self.data.role(i).commands_blocked()
                role_cog = await self.data.role(i).cogs_blocked()
                for i in role_whitelist:
                    if i == command:
                        return True
                for i in role_blacklist:
                    if i == command:
                        tmp = True
                        pass
        everyone = discord.utils.get(ctx.author.roles, name="@everyone")
        everyone_whitelist = await self.data.role(everyone).commands_allowed()
        everyone_blacklist = await self.data.role(everyone).commands_blocked()
        everyone_cog = await self.data.role(everyone).cogs_blocked()
        for i in everyone_whitelist:
            if i == command:
                return True
        for i in everyone_blacklist:
            if i == command:
                return False            
        for i in lock:
            if i == command:
                return False
        for i in global_blacklist:
            if i == command:
                return False
        for i in global_cog:
            if command in dir(self.bot.get_cog(i)):
                return False
        for i in chan_whitelist:
            if i == command:
                return True
        for i in chan_blacklist:
            if i == command:
                return False
        if tmp:
            return False
        return True

    @commands.group(invoke_without_command=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def perm(self, ctx):
        """Permissions manager"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @perm.command()
    @checks.admin_or_permissions(manage_roles=True)
    async def lock(self, ctx, command : str):
        """Lock a command to be used only by owner."""
        if self.bot.get_command(command) is None:
            await ctx.send("Unknown command")
        else:
            async with self.data.guild(ctx.guild).commands_locked() as lock:
                lock.append(command)
                await ctx.send("Permission set")
                return

    @perm.group(invoke_without_command=True, name="global")
    @checks.admin_or_permissions(manage_roles=True)
    async def _global(self, ctx):
        """Manage permissions of the entire server."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @perm.group(name="command", invoke_without_command=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def _command(self, ctx):
        """Manage permissions of a command on the entire server."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @_command.command(name="deny")
    @checks.admin_or_permissions(manage_roles=True)
    async def deny_global(self, ctx, command : str):
        """Deny a command to the entire server."""
        if self.bot.get_command(command) is None:
            await ctx.send("Unknown command")
        else:
            bl = await self.data.guild(ctx.guild).commands_blocked()
            if command in bl:
                await ctx.send("Command is already in global blacklist !")
                return
            async with self.data.guild(ctx.guild).commands_blocked() as bl:
                bl.append(command)
                await ctx.send("Permission set")
                return


    @_global.group(name="cog")
    @checks.admin_or_permissions(manage_roles=True)
    async def _cog(self, ctx):
        """Manage cog permissions on the entire server."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @_cog.command(name="deny")
    @checks.admin_or_permissions(manage_roles=True)
    async def deny_cog(self, ctx, cog : str):
        """Deny use of a cog on the entire server."""
        if self.bot.get_cog(cog) is None:
            await ctx.send("Unknown cog")
        else:
            async with self.data.guild(ctx.guild).cogs_blocked() as bl:
                bl.append(cog)
                await ctx.send("Permission set")
                return

    @_cog.command(name="reset")
    @checks.admin_or_permissions(manage_roles=True)
    async def reset_cog(self, ctx):
        """Reset any denied cog configured."""
        await self.data.guild(ctx.guild).cogs_blocked.set([])
        await self.data.guild(ctx.guild).cogs_blocked.set([])
        await ctx.send("Successfully reset global cogs permissions")

    @perm.group(invoke_without_command=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def channel(self, ctx):
        """Manage per-channel permissions."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()

    @channel.command(name="allow")
    @checks.admin_or_permissions(manage_roles=True)
    async def allow_channel(self, ctx, command : str, chan : discord.TextChannel):
        """Allow a command to a specific channel."""
        if self.bot.get_command(command) is None:
            await ctx.send("Unknown command")
        else:
            bl = await self.data.channel(ctx.channel).commands_blocked()
            if command in bl:
                for i in bl:
                    if i == command:
                        bl.pop(i)
                        await self.data.channel(ctx.channel).commands_blocked.set(bl)
                        break
            async with self.data.channel(ctx.channel).commands_allowed() as wl:
                wl.append(command)
                await ctx.send("Permission set")
                return


    @channel.command(name="deny")
    @checks.admin_or_permissions(manage_roles=True)
    async def deny_channel(self, ctx, command : str, chan : discord.TextChannel):
        """Deny a command to a specific channel."""
        if self.bot.get_command(command) is None:
            await ctx.send("Unknown command")
        else:
            wl = await self.data.channel(ctx.channel).commands_allowed()
            if command in wl:
                for i in range(len(wl)):
                    if wl[i] == command:
                        wl.pop(i)
                        await self.data.channel(ctx.channel).commands_allowed.set(wl)
                        return
            async with self.data.channel(ctx.channel).commands_blocked() as bl:
                bl.append(command)
                await ctx.send("Permission set")
                return

    @channel.command(name="reset")
    @checks.admin_or_permissions(manage_roles=True)
    async def reset_channel(self, ctx, chan : discord.TextChannel):
        """Reset permissions of a channel."""
        await self.data.channel(chan).commands_allowed.set([])
        await self.data.channel(chan).commands_blocked.set([])
        await ctx.send("Successfully reset {} permissions".format(chan))


    @perm.group(invoke_without_command=True)
    @checks.admin_or_permissions(manage_roles=True)
    async def role(self, ctx):
        """Manage per-role permissions."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()


    @role.command(name="allow")
    @checks.admin_or_permissions(manage_roles=True)
    async def allow_role(self, ctx, command : str, role : discord.Role):
        """Allow a command to be used by a specific role."""
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
        """Deny a command to be used by a specific role."""
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
        """Reset permissions of a role."""
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
        """Shows permissions set up to a role."""
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
        """Shows permissions set up to a channel."""
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

    @info.command(name="global")
    @checks.admin_or_permissions(manage_roles=True)
    async def _global_(self, ctx):
        """Shows permissions set up to the entire server."""
        msg = "```"
        async with self.data.guild(ctx.guild).cogs_blocked() as bl:
            msg += "Cogs Blocked : \t" + ", ".join(bl) + "\n"
        async with self.data.guild(ctx.guild).commands_blocked() as bl:
            msg += "Blocked : \t" + ", ".join(bl)
        msg += "```"
        await ctx.send(msg)
            


    
            
