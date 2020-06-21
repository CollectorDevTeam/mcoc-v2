import discord
import aiohttp
import urllib
import json  # For fetching JSON from alliancewar.com
import os
import requests
import re
import json
from .utils.dataIO import dataIO
from .utils import chat_formatting as chat
from collections import defaultdict, ChainMap, namedtuple, OrderedDict

from discord.ext import commands
from __main__ import send_cmd_help
from .mcocTools import (StaticGameData, PagesMenu, KABAM_ICON, CDTEmbed,
                            COLLECTOR_ICON, CDTHelperFunctions, GSHandler, CDT_COLORS)
from .mcocTools import (SearchExpr, P0Expr, ParenExpr, SearchNumber, SearchPhrase,
                            ExplicitKeyword, SearchNumber, SearchWord, SearchPhrase)  # search stuff
from .mcoc import ChampConverter, ChampConverterDebug, Champion

GSHEET_ICON = 'https://d2jixqqjqj5d23.cloudfront.net/assets/developer/imgs/icons/google-spreadsheet-icon.png'
ACT6_SHEET = 'https://docs.google.com/spreadsheets/d/1xTw37M_fwYClNfgvi7-09M6MLIcgMziTfM5_MGbAs0Q/view'
REBIRTH = 'https://cdn.discordapp.com/attachments/398210253923024902/556216721933991936/46BBFB298E7EEA7DD8A5A1FAC65FBA621A6212B5.jpg'
PATREON = 'https://patreon.com/collectorbot'


class STORYQUEST:
    EmojiReact = namedtuple('EmojiReact', 'emoji include path text')

    def __init__(self, bot):
        self.bot = bot
        self.search_parser = SearchExpr.parser()
        self.gsheet_handler = GSHandler(bot)
        self.umcoc = self.bot.get_server('378035654736609280')
        self.catmurdock = self.umcoc.get_member('373128988962586635')

        self.gsheet_handler.register_gsheet(
            name='cdt_glossary',
            gkey='1Up5SpQDhp_SUOb5UFuD6BwkVKsJ4ZKN13DHHNJrNrEc',
            local='data/storyquest/cdt_glossary.json',
            sheet_name='glossary',
            range_name='glossary_export'
        )
        self.gsheet_handler.register_gsheet(
            name='cdt_export',
            gkey='1Up5SpQDhp_SUOb5UFuD6BwkVKsJ4ZKN13DHHNJrNrEc',
            local='data/storyquest/cdt_export.json',
            sheet_name='export',
            range_name='export'
        )
        self.gsheet_handler.register_gsheet(
            name='cdt_paths',
            gkey='1Up5SpQDhp_SUOb5UFuD6BwkVKsJ4ZKN13DHHNJrNrEc',
            local='data/storyquest/cdt_paths.json',
            sheet_name='paths',
            range_name='paths'
        )
        self.gsheet_handler.register_gsheet(
            name='cdt_globals',
            gkey='1Up5SpQDhp_SUOb5UFuD6BwkVKsJ4ZKN13DHHNJrNrEc',
            local='data/storyquest/cdt_globals.json',
            sheet_name='globals',
            range_name='globals'
        )
        try:
            self.glossary = dataIO.load_json(
                'data/storyquest/cdt_glossary.json')
            self.glossary_desc = dataIO.load_json(
                'data/storyquest/cdt_glossary_desc.json')
            self.glossary_tips = dataIO.load_json(
                'data/storyquest/cdt_glossary_tips.json')
            self.glossary_keys = dataIO.load_json(
                'data/storyquest/cdt_glossary_keys.json')
            self.export = dataIO.load_json('data/storyquest/cdt_export.json')
            self.paths = dataIO.load_json('data/storyquest/cdt_paths.json')
            self.globals = dataIO.load_json('data/storyquest/cdt_globals.json')
        except:
            self.glossary = {}
            self.glossary_tips = {}
            self.glossary_keys = {}
            self.glossary_desc = {}
            self.export = {}
            self.paths = {}
            self.globals = {}
        self.all_emojis = OrderedDict([(i.emoji, i) for i in (
            self.EmojiReact("0⃣", 0, 'path0', ':zero:'),
            self.EmojiReact("1⃣", 1, 'path1', ':one:'),
            self.EmojiReact("2⃣", 2, 'path2', ':two:'),
            self.EmojiReact("3⃣", 3, 'path3', ':three:'),
            self.EmojiReact("4⃣", 4, 'path4', ':four:'),
            self.EmojiReact("5⃣", 5, 'path5', ':five:'),
            self.EmojiReact("6⃣", 6, 'path6', ':six:'),
            self.EmojiReact("7⃣", 7, 'path7', ':seven:'),
            self.EmojiReact("8⃣", 8, 'path8', ':eight:'),
            self.EmojiReact("9⃣", 9, 'path9', ':nine:'),
            self.EmojiReact("🔟", 10, 'path10', ':keycap_ten:'),
        )])

    async def _load_sq(self, force=False):
        if self.glossary == {} or self.export == {} or force is True:
            await self.gsheet_handler.cache_gsheets('cdt_glossary')
            await self.gsheet_handler.cache_gsheets('cdt_export')
            await self.gsheet_handler.cache_gsheets('cdt_paths')
            await self.gsheet_handler.cache_gsheets('cdt_globals')
        temp = dataIO.load_json('data/storyquest/cdt_glossary.json')
        glossary_keys = {}
        glossary_tips = {}
        glossary_desc = {}
        # glossary_titles = {}
        for t in temp.keys():
            if t not in ('', '-', '_headers'):
                glossary_desc.update({t: temp[t]['description']})
                glossary_tips.update({t: temp[t]['tips']})
                glossary_keys.update({t: temp[t]['title']})
                # glossary_titles.update({t: temp[t]['title']})
        self.glossary_desc = glossary_desc
        self.glossary_keys = glossary_keys
        self.glossary_tips = glossary_tips
        # self.glossary_titles = glossary_titles
        self.glossary = temp
        dataIO.save_json('data/storyquest/cdt_glossary.json', self.glossary)
        dataIO.save_json(
            'data/storyquest/cdt_glossary_desc.json', self.glossary_desc)
        dataIO.save_json(
            'data/storyquest/cdt_glossary_keys.json', self.glossary_keys)
        dataIO.save_json(
            'data/storyquest/cdt_glossary_tips.json', self.glossary_tips)
        # dataIO.save_json('data/storyquest/cdt_glossary_titles.json', self.glossary_titles)
        # self.glossary_keys = dataIO.load_json('data/storyquest/cdt_glossary_keys.json')
        self.export = dataIO.load_json('data/storyquest/cdt_export.json')
        self.paths = dataIO.load_json('data/storyquest/cdt_paths.json')
        self.globals = dataIO.load_json('data/storyquest/cdt_globals.json')

        return

    @commands.group(pass_context=True, aliases=('sq',))
    async def storyquest(self, ctx):
        """[BETA]: Story Quest
        Supporting Act 6.1.x
        Boost Glossary & Paths"""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @storyquest.command(hidden=True, name='fetch')
    async def _fetch(self):
        await self._load_sq(force=True)

    @commands.command(pass_context=True, name='glossary', aliases=('boost',))
    async def _boost_info(self, ctx, *, boost=None):
        """Story Quest Glossary
        Supporting Act 5 & Act 6 node boosts."""
        keys = []
        for k in self.glossary.keys():
            if k != "-" and k != "_headers" and k != "":
                keys.append(k)
        keys = sorted(keys)
        author = ctx.message.author
        if ctx.message.channel.is_private:
            ucolor = discord.Color.gold()
        else:
            ucolor = author.color
        if boost is not None and boost.lower() not in keys:
            for k in keys:
                if self.glossary[k]['title'].lower() == boost.lower():
                    boost = k
                    continue

        if boost is not None and boost.lower() in keys:
            data = discord.Embed(color=ucolor, title='{}'.format(
                self.glossary[boost.lower()]['title']), description='', url=PATREON)
            data.set_thumbnail(url=COLLECTOR_ICON)
            data.set_author(name='Support CollectorDevTeam')
            data.set_thumbnail(url=REBIRTH)
            # data.set_author(name='Glossary by StarFighter + DragonFei + Royal', icon_url=GSHEET_ICON)
            data.set_footer(
                text='Glossary by StarFighter + DragonFei + Royal | Requested by {}'.format(
                    author.display_name),
                icon_url=GSHEET_ICON)
            data.description = self.glossary[boost.lower()]['description']
            if self.glossary[boost.lower()]['tips'] != "":
                data.add_field(name='CollectorVerse Tips',
                               value=self.glossary[boost.lower()]['tips'])
            await self.bot.say(embed=data)
            return
        elif boost is None:
            pages = []
            glossary = ''
            linebreak = '---------------------------------------------------------\n'
            for key in keys:
                try:
                    glossary += linebreak+'key: {}\n**{}**\n{}\n'.format(
                        key, self.glossary[key]['title'], self.glossary[key]['description'])
                except KeyError:
                    raise KeyError('Cannot resolve {}'.format(boost.lower()))
            glossary = chat.pagify(glossary)
            for g in glossary:
                data = discord.Embed(
                    color=ucolor, title='Story Quest Boost Glossary', description=g, url=ACT6_SHEET)
                data.set_thumbnail(url=REBIRTH)
                # data.set_author(name='Glossary by StarFighter + DragonFei + Royal', icon_url=GSHEET_ICON)
                data.set_footer(
                    text='Glossary by StarFighter + DragonFei + Royal | Requested by {}'.format(
                        author.display_name),
                    icon_url=GSHEET_ICON)
                pages.append(data)
            if len(pages) > 0:
                menu = PagesMenu(self.bot, timeout=120,
                                 delete_onX=True, add_pageof=True)
                await menu.menu_start(pages)
        else:
            result = self.search_parser.parse_string(boost)
            print(result.elements)
            matches = result.match(self.glossary_desc, self.glossary_keys)
            package = []
            for k in sorted(matches):
                package.append('\n__{}__\n{}'.format(
                    self.glossary[k]['title'], self.glossary[k]['description']))
            pages = chat.pagify('\n'.join(package))
            page_list = []
            for page in pages:
                data = discord.Embed(
                    title='Support CollectorDevTeam', description=page, color=ucolor, url=PATREON)
                data.set_thumbnail(url=COLLECTOR_ICON)
                data.set_author(
                    name='Glossary Search: [{}]'.format(boost.lower()))
                data.set_footer(
                    text='Glossary by StarFighter + DragonFei + Royal | Requested by {}'.format(
                        author.display_name),
                    icon_url=GSHEET_ICON)
                page_list.append(data)
            menu = PagesMenu(self.bot, timeout=120,
                             delete_onX=True, add_pageof=True)
            await menu.menu_start(page_list)
            return

        # if boost in boost_keys:
        #     await self.bot.say('debug: boost found')
        #     await self.bot.say(self.glossary[boost]['description'])
        # else:
        #     await self.bot.say('boost not found '
        #                        'available boosts')

    @commands.command(pass_context=True, name='act', aliases=('sq path',))
    async def _paths(self, ctx, map=None, path=None, verbose=True):
        """[BETA] Story Quest
        Act 6 Fights
        maps: 6.1.1, 6.1.2, 6.1.3, 6.1.4, 6.1.5, 6.1.6
        paths:  path1 to path10
        verbose: If true, will play all fights sequentially
        """
        author = ctx.message.author
        ucolor = discord.Color.gold()
        if ctx.message.channel.is_private is False:
            ucolor = author.color
        data = discord.Embed(
            color=ucolor, title='Story Quest Help', description='')
        starfire_maps = ('6.1.1', '6.1.2', '6.1.3', '6.1.4', '6.1.5', '6.1.6')
        valid_maps = []
        for k in self.paths.keys():
            if k != '_headers' and k != 'emoji' and k != 'map' and 'rttl_' not in k:
                valid_maps.append(k)
                valid_maps.sort()
        if map not in valid_maps or map is None:
            message = 'Select a valid map:\n'
            message += '5.3: 5.3.1, 5.3.2, 5.3.3, 5.3.4, 5.3.5, 5.3.6\n'
            message += '5.4: 5.4.1, 5.4.2, 5.4.3, 5.4.4, 5.4.5, 5.4.6\n'
            message += '6.1: 6.1.1, 6.1.2, 6.1.3, 6.1.4, 6.1.5, 6.1.6\n'
            message += '6.2: N/A\n'
            # message += '6.2.1, 6.2.2, 6.2.3, 6.2.4, 6.2.5, 6.2.6\n'
            # message += ', '.join(valid_maps)
            data.description = message
            await self.bot.say(embed=data)
            return

        all_paths = self.paths['_headers']['paths']
        all_paths = list(filter(lambda a: a != '', all_paths)
                         )  # remove "" from valid paths
        valid_paths = []
        for a in all_paths:
            if a in self.paths[map].keys() and self.paths[map][a] != "":
                valid_paths.append(a)

        if path not in valid_paths and path is not None:
            if "path{}".format(path) in valid_paths:
                path = "path{}".format(path)
            else:
                return

        if path is None or path not in valid_paths:
            attrs = {}
            attrs['star'] = 5
            attrs['rank'] = 5
            if self.globals[map]['chapter_champ'] != '':
                boss = await ChampConverter.get_champion(self, self.bot, self.globals[map]['chapter_champ'], attrs)
                data.title = 'Map {}\nAct: {}\nChapter: {}\nQuest: {}'.\
                    format(map, self.globals[map]['act_title'],
                           self.globals[map]['chapter_title'],
                           self.globals[map]['quest_title'])
                data.set_thumbnail(url=boss.get_avatar())
            print(valid_paths)
            data.set_image(url=self.globals[map]['chapter_image'])

            for p in valid_paths:
                if p is not None and p != "":
                    key = '{}-{}-1'.format(map, p)
                    for emoji in self.all_emojis.values():
                        if emoji.path == p:
                            data.add_field(name=emoji.text, value='Quest: {}\nTiles: {}\nEnergy: {}\nNotes: {}\n'
                                           .format(p[-1:], self.export[key]['tiles'],
                                                   self.export[key]['tiles']*3,
                                                   self.export[key]['notes']))
                            continue
            description = ''
            gboosts = self.export[key]['global'].split(', ')
            for g in gboosts:
                if g != '-' and g != '':
                    # description += 'Global: {}\n{}\n\n'.format(self.glossary_titles[g], self.glossary_desc[g])
                    data.add_field(name='Global Boost: {}'.format(self.glossary_keys[g].title()),
                                   value='{}'.format(self.glossary_desc[g]))
                    if self.glossary_tips[g] != "":
                        data.add_field(name='CollectorVerse Tips',
                                       value=self.glossary_tips[g])

            # data.description=description
            message = await self.bot.say(embed=data)
            self.included_emojis = set()
            for emoji in self.all_emojis.values():
                if emoji.path in valid_paths:
                    try:
                        print(emoji.emoji)
                        await self.bot.add_reaction(message, emoji.emoji)
                    except:
                        raise KeyError(
                            'Unknwon Emoji : {}'.format(emoji.emoji))
                    self.included_emojis.add(emoji.emoji)
            react = await self.bot.wait_for_reaction(message=message, user=ctx.message.author,
                                                     timeout=30, emoji=self.included_emojis)
            if react is None:
                try:
                    await self.bot.clear_reactions(message)
                except discord.errors.NotFound:
                    # logger.warn("Message has been deleted")
                    print('Message deleted')
                except discord.Forbidden:
                    # logger.warn("clear_reactions didn't work")
                    for emoji in self.included_emojis:
                        await self.bot.remove_reaction(message, emoji, self.bot.user)
                return
            emoji = react.reaction.emoji
            path = self.all_emojis[emoji].path if emoji in self.all_emojis else None

        if path in valid_paths:
            tiles = self.paths[map][path]
            tiles = tiles.split(',')
            pages = []
            i = 1
            for tile in tiles:
                key = '{}-{}-{}'.format(map, path, tile)
                attrs = {}
                mob = self.export[key]['mob'].lower()
                attrs['star'] = 5
                attrs['rank'] = 5
                champion = await ChampConverter.get_champion(self, self.bot, mob, attrs)
                power = self.export[key]['power']
                hp = self.export[key]['hp']
                boosts = self.export[key]['boosts'].split(', ')
                gboosts = self.export[key]['global'].split(', ')
                notes = self.export[key]['notes']
                # attack = self.export[key]['attack']
                data = discord.Embed(color=CDT_COLORS[champion.klass], title='Act {} Path {} | Fight {}'.format(map, path[-1:], i),
                                     description='', url=ACT6_SHEET)
                tiles = self.export[key]['tiles']
                if champion.full_name is not None:
                    if power is not None:
                        data.set_author(name='{} : {:,}'.format(
                            champion.full_name, power))
                    else:
                        data.set_author(name='{}'.format(champion.full_name))
                if champion.get_avatar() is not None:
                    data.set_thumbnail(url=champion.get_avatar())
                if tiles != '':
                    data.description += '\nTiles: {}\n<:energy:557675957515845634>     {:,}'.format(
                        tiles, tiles*3)
                if hp != '':
                    data.description += '\n<:friendshp:344221218708389888>     {:,}'.format(
                        hp)
                else:
                    data.description += '\n<:friendshp:344221218708389888>     ???'

                for g in gboosts:
                    if g != '-' and g != '':
                        data.description += '\n\n__Global__: __{}__\n{}'.format(
                            self.glossary_keys[g], self.glossary_desc[g])
                        # data.add_field(name='Global Boost: {}'.format(g.title()),
                        #                value='{}'.format(self.glossary_desc[g]))
                        # if self.glossary_tips[g] != "":
                        #     data.add_field(name='CollectorVerse Tips', value=self.glossary_tips[g])

                for b in boosts:
                    if b != '-' and b != '':
                        data.description += '\n\n__{}__\n{}'.format(
                            self.glossary_keys[b], self.glossary_desc[b])
                        # data.add_field(name='{}'.format(b.title()),
                        #                value='{}'.format(self.glossary_desc[b]))
                        # if self.glossary_tips[b] != "":
                        #     data.add_field(name='CollectorVerse Tips', value=self.glossary_tips[b])
                if notes != '':
                    data.description += '\n\n__Notes__\n{}'.format(notes)
                    # data.add_field(name='Notes', value=notes)
                if map in starfire_maps:
                    data.set_footer(
                        text='Glossary by StarFighter + DragonFei + Royal | Requested by {}'
                             ''.format(author.display_name),
                        icon_url=GSHEET_ICON)
                else:
                    data.set_footer(
                        text='CollectorDevTeam Data + StarFighter | Requested by {}'.format(
                            author.display_name),
                        icon_url=COLLECTOR_ICON)
                pages.append(data)
                i += 1
            if verbose:
                i = 1
                for page in pages:
                    if map in starfire_maps:
                        page.set_footer(
                            text='Glossary by StarFighter + DragonFei + Royal | Requested by {} | Fight {} of {}'
                                 ''.format(author.display_name, i, len(pages)),
                            icon_url=GSHEET_ICON)
                    else:
                        page.set_footer(
                            text='CollectorDevTeam Data + StarFighter | Requested by {}'
                                 ''.format(
                                     author.display_name),
                            icon_url=COLLECTOR_ICON)
                    await self.bot.say(embed=page)
                    i += 1
            else:
                menu = PagesMenu(self.bot, timeout=720,
                                 delete_onX=True, add_pageof=True)
                await menu.menu_start(pages)
            return

    # @storyquest.command(pass_context=True, name='map')
    # async def _maps(self, ctx, map=None):
    #     '''Currently supporting Cat Murdock maps for 6.1 and 6.4'''
    #     cat_maps=('6.1.1', '6.1.2', '6.1.3', '6.1.4', '6.1.5', '6.1.6',
    #         '6.4.1', '6.4.2', '6.4.3', '6.4.4', '6.4.5', '6.4.6')
    #     if map is None:
    #         pages = []
    #         for map in cat_maps:
    #             data=CDTEmbed.get_embed(self, ctx)
    #             data.title='Act {} Map by :cat::sparkles:'.format(map)
    #             data.set_image(url=self.globals[map]['chapter_image'])
    #             data.set_author(name=self.catmurdock.display_name,
    #                 icon_url=self.catmurdock.avatar_url)
    #             data.add_field(
    #                 name='Support Cat', value='[Visit Cat\'s Store](https://www.redbubble.com/people/CatMurdock/explore)')
    #             pages.append(data)
    #         menu = PagesMenu(self.bot, timeout=30,
    #                             delete_onX=True, add_pageof=True)
    #         await menu.menu_start(pages)
    #     if map is not None and map in cat_maps:
    #         data=CDTEmbed.get_embed(self, ctx)
    #         data.title='Act {} Map by :cat::sparkles:'.format(map)
    #         data.set_image(url=self.globals[map]['chapter_image'])
    #         data.set_author(name=self.catmurdock.display_name,
    #             icon_url=self.catmurdock.avatar_url)
    #         data.add_field(
    #             name='Support Cat', value='[Visit Cat\'s Store](https://www.redbubble.com/people/CatMurdock/explore)')

    #         await self.bot.send_message(ctx.message.channel, embed=data)

    @commands.command(pass_context=True, name='rttl')
    async def rttl_paths(self, ctx, map=None, path=None, verbose=True):
        """Road To The Labyrinth Guide

        """
        author = ctx.message.author
        ucolor = discord.Color.gold()
        if ctx.message.channel.is_private is False:
            ucolor = author.color
        data = discord.Embed(
            color=ucolor, title='Story Quest Help', description='')

        # starfire_maps = ('6.1.1', '6.1.2', '6.1.3', '6.1.4', '6.1.5', '6.1.6')
        valid_maps = []
        for k in self.paths.keys():
            if k != '_headers' and k != 'emoji' and k != 'map' and k != 'rttl':
                valid_maps.append(k)
                valid_maps.sort()
        if map not in valid_maps and map is not None and path is None:
            if '.' in map:
                map, path = map.split('.')
                map = "rttl_{}".format(map)
                path = 'path{}'.format(path)
            elif "rttl_{}".format(map) in valid_maps:
                map = "rttl_{}".format(map)
            else:
                return
        else:
            data.description = 'Please select a valid Road to the Labyrinth Chapter:\n1, 2, 3, 4'
            await self.bot.say(embed=data)
            return

        print(map)
        print(path)
        all_paths = self.paths['_headers']['paths']
        all_paths = list(filter(lambda a: a != '', all_paths)
                         )  # remove "" from valid paths
        valid_paths = []
        for a in all_paths:
            if a in self.paths[map].keys() and self.paths[map][a] != "":
                valid_paths.append(a)

        if path not in valid_paths and path is not None:
            if "path{}".format(path) in valid_paths:
                path = "path{}".format(path)
            else:
                return
        elif path is None or path not in valid_paths:
            attrs = {}
            attrs['star'] = 5
            attrs['rank'] = 5
            if self.globals[map]['chapter_champ'] != '':
                boss = await ChampConverter.get_champion(self, self.bot, self.globals[map]['chapter_champ'], attrs)
                data.title = '{} | {}\nQuest: {}'.\
                    format(self.globals[map]['act_title'],
                           self.globals[map]['chapter_title'],
                           self.globals[map]['quest_title'])
                data.set_thumbnail(url=boss.get_avatar())
            print(valid_paths)

            for p in valid_paths:
                if p is not None and p != "":
                    key = '{}-{}-1'.format(map, p)
                    for emoji in self.all_emojis.values():
                        if emoji.path == p:
                            data.add_field(name=emoji.text, value='Quest: {}\nTiles: {}\nEnergy: {}\nNotes: {}'
                                           .format(p[-1:], self.export[key]['tiles'],
                                                   self.export[key]['tiles']*3,
                                                   self.export[key]['notes']))
                            continue
            gboosts = self.export[key]['global'].split(', ')
            for g in gboosts:
                if g != '-' and g != '':
                    data.add_field(name='Global Boost: {}'.format(g.title()),
                                   value='{}'.format(self.glossary_desc[g]))
                    if self.glossary_tips[g] != "":
                        data.add_field(name='CollectorVerse Tips',
                                       value=self.glossary_tips[g])

            message = await self.bot.say(embed=data)
            self.included_emojis = set()
            for emoji in self.all_emojis.values():
                if emoji.path in valid_paths:
                    try:
                        print(emoji.emoji)
                        await self.bot.add_reaction(message, emoji.emoji)
                    except:
                        raise KeyError(
                            'Unknwon Emoji : {}'.format(emoji.emoji))
                    self.included_emojis.add(emoji.emoji)

            react = await self.bot.wait_for_reaction(message=message, user=ctx.message.author,
                                                     timeout=30, emoji=self.included_emojis)
            if react is None:
                try:
                    await self.bot.clear_reactions(message)
                except discord.errors.NotFound:
                    # logger.warn("Message has been deleted")
                    print('Message deleted')
                except discord.Forbidden:
                    # logger.warn("clear_reactions didn't work")
                    for emoji in self.included_emojis:
                        await self.bot.remove_reaction(message, emoji, self.bot.user)
                return
            emoji = react.reaction.emoji
            path = self.all_emojis[emoji].path if emoji in self.all_emojis else None

        if path in valid_paths:
            tiles = self.paths[map][path]
            tiles = tiles.split(',')
            pages = []
            i = 1
            for tile in tiles:
                key = '{}-{}-{}'.format(map, path, tile)
                attrs = {}
                mob = self.export[key]['mob'].lower()
                attrs['star'] = 5
                attrs['rank'] = 5
                champion = await ChampConverter.get_champion(self, self.bot, mob, attrs)
                power = self.export[key]['power']
                hp = self.export[key]['hp']
                boosts = self.export[key]['boosts'].split(', ')
                gboosts = self.export[key]['global'].split(', ')
                notes = self.export[key]['notes']
                # attack = self.export[key]['attack']
                data = discord.Embed(color=CDT_COLORS[champion.klass], title='Road To The Labyrinth\nChapter {} Quest {} | Fight {}'.format(map[-1:], path[-1:], i),
                                     description='', url=ACT6_SHEET)
                tiles = self.export[key]['tiles']
                if power != '':
                    data.set_author(name='{} : {:,}'.format(
                        champion.full_name, power))
                else:
                    data.set_author(name='{}'.format(champion.full_name))
                data.set_thumbnail(url=champion.get_avatar())
                if tiles != '':
                    data.description += '\nTiles: {}\n<:energy:557675957515845634>     {:,}'.format(
                        tiles, tiles*3)
                # if power != '':
                #     data.description += '\nPower  {:,}'.format(power)
                if hp != '':
                    data.description += '\n<:friendshp:344221218708389888>     {:,}'.format(
                        hp)
                else:
                    data.description += '\n<:friendshp:344221218708389888>     ???'
                # if attack != '':
                #     data.description += '\n<:xassassins:487357359241297950>     {}'.format(attack)
                # else:
                #     data.description += '\n<:xassassins:487357359241297950>     ???'
                for g in gboosts:
                    if g != '-' and g != '':
                        data.add_field(name='Global Boost: {}'.format(g.title()),
                                       value='{}'.format(self.glossary_desc[g]))
                        if self.glossary_tips[g] != "":
                            data.add_field(
                                name='CollectorVerse Tips', value=self.glossary_tips[g])

                for b in boosts:
                    if b != '-' and b != '':
                        data.add_field(name='{}'.format(b.title()),
                                       value='{}'.format(self.glossary_desc[b]))
                        if self.glossary_tips[b] != "":
                            data.add_field(
                                name='CollectorVerse Tips', value=self.glossary_tips[b])
                if notes != '':
                    data.add_field(name='Notes', value=notes)
                data.set_footer(
                    text='CollectorDevTeam Data + StarFighter | Requested by {}'.format(
                        author.display_name),
                    icon_url=COLLECTOR_ICON)
                pages.append(data)
                i += 1
            if verbose:
                for page in pages:
                    await self.bot.say(embed=page)
            else:
                menu = PagesMenu(self.bot, timeout=360,
                                 delete_onX=True, add_pageof=True)
                await menu.menu_start(pages)
            return


def check_folders():
    folders = ('data', 'data/storyquest/')
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)


def check_files():
    ignore_list = {'SERVERS': [], 'CHANNELS': []}

    files = {
        'settings.json': {},
        'cdt_glossary.json': {},
        'cdt_paths.json': {},
        'cdt_path_keys.json': {}
    }

    for filename, value in files.items():
        if not os.path.isfile('data/storyquest/{}'.format(filename)):
            print("Creating empty {}".format(filename))
            dataIO.save_json('data/storyquest/{}'.format(filename), value)


def setup(bot):
    check_folders()
    check_files()
    sgd = StaticGameData()
    sgd.register_gsheets(bot)
    bot.add_cog(STORYQUEST(bot))
