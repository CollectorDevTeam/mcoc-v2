import re
import os
import json
import logging
import datetime
import discord
import requests
import csv
import pygsheets
from discord.ext import commands
from dateutil.parser import parse as date_parse
from __main__ import send_cmd_help
from .utils.dataIO import dataIO
from .utils import checks
from .utils import chat_formatting as chat
from cogs.mcocTools import (
    KABAM_ICON, COLLECTOR_ICON, CDT_COLORS, PATREON, COLLECTOR_FEATURED)
from .cdtembed import CDTEmbed
from .cdtpagesmenu import PagesMenu
from cogs.hook import RosterUserConverter, ChampionRoster
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
        self.backup = "data/account/alliances-backup-{}.json"
        self.guilds = dataIO.load_json(self.alliances)
        self.alliance_keys = ('officers', 'bg1', 'bg2', 'bg3', 'alliance',)
        self.advanced_keys = ('officers', 'bg1', 'bg2', 'bg3', 'alliance',
                              'bg1aq', 'bg2aq', 'bg3aq', 'bg1aw', 'bg2aw', 'bg3aw',)
        self.info_keys = ('name', 'tag', 'type', 'about',
                          'started', 'invite', 'poster', 'wartool')
        self.service_file = "data/mcoc/mcoc_service_creds.json"
        self.diagnostics_channel = '565254324595326996'
        self.pagesmenu = PagesMenu(self.bot)

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
                await self.bot.send_message(ctx.message.channel, embed=data)

    @commands.command(pass_context=True, no_pm=True, hidden=True)
    async def bglanes(self, ctx, role: discord.role):
        server = ctx.message.server
        alliance = server.id
        members = _get_members(server, role)

        if members is not None:
            pages = []
            for m in ('aq1', 'aq2', 'aq3', 'aq4', 'aq5', 'aq6', 'aq7', 'aw',):
                data = self._get_embed(
                    ctx, alliance=alliance, color=role.color)
                data.title = '{} Assignments for {}'.format(
                    role.name, m.upper())
                cnt = 0
                for member in members:
                    if member.id in self.guilds[alliance]['assignments'].keys():
                        if m in self.guilds[alliance]['assignments'][member.id].keys():
                            data.add_field(
                                name=member.display_name, value=self.guilds[alliance]['assignments'][member.id][m])
                            cnt += 1
                if cnt > 0:
                    pages.append(data)
            if len(pages) > 0:
                menu = PagesMenu(self.bot, timeout=120,
                                 delete_onX=True, add_pageof=True)
                await menu.menu_start(pages=pages)
            else:
                logger.warning('No Pages to display')

    @commands.group(aliases=('clan', 'guild'), pass_context=True, invoke_without_command=True, hidden=False, no_pm=True)
    async def alliance(self, ctx, user: discord.Member = None):
        """CollectorVerse Alliance tools

        """
        # server = ctx.message.server
        print('debug: alliance group')
        # self._update_members(ctx, ctx.message.server)

        if ctx.invoked_subcommand is None:
            if user is None:
                user = ctx.message.author
            await self._show_public(ctx, user)

    async def _show_public(self, ctx, user: discord.Member = None):
        """Display Alliance public profile"""
        if user is None:
            user = ctx.message.author
        alliances, message = await self._find_alliance(ctx, user)
        pages = []
        if ctx.message.server.id in self.guilds.keys():
            if "alliance" not in self.guilds[ctx.message.server.id].keys():
                data = self._get_embed(ctx)
                data.title = "Attention"
                data.description = "This Discord guild is a registered CollectorVerse Alliance.\nThe ``alliance`` role is not set.\n\nUse the command ``/alliance set alliance <alliance role>`` to set this value.\nThe Alliance system will be disabled until this is corrected."
                data.add_field(name="Server ID", value=ctx.message.server.id)
                await self.bot.send_message(ctx.message.channel, embed=data)
                await self.diagnostics(data)
        if alliances is None:
            data = self._get_embed(ctx)
            data.title = message+':sparkles:'
            if ctx.message.server.id in self.guilds.keys():
                alliance = ctx.message.server.id
                keys = self.guilds[alliance].keys()
                roleregistered = False
                for key in self.advanced_keys:
                    if key in keys:
                        roleregistered = True
                        continue
                if roleregistered is False:
                    data.add_field(name='This alliance server is registered.',
                                   value='However, no roles have been registered for '
                                         '``alliance``, ``officers`` or ``bg1 | bg2 | bg3``')
            await self.bot.send_message(ctx.message.channel, embed=data)
            return
        else:
            for alliance in alliances:
                self._update_members(ctx, self.bot.get_server(alliance))
        alliances, message = await self._find_alliance(ctx, user)
        if alliances is not None:
            for alliance in alliances:
                keys = self.guilds[alliance].keys()
                server = self.bot.get_server(alliance)
                data = self._get_embed(ctx, alliance=alliance, user_id=user.id)
                if server is not None:
                    if 'tag' in keys:
                        if 'name' in keys:
                            data.title = '[{}] {}:sparkles:'.format(
                                self.guilds[alliance]['tag'], self.guilds[alliance]['name'])
                        else:
                            data.title = '[{}] {}:sparkles:'.format(
                                self.guilds[alliance]['tag'], server.name)
                    elif 'name' in keys:
                        data.title = '{}:sparkles:'.format(server.name)
                        data.add_field(name='Alliance Tag',
                                       value='Alliance Tag not set.')
                    else:
                        data.title = server.name+':sparkles:'
                    if 'about' in keys:
                        data.description = self.guilds[alliance]['about']
                    else:
                        data.description = 'Alliance About is not set.'
                    if 'alliance' in keys:
                        alliance_role = self._get_role(server, 'alliance')
                        if alliance_role is None:
                            await self.diagnostics('Alliance role not found')
                        else:
                            # role_members = _get_members(server, alliance_role)
                            verbose = False
                            if ctx.message.server == server:  # on home server
                                verbose = True
                            data = await self._get_prestige(server=server, role=alliance_role, verbose=verbose,
                                                            data=data)
                            # data.add_field(name='Alliance Prestige', value=clan_prestige)
                    else:
                        data.add_field(name='⚠ Alliance Role ⚠',
                                       value='Alliance role is not set. '
                                            'A role to designate all 30 alliance members is essential. '
                                            'Use the command ``/alliance set alliance <role>`` to correct.')
                    if 'started' in keys:
                        since = date_parse(self.guilds[alliance]['started'])
                        days_since = (datetime.datetime.utcnow() - since).days
                        data.add_field(name='Alliance founded: {}'.format(since.date()), value="Playing for {} days!"
                                       .format(days_since))
                    if 'poster' in keys:
                        data.set_image(url=self.guilds[alliance]['poster'])
                    if 'invite' in keys:
                        data.url = self.guilds[alliance]['invite']
                        data.add_field(name='Join server',
                                       value=self.guilds[alliance]['invite'])
                    else:
                        data.add_field(name='Join server',
                                       value='Invitation not set.')
                    pages.append(data)
        if len(pages) > 0:
            if ctx.message.server.id in alliances:
                i = alliances.index(ctx.message.server.id)
            else:
                i = 0
            menu = PagesMenu(self.bot, timeout=120,
                             delete_onX=True, add_pageof=True)
            await menu.menu_start(pages=pages, page_number=i)
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
        data = CDTEmbed.create(
            self, ctx, footer_text="A CollectorVerse Alliance")
        # data = discord.Embed(color=color, title='', description='')
        # data.set_author(name='A CollectorVerse Alliance',
        #                 icon_url=COLLECTOR_ICON)
        if server is not None:
            data.set_thumbnail(url=server.icon_url)
        # data.set_footer(text='CollectorDevTeam', icon_url=COLLECTOR_ICON)
        return data

    async def _get_prestige(self, server: discord.Server, role: discord.Role, verbose=False,
                            data: discord.Embed = None, role_members=None):
        """Return Clan Prestige and Verbose Prestige for Role members"""
        # await self.diagnostics("_get_prestige for role: {} on guild: {}".format(role.id, server.id))
        # logger.info("Retrieving prestige for role '{}' on guild '{}'".format(
        #     role.name, server.name, ))
        # members = []
        line_out = {}
        # line_out = []
        width = 20
        prestige = 0
        cnt = 0
        if role_members is None:
            role_members = []
            for member in server.members:
                if role in member.roles:
                    role_members.append(member)
        for member in role_members:
            roster = ChampionRoster(self.bot, member)
            await roster.load_champions(silent=True)
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
        if cnt > 0 and cnt <= 30:
            summary = '{0:{width}}   = {1} from {2}/{3} members'.format(
                role.name, round(prestige / cnt, 0), cnt, len(role_members), width=width)
            clan_prestige = int(round(prestige / cnt, 0))
            # print("Prestige:  ", clan_prestige)
        if data is None:
            if len(role_members) == 0 or len(role_members) > 30:
                return None
            elif verbose:
                return verbose_prestige
            else:
                return clan_prestige
        else:
            if verbose and len(role_members) <= 30:
                data.add_field(name='{} [{}/{}] prestige: {}'
                               .format(role.name, cnt, len(role_members), clan_prestige),
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

    @checks.is_owner()
    @alliance.command(pass_context=True, hidden=True, name='scavenge')
    async def _scavenge(self, ctx, server=None):
        dataIO.save_json(
            self.backup.format(ctx.message.id), self.guilds)
        servers = self.bot.servers
        serverids = []
        good_alliance = 0
        bad_alliance_role = 0
        # message = ['guildkeys          | server ids\n'
        message = []
        kill_list = []
        guildkeys = self.guilds.keys()
        for key in guildkeys:
            server = self.bot.get_server(key)
            if server is None:
                await self.diagnostics("Could not retrieve server "+key)
            # if key not in serverids:
                message.append('{} | {}'.format(key, 'not found'))
                kill_list.append(key)
            if server is not None:
                if 'alliance' not in self.guilds[key].keys():
                    # bad alliance:
                    await self.diagnostics("Searching for 'alliance' role in server "+key)
                    for r in server.roles:
                        if r.name == 'alliance':
                            await self.diagnostics("'alliance' = {} role found for server {}".format(r.id, key))
                            message.append('{} | {}'.format(
                                key, 'found      | setting alliance id = {}'.format(r.id)))
                            # self._update_role(ctx, 'alliance', r)
                            self._get_role_members(ctx, server, r, "alliance")
                            break
                    if 'alliance' not in self.guilds[key].keys():
                        message.append('{} | {}'.format(
                            key, 'not found  | alliance undefined'))

                await self.diagnostics("Updating members in server "+key)
                self._update_members(ctx, server)

        if len(kill_list) > 0:
            for k in kill_list:
                self.guilds.pop(k, None)
        dataIO.save_json(self.alliances, self.guilds)
        pages = chat.pagify('\n'.join(sorted(message)))
        header = '```Alliance Guilds    | found y/n  | status ```'
        for page in pages:
            await self.diagnostics(header)
            await self.diagnostics(chat.box(page))
        await self.bot.send_message(ctx.message.channel, "Alliance good: {}\nAlliance bad updated: {}\nAlliance deleted: {}\nTotal guilds checked: {}".format(good_alliance, bad_alliance_role, len(kill_list), len(servers)))

    @alliance.command(pass_context=True, hidden=False, name='template', )
    async def _template(self, ctx):
        '''Basic server alliance creation.
        '''
        author = ctx.message.author
        chan = ctx.message.channel
        data = self._get_embed(ctx)
        data.title = "CollectorDevTeam Alliance Template:sparkles:"
        data.url = PATREON
        data.description = 'Want to create an MCOC alliance server? \n\n' \
            '1. Use CDT [Alliance Template](https://discord.new/gtzuXHq2kCg4) to create a new Discord guild with necessary channels, roles, & permissions. \n' \
            '2. Invite [Collector <:portrait_collector:398531581834166293> ](https://discordapp.com/oauth2/authorize?client_id=210480249870352385&scope=bot&permissions=8) \n' \
            '3. Add announcements in #announcemets with ``/addchan`` \n' \
            '4. Use ``/alliance create`` to register your CollectorVerse Alliance so you can easily recruit in <#403412020155645962>.\n' \
            '5. Visit [CollectorDevTeam](https://discord.gg/BwhgZxk) for Support and Q&A. \n\n' \
            'Don\'t forget to follow <#616679045026938886> , <#616679471201648682> or the <#594209177639976976> '
        data.set_footer(
            text='CollectorDevTeam | Alliance Template', icon_url=COLLECTOR_ICON)
        data.set_thumbnail(url=COLLECTOR_FEATURED)
        data.set_author(name='{}\n[{}]'.format(
            author.display_name, author.id), icon_url=author.avatar_url)
        await self.bot.send_message(chan, embed=data)
        await self.diagnostics(data)

    @alliance.command(pass_context=True, hidden=False, name='export', aliases=('awx',))
    async def _role_roster_export(self, ctx):
        '''Returns a CSV file with all Roster data for alliance members
        Requires that ALLIANCE settings be configured with roles for alliance, bg1, bg2, bg3
        '''
        server = ctx.message.server
        alliance = server.id
        roster = ChampionRoster(ctx.bot, ctx.message.author)
        await roster.load_champions(silent=True)
        # rand = randint(1000, 9999)
        path, ext = os.path.split(roster.champs_file)
        tmp_file = '{}-{}.tmp'.format(path, alliance)
        # with open(tmp_file, 'w') as fp:
        with open(tmp_file, 'w', encoding='utf-8') as fp:
            writer = csv.DictWriter(fp, fieldnames=['member_mention', 'member_name', *(
                roster.fieldnames), 'bg'], extrasaction='ignore', lineterminator='\n')
            writer.writeheader()
            if alliance in self.guilds.keys():
                members = _get_members(
                    server, self._get_role(server, 'alliance'))
                if self.guilds[alliance]['type'] == 'basic':
                    bg1 = self._get_role(server, 'bg1')
                    bg2 = self._get_role(server, 'bg2')
                    bg3 = self._get_role(server, 'bg3')
                else:
                    bg1 = self._get_role(server, 'bg1aw')
                    bg2 = self._get_role(server, 'bg2aw')
                    bg3 = self._get_role(server, 'bg3aw')
                for member in members:
                    if bg1 in member.roles and bg1 is not None:
                        bg = 'bg1'
                    elif bg2 in member.roles and bg2 is not None:
                        bg = 'bg2'
                    elif bg3 in member.roles and bg3 is not None:
                        bg = 'bg3'
                    else:
                        bg = 'NA'
                    roster = ChampionRoster(ctx.bot, member)
                    await roster.load_champions(silent=True)
                    for champ in roster.roster.values():
                        champ_dict = champ.to_json()
                        champ_dict['member_mention'] = member.mention
                        champ_dict['member_name'] = member.name
                        champ_dict['bg'] = bg
                        writer.writerow(champ_dict)
            else:
                for member in server.members:
                    for roles in member.roles:
                        if 'bg1' in roles.name:
                            bg = 'bg1'
                            continue
                        elif 'bg2' in roles.name:
                            bg = 'bg2'
                            continue
                        elif 'bg3' in roles.name:
                            bg = 'bg3'
                            continue
                        else:
                            bg = 'NA'
                            continue
                        roster = ChampionRoster(ctx.bot, member)
                        await roster.load_champions(silent=True)
                        for champ in roster.roster.values():
                            champ_dict = champ.to_json()
                            champ_dict['member_mention'] = member.mention
                            champ_dict['member_name'] = member.name
                            champ_dict['bg'] = bg
                            writer.writerow(champ_dict)
        filename = roster.data_dir + '/' + alliance + '.csv'
        os.replace(tmp_file, filename)
        await self.bot.upload(filename)
        os.remove(filename)

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
            menu = PagesMenu(self.bot, timeout=120,
                             delete_onX=True, add_pageof=True)
            await self.bot.delete_message(confirmation)
            await menu.menu_start(pages=[data])

    @checks.admin_or_permissions(manage_server=True)
    @alliance.command(
        name='settings',
        pass_context=True,
        invoke_without_command=True,
        hidden=False,
        no_pm=True)
    async def _settings(self, ctx, serverid=None):
        if serverid is None:
            server = ctx.message.server
            alliance = server.id
        else:
            server = self.bot.get_server(serverid)
            alliance = server.id
        if alliance in self.guilds.keys():
            keys = self.guilds[alliance].keys()
            data = self._get_embed(ctx)
            data.title = 'Alliance Settings:sparkles:'
            for item in self.info_keys:
                if item in keys:
                    data.add_field(
                        name=item, value=self.guilds[alliance][item])
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
            #         await self.bot.send_message(ctx.message.channel, embed=junk)
            for key in type_keys:
                if key in keys:
                    for role in server.roles:
                        if self.guilds[alliance][key]['id'] == role.id:
                            data.add_field(
                                name=key, value='{} : {}'.format(role.name, role.id))
                else:
                    data.add_field(name=key, value='Role is not set.\n``/alliance set {} value``'
                                   .format(key), inline=False)
            await self.bot.send_message(ctx.message.channel, embed=data)
            # channel = self.bot.get_channel('565254324595326996')
            data.add_field(name='Requested by', value='User: {} \nID: {} \nServer {} \nID: {}'.format(
                ctx.message.author.display_name, ctx.message.author.id, ctx.message.server.name, ctx.message.server.id))
            await self.diagnostics(data)

    async def _find_alliance(self, ctx, user: discord.User):
        """Returns a list of Server IDs or None"""
        user_alliances = []
        poplist = []
        for alliance in self.guilds.keys():
            server = self.bot.get_server(alliance)
            if server is None:
                poplist.append(alliance)
                await self.diagnostics("find_alliance not-CollectorVerse {}: popped".format(alliance))
            else:
                # self._update_members(ctx, server)
                if "alliance" not in self.guilds[alliance].keys():
                    for r in server.roles:
                        if r.name == 'alliance':
                            # self._update_role(ctx, 'alliance', r)
                            self._get_role_members(ctx, server, r, "alliance")
                            await self.diagnostics("find_alliance 'alliance' role found, updated guild")
                if "alliance" in self.guilds[alliance].keys():
                    if user.id in self.guilds[alliance]["alliance"]["member_ids"]:
                        user_alliances.append(alliance)
                        await self.diagnostics("{} found in {} members".format(user.id, alliance))
        if len(poplist) > 0:
            for a in poplist:
                self.guilds.pop(a, None)
        dataIO.save_json(self.alliances, self.guilds)

        # await self.diagnostics(user_alliances)
        if len(user_alliances) > 0:
            return user_alliances, None
        else:
            return None, '{} not found in a registered CollectorVerse Alliance.'.format(user.name)

    def _get_role(self, server: discord.Server, role_key: str):
        """Returns discord.Role"""
        if role_key in self.guilds[server.id].keys() and self.guilds[server.id][role_key] is not None:
            for role in server.roles:
                if role.id == self.guilds[server.id][role_key]['id']:
                    print("_get_role found role")
                    return role
        return None

    @alliance.command(name='bg', aliases=('battlegroups', 'bgs', 'BG', 'BGs'), pass_context=True, no_pm=True)
    async def _battle_groups(self, ctx):
        """Report Alliance Battlegroups"""
        alliances, message = await self._find_alliance(ctx, ctx.message.author)
        # dcolor = discord.Color.gold()
        server = ctx.message.server
        alliance = server.id
        if alliances is None:
            data = self._get_embed(ctx)
            data.title = 'Access Denied:sparkles:'
            data.description = 'This tool is only available for members of this alliance.'
            await self.bot.send_message(ctx.message.channel, embed=data)
            return
        elif alliance in self.guilds.keys():
            # server = ctx.message.server
            # alliance = server.id
            if 'alliance' in self.guilds[alliance].keys():
                members = _get_members(
                    server, self._get_role(server, 'alliance'))
                if members is None:
                    members = server.members
            else:
                members = server.members
        else:
            print('server id not in alliances manifest')
            return
        if alliance in self.guilds.keys():
            battle_groups = {}
            pages = []
            basic = False
            if self.guilds[alliance]['type'] == 'basic':
                basic = True
                for bg in ('bg1', 'bg2', 'bg3'):
                    role = self._get_role(server, bg)
                    if role is not None:
                        role_members = _get_members(server, role)
                        if role_members is not None:
                            battle_groups.update(
                                {bg: {'role': role, 'members': role_members}})
            else:
                for bg in ('bg1', 'bg2', 'bg3', 'bg1aq', 'bg2aq', 'bg3aq', 'bg1aw', 'bg2aw', 'bg3aw'):
                    if bg in self.guilds[alliance].keys():
                        role = self._get_role(server, bg)
                        if role is not None:
                            role_members = _get_members(server, role)
                            if role_members is not None:
                                battle_groups.update(
                                    {bg: {'role': role, 'members': role_members}})
            tag = ''
            if 'tag' in self.guilds[alliance].keys():
                tag = '[{}] '.format(self.guilds[alliance]['tag'])
            if basic:
                data = self._get_embed(ctx, alliance=alliance)
                data.title = tag+'Alliance Battlegroups:sparkles:'
                for bg in ('bg1', 'bg2', 'bg3'):
                    if bg in battle_groups.keys() and len(battle_groups[bg]['members']) > 0:
                        data = await self._get_prestige(server, battle_groups[bg]['role'], verbose=True,
                                                        data=data)
                    elif bg in battle_groups.keys() and len(battle_groups[bg]['members']) == 0:
                        data.description = 'Battlegroup {} has no members assigned'.format(
                            bg)
                needsbg = []
                if self.guilds[alliance]['alliance']['id'] is not None:
                    alliance_role = self._get_role(server, 'alliance')
                    amembers = _get_members(server, alliance_role)
                    if amembers is not None:
                        for member in amembers:
                            assigned = False
                            for bg in battle_groups.keys():
                                if member in battle_groups[bg]['members']:
                                    assigned = True
                                    continue
                            if assigned is False:
                                needsbg.append(member)
                        if len(needsbg) > 0:
                            # data.add_field(name='Pending Battlegroup assignment:', value='  ')
                            data = await self._get_prestige(server=server, role=alliance_role, verbose=True,
                                                            data=data, role_members=needsbg)
                            # data.add_field(name='Needs Battlegroup assignment', value=package)
                            # await self.bot.send_message(ctx.message.channel, "Needs BG assignment\n"+package)
                pages.append(data)
            else:
                data = self._get_embed(ctx, alliance=alliance)
                data.title = tag + 'Alliance Quest Battlegroups:sparkles:'
                for bg in ('bg1aq', 'bg2aq', 'bg3aq'):
                    if bg in battle_groups.keys():
                        data = await self._get_prestige(server, battle_groups[bg]['role'], verbose=True, data=data)
                pages.append(data)
                data = self._get_embed(ctx, alliance=alliance)
                data.title = tag + 'Alliance War Battlegroups:sparkles:'
                for bg in ('bg1aw', 'bg2aw', 'bg3aw'):
                    if bg in battle_groups.keys():
                        data = await self._get_prestige(server, battle_groups[bg]['role'], verbose=True, data=data)
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
                data = self._get_embed(ctx, alliance=alliance)
                data.title = 'Overloaded Battle Groups'
                block = '\n'.join(m.display_name for m in overload)
                data.add_field(name='Check these user\'s roles',
                               value='```{}```'.format(block))
                pages.append(data)

            menu = PagesMenu(self.bot, timeout=120,
                             delete_onX=True, add_pageof=True)
            await menu.menu_start(pages=pages)

    # @alliance.command(name="timezone", aliases=('tz','time','times'), pass_context=True, no_pm=True)
    # async def _timezone_by_role(self, ctx, role: discord.Role = None):
    #     alliances, message = await self._find_alliance(ctx.message.author)
    #     dcolor = discord.Color.gold()
    #     server = ctx.message.server
    #     data = self._get_embed(ctx, color=dcolor)
    #     alliance = server.id
    #     if alliances is None:
    #         data.title = 'Access Denied:sparkles:'
    #         data.description = 'This tool is only available for members of this alliance.'
    #         await self.bot.send_message(ctx.message.channel, embed=data)
    #         return
    #     elif role is None:
    #         data.title = 'Invalid Role:sparkles:'
    #         data.description = 'Include a valid role from this server.'
    #         await self.bot.send_message(ctx.message.channel, embed=data)
    #         return
    #     else:
    #         role_members = _get_members(server, role)
    #         if role_members is None:
    #             data.title = 'Unassigned Role:sparkles:'
    #             data.description = 'Role {} is not assigned to any server members.'.format(role.name)
    #         else:

    @checks.admin_or_permissions(manage_server=True)
    @alliance.command(name="create", aliases=('register', 'add'),
                      pass_context=True, invoke_without_command=True, no_pm=True)
    async def _reg(self, ctx):
        await self.register_alliance(ctx)
        return

    async def register_alliance(self, ctx):
        """Sign up to register your Alliance server!"""
        user = ctx.message.author
        server = ctx.message.server
        question = '{}, do you want to register this Discord Server as your Alliance Server?' \
                   'If you have any of the following roles, they will be automatically bound.\n' \
                   '```alliance, officers, bg1, @bg2, @bg3```\n' \
                   ':warning:\n' \
                   'The Alliance tool will not function unless an **alliance** role is designated.\n' \
                   'If you do not have an **alliance** role, create one and assign it to the members of your alliance.\n' \
                   'Designate that role using the command ``/alliance set alliance <role>``\n' \
                   'If you have other issues, use the command ``/alliance settings`` to view and verify your settings.\n'\
            .format(ctx.message.author.mention)
        # answer, confirmation = await PagesMenu.confirm(self, ctx, question)
        answer, confirmation = await self.pagesmenu.confirm(ctx, question)
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
                            # await self.bot.send_message(ctx.message.channel, '{} role recognized and auto-registered.'.format(role.name))
                            data_pages.append(data)
            else:
                data = discord.Embed(colour=get_color(ctx))
                data.add_field(name="Error:warning:",
                               value="Oops, it seems like you have already registered this guild, {}."
                               .format(user.mention))
                data.set_footer(text='CollectorDevTeam',
                                icon_url=COLLECTOR_ICON)
                data_pages.append(data)
            if len(data_pages) > 0:
                await self.bot.delete_message(confirmation)
            menu = PagesMenu(self.bot, timeout=120,
                             delete_onX=True, add_pageof=True)
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
        await self.bot.send_message(ctx.message.channel, embed=data)

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
            await self.bot.send_message(ctx.message.channel, embed=data)
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
        await self.bot.send_message(ctx.message.channel, embed=data)

    @update.command(pass_context=True, name='tag')
    async def _alliance_tag(self, ctx, *, value):
        """5 character Alliance Tag."""
        key = "tag"
        # v = value.split('')
        if len(value) > 5:
            await self.bot.send_message(ctx.message.channel, 'Clan Tag must be <= 5 characters.\nDo not include the [ or ] brackets.')
        server = ctx.message.server
        if server.id not in self.guilds:
            data = _unknown_guild(ctx)
        else:
            data = self._update_guilds(ctx, key, value)
        await self.bot.send_message(ctx.message.channel, embed=data)

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
            await self.bot.send_message(ctx.message.channel, embed=data)
        else:
            await self.bot.send_message(ctx.message.channel, 'Enter a valid date.')

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
        await self.bot.send_message(ctx.message.channel, embed=data)

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
        await self.bot.send_message(ctx.message.channel, embed=data)

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
            data.add_field(name='Warning:sparkles:',
                           value='Only Discord server links are supported.')
        else:
            data = self._update_guilds(ctx, key, value)
        menu = PagesMenu(self.bot, timeout=120,
                         delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=[data])

    @checks.admin_or_permissions(manage_server=True)
    @update.command(pass_context=True, name='officers')
    async def _officers(self, ctx, role: EnhancedRoleConverter = None):
        """Which role are your Alliance Officers?"""
        data = await self._update_role(ctx, key='officers', role=role)
        await self.bot.send_message(ctx.message.channel, embed=data)

    @update.command(pass_context=True, name='bg1')
    async def _bg1(self, ctx, role: EnhancedRoleConverter = None):
        """Which role is your Battlegroup 1?"""
        print("updating bg1")
        data = await self._update_role(ctx, key='bg1', role=role)
        await self.bot.send_message(ctx.message.channel, embed=data)

    @update.command(pass_context=True, name='bg1aq')
    async def _bg1aq(self, ctx, role: EnhancedRoleConverter = None):
        """Which role is your Battlegroup 1 for Alliance Quest?"""
        data = await self._update_role(ctx, key='bg1aq', role=role)
        await self.bot.send_message(ctx.message.channel, embed=data)

    @update.command(pass_context=True, name='bg1aw')
    async def _bg1aw(self, ctx, role: EnhancedRoleConverter = None):
        """Which role is your Battlegroup 1 for Alliance War?"""
        # if role.name == 'everyone':
        #     data = self._get_embed(ctx)
        #     data.title = 'Alliance Role restriction:sparkles:'
        #     data.description = 'The ``@everyone`` role is prohibited from being set as an alliance role.'
        # else:
        data = await self._update_role(ctx, key='bg1aw', role=role)
        await self.bot.send_message(ctx.message.channel, embed=data)

    @update.command(pass_context=True, name='bg2')
    async def _bg2(self, ctx, role: EnhancedRoleConverter = None):
        """Which role is your Battlegroup 2?"""
        data = await self._update_role(ctx, key='bg2', role=role)
        await self.bot.send_message(ctx.message.channel, embed=data)

    @update.command(pass_context=True, name='bg2aq')
    async def _bg2aq(self, ctx, role: EnhancedRoleConverter = None):
        """Which role is your Battlegroup 2 for Alliance Quest?"""
        data = await self._update_role(ctx, key='bg2aq', role=role)
        await self.bot.send_message(ctx.message.channel, embed=data)

    @update.command(pass_context=True, name='bg2aw')
    async def _bg2aw(self, ctx, role: EnhancedRoleConverter = None):
        """Which role is your Battlegroup 2 for Alliance War?"""
        data = await self._update_role(ctx, key='bg2aw', role=role)
        await self.bot.send_message(ctx.message.channel, embed=data)

    @update.command(pass_context=True, name='bg3')
    async def _bg3(self, ctx, role: EnhancedRoleConverter = None):
        """Which role is your Battlegroup 3?"""
        data = await self._update_role(ctx, key='bg3', role=role)
        await self.bot.send_message(ctx.message.channel, embed=data)

    @update.command(pass_context=True, name='bg3aq')
    async def _bg3aq(self, ctx, role: EnhancedRoleConverter = None):
        """Which role is your Battlegroup 3 for Alliance Quest?"""
        data = await self._update_role(ctx, key='bg3aq', role=role)
        await self.bot.send_message(ctx.message.channel, embed=data)

    @update.command(pass_context=True, name='bg3aw')
    async def _bg3aw(self, ctx, role: EnhancedRoleConverter = None):
        """Which role is your Battlegroup 3 for Alliance War?"""
        data = await self._update_role(ctx, key='bg3aw', role=role)
        await self.bot.send_message(ctx.message.channel, embed=data)

    @update.command(pass_context=True, name='alliance')
    async def _alliance(self, ctx, role: EnhancedRoleConverter = None):
        """Which role represents all members of your alliance (up to 30)?"""
        data = await self._update_role(ctx, key='alliance', role=role)
        await self.bot.send_message(ctx.message.channel, embed=data)

    @update.command(pass_context=True, name='wartool')
    async def _wartool(self, ctx, wartool_url: str = None):
        """Save your WarTool URL"""
        data = self._get_embed(ctx)
        if wartool_url is not None:
            c = await self.authorize()
            # sheet_data = await self.retrieve_data()
            sheet_id = re.findall(
                r'/spreadsheets/d/([a-zA-Z0-9-_]+)', wartool_url)
            print(sheet_id[0])
            try:
                wartool = await c.open_by_key(sheet_id[0])
                data = self._update_guilds[ctx, 'wartool', sheet_id]
                data.title = "WarTool Valid"
                # data.url=wartool_url
                data.description = "Valid WarTool URL provided."
                data.add_field(name="Wartool ID", value=sheet_id)

                # else:
                #     data.title = "Get CollectorDevTeam WarTool"
                #     data.description = "Invalid WarTool URL provided.  If you do not have a valid WarTool URL open the following Google Sheet and create a copy for your alliance.  Save the URL to your WarTool and try this command again."

            except:
                data.title = "WarTool Invalid"
                data.description = "Invalid WarTool URL provided.\nDo you need a WarTool Sheet?\n[Make a Copy now](https://docs.google.com/spreadsheets/d/111akgaclw5sb-6gsf5pVsX7EkqvxGdrpXLHdHYmLm60/copy)"
        else:
            data.title = "WarTool URL required"
            data.description = "Do you need a WarTool Sheet for your Alliance?\n[Make a Copy now](https://docs.google.com/spreadsheets/d/111akgaclw5sb-6gsf5pVsX7EkqvxGdrpXLHdHYmLm60/copy)"
        await self.bot.send_message(ctx.message.channel, embed=data)

    def _create_alliance(self, ctx, server):
        """Create alliance.
        Set basic information"""
        self.guilds[server.id] = {'type': 'basic',
                                  'name': server.name, 'assign': 'officers'}
        dataIO.save_json(self.alliances, self.guilds)
        data = discord.Embed(colour=get_color(ctx), url=PATREON)
        data.add_field(name="Congrats!:sparkles:",
                       value='{}, you have officially registered {} as a CollectorVerse Alliance.\n'
                             ':warning: The Alliance tool will not function unless an **alliance** role is designated.\n'
                             'If you do not have an **alliance** role, create one and assign it to the members of your alliance.\n'
                             'Designate that role using the command ``/alliance set alliance <role>``\n'
                             'If you have other issues, use the command ``/alliance settings`` to view and verify your settings.\n'
                             'For additional support visit the CollectorDevTeam ``/joincdt``.\n'
                             'Reminder: Patrons receive priority support.\n'
                       .format(ctx.message.author.mention, server.name))
        data.set_footer(text='CollectorDevTeam', icon_url=COLLECTOR_ICON)
        return data

    async def _update_role(self, ctx, key, role: None):
        """For a given context, key, and role, search message server for role and set role for that alliance key"""
        server = ctx.message.server
        # if role is not None:
        #     print("update: ", server.name, role.name)
        data = discord.Embed(colour=get_color(
            ctx), title='Role Registration:sparkles:')
        if role == "None":
            role = None
        if server.id not in self.guilds:
            return _unknown_guild(ctx)
        if role is not None and role.name == '@everyone':
            data = self._get_embed(ctx)
            data.title = 'Alliance Role restriction:sparkles:'
            data.description = 'The ``@everyone`` role is prohibited from ' \
                               'being set as an alliance role.'
            return data
        elif role is None:
            question = '{}, do you want to remove this ``{}`` registration?'.format(
                ctx.message.author.mention, key)
            answer, confirmation = await PagesMenu.confirm(self, ctx, question)
            if answer is True:
                self.guilds[server.id].pop(key, None)
                await self.bot.delete_message(confirmation)
                data.add_field(name="Congrats!:sparkles:",
                               value="You have unregistered ``{}`` from your Alliance.".format(key))
        else:
            data, member_names = self._get_role_members(
                ctx, server, role, key, data)
            data.add_field(name="Congrats!:sparkles:",
                           value="You have set your {} to {}".format(key, role.name), inline=False)
            if len(member_names) > 0:
                data.add_field(name='{} members'.format(
                    role.name), value='\n'.join(member_names))
            else:
                data.add_field(name='{} members'.format(
                    role.name), value='No Members assigned')
        dataIO.save_json(self.alliances, self.guilds)
        data.set_footer(text='CollectorDevTeam', icon_url=COLLECTOR_ICON)
        return data

    def _get_role_members(self, ctx, server: discord.Server, role: discord.Role, key: str, data=None):
        """package and set role members & ids"""
        if server is None or role is None or key is None:
            return data
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
            if len(member_ids) > 10 and data is not None:
                data.add_field(name=':warning: Warning - Overloaded Battlegroup:',
                               value='Battlegroups are limited to 10 members. '
                               'Check your {} assignments'.format(role.name))
        elif key == 'alliance':
            if len(member_ids) > 30 and data is not None:
                data.add_field(name=':warning: Warning - Overloaded Alliance',
                               value='Alliances are limited to 30 members. '
                               'Check your {} members'.format(role.name))
        self.guilds[server.id].update({key: package})
        return data, member_names

    def _update_members(self, ctx, server):
        if server is None:
            return
        for key in self.advanced_keys:
            if key in self.guilds[server.id]:
                role = self._get_role(server, key)
                if role is not None:
                    self._get_role_members(ctx, server, role, key)
                    # member_names = []
                    # member_ids = []
                    # for m in server.members:
                    #     if role in m.roles:
                    #         member_names.append(m.name)
                    #         member_ids.append(m.id)
                    # package = {'id': role.id,
                    #            'name': role.name,
                    #            'member_ids': member_ids,
                    #            'member_names': member_names}
                    # self.guilds[server.id].update({key: package})
                    continue
                elif role is None:
                    self.guilds[server.id].pop(key, None)
        dataIO.save_json(self.alliances, self.guilds)
        print('Debug: Alliance details refreshed')
        return

    def _update_guilds(self, ctx, key, value):
        server = ctx.message.server
        data = discord.Embed(colour=get_color(ctx))
        if value in ('""', "''", " ", "None", "none", "-",):
            self.guilds[server.id].pop(key, None)
            data.add_field(name="Congrats!:sparkles:",
                           value="You have deleted {} from your Alliance.".format(key))
        else:
            self.guilds[server.id].update({key: value})
            data.add_field(name="Congrats!:sparkles:",
                           value="You have set your {} to {}".format(key, value))
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
    #         await self.bot.send_message(ctx.message.channel, embed=data)
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
    #     await self.bot.send_message(ctx.message.channel, embed=data)

    async def diagnostics(self, message):
        """Messages accepts string, embed, or list of strings or embeds"""
        if isinstance(message, list) == False:
            messages = [message]
        else:
            messages = message
        for m in messages:
            channel = self.bot.get_channel(self.diagnostics_channel)
            if isinstance(m, discord.Embed):
                await self.bot.send_message(channel, embed=m)
            elif m is not None:
                await self.bot.send_message(channel, m)
        return

    async def authorize(self):
        """pygsheets authorizes client based on credentials file"""
        try:
            return pygsheets.authorize(service_file=self.service_file, no_cache=True)
        except FileNotFoundError:
            err_msg = 'Cannot find credentials file.  Needs to be located:\n' \
                      + self.service_file
            await self.bot.send_message(ctx.message.channel, err_msg)
            raise FileNotFoundError(err_msg)


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


def _get_members(server: discord.Server, role: discord.Role):
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
