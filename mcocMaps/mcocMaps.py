import discord
from discord.ext import commands
import json
from __main__ import send_cmd_help
from .mcocTools import (CDTEmbed, PagesMenu, DIAGNOSTICS)
from .utils import chat_formatting as chat

basepath = "https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/images/maps/"
catcorner = "{}catmurdock/cat_corner_left.png".format(
    basepath)
catsupport = "Visit Cat\"s [Store](https://www.redbubble.com/people/CatMurdock/explore)\n"\
    "<:twitter:548637190587154432>[@CatMurdock_art](https://twitter.com/CatMurdock_Art)"


class MCOCMaps:
    """Maps for Marvel Contest of Champions"""

    def __init__(self, bot):
        self.bot = bot
        self.diagnostics = DIAGNOSTICS(self.bot)
        self.settings = {}
        self.jjw = None
        self.catmurdock = None
        self.channel = None
        self.get_stuffs()

    @commands.group(pass_context=True, aliases=("map",))
    async def maps(self, ctx):
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
        msg = self.diagnostics.log(ctx)
        await self.bot.send_message(self.channel, msg)

    @maps.command(pass_context=True, name='settings', hidden=True)
    async def maps_settings(self, ctx):
        paged = chat.pagify(self.settings.items())
        boxed = []
        boxed.append(chat.box(p) for p in paged)
        for b in boxed:
            await self.bot.send_message(self.channel, b)

    @maps.command(pass_context=True, name="aq", aliases=("alliancequest",))
    async def maps_alliancequest(self, ctx, maptype: str = None):
        """Alliance Quest Maps
            cheatsheet : cheatsheet
            aq maps : 5, 5.1, 5.2, 5.3, 7.1, 7.2, 7.3
            cat maps: 6, 6.1, 6.2, 6.3
            /aq 5"""
        author = ctx.message.author
        embeds = []
        cat_maps = {
            "6.1": {"map": ["aq_6_v1_s1", "aq_6_v2_s1"], "maptitle": "6 Tier 1"},
            "6.2": {"map": ["aq_6_v1_s2", "aq_6_v2_s2"], "maptitle": "6 Tier 2"},
            "6.3": {"map": ["aq_6_v1_s3", "aq_6_v2_s3"], "maptitle": "6 Tier 3"},
        }
        if maptype in cat_maps.keys():
            for i in (0, 1):
                mapurl = "{}catmurdock/AQ/{}.png".format(
                    basepath, cat_maps[maptype]["map"][i])
                maptitle = "Alliance Quest {} :smiley_cat::sparkles:| Variation {}".format(
                    cat_maps[maptype]["maptitle"], i+1)
                data = CDTEmbed.get_embed(
                    self, ctx, image=mapurl, thumbnail=catcorner, title=maptitle)
                data.set_author(name=self.catmurdock.display_name,
                                icon_url=self.catmurdock.avatar_url)
                data.add_field(
                    name="Support Cat", value=catsupport)
                embeds.append(data)
            menu = PagesMenu(self.bot, timeout=120,
                             delete_onX=True, add_pageof=True)
            await menu.menu_start(pages=embeds)
            return
        elif maptype in ("7", "7.1", "7.2", "7.3"):
            seven = {"A": "1", "B": "2", "C": "3"}
            for k in seven.keys():
                mapurl = "{}{}{}.png".format(
                    basepath, self.settings["aq_map"][maptype]["map"], k)
                maptitle = "Alliance Quest {} | Variation {}".format(
                    self.settings["aq_map"][maptype]["maptitle"], seven[k])
                data = CDTEmbed.get_embed(
                    self, ctx, title=maptitle, image=mapurl)
                data.set_author(
                    name="JJW | CollectorDevTeam", icon_url=self.jjw.avatar_url)
                embeds.append(data)
            menu = PagesMenu(self.bot, timeout=30,
                             delete_onX=True, add_pageof=True)
            await menu.menu_start(pages=embeds)
            return
        elif maptype in self.settings["aq_map"].keys():
            mapurl = "{}{}.png".format(
                basepath, self.settings["aq_map"][maptype]["map"])
            maptitle = "Alliance Quest {}".format(
                self.settings["aq_map"][maptype]["maptitle"])
            data = CDTEmbed.get_embed(self, ctx, title=maptitle, image=mapurl)
            data.set_author(
                name="JJW | CollectorDevTeam", icon_url=self.jjw.avatar_url)
            if self.settings["aq_map_tips"][maptype]["required"] != "":
                data.add_field(name="Required",
                               value=self.settings["aq_map_tips"][maptype]["required"])
            #     em.add_field(name="Suggestions", value=self.settings["aq_map_tips"][maptype]["tips"])
            # em.set_image(url=mapurl)
            embeds.append(data)
            if "tips" in self.settings["aq_map_tips"][maptype].keys():
                mapurl = "{}{}.png".format(
                    basepath, self.settings["aq_map"][maptype]["map"])
                maptitle = "Alliance Quest {}".format(
                    self.settings["aq_map"][maptype]["maptitle"])
                em2 = CDTEmbed.get_embed(
                    self, ctx, title=maptitle, image=mapurl)

                if self.settings["aq_map_tips"][maptype]["required"] != "":
                    em2.add_field(name="Required",
                                  value=self.settings["aq_map_tips"][maptype]["required"])
                if self.settings["aq_map_tips"][maptype]["energy"] != "":
                    em2.add_field(
                        name="Energy", value=self.settings["aq_map_tips"][maptype]["energy"])
                if self.settings["aq_map_tips"][maptype]["tips"] != "":
                    em2.add_field(name="Suggestions",
                                  value=self.settings["aq_map_tips"][maptype]["tips"])
                embeds.append(em2)
            if "miniboss" in self.settings["aq_map_tips"][maptype].keys():
                mapurl = "{}{}.png".format(
                    basepath, self.settings["aq_map"][maptype]["map"])
                maptitle = "Alliance Quest {}".format(
                    self.settings["aq_map"][maptype]["maptitle"])
                em3 = CDTEmbed.get_embed(
                    self, ctx, title=maptitle, image=mapurl)
                for miniboss in self.settings["aq_map_tips"][maptype]["miniboss"]:
                    em3.add_field(name=miniboss[0], value=miniboss[1])
                embeds.append(em3)
            menu = PagesMenu(self.bot, timeout=30,
                             delete_onX=True, add_pageof=True)
            await menu.menu_start(pages=embeds)
        else:
            desc = "Currently supporting AQ maps:\nAQ 5: 5.1, 5.2, 5.3\nAQ 6: 6.1, 6.2, 6.3\nAQ 7: 7.1, 7.2, 7.3"
            data = CDTEmbed.get_embed(
                self, ctx, title="Alliance Quest Maps", description=desc)
            await self.bot.send_message(ctx.message.channel, embed=data)

    @maps.command(pass_context=True, name="aw", aliases=("war", "alliancewar",))
    async def maps_alliancewar(self, ctx, tier=None):
        """Alliance War Maps by Cat Murdock:
        Challenger
        Intermediate
        Hard
        Expert
        """
        warmaps = ("challenger", "expert", "hard", "intermediate")
        if tier is None:
            pages = []
            for tier in ("challenger", "intermediate", "hard", "expert"):
                data = CDTEmbed.get_embed(self, ctx,
                                          image="{}catmurdock/AW/{}.png".format(
                                              basepath, tier),
                                          thumbnail=catcorner,
                                          title="Alliane War {} Map :cat::sparkles:".format(
                                              tier.title()))
                data.set_author(name=self.catmurdock.display_name,
                                icon_url=self.catmurdock.avatar_url)
                data.add_field(
                    name="Support Cat", value=catsupport)
                pages.append(data)
            menu = PagesMenu(self.bot, timeout=30,
                             delete_onX=True, add_pageof=True)
            await menu.menu_start(pages)
        elif tier.lower() in warmaps:
            mapurl = "{}catmurdock/AW/{}.png".format(
                basepath, tier.lower())
            data = CDTEmbed.get_embed(self, ctx,
                                      image="{}catmurdock/AW/{}.png".format(
                                          basepath, tier.lower()),
                                      thumbnail=catcorner,
                                      title="Alliane War {} Map :cat::sparkles:".format(
                                          tier.title()))
            data.set_author(name=self.catmurdock.display_name,
                            icon_url=self.catmurdock.avatar_url)
            data.add_field(
                name="Support Cat", value=catsupport)
            await self.bot.send_message(ctx.message.channel, embed=data)
        else:
            desc = "Currently supporting \nChallenger\nIntermediate\nHard\nExpert"
            data = CDTEmbed.get_embed(self, ctx, title="Alliance War Maps :cat::sparkles:".format(
                tier.title()), thumbnail=catcorner, description=desc)
            data.set_author(name=self.catmurdock.display_name,
                            icon_url=self.catmurdock.avatar_url)
            data.add_field(
                name="Support Cat", value=catsupport)
            await self.bot.send_message(ctx.message.channel, embed=data)

    @maps.command(pass_context=True, name="sq", aliases=("story",))
    async def maps_storyquest(self, ctx, level: str = None):
        """Currently supporting Cat Murdock maps for 6.1 and 6.4"""
        cat_maps = ("6.1.1", "6.1.2", "6.1.3", "6.1.4", "6.1.5", "6.1.6",
                    "6.4.1", "6.4.2", "6.4.3", "6.4.4", "6.4.5", "6.4.6")
        if level is None:
            pages = []
            for catmap in cat_maps:
                mapurl = "{}catmurdock/SQ/sq_{}.png".format(
                    basepath, catmap)
                data = CDTEmbed.get_embed(self, ctx, title="Act {} Map :cat::sparkles:".format(
                    catmap), image=mapurl, thumbnail=catcorner)
                data.set_author(name=self.catmurdock.display_name,
                                icon_url=self.catmurdock.avatar_url)
                data.add_field(
                    name="Support Cat", value=catsupport)
                pages.append(data)
            menu = PagesMenu(self.bot, timeout=30,
                             delete_onX=True, add_pageof=True)
            await menu.menu_start(pages)
        elif level is not None and level in cat_maps:
            data = CDTEmbed.get_embed(self, ctx, title="Act {} Map by :cat::sparkles:".format(
                level), image="{}catmurdock/SQ/sq_{}.png".format(basepath, level), thumbnail=catcorner)
            data.set_author(name=self.catmurdock.display_name,
                            icon_url=self.catmurdock.avatar_url)
            data.add_field(
                name="Support Cat", value=catsupport)

            await self.bot.send_message(ctx.message.channel, embed=data)
        else:
            data = CDTEmbed.get_embed(self, ctx, title="Available Story Quest Maps :cat::sparkles:",
                                      description="Act 6.1:\n6.1.1, 6.1.2, 6.1.3, 6.1.4, 6.1.5, 6.1.6\n"
                                      "Act 6.4:\n6.4: 6.4.1, 6.4.1, 6.4.3, 6.4.4, 6.4.5, 6.4.6",
                                      thumbnail=catcorner)
            data.set_author(name=self.catmurdock.display_name,
                            icon_url=self.catmurdock.avatar_url)
            data.add_field(name="Want more?", value=catsupport)
            await self.bot.send_message(ctx.message.channel, embed=data)

    @maps.command(pass_context=True, name="lol", aliases=["lab", ])
    async def maps_lol(self, ctx, *, maptype: str = "0"):
        """Labyrinth of Legends Maps
            LOL maps: 0, 1, 2, 3, 4, 5, 6, 7
            /lol 5"""
        if maptype in self.settings["lolmaps"].keys():
            pages = []
            for i in range(0, 8):
                maptitle = "Labyrinth of Legends: {}".format(
                    self.settings["lolmaps"][str(i)]["maptitle"])
                data = CDTEmbed.get_embed(
                    self, ctx, title=maptitle, image="{}lolmap{}v3.png".format(basepath, i))
                lanes = self.settings["lolanes"][str(i)[0]]
                # desclist = []
                for l in lanes:
                    enigma = self.settings["enigmatics"][l]
                    print(enigma)
                    # desclist.append("{}\n{}\n\n".format(enigma[0], enigma[1]))
                    data.add_field(name="Enigmatic {}".format(
                        enigma[0]), value=enigma[1])
                pages.append(data)
            menu = PagesMenu(self.bot, timeout=30,
                             delete_onX=True, add_pageof=True)
            await menu.menu_start(pages=pages, page_number=int(maptype))
            # await self.bot.send_message(ctx.message.channel, embed=em)

    def get_stuffs(self):
        """Check for settings changes. If changes, dump to settings.json"""
        if self.channel is None:
            self.channel = self.bot.get_channel("725397961072181349")
        if self.catmurdock is None or self.jjw is None:
            umcoc = self.bot.get_server('378035654736609280')
            self.catmurdock = umcoc.get_member("373128988962586635")
            self.jjw = umcoc.get_member("124984294035816448")
        if self.settings == {}:
            with open("data/mcocTools/settings.json") as f:
                settings = json.load(f)
            self.settings.update(settings)
            print('settings keys: {}'.format(self.settings.keys()))
        return


def setup(bot):
    bot.add_cog(MCOCMaps(bot))
