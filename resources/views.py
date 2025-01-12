# views.py
"""Contains global interaction views"""

from typing import List, Optional, Union

import discord
from discord.ext import commands

from content import settings as settings_cmd
from database import clans, reminders, users
from resources import components, functions, settings, strings

COMMANDS_SETTINGS = {
    'Guild channel': settings_cmd.command_settings_clan,
    'Helpers': settings_cmd.command_settings_helpers,
    'Partner': settings_cmd.command_settings_partner,
    'Ready list': settings_cmd.command_settings_ready,
    'Reminders': settings_cmd.command_settings_reminders,
    'Reminder messages': settings_cmd.command_settings_messages,
    'User settings': settings_cmd.command_settings_user,
}

class AutoReadyView(discord.ui.View):
    """View with button to toggle the auto_ready feature.

    Also needs the message of the response with the view, so do AbortView.message = await message.reply('foo').

    Returns
    -------
    'follow' if auto_ready was enabled
    'unfollow' if auto_ready was disabled
    'timeout' on timeout.
    None if nothing happened yet.
    """
    def __init__(self, ctx: Union[commands.Context, discord.ApplicationContext], user: discord.User,
                 user_settings: users.User,
                 interaction_message: Optional[Union[discord.Message, discord.Interaction]] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.value = None
        self.ctx = ctx
        self.interaction_message = interaction_message
        self.user = user
        self.user_settings = user_settings
        if not user_settings.auto_ready_enabled:
            custom_id = 'follow'
            label = 'Follow me!'
        else:
            custom_id = 'unfollow'
            label = 'Stop following me!'
        self.add_item(components.ToggleAutoReadyButton(custom_id=custom_id, label=label))
        if isinstance(ctx, discord.ApplicationContext):
            self.add_item(components.CustomButton(discord.ButtonStyle.grey, 'show_settings', '➜ Settings'))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(strings.MSG_INTERACTION_ERROR, ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        self.disable_all_items()
        if isinstance(self.ctx, discord.ApplicationContext):
            await functions.edit_interaction(self.interaction_message, view=self)
        else:
            await self.interaction_message.edit(view=self)
        self.stop()


class ConfirmCancelView(discord.ui.View):
    """View with confirm and cancel button.

    Args: ctx, styles: Optional[list[discord.ButtonStyle]], labels: Optional[list[str]]

    Also needs the message with the view, so do view.message = await ctx.interaction.original_message().
    Without this message, buttons will not be disabled when the interaction times out.

    Returns 'confirm', 'cancel' or None (if timeout/error)
    """
    def __init__(self, ctx: Union[commands.Context, discord.ApplicationContext],
                 styles: Optional[List[discord.ButtonStyle]] = [discord.ButtonStyle.grey, discord.ButtonStyle.grey],
                 labels: Optional[list[str]] = ['Yes','No'],
                 interaction_message: Optional[Union[discord.Message, discord.Interaction]] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.ctx = ctx
        self.value = None
        self.user = ctx.author
        self.interaction_message = interaction_message
        self.add_item(components.CustomButton(style=styles[0], custom_id='confirm', label=labels[0]))
        self.add_item(components.CustomButton(style=styles[1], custom_id='cancel', label=labels[1]))

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.user:
            return False
        return True

    async def on_timeout(self):
        self.stop()


class ConfirmMarriageView(discord.ui.View):
    """View with confirm and cancel button.

    Args: ctx, labels: Optional[list[str]]

    Also needs the message with the view, so do view.message = await ctx.interaction.original_message().
    Without this message, buttons will not be disabled when the interaction times out.

    Returns 'confirm', 'cancel' or None (if timeout/error)
    """
    def __init__(self, ctx: discord.ApplicationCommand, new_partner: discord.User,
                 interaction: Optional[discord.Interaction] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.value = None
        self.user = ctx.author
        self.new_partner = new_partner
        self.interaction = interaction
        self.add_item(components.CustomButton(style=discord.ButtonStyle.green,
                                              custom_id='confirm',
                                              label='I do!'))
        self.add_item(components.CustomButton(style=discord.ButtonStyle.grey,
                                              custom_id='cancel',
                                              label='Forever alone'))
    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user != self.new_partner:
            await interaction.response.send_message(strings.MSG_INTERACTION_ERROR, ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        self.disable_all_items()
        await functions.edit_interaction(self.interaction, view=self)
        self.stop()


class TrainingAnswerView(discord.ui.View):
    """View with training answers."""
    def __init__(self, buttons: dict):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.value = None
        for row, row_buttons in buttons.items():
            for custom_id, button_data in row_buttons.items():
                label, emoji, correct_answer = button_data
                if correct_answer:
                    if custom_id == 'training_no':
                        style = discord.ButtonStyle.red
                    else:
                        style = discord.ButtonStyle.green
                else:
                    style = discord.ButtonStyle.grey
                self.add_item(components.DisabledButton(style=style, label=label, row=row, emoji=emoji))
        self.stop()


class SettingsClanView(discord.ui.View):
    """View with a all components to manage clan settings.
    Also needs the interaction of the response with the view, so do view.interaction = await ctx.respond('foo').

    Arguments
    ---------
    ctx: Context.
    bot: Bot.
    clan_settings: Clan object with the settings of the clan.
    embed_function: Functino that returns the settings embed. The view expects the following arguments:
    - bot: Bot
    - clan_settings: Clan object with the settings of the clan

    Returns
    -------
    None

    """
    def __init__(self, ctx: discord.ApplicationContext, bot: discord.Bot, clan_settings: clans.Clan,
                 embed_function: callable, interaction: Optional[discord.Interaction] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.ctx = ctx
        self.bot = bot
        self.value = None
        self.embed_function = embed_function
        self.interaction = interaction
        self.user = ctx.author
        self.clan_settings = clan_settings
        self.add_item(components.ManageClanSettingsSelect(self))
        self.add_item(components.SwitchSettingsSelect(self, COMMANDS_SETTINGS))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(strings.MSG_INTERACTION_ERROR, ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        await functions.edit_interaction(self.interaction, view=None)
        self.stop()


class SettingsHelpersView(discord.ui.View):
    """View with a all components to manage helper settings.
    Also needs the interaction of the response with the view, so do view.interaction = await ctx.respond('foo').

    Arguments
    ---------
    ctx: Context.
    bot: Bot.
    user_settings: User object with the settings of the user.
    embed_function: Function that returns the settings embed. The view expects the following arguments:
    - bot: Bot
    - user_settings: User object with the settings of the user

    Returns
    -------
    None

    """
    def __init__(self, ctx: discord.ApplicationContext, bot: discord.Bot, user_settings: users.User,
                 embed_function: callable, interaction: Optional[discord.Interaction] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.ctx = ctx
        self.bot = bot
        self.value = None
        self.interaction = interaction
        self.user = ctx.author
        self.user_settings = user_settings
        self.embed_function = embed_function
        toggled_settings = {
            'Context helper': 'context_helper_enabled',
            'Heal warning': 'heal_warning_enabled',
            'Pet catch helper': 'pet_helper_enabled',
            'Ruby counter': 'ruby_counter_enabled',
            'Training helper': 'training_helper_enabled',
        }
        self.add_item(components.ToggleUserSettingsSelect(self, toggled_settings, 'Toggle helpers'))
        self.add_item(components.SwitchSettingsSelect(self, COMMANDS_SETTINGS))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(strings.MSG_INTERACTION_ERROR, ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        await functions.edit_interaction(self.interaction, view=None)
        self.stop()


class SettingsReadyView(discord.ui.View):
    """View with a all components to manage ready settings.
    Also needs the interaction of the response with the view, so do view.interaction = await ctx.respond('foo').

    Arguments
    ---------
    ctx: Context.
    bot: Bot.
    user_settings: User object with the settings of the user.
    clan_settings: Clan object with the settings of the clan.
    embed_function: Function that returns the settings embed. The view expects the following arguments:
    - bot: Bot
    - user_settings: User object with the settings of the user

    Returns
    -------
    None

    """
    def __init__(self, ctx: discord.ApplicationContext, bot: discord.Bot, user_settings: users.User,
                 clan_settings: clans.Clan, embed_function: callable,
                 interaction: Optional[discord.Interaction] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.ctx = ctx
        self.bot = bot
        self.value = None
        self.interaction = interaction
        self.user = ctx.author
        self.user_settings = user_settings
        self.clan_settings = clan_settings
        self.embed_function = embed_function
        toggled_settings_commands = {
            'Adventure': 'alert_adventure',
            'Arena': 'alert_arena',
            'Daily': 'alert_daily',
            'Duel': 'alert_duel',
            'Dungeon / Miniboss': 'alert_dungeon_miniboss',
            'Farm': 'alert_farm',
            'Guild': 'alert_guild',
            'Horse': 'alert_horse_breed',
            'Hunt': 'alert_hunt',
            'Lootbox': 'alert_lootbox',
            'Quest': 'alert_quest',
            'Training': 'alert_training',
            'Vote': 'alert_vote',
            'Weekly': 'alert_weekly',
            'Work': 'alert_work',

        }
        toggled_settings_events = {
            'Big arena': 'alert_big_arena',
            'Horse race': 'alert_horse_race',
            'Lottery': 'alert_lottery',
            'Minin\'tboss': 'alert_not_so_mini_boss',
            'Pet tournament': 'alert_pet_tournament',
        }
        self.add_item(components.ManageReadySettingsSelect(self))
        self.add_item(components.ToggleReadySettingsSelect(self, toggled_settings_commands, 'Toggle command reminders',
                                                           'toggle_command_reminders'))
        self.add_item(components.ToggleReadySettingsSelect(self, toggled_settings_events, 'Toggle event reminders',
                                                           'toggle_event_reminders'))
        self.add_item(components.SwitchSettingsSelect(self, COMMANDS_SETTINGS))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(strings.MSG_INTERACTION_ERROR, ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        await functions.edit_interaction(self.interaction, view=None)
        self.stop()


class SettingsRemindersView(discord.ui.View):
    """View with a all components to manage reminder settings.
    Also needs the interaction of the response with the view, so do view.interaction = await ctx.respond('foo').

    Arguments
    ---------
    ctx: Context.
    bot: Bot.
    user_settings: User object with the settings of the user.
    embed_function: Function that returns the settings embed. The view expects the following arguments:
    - bot: Bot
    - user_settings: User object with the settings of the user

    Returns
    -------
    None

    """
    def __init__(self, ctx: discord.ApplicationContext, bot: discord.Bot, user_settings: users.User,
                 embed_function: callable, interaction: Optional[discord.Interaction] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.ctx = ctx
        self.bot = bot
        self.value = None
        self.interaction = interaction
        self.user = ctx.author
        self.user_settings = user_settings
        self.embed_function = embed_function
        toggled_settings_commands = {
            'Adventure': 'alert_adventure',
            'Arena': 'alert_arena',
            'Daily': 'alert_daily',
            'Duel': 'alert_duel',
            'Dungeon / Miniboss': 'alert_dungeon_miniboss',
            'Farm': 'alert_farm',
            'Guild': 'alert_guild',
            'Horse': 'alert_horse_breed',
            'Hunt': 'alert_hunt',
            'Lootbox': 'alert_lootbox',
            'Partner alert': 'alert_partner',
            'Pets': 'alert_pets',
            'Quest': 'alert_quest',
            'Training': 'alert_training',
            'Vote': 'alert_vote',
            'Weekly': 'alert_weekly',
            'Work': 'alert_work',

        }
        toggled_settings_events = {
            'Big arena': 'alert_big_arena',
            'Horse race': 'alert_horse_race',
            'Lottery': 'alert_lottery',
            'Minin\'tboss': 'alert_not_so_mini_boss',
            'Pet tournament': 'alert_pet_tournament',
        }
        self.add_item(components.ToggleUserSettingsSelect(self, toggled_settings_commands, 'Toggle command reminders',
                                                          'toggle_command_reminders'))
        self.add_item(components.ToggleUserSettingsSelect(self, toggled_settings_events, 'Toggle event reminders',
                                                          'toggle_event_reminders'))
        self.add_item(components.SwitchSettingsSelect(self, COMMANDS_SETTINGS))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(strings.MSG_INTERACTION_ERROR, ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        await functions.edit_interaction(self.interaction, view=None)
        self.stop()


class SettingsUserView(discord.ui.View):
    """View with a all components to manage user settings.
    Also needs the interaction of the response with the view, so do view.interaction = await ctx.respond('foo').

    Arguments
    ---------
    ctx: Context.
    bot: Bot.
    user_settings: User object with the settings of the user.
    embed_function: Function that returns the settings embed. The view expects the following arguments:
    - bot: Bot
    - user_settings: User object with the settings of the user

    Returns
    -------
    None

    """
    def __init__(self, ctx: discord.ApplicationContext, bot: discord.Bot, user_settings: users.User,
                 embed_function: callable, interaction: Optional[discord.Interaction] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.ctx = ctx
        self.bot = bot
        self.value = None
        self.interaction = interaction
        self.user = ctx.author
        self.user_settings = user_settings
        self.embed_function = embed_function
        self.add_item(components.ManageUserSettingsSelect(self))
        self.add_item(components.SetDonorTierSelect(self, 'Change your donor tier', 'user'))
        partner_select_disabled = True if user_settings.partner_id is not None else False
        self.add_item(components.SetDonorTierSelect(self, 'Change partner donor tier', 'partner', partner_select_disabled))
        self.add_item(components.SwitchSettingsSelect(self, COMMANDS_SETTINGS))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(strings.MSG_INTERACTION_ERROR, ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        await functions.edit_interaction(self.interaction, view=None)
        self.stop()


class SettingsMessagesView(discord.ui.View):
    """View with a all components to change message reminders.
    Also needs the interaction of the response with the view, so do view.interaction = await ctx.respond('foo').

    Arguments
    ---------
    ctx: Context.
    bot: Bot.
    user_settings: User object with the settings of the user.
    embed_function: Function that returns a list of embeds to see specific messages. The view expects the following arguments:
    - bot: Bot
    - user_settings: User object with the settings of the user
    - activity: str, If this is None, the view doesn't show the buttons to change a message

    Returns
    -------
    None

    """
    def __init__(self, ctx: discord.ApplicationContext, bot: discord.Bot, user_settings: users.User,
                 embed_function: callable, activity: Optional[str] = 'all',
                 interaction: Optional[discord.Interaction] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.ctx = ctx
        self.bot = bot
        self.value = None
        self.interaction = interaction
        self.user = ctx.author
        self.user_settings = user_settings
        self.embed_function = embed_function
        self.activity = activity
        if activity == 'all':
            self.add_item(components.SetReminderMessageButton(style=discord.ButtonStyle.red, custom_id='reset_all',
                                                              label='Reset all messages'))
        else:
            self.add_item(components.SetReminderMessageButton(style=discord.ButtonStyle.blurple, custom_id='set_message',
                                                              label='Change'))
            self.add_item(components.SetReminderMessageButton(style=discord.ButtonStyle.red, custom_id='reset_message',
                                                              label='Reset'))
        self.add_item(components.ReminderMessageSelect(self, row=2))
        self.add_item(components.SwitchSettingsSelect(self, COMMANDS_SETTINGS, row=3))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(strings.MSG_INTERACTION_ERROR, ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        await functions.edit_interaction(self.interaction, view=None)
        self.stop()


class SettingsPartnerView(discord.ui.View):
    """View with a all components to manage partner settings.
    Also needs the interaction of the response with the view, so do view.interaction = await ctx.respond('foo').

    Arguments
    ---------
    ctx: Context.
    bot: Bot.
    user_settings: User object with the settings of the user.
    embed_function: Function that returns the settings embed. The view expects the following arguments:
    - bot: Bot
    - user_settings: User object with the settings of the user
    - partner_settings: User object with the settings of the partner

    Returns
    -------
    None

    """
    def __init__(self, ctx: discord.ApplicationContext, bot: discord.Bot, user_settings: users.User,
                 partner_settings: users.User, embed_function: callable,
                 interaction: Optional[discord.Interaction] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.ctx = ctx
        self.bot = bot
        self.value = None
        self.interaction = interaction
        self.user = ctx.author
        self.user_settings = user_settings
        self.partner_settings = partner_settings
        self.embed_function = embed_function
        self.add_item(components.ManagePartnerSettingsSelect(self))
        partner_select_disabled = True if user_settings.partner_id is not None else False
        self.add_item(components.SetDonorTierSelect(self, 'Change partner donor tier', 'partner', partner_select_disabled))
        self.add_item(components.SwitchSettingsSelect(self, COMMANDS_SETTINGS))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(strings.MSG_INTERACTION_ERROR, ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        await functions.edit_interaction(self.interaction, view=None)
        self.stop()


class OneButtonView(discord.ui.View):
    """View with one button that returns the custom id of that button.

    Also needs the interaction of the response with the view, so do view.interaction = await ctx.respond('foo').

    Returns
    -------
    None while active
    custom id of the button when pressed
    'timeout' on timeout.
    """
    def __init__(self, ctx: Union[commands.Context, discord.ApplicationContext], style: discord.ButtonStyle,
                 custom_id: str, label: str, emoji: Optional[discord.PartialEmoji] = None,
                 interaction_message: Optional[Union[discord.Message, discord.Interaction]] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.value = None
        self.interaction_message = interaction_message
        self.user = ctx.author
        self.add_item(components.CustomButton(style=style, custom_id=custom_id, label=label, emoji=emoji))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(strings.MSG_INTERACTION_ERROR, ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        self.disable_all_items()
        if isinstance(self.view.ctx, discord.ApplicationContext):
            await functions.edit_interaction(self.interaction_message, view=self)
        else:
            await self.interaction_message.edit(view=self)
        self.stop()


class RemindersListView(discord.ui.View):
    """View with a select that deletes custom reminders.

    Also needs the message of the response with the view, so do view.interaction = await ctx.respond('foo').

    Returns
    -------
    None
    """
    def __init__(self, bot: discord.Bot, ctx: Union[commands.Context, discord.ApplicationContext], user: discord.User,
                 user_settings: users.User, custom_reminders: List[reminders.Reminder],
                 embed_function: callable,
                 interaction_message: Optional[Union[discord.Message, discord.Interaction]] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.value = None
        self.bot = bot
        self.ctx = ctx
        self.custom_reminders = custom_reminders
        self.embed_function = embed_function
        self.interaction_message = interaction_message
        self.user = user
        self.user_settings = user_settings
        self.add_item(components.DeleteCustomRemindersButton())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(strings.MSG_INTERACTION_ERROR, ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        self.disable_all_items()
        if isinstance(self.ctx, discord.ApplicationContext):
            await functions.edit_interaction(self.interaction_message, view=self)
        else:
            await self.interaction_message.edit(view=self)
        self.stop()


class StatsView(discord.ui.View):
    """View with a button to toggle command tracking.

    Also needs the message of the response with the view, so do AbortView.message = await message.reply('foo').

    Returns
    -------
    'track' if tracking was enabled
    'untrack' if tracking was disabled
    'timeout' on timeout.
    None if nothing happened yet.
    """
    def __init__(self, ctx: Union[commands.Context, discord.ApplicationContext], user: discord.User,
                 user_settings: users.User,
                 interaction_message: Optional[Union[discord.Message, discord.Interaction]] = None):
        super().__init__(timeout=settings.INTERACTION_TIMEOUT)
        self.value = None
        self.ctx = ctx
        self.interaction_message = interaction_message
        self.user = ctx.author
        self.user_settings = user_settings
        if not user_settings.tracking_enabled:
            style = discord.ButtonStyle.green
            custom_id = 'track'
            label = 'Track me!'
        else:
            style = discord.ButtonStyle.grey
            custom_id = 'untrack'
            label = 'Stop tracking me!'
        self.add_item(components.ToggleTrackingButton(style=style, custom_id=custom_id, label=label))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.user:
            await interaction.response.send_message(strings.MSG_INTERACTION_ERROR, ephemeral=True)
            return False
        return True

    async def on_timeout(self) -> None:
        self.disable_all_items()
        if isinstance(self.ctx, discord.ApplicationContext):
            await functions.edit_interaction(self.interaction_message, view=self)
        else:
            await self.interaction_message.edit(view=self)
        self.stop()