# components.py
"""Contains global interaction components"""

import asyncio
import re
from typing import Dict, List, Optional

import discord

from database import reminders, users
from resources import emojis, functions, modals, strings, views


class ToggleAutoReadyButton(discord.ui.Button):
    """Button to toggle the auto-ready feature"""
    def __init__(self, custom_id: str, label: str, disabled: bool = False, emoji: Optional[discord.PartialEmoji] = None):
        super().__init__(style=discord.ButtonStyle.grey, custom_id=custom_id, label=label, emoji=emoji,
                         disabled=disabled)

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.custom_id == 'follow':
            enabled = True
            response = (
                f'Done. I will now show you your ready commands after every created reminder.'
            )
        else:
            enabled = False
            response = 'Done. I will now stop showing your ready commands automatically.'
        await self.view.user_settings.update(auto_ready_enabled=enabled)
        self.view.value = self.custom_id
        await self.view.user_settings.refresh()
        if self.view.user_settings.auto_ready_enabled:
            self.label = 'Stop following me!'
            self.custom_id = 'unfollow'
        else:
            self.label = 'Follow me!'
            self.custom_id = 'follow'
        await self.view.message.edit(view=self.view)
        if not interaction.response.is_done():
            await interaction.response.send_message(response, ephemeral=True)
        else:
            await interaction.followup.send(response, ephemeral=True)


class CustomButton(discord.ui.Button):
    """Simple Button. Writes its custom id to the view value, stops the view and does an invisible response."""
    def __init__(self, style: discord.ButtonStyle, custom_id: str, label: Optional[str],
                 emoji: Optional[discord.PartialEmoji] = None):
        super().__init__(style=style, custom_id=custom_id, label=label, emoji=emoji)

    async def callback(self, interaction: discord.Interaction):
        self.view.value = self.custom_id
        self.view.stop()
        try:
            await interaction.response.send_message()
        except Exception:
            pass


class DisabledButton(discord.ui.Button):
    """Disabled button with no callback"""
    def __init__(self, style: discord.ButtonStyle, label: str, row: int, emoji: Optional[discord.PartialEmoji] = None):
        super().__init__(style=style, label=label, emoji=emoji, disabled=True, row=row)


class ToggleUserSettingsSelect(discord.ui.Select):
    """Toggle select that shows and toggles the status of user settings (except alerts)."""
    def __init__(self, view: discord.ui.View, toggled_settings: Dict[str, str], placeholder: str,
                 custom_id: Optional[str] = 'toggle_user_settings', row: Optional[int] = None):
        self.toggled_settings = toggled_settings
        options = []
        options.append(discord.SelectOption(label='Enable all', value='enable_all', emoji=None))
        options.append(discord.SelectOption(label='Disable all', value='disable_all', emoji=None))
        for label, setting in toggled_settings.items():
            setting_enabled = getattr(view.user_settings, setting)
            if isinstance(setting_enabled, users.UserAlert):
                setting_enabled = getattr(setting_enabled, 'enabled')
            emoji = emojis.GREENTICK if setting_enabled else emojis.REDTICK
            options.append(discord.SelectOption(label=label, value=setting, emoji=emoji))
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options, row=row,
                         custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        select_value = self.values[0]
        kwargs = {}
        if select_value in ('enable_all','disable_all'):
            enabled = True if select_value == 'enable_all' else False
            for setting in self.toggled_settings.values():
                if not setting.endswith('_enabled'):
                    setting = f'{setting}_enabled'
                kwargs[setting] = enabled
        else:
            setting_value = getattr(self.view.user_settings, select_value)
            if isinstance(setting_value, users.UserAlert):
                setting_value = getattr(setting_value, 'enabled')
            if not select_value.endswith('_enabled'):
                select_value = f'{select_value}_enabled'
            kwargs[select_value] = not setting_value
        await self.view.user_settings.update(**kwargs)
        for child in self.view.children.copy():
            if child.custom_id == self.custom_id:
                self.view.remove_item(child)
                self.view.add_item(ToggleUserSettingsSelect(self.view, self.toggled_settings,
                                                            self.placeholder, self.custom_id))
                break
        embed = await self.view.embed_function(self.view.bot, self.view.ctx, self.view.user_settings)
        await interaction.response.edit_message(embed=embed, view=self.view)


class ToggleReadySettingsSelect(discord.ui.Select):
    """Toggle select that shows and toggles the status of ready settings."""
    def __init__(self, view: discord.ui.View, toggled_settings: Dict[str, str], placeholder: str,
                 custom_id: Optional[str] = 'toggle_ready_settings', row: Optional[int] = None):
        self.toggled_settings = toggled_settings
        options = []
        options.append(discord.SelectOption(label='Show all', value='enable_all', emoji=None))
        options.append(discord.SelectOption(label='Hide all', value='disable_all', emoji=None))
        for label, setting in toggled_settings.items():
            setting_enabled = getattr(view.user_settings, setting)
            if isinstance(setting_enabled, users.UserAlert):
                setting_enabled = getattr(setting_enabled, 'visible')
            emoji = emojis.GREENTICK if setting_enabled else emojis.REDTICK
            options.append(discord.SelectOption(label=label, value=setting, emoji=emoji))
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options, row=row,
                         custom_id=custom_id)

    async def callback(self, interaction: discord.Interaction):
        select_value = self.values[0]
        kwargs = {}
        if select_value in ('enable_all','disable_all'):
            enabled = True if select_value == 'enable_all' else False
            for setting in self.toggled_settings.values():
                if not setting.endswith('_visible'):
                    setting = f'{setting}_visible'
                kwargs[setting] = enabled
        else:
            setting_value = getattr(self.view.user_settings, select_value)
            if isinstance(setting_value, users.UserAlert):
                setting_value = getattr(setting_value, 'visible')
            if not select_value.endswith('_visible'):
                select_value = f'{select_value}_visible'
            kwargs[select_value] = not setting_value
        await self.view.user_settings.update(**kwargs)
        for child in self.view.children.copy():
            if child.custom_id == self.custom_id:
                self.view.remove_item(child)
                self.view.add_item(ToggleReadySettingsSelect(self.view, self.toggled_settings,
                                                             self.placeholder, self.custom_id))
                break
        embed = await self.view.embed_function(self.view.bot, self.view.ctx, self.view.user_settings, self.view.clan_settings)
        await interaction.response.edit_message(embed=embed, view=self.view)


class ManageClanSettingsSelect(discord.ui.Select):
    """Select to change guild settings"""
    def __init__(self, view: discord.ui.View, row: Optional[int] = None):
        options = []
        reminder_action = 'Disable' if view.clan_settings.alert_enabled else 'Enable'
        quest_action = 'Disable' if view.clan_settings.upgrade_quests_enabled else 'Allow'
        options.append(discord.SelectOption(label=f'{reminder_action} reminder',
                                            value='toggle_reminder'))
        options.append(discord.SelectOption(label=f'{quest_action} quests below stealth threshold',
                                            value='toggle_quest'))
        options.append(discord.SelectOption(label='Change stealth threshold',
                                            value='set_threshold', emoji=None))
        options.append(discord.SelectOption(label='Set this channel as guild channel',
                                            value='set_channel', emoji=None))
        options.append(discord.SelectOption(label='Reset guild channel',
                                            value='reset_channel', emoji=None))
        super().__init__(placeholder='Change settings', min_values=1, max_values=1, options=options, row=row,
                         custom_id='manage_clan_settings')

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.clan_settings.leader_id:
            await interaction.response.send_message(
                f'**{interaction.user.name}**, you are not registered as the guild owner. Only the guild owner can '
                f'change these settings.\n'
                f'If you _are_ the guild owner, run {strings.SLASH_COMMANDS_NEW["guild list"]} to update '
                f'your guild in my database.\n',
                ephemeral=True
            )
            return
        select_value = self.values[0]
        if select_value == 'toggle_reminder':
            if not self.view.clan_settings.alert_enabled and self.view.clan_settings.channel_id is None:
                await interaction.response.send_message('You need to set a guild channel first.', ephemeral=True)
                return
            await self.view.clan_settings.update(alert_enabled=not self.view.clan_settings.alert_enabled)
        elif select_value == 'toggle_quest':
            await self.view.clan_settings.update(upgrade_quests_enabled=not self.view.clan_settings.upgrade_quests_enabled)
        elif select_value == 'set_threshold':
            modal = modals.SetStealthThresholdModal(self.view)
            await interaction.response.send_modal(modal)
            return
        elif select_value == 'set_channel':
            confirm_view = views.ConfirmCancelView(self.view.ctx, styles=[discord.ButtonStyle.blurple, discord.ButtonStyle.grey])
            confirm_interaction = await interaction.response.send_message(
                f'**{interaction.user.name}**, do you want to set `{interaction.channel.name}` as the alert channel '
                f'for the guild `{self.view.clan_settings.clan_name}`?',
                view=confirm_view,
                ephemeral=True
            )
            confirm_view.interaction_message = confirm_interaction
            await confirm_view.wait()
            if confirm_view.value == 'confirm':
                await self.view.clan_settings.update(channel_id=interaction.channel.id)
                await confirm_interaction.edit_original_message(content='Channel updated.', view=None)
            else:
                await confirm_interaction.edit_original_message(content='Aborted', view=None)
                return
        elif select_value == 'reset_channel':
            if self.view.clan_settings.channel_id is None:
                await interaction.response.send_message(
                    f'You don\'t have a guild channel set already.',
                    ephemeral=True
                )
                return
            confirm_view = views.ConfirmCancelView(self.view.ctx, styles=[discord.ButtonStyle.red, discord.ButtonStyle.grey])
            confirm_interaction = await interaction.response.send_message(
                f'**{interaction.user.name}**, do you want to reset the guild alert channel '
                f'for the guild `{self.view.clan_settings.clan_name}`?\n\n'
                f'Note that this will also disable the reminder if enabled.',
                view=confirm_view,
                ephemeral=True
            )
            confirm_view.interaction_message = confirm_interaction
            await confirm_view.wait()
            if confirm_view.value == 'confirm':
                await self.view.clan_settings.update(channel_id=None, alert_enabled=False)
                await confirm_interaction.edit_original_message(content='Channel reset.', view=None)
            else:
                await confirm_interaction.edit_original_message(content='Aborted', view=None)
                return
        for child in self.view.children.copy():
            if isinstance(child, ManageClanSettingsSelect):
                self.view.remove_item(child)
                self.view.add_item(ManageClanSettingsSelect(self.view))
                break
        embed = await self.view.embed_function(self.view.bot, self.view.ctx, self.view.clan_settings)
        if interaction.response.is_done():
            await interaction.message.edit(embed=embed, view=self.view)
        else:
            await interaction.response.edit_message(embed=embed, view=self.view)


class ManageReadySettingsSelect(discord.ui.Select):
    """Select to change ready settings"""
    def __init__(self, view: discord.ui.View, row: Optional[int] = None):
        options = []
        message_style = 'normal message' if view.user_settings.ready_as_embed else 'embed'
        cmd_cd_action = 'Hide' if view.user_settings.cmd_cd_visible else 'Show'
        up_next_reminder_action = 'Hide' if view.user_settings.ready_up_next_visible else 'Show'
        up_next_style = 'static time' if view.user_settings.ready_up_next_as_timestamp else 'timestamp'
        auto_ready_action = 'Disable' if view.user_settings.auto_ready_enabled else 'Enable'
        other_position = 'on bottom' if view.user_settings.ready_other_on_top else 'on top'
        options.append(discord.SelectOption(label=f'{auto_ready_action} auto-ready',
                                            value='toggle_auto_ready', emoji=None))
        options.append(discord.SelectOption(label=f'Show ready commands as {message_style}',
                                            value='toggle_message_style', emoji=None))
        options.append(discord.SelectOption(label='Change embed color',
                                            value='change_embed_color', emoji=None))
        options.append(discord.SelectOption(label=f'{up_next_reminder_action} "up next" reminder',
                                                value='toggle_up_next'))
        options.append(discord.SelectOption(label=f'Show "up next" reminder with {up_next_style}',
                                                value='toggle_up_next_timestamp'))
        if view.clan_settings is not None:
            clan_reminder_action = 'Hide' if view.clan_settings.alert_visible else 'Show'
            options.append(discord.SelectOption(label=f'{clan_reminder_action} guild channel reminder',
                                                value='toggle_alert'))
        options.append(discord.SelectOption(label=f'{cmd_cd_action} /cd command',
                                            value='toggle_cmd_cd'))
        options.append(discord.SelectOption(label=f'Show "other" field {other_position}',
                                            value='toggle_other_position', emoji=None))
        super().__init__(placeholder='Change settings', min_values=1, max_values=1, options=options, row=row,
                         custom_id='manage_ready_settings')

    async def callback(self, interaction: discord.Interaction):
        select_value = self.values[0]
        if select_value == 'toggle_auto_ready':
            await self.view.user_settings.update(auto_ready_enabled=not self.view.user_settings.auto_ready_enabled)
        elif select_value == 'toggle_alert':
            await self.view.clan_settings.update(alert_visible=not self.view.clan_settings.alert_visible)
        elif select_value == 'toggle_message_style':
            await self.view.user_settings.update(ready_as_embed=not self.view.user_settings.ready_as_embed)
        elif select_value == 'change_embed_color':
            modal = modals.SetEmbedColorModal(self.view)
            await interaction.response.send_modal(modal)
            return
        elif select_value == 'toggle_cmd_cd':
            await self.view.user_settings.update(cmd_cd_visible=not self.view.user_settings.cmd_cd_visible)
        elif select_value == 'toggle_other_position':
            await self.view.user_settings.update(ready_other_on_top=not self.view.user_settings.ready_other_on_top)
        elif select_value == 'toggle_up_next':
            await self.view.user_settings.update(ready_up_next_visible=not self.view.user_settings.ready_up_next_visible)
        elif select_value == 'toggle_up_next_timestamp':
            await self.view.user_settings.update(ready_up_next_as_timestamp=not self.view.user_settings.ready_up_next_as_timestamp)
        for child in self.view.children.copy():
            if isinstance(child, ManageReadySettingsSelect):
                self.view.remove_item(child)
                self.view.add_item(ManageReadySettingsSelect(self.view))
                break
        embed = await self.view.embed_function(self.view.bot, self.view.ctx, self.view.user_settings, self.view.clan_settings)
        if interaction.response.is_done():
            await interaction.message.edit(embed=embed, view=self.view)
        else:
            await interaction.response.edit_message(embed=embed, view=self.view)


class SwitchSettingsSelect(discord.ui.Select):
    """Select to switch between settings embeds"""
    def __init__(self, view: discord.ui.View, commands_settings: Dict[str, callable], row: Optional[int] = None):
        self.commands_settings = commands_settings
        options = []
        for label in commands_settings.keys():
            options.append(discord.SelectOption(label=label, value=label, emoji=None))
        super().__init__(placeholder='➜ Switch to other settings', min_values=1, max_values=1, options=options, row=row,
                         custom_id='switch_settings')

    async def callback(self, interaction: discord.Interaction):
        select_value = self.values[0]
        await interaction.response.edit_message()
        await self.commands_settings[select_value](self.view.bot, self.view.ctx, switch_view = self.view)


class ManageUserSettingsSelect(discord.ui.Select):
    """Select to change user settings"""
    def __init__(self, view: discord.ui.View, row: Optional[int] = None):
        options = []
        reactions_action = 'Disable' if view.user_settings.reactions_enabled else 'Enable'
        dnd_action = 'Disable' if view.user_settings.dnd_mode_enabled else 'Enable'
        hardmode_action = 'Disable' if view.user_settings.hardmode_mode_enabled else 'Enable'
        hunt_action = 'Disable' if view.user_settings.hunt_rotation_enabled else 'Enable'
        mentions_action = 'Disable' if view.user_settings.slash_mentions_enabled else 'Enable'
        tracking_action = 'Disable' if view.user_settings.tracking_enabled else 'Enable'
        options.append(discord.SelectOption(label=f'{reactions_action} reactions',
                                            value='toggle_reactions'))
        options.append(discord.SelectOption(label=f'{dnd_action} DND mode',
                                            value='toggle_dnd'))
        options.append(discord.SelectOption(label=f'{hardmode_action} hardmode mode',
                                            value='toggle_hardmode'))
        options.append(discord.SelectOption(label=f'{hunt_action} hunt rotation',
                                            value='toggle_hunt'))
        options.append(discord.SelectOption(label=f'{mentions_action} slash mentions',
                                            value='toggle_mentions'))
        options.append(discord.SelectOption(label=f'{tracking_action} command tracking',
                                            value='toggle_tracking'))
        options.append(discord.SelectOption(label=f'Change last time travel time',
                                            value='set_last_tt', emoji=None))
        super().__init__(placeholder='Change settings', min_values=1, max_values=1, options=options, row=row,
                         custom_id='manage_user_settings')

    async def callback(self, interaction: discord.Interaction):
        select_value = self.values[0]
        if select_value == 'toggle_reactions':
            await self.view.user_settings.update(reactions_enabled=not self.view.user_settings.reactions_enabled)
        elif select_value == 'toggle_dnd':
            await self.view.user_settings.update(dnd_mode_enabled=not self.view.user_settings.dnd_mode_enabled)
        elif select_value == 'toggle_hardmode':
            await self.view.user_settings.update(hardmode_mode_enabled=not self.view.user_settings.hardmode_mode_enabled)
            if self.view.user_settings.partner_id is not None:
                partner_discord = await functions.get_discord_user(self.view.bot, self.view.user_settings.partner_id)
                partner: users.User = await users.get_user(self.view.user_settings.partner_id)
                if partner.partner_channel_id is not None:
                    action = 'started' if self.view.user_settings.hardmode_enabled else 'stopped'
                    if not self.view.user_settings.dnd_mode_enabled:
                        partner_message = partner_discord.mention
                    else:
                        partner_message = f'**{partner_discord.name}**,'
                    partner_message = f'{partner_message} **{interaction.user.name}** just {action} **hardmoding**.'
                    if action == 'started':
                        partner_message = (
                            f'{partner_message}\n'
                            f'Please don\'t use `hunt together` until they turn it off. '
                            f'If you want to hardmode too, please activate hardmode mode as well and hunt solo.'
                        )
                    else:
                        partner_message = (
                            f'{partner_message}\n'
                            f'Feel free to use `hunt together` again.'
                        )
                    partner_channel = await functions.get_discord_channel(self.bot, partner.partner_channel_id)
                    await partner_channel.send(partner_message)
        elif select_value == 'toggle_hunt':
            await self.view.user_settings.update(hunt_rotation_enabled=not self.view.user_settings.hunt_rotation_enabled)
        elif select_value == 'toggle_mentions':
            await self.view.user_settings.update(slash_mentions_enabled=not self.view.user_settings.slash_mentions_enabled)
        elif select_value == 'toggle_tracking':
            await self.view.user_settings.update(tracking_enabled=not self.view.user_settings.tracking_enabled)
        elif select_value == 'set_last_tt':
            modal = modals.SetLastTTModal(self.view)
            await interaction.response.send_modal(modal)
            return
        for child in self.view.children.copy():
            if isinstance(child, ManageUserSettingsSelect):
                self.view.remove_item(child)
                self.view.add_item(ManageUserSettingsSelect(self.view))
                break
        embed = await self.view.embed_function(self.view.bot, self.view.ctx, self.view.user_settings)
        if interaction.response.is_done():
            await interaction.message.edit(embed=embed, view=self.view)
        else:
            await interaction.response.edit_message(embed=embed, view=self.view)


class ManagePartnerSettingsSelect(discord.ui.Select):
    """Select to change partner settings"""
    def __init__(self, view: discord.ui.View, row: Optional[int] = None):
        options = []
        options.append(discord.SelectOption(label='Set this channel as partner channel',
                                            value='set_channel', emoji=None))
        options.append(discord.SelectOption(label='Reset partner channel',
                                            value='reset_channel', emoji=None))
        options.append(discord.SelectOption(label='Reset partner',
                                            value='reset_partner', emoji=None))
        super().__init__(placeholder='Change settings', min_values=1, max_values=1, options=options, row=row,
                         custom_id='manage_partner_settings')

    async def callback(self, interaction: discord.Interaction):
        select_value = self.values[0]
        if select_value == 'set_channel':
            if self.view.user_settings.partner_id is None:
                await interaction.response.send_message(
                    f'You need to set a partner first.\n'
                    f'To set a partner use {strings.SLASH_COMMANDS_NAVI["settings partner"]} `partner: @partner`.',
                    ephemeral=True
                )
                return
            confirm_view = views.ConfirmCancelView(self.view.ctx, styles=[discord.ButtonStyle.blurple, discord.ButtonStyle.grey])
            confirm_interaction = await interaction.response.send_message(
                f'**{interaction.user.name}**, do you want to set `{interaction.channel.name}` as the partner alert '
                f'channel?\n'
                f'The partner alert channel is where you will be sent lootbox and hardmode alerts from your '
                f'partner. You can toggle partner alerts in `Reminder settings`.',
                view=confirm_view,
                ephemeral=True
            )
            confirm_view.interaction_message = confirm_interaction
            await confirm_view.wait()
            if confirm_view.value == 'confirm':
                await self.view.user_settings.update(partner_channel_id=interaction.channel.id)
                await confirm_interaction.edit_original_message(
                    content=(
                        f'Channel updated.\n'
                        f'To receive partner alerts, make sure the partner alert is enabled in `Reminder settings`.'
                    ),
                    view=None
                )
            else:
                await confirm_interaction.edit_original_message(content='Aborted', view=None)
                return
        elif select_value == 'reset_channel':
            if self.view.user_settings.partner_channel_id is None:
                await interaction.response.send_message(
                    f'You don\'t have a partner alert channel set already.',
                    ephemeral=True
                )
                return
            confirm_view = views.ConfirmCancelView(self.view.ctx, styles=[discord.ButtonStyle.red, discord.ButtonStyle.grey])
            confirm_interaction = await interaction.response.send_message(
                f'**{interaction.user.name}**, do you want to reset your partner alert channel?\n\n'
                f'If you do this, partner alerts will not work even if turned on.',
                view=confirm_view,
                ephemeral=True
            )
            confirm_view.interaction_message = confirm_interaction
            await confirm_view.wait()
            if confirm_view.value == 'confirm':
                await self.view.user_settings.update(partner_channel_id=None)
                await confirm_interaction.edit_original_message(content='Channel reset.', view=None)
            else:
                await confirm_interaction.edit_original_message(content='Aborted', view=None)
                return
        elif select_value == 'reset_partner':
            if self.view.user_settings.partner_id is None:
                await interaction.response.send_message(
                    f'You don\'t have a partner set already.',
                    ephemeral=True
                )
                return
            confirm_view = views.ConfirmCancelView(self.view.ctx, styles=[discord.ButtonStyle.red, discord.ButtonStyle.grey])
            confirm_interaction = await interaction.response.send_message(
                f'**{interaction.user.name}**, do you want to reset your partner?\n\n'
                f'This will also reset your partner\'s partner (which is you, heh) and set the '
                f'partner donor tiers back to `Non-donator`.',
                view=confirm_view,
                ephemeral=True
            )
            confirm_view.interaction_message = confirm_interaction
            await confirm_view.wait()
            if confirm_view.value == 'confirm':
                await self.view.user_settings.update(partner_id=None, partner_donor_tier=0)
                await self.view.partner_settings.update(partner_id=None, partner_donor_tier=0)
                self.view.partner_settings = None
                await confirm_interaction.edit_original_message(content='Partner reset.', view=None)
                for child in self.view.children.copy():
                    if isinstance(child, SetDonorTierSelect):
                        child.disabled = False
            else:
                await confirm_interaction.edit_original_message(content='Aborted', view=None)
                return
        for child in self.view.children.copy():
            if isinstance(child, ManagePartnerSettingsSelect):
                self.view.remove_item(child)
                self.view.add_item(ManagePartnerSettingsSelect(self.view))
                break
        embed = await self.view.embed_function(self.view.bot, self.view.ctx, self.view.user_settings, self.view.partner_settings)
        if interaction.response.is_done():
            await interaction.message.edit(embed=embed, view=self.view)
        else:
            await interaction.response.edit_message(embed=embed, view=self.view)


class SetDonorTierSelect(discord.ui.Select):
    """Select to set a donor tier"""
    def __init__(self, view: discord.ui.View, placeholder: str, donor_type: Optional[str] = 'user',
                 disabled: Optional[bool] = False, row: Optional[int] = None):
        self.donor_type = donor_type
        options = []
        for index, donor_tier in enumerate(strings.DONOR_TIERS):
            options.append(discord.SelectOption(label=donor_tier, value=str(index), emoji=None))
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options, disabled=disabled,
                         row=row, custom_id=f'set_{donor_type}_donor_tier')

    async def callback(self, interaction: discord.Interaction):
        select_value = self.values[0]
        if self.donor_type == 'user':
            await self.view.user_settings.update(user_donor_tier=int(select_value))
        elif self.donor_type == 'partner':
            await self.view.user_settings.update(partner_donor_tier=int(select_value))
        embed = await self.view.embed_function(self.view.bot, self.view.ctx, self.view.user_settings)
        await interaction.response.edit_message(embed=embed, view=self.view)


class ReminderMessageSelect(discord.ui.Select):
    """Select to select reminder messages by activity"""
    def __init__(self, view: discord.ui.View, row: Optional[int] = None):
        options = []
        options.append(discord.SelectOption(label='All', value='all', emoji=None))
        for activity in strings.ACTIVITIES:
            options.append(discord.SelectOption(label=activity.replace('-',' ').capitalize(), value=activity, emoji=None))
        super().__init__(placeholder='Choose activity', min_values=1, max_values=1, options=options, row=row,
                         custom_id='select_message_activity')

    async def callback(self, interaction: discord.Interaction):
        select_value = self.values[0]
        self.view.activity = select_value
        all_custom_ids = []
        for child in self.view.children:
            all_custom_ids.append(child.custom_id)
        if select_value == 'all':
            if 'set_message' in all_custom_ids or 'reset_message' in all_custom_ids:
                for child in self.view.children.copy():
                    if child.custom_id in ('set_message', 'reset_message'):
                        self.view.remove_item(child)
            if 'reset_all' not in all_custom_ids:
                self.view.add_item(SetReminderMessageButton(style=discord.ButtonStyle.red, custom_id='reset_all',
                                                            label='Reset all messages', row=1))
        else:
            if 'reset_all' in all_custom_ids:
                for child in self.view.children.copy():
                    if child.custom_id == 'reset_all':
                        self.view.remove_item(child)
            if 'set_message' not in all_custom_ids:
                self.view.add_item(SetReminderMessageButton(style=discord.ButtonStyle.blurple, custom_id='set_message',
                                                       label='Change', row=1))
            if 'reset_message' not in all_custom_ids:
                self.view.add_item(SetReminderMessageButton(style=discord.ButtonStyle.red, custom_id='reset_message',
                                                       label='Reset', row=1))
        embeds = await self.view.embed_function(self.view.bot, self.view.ctx, self.view.user_settings, select_value)
        await interaction.response.edit_message(embeds=embeds, view=self.view)


class SetReminderMessageButton(discord.ui.Button):
    """Button to edit reminder messages"""
    def __init__(self, style: discord.ButtonStyle, custom_id: str, label: str, disabled: Optional[bool] = False,
                 emoji: Optional[discord.PartialEmoji] = None, row: Optional[int] = 1):
        super().__init__(style=style, custom_id=custom_id, label=label, emoji=emoji,
                         disabled=disabled, row=row)

    async def callback(self, interaction: discord.Interaction) -> None:
        def check(m: discord.Message) -> bool:
            return m.author == interaction.user and m.channel == interaction.channel

        if self.custom_id == 'reset_all':
            confirm_view = views.ConfirmCancelView(self.view.ctx, styles=[discord.ButtonStyle.red, discord.ButtonStyle.grey])
            confirm_interaction = await interaction.response.send_message(
                f'**{interaction.user.name}**, this will reset **all** messages to the default one. '
                f'Are you sure?',
                view=confirm_view,
                ephemeral=True
            )
            confirm_view.interaction_message = confirm_interaction
            await confirm_view.wait()
            if confirm_view.value == 'confirm':
                kwargs = {}
                for activity in strings.ACTIVITIES:
                    activity_column = strings.ACTIVITIES_COLUMNS[activity]
                    kwargs[f'{activity_column}_message'] = strings.DEFAULT_MESSAGES[activity]
                await self.view.user_settings.update(**kwargs)
                await interaction.edit_original_message(
                    content=(
                        f'Changed all messages back to their default message.\n\n'
                        f'Note that running reminders do not update automatically.'
                    ),
                    view=None
                )
                embeds = await self.view.embed_function(self.view.bot, self.view.ctx, self.view.user_settings, self.view.activity)
                await interaction.message.edit(embeds=embeds, view=self.view)
                return
            else:
                await confirm_interaction.edit_original_message(content='Aborted', view=None)
                return
        elif self.custom_id == 'set_message':
            await interaction.response.send_message(
                f'**{interaction.user.name}**, please send the new reminder message to this channel (or `abort` to abort):',
            )
            try:
                answer = await self.view.bot.wait_for('message', check=check, timeout=60)
            except asyncio.TimeoutError:
                await interaction.edit_original_message(content=f'**{interaction.user.name}**, you didn\'t answer in time.')
                return
            if answer.mentions:
                for user in answer.mentions:
                    if user != answer.author:
                        await interaction.delete_original_message(delay=5)
                        followup_message = await interaction.followup.send(
                            content='Aborted. Please don\'t ping other people in your reminders.',
                        )
                        await followup_message.delete(delay=5)
                        return
            new_message = answer.content
            if new_message.lower() in ('abort','cancel','stop'):
                await interaction.delete_original_message(delay=3)
                followup_message = await interaction.followup.send('Aborted.')
                await followup_message.delete(delay=3)
                return
            if len(new_message) > 1024:
                await interaction.delete_original_message(delay=5)
                followup_message = await interaction.followup.send(
                    'This is a command to set a new message, not to write a novel :thinking:',
                )
                await followup_message.delete(delay=5)
                return
            for placeholder in re.finditer('\{(.+?)\}', new_message):
                placeholder_str = placeholder.group(1)
                if placeholder_str not in strings.DEFAULT_MESSAGES[self.view.activity]:
                    allowed_placeholders = ''
                    for placeholder in re.finditer('\{(.+?)\}', strings.DEFAULT_MESSAGES[self.view.activity]):
                        allowed_placeholders = (
                            f'{allowed_placeholders}\n'
                            f'{emojis.BP} {{{placeholder.group(1)}}}'
                        )
                    if allowed_placeholders == '':
                        allowed_placeholders = f'There are no placeholders available for this message.'
                    else:
                        allowed_placeholders = (
                            f'Available placeholders for this message:\n'
                            f'{allowed_placeholders.strip()}'
                        )
                    await interaction.delete_original_message(delay=3)
                    followup_message = await interaction.followup.send(
                        f'Invalid placeholder found.\n\n'
                        f'{allowed_placeholders}',
                        ephemeral=True
                    )
                    await followup_message.delete(delay=3)
                    return
            await interaction.delete_original_message(delay=3)
            followup_message = await interaction.followup.send(
                f'Message updated!\n\n'
                f'Note that running reminders do not update automatically.'
            )
            await followup_message.delete(delay=3)
        elif self.custom_id == 'reset_message':
            new_message = strings.DEFAULT_MESSAGES[self.view.activity]
        kwargs = {}
        activity_column = strings.ACTIVITIES_COLUMNS[self.view.activity]
        kwargs[f'{activity_column}_message'] = new_message
        await self.view.user_settings.update(**kwargs)
        embeds = await self.view.embed_function(self.view.bot, self.view.ctx, self.view.user_settings, self.view.activity)
        if interaction.response.is_done():
            await interaction.message.edit(embeds=embeds, view=self.view)
        else:
            await interaction.response.edit_message(embeds=embeds, view=self.view)


class DeleteCustomRemindersButton(discord.ui.Button):
    """Button to activate the select to delete custom reminders"""
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.grey, custom_id='active_select', label='Delete custom reminders',
                         emoji=None, row=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        self.view.remove_item(self)
        self.view.add_item(DeleteCustomReminderSelect(self.view, self.view.custom_reminders))
        embed = await self.view.embed_function(self.view.bot, self.view.user, self.view.user_settings)
        await interaction.response.edit_message(embed=embed, view=self.view)


class DeleteCustomReminderSelect(discord.ui.Select):
    """Select to delete custom reminders"""
    def __init__(self, view: discord.ui.View, custom_reminders: List[reminders.Reminder], row: Optional[int] = None):
        self.custom_reminders = custom_reminders

        options = []
        for reminder in custom_reminders:
            label = f'{reminder.custom_id} - {reminder.message[:92]}'
            options.append(discord.SelectOption(label=label, value=str(reminder.custom_id), emoji=None))
        super().__init__(placeholder='Delete custom reminders', min_values=1, max_values=1, options=options,
                         row=row, custom_id=f'delete_reminders')

    async def callback(self, interaction: discord.Interaction):
        select_value = self.values[0]
        for reminder in self.custom_reminders.copy():
            if reminder.custom_id == int(select_value):
                await reminder.delete()
                self.custom_reminders.remove(reminder)
        embed = await self.view.embed_function(self.view.user, self.view.user_settings)
        if self.custom_reminders:
            self.view.remove_item(self)
            self.view.add_item(DeleteCustomReminderSelect(self.view, self.view.custom_reminders))
            await interaction.response.edit_message(embed=embed, view=self.view)
        else:
            await interaction.response.edit_message(embed=embed, view=None)
            self.view.stop()


class ToggleTrackingButton(discord.ui.Button):
    """Button to toggle the auto-ready feature"""
    def __init__(self, style: Optional[discord.ButtonStyle], custom_id: str, label: str,
                 disabled: bool = False, emoji: Optional[discord.PartialEmoji] = None):
        super().__init__(style=style, custom_id=custom_id, label=label, emoji=emoji,
                         disabled=disabled, row=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        enabled = True if self.custom_id == 'track' else False
        await self.view.user_settings.update(tracking_enabled=enabled)
        self.view.value = self.custom_id
        await self.view.user_settings.refresh()
        if self.view.user_settings.tracking_enabled:
            self.style = discord.ButtonStyle.grey
            self.label = 'Stop tracking me!'
            self.custom_id = 'untrack'
        else:
            self.style = discord.ButtonStyle.green
            self.label = 'Track me!'
            self.custom_id = 'track'
        if not interaction.response.is_done():
            await interaction.response.edit_message(view=self.view)
        else:
            await self.view.message.edit(view=self.view)