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
from cogs.mcocTools import (StaticGameData, PagesMenu, KABAM_ICON, COLLECTOR_ICON, CDTHelperFunctions, GSHandler, check_folders, check_files)
from cogs.mcoc import ChampConverter, ChampConverterDebug, Champion


class STORYQUEST:

    def __init__(self, bot):
        self.bot = bot
        self.gsheet_handler = GSHandler(bot)
        self.gsheet_handler.register_gsheet(
                name='act6_glossary',
                gkey='1Up5SpQDhp_SUOb5UFuD6BwkVKsJ4ZKN13DHHNJrNrEc',
                local='data/storyquest/act6_glossary.json',
                range='glossary'
            )
        self.gsheet_handler.register_gsheet(
                name='act6_paths',
                gkey='1Up5SpQDhp_SUOb5UFuD6BwkVKsJ4ZKN13DHHNJrNrEc',
                local='data/storyquest/act6_paths.json',
                range='export'
            )
        sgd = StaticGameData()
        self.glossary = sgd.get_gsheets_data('act6_glossary')
        self.export = sgd.get_gsheets_data('act6_paths')

    @commands.group(pass_context=True, aliases='sq')
    async def storyquest(self, ctx):
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @storyquest.command(pass_context=True, name='boost')
    async def _boost_info(self, ctx, boost):
        boosts = self.glossary.keys()
        if boost in boosts:
            await self.bot.say('boost found')
        else:
            await self.bot.say('boost not found '
                               'available boosts')
            await self.bot.say('\n'.join(b for b in boosts))





def setup(bot):
    check_folders()
    check_files()
    sgd = StaticGameData()
    sgd.register_gsheets(bot)
    bot.add_cog(STORYQUEST(bot))
