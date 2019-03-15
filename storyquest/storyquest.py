import discord
import aiohttp
import urllib, json #For fetching JSON from alliancewar.com
import os
import requests
import re
import json
from .utils.dataIO import dataIO
from .utils import chat_formatting as chat

from discord.ext import commands
from __main__ import send_cmd_help
from cogs.mcocTools import (StaticGameData, PagesMenu, KABAM_ICON, COLLECTOR_ICON, CDTHelperFunctions, GSHandler)
from cogs.mcoc import ChampConverter, ChampConverterDebug, Champion

GSHEET_ICON = 'https://d2jixqqjqj5d23.cloudfront.net/assets/developer/imgs/icons/google-spreadsheet-icon.png'
ACT6_SHEET = 'https://docs.google.com/spreadsheets/d/1xTw37M_fwYClNfgvi7-09M6MLIcgMziTfM5_MGbAs0Q/view'
REBIRTH = 'https://cdn.discordapp.com/attachments/398210253923024902/556216721933991936/46BBFB298E7EEA7DD8A5A1FAC65FBA621A6212B5.jpg'

class STORYQUEST:

    def __init__(self, bot):
        self.bot = bot
        self.gsheet_handler = GSHandler(bot)
        self.gsheet_handler.register_gsheet(
                name='act6_glossary',
                gkey='1Up5SpQDhp_SUOb5UFuD6BwkVKsJ4ZKN13DHHNJrNrEc',
                local='data/storyquest/act6_glossary.json',
                sheet_name='glossary',
                range_name='glossary'
            )
        self.gsheet_handler.register_gsheet(
                name='act6_paths',
                gkey='1Up5SpQDhp_SUOb5UFuD6BwkVKsJ4ZKN13DHHNJrNrEc',
                local='data/storyquest/act6_paths.json',
                sheet_name='glossary',
                range_name='export'
            )
        try:
            self.glossary = dataIO.load_json('data/storyquest/act6_glossary.json')
            self.paths = dataIO.load_json('data/storyquest/act6_paths.json')
        except:
            self.glossary = {}
            self.paths = {}

    async def _load_sq(self, force=False):
        if self.glossary == {} or self.paths == {} or force is True:
            await self.gsheet_handler.cache_gsheets('act6_glossary')
            await self.gsheet_handler.cache_gsheets('act6_paths')
        self.glossary = dataIO.load_json('data/storyquest/act6_glossary.json')
        self.paths = dataIO.load_json('data/storyquest/act6_paths.json')
        return

    @commands.group(pass_context=True, aliases=('sq',))
    async def storyquest(self, ctx):
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @storyquest.command(hidden=True, name='fetch')
    async def _fetch(self):
        await self._load_sq(force=True)

    @storyquest.command(pass_context=True, name='boost')
    async def _boost_info(self, ctx, *, boost=None):
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
                    glossary += '{}\n{}\n\n'.format(key, self.glossary[key]['description'])
                except KeyError:
                    raise KeyError('Cannot resolve {}'.format(key))
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
        'act6_paths.json': {}
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
