import discord
import asyncio
import aiohttp
import urllib
import json  # For fetching JSON from alliancewar.com
import os
import requests
import re
import json
# from .utils.dataIO import dataIO
from discord.ext import commands
from __main__ import send_cmd_help
from .mcocTools import (CDTEmbed,
                        StaticGameData, PagesMenu, KABAM_ICON, COLLECTOR_ICON, CDTHelperFunctions)
from .mcoc import ChampConverter, ChampConverterDebug, Champion
from .utils import chat_formatting as chat

JPAGS = 'http://www.alliancewar.com'
PATREON = 'https://patreon.com/collectorbot'
JOINCDT = 'https://discord.gg/BwhgZxk'
# remote_data_basepath = "https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/"


boosts = json.loads(requests.get(
    'https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/json/alliancewar/boosts.json').text)
aw_advanced = json.loads(requests.get(
    'https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/json/alliancewar/aw_advanced.json').text)
aw_challenger = json.loads(requests.get(
    'https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/json/alliancewar/aw_challenger.json').text)
aw_expert = json.loads(requests.get(
    'https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/json/alliancewar/aw_expert.json').text)
aw_hard = json.loads(requests.get(
    'https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/json/alliancewar/aw_hard.json').text)
aw_intermediate = json.loads(requests.get(
    'https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/json/alliancewar/aw_intermediate.json').text)


AWD_API_URL_TEST = 'http://scouter-staging.herokuapp.com/awd'
AWD_API_URL = 'http://scouter-prod.herokuapp.com/awd'
# MAS_API_URL = 'http://chocripplebot.herokuapp.com/mas'
# aw_map_paths = {
#     'bosskill': {
#         'A': [1, 2, 19, 25, 46, 49, 50, 53],
#         'B': [],
#         'C': [3, 21, 27, 41, 45, 47, 51],
#         'D': [11, 17, 22, 28, 34, 36, 48],
#         'E': [],
#         'F': [12, 18, 24, 30, 35, 37, 48],
#         'G': [4, 7, 13, 14, 31, 38, 42, 52],
#         'H': [],
#         'I': [6, 9, 15, 14, 33, 40, 44, 55]
#     },
#     'expert': {
#         'A': [1, 19, 25, 46, 49, 50, 53],
#         'B': [1, 2, 19, 20, 26, 41, 45, 47],
#         'C': [3, 21, 27, 41, 45, 47, 51],
#         'D': [11, 17, 22, 28, 34, 36, 48],
#         'E': [10, 16, 23, 29, 48],
#         'F': [12, 18, 24, 30, 35, 37, 48],
#         'G': [4, 7, 13, 14, 31, 38, 42, 52],
#         'H': [5, 8, 14, 32, 39, 43, 55],
#         'I': [6, 9, 15, 14, 33, 40, 44, 55]
#     },

# }

aw_tiers = {1: {'mult': 8.0, 'diff': 'Expert', 'color': discord.Color.gold()},
            2: {'mult': 7.0, 'diff': 'Expert', 'color': discord.Color.gold()},
            3: {'mult': 6.0, 'diff': 'Expert', 'color': discord.Color.gold()},
            4: {'mult': 4.5, 'diff': 'Challenger', 'color': discord.Color.red()},
            5: {'mult': 4.0, 'diff': 'Challenger', 'color': discord.Color.red()},
            6: {'mult': 3.4, 'diff': 'Hard', 'color': discord.Color.orange()},
            7: {'mult': 3.2, 'diff': 'Hard', 'color': discord.Color.orange()},
            8: {'mult': 3.0, 'diff': 'Hard', 'color': discord.Color.orange()},
            9: {'mult': 2.8, 'diff': 'Hard', 'color': discord.Color.orange()},
            10: {'mult': 2.4, 'diff': 'Intermediate', 'color': discord.Color.blue()},
            11: {'mult': 2.3, 'diff': 'Intermediate', 'color': discord.Color.blue()},
            12: {'mult': 2.2, 'diff': 'Intermediate', 'color': discord.Color.blue()},
            13: {'mult': 2.0, 'diff': 'Normal', 'color': discord.Color.green()},
            14: {'mult': 1.9, 'diff': 'Normal', 'color': discord.Color.green()},
            15: {'mult': 1.8, 'diff': 'Normal', 'color': discord.Color.green()},
            16: {'mult': 1.6, 'diff': 'Easy', 'color': discord.Color.green()},
            17: {'mult': 1.5, 'diff': 'Easy', 'color': discord.Color.green()},
            18: {'mult': 1.4, 'diff': 'Easy', 'color': discord.Color.green()},
            19: {'mult': 1.3, 'diff': 'Easy', 'color': discord.Color.green()},
            20: {'mult': 1.2, 'diff': 'Easy', 'color': discord.Color.green()},
            21: {'mult': 1.1, 'diff': 'Easy', 'color': discord.Color.green()},
            22: {'mult': 1.0, 'diff': 'Easy', 'color': discord.Color.green()},
            }

aw_maps = {'advanced': aw_advanced,
           'challenger': aw_challenger,
           'expert': aw_expert,
           'hard': aw_hard,
           'intermediate': aw_intermediate,
           'easy': aw_advanced,
           'normal': aw_advanced
           }


class Scout:

    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, hidden=True)
    async def boost_info(self, ctx, boost):
        # boosturl = 'http://www.alliancewar.com/global/ui/js/boosts.json'
        # boosts = alliancewarboosts
        keys = boosts.keys()
        if boost not in keys:
            await self.bot.send_message(ctx.message.channel, 'Available boosts:\n'+'\n'.join(k for k in keys))
        else:
            info = boosts[boost]
            # img = '{}/global/ui/images/booster/{}.png'.format(JPAGS, info['img'])
            img = 'https://raw.githubusercontent.com/JPags/alliancewar_data/master/global/images/boosterr/{}.png'.format(
                info['img'])
            title = info['title']
            text = info['text']
            em = discord.Embed(color=discord.Color.gold(),
                               title='Boost Info', descritpion='', url=JPAGS)
            em.set_thumbnail(url=img)
            em.add_field(name=title, value=text)
            em.set_footer(icon_url=JPAGS+'/aw/images/app_icon.jpg',
                          text='AllianceWar.com')
            await self.bot.send_message(ctx.message.channel, embed=em)

    @commands.group(pass_context=True, aliases=['aw', ])
    async def alliancewar(self, ctx):
        """Alliancewar.com Commands [WIP]"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @alliancewar.command(pass_context=True, hidden=True, name='seasons', aliases=['rewards'])
    async def _season_rewards(self, ctx, tier, rank=''):
        sgd = StaticGameData()
        cdt_sr = await sgd.get_gsheets_data('aw_season_rewards')
        col = set(cdt_sr.keys()) - {'_headers'}
        rows = ('master', 'platinum', 'gold', 'silver',
                'bronze', 'stone', 'participation')
        tier = tier.lower()
        if tier in rows:
            pages = []
            for r in (1, 2, 3, ''):
                if '{}{}'.format(tier, r) in cdt_sr['unique']:
                    em = discord.embed(color=discord.Color.gold(), title='{} {}'.format(
                        tier.title(), rank), description=cdt_sr['{}{}'.format(tier, r)]['rewards'])

        else:
            await self.bot.send_message(ctx.message.channel, 'Valid tiers: Master\nPlatinum\nGold\nSilver\nBronze\nStone\nParticipation')

    @alliancewar.command(pass_context=True, hidden=False, name="node")
    async def _node_info(self, ctx, node, tier='expert'):
        """Report Node information."""
        season = 2
        tier = tier.lower()
        if tier in aw_maps.keys():
            print('aw_node req: {} {}'.format(node, tier))
            em = await self.get_awnode_details(ctx=ctx, nodeNumber=int(node), tier=tier)
            await self.bot.send_message(ctx.message.channel, embed=em)
        else:
            await self.bot.send_message(ctx.message.channel, 'Valid tiers include: {}'.format(', '.join(aw_maps.keys())))

    @alliancewar.command(pass_context=True, hidden=False, name="nodes")
    async def _nodes_info(self, ctx, tier: str, *, nodes):
        """Report Node information.
        This command has a reported defect and it is being investigatedself."""
        season = 2
        tier = tier.lower()
        pages = []
        if tier in aw_maps.keys():
            # nodeNumbers = nodes.split(' ')
            for node in nodes.split(' '):
                print('aw_nodes req: '+node+' '+tier)
                em = await self.get_awnode_details(ctx=ctx, nodeNumber=node, tier=tier)
                mapurl = '{}warmap_3_{}.png'.format(
                    self.basepath, tier.lower())
                em.set_image(url=mapurl)
                pages.append(em)
                # await self.bot.send_message(ctx.message.channel, embed=em)
            if len(pages) > 0:
                menu = PagesMenu(self.bot, timeout=30,
                                 delete_onX=True, add_pageof=True)
                await menu.menu_start(pages=pages, page_number=0)
        else:
            await self.bot.send_message(ctx.message.channel, 'Valid tiers include: {}'.format(', '.join(aw_maps.keys())))

    async def get_awnode_details(self, ctx, nodeNumber, tier, em: discord.Embed = None):
        # boosts = self.alliancewarboosts
        tiers = {
            'expert': {'color': discord.Color.gold(), 'minis': [27, 28, 29, 30, 31, 48, 51, 52, 53, 55], 'boss': [54]},
            'hard': {'color': discord.Color.red(), 'minis': [48, 51, 52, 53, 55], 'boss': [54]},
            'challenger': {'color': discord.Color.orange(), 'minis': [27, 28, 29, 30, 31, 48, 51, 52, 53, 55], 'boss': [54]},
            'intermediate': {'color': discord.Color.blue(), 'minis': [48, 51, 52, 53, 55], 'boss': [54]},
            'advanced': {'color': discord.Color.green(), 'minis': [], 'boss': []},
        }
        if tier not in tiers:
            tier = 'advanced'
        pathdata = aw_maps[tier]
        # if paths is not None:
        # await self.bot.send_message(ctx.message.channel, 'DEBUG: 9path.json loaded from alliancewar.com')
        if int(nodeNumber) in tiers[tier]['minis']:
            title = '{} MINIBOSS Node {} Boosts'.format(
                tier.title(), nodeNumber)
        elif int(nodeNumber) in tiers[tier]['boss']:
            title = '{} BOSS Node {} Boosts'.format(tier.title(), nodeNumber)
        else:
            title = '{} Node {} Boosts'.format(tier.title(), nodeNumber)
        if em == None:
            em = discord.Embed(
                color=tiers[tier]['color'], title=title, descritpion='', url=JPAGS)
            em.set_footer(icon_url=JPAGS+'/aw/images/app_icon.jpg',
                          text='AllianceWar.com')
        if pathdata is not None:
            nodedetails = pathdata['boosts'][str(nodeNumber)]
            for n in nodedetails:
                title, text = '', 'No description. Report to @jpags#5202'
                if ':' in n:
                    nodename, bump = n.split(':')
                else:
                    nodename = n
                    bump = 0
                if nodename in boosts:
                    title = boosts[nodename]['title']
                    if boosts[nodename]['text'] is not '':
                        text = boosts[nodename]['text']
                        print('nodename: {}\ntitle: {}\ntext: {}'.format(
                            nodename, boosts[nodename]['title'], boosts[nodename]['text']))
                        if bump is not None:
                            try:
                                text = text.format(bump)
                            except:  # wrote specifically for limber_percent
                                # wrote specifically for limber_percent
                                text = text.replace('}%}', '}%').format(bump)
                            print('nodename: {}\ntitle: {}\nbump: {}\ntext: {}'.format(
                                nodename, boosts[nodename]['title'], bump, boosts[nodename]['text']))
                    else:
                        text = 'Description text is missing from alliancewar.com.  Report to @jpags#5202.'
                else:
                    title = 'Error: {}'.format(nodename)
                    value = 'Boost details for {} missing from alliancewar.com.  Report to @jpags#5202.'.format(
                        nodename)
                em.add_field(name=title, value=text, inline=False)
        else:
            em.add_field(name='Apologies Summoner',
                         value='Alliance War data for {} has not been *collected*.  \nDonate data to CollectorDevTeam : https://discord.gg/BwhgZxk'.format(tier.title()))
        #     img = '{}/global/ui/images/booster/{}.png'.format(JPAGS, boosts['img'])
        # em.set_thumbnail(url=img)
        return em

    @alliancewar.command(pass_context=True, hidden=False, name="map")
    async def _map(self, ctx, tier='expert'):
        """Alliance War Maps by Cat Murdock:
        Challenger
        Intermediate
        Hard
        Expert
        """
        warmaps = ('challenger', 'expert', 'hard', 'intermediate')
        if tier is None:
            pages = []
            for tier in ('challenger', 'intermediate', 'hard', 'expert'):
                data = CDTEmbed.get_embed(self, ctx)
                data.title = 'Alliane War {} Map :cat::sparkles:'.format(
                    tier.title())
                data.set_author(name=self.catmurdock.display_name,
                                icon_url=self.catmurdock.avatar_url)
                data.add_field(
                    name='Support Cat', value=self.catsupport)
                data.set_image(
                    url='{}catmurdock/AW/{}.png'.format(self.basepath, tier.title()))
                data.set_thumbnail(url=self.catcorner)
                pages.append(data)
            menu = PagesMenu(self.bot, timeout=30,
                             delete_onX=True, add_pageof=True)
            await menu.menu_start(pages)
        elif tier.lower() in warmaps:
            mapurl = '{}catmurdock/AW/{}.png'.format(
                self.basepath, tier.lower())
            data = CDTEmbed.get_embed(self, ctx)
            data.title = 'Alliance War {} Map :cat::sparkles:'.format(
                tier.title())
            data.set_author(name=self.catmurdock.display_name,
                            icon_url=self.catmurdock.avatar_url)
            data.add_field(
                name='Support Cat', value=self.catsupport)
            data.set_image(url=mapurl)
            data.set_thumbnail(url=self.catcorner)
            data.set_footer(text='CollectorDevTeam',
                            icon_url=self.COLLECTOR_ICON)
            await self.bot.send_message(ctx.message.channel, embed=data)
        else:
            data = CDTEmbed.get_embed(self, ctx)
            data.title = 'Alliance War Maps :cat::sparkles:'.format(
                tier.title())
            data.set_author(name=self.catmurdock.display_name,
                            icon_url=self.catmurdock.avatar_url)
            data.description = 'Currently supporting "Challenger", "Intermediate", "Hard", "Expert"'
            data.add_field(
                name='Support Cat', value=self.catsupport)
            data.set_thumbnail(url=self.catcorner)
            data.set_footer(text='CollectorDevTeam',
                            icon_url=self.COLLECTOR_ICON)
            await self.bot.send_message(ctx.message.channel, embed=data)

    @alliancewar.command(pass_context=True, hidden=False, name="tiers", aliases=['tier'])
    async def _tiers(self, ctx):
        """List Alliance War Tiers"""
        aw_tiers = aw_tiers
        # name = '\u200b'
        # value = [['Tier', 'Mult', 'Difficulty']]
        name = 'Tier, Multiplier & Difficulty'
        value = []
        for k, v in aw_tiers.items():
            value.append([k, v['mult'], v['diff']])
        v = CDTHelperFunctions.tabulate_data(value, width=[3, 4, 14], align=[
                                             'left', 'left', 'left'], rotate=False, separate_header=False)
        em = discord.Embed(color=discord.Color.gold(
        ), title='Alliance War Tier Multipliers and Difficulty', url=JOINCDT)
        em.set_thumbnail(
            url='http://www.alliancewar.com/aw/images/app_icon.jpg')
        em.add_field(name=name, value='```{}```'.format(v))
        # em.add_field(name=name, value=chat.box(v), inline=False)
        em.set_footer(text='CollectorDevTeam', icon_url=self.COLLECTOR_ICON)
        await self.bot.send_message(ctx.message.channel, embed=em)

    @alliancewar.command(pass_context=True, hidden=False, name="scout")
    async def _scout(self, ctx, *, scoutargs):
        """
        JM's Scouter Lens inspection tool.
        Req: The Scouter Lens Mastery must contain at least 1 point.

        Valid Options:
        <tier>  : T1 - T22, expert, challenger, hard, inter, normal, easy
        <node>  : n1 - 55
        <hp>    : hp12345, h12345, 12345
        <attack>: a1234, atk1234, 1234
        [class] : science, skill, mutant, tech, cosmic, mystic
        [star]  : 4, 5, 6

        """
        sgd = StaticGameData()
        # print(len(sgd.cdt_data), len(sgd.cdt_masteries), sgd.test)
        cm = sgd.cdt_masteries

        default = self.NodeParser(scoutargs)
        keys = default.keys()

        package = []
        if default['node'] == 0 and default['nodes'] == '':
            package.append(
                '\nYou must specify an Alliance War Node number. \n Examples:\n``node30``\n``n30``')
        if default['tier'] == 0 and default['difficulty'] == '':
            package.append(
                '\nYou must specify either an Alliance War Tier (T1 - T22) or a valid difficulty.\nExamples:\n``t4``\n``T4``\n``Expert``')
        if default['hp'] == 0:
            package.append(
                '\nYou must specify the mystery champion observed Health\nExamples:\n``hp123456``\n``h123456``\n``123456``')
        if default['atk'] == 0:
            package.append(
                '\nYou must specify the mystery champion observed Attack\nExamples:\n``hp12345``\n``h12345``\n``12345``')
        # for key in keys:
        #     package.append('{} : {}'.format(key, default[key]))
        em = discord.Embed(color=default['color'], title='JM\'s ScouterLens',
                           description='', url='https://goo.gl/forms/ZgJG97KOpeSsQ2092')
        em2 = discord.Embed(color=default['color'], title='JM\'s ScouterLens',
                            description='', url='https://goo.gl/forms/ZgJG97KOpeSsQ2092')
        em.set_footer(text='CollectorDevTeam + JM\'s Scouter Lens Bot',
                      icon_url=self.COLLECTOR_ICON)
        em2.set_footer(
            text='CollectorDevTeam + JM\'s Scouter Lens Bot', icon_url=self.COLLECTOR_ICON)
        if len(package) > 0:
            em.description = '\n'.join(package)
            await self.bot.send_message(ctx.message.channel, embed=em)
            return
        else:
            data = {}
            for d in {'difficulty', 'star_filter', 'class_filter', 'hp', 'atk', 'tier'}:
                if d in keys:
                    data[d] = default[d]  # stringify all data?
                if default['node'] > 0:
                    data['node'] = 'n{}'.format(default['node'])
                elif default['nodes'] != '':
                    data['node'] = default['nodes']

            if default['test'] == True:
                url = AWD_API_URL_TEST
            else:
                url = AWD_API_URL

            response = await self.jm_send_request(url, data=data)
            fringe = None
            if not response:
                tier = int(default['tier'])
                if tier > 1 and aw_tiers[tier - 1]['diff'] != aw_tiers[tier]['diff']:
                    data['difficulty'] = aw_tiers[tier - 1]['diff'].lower()
                    response = await self.jm_send_request(url, data=data)
                    if not response:
                        data['difficulty'] = default['difficulty'].lower()
                    else:
                        data['tier'] = tier - 1
                        fringe = 'Opponent in higher tier'
                elif tier < 22 and aw_tiers[tier + 1]['diff'] != aw_tiers[tier]['diff']:
                    data['difficulty'] = aw_tiers[tier + 1]['diff'].lower()
                    response = await self.jm_send_request(url, data=data)
                    if not response:
                        data['difficulty'] = default['difficulty'].lower()
                    else:
                        data['tier'] = tier + 1
                        fringe = 'Opponent in lower tier'

            pathdata = aw_maps[data['difficulty'].lower()]
            # nodedetails = pathdata['boosts'][str(default['node'])]
            if data['tier'] == 0:
                desc = '{} Bracket | Node {}'.format(
                    data['difficulty'].title(), default['node'])
            else:
                desc = 'Tier {} | {} Bracket | Node {}'.format(
                    data['tier'], data['difficulty'].title(), default['node'])
            em.description = desc
            if 'error' in response and default['debug'] == 1:
                if fringe is not None:
                    em.add_field(name='Fringe check', value=fringe)
                em.add_field(name='Transmitting:', value=json.dumps(data))
                em.add_field(name='Scout API Error & Debug',
                             value=str(response['error']))
                await self.bot.send_message(ctx.message.channel, embed=em)
                return
            elif default['debug'] == 1:
                if fringe is not None:
                    em.add_field(name='Fringe check', value=fringe)
                em.add_field(name='Transmitting:', value=json.dumps(data))
                em.add_field(name='Scout API Debug',
                             value=json.dumps(response))

            elif 'error' in response:
                if fringe is not None:
                    em.add_field(name='Fringe check', value=fringe)
                em.add_field(name='Scout API Error', value='unknown error')
                await self.bot.send_message(ctx.message.channel, embed=em)
                return
            else:
                desc1 = []
                desc2 = []
                desc1.append(desc)
                desc2.append(desc)
                xchampions = {}
                for x in response:
                    champ = await self.jm_format_champ(x['champ'])
                    if len(response) == 1:
                        em.set_thumbnail(url=champ.get_avatar())

                    v2 = 'V:{0} GV:{1} S:{2} GS:{3} GC:{4} LCDE:{5}'.format(
                        # v2 = 'v:{0} gv:{1} str:{2} gstr:{3} gc:{4} lcde:{5}'.format(
                        x["masteries"]["v"],
                        x["masteries"]["gv"],
                        x["masteries"]["s"],
                        x["masteries"]["gs"],
                        x["masteries"]["gc"],
                        x["masteries"]["lcde"])
                    if x['masteries']['lcde'] == 0:
                        v = 'No Recoil detected'
                    else:
                        v = '<:recoil:524641305347883009> Recoil activated'
                    try:
                        prettyname = '\n{0.collectoremoji}  {0.verbose_str}'.format(
                            champ)
                    except:
                        prettyname = '\n'+champ.verbose_str

                    if prettyname not in desc1:
                        desc1.append(prettyname)
                        desc2.append(prettyname)
                    desc1.append(v)
                    desc2.append(v2)

                em.description = '\n'.join(desc1)
                em2.description = '\n'.join(desc2)
                # testing as Description
                # em.add_field(name='{}  {}'.format(champ.collectoremoji, champ.star_name_str),
                #     value = v, inline=False)
                #

                # em.add_field(name='{}  {}'.format(champ.collectoremoji, champ.star_name_str),
                #     value='v:{0} gv:{1} str:{2} gstr:{3} gc:{4} lcde:{5}'.format(
                #         x["masteries"]["v"],
                #         x["masteries"]["gv"],
                #         x["masteries"]["s"],
                #         x["masteries"]["gs"],
                #         x["masteries"]["gc"],
                #         x["masteries"]["lcde"]
                #     ), inline=False
                # )
                # em.add_field(name='{}  {}'.format(champ.collectoremoji, champ.star_name_str),
                #     value='{6}  {0}   {7}  {1}  {8}  {2}  {9}  {3}  {10}  {4}  {11}{12}  {5}'.format(
                #         x["masteries"]["v"],
                #         x["masteries"]["gv"],
                #         x["masteries"]["s"],
                #         x["masteries"]["gs"],
                #         x["masteries"]["gc"],
                #         x["masteries"]["lcde"],
                #         cm['vitality']['icon'],
                #         cm['greatervitality']['icon'],
                #         cm['strength']['icon'],
                #         cm['greaterstrength']['icon'],
                #         cm['glasscanon']['icon'],
                #         cm['liquidcourage']['icon'],
                #         cm['doubleedge']['icon']
                #     ), inline=False
                # )

            em.add_field(name='Scout observed Health & Attack', value='{}, {}'.format(
                default['hp'], default['atk']), inline=False)
            em2.add_field(name='Scout observed Health & Attack', value='{}, {}'.format(
                default['hp'], default['atk']), inline=False)

            if pathdata is not None:
                em = await self.get_awnode_details(ctx, default['node'], data['difficulty'], em)
                em2 = await self.get_awnode_details(ctx, default['node'], data['difficulty'], em2)

            pages = []
            pages.append(em)
            pages.append(em2)
            menu = PagesMenu(self.bot, timeout=30,
                             delete_onX=True, add_pageof=True)
            await menu.menu_start(pages=pages)

            # await self.bot.send_message(ctx.message.channel, embed=em)

    def NodeParser(self, nargs):
        # bounderies around all matches (N34T4 not allowed)
        # starsigns '★|☆|\*' dont match bounderies (/b) that why its outside the main capturing group
        # HP and ATK from dual int match will be returned in diffrent groups then when specified with h<int> or a<int>
        # "hp12345 atk1234" will return hp:12345, atk:1234, and if entered as "... 54321 4321" hpi: 54321 atki: 4321 would be returned instead
        # changed min digits from 1 to 2 for hp,hpi,atk,atki
        # added class: as full class name or initial 2 letters
        # ~ Zlobber

        # 'class_filter' : None, 'star_filter': 0,

        default = {'tier': 0, 'difficulty': '', 'hp': 0, 'atk': 0, 'node': 0, 'nodes': '',
                   'color': discord.Color.gold(), 'debug': 0, 'test': False}
        parse_re = re.compile(r"""\b(?:t(?:ier)?(?P<tier>[0-9]{1,2})
                    | hp?(?P<hp>[0-9]{2,6})
                    | a(?:tk)?(?P<atk>[0-9]{2,5})
                    | (?P<hpi>\d{2,6})\s(?:\s)*(?P<atki>\d{2,5})
                    # | (?P<nodes>(n\d+(n\d+(n\d+(n\d+(n\d+)?)?)?)?)?)? 
                    | n(?:ode)?(?P<node>[0-9]{1,2}))
                    | (?:d(?P<debug>[0-9]{1,2}))\b
                    | (?P<star_filter>[1-6](?=(?:star|s)\b|(?:★|☆|\*)\B)) """, re.X)

        class_re = re.compile(
            r"""(?:(?P<class>sc(?:ience)?|sk(?:ill)?|mu(?:tant)?|my(?:stic)?|co(?:smic)?|te(?:ch)?))""", re.X)

        for arg in nargs.lower().split(' '):
            for m in parse_re.finditer(arg):
                default[m.lastgroup] = int(m.group(m.lastgroup))
            if arg.lower() in {'science', 'skill', 'mutant', 'mystic', 'cosmic', 'tech', 'sc', 'sk', 'mu', 'my', 'co', 'te'}:
                default['class_filter'] = arg.lower()
            elif arg.lower() in {'expert', 'challenger', 'hard', 'intermediate', 'normal', 'easy'}:
                default['difficulty'] = class_re.sub('', arg.lower())
            elif arg == 'test':
                default['test'] = True
            else:
                pass

        if default['hp'] == 0 or default['atk'] == 0:
            print('looking for hp atk raw values')
            hpatkint = [int(s) for s in nargs.split() if s.isdigit()]
            print('hptatkt len: {}'.format(len(hpatkint)))

            if len(hpatkint) == 2:
                print('found 2 integers')
                default['hp'] = max(hpatkint)
                default['atk'] = min(hpatkint)
            elif len(hpatkint) > 2:
                print('found at least 3 integers')
                default['hp'] = hpatkint.pop(hpatkint.index(max(hpatkint)))
                default['atk'] = hpatkint.pop(hpatkint.index(max(hpatkint)))
            elif len(hpatkint) == 0:
                print('found zero integers')
            else:
                print('found one integer')
                if default['hp'] == 0 and default['atk'] > 0:
                    default['hp'] = hpatkint[0]
                elif default['hp'] > 0 and default['atk'] == 0:
                    default['atk'] = hpatkint[0]
                else:
                    print('unable to determine whether value is hp or attack')

        if default['tier'] > 0:
            # if Tier provided, override given difficulty.  Because stupid people.
            default['difficulty'] = aw_tiers[int(
                default['tier'])]['diff'].lower()
            default['color'] = aw_tiers[int(default['tier'])]['color']

        return(default)

    async def jm_send_request(self, url, data):
        """Send request to service"""
        async with aiohttp.request('POST', url, data=json.dumps(data)) as response:
            if response.status == 200 or response.status == 400:
                return await response.json()
            else:
                return {'error': await response.text()}

    async def jm_format_champ(self, champ):
        """ Format champ name for display """
        print('starting jm_format_champ')
        attrs = {}
        token = champ[2:-2]
        attrs['star'] = int(champ[0])
        attrs['rank'] = int(champ[-1])
        champion = await ChampConverter.get_champion(self, self.bot, token, attrs)

        print('champ: '+champion.verbose_str)
        return champion


def setup(bot):
    bot.add_cog(Scout(bot))
