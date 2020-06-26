
import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import discord
from discord.ext import commands


from .utils.dataIO import dataIO
from .cdtdiagnostics import DIAGNOSTICS
from .cdtembed import CDTEmbed

from __main__ import send_cmd_help


class ScreenShot:
    """Save a Screenshot from x website"""

    def __init__(self, bot):
        self.bot = bot
        self.diagnostics = DIAGNOSTICS(self.bot)
        self.settings = dataIO.load_json('data/cdtscreenshot/settings.json')
        self.channel = self.bot.get_channel(
            self.settings["diagnostics_channel"])
        if 'calendar' not in self.settings.keys():
            self.settings['calendar'] = {'screenshot': '', 'time': 0}
            dataIO.save_json(
                'data/cdtscreenshot/settings.json', self.settings)

    @commands.group(pass_context=True, hidden=True, aliases=('ss', 'screenshots',))
    async def screenshot(self, ctx):
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
        await self.diagnostics.log(ctx, self.channel)

    @screenshot.command(pass_context=True, name='setexec')
    async def ss_exec(self, ctx, *, exectuable_path: str, hidden=True):
        """Set the executable path for the Chrome Webdriver"""
        self.settings.update({"executable_path": str})
        dataIO.save_json(
            'data/cdtscreenshot/settings.json', self.settings)

    @screenshot.command(pass_context=True, name='take')
    async def ss_take(self, ctx, *, url, width=1920, height=1080):
        """Take URL screenshot & return embed"""
        imgurl = await self.get_screenshot(url, width, height)
        data = CDTEmbed.create(ctx, image=imgurl)
        await self.bot.send_message(ctx.message.channel, embed=data)

    async def get_screenshot(self, url, w=1920, h=1080):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size={}, {}".format(w, h))
        chrome_options.add_argument("allow-running-insecure-content")
        # chrome_options.binary_location = '/Applications/Google Chrome   Canary.app/Contents/MacOS/Google Chrome Canary'
        driver = webdriver.Chrome(
            executable_path=self.settings["executable_path"],   chrome_options=chrome_options)
        # channel = self.bot.get_channel('391330316662341632')
        # DRIVER = 'chromedriver'
        # driver = webdriver.Chrome(DRIVER)
        driver.get(url)
        asyncio.sleep(1)
        screenshot = driver.save_screenshot(self.settings["temp_png"])
        driver.quit()
        # await asyncio.sleep(3)
        message = await self.bot.send_file(self.channel, self.settings["temp_png"])
        await asyncio.sleep(1)
        if len(message.attachments) > 0:
            return message.attachments[0]['url']
        else:
            return None


def setup(bot):
    bot.add_cog(ScreenShot)
