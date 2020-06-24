import discord
import urllib
from discord.ext import commands
from __main__ import send_cmd_help
from .mcocTools import (CDTEmbed,
                        StaticGameData, PagesMenu, COLLECTOR_ICON)

PATREON = 'https://patreon.com/collectorbot'
JOINCDT = 'https://discord.gg/BwhgZxk'
# remote_data_basepath = "https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/"
basepath = 'https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/images/maps/'
catcorner = '{}catmurdock/cat_corner_left.png'.format(
    basepath)
catsupport = 'Visit Cat\'s [Store](https://www.redbubble.com/people/CatMurdock/explore)\n'\
    '<:twitter:548637190587154432>[@CatMurdock_art](https://twitter.com/CatMurdock_Art)'
aq_map = {
    'cheatsheet': {'map': 'cheatsheetv2', 'maptitle': 'Season 5 Cheat Sheet'},
    '5': {'map': 's5aq5', 'maptitle': '5'},
    '5.1': {'map': 's5aq51', 'maptitle': '5 Tier 1'},
    '5.2': {'map':  's5aq52', 'maptitle': '5 Tier 2'},
    '5.3': {'map': 's5aq53', 'maptitle': '5 Tier 3'},
    '7': {'map': 's7aq7', 'maptitle': '7'},
    '7.1': {'map': 's7aq71', 'maptitle': '7 Tier 1'},
    '7.2': {'map':  's7aq72', 'maptitle': '7 Tier 2'},
    '7.3': {'map': 's7aq73', 'maptitle': '7 Tier 3'}}

aq_map_tips = {
    'cheatsheet': {
        'required': '',
        'energy': '',
        'tips': 'Sentinel gains 1 Adaptation charge(s) when an Opponent performs the same action consecutively. Actions include Light Attacks, Medium Attacks, Heavy Attacks, Dashing, Dodging, and Blocking an Attack. Max: 50 charges.\n\nMM combo = 2 Analysis Charges\nMLLM = 2 Analysis Charges\nMLLLL = 3 Analysis Charges\nLMLM = 0 Analysis Charges\n\n~ RobShiBob'},
    '5': {'required': '',
          'energy': '',
          'tips': '', },
    '5.1': {'required': '',
            'energy': '',
            'tips': '',
            'miniboss': [['Morningstar 1', '+250% Champion Boost\n+200% Health\nEnhanced Bleed\nOppressive Curse'],
                         ['Green Goblin 1', '+250% Champion Boost\n+200% Health\nEnhanced Abilities\nRecovery 100%'],
                         ['Nightcrawler 1', '+250% Champion Boost\n+200% Health\nLimber (10%)\nDefensive'], ]},
    '5.2': {'required': 'Path A\n- Bleed Immune\nPath H\n- Poison Immune',
            'energy': '',
            'tips': '',
            'miniboss': [['Morningstar 2', '+250% Champion Boost\n+300% Health\nEnhanced Bleed\nOppressive Curse\nPower Gain 100%'],
                         ['Green Goblin 2', '+250% Champion Boost\n+300% Health\nEnhanced Abilities\nRecovery 150%\nEnhanced Special 1'],
                         ['Nightcrawler 2', '+250% Champion Boost\n+300% Health\nLimber (10%)\nDefensive\nSpecial 1 Bias'], ]},
    '5.3': {'required': '',
            'energy': '',
            'tips': '',
            'miniboss': [['Kingpin', '+525% Champion Boost\n+100% Health\nDimensional Anchor\nHeal Block\nLimber (0.10s)\n+50% Power Gain\nUnblockable'], ]},
    '6': {'required': '',
          'energy': '',
          'tips': '', },
    '6.1': {'required': 'A - 2 players\nB - 2 players\nF - Power Control\nG - 2 players',
            'energy': 'D & E move first\nB, C, F, G move next\nA moves last.',
            'tips': 'A - Defense Ability Reduction for tile 22.\nD  - Thorns, Degeneration\nE - Thorns, Starburst\nF - All or Nothing 9\nG - Enhanced Raged Specials',
            'miniboss': [['Void 1',
                          'Champion Boost: 300% Attack & Health\n'
                          'Health: 200% Health\n'
                          'Limber: Each time the Defender receives a Stun Debuff, '
                          'they reduce the Duration of further Stun Debuffs by 0.10 seconds.\n'
                          'Unblockable Finale: Attacks are unblockable as long as Health remains below 25%.'],
                         ['Yondu 1',
                             'Champion Boost: 300% Attack & Health '
                             'Health: 200% Health\n'
                             'Enhanced Bleed: Bleed abilities are 40% more effective.\n'
                             'Collar Tech V: Gives Tech Champions a field that inhibits enemy Power Gain by 18%\n'
                             'Special 2 Bias: This defender is more likely to activate Special Attack 2'],
                         ['Mephisto 1',
                             'Champion Boost: 300% Attack & Health\n '
                             'Health: 200% Health\n ']]},
    '6.2': {'required': 'A - 2 players, Poison Immune\nB - Poison Immune\nG - Power control\nH - Bleed Immune\nI - 2 players, Bleed Immune',
            'energy': 'A, B, E, H, & I move first\nD, F, G move next\nC moves last',
            'tips': 'A - Poison\nB - Poison\nC - Immunity, Stun Immunity\nE - Power Gain, Stun Immunity\nA, B, C, D, & E - Daredevil for Enhanced range special tiles 73, 63\nF - Degeneration\nG - Power Gain, All or Nothing\nH - Bleed Immune\nI -Bleed Immune',
            'miniboss': [['Void 1',
                          'Champion Boost: 300% Attack & Health\n'
                          'Health: 300% Health\n'
                          'Limber: Each time the Defender receives a Stun Debuff, '
                          'they reduce the Duration of further Stun Debuffs by 0.10 seconds.\n'
                          'Unblockable Finale: Attacks are unblockable as long as Health remains below 25%.'],
                         ['Mephisto 2',
                             'Champion Boost: 300% Attack & Health\n'
                             'Health: 300% Health\n'
                             '\n'],
                         ['Yondu 2',
                             'Champion Boost: 300% Attack & Health\n'
                             'Health: 300% Health\n'
                             'Enhanced Bleed: Bleed abilities are 40% more effective.\n'
                             'Collar Tech V: Gives Tech Champions a field that inhibits enemy Power Gain by 18%\n'
                             'Enhanced Special 2: Special 2 deals 20% more damage and cannot be Blocked\n'
                             'Special 2 Bias: This defender is more likely to activate Special Attack 2']]},
    '6.3': {'required': 'A - Poison Immune\nB - Bleed Immune\nC - Bleed Immune\nD - Regeneration\nE - Regeneration\nF - Power Control, Regeneration\nG - Power Control\nI - Power control\nJ - Regeneration',
            'energy': 'D & E move first\nC & F move second\nA, B, G & I move third\nH & J move last',
            'tips': 'A - Poison\nB - Caltrops\nC - Caltrops\nA, B & C - All or Nothing tile 118\nD - Degeneration\nE - Degeneration & Starburst\nF - Starburst & Power Gain\nG - Power Gain\nH \nI - Power Gain\nJ - Starburst',
            'miniboss': [['Kingpin', '+575% Champion Boost\n+200% Health\nDimensional Anchor\nHeal Block\nLimber (20%)\n+50% Power Gain\nUnblockable'], ]},
    '7': {'required': '',
          'energy': '',
          'tips': '', },
    '7.1': {'required': '',
            'energy': '',
            'tips': '', },
    '7.2': {'required': '',
            'energy': '',
            'tips': '', },
    '7.3': {'required': '',
            'energy': '',
            'tips': '', },
}

lolmaps = {'0': {'map': '0', 'maptitle': 'Completion Path 0'},
           '1': {'map': '1', 'maptitle': 'Exploration Path 1'},
           '2': {'map': '2', 'maptitle': 'Exploration Path 2'},
           '3': {'map': '3', 'maptitle': 'Exploration Path 3'},
           '4': {'map': '4', 'maptitle': 'Exploration Path 4'},
           '5': {'map': '5', 'maptitle': 'Exploration Path 5'},
           '6': {'map': '6', 'maptitle': 'Exploration Path 6'},
           '7': {'map': '7', 'maptitle': 'Exploration Path 7'}, }

lollanes = {'0': ['colossus', 'maestro'],
            '1': ['spiderman', 'maestro'],
            '2': ['starlord', 'thorjanefoster', 'abomination', 'guillotine', 'venompool', 'drstrange', 'kamalakhan', 'rocket', 'maestro'],
            '3': ['colossus', 'magneto', 'daredevilnetflix', 'spidermanmorales', 'blackwidow', 'drstrange', 'moonknight', 'rocket', 'maestro'],
            '4': ['groot', 'vision', 'thor', 'electro', 'hulkbuster', 'blackwidow', 'cyclops90s', 'rhino', 'maestro'],
            '5': ['blackpanthercivilwar', 'vision', 'juggernaut', 'hulkbuster', 'drstrange', 'blackwidow', 'kamalakhan', 'rocket', 'maestro'],
            '6': ['starlord', 'agentvenom', 'daredevilnetflix', 'venompool', 'cyclops90s', 'ultronprime', 'maestro'],
            '7': ['colossus', 'x23', 'maestro']
            }

enigmatics = {
    'maestro': ['Maestro', 'At the start of the fight, Maestro changes his class abilities depending on his Opponent.'
                '\n**vs. MYSTIC** Applies different Debuffs depending on specific actions taken by Maestro and his Opponents'
                '\n**vs. TECH** Receives random buffs throughout the fight.'
                '\n**vs. MUTANT** Powerdrain when Blocked & receives Armor Up when activating a Special 1 or 2.'
                '\n**vs. SKILL** Reduces Opponent Effect Accuracy when attacked.'
                '\n**vs. SCIENCE** Shrugs off Debuffs'],
    'colossus': ['Colossus', 'When Blocking a Special 1 or 2, Colossus reflects his opponent\'s Attack damage back. Heavy attacks do damage equal to 1000\% of the opponent\'s max health.'],
    'spiderman': ['Spider-Man', 'Spider-Man starts with 100\% chance to Evade passive, this is removed when he becomes Stunned. The Evade passive returns when Spider-Man activates his Special 2.'],
    'starlord': ['Star-Lord', 'Every 15 Blocked attacks, Star-Lord receives a permanent Fury Stack, increasing his Attack by 100%'],
    'thorjanefoster': ['Thor (Jane Foster)', 'While Blocking an attack, Thor Shocks her opponent for 100\% of her attack over 3 seconds.'],
    'abomination': ['Abomination', 'At the beginning of the fight, Abomination excretes poison that has 100\% chance to permanently Poison the opponent for 25\% of his Attack every second.'],
    'guillotine': ['Guillotine', 'At the beginning of the fight, Guillotine\'s ancestors slice the opponent with ghostly blades that have 100\% chance to permanently Bleed the opponent for 25\% of her Attack every second'],
    'venompool': ['Venompool', 'When enemies activate a Buff effect, Venompool copies that Buff. Any Debuff applied to Venompool is immediately removed.'],
    'drstrange': ['Dr. Strange', 'When Blocked, Dr. Strange steals 5\% Power from his opponents. Buff duration is increased by 100\%.'],
    'kamalakhan': ['Ms. Marvel Kamala Khan', 'Ms. Marvel has 100\% chance to convert a Debuff to a Fury stack, increasing her Attack by 10\%. A fury stack is removed when attacked with a Special.'],
    'rocket': ['Rocket Raccoon', 'Upon reaching 2 bars of Power, Rocket becomes Unblockable until he attacks his opponent or is attacked with a Heavy Attack.'],
    'magneto': ['magneto', 'Magneto begins the fight with 1 bar of Power. Enemies reliant on metal suffer 100\% reduced Ability Accuracy and ar Stunned for 5 seconds when magnetized.'],
    'daredevilnetflix': ['Daredevil', 'While opponents of Daredevil ar Blocking, they take Degeneration damage every second equal to the percentage of their health lost.'],
    'spidermanmorales': ['Spider-Man Mile Morales', 'When Miles loses all his charges of Evasion, he gains Fury, Cruelty, Precision, and Resistances. These Enhancements are removed when his opponent activates a Special 1 or 2.'],
    'blackwidow': ['Black Widow', 'When Black Widow activatesa Special 1 or 2, she receives an Electric Barrier for 3 seconds. If she receives an attack with the Electric Barrier active, the opponent is Stunned for 2 seconds.'],
    'moonknight': ['Moon Knight', 'When Moon Knight activates his Special, each attack that makes contact with his opponent, a Degeneration stack is applied that deals 0.1\% direct damage every second, stacks go up to 4. These stacks are removed when Moon Knight is attacked with a Special.'],
    'groot': ['Groot', 'Groot begins Regeneration upon eneimes activation of their Regeneration Buffs. Groot\'s Regeneration lasts for 3 seconds and increases in strength the lower he is.'],
    'vision': ['Vision', 'Opponents of Vision lose 5\% of their Power every time they Dash backwards. If they dash backwards with 0 Power, they become Stunned for 1 second. Vision has Unblockable Special 2.'],
    'thor': ['Thor', 'When attacked, Thor has a 5% chance to apply a Stun timer stack, up to 3, to his opponent, lasting 30 seconds. These stacks are removed when attacked with a Heavy Attack. If the timer ends, the opponent is Stunned for 2 seconds.'],
    'electro': ['Electro', 'Every 15 seconds, Electro\'s Static Shock is enhanced for 5 seconds.'],
    'hulkbuster': ['Hulkbuster', 'While Blocking, Hulkbuster reflects direct damage that increases exponentially in power with every attack Blocked.'],
    'cyclops90s': ['Cyclops Blue Team', 'Upon reaching 1 bar of Power, Cyclops becomes Unblockable until he attacks his opponent or reaches 2 bars of power.'],
    'rhino': ['Rhino', 'Rhino has 90\% Physical Resistance and takes no Damage from Physical-based Special 1 & 2 attacks.'],
    'blackpanthercivilwar': ['Black Panther Civil War', 'At the beginning of the fight, Black Panther recieves Physical and Energy Resistance Buffs. Every 10 attacks on Black Panther, the Resistance Buffs are removed for 10 seconds.'],
    'juggernaut': ['Juggernaut', 'Juggernaut\'s Unstoppable lasts until he is attacked with a Heavy Attack.'],
    'agentvenom': ['Agent Venom', 'Throughout the fight, when combatants strike their opponent, they apply a timer that lasts for 3 seconds. The only way to remove the timer is to strike back and transfer it to the attacked combatant. If the timer runs out the combatant with the timer receives a Debuff that Incinerates 25% of the opponent Health as direct damage over 3 seconds.'],
    'ultronprime': ['Ultron Prime', 'Ultron has 90\% Energy Resistance and takes no damage from Energy-Based Special 1 & 2 attacks.'],
    'x23': ['Wolverine (X-23)', 'Every 15 seconds, Wolverine Regenerates 5\% of her Health over 3 seconds.']
}


class MCOCMaps:
    """Maps for Marvel Contest of Champions"""

    def __init__(self, bot):
        self.bot = bot
        self.diagnostics = self.bot.get_channel('725397961072181349')
        self.catmurdock = self.bot.get_member('373128988962586635')
        self.jjw = self.bot.get_member('124984294035816448')

    @commands.group(pass_context=True, aliases=('map',))
    async def maps(self, ctx):
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @maps.command(pass_context=True, name='aq', aliases=('alliancequest',))
    async def maps_alliancequest(self, ctx, maptype: str = None):
        """Alliance Quest Maps
            cheatsheet : cheatsheet
            aq maps : 5, 5.1, 5.2, 5.3, 7.1, 7.2, 7.3
            cat maps: 6, 6.1, 6.2, 6.3
            /aq 5"""
        author = ctx.message.author
        embeds = []
        cat_maps = {
            '6.1': {'map': ['aq_6_v1_s1', 'aq_6_v2_s1'], 'maptitle': '6 Tier 1'},
            '6.2': {'map': ['aq_6_v1_s2', 'aq_6_v2_s2'], 'maptitle': '6 Tier 2'},
            '6.3': {'map': ['aq_6_v1_s3', 'aq_6_v2_s3'], 'maptitle': '6 Tier 3'},
        }
        if maptype in cat_maps.keys():
            for i in (0, 1):
                mapurl = '{}catmurdock/AQ/{}.png'.format(
                    basepath, cat_maps[maptype]['map'][i])
                maptitle = 'Alliance Quest {} :smiley_cat::sparkles:| Variation {}'.format(
                    cat_maps[maptype]['maptitle'], i+1)
                data = CDTEmbed.get_embed(
                    self, ctx, image=mapurl, thumbnail=catcorner, title=maptitle)
                data.set_author(name=self.catmurdock.display_name,
                                icon_url=self.catmurdock.avatar_url)
                data.add_field(
                    name='Support Cat', value=catsupport)
                embeds.append(data)
            menu = PagesMenu(self.bot, timeout=120,
                             delete_onX=True, add_pageof=True)
            await menu.menu_start(pages=embeds)
            return
        elif maptype in ('7', '7.1', '7.2', '7.3'):
            seven = {'A': '1', 'B': '2', 'C': '3'}
            for k in seven.keys():
                mapurl = '{}{}{}.png'.format(
                    basepath, aq_map[maptype]['map'], k)
                maptitle = 'Alliance Quest {} | Variation {}'.format(
                    aq_map[maptype]['maptitle'], seven[k])
                data = CDTEmbed.get_embed(
                    self, ctx, title=maptitle, image=mapurl)
                data.set_author(
                    name='JJW | CollectorDevTeam', icon_url=self.jjw.avatar_url)
                embeds.append(data)
            menu = PagesMenu(self.bot, timeout=30,
                             delete_onX=True, add_pageof=True)
            await menu.menu_start(pages=embeds)
            return
        elif maptype in aq_map:
            mapurl = '{}{}.png'.format(
                basepath, aq_map[maptype]['map'])
            maptitle = 'Alliance Quest {}'.format(
                aq_map[maptype]['maptitle'])
            data = CDTEmbed.get_embed(self, ctx, title=maptitle, image=mapurl)
            data.set_author(
                name='JJW | CollectorDevTeam', icon_url=self.jjw.avatar_url)
            if aq_map_tips[maptype]['required'] != '':
                data.add_field(name='Required',
                               value=aq_map_tips[maptype]['required'])
            #     em.add_field(name='Suggestions', value=aq_map_tips[maptype]['tips'])
            # em.set_image(url=mapurl)
            embeds.append(data)
            if 'tips' in aq_map_tips[maptype]:
                mapurl = '{}{}.png'.format(
                    basepath, aq_map[maptype]['map'])
                maptitle = 'Alliance Quest {}'.format(
                    aq_map[maptype]['maptitle'])
                em2 = CDTEmbed.get_embed(
                    self, ctx, title=maptitle, image=mapurl)

                if aq_map_tips[maptype]['required'] != '':
                    em2.add_field(name='Required',
                                  value=aq_map_tips[maptype]['required'])
                if aq_map_tips[maptype]['energy'] != '':
                    em2.add_field(
                        name='Energy', value=aq_map_tips[maptype]['energy'])
                if aq_map_tips[maptype]['tips'] != '':
                    em2.add_field(name='Suggestions',
                                  value=aq_map_tips[maptype]['tips'])
                embeds.append(em2)
            if 'miniboss' in aq_map_tips[maptype]:
                mapurl = '{}{}.png'.format(
                    basepath, aq_map[maptype]['map'])
                maptitle = 'Alliance Quest {}'.format(
                    aq_map[maptype]['maptitle'])
                em3 = CDTEmbed.get_embed(
                    self, ctx, title=maptitle, image=mapurl)
                for miniboss in aq_map_tips[maptype]['miniboss']:
                    em3.add_field(name=miniboss[0], value=miniboss[1])
                embeds.append(em3)
            menu = PagesMenu(self.bot, timeout=30,
                             delete_onX=True, add_pageof=True)
            await menu.menu_start(pages=embeds)
        else:
            desc = 'Currently supporting AQ maps:\nAQ 5: 5.1, 5.2, 5.3\nAQ 6: 6.1, 6.2, 6.3\nAQ 7: 7.1, 7.2, 7.3'
            data = CDTEmbed.get_embed(
                self, ctx, title='Alliance Quest Maps', description=desc)
            await self.bot.send_message(ctx.message.channel, embed=data)

    @maps.command(pass_context=True, name='aw', aliases=('war', 'alliancewar',))
    async def maps_alliancewar(self, ctx, tier=None):
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
                data = CDTEmbed.get_embed(self, ctx,
                                          image='{}catmurdock/AW/{}.png'.format(
                                              basepath, tier),
                                          thumbnail=catcorner,
                                          title='Alliane War {} Map :cat::sparkles:'.format(
                                              tier.title()))
                data.set_author(name=self.catmurdock.display_name,
                                icon_url=self.catmurdock.avatar_url)
                data.add_field(
                    name='Support Cat', value=catsupport)
                pages.append(data)
            menu = PagesMenu(self.bot, timeout=30,
                             delete_onX=True, add_pageof=True)
            await menu.menu_start(pages)
        elif tier.lower() in warmaps:
            mapurl = '{}catmurdock/AW/{}.png'.format(
                basepath, tier.lower())
            data = CDTEmbed.get_embed(self, ctx,
                                      image='{}catmurdock/AW/{}.png'.format(
                                          basepath, tier.lower()),
                                      thumbnail=catcorner,
                                      title='Alliane War {} Map :cat::sparkles:'.format(
                                          tier.title()))
            data.set_author(name=self.catmurdock.display_name,
                            icon_url=self.catmurdock.avatar_url)
            data.add_field(
                name='Support Cat', value=catsupport)
            await self.bot.send_message(ctx.message.channel, embed=data)
        else:
            desc = 'Currently supporting \nChallenger\nIntermediate\nHard\nExpert'
            data = CDTEmbed.get_embed(self, ctx, title='Alliance War Maps :cat::sparkles:'.format(
                tier.title()), thumbnail=catcorner, description=desc)
            data.set_author(name=self.catmurdock.display_name,
                            icon_url=self.catmurdock.avatar_url)
            data.add_field(
                name='Support Cat', value=catsupport)
            await self.bot.send_message(ctx.message.channel, embed=data)

    @maps.command(pass_context=True, name='sq', aliases=('story',))
    async def maps_storyquest(self, ctx, level: str = None):
        '''Currently supporting Cat Murdock maps for 6.1 and 6.4'''
        cat_maps = ('6.1.1', '6.1.2', '6.1.3', '6.1.4', '6.1.5', '6.1.6',
                    '6.4.1', '6.4.2', '6.4.3', '6.4.4', '6.4.5', '6.4.6')
        if level is None:
            pages = []
            for catmap in cat_maps:
                mapurl = '{}catmurdock/SQ/sq_{}.png'.format(
                    basepath, catmap)
                data = CDTEmbed.get_embed(self, ctx, title='Act {} Map :cat::sparkles:'.format(
                    catmap), image=mapurl, thumbnail=catcorner)
                data.set_author(name=self.catmurdock.display_name,
                                icon_url=self.catmurdock.avatar_url)
                data.add_field(
                    name='Support Cat', value=catsupport)
                pages.append(data)
            menu = PagesMenu(self.bot, timeout=30,
                             delete_onX=True, add_pageof=True)
            await menu.menu_start(pages)
        elif level is not None and level in cat_maps:
            data = CDTEmbed.get_embed(self, ctx, title='Act {} Map by :cat::sparkles:'.format(
                level), image='{}catmurdock/SQ/sq_{}.png'.format(basepath, level), thumbnail=catcorner)
            data.set_author(name=self.catmurdock.display_name,
                            icon_url=self.catmurdock.avatar_url)
            data.add_field(
                name='Support Cat', value=catsupport)

            await self.bot.send_message(ctx.message.channel, embed=data)
        else:
            data = CDTEmbed.get_embed(self, ctx, title='Available Story Quest Maps :cat::sparkles:',
                                      description='Act 6.1:\n6.1.1, 6.1.2, 6.1.3, 6.1.4, 6.1.5, 6.1.6\n'
                                      'Act 6.4:\n6.4: 6.4.1, 6.4.1, 6.4.3, 6.4.4, 6.4.5, 6.4.6',
                                      thumbnail=catcorner)
            data.set_author(name=self.catmurdock.display_name,
                            icon_url=self.catmurdock.avatar_url)
            data.add_field(name="Want more?", value=catsupport)
            await self.bot.send_message(ctx.message.channel, embed=data)

    @maps.command(pass_context=True, name='lol', aliases=['lab', ])
    async def maps_lol(self, ctx, *, maptype: str = '0'):
        """Labyrinth of Legends Maps
            LOL maps: 0, 1, 2, 3, 4, 5, 6, 7
            /lol 5"""
        if maptype in lolmaps:
            pages = []
            for i in range(0, 8):
                maptitle = 'Labyrinth of Legends: {}'.format(
                    lolmaps[str(i)]['maptitle'])
                data = CDTEmbed.get_embed(
                    self, ctx, title=maptitle, image='{}lolmap{}v3.png'.format(basepath, i))
                lanes = lollanes[str(i)[0]]
                # desclist = []
                for l in lanes:
                    enigma = enigmatics[l]
                    print(enigma)
                    # desclist.append('{}\n{}\n\n'.format(enigma[0], enigma[1]))
                    data.add_field(name='Enigmatic {}'.format(
                        enigma[0]), value=enigma[1])
                pages.append(data)
            menu = PagesMenu(self.bot, timeout=30,
                             delete_onX=True, add_pageof=True)
            await menu.menu_start(pages=pages, page_number=int(maptype))
            # await self.bot.send_message(ctx.message.channel, embed=em)


def setup(bot):
    bot.add_cog(MCOCMaps(bot))
