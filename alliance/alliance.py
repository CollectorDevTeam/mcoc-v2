import re
import os
import json
import logging
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

logger = logging.getLogger('red.mcoc.alliance')
logger.setLevel(logging.INFO)


class EnhancedRoleConverter(commands.RoleConverter):
    def convert(self):
        if self.argument == 'everyone':
            self.argument = '@everyone'
        return super().convert()


class Alliance:
    """The CollectorVerse Alliance Cog"""

    def __init__(self, bot):
        self.bot = bot
        self.alliances = "data/account/alliances.json"
        self.guilds = dataIO.load_json(self.alliances)
        self.alliance_keys = ('officers', 'bg1', 'bg2', 'bg3', 'alliance',)
        self.advanced_keys = ('officers', 'bg1', 'bg2', 'bg3', 'alliance',
                              'bg1aq', 'bg2aq', 'bg3aq', 'bg1aw', 'bg2aw', 'bg3aw',)
        self.info_keys = ('name', 'tag', 'type', 'about', 'started', 'invite', 'poster')

    @commands.command(pass_context=True, no_pm=True, hidden=True)
    async def lanes(self, ctx, user: discord.Member = None):
        server = ctx.message.server
        alliance = server.id
        if user is None:
            user = ctx.message.author
        if user is not None:
            if alliance in self.guilds.keys() and 'assignments' in self.guilds[alliance].keys() \
                    and user.id in self.guilds[alliance]['assignments'].keys():
                data = self._get_embed(ctx, alliance, user.id, user.color)
                for m in ('aq1', 'aq2', 'aq3', 'aq4', 'aq5', 'aq6', 'aq7', 'aw',):
                    if m in self.guilds[alliance]['assignments'][user.id].keys():
                        data.add_field(name=m.upper()+' Assignment',
                                       value=self.guilds[alliance]['assignments'][user.id][m])
                await self.bot.say(embed=data)

    @commands.command(pass_context=True, no_pm=True, hidden=True)
    async def bglanes(self, ctx, role: discord.role):
        server = ctx.message.server
        alliance = server.id
        members = _get_members(server, role)

        if members is not None:
            pages = []
            for m in ('aq1', 'aq2', 'aq3', 'aq4', 'aq5', 'aq6', 'aq7', 'aw',):
                data = self._get_embed(ctx, alliance=alliance, color=role.color)
                data.title = '{} Assignments for {}'.format(role.name, m.upper())
                cnt = 0
                for member in members:
                    if member.id in self.guilds[alliance]['assignments'].keys():
                        if m in self.guilds[alliance]['assignments'][member.id].keys():
                            data.add_field(name=member.display_name, value=self.guilds[alliance]['assignments'][member.id][m])
                            cnt += 1
                if cnt > 0:
                    pages.append(data)
            if len(pages) > 0:
                menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
                await menu.menu_start(pages=pages)
            else:
                logger.warning('No Pages to display')

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

    async def _show_public(self, ctx, user: discord.Member = None):
        """Display Alliance public profile"""
        if user is None:
            user = ctx.message.author
        alliances, message = self._find_alliance(user)
        pages = []
        if alliances is None:
            data = self._get_embed(ctx)
            data.title = message+':sparkles:'
            if ctx.message.server.id in self.guilds.keys():
                alliance = ctx.message.server.id
                keys = self.guilds[alliance].keys()
                role_registered = False
                for key in self.advanced_keys:
                    if key in keys:
                        role_registered = True
                        continue
                if role_registered is False:
                    data.add_field(name='This alliance server is registered.',
                                   value='However, no roles have been registered for '
                                         '``alliance``, ``officers`` or ``bg1 | bg2 | bg3``')
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
                    data.title = '[{}] {}:sparkles:'.format(self.guilds[alliance]['tag'], self.guilds[alliance]['name'])
                else:
                    data.title = '[{}] {}:sparkles:'.format(self.guilds[alliance]['tag'], server.name)
            elif 'name' in keys:
                data.title = '{}:sparkles:'.format(server.name)
                data.add_field(name='Alliance Tag', value='Alliance Tag not set.')
            else:
                data.title = server.name+':sparkles:'
            if 'about' in keys:
                data.description = self.guilds[alliance]['about']
            else:
                data.description = 'Alliance About is not set.'
            if 'alliance' in keys:
                role = self._get_role(server, 'alliance')
                role_members = _get_members(server, role)
                if role is not None:
                    verbose = False
                    if ctx.message.server == server:  # on home server
                        verbose = True
                    data = await self._get_prestige(server=server, role=role, verbose=verbose,
                                                    data=data, role_members=role_members)
                    # data.add_field(name='Alliance Prestige', value=clan_prestige)
            else:
                data.add_field(name='Alliance Role', value='Alliance role is not set.')
            if 'started' in keys:
                since = date_parse(self.guilds[alliance]['started'])
                days_since = (datetime.datetime.utcnow() - since).days
                data.add_field(name='Alliance founded: {}'.format(since.date()), value="Playing for {} days!"
                               .format(days_since))
            if 'poster' in keys:
                data.set_image(url=self.guilds[alliance]['poster'])
            if 'invite' in keys:
                data.url = self.guilds[alliance]['invite']
                data.add_field(name='Join server', value=self.guilds[alliance]['invite'])
            else:
                data.add_field(name='Join server', value='Invitation not set.')
            pages.append(data)
        if len(pages) > 0:
            menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
            await menu.menu_start(pages=pages)
        else:
            logger.warning('No Pages to display')
            # print('alliance._show_public - no pages')

    def _get_embed(self, ctx, alliance=None, user_id=None, color=discord.Color.gold()):
        """Return a color styled embed with no title or description"""
        # color = discord.Color.gold()
        if alliance is not None:
            server = self.bot.get_server(alliance)
            if server is not None:
                members = server.members
                if user_id is not None:
                    for member in members:
                        if member.id == user_id:
                            color = member.color
                            break
        else:
            server = ctx.message.server
            if color is None:
                color = get_color(ctx)
        data = discord.Embed(color=color, title='', description='')
        data.set_author(name='A CollectorVerse Alliance', icon_url=COLLECTOR_ICON)
        if server.icon_url is not None:
            data.set_thumbnail(url=server.icon_url)
        data.set_footer(text='CollectorDevTeam', icon_url=COLLECTOR_ICON)
        return data

    async def _get_prestige(self, server, role, verbose=False,
                            data=None, role_members: list = None):
        """Return Clan Prestige and Verbose Prestige for Role members"""
        logger.info("Retrieving prestige for role '{}' on guild '{}'".format(
                role.name, server.name, ))
        members = []
        line_out = {}
        # line_out = []
        width = 20
        prestige = 0
        cnt = 0
        if role_members is None:
            for member in server.members:
                if role in member.roles:
                    role_members.append(member)
        if len(role_members) > 0:
            for member in role_members:
                members.append(member)
                roster = ChampionRoster(self.bot, member)
                await roster.load_champions()
                if roster.prestige > 0:
                    prestige += roster.prestige
                    cnt += 1
                temp_line = '{:{width}} p = {}'.format(
                        member.display_name, int(roster.prestige), width=width)
                # print(temp_line)
                # line_out.append(temp_line)
                line_out.update({roster.prestige: temp_line})
            joined = '\n'.join(v for k, v in line_out.items())
            # verbose_prestige = '```{}```'.format('\n'.join(line_out))
            verbose_prestige = '```{}```'.format(joined)
            # line_out.append('_' * (width + 11))
            clan_prestige = 0
            summary = 0
            if cnt > 0:
                summary = '{0:{width}}   = {1} from {2} members'.format(
                    role.name, round(prestige / cnt, 0), cnt, width=width)
                clan_prestige = int(round(prestige / cnt, 0))
                # print("Prestige:  ", clan_prestige)
            if data is None:
                if len(members) == 0 or len(members) > 30:
                    return None
                elif verbose:
                    return verbose_prestige
                else:
                    return clan_prestige
            else:
                if verbose and len(role_members) <= 30:
                    data.add_field(name='{} [{}] prestige: {}'
                                   .format(role.name, len(role_members), clan_prestige),
                                   value=verbose_prestige, inline=False)
                elif verbose:
                    data.add_field(
                            name='{} prestige {}'.format(role.name, clan_prestige),
                            value=summary + '\n\nVerbose prestige details '
                                            'restricted for roles with more than 30 members.',
                            inline=False)
                else:
                    data.add_field(
                            name='{} prestige {}'.format(role.name, clan_prestige),
                            value=summary,
                            inline=False)
                return data

    @checks.admin_or_permissions(manage_server=True)
    @alliance.command(name='delete', aliases=('unregister', 'del' 'remove', 'rm',), pass_context=True,
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
    @alliance.command(
                name='settings',
                pass_context=True,
                invoke_without_command=True,
                hidden=True,
                no_pm=True)
    async def _settings(self, ctx):
        server = ctx.message.server
        alliance = server.id
        if alliance in self.guilds.keys():
            keys = self.guilds[alliance].keys()
            data = self._get_embed(ctx)
            data.title = 'Alliance Settings:sparkles:'
            for item in self.info_keys:
                if item in keys:
                    data.add_field(name=item, value=self.guilds[alliance][item])
                else:
                    data.add_field(name=item, value='Not set.\n``/alliance set {} value``'
                                   .format(item), inline=False)
            if self.guilds[alliance]['type'] == 'basic':
                print('basic alliance')
                type_keys = self.alliance_keys
            else:
                type_keys = self.advanced_keys
            # for r in server.roles:
            #     if r.id == self.guilds[alliance]['officers']['id']:
            #         junk = await self._update_role(ctx, 'assign', r)
            #         junk.title = 'Alliance Assignment:sparkles:'
            #         junk.add_field(name='Assignment policy updated to:', value='basic')
            #         await self.bot.say(embed=junk)
            for key in type_keys:
                if key in keys:
                    for role in server.roles:
                        if self.guilds[alliance][key]['id'] == role.id:
                            data.add_field(name=key, value='{} : {}'.format(role.name, role.id))
                else:
                    data.add_field(name=key, value='Role is not set.\n``/alliance set {} value``'
                                   .format(key), inline=False)
            await self.bot.say(embed=data)

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
            return None, '{} not found in a registered CollectorVerse Alliance.'.format(user.name)

    def _get_role(self, server, role_key: str):
        """Returns discord.Role"""
        for role in server.roles:
            if role.id == self.guilds[server.id][role_key]['id']:
                return role
        return None

    @alliance.command(
                name='bg',
                aliases=('battlegroups', 'bgs', 'BG', 'BGs'),
                pass_context=True,
                no_pm=True
        )
    async def _battle_groups(self, ctx):
        """Report Alliance Battlegroups"""
        alliances, message = self._find_alliance(ctx.message.author)
        dcolor = discord.Color.gold()
        if alliances is None:
            data = self._get_embed(ctx, color=dcolor)
            data.title = 'Access Denied:sparkles:'
            data.description = 'This tool is only available for members of this alliance.'
            await self.bot.say(embed=data)
            return
        elif ctx.message.server.id in alliances:
            server = ctx.message.server
            alliance = server.id
            if 'alliance' in self.guilds[alliance].keys():
                members = _get_members(server, 'alliance')
                if members is None:
                    members = server.members
            else:
                members = server.members
            battle_groups = {}
            pages = []
            basic = False
            if self.guilds[alliance]['type'] == 'basic':
                basic = True
                for bg in 'bg1', 'bg2', 'bg3':
                    role = self._get_role(server, bg)
                    if role is not None:
                        role_members = _get_members(server, role)
                        if role_members is not None:
                            battle_groups.update({bg: {'role': role, 'members': role_members}})
            else:
                for bg in ('bg1', 'bg2', 'bg3', 'bg1aq', 'bg2aq', 'bg3aq', 'bg1aw', 'bg2aw', 'bg3aw'):
                    if bg in self.guilds[alliance].keys():
                        role = self._get_role(server, bg)
                        if role is not None:
                            role_members = _get_members(server, role)
                            if role_members is not None:
                                battle_groups.update({bg: {'role': role, 'members': role_members}})
            tag = ''
            if 'tag' in self.guilds[alliance].keys():
                tag = '[{}] '.format(self.guilds[alliance]['tag'])
            if basic:
                data = self._get_embed(ctx, alliance=alliance, color=dcolor)
                data.title = tag+'Alliance Battlegroups:sparkles:'
                for bg in ('bg1', 'bg2', 'bg3'):
                    if bg in battle_groups.keys() and len(battle_groups[bg]['members']) > 0:
                        data = await self._get_prestige(server, battle_groups[bg]['role'], verbose=True,
                                                        data=data, role_members=battle_groups[bg]['members'])
                    elif bg in battle_groups.keys() and len(battle_groups[bg]['members']) == 0:
                        data.description = 'Battlegroup {} has no members assigned'.format(bg)
                pages.append(data)
            else:
                data = self._get_embed(ctx, alliance=alliance, color=dcolor)
                data.title = tag + 'Alliance Quest Battlegroups:sparkles:'
                for bg in ('bg1aq', 'bg2aq', 'bg3aq'):
                    if bg in battle_groups.keys():
                        data = await self._get_prestige(server, battle_groups[bg]['role'], verbose=True, data=data,
                                                        role_members=battle_groups[bg]['members'])
                pages.append(data)
                data = self._get_embed(ctx, alliance=alliance, color=dcolor)
                data.title = tag + 'Alliance War Battlegroups:sparkles:'
                for bg in ('bg1aw', 'bg2aw', 'bg3aw'):
                    if bg in battle_groups.keys():
                        data = await self._get_prestige(server, battle_groups[bg]['role'], verbose=True, data=data,
                                                        role_members=battle_groups[bg]['members'])
                pages.append(data)
            overload = []
            for m in members:
                cnt = 0
                if basic:
                    for bg in ('bg1', 'bg2', 'bg3'):
                        if bg in battle_groups.keys() and m in battle_groups[bg]['members']:
                            cnt += 1
                else:
                    for bg in ('bg1aq', 'bg2aq', 'bg3aq'):
                        if bg in battle_groups.keys() and m in battle_groups[bg]['members']:
                            cnt += 1
                    if cnt > 1:
                        overload.append(m)
                    for bg in ('bg1aw', 'bg2aw', 'bg3aw'):
                        if bg in battle_groups.keys() and m in battle_groups[bg]['members']:
                            cnt += 1
                    if cnt > 1:
                        overload.append(m)
                if cnt > 1:
                    overload.append(m)
            if len(overload) > 0:
                data = self._get_embed(ctx, alliance=alliance, color=dcolor)
                data.title = 'Overloaded Battle Groups'
                block = '\n'.join(m.display_name for m in overload)
                data.add_field(name='Check these user\'s roles', value='```{}```'.format(block))
                pages.append(data)

    @checks.admin_or_permissions(manage_server=True)
    @alliance.command(name="create", aliases=('register', 'add'),
                      pass_context=True, invoke_without_command=True, no_pm=True)
    async def _reg(self, ctx):
        """Sign up to register your Alliance server!"""
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
    @alliance.group(
            name="set",
            aliases=('update',),
            pass_context=True,
            invoke_without_command=True,
            no_pm=True)
    async def update(self, ctx):
        """Update your CollectorVerse Alliance"""
        await send_cmd_help(ctx)

    @update.command(pass_context=True, name='name', no_pm=True)
    async def _alliance_name(self, ctx, *, value):
        """What's your Alliance name?"""
        key = "name"
        server = ctx.message.server
        if server.id not in self.guilds:
            data = _unknown_guild(ctx)
        else:
            data = self._update_guilds(ctx, key, value)
        await self.bot.say(embed=data)

    @update.command(pass_context=True, name='assign', no_pm=True)
    async def _assign(self, ctx, value, role: EnhancedRoleConverter):
        """Alliance assignment policy:
        officers (default)
        advanced (uncommon)

        'officers' : The Officers role will be allowed to set member assignments for Alliance Quest and Alliance War.
        'advanced' : The role specified will be allowed to set member assignments for Alliance Quest and Alliance War.
        """
        if value in ('basic', 'advanced',):
            key = "assign"
            server = ctx.message.server
            if server.id not in self.guilds:
                data = _unknown_guild(ctx)
            elif value == 'basic' and 'officers' in self.guilds[server.id].keys():
                for r in server.roles:
                    if r.id == self.guilds[server.id]['officers']['id']:
                        data = self._update_role(ctx, key, r)
                        continue
            elif value == 'advanced' and role is not None:
                data = self._update_role(ctx, key, role)
            else:
                data = self._get_embed(ctx)
                data.title = 'Alliance Assignment Error:sparkles:'
                data.description = 'Advanced Alliance assignment policies require a role be specified'
            await self.bot.say(embed=data)
        else:
            pass

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
            data = discord.Embed(color=get_color(ctx), title='CollectorVerse Alliances:sparkles:', description=message,
                                 url='https://discord.gg/umcoc')
        await self.bot.say(embed=data)

    @update.command(pass_context=True, name='tag')
    async def _alliance_tag(self, ctx, *, value):
        """5 character Alliance Tag."""
        key = "tag"
        # v = value.split('')
        if len(value) > 5:
            await self.bot.say('Clan Tag must be <= 5 characters.\nDo not include the [ or ] brackets.')
        server = ctx.message.server
        if server.id not in self.guilds:
            data = _unknown_guild(ctx)
        else:
            data = self._update_guilds(ctx, key, value)
        await self.bot.say(embed=data)

    @update.command(name='started', pass_context=True)
    async def _started(self, ctx, *, date: str):
        """When did you create this Alliance?"""
        key = "started"
        # value = date
        # print(value)
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
        elif 'line.me/' in value:
            data = self._get_embed(ctx)
            data.title = 'Discord > Line:sparkles:'
            data.description = 'Ooh, sorry. Line links are not supported by this Alliance management system. ' \
                               'Admit it.  You know Line is terrible.'
        elif 'group.me/' in value:
            data = self._get_embed(ctx)
            data.title = 'Discord > GroupMe:sparkles:'
            data.description = 'Ooh, sorry. GroupMe links are not supported by this Alliance management system. ' \
                               'Also, GroupMe?  Did you even try?'
        elif 'wa.me/' in value:
            data = self._get_embed(ctx)
            data.title = 'Discord > WhatsApp:sparkles:'
            data.description = 'Ooh, sorry. WhatsApp links are not supported by this Alliance management system. ' \
                               'Also, WhatsApp? That is really sad.'
        elif 'clanhq.app.link/' in value:
            data = self._get_embed(ctx)
            data.title = 'Discord > WhatsApp:sparkles:'
            data.description = 'Ooh, sorry. ClanHQ links are not supported by this Alliance management system. ' \
                               'Also, Hahahahaha ha ha haa ha ha ' \
                               '...' \
                               'whew ' \
                               'I ran out of breath.'
        else:
            data = self._update_guilds(ctx, key, value)
        await self.bot.say(embed=data)

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
                data.title = 'Image Verification Failed:sparkles:'
            else:
                data = self._update_guilds(ctx, key, value)
                data.set_image(url=value)
        await self.bot.say(embed=data)

    @update.command(pass_context=True, name='invite')
    async def _invite(self, ctx, *, value):
        """Alliance Server permanent join link"""
        key = 'invite'
        if ctx.message.server.id not in self.guilds:
            data = _unknown_guild(ctx)
        elif 'line.me/' in value:
            data = self._get_embed(ctx)
            data.title = 'Discord > Line:sparkles:'
            data.description = 'Ooh, sorry. Line links are not supported by this Alliance management system. ' \
                               'Admit it.  You know Line is terrible.'
        elif 'group.me/' in value:
            data = self._get_embed(ctx)
            data.title = 'Discord > GroupMe:sparkles:'
            data.description = 'Ooh, sorry. GroupMe links are not supported by this Alliance management system. ' \
                               'Also, GroupMe?  Did you even try?'
        elif 'wa.me/' in value:
            data = self._get_embed(ctx)
            data.title = 'Discord > WhatsApp:sparkles:'
            data.description = 'Ooh, sorry. WhatsApp links are not supported by this Alliance management system. ' \
                               'Also, WhatsApp? That is really sad.'
        elif 'clanhq.app.link/' in value:
            data = self._get_embed(ctx)
            data.title = 'Discord > WhatsApp:sparkles:'
            data.description = 'Ooh, sorry. ClanHQ links are not supported by this Alliance management system. ' \
                               'Also, Hahahahaha ha ha haa ha ha ' \
                               '...' \
                               'whew ' \
                               'I ran out of breath.'
        elif 'discord.gg' not in value:
            data = self._get_embed(ctx)
            data.add_field(name='Warning:sparkles:', value='Only Discord server links are supported.')
        else:
            data = self._update_guilds(ctx, key, value)
        menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @checks.admin_or_permissions(manage_server=True)
    @update.command(pass_context=True, name='officers')
    async def _officers(self, ctx, role: EnhancedRoleConverter = None):
        """Which role are your Alliance Officers?"""
        data = await self._update_role(ctx, key='officers', role=role)
        await self.bot.say(embed=data)

    @update.command(pass_context=True, name='bg1')
    async def _bg1(self, ctx, role: EnhancedRoleConverter = None):
        """Which role is your Battlegroup 1?"""
        print("updating bg1")
        data = await self._update_role(ctx, key='bg1', role=role)
        await self.bot.say(embed=data)

    @update.command(pass_context=True, name='bg1aq')
    async def _bg1aq(self, ctx, role: EnhancedRoleConverter = None):
        """Which role is your Battlegroup 1 for Alliance Quest?"""
        data = await self._update_role(ctx, key='bg1aq', role=role)
        await self.bot.say(embed=data)

    @update.command(pass_context=True, name='bg1aw')
    async def _bg1aw(self, ctx, role: EnhancedRoleConverter = None):
        """Which role is your Battlegroup 1 for Alliance War?"""
        # if role.name == 'everyone':
        #     data = self._get_embed(ctx)
        #     data.title = 'Alliance Role restriction:sparkles:'
        #     data.description = 'The ``@everyone`` role is prohibited from being set as an alliance role.'
        # else:
        data = await self._update_role(ctx, key='bg1aw', role=role)
        await self.bot.say(embed=data)

    @update.command(pass_context=True, name='bg2')
    async def _bg2(self, ctx, role: EnhancedRoleConverter = None):
        """Which role is your Battlegroup 2?"""
        data = await self._update_role(ctx, key='bg2', role=role)
        await self.bot.say(embed=data)

    @update.command(pass_context=True, name='bg2aq')
    async def _bg2aq(self, ctx, role: EnhancedRoleConverter = None):
        """Which role is your Battlegroup 2 for Alliance Quest?"""
        data = await self._update_role(ctx, key='bg2aq', role=role)
        await self.bot.say(embed=data)

    @update.command(pass_context=True, name='bg2aw')
    async def _bg2aw(self, ctx, role: EnhancedRoleConverter = None):
        """Which role is your Battlegroup 2 for Alliance War?"""
        data = await self._update_role(ctx, key='bg2aw', role=role)
        await self.bot.say(embed=data)

    @update.command(pass_context=True, name='bg3')
    async def _bg3(self, ctx, role: EnhancedRoleConverter = None):
        """Which role is your Battlegroup 3?"""
        data = await self._update_role(ctx, key='bg3', role=role)
        await self.bot.say(embed=data)

    @update.command(pass_context=True, name='bg3aq')
    async def _bg3aq(self, ctx, role: EnhancedRoleConverter = None):
        """Which role is your Battlegroup 3 for Alliance Quest?"""
        data = await self._update_role(ctx, key='bg3aq', role=role)
        await self.bot.say(embed=data)

    @update.command(pass_context=True, name='bg3aw')
    async def _bg3aw(self, ctx, role: EnhancedRoleConverter = None):
        """Which role is your Battlegroup 3 for Alliance War?"""
        data = await self._update_role(ctx, key='bg3aw', role=role)
        await self.bot.say(embed=data)

    @update.command(pass_context=True, name='alliance')
    async def _alliance(self, ctx, role: EnhancedRoleConverter = None):
        """Which role represents all members of your alliance (up to 30)?"""
        data = await self._update_role(ctx, key='alliance', role=role)
        await self.bot.say(embed=data)

    def _create_alliance(self, ctx, server):
        """Create alliance.
        Set basic information"""
        self.guilds[server.id] = {'type': 'basic', 'name': server.name, 'assign': 'officers'}
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
        print("update: ", server.name, role.name)
        if server.id not in self.guilds:
            return _unknown_guild(ctx)
        if role is not None and role.name == '@everyone':
            data = self._get_embed(ctx)
            data.title = 'Alliance Role restriction:sparkles:'
            data.description = 'The ``@everyone`` role is prohibited from ' \
                               'being set as an alliance role.'
            return data
        data = discord.Embed(colour=get_color(ctx), title='Role Registration:sparkles:')
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

    # @alliance.command(pass_context=True, invoke_without_command=True, hidden=False, no_pm=True)
    # async def assign(self, ctx, alliance_map: str, tier, path, user=discord.Member):
    #     """Alliance Assignment tool
    #     Tiers = t1, t2, t3
    #     Paths = A, B, C, E, F, G, H, I, J
    #
    #     example:
    #     /alliance assign aq5 t1 B <user>
    #     """
    #     alliance_map=alliance_map.lower()
    #     tier = tier.lower()
    #     path = path.lower()
    #     server = ctx.message.server
    #     alliance = server.id
    #     if 'alliance' in self.guilds[alliance]:
    #         alliancerole = self._get_role(server, 'alliance')
    #     members = _get_members(server, alliancerole)
    #     valid_maps = {'aw': {'t1': 'abcdefghi'},
    #                   'aq1': {'t1': 'abcdefgh', 't2': 'abcdefgh', 't3': 'abcdefgh'},
    #                   'aq2': {'t1': 'abcdefgh', 't2': 'abcdefgh'},
    #                   'aq3': {'t1': 'abcde', 't2': 'abcd', 't3': 'abcde'},
    #                   'aq4': {'t1': 'abcde', 't2': 'abcdef', 't3': 'abcdefg'},
    #                   'aq5': {'t1': 'abcdefgh', 't2': 'abcdefgh', 't3': 'abcdefgh'},
    #                   'aq6': {'t1': 'abcdefg', 't2': 'abcdefghi', 't3': 'abcdefghij'},
    #                   'aq7': {'t1': 'abcdefg', 't2': 'abcdefghi', 't3': 'abcdefghij'}}
    #
    #     data = self._get_embed(ctx, color=user.color)
    #
    #     if alliance_map not in ('aq1', 'aq2', 'aq3', 'aq4', 'aq5', 'aq6', 'aq7', 'aw'):
    #         data.title = 'Assignment Error'
    #         data.description = 'Specify the AQ or AW map.  \n' \
    #                            'aq1, aq2, aq3, aq4, aq5, aq6, aq7, aw'
    #         await self.bot.say(embed=data)
    #         return
    #
    #     if 'assignments' not in self.guilds[alliance].keys():
    #         self.guilds[alliance].update({'assignments': {}})
    #         dataIO.save_json(self.alliances, self.guilds)
    #     if alliance_map not in self.guilds[alliance]['assignments'].keys():
    #         self.guilds[alliance]['assignments'].update({alliance_map: {'t1': {}, 't2': {}, 't3': {}}})
    #         for t in ('t1', 't2', 't3'):
    #             if t in valid_maps[alliance_map].keys():
    #                 for path in valid_maps[alliance_map][t].split(''):
    #                     self.guilds[alliance]['assignments'][alliance_map][t].update({path: {}})
    #         dataIO.save_json(self.alliances, self.guilds)
    #
    #     if alliance_map in valid_maps.keys and tier in ('t1', 't2', 't3')
    #
    #
    #     data.title = 'Member Assignment'
    #     for m in self.guilds[alliance]['assignments'][user.id].keys():
    #         data.add_field(name=m.upper(), value=self.guilds[alliance]['assignments'][user.id][m])
    #     await self.bot.say(embed=data)


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


def _get_members(server, role):
    """Returns list of discord.server.members"""
    members = []
    for m in server.members:
        if role in m.roles:
            members.append(m)
    if len(members) > 0:
        return members
    else:
        return None


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
