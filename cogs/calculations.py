"""Calculation commands: effcalc, gambit, dmg."""
import math

from discord.ext import commands
from tabulate import tabulate

from helpers import send_error_msg, custom_cooldown
from utils import fetch_war_data, fetch_im, format_gambitcalc, cooldown_error_handler
from find_planets import name_to_idx
from static_data import diff_to_dmg
from effcalc import calc_region_eff_from_name
from gambit_calculator import calc_gambit


class Calculations(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='effcalc')
    @commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
    async def effcalc_command(self, ctx, *, name: str):
        data = await fetch_war_data()
        if data is None:
            return await send_error_msg(ctx)
        api, planets, warinfo = data

        effs, planet_eff, _ = calc_region_eff_from_name(api, warinfo, planets, name)
        if planet_eff is None:
            return await ctx.reply("Planet not found.")

        _, name = name_to_idx(name)
        msg = f"### Eff calc for planet: {name.upper()}\n"

        if effs is None:
            msg += "-# No regions found.\n"
            msg += f" Planetary eff: {planet_eff}\n"
        else:
            msg += f" - Non-region planetary eff: {planet_eff}\n"
            msg += "Region eff:\n"
            msg += f"```{tabulate(effs)}```"

        return await ctx.reply(msg)

    @commands.command(name="gambit", help="Calculates feasibility of a gambit.")
    @commands.dynamic_cooldown(custom_cooldown, commands.BucketType.user)
    async def gambitcalc(self, ctx, *, name: str):
        data = await fetch_war_data()
        if data is None:
            return await send_error_msg(ctx)
        api, planets, warinfo = data

        response = calc_gambit(name, api, planets, warinfo)
        msg = format_gambitcalc(response)
        if msg is None:
            msg = "This is not a defense."
        return await ctx.reply(msg)

    @gambitcalc.error
    async def gambitcalc_error(self, ctx, error):
        await cooldown_error_handler()(ctx, error)

    @commands.command(name="dmg", help="Fetches a list of damage dealt per difficulty with the current IM.")
    @commands.dynamic_cooldown(custom_cooldown, commands.BucketType.user)
    async def dmgcalc(self, ctx):
        im = await fetch_im()
        if im is None:
            return await send_error_msg(ctx)
        results = []
        for diff in diff_to_dmg:
            name = diff[0]
            avg_mission_dmg = round(sum([math.floor(im * dmg) for dmg in diff[1:]]) / (len(diff) - 1), 2)
            non_ocb_dmg = math.floor(im * diff[1]) if len(diff) > 2 else 'N/A'
            ocb_dmg = math.floor(im * diff[-1])
            results.append([name, avg_mission_dmg, non_ocb_dmg, ocb_dmg])
        table = tabulate(results, headers=["", "Avg", "Non-OCB", "OCB"], stralign="left")
        msg = f"### Current Impact Modifier: {im}\n```{table}```"
        return await ctx.reply(msg)

    @dmgcalc.error
    async def dmgcalc_error(self, ctx, error):
        await cooldown_error_handler()(ctx, error)


async def setup(bot):
    await bot.add_cog(Calculations(bot))
