from discord.ext import commands
import aiohttp
from .utils import chat_formatting as chat


class DadJokes:
    """Random dad jokes from icanhazdadjoke.com"""

    def __init__(self, bot):
        self.bot = bot
        self.diagnostics = self.bot.get_channel('391330316662341632')

    @commands.command(pass_context=True)
    async def dadjoke(self, ctx):
        """Gets a random dad joke."""
        api = 'https://icanhazdadjoke.com/'
        async with aiohttp.request('GET', api, headers={'Accept': 'application/json'}) as r:
            result = await r.json
            await self.bot.send_message(self.diagnostics, chat.box(result))
            # await self.bot.send_message(ctx.message.channel, '`' + result + '`')


def setup(bot):
    n = DadJokes(bot)
    bot.add_cog(n)
