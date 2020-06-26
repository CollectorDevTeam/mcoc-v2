import discord
import requests
from validator_collection import validators, checkers


class CDTEmbed:
    COLLECTOR_ICON = 'https://raw.githubusercontent.com/CollectorDevTeam/assets/master/data/cdt_icon.png'
    PATREON = 'https://patreon.com/collectorbot'

    def __init__(self, bot):
        self.bot = bot

    def create(self, ctx, user_id=None, color=discord.Color.gold(), title='', description='', image=None, thumbnail=None, url=None):
        '''Return a color styled embed with CDT footer, and optional title or description.
        user_id = user id string. If none provided, takes message author.
        color = manual override, otherwise takes gold for private channels, or author color for server.
        title = String, sets title.
        description = String, sets description.
        image = String url.  Validator checks for valid url.
        thumbnail = String url. Validator checks for valid url.'''
        if user_id is None:
            color = discord.Color.gold()
        elif isinstance(user_id, discord.User):
            user = user_id
            member = ctx.message.server.get_member(user.id)
            color = member.color
        else:
            # member = self.bot.get_member(user_id)
            member = discord.utils.get(ctx.message.server.members, id=user_id)
            color = member.color
        if url is None:
            url = PATREON
        data = discord.Embed(color=color, title=title, url=url)
        if description is not None:
            if len(description) < 1500:
                data.description = description
        data.set_author(name='CollectorVerse',
                        icon_url=self.COLLECTOR_ICON)
        if image is not None:
            validators.url(image)
            code = requests.get(image).status_code
            if code == 200:
                data.set_image(url=image)
            else:
                print('Image URL Failure, code {}'.format(code))
                print('Attempted URL:\n{}'.format(image))
        if thumbnail is not None:
            validators.url(thumbnail)
            code = requests.get(thumbnail).status_code
            if code == 200:
                data.set_thumbnail(url=thumbnail)
            else:
                print('Thumbnail URL Failure, code {}'.format(code))
                print('Attempted URL:\n{}'.format(thumbnail))
        data.set_footer(text='CollectorDevTeam | Requested by {}'.format(
            ctx.message.author), icon_url=self.COLLECTOR_ICON)
        return data


def setup(bot):
    bot.add_cog(CDTEmbed)
