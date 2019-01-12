import discord
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import send_cmd_help
import os
from .utils.chat_formatting import *
from .hook import RosterUserConverter



class Account:
    """The CollectorVerse Account Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.profile = "data/account/accounts.json"
        self.nerdie = dataIO.load_json(self.profile)
        self.COLLECTOR_ICON='https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/cdt_icon.png'

    @commands.command(name="signup", pass_context=True, invoke_without_command=True, no_pm=True)
    async def _reg(self, ctx):
        """Sign up to get your own account today!"""
        user = ctx.message.author

        if user.id not in self.nerdie:
            data = self._createuser(user)
        else:
            data = discord.Embed(colour=user.colour)
            data.add_field(name="Error:warning:",value="Opps, it seems like you already have an account, {}.".format(user.mention))

        data.set_footer(text='CollectorDevTeam',
                icon_url=self.COLLECTOR_ICON)
        await self.bot.say(embed=data)

    @commands.command(name="account", aliases=('profile',), pass_context=True, invoke_without_command=True, no_pm=True)
    async def _acc(self, ctx, user : discord.Member=None):
        """Your/Others Account"""

        if not user:
            user = ctx.message.author

        if user.id in self.nerdie:
            data = discord.Embed(description="CollectorVerse Profile", colour=user.colour)
            for i in ['MCOC username', 'Alliance', 'Recruiting', 'Age', 'Gender', 'Timezone', 'About', 'Other', 'Website']:
                if i in self.nerdie[user.id]:
                    data.add_field(name=i+":", value=self.nerdie[user.id][i])
                else:
                    pass
            if user.avatar_url:
                name = str(user)
                name = " ~ ".join((name, user.nick)) if user.nick else name
                data.set_author(name=name, url=user.avatar_url)
                data.set_thumbnail(url=user.avatar_url)
            else:
                data.set_author(name=user.name)

            roster = await RosterUserConverter(ctx, user.mention).convert()
            if roster:
                data.add_field(name='Prestige', value=roster.prestige, inline=False)
                data.add_field(name='Top 5 Champs', value='\n'.join(roster.top5), inline=False)
            else:
                data.add_field(name='Prestige', value='User has no registerd CollectorVerse roster.\nUse the ``/roster`` command to get started.')

        elif user == ctx.message.author:
            data = self._unknownuser(ctx, user)
        else:
            data = discord.Embed(colour=user.colour)
            data.add_field(name="Error:warning:",value="{} doesn't have an account at the moment, sorry.".format(user.mention))

        data.set_footer(text='CollectorDevTeam',
                icon_url=self.COLLECTOR_ICON)
        await self.bot.say(embed=data)

    @commands.group(name="update", pass_context=True, invoke_without_command=True, no_pm=True)
    async def update(self, ctx):
        """Update your TPC"""
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
            data = self._updated(ctx, key, value)
            if self.nerdie[user.id]["Recruiting"] in ('Looking For Alliance',):
                self._updated(ctx, "Recruiting", None)
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
                    self._updated(ctx, "Alliance", None)
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
        """What's your timezone?"""
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
        """Do you have a job?"""
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


    @update.command(pass_context=True, no_pm=True)
    async def email(self, ctx, *, timezone):
        """What's your timezone?"""
        key = "Timezone"
        value = timezone
        user = ctx.message.author

        if ctx.message.author.id not in self.nerdie:
            data = self._unknownuser(ctx, user)
        else:
            data = self._updated(ctx, key, value)
        await self.bot.say(embed=data)


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
