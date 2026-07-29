"""Shared helper functions used by bot.py and cogs."""
import ast
from discord.ext import commands
from config import OWNER_ID, ACECON_MSG_LINK, ADVISORY_LINK
from utils import BotConfig

# Module-level singleton config instance
botconfig = BotConfig()


def is_authorized(ctx):
    """Check if the context author has an authorized role or is the bot owner."""
    try:
        for role in ['galactic war leader', 'galactic war advisor', 'turbo nerd', 'commander\U0001f3b1']:
            if role in [y.name.lower() for y in ctx.author.roles] or ctx.author.id == OWNER_ID:
                return True
    except AttributeError:
        return False


async def send_error_msg(ctx=None):
    """Send a network error message, or just print if ctx is None."""
    if ctx is None:
        print("network error detected")
        return
    return await ctx.reply("```Network error detected.\nPossible Automaton interference, please report to your nearest Democracy Officer.```")


def safe_parse_config(input_str):
    """Safely parse a config value string into a Python object."""
    clean_input = input_str.strip()
    if clean_input.lower() == 'true':
        return True
    if clean_input.lower() == 'false':
        return False
    try:
        return ast.literal_eval(clean_input)
    except (ValueError, SyntaxError):
        return clean_input


def acecon_format(num):
    """Format an ACECON level into a Discord message."""
    icon = botconfig.config['ICON_LIST']['value'][num]
    return f"We are at: \n## {icon} [ACECON {str(num)}]({ACECON_MSG_LINK}) {icon}\nSee [Advisory]({ADVISORY_LINK}) for more details."


def custom_cooldown(message):
    """Dynamic cooldown: no cooldown for authorized users, configured cooldown for others."""
    cooldown = botconfig.config['COOLDOWN']['value']
    if is_authorized(message):
        return None
    else:
        return commands.Cooldown(1, cooldown)
