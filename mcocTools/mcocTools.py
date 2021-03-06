import asyncio
import csv
# from datetime import datetime, timedelta
import datetime
import time
from dateutil.parser import parse as dateParse
import json
import logging
import os
import re
# from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.common.keys import Keys
# defaultdict & partial needed for cache_gsheets
from collections import defaultdict, ChainMap, namedtuple, OrderedDict
from functools import partial
from pygsheets.utils import numericise_all, numericise
from validator_collection import validators, checkers
import requests
import random
import urllib

import aiohttp
import discord
import modgrammar as md
import pygsheets

from .cdtdiagnostics import DIAGNOSTICS
from .cdtembed import CDTEmbed
from .cdtpagesmenu import PagesMenu
from .cdtscreenshot import ScreenShot

from __main__ import send_cmd_help

from cogs.utils import checks
from discord.ext import commands

from .utils import chat_formatting as chat
from .utils.dataIO import dataIO

# for Calculator/

# from . import hook as hook
logger = logging.getLogger('red.mcoc.tools')
logger.setLevel(logging.INFO)

COLLECTOR_ICON = 'https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/cdt_icon.png'
COLLECTOR_FEATURED = 'https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/images/featured/collector.png'
COLLECTOR_CRYSTAL = 'https://media.discordapp.net/attachments/391330316662341632/725036637939171378/D1F5DE64D72C52880F61DBD6B2142BC6C096520D.png?width=461&height=461'
PATREON = 'https://patreon.com/collectorbot'

KABAM_ICON = 'https://imgur.com/UniRf5f.png'
GSX2JSON = 'http://gsx2json.com/api?id={}&sheet={}&columns=false&integers=false'

gapi_service_creds = "data/mcoc/mcoc_service_creds.json"

CDT_COLORS = {1: discord.Color(0x3c4d3b), 2: discord.Color(0xa05e44), 3: discord.Color(0xa0aeba),
              4: discord.Color(0xe1b963), 5: discord.Color(0xf55738), 6: discord.Color(0x07c6ed),
              'Cosmic': discord.Color(0x2799f7), 'Tech': discord.Color(0x0033ff),
              'Mutant': discord.Color(0xffd400), 'Skill': discord.Color(0xdb1200),
              'Science': discord.Color(0x0b8c13), 'Mystic': discord.Color(0x7f0da8),
              'All': discord.Color(0x03f193), 'Superior': discord.Color(0x03f193),
              'default': discord.Color.gold(), 'easy': discord.Color.green(),
              'beginner': discord.Color.green(), 'medium': discord.Color.gold(),
              'normal': discord.Color.gold(), 'heroic': discord.Color.red(),
              'hard': discord.Color.red(), 'expert': discord.Color.purple(),
              'master': discord.Color.purple(), 'epic': discord.Color(0x2799f7),
              'uncollected': discord.Color(0x2799f7), 'symbiote': discord.Color.darker_grey(),
              }


# class_color_codes = {
#         'Cosmic': discord.Color(0x2799f7), 'Tech': discord.Color(0x0033ff),
#         'Mutant': discord.Color(0xffd400), 'Skill': discord.Color(0xdb1200),
#         'Science': discord.Color(0x0b8c13), 'Mystic': discord.Color(0x7f0da8),
#         'All': discord.Color(0x03f193), 'Superior': discord.Color(0x03f193), 'default': discord.Color.light_grey(),
#         }

# def sync_to_async(func):
#     @wraps(func)
#     async def run(*args, loop=None, executor=None, **kwargs):
#         if loop is None:
#             loop = asyncio.get_event_loop()
#         pfunc = partial(func, *args, **kwargs)
#         return await loop.run_in_executor(executor, pfunc)
#     return run

class GSExport:
    default_settings = {
        'sheet_name': None,
        'sheet_action': 'file',
        'data_type': 'dict',
        'range': None,
        'include_empty': False,
        'column_handler': None,
        'row_handler': None,
        'rc_priority': 'column',
        'postprocess': None,
        'prepare_function': 'numericise_bool',
    }
    default_cell_handlers = (
        'cell_to_list',
        'cell_to_dict',
        'remove_commas',
        'remove_NA',
        'numericise',
        'numericise_bool'
    )
    cell_handler_aliases = {
        'to_list': 'cell_to_list',
        'to_dict': 'cell_to_dict',
    }

    def __init__(self, bot, gc, *, name, gkey, local, **kwargs):
        self.bot = bot
        self.gc = gc
        self.name = name
        self.gkey = gkey
        self.local = local
        self.meta_sheet = kwargs.pop('meta_sheet', 'meta_sheet')
        self.settings = self.default_settings.copy()
        self.settings.update(kwargs)
        self.data = defaultdict(partial(defaultdict, dict))
        self.cell_handlers = {}
        module_namespace = globals()
        for handler in self.default_cell_handlers:
            self.cell_handlers[handler] = module_namespace[handler]
        for alias, handler in self.cell_handler_aliases.items():
            self.cell_handlers[alias] = module_namespace[handler]
        self.robotworkshop = self.bot.get_channel('391330316662341632')

    async def retrieve_data(self):
        try:
            ss = self.gc.open_by_key(self.gkey)
        except:
            raise
            await self.bot.say("Error opening Spreadsheet <{}>".format(self.gkey))
            return
        if self.meta_sheet and self.settings['sheet_name'] is None:
            try:
                meta = ss.worksheet('title', self.meta_sheet)
            except pygsheets.WorksheetNotFound:
                meta = None
        else:
            meta = None

        if meta:
            for record in meta.get_all_records():
                [record.update(((k, v),)) for k, v in self.settings.items(
                ) if k not in record or not record[k]]
                await self.retrieve_sheet(ss, **record)
        else:
            await self.retrieve_sheet(ss, **self.settings)

        if self.settings['postprocess']:
            try:
                await self.settings['postprocess'](self.bot, self.data)
            except Exception as err:
                await self.bot.say("Runtime Error in postprocess of Spreadsheet "
                                   "'{}':\n\t{}".format(self.name, err))
                raise
        if self.local:
            dataIO.save_json(self.local, self.data)
        return self.data

    async def retrieve_sheet(self, ss, *, sheet_name, sheet_action, data_type, **kwargs):
        sheet_name, sheet = await self._resolve_sheet_name(ss, sheet_name)
        data = self.get_sheet_values(sheet, kwargs)
        header = data[0]

        if data_type.startswith('nested_list'):
            data_type, dlen = data_type.rsplit('::', maxsplit=1)
            dlen = int(dlen)
        # prep_func = self.cell_handlers[kwargs['prepare_function']]
        prep_func = self.get_prepare_function(kwargs)
        self.data['_headers'][sheet_name] = header
        col_handlers = self._build_column_handlers(sheet_name, header,
                                                   kwargs['column_handler'])
        if sheet_action == 'table':
            self.data[sheet_name] = [header]
        for row in data[1:]:
            clean_row = self._process_row(header, row, col_handlers, prep_func)
            rkey = clean_row[0]
            if sheet_action == 'merge':
                if data_type == 'nested_dict':
                    pack = dict(zip(header[2:], clean_row[2:]))
                    self.data[rkey][sheet_name][clean_row[1]] = pack
                    continue
                if data_type == 'list':
                    pack = clean_row[1:]
                elif data_type == 'dict':
                    pack = dict(zip(header[1:], clean_row[1:]))
                elif data_type == 'nested_list':
                    if len(clean_row[1:]) < dlen or not any(clean_row[1:]):
                        pack = None
                    else:
                        pack = [clean_row[i:i + dlen]
                                for i in range(1, len(clean_row), dlen)]
                else:
                    await self.bot.say("Unknown data type '{}' for worksheet '{}' in spreadsheet '{}'".format(
                        data_type, sheet_name, self.name))
                    return
                self.data[rkey][sheet_name] = pack
            elif sheet_action in ('dict', 'file'):
                if data_type == 'list':
                    pack = clean_row[1:]
                elif data_type == 'dict':
                    pack = dict(zip(header, clean_row))
                if data_type == 'nested_dict':
                    pack = dict(zip(header[2:], clean_row[2:]))
                    self.data[sheet_name][rkey][clean_row[1]] = pack
                elif sheet_action == 'dict':
                    self.data[sheet_name][rkey] = pack
                elif sheet_action == 'file':
                    self.data[rkey] = pack
            elif sheet_action == 'list':
                if data_type == 'list':
                    pack = clean_row[0:]
                elif data_type == 'dict':
                    pack = dict(zip(header, clean_row))
                if sheet_name not in self.data:
                    self.data[sheet_name] = []
                self.data[sheet_name].append(pack)
            elif sheet_action == 'table':
                self.data[sheet_name].append(clean_row)
            else:
                raise KeyError("Unknown sheet_action '{}' for worksheet '{}' in spreadsheet '{}'".format(
                    sheet_action, sheet_name, self.name))

    async def _resolve_sheet_name(self, ss, sheet_name):
        if sheet_name:
            try:
                sheet = ss.worksheet('title', sheet_name)
            except pygsheets.WorksheetNotFound:
                await self.bot.say("Cannot find worksheet '{}' in Spreadsheet '{}' ({})".format(
                    sheet_name, ss.title, ss.id))
        else:
            sheet = ss.sheet1
            sheet_name = sheet.title
        return sheet_name, sheet

    def _process_row(self, header, row, col_handlers, prep_func):
        clean_row = [row[0]]
        # don't process first column.  Can't use list, dicts, or numbers as keys in json
        for cell_head, cell, c_hand in zip(header[1:], row[1:], col_handlers[1:]):
            if c_hand:
                clean_row.append(c_hand(cell))
            else:
                clean_row.append(prep_func(cell))
        return clean_row

    def get_prepare_function(self, kwargs):
        prep_func = kwargs['prepare_function']
        prep_list = cell_to_list(prep_func)
        if prep_list[0] == prep_func:  # single prep
            return self.cell_handlers[prep_func]

        #  multiple prep
        handlers = [self.cell_handlers[i] for i in prep_list]

        def _curried(x):
            ret = x
            for func in handlers:
                ret = func(ret)
            return ret

        return _curried

    def get_sheet_values(self, sheet, kwargs):
        if kwargs['range']:
            rng = self.bound_range(sheet, kwargs['range'])
            data = sheet.get_values(*rng, returnas='matrix',
                                    include_empty=kwargs['include_empty'])
        else:
            data = sheet.get_all_values(include_empty=kwargs['include_empty'])
        return data

    def _build_column_handlers(self, sheet_name, header, column_handler_str):
        if not column_handler_str:
            return [None] * len(header)
        col_handler = cell_to_dict(column_handler_str)
        # print(col_handler)

        #  Column Header check
        invalid = set(col_handler.keys()) - set(header)
        if invalid:
            raise ValueError("Undefined Columns in column_handler for sheet "
                             + "'{}':\n\t{}".format(sheet_name, ', '.join(invalid)))
        #  Callback Cell Handler check
        invalid = set(col_handler.values()) - set(self.cell_handlers.keys())
        if invalid:
            raise ValueError("Undefined CellHandler in column_handler for sheet "
                             + "'{}':\n\t{}".format(sheet_name, ', '.join(invalid)))

        handler_funcs = []
        for column in header:
            if column not in col_handler:
                handler_funcs.append(None)
            else:
                handler_funcs.append(self.cell_handlers[col_handler[column]])
        return handler_funcs

    @staticmethod
    def bound_range(sheet, rng_str):
        rng = rng_str.split(':')
        rows = (1, sheet.rows)
        for i in range(2):
            if not rng[i][-1].isdigit():
                rng[i] = '{}{}'.format(rng[i], rows[i])
        return rng


class GSHandler:

    def __init__(self, bot, service_file=gapi_service_creds):
        self.bot = bot
        self.service_file = service_file
        self.gsheets = {}

    def register_gsheet(self, *, name, gkey, local, **kwargs):
        if name in self.gsheets:
            raise KeyError("Key '{}' has already been registered".format(name))
        self.gsheets[name] = dict(gkey=gkey, local=local, **kwargs)

    async def cache_gsheets(self, key=None):
        gc = await self.authorize()
        if key and key not in self.gsheets:
            raise KeyError("Key '{}' is not registered".format(key))
        gfiles = self.gsheets.keys() if not key else (key,)
        diagnostics = self.bot.get_channel('731208074043588649')

        num_files = len(gfiles)
        msg = await self.bot.send_message(diagnostics, 'Pulled Google Sheet data 0/{}'.format(num_files))
        package = {}
        for i, k in enumerate(gfiles):
            pulled = False
            # if not force and os.path.exists(self.gsheets[k]['local']):
            #     pulled = True
            #     package[k] = json.load(self.gsheets[k]['local'])
            if not pulled:
                for try_num in range(3):
                    gsdata = GSExport(self.bot, gc, name=k, **self.gsheets[k])
                    try:
                        package[k] = await gsdata.retrieve_data()
                        pulled = True
                        break
                    except:
                        logger.info(
                            "`cache_gsheets key={}`\nError while pulling '{}' try: {}".format(key, k, try_num))
                        if try_num < 3:
                            # time.sleep(.3 * try_num)
                            asyncio.sleep(.3*try_num)
                            await self.bot.send_message(diagnostics, "``cache_gsheets`` key={}:  Error while pulling '{}', try: {}".format(key, k, try_num))
            msg = await self.bot.edit_message(msg,
                                              'Pulled Google Sheet data {}/{}'.format(i + 1, num_files))
            logger.info('Pulled Google Sheet data {}/{}, {}'.format(i +
                                                                    1, num_files, "" if pulled else "Failed"))
        msg = await self.bot.edit_message(msg, 'Retrieval Complete')
        return package

    async def authorize(self):
        try:
            return pygsheets.authorize(service_file=self.service_file, no_cache=True)
        except FileNotFoundError:
            err_msg = 'Cannot find credentials file.  Needs to be located:\n' \
                      + self.service_file
            await self.bot.say(err_msg)
            raise FileNotFoundError(err_msg)


class StaticGameData:
    __instance = None
    remote_data_basepath = "https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/"
    cdt_data = {}
    cdt_versions = {}
    cdt_masteries = {}
    cdt_trials = None
    cdt_stats = {}
    gsheets_data = None
    test = 3
    tiercolors = {
        'easy': discord.Color.green(),
        'beginner': discord.Color.green(),
        'medium': discord.Color.gold(),
        'normal': discord.Color.gold(),
        'heroic': discord.Color.red(),
        'hard': discord.Color.red(),
        'expert': discord.Color.purple(),
        'master': discord.Color.purple(),
        'epic': discord.Color(0x2799f7),
        'uncollected': discord.Color(0x2799f7),
        'symbiote': discord.Color.darker_grey(),
    }

    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
            cls.__instance.__initialized = False
        return cls.__instance

    def __init__(self, bot=None):
        if self.__initialized:
            return
        if bot is None:
            raise ValueError('Missing argument "bot" during SGD init')
        self.__initialized = True
        self.bot = bot
        self.hash_parser = HashParser(bot)
        self.register_gsheets(bot)
        check_folders()
        check_files()
        self.cdt_data = dataIO.load_json('data/mcocTools/sgd_cdt_data.json')
        self.cdt_versions = dataIO.load_json(
            'data/mcocTools/sgd_cdt_versions.json')
        self.cdt_masteries = dataIO.load_json(
            'data/mcocTools/sgd_cdt_masteries.json')
        self.cdt_stats = dataIO.load_json('data/mcocTools/sgd_cdt_stats.json')
        # self.ability_counters = ('data/mcocTools/ability_counters.json')

    async def parse_with_attr(self, *args, **kwargs):
        return await self.hash_parser.parse_with_attr(*args, **kwargs)

    async def parse_with_user(self, *args, **kwargs):
        return await self.hash_parser.parse_with_user(*args, **kwargs)

    def register_gsheets(self, bot):
        self.gsheet_handler = GSHandler(bot, gapi_service_creds)
        self.gsheet_handler.register_gsheet(
            name='elemental_trials',
            gkey='1TSmQOTXz0-jIVgyuFRoaPCUZA73t02INTYoXNgrI5y4',
            local='data/mcocTools/sgd_event_quests.json',
            sheet_name='trials',
            # settings=dict(column_handler='champs: to_list')
        )
        self.gsheet_handler.register_gsheet(
            name='aw_season_rewards',
            gkey='1DZUoQr4eELkjxRo6N6UTtd6Jn15OfpEjiAV8M_v7_LI',
            local='data/mcocTools/sgd_season_rewards.json',
            sheet_name='season7',
            # settings=dict(column_handler='champs: to_list')
        )

        self.gsheet_handler.register_gsheet(
            name='tldr',
            gkey='1tQdQNjzr8dlSz2A8-G33YoNIU1NF8xqAmIgZtR7DPjM',
            local='data/mcocTools/sgd_tldr.json',
            sheet_name='output',
            range_name='tldr_output',
            # settings=dict(column_handler='champs: to_list')
        )

        self.gsheet_handler.register_gsheet(
            name='variant',
            gkey='1ZnoP_Kz_dC1DuTYmRX0spQLcHjiUZtT-oVTF52MHO3g',
            local='data/mcocTools/sgd_variant.json',
            sheet_name='Collectorfy',
            range_name='variant',
            # settings=dict(column_handler='champs: to_list')
        )
        self.gsheet_handler.register_gsheet(
            name='cdt_stats',
            gkey='1I3T2G2tRV05vQKpBfmI04VpvP5LjCBPfVICDmuJsjks',
            local='data/mcocTools/sgd_cdt_stats.json',
            sheet_name='spotlightJSON',
            range_name='stats_export',
        )

        # self.gsheet_handler.register_gsheet(
        #     name='ability_counters',
        #     gkey='1JSiGo-oGbPdmlegmGTH7hcurd_HYtkpTnZGY1mN_XCE',
        #     local='data/mcocTools/sgd_ability_counters.json',
        #     sheet_name='counters',
        #     range_name='awahapo_counters',
        # )

        # Update this list to add Events
        # events = ['13', '13.1', '14', '14.1', '15', '15.1', '16', '16.1', '17', '17.1', '17.2', '18', '18.1', '19',
        #           '19.1', '20', '20.1', '21', '21.1', '21.2', '21.3', '22', '22.1','23','23.1', '24',
        #           'love3', 'cmcc', 'recon', 'nzbounties', 'classtrip']
        #
        # for event in events:
        #     self.gsheet_handler.register_gsheet(
        #         name='eq_' + event,
        #         gkey='1TSmQOTXz0-jIVgyuFRoaPCUZA73t02INTYoXNgrI5y4',
        #         local='data/mcoc/eq_' + event + '.json',
        #         sheet_name='eq_' + event,
        #         # settings=dict(column_handler='champs: to_list')
        #     )

    async def load_cdt_data(self):
        # cdt_data, cdt_versions = ChainMap(), ChainMap()
        cdt_data, cdt_versions = {}, {}
        cdt_stats = None
        diagnostics = self.bot.get_channel('725478527969001483')
        files = {
            'data/mcocTools/bcg_en.json': 'https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/json/snapshots/en/bcg_en.json',
            'data/mcocTools/bcg_stat_en.json': 'https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/json/snapshots/en/bcg_stat_en.json',
            'data/mcocTools/special_attacks_en.json': 'https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/json/snapshots/en/special_attacks_en.json',
            'data/mcocTools/masteries_en.json': 'https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/json/snapshots/en/masteries_en.json',
            'data/mcocTools/character_bios_en.json': 'https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/json/snapshots/en/character_bios_en.json',
            # 'https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/json/snapshots/en/dungeons_en.json',
            # 'https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/json/snapshots/en/cutscenes_en.json',
            # 'https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/json/snapshots/en/initial_en.json',
            # 'https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/json/snapshots/en/alliances_en.json'
        }
        m1 = await self.bot.send_message(diagnostics, '1. Saving CDT Data + Versions')
        filelist = 0
        m1msg = '1. CDT Data + Versions\n'
        for f in files.keys():
            raw_data = await self.fetch_json(url=files[f], filepath=f)
            if raw_data is not None:
                m1msg += '{} saved.\n'.format(f)
                val, ver = {}, {}
                for dlist in raw_data['strings']:
                    cdt_data.update({dlist['k']: dlist['v']})
                    if 'vn' in dlist:
                        cdt_versions.update({dlist['k']: dlist['vn']})
                #     val[dlist['k']] = dlist['v']
                #     if 'vn' in dlist:
                #         ver[dlist['k']] = dlist['vn']
                # cdt_data.maps.append(val)
                # cdt_versions.maps.append(ver)
            else:
                m1msg += '{} not saved.'.format(f)
            await self.bot.edit_message(m1, m1msg)
        # for url in files:
        #     try:
        #         async with aiohttp.ClientSession() as session:
        #             validators.url(url)
        #             code = requests.get(url).status_code
        #             if code == 200:
        #                 try:
        #                     raw_data = await self.fetch_json(url, session)
        #                     if raw_data is not None:
        #                         await self.bot.send_message(diagnostics, 'URL {} is not empty'.format(filelist+1))
        #                         print(raw_data)
        #                         val, ver = {}, {}
        #                         for dlist in raw_data['strings']:
        #                             val[dlist['k']] = dlist['v']
        #                             if 'vn' in dlist:
        #                                 ver[dlist['k']] = dlist['vn']
        #                         cdt_data.maps.append(val)
        #                         cdt_versions.maps.append(ver)
        #                         filelist += 1
        #                 except:
        #                     await self.bot.send_message(diagnostics, 'Downloads failure: \n{}'.format(url))
        #             else:
        #                 print('CDT DATA URL Failure, code {}'.format(code))
        #                 print('Attempted URL:\n{}'.format(image))
        #         await self.bot.edit_message(m1, '1. CDT Data + Versions saved {} files'.format(filelist))
        #     except:
        #         await self.bot.edit_message(m1, '1. CDT Data + Versions failed to save')
        if cdt_data is not None:
            self.cdt_data.update(cdt_data)
            with open('data/mcocTools/sgd_cdt_data.json', 'w') as f:
                json.dump(self.cdt_data, f)
        # dataIO.save_json('data/mcocTools/sgd_cdt_data.json', self.cdt_data)
        if cdt_versions is not None:
            self.cdt_versions.update(cdt_versions)
            with open('data/mcocTools/sgd_cdt_versions.json', 'w') as f:
                json.dump(self.cdt_versions, f)
        # dataIO.save_json(
            # 'data/mcocTools/sgd_cdt_versions.json', self.cdt_versions)
        m2 = await self.bot.send_message(diagnostics, '2. Saving Masteries data')
        try:
            async with aiohttp.ClientSession() as session:
                self.cdt_masteries = await self.fetch_json(
                    self.remote_data_basepath + 'json/masteries.json',
                    session)
            dataIO.save_json(
                'data/mcocTools/sgd_masteries.json', self.cdt_masteries)
            await self.bot.edit_message(m2, '2. Masteries data saved')
        except:
            await self.bot.edit_message(m2, '2. Masteries data failed to save')
        m3 = await self.bot.send_message(diagnostics, '3. Saving CDT Champion Stats data.')
        try:
            self.cdt_stats = await StaticGameData.get_gsheets_data('cdt_stats')
            # dataIO.save_json('data/mcocTools/sgd_cdt_stats.json')
            await self.bot.edit_message(m3, '3. CDT Champion Stats saved.')
        except:
            await self.bot.edit_message(m3, '3. CDT Champion Stats failed to save.')
        # m4 = await self.bot.send_message(robotworkshop, 'Saving Ability counters')
        # self.ability_counters = await StaticGameData.get_gsheets_data('ability_counters')
        # dataIO.save_json(
        #     'data/mcocTools/sgd_ability_counters.json', self.ability_counters)
        # await self.bot.edit_message(m4, 'Ability Counters saved')

    async def cache_gsheets(self):
        print("Attempt gsheet pull")
        self.gsheets_data = await self.gsheet_handler.cache_gsheets()

    async def load_cdt_trials(self):
        raw_data = await self.fetch_gsx2json('1TSmQOTXz0-jIVgyuFRoaPCUZA73t02INTYoXNgrI5y4')
        package = {}
        rows = raw_data['rows'][0]
        for dlist in rows:
            package[dlist['unique']] = {'name': dlist['name'], 'champs': dlist['champs'], 'easy': dlist['easy'],
                                        'medium': dlist['medium'], 'hard': dlist['hard'], 'expert': dlist['expert']}
        self.cdt_trials = package

    async def get_gsheets_data(self, key=None, force=False):
        if force or self.gsheets_data is None:
            await self.cache_gsheets()
        if key:
            try:
                return self.gsheets_data[key]
            except KeyError:
                raise KeyError("Unregistered Key '{}':\n{}".format(
                    key, ', '.join(self.gsheets_data.keys())
                ))
        else:
            return self.gsheets_data

    @staticmethod
    async def fetch_json(url, session=None, filepath=None):
        try:
            r = requests.get(url)
            raw_data = r.json()
            if filepath is not None:
                with open(filepath, 'w') as f:
                    json.dump(raw_data, f)
        except:
            print('fecth_json requests.get(url) failed')
            if session is not None:
                async with session.get(url) as response:
                    raw_data = json.loads(await response.text())
                logger.info("Fetching " + url)
        if raw_data is not None:
            return raw_data
        else:
            return

    @staticmethod
    async def fetch_gsx2json(sheet_id, sheet_number=1, query: str = ''):
        url = GSX2JSON.format(sheet_id, sheet_number)
        if query != '':
            url = url + '&q' + query
        async with aiohttp.ClientSession() as session:
            json_data = await fetch_json(url=url, session=session)
            return json_data


##################################################
#  Grammar definitions
##################################################
md.grammar_whitespace_mode = 'optional'


class SearchNumber(md.Grammar):
    grammar = md.WORD('.0-9')

    def match(self, data, ver_data):
        matches = set()
        ver = self.string
        for key, val in ver_data.items():
            if ver == val:
                matches.add(key)
        return matches


class SearchWord(md.Grammar):
    grammar = md.WORD('-.,0-9A-Za-z_%')


class SearchPhrase(md.Grammar):
    grammar = md.ONE_OR_MORE(SearchWord)

    def match(self, data, ver_data):
        matches = set()
        up, low = self.string.upper(), self.string.lower()
        for key, val in data.items():
            if up == key:
                matches.add(key)
            elif low in val.lower():
                matches.add(key)
        return matches


class ExplicitKeyword(md.Grammar):
    grammar = (md.L('k:') | md.L('K:'), SearchWord)

    def match(self, data, ver_data):
        matches = set()
        up = self[1].string.upper()
        for key in data.keys():
            if up in key:
                matches.add(key)
        return matches


class ParenExpr(md.Grammar):
    grammar = (md.L('('), md.REF("SearchExpr"), md.L(")"))

    def match(self, data, ver_data):
        return self[1].match(data, ver_data)


class Operator(md.Grammar):
    grammar = md.L('&') | md.L('|')

    def op(self):
        if self.string == '&':
            return set.intersection
        elif self.string == '|':
            return set.union


class P0Term(md.Grammar):
    grammar = (ParenExpr | SearchNumber | SearchPhrase | ExplicitKeyword)

    def match(self, data, ver_data):
        return self[0].match(data, ver_data)


class P0Expr(md.Grammar):
    grammar = (P0Term, md.ONE_OR_MORE(Operator, P0Term))

    def match(self, data, ver_data):
        matches = self[0].match(data, ver_data)
        for e in self[1]:
            matches = e[0].op()(matches, e[1].match(data, ver_data))
        return matches


class SearchExpr(md.Grammar):
    grammar = (P0Expr | ParenExpr | SearchNumber |
               SearchPhrase | ExplicitKeyword)

    def match(self, data, ver_data):
        return self[0].match(data, ver_data)


##################################################
#  Champ Attr grammar

class AttrSigToken(md.Grammar):
    grammar = md.WORD('s', '0-9', min=2, max=4)

    def get_attrs(self, attrs):
        attrs['sig'] = int(self.string[1:])


class AttrRankToken(md.Grammar):
    grammar = md.WORD('r', '0-9', count=2)

    def get_attrs(self, attrs):
        attrs['rank'] = int(self.string[1])


class AttrDebugToken(md.Grammar):
    grammar = md.WORD('d', '0-9', count=2)

    def get_attrs(self, attrs):
        attrs['debug'] = int(self.string[1])


class AttrStarToken(md.Grammar):
    grammar = (md.WORD('0-9', count=1),
               md.OPTIONAL(md.L('\\')),
               md.WORD('*★☆', count=1))

    def get_attrs(self, attrs):
        attrs['star'] = int(self.string[0])


class AttrExpr(md.Grammar):
    grammar = md.ONE_OR_MORE(AttrSigToken | AttrRankToken |
                             AttrDebugToken | AttrStarToken, collapse=True)

    def get_attrs(self, attrs=None):
        attrs = attrs if attrs is not None else {}
        {e.get_attrs(attrs) for e in self}
        return attrs


class UserSnowflake(md.Grammar):
    grammar = md.L('<@'), md.OPTIONAL(md.L('!')), md.WORD('0-9'), md.L('>')
    grammar_whitespace_mode = 'explicit'


class UserDiscriminator(md.Grammar):
    grammar = md.L('#'), md.WORD('0-9', count=4)
    grammar_whitespace_mode = 'explicit'


class UserString(md.Grammar):
    grammar = (md.OPTIONAL(md.L('@')), md.ANY_EXCEPT('@!#()&|'),
               md.OPTIONAL(UserDiscriminator))
    grammar_whitespace_mode = 'explicit'


class UserExpr(md.Grammar):
    grammar = UserString | UserSnowflake

    def get_user(self, ctx):
        return commands.UserConverter(ctx, self.string).convert()

##################################################
#  Hashtag grammar


class HashtagPlusError(TypeError):
    pass


class HashtagToken(md.Grammar):
    grammar = md.WORD('#', "_a-zA-Z:*'0-9-"), md.WORD('_a-zA-Z:*0-9')

    def match_set(self, roster):
        return roster.raw_filtered_ids(set([self.string]))

    def sub_aliases(self, aliases):
        if self.string in aliases:
            return '({})'.format(aliases[self.string])
        else:
            return self.string


class HashParenExpr(md.Grammar):
    grammar = (md.L('('), md.REF("HashExplicitSearchExpr"), md.L(")"))

    def match_set(self, roster):
        return self[1].match_set(roster)

    def sub_aliases(self, aliases):
        return '({})'.format(self[1].sub_aliases(aliases))


class HashUnaryOperator(md.Grammar):
    grammar = md.L('!')

    def op(self, roster):
        return roster.ids_set().difference


class HashBinaryOperator(md.Grammar):
    grammar = md.L('&') | md.L('|') | md.L('-') | md.L('+')

    def op(self, roster):
        if self.string == '&':
            return set.intersection
        elif self.string == '|':
            return set.union
        elif self.string == '-':
            return set.difference
        elif self.string == '+':
            raise HashtagPlusError(
                "Operator '+' is not defined for Hashtag Syntax")

    def sub_aliases(self, aliases):
        if self.string == '+':
            raise HashtagPlusError(
                "Operator '+' is not defined for Hashtag Syntax")
        else:
            return self.string


class HashP0Term(md.Grammar):
    grammar = (HashParenExpr | HashtagToken)

    def match_set(self, roster):
        return self[0].match_set(roster)

    def sub_aliases(self, aliases):
        return self[0].sub_aliases(aliases)


class HashP0Expr(md.Grammar):
    grammar = (HashUnaryOperator, HashP0Term)

    def match_set(self, roster):
        return self[0].op(roster)(self[1].match_set(roster))

    def sub_aliases(self, aliases):
        return self[0].string + self[1].sub_aliases(aliases)


class HashP1Term(md.Grammar):
    grammar = (HashP0Expr | HashParenExpr | HashtagToken)

    def match_set(self, roster):
        return self[0].match_set(roster)

    def sub_aliases(self, aliases):
        return self[0].sub_aliases(aliases)


class HashP1Expr(md.Grammar):
    grammar = (HashP1Term, md.ONE_OR_MORE(HashBinaryOperator, HashP1Term))

    def match_set(self, roster):
        matches = self[0].match_set(roster)
        for e in self[1]:
            matches = e[0].op(roster)(matches, e[1].match_set(roster))
        return matches

    def sub_aliases(self, aliases):
        ret = self[0].sub_aliases(aliases)
        for e in self[1]:
            ret += e[0].sub_aliases(aliases) + e[1].sub_aliases(aliases)
        return ret


class HashExplicitSearchExpr(md.Grammar):
    grammar = (HashP1Expr | HashP0Expr | HashParenExpr | HashtagToken)

    def match_set(self, roster):
        return self[0].match_set(roster)

    def sub_aliases(self, aliases):
        return self[0].sub_aliases(aliases)

    def filter_roster(self, roster):
        filt_ids = self.match_set(roster)
        filt_roster = roster.filtered_roster_from_ids(filt_ids)
        return filt_roster


class HashImplicitSearchExpr(md.Grammar):
    grammar = md.ONE_OR_MORE(HashtagToken, collapse=True)

    def match_set(self, roster):
        filt_ids = roster.ids_set()
        for token in self:
            filt_ids = filt_ids.intersection(token.match_set(roster))
        return filt_ids

    def sub_aliases(self, aliases):
        ret = [token.sub_aliases(aliases) for token in self]
        return ' & '.join(ret)


class HashAttrSearchExpr(md.Grammar):
    grammar = (md.OPTIONAL(AttrExpr),
               md.OPTIONAL(HashImplicitSearchExpr | HashExplicitSearchExpr),
               md.OPTIONAL(AttrExpr))

    def sub_aliases(self, ctx, aliases):
        attrs = self[0].get_attrs() if self[0] else {}
        attrs = self[2].get_attrs(attrs) if self[2] else attrs
        return (attrs, self[1].sub_aliases(aliases)) if self[1] else (attrs, '')


class HashUserSearchExpr(md.Grammar):
    grammar = (md.OPTIONAL(UserExpr),
               md.OPTIONAL(HashImplicitSearchExpr | HashExplicitSearchExpr))

    def sub_aliases(self, ctx, aliases):
        user = self[0].get_user(ctx) if self[0] else ctx.message.author
        return (user, self[1].sub_aliases(aliases)) if self[1] else (user, '')


class HashParser:

    def __init__(self, bot):
        self.bot = bot
        self.attr_parser = HashAttrSearchExpr.parser()
        self.user_parser = HashUserSearchExpr.parser()
        self.explicit_parser = HashExplicitSearchExpr.parser()

    async def parse_1st_pass(self, ctx, parser, hargs, aliases=None):
        try:
            result1 = parser.parse_string(hargs)
        except md.ParseError as e:
            await self.generic_syntax_error_msg(hargs, e)
            raise
        try:
            return result1.sub_aliases(ctx, aliases)
        except HashtagPlusError as e:
            await self.hashtag_plus_error_msg()
            raise

    async def parse_2nd_pass(self, roster, expl_hargs):
        if expl_hargs:
            try:
                result2 = self.explicit_parser.parse_string(expl_hargs)
            except md.ParseError as e:
                await self.generic_syntax_error_msg(hargs, e)
                return
            try:
                return result2.filter_roster(roster)
            except HashtagPlusError as e:
                await self.hashtag_plus_error_msg()
                return
        else:
            return roster

    async def parse_with_attr(self, ctx, hargs, roster_cls, aliases=None):
        '''Parser implies no user roster so use bot.  Parse attrs to pass to roster creation.'''
        aliases = aliases if aliases else {}
        try:
            attrs, expl_hargs = await self.parse_1st_pass(ctx,
                                                          self.attr_parser, hargs, aliases)
        except (HashtagPlusError, md.ParseError) as e:
            # logger.info('SyntaxError caught ', str(e))
            return
        roster = roster_cls(self.bot, self.bot.user, attrs=attrs)
        return await self.parse_2nd_pass(roster, expl_hargs)

    async def parse_with_user(self, ctx, hargs, roster_cls, aliases=None):
        '''Parser implies user roster.'''
        aliases = aliases if aliases else {}
        try:
            user, expl_hargs = await self.parse_1st_pass(ctx, self.user_parser,
                                                         hargs, aliases)
        except (HashtagPlusError, md.ParseError) as e:
            # logger.info('SyntaxError caught ', str(e))
            return
        roster = roster_cls(self.bot, user)
        await roster.load_champions()
        return await self.parse_2nd_pass(roster, expl_hargs)

    async def generic_syntax_error_msg(self, hargs, e=None):
        em = discord.Embed(title='Input Error', description='Syntax problem',
                           color=discord.Color.red())
        em.add_field(name="Don't mix implicit and explicit operators",
                     value=hargs)
        await self.bot.say(embed=em)
        return

    async def hashtag_plus_error_msg(self):
        em = discord.Embed(title='Input Error', description='Syntax problem',
                           color=discord.Color.red())
        em.add_field(name="`+` operator is not defined for hashtags.",
                     value="You probably want the `|` operator.  Call "
                     "`/help hashtags` for detailed syntax.")
        await self.bot.say(embed=em)
        return

    async def filter_and_display(self, ctx, hargs, roster_cls, aliases=None):
        filtered = await self.parse_with_attr(ctx, hargs, roster_cls, aliases)
        if filtered:
            await filtered.display()
        elif filtered is not None:
            await filtered.warn_empty_roster(hargs)


##################################################
#  End Grammar definitions
##################################################

# class PagesMenu:
#     EmojiReact = namedtuple('EmojiReact', 'emoji include page_inc')

#     def __init__(self, bot, *, add_pageof=True, timeout=30, choice=False,
#                  delete_onX=True):
#         self.bot = bot
#         self.timeout = timeout
#         self.add_pageof = add_pageof
#         self.choice = choice
#         self.delete_onX = delete_onX
#         self.embedded = True

#     async def menu_start(self, pages, page_number=0):
#         page_list = []
#         if isinstance(pages, list):
#             page_list = pages
#         else:
#             for page in pages:
#                 page_list.append(page)
#         page_length = len(page_list)
#         if page_length == 1:
#             if isinstance(page_list[0], discord.Embed) == True:
#                 message = await self.bot.say(embed=page_list[0])
#             else:
#                 message = await self.bot.say(page_list[0])
#             return
#         self.embedded = isinstance(page_list[0], discord.Embed)
#         self.all_emojis = OrderedDict([(i.emoji, i) for i in (
#             self.EmojiReact(
#                 "\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}", page_length > 5, -5),
#             self.EmojiReact("\N{BLACK LEFT-POINTING TRIANGLE}", True, -1),
#             self.EmojiReact("\N{CROSS MARK}", True, None),
#             self.EmojiReact("\N{BLACK RIGHT-POINTING TRIANGLE}", True, 1),
#             self.EmojiReact(
#                 "\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}", page_length > 5, 5),
#         )])

#         print('menu_pages is embedded: ' + str(self.embedded))

#         if self.add_pageof:
#             for i, page in enumerate(page_list):
#                 if isinstance(page, discord.Embed):
#                     ftr = page.footer
#                     page.set_footer(text='{} (Page {} of {})'.format(ftr.text,
#                                                                      i + 1, page_length), icon_url=ftr.icon_url)
#                 else:
#                     page += '\n(Page {} of {})'.format(i + 1, page_length)

#         self.page_list = page_list
#         await self.display_page(None, page_number)

#     async def display_page(self, message, page):
#         if not message:
#             if isinstance(self.page_list[page], discord.Embed) == True:
#                 message = await self.bot.say(embed=self.page_list[page])
#             else:
#                 message = await self.bot.say(self.page_list[page])
#             self.included_emojis = set()
#             for emoji in self.all_emojis.values():
#                 if emoji.include:
#                     await self.bot.add_reaction(message, emoji.emoji)
#                     self.included_emojis.add(emoji.emoji)
#         else:
#             if self.embedded == True:
#                 message = await self.bot.edit_message(message, embed=self.page_list[page])
#             else:
#                 message = await self.bot.edit_message(message, self.page_list[page])
#         await asyncio.sleep(1)

#         react = await self.bot.wait_for_reaction(message=message,
#                                                  timeout=self.timeout, emoji=self.included_emojis)
#         if react is None:
#             try:
#                 await self.bot.clear_reactions(message)
#             except discord.errors.NotFound:
#                 logger.warn("Message has been deleted")
#                 print('Message deleted')
#             except discord.Forbidden:
#                 logger.warn("clear_reactions didn't work")
#                 for emoji in self.included_emojis:
#                     await self.bot.remove_reaction(message, emoji, self.bot.user)
#             return None

#         emoji = react.reaction.emoji
#         pages_to_inc = self.all_emojis[emoji].page_inc if emoji in self.all_emojis else None
#         if pages_to_inc:
#             next_page = (page + pages_to_inc) % len(self.page_list)
#             try:
#                 await self.bot.remove_reaction(message, emoji, react.user)
#                 await self.display_page(message=message, page=next_page)
#             except discord.Forbidden:
#                 await self.bot.delete_message(message)
#                 await self.display_page(message=None, page=next_page)
#         elif emoji == '\N{CROSS MARK}':
#             try:
#                 if self.delete_onX:
#                     await self.bot.delete_message(message)
#                     report = ('Message deleted by {} {} on {} {}'.format(
#                         react.user.display_name, react.user.id, message.server.name, message.server.id))
#                     print(report)
#                     channel = self.bot.get_channel('537330789332025364')
#                     await self.bot.send_message(channel, report)
#                     # await self.bot.edit_message(message, 'Menu deleted by {}'.format(react.user.display_name))
#                 else:
#                     await self.bot.clear_reactions(message)
#             except discord.Forbidden:
#                 await self.bot.say("Bot does not have the proper Permissions")

#     async def confirm(self, ctx, question: str):
#         """Returns Boolean"""
#         if ctx.message.channel.is_private:
#             ucolor = discord.Color.gold()
#         else:
#             ucolor = ctx.message.author.color
#         data = discord.Embed(title='Confirmation:sparkles:',
#                              description=question, color=ucolor)
#         data.set_footer(text='CollectorDevTeam Dataset',
#                         icon_url=COLLECTOR_ICON)
#         message = await self.bot.say(embed=data)

#         await self.bot.add_reaction(message, '❌')
#         await self.bot.add_reaction(message, '🆗')
#         react = await self.bot.wait_for_reaction(message=message,
#                                                  user=ctx.message.author, timeout=90, emoji=['❌', '🆗'])
#         if react is not None:
#             if react.reaction.emoji == '❌':
#                 data.description = '{} has canceled confirmation'.format(
#                     ctx.message.author.name)
#                 # data.add_field(name='Confirmation', value='{} has canceled confirmation'.format(ctx.message.author.name))
#                 await self.bot.edit_message(message, embed=data)
#                 return False, message
#             elif react.reaction.emoji == '🆗':
#                 data.description = '{} has confirmed.'.format(
#                     ctx.message.author.name)
#                 # data.add_field(name='Confirmation', value='{} has confirmed.'.format(ctx.message.author.name))
#                 await self.bot.edit_message(message, embed=data)
#                 return True, message
#         else:
#             data.description = '{} has not responded'.format(
#                 ctx.message.author.name)
#             # data.add_field(name='Confirmation', value='{} has not responded'.format(ctx.message.author.name))
#             await self.bot.edit_message(message, embed=data)
#             return False, message


class MCOCTools:
    """Tools for Marvel Contest of Champions"""

    def __init__(self, bot):
        self.bot = bot
        self.search_parser = SearchExpr.parser()
        self.mcoctools = dataIO.load_json('data/mcocTools/mcoctools.json')
        self.calendar_url = ''
        # self.cutoffs_url = ''
        self.arena = ''
        self.cutoffs = dataIO.load_json('data/mcocTools/cutoffs.json')
        self.summarystats = ''

        # self.tldr = dataIO.load_json('data/mcocTools/tldr.json')
        # self.date = ''
        # self.calendar = {}
        # self.calendar['time'] = dateParse(0)
        # self.calendar['screenshot'] = ''
        # dataIO.save_json('data/mcocTools/mcoctools.json', self.calendar)

    # lookup_links = {
    #     'hook': (
    #         '<http://hook.github.io/champions>',
    #         '[hook/Champions by gabriel](http://hook.github.io/champions)',
    #         'hook/champions for Collector',
    #         'https://assets-cdn.github.com/favicon.ico'),
    #     'alsciende': (
    #         '<https://alsciende.github.io/masteries/v10.0.1/#>',
    #         '[Alsciende Mastery Tool](https://alsciende.github.io/masteries/v17.0.2/#)',
    #         'by u/alsciende',
    #         'https://images-ext-2.discordapp.net/external/ymdMNrkhO9L5tUDupbFSEmu-JK0X2bpV0ZE-VYTBICc/%3Fsize%3D1024/https/cdn.discordapp.com/avatars/268829380262756357/b55ae7fc51d9b741450f949accd15fbe.webp?width=80&height=80'),
    # }
    # mcolor = discord.Color.red()
    # COLLECTOR_ICON = 'https://raw.githubusercontent.com/JasonJW/mcoc-cogs/master/mcoc/data/cdt_icon.png'
    # icon_sdf = 'https://raw.githubusercontent.com/JasonJW/mcoc-cogs/master/mcoc/data/sdf_icon.png'
    # dataset = 'data/mcoc/masteries.csv'

    # def present(self, lookup):
    #     em = discord.Embed(color=self.mcolor, title='', description=lookup[1])
    #     print(len(lookup))
    #     if len(lookup) > 2:
    #         em.set_footer(text=lookup[2], icon_url=lookup[3])
    #     else:
    #         em.set_footer(text='CollectorDevTeam', icon_url=COLLECTOR_ICON)
    #     return em

    @commands.command(pass_context=True, name='collectormap', hidden=True)
    async def _collectormap(self, ctx):
        buildlist = {}
        servers = self.bot.servers
        print('server inventory')
        for server in servers:
            print(server.id)
            print('member inventory')
            members = []
            for member in server.members:
                if member.bot is False:
                    members.append(member.id)
            buildlist.update({server.id: members})

        dataIO.save_json('data/mcocTools/collectormap.json', buildlist)
        await self.bot.upload('data/mcocTools/collectormap.json')

    @commands.command(pass_context=True, name='calendar', aliases=('events',))
    async def _calendar(self, ctx, force=False):
        PUBLISHED = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vT5A1MOwm3CvOGjn7fMvYaiTKDuIdvKMnH5XHRcgzi3eqLikm9SdwfkrSuilnZ1VQt8aSfAFJzZ02zM/pubhtml?gid=390226786'
        author = ctx.message.author
        now = datetime.datetime.now().date()
        gsh = GSHandler(self.bot)
        gsh.register_gsheet(
            name='calendar',
            gkey='1a-gA4FCaChByM1oMoRn8mI3wx8BsHAJGlU0kbY9gQLE',
            local='data/mcocTools/calendar.json',
            sheet_name='collector_export',
            range_name='collector_export'
        )
        if force:
            await gsh.cache_gsheets('calendar')
        if self.calendar_url == '' or self.mcoctools['calendar_date'] != now or force:
            self.screenshot = ScreenShot(self.bot)
            self.calendar_url = await self.screenshot.get_screenshot(PUBLISHED, w=1700, h=800)
            self.mcoctools['calendar'] = self.calendar_url
            self.mcoctools['calendar_date'] = now
            # dataIO.save_json('data/mcocTools/mcoctools.json', self.mcoctools)
        ssurl = self.calendar_url
        mcoc = self.bot.get_cog('MCOC')
        filetime = datetime.datetime.fromtimestamp(
            os.path.getctime('data/mcocTools/calendar.json'))
        if os.path.exists('data/mcocTools/calendar.json'):
            if filetime.date() != now:
                await gsh.cache_gsheets('calendar')
        else:
            await gsh.cache_gsheets('calendar')
        calendar = dataIO.load_json('data/mcocTools/calendar.json')
        ucolor = discord.Color.gold()
        if ctx.message.channel.is_private is False:
            ucolor = author.color
        pages = []
        for start in range(1, 10):
            data = discord.Embed(
                color=ucolor, title='CollectorDevTeam | MCOC Schedule', url=PUBLISHED)
            data.set_thumbnail(url=COLLECTOR_FEATURED)
            data.set_footer(text='Requested by {}'.format(
                author.display_name), icon_url=author.avatar_url)
            data.set_image(url=ssurl)
            for i in range(start, start+2):
                i = str(i)
                if i == '3':
                    name = 'Today, {}'.format(calendar[i]['date'])
                elif i == '4':
                    name = 'Tomorrow, {}'.format(calendar[i]['date'])
                else:
                    name = '{}, {}'.format(
                        calendar[i]['day'], calendar[i]['date'])
                package = ''
                if calendar[i]['feature'] == 'Crystal':
                    package += 'Arena: Crystal Cornucopia\n'
                elif calendar[i]['feature'] != "?" and calendar[i]['feature'] != "Crystal":
                    try:
                        if mcoc is not None:
                            feature = await mcoc.get_champion(calendar[i]['feature'])
                            package += '__Arena__\n' \
                                'Feature: 4★ & 5★ {0}\n'.format(
                                    feature.full_name)
                            data.set_thumbnail(url=feature.get_featured())
                    except:
                        package += '__Arena__\n' \
                                   'Feature: {0}\n'.format(
                                       calendar[i]['feature'])
                    try:
                        if mcoc is not None:
                            basic = await mcoc.get_champion(calendar[i]['basic'])
                            package += 'Basic:   4☆ {0.full_name}\n\n'.format(
                                basic)
                    except:
                        'Basic:   4☆ {0.full_name}\n\n'.format(
                            calendar[i]['basic'])
                    # feature = await mcoc.get_champion(calendar[i]['feature'])

                # if calendar[i]['eq'] != '':
                #     package += 'Event Quest vn: {0}\n``/eq {0}``\n'.format(calendar[i]['eq'])
                # if calendar[i]['notes'] != '':
                #     package += 'Notes: {}\n'.format(calendar[i]['notes'])
                package += '__Alliance Events__\n1 Day : {}\n3 Day : {}\n'.format(
                    calendar[i]['1day'], calendar[i]['3day'])
                if calendar[i]['aq'] != 'off':
                    day = calendar[i]['aq']
                    package += 'Quest {}: On, Day {}\n'.format(
                        calendar[i]['aqseason'], day[-1:])
                else:
                    package += 'Quest: Off\n'
                package += 'War {}: {}'.format(
                    calendar[i]['awseason'], calendar[i]['aw'])
                data.add_field(name=name, value=package, inline=False)
            data.add_field(name='Link to MCOC Schedule',
                           value='[MCOC Schedule by CollectorDevTeam]({})'.format(PUBLISHED), inline=False)
            pages.append(data)
        menu = PagesMenu(self.bot, timeout=120,
                         delete_onX=True, add_pageof=True)
        await menu.menu_start(pages=pages, page_number=2)
        # take a new ssurl after the fact
        if self.mcoctools['calendar_date'] != now:
            self.calendar_url = await ScreenShot.get_screenshot(self, url=PUBLISHED, w=1700, h=400)
            self.mcoctools['calendar'] = self.calendar_url
            self.mcoctools['calendar_date'] = now
            # dataIO.save_json('data/mcocTools/mcoctools.json', self.mcoctools)

    @commands.command(pass_context=True, name='commands', aliases=('dummies', 'dummy',))
    async def _command_images(self, ctx, name: str = None):
        ucolor = discord.Color.gold()
        author = ctx.message.author
        if ctx.message.channel.is_private is False:
            ucolor = author.color
        IMGBASE = 'https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/images/commands/'
        commands = ('admin', 'moderator', 'alliance', 'roster', 'champ')
        if name is not None and name.lower() in commands:
            data = discord.Embed(
                color=ucolor, title='Commands for Dummies', url=PATREON)
            data.set_image(url='{}{}1.png'.format(IMGBASE, name.lower()))
            data.set_footer(text='Requested by {}'.format(
                author.display_name), icon_url=author.avatar_url)
            data.set_author(name='CollectorDevTeam', icon_url=COLLECTOR_ICON)
            await self.bot.say(embed=data)
            return
        else:
            pages = []
            for i in commands:
                data = discord.Embed(
                    color=ucolor, title='Commands for Dummies', url=PATREON)
                data.set_image(url='{}{}1.png'.format(IMGBASE, i))
                data.set_footer(text='Requested by {}'.format(
                    author.display_name), icon_url=author.avatar_url)
                data.set_author(name='CollectorDevTeam',
                                icon_url=COLLECTOR_ICON)
                pages.append(data)
            menu = PagesMenu(self.bot, timeout=120,
                             delete_onX=True, add_pageof=True)
            await menu.menu_start(pages=pages, page_number=0)

    @commands.command(pass_context=True, name='cutoffs')
    async def _cutoffs(self, ctx, champ=None):
        """Cutoff results sourced from ArenaResultsKnight on the r/ContestOfChammpions subreddit."""
        # PUBLISHED = 'https://docs.google.com/spreadsheets/d/15F7_kKpiudp3FJu_poQohkWlCRi1CSylQOdGoyuVqSE/pubhtml'
        PUBLISHED = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vQPCDFUfBDv66g9ngxeQebfiu-rNUK377tYj_VZ5byu6sznShTBF3c7AlFF5IbWV3V4bc5qMu6PPDwl/pubhtml?gid=1281713249&single=true'
        author = ctx.message.author
        if ctx.message.channel.is_private is False:
            ucolor = author.color
        else:
            ucolor = discord.Color.gold()
        thumbnail = COLLECTOR_FEATURED
        prize = "Champ"
        if champ is not None:
            mcoc = self.bot.get_cog('MCOC')
            try:
                champ = await mcoc.get_champion(champ.lower())
                thumbnail = champ.get_featured()
                prize = champ.collectoremoji
            except:
                champ = None
                await self.bot.say('Not a valid champion.')
        now = datetime.datetime.now().date()
        gsh = GSHandler(self.bot)
        gsh.register_gsheet(
            name='cutoffs',
            gkey='15F7_kKpiudp3FJu_poQohkWlCRi1CSylQOdGoyuVqSE',
            local='data/mcocTools/cutoffs.json',
            sheet_name='export',
            range_name='export'
        )
        gsh.register_gsheet(
            name='summarystats',
            gkey='15F7_kKpiudp3FJu_poQohkWlCRi1CSylQOdGoyuVqSE',
            local='data/mcocTools/summarystats.json',
            sheet_name='stats',
            range_name='summarystats'
        )
        delay = CDTEmbed.create(self, ctx,
                                title="Retrieving Cutoff Data", description="Please wait whilst I interrogate the ArenaResultsKnight dataset.", image=COLLECTOR_CRYSTAL)
        pleasewait = await self.bot.send_message(ctx.message.channel, embed=delay)
        if self.mcoctools['cutoffs_date'] != now:
            await gsh.cache_gsheets('cutoffs')
            await gsh.cache_gsheets('summarystats')
            # self.mcoctools['cutoffs'] = await ScreenShot.get_screenshot(self, url=PUBLISHED, w=1440, h=900)
            self.mcoctools['cutoffs_date'] = now
            self.cutoffs = dataIO.load_json('data/mcocTools/cutoffs.json')
            self.summarystats = dataIO.load_json(
                'data/mcocTools/summarystats.json')
            desc = []
            for k in range(1, int(self.cutoffs["1"]["max"])):
                desc.append("{} {} {} {} [{}]\n".format(self.cutoffs[str(k)]["date"], self.cutoffs[str(k)]["contest"],
                                                        self.cutoffs[str(k)]["champ"], self.cutoffs[str(k)]["cutoff"], self.cutoffs[str(k)]["bracket1"]))
            # load the full dataset into a default arena description file.
            self.arena = ''.join(desc)
        delay.title = "Formatting ArenaResultsKnight dataset"
        delay.description = "Please wait. Dataset is being prepared."
        pleasewait = await self.bot.edit_message(pleasewait, embed=delay)

        description = self.arena
        if champ is not None:
            # If there is a champion, parse the cutoffs for that Champion.
            desc = []
            for k in range(1, int(self.cutoffs["1"]["max"])):
                if self.cutoffs[str(k)]["champ"] == champ.full_name:
                    desc.append("{} {} {} {} [{}]\n".format(self.cutoffs[str(k)]["date"], self.cutoffs[str(k)]["contest"],
                                                            self.cutoffs[str(k)]["champ"], self.cutoffs[str(k)]["cutoff"], self.cutoffs[str(k)]["bracket1"]))
                    description = ''.join(desc)

        arena_pages = chat.pagify(description, page_length=500)
        filetime = datetime.datetime.fromtimestamp(
            os.path.getctime('data/mcocTools/cutoffs.json'))
        if os.path.exists('data/mcocTools/cutoffs.json'):
            if filetime.date() != datetime.datetime.now().date():
                await gsh.cache_gsheets('cutoffs')
        else:
            await gsh.cache_gsheets('cutoffs')

        pages = []

        feature5cutoff = '```N Min {} | Avg {} | Max {}\nR Min {} | Avg {} | Max {}```'\
            .format(self.summarystats["5FNcutoff"]["min"], self.summarystats["5FNcutoff"]["average"],
                    self.summarystats["5FNcutoff"]["max"], self.summarystats["5FRcutoff"]["min"],
                    self.summarystats["5FRcutoff"]["average"], self.summarystats["5FRcutoff"]["max"])
        feature4cutoff = '```N Min {} | Avg {} | Max {}\nR Min {} | Avg {} | Max {}```'\
            .format(self.summarystats["4FNcutoff"]["min"], self.summarystats["4FNcutoff"]["average"],
                    self.summarystats["4FNcutoff"]["max"], self.summarystats["4FRcutoff"]["min"],
                    self.summarystats["4FRcutoff"]["average"], self.summarystats["4FRcutoff"]["max"])
        basic4cutoff = '```R Min {} | Avg {} | Max {}```'\
            .format(self.summarystats["4BRcutoff"]["min"],
                    self.summarystats["4BRcutoff"]["average"], self.summarystats["4BRcutoff"]["max"])
        feature5bracket2 = '```N Min {} | Avg {} | Max {}\nR Min {} | Avg {} | Max {}```'\
            .format(self.summarystats["5FNbracket2"]["min"], self.summarystats["5FNbracket2"]["average"],
                    self.summarystats["5FNbracket2"]["max"], self.summarystats["5FRbracket2"]["min"],
                    self.summarystats["5FRbracket2"]["average"], self.summarystats["5FRbracket2"]["max"])
        feature4bracket2 = '```N Min {} | Avg {} | Max {}\nR Min {} | Avg {} | Max {}```'\
            .format(self.summarystats["4FNbracket2"]["min"], self.summarystats["4FNbracket2"]["average"],
                    self.summarystats["4FNbracket2"]["max"], self.summarystats["4FRbracket2"]["min"],
                    self.summarystats["4FRbracket2"]["average"], self.summarystats["4FRbracket2"]["max"])
        basic4bracket2 = '```R Min {} | Avg {} | Max {}```'\
            .format(self.summarystats["4BRbracket2"]["min"],
                    self.summarystats["4BRbracket2"]["average"], self.summarystats["4BRbracket2"]["max"])
        cutoffstats = '{}\n{}\n{}'.format(
            feature5cutoff, feature4cutoff, basic4cutoff)
        bracketstats = '{}\n{}\n{}'.format(
            feature5bracket2, feature4bracket2, basic4bracket2)

        pred = "date contest champ cutoff [bracket]\n"
        for d in arena_pages:
            data = discord.Embed(color=ucolor, title='Arena Cutoffs [Link to Graph]', url=PUBLISHED,
                                 description=chat.box(pred+d))
            data.add_field(name="90-Day Summary Statistics",
                           value="The following fields contain ``Min | Average | Max`` breakouts for [N]ew and [R]erun champions over the last 90 days.", inline=False)
            data.add_field(name="Feature 5★ Top 150 = {} + {}".format(
                prize, self.summarystats["5FRcutoff"]["prize"]), value=feature5cutoff, inline=False)
            data.add_field(name="Feature 5★ Top 10% = {}".format(
                self.summarystats["5FRbracket2"]["prize"]), value=feature5bracket2, inline=False)
            data.add_field(name="Feature 4★ Top 800 = {} + {}".format(
                prize, self.summarystats["4FRcutoff"]["prize"]), value=feature4cutoff, inline=False)
            data.add_field(name="Feature 4★ Top 10% = {}".format(
                self.summarystats["4FNbracket2"]["prize"]), value=feature4bracket2, inline=False)
            data.add_field(name="Basic 4★ Top 10% = {} + {}".format(
                prize, self.summarystats["4BRcutoff"]["prize"]), value=basic4cutoff, inline=False)
            data.add_field(name="Basic 4★ 11-25% = {}".format(
                self.summarystats["4BRbracket2"]["prize"]), value=basic4bracket2, inline=False)

            # data.add_field(name='90 Days Cutoff Stats', value=cutoffstats, inline=False)
            # data.add_field(name='90 Days Bracket 2 Stats', value=bracketstats, inline=False)
            data.set_author(
                name='CollectorDevTeam + ArenaResultsKnight', icon_url=COLLECTOR_ICON)
            data.set_footer(text='Requested by {}'.format(
                author.display_name), icon_url=author.avatar_url)
            # data.set_image(url=self.mcoctools['cutoffs'])
            data.set_thumbnail(url=thumbnail)
            pages.append(data)
        if len(pages) > 0:
            await self.bot.delete_message(pleasewait)
            menu = PagesMenu(self.bot, timeout=120,
                             delete_onX=True, add_pageof=True)
            await menu.menu_start(pages=pages)
        if self.mcoctools['cutoffs_date'] != now:
            # self.mcoctools['cutoffs'] = await ScreenShot.get_screenshot(self, url=PUBLISHED, w=1440, h=900)
            # self.mcoctools['cutoffs'] = self.mcoctools['cutoffs']
            self.mcoctools['cutoffs_date'] = now

    @commands.command(pass_context=True, no_pm=True)
    async def topic(self, ctx, channel: discord.Channel = None):
        """Play the Channel Topic in the chat channel."""
        if channel is None:
            channel = ctx.message.channel
        topic = channel.topic
        if topic is not None and topic != '':
            data = discord.Embed(color=ctx.message.author.color,
                                 title='#{} Topic :sparkles:'.format(
                                     channel.name),
                                 description=topic)
            data.set_thumbnail(url=ctx.message.server.icon_url)
            data.set_footer(text='CollectorDevTeam', icon_url=COLLECTOR_ICON)
            await self.bot.say(embed=data)

    #
    @commands.command(pass_context=True, aliases={'collector', 'infocollector', 'about'})
    async def aboutcollector(self, ctx):
        """Shows info about Collector"""
        author = ctx.message.author
        if ctx.message.channel.is_private:
            ucolor = discord.Color.gold()
        else:
            ucolor = author.color
        # user lists from CDT
        cdt = self.bot.get_server("215271081517383682")
        cdtdevteam = self._get_role(cdt, "390253643330355200")
        cdtpatrons = self._get_role(cdt, "428627905233420288")
        cdtsupport = self._get_role(cdt, "390253719125622807")
        cdtpartners = self._get_role(cdt, "390253856182894593")
        cdtmaps = self._get_role(cdt, "553407585743536150")
        devteam = ', '.join(self._get_members(cdt, cdtdevteam))
        support = ', '.join(self._get_members(cdt, cdtsupport))
        partners = ', '.join(self._get_members(cdt, cdtpartners))
        mappers = ', '.join(self._get_members(cdt, cdtmaps))
        if self._get_members(cdt, cdtpatrons) is not None:
            patrons = ', '.join(self._get_members(cdt, cdtpatrons))
            patrons += ', Caitibee, Fabio F., Vajda R.'
        else:
            patrons = "[Become a CollectorBot patron today!](https://patreon.com/collectorbot)"

        author_repo = "https://github.com/Twentysix26"
        red_repo = author_repo + "/Red-DiscordBot"
        server_url = "https://discord.gg/wJqpYGS"
        dpy_repo = "https://github.com/Rapptz/discord.py"
        python_url = "https://www.python.org/"
        collectorpatreon = 'https://patreon.com/collectorbot'
        since = datetime.datetime(2016, 1, 2, 0, 0)
        days_since = (datetime.datetime.utcnow() - since).days
        dpy_version = "[{}]({})".format(discord.__version__, dpy_repo)
        py_version = "[{}.{}.{}]({})".format(*os.sys.version_info[:3],
                                             python_url)

        owner_set = self.bot.settings.owner is not None
        owner = self.bot.settings.owner if owner_set else None
        if owner:
            owner = discord.utils.get(self.bot.get_all_members(), id=owner)
            if not owner:
                try:
                    owner = await self.bot.get_user_info(self.bot.settings.owner)
                except:
                    owner = None
        if not owner:
            owner = "Unknown"

        about = (
            "Collector is an instance of [Red, an open source Discord bot]({0}) "
            "created by [Twentysix]({1}) and improved by many.\n\n"
            "The Collector Dev Team is backed by a passionate community who contributes and "
            "creates content for everyone to enjoy. [Join us today]({2}) "
            "and help us improve!\n\n"
            "★ If you would like to support the Collector, please visit {3}.\n"
            "★ Patrons and Collaborators receive priority support and secrety stuff.\n\n~ JJW"
            "".format(red_repo, author_repo, server_url, collectorpatreon))
        # devteam = ("DeltaSigma#8530\n"
        #            "JJW#8071\n"
        #            "JM#7725"
        #            )
        supportteam = support
        # supportteam = ('phil_wo#3733\nSpiderSebas#9910\nsuprmatt#2753\ntaoness#5565')
        embed = discord.Embed(
            colour=ucolor, title="Collector", url=collectorpatreon)
        embed.add_field(name="Patrons", value=patrons, inline=True)
        embed.add_field(name="Instance owned by", value=str(owner))
        embed.add_field(name="Python", value=py_version)
        embed.add_field(name="discord.py", value=dpy_version)
        embed.add_field(name="About", value=about, inline=False)
        embed.add_field(name="PrestigePartners",
                        value='Kelldor#3162\nmutamatt#4704', inline=True)
        # embed.add_field(name='DuelsPartners', value='ƦƆ51#4587', inline=True)
        embed.add_field(name='MapsPartners',
                        value=mappers, inline=True)
        # embed.add_field(name='LabyrinthTeam',
        #                 value='Kiryu#5755\nre-1#7595', inline=True)
        embed.add_field(name='Collector Partners', value=partners, inline=True)
        embed.add_field(name='CollectorSupportTeam',
                        value=supportteam, inline=True)
        embed.add_field(name="CollectorDevTeam", value=devteam, inline=True)
        embed.set_footer(text="Bringing joy since 02 Jan 2016 (over "
                              "{} days ago!)".format(days_since))

        try:
            await self.bot.say(embed=embed)
        except discord.HTTPException:
            await self.bot.say("I need the `Embed links` permission "
                               "to send this")

    def _get_role(self, server, role_key: str):
        """Returns discord.Role"""
        for role in server.roles:
            if role.id == role_key:
                return role
        return None

    def _get_members(self, server, role):
        """Returns list of discord.server.members"""
        members = []
        for m in server.members:
            if role in m.roles:
                members.append('{}'.format(m.display_name))
        if len(members) > 0:
            return members
        else:
            return None
    #
    # @commands.command(help=lookup_links['event'][0], aliases=['events', 'schedule', ], hidden=True)
    # async def event(self):
    #     x = 'event'
    #     lookup = self.lookup_links[x]
    #     await self.bot.say(embed=self.present(lookup))
    #     # await self.bot.say('iOS dumblink:\n{}'.format(lookup[0]))
    #
    # @commands.command(help=lookup_links['spotlight'][0], )
    # async def spotlight(self):
    #     """CollectorDevTeam Spotlight Dataset"""
    #     x = 'spotlight'
    #     lookup = self.lookup_links[x]
    #     await self.bot.say(embed=self.present(lookup))
    #     # await self.bot.say('iOS dumblink:\n{}'.format(lookup[0]))
    #
    # @commands.command(help=lookup_links['rttl'][0], )
    # async def rttl(self):
    #     x = 'rttl'
    #     lookup = self.lookup_links[x]
    #     await self.bot.say(embed=self.present(lookup))
    #     # await self.bot.say('iOS dumblink:\n{}'.format(lookup[0]))
    #
    # @commands.command(help=lookup_links['alsciende'][0], aliases=('mrig',), hidden=True)
    # async def alsciende(self):
    #     x = 'alsciende'
    #     lookup = self.lookup_links[x]
    #     await self.bot.say(embed=self.present(lookup))
    #     # await self.bot.say('iOS dumblink:\n{}'.format(lookup[0]))
    #
    # @commands.command(help=lookup_links['hook'][0], hidden=True)
    # async def hook(self):
    #     x = 'hook'
    #     lookup = self.lookup_links[x]
    #     await self.bot.say(embed=self.present(lookup))
    #     # await self.bot.say('iOS dumblink:\n{}'.format(lookup[0]))

    @commands.command(hidden=True, pass_context=True, aliases=('parse_search', 'ps', 'dm', 'km',))
    async def kabam_search(self, ctx, *, phrase: str):
        """Enter a search term or a JSON key
        k: <term> | search in Keys
        vn: <int> | search for version numbers
        Use pipe "|" to chain terms
        """
        author = ctx.message.author
        if ctx.message.channel.is_private:
            ucolor = discord.Color.gold()
        else:
            ucolor = author.color
        kdata = StaticGameData()
        cdt_data, cdt_versions = kdata.cdt_data, kdata.cdt_versions
        result = self.search_parser.parse_string(phrase)
        print(result.elements)
        matches = result.match(cdt_data, cdt_versions)
        # print(matches)
        if len(matches) == 0:
            await self.bot.say('**Search resulted in 0 matches**')
            return
        package = []
        for k in sorted(matches):
            if k in cdt_versions:
                ver = '\nvn: {}'.format(cdt_versions[k])
            else:
                ver = ''
            package.append('\n**{}**\n{}{}'.format(
                k, self._bcg_recompile(cdt_data[k]), ver))
        pages = chat.pagify('\n'.join(package))
        page_list = []
        for page in pages:
            em = discord.Embed(title='Data Search',
                               description=page, color=ucolor)
            em.set_author(name='CollectorDevTeam', icon_url=COLLECTOR_ICON)
            em.set_footer(text='MCOC Game Files | requested by {}'.format(
                author.display_name), icon_url=KABAM_ICON)
            page_list.append(em)
        menu = PagesMenu(self.bot, timeout=120,
                         delete_onX=True, add_pageof=True)
        await menu.menu_start(page_list)

    def _bcg_recompile(self, str_data):
        hex_re = re.compile(r'\[[0-9a-f]{6,8}\](.+?)\[-\]', re.I)
        return hex_re.sub(r'\1', str_data)

    async def cache_sgd_gsheets(self):
        sgd = StaticGameData()
        await sgd.cache_gsheets()

    @commands.command(hidden=True)
    async def aux_sheets(self):
        await self.cache_sgd_gsheets()

    @commands.command(hidden=True, pass_context=True)
    async def get_file(self, ctx, *, filename: str):
        if check_collectordevteam(self, ctx) is False:
            return
        elif filename is 'mcoc_service_creds':
            return
        elif dataIO.is_valid_json('data/mcoc/{}.json'.format(filename)) is True:
            await self.bot.send_file(ctx.message.channel, 'data/mcoc/{}.json'.format(filename))
            return
        elif dataIO.is_valid_json('data/hook/{}/champs.json'.format(filename)) is True:
            await self.bot.send_file(ctx.message.channel, 'data/hook/{}/champs.json'.format(filename))
            return
        elif dataIO.is_valid_json('data/account/{}.json'.format(filename)) is True:
            await self.bot.send_file(ctx.message.channel, 'data/account/{}.json'.format(filename))
            return
        elif dataIO.is_valid_json(filename) is True:
            await self.bot.send_file(ctx.message.channel, filename)
            return
        else:
            await self.bot.say('I could not find that file.')


def check_collectordevteam(self, ctx):
    cdtid = '390253643330355200'
    cdtserver = self.bot.get_server('215271081517383682')
    for member in cdtserver.members:
        if member.id == ctx.message.author.id:
            author = member
            continue

    for role in author.roles:
        if role.id == cdtid:
            return True
    return False


def check_collectorsupportteam(self, ctx):
    cstid = '390253719125622807'
    cdtid = '390253643330355200'
    cdtserver = self.bot.get_server('215271081517383682')
    for member in cdtserver.members:
        if member.id == ctx.message.author.id:
            author = member
            continue

    for role in author.roles:
        if role.id == cstid or role.id == cdtid:
            return True
    return False


class MCOCEvents:
    def __init__(self, bot):
        self.bot = bot
        self.gsheet_handler = GSHandler(bot, gapi_service_creds)
        self.gsheet_handler.register_gsheet(
            name='event_data',
            gkey='1TSmQOTXz0-jIVgyuFRoaPCUZA73t02INTYoXNgrI5y4',
            local='data/mcocTools/sgd_event_data.json',
            sheet_name='event_trans',
        )
        self.event_data = None

    @commands.command(name='trials', pass_context=True, aliases=('trial',), hidden=False)
    async def _trials(self, ctx, trial, tier='epic'):
        """Elements of the Trials
        trials   | tier
        Wind     | easy
        Fire     | medium
        Earth    | hard
        Darkness | expert
        Water    | epic
        Light
        Alchemist"""
        author = ctx.message.author
        trial = trial.lower()
        tier = tier.lower()
        tiers = ('easy', 'medium', 'hard', 'expert', 'epic')
        sgd = StaticGameData()
        # sgd = self.sgd
        cdt_trials = await sgd.get_gsheets_data('elemental_trials')
        trials = set(cdt_trials.keys()) - {'_headers'}

        if trial not in trials:
            em = discord.Embed(color=discord.Color.red(), title='Trials Error',
                               description="Invalid trial '{}'".format(trial))
            em.add_field(name='Valid Trials:', value='\n'.join(trials))
            await self.bot.say(embed=em)
        elif tier not in tiers:
            em = discord.Embed(color=discord.Color.red(), title='Trials Error',
                               description="Invalid tier '{}'".format(tier))
            em.add_field(name='Valid Tiers:', value='\n'.join(tiers))
            await self.bot.say(embed=em)
        else:
            em = discord.Embed(
                color=CDT_COLORS[tier],
                title=tier.title() + " " + cdt_trials[trial]['name'],
                description='',
                url='https://forums.playcontestofchampions.com/en/discussion/114604/take-on-the-trials-of-the-elementals/p1'
            )
            em.add_field(name='Champions', value=cdt_trials[trial]['champs'])
            em.add_field(name='Boosts', value=cdt_trials[trial][tier])
            if trial == 'alchemist':
                em.add_field(name=cdt_trials['alchemistrewards']['name'],
                             value=cdt_trials['alchemistrewards'][tier])
            else:
                em.add_field(name=cdt_trials['rewards']['name'],
                             value=cdt_trials['rewards'][tier])
            em.set_author(name='CollectorDevTeam',
                          icon_url=COLLECTOR_ICON)
            em.set_footer(text='Requested by {}'.format(
                author.display_name), icon_url=author.avatar_url)
            await self.bot.say(embed=em)

    ### BEGIN EVENTQUEST GROUP ###

    @commands.group(pass_context=True, aliases=('eq', 'event'), hidden=False)
    async def eventquest(self, ctx, eq: str, tier=None):
        author = ctx.message.author
        if ctx.message.channel.is_private:
            ucolor = discord.Color.gold()
        else:
            ucolor = ctx.message.author.color
        valid = False
        if self.event_data is None:
            if os.path.exists('data/mcoc/event_data.json'):
                now = datetime.datetime.now().date()
                filetime = datetime.datetime.fromtimestamp(
                    os.path.getctime('data/mcoc/event_data.json'))
                if filetime.date() == now:
                    self.event_data = dataIO.load_json(
                        'data/mcoc/event_data.json')
                else:
                    await self.gsheet_handler.cache_gsheets('event_data')
                    self.event_data = dataIO.load_json(
                        'data/mcoc/event_data.json')
        if eq in self.event_data.keys():
            valid = True
        elif eq not in self.event_data.keys():
            # eqchamp = mcoc.ChampionConverter.convert(eq)
            await self.gsheet_handler.cache_gsheets('event_data')
            self.event_data = dataIO.load_json('data/mcoc/event_data.json')
            if eq not in self.event_data.keys():
                data = discord.Embed(color=ucolor, title='Event Quest Help',
                                     description='Please choose a valid Event Quest version number:\n')
                # eqs = OrderedDict([(i, self.event_data[i]['event_title']) for i in self.event_data.keys()
                eqs = []
                for k in self.event_data.keys():
                    eqs.append(k)
                eqs.sort()
                for k in eqs:
                    if k is not None:
                        try:
                            data.description += '{} : {}\n'.format(
                                k, self.event_data[k]['event_title'])
                        except:
                            continue
                data.set_author(name='CollectorDevTeam',
                                icon_url=COLLECTOR_ICON)
                data.set_footer(text='Requested by {}'.format(
                    author.display_name), icon_url=author.avatar_url)
                await self.bot.say(embed=data)
                return
        #
        #
        # if os.path.exists('data/mcoc/event_data.json'):
        #     if self.event_data is None:
        #         self.event_data = dataIO.load_json('data/mcoc/event_data.json')
        # if self.event_data is not None:
        #     unique = self.event_data.keys()
        #     if eq in unique:
        #         valid = True
        #     elif "eq_"+eq in unique:
        #         eq = "eq_"+eq
        #         valid = True
        # if os.path.exists('data/mcoc/event_data.json'):
        #     now = datetime.now().date()
        #     # filetime = datetime.datetime.fromtimestamp(os.path.getctime('data/mcoc/tldr.json'))
        #     filetime = datetime.fromtimestamp(os.path.getctime('data/mcoc/event_data.json'))
        #     if filetime.date() != now or valid is False:
        #         await self.gsheet_handler.cache_gsheets('event_data')
        #         event_data = dataIO.load_json('data/mcoc/event_data.json')
        #         self.event_data = event_data
        #         unique = self.event_data.keys()
        # else:
        #     await self.gsheet_handler.cache_gsheets('event_data')
        #     event_data = dataIO.load_json('data/mcoc/event_data.json')
        #     self.event_data = event_data
        #     unique = self.event_data.keys()

        if valid is True:
            tiers = self.event_data[eq]['tiers'].split(", ")
            last = tiers[-1]
            if tier is not None and tier.lower() in tiers:
                last = tier.lower()
            await self.format_eventquest(event=eq, tier=last)

        # if ctx.invoked_subcommand is None:
        #     await send_cmd_help(ctx)

    # @eventquest.command(name='', aliases=(,))
    # async def eq_(self, tier='Master'):
    #     """TITLE"""
    #     event = 'eq_'
    #     await self.format_eventquest(event, tier.lower())

    # @eventquest.command(name='13', aliases=('guardians', 'yondu', 'nebula', 'guardiansvolzero',))
    # async def eq_guardiansvolzero(self, tier='Master'):
    #     """Guardians of the Galaxy Vol Zero"""
    #     event = 'eq_13'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='13.1', aliases=('secretempireforever', 'punisher2099', 'carnage', 'p99',))
    # async def eq_secretempireforever(self, tier='Master'):
    #     """Secret Empire Forever"""
    #     event = 'eq_13.1'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='14.1', aliases=('sinisterfoes', 'sinisterfoesofspiderman', 'vulture', 'sparky', 'smse',))
    # async def eq_sinisterfoes(self, tier='Master'):
    #     """Sinister Foes of Spider-Man"""
    #     event = 'eq_14.1'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='15', aliases=('haveyouseenthisdog', 'kingping', 'medusa', 'kp',))
    # async def eq_haveyouseenthisdog(self, tier='Master'):
    #     """Have You Seen This Dog?"""
    #     event = 'eq_15'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='15.1', aliases=('blades', 'blade', 'mephisto', 'morningstar',))
    # async def eq_blades(self, tier='Master'):
    #     """Blades"""
    #     event = 'eq_15.1'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='16', aliases=('thorragnarok', 'hela', 'tr', 'godsofthearena', 'godsofarena',))
    # async def eq_godsofthearena(self, tier='Master'):
    #     """Gods of the Arena"""
    #     event = 'eq_16'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='16.1', aliases=('hotelmodok', 'modok', 'taskmaster', 'tm',))
    # async def eq_hotelmodok(self, tier='Uncollected'):
    #     """Hotel M.O.D.O.K."""
    #     event = 'eq_16.1'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='17', aliases=('riseoftheblackpanther', 'hulkragnarok', 'killmonger', 'hr', 'km',))
    # async def eq_riseoftheblackpanther(self, tier='Uncollected'):
    #     """Rise of the Black Panther"""
    #     event = 'eq_17'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='17.1', aliases=('bishop', 'sabretooth', 'sentinel', 'savage', 'savagefuture',))
    # async def eq_savagefuture(self, tier='Uncollected'):
    #     """X-Men: Savage Future"""
    #     event = 'eq_17.1'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='17.2', aliases=(
    #         'chaos', 'infinitychaos', 'corvus', 'proximamidnight', 'pm', 'corvusglaive', 'cg', 'proxima',))
    # async def eq_infinitychaos(self, tier='Uncollected'):
    #     """Infinity Chaos"""
    #     event = 'eq_17.2'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='18', aliases=('infinity', 'capiw', 'imiw', 'infinitywar', 'iw',))
    # async def eq_infinitynightmare(self, tier='Uncollected'):
    #     """Infinity Nightmare"""
    #     event = 'eq_18'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='18.1',
    #                     aliases=('mercs', 'masacre', 'domino', 'goldpool', 'mercsformoney',))
    # async def eq_mercsforthemoney(self, tier='Uncollected'):
    #     """Masacre and the Mercs for Money"""
    #     event = 'eq_18.1'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='19', aliases=('wasp', 'ghost'))
    # async def eq_returntomicrorealm(self, tier='Uncollected'):
    #     """Return to the Micro-Realm"""
    #     event = 'eq_19'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='19.1', aliases=('cabal', 'enterthecabal', 'korg', 'redskull', 'heimdall',))
    # async def eq_enterthecabal(self, tier='Uncollected'):
    #     """Enter The Cabal"""
    #     event = 'eq_19.1'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='20', aliases=('omega', 'classomega', 'omegared', 'emma', 'emmafrost',))
    # async def eq_classomega(self, tier='Uncollected'):
    #     """X-Men: Class Omega"""
    #     event = 'eq_20'
    #     await self.format_eventquest(event, tier)
    #
    # @eventquest.command(name='20.1',
    #                     aliases=('symbiotes', 'symbiomancer', 'venomtheduck', 'symbiotesupreme'))
    # async def eq_symbiomancer(self, tier='Epic'):
    #     """Blood & Venom: Symbiomanncer"""
    #     event = 'eq_20.1'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='21',
    #                     aliases=('brawlinthebattlerealm', 'aegon', 'thechampion', 'brawl',))
    # async def eq_brawl(self, tier='Uncollected'):
    #     """Brawl in the Battlerealm"""
    #     event = 'eq_21'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='21.1', aliases=('nightriders', 'nightthrasher', 'darkhawk',))
    # async def eq_nightriders(self, tier='Uncollected'):
    #     """Night Riders"""
    #     event = 'eq_21.1'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='21.2', aliases=('monster', 'thismanthismonster', 'thing', 'diablo',))
    # async def eq_monster(self, tier='Uncollected'):
    #     """This Man... This Monster"""
    #     event = 'eq_21.2'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='21.3', aliases=('xenoclast', 'mrsinister', 'sinister', 'havok',))
    # async def eq_xenoclast(self, tier='Uncollected'):
    #     """X-Men Xenoclast"""
    #     event = 'eq_21.3'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='love3', aliases=('loveisabattlefield3',))
    # async def eq_love3(self, tier='Epic'):
    #     """Love is a Battlefield 3"""
    #     event = 'eq_love3'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='cmcc', aliases=('cmclash', 'captainmarvelclash',))
    # async def eq_cmcc(self, tier='Act'):
    #     """Captain Marvel\'s Combat Clash"""
    #     event = 'eq_cmcc'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='recon', aliases=('nickfuryrecon',))
    # async def eq_recon(self, tier='part1'):
    #     """Nick Fury's Recon Initiatives"""
    #     event = 'eq_recon'
    #     await self.format_eventquest(event, tier.lower(), rewards=False)
    #
    # @eventquest.command(name='negativezone', aliases=('nzbounties',))
    # async def eq_nzbounties(self, tier='Epic'):
    #     """Negative Zone Bounty Missions"""
    #     event = 'eq_nzbounties'
    #     await self.format_eventquest(event, tier.lower())
    #
    #
    # @eventquest.command(name='22', aliases=('secretinvasion','captainmarvel','nickfury','cm','nf',))
    # async def eq_22(self, tier='Uncollected'):
    #     """Battlerealm: Under Siege"""
    #     event = 'eq_22'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='22.1', aliases=('annihilus','humantorch',))
    # async def eq_livingdeath(self, tier='Uncollected'):
    #     """The Living Death Who Walks"""
    #     event = 'eq_22.1'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='23', aliases=('ronin','ebonymay','cullobsidian','avengersforever',))
    # async def eq_avengersforever(self, tier='Uncollected'):
    #     """AVENGERS FOREVER"""
    #     event = 'eq_23'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='23.1', aliases=('namor','invisiblewoman',))
    # async def eq_imperiusrex(self, tier='Uncollected'):
    #     """IMPERIUS REX"""
    #     event = 'eq_23.1'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='classtrip', aliases=())
    # async def eq_classtrip(self, tier='Epic'):
    #     """Time to Take A Class Trip"""
    #     event = 'eq_classtrip'
    #     await self.format_eventquest(event, tier.lower())
    #
    # @eventquest.command(name='24', aliases=('phantasmagoria','mysterio','spidermanstealth','smss',))
    # async def eq_phantasmagoria(self, tier='Uncollected'):
    #     """Phantasmagoria"""
    #     event = 'eq_24'
    #     await self.format_eventquest(event, tier.lower())

    # @eventquest.command(name='', aliases=(,))
    # async def eq_(self, tier='Uncollected'):
    #     """TITLE"""
    #     event = 'eq_'
    #     await self.format_eventquest(event, tier.lower())

    @commands.command(name='variant', hidden=False)
    async def eq_variant(self, chapter: str):
        """Variant Quest
        1.1 : Dark Portents
        1.2 : A Villain Revealed
        1.3 : The Collector's Task
        2.1 : Ultron Strikes
        2.2 : Drone Duel
        2.3 : The Avengers
        3.1 : The Campaign
        3.2 : Heroes Arise
        3.3 : Avengers Assemble
        """

        sgd = StaticGameData()
        vq = await sgd.get_gsheets_data('variant')
        chapters = ('1.1', '1.2', '1.3', '2.1',
                    '2.2', '2.3', '3.1', '3.2', '3.3')
        valid = ['1.1A', '1.1B', '1.1C', '1.1D', '1.1E', '1.1F', '1.1Boss', '1.2A', '1.2B', '1.2C', '1.2D', '1.2E',
                 '1.2Boss', '1.3A', '1.3B', '1.3C', '1.3D', '1.3E', '1.3Boss', '2.1A', '2.1B', '2.1C', '2.1D', '2.1E',
                 '2.1F', '2.1Boss', '2.2A', '2.2B', '2.2C', '2.2D', '2.2Boss', '2.3A', '2.3B', '2.3C', '2.3D', '2.3E',
                 '2.3F', '2.3Boss', '3.1A', '3.1B', '3.1C', '3.1D', '3.1E', '3.1F', '3.1Boss', '3.2A', '3.2B', '3.2C',
                 '3.2D', '3.2E', '3.2F', '3.2Boss', '3.3A', '3.3B', '3.3C', '3.3D', '3.3E', '3.3F', '3.3Boss']
        if chapter not in chapters and chapter not in valid:
            return
        elif chapter in valid:
            v = vq[chapter]
            data = discord.Embed(color=discord.Color.gold(), title=v['title'])
            data.set_footer(text='CollectorDevTeam + ƦƆ51',
                            icon_url=COLLECTOR_ICON)
            if 'imageurl' in v:
                data.set_image(url=v['imageurl'])
                data.url = v['imageurl']
            if 'comments' in v:
                data.description = 'ƦƆ51 Coments:\n{}'.format(v['comments'])
            data.add_field(name='Fights', value=v['fights'])
            data.add_field(name='Boosts', value=v['boosts'])
            data.add_field(name='MVPs', value=v['mvps'])
            data.add_field(name='Alternatives', value=v['options'])
            data.add_field(name=v['af1_name'], value=v['af1_value'])

            await self.bot.say(embed=data)
            return
        else:
            page_number = valid.index(chapter + 'A')
            page_list = []
            for cp in valid:
                v = vq[cp]
                data = discord.Embed(
                    color=discord.Color.gold(), title=v['title'])
                data.set_footer(text='CollectorDevTeam + ƦƆ51',
                                icon_url=COLLECTOR_ICON)
                if 'imageurl' in v:
                    data.set_image(url=v['imageurl'])
                    data.url = v['imageurl']
                if 'comments' in v:
                    data.description = 'ƦƆ51 Coments:\n{}'.format(
                        v['comments'])
                data.add_field(name='Fights', value=v['fights'])
                data.add_field(name='Boosts', value=v['boosts'])
                data.add_field(name='MVPs', value=v['mvps'])
                data.add_field(name='Alternatives', value=v['options'])
                data.add_field(name=v['af1_name'], value=v['af1_value'])
                page_list.append(data)
            menu = PagesMenu(self.bot, timeout=120,
                             delete_onX=True, add_pageof=True)
            await menu.menu_start(page_list, page_number)

    # , tiers=('beginner','normal','heroic','master')):
    async def format_eventquest(self, event, tier, rewards=True):
        # sgd = StaticGameData()
        # sgd = self.sgd
        # cdt_eq = await sgd.get_gsheets_data(event)
        # rows = set(cdt_eq.keys()) - {'_headers'}
        # print(', '.join(rows))
        # tiers = cdt_eq['tiers']['value'].split(", ")
        # print(tiers)
        # cdt_eq = self.event_data[event].items()
        tiers = self.event_data[event]['tiers'].split(", ")
        if tier not in tiers:
            await self.bot.say('Invalid tier selection')
            return
        else:
            page_list = []
            page_number = list(tiers).index(tier)
            for row in tiers:
                if row in CDT_COLORS:
                    color = CDT_COLORS[row]
                else:
                    color = discord.Color.gold()
                em = discord.Embed(color=color, title=self.event_data[event]['event_title'].capitalize(),
                                   url=self.event_data[event]['event_url'])
                em.set_author(name=self.event_data[event]['date'])
                em.description = '{}\n\n{}'.format(
                    self.event_data[event]['story_title'].capitalize(), self.event_data[event]['story_value'])
                # em.add_field(name=cdt_eq['story_title']['value'], value=cdt_eq['story_value']['value'])
                if rewards:
                    em.add_field(name='{} Rewards'.format(
                        row.title()), value=self.event_data[event][row])
                else:
                    em.add_field(name='{}'.format(row.title()),
                                 value=self.event_data[event][row])
                if 'champions' in self.event_data[event] and 'value' in self.event_data[event]['champions'] != "":
                    em.add_field(name='Introducing',
                                 value=self.event_data[event]['champions'])
                em.set_image(url=self.event_data[event]['story_image'])
                em.set_footer(text='CollectorDevTeam', icon_url=COLLECTOR_ICON)
                page_list.append(em)

            menu = PagesMenu(self.bot, timeout=120,
                             delete_onX=True, add_pageof=True)
            await menu.menu_start(page_list, page_number)


class Calculator:
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, name='calculator', aliases=('calc',))
    async def _calc(self, context, *, m):
        """Math is fun!
        Type math, get fun."""
        print(m)
        m = ''.join(m)
        math_filter = re.findall(r'[\[\]\-()*+/0-9=.,% ]|>|<|==|>=|<=|\||&|~|!=|^|sum'
                                 + '|range|random|randint|choice|randrange|True|False|if|and|or|else'
                                 + '|is|not|for|in|acos|acosh|asin|asinh|atan|atan2|atanh|ceil'
                                 + '|copysign|cos|cosh|degrees|e|erf|erfc|exp|expm1|fabs|factorial'
                                 + '|floor|fmod|frexp|fsum|gamma|gcd|hypot|inf|isclose|isfinite'
                                 + '|isinf|isnan|ldexp|lgamma|log|log10|log1p|log2|modf|nan|pi'
                                 + '|pow|radians|sin|sinh|sqrt|tan|tanh|round', m)
        print(''.join(math_filter))
        calculate_stuff = eval(''.join(math_filter))
        if len(str(calculate_stuff)) > 0:
            em = discord.Embed(color=discord.Color.blue(),
                               description='**Input**\n`{}`\n\n**Result**\n`{}`'.format(m, calculate_stuff))
            await self.bot.say(embed=em)


class CDTGAPS:
    def __init__(self, bot):
        self.bot = bot

    @checks.admin_or_permissions(manage_server=True, manage_roles=True)
    @commands.command(name='gaps', pass_context=True, hidden=False, allow_pm=False)
    async def _alliance_popup(self, ctx, *args):
        """Guild | Alliance Popup System
        The Guild Alliance Pop System (G.A.P.S) allows you to configure your Discord server (guild) for alliance operations.
        Roles and channels are created: alliance, officers, bg1, bg2, bg3
        Channels and Server notifications settings are adjusted.
        """
        user = ctx.message.author
        warning_msg = ('The G.A.P.S. System will configure your server for basic Alliance Operations.\n'
                       'Roles will be added for summoners, alliance, officers, bg1, bg2, bg3\n'
                       'Channels will be added for announcements, alliance, & battlegroups.\n'
                       'Channel permissions will be configured.\n'
                       'After the G.A.P.S. system prepares your server, there will be additional instructions.\n'
                       'If you consent, press OK')
        em = discord.Embed(color=ctx.message.author.color,
                           title='G.A.P.S. Warning Message', description=warning_msg)
        em.set_author(
            name='CollectorDevTeam Guild Alliance Popup System', url=COLLECTOR_ICON)
        message = await self.bot.say(embed=em)
        await self.bot.add_reaction(message, '❌')
        await self.bot.add_reaction(message, '🆗')
        react = await self.bot.wait_for_reaction(message=message, user=ctx.message.author, timeout=30,
                                                 emoji=['❌', '🆗'])
        if react is not None:
            if react.reaction.emoji == '❌':
                await self.bot.say('G.A.P.S. canceled.')
                return
            elif react.reaction.emoji == '🆗':
                message2 = await self.bot.say('G.A.P.S. in progress.')
        else:
            await self.bot.say('Ambiguous response.  G.A.P.S. canceled')
            return

        server = ctx.message.server
        adminpermissions = discord.PermissionOverwrite(administrator=True)
        moderatorpermissions = discord.PermissionOverwrite(manage_roles=True)
        moderatorpermissions.manage_server = True
        moderatorpermissions.kick_members = True
        moderatorpermissions.ban_members = True
        moderatorpermissions.manage_channels = True
        moderatorpermissions.manage_server = True
        moderatorpermissions.manage_messages = True
        moderatorpermissions.view_audit_logs = True
        moderatorpermissions.read_messages = True
        moderatorpermissions.create_instant_invite = True

        roles = server.roles
        rolenames = []
        for r in roles:
            rolenames.append('{}'.format(r.name))
        aroles = ['officers', 'bg1', 'bg2', 'bg3', 'alliance', 'summoners']
        # message = await self.bot.say('Stage 1: Creating roles')
        if 'admin' not in rolenames:
            admin = await self.bot.create_role(server=server, name='admin', color=discord.Color.gold(), hoist=False,
                                               mentionable=False)

        if 'officers' not in rolenames:
            officers = await self.bot.create_role(server=server, name='officers', color=discord.Color.light_grey(),
                                                  hoist=False, mentionable=True)
        if 'bg1' not in rolenames:
            bg1 = await self.bot.create_role(server=server, name='bg1', color=discord.Color.blue(), hoist=False,
                                             mentionable=True)
        if 'bg2' not in rolenames:
            bg2 = await self.bot.create_role(server=server, name='bg2', color=discord.Color.purple(), hoist=False,
                                             mentionable=True)
        if 'bg3' not in rolenames:
            bg3 = await self.bot.create_role(server=server, name='bg3', color=discord.Color.orange(), hoist=False,
                                             mentionable=True)
        if 'alliance' not in rolenames:
            alliance = await self.bot.create_role(server=server, name='alliance', color=discord.Color.teal(),
                                                  hoist=True, mentionable=True)
        if 'summoners' not in rolenames:
            summoners = await self.bot.create_role(server=server, name='summoners', color=discord.Color.lighter_grey(),
                                                   hoist=True, mentionable=True)
        for r in server.roles:
            if r.name == 'officers':
                await self.bot.add_roles(user, r)
            elif r.name == 'alliance':
                await self.bot.add_roles(user, r)
        roles = sorted(
            server.roles, key=lambda roles: roles.position, reverse=True)
        em = discord.Embed(color=discord.Color.red(),
                           title='Guild Alliance Popup System', description='')
        positions = []
        for r in roles:
            positions.append('{} = {}'.format(r.position, r.mention))
            if r.name == 'officers':
                officers = r
            elif r.name == 'bg1':
                bg1 = r
            elif r.name == 'bg2':
                bg2 = r
            elif r.name == 'bg3':
                bg3 = r
            elif r.name == 'alliance':
                alliance = r
            elif r.name == 'summoners':
                summoners = r
            elif r.name == 'admin':
                admin = r
            elif r.name == 'everyone':
                everyone = r
        em.add_field(name='Stage 1 Role Creation',
                     value='\n'.join(positions), inline=False)
        await self.bot.say(embed=em)

        # everyone_perms = discord.PermissionOverwrite(read_messages=False)
        # everyoneperms = discord.ChannelPermissions(target=server.default_role, overwrite=discord.PermissionOverwrite(read_messages=True))
        # readperm = discord.PermissionOverwrite(read_messages=True)
        # officerperms = discord.ChannelPermissions(target=officers, overwrite=discord.PermissionOverwrite(read_messages=True))
        # allianceperms = discord.ChannelPermissions(target=alliance, overwrite=discord.PermissionOverwrite(read_messages=True))
        # summonerperms = discord.ChannelPermissions(target=summoners, overwrite=discord.PermissionOverwrite(read_messages=True))
        # bg1perms = discord.ChannelPermissions(target=bg1, overwrite=discord.PermissionOverwrite(read_messages=True))
        # bg2perms = discord.ChannelPermissions(target=bg2, overwrite=discord.PermissionOverwrite(read_messages=True))
        # bg3perms = discord.ChannelPermissions(target=bg3, overwrite=discord.PermissionOverwrite(read_messages=True))

        # channellist = []
        # for c in server.channels:
        #     channellist.append(c.name)
        # # if 'announcements' not in channellist:
        # #     await self.bot.create_channel(server, 'announcements', everyoneperms, allianceperms, summonerperms)
        # # if 'alliance' not in channellist:
        # #     await self.bot.create_channel(server, 'alliance', everyoneperms, allianceperms)
        # if 'alliance-chatter' not in channellist:
        #     await self.bot.create_channel(server, 'alliance-chatter', everyoneperms, allianceperms)
        # if 'officers' not in channellist:
        #     await self.bot.create_channel(server, 'officers', everyoneperms, officerperms)
        # if 'bg1aq' not in channellist:
        #     await self.bot.create_channel(server, 'bg1aq', everyoneperms, officerperms, bg1perms)
        # if 'bg1aw' not in channellist:
        #     await self.bot.create_channel(server, 'bg1aw', everyoneperms, officerperms, bg1perms)
        # if 'bg2aq' not in channellist:
        #     await self.bot.create_channel(server, 'bg2aq', everyoneperms, officerperms, bg2perms)
        # if 'bg2aw' not in channellist:
        #     await self.bot.create_channel(server, 'bg2aw', everyoneperms, officerperms, bg2perms)
        # if 'bg3aq' not in channellist:
        #     await self.bot.create_channel(server, 'bg3aq', everyoneperms, officerperms, bg3perms)
        # if 'bg3aw' not in channellist:
        #     await self.bot.create_channel(server, 'bg3aw', everyoneperms, officerperms, bg2perms)

        peveryone = discord.ChannelPermissions(
            target=server.default_role, overwrite=discord.PermissionOverwrite(read_messages=False))
        pofficers = discord.PermissionOverwrite(read_messages=True)
        pbg1 = discord.PermissionOverwrite(read_messages=True)
        pbg2 = discord.PermissionOverwrite(read_messages=True)
        pbg3 = discord.PermissionOverwrite(read_messages=True)
        palliance = discord.PermissionOverwrite(read_messages=True)
        channels = sorted(
            server.channels, key=lambda channels: channels.position, reverse=False)
        channelnames = []
        for c in channels:
            channelnames.append('{} = {} '.format(c.position, c.mention))
        em = discord.Embed(color=discord.Color.red(), title='Guild Alliance Popup System',
                           description='Automated channel creation is currently disabled.  '
                                       'JJ needs to rewrite channel.permissions.')

        # if len(channelnames) > 0:
        #     em.description=''
        em.add_field(name='Stage 2 Create Channels',
                     value='\n'.join(channelnames), inline=False)
        await self.bot.say(embed=em)

        em = discord.Embed(color=discord.Color.red(),
                           titel='Guild Alliance Popup System', descritpion='')

        fixNotifcations = await self.bot.say('Stage 3: Attempting to set Default Notification to Direct Message Only')
        try:
            # mentions only
            await self.bot.http.request(discord.http.Route('PATCH', '/guilds/{guild_id}', guild_id=server.id),
                                        json={'default_message_notifications': 1})
            em.add_field(name='Stage 3: Notification Settings',
                         value='I have modified the servers to use better notification settings.')
            await self.bot.delete_message(fixNotifcations)
        except Exception as e:
            await self.bot.edit_message(fixNotifcations, "An exception occurred. check your log.")

        await self.bot.say(embed=em)
        em = discord.Embed(color=ctx.message.author.color, titel='Guild Alliance Popup System',
                           descritpion='Server Owner Instructions')
        em.add_field(name='Enroll for Collector announcements',
                     value='Enroll a channel for Collector announcements\n```/addchan #announcements```\n',
                     inline=False)
        em.add_field(name='Set up Autorole',
                     value='Default Role should be {}\n```/autorole role summoners```\n```/autorole toggle``` '.format(
                         summoners.mention), inline=False)
        await self.bot.say(embed=em)
        await self.bot.delete_message(message2)
        try:
            alliance = self.bot.get_cog("Alliance")
            await alliance.register_alliance(ctx)
            return
        except:
            raise
            await self.bot.say("Now register your alliance:\n```/alliance register```")
            return

    # @checks.is_owner()

    @checks.admin_or_permissions(manage_roles=True)
    @commands.command(name='norole', pass_context=True, hidden=True)
    async def _no_role(self, ctx, role: discord.Role):
        members = ctx.message.server.members
        missing = []
        print(str(len(missing)))
        for member in members:
            if not member.bot:
                if role not in member.roles:
                    missing.append('{0.name} : {0.id}'.format(member))
        print(str(len(missing)))
        if len(missing) == 0:
            await self.bot.say('No users are missing the role: {}'.format(role.name))
        else:
            pages = chat.pagify('\n'.join(missing))
            for page in pages:
                await self.bot.say(chat.box(page))


class INSPECTOR:
    '''Guild inspector tool for Support Diagnostics'''

    def __init__(self, bot):
        self.bot = bot
        self.diagnostics = self.bot.get_channel('725478527969001483')
        self.cdtcheck = CDTCheck(self.bot)

    @commands.group(pass_context=True)
    async def inspect(self, ctx):
        '''CollectorVerse installation compliance utility
        Only for use by CollectorDevTeam and CollectorSupportTeam
        Or server Admin+'''
        author = ctx.message.author
        # if author.server_permissions.administrator or author is ctx.message.server.owner:
        #     print('server admin+')
        #     pass
        # el
        allowed = await self.cdtcheck.collectordevteam(ctx)

    @inspect.command(pass_context=True, name='check', hidden=True)
    async def _checker(self, ctx):
        test = await self.cdtcheck.collectordevteam(ctx)
        await self.bot.send_message('CDTCheck is {}'.format(test))

    @inspect.command(pass_context=True, name='server')
    async def _inspect_server(self, ctx, server_id=None):
        '''Inspect CollectorVerse server for Collector installation compliance'''
        data = CDTEmbed.create(
            self, ctx)
        data.title = 'CollectorDevTeam Inspection:sparkles:'
        if server_id is None:
            server = ctx.message.server
        else:
            try:
                server = self.bot.get_server(server_id)
            except:
                server = None

        if server is None:
            data.description = "Bad server id."
            data.add_field(name="Installation",
                           value='Collector is not installed.')
        else:
            data.set_author(
                name='Owner: {0.display_name} [{0.id}]'.format(server.owner))
            data.set_thumbnail(url=server.icon_url)
            data.add_field(name="Member Count", value=server.member_count)
            data.add_field(name="Installation",
                           value='Collector is installed.')
            data.add_field(name="Server Name", value=server.name)
            data.description = \
                '```Administrator:    {0.administrator}\n' \
                'Kick Members:     {0.kick_members}\n'\
                'Ban Members:      {0.ban_members}\n' \
                'Manage Channels:  {0.manage_channels}\n' \
                'Manage Messages:  {0.manage_messages}\n' \
                'Manage Nicknames: {0.manage_nicknames}\n' \
                'Manage Server:    {0.manage_server}\n' \
                'Manage Roles:     {0.manage_roles}\n' \
                'Read Messages:    {0.read_messages}\n' \
                'Send Messages:    {0.send_messages}\n' \
                'Add Reactions:    {0.add_reactions}\n' \
                'Embed Links:      {0.embed_links}\n' \
                'Attach Files:     {0.attach_files}\n' \
                'External Emoji:   {0.external_emojis}\n' \
                '```'.format(server.me.server_permissions)

        await self.bot.send_message(ctx.message.channel, embed=data)
        await self.bot.send_message(self.diagnostics, embed=data)

    @inspect.command(pass_context=True, name='roles', aliases=['role', 'ir', ])
    async def _inspect_roles(self, ctx, server_id=None):
        '''Inspect CollectoVerse server for role hierarchy compliance.'''
        if server_id is None:
            server = ctx.message.server
        else:
            try:
                server = self.bot.get_server(server_id)
            except:
                server = None
        data = CDTEmbed.create(
            self, ctx)
        data.title = 'CollectorDevTeam Inspector: ROLES:sparkles:'
        if server is not None:
            roles = sorted(
                server.roles, key=lambda roles: roles.position, reverse=True)
            positions = []
            for r in roles:
                positions.append('{} = {}'.format(r.position, r.name))
            data.description = '\n'.join(positions)
            data.set_author(
                name='Owner: {0.display_name} [{0.id}]'.format(server.owner))
            data.set_thumbnail(url=server.icon_url)
        else:
            data.description = 'Invalid server id'
        await self.bot.send_message(ctx.message.channel, embed=data)
        await self.bot.send_message(self.diagnostics, embed=data)

    @inspect.command(pass_context=True, name='user')
    async def inspect_user(self, ctx, user: discord.User):
        servers = self.bot.servers
        serverlist = []
        for server in servers:
            check = server.get_member(user.id)
            if check is not None:
                serverlist.append('[{}] {} as {}\n'.format(
                    server.id, server.name, check.display_name))

        if len(serverlist) > 0:
            package = ''.join(serverlist)
            await self.bot.send_message(ctx.message.channel, package)


# class DIAGNOSTICS:

#     def __init__(self, bot):
#         self.bot = bot

#     def log(self, ctx, msg=None):
#         message = 'CollectorDevTeam diagnostics:\n```'
#         if ctx.message.channel.is_private is True:
#             message += 'Private Channel: [{}]\n'.format(
#                 ctx.message.channel.id)
#         elif ctx.message.channel.is_private is False:
#             message += 'Server:  [{0.message.server.id}] {0.message.server.name} \n'.format(
#                 ctx)
#             message += 'Channel: [{0.message.channel.id}] {0.message.channel.name} \n'.format(
#                 ctx)
#         message += 'User:    [{0.message.author.id}] {0.message.author.display_name} \n'.format(
#             ctx)
#         if ctx.invoked_subcommand is not None:
#             if ctx.message.content is None:
#                 message += 'Subcommand Invoked: {0.invoked_subcommand}\n'.format(
#                     ctx)
#             else:
#                 message += 'Subcommand Invoked: {0.invoked_subcommand}\n'.format(
#                     ctx)
#                 message += 'Conent: {0.message.content}\n'.format(
#                     ctx)
#         message.format(ctx)
#         # elif ctx.invoked is not None:
#         #     message += 'Invoked command: {0.invoked}'.format(ctx)
#         if msg is not None:
#             message += 'Comment: {}\n'.format(msg)
#         message += '```'
#         return message


# class ScreenShot:
#     """Save a Screenshot from x website in mcocTools"""

#     def __init__(self, bot):
#         self.bot = bot
#         self.settings = dataIO.load_json('data/mcocTools/settings.json')
#         if 'calendar' not in self.settings.keys():
#             self.settings['calendar'] = {'screenshot': '', 'time': 0}
#             dataIO.save_json('data/mcocTools/settings.json', self.settings)

#     async def get_screenshot(self, url, w=1920, h=1080):
#         chrome_options = Options()
#         chrome_options.add_argument("--headless")
#         chrome_options.add_argument("--window-size={}, {}".format(w, h))
#         chrome_options.add_argument("allow-running-insecure-content")
#         # chrome_options.binary_location = '/Applications/Google Chrome   Canary.app/Contents/MacOS/Google Chrome Canary'
#         driver = webdriver.Chrome(
#             executable_path="C:\webdrivers\chromedriver_win32\chromedriver",   chrome_options=chrome_options)
#         channel = self.bot.get_channel('391330316662341632')
#         # DRIVER = 'chromedriver'
#         # driver = webdriver.Chrome(DRIVER)
#         driver.get(url)

#         screenshot = driver.save_screenshot('data/mcocTools/temp.png')
#         driver.quit()
#         # await asyncio.sleep(3)
#         message = await self.bot.send_file(channel, 'data/mcocTools/temp.png')
#         await asyncio.sleep(5)
#         if len(message.attachments) > 0:
#             return message.attachments[0]['url']
#         else:
#             return None


class CDTHelperFunctions:
    """Helper Functions"""

    def tabulate(table_data, width, rotate=True, header_sep=True, align_out=True):
        rows = []
        cells_in_row = None
        for i in iter_rows(table_data, rotate):
            if cells_in_row is None:
                cells_in_row = len(i)
            elif cells_in_row != len(i):
                raise IndexError("Array is not uniform")
            if align_out:
                fstr = '{:<{width}}'
                if len(i) > 1:
                    fstr += '|' + '|'.join(['{:>{width}}'] * (len(i) - 1))
                rows.append(fstr.format(*i, width=width))
            else:
                rows.append('|'.join(['{:^{width}}'] *
                                     len(i)).format(*i, width=width))
        if header_sep:
            rows.insert(1, '|'.join(['-' * width] * cells_in_row))
        return chat.box('\n'.join(rows))

    def tabulate_data(table_data, width=None, align=None, rotate=False, separate_header=True):
        """Turn a list of lists into a tabular string"""
        align_opts = {'center': '^', 'left': '<', 'right': '>'}
        default_align = 'center'
        default_width = 5

        rows = []
        if table_data:
            tbl_cols = len(table_data[0])
            if any(len(x) != tbl_cols for x in table_data):
                raise IndexError('Array is not uniform')

            width = CDTHelperFunctions.pad_list(width, tbl_cols, default_width)
            align = CDTHelperFunctions.pad_list(align, tbl_cols, default_align)
            for i in CDTHelperFunctions.iter_rows(table_data, rotate):
                fstr = '{:{}{}}'.format(i[0], align_opts[align[0]], width[0])
                if tbl_cols > 1:
                    for n in range(1, tbl_cols):
                        fstr += '|{:{}{}}'.format(i[n],
                                                  align_opts[align[n]], width[n])
                rows.append(fstr)
            if separate_header:
                rows.insert(1, '-' * (sum(width) + len(width)))
        return '\n'.join(rows)

    def pad_list(lst, new_length, pad_value):
        """Pad out a list to a desired length"""
        if lst is None:
            lst = []
        pad = [pad_value] * (new_length - len(lst))
        for x in pad:
            lst.append(x)
        return lst

    def iter_rows(array, rotate):
        if not rotate:
            for i in array:
                yield i
        else:
            for j in range(len(array[0])):
                row = []
                for i in range(len(array)):
                    row.append(array[i][j])
                yield row


class CDTReport:
    """Report Users"""

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/mcocTools/settings.json')

    async def init(self, server):
        self.settings[server.id] = {
            'report-channel': '0'
        }

    async def error(self, ctx):  # In case files dont exist.
        message_file = ""
        for folder in folders:
            if not os.path.exists(folder):
                message_file += "`{}` folder\n".format(folder)
                print("Creating " + folder + " folder...")
                os.makedirs(folder)
                error_file = 1
        for filename in files:
            if not os.path.isfile('data/mcocTools/{}'.format(filename)):
                print("Creating empty {}".format(filename))
                dataIO.save_json('data/mcocTools/{}'.format(filename), {})
                message_file += "`{}` is missing\n".format(filename)
                error_file = 1
        if error_file == 1:
            message_file += "The files were successfully re-created. Try again your command (you may need to set your local settings again)"
            await self.bot.say(message_file)
        if ctx.message.server.id not in self.settings:
            await self.init(ctx.message.server)

    @commands.group(pass_context=True)
    @checks.admin()
    async def reportchannel(self, ctx, *, channel: discord.Channel = None):
        """Sets a channel as log"""

        if not channel:
            channel = ctx.message.channel
        else:
            pass
        server = ctx.message.server
        if server.id not in self.settings:
            await self.init(server)
        self.settings[server.id]['report-channel'] = channel.id
        await self.bot.say("Reports will be sent to **" + channel.name + "**.")
        dataIO.save_json('data/mcocTools/settings.json', self.settings)

    @commands.group(pass_context=True, hidden=True)
    @checks.admin()
    async def masterchannel(self, ctx, *, channel: discord.Channel = None):
        """Sets a global channel as log"""
        if ctx.message.author.id in ('148622879817334784', '124984294035816448', '209339409655398400'):
            if not channel:
                channel = ctx.message.channel
            else:
                pass
            server = ctx.message.server
            self.settings['cdt-master-channel'] = channel.id
            await self.bot.say("Reports will be sent to **" + channel.name + "**.")
            dataIO.save_json('data/mcocTools/settings.json', self.settings)
        else:
            await self.bot.say("CollectorDevTeam only sucka!")

    @commands.command(pass_context=True, no_pm=True, name='report')
    # changed terminology. Discord has people not players.
    async def cdtreport(self, ctx, person, *, reason):
        """Report a user. Please provide evidence.
        Upload a screenshot, and copy a link to the screenshotself.
        Include the link in your report."""  # Where is the evidence field? Might want to add one
        author = ctx.message.author.name  # String for the Author's name
        server = ctx.message.server
        try:
            reportchannel = self.bot.get_channel(
                self.settings[server.id]['report-channel'])
            masterchannel = self.bot.get_channel(
                self.settings['cdt-master-channel'])
        except:
            KeyError
            await self.bot.send_message(ctx.message.author,
                                        "Uh Oh! Your report was not sent D: Please let an admin know that they need to set the default report channel")
            return
        embed = discord.Embed(
            title="Report:", description="A Report has been filed against somebody!")
        embed.set_author(name="CollectorVerse Report System")
        embed.add_field(name="User:", value=person, inline=False)
        embed.add_field(name="Reason:", value=reason, inline=False)
        embed.add_field(name="Reported By:", value=author, inline=True)
        embed.set_footer(text='CollectorDevTeam',
                         icon_url=COLLECTOR_ICON)
        await self.bot.send_message(ctx.message.author, "Your report against {} has been created.".format(
            person))  # Privately whispers to a user that said report was created and sent
        # Sends report to the channel we specified earlier
        await self.bot.send_message(reportchannel, embed=embed)
        # Sends report to the channel we specified earlier
        await self.bot.send_message(masterchannel, embed=embed)


# class CDTEmbed:
#     def __init__(self, bot):
#         self.bot = bot

#     def get_embed(self, ctx, user_id=None, color=discord.Color.gold(), title='', description='', image=None, thumbnail=None, url=None):
#         '''Return a color styled embed with CDT footer, and optional title or description.
#         user_id = user id string. If none provided, takes message author.
#         color = manual override, otherwise takes gold for private channels, or author color for server.
#         title = String, sets title.
#         description = String, sets description.
#         image = String url.  Validator checks for valid url.
#         thumbnail = String url. Validator checks for valid url.'''
#         if user_id is None:
#             color = discord.Color.gold()
#         elif isinstance(user_id, discord.User):
#             user = user_id
#             member = ctx.message.server.get_member(user.id)
#             color = member.color
#         else:
#             # member = self.bot.get_member(user_id)
#             member = discord.utils.get(ctx.message.server.members, id=user_id)
#             color = member.color
#         if url is None:
#             url = PATREON
#         data = discord.Embed(color=color, title=title, url=url)
#         if description is not None:
#             if len(description) < 1500:
#                 data.description = description
#         data.set_author(name='CollectorVerse',
#                         icon_url=COLLECTOR_ICON)
#         if image is not None:
#             validators.url(image)
#             code = requests.get(image).status_code
#             if code == 200:
#                 data.set_image(url=image)
#             else:
#                 print('Image URL Failure, code {}'.format(code))
#                 print('Attempted URL:\n{}'.format(image))
#         if thumbnail is not None:
#             validators.url(thumbnail)
#             code = requests.get(thumbnail).status_code
#             if code == 200:
#                 data.set_thumbnail(url=thumbnail)
#             else:
#                 print('Thumbnail URL Failure, code {}'.format(code))
#                 print('Attempted URL:\n{}'.format(thumbnail))
#         data.set_footer(text='CollectorDevTeam | Requested by {}'.format(
#             ctx.message.author), icon_url=COLLECTOR_ICON)
#         return data


class CDTCheck:
    def __init__(self, bot):
        self.bot = bot
        self.cdtserver = self.bot.get_server('215271081517383682')
        self.roles = {}

    @commands.command(pass_context=True, hidden=True, name="promote", aliases=("promo",))
    async def cdt_promote(self, ctx, channel: discord.Channel, *, content):
        """Content will fill the embed description.
        title;content will split the message into Title and Content.
        An image attachment added to this command will replace the image embed."""
        robotworkshop = self.bot.get_channel('391330316662341632')
        authorized = check_collectorsupportteam(self, ctx)
        if authorized is not True:
            return
        else:
            pages = []
            # contents = content.split(";")
            # if len(contents) > 1:
            #     title = contents[0]
            #     description = contents[1]
            # else:
            #     title = "CollectorVerse Tips"
            #     description = content
            if len(ctx.message.attachments) > 0:
                image = ctx.message.attachments[0]
                imgurl = image['url']
                # urllib.request.urlretrieve(imgurl, 'data/mcocTools/temp.png')
                # asyncio.wait(5)
                # newfile = await self.bot.file_upload(robotworkshop, 'data/mcocTools/temp.png')
                # image = newfile.attachments[0]
                # imgurl = image['url']
                # imagelist = []
                # for i in ctx.message.attachments.keys():
                #     imagelist.append(ctx.message.attachments[i]['url'])
            else:
                imagelist = [
                    'https://cdn.discordapp.com/attachments/391330316662341632/725045045794832424/collector_dadjokes.png',
                    'https://cdn.discordapp.com/attachments/391330316662341632/725054700457689210/dadjokes2.png',
                    'https://cdn.discordapp.com/attachments/391330316662341632/725055822023098398/dadjokes3.png',
                    'https://cdn.discordapp.com/attachments/391330316662341632/725056025404637214/dadjokes4.png',
                    'https://media.discordapp.net/attachments/391330316662341632/727598814327865364/D1F5DE64D72C52880F61DBD6B2142BC6C096520D.png',
                    'https://media.discordapp.net/attachments/391330316662341632/727598813820485693/8952A192395C772767ED1135A644B3E3511950BA.jpg',
                    'https://media.discordapp.net/attachments/391330316662341632/727598813447192616/D77D9C96DC5CBFE07860B6211A2E32448B3E3374.jpg',
                    'https://media.discordapp.net/attachments/391330316662341632/727598812746612806/9C15810315010F5940556E48A54C831529A35016.jpg']
                imgurl = random.choice(imagelist)
            thumbnail = 'https://images-ext-1.discordapp.net/external/6Q7QyBwbwH2SCmwdt_YR_ywkHWugnXkMc3rlGLUnvCQ/https/raw.githubusercontent.com/CollectorDevTeam/assets/master/data/images/featured/collector.png?width=230&height=230'
            # for imgurl in imagelist:
            data = CDTEmbed.create(self, ctx,
                                   title='CollectorVerse Tips', description=content,
                                   image=imgurl)
            data.set_author(name="{} of CollectorDevTeam".format(
                ctx.message.author.display_name), icon_url=ctx.message.author.avatar_url)
            data.add_field(name="Alliance Template",
                           value="[Make a Server](https://discord.new/gtzuXHq2kCg4)")
            data.add_field(
                name="Get Collector", value="[Invite](https://discord.com/oauth2/authorize?client_id=210480249870352385&scope=bot&permissions=8)")
            data.add_field(
                name="Get Support", value="[CollectorDevTeam Server](https://discord.gg/BwhgZxk)")
            await self.bot.send_message(channel, embed=data)
            # await self.bot.delete_message(ctx.message)
            # pages.append(data)
            # menu = PagesMenu(self.bot, timeout=30, add_pageof=True)
            # await menu.menu_start(pages=pages)

    async def collectordevteam(self, ctx):
        '''Verifies if calling user has either the trusted CollectorDevTeam role, or CollectorSupportTeam'''
        role_ids = ('390253643330355200', '390253719125622807',)
        authnorized = False
        passfail = "fail"
        for r in role_ids:
            self.roles.update(
                {r: self._get_role(self.bot.get_server('215271081517383682'), r)})
            if self.roles[r] in ctx.message.author.roles:
                authorized = True
                passfail = "pass"
                continue

        elevation_requests = self.bot.get_channel('720668625815732316')
        author = ctx.message.author
        member = self.cdtserver.get_member(author.id)
        await self.bot.send_message(elevation_requests, '```CDT Authentication attempt: {0}\n{1.display_name} [{1.id}] on {2.name} [{2.id}]```'.format(passfail, author, ctx.message.server))
        return authorized

    def _get_role(self, server: discord.Server, role_key: str):
        """Returns discord.Role"""
        try:
            # tstart = time.time()
            role = discord.utils.get(server.roles, id=role_key)
            # print('_get_role with utils in: {:.3f}'.format(time.time()-tstart))
            return role
        except:
            roles = server.roles
            for role in roles:
                if role.id == role_key:
                    return role
        return None


def cell_to_list(cell):
    if cell is not None:
        return [strip_and_numericise(i) for c in cell.split(',') for i in c.split('\n')]


def cell_to_dict(cell):
    if cell is None:
        return None
    ret = {}
    for i in cell.split(','):
        k, v = [strip_and_numericise(j) for j in i.split(':')]
        ret[k] = v
    return ret


def check_folders():
    folders = ('data', 'data/mcocTools/', 'data/storyquest/')
    for folder in folders:
        if not os.path.exists(folder):
            print("Creating " + folder + " folder...")
            os.makedirs(folder)


def check_files():
    ignore_list = {'SERVERS': [], 'CHANNELS': []}

    files = {
        'settings.json': {},
        'mcoctools.json': {'calendar': '', 'cutoffs': '', 'calendar_date': '', 'cutoffs_date': ''},
        'collectormap.json': {},
        'sgd_cdt_stats.json': {},
        'sgd_event_data.json': {},
        'sgd_season_rewards.json': {},
        'sgd_tldr.json': {},
        'sgd_variant.json': {},
        'sgd_cdt_data.json': {},
        'sgd_cdt_versions.json': {},
        'sgd_cdt_masteries.json': {},
        'ability_counters.json': {}

    }

    for filename, value in files.items():
        if not os.path.isfile('data/mcocTools/{}'.format(filename)):
            print("Creating empty {}".format(filename))
            dataIO.save_json('data/mcocTools/{}'.format(filename), value)


def load_csv(filename):
    return csv.DictReader(open(filename))


def get_csv_row(filecsv, column, match_val, default=None):
    print(match_val)
    csvfile = load_csv(filecsv)
    for row in csvfile:
        if row[column] == match_val:
            if default is not None:
                for k, v in row.items():
                    if v == '':
                        row[k] = default
            return row


def get_csv_rows(filecsv, column, match_val, default=None):
    print(match_val)
    csvfile = load_csv(filecsv)
    package = []
    for row in csvfile:
        if row[column] == match_val:
            if default is not None:
                for k, v in row.items():
                    if v == '':
                        row[k] = default
            package.append(row)
    return package


def numericise_bool(val):
    if val == "TRUE":
        return True
    elif val == "FALSE":
        return False
    else:
        return numericise(val)


def remove_commas(cell):
    return numericise_bool(cell.replace(',', ''))


def remove_NA(cell):
    return None if cell in ("#N/A", "") else numericise_bool(cell)


def strip_and_numericise(val):
    return numericise_bool(val.strip())


def tabulate(table_data, width, rotate=True, header_sep=True):
    rows = []
    cells_in_row = None
    for i in iter_rows(table_data, rotate):
        if cells_in_row is None:
            cells_in_row = len(i)
        elif cells_in_row != len(i):
            raise IndexError("Array is not uniform")
        rows.append('|'.join(['{:^{width}}'] * len(i)).format(*i, width=width))
    if header_sep:
        rows.insert(1, '|'.join(['-' * width] * cells_in_row))
    return chat.box('\n'.join(rows))


def setup(bot):
    check_folders()
    check_files()
    sgd = StaticGameData(bot)
    # sgd.register_gsheets(bot)
    bot.loop.create_task(sgd.load_cdt_data())
    bot.add_cog(CDTReport(bot))
    bot.add_cog(Calculator(bot))
    bot.add_cog(CDTGAPS(bot))
    bot.add_cog(MCOCEvents(bot))
    bot.add_cog(INSPECTOR(bot))
    bot.add_cog(CDTCheck(bot))
    bot.add_cog(MCOCTools(bot))
