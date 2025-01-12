# tasks.py
"""Contains task related stuff"""

import asyncio
from datetime import datetime, timedelta
from typing import List

import discord
from discord.ext import commands, tasks

from database import clans, errors, reminders, users
from resources import emojis, exceptions, functions, settings, strings


running_tasks = {}


class TasksCog(commands.Cog):
    """Cog with tasks"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Task management
    async def background_task(self, reminders_list: List[reminders.Reminder]) -> None:
        """Background task for scheduling reminders"""
        first_reminder = reminders_list[0]
        current_time = datetime.utcnow().replace(microsecond=0)
        def get_time_left() -> timedelta:
            time_left = first_reminder.end_time - current_time
            if time_left.total_seconds() < 0: time_left = timedelta(seconds=0)
            return time_left

        try:
            channel = await functions.get_discord_channel(self.bot, first_reminder.channel_id)
            if first_reminder.reminder_type == 'user':
                user = await functions.get_discord_user(self.bot, first_reminder.user_id)
                user_settings = await users.get_user(user.id)
                message_no = 1
                messages = {message_no: ''}
                for reminder in reminders_list:
                    if reminder.activity == 'custom':
                        reminder_message = strings.DEFAULT_MESSAGE_CUSTOM_REMINDER.format(message=reminder.message)
                    else:
                        reminder_message = reminder.message
                    if user_settings.dnd_mode_enabled:
                        message = f'{reminder_message.replace("{name}", f"**{user.name}**")}\n'
                    else:
                        message = f'{reminder_message.replace("{name}", user.mention)}\n'
                    if len(f'{messages[message_no]}{message}') > 1900:
                        message_no += 1
                        messages[message_no] = ''
                    messages[message_no] = f'{messages[message_no]}{message}'
                if reminder.activity.startswith('pets'):
                    try:
                        pet_reminders = (
                            await reminders.get_active_user_reminders(user_id=reminder.user_id, activity='pets',
                                                                      end_time=reminder.end_time)
                        )
                    except exceptions.NoDataFoundError:
                        pet_reminders = ()
                    command_pets_claim = await functions.get_slash_command(user_settings, 'pets claim')
                    if not pet_reminders:
                        messages[message_no] = (
                            f'{messages[message_no]}'
                            f"➜ {command_pets_claim} - No more pets on adventures."
                        )
                    else:
                        next_pet_reminder = pet_reminders[0]
                        next_pet_id = next_pet_reminder.activity.replace('pets-','')
                        time_left_next = next_pet_reminder.end_time - reminder.end_time
                        timestring = await functions.parse_timedelta_to_timestring(time_left_next)
                        pet_amount_left = len(pet_reminders)
                        pets_left = f'**{pet_amount_left}** pet'
                        if pet_amount_left > 1: pets_left = f'{pets_left}s'
                        messages[message_no] = (
                            f'{messages[message_no]}'
                            f"➜ {command_pets_claim} - {pets_left} left. Next pet (`{next_pet_id}`) "
                            f'in **{timestring}**.'
                        )
                time_left = get_time_left()
                try:
                    await asyncio.sleep(time_left.total_seconds())
                    allowed_mentions = discord.AllowedMentions(users=[user,])
                    for message in messages.values():
                        await channel.send(message.strip(), allowed_mentions=allowed_mentions)
                except asyncio.CancelledError:
                    return

            if first_reminder.reminder_type == 'clan':
                clan = await clans.get_clan_by_clan_name(first_reminder.clan_name)
                if clan.quest_user_id is not None:
                    quest_user_id = clan.quest_user_id
                    await clan.update(quest_user_id=None)
                    time_left_all_members = timedelta(minutes=5)
                    if clan.stealth_current >= clan.stealth_threshold:
                        alert_message = strings.SLASH_COMMANDS_NEW["guild raid"]
                    else:
                        alert_message = strings.SLASH_COMMANDS_NEW["guild upgrade"]
                    time_left = get_time_left()
                    try:
                        await asyncio.sleep(time_left.total_seconds())
                        await channel.send(
                            f'<@{quest_user_id}> Hey! It\'s time for your raid quest. '
                            f'You have 5 minutes, chop chop.'
                        )
                        reminder: reminders.Reminder = (
                            await reminders.insert_clan_reminder(clan.clan_name, time_left_all_members,
                                                                 clan.channel_id, alert_message)
                        )
                        return
                    except asyncio.CancelledError:
                        return
                message_mentions = ''
                for member_id in clan.member_ids:
                    if member_id is not None:
                        message_mentions = f'{message_mentions}<@{member_id}> '
                time_left = get_time_left()
                try:
                    await asyncio.sleep(time_left.total_seconds())
                    await channel.send(f'It\'s time for {first_reminder.message}!\n\n{message_mentions}')
                except asyncio.CancelledError:
                    return
            running_tasks.pop(first_reminder.task_name, None)
        except Exception as error:
            await errors.log_error(error)

    async def create_task(self, reminders_list: List[reminders.Reminder]) -> None:
        """Creates a new background task"""
        await self.delete_task(reminders_list[0].task_name)
        task = self.bot.loop.create_task(self.background_task(reminders_list))
        running_tasks[reminders_list[0].task_name] = task

    async def delete_task(self, task_name: str) -> None:
        """Stops and deletes a running task if it exists"""
        if task_name in running_tasks:
            running_tasks[task_name].cancel()
            running_tasks.pop(task_name, None)
        return

    # Events
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Fires when bot has finished starting"""
        reminders.schedule_reminders.start()
        self.delete_old_reminders.start()
        self.reset_clans.start()
        self.schedule_tasks.start()

    # Tasks
    @tasks.loop(seconds=0.5)
    async def schedule_tasks(self):
        """Task that creates or deletes tasks from scheduled reminders.
        Reminders that fire at the same second for the same user in the same channel are combined into one task.
        """
        user_reminders = {}
        for reminder in reminders.scheduled_for_tasks.copy().values():
            reminders.scheduled_for_tasks.pop(reminder.task_name, None)
            if reminder.reminder_type == 'user':
                reminder_user_channel = f'{reminder.user_id}-{reminder.channel_id}-{reminder.end_time}'
                if reminder_user_channel in user_reminders:
                    user_reminders[reminder_user_channel].append(reminder)
                else:
                    user_reminders[reminder_user_channel] = [reminder,]
            else:
                await self.create_task([reminder,])
        for reminder in reminders.scheduled_for_deletion.copy().values():
            reminders.scheduled_for_deletion.pop(reminder.task_name, None)
            await self.delete_task(reminder.task_name)
        if user_reminders:
            for reminders_list in user_reminders.values():
                reminders_list.sort(key=lambda reminder: reminder.activity)
                pet_reminders = []
                other_reminders = []
                for reminder in reminders_list:
                    if reminder.activity.startswith('pets'):
                        pet_reminders.append(reminder)
                    else:
                        other_reminders.append(reminder)
                await self.create_task(other_reminders + pet_reminders)

    @tasks.loop(minutes=2.0)
    async def delete_old_reminders(self) -> None:
        """Task that deletes all old reminders"""
        try:
            old_user_reminders = await reminders.get_old_user_reminders()
        except:
            old_user_reminders = ()
        try:
            old_clan_reminders = await reminders.get_old_clan_reminders()
        except:
            old_clan_reminders = ()
        old_reminders = list(old_user_reminders) + list(old_clan_reminders)

        for reminder in old_reminders:
            try:
                await reminder.delete()
            except Exception as error:
                await errors.log_error(
                    f'Error deleting old reminder.\nFunction: delete_old_reminders\n'
                    f'Reminder: {reminder}\nError: {error}'
            )

    @tasks.loop(seconds=55)
    async def reset_clans(self) -> None:
        """Task that creates the weekly reports and resets the clans"""
        clan_reset_time = settings.ClanReset()
        current_time = datetime.utcnow().replace(microsecond=0)
        if (
            (datetime.today().weekday() == clan_reset_time.weekday)
            and
            (current_time.hour == clan_reset_time.hour)
            and
            (current_time.minute == clan_reset_time.minute)
        ):
            # Create weekly clan reports, reset clan energy, delete current reminders and create a new reminder
            all_clans = await clans.get_all_clans()
            for clan in all_clans:
                await clan.update(stealth_current=1)
                try:
                    reminder = await reminders.get_clan_reminder(clan.clan_name)
                    await reminder.delete()
                except:
                    pass
                if not clan.alert_enabled: continue
                if clan.stealth_threshold > 1:
                    command = strings.SLASH_COMMANDS_NEW["guild upgrade"]
                else:
                    command = strings.SLASH_COMMANDS_NEW["guild raid"]
                time_left = timedelta(minutes=1)
                await reminders.insert_clan_reminder(clan.clan_name, time_left, clan.channel_id, command)
                try:
                    weekly_report: clans.ClanWeeklyReport = await clans.get_weekly_report(clan)
                except exceptions.NoDataFoundError:
                    continue
                message = (
                    f'**{clan.clan_name} weekly guild report**\n\n'
                    f'__Total energy from raids__: {weekly_report.energy_total:,} {emojis.ENERGY}\n\n'
                )
                if weekly_report.best_raid is None:
                    message = f'{message}{emojis.BP} There were no cool raids. Not cool.\n'
                else:
                    best_user = await functions.get_discord_user(self.bot, weekly_report.best_raid.user_id)
                    best_user_praise = weekly_report.praise.format(username=best_user.name)
                    message = (
                        f'{message}{emojis.BP} '
                        f'{best_user_praise} (_Best raid: {weekly_report.best_raid.energy:,}_ {emojis.ENERGY})\n'
                    )
                if weekly_report.worst_raid is None:
                    message = f'{message}{emojis.BP} There were no lame raids. How lame.\n'
                else:
                    worst_user = await functions.get_discord_user(self.bot, weekly_report.worst_raid.user_id)
                    worst_user_roast = weekly_report.roast.format(username=worst_user.name)
                    message = (
                        f'{message}{emojis.BP} '
                        f'{worst_user_roast} (_Worst raid: {weekly_report.worst_raid.energy:,}_ {emojis.ENERGY})\n'
                    )
                clan_channel = await functions.get_discord_channel(self.bot, clan.channel_id)
                await clan_channel.send(message)
            # Delete leaderboard
            await clans.delete_clan_leaderboard()


# Initialization
def setup(bot):
    bot.add_cog(TasksCog(bot))