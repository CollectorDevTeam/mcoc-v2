import discord
from discord.ext import commands
import aiohttp
import json
# from .mcocTools import (DIAGNOSTICS)
from .cdtdiagnostics import DIAGNOSTICS
from .cdtembed import CDTEmbed
import random


class DadJokes:
    """Random dad jokes from icanhazdadjoke.com"""

    def __init__(self, bot):
        self.bot = bot
        self.diagnostics = DIAGNOSTICS(self.bot)
        self.channel = None
        self.dadjoke_images = [
            'https://cdn.discordapp.com/attachments/391330316662341632/725045045794832424/collector_dadjokes.png',
            'https://cdn.discordapp.com/attachments/391330316662341632/725054700457689210/dadjokes2.png',
            'https://cdn.discordapp.com/attachments/391330316662341632/725055822023098398/dadjokes3.png',
            'https://cdn.discordapp.com/attachments/391330316662341632/725056025404637214/dadjokes4.png']

    @commands.command(pass_context=True, aliases=('joke', 'dadjokes', 'jokes',))
    async def dadjoke(self, ctx):
        """Gets a random dad joke."""
        author = ctx.message.author
        joke = await self.get_joke()
        data = CDTEmbed.create(self, ctx, title='CollectorVerse Dad Jokes:sparkles:',
                               description=joke)
        data.set_author
        data.set_image(url=random.choice(self.dadjoke_images))
        while self.channel is None:
            self.set_channel()
        try:
            await self.bot.send_message(ctx.message.channel, embed=data)
            await DIAGNOSTICS.log(self.channel)
        except:
            await DIAGNOSTICS.log(self.channel, msg=joke)

    async def get_joke(self):
        api = 'https://icanhazdadjoke.com/slack'
        joke = None
        while joke is None:
            async with aiohttp.ClientSession() as session:
                async with session.get(api) as response:
                    result = await response.json()
                    attachments = result['attachments'][0]
                    joke = attachments['text']
        if joke is not None:
            return joke

    def set_channel(self):
        self.channel = self.bot.get_channel('725065939460030575')
        return


def setup(bot):
    n = DadJokes(bot)
    bot.add_cog(n)
