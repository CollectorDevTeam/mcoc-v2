import discord
from discord.ext import commands
import aiohttp
import json
from .utils import chat_formatting as chat
import requests
from .mcocTools import (PATREON, COLLECTOR_ICON, COLLECTOR_CRYSTAL, CDTEmbed)


class DadJokes:
    """Random dad jokes from icanhazdadjoke.com"""

    def __init__(self, bot):
        self.bot = bot
        self.diagnostics = self.bot.get_channel('391330316662341632')

    @commands.command(pass_context=True)
    async def dadjoke(self, ctx):
        """Gets a random dad joke."""
        api = 'https://icanhazdadjoke.com/slack'
        author = ctx.message.author
        async with aiohttp.ClientSession() as session:
            async with session.get(api) as response:
                result = await response.json()
                attachments = result['attachments'][0]
                joke = attachments['text']
                print(result)
                print(attachments)
        if joke is not None:
            data = CDTEmbed.get_embed(self, ctx, title='Dadjokes',
                                      description=joke)

            # data = discord.Embed(
            #     title='DadJokes', color=discord.Color.gold(), description=joke)
            # data.set_thumbnail(url=COLLECTOR_FEATURED)
            # data.footer(text='CollectorDevTeam | Requested by {}'.format(
            #     ctx.message.author.display_name), url=COLLECTOR_ICON)
            await self.bot.send_message(self.diagnostics, embed=data)
            try:
                await self.bot.send_message(ctx.message.channel, embed=data)
            except:
                self.bot.send_message(self.diagnostics,
                                      'dadjoke debug response.json: \n{}'.format(result))
                print(joke)


def setup(bot):
    n = DadJokes(bot)
    bot.add_cog(n)
