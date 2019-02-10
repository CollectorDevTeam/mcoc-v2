import re
import os
import json
import datetime
import discord
from discord.ext import commands
from dateutil.parser import parse as dateParse
from __main__ import send_cmd_help
from .utils.dataIO import dataIO
from .utils import checks
# from .utils import chat_formatting as chat
from .mcocTools import (KABAM_ICON, COLLECTOR_ICON, PagesMenu)
from .hook import RosterUserConverter
# import cogs.mcocTools


class Alliance:
    """The CollectorVerse Alliance Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.alliances = "data/account/alliances.json"
        self.guilds = dataIO.load_json(self.alliances)
        self.alliancekeys = ('officers', 'bg1', 'bg2', 'bg3', 'alliance',)
        self.advancedkeys = ('officers', 'bg1', 'bg2', 'bg3', 'alliance', 'bg1aq', 'bg2aq', 'bg3aq', 'bg1aw', 'bg2aw', 'bg3aw',)
        self.infokeys = ('name', 'tag', 'started',)

    @commands.group(aliases=('clan', 'guild'), pass_context=True, invoke_without_command=True, hidden=False)
    async def alliance(self, ctx, user: discord.Member = None):
        """[ALPHA] CollectorVerse Alliance tools

        """
        # server = ctx.message.server
        print('debug: alliance group')
        if ctx.invoked_subcommand is None:
            if user is None:
                user = ctx.message.author
            alliances, message = self._find_alliance(user)  # list
            if alliances is None:
                data = discord.Embed(color=get_color(ctx), title='CollectorVerse Alliances', description=message,
                                     url='https://discord.gg/umcoc')
                await self.bot.say(embed=data)
            elif ctx.message.server.id in self.guilds:
                #refresh server data
                self._updatemembers(ctx.message.server)
                data = discord.Embed(color=get_color(ctx), title='CollectorVerse Alliances', description=message,
                                     url='https://discord.gg/umcoc')
                await self.bot.say(embed=data)
            else:
                data = discord.Embed(color=get_color(ctx), title='CollectorVerse Alliances', description=message,
                                     url='https://discord.gg/umcoc')
                data.add_field(name='Alliance codes', value=', '.join(alliances))
                await self.bot.say(embed=data)
                # await self._present_alliance(ctx, alliances, user)
            # print('_present_alliance placeholder')

    @checks.admin_or_permissions(manage_server=True)
    @alliance.command(name='delete', pass_context=True, aliases=('remove', 'del','rm'), invoke_without_command=True, no_pm=True)
    async def _delete(self, ctx):
        '''Delete CollectorVerse Alliance'''
        server = ctx.message.server
        if server.id in self.guilds:
            question = '{}, are you sure you want to deregsister {} as your CollectorVerse Alliance?'.format(ctx.message.author.mention, server.name)
            answer, confirmation = await PagesMenu.confirm(self, ctx, question)
            if answer:
                self.guilds.pop(server.id, None)
                # dropped = self.guilds.pop(server.id, None)
                dataIO.save_json(self.alliances, self.guilds)
                data = discord.Embed(title="Congrats!:sparkles:", description="You have deleted your CollectorVerse Alliance.", color=get_color(ctx))
            else:
                data = discord.Embed(title="Sorry!:sparkles:", description="You have no CollectorVerse Alliance.", color=get_color(ctx))
            menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
            await self.bot.delete_message(confirmation)
            await menu.menu_start(pages=[data])

    @checks.admin_or_permissions(manage_server=True)
    @alliance.command(name='report', pass_context=True, invoke_without_command=True, no_pm=True)
    async def _report(self, ctx):
        user = ctx.message.author
        alliances, message = self._find_alliance(user)  # list
        if alliances is None:
            return
        elif ctx.message.server.id in alliances:
            #report
            # guild = ctx.message.server.id
            # # guild = self.guilds[ctx.message.server.id]
            # data = discord.Embed(color=get_color(ctx), title='CollectorVerse Alliance Report', description='',
            #                      url='https://discord.gg/umcoc')
            # data.set_thumbnail(url=ctx.message.server.icon)
            # if 'about' in self.guilds[guild]:
            #     data.description=guild['about']
            # if self.guilds[guild]['type'] == 'basic':
            #     rolekeys= ('officers','bg1','bg2','bg3')
            # elif self.guilds[guild]['type'] == 'advanced':
            #     rolekeys=('officers', 'bg1aq', 'bg2aq', 'bg3aq', 'bg1aw', 'bg2aw', 'bg3aw')
            # else:
            #     await self.bot.say('Error: Alliance Type is not set\n``/alliance set type (basic | advanced)``')
            #     return
            # for key in rolekeys:
            #     data.add_field(name=key, value='\n'.join(self.guilds[guild][key]))
            # for key in self.infokeys:
            #     if key in self.guilds[guild]:
            #         data.add_field(name=key, value=self.guilds[guild][key]['name'])
            # await self.bot.say(embed=data)
            message = json.dumps(self.guilds[ctx.message.server.id])
            await self.bot.say('Alliance Debug Report'+message)
        else:
            return


    @alliance.command(name='show', pass_context=True, invoke_without_command=True, no_pm=True, hidden=True)
    async def _show(self, ctx, user: discord.Member = None):
        if user is None:
            user = ctx.message.author
        alliances, message = self._find_alliance(user)
        if len(alliances) > 0:
            await self._present_alliance(ctx, alliances, user)

    async def _present_alliance(self, ctx, alliances:list, user):
        ## 1 search for user in registered alliances
        ## 2 if user in alliance:
        ##    if ctx.server == alliance:
        ##         present full info
        ##      if ctx.server != alliance:
        ##         present public info
        await self.bot.say('testing alliance presentation')
        pages = []
        for alliance in alliances:
            guild = self.guilds[alliance]
            # server = await self.bot.get_server(alliance)

            # need a function to update all alliance roles + members
            if ctx.message.server.id == alliance and ctx.message.author.id == user.id:  #Alliance server & Alliance member
                data = discord.Embed(color=get_color(ctx), title='CollectorVerse Alliances', description='Display private profile ~ All kinds of info stored', url='https://discord.gg/umcoc')
                if 'about' in guild.keys():
                    data.description=guild['about']

                # for s in self.alliancekeys:
                #     if s in guild:
                #         data.add_field(name=s.title(), value=guild)

            elif server.id == alliance.id: #Alliance server visitor
                data = discord.Embed(color=get_color(ctx), title='CollectorVerse Alliances', description='Display Alliance Server recruiting profile', url='https://discord.gg/umcoc')
                # publiclist = ['name','tag','founded','leader','invitation','recruiting']
                # for public in publiclist:
                #     if public in guild:
                #         data.add_field(name=public.title(),value=guild[public])
            else: #Alliance stranger
                data = discord.Embed(color=get_color(ctx), title='CollectorVerse Alliances', description='Display public profile.\nInclude server join link, if set.\nInclude Alliance Prestige\nInclude About\n etc', url='https://discord.gg/umcoc')
            data.set_footer(text='CollectorDevTeam', icon_url=COLLECTOR_ICON)
            pages.append(data)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=pages)

    def _find_alliance(self, user):
        '''Returns a list of Server IDs or None'''
        user_alliances = []
        for guild in self.guilds.keys():
            keys = self.guilds[guild].keys()
            for key in keys:
                if key in self.advancedkeys:
                    if user.id in self.guilds[guild][key]['member_ids']:
                        if guild not in user_alliances:
                            user_alliances.append(guild)
                        print('keys: '.join([guild, key, 'member_ids']))
                        continue

        if len(user_alliances) > 0:
            return user_alliances, '{} found'.format(user.name)
        else:
            return None, '{} not found'.format(user.name)
    # def _get_members(self, server, key, role):
    #     '''For known Server and Role, find all server.members with role'''
    #     servermembers = server.members
    #     members = []
    #     for m in servermembers:
    #         if role in m.roles:
    #             members.append(m)
    #     package = {key: {'role':role, 'members':members}}
    #     self.guilds[server.id].update(package)
    #     dataIO.save_json(self.alliances, self.guilds)
    #     print('Members saved for {}'.format(role.name))
    #     print(json.dumps(package))
    #     return

    @checks.admin_or_permissions(manage_server=True)
    @alliance.command(name="register", pass_context=True, invoke_without_command=True, no_pm=True)
    async def _reg(self, ctx):
        """[ALPHA] Sign up to register your Alliance server!"""
        user = ctx.message.author
        server = ctx.message.server
        question = '{}, do you want to register this Discord Server as your Alliance Server?'.format(ctx.message.author.mention)
        answer, confirmation = await PagesMenu.confirm(self, ctx, question)
        datapages = []
        if answer is True:
            if server.id not in self.guilds:
                data = self._createalliance(ctx, server)
                datapages.append(data)
                for role in server.roles:
                    #add default roles
                    for key in self.alliancekeys:
                        if role.name.lower() == key:
                            # await self._updaterole(ctx, key, role)
                            data = await self._updaterole(ctx, key, role)
                            # await self.bot.say('{} role recognized and auto-registered.'.format(role.name))
                            datapages.append(data)
            else:
                data = discord.Embed(colour=get_color(ctx))
                data.add_field(name="Error:warning:", value="Opps, it seems like you have already registered this guild, {}.".format(user.mention))
                data.set_footer(text='CollectorDevTeam', icon_url=COLLECTOR_ICON)
                datapages.append(data)
            if len(datapages)>0:
                await self.bot.delete_message(confirmation)
            menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
            await menu.menu_start(pages=datapages)
        else:
            return
#
#     # @commands.group(name="update", pass_context=True, invoke_without_command=True)
    @checks.admin_or_permissions(manage_server=True)
    @alliance.group(name="set", aliases=('update',), pass_context=True, invoke_without_command=True, no_pm=True)
    async def update(self, ctx):
        """Update your CollectorVerse Alliance"""
        await send_cmd_help(ctx)
#
    @update.command(pass_context=True, name='name', no_pm=True)
    async def _alliancename(self, ctx, *, value):
        """What's your Alliance name?"""
        key = "guildname"
        server = ctx.message.server

        if server.id not in self.guilds:
            data = self._unknownguild(ctx)
        else:
            data = self._updateguilds(ctx, key, value)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='type', no_pm=True)
    async def _type(self, ctx, *, value):
        """Update your Alliance type:
        basic (default)
        advanced (uncommon)

        A 'basic' alliance with up to 3 roles defined for Battlegroups: bg1, bg2, bg3
        An 'advanced' alliance has up to 6 roles Battlegroups when Alliance War and Alliance Quest assignments are different: bg1aq, bg1aw, bg2aq, bg2aw, bg3aq, bg3aw"""
        if value in ('basic', 'advanced',):
            key = "type"
            server = ctx.message.server
            if server.id not in self.guilds:
                data = self._unknownguild(ctx)
            else:
                data = self._updateguilds(ctx, key, value)
        else:
            # send definitions
            message ='''basic (default)
            advanced (uncommon)
            
            A 'basic' alliance can have up to 3 roles defined for AQ & AW Battlegroups: 
            bg1, bg2, bg3
            
            An 'advanced' alliance has up to 6 roles defined for AQ & AW Battlegroups when assignments are different: 
            bg1aq, bg1aw, bg2aq, bg2aw, bg3aq, bg3aw'''
            data = discord.Embed(color=get_color(ctx), title='CollectorVerse Alliances', description=message,
                                 url='https://discord.gg/umcoc')

        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='tag')
    async def _alliancetag(self, ctx, *, value):
        """What's your Alliance tag? Only include the 5 tag characters."""
        key = "guildtag"
        # v = value.split('')
        if len(value) > 5:
            await self.bot.say('Clan Tag must be <= 5 characters.\nDo not include the [ or ] brackets.')
        server = ctx.message.server
        if server.id not in self.guilds:
            data = self._unknownguild(ctx)
        else:
            data = self._updateguilds(ctx, key, value)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True)
    async def started(self, ctx, *, started:str):
        """When did you start playing Contest of Champions?"""
        key = "Started"
        value = 'started'
        started = dateParse(started)
        print(value)

        if isinstance(started, datetime.datetime):
            user = ctx.message.author
            if ctx.message.author.id not in self.nerdie:
                data = self._unknownguild(ctx)
            else:
                data = self._updateguilds(ctx, key, value)
            await PagesMenu.menu_start(self, [data])
        else:
            await self.bot.say('Enter a valid date.')

    @update.command(pass_context=True, name='about')
    async def _allianceabout(self, ctx, *, value):
        '''Alliance About page'''
        key = 'about'
        if ctx.message.server.id not in self.guilds:
            data = self._unknownguild(ctx)
        else:
            data = self._updateguilds(ctx, key, value)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @checks.admin_or_permissions(manage_server=True)
    @update.command(pass_context=True, name='officers')
    async def _officers(self, ctx, role: discord.Role = None):
        """Which role are your Alliance Officers?"""
        data = await self._updaterole(ctx, key='officers', role=role)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='bg1')
    async def _bg1(self, ctx, role: discord.Role = None):
        """Which role is your Battlegroup 1?"""
        data = await self._updaterole(ctx, key='bg1', role=role)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='bg1aq')
    async def _bg1aq(self, ctx, role: discord.Role = None):
        """Which role is your Battlegroup 1 for Alliance Quest?"""
        data = await self._updaterole(ctx, key='bg1aq', role=role)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='bg1aw')
    async def _bg1aw(self, ctx, role: discord.Role = None):
        """Which role is your Battlegroup 1 for Alliance War?"""
        data = await self._updaterole(ctx, key='bg1aw', role=role)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='bg2')
    async def _bg2(self, ctx, role: discord.Role = None):
        """Which role is your Battlegroup 2?"""
        data = await self._updaterole(ctx, key='bg2', role=role)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='bg2aq')
    async def _bg2aq(self, ctx, role: discord.Role = None):
        """Which role is your Battlegroup 2 for Alliance Quest?"""
        data = await self._updaterole(ctx, key='bg2aq', role=role)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='bg2aw')
    async def _bg2aw(self, ctx, role: discord.Role = None):
        """Which role is your Battlegroup 2 for Alliance War?"""
        data = await self._updaterole(ctx, key='bg2aw', role=role)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='bg3')
    async def _bg3(self, ctx, role: discord.Role = None):
        """Which role is your Battlegroup 3?"""
        data = await self._updaterole(ctx, key='bg3', role=role)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='bg3aq')
    async def _bg3aq(self, ctx, role: discord.Role = None):
        """Which role is your Battlegroup 3 for Alliance Quest?"""
        data = await self._updaterole(ctx, key='bg3aq', role=role)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='bg3aw')
    async def _bg3aw(self, ctx, role: discord.Role = None):
        """Which role is your Battlegroup 3 for Alliance War?"""
        data = await self._updaterole(ctx, key='bg3aw', role=role)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='alliance', aliases=('members', 'memberrole',))
    async def _alliance(self, ctx, role: discord.Role = None):
        """Which role represents all members of your alliance (up to 30)?"""
        data = await self._updaterole(ctx, key='alliance', role=role)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])
#
    def _createalliance(self, ctx, server):

        self.guilds[server.id] = {'type': 'basic'}
        dataIO.save_json(self.alliances, self.guilds)
        data = discord.Embed(colour=get_color(ctx))
        data.add_field(name="Congrats!:sparkles:", value="{}, you have officially registered {} as a CollectorVerse Alliance.".format(ctx.message.author.mention, server.name))
        data.set_footer(text='CollectorDevTeam',
                icon_url=COLLECTOR_ICON)
        return data

    def _unknownguild(self, ctx):
        data = discord.Embed(colour=get_color(ctx))
        data.add_field(name="Error:warning:",value="Sadly, this feature is only available for Discord server owners who registerd for an Alliance. \n\nYou can register for a account today for free. All you have to do is:\nCreate a Discord server.\nInvite Collector\nOn your Alliance server say `{} alliance signup` and you'll be all set.".format(ctx.prefix))
        data.set_footer(text='CollectorDevTeam',
                icon_url=COLLECTOR_ICON)
        return data

    async def _updaterole(self, ctx, key, role):
        '''For a given context, key, and role, search message server for role and set role for that alliance key'''
        server = ctx.message.server
        if server.id not in self.guilds:
            data = self._unknownguild(ctx)
        else:
            data = discord.Embed(colour=get_color(ctx), title='Role Registration')
            if role is None:
                question = '{}, do you want to remove this ``{}`` registration?'.format(
                    ctx.message.author.mention, key)
                answer, confirmation = await PagesMenu.confirm(self, ctx, question)
                if answer is True:
                    self.guilds[server.id].pop(key, None)
                    await self.bot.delete_message(confirmation)
                    data.add_field(name="Congrats!:sparkles:", value="You have unregistered ``{}`` from your Alliance.".format(key))
            else:
                member_names = []
                member_ids = []
                for m in server.members:
                    if role in m.roles:
                        member_names.append(m.name)
                        member_ids.append(m.id)
                if len(member_ids)==0:
                    member_ids.append('n/a')
                    member_names.append('n/a')
                package = {'id': role.id,
                           'name': role.name,
                           'member_ids': member_ids,
                           'member_names': member_names}
                if key in ('bg1', 'bg2', 'bg3', 'bg1aw', 'bg1aq', 'bg2aw', 'bg2aq', 'bg3aw', 'bg3aq'):
                    if len(member_ids) > 10:
                        data.add_field(name=':warning: Warning - Overloaded Battlegroup:', value='Battlegroups are limited to 10 members.\nCheck your {} assignments'.format(role.name))
                elif key == 'alliance':
                    if len(member_ids) > 30:
                        data.add_field(name=':warning: Warning - Overloaded Alliance', value='Alliances are limited to 30 members.\nCheck your {} members'.format(role.name))
                self.guilds[server.id].update({key: package})
                data.add_field(name="Congrats!:sparkles:",value="You have set your {} to {}".format(key, role.name), inline=False)
                data.add_field(name='{} members'.format(role.name), value='\n'.join(member_names))
            dataIO.save_json(self.alliances, self.guilds)
            data.set_footer(text='CollectorDevTeam',
                    icon_url=COLLECTOR_ICON)
        return data

    def _updatemembers(self, server):
        for key in self.advancedkeys:
            if key in self.guilds:
                for role in server.roles:
                    if self.guilds[key]['role_id'] == role.id:
                        member_names = []
                        member_ids = []
                        for m in server.members:
                            if role in m.roles:
                                member_names.append(m.name)
                                member_ids.append(m.id)
                        package = {'id': role.id,
                                   'name': role.name,
                                   'member_ids': member_ids,
                                   'member_names': member_names}
                        self.guilds[server.id].update({key: package})
                        continue
        dataIO.save_json(self.alliances, self.guilds)
        print('Debug: Alliance details refreshed')
        return

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
    bot.add_cog(Alliance(bot))
