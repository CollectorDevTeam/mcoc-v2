import discord
import datetime
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import send_cmd_help
from dateutil.parser import parse as dateParse
import os
from .utils.chat_formatting import *
from .hook import RosterUserConverter
import cogs.mcocTools
from .mcocTools import (KABAM_ICON, COLLECTOR_ICON, PagesMenu)

class Account:
    """The CollectorVerse Account Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.profile = "data/account/accounts.json"
        self.nerdie = dataIO.load_json(self.profile)
        self.COLLECTOR_ICON='https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/cdt_icon.png'

    @commands.group(name="account", aliases=('profile',), pass_context=True, invoke_without_command=True, no_pm=True)
    # @commands.group(name="account", aliases=('profile',), pass_context=True, invoke_without_command=True)
    async def _acc(self, ctx, user : discord.Member=None):
        """CollectorVerse Account

        In-Game username
        CollectorVerse Roster Top 5 + Prestige
        Alliance, Job, Age, Gender, Timezone, About, Website, Playing Since
        """

        if ctx.invoked_subcommand is None:
            if not user:
                user = ctx.message.author
            if user.id not in self.nerdie:
                data = self._createuser(user)

            if 'MCOC username' in self.nerdie[user.id]:
                ingame = 'MCOC in-game id: {}'.format(self.nerdie[user.id]['MCOC username'])
            else:
                ingame = 'No MCOC in-game id registered.'
            try:
                color = user.colour
            except:
                color = discord.Color.gold()
            data = discord.Embed(title="CollectorVerse Profile", colour=color, description='Discord user: {}#{}'.format(user.name, user.discriminator), url='https://discord.gg/umcoc')
            roster = await RosterUserConverter(ctx, user.mention).convert()
            if roster:
                data.add_field(name='Prestige', value=roster.prestige, inline=False)
                data.add_field(name='Top 5 Champs', value='\n'.join(roster.top5), inline=False)
            else:
                data.add_field(name='Prestige', value='User has no registerd CollectorVerse roster.\nUse the ``/roster`` command to get started.')
            for i in ['Alliance', 'Job', 'Recruiting', 'Age', 'Gender', 'Timezone', 'About', 'Other', 'Website']:
                if i in self.nerdie[user.id]:
                    data.add_field(name=i+":", value=self.nerdie[user.id][i])
                else:
                    pass
            # if 'Started' in self.nerdie[user.id]:
            #     since = datetime.datetime(self.nerdie[user.id]['Started'])
            #     days_since = (datetime.datetime.utcnow() - since).days
                # data.add_field(name='Entered the Contest {}'.format(since.date()), value="Playing for {} days!".format(days_since))

            if user.avatar_url:
                data.set_author(name=ingame, url=user.avatar_url)
                data.set_thumbnail(url=user.avatar_url)
            else:
                data.set_author(name=ingame)



            data.add_field(name='Join the UMCOC community',value='https://discord.gg/umcoc', inline=False)
            data.set_footer(text='CollectorDevTeam - customize with /account update',
                    icon_url=self.COLLECTOR_ICON)
            await self.bot.say(embed=data)

    # @_acc.commands(pass_context=True, name="delete")
    # async def _delete(self,ctx):
    #     '''Delete your CollectorVerse account'''
    #     user = ctx.message.author
    #     if user.id in self.nerdie:
    #         self.nerdie.pop(user.id, None)
    #         dataIO.save_json(self.profile, self.nerdie)
    #     data.add_field(name="Congrats!:sparkles:", value="You have deleted your CollectorVerse account.")


    # @commands.group(name="update", pass_context=True, invoke_without_command=True, no_pm=True)
    @_acc.group(name="update", pass_context=True, invoke_without_command=True, no_pm=True)
    async def update(self, ctx):
        """Update your CollectorVerse account"""
        await send_cmd_help(ctx)

    @update.command(pass_context=True, no_pm=True)
    async def ingame(self, ctx, *, value):
        """What's your in-game MCOC username?"""
        key = "MCOC username"
        user = ctx.message.author

        if user.id not in self.nerdie:
            data = self._unknownuser(ctx, user)
        else:
            data = self._updated(ctx, key, value)
        await self.bot.say(embed=data)

    @update.command(pass_context=True, no_pm=True)
    async def alliance(self, ctx, *, value=None):
        """What's your Alliance name?"""
        key = "Alliance"
        user = ctx.message.author
        if user.id not in self.nerdie:
            data = self._unknownuser(ctx, user)
        else:
            if "Recruiting" in self.nerdie[user.id]:
                if 'Looking for Alliance' in self.nerdie[user.id]["Recruiting"]:
                    self.nerdie[user.id].pop("Recruiting",None)
                    dataIO.save_json(self.profile, self.nerdie)
            data = self._updated(ctx, key, value)
            pass
        await self.bot.say(embed=data)


    @update.command(pass_context=True, no_pm=True)
    async def recruiting(self, ctx, *, value):
        """Are you Looking for Alliance or Members?
        lfa   = Looking for Alliance
        lfm   = Looking for members
        merge = Looking for Merger"""
        key = "Recruiting"
        user = ctx.message.author
        valid = {'lfa':'Looking for Alliance', 'lfm': 'Looking for Members', 'merge':'Looking for Merger'}
        if value in valid.keys():
            if user.id not in self.nerdie:
                data = self._unknownuser(ctx, user)
            else:
                if value in ('lfa','Looking for Alliance'):
                    self.nerdie[user.id].pop("Alliance",None)
                    dataIO.save_json(self.profile, self.nerdie)
                if value in ('lfa','lfm','merge'):
                    data = self._updated(ctx, key, valid[value])
                else:
                    data = self._updated(ctx, key, value)
        else:
            data = discord.Embed(colour=user.colour)
            data.add_field(name="Error:warning:",value='Use one of the valid codes: lfa, lfm, merge.')
            data.set_footer(text='CollectorDevTeam',
                    icon_url=self.COLLECTOR_ICON)
        await self.bot.say(embed=data)

    @update.command(pass_context=True, no_pm=True)
    async def timezone(self, ctx, *, value):
        """What's your UTC timezone?"""
        key = "Timezone"
        user = ctx.message.author
        if 'UTC+' in value or 'UTC-' in value:
            if user.id not in self.nerdie:
                data = self._unknownuser(ctx, user)
            else:
                data = self._updated(ctx, key, value)
        else:
            data = discord.Embed(colour=user.colour)
            data.add_field(name="Error:warning:",value='Timezone value must be recorded in UTC+ or UTC- format.')
            data.set_footer(text='CollectorDevTeam',
                    icon_url=self.COLLECTOR_ICON)
        await self.bot.say(embed=data)


    @update.command(pass_context=True, no_pm=True)
    async def about(self, ctx, *, about):
        """Tell us about yourself"""
        key = "About"
        value = about
        user = ctx.message.author

        if user.id not in self.nerdie:
            data = self._unknownuser(ctx, user)
        else:
            data = self._updated(ctx, key, value)
        await self.bot.say(embed=data)

    @update.command(pass_context=True, no_pm=True)
    async def website(self, ctx, *, site):
        """Do you have a website?"""
        key = "Website"
        value = site
        user = ctx.message.author

        if ctx.message.author.id not in self.nerdie:
            data = self._unknownuser(ctx, user)
        else:
            data = self._updated(ctx, key, value)
        await self.bot.say(embed=data)


    @update.command(pass_context=True, no_pm=True)
    async def age(self, ctx, *, age):
        """How old are you?"""
        key = "Age"
        value = age
        user = ctx.message.author

        if ctx.message.author.id not in self.nerdie:
            data = self._unknownuser(ctx, user)
        else:
            data = self._updated(ctx, key, value)
        await self.bot.say(embed=data)


    @update.command(pass_context=True, no_pm=True)
    async def job(self, ctx, *, job):
        """Do you have an alliance job?"""
        key = "Job"
        value = job
        user = ctx.message.author

        if ctx.message.author.id not in self.nerdie:
            data = self._unknownuser(ctx, user)
        else:
            data = self._updated(ctx, key, value)
        await self.bot.say(embed=data)


    @update.command(pass_context=True, no_pm=True)
    async def gender(self, ctx, *, gender):
        """What's your gender?"""
        key = "Gender"
        value = gender
        user = ctx.message.author

        if ctx.message.author.id not in self.nerdie:
            data = self._unknownuser(ctx, user)
        else:
            data = self._updated(ctx, key, value)
        await self.bot.say(embed=data)


    # @update.command(pass_context=True, no_pm=True)
    # async def started(self, ctx, *, started):
    #     """When did you start playing Contest of Champions?"""
    #     key = "Started"
    #     try:
    #         value = dateParse(started)
    #         print(value)
    #         user = ctx.message.author
    #         if ctx.message.author.id not in self.nerdie:
    #             data = self._unknownuser(ctx, user)
    #         else:
    #             data = self._updated(ctx, key, value)
    #         await self.bot.say(embed=data)
    #     except:
    #         await self.bot.say('Please enter a date.')


    @update.command(pass_context=True, no_pm=True)
    async def other(self, ctx, *, other):
        """Incase you want to add anything else..."""
        key = "Other"
        value = other
        user = ctx.message.author

        if ctx.message.author.id not in self.nerdie:
            data = self._unknownuser(ctx, user)
        else:
            data = self._updated(ctx, key, value)
        await self.bot.say(embed=data)

    def _createuser(self, user):
        self.nerdie[user.id] = {}
        dataIO.save_json(self.profile, self.nerdie)
        data = discord.Embed(colour=user.colour)
        data.add_field(name="Congrats!:sparkles:", value="You have officaly created your CollectorVerse account, {}.".format(user.mention))
        data.set_footer(text='CollectorDevTeam',
                icon_url=self.COLLECTOR_ICON)
        return data

    def _unknownuser(self, ctx, user):
        data = discord.Embed(colour=user.colour)
        data.add_field(name="Error:warning:",value="Sadly, this feature is only available for people who had registered for an account. \n\nYou can register for a account today for free. All you have to do is say `{}signup` and you'll be all set.".format(ctx.prefix))
        data.set_footer(text='CollectorDevTeam',
                icon_url=self.COLLECTOR_ICON)
        return data

    def _updated(self, ctx, key, value):
        user = ctx.message.author
        data = discord.Embed(colour=user.colour)
        if value in ('""',"''"," ","None","none","-",):
            self.nerdie[user.id].pop(key, None)
            data.add_field(name="Congrats!:sparkles:", value="You have deleted {} from your account.".format(key))
        else:
            self.nerdie[user.id].update({key : value})
            data.add_field(name="Congrats!:sparkles:",value="You have set your {} to {}".format(key, value))
        dataIO.save_json(self.profile, self.nerdie)
        data.set_footer(text='CollectorDevTeam',
                icon_url=self.COLLECTOR_ICON)
        return data

class Alliance:
    """The CollectorVerse Alliance Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.profile = "data/account/alliances.json"
        self.guild = dataIO.load_json(self.profile)
        self.COLLECTOR_ICON='https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/cdt_icon.png'



    @commands.group(name="alliance", aliases=('clan','guild'), pass_context=True, invoke_without_command=True, no_pm=True, hidden=True)
    # @commands.group(name="account", aliases=('profile',), pass_context=True, invoke_without_command=True)
    async def _alliance(self, ctx, user : discord.Member=None):
        """CollectorVerse Account

        In-Game username
        CollectorVerse Roster Top 5 + Prestige
        Alliance, Job, Age, Gender, Timezone, About, Website, Playing Since
        """
        server = ctx.message.server
        if ctx.invoked_subcommand is None:
            if not user:
                user = ctx.message.author
            # if server.id not in self.guild:
            #     data = self._createserver(server)

            # if 'MCOC username' in self.guild[user.id]:
            #     ingame = 'MCOC in-game id: {}'.format(self.guild[user.id]['MCOC username'])
            # else:
            #     ingame = 'No MCOC in-game id registered.'
            # try:
            #     color = user.colour
            # except:
            #     color = discord.Color.gold()
            # data = discord.Embed(title="CollectorVerse Profile", colour=color, description='Discord user: {}#{}'.format(user.name, user.discriminator), url='https://discord.gg/umcoc')
            # roster = await RosterUserConverter(ctx, user.mention).convert()
            # if roster:
            #     data.add_field(name='Prestige', value=roster.prestige, inline=False)
            #     data.add_field(name='Top 5 Champs', value='\n'.join(roster.top5), inline=False)
            # else:
            #     data.add_field(name='Prestige', value='User has no registerd CollectorVerse roster.\nUse the ``/roster`` command to get started.')
            # for i in ['Alliance', 'Job', 'Recruiting', 'Age', 'Gender', 'Timezone', 'About', 'Other', 'Website']:
            #     if i in self.guild[user.id]:
            #         data.add_field(name=i+":", value=self.guild[user.id][i])
            #     else:
            #         pass
            # if 'Started' in self.guild[user.id]:
            #     since = datetime.datetime(self.guild[user.id]['Started'])
            #     days_since = (datetime.datetime.utcnow() - since).days
            #     # data.add_field(name='Entered the Contest {}'.format(since.date()), value="Playing for {} days!".format(days_since))
            #
            # if user.avatar_url:
            #     # name = str(user)
            #     # name = user.n
            #     # name = " ~ ".join((name, user.nick)) if user.nick else name
            #     data.set_author(name=ingame, url=user.avatar_url)
            #     data.set_thumbnail(url=user.avatar_url)
            # else:
            #     data.set_author(name=ingame)


            # elif user == ctx.message.author:
            #     data = self._unknownuser(ctx, user)
            # else:
            #     try:
            #         data = discord.Embed(colour=user.colour)
            #     except:
            #         data = discord.Embed(colour=discord.Color.gold())
            #     data.add_field(name="Error:warning:",value="{} doesn't have an account at the moment, sorry.".format(user.mention))

            # data.add_field(name='Join the UMCOC community',value='https://discord.gg/umcoc', inline=False)
            # data.set_footer(text='CollectorDevTeam - customize with /account update',
            #         icon_url=self.COLLECTOR_ICON)
            # await self.bot.say(embed=data)

    # @_acc.commands(pass_context=True, name="delete")
    # async def _delete(self,ctx):
    #     '''Delete your CollectorVerse account'''
    #     user = ctx.message.author
    #     if user.id in self.guild:
    #         self.guild.pop(user.id, None)
    #         dataIO.save_json(self.profile, self.guild)
    #     data.add_field(name="Congrats!:sparkles:", value="You have deleted your CollectorVerse account.")

    @checks.admin_or_permissions(manage_server=True)
    @_alliance.command(name="register", pass_context=True, invoke_without_command=True, no_pm=True)
    async def _reg(self, ctx):
        """Sign up to register your Alliance server!"""
        user = ctx.message.author
        server = ctx.message.server

        if server.id not in self.guild:
            data = self._createalliance(server)
        else:
            data = discord.Embed(colour=user.colour)
            data.add_field(name="Error:warning:",value="Opps, it seems like you already have an guild registered, {}.".format(user.mention))

        data.set_footer(text='CollectorDevTeam',
                icon_url=self.COLLECTOR_ICON)
        await self.bot.say(embed=data)

    # @commands.group(name="update", pass_context=True, invoke_without_command=True, no_pm=True)
    @_alliance.group(name="update", pass_context=True, invoke_without_command=True, no_pm=True)
    async def update(self, ctx):
        """Update your CollectorVerse account"""
        await send_cmd_help(ctx)

    # @update.command(pass_context=True, no_pm=True)
    # async def ingame(self, ctx, *, value):
    #     """What's your in-game MCOC username?"""
    #     key = "MCOC username"
    #     user = ctx.message.author
    #
    #     if user.id not in self.guild:
    #         data = self._unknownuser(ctx, user)
    #     else:
    #         data = self._updated(ctx, key, value)
    #     await self.bot.say(embed=data)
    #
    # @update.command(pass_context=True, no_pm=True)
    # async def alliance(self, ctx, *, value=None):
    #     """What's your Alliance name?"""
    #     key = "Alliance"
    #     user = ctx.message.author
    #     if user.id not in self.guild:
    #         data = self._unknownuser(ctx, user)
    #     else:
    #         if "Recruiting" in self.guild[user.id]:
    #             if 'Looking for Alliance' in self.guild[user.id]["Recruiting"]:
    #                 self.guild[user.id].pop("Recruiting",None)
    #                 dataIO.save_json(self.profile, self.guild)
    #         data = self._updated(ctx, key, value)
    #         pass
    #     await self.bot.say(embed=data)
    #
    #
    # @update.command(pass_context=True, no_pm=True)
    # async def recruiting(self, ctx, *, value):
    #     """Are you Looking for Alliance or Members?
    #     lfa   = Looking for Alliance
    #     lfm   = Looking for members
    #     merge = Looking for Merger"""
    #     key = "Recruiting"
    #     user = ctx.message.author
    #     valid = {'lfa':'Looking for Alliance', 'lfm': 'Looking for Members', 'merge':'Looking for Merger'}
    #     if value in valid.keys():
    #         if user.id not in self.guild:
    #             data = self._unknownuser(ctx, user)
    #         else:
    #             if value in ('lfa','Looking for Alliance'):
    #                 self.guild[user.id].pop("Alliance",None)
    #                 dataIO.save_json(self.profile, self.guild)
    #             if value in ('lfa','lfm','merge'):
    #                 data = self._updated(ctx, key, valid[value])
    #             else:
    #                 data = self._updated(ctx, key, value)
    #     else:
    #         data = discord.Embed(colour=user.colour)
    #         data.add_field(name="Error:warning:",value='Use one of the valid codes: lfa, lfm, merge.')
    #         data.set_footer(text='CollectorDevTeam',
    #                 icon_url=self.COLLECTOR_ICON)
    #     await self.bot.say(embed=data)
    #
    # @update.command(pass_context=True, no_pm=True)
    # async def timezone(self, ctx, *, value):
    #     """What's your UTC timezone?"""
    #     key = "Timezone"
    #     user = ctx.message.author
    #     if 'UTC+' in value or 'UTC-' in value:
    #         if user.id not in self.guild:
    #             data = self._unknownuser(ctx, user)
    #         else:
    #             data = self._updated(ctx, key, value)
    #     else:
    #         data = discord.Embed(colour=user.colour)
    #         data.add_field(name="Error:warning:",value='Timezone value must be recorded in UTC+ or UTC- format.')
    #         data.set_footer(text='CollectorDevTeam',
    #                 icon_url=self.COLLECTOR_ICON)
    #     await self.bot.say(embed=data)
    #
    #
    # @update.command(pass_context=True, no_pm=True)
    # async def about(self, ctx, *, about):
    #     """Tell us about yourself"""
    #     key = "About"
    #     value = about
    #     user = ctx.message.author
    #
    #     if user.id not in self.guild:
    #         data = self._unknownuser(ctx, user)
    #     else:
    #         data = self._updated(ctx, key, value)
    #     await self.bot.say(embed=data)
    #
    # @update.command(pass_context=True, no_pm=True)
    # async def website(self, ctx, *, site):
    #     """Do you have a website?"""
    #     key = "Website"
    #     value = site
    #     user = ctx.message.author
    #
    #     if ctx.message.author.id not in self.guild:
    #         data = self._unknownuser(ctx, user)
    #     else:
    #         data = self._updated(ctx, key, value)
    #     await self.bot.say(embed=data)
    #
    #
    # @update.command(pass_context=True, no_pm=True)
    # async def age(self, ctx, *, age):
    #     """How old are you?"""
    #     key = "Age"
    #     value = age
    #     user = ctx.message.author
    #
    #     if ctx.message.author.id not in self.guild:
    #         data = self._unknownuser(ctx, user)
    #     else:
    #         data = self._updated(ctx, key, value)
    #     await self.bot.say(embed=data)
    #
    #
    # @update.command(pass_context=True, no_pm=True)
    # async def job(self, ctx, *, job):
    #     """Do you have an alliance job?"""
    #     key = "Job"
    #     value = job
    #     user = ctx.message.author
    #
    #     if ctx.message.author.id not in self.guild:
    #         data = self._unknownuser(ctx, user)
    #     else:
    #         data = self._updated(ctx, key, value)
    #     await self.bot.say(embed=data)
    #
    #
    # @update.command(pass_context=True, no_pm=True)
    # async def gender(self, ctx, *, gender):
    #     """What's your gender?"""
    #     key = "Gender"
    #     value = gender
    #     user = ctx.message.author
    #
    #     if ctx.message.author.id not in self.guild:
    #         data = self._unknownuser(ctx, user)
    #     else:
    #         data = self._updated(ctx, key, value)
    #     await self.bot.say(embed=data)
    #
    #
    # @update.command(pass_context=True, no_pm=True)
    # async def started(self, ctx, *, started):
    #     """When did you start playing Contest of Champions?"""
    #     key = "Started"
    #     try:
    #         value = dateParse(started)
    #         user = ctx.message.author
    #         if ctx.message.author.id not in self.guild:
    #             data = self._unknownuser(ctx, user)
    #         else:
    #             data = self._updated(ctx, key, value)
    #         await self.bot.say(embed=data)
    #     except:
    #         await self.bot.say('Please enter a date.')
    #
    #
    # @update.command(pass_context=True, no_pm=True)
    # async def other(self, ctx, *, other):
    #     """Incase you want to add anything else..."""
    #     key = "Other"
    #     value = other
    #     user = ctx.message.author
    #
    #     if ctx.message.author.id not in self.guild:
    #         data = self._unknownuser(ctx, user)
    #     else:
    #         data = self._updated(ctx, key, value)
    #     await self.bot.say(embed=data)

    def _createalliance(self, server):
        self.guild[server.id] = {}
        dataIO.save_json(self.profile, self.guild)
        data = discord.Embed(colour=get_color(ctx))
        data.add_field(name="Congrats!:sparkles:", value="You have officaly created your CollectorVerse Alliance account, {}.".format(user.mention))
        data.set_footer(text='CollectorDevTeam',
                icon_url=self.COLLECTOR_ICON)
        return data

    def _unknownguild(self, ctx, user):
        data = discord.Embed(colour=get_color(ctx))
        data.add_field(name="Error:warning:",value="Sadly, this feature is only available for people who had registered for an account. \n\nYou can register for a account today for free. All you have to do is say `{}signup` and you'll be all set.".format(ctx.prefix))
        data.set_footer(text='CollectorDevTeam',
                icon_url=self.COLLECTOR_ICON)
        return data

    # def _updated(self, ctx, key, value):
    #     user = ctx.message.author
    #     data = discord.Embed(colour=user.colour)
    #     if value in ('""',"''"," ","None","none","-",):
    #         self.guild[user.id].pop(key, None)
    #         data.add_field(name="Congrats!:sparkles:", value="You have deleted {} from your account.".format(key))
    #     else:
    #         self.guild[user.id].update({key : value})
    #         data.add_field(name="Congrats!:sparkles:",value="You have set your {} to {}".format(key, value))
    #     dataIO.save_json(self.profile, self.guild)
    #     data.set_footer(text='CollectorDevTeam',
    #             icon_url=self.COLLECTOR_ICON)
    #     return data

def get_color(ctx):
    if ctx.message.channel.is_private():
        return discord.Color.gold()
    else:
        return ctx.message.author.color

def check_folder():
    if not os.path.exists("data/account"):
        print("Creating data/account folder...")
        os.makedirs("data/account")

def check_file():
    data = {}
    f = "data/account/accounts.json"
    if not dataIO.is_valid_json(f):
        print("I'm creating the file, so relax bruh.")
        dataIO.save_json(f, data)

def setup(bot):
    check_folder()
    check_file()
    bot.add_cog(Account(bot))
    bot.add_cog(Alliance(bot))
