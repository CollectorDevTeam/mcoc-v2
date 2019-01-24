import discord
import asyncio
import urllib, json #For fetching JSON from alliancewar.com
import os
import requests
import re
from .utils.dataIO import dataIO
from discord.ext import commands
from .mcocTools import StaticGameData
from .mcoc import ChampConverter, ChampConverterDebug, Champion

JPAGS = 'http://www.alliancewar.com'
PATREON = 'https://patreon.com/collectorbot'
PORTRAIT = "https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/images/portraits/{}.png"
FEATURED = "https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/images/featured/{}.png"
# remote_data_basepath = "https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/"


boosts = json.loads(requests.get('https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/json/alliancewar/boosts.json').text)
aw_advanced = json.loads(requests.get('https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/json/alliancewar/aw_advanced.json').text)
aw_challenger = json.loads(requests.get('https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/json/alliancewar/aw_challenger.json').text)
aw_expert = json.loads(requests.get('https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/json/alliancewar/aw_expert.json').text)
aw_hard = json.loads(requests.get('https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/json/alliancewar/aw_hard.json').text)
aw_intermediate = json.loads(requests.get('https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/json/alliancewar/aw_intermediate.json').text)

AWD_API_URL = 'http://chocripplebot.herokuapp.com/awd'
# MAS_API_URL = 'http://chocripplebot.herokuapp.com/mas'

class MCOCMaps:
    '''Maps for Marvel Contest of Champions'''
    aw_maps = {'advanced': aw_advanced,
        'challenger': aw_challenger,
        'expert': aw_expert,
        'hard' : aw_hard,
        'intermediate': aw_intermediate
        }

    aq_map = {
        'cheatsheet':{'map':'cheatsheetv2', 'maptitle':'Season 5 Cheat Sheet'},
        '5':{'map': 's5aq5', 'maptitle':'5'},
        '5.1':{'map': 's5aq51','maptitle':'5 Tier 1'},
        '5.2':{'map':  's5aq52', 'maptitle':'5 Tier 2'},
        '5.3':{'map': 's5aq53','maptitle':'5 Tier 3'},
        '6':{'map': 's5aq6', 'maptitle':'6'},
        '6.1':{'map': 's5aq61','maptitle':'6 Tier 1'},
        '6.2':{'map':  's5aq62', 'maptitle':'6 Tier 2'},
        '6.3':{'map': 's5aq63','maptitle':'6 Tier 3'},}

    aq_map_tips = {
        'cheatsheet':{
            'required':'',
            'energy':'',
            'tips':'Sentinel gains 1 Adaptation charge(s) when an Opponent performs the same action consecutively. Actions include Light Attacks, Medium Attacks, Heavy Attacks, Dashing, Dodging, and Blocking an Attack. Max: 50 charges.\n\nMM combo = 2 Analysis Charges\nMLLM = 2 Analysis Charges\nMLLLL = 3 Analysis Charges\nLMLM = 0 Analysis Charges\n\n~ RobShiBob'},
        '5':{'required':'',
            'energy':'',
            'tips':'',},
        '5.1':{'required':'',
            'energy':'',
            'tips':'',
            'miniboss':[['Morningstar 1','+250% Champion Boost\n+200% Health\nEnhanced Bleed\nOppressive Curse'],
                ['Green Goblin 1','+250% Champion Boost\n+200% Health\nEnhanced Abilities\nRecovery 100%'],
                ['Nightcrawler 1','+250% Champion Boost\n+200% Health\nLimber (10%)\nDefensive'],]},
        '5.2':{'required':'Path A\n- Bleed Immune\nPath H\n- Poison Immune',
            'energy':'',
            'tips':'',
            'miniboss':[['Morningstar 2','+250% Champion Boost\n+300% Health\nEnhanced Bleed\nOppressive Curse\nPower Gain 100%'],
                ['Green Goblin 2','+250% Champion Boost\n+300% Health\nEnhanced Abilities\nRecovery 150%\nEnhanced Special 1'],
                ['Nightcrawler 2','+250% Champion Boost\n+300% Health\nLimber (10%)\nDefensive\nSpecial 1 Bias'],]},
        '5.3':{'required':'',
            'energy':'',
            'tips':'',
            'miniboss':[['Dormamu','+525% Champion Boost\n+100% Health\nDimensional Anchor\nHeal Block\nLimber (0.10s)\n+50% Power Gain\nUnblockable'],]},
        '6':{'required':'',
            'energy':'',
            'tips':'',},
        '6.1':{'required':'A - 2 players\nB - 2 players\nF - Power Control\nG - 2 players',
            'energy':'D & E move first\nB, C, F, G move next\nA moves last.',
            'tips':'A - Defense Ability Reduction for tile 22.\nD  - Thorns, Degeneration\nE - Thorns, Starburst\nF - All or Nothing 9\nG - Enhanced Raged Specials',
            'miniboss':[['Void 1','+300% Champion Boost\n+200% Health\nLimber (10%)\nUnblockable Finale (<25% HP)'],]},
        '6.2':{'required':'A - 2 players, Poison Immune\nB - Poison Immune\nG - Power control\nH - Bleed Immune\nI - 2 players, Bleed Immune',
            'energy': 'A, B, E, H, & I move first\nD, F, G move next\nC moves last',
            'tips':'A - Poison\nB - Poison\nC - Immunity, Stun Immunity\nE - Power Gain, Stun Immunity\nA, B, C, D, & E - Daredevil for Enhanced range special tiles 73, 63\nF - Degeneration\nG - Power Gain, All or Nothing\nH - Bleed Immune\nI -Bleed Immune',
            'miniboss':[['Void 1','+300% Champion Boost\n+300% Health\nLimber (10%)\nUnblockable Finale (<25% HP)'],]},
        '6.3':{'required':'A - Poison Immune\nB - Bleed Immune\nC - Bleed Immune\nD - Regeneration\nE - Regeneration\nF - Power Control, Regeneration\nG - Power Control\nI - Power control\nJ - Regeneration',
            'energy':'D & E move first\nC & F move second\nA, B, G & I move third\nH & J move last',
            'tips':'A - Poison\nB - Caltrops\nC - Caltrops\nA, B & C - All or Nothing tile 118\nD - Degeneration\nE - Degeneration & Starburst\nF - Starburst & Power Gain\nG - Power Gain\nH \nI - Power Gain\nJ - Starburst',
            'miniboss':[['Dormamu','+575% Champion Boost\n+200% Health\nDimensional Anchor\nHeal Block\nLimber (20%)\n+50% Power Gain\nUnblockable'],]},
    }

    lolmaps = {'0':{'map':'0', 'maptitle': 'Completion Path 0'},
        '1':{'map':'1', 'maptitle': 'Exploration Path 1'},
        '2':{'map':'2', 'maptitle': 'Exploration Path 2'},
        '3':{'map':'3', 'maptitle': 'Exploration Path 3'},
        '4':{'map':'4', 'maptitle': 'Exploration Path 4'},
        '5':{'map':'5', 'maptitle': 'Exploration Path 5'},
        '6':{'map':'6', 'maptitle': 'Exploration Path 6'},
        '7':{'map':'7', 'maptitle': 'Exploration Path 7'},}

    lollanes = {'0':['colossus','maestro'],
        '1':['spiderman','maestro'],
        '2':['starlord','thorjanefoster','abomination','guillotine','venompool','drstrange','kamalakhan','rocket','maestro'],
        '3':['colossus','magneto','daredevilnetflix','spidermanmorales','blackwidow','drstrange','moonknight','rocket','maestro'],
        '4':['groot','vision','thor','electro','hulkbuster','blackwidow','cyclops90s','rhino','maestro'],
        '5':['blackpanthercivilwar','vision','juggernaut','hulkbuster','drstrange','blackwidow','kamalakhan','rocket','maestro'],
        '6':['starlord','agentvenom','daredevilnetflix','venompool','cyclops90s','ultronprime','maestro'],
        '7':['colossus','x23','maestro']
    }

    aw_map_paths={
        'bosskill': {
            'A':[1,2,19,25,46,49,50,53],
            'B':[],
            'C':[3,21,27,41,45,47,51],
            'D':[11,17,22,28,34,36,48],
            'E':[],
            'F':[12,18,24,30,35,37,48],
            'G':[4,7,13,14,31,38,42,52],
            'H':[],
            'I':[6,9,15,14,33,40,44,55]
            },
        'expert':{
            'A':[1,19,25,46,49,50,53],
            'B':[1,2,19,20,26,41,45,47],
            'C':[3,21,27,41,45,47,51],
            'D':[11,17,22,28,34,36,48],
            'E':[10,16,23,29,48],
            'F':[12,18,24,30,35,37,48],
            'G':[4,7,13,14,31,38,42,52],
            'H':[5,8,14,32,39,43,55],
            'I':[6,9,15,14,33,40,44,55]
        },

    }

    aw_tiers = {1 : {'mult': 8.0, 'diff': 'Expert','color' :discord.Color.gold()},
                2 : {'mult': 7.0, 'diff': 'Expert','color' :discord.Color.gold()},
                3 : {'mult': 6.0, 'diff': 'Expert','color' :discord.Color.gold()},
                4 : {'mult': 4.5, 'diff': 'Challenger','color' :discord.Color.red()},
                5 : {'mult': 4.0, 'diff': 'Challenger','color' :discord.Color.red()},
                6 : {'mult': 3.4, 'diff': 'Hard','color' :discord.Color.orange()},
                7 : {'mult': 3.2, 'diff': 'Hard','color' :discord.Color.orange()},
                8 : {'mult': 3.0, 'diff': 'Hard','color' :discord.Color.orange()},
                9 : {'mult': 2.8, 'diff': 'Hard','color' :discord.Color.orange()},
                10 : {'mult': 2.4, 'diff': 'Intermediate','color' :discord.Color.blue()},
                11 : {'mult': 2.3, 'diff': 'Intermediate','color' :discord.Color.blue()},
                12 : {'mult': 2.2, 'diff': 'Intermediate','color' :discord.Color.blue()},
                13 : {'mult': 2.0, 'diff': 'Normal','color' :discord.Color.green()},
                14 : {'mult': 1.9, 'diff': 'Normal','color' :discord.Color.green()},
                15 : {'mult': 1.8, 'diff': 'Normal','color' :discord.Color.green()},
                16 : {'mult': 1.6, 'diff': 'Easy','color' :discord.Color.green()},
                17 : {'mult': 1.5, 'diff': 'Easy','color' :discord.Color.green()},
                18 : {'mult': 1.4, 'diff': 'Easy','color' :discord.Color.green()},
                19 : {'mult': 1.3, 'diff': 'Easy','color' :discord.Color.green()},
                20 : {'mult': 1.2, 'diff': 'Easy','color' :discord.Color.green()},
                21 : {'mult': 1.1, 'diff': 'Easy','color' :discord.Color.green()},
                22 : {'mult': 1.0, 'diff': 'Easy','color' :discord.Color.green()},
    }

    enigmatics = {
        'maestro':['Maestro','At the start of the fight, Maestro changes his class abilities depending on his Opponent.' \
                    '\n**vs. MYSTIC** Applies different Debuffs depending on specific actions taken by Maestro and his Opponents' \
                    '\n**vs. TECH** Receives random buffs throughout the fight.' \
                    '\n**vs. MUTANT** Powerdrain when Blocked & receives Armor Up when activating a Special 1 or 2.' \
                    '\n**vs. SKILL** Reduces Opponent Effect Accuracy when attacked.' \
                    '\n**vs. SCIENCE** Shrugs off Debuffs'],
        'colossus':['Colossus','When Blocking a Special 1 or 2, Colossus reflects his opponent\'s Attack damage back. Heavy attacks do damage equal to 1000\% of the opponent\'s max health.'],
        'spiderman':['Spider-Man','Spider-Man starts with 100\% chance to Evade passive, this is removed when he becomes Stunned. The Evade passive returns when Spider-Man activates his Special 2.'],
        'starlord':['Star-Lord','Every 15 Blocked attacks, Star-Lord receives a permanent Fury Stack, increasing his Attack by 100%'],
        'thorjanefoster':['Thor (Jane Foster)','While Blocking an attack, Thor Shocks her opponent for 100\% of her attack over 3 seconds.'],
        'abomination':['Abomination','At the beginning of the fight, Abomination excretes poison that has 100\% chance to permanently Poison the opponent for 25\% of his Attack every second.'],
        'guillotine':['Guillotine','At the beginning of the fight, Guillotine\'s ancestors slice the opponent with ghostly blades that have 100\% chance to permanently Bleed the opponent for 25\% of her Attack every second'],
        'venompool':['Venompool','When enemies activate a Buff effect, Venompool copies that Buff. Any Debuff applied to Venompool is immediately removed.'],
        'drstrange':['Dr. Strange','When Blocked, Dr. Strange steals 5\% Power from his opponents. Buff duration is increased by 100\%.'],
        'kamalakhan':['Ms. Marvel Kamala Khan','Ms. Marvel has 100\% chance to convert a Debuff to a Fury stack, increasing her Attack by 10\%. A fury stack is removed when attacked with a Special.'],
        'rocket':['Rocket Raccoon','Upon reaching 2 bars of Power, Rocket becomes Unblockable until he attacks his opponent or is attacked with a Heavy Attack.'],
        'magneto':['magneto','Magneto begins the fight with 1 bar of Power. Enemies reliant on metal suffer 100\% reduced Ability Accuracy and ar Stunned for 5 seconds when magnetized.'],
        'daredevilnetflix':['Daredevil','While opponents of Daredevil ar Blocking, they take Degeneration damage every second equal to the percentage of their health lost.'],
        'spidermanmorales':['Spider-Man Mile Morales','When Miles loses all his charges of Evasion, he gains Fury, Cruelty, Precision, and Resistances. These Enhancements are removed when his opponent activates a Special 1 or 2.'],
        'blackwidow':['Black Widow','When Black Widow activatesa Special 1 or 2, she receives an Electric Barrier for 3 seconds. If she receives an attack with the Electric Barrier active, the opponent is Stunned for 2 seconds.'],
        'moonknight':['Moon Knight','When Moon Knight activates his Special, each attack that makes contact with his opponent, a Degeneration stack is applied that deals 0.1\% direct damage every second, stacks go up to 4. These stacks are removed when Moon Knight is attacked with a Special.'],
        'groot':['Groot','Groot begins Regeneration upon eneimes activation of their Regeneration Buffs. Groot\'s Regeneration lasts for 3 seconds and increases in strength the lower he is.'],
        'vision':['Vision','Opponents of Vision lose 5\% of their Power every time they Dash backwards. If they dash backwards with 0 Power, they become Stunned for 1 second. Vision has Unblockable Special 2.'],
        'thor':['Thor','When attacked, Thor has a 5% chance to apply a Stun timer stack, up to 3, to his opponent, lasting 30 seconds. These stacks are removed when attacked with a Heavy Attack. If the timer ends, the opponent is Stunned for 2 seconds.'],
        'electro':['Electro','Every 15 seconds, Electro\'s Static Shock is enhanced for 5 seconds.'],
        'hulkbuster':['Hulkbuster','While Blocking, Hulkbuster reflects direct damage that increases exponentially in power with every attack Blocked.'],
        'cyclops90s':['Cyclops Blue Team','Upon reaching 1 bar of Power, Cyclops becomes Unblockable until he attacks his opponent or reaches 2 bars of power.'],
        'rhino':['Rhino','Rhino has 90\% Physical Resistance and takes no Damage from Physical-based Special 1 & 2 attacks.'],
        'blackpanthercivilwar':['Black Panther Civil War','At the beginning of the fight, Black Panther recieves Physical and Energy Resistance Buffs. Every 10 attacks on Black Panther, the Resistance Buffs are removed for 10 seconds.'],
        'juggernaut':['Juggernaut','Juggernaut\'s Unstoppable lasts until he is attacked with a Heavy Attack.'],
        'agentvenom':['Agent Venom','Throughout the fight, when combatants strike their opponent, they apply a timer that lasts for 3 seconds. The only way to remove the timer is to strike back and transfer it to the attacked combatant. If the timer runs out the combatant with the timer receives a Debuff that Incinerates 25% of the opponent Health as direct damage over 3 seconds.'],
        'ultronprime':['Ultron Prime','Ultron has 90\% Energy Resistance and takes no damage from Energy-Based Special 1 & 2 attacks.'],
        'x23':['Wolverine (X-23)','Every 15 seconds, Wolverine Regenerates 5\% of her Health over 3 seconds.']
    }

    basepath = 'https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/images/maps/'
    icon_sdf = 'https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/sdf_icon.png'
    COLLECTOR_ICON='https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/cdt_icon.png'


    def __init__(self, bot):
        self.bot = bot

    @commands.group(pass_context=True, aliases=['aq',])
    async def alliancequest(self, ctx):
        '''Alliance Quest Commands [WIP]'''

    @alliancequest.command(pass_context=True, name='map')
    async def _aq_map(self, ctx, *, maptype: str):
        '''Select a Map
            cheatsheet : cheatsheet
            aq maps : 5, 5.1, 5.2, 5.3, 6, 6.1, 6.2, 6.3
            /aq 5'''
        embeds = []
        if maptype in self.aq_map:
            mapurl = '{}{}.png'.format(self.basepath, self.aq_map[maptype]['map'])
            maptitle = 'Alliance Quest {}'.format(self.aq_map[maptype]['maptitle'])
            em = discord.Embed(color=discord.Color.gold(),title=maptitle,url=PATREON)
            # if 'required' in self.aq_map_tips[maptype]:
            #     em.add_field(name='Required',value=self.aq_map_tips[maptype]['required'])
            if self.aq_map_tips[maptype]['required'] != '':
                em.add_field(name='Required', value=self.aq_map_tips[maptype]['required'])
            #     em.add_field(name='Suggestions', value=self.aq_map_tips[maptype]['tips'])
            em.set_image(url=mapurl)
            em.set_footer(text='CollectorDevTeam',icon_url=self.COLLECTOR_ICON)
            embeds.append(em)
            if 'tips' in self.aq_map_tips[maptype]:
                mapurl = '{}{}.png'.format(self.basepath, self.aq_map[maptype]['map'])
                maptitle = 'Alliance Quest {}'.format(self.aq_map[maptype]['maptitle'])
                em2 = discord.Embed(color=discord.Color.gold(),title=maptitle,url=PATREON)
                em2.set_image(url=mapurl)
                em2.set_footer(text='CollectorDevTeam',icon_url=self.COLLECTOR_ICON)
                if self.aq_map_tips[maptype]['required'] != '':
                    em2.add_field(name='Required',value=self.aq_map_tips[maptype]['required'])
                if self.aq_map_tips[maptype]['energy'] != '':
                    em2.add_field(name='Energy', value=self.aq_map_tips[maptype]['energy'])
                if self.aq_map_tips[maptype]['tips'] != '':
                    em2.add_field(name='Suggestions', value=self.aq_map_tips[maptype]['tips'])
                embeds.append(em2)
            if 'miniboss' in self.aq_map_tips[maptype]:
                mapurl = '{}{}.png'.format(self.basepath, self.aq_map[maptype]['map'])
                maptitle = 'Alliance Quest {}'.format(self.aq_map[maptype]['maptitle'])
                em3 = discord.Embed(color=discord.Color.gold(),title=maptitle,url=PATREON)
                em3.set_image(url=mapurl)
                em3.set_footer(text='CollectorDevTeam',icon_url=self.COLLECTOR_ICON)
                for miniboss in self.aq_map_tips[maptype]['miniboss']:
                    em3.add_field(name=miniboss[0],value=miniboss[1])
                embeds.append(em3)
            await self.pages_menu(ctx=ctx, embed_list=embeds, timeout=120)




    @commands.command(pass_context=True, aliases=['lol'])
    async def lolmap(self, ctx, *, maptype: str = '0'):
        '''Select a Map
            LOL maps: 0, 1, 2, 3, 4, 5, 6, 7
            /lol 5'''
        if maptype in self.lolmaps:
            page_list = []
            for i in range(0, 8):
                maptitle = 'Labyrinth of Legends: Kiryu\'s {}'.format(self.lolmaps[str(i)]['maptitle'])
                em = discord.Embed(color=discord.Color.gold(),title=maptitle,url=PATREON) #, description = '\n'.join(desclist))
                mapurl = '{}lolmap{}v3.png'.format(self.basepath, i)
                em.set_image(url=mapurl)
                print(mapurl)
                lanes = self.lollanes[str(i)[0]]
                # desclist = []
                for l in lanes:
                    enigma = self.enigmatics[l]
                    print(enigma)
                    # desclist.append('{}\n{}\n\n'.format(enigma[0], enigma[1]))
                    em.add_field(name='Enigmatic {}'.format(enigma[0]), value =enigma[1])
                em.set_footer(text='Art: CollectorDevTeam, Plan: LabyrinthTeam',)
                page_list.append(em)
            await self.pages_menu(ctx=ctx, embed_list=page_list, timeout=120, page=int(maptype))
                #await self.bot.say(embed=em)

    @commands.command(pass_context=True, aliases=['lolteam, kiryu'])
    async def lolteams(self, ctx, *, team: int = 1):
        '''Highly Effective LOL Teams'''
        maxkiryu = 5
        page_list = []
        for i in range(1, maxkiryu+1):
            imgurl = '{}kiryu{}.png'.format(self.basepath, i)
            print(imgurl)
            imgtitle = 'Labyrinth of Legends: Kiryu\'s Teams #{}'.format(i)
            em = discord.Embed(color=discord.Color.gold(),title=imgtitle,url=PATREON)
            em.set_image(url=imgurl)
            em.set_footer(text='Art: CollectorDevTeam Plan: LabyrinthTeam',)
            page_list.append(em)
        await self.pages_menu(ctx=ctx, embed_list=page_list, timeout=60, page=team-1)

    @commands.command(pass_context=True)
    async def warmap(self, ctx, *, maptype: str = 'expert'):
        '''Alliance War 2.0 Map
        '''
        warmaps = {
            'expert' : '_expert'
        }
        mapurl = '{}warmap_3_expert.png'.format(self.basepath)
        mapTitle = 'Alliance War 3.0 Map'
        em = discord.Embed(color=discord.Color.gold(),title=mapTitle,url=PATREON)
        em.set_image(url=mapurl)
        em.set_footer(text='CollectorDevTeam',icon_url=self.COLLECTOR_ICON)
        await self.bot.say(embed=em)

### Beginning of Alliance Management Functions
    @commands.group(pass_context=True, hidden=True)
    async def alliance(self, ctx):
        '''Alliance Commands'''

    @alliance.command(pass_context=True, name='setalliancerole', hidden=False)
    async def _set_alliance_role(self, ctx, role : discord.Role):
        '''Alliance Set subcommands'''
        server = ctx.message.server
        if role in server.roles:
            message = await self.bot.say('Setting the Alliance Role as ``{}``\nClick OK to confirm.'.format(role.name))
            confirm = await self._confirmation(ctx, message)
            if confirm:
                await self.bot.edit_message(message,'Setting the Alliance Role as ``{}``'.format(role.name))
            else:
                await self.bot.edit_message(message,'Setting the Alliance Role as ``{}``\nOperation canceled.'.format(role.name))

    async def _confirmation(self, ctx, message):
            await self.bot.add_reaction(message, '❌')
            await self.bot.add_reaction(message, '🆗')
            react = await self.bot.wait_for_reaction(message=message, user=ctx.message.author, timeout=30, emoji=['❌', '🆗'])
            if react.reaction == None:
                await self.bot.remove_reaction(message, '❌')
                await self.bot.remove_reaction(message, '🆗')
                return False
            elif react.reaction == '❌':
                await self.bot.remove_reaction(message, '❌')
                await self.bot.remove_reaction(message, '🆗')
                return False
            elif react.reaction == '🆗':
                await self.bot.remove_reaction(message, '❌')
                await self.bot.remove_reaction(message, '🆗')
                return True


### Beginning of AllianceWar.com integration

    @commands.command(pass_context=True, hidden=True)
    async def boost_info(self, ctx, boost):
        # boosturl = 'http://www.alliancewar.com/global/ui/js/boosts.json'
        # boosts = alliancewarboosts
        keys = boosts.keys()
        if boost not in keys:
            await self.bot.say('Available boosts:\n'+'\n'.join(k for k in keys))
        else:
            info = boosts[boost]
            # img = '{}/global/ui/images/booster/{}.png'.format(JPAGS, info['img'])
            img = 'https://raw.githubusercontent.com/JPags/alliancewar_data/master/global/images/boosterr/{}.png'.format(info['img'])
            title = info['title']
            text = info['text']
            em = discord.Embed(color=discord.Color.gold(), title='Boost Info', descritpion='', url=JPAGS)
            em.set_thumbnail(url=img)
            em.add_field(name=title, value=text)
            em.set_footer(icon_url=JPAGS+'/aw/images/app_icon.jpg',text='AllianceWar.com')
            await self.bot.say(embed=em)

    @commands.group(pass_context=True, aliases=['aw',])
    async def alliancewar(self, ctx):
        '''Alliancewar.com Commands [WIP]'''

    @alliancewar.command(pass_context=True, hidden=False, name='seasons', aliases=['rewards'])
    async def _season_rewards(self, ctx, tier, rank=''):
        sgd = StaticGameData()
        cdt_sr = await sgd.get_gsheets_data('aw_season_rewards')
        col = set(cdt_sr.keys()) - {'_headers'}
        rows = ('master','platinum','gold','silver','bronze','stone','participation')
        tier = tier.lower()
        if tier in rows:
            pages=[]
            for r in (1, 2, 3, ''):
                if '{}{}'.format(tier,r) in cdt_sr['unique']:
                    em=discord.embed(color=discord.Color.gold(),title='{} {}'.format(tier.title(), rank), description=cdt_sr['{}{}'.format(tier,r)]['rewards'])

        else:
            await self.bot.say('Valid tiers: Master\nPlatinum\nGold\nSilver\nBronze\nStone\nParticipation')

    @alliancewar.command(pass_context=True, hidden=False, name="node")
    async def _node_info(self, ctx, node, tier = 'expert'):
        '''Report Node information.'''
        season = 2
        tier = tier.lower()
        if tier in self.aw_maps.keys():
            print('aw_node req: {} {}'.format(node, tier))
            em = await self.get_awnode_details(ctx = ctx, nodeNumber=int(node),tier=tier)
            await self.bot.say(embed=em)
        else:
            await self.bot.say('Valid tiers include: {}'.format(', '.join(self.aw_maps.keys())))

    @alliancewar.command(pass_context=True, hidden=True, name="nodes")
    async def _nodes_info(self, ctx, tier: str, *, nodes):
        '''Report Node information.
        This command has a reported defect and it is being investigatedself.'''
        season = 2
        tier = tier.lower()
        page_list = []
        if tier in self.aw_maps.keys():
            # nodeNumbers = nodes.split(' ')
            for node in nodes.split(' '):
                print('aw_nodes req: '+node+' '+tier)
                em = await self.get_awnode_details(ctx = ctx, nodeNumber=node,tier=tier)
                mapurl = '{}warmap_3_{}.png'.format(self.basepath,tier.lower())
                em.set_image(url=mapurl)
                page_list.append(em)
                # await self.bot.say(embed=em)
            if len(page_list) > 0:
                await self.pages_menu(ctx=ctx, embed_list=page_list, timeout=60, page=0)
        else:
            await self.bot.say('Valid tiers include: {}'.format(', '.join(self.aw_maps.keys())))


    async def get_awnode_details(self, ctx, nodeNumber, tier):
        # boosts = self.alliancewarboosts
        tiers = {
            'expert':{ 'color' :discord.Color.gold(), 'minis': [27,28,29,30,31,48,51,52,53,55], 'boss':[54]},
            'hard':{ 'color' :discord.Color.red(), 'minis': [48,51,52,53,55], 'boss':[54]},
            'challenger':{ 'color' :discord.Color.orange(), 'minis': [27,28,29,30,31,48,51,52,53,55], 'boss':[54]},
            'intermediate':{ 'color' :discord.Color.blue(), 'minis': [48,51,52,53,55], 'boss':[54]},
            'advanced':{ 'color' :discord.Color.green(), 'minis': [], 'boss':[]},
            }
        if tier not in tiers:
            tier = 'advanced'
        pathdata= self.aw_maps[tier]
        # if paths is not None:
            # await self.bot.say('DEBUG: 9path.json loaded from alliancewar.com')
        if int(nodeNumber) in tiers[tier]['minis']:
            title='{} MINIBOSS Node {} Boosts'.format(tier.title(),nodeNumber)
        elif int(nodeNumber) in tiers[tier]['boss']:
            title='{} BOSS Node {} Boosts'.format(tier.title(),nodeNumber)
        else:
            title='{} Node {} Boosts'.format(tier.title(),nodeNumber)
        em = discord.Embed(color=tiers[tier]['color'], title=title, descritpion='', url=JPAGS)
        nodedetails = pathdata['boosts'][str(nodeNumber)]
        for n in nodedetails:
            title, text = '','No description. Report to @jpags#5202'
            if ':' in n:
                nodename, bump = n.split(':')
            else:
                nodename = n
                bump = 0
            if nodename in boosts:
                title = boosts[nodename]['title']
                if boosts[nodename]['text'] is not '':
                    text = boosts[nodename]['text']
                    print('nodename: {}\ntitle: {}\ntext: {}'.format(nodename, boosts[nodename]['title'], boosts[nodename]['text']))
                    if bump is not None:
                        try:
                            text = text.format(bump)
                        except:  #wrote specifically for limber_percent
                            text = text.replace('}%}','}%').format(bump)  #wrote specifically for limber_percent
                        print('nodename: {}\ntitle: {}\nbump: {}\ntext: {}'.format(nodename, boosts[nodename]['title'], bump, boosts[nodename]['text']))
                else:
                    text = 'Description text is missing from alliancewar.com.  Report to @jpags#5202.'
            else:
                title = 'Error: {}'.format(nodename)
                value = 'Boost details for {} missing from alliancewar.com.  Report to @jpags#5202.'.format(nodename)
            em.add_field(name=title, value=text, inline=False)
        #     img = '{}/global/ui/images/booster/{}.png'.format(JPAGS, boosts['img'])
        # em.set_thumbnail(url=img)
        em.set_footer(icon_url=JPAGS+'/aw/images/app_icon.jpg',text='AllianceWar.com')
        return em

    @alliancewar.command(pass_context=True, hidden=False, name="map")
    async def _map(self, ctx, tier = 'expert'):
        '''Report AW track information.'''
        season = 2
        # boosts = self.alliancewarboosts
        # if boosts is not None:
            # await self.bot.say('DEBUG: boosts.json loaded from alliancewar.com')
        tiers = {'expert': discord.Color.gold(),'bosskill': discord.Color.gold(),'hard':discord.Color.red(),'challenger':discord.Color.orange(),'intermediate':discord.Color.blue(), 'advanced':discord.Color.green(), 'normal':discord.Color.green(), 'easy':discord.Color.green()}
        if tier.lower() in tiers:
            mapTitle = 'Alliance War 3.0 {} Map'.format(tier.title())
            if tier.lower()=='advanced' or tier.lower()=='easy':
                tier ='normal'
            mapurl = '{}warmap_3_{}.png'.format(self.basepath,tier.lower())
            em = discord.Embed(color=tiers[tier],title=mapTitle,url=PATREON)
            em.set_image(url=mapurl)
            em.set_footer(text='CollectorDevTeam',icon_url=self.COLLECTOR_ICON)
            await self.bot.say(embed=em)



    @alliancewar.command(pass_context=True, hidden=False, name="path", aliases=('tracks','track','paths'))
    async def _path_info(self, ctx, track='A', tier = 'expert'):
        '''Report AW track information.'''
        season = 2
        tiers = {'expert':discord.Color.gold(),'hard':discord.Color.red(),'challenger':discord.Color.orange(),'intermediate':discord.Color.blue(),'advanced':discord.Color.green()}
        tracks = {'A':1,'B':2,'C':3,'D':4,'E':5,'F':6,'G':7,'H':8,'I':9}

        if tier in tiers:
            # pathurl = 'http://www.alliancewar.com/aw/js/aw_s{}_{}_9path.json'.format(tier)
            if tier is 'expert':
                pathdata = aw_expert
            elif tier is 'hard':
                pathdata = aw_hard
            elif tier is 'challenger':
                pathdata = aw_challenger
            elif tier is 'advanced':
                pathdata = aw_advanced
            else:
                pathdata = aw_intermediate
            # pathdata = json.loads(requests.get(pathurl).text)
            page_list = []
            for t in tracks:
                em = discord.Embed(color=tiers[tier], title='{} Alliance War Path {}'.format(tier.title(), track), descritpion='', url=JPAGS)
                em.add_field(name='node placeholder',value='boosts placeholders')
                em.add_field(name='node placeholder',value='boosts placeholders')
                em.add_field(name='node placeholder',value='boosts placeholders')
                mapurl = '{}warmap_3_{}.png'.format(self.basepath,tier.lower())
                em.set_image(url=mapurl)
                em.set_footer(icon_url=JPAGS+'/aw/images/app_icon.jpg',text='AllianceWar.com')
                page_list.append(em)

        await self.pages_menu(ctx=ctx, embed_list=page_list, timeout=60, page=tracks[track]-1)

    @alliancewar.command(pass_context=False, hidden=False, name="tiers", aliases=('tier'))
    async def _tiers(self):
        '''List Alliance War Tiers'''
        name =  '''Tier   | Mult  | Difficulty'''
        value = '\n'.join(str(m)+'   | '+aw_tiers[m]['mult']+'   | ' + aw_tiers[m]['diff'] for m in aw_tiers.keys())
        em = discord.Embed(color=discord.Color.gold(), title='Alliance War Tiers', descritpion=desc, url=JPAGS)
        add_field(name=name, value=value)
        em.set_footer(text='CollectorDevTeam',icon_url=self.COLLECTOR_ICON)
        # em.set_image(url='https://us.v-cdn.net/6029252/uploads/editor/ok/zqyh48pgmptc.png') ## from Kabam_mike ~ Jan 2018
        await self.bot.say(embed=em)

    @alliancewar.command(pass_context=True, hidden=True, name="scout")
    async def _scout(self, ctx, *, scoutargs):
        '''
        JM's Scouter Lens inspection tool.
        The Scouter Lens Mastery must contain at least 1 point.

        Valid Options:
        <tier>  : T1 - T22, expert, challenger, hard, inter, normal, easy
        <node>  : 1 - 55
        <hp>    : hp12345, h12345, 12345
        <attack>: a1234, atk1234, 1234
        [class] : science, skill, mutant, tech, cosmic, mystic
        [star]  : 4, 5, 6

        '''

        default = self.NodeParser(scoutargs)
        keys = default.keys()

        package = []
        for key in keys:
            package.append('{} : {}'.format(key, default[key]))

        await self.bot.say('scoutlen testing')
        await self.bot.say('\n'.join(package))

        pathdata = self.aw_maps[default['difficulty']]
        title='Scout Test node {}'.format(default['node'])
        nodedetails = pathdata['boosts'][str(default['node'])]
        em = discord.Embed(color=default['color'], title=title, descritpion='', url='https://goo.gl/forms/ZgJG97KOpeSsQ2092')

        response = [{'champ':'4-electro-5','class':'science','masteries':{'v':1, 'gv':1,'s':1, 'gs':1, 'gc':1, 'lcde':0}}]

        # calls to jm service
        # response = await self.jm_send_request(AWD_API_URL, data=default)

        if 'error' in response:
            em.add_field(name='Scout API Error', value=str(response['error']))
        else:
            # result_em = discord.Embed(color=discord.Color.green(), title='Scout Results')
            avatar_url = None
            for x in response:
                # I'm probably going to override this champ thing
                champ = await self.jm_format_champ(x['champ'])
                if avatar_url is None:
                    avatar_url = PORTRAIT.format(champ.mattkraftid)
                    em.set_thumbnail(url=avatar_url)
                    # em.set_thumbnail(url=champ.get_avatar())
                em.add_field(name=champ.verbose_str,
                    value='vit:{0} gvit:{1} str:{2} gstr:{3} gc:{4} lcde:{5}'.format(
                        x["masteries"]["v"],
                        x["masteries"]["gv"],
                        x["masteries"]["s"],
                        x["masteries"]["gs"],
                        x["masteries"]["gc"],
                        x["masteries"]["lcde"]
                    )
                )
        em.add_field(name='nodedetails', value=nodedetails)
        em.add_field(name='observed hp', value='{}'.format(default['hp']))
        em.add_field(name='observed attack', value='{}'.format(default['atk']))
        em.set_thumbnail()
        em.set_footer(text='CollectorDevTeam + JM\'s Scouter Lens Bot',icon_url=self.COLLECTOR_ICON)

        await self.bot.say(embed=em)
        # champ_class = None
        # champ_classes = ('Mystic', 'Science', 'Skill', 'Mutant', 'Tech', 'Cosmic')
        # for c in champ_classes:
        #     if c in hargs:
        #         champ_class = c

    def NodeParser(self, nargs):
        # bounderies around all matches (N34T4 not allowed)
        # starsigns '★|☆|\*' dont match bounderies (/b) that why its outside the main capturing group
        # HP and ATK from dual int match will be returned in diffrent groups then when specified with h<int> or a<int>
        # "hp12345 atk1234" will return hp:12345, atk:1234, and if entered as "... 54321 4321" hpi: 54321 atki: 4321 would be returned instead
        # changed min digits from 1 to 2 for hp,hpi,atk,atki
        # added class: as full class name or initial 2 letters
        # ~ Zlobber

        default = {'tier': 0, 'difficulty' : '', 'hp': 0, 'atk': 0, 'node' : 0, 'class_filter' : None, 'star_filter': 0, 'color':discord.Color.gold()}
        parse_re = re.compile(r'''\b(?:t(?:ier)?(?P<tier>[0-9]{1,2})
                    | hp?(?P<hp>[0-9]{2,6})
                    | a(?:tk)?(?P<atk>[0-9]{2,5})
                    | (?P<hpi>\d{2,6})\s(?:\s)*(?P<atki>\d{2,5})
                    | n(?:ode)?(?P<node>[0-9]{1,2}))\b
                    | (?P<star_filter>[1-6](?=(?:star|s)\b|(?:★|☆|\*)\B)) ''', re.X)

        # class_re = re.compile(r'''(?:(?P<class>sc(?:ience)?|sk(?:ill)?|mu(?:tant)?|my(?:stic)?|co(?:smic)?|te(?:ch)?))''',re.X)

        for arg in nargs.lower().split(' '):
            for m in parse_re.finditer(arg):
                default[m.lastgroup] = int(m.group(m.lastgroup))
            if arg in {'science', 'skill', 'mutant', 'mystic', 'cosmic','tech'}:
                default['class_filter'] = arg

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
            default['difficulty'] = self.aw_tiers[default['tier']]['diff'].lower()
            default['color'] = self.aw_tiers[default['tier']]['color']

        return(default)

    async def jm_send_request(self, url, data):
        ''' Send request to service'''
        response = requests.post(url, json=data)
        if response.status_code == 200 or response.status_code == 400:
            return response.json()
        else:
            return {'error': 'unknown response'}


    async def jm_format_champ(self, champ):
        ''' Format champ name for display '''
        print('starting jm_format_champ')
        attrs = {}
        token = champ[2:-2]
        attrs['star'] = int(champ[0])
        attrs['rank'] = int(champ[-1])
        champion = await ChampConverter.get_champion(self, self.bot, token, attrs)

        # token = '{0}★{1}r{2}'.format(
        #     # self.class_emoji[champ_class], // don't need this
        #     champ[0], #star
        #     champ[2:-2], #name
        #     champ[-1] # rank
        # )
        # champion = await ChampConverter.convert(self, token)

        print('champ: '+champion.verbose_str)
        return champion

    # async def jm_parse_champ_filter(self, champ_filter):
    #     star_filter = ''.join(ch for ch in champ_filter if ch.isdigit())
    #     champ_filter = ''.join(ch for ch in champ_filter if ch.isalpha())
    #     return star_filter, champ_filter


    async def pages_menu(self, ctx, embed_list: list, category: str='', message: discord.Message=None, page=0, timeout: int=30, choice=False):
        """menu control logic for this taken from
           https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py"""
        print('list len = {}'.format(len(embed_list)))
        length = len(embed_list)
        em = embed_list[page]
        if not message:
            message = await self.bot.say(embed=em)
            # try:
            #     await self.bot.delete_message(ctx.message)
            # except:
            #     pass
            if length > 5:
                await self.bot.add_reaction(message, '⏪')
            if length > 1:
                await self.bot.add_reaction(message, '◀')
            if choice is True:
                await self.bot.add_reaction(message,'🆗')
            await self.bot.add_reaction(message, '❌')
            if length > 1:
                await self.bot.add_reaction(message, '▶')
            if length > 5:
                await self.bot.add_reaction(message, '⏩')
        else:
            message = await self.bot.edit_message(message, embed=em)
        await asyncio.sleep(1)

        react = await self.bot.wait_for_reaction(message=message, timeout=timeout,emoji=['▶', '◀', '❌', '⏪', '⏩','🆗'])
        # if react.reaction.me == self.bot.user:
        #     react = await self.bot.wait_for_reaction(message=message, timeout=timeout,emoji=['▶', '◀', '❌', '⏪', '⏩','🆗'])
        if react is None:
            try:
                try:
                    await self.bot.clear_reactions(message)
                except:
                    await self.bot.remove_reaction(message,'⏪', self.bot.user) #rewind
                    await self.bot.remove_reaction(message, '◀', self.bot.user) #previous_page
                    await self.bot.remove_reaction(message, '❌', self.bot.user) # Cancel
                    await self.bot.remove_reaction(message,'🆗',self.bot.user) #choose
                    await self.bot.remove_reaction(message, '▶', self.bot.user) #next_page
                    await self.bot.remove_reaction(message,'⏩', self.bot.user) # fast_forward
            except:
                pass
            return None
        elif react is not None:
            # react = react.reaction.emoji
            if react.reaction.emoji == '▶': #next_page
                next_page = (page + 1) % len(embed_list)
                # await self.bot.remove_reaction(message, '▶', react.user)
                await self.bot.remove_reaction(message, '▶', react.user)
                return await self.pages_menu(ctx, embed_list, message=message, page=next_page, timeout=timeout)
            elif react.reaction.emoji == '◀': #previous_page
                next_page = (page - 1) % len(embed_list)
                await self.bot.remove_reaction(message, '◀', react.user)
                return await self.pages_menu(ctx, embed_list, message=message, page=next_page, timeout=timeout)
            elif react.reaction.emoji == '⏪': #rewind
                next_page = (page - 5) % len(embed_list)
                await self.bot.remove_reaction(message, '⏪', react.user)
                return await self.pages_menu(ctx, embed_list, message=message, page=next_page, timeout=timeout)
            elif react.reaction.emoji == '⏩': # fast_forward
                next_page = (page + 5) % len(embed_list)
                await self.bot.remove_reaction(message, '⏩', react.user)
                return await self.pages_menu(ctx, embed_list, message=message, page=next_page, timeout=timeout)
            elif react.reaction.emoji == '🆗': #choose
                if choice is True:
                    # await self.bot.remove_reaction(message, '🆗', react.user)
                    prompt = await self.bot.say(SELECTION.format(category+' '))
                    answer = await self.bot.wait_for_message(timeout=10, author=ctx.message.author)
                    if answer is not None:
                        await self.bot.delete_message(prompt)
                        prompt = await self.bot.say('Process choice : {}'.format(answer.content.lower().strip()))
                        url = '{}{}/{}'.format(BASEURL,category,answer.content.lower().strip())
                        await self._process_item(ctx, url=url, category=category)
                        await self.bot.delete_message(prompt)
                else:
                    pass
            else:
                try:
                    return await self.bot.delete_message(message)
                except:
                    pass

def setup(bot):
    bot.add_cog(MCOCMaps(bot))
