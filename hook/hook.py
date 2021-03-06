import discord
from datetime import datetime, timedelta
from discord.ext import commands
from cogs.mcoc import (ChampConverter, ChampConverterMult,
                       QuietUserError, override_error_handler)
from .utils.dataIO import dataIO
from .utils.dataIO import fileIO
from .utils import checks
from .utils import chat_formatting as chat
from functools import partial
from operator import itemgetter, attrgetter
from collections import OrderedDict, namedtuple
from random import randint
from math import ceil
import shutil
import time
import types
import logging
import os
import ast
import csv
import aiohttp
import re
import asyncio
# Monkey Patch of JSONEncoder
from json import JSONEncoder, dump, dumps
from .cdtpagesmenu import PagesMenu
from .cdtembed import CDTEmbed
from cogs.mcocTools import (StaticGameData, KABAM_ICON, COLLECTOR_ICON, COLLECTOR_FEATURED, CDTHelperFunctions,
                            GSHandler, GSExport, CDT_COLORS)


logger = logging.getLogger('red.roster')
logger.setLevel(logging.INFO)


def _default(self, obj):
    return getattr(obj.__class__, "to_json", _default.default)(obj)


PRESTIGE_SURVEY = 'https://docs.google.com/forms/d/e/1FAIpQLSeo3YhZ70PQ4t_I4i14jX292CfBM8DMb5Kn2API7O8NAsVpRw/viewform?usp=sf_link'
GITHUB_ICON = 'http://www.smallbutdigital.com/static/media/twitter.png'
HOOK_URL = 'http://hook.github.io/champions/#/roster'
COLLECTOR_ICON = 'https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/images/portraits/collector.png'
GSHEET_ICON = 'https://d2jixqqjqj5d23.cloudfront.net/assets/developer/imgs/icons/google-spreadsheet-icon.png'
PATREON = 'https://patreon.com/collectorbot'
AUNTMAI = 'https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/images/AuntMai_Tile_Center.png'


_default.default = JSONEncoder().default  # Save unmodified default.
JSONEncoder.default = _default  # replacemente
# Done with patch
# class CustomEncoder(JSONEncoder):
#    def default(self, obj):
#        return getattr(obj.__class__, "to_json", JSONEncoder.default)(obj)


class MissingRosterError(QuietUserError):
    pass


class MisorderedArgumentError(QuietUserError):
    pass


class HashtagRosterConverter(commands.Converter):
    async def convert(self):
        tags = set()
        user = None
        for arg in self.argument.split():
            if arg.startswith('#'):
                tags.add(arg.lower())
            elif user is None:
                user = commands.UserConverter(self.ctx, arg).convert()
            else:
                err_msg = "There can only be 1 user argument.  All others should be '#'"
                await self.ctx.bot.say(err_msg)
                raise commands.BadArgument(err_msg)
        if user is None:
            user = self.ctx.message.author
        chmp_rstr = ChampionRoster(self.ctx.bot, user)
        await chmp_rstr.load_champions()
        if not chmp_rstr:
            menu = PagesMenu(self.ctx.bot, timeout=120,
                             delete_onX=True, add_pageof=True)
            #hook = Hook(self.ctx.bot)
            try:
                color = user.color
            except:
                color = discord.Color.gold()
            embeds = await Hook.roster_kickback(color)
            await menu.menu_start(pages=embeds)

            raise MissingRosterError(
                'No Roster found for {}'.format(user.name))
        return types.SimpleNamespace(tags=tags, roster=chmp_rstr)


class HashtagRankConverter(commands.Converter):
    parse_re = ChampConverter.parse_re

    async def convert(self):
        tags = set()
        attrs = {}
        arguments = self.argument.split()
        start_hashtags = 0
        for i, arg in enumerate(arguments):
            if arg[0] in '#(~':
                start_hashtags = i
                break
            for m in self.parse_re.finditer(arg):
                attrs[m.lastgroup] = int(m.group(m.lastgroup))
        else:
            start_hashtags = len(arguments)
        for arg in arguments[start_hashtags:]:
            if arg[0] not in '#(~':
                await self.ctx.bot.say('All arguments must be before the Hashtags')
                raise MisorderedArgumentError(arg)
            if arg.startswith('#'):
                tags.add(arg.lower())
        return types.SimpleNamespace(tags=tags, attrs=attrs)


class RosterUserConverter(commands.Converter):
    async def convert(self):
        user = None
        if self.argument:
            user = commands.UserConverter(self.ctx, self.argument).convert()
        else:
            user = self.ctx.message.author
        chmp_rstr = ChampionRoster(self.ctx.bot, user)
        await chmp_rstr.load_champions()
        return chmp_rstr


class RosterConverter(commands.Converter):
    async def convert(self):
        chmp_rstr = ChampionRoster(self.ctx.bot, self.ctx.message.author)
        await chmp_rstr.load_champions()
        return chmp_rstr


class ChampionRoster:

    _data_dir = 'data/hook/users/{}/'
    _champs_file = _data_dir + 'champs.json'
    #champ_str = '{0.star}{0.star_char} {0.full_name} r{0.rank} s{0.sig:<2} [ {0.prestige} ]'
    attr_map = {'Rank': 'rank', 'Awakened': 'sig',
                'Stars': 'star', 'Role': 'quest_role'}
    alliance_map = {'alliance-war-defense': 'awd',
                    'alliance-war-attack': 'awo',
                    'alliance-quest': 'aq'}
    update_str = '{0.star_name_str} {1} -> {0.rank_sig_str} [ {0.prestige} ]'

    def __init__(self, bot, user, attrs=None, is_filtered=False, hargs=None):
        self.bot = bot
        self.user = user
        self.roster = {}
        self.is_filtered = is_filtered
        self.hargs = hargs
        self.previous_hargs = None
        self._create_user()
        self._cache = {}
        # self.load_champions()
        if self.is_bot and not is_filtered:
            self.autofill_bot_user(attrs)

    def __len__(self):
        return len(self.roster)

    def __contains__(self, item):
        if hasattr(item, 'immutable_id'):
            return item.immutable_id in self.roster
        return item in self.roster

    def _normalize_ids(self, other):
        if isinstance(other, ChampionRoster):
            return self.ids_set(), other.ids_set()
        elif isinstance(other, set):
            return self.ids_set(), other
        else:
            raise TypeError(
                "Roster operations can't handle type {}".format(type(other)))

    def __sub__(self, other):
        s_ids, o_ids = self._normalize_ids(other)
        return self.filtered_roster_from_ids(s_ids - o_ids)

    @property
    def is_bot(self):
        return self.user == self.bot.user

    def ids_set(self):
        return set(self.roster.keys())

    def autofill_bot_user(self, attrs):
        attrs = attrs if attrs is not None else {}
        mcoc = self.bot.get_cog('MCOC')
        rlist = []
        for champ_class in mcoc.champions.values():
            champ = champ_class(attrs.copy())
            if champ.has_prestige:
                rlist.append(champ)
        self.from_list(rlist)
        #self.display_override = 'Prestige Listing: {0.attrs_str}'.format(rlist[0])

    # handles user creation, adding new server, blocking

    def _create_user(self):
        if not os.path.exists(self.champs_file):
            if not os.path.exists(self.data_dir):
                os.makedirs(self.data_dir)
            champ_data = {
                # "clan": None,
                # "battlegroup": None,
                "fieldnames": ["Id", "Stars", "Rank", "Level", "Awakened", "Pi", "Role"],
                "roster": [],
                "prestige": 0,
                "top5": [],
                "aq": [],
                "awd": [],
                "awo": [],
                "max5": [],
            }
            dataIO.save_json(self.champs_file, champ_data)
            # self.save_champ_data(champ_data)

    # handles user deletion
    # def _delete_user(self):

    async def load_champions(self, silent=False):
        data = self.load_champ_data()
        self.roster = {}
        name = 'roster' if 'roster' in data else 'champs'
        for k in data[name]:
            champ = await self.get_champion(k)
            self.roster[champ.immutable_id] = champ
        if len(self.roster) == 0 and not silent:
            await self.warn_missing_roster()

    def from_list(self, champ_list):
        self.roster = {champ.immutable_id: champ for champ in champ_list}

    def load_champ_data(self):
        data = dataIO.load_json(self.champs_file)
        self.fieldnames = data['fieldnames']
        return data

    def save_champ_data(self):
        #print(dumps(self, cls=CustomEncoder))
        # with open(self.champs_file.format(self.user.id), 'w') as fp:
        #dump(self, fp, indent=2, cls=CustomEncoder)
        dataIO.save_json(self.champs_file, self)

    def to_json(self):
        translate = ['fieldnames', 'prestige', 'max_prestige', 'top5',
                     'max5']
        pack = {i: getattr(self, i) for i in translate}
        pack['roster'] = list(self.roster.values())
        return pack
        # return {i: getattr(self, i) for i in translate}

    @property
    def data_dir(self):
        return self._data_dir.format(self.user.id)

    @property
    def champs_file(self):
        return self._champs_file.format(self.user.id)

    @property
    def embed_display(self):
        if self.user is self.bot.user:
            # should be safe to just grab the first one since bot rosters are uniform
            champ = list(self.roster.values())[0]
            return 'Listing ({} champs): {}'.format(len(self), champ.attrs_str)
        else:
            return 'Filtered Prestige ({} champs):  {:.2f}'.format(len(self), self.prestige)

    async def get_champion(self, cdict):
        mcoc = self.bot.get_cog('MCOC')
        champ_attr = {v: cdict[k] for k, v in self.attr_map.items()}
        return await mcoc.get_champion(cdict['Id'], champ_attr)

    async def filter_champs(self, tags):
        if tags is None:
            return self
        residual_tags = tags - self.all_tags
        if residual_tags:
            em = discord.Embed(title='Unused tags',
                               description=' '.join(residual_tags))
            await self.bot.say(embed=em)
        filtered = self.raw_filtered_ids(tags)
        return self.filtered_roster_from_ids(filtered)

    def raw_filtered_ids(self, tags):
        filtered = set()
        for c in self.roster.values():
            if tags.issubset(c.all_tags):
                filtered.add(c.immutable_id)
        self.previous_hargs = tags
        return filtered

    def filtered_roster_from_ids(self, filtered, hargs=None):
        hargs = hargs if hargs else self.previous_hargs
        filt_roster = ChampionRoster(self.bot, self.user, is_filtered=True,
                                     hargs=hargs)
        filt_roster.roster = {iid: self.roster[iid] for iid in filtered}
        return filt_roster

    @property
    def all_tags(self):
        if not self.roster:
            return set()
        return set.union(*[c.all_tags for c in self.roster.values()])

    @property
    def prestige(self):
        return self._get_five('prestige')[0]

    @property
    def top5(self):
        return self._get_five('prestige')[1]

    @property
    def max_prestige(self):
        return self._get_five('max_prestige')[0]

    @property
    def max5(self):
        return self._get_five('max_prestige')[1]

    def _get_five(self, key):
        if self._cache.get(key, None) is None:
            champs = sorted(self.roster.values(), key=attrgetter(key),
                            reverse=True)
            if len(champs) > 0 and len(champs) <= 5:
                denom = len(champs)
            else:
                denom = 5
            prestige = sum([getattr(champ, key) for champ in champs[:5]])/denom
            champs_str = [champ.verbose_prestige_str for champ in champs[:5]]
            self._cache[key] = (prestige, champs_str)
        return self._cache[key]

    async def parse_champions_csv(self, channel, attachment):
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment['url']) as response:
                file_txt = await response.text()
        #dialect = csv.Sniffer().sniff(file_txt[:1024])
        cr = csv.DictReader(file_txt.split('\n'),  # dialect,
                            quoting=csv.QUOTE_NONE)
        missing = []
        dupes = []
        for row in cr:
            champ_csv = {k: parse_value(v) for k, v in row.items()}
            try:
                champ = await self.get_champion(champ_csv)
            except KeyError:
                if champ_csv['Id'].strip():
                    # non-empty champion ID
                    missing.append(champ_csv['Id'])
                continue
            if champ.immutable_id in self.roster:
                dupes.append(champ)
            self.roster[champ.immutable_id] = champ

        if missing:
            await self.bot.send_message(channel, 'Missing hookid for champs: '
                                        + ', '.join(missing))
        if dupes:
            await self.bot.send_message(channel,
                                        'WARNING: Multiple instances of champs in file.  '
                                        + 'Overloading:\n\t'.format(
                                            ', '.join([c.star_name_str for c in dupes])))

        em = discord.Embed(title="Updated Champions")
        em.add_field(name='Prestige', value=self.prestige)
        em.add_field(name='Max Prestige', value=self.max_prestige, inline=True)
        em.add_field(name='Top Champs', value='\n'.join(
            self.top5), inline=False)
        em.add_field(name='Max PI Champs',
                     value='\n'.join(self.max5), inline=True)

        self.fieldnames = cr.fieldnames

        #champ_data.update({v: [] for v in self.alliance_map.values()})
        # for champ in champ_data['champs']:
        #    if champ['Role'] in self.alliance_map:
        #        champ_data[self.alliance_map[champ['Role']]].append(champ['Id'])

        self.save_champ_data()
        # if mcoc:
        await self.bot.send_message(channel, embed=em)
        # else:
        #    await self.bot.send_message(channel, 'Updated Champion Information')

    def set_defaults_of(self, champs):
        for champ in champs:
            iid = champ.immutable_id
            if iid not in self.roster:
                champ.update_default({'rank': 1, 'sig': 0})
            else:
                champ.update_default({'rank': self.roster[iid].rank,
                                      'sig': self.roster[iid].sig})

    def update(self, champs, skip_save=False):
        self.set_defaults_of(champs)
        track = {'new': set(), 'modified': set(), 'unchanged': set()}
        self._cache = {}
        for champ in champs:
            iid = champ.immutable_id
            if iid not in self.roster:
                track['new'].add(champ.verbose_prestige_str)
            else:
                if champ == self.roster[iid]:
                    track['unchanged'].add(champ.verbose_prestige_str)
                else:
                    track['modified'].add(self.update_str.format(champ,
                                                                 self.roster[iid].rank_sig_str))
            self.roster[iid] = champ
        if not skip_save:
            self.save_champ_data()
        return track

    def inc_dupe(self, champs):
        self.set_defaults_of(champs)
        track = {'modified': set(), 'missing': set()}
        self._cache = {}
        for champ in champs:
            iid = champ.immutable_id
            if iid in self.roster:
                old_str = self.roster[iid].rank_sig_str
                self.roster[iid].inc_dupe()
                track['modified'].add(
                    self.update_str.format(self.roster[iid], old_str))
            else:
                track['missing'].add(champ.star_name_str)
        self.save_champ_data()
        return track

    def delete(self, champs):
        track = {'deleted': set(), 'non-existant': set()}
        self._cache = {}
        for champ in champs:
            iid = champ.immutable_id
            if iid not in self.roster:
                track['non-existant'].add(champ.star_name_str)
            else:
                track['deleted'].add(champ.star_name_str)
                self.roster.pop(iid)
        self.save_champ_data()
        return track

    async def warn_missing_roster(self):
        menu = PagesMenu(self.bot, timeout=120,
                         delete_onX=True, add_pageof=True)
        try:
            color = self.user.color
        except:
            color = discord.Color.gold()
        embeds = await Hook.roster_kickback(color)
        await menu.menu_start(pages=embeds)
        raise MissingRosterError(
            'No Roster found for {}'.format(self.user.name))

    async def warn_empty_roster(self, tags=None):
        tags = tags if tags else self.hargs
        if tags is None:
            tags = ''
        elif not isinstance(tags, str):
            tags = ' '.join(tags)
        em = discord.Embed(title='User', description=self.user.name,
                           color=discord.Color.gold(), url=PRESTIGE_SURVEY)
        em.add_field(name='Tags used filtered to an empty roster',
                     value=tags)
        await self.bot.say(embed=em)

    async def display_prestige(self, tags=None):
        em = discord.Embed(title=self.user.display_name+':sparkles:',
                           description=self.embed_display,
                           color=discord.Color.gold(), url=PATREON)
        await self.bot.say(embed=em)

    async def display_prestige_delta(self, orig_prestige, tags=None):
        outstr = 'Potential Prestige: {:.0f} -> {:.0f} ({:+.0f} delta)'.format(
            orig_prestige, self.prestige, self.prestige - orig_prestige)
        em = discord.Embed(title=self.user.display_name+':no_entry:',
                           description=outstr,
                           color=discord.Color.gold(), url=PATREON)
        await self.bot.say(embed=em)

    async def display(self, tags=None):
        if tags is not None:
            filt_roster = await self.filter_champs(tags)
            return await filt_roster.display()

        filtered = list(self.roster.values())
        user = self.user
        embeds = []
        if not filtered:
            await self.warn_empty_roster()
            return

        strs = [champ.verbose_prestige_str for champ in sorted(filtered, reverse=True,
                                                               key=attrgetter('prestige', 'chlgr_rating', 'star', 'klass', 'full_name'))]
        champs_per_page = 15
        for i in range(0, len(strs)+1, champs_per_page):
            em = discord.Embed(title=user.display_name+':sparkles:',
                               color=discord.Color.gold(), url=PATREON)
            # em.set_thumbnail(user.avatar_url)
            em.set_author(name='CollectorDevTeam', icon_url=COLLECTOR_ICON)
            em.set_footer(text='https://auntm.ai | CollectorVerse',
                          icon_url=AUNTMAI)
            page = strs[i:min(i+champs_per_page, len(strs))]
            if not page:
                break
            em.add_field(name=self.embed_display, inline=False,
                         value='\n'.join(page))
            embeds.append(em)

        if len(embeds) == 1:
            await self.bot.say(embed=embeds[0])
        else:
            menu = PagesMenu(self.bot, timeout=120,
                             delete_onX=True, add_pageof=True)
            await menu.menu_start(pages=embeds)


class Hook:

    def __init__(self, bot):
        self.bot = bot
        self.champ_re = re.compile(r'.*hamp.*\.csv')
        self.gsheet_handler = GSHandler(bot)
        self.collection = None
        self.gsheet_handler.register_gsheet(
            name='collection',
            gkey='1JSiGo-oGbPdmlegmGTH7hcurd_HYtkpTnZGY1mN_XCE',
            local='data/mcoc/collection.json',
            sheet_name='collection',
            range_name='available_collection'
        )
        # self.champ_re = re.compile(r'champ.*\.csv')
        #self.champ_re = re.compile(r'champions(?:_\d+)?.csv')
        #self.champ_str = '{0[Stars]}★ R{0[Rank]} S{0[Awakened]:<2} {0[Id]}'

    @staticmethod
    async def roster_kickback(ucolor=discord.Color.gold()):
        embeds = []
        em0 = discord.Embed(color=ucolor, title='No Roster detected!',
                            description='There are several methods available to you to create your roster.'
                            '\nPlease note the paging buttons below to select your instruction set.')
        em0.set_footer(text='CollectorVerse Roster', icon_url=COLLECTOR_ICON)
        embeds.append(em0)
        em01 = discord.Embed(color=ucolor, title='Manual Entry',
                             description='Use the ```/roster add <champs>``` command to submit Champions directly to Collector.\nThis is the most common method to add to your roster, and the method you will use to maintain your roster.\n```/roster del <champs>``` allows you to remove a Champion.\n\nYouTube demo: https://youtu.be/O9Wqn1l2DEg', url='https://youtu.be/O9Wqn1l2DEg')
        em01.set_footer(text='CollectorVerse Roster', icon_url=COLLECTOR_ICON)
        embeds.append(em01)
        em = discord.Embed(
            color=ucolor, title='Champion CSV template', url='https://goo.gl/LaFrg7')
        em.add_field(name='Google Sheet Instructions',
                     value='Save a copy of the template (blue text):\n1. Add 5★ champions you do have.\n2. Delete 4★ champion rows you do not have.\n3. Set Rank = champion rank (1 to 5).\n4. Set Awakened = signature ability level.\n``[4★: 0 to 99 | 5★: 0 to 200]``\n5. Export file as \'champions.csv\'.\n6. Upload to Collector.\n7. Select OK to confirm')
        em.add_field(name='Prerequisite',
                     value='Google Sheets\n(there is an app for iOS|Android)', inline=False)
        em.set_footer(text='CSV import', icon_url=GSHEET_ICON)
        embeds.append(em)
        em2 = discord.Embed(
            color=ucolor, title='Import from Hook', url=HOOK_URL)
        em2.add_field(name='Hook instructions', value='1. Go to Hook/Champions webapp (blue text)\n2. Add Champions.\n3. Set Rank & Signature Ability level\n4. From the Menu > Export CSV as \'champions.csv\'\n5. Upload to Collector.\n6. Select OK to confirm')
        em2.set_footer(text='https://auntm.ai | CollectorVerse',
                       icon_url=AUNTMAI)
        embeds.append(em2)
        em3 = discord.Embed(
            color=ucolor, title='Import from Hook', url=HOOK_URL)
        em3.add_field(name='iOS + Hook instructions', value='1. Go to Hook/Champions webapp (blue text)\n2. Add Champions.\n3. Set Rank & Signature Ability level\n4. From the Menu > Export CSV > Copy Text from Safari\n5. In Google Sheets App > paste\n6. Download as \'champions.csv\'\n5. Upload to Collector.\n6. Select OK to confirm')
        em3.add_field(name='Prerequisite',
                      value='Google Sheets\n(there is an app for iOS|Android)', inline=False)
        em2.set_footer(text='https://auntm.ai | CollectorVerse',
                       icon_url=AUNTMAI)
        embeds.append(em3)
        return embeds

    @commands.command(pass_context=True, aliases=('th',))
    async def test_hash(self, ctx, *, hargs=''):
        # hargs = await hook.HashtagRankConverter(ctx, hargs).convert() #imported from hook
        #roster = partial(ChampionRoster, self.bot, self.bot.user)
        sgd = StaticGameData()
        aliases = {'#var2': '(#5star | #6star) & #size:xl',
                   '#poisoni': '#poisonimmunity'}
        # await sgd.filter_and_display(hargs, roster, aliases=aliases)
        roster = await sgd.parse_with_attr(ctx, hargs, ChampionRoster, aliases=aliases)
        if roster is not None:
            await roster.display()

    @commands.command(pass_context=True, aliases=('list_members', 'role_roster', 'list_users'))
    async def users_by_role(self, ctx, role: discord.Role, use_alias=True):
        '''Embed a list of server users by Role'''
        server = ctx.message.server
        user = ctx.message.author
        members = []
        for member in server.members:
            if role in member.roles:
                members.append(member)
        # members.sort(key=attrgetter('name'))
        if use_alias:
            ret = '\n'.join([m.display_name for m in members])
        else:
            ret = '\n'.join([m.name for m in members])
        if len(ret) > 0:
            # rets = chat.pagify(ret)
            pagified = chat.pagify(text=ret, page_length=1700)
            pages = []
            for page in pagified:
                em = discord.Embed(title='{0.name} Role - {1} member(s)'.format(role, len(members)),
                                   description=page, color=role.color)
                em.set_footer(text="Requested by {}".format(
                    user.display_name), icon_url=user.avatar_url)
                pages.append(em)
            menu = PagesMenu(self.bot, timeout=120,
                             delete_onX=True, add_pageof=True)
            await menu.menu_start(pages=pages)

        # await self.bot.say(embed=em)

    # @commands.command(pass_context=True, no_pm=True)
    # async def team(self,ctx, *, user : discord.Member=None):
    #     """Displays a user's AQ/AWO/AWD teams.
    #     Teams are set in hook/champions"""
    #     if user is None:
    #         user = ctx.message.author
    #     # creates user if doesn't exist
    #     info = self.load_champ_data(user)
    #     em = discord.Embed(title="User Profile", description=user.name)
    #     if info['aq']:
    #         em.add_field(name='AQ Champs', value='\n'.join(info['aq']))
    #     if info['awo']:
    #         em.add_field(name='AWO Champs', value='\n'.join(info['awo']))
    #     if info['awd']:
    #         em.add_field(name='AWD Champs', value='\n'.join(info['awd']))
    #     await self.bot.say(embed=em)

    @commands.group(pass_context=True, invoke_without_command=True)
    async def roster(self, ctx, *, hargs=''):
        # async def roster(self, ctx, *, hargs: HashtagRosterConverter):
        """Displays a user roster with tag filtering

        example:
        /roster [user] [#mutant #bleed]"""
        sgd = StaticGameData()
        aliases = {'#var2': '(#5star | #6star) & #size:xl',
                   '#poisoni': '#poisonimmunity'}
        # await sgd.filter_and_display(hargs, roster, aliases=aliases)
        roster = await sgd.parse_with_user(ctx, hargs, ChampionRoster, aliases=aliases)
        if roster is not None:
            await roster.display()
        # hargs = await HashtagRosterConverter(ctx, hargs).convert()
        # await hargs.roster.display(hargs.tags)

    @roster.command(pass_context=True, name='add', aliases=('update',))
    async def _roster_update(self, ctx, *, champs: ChampConverterMult):
        '''Add or Update champion(s).

        Add or Update your roster using the standard command line syntax.
        Defaults for champions you specify are the current values in your roster.
        If it is a new champ, defaults are 4*, rank 1, sig 0.

        This means that
        /roster update some_champs20
        would just set some_champ's sig to 20 but keep it's rank the same.

        example:
        /roster add angelar4s20 karnakr5s80 medusar4s20
        '''
        roster = ChampionRoster(ctx.bot, ctx.message.author)
        await roster.load_champions(silent=True)
        await self._update(roster, champs)

    @roster.command(pass_context=True, name='try', aliases=('scratch', 'sandbox'))
    async def _roster_try(self, ctx, *, champs: ChampConverterMult):
        '''Try updating a champ without saving the results.  Typically used
        to experiment with prestige.'''
        roster = ChampionRoster(ctx.bot, ctx.message.author)
        await roster.load_champions(silent=True)
        await self._update(roster, champs, skip_save=True)

    @roster.command(pass_context=True, name='missing')
    async def _roster_missing(self, ctx, *, hargs=''):
        '''Show champions missing from user's roster (one star only)

        This uses the same syntax as `/champ list` and shows all of the missing
        champs from the star level specified <default: 4*>.  Hashtags are
        also accepted

        example:
        /roster missing              (missing 4* champs)
        /roster missing 5* #science  (missing 5* science champs)
        '''
        sgd = StaticGameData()
        aliases = {'#var2': '(#5star | #6star) & #size:xl',
                   '#poisoni': '#poisonimmunity'}
        bot_roster = await sgd.parse_with_attr(ctx, hargs, ChampionRoster, aliases=aliases)
        roster = ChampionRoster(ctx.bot, ctx.message.author)
        await roster.load_champions(silent=True)
        missing = bot_roster - roster
        await missing.display()

    @roster.command(pass_context=True, name='stats', hidden=True)
    async def _roster_stats(self, ctx, user: discord.User = None):
        # sgd = StaticGameData()

        now = datetime.now().date()
        if os.path.exists('data/mcoc/collection.json'):
            # filetime = datetime.datetime.fromtimestamp(os.path.getctime('data/mcoc/tldr.json'))
            filetime = datetime.fromtimestamp(
                os.path.getctime('data/mcoc/collection.json'))
            if filetime.date() != now:
                await self.gsheet_handler.cache_gsheets('collection')
                self.collection = dataIO.load_json('data/mcoc/collection.json')
        else:
            await self.gsheet_handler.cache_gsheets('collection')
            self.collection = dataIO.load_json('data/mcoc/collection.json')
        if self.collection is None:
            self.collection = dataIO.load_json('data/mcoc/collection.json')
        collection = self.collection
        if user is None:
            user = ctx.message.author
        if ctx.message.channel.is_private:
            ucolor = discord.Color.gold()
        else:
            ucolor = user.color
        roster = ChampionRoster(self.bot, user)
        await roster.load_champions()
        total = 0
        total_power = 0
        pages = []

        stats = {'top': {6: {'count': 0, 'sum': 0},
                         5: {'count': 0, 'sum': 0},
                         4: {'count': 0, 'sum': 0},
                         3: {'count': 0, 'sum': 0},
                         2: {'count': 0, 'sum': 0},
                         1: {'count': 0, 'sum': 0}},
                 'Science': {6: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}},
                             5: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}},
                             4: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}},
                             3: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0, 4: 0}},
                             2: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0}},
                             1: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0}}},
                 'Mystic': {6: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}},
                            5: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}},
                            4: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}},
                            3: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0, 4: 0}},
                            2: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0}},
                            1: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0}}},
                 'Cosmic': {6: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}},
                            5: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}},
                            4: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}},
                            3: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0, 4: 0}},
                            2: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0}},
                            1: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0}}},
                 'Tech': {6: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}},
                          5: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}},
                          4: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}},
                          3: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0, 4: 0}},
                          2: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0}},
                          1: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0}}},
                 'Mutant': {6: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}},
                            5: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}},
                            4: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}},
                            3: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0, 4: 0}},
                            2: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0}},
                            1: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0}}},
                 'Skill': {6: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}},
                           5: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}},
                           4: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}},
                           3: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0, 4: 0}},
                           2: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0, 3: 0}},
                           1: {'count': 0, 'sum': 0, 'ranks': {1: 0, 2: 0}}}}

        for champ in roster.roster.values():
            # champ = ChampConverter()
            klass = champ.klass
            star = champ.star
            total += 1
            total_power += champ.prestige
            stats[klass][star]['count'] += 1
            stats[klass][star]['sum'] += champ.prestige
            stats['top'][star]['count'] += 1
            stats['top'][star]['sum'] += champ.prestige
            stats[klass][star]['ranks'][champ.rank] += 1
            # export master count list from XREF
        data = discord.Embed(
            color=ucolor, title='CollectorVerse Roster Stats', url=PATREON)
        data.set_author(name='CollectorDevTeam', icon_url=COLLECTOR_ICON)
        data.set_thumbnail(url=user.avatar_url)
        data.set_footer(text='{} Roster Stats'.format(user.display_name))
        available = collection['Total']['Total']
        data.description = 'Champion Count: {} / {} \nCollected: % {}\nTotal Power: {:,} \n'\
            .format(total, available, round(total/available*100, 2), total_power)
        for star in (6, 5, 4, 3, 2, 1):
            count = stats['top'][star]['count']
            available = collection['Total'][str(star)]
            collected = round(count / available * 100, 2)
            data.add_field(name='\n{}★ Champion Count: {} / {}'.format(star, count, available),
                           value='Collected: % {} \nBasic Hero Rating: {:,}'
                           .format(collected, stats['top'][star]['sum']))
        pages.append(data)
        for star in (6, 5, 4, 3, 2, 1):
            data = discord.Embed(
                color=CDT_COLORS[star], title='CollectorVerse {}★ Roster Stats'.format(star), url=PATREON)
            data.set_author(name='CollectorDevTeam', icon_url=COLLECTOR_ICON)
            data.set_thumbnail(url=user.avatar_url)
            data.set_footer(text='{} Roster Stats'.format(user.display_name))
            for klass in ('Cosmic', 'Tech', 'Mutant', 'Skill', 'Science', 'Mystic'):
                list = []
                if stats[klass][star]['count'] > 0:
                    count = stats[klass][star]['count']
                    power = stats[klass][star]['sum']
                    available = collection[klass][str(star)]
                    collected = round(count/available*100, 2)
                    list.append('Collected:  % {} \nBasic Hero Rating: {:,}'
                                .format(collected, power))
                    ranks = min(star+1, 5)+1
                    for r in range(1, ranks):
                        if stats[klass][star]['ranks'][r] > 0:
                            list.append('{}★ Rank {} x {}'.format(
                                star, r, stats[klass][star]['ranks'][r]))
                    if len(list) > 0:
                        data.add_field(name='{}★ {} : {} / {}'.format(star,
                                                                      klass, count, available), value='\n'.join(list))
            if stats['top'][star]['count'] > 0:
                pages.append(data)
        menu = PagesMenu(self.bot, timeout=120,
                         delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=pages)

    async def _update(self, roster, champs, skip_save=False):
        orig_prestige = roster.prestige
        track = roster.update(champs, skip_save=skip_save)
        if skip_save:
            await roster.display_prestige_delta(orig_prestige)
        else:
            await self._display_tracked_changes(track, skip_save)

    async def _display_tracked_changes(self, track, skip_save):
        tracked = ''
        for k in ('new', 'modified', 'unchanged'):
            tracked += '{} Champions : {}\n'.format(
                k.capitalize(), len(track[k]))
        for k in ('new', 'modified', 'unchanged'):
            tracked += '\n{} Champions\n'.format(k.capitalize())
            tracked += '\n'.join(sorted(track[k]))
        total = len(track['new'])+len(track['modified'])
        pagified = chat.pagify(text=tracked, page_length=1700)
        pages = []
        emoji = ':sparkles:' if not skip_save else ':no_entry: (NO SAVE)'
        title = '{} Roster Updates {}'.format(total, emoji)

        for page in pagified:
            data = discord.Embed(title=title,
                                 color=discord.Color.gold(),
                                 description=page, url=PATREON)
            data.set_author(name='CollectorDevTeam Roster Update',
                            icon_url=COLLECTOR_ICON)
            data.set_footer(text='``/roster update <champions>``',
                            icon_url=COLLECTOR_ICON)
            data.set_thumbnail(url=COLLECTOR_FEATURED)
            pages.append(data)
        menu = PagesMenu(self.bot, timeout=240,
                         delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=pages)

    @roster.command(pass_context=True, name='dupe')
    async def _roster_dupe(self, ctx, *, champs: ChampConverterMult):
        '''Increase sig level by dupe.

        Update your roster by incrementing your champs by the duped sig level, i.e. 20 for a 4*.
        example:
        /roster dupe karnak
        '''
        roster = ChampionRoster(ctx.bot, ctx.message.author)
        await roster.load_champions()
        track = roster.inc_dupe(champs)
        em = discord.Embed(title='Champion Dupe Update for {}'.format(roster.user.name),
                           color=discord.Color.gold())
        for k in ('modified', 'missing'):
            if track[k]:
                em.add_field(name='{} Champions'.format(k.capitalize()),
                             value='\n'.join(sorted(track[k])), inline=False)
        await self.bot.say(embed=em)

    @roster.command(pass_context=True, name='delete', aliases=('del', 'remove',))
    async def _roster_del(self, ctx, *, champs: ChampConverterMult):
        '''Delete champion(s)

        Delete champion(s) from your roster.
        example:
        /roster delete angela blackbolt medusa'''
        roster = ChampionRoster(ctx.bot, ctx.message.author)
        await roster.load_champions()
        track = roster.delete(champs)
        em = discord.Embed(title='Champion Deletion for {}'.format(roster.user.name),
                           color=discord.Color.gold())
        for k in ('deleted', 'non-existant'):
            if track[k]:
                em.add_field(name='{} Champions'.format(k.capitalize()),
                             value='\n'.join(sorted(track[k])), inline=False)
        await self.bot.say(embed=em)

    @roster.command(pass_context=True, name='import', hidden=True)
    async def _roster_import(self, ctx):
        '''Silent import file attachement'''
        if not ctx.message.attachments:
            await self.bot.say('This command can only be used when uploading files')
            return
        for atch in ctx.message.attachments:
            if atch['filename'].endswith('.csv'):
                roster = ChampionRoster(self.bot, ctx.message.author)
                await roster.parse_champions_csv(ctx.message.channel, atch)
            else:
                await self.bot.say("Cannot import '{}'.".format(atch)
                                   + "  File must end in .csv and come from a Hook export")

    @roster.command(pass_context=True, name='export')
    async def _roster_export(self, ctx):
        '''Export roster as champions.csv
        Exported file can be imported to hook/champions
        '''
        roster = ChampionRoster(ctx.bot, ctx.message.author)
        await roster.load_champions(silent=True)
        rand = randint(1000, 9999)
        path, ext = os.path.split(roster.champs_file)
        tmp_file = '{}-{}.tmp'.format(path, rand)
        # with open(tmp_file, 'w') as fp:
        with open(tmp_file, 'w', encoding='utf-8') as fp:
            writer = csv.DictWriter(fp, fieldnames=roster.fieldnames,
                                    extrasaction='ignore', lineterminator='\n')
            writer.writeheader()
            for champ in roster.roster.values():
                writer.writerow(champ.to_json())
        filename = roster.data_dir + '/champions.csv'
        os.replace(tmp_file, filename)
        await self.bot.upload(filename)
        os.remove(filename)

    @roster.command(pass_context=True, name='template')
    async def _roster_template(self, ctx, *, user: discord.User = None):
        '''Google Sheet Template

        Blank CSV template for champion importself.

        1. Add 5★ champions you do have.
        2. Delete 4★ champions (rows) you do not have.
        3. Set Rank = champion rank (1 to 5).
        4. Set Awakened = signature ability level.
        [4★: 0 to 99 | 5★: 0 to 200]
        5. Export file as 'champions.csv'.
        6. Upload CSV to Collector.
        7. Press OK'''

        if user is None:
            user = ctx.message.author
        message = 'Save a copy of the template (blue text):\n\n1. Add 5★ champions you do have.\n2. Delete 4★ champions you do not have.\n3. Set Rank = champion rank (1 to 5).\n4. Set Awakened = signature ability level.\n``[4★: 0 to 99 | 5★: 0 to 200]``\n5. Export file as \'champions.csv\'.\n6. Upload to Collector.\n7. Press OK\n\nPrerequisite: Google Sheets\n(there is an app for iOS|Android)\n'

        em = discord.Embed(color=user.color, title='Champion CSV template',
                           description=message, url='https://goo.gl/LaFrg7')
        em.set_author(name=user.name, icon_url=user.avatar_url)
        em.set_footer(text='Kelldor | CollectorDevTeam', icon_url=AUNTMAI)
        await self.bot.send_message(ctx.message.channel, embed=em)
        # await self.bot.send_message(ctx.message.channel,'iOS dumblink: https://goo.gl/LaFrg7')

    @roster.command(pass_context=True, hidden=True, name='role_export', aliases=('rrx',))
    async def _role_roster_export(self, ctx, role: discord.Role):
        '''Returns a CSV file with all Roster data for all members of a Role'''
        server = ctx.message.server
        roster = ChampionRoster(ctx.bot, ctx.message.author)
        await roster.load_champions(silent=True)
        rand = randint(1000, 9999)
        path, ext = os.path.split(roster.champs_file)
        tmp_file = '{}-{}.tmp'.format(path, rand)
        # with open(tmp_file, 'w') as fp:
        with open(tmp_file, 'w', encoding='utf-8') as fp:
            writer = csv.DictWriter(fp, fieldnames=['member_mention', 'member_name', *(
                roster.fieldnames), 'bg'], extrasaction='ignore', lineterminator='\n')
            writer.writeheader()
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
                if role in member.roles:
                    roster = ChampionRoster(ctx.bot, member)
                    await roster.load_champions(silent=True)
                    for champ in roster.roster.values():
                        champ_dict = champ.to_json()
                        champ_dict['member_mention'] = member.mention
                        champ_dict['member_name'] = member.name
                        champ_dict['bg'] = bg
                        writer.writerow(champ_dict)
        filename = roster.data_dir + '/' + role.name + '.csv'
        os.replace(tmp_file, filename)
        await self.bot.upload(filename)
        os.remove(filename)

    @checks.admin_or_permissions(manage_server=True)
    @commands.command(pass_context=True, name='rank_prestige', aliases=('prestige_list',))
    async def _rank_prestige(self, ctx, *, hargs=''):
        hargs = await HashtagRankConverter(ctx, hargs).convert()
        roster = ChampionRoster(self.bot, self.bot.user, attrs=hargs.attrs)
        await roster.display(hargs.tags)

    @commands.command(pass_context=True, no_pm=True, aliases=('cp',))
    async def clan_prestige(self, ctx, role: discord.Role, verbose=0):
        '''Report Clan Prestige.
        Specify clan-role or battlegroup-role.

        If a detailed listing is desired, a verbose mode is included that handles sorting.
            1:  sort by prestige
            2:  sort by name
            3:  sort by display name

        Negative numbers reverse sorting order.

        Examples:
            /clan_prestige alliance 1        (sorted by prestige)
            /clan_prestige bg1 -2            (sorted by name, reversed)
        '''
        server = ctx.message.server
        width = 20
        str_out = '{{1:{width}}} p = {{0}}'.format(width=width)
        prestige = 0
        cnt = 0
        bundle = []
        line_out = []
        for member in server.members:
            if role in member.roles:
                roster = ChampionRoster(self.bot, member)
                if roster.is_bot:
                    continue
                await roster.load_champions(silent=True)
                if roster.prestige > 0:
                    prestige += roster.prestige
                    cnt += 1
                if verbose != 0:
                    bundle.append(
                        (roster.prestige, member.name, member.display_name))
        if verbose != 0:
            index = min(abs(verbose) - 1, 2)
            if index == 0:
                def getter(e): return e[index]
                rvs = True if verbose > 0 else False
            else:
                def getter(e): return e[index].lower()
                rvs = False if verbose > 0 else True
            for member in sorted(bundle, key=getter, reverse=rvs):
                name = member[1] if index < 2 else member[2]
                line_out.append(str_out.format(member[0], name))
            line_out.append('_' * (width + 11))
        if cnt > 0:
            line_out.append('{0:{width}} p = {1}  from {2} members'.format(
                role.name, round(prestige/cnt, 0), cnt, width=width))
            await self.bot.say('```{}```'.format('\n'.join(line_out)))
        else:
            await self.bot.say('You cannot divide by zero.')

    async def _on_attachment(self, msg):
        channel = msg.channel
        prefixes = tuple(self.bot.settings.get_prefixes(msg.server))
        if not msg.attachments or msg.author.bot or msg.content.startswith(prefixes):
            return
        for attachment in msg.attachments:
            if self.champ_re.match(attachment['filename']):
                message = await self.bot.send_message(channel,
                                                      "Found a CSV file to import.  \nLoad new champions? \nSelect OK to continue or X to cancel.")
                await self.bot.add_reaction(message, '❌')
                await self.bot.add_reaction(message, '🆗')
                react = await self.bot.wait_for_reaction(message=message, user=msg.author, timeout=30, emoji=['❌', '🆗'])
                if react is not None:
                    # await self.bot.send_message(channel, 'Reaction detected.')
                    if react.reaction.emoji == '🆗':
                        await self.bot.send_message(channel, 'OK detected')
                        roster = ChampionRoster(self.bot, msg.author)
                        await roster.parse_champions_csv(msg.channel, attachment)
                    elif react.reaction.emoji == '❌':
                        await self.bot.send_message(channel, 'X detected')
                        await self.bot.delete_message(message)
                        await self.bot.send_message(channel, 'Import canceled by user.')
                elif react is None:
                    await self.bot.send_message(channel, 'No reaction detected.')
                    try:
                        # Cancel
                        await self.bot.remove_reaction(message, '❌', self.bot.user)
                        # choose
                        await self.bot.remove_reaction(message, '🆗', self.bot.user)
                    except:
                        self.bot.delete_message(message)
                    await self.bot.send_message(channel, "Did not import")

    async def get_champ_list(self, ctx, hargs=''):

        if ChampionRoster is not None:
            sgd = StaticGameData()
            aliases = {'#var2': '(#5star | #6star) & #size:xl',
                       '#poisoni': '#poisonimmunity',
                       '#bleedi': '#bleedimmunity'}
            roster = await sgd.parse_with_attr(ctx, hargs, ChampionRoster, aliases=aliases)
            if roster is not None:
                await roster.display()
        else:
            return

    # async def get_counter_list(self, ctx, hargs=''):
    #     if ChampionRoster is not None:
    #         sgd = StaticGameData()
    #         aliases = {'#var2': '(#5star | #6star) & #size:xl',
    #                    '#poisoni': '#poisonimmunity',
    #                    '#bleedi': '#bleedimmunity',
    #                    '#regen': '#regeneration'}
    #         counterhargs = []

    #         roster = await sgd.parse_with_attr(ctx, hargs, ChampionRoster, aliases=aliases)
    #         if roster is not None:
    #             await roster.display()
    #     else:
    #         return


def parse_value(value):
    try:
        return ast.literal_eval(value)
    except Exception:
        return value


# -------------- setup -------------
def check_folders():
    # if not os.path.exists("data/hook"):
    #print("Creating data/hook folder...")
    # os.makedirs("data/hook")

    if not os.path.exists("data/hook/users"):
        print("Creating data/hook/users folder...")
        os.makedirs("data/hook/users")
        # transfer_info()


def setup(bot):
    check_folders()
    override_error_handler(bot)
    n = Hook(bot)
    sgd = StaticGameData(bot)
    # sgd.register_gsheets(bot)
    bot.add_cog(n)
    bot.add_listener(n._on_attachment, name='on_message')
