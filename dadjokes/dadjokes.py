import discord
from discord.ext import commands
import aiohttp
import json
from .utils import chat_formatting as chat
import requests
from .mcocTools import (PATREON, COLLECTOR_ICON, COLLECTOR_FEATURED)


class DadJokes:
    """Random dad jokes from icanhazdadjoke.com"""

    def __init__(self, bot):
        self.bot = bot
        self.diagnostics = self.bot.get_channel('391330316662341632')

    @commands.command(pass_context=True)
    async def dadjoke(self, ctx):
        """Gets a random dad joke."""
        api = 'https://icanhazdadjoke.com/slack'
        jokejson = json.load(requests.get(api))
        data = discord.Embed(
            title='DadJokes', color=discord.Color.gold(), description=jokejson['text'])
        data.set_thumbnail(url=COLLECTOR_FEATURED)
        data.footer(text='CollectorDevTeam | Requested by {}'.format(
            ctx.message.author.display_name), url=COLLECTOR_ICON)
        await self.bot.send_message(ctx.message.channel, embed=data)
        # async with aiohttp.request('GET', api, headers={'Accept': 'application/json'}) as r:
        #     result = await r.json
        #     await self.bot.send_message(self.diagnostics, chat.box(result))
        # await self.bot.send_message(ctx.message.channel, '`' + result + '`')


def setup(bot):
    n = DadJokes(bot)
    bot.add_cog(n)
