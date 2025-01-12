# fun.py
"""Contains some nonsense"""

import re

import discord
from discord.ext import commands

from database import errors, users
from resources import emojis, exceptions, functions, regex, settings


class FunCog(commands.Cog):
    """Cog with events and help and about commands"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_edit(self, message_before: discord.Message, message_after: discord.Message) -> None:
        """Runs when a message is edited in a channel."""
        for row in message_after.components:
            for component in row.children:
                if component.disabled:
                    return
        await self.on_message(message_after)

    @commands.command(aliases=('listen',))
    @commands.bot_has_permissions(send_messages=True, embed_links=True, read_message_history=True)
    async def hey(self, ctx: commands.Context) -> None:
        """Hey! Listen!"""
        if ctx.prefix.lower() == 'rpg ': return
        await ctx.reply('https://tenor.com/view/navi-hey-listen-gif-4837431')

    @commands.command(aliases=('hold','cuddle','kiss','love','thanks','smile'))
    @commands.bot_has_permissions(send_messages=True, embed_links=True, read_message_history=True)
    async def hug(self, ctx: commands.Context) -> None:
        """Aww"""
        if ctx.prefix.lower() == 'rpg ': return
        await ctx.reply('https://www.youtube.com/watch?v=SB4sDPTZPYM')

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Runs when a message is sent in a channel."""

        if not message.embeds and not message.author.bot:
            message_content = message.content
            if message_content.lower() == 'navi lit':
                await message.reply('https://tenor.com/view/betty-white-dab-mood-gif-5044603')

        if not message.embeds and message.author.id == settings.EPIC_RPG_ID:
            message_content = message.content
            if 'died fighting the **mysterious man**' in message_content.lower():
                user_command_message = user_name = None
                user = await functions.get_interaction_user(message)
                if user is None:
                    user_name_match = re.search(regex.NAME_FROM_MESSAGE_START, message_content)
                    if user_name_match:
                        user_name = user_name_match.group(1)
                        user_command_message = (
                            await functions.get_message_from_channel_history(
                                message.channel, regex.COMMAND_HEAL,
                                user_name=user_name
                            )
                        )
                    if not user_name_match or user_command_message is None:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('User not found for heal event message for the fun reaction.', message)
                        return
                    user = user_command_message.author
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.reactions_enabled: return
                await message.add_reaction(emojis.PEPE_LAUGH)

            if 'is now in the jail' in message_content.lower():
                user = await functions.get_interaction_user(message)
                if user is None:
                    user_name = None
                    user_name_match = re.search(r"car \*\*(.+?)\n", message_content)
                    if user_name_match:
                        user_name = user_name_match.group(1)
                        user_command_message = (
                            await functions.get_message_from_channel_history(
                                message.channel, user_name=user_name
                            )
                        )
                    if not user_name_match or user_command_message is None:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('User not found in epic guard message for the fun reaction.', message)
                        return
                    user = user_command_message.author
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.reactions_enabled: return
                await message.add_reaction(emojis.PEEPO_JAIL)

            if 'again, it **exploded**' in message_content.lower():
                user = await functions.get_interaction_user(message)
                user_name = user_command_message = None
                if user is None:
                    user_name_match = re.search(r"\*\*(.+?)\*\* tries to", message_content)
                    if user_name_match:
                        user_name = user_name_match.group(1)
                        user_command_message = (
                            await functions.get_message_from_channel_history(
                                message.channel, regex.COMMAND_ENCHANT,
                                user_name=user_name
                            )
                        )
                    if not user_name_match or user_command_message is None:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('User not found in enchant message for the fun reaction.', message)
                        return
                    user = user_command_message.author
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.reactions_enabled: return
                await message.add_reaction(emojis.PEPE_LAUGH)

            if 'took the seed from the ground and decided to try planting it again later' in message_content.lower():
                user = await functions.get_interaction_user(message)
                user_name = user_command_message = None
                if user is None:
                    user_name_match = re.search(r'\*\*(.+?)\*\* (?:HITS|is about)', message_content)
                    if user_name_match:
                        user_name = user_name_match.group(1)
                        user_command_message = (
                            await functions.get_message_from_channel_history(
                                message.channel, regex.COMMAND_FARM,
                                user_name=user_name
                            )
                        )
                    if not user_name_match or user_command_message is None:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('User not found in farm event message for the fun reaction.', message)
                        return
                    user = user_command_message.author
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.reactions_enabled: return
                await message.add_reaction(emojis.PEPE_LAUGH)

            if 'fighting them wasn\'t very clever' in message_content.lower():
                user = await functions.get_interaction_user(message)
                user_name = user_command_message = None
                if user is None:
                    user_name_match = re.search(r"\*\*(.+?)\*\* fights", message_content)
                    if user_name_match:
                        user_name = user_name_match.group(1)
                        user_command_message = (
                            await functions.get_message_from_channel_history(
                                message.channel, regex.COMMAND_HUNT,
                                user_name=user_name
                            )
                        )
                    if not user_name_match or user_command_message is None:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('User not found in hunt event message for the fun reaction.',  message)
                        return
                    user = user_command_message.author
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.reactions_enabled: return
                await message.add_reaction(emojis.PEPE_LAUGH)

            if 'you just lost your lootbox' in message_content.lower():
                user = await functions.get_interaction_user(message)
                user_name = user_command_message = None
                if user is None:
                    user_name_match = re.search(r"\*\*(.+?)\*\* uses a", message_content)
                    if user_name_match:
                        user_name = user_name_match.group(1)
                        user_command_message = (
                            await functions.get_message_from_channel_history(
                                message.channel, regex.COMMAND_OPEN,
                                user_name=user_name
                            )
                        )
                    if not user_name_match or user_command_message is None:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('User not found in lootbox event message for the fun reaction.', message)
                        return
                    user = user_command_message.author
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.reactions_enabled: return
                await message.add_reaction(emojis.PEPE_LAUGH)

            if 'christmas slime' in message_content.lower() and 'got 100' in message_content.lower():
                user = await functions.get_interaction_user(message)
                user_name = user_command_message = None
                if user is None:
                    user_name_match = re.search(regex.NAME_FROM_MESSAGE_START, message_content)
                    if user_name_match:
                        user_name = user_name_match.group(1)
                        user_command_message = (
                            await functions.get_message_from_channel_history(
                                message.channel, regex.COMMAND_HUNT,
                                user_name=user_name
                            )
                        )
                    if not user_name_match or user_command_message is None:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('User not found for the christmas slime reaction.', message)
                        return
                    user = user_command_message.author
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.reactions_enabled: return
                await message.add_reaction(emojis.PEEPO_XMAS_YAY)

            search_strings = [
                '<:coolness', #All languages
            ]
            if any(search_string in message_content.lower() for search_string in search_strings):
                user = await functions.get_interaction_user(message)
                if user is None:
                    search_patterns = [
                        r"\*\*(.+?)\*\* (also )?earned [0-9] <:coolness", #English
                        r"\*\*(.+?)\*\* found", #English 2
                    ]
                    user_name_match = await functions.get_match_from_patterns(search_patterns, message_content)
                    if user_name_match:
                        user_name = user_name_match.group(1)
                        user_command_message = (
                            await functions.get_message_from_channel_history(
                                message.channel, user_name=user_name
                            )
                        )
                    if not user_name_match or user_command_message is None:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('Couldn\'t find a user for the coolness reaction.', message)
                        return
                    user = user_command_message.author
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.reactions_enabled: return
                await message.add_reaction(emojis.PANDA_COOL)

        if message.embeds and message.author.id == settings.EPIC_RPG_ID:
            embed: discord.Embed = message.embeds[0]

            if embed.fields:
                field = embed.fields[0]

                # Lost pet reaction
                search_strings = [
                    'got bored and left', #English
                    'se aburrió y se fue', #Spanish
                    'ficou entediado e foi embora', #Portuguese
                ]
                if any(search_string in field.value.lower() for search_string in search_strings):
                    user = await functions.get_interaction_user(message)
                    if user is None:
                        user_command_message = (
                            await functions.get_message_from_channel_history(
                                message.channel, regex.COMMAND_TRAINING,
                                limit=100
                            )
                        )
                        if user_command_message is None:
                            await functions.add_warning_reaction(message)
                            await errors.log_error('Couldn\'t find a user for the lost pet reaction.', message)
                            return
                        user = user_command_message.author
                    try:
                        user_settings: users.User = await users.get_user(user.id)
                    except exceptions.FirstTimeUserError:
                        return
                    if not user_settings.bot_enabled or not user_settings.reactions_enabled: return
                    await message.add_reaction(emojis.PANDA_SAD)

                # Shitty lootbox reaction
                shitty_lootbox_found = False
                search_strings = [
                    'lootbox opened', #English
                    'lootbox abierta', #Spanish
                    'lootbox aberto', #Portuguese
                ]
                if any(search_string in field.name.lower() for search_string in search_strings):
                    if '+1' in field.value.lower() and field.value.lower().count('<:') == 1:
                        if 'wooden log' in field.value.lower() or 'normie fish' in field.value.lower():
                            shitty_lootbox_found = True
                    elif 'nothing' in field.value.lower():
                        shitty_lootbox_found = True
                if shitty_lootbox_found:
                    user = await functions.get_interaction_user(message)
                    if user is None:
                        user_command_message = (
                            await functions.get_message_from_channel_history(
                                message.channel, regex.COMMAND_OPEN
                            )
                        )
                        if user_command_message is None:
                            await functions.add_warning_reaction(message)
                            await errors.log_error('Couldn\'t find a user for the shitty lootbox reaction.', message)
                            return
                        user = user_command_message.author
                    try:
                        user_settings: users.User = await users.get_user(user.id)
                    except exceptions.FirstTimeUserError:
                        return
                    if not user_settings.bot_enabled or not user_settings.reactions_enabled: return
                    await message.add_reaction(emojis.PEPE_LAUGH)


# Initialization
def setup(bot):
    bot.add_cog(FunCog(bot))