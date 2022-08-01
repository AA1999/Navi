# horse.py

import re

import discord
from discord.ext import commands

from database import errors, reminders, users
from resources import emojis, exceptions, functions, settings, strings


class HorseCog(commands.Cog):
    """Cog that contains the horse detection commands"""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Runs when a message is sent in a channel."""
        if message.author.id != settings.EPIC_RPG_ID: return

        if not message.embeds: return
        embed: discord.Embed = message.embeds[0]
        message_author = message_title = icon_url = ''
        if embed.author:
            message_author = str(embed.author.name)
            icon_url = embed.author.icon_url
        if embed.title: message_title = str(embed.title)

        # Horse cooldown
        search_strings = [
                'you have used this command recently', #Engli
                'usaste este comando recientemente', #Spanish
                'você usou este comando recentementesh', #Portuguese
            ]
        if any(search_string in message_title.lower() for search_string in search_strings):
            user_id = user_name = None
            user = await functions.get_interaction_user(message)
            if user is not None:
                user_command = f"{strings.SLASH_COMMANDS['horse breeding'] or strings.SLASH_COMMANDS['horse race']}"
            else:
                user_command = '`rpg horse breed` or `rpg horse race`'
            if user is None:
                user_id_match = re.search(strings.REGEX_USER_ID_FROM_ICON_URL, icon_url)
                if user_id_match:
                    user_id = int(user_id_match.group(1))
                else:
                    user_name_match = re.search(strings.REGEX_USERNAME_FROM_EMBED_AUTHOR, message_author)
                    if user_name_match:
                        user_name = await functions.encode_text(user_name_match.group(1))
                    else:
                        await functions.add_warning_reaction(message)
                        await errors.log_error('User not found in horse cooldown message.', message)
                        return
                if user_id is not None:
                    user = await message.guild.fetch_member(user_id)
                else:
                    user = await functions.get_guild_member_by_name(message.guild, user_name)
            if user is None:
                await functions.add_warning_reaction(message)
                await errors.log_error('User not found in horse cooldown message.', message)
                return
            try:
                user_settings: users.User = await users.get_user(user.id)
            except exceptions.FirstTimeUserError:
                return
            if not user_settings.bot_enabled or not user_settings.alert_horse_breed.enabled: return
            timestring_match = await functions.get_match_from_patterns(strings.PATTERNS_COOLDOWN_TIMESTRING,
                                                                       message_title)
            if not timestring_match:
                await functions.add_warning_reaction(message)
                await errors.log_error('Timestring not found in horse cooldown message.', message)
                return
            timestring = timestring_match.group(1)
            time_left = await functions.calculate_time_left_from_timestring(message, timestring)
            reminder_message = user_settings.alert_horse_breed.message.replace('{command}', user_command)
            reminder: reminders.Reminder = (
                await reminders.insert_user_reminder(user.id, 'horse', time_left,
                                                    message.channel.id, reminder_message)
            )
            await functions.add_reminder_reaction(message, reminder, user_settings)


# Initialization
def setup(bot):
    bot.add_cog(HorseCog(bot))