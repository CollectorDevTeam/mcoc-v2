import discord
import aiohttp
import urllib, json #For fetching JSON from alliancewar.com
import os
import requests
import re
import json
from .utils.dataIO import dataIO
from discord.ext import commands
from __main__ import send_cmd_help
from cogs.mcocTools import (StaticGameData, PagesMenu, KABAM_ICON, COLLECTOR_ICON, CDTHelperFunctions, GSHandler)
from cogs.mcoc import ChampConverter, ChampConverterDebug, Champion


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
        self.act6_glossary = None
        self.act6_paths = None

        # sgd = StaticGameData()
        # self.glossary = await sgd.get_gsheets_data('act6_glossary')
        # self.export = await sgd.get_gsheets_data('act6_paths')

    async def _load_sq(self):
        await self.gsheet_handler.cache_gsheets('act6_glossary')
        await self.gsheet_handler.cache_gsheets('act6_paths')
        self.glossary = dataIO.load_json('data/storyquest/act6_glossary.json')
        self.paths = dataIO.load_json('data/storyquest/act6_paths.json')

    @commands.group(pass_context=True, aliases=('sq',))
    async def storyquest(self, ctx):
        if self.act6_glossary is None:
            await self._load_sq()
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @storyquest.command(pass_context=True, name='boost')
    async def _boost_info(self, ctx, boost):
        boosts = self.act6_glossary.keys()
        if boost in boosts:
            await self.bot.say('boost found')
        else:
            await self.bot.say('boost not found '
                               'available boosts')
            await self.bot.say('\n'.join(b for b in boosts))



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
