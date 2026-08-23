"""Information commands: get, get_top, get_region, dss, dss_vote, sitrep, ddl, progress."""
import time
import json
import os

import discord
from discord.ext import commands
from tabulate import tabulate

from config import LOUNGE_CHANNEL, LAB_CHANNEL, EVENTS_DIR
from helpers import is_authorized, send_error_msg, custom_cooldown, acecon_format, botconfig
from utils import (
    fetch_war_data, api_data, dss_donation_data, MO_data,
    format_environmental_data, format_region_data, format_dss_votes,
    format_mo_progress, convert_time, format_gambitcalc,
    cooldown_error_handler,
)
from find_planets import (
    name_to_idx, get_stats_by_name, get_effects_by_idx,
    get_regions_by_name, get_defense_rating,
)
from parse_dss import get_dss_info
from parse_assignment import parse_mo
from horse import horse_predict
from effcalc import calc_region_eff_from_name


class Info(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ====================
    # DSS Commands
    # ====================

    @commands.command(name='dss_vote')
    @commands.dynamic_cooldown(custom_cooldown, commands.BucketType.user)
    async def dss_voting_command(self, ctx):
        api = api_data()
        if api is None:
            return await send_error_msg(ctx)
        secret = ctx.channel.id in [LOUNGE_CHANNEL, LAB_CHANNEL]
        try:
            dss_dll = convert_time(api.get('spaceStations')[0]['currentElectionEndWarTime'], api)
            dss_txt = format_dss_votes(secret)
            ddl_txt = f"DSS moves: <t:{dss_dll}:R>\n"
            await ctx.reply(ddl_txt + dss_txt)
        except Exception as e:
            print(e)
            await ctx.reply("DSS data offline.")

    @dss_voting_command.error
    async def dss_voting_error(self, ctx, error):
        await cooldown_error_handler("Look up.")(ctx, error)

    @commands.command(name='dss')
    @commands.dynamic_cooldown(custom_cooldown, commands.BucketType.user)
    async def dss_command(self, ctx):
        dss_json = dss_donation_data()
        text, _ = await get_dss_info(dss_json)
        await ctx.reply(text)

    @dss_command.error
    async def dss_command_error(self, ctx, error):
        await cooldown_error_handler("Look up.")(ctx, error)

    # ====================
    # Progress / MO
    # ====================

    @commands.command(name='progress')
    @commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
    async def progress_command(self, ctx):
        mo_data = MO_data()
        orders = parse_mo(mo_data)
        mo_tracker_path = os.path.join(EVENTS_DIR, 'mo_tracker.json')
        if os.path.isfile(mo_tracker_path):
            with open(mo_tracker_path, 'r') as f:
                deltas = json.load(f)
        for order in orders:
            if os.path.isfile(mo_tracker_path):
                for task in order['tasks']:
                    delta = deltas[orders.index(order)][order['tasks'].index(task)]['delta']
                    goal = task['goal']
                    task['rate'] = round(delta / goal * 600, 2)
            await ctx.reply(format_mo_progress(order))

    # ====================
    # Planet Commands
    # ====================

    @commands.command(name="get", help="Fetches real-time info about a planet.")
    @commands.dynamic_cooldown(custom_cooldown, commands.BucketType.user)
    async def get_command(self, ctx, *, name: str = commands.parameter(description="- Name (case insensitive) or ID of the desired planet.")):
        data = await fetch_war_data()
        if data is None:
            return await send_error_msg(ctx)
        api, planet, warinfo = data

        stats = get_stats_by_name(api, planet, warinfo, name)
        if stats is None:
            return await ctx.reply("Unable to find planet.")
        static, names, name = stats
        idx = static['id']
        # Avery ARG Special
        # arg = idx == 227
        arg = False
        

        has_region = static['has regions']
        environmentals = static['environmentals']
        if not is_authorized(ctx):
            for key in ['id', 'environmentals', 'dist', 'has regions']:
                try:
                    static.pop(key)
                except KeyError:
                    continue

        static_txt = []
        for key in static:
            if not (key == 'progress' or key == 'eta'):
                static_txt.append([key, str(static[key])])
        effects = get_effects_by_idx(api, idx)[0]

        eta = static['eta']
        progress = static['progress']
        current = time.time()
        campaign = static['campaign']
        regions, _ = get_regions_by_name(api, warinfo, planet, name)
        total_region_pop = sum([r['pop'] for r in regions])
        total_region_health = sum([r['health'] for r in regions])
        all_liberated = all([r['eta'] in ["**Liberty Secured**", "Unavailable"] for r in regions])
        flag = 'level' in static
        usealg = eta is None
        if usealg:
            required = static['required']
            if total_region_health <= required or (flag and not all_liberated):
                opt_pop = static['pop%'] * total_region_pop / 100
            else:
                opt_pop = static['pop%'] * (1 - total_region_pop / 100)

            _, _, weighted_eff = calc_region_eff_from_name(api, warinfo, planet, name)
            regen_per_hour = static.get('regen', 0) * 3600
            rate = weighted_eff * opt_pop - regen_per_hour
            if rate > 0:
                eta = required / rate
            elif rate < 0:
                eta = (static['maxhealth'] - static['health']) / rate
            else:
                eta = "**STALEMATE**"

        if campaign == "Already liberated":
            etamsg = "**Liberty Secured**"
            progress = 100
        elif campaign == "Currently unreachable":
            etamsg = "**Unreachable**"
            progress = 0
        elif eta == "**STALEMATE**" or eta == "**UNCERTAIN**":
            etamsg = eta
        elif float(eta) >= 0:
            etamsg = f"**Full Liberation <t:{int(current + eta * 3600)}:R>**"
            if 'ddl' in static:
                deadline = static['ddl']
                etamsg += f"\n**Planet lost: <t:{int(deadline)}:R>**"
        elif float(eta) < 0:
            etamsg = f"**Full Withdrawal <t:{int(current - eta * 3600)}:R>**"
        if usealg:
            etamsg += "\n-# Regions detected, using experimental ETA extrapolation algorithm"

        msg = f"## Planet Summary: {name.upper()}\n"

        if is_authorized(ctx):
            msg += f"### {names}\n\n"

        msg += format_environmental_data(environmentals.split('\n'))
        msg += f"### {campaign.upper()}\n"
        if not flag:
            msg += "-" * 20 + '\n'
            msg += f"**{progress}% LIBERATED**\n{etamsg}\n"
        else:
            msg += "-" * 20 + '\n'
            level = static['level']
            duration = static['duration']
            msg += f"LEVEL **{level}** | **{duration}** HOURS\n"
            rating = get_defense_rating(level, duration)
            msg += f"Difficulty rating: __{rating}__\n"
            if campaign.upper() == 'LIBERATION':
                msg += f"**{progress}% LIBERATED**\n{etamsg}\n"
            else:
                msg += f"**{progress}% DEFENDED**\n{etamsg}\n"

        msg += "-" * 20 + '\n'
        msg += "### Planet stats:\n"
        msg += f"```{tabulate(static_txt, colalign=('left',))}```\n"
        if not is_authorized(ctx):
            return await ctx.reply(msg)

        score = horse_predict(static, effects)
        msg += "### Planet Effects:\n - "
        if effects == []:
            msg += "No current effects detected.\n"
        elif not arg:
            msg += '\n - '.join(effects) + '\n'
        else:
            msg += '1BjbsgTJu_HXB7hZbKYn5MIJZsJais94Svv7G8gxqUok\n'
        if score is not None:
            msg += f"### Holistic Overall Reallocation Sequence Evaluator (H.O.R.S.E.) score:\n{round(score * 100, 1)}"
        else:
            msg += "-# Planet unreachable or already liberated, H.O.R.S.E. not available"

        return await ctx.reply(msg)

    @get_command.error
    async def get_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.reply(f"\n-# Command on cooldown, try again after {error.retry_after:.2f}s.")
        else:
            print(error)
            import traceback
            traceback.print_exc()

    @commands.command(name='get_region')
    @commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
    async def getregion_command(self, ctx, *, name: str):
        data = await fetch_war_data()
        if data is None:
            return await send_error_msg(ctx)
        api, planet, warinfo = data
        try:
            regions, name = get_regions_by_name(api, warinfo, planet, name)
        except Exception:
            return await ctx.reply("Unable to find planet.")
        if regions == []:
            return await ctx.reply("No currently active regions on this planet.")
        result = format_region_data(regions, name)
        return await ctx.reply(result)

    @commands.command(name="get_top", help="Fetches info about the planets with the most amount of divers deployed.")
    @commands.dynamic_cooldown(custom_cooldown, commands.BucketType.user)
    async def gettop_command(self, ctx):
        data = await fetch_war_data()
        if data is None:
            return await send_error_msg(ctx)
        api, planets, warinfo = data

        campaigns = api.get('campaigns')
        leaderboard = []
        for campaign in campaigns:
            idx = campaign['planetIndex']
            stats, _, name = get_stats_by_name(api, planets, warinfo, idx)
            leaderboard.append([name.upper(), stats['progress'], stats['pop%']])
        leaderboard = sorted(leaderboard, key=lambda x: x[2], reverse=True)
        leaderboard.insert(0, ['Planet', 'Progress', 'pop%'])
        if is_authorized(ctx):
            await ctx.reply(f"## Top Ten Deployed Planets: \n```{tabulate(leaderboard[:11])}```")
        else:
            await ctx.reply(f"## Top Three Deployed Planets: \n```{tabulate(leaderboard[:4])}```")

    @gettop_command.error
    async def gettop_error(self, ctx, error):
        await cooldown_error_handler()(ctx, error)

    # ====================
    # Sitrep / DDL
    # ====================

    @commands.command(name="sitrep", help="Fetches a short summary of the current orders and situation.")
    @commands.dynamic_cooldown(custom_cooldown, commands.BucketType.user)
    async def sitrep(self, ctx):
        with open('ACECON.txt', 'r') as f:
            acecon = int(f.read())
        with open('ADVISORY.txt', 'r') as f:
            advisory = f.read()

        api = api_data()
        if api is None:
            return await send_error_msg(ctx)

        return await ctx.reply(acecon_format(acecon) + f"\n## __Advisory Summary__\n{advisory}")

    @sitrep.error
    async def sitrep_error(self, ctx, error):
        await cooldown_error_handler("Look up.")(ctx, error)

    @commands.command(name='ddl')
    @commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
    async def ddl(self, ctx):
        api = api_data()
        mo_data = MO_data()
        if None in [api, mo_data]:
            return await send_error_msg(ctx)

        try:
            dss_dll = convert_time(api.get('spaceStations')[0]['currentElectionEndWarTime'], api)
            mo_ddl = int(time.time()) + mo_data[0]['expiresIn']
            await ctx.reply(f"Current MO ends: <t:{mo_ddl}:R>\n```<t:{mo_ddl}:R>```\nDSS moves: <t:{dss_dll}:R>\n```<t:{dss_dll}:R>```")
        except Exception:
            await ctx.reply("DSS data offline.")


async def setup(bot):
    await bot.add_cog(Info(bot))
