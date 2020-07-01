
import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import discord
from discord.ext import commands
import os

# imported from redbot utils
from .utils.dataIO import dataIO
# imported from cdt installations
from .cdtdiagnostics import DIAGNOSTICS
from .cdtpagesmenu import PagesMenu
from .cdtembed import CDTEmbed

from __main__ import send_cmd_help


class ScreenShot:
    """Save a Screenshot from x website"""

    def __init__(self, bot):
        self.bot = bot
        self.screenshot_settings = dataIO.load_json(
            'data/cdtscreenshot/settings.json')
        self.channel = None
        self.diagnostics = DIAGNOSTICS(self.bot)
        self.get_stuffs()

    def getsuffs(self):
        self.channel = self.bot.get_channel(
            self.screenshot_settings["diagnostics_channel"])
        if 'calendar' not in self.screenshot_settings.keys():
            self.screenshot_settings['calendar'] = {
                'screenshot': '', 'time': 0}
            dataIO.save_json(
                'data/cdtscreenshot/settings.json', self.screenshot_settings)
        return

    @commands.group(pass_context=True, hidden=True)
    async def screenshot(self, ctx):
        if not collectordevteam(ctx):
            await self.diagnostics.log(ctx, self.channel)
            return
        elif ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @screenshot.command(pass_context=True, name='setexec', hidden=True)
    async def ss_exec(self, ctx, exectuable_path: str):
        """Set the executable path for the Chrome Webdriver"""
        self.screenshot_settings.update({"executable_path": str})
        if exectuable_path is None:
            return
        else:
            if os.path.exists(executable_path):
                msg = "Do you want to set your Chromium Webdriver path to:\n{}".format(
                    exectuable_path)
                test = await PagesMenu.confirm(ctx, msg)
                if test:
                    dataIO.save_json(
                        'data/cdtscreenshot/settings.json', self.screenshot_settings)
                else:
                    msg = "Chromium webdriver settings unchanged:\n{}".format(
                        self.screenshot_settings["executable_path"])
            else:
                msg = "Executable path not present on host."
            await self.bot.send_message(ctx.message.channel, msg)

    @screenshot.command(pass_context=True, name='take')
    async def ss_take(self, ctx, url: str, width=1920, height=1080):
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
            executable_path=self.screenshot_settings["executable_path"],   chrome_options=chrome_options)
        # channel = self.bot.get_channel('391330316662341632')
        # DRIVER = 'chromedriver'
        # driver = webdriver.Chrome(DRIVER)
        driver.get(url)
        asyncio.sleep(1)
        screenshot = driver.save_screenshot(
            self.screenshot_settings["temp_png"])
        driver.quit()
        # await asyncio.sleep(3)
        message = await self.bot.send_file(self.channel, self.screenshot_settings["temp_png"])
        await asyncio.sleep(1)
        if len(message.attachments) > 0:
            return message.attachments[0]['url']
        else:
            return None


def collectordevteam(ctx):
    author = ctx.message.author
    for role in author.roles:
        if role.id == '390253643330355200':
            return True
    return False


def setup(bot):
    bot.add_cog(ScreenShot)
