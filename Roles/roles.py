from redbot.core import Config
import discord
from discord.ext import commands
from redbot.core.utils import mod
import asyncio

class Roles:
    def __init__(self, bot):
        self.bot = bot
        self.data = Config.get_conf(self, identifier=42)
        default_guild = {
            "roles": {},
            "colors": {}
        }
        self.data.register_guild(**default_guild)


    @commands.command()
    async def create_role(self, ctx, nomRole = None, text : bool = True, voc : bool = True, *, alias : str = None):
        """Crée un role et le rend accessible en utilisant la commande .role"""
        if await mod.is_mod_or_superior(self.bot, obj=ctx.author):
            await ctx.send("Vous n'avez pas l'autorisation de faire sa !")
            return
        async with self.data.guild(ctx.guild).roles() as roles:
            if nomRole in roles:
                await ctx.send("Ce rôle est déjà enregistré !")
                return
            if alias == None:
                alias = [nomRole]
            else:
                alias = alias.split(" ")
                alias.append(nomRole)
            for i in ctx.guild.roles:
                if i.name.lower() == nomRole.lower():
                    roles[nomRole] = alias
                    await ctx.send("Le role a bien été créé !")
                    return 0
            grade = await ctx.guild.create_role(name=nomRole)
            if text:
                ow = {
                    ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    ctx.guild.me: discord.PermissionOverwrite(read_messages=True),
                    grade: discord.PermissionOverwrite(read_messages=True)
                }
                await ctx.guild.create_text_channel(name=nomRole, overwrites=ow)
            if voc:
                ow = {
                    ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    ctx.guild.me: discord.PermissionOverwrite(read_messages=True),
                    grade: discord.PermissionOverwrite(read_messages=True)
                }
                nomVoc = chr(ord(nomRole[0]) - 32) + nomRole[1:]
                await ctx.guild.create_voice_channel(name=nomVoc, overwrites=ow)
            await ctx.send("Le role a bien été créé !")

    @commands.group(invoke_without_command=True)
    async def role(self, ctx, *, role):
        """Commande principale pour s'attribuer un role."""
        async with self.data.guild(ctx.guild).roles() as roles:
            for i in ctx.guild.roles:
                try:
                    if role in roles[i.name] or role.lower() == i.name.lower():
                        if i in ctx.author.roles:
                            await ctx.author.remove_roles(i)
                            await ctx.send("Vous avez bien été enlevé du rôle {} !".format(i.name))
                            return
                        else:
                            await ctx.author.add_roles(i)
                            await ctx.send("Vous avez bien été ajouté au rôle {} !".format(i.name))
                            return
                except:
                    pass

    @role.command(name="delete")
    async def _delete(self, ctx, role, deltext : bool = False, delvoc : bool = False):
        """Supprime un role du server et de la liste des roles attribuables."""
        async with self.data.guild(ctx.guild).roles() as roles:
            if role in roles:
                del roles[role]
                await discord.utils.get(ctx.guild, name=role).delete()
                if deltext:
                    channel = discord.utils.get(self.bot.get_all_channels(), name=role)
                    await channel.delete()
                if delvoc:
                    nomVoc = chr(ord(role[0]) - 32) + role[1:]
                    channel = discord.utils.get(self.bot.get_all_channels(), name=nomVoc)
                    await channel.delete()
                await ctx.send("Role supprimé")
            else:
                await ctx.send("Role inconnu. Le nom du grade correspondant est peut etre mauvais ?")
        


    @role.group(name="color", invoke_without_command=True)
    async def _color(self, ctx, *, role):
        """Commande principale pour s'attribuer une couleur."""
        async with self.data.guild(ctx.guild).colors() as colors:
##            try:
            for i in colors:
                grade = discord.utils.get(ctx.guild.roles, name=i)
                if grade in ctx.author.roles:
                    await ctx.author.remove_roles(grade)
                    await ctx.send("Vous n'avez plus la couleur {}".format(role))
                    return
                if role.lower() == "aucune":
                    ctx.send("Vous n'avez plus de couleur")
                    return
                if role.lower() in colors[i]:
                    await ctx.author.add_roles(grade)
                    await ctx.send("Vous avez maintenant la couleur {} !".format(role))
                    return
##            except:
##                await ctx.send("La commande a malheureusement rencontrée un bug inattendue. Signalez le à Malarne vite !")

    @_color.command(name="add")
    async def _color_add(self, ctx, color : int, *, alias : str = None):
        """Commande d'ajout de couleur attribuables."""
        if await mod.is_mod_or_superior(self.bot, obj=ctx.author):
            await ctx.send("Vous n'avez pas l'autorisation de faire sa !")
            return
        async with self.data.guild(ctx.guild).colors() as colors:
            if alias.split(" ")[0] in colors:
                await ctx.send("Cette couleur est déjà enregistrée !")
                return
            def checkrole(ctx, role):
                for i in ctx.guild.roles:
                    if i == role:
                        return False
                    else:
                        return True
            if alias == None:
                await ctx.send("Merci de mettre en alias au moins le nom de la couleur.")
                return
            else:
                lalias = alias.split(" ")
                colorname = alias.split(" ")[0].lower()
            dcolor = discord.Colour(color)
            if checkrole(ctx, colorname):
                grade = await ctx.guild.create_role(name=colorname, colour=dcolor)
                await grade.edit(position=(len(ctx.guild.roles)-21-len(colors)))
            else:
                grade = discord.utils.get(ctx.guild.roles, name=colorname)
            await ctx.send("Couleur ajoutée avec succès.")
            colors[colorname] = lalias

    @commands.command(pass_context = True)
    async def delcolor(self, ctx, color): #on supprime la couleur et le grade associé
        """Commande de suppression de couleur attribuable."""
        if await mod.is_mod_or_superior(self.bot, obj=ctx.author):
            await ctx.send("Vous n'avez pas l'autorisation de faire sa !")
            return
        async with self.data.guild(ctx.guild).colors() as colors:
            try:
                grade = discord.utils.get(ctx.guild.roles, name=color)
                await grade.delete()
                del colors[color]
                self.savejson()
                await ctx.send("Couleur supprimée.")
            except:
                await ctx.send("Couleur introuvable.")

    @commands.command(pass_context = True)
    async def kickrole(self, ctx, role): #Pour virer un grade de tout ceux qui l'ont sans le supprimer
        """Remove a given role to everyone having it."""
        if await mod.is_mod_or_superior(self.bot, obj=ctx.author):
            await ctx.send("Vous n'avez pas l'autorisation de faire sa !")
            return
        async with self.data.guild(ctx.guild).colors() as colors:
            grade = discord.utils.get(ctx.guild.roles, name=role)
            for j in ctx.guild.members:
                if grade in j.roles:
                    await j.remove_roles(grade)
            await ctx.send("Tous les grades {} ont été enlevés !".format(grade.name))   


    @_color.command(name="list",pass_context = True)
    async def _color_list(self, ctx):
        """List existing colors."""
        async with self.data.guild(ctx.guild).colors() as colors:
            msg = discord.Embed(title="Liste des couleurs disponibles:", color=3447003)
            desc = ""
            for i in colors:
                desc = desc + i + "\n"
            msg.description = desc
            await ctx.send(embed=msg)

    @role.command(name="list", pass_context = True)
    async def _role_list(self, ctx):
        """List existing roles."""
        async with self.data.guild(ctx.guild).roles() as roles:
            msg = discord.Embed(title="Liste des rôles existants:", color=3447003)
            desc = ""
            for i in roles:
                desc = desc + i + "\n"
            msg.description = desc
            await ctx.send(embed=msg)


    @commands.command()
    async def assign(self, ctx, role):
        if await mod.is_mod_or_superior(self.bot, obj=ctx.author):
            await ctx.send("Vous n'avez pas l'autorisation de faire sa !")
            return
        else:
            grade = discord.utils.get(ctx.guild.roles, name=role)
            for i in ctx.guild.members:
                await i.add_roles(grade)
                await asyncio.sleep(0.5)
                print("a")
            await ctx.send("Done")

