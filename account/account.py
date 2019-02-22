import re
import os
import discord
import datetime
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import send_cmd_help
from dateutil.parser import parse as dateParse
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
        self.umcoc = self.bot.get_server('378035654736609280')
        # self.uroles = []
        # for role in self.umcoc.roles:
        #     if role.color == discord.Color(0x3498db): # or role.color == keycolor:
        #         self.uroles.append(role)

    # 
    # @commands.command(name='getrolecolor', pass_context=True, hidden=True)
    # async def set_keyrole(self, ctx, role: discord.Role):
    #     if 'umcoc' not in self.nerdie:
    #         self.nerdie['umcoc'] = {'server' : '378035654736609280', 'rolecolor' : role.color}
    #         dataIO.save_json(self.profile, self.nerdie)
    #         await self.bot.say('umcoc stored')
    #     else:
    #         self.nerdie['umcoc'].update({'rolecolor' : role.colour})
    #         dataIO.save_json(self.profile, self.nerdie)
    #         await self.bot.say('umococ updated')
    #     await self.bot.say('role code: {}'.format(role.colour))
    #
    # @commands.command(name='testtitles', pass_context=True, hidden=True)
    # async def _titles(self, ctx, user: discord.User = None):
    #     if user is None:
    #         user = ctx.message.author
    #     if 'umcoc' in self.nerdie.keys():
    #         umcoc = self.bot.get_server(self.nerdie['umcoc']['server'])
    #         print('got server')
    #         umember = umcoc.get_member(user.id)
    #         titles = []
    #         for userrole in umember.roles:
    #             if userrole.color == self.nerdie['umcoc']['rolecolor']:
    #                 titles.append('\n{}'.format(userrole.name))
    #         await self.bot.say(''.join(titles))
    #     else:
    #         return

    @commands.group(name='account', aliases=('profile',), pass_context=True, invoke_without_command=True)
    async def _account(self, ctx, user: discord.Member = None):
        """CollectorVerse Account

        In-Game username
        CollectorVerse Roster Top 5 + Prestige
        Alliance, Job, Age, Gender, Timezone, About, Website, Playing Since
        """
        if ctx.invoked_subcommand is None:
            if not user:
                user = ctx.message.author
            if user.id not in self.nerdie:
                data = self._createuser(ctx, user)

            if 'MCOC username' in self.nerdie[user.id]:
                ingame = 'MCOC in-game id: {}'.format(self.nerdie[user.id]['MCOC username'])
            else:
                ingame = 'No MCOC in-game id registered.'
            data = discord.Embed(title="CollectorVerse Profile", colour=get_color(ctx), description='Discord user: {}#{}'.format(user.name, user.discriminator), url='https://discord.gg/umcoc')
            roster = await RosterUserConverter(ctx, user.mention).convert()
            if roster:
                data.add_field(name='Prestige', value=roster.prestige, inline=False)
                data.add_field(name='Top 5 Champs', value='\n'.join(roster.top5), inline=False)
            else:
                data.add_field(name='Prestige', value='User has no registerd CollectorVerse roster.\nUse the ``/roster`` command to get started.')
            for i in ['Alliance', 'Job', 'Recruiting', 'Age', 'Gender', 'Timezone', 'Phone', 'About', 'Other', 'Website']:
                if i in self.nerdie[user.id]:
                    data.add_field(name=i+":", value=self.nerdie[user.id][i])
                else:
                    pass
            if 'Started' in self.nerdie[user.id]:
                since = dateParse(self.nerdie[user.id]['Started'])
                days_since = (datetime.datetime.utcnow() - since).days
                data.add_field(name='Entered the Contest {}'.format(since.date()), value="Playing for {} days!".format(days_since))
            if user.avatar_url:
                data.set_author(name=ingame, url=user.avatar_url)
                data.set_thumbnail(url=user.avatar_url)
            else:
                data.set_author(name=ingame)
            data.add_field(name='Join the UMCOC community',value='https://discord.gg/umcoc', inline=False)
            data.set_footer(text='CollectorDevTeam - customize with /account update', icon_url=COLLECTOR_ICON)
            # umcoc = self.bot.get_server('378035654736609280')
            # uroles = umcoc.roles
            #
            #
            #
            # uroles = []
            # for role in self.uroles:
            #     if role in user.roles:
            #         uroles.append(role.name)
            #         print(role.name)
            # if len(uroles) > 0:
            #     data2 = discord.Embed(title="CollectorVerse Profile", colour=get_color(ctx), description='Discord user: {}#{}'.format(user.name, user.discriminator), url='https://discord.gg/umcoc')
            #     data2.add_field(name='UMCOC Verfied Titles', value='\n'.join(uroles), inline=True)
            #     data2.add_field(name='Join the UMCOC community',value='https://discord.gg/umcoc', inline=False)
            #     data2.set_footer(text='CollectorDevTeam - customize with /account update', icon_url=COLLECTOR_ICON)
            #     await PagesMenu.menu_start(self, [data, data2])
            # else:
            await PagesMenu.menu_start(self, [data])
        else:
            pass

    @_account.command(name='delete', pass_context=True, aliases=('remove', 'del',), invoke_without_command=True)
    async def _delete(self, ctx):
        '''Delete CollectorVerse account'''
        user = ctx.message.author
        if user.id in self.nerdie:
            question = 'Are you sure you want to delete your CollectorVerse account {}?'.format(user.name)
            answer = await PagesMenu.confirm(self, ctx, question)
            if answer:
                dropped = self.nerdie.pop(user.id, None)
                dataIO.save_json(self.profile, self.nerdie)
                data=discord.Embed(title="Congrats!:sparkles:", description="You have deleted your CollectorVerse account.", color=get_color(ctx))
            else:
                data=discord.Embed(title="Sorry!:sparkles:", description="You have no CollectorVerse account.", color=get_color(ctx))
            await PagesMenu.menu_start(self, [data])

    # @commands.group(name="update", pass_context=True, invoke_without_command=True)
    @_account.group(name="set", aliases=('update',), pass_context=True, invoke_without_command=True)
    async def _update(self, ctx):
        """Update your CollectorVerse account"""
        await send_cmd_help(ctx)

    @_update.command(pass_context=True)
    async def ingame(self, ctx, *, value):
        """What's your in-game MCOC username?"""
        key = "MCOC username"
        user = ctx.message.author

        if user.id not in self.nerdie:
            data = self._unknownuser(ctx, user)
        else:
            data = self._updateuser(ctx, key, value)
        await PagesMenu.menu_start(self, [data])

    @_update.command(pass_context=True, aliases=('os','iphone','android',))
    async def phone(self, ctx, *, value):
        """What's your device OS?
        iOS, Android, Both"""
        key = "Phone"
        user = ctx.message.author
        for i in ('ios', 'iphone', 'ipad', 'apple'):
            if i in value.lower():
                value = '<:ios:548619937296416789> '+value
                continue
        if 'android' in value.lower() or 'samsung' in value.lower():
            value = '<:android:548634644455882762> '+value
        elif 'both' in value.lower():
            value = '<:ios:548619937296416789> iOS & <:android:548634644455882762> Android'
        if user.id not in self.nerdie:
            data = self._unknownuser(ctx, user)
        else:
            data = self._updateuser(ctx, key, value)
        await PagesMenu.menu_start(self, [data])

    @_update.command(pass_context=True)
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
            data = self._updateuser(ctx, key, value)
            pass
        await PagesMenu.menu_start(self, [data])


    @_update.command(pass_context=True)
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
                    data = self._updateuser(ctx, key, valid[value])
                else:
                    data = self._updateuser(ctx, key, value)
        else:
            data = discord.Embed(colour=get_color(ctx))
            data.add_field(name="Error:warning:",value='Use one of the valid codes: lfa, lfm, merge.')
            data.set_footer(text='CollectorDevTeam',
                    icon_url=COLLECTOR_ICON)
        await PagesMenu.menu_start(self, [data])

    @_update.command(pass_context=True)
    async def timezone(self, ctx, *, value):
        """What's your UTC timezone?"""
        key = "Timezone"
        user = ctx.message.author
        if 'UTC+' in value or 'UTC-' in value:
            if user.id not in self.nerdie:
                data = self._unknownuser(ctx, user)
            else:
                data = self._updateuser(ctx, key, value)
        else:
            data = discord.Embed(colour=get_color(ctx))
            data.add_field(name="Error:warning:",value='Timezone value must be recorded in UTC+ or UTC- format.')
            data.set_footer(text='CollectorDevTeam',
                    icon_url=COLLECTOR_ICON)
        await PagesMenu.menu_start(self, [data])


    @_update.command(pass_context=True)
    async def about(self, ctx, *, about):
        """Tell us about yourself"""
        key = "About"
        value = about
        user = ctx.message.author

        if user.id not in self.nerdie:
            data = self._unknownuser(ctx, user)
        else:
            data = self._updateuser(ctx, key, value)
        await PagesMenu.menu_start(self, [data])

    @_update.command(pass_context=True)
    async def website(self, ctx, *, site):
        """Do you have a website?"""
        key = "Website"
        value = site
        user = ctx.message.author

        if ctx.message.author.id not in self.nerdie:
            data = self._unknownuser(ctx, user)
        else:
            data = self._updateuser(ctx, key, value)
        await PagesMenu.menu_start(self, [data])


    @_update.command(pass_context=True)
    async def age(self, ctx, *, age):
        """How old are you?"""
        key = "Age"
        value = age
        user = ctx.message.author

        if ctx.message.author.id not in self.nerdie:
            data = self._unknownuser(ctx, user)
        else:
            data = self._updateuser(ctx, key, value)
        await PagesMenu.menu_start(self, [data])


    @_update.command(pass_context=True)
    async def job(self, ctx, *, job):
        """Do you have an alliance job?"""
        key = "Job"
        value = job
        user = ctx.message.author

        if ctx.message.author.id not in self.nerdie:
            data = self._unknownuser(ctx, user)
        else:
            data = self._updateuser(ctx, key, value)
        await PagesMenu.menu_start(self, [data])


    @_update.command(pass_context=True)
    async def gender(self, ctx, *, gender):
        """What's your gender?"""
        key = "Gender"
        value = gender
        user = ctx.message.author

        if ctx.message.author.id not in self.nerdie:
            data = self._unknownuser(ctx, user)
        else:
            data = self._updateuser(ctx, key, value)
        await PagesMenu.menu_start(self, [data])


    @_update.command(pass_context=True)
    async def started(self, ctx, *, started:str):
        """When did you start playing Contest of Champions?"""
        key = "Started"
        value = started
        started = dateParse(started)
        print(value)

        if isinstance(started, datetime.datetime):
            user = ctx.message.author
            if ctx.message.author.id not in self.nerdie:
                data = self._unknownuser(ctx, user)
            else:
                data = self._updateuser(ctx, key, value)
            await PagesMenu.menu_start(self, [data])
        else:
            await self.bot.say('Enter a valid date.')


    @_update.command(pass_context=True)
    async def other(self, ctx, *, other):
        """Incase you want to add anything else..."""
        key = "Other"
        value = other
        user = ctx.message.author

        if ctx.message.author.id not in self.nerdie:
            data = self._unknownuser(ctx, user)
        else:
            data = self._updateuser(ctx, key, value)
        await PagesMenu.menu_start(self, [data])

    def _createuser(self, ctx, user):
        self.nerdie[user.id] = {}
        dataIO.save_json(self.profile, self.nerdie)
        data = discord.Embed(colour=get_color(ctx))
        data.add_field(name="Congrats!:sparkles:", value="You have officaly created your CollectorVerse , {}.".format(user.mention))
        data.set_footer(text='CollectorDevTeam',
                icon_url=COLLECTOR_ICON)
        return data

    def _unknownuser(self, ctx, user):
        data = discord.Embed(colour=get_color(ctx))
        data.add_field(name="Error:warning:",value="Sadly, this feature is only available for people who had registered for an account. \n\nYou can register for a account today for free. All you have to do is say `{}signup` and you'll be all set.".format(ctx.prefix))
        data.set_footer(text='CollectorDevTeam',
                icon_url=COLLECTOR_ICON)
        return data

    def _updateuser(self, ctx, key, value):
        user = ctx.message.author
        data = discord.Embed(colour=get_color(ctx))
        if value in ('""',"''"," ","None","none","-",):
            self.nerdie[user.id].pop(key, None)
            data.add_field(name="Congrats!:sparkles:", value="You have deleted {} from your account.".format(key))
        else:
            self.nerdie[user.id].update({key : value})
            data.add_field(name="Congrats!:sparkles:",value="You have set your {} to {}".format(key, value))
        dataIO.save_json(self.profile, self.nerdie)
        data.set_footer(text='CollectorDevTeam',
                icon_url=COLLECTOR_ICON)
        return data

def get_color(ctx):
    if ctx.message.channel.is_private:
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
    f2 = "data/account/alliances.json"
    if not dataIO.is_valid_json(f):
        print("I'm creating the file, so relax bruh.")
        dataIO.save_json(f, data)
    if not dataIO.is_valid_json(f2):
        print("I'm creating the file, so relax bruh.")
        dataIO.save_json(f2, data)

def setup(bot):
    check_folder()
    check_file()
    bot.add_cog(Account(bot))
    # bot.add_cog(Alliance(bot))
