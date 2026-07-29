"""Administrative commands: config, kill, set_acecon, set_advisory, send, dispatch."""
import sys
import asyncio

import discord
from discord.ext import commands

from config import (
    OWNER_ID, LEADER_ROLE_ID, ADVISORY_CHANNEL, NEWS_CHANNEL,
)
from helpers import (
    is_authorized, send_error_msg, safe_parse_config, acecon_format, botconfig,
)
from utils import api_data
from render_mo4 import format_html, render_html_to_image


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="config")
    @commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
    async def config_command(self, ctx):
        await ctx.reply("Current configuration:\n" + str(botconfig) +
                        "\nType the name and value (e.g., COOLDOWN 600)")

        def check(m):
            if not (m.author == ctx.author and m.channel == ctx.channel):
                return False
            parts = m.content.split(' ', 1)
            if len(parts) < 2:
                return False
            name = parts[0]
            return name in botconfig.config

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=300)
            parts = msg.content.split(' ', 1)
            name, raw_value = parts[0], parts[1]

            if "LIST" in name:
                value = raw_value.split(' ')
            else:
                value = safe_parse_config(raw_value)

            botconfig.update_config(name, value)
            await ctx.reply(f"Config updated:\n{botconfig}")

        except asyncio.TimeoutError:
            await ctx.reply("Config session timed out.")

    @commands.command(name="kill")
    async def kill_command(self, ctx):
        if ctx.author.id == OWNER_ID:
            await ctx.reply("Powering down.")
            sys.exit()

    @commands.command(name='set_acecon')
    @commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
    async def acecon_command(self, ctx, ACECON: str):
        with open('ACECON.txt', 'w') as f:
            f.write(ACECON)
        await ctx.reply(f"ACECON set to: {int(ACECON)}")

    @commands.command(name='set_advisory')
    @commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
    async def advisory_command(self, ctx):
        await ctx.reply("Your next message will be set as the current Advisory Summary.\n-# Send !cancel to cancel.")

        def is_valid_advisory(m):
            return m.author == ctx.author

        try:
            advisory = await self.bot.wait_for('message', check=is_valid_advisory, timeout=300)
            advisory_text = advisory.content
        except asyncio.TimeoutError:
            return await ctx.reply("Timed out, advisory has not been updated.", mention_author=False)

        if advisory_text == '!cancel':
            await ctx.reply("Action cancelled, advisory has not been updated.", mention_author=False)
        else:
            line_cnt = advisory_text.count('\n')

            if line_cnt > botconfig.config['MAX_LINE']['value']:
                await ctx.reply("Too many lines detected. Please be succinct with Advisory Summaries.\nAdvisory has not been updated.", mention_author=False)

            await ctx.reply(f"New Advisory:\n {advisory_text}\nConfirm reset advisory?\n-# Send y or n")

            def is_valid_confirm(m):
                return m.content.lower() in ['y', 'n'] and m.author == ctx.author

            try:
                confirm = await self.bot.wait_for('message', check=is_valid_confirm, timeout=120)
                confirm = confirm.content.lower()
            except asyncio.TimeoutError:
                return await ctx.reply("Timed out, advisory has not been updated.", mention_author=False)

        if confirm == 'y':
            with open("ADVISORY.txt", 'w') as f:
                f.write(advisory_text)
            with open("ACECON.txt", 'r') as f:
                acecon = int(f.read())
            await self.bot.get_channel(ADVISORY_CHANNEL).send(
                acecon_format(acecon) + f"\n## __Advisory Summary__\n{advisory_text}"
            )
            await ctx.reply("Advisory has been set.", mention_author=False)
        else:
            await ctx.reply("Action cancelled, advisory has not been updated.", mention_author=False)

    @commands.command(name='send')
    @commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
    async def send_msg(self, ctx):
        await ctx.reply("Paste the channel (starting with #) you want the message to send to.")

        def is_valid_channel(m):
            msg = m.content
            is_channel_tag = msg.startswith("<#") and msg.endswith(">")
            is_channel_link = msg.startswith("https://discord.com/channels/")
            return (is_channel_tag or is_channel_link) and m.author == ctx.author

        try:
            channel_id = await self.bot.wait_for('message', check=is_valid_channel, timeout=120)
            channel_id = channel_id.content
            if channel_id.startswith('<'):
                channel_id = int(channel_id.lstrip('<#').rstrip('>'))
            elif channel_id.startswith('http'):
                channel_id = int(channel_id.split('/')[-1])
        except asyncio.TimeoutError:
            return await ctx.reply("Timed out.", mention_author=False)
        except Exception as e:
            print(e)
            return await ctx.reply("Invalid channel name. Please retry.")

        if channel_id == NEWS_CHANNEL:
            leader = discord.utils.get(ctx.guild.roles, id=LEADER_ROLE_ID)
            if leader not in ctx.author.roles:
                return await ctx.reply("You're not authorized to send messages in that channel.")

        try:
            channel = await self.bot.fetch_channel(channel_id)
            if not channel:
                return await ctx.reply("Invalid channel name. Please retry.")
        except discord.errors.Forbidden:
            return await ctx.reply("Access forbidden.")

        await ctx.reply("Your next message will be sent to that channel.\n-# type 'cancel' to cancel")

        def is_valid_msg(m):
            return m.author == ctx.author

        try:
            message = await self.bot.wait_for('message', check=is_valid_msg, timeout=120)
            msg = message.content
        except asyncio.TimeoutError:
            return await ctx.reply("Timed out.", mention_author=False)

        if message.attachments:
            files = [await attachment.to_file() for attachment in message.attachments]
        else:
            files = False

        if msg == 'cancel':
            return await ctx.reply("Cancelled.")
        else:
            await ctx.reply("Confirm send message?\n-# Send y or n")

            def is_valid_confirm(m):
                return m.content.lower() in ['y', 'n'] and m.author == ctx.author

            try:
                confirm = await self.bot.wait_for('message', check=is_valid_confirm, timeout=120)
                confirm = confirm.content.lower()
            except asyncio.TimeoutError:
                return await ctx.reply("Timed out.", mention_author=False)

        if confirm == 'y':
            if not files:
                await channel.send(f"```{msg}```")
            else:
                await channel.send(files=files)
            return await ctx.reply("Message sent.")
        else:
            await ctx.reply("Action cancelled.", mention_author=False)

    @commands.command(name='dispatch')
    @commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
    async def gen_dispatch(self, ctx, title: str, body: str):
        if not ctx.message.attachments:
            content = format_html(title, body)
        else:
            img = ctx.message.attachments[0]
            content_type = img.content_type
            if not content_type.startswith('image'):
                return await ctx.reply("```No image attachment detected, please retry.```")
            await img.save(fp='render_img/header.png')
            content = format_html(title, body, 'render_img/header.png')

        with open('render_img/temp.html', 'w') as f:
            f.write(content)
        img_stream = await render_html_to_image(content)
        img_file = discord.File(fp=img_stream, filename='render.png')
        await ctx.reply(file=img_file)


async def setup(bot):
    await bot.add_cog(Admin(bot))
