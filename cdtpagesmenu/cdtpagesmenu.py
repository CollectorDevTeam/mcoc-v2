import discord
from collections import namedtuple, OrderedDict
import asyncio
from .cdtembed import CDTEmbed


class PagesMenu:
    EmojiReact = namedtuple('EmojiReact', 'emoji include page_inc')

    def __init__(self, bot, *, add_pageof=True, timeout=30, choice=False,
                 delete_onX=True):
        self.bot = bot
        self.timeout = timeout
        self.add_pageof = add_pageof
        self.choice = choice
        self.delete_onX = delete_onX
        self.embedded = True

    async def menu_start(self, pages, page_number=0):
        page_list = []
        if isinstance(pages, list):
            page_list = pages
        else:
            for page in pages:
                page_list.append(page)
        page_length = len(page_list)
        if page_length == 1:
            if isinstance(page_list[0], discord.Embed) == True:
                message = await self.bot.say(embed=page_list[0])
            else:
                message = await self.bot.say(page_list[0])
            return
        self.embedded = isinstance(page_list[0], discord.Embed)
        self.all_emojis = OrderedDict([(i.emoji, i) for i in (
            self.EmojiReact(
                "\N{BLACK LEFT-POINTING DOUBLE TRIANGLE}", page_length > 5, -5),
            self.EmojiReact("\N{BLACK LEFT-POINTING TRIANGLE}", True, -1),
            self.EmojiReact("\N{CROSS MARK}", True, None),
            self.EmojiReact("\N{BLACK RIGHT-POINTING TRIANGLE}", True, 1),
            self.EmojiReact(
                "\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE}", page_length > 5, 5),
        )])

        print('menu_pages is embedded: ' + str(self.embedded))

        if self.add_pageof:
            for i, page in enumerate(page_list):
                if isinstance(page, discord.Embed):
                    ftr = page.footer
                    page.set_footer(text='{} (Page {} of {})'.format(ftr.text,
                                                                     i + 1, page_length), icon_url=ftr.icon_url)
                else:
                    page += '\n(Page {} of {})'.format(i + 1, page_length)

        self.page_list = page_list
        await self.display_page(None, page_number)

    async def display_page(self, message, page):
        if not message:
            if isinstance(self.page_list[page], discord.Embed) == True:
                message = await self.bot.say(embed=self.page_list[page])
            else:
                message = await self.bot.say(self.page_list[page])
            self.included_emojis = set()
            for emoji in self.all_emojis.values():
                if emoji.include:
                    await self.bot.add_reaction(message, emoji.emoji)
                    self.included_emojis.add(emoji.emoji)
        else:
            if self.embedded == True:
                message = await self.bot.edit_message(message, embed=self.page_list[page])
            else:
                message = await self.bot.edit_message(message, self.page_list[page])
        await asyncio.sleep(1)

        react = await self.bot.wait_for_reaction(message=message,
                                                 timeout=self.timeout, emoji=self.included_emojis)
        if react is None:
            try:
                await self.bot.clear_reactions(message)
            except discord.errors.NotFound:
                # logger.warn("Message has been deleted")
                print('Message deleted')
            except discord.Forbidden:
                # logger.warn("clear_reactions didn't work")
                for emoji in self.included_emojis:
                    await self.bot.remove_reaction(message, emoji, self.bot.user)
            return None

        emoji = react.reaction.emoji
        pages_to_inc = self.all_emojis[emoji].page_inc if emoji in self.all_emojis else None
        if pages_to_inc:
            next_page = (page + pages_to_inc) % len(self.page_list)
            try:
                await self.bot.remove_reaction(message, emoji, react.user)
                await self.display_page(message=message, page=next_page)
            except discord.Forbidden:
                await self.bot.delete_message(message)
                await self.display_page(message=None, page=next_page)
        elif emoji == '\N{CROSS MARK}':
            try:
                if self.delete_onX:
                    await self.bot.delete_message(message)
                    report = ('Message deleted by {} {} on {} {}'.format(
                        react.user.display_name, react.user.id, message.server.name, message.server.id))
                    print(report)
                    channel = self.bot.get_channel('537330789332025364')
                    await self.bot.send_message(channel, report)
                    # await self.bot.edit_message(message, 'Menu deleted by {}'.format(react.user.display_name))
                else:
                    await self.bot.clear_reactions(message)
            except discord.Forbidden:
                await self.bot.say("Bot does not have the proper Permissions")

    async def confirm(self, ctx, question: str):
        """Returns Boolean"""
        if ctx.message.channel.is_private:
            ucolor = discord.Color.gold()
        else:
            ucolor = ctx.message.author.color
        # data = discord.Embed(title='Confirmation:sparkles:',
        #                      description=question, color=ucolor)
        data = CDTEmbed.create(
            ctx, title="Convirmation:sparkles:", description=question)
        message = await self.bot.say(embed=data)

        await self.bot.add_reaction(message, '❌')
        await self.bot.add_reaction(message, '🆗')
        react = await self.bot.wait_for_reaction(message=message,
                                                 user=ctx.message.author, timeout=90, emoji=['❌', '🆗'])
        if react is not None:
            if react.reaction.emoji == '❌':
                data.description = '{} has canceled confirmation'.format(
                    ctx.message.author.name)
                # data.add_field(name='Confirmation', value='{} has canceled confirmation'.format(ctx.message.author.name))
                await self.bot.edit_message(message, embed=data)
                return False, message
            elif react.reaction.emoji == '🆗':
                data.description = '{} has confirmed.'.format(
                    ctx.message.author.name)
                # data.add_field(name='Confirmation', value='{} has confirmed.'.format(ctx.message.author.name))
                await self.bot.edit_message(message, embed=data)
                return True, message
        else:
            data.description = '{} has not responded'.format(
                ctx.message.author.name)
            # data.add_field(name='Confirmation', value='{} has not responded'.format(ctx.message.author.name))
            await self.bot.edit_message(message, embed=data)
            return False, message


def setup(bot):
    bot.add_cog(PagesMenu)
