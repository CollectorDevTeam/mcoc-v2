import discord
import datetime
from discord.ext import commands
from .utils.dataIO import dataIO
from .utils import checks
from __main__ import send_cmd_help
from dateutil.parser import parse as dateParse
import re
import os
from .utils.chat_formatting import *
from .hook import RosterUserConverter
import cogs.mcocTools
from .mcocTools import (KABAM_ICON, COLLECTOR_ICON, PagesMenu)

class Alliance:
    """The CollectorVerse Alliance Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.alliances = "data/account/alliances.json"
        self.guilds = dataIO.load_json(self.alliances)
        # COLLECTOR_ICON='https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/cdt_icon.png'

    @commands.group(name='alliance', aliases=('clan','guild'), pass_context=True, invoke_without_command=True, hidden=False)
    async def _alliance(self, ctx, user : discord.Member=None):
        """[ALPHA] CollectorVerse Alliance tools

        """
        server = ctx.message.server
        if ctx.invoked_subcommand is None:
            await self._present_alliance(ctx, user)

#             if not user:
#                 user = ctx.message.author
#             # if server.id not in self.guilds:
#             #     data = self._createserver(server)
#
#             # if 'MCOC username' in self.guilds[user.id]:
#             #     ingame = 'MCOC in-game id: {}'.format(self.guilds[user.id]['MCOC username'])
#             # else:
#             #     ingame = 'No MCOC in-game id registered.'
#             # data = discord.Embed(title="CollectorVerse Profile", colour=get_color(ctx), description='Discord user: {}#{}'.format(user.name, user.discriminator), url='https://discord.gg/umcoc')
#             # roster = await RosterUserConverter(ctx, user.mention).convert()
#             # if roster:
#             #     data.add_field(name='Prestige', value=roster.prestige, inline=False)
#             #     data.add_field(name='Top 5 Champs', value='\n'.join(roster.top5), inline=False)
#             # else:
#             #     data.add_field(name='Prestige', value='User has no registerd CollectorVerse roster.\nUse the ``/roster`` command to get started.')
#             # for i in ['Alliance', 'Job', 'Recruiting', 'Age', 'Gender', 'Timezone', 'About', 'Other', 'Website']:
#             #     if i in self.guilds[user.id]:
#             #         data.add_field(name=i+":", value=self.guilds[user.id][i])
#             #     else:
#             #         pass
#             # if 'Started' in self.guilds[user.id]:
#             #     since = datetime.datetime(self.guilds[user.id]['Started'])
#             #     days_since = (datetime.datetime.utcnow() - since).days
#             #     # data.add_field(name='Entered the Contest {}'.format(since.date()), value="Playing for {} days!".format(days_since))
#             #
#             # if user.avatar_url:
#             #     # name = str(user)
#             #     # name = user.n
#             #     # name = " ~ ".join((name, user.nick)) if user.nick else name
#             #     data.set_author(name=ingame, url=user.avatar_url)
#             #     data.set_thumbnail(url=user.avatar_url)
#             # else:
#             #     data.set_author(name=ingame)
#
#
#             # elif user == ctx.message.author:
#             #     data = self._unknownuser(ctx, user)
#             # else:
#             #     try:
#             #         data = discord.Embed(colour=get_color(ctx))
#             #     except:
#             #         data = discord.Embed(colour=discord.Color.gold())
#             #     data.add_field(name="Error:warning:",value="{} doesn't have an account at the moment, sorry.".format(user.mention))
#
#             # data.add_field(name='Join the UMCOC community',value='https://discord.gg/umcoc', inline=False)
#             # data.set_footer(text='CollectorDevTeam - customize with /account update',
#             #         icon_url=COLLECTOR_ICON)
#             # await PagesMenu.menu_start(self, [data])
#
    @checks.admin_or_permissions(manage_server=True)
    @_alliance.command(name='delete', pass_context=True, aliases=('remove', 'del','rm'), invoke_without_command=True, no_pm=True)
    async def _delete(self, ctx):
        '''Delete CollectorVerse Alliance'''
        server = ctx.message.server
        if server.id in self.guilds:
            question = '{}, are you sure you want to deregsister {} as your CollectorVerse Alliance?'.format(ctx.message.author.mention, server.name)
            answer = await PagesMenu.confirm(self, ctx, question)
            if answer:
                dropped = self.guilds.pop(server.id, None)
                dataIO.save_json(self.alliances, self.guilds)
                data=discord.Embed(title="Congrats!:sparkles:", description="You have deleted your CollectorVerse Alliance.", color=get_color(ctx))
            else:
                data=discord.Embed(title="Sorry!:sparkles:", description="You have no CollectorVerse Alliance.", color=get_color(ctx))
            await PagesMenu.menu_start(self, [data])

    async def _present_alliance(self, ctx, user):
        ## 1 search for user in registered alliances
        ## 2 if user in alliance:
        ##    if ctx.server == alliance:
        ##         present full info
        ##      if ctx.server != alliance:
        ##         present public info
        await self.bot.say('testing alliance presentation')
        if user is None:
            user = ctx.message.author
        server = ctx.message.server
        alliances = self._find_alliance(user) #list

        if alliances is None:
            data = discord.Embed(color=get_color(ctx), title='CollectorVerse Alliances', description='User is not regisered with a Collectorverse alliance.', url='https://discord.gg/umcoc')
        else:
            for alliance in alliances:
                guild = self.guilds[alliance]
                # s = discord.Client.get_server(alliance)
                # members = discord.Client._get_members(s)

                ## need a function to update all alliance roles + members

                if server.id == alliance.id and user.id in guild:  #Alliance server & Alliance member
                    if members is None:
                        await self.bot.say('No alliances found')
                    else:
                        data = discord.Embed(color=get_color(ctx), title='CollectorVerse Alliances', description='Display private profile ~ All kinds of info stored', url='https://discord.gg/umcoc')
                        for m in members.keys():
                            data.add_field(name=m.title(), value='\n'.join(members[m]))
                if server.id == alliance.id: #Alliance server visitor
                    data = discord.Embed(color=get_color(ctx), title='CollectorVerse Alliances', description='Display Alliance Server recruiting profile', url='https://discord.gg/umcoc')
                    publiclist = ['name','tag','founded','leader','invitation','recruiting']
                    for public in publiclist:
                        if public in guild:
                            data.add_field(name=public.title(),value=guild[public])
                else: #Alliance stranger
                    data = discord.Embed(color=get_color(ctx), title='CollectorVerse Alliances', description='Display public profile.\nInclude server join link, if set.\nInclude Alliance Prestige\nInclude About\n etc', url='https://discord.gg/umcoc')
                data.set_footer(text='CollectorDevTeam', icon_url=COLLECTOR_ICON)
                await PagesMenu.menu_start(self, [data])

    def _find_alliance(self, user):
        '''Returns a list of Server IDs or None'''
        alliances = []
        guilds = self.guilds
        for g in guilds.keys():
            if user.id in guilds[g]:
                discord.Client.get_server(g)
                alliances.append(g)
                print('debug: found user\'s alliances')
                return alliances
        print('debug: found no alliance')
        return None

    def _get_members(self, server):
        if server.id  in self.guilds:
            members = server.members
            jobs = {'officers':[], 'bg1':[], 'bg2':[], 'bg3':[]}
            for job in jobs.keys():
                if job in self.guilds[server.id]:
                    roles = server.roles
                    for r in roles:
                        if r.id == self.guilds[server.id]:
                            for m in members:
                                if r in member.roles:
                                    jobs[job].append(m.name)
                self.guilds[server.id][job]['members'] = jobs[job]
                # else:
                #     pass
            dataIO.save_json(self.alliances, self.guilds)
            print('Members saved for {}'.format(self.guilds[server.id][r]))
            return
        else:
            data = self._unknownguild(ctx, server)
            return None

    @checks.admin_or_permissions(manage_server=True)
    @_alliance.command(name="register", pass_context=True, invoke_without_command=True, no_pm=True)
    async def _reg(self, ctx):
        """[ALPHA] Sign up to register your Alliance server!"""
        user = ctx.message.author
        server = ctx.message.server
        question = '{}, do you want to register this Discord Server as your Alliance Server?'.format(ctx.message.author.mention)
        answer = await PagesMenu.confirm(self, ctx, question)
        if answer is True:
            if server.id not in self.guilds:
                data = self._createalliance(ctx, server)
            else:
                data = discord.Embed(colour=get_color(ctx))
                data.add_field(name="Error:warning:",value="Opps, it seems like you already have an guild registered, {}.".format(user.mention))

            data.set_footer(text='CollectorDevTeam',
                    icon_url=COLLECTOR_ICON)
            await PagesMenu.menu_start(self, [data])
        else:
            return
#
#     # @commands.group(name="update", pass_context=True, invoke_without_command=True)
    @checks.admin_or_permissions(manage_server=True)
    @_alliance.group(name="set", aliases='update', pass_context=True, invoke_without_command=True, no_pm=True)
    async def _update(self, ctx):
        """Update your CollectorVerse Alliance"""
        await send_cmd_help(ctx)
#
    @_update.command(pass_context=True, name='name', aliases=('clanname','guildname',) ,no_pm=True)
    async def _alliancename(self, ctx, *, value):
        """What's your Alliance name?"""
        key = "guildname"
        server = ctx.message.server

        if server.id not in self.guilds:
            data = self._unknownuser(ctx, server)
        else:
            data = self._updateguilds(ctx, key, value)
        await PagesMenu.menu_start(self, [data])

    @_update.command(pass_context=True, name='tag')
    async def _alliancetag(self, ctx, *, value):
        """What's your Alliance tag? Only include the 5 tag characters."""
        key = "guildtag"
        # v = value.split('')
        if len(value) > 5:
            await self.bot.say('Clan Tag must be <= 5 characters.\nDo not include the \[ or \] brackets.')
        server = ctx.message.server
        if server.id not in self.guilds:
            data = self._unknownguild(ctx, server)
        else:
            data = self._updateguilds(ctx, key, value)
        await PagesMenu.menu_start(self, [data])

    @_update.command(pass_context=True, name='officers')
    async def _officers(self, ctx, *, value: discord.Role):
        """Which role are your Alliance Officers?"""
        key = "officers"
        server = ctx.message.server
        members = server.members
        if server.id not in self.guilds:
            data = self._unknownguild(ctx, server)
            await PagesMenu.menu_start(self, [data])
        else:
            package = []
            for m in members:
                if value in m.roles:
                    package.append(m.id)
            data = self._updateguilds(ctx, key, value.id)
            data2 = self._updateguilds(ctx, key+'members', '\n'.join(package))
            await PagesMenu.menu_start(self, [data, data2])
        # members = self._get_members(server)

    # @_update.command(pass_context=True, name='bg1', aliases=('battlegroup1',))
    # async def _bg1(self, ctx, *, value: discord.Role):
    #     """Which role is your Battlegroup 1?"""
    #     key = "bg1"
    #     server = ctx.message.server
    #     if server.id not in self.guilds:
    #         data = self._unknownguild(ctx, server)
    #     else:
    #         data = self._updateguilds(ctx, key, {value.id})
    #     await PagesMenu.menu_start(self, [data])
    #
    # @_update.command(pass_context=True, name='bg2', aliases=('battlegroup2',))
    # async def _bg2(self, ctx, *, value: discord.Role):
    #     """Which role is your Battlegroup 2?"""
    #     key = "bg2"
    #     server = ctx.message.server
    #     if server.id not in self.guilds:
    #         data = self._unknownguild(ctx, server)
    #     else:
    #         data = self._updateguilds(ctx, key, {value.id})
    #     await PagesMenu.menu_start(self, [data])
    #
    # @_update.command(pass_context=True, name='bg3', aliases=('battlegroup3',))
    # async def _bg3(self, ctx, *, value: discord.Role):
    #     """Which role is your Battlegroup 3?"""
    #     key = "bg3"
    #     server = ctx.message.server
    #     if server.id not in self.guilds:
    #         data = self._unknownguild(ctx, server)
    #     else:
    #         data = self._updateguilds(ctx, key, {value.id})
    #     await PagesMenu.menu_start(self, [data])
    #
    # @_update.command(pass_context=True, name='memberrole', aliases=('members','alliance',))
    # async def _memberrole(self, ctx, value: discord.Role):
    #     """Which role represents all members of your alliance (up to 30)?"""
    #     key = "memberrole"
    #     server = ctx.message.server
    #     if server.id not in self.guilds:
    #         data = self._unknownguild(ctx, server)
    #     else:
    #         data = self._updateguilds(ctx, key, {value.id})
    #     await PagesMenu.menu_start(self, [data])
#
    def _createalliance(self, ctx, server):

        self.guilds[server.id] = {}
        dataIO.save_json(self.alliances, self.guilds)
        data = discord.Embed(colour=get_color(ctx))
        data.add_field(name="Congrats!:sparkles:", value="{}, you have officaly registered {} as a CollectorVerse Alliance.".format(ctx.message.author.mention, server.name))
        data.set_footer(text='CollectorDevTeam',
                icon_url=COLLECTOR_ICON)
        return data

    def _unknownguild(self, ctx, user):
        data = discord.Embed(colour=get_color(ctx))
        data.add_field(name="Error:warning:",value="Sadly, this feature is only available for Discord server owners who registerd for an Alliance. \n\nYou can register for a account today for free. All you have to do is:\nCreate a Discord server.\nInvite Collector\nOn your Alliance server say `{} alliance signup` and you'll be all set.".format(ctx.prefix))
        data.set_footer(text='CollectorDevTeam',
                icon_url=COLLECTOR_ICON)
        return data

    def _updateguilds(self, ctx, key, value):
        server = ctx.message.server
        data = discord.Embed(colour=get_color(ctx))
        if value in ('""',"''"," ","None","none","-",):
            self.guilds[server.id].pop(key, None)
            data.add_field(name="Congrats!:sparkles:", value="You have deleted {} from your Alliance.".format(key))
        else:
            self.guilds[server.id].update({key : value})
            data.add_field(name="Congrats!:sparkles:",value="You have set your {} to {}".format(key, value))
        dataIO.save_json(self.alliances, self.guilds)
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
    # bot.add_cog(Account(bot))
    bot.add_cog(Alliance(bot))