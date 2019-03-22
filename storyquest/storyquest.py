import discord
import aiohttp
import urllib, json #For fetching JSON from alliancewar.com
import os
import requests
import re
import json
import asyncio
from collections import namedtuple, OrderedDict
from .utils.dataIO import dataIO
from .utils import chat_formatting as chat


from discord.ext import commands
from __main__ import send_cmd_help
from cogs.mcocTools import (StaticGameData, PagesMenu, KABAM_ICON, COLLECTOR_ICON, CDTHelperFunctions, GSHandler, CDT_COLORS)
from cogs.mcoc import ChampConverter, ChampConverterDebug, Champion

GSHEET_ICON = 'https://d2jixqqjqj5d23.cloudfront.net/assets/developer/imgs/icons/google-spreadsheet-icon.png'
ACT6_SHEET = 'https://docs.google.com/spreadsheets/d/1xTw37M_fwYClNfgvi7-09M6MLIcgMziTfM5_MGbAs0Q/view'
REBIRTH = 'https://cdn.discordapp.com/attachments/398210253923024902/556216721933991936/46BBFB298E7EEA7DD8A5A1FAC65FBA621A6212B5.jpg'

EmojiReact = namedtuple('EmojiReact', 'emoji include')


class STORYQUEST:

    def __init__(self, bot):
        self.bot = bot
        self.all_emojis = OrderedDict([(i.emoji, i) for i in (
            self.EmojiReact(":zero:", 0),
            self.EmojiReact(":one:", 1),
            self.EmojiReact(":two:", 2),
            self.EmojiReact(":three:", 3),
            self.EmojiReact(":four:", 4),
            self.EmojiReact(":five:", 5),
            self.EmojiReact(":six:", 6),
            self.EmojiReact(":seven:", 7),
            self.EmojiReact(":eight:", 8),
            self.EmojiReact(":nine:", 9),
            self.EmojiReact("🔟",  10),
        )])

        self.gsheet_handler = GSHandler(bot)
        self.gsheet_handler.register_gsheet(
                name='act6_glossary',
                gkey='1Up5SpQDhp_SUOb5UFuD6BwkVKsJ4ZKN13DHHNJrNrEc',
                local='data/storyquest/act6_glossary.json',
                sheet_name='glossary',
                range_name='glossary'
            )
        self.gsheet_handler.register_gsheet(
                name='act6_export',
                gkey='1Up5SpQDhp_SUOb5UFuD6BwkVKsJ4ZKN13DHHNJrNrEc',
                local='data/storyquest/act6_export.json',
                sheet_name='export',
                range_name='export'
            )
        self.gsheet_handler.register_gsheet(
            name='act6_paths',
            gkey='1Up5SpQDhp_SUOb5UFuD6BwkVKsJ4ZKN13DHHNJrNrEc',
            local='data/storyquest/act6_paths.json',
            sheet_name='paths',
            range_name='paths'
        )
        try:
            self.glossary = dataIO.load_json('data/storyquest/act6_glossary.json')
            self.export = dataIO.load_json('data/storyquest/act6_export.json')
            self.paths = dataIO.load_json('data/storyquest/act6_paths.json')
        except:
            self.glossary = {}
            self.export = {}
            self.paths = {}

    async def _load_sq(self, force=False):
        if self.glossary == {} or self.export == {} or force is True:
            await self.gsheet_handler.cache_gsheets('act6_glossary')
            await self.gsheet_handler.cache_gsheets('act6_export')
            await self.gsheet_handler.cache_gsheets('act6_paths')
        self.glossary = dataIO.load_json('data/storyquest/act6_glossary.json')
        self.export = dataIO.load_json('data/storyquest/act6_export.json')
        self.paths = dataIO.load_json('data/storyquest/act6_paths.json')
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

    @storyquest.command(pass_context=True, name='boost')
    async def _boost_info(self, ctx, *, boost=None):
        """Story Quest Glossary
        Supporting Act 6 node boosts."""
        keys = []
        for k in self.glossary.keys():
            if k != "-" and k != "_headers":
                keys.append(k)
        keys = sorted(keys)
        author = ctx.message.author
        if ctx.message.channel.is_private:
            ucolor = discord.Color.gold()
        else:
            ucolor = author.color
        if boost is None or boost not in keys:
            pages = []
            glossary = ''
            for key in keys:
                try:
                    glossary += '__{}__\n{}\n\n'.format(self.glossary[key]['name'], self.glossary[key]['description'])
                except KeyError:
                    raise KeyError('Cannot resolve {}'.format(boost))
            glossary = chat.pagify(glossary)
            for g in glossary:
                data = discord.Embed(color=ucolor, title='Story Quest Boost Glossary', description=g, url=ACT6_SHEET)
                data.set_thumbnail(url=REBIRTH)
                # data.set_author(name='Glossary by StarFighter + DragonFei + Royal', icon_url=GSHEET_ICON)
                data.set_footer(
                    text='Glossary by StarFighter + DragonFei + Royal | Requested by {}'.format(author.display_name),
                    icon_url=GSHEET_ICON)
                pages.append(data)
            if len(pages) > 0:
                menu = PagesMenu(self.bot, timeout=120, delete_onX=True, add_pageof=True)
                await menu.menu_start(pages)
        elif boost in keys:
            data = discord.Embed(color=ucolor, title='Story Quest Boost Glossary', description='', url=ACT6_SHEET)
            data.set_thumbnail(url=REBIRTH)
            # data.set_author(name='Glossary by StarFighter + DragonFei + Royal', icon_url=GSHEET_ICON)
            data.set_footer(
                text='Glossary by StarFighter + DragonFei + Royal | Requested by {}'.format(author.display_name),
                icon_url=GSHEET_ICON)
            data.description = self.glossary[boost]['description']
            await self.bot.say(embed=data)
        # if boost in boost_keys:
        #     await self.bot.say('debug: boost found')
        #     await self.bot.say(self.glossary[boost]['description'])
        # else:
        #     await self.bot.say('boost not found '
        #                        'available boosts')

    @storyquest.command(pass_context=True, name='path')
    async def _paths(self, ctx, map:str, path=None, verbose=False):
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
        data = discord.Embed(color=ucolor, title='Story Quest Help',)
        # jjs_maps = ('5.3.1', '5.3.2')
        bg_maps = ('5.4.1', '5.4.2', '5.4.3', '5.4.4', '5.4.5', '5.4.6')
        starfighter_maps = ('6.1.1', '6.1.2', '6.1.3', '6.1.4', '6.1.5', '6.1.6')
        if map in starfighter_maps:
            footer = 'Data by StarFighter + DragonFei + Royal | Requested by {}'.format(author.display_name)
        elif map in bg_maps:
            footer = '[Data by Brian Grant](https://www.reddit.com/r/ContestOfChampions/comments/7y4qgh/heres_the_spreadsheet_of_node_info_i_gathered_for/)' \
                     ' | Requested by {}'.format(author.display_name)
        else:
            footer = 'CollectorDevTeam | Requested by {}'.format(author.display_name)
        valid_maps = []
        for k in self.paths.keys():
            valid_maps.append(k)
        if map not in valid_maps:
            message = 'Select a valid map:\n'
            message += '\n'.join(valid_maps)
            data.description = message
            message = await self.bot.say(embed=data)
            return

        valid_paths = []
        for k in self.paths[map].keys():
            if k != "":
                valid_paths.append(k)

        # elif map in jjs_maps:
        #     valid_paths = ('path1', 'path2', 'path3', 'path4', 'path5')
        # elif map == '6.1.3':
        #     valid_paths = ('path0', 'path1', 'path2', 'path3', 'path4')
        # else:
        #     valid_paths = ('path1', 'path2', 'path3', 'path4', 'path5', 'path6', 'path7', 'path8', 'path9', 'path10')

        if isinstance(path, int):
            if 'path{}'.format(path) in valid_paths:
                path = 'path{}'.format(path)
        if path is None or path not in valid_paths:
            message = 'Valid paths include:\n'
            message += '\n'.join(valid_paths)
            data.description = message
            message = await self.bot.say(embed=data)
            # return
            ## this needs to be down in valid paths ##
            included = []
            for i in valid_paths:
                included.append(int(i[4:]))

            self.included_emojis = set()
            for emoji in self.all_emojis.values():
                if emoji.include in included:
                    await self.bot.add_reaction(message, emoji.emoji)
                    self.included_emojis.add(emoji.emoji)
            await asyncio.sleep(1)
            react = await self.bot.wait_for_reaction(message=message, timeout=120, emoji=self.included_emojis)
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
                return None
            # await self.bot.delete_message(message)
            emoji = react.reaction.emoji
            path = 'path{}'.format(emoji.include)

        if path is not None:
            tiles = self.paths[map][path]
            tiles = list(tiles)
            max = tiles[-1]
            pages = []
            i = 1
            for tile in list(tiles):
                key = '{}-{}-{}'.format(map, path, tile)
                attrs = {}
                mob = self.export[key]['mob']
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
                data.set_author(name='{} : {}'.format(champion.full_name,power))
                data.set_thumbnail(url=champion.get_avatar())
                if tiles != '':
                    data.description += '\nTiles: {}\n<:energy:557675957515845634>     {:,}'.format(tiles, tiles*3)
                # if power != '':
                #     data.description += '\nPower  {:,}'.format(power)
                if hp != '':
                    data.description += '\n<:friendshp:344221218708389888>     {:,}'.format(hp)
                else:
                    data.description += '\n<:friendshp:344221218708389888>     ???'
                # if attack != '':
                #     data.description += '\n<:xassassins:487357359241297950>     {}'.format(attack)
                # else:
                #     data.description += '\n<:xassassins:487357359241297950>     ???'
                for g in gboosts:
                    if g != '-' and g != '':
                        data.add_field(name='Global Boost: {}'.format(self.glossary[g.lower()]['name']),
                                       value='{}'.format(self.glossary[g.lower()]['description']))
                for b in boosts:
                    if b != '-' and b !='':
                        data.add_field(name='Local Boost: {}'.format(self.glossary[b.lower()]['name']),
                                       value='{}'.format(self.glossary[b.lower()]['description']))
                if notes != '':
                    data.add_field(name='Notes', value=notes)
                foot = footer + ' | Fight {} of {}'.format(i, max)
                data.set_footer(foot)
                pages.append(data)
                i += 1
            if verbose:
                for page in pages:
                    await self.bot.say(embed=page)
            else:
                menu = PagesMenu(self.bot, timeout=360, delete_onX=True, add_pageof=True)
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
        'act6_glossary.json': {},
        'act6_paths.json': {},
        'act6_path_keys.json': {}
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
