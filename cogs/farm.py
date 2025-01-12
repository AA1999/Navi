# farm.py

from datetime import datetime, timedelta
import re

import discord
from discord.ext import commands

from database import errors, reminders, tracking, users
from resources import emojis, exceptions, functions, regex, settings, strings


class FarmCog(commands.Cog):
    """Cog that contains the farm detection commands"""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_edit(self, message_before: discord.Message, message_after: discord.Message) -> None:
        """Runs when a message is edited in a channel."""
        for row in message_after.components:
            for component in row.children:
                if component.disabled:
                    return
        await self.on_message(message_after)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Runs when a message is sent in a channel."""
        if message.author.id != settings.EPIC_RPG_ID: return

        if message.embeds:
            embed: discord.Embed = message.embeds[0]
            message_author = message_title = icon_url = ''
            if embed.author:
                message_author = str(embed.author.name)
                icon_url = embed.author.icon_url
            if embed.title: message_title = str(embed.title)

            # Farm cooldown
            search_strings = [
                'you have farmed already', #English
                'ya cultivaste recientemente', #Spanish
                'você plantou recentemente', #Portuguese
            ]
            if any(search_string in message_title.lower() for search_string in search_strings):
                user_id = user_name = user_command = user_command_message = None
                user = await functions.get_interaction_user(message)
                slash_command = True if user is not None else False
                if user is None:
                    user_id_match = re.search(regex.USER_ID_FROM_ICON_URL, icon_url)
                    if user_id_match:
                        user_id = int(user_id_match.group(1))
                        user = await message.guild.fetch_member(user_id)
                    else:
                        user_name_match = re.search(regex.USERNAME_FROM_EMBED_AUTHOR, message_author)
                        if user_name_match:
                            user_name = user_name_match.group(1)
                        if user_name_match is None:
                            await functions.add_warning_reaction(message)
                            await errors.log_error('User not found in farm cooldown message.', message)
                            return
                    user_command_message = (
                        await functions.get_message_from_channel_history(
                            message.channel, regex.COMMAND_FARM,
                            user=user, user_name=user_name
                        )
                    )
                    if user_command_message is None:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('Couldn\'t find a command for the farm cooldown message.', message)
                        return
                    if user is None: user = user_command_message.author
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled or not user_settings.alert_farm.enabled: return
                if not slash_command:
                    last_farm_seed = None
                    if 'carrot' in user_command_message.content.lower():
                        last_farm_seed = 'carrot'
                    elif 'bread' in user_command_message.content.lower():
                        last_farm_seed = 'bread'
                    elif 'potato' in user_command_message.content.lower():
                        last_farm_seed = 'potato'
                    await user_settings.update(last_farm_seed=last_farm_seed)
                user_command = await functions.get_slash_command(user_settings, 'farm')
                if user_settings.last_farm_seed != '':
                    user_command = f'{user_command} `seed: {user_settings.last_farm_seed}`'
                timestring_match = await functions.get_match_from_patterns(regex.PATTERNS_COOLDOWN_TIMESTRING,
                                                                           message_title)
                if not timestring_match:
                    await functions.add_warning_reaction(message)
                    await errors.log_error('Timestring not found in farm cooldown message.', message)
                    return
                timestring = timestring_match.group(1)
                time_left = await functions.calculate_time_left_from_timestring(message, timestring)
                if time_left < timedelta(0): return
                reminder_message = user_settings.alert_farm.message.replace('{command}', user_command)
                reminder: reminders.Reminder = (
                    await reminders.insert_user_reminder(user.id, 'farm', time_left,
                                                         message.channel.id, reminder_message)
                )
                await functions.add_reminder_reaction(message, reminder, user_settings)

        if not message.embeds:
            message_content = message.content
            # Farm
            search_strings = [
               'seed in the ground...', #English
               'en el suelo...', #Spanish
               'no solo...', #Portuguese
            ]
            if any(search_string in message_content.lower() for search_string in search_strings):
                user_name = last_farm_seed = user_command_message = None
                user = await functions.get_interaction_user(message)
                slash_command = True if user is not None else False
                if user is None:
                    search_patterns = [
                        r"^\*\*(.+?)\*\* plant", #English, Spanish, Portuguese
                    ]
                    user_name_match = await functions.get_match_from_patterns(search_patterns, message_content)
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
                        await errors.log_error('User not found for farm message.', message)
                        return
                    user = user_command_message.author
                try:
                    user_settings: users.User = await users.get_user(user.id)
                except exceptions.FirstTimeUserError:
                    return
                if not user_settings.bot_enabled: return
                current_time = datetime.utcnow().replace(microsecond=0)
                if user_settings.tracking_enabled:
                    await tracking.insert_log_entry(user.id, message.guild.id, 'farm', current_time)
                if not user_settings.alert_farm.enabled: return
                search_strings = [
                    '{} in the ground', #English
                    '{} en el suelo', #Spanish
                    '{} no solo', #Portuguese
                ]
                user_command = await functions.get_slash_command(user_settings, 'farm')
                if any(search_string.format('bread seed') in message_content.lower() for search_string in search_strings):
                    last_farm_seed = 'bread'
                elif any(search_string.format('carrot seed') in message_content.lower() for search_string in search_strings):
                    last_farm_seed = 'carrot'
                elif any(search_string.format('potato seed') in message_content.lower() for search_string in search_strings):
                    last_farm_seed = 'potato'
                await user_settings.update(last_farm_seed=last_farm_seed)
                if user_settings.last_farm_seed != '':
                    user_command = f'{user_command} `seed: {user_settings.last_farm_seed}`'
                time_left = await functions.calculate_time_left_from_cooldown(message, user_settings, 'farm')
                if time_left < timedelta(0): return
                reminder_message = user_settings.alert_farm.message.replace('{command}', user_command)
                reminder: reminders.Reminder = (
                    await reminders.insert_user_reminder(user.id, 'farm', time_left,
                                                         message.channel.id, reminder_message)
                )
                await functions.add_reminder_reaction(message, reminder, user_settings)
                if user_settings.auto_ready_enabled:
                    await functions.call_ready_command(self.bot, message, user)
                search_strings = [
                    'also got', #English
                    'también consiguió', #Spanish
                    'também conseguiu', #Portuguese
                ]
                if any(search_string in message_content.lower() for search_string in search_strings):
                    if 'potato seed**' in message_content.lower():
                        if user_settings.reactions_enabled: await message.add_reaction(emojis.SEED_POTATO)
                    elif 'carrot seed**' in message_content.lower():
                        if user_settings.reactions_enabled: await message.add_reaction(emojis.SEED_CARROT)
                    elif 'bread seed**' in message_content.lower():
                        if user_settings.reactions_enabled: await message.add_reaction(emojis.SEED_BREAD)

            # Farm event non-slash (always English)
            if ('hits the floor with the' in message_content.lower()
                or 'is about to plant another seed' in message_content.lower()):
                interaction = await functions.get_interaction(message)
                if interaction is None:
                    user_name = user_command = user_command_message = None
                    user_name_match = re.search(regex.NAME_FROM_MESSAGE, message_content)
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
                        await errors.log_error('User not found in farm event non-slash message.', message)
                        return
                    user = user_command_message.author
                    try:
                        user_settings: users.User = await users.get_user(user.id)
                    except exceptions.FirstTimeUserError:
                        return
                    if not user_settings.bot_enabled: return
                    current_time = datetime.utcnow().replace(microsecond=0)
                    if user_settings.tracking_enabled:
                        await tracking.insert_log_entry(user.id, message.guild.id, 'farm', current_time)
                    if not user_settings.alert_farm.enabled: return
                    user_command = await functions.get_slash_command(user_settings, 'farm')
                    seed = None
                    if 'bread' in user_command_message.content.lower():
                        seed = 'bread'
                    elif 'carrot' in user_command_message.content.lower():
                        seed = 'carrot'
                    elif 'potato' in user_command_message.content.lower():
                        seed = 'potato'
                    if seed is not None:
                        user_command = f'{user_command} `seed: {seed}`'
                    time_left = await functions.calculate_time_left_from_cooldown(message, user_settings, 'farm')
                    if time_left < timedelta(0): return
                    reminder_message = user_settings.alert_farm.message.replace('{command}', user_command)
                    reminder: reminders.Reminder = (
                        await reminders.insert_user_reminder(user.id, 'farm', time_left,
                                                            message.channel.id, reminder_message)
                    )
                    await functions.add_reminder_reaction(message, reminder, user_settings)

            # Farm event slash (all languages)
            if  (('<:seed' in message_content.lower() and '!!' in message_content.lower())
                 or ':crossed_swords:' in message_content.lower()
                 or ':sweat_drops:' in message_content.lower()):
                user_name = user_command = None
                interaction = await functions.get_interaction(message)
                if interaction is not None:
                    if interaction.name != 'farm': return
                    user = interaction.user
                    try:
                        user_settings: users.User = await users.get_user(user.id)
                    except exceptions.FirstTimeUserError:
                        return
                    if not user_settings.bot_enabled: return
                    user_command = await functions.get_slash_command(user_settings, 'farm')
                    current_time = datetime.utcnow().replace(microsecond=0)
                    if user_settings.tracking_enabled:
                        await tracking.insert_log_entry(user.id, message.guild.id, 'farm', current_time)
                    if not user_settings.alert_farm.enabled: return
                    time_left = await functions.calculate_time_left_from_cooldown(message, user_settings, 'farm')
                    if time_left < timedelta(0): return
                    reminder_message = user_settings.alert_farm.message.replace('{command}', user_command)
                    reminder: reminders.Reminder = (
                        await reminders.insert_user_reminder(user.id, 'farm', time_left,
                                                            message.channel.id, reminder_message)
                    )
                    await functions.add_reminder_reaction(message, reminder, user_settings)
                    if user_settings.auto_ready_enabled: await functions.call_ready_command(self.bot, message, user)


# Initialization
def setup(bot):
    bot.add_cog(FarmCog(bot))