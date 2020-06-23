import discord
from discord.ext import commands
import aiohttp
import json
from .utils import chat_formatting as chat
import requests
from .mcocTools import (PATREON, COLLECTOR_ICON, CDTEmbed)
import random


class DadJokes:
    """Random dad jokes from icanhazdadjoke.com"""

    def __init__(self, bot):
        self.bot = bot
        self.diagnostics = self.bot.get_channel('391330316662341632')
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
        if joke is not None:
            data = CDTEmbed.get_embed(self, ctx, title='CollectorVerse Dad Jokes:sparkles:',
                                      description=joke)
            data.set_author
            data.set_image(url=random.choice(self.dadjoke_images))
            await self.bot.send_message(self.diagnostics, embed=data)
            try:
                await self.bot.send_message(ctx.message.channel, embed=data)
            except:
                self.bot.send_message(self.diagnostics,
                                      'dadjoke debug response.json: \n{}'.format(result))
                print(joke)

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


def setup(bot):
    n = DadJokes(bot)
    bot.add_cog(n)
