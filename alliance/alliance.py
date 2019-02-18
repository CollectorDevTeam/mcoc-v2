# import re
import os
import json
import datetime
import discord
import requests
from discord.ext import commands
from dateutil.parser import parse as date_parse
from __main__ import send_cmd_help
from .utils.dataIO import dataIO
from .utils import checks
# from .utils import chat_formatting as chat
from .mcocTools import (KABAM_ICON, COLLECTOR_ICON, PagesMenu)
from .hook import RosterUserConverter, ChampionRoster
# import cogs.mcocTools


class Alliance:
    """The CollectorVerse Alliance Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.alliances = "data/account/alliances.json"
        self.guilds = dataIO.load_json(self.alliances)
        self.alliance_keys = ('officers', 'bg1', 'bg2', 'bg3', 'alliance',)
        self.advanced_keys = ('officers', 'bg1', 'bg2', 'bg3', 'alliance',
                              'bg1aq', 'bg2aq', 'bg3aq', 'bg1aw', 'bg2aw', 'bg3aw',)
        self.infokeys = ('name', 'tag', 'started', 'invite')
        self.hook = bot.get_cog('Hook')

    @commands.group(aliases=('clan', 'guild'), pass_context=True, invoke_without_command=True, hidden=False, no_pm=True)
    async def alliance(self, ctx, user: discord.Member = None):
        """[ALPHA] CollectorVerse Alliance tools

        """
        # server = ctx.message.server
        print('debug: alliance group')
        # self._update_members(ctx.message.server)

        if ctx.invoked_subcommand is None:
            if user is None:
                user = ctx.message.author
            await self._show_public(ctx, user)
            # alliances, message = self._find_alliance(user)  # list
            # if alliances is None:
            #     data = discord.Embed(color=get_color(ctx), title='CollectorVerse Alliances', description=message,
            #                          url='https://discord.gg/umcoc')
            #     data.set_thumbnail(url=ctx.message.server.icon_url)
            #     await self.bot.say(embed=data)
            # elif ctx.message.server.id in self.guilds:
            #     self._update_members(ctx.message.server)
            #     data = discord.Embed(color=get_color(ctx), title='CollectorVerse Alliances', description=message,
            #                          url='https://discord.gg/umcoc')
            #     data.set_thumbnail(url=ctx.message.server.icon_url)
            #     await self.bot.say(embed=data)
            # else:
            #     data = discord.Embed(color=get_color(ctx), title='CollectorVerse Alliances', description=message,
            #                          url='https://discord.gg/umcoc')
            #     data.add_field(name='Alliance codes', value=', '.join(self.guilds[a]['name'] for a in alliances))
            #     await self.bot.say(embed=data)

    # @alliance.command(name='show', pass_context=True, invoke_without_command=True, no_pm=True)
    async def _show_public(self, ctx, user: discord.Member = None):
        """Display Alliance public profile"""
        if user is None:
            user = ctx.message.author
        alliances, message = self._find_alliance(user)
        pages = []
        if alliances is None:
            data = self._get_embed(ctx)
            data.title = message
            await self.bot.say(embed=data)
            return
        elif ctx.message.server.id in alliances:
            alliances = [ctx.message.server.id]
        else:
            pass

        for alliance in alliances:
            keys = self.guilds[alliance].keys()
            server = self.bot.get_server(alliance)
            data = self._get_embed(ctx, alliance, user.id)
            if 'tag' in keys:
                if 'name' in keys:
                    data.title = '[{}] {}'.format(self.guilds[alliance]['tag'], self.guilds[alliance]['name'])
                else:
                    data.title = '[{}] {}'.format(self.guilds[alliance]['tag'], server.name)
            elif 'name' in keys:
                data.title = '{}'.format(server.name)
                data.add_field(name='Alliance Tag', value='Alliance Tag not set\n``/alliance set tag <tag>``')
            else:
                data.title = server.name
            if 'about' in keys:
                data.description = self.guilds[alliance]['about']
            else:
                data.description = 'Alliance About is not set\n``/alliance set about <about>``'
            if 'alliance' in keys:
                for r in server.roles:
                    if r.id == self.guilds[alliance]['alliance']['id']:
                        verbose = False
                        if ctx.message.server == server:
                            verbose = True
                        data = await self._get_prestige(server=server, role=r, verbose=verbose, data=data)
                        # data.add_field(name='Alliance Prestige', value=clan_prestige)
                        continue
            if 'invite' in keys:
                data.url = self.guilds[alliance]['invite']
                data.add_field(name='Join server', value=self.guilds[alliance]['invite'])
            else:
                data.add_field(name='Join server', value='Invitation not set\n``/alliance set invite <link>``')
            if 'started' in keys:
                since = date_parse(self.guilds[alliance]['started'])
                days_since = (datetime.datetime.utcnow() - since).days
                data.add_field(name='Alliance founded: {}'.format(since.date()), value="Playing for {} days!"
                               .format(days_since))
            if 'poster' in keys:
                data.set_image(url=self.guilds[alliance]['poster'])
            pages.append(data)
        if len(pages) > 0:
            menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
            await menu.menu_start(pages=pages)
        else:
            print('alliance._show_public - no pages')

    def _get_embed(self, ctx, alliance=None, user_id=None):
        """Return a color styled embed with no title or description"""
        color = discord.Color.gold()
        if alliance is not None:
            server = self.bot.get_server(alliance)
            for member in server.members:
                if user_id == member.id:
                    color = member.color
                    continue
        else:
            server = ctx.message.server
            color = get_color(ctx)
        data = discord.Embed(color=color, title='', description='')
        data.set_author(name='A CollectorVerse Alliance', icon_url=COLLECTOR_ICON)
        data.set_thumbnail(url=server.icon_url)
        data.set_footer(text='CollectorDevTeam', icon_url=COLLECTOR_ICON)
        return data

    async def _get_prestige(self, server, role, verbose=False, data=None):
        """Pull User Prestige for all users in Role"""
        print('_get_prestige activated')
        print('server: '+server.name)
        print('role: '+role.name)
        members = []
        line_out = []
        width = 20
        prestige = 0
        cnt = 0
        role_members = []
        for member in server.members:
            print(member.display_name)
            print('\n'.join(r.name for r in member.roles))
            if role in member.roles:
                role_members.append(member)
                print('role in member.roles')
        print('role_member count {}'.format(len(role_members)))
        for member in role_members:
            members.append(member)
            roster = ChampionRoster(self.bot, member)
            await roster.load_champions()
            if roster.prestige > 0:
                prestige += roster.prestige
                cnt += 1
            temp_line = '{:{width}} p = {}'.format(member.display_name, roster.prestige, width=width)
            print(temp_line)
            line_out.append(temp_line)
        verbose_prestige = '```{}```'.format('\n'.join(line_out))
        # line_out.append('_' * (width + 11))
        clan_prestige = 0
        summary = 0
        if cnt > 0:
            summary = '{0:{width}}   = {1} from {2} members'.format(
                role.name, round(prestige / cnt, 0), cnt, width=width)
            clan_prestige = round(prestige / cnt, 0)
            print(clan_prestige)
        if data is None:
            if len(members) == 0 or len(members) > 30:
                return None
            elif verbose:
                return verbose_prestige
            else:
                return clan_prestige
        else:
            if verbose and len(role_members) <= 30:
                data.add_field(name='{} prestige: {}'.format(role.name, clan_prestige), value=verbose_prestige,
                               inline=False)
            elif verbose:
                data.add_field(name='{} prestige {}'.format(role.name, clan_prestige),
                               value='{}\n\nVerbose prestige details restricted for roles with more than 30 members.'
                               .format(summary), inline=False)
            else:
                data.add_field(name='{} prestige {}'.format(role.name, clan_prestige), value=summary, inline=False)
            return data

    @checks.admin_or_permissions(manage_server=True)
    @alliance.command(name='unregister', aliases=('delete', 'del' 'remove', 'rm',), pass_context=True,
                      invoke_without_command=True, no_pm=True)
    async def _delete(self, ctx):
        """Delete CollectorVerse Alliance"""
        server = ctx.message.server
        if server.id in self.guilds:
            question = '{}, are you sure you want to un-register {} as your CollectorVerse Alliance?'\
                .format(ctx.message.author.mention, server.name)
            answer, confirmation = await PagesMenu.confirm(self, ctx, question)
            if answer:
                self.guilds.pop(server.id, None)
                # dropped = self.guilds.pop(server.id, None)
                dataIO.save_json(self.alliances, self.guilds)
                data = discord.Embed(title="Congrats!:sparkles:",
                                     description="You have deleted your CollectorVerse Alliance.", color=get_color(ctx))
            else:
                data = discord.Embed(title="Sorry!:sparkles:",
                                     description="You have no CollectorVerse Alliance.",
                                     color=get_color(ctx))
            menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
            await self.bot.delete_message(confirmation)
            await menu.menu_start(pages=[data])

    @checks.admin_or_permissions(manage_server=True)
    @alliance.command(name='report', pass_context=True, invoke_without_command=True, hidden=True, no_pm=True)
    async def _report(self, ctx, alliance=None):
        if alliance is not None:
            server = self.bot.get_server(alliance)
            await self.bot.say('server name: '+server.name)

        else:
            user = ctx.message.author
            alliances, message = self._find_alliance(user)  # list
            if alliances is None:
                return
            elif ctx.message.server.id in alliances:
                # report
                # guild = ctx.message.server.id
                # # guild = self.guilds[ctx.message.server.id]
                # data = discord.Embed(color=get_color(ctx), title='CollectorVerse Alliance Report', description='',
                #                      url='https://discord.gg/umcoc')
                # data.set_thumbnail(url=ctx.message.server.icon_url)
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

    def _find_alliance(self, user):
        """Returns a list of Server IDs or None"""
        user_alliances = []
        for guild in self.guilds.keys():
            keys = self.guilds[guild].keys()
            for key in keys:
                if key in self.advanced_keys:
                    if user.id in self.guilds[guild][key]['member_ids']:
                        if guild not in user_alliances:
                            user_alliances.append(guild)
                        print('keys: '.join([guild, key, 'member_ids']))
                        continue

        if len(user_alliances) > 0:
            return user_alliances, '{} found.'.format(user.name)
        else:
            return None, '{} not found in a registered CollectorVerse Alliance.\nPerhaps Alliance roles are not registered.'.format(user.name)
    # def _get_members(self, server, key, role):
    #     """For known Server and Role, find all server.members with role"""
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

    @alliance.command(name='bg', aliases=('battlegroups', 'bgs'), pass_context=True, no_pm=True)
    async def _battle_groups(self, ctx):
        """Report Alliance Battlegroups"""
        alliances, message = self._find_alliance(ctx.message.author)
        if alliances is None:
            data = self._get_embed(ctx)
            data.title = 'Access Denied'
            data.description = 'This tool is only available for members of this alliance.'
            await self.bot.say(embed=data)
            return
        elif ctx.message.server.id in alliances:
            server = ctx.message.server
            alliance = server.id
            roles = server.roles
            members = server.members
            aq_roles = []
            aw_roles = []
            pages = []
            basic = ('bg1', 'bg2', 'bg3')
            if self.guilds[alliance]['type'] == 'basic':
                for bg in basic:
                    for r in roles:
                        if r.id == self.guilds[alliance][bg]['id']:
                            aq_roles.append(r)
                aw_roles = aq_roles
            elif self.guilds[alliance]['type'] == 'advanced':
                for bg in basic:
                    for r in roles:
                        if r.id == self.guilds[alliance][bg+'aq']['id']:
                            aq_roles.append(r)
                        elif r.id == self.guilds[alliance][bg+'aw']['id']:
                            aq_roles.append(r)
                        else:
                            pass
            for a in (aq_roles, aw_roles):
                data = self._get_embed(ctx)
                data.color = discord.Color.gold()
                overload = []
                if a == aq_roles:
                    data.title = 'Alliance Quest Battlegroups'
                else:
                    data.title = 'Alliance War Battlegroups'
                for role in a:
                    data = await self._get_prestige(server, role, verbose=True, data=data)
                # for member in members:
                #     for battlegroups in (aq_roles, aw_roles):
                #         for role in battlegroups:
                #             count = 0
                #             if role in member.roles:
                #                 count += 1
                #             if count > 1:
                #                 overload.append(member.display_name)
                # if len(overload) > 0:
                #     data.add_field(name='Battlegroup Overload', value='\n'.join(overload))
                pages.append(data)
            menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
            await menu.menu_start(pages=pages)

    @checks.admin_or_permissions(manage_server=True)
    @alliance.command(name="register", aliases=('create', 'add'),
                      pass_context=True, invoke_without_command=True, no_pm=True)
    async def _reg(self, ctx):
        """[ALPHA] Sign up to register your Alliance server!"""
        user = ctx.message.author
        server = ctx.message.server
        question = '{}, do you want to register this Discord Server as your Alliance Server?'\
            .format(ctx.message.author.mention)
        answer, confirmation = await PagesMenu.confirm(self, ctx, question)
        data_pages = []
        if answer is True:
            if server.id not in self.guilds:
                data = self._create_alliance(ctx, server)
                data_pages.append(data)
                for role in server.roles:
                    # add default roles
                    for key in self.alliance_keys:
                        if role.name.lower() == key:
                            # await self._update_role(ctx, key, role)
                            data = await self._update_role(ctx, key, role)
                            # await self.bot.say('{} role recognized and auto-registered.'.format(role.name))
                            data_pages.append(data)
            else:
                data = discord.Embed(colour=get_color(ctx))
                data.add_field(name="Error:warning:",
                               value="Oops, it seems like you have already registered this guild, {}."
                               .format(user.mention))
                data.set_footer(text='CollectorDevTeam', icon_url=COLLECTOR_ICON)
                data_pages.append(data)
            if len(data_pages) > 0:
                await self.bot.delete_message(confirmation)
            menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
            await menu.menu_start(pages=data_pages)
        else:
            return

    @checks.admin_or_permissions(manage_server=True)
    @alliance.group(name="set", aliases=('update',), pass_context=True, invoke_without_command=True, no_pm=True)
    async def update(self, ctx):
        """Update your CollectorVerse Alliance"""
        await send_cmd_help(ctx)

    @update.command(pass_context=True, name='name', no_pm=True)
    async def _alliancename(self, ctx, *, value):
        """What's your Alliance name?"""
        key = "name"
        server = ctx.message.server

        if server.id not in self.guilds:
            data = _unknown_guild(ctx)
        else:
            data = self._update_guilds(ctx, key, value)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='type', no_pm=True)
    async def _type(self, ctx, *, value):
        """Update your Alliance type:
        basic (default)
        advanced (uncommon)

        A 'basic' alliance with up to 3 roles defined for Battlegroups:
        bg1, bg2, bg3

        An 'advanced' alliance has up to 6 roles Battlegroups when AW and AQ assignments are different:
        bg1aq, bg1aw, bg2aq, bg2aw, bg3aq, bg3aw"""
        if value in ('basic', 'advanced',):
            key = "type"
            server = ctx.message.server
            if server.id not in self.guilds:
                data = _unknown_guild(ctx)
            else:
                data = self._update_guilds(ctx, key, value)
        else:
            # send definitions
            message = """basic (default)
            advanced (uncommon)
            
            A 'basic' alliance can have up to 3 roles defined for AQ & AW Battlegroups: 
            bg1, bg2, bg3
            
            An 'advanced' alliance has up to 6 roles defined for AQ & AW Battlegroups when assignments are different: 
            bg1aq, bg1aw, bg2aq, bg2aw, bg3aq, bg3aw"""
            data = discord.Embed(color=get_color(ctx), title='CollectorVerse Alliances', description=message,
                                 url='https://discord.gg/umcoc')

        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='tag')
    async def _alliance_tag(self, ctx, *, value):
        """What's your Alliance tag? Only include the 5 tag characters."""
        key = "tag"
        # v = value.split('')
        if len(value) > 5:
            await self.bot.say('Clan Tag must be <= 5 characters.\nDo not include the [ or ] brackets.')
        server = ctx.message.server
        if server.id not in self.guilds:
            data = _unknown_guild(ctx)
        else:
            data = self._update_guilds(ctx, key, value)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(name='started', pass_context=True)
    async def _started(self, ctx, *, date: str):
        """When did you create this Alliance?"""
        key = "started"
        value = date
        print(value)
        started = date_parse(date)

        if isinstance(started, datetime.datetime):
            if ctx.message.server.id not in self.guilds:
                data = _unknown_guild(ctx)
            else:
                data = self._update_guilds(ctx, key, date)
            await self.bot.say(embed=data)
        else:
            await self.bot.say('Enter a valid date.')

    @update.command(pass_context=True, name='about')
    async def _alliance_about(self, ctx, *, value):
        """Alliance About page"""
        key = 'about'
        if ctx.message.server.id not in self.guilds:
            data = _unknown_guild(ctx)
        else:
            data = self._update_guilds(ctx, key, value)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='poster')
    async def _poster(self, ctx, *, value=None):
        """Alliance recruitment poster url or upload image"""
        key = 'poster'
        # test key for url
        if value is None:
            if len(ctx.message.attachments) > 0:
                image = ctx.message.attachments[0]
                print(json.dumps(image))
                value = image['url']
        if ctx.message.server.id not in self.guilds:
            data = _unknown_guild(ctx)
        else:
            # verified = verify(str(value))
            img = send_request(value)
            if img is False:
                data = self._get_embed(ctx)
                data.title = 'Image Verification Failed'
            else:
                data = self._update_guilds(ctx, key, value)
                data.set_image(url=value)

        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='invite')
    async def _invite(self, ctx, *, value):
        """Alliance Server permanent join link"""
        key = 'invite'
        if ctx.message.server.id not in self.guilds:
            data = _unknown_guild(ctx)
        elif 'discord.gg' not in value:
            data = self._get_embed(ctx)
            data.add_field(name='Warning:sparkles:', value='Only Discord server links are supported.')
        else:
            data = self._update_guilds(ctx, key, value)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @checks.admin_or_permissions(manage_server=True)
    @update.command(pass_context=True, name='officers')
    async def _officers(self, ctx, role: discord.Role = None):
        """Which role are your Alliance Officers?"""
        data = await self._update_role(ctx, key='officers', role=role)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='bg1')
    async def _bg1(self, ctx, role: discord.Role = None):
        """Which role is your Battlegroup 1?"""
        data = await self._update_role(ctx, key='bg1', role=role)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='bg1aq')
    async def _bg1aq(self, ctx, role: discord.Role = None):
        """Which role is your Battlegroup 1 for Alliance Quest?"""
        data = await self._update_role(ctx, key='bg1aq', role=role)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='bg1aw')
    async def _bg1aw(self, ctx, role: discord.Role = None):
        """Which role is your Battlegroup 1 for Alliance War?"""
        data = await self._update_role(ctx, key='bg1aw', role=role)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='bg2')
    async def _bg2(self, ctx, role: discord.Role = None):
        """Which role is your Battlegroup 2?"""
        data = await self._update_role(ctx, key='bg2', role=role)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='bg2aq')
    async def _bg2aq(self, ctx, role: discord.Role = None):
        """Which role is your Battlegroup 2 for Alliance Quest?"""
        data = await self._update_role(ctx, key='bg2aq', role=role)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='bg2aw')
    async def _bg2aw(self, ctx, role: discord.Role = None):
        """Which role is your Battlegroup 2 for Alliance War?"""
        data = await self._update_role(ctx, key='bg2aw', role=role)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='bg3')
    async def _bg3(self, ctx, role: discord.Role = None):
        """Which role is your Battlegroup 3?"""
        data = await self._update_role(ctx, key='bg3', role=role)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='bg3aq')
    async def _bg3aq(self, ctx, role: discord.Role = None):
        """Which role is your Battlegroup 3 for Alliance Quest?"""
        data = await self._update_role(ctx, key='bg3aq', role=role)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='bg3aw')
    async def _bg3aw(self, ctx, role: discord.Role = None):
        """Which role is your Battlegroup 3 for Alliance War?"""
        data = await self._update_role(ctx, key='bg3aw', role=role)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @update.command(pass_context=True, name='alliance')
    async def _alliance(self, ctx, role: discord.Role = None):
        """Which role represents all members of your alliance (up to 30)?"""
        data = await self._update_role(ctx, key='alliance', role=role)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    def _create_alliance(self, ctx, server):
        """Create alliance.
        Set basic information"""
        self.guilds[server.id] = {'type': 'basic', 'name': server.name}
        dataIO.save_json(self.alliances, self.guilds)
        data = discord.Embed(colour=get_color(ctx))
        data.add_field(name="Congrats!:sparkles:",
                       value="{}, you have officially registered {} as a CollectorVerse Alliance."
                       .format(ctx.message.author.mention, server.name))
        data.set_footer(text='CollectorDevTeam', icon_url=COLLECTOR_ICON)
        return data

    async def _update_role(self, ctx, key, role):
        """For a given context, key, and role, search message server for role and set role for that alliance key"""
        server = ctx.message.server
        if server.id not in self.guilds:
            data = _unknown_guild(ctx)
        else:
            data = discord.Embed(colour=get_color(ctx), title='Role Registration')
            if role is None:
                question = '{}, do you want to remove this ``{}`` registration?'.format(
                    ctx.message.author.mention, key)
                answer, confirmation = await PagesMenu.confirm(self, ctx, question)
                if answer is True:
                    self.guilds[server.id].pop(key, None)
                    await self.bot.delete_message(confirmation)
                    data.add_field(name="Congrats!:sparkles:",
                                   value="You have unregistered ``{}`` from your Alliance.".format(key))
            else:
                member_names = []
                member_ids = []
                for m in server.members:
                    if role in m.roles:
                        member_names.append(m.display_name)
                        member_ids.append(m.id)
                package = {'id': role.id,
                           'name': role.name,
                           'member_ids': member_ids,
                           'member_names': member_names}
                if key in ('bg1', 'bg2', 'bg3', 'bg1aw', 'bg1aq', 'bg2aw', 'bg2aq', 'bg3aw', 'bg3aq'):
                    if len(member_ids) > 10:
                        data.add_field(name=':warning: Warning - Overloaded Battlegroup:',
                                       value='Battlegroups are limited to 10 members. '
                                             'Check your {} assignments'.format(role.name))
                elif key == 'alliance':
                    if len(member_ids) > 30:
                        data.add_field(name=':warning: Warning - Overloaded Alliance',
                                       value='Alliances are limited to 30 members. '
                                             'Check your {} members'.format(role.name))
                self.guilds[server.id].update({key: package})
                data.add_field(name="Congrats!:sparkles:", 
                               value="You have set your {} to {}".format(key, role.name), inline=False)
                if len(member_names) > 0:
                    data.add_field(name='{} members'.format(role.name), value='\n'.join(member_names))
                else:
                    data.add_field(name='{} members'.format(role.name), value='No Members assigned')
            dataIO.save_json(self.alliances, self.guilds)
            data.set_footer(text='CollectorDevTeam', icon_url=COLLECTOR_ICON)
        return data

    def _update_members(self, server):
        for key in self.advanced_keys:
            if key in self.guilds:
                for role in server.roles:
                    if self.guilds[key]['id'] == role.id:
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

    def _update_guilds(self, ctx, key, value):
        server = ctx.message.server
        data = discord.Embed(colour=get_color(ctx))
        if value in ('""', "''", " ", "None", "none", "-",):
            self.guilds[server.id].pop(key, None)
            data.add_field(name="Congrats!:sparkles:", value="You have deleted {} from your Alliance.".format(key))
        else:
            self.guilds[server.id].update({key: value})
            data.add_field(name="Congrats!:sparkles:", value="You have set your {} to {}".format(key, value))
        dataIO.save_json(self.alliances, self.guilds)
        data.set_footer(text='CollectorDevTeam', icon_url=COLLECTOR_ICON)
        return data


def send_request(url):
    try:
        page = requests.get(url)

    except Exception as e:
        print("error:", e)
        return False

    # check status code
    if page.status_code != 200:
        print('status code'+page.status_code)
        return False

    return page


def _unknown_guild(ctx):
    data = discord.Embed(colour=get_color(ctx))
    data.add_field(name="Error:warning:",
                   value="Sadly, this feature is only available for registered guild owners."
                        " "
                        "You can register for a account today for free. All you have to do is:"
                        "Create a Discord server."
                        "Invite Collector"
                        "On your Alliance server say `{} alliance signup` and you'll be all set."
                   .format(ctx.prefix))
    data.set_footer(text='CollectorDevTeam', icon_url=COLLECTOR_ICON)
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
