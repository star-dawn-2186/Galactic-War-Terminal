"""Background task loops and event handlers."""
import os
import gc
import json
import time
import pickle
import asyncio
import datetime
import functools
from concurrent.futures import ProcessPoolExecutor

import aiohttp
import discord
import requests
from discord.ext import commands, tasks
from tabulate import tabulate

from config import (
    LEADER_ROLE_ID, HQ_CHANNEL, LOUNGE_CHANNEL, HANGOUT_CHANNEL, NEWS_CHANNEL,
    LIBERATION_DIR, EVENTS_DIR,
)
from helpers import is_authorized, send_error_msg, botconfig
from utils import (
    fetch_war_data, api_data, planet_data, warinfo_data, MO_data,
    format_duration, dss_donation_data,
)
from find_planets import (
    name_to_idx, get_stats_by_name, get_effects_by_idx, get_regions_by_name,
    get_defense_rating,
)
from parse_assignment import update_mo_tracker
from parse_dss import get_dss_info
from libcalc import get_librate_from_idx, update_librate, UPDATE_INTERVAL
from effcalc import calc_region_eff_from_name
from ticker import create_stock_ticker_gif
from cogs.events import gen_mo4_progress

process_executor = ProcessPoolExecutor(max_workers=1)


class Tasks(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Initialize reminder state
        if not os.path.isfile(os.path.join(EVENTS_DIR, "reminder_set.pkl")):
            with open(os.path.join(EVENTS_DIR, "reminder_set.pkl"), 'wb') as f:
                pickle.dump(False, f)

    def cog_unload(self):
        self.alert_loop.cancel()
        self.ticker_loop.cancel()
        self.reminder_loop.cancel()
        self.mo_loop.cancel()
        self.mo_archive_loop.cancel()
        self.leaderboard_loop.cancel()

    # ====================
    # Event Handlers
    # ====================

    @commands.Cog.listener()
    async def on_ready(self):
        self.alert_loop.start()
        self.ticker_loop.start()
        self.mo_archive_loop.start()
        self.reminder_loop.start()
        self.leaderboard_loop.start()
        self.mo_loop.start()

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        if thread.parent.id == HQ_CHANNEL:
            channel = self.bot.get_channel(NEWS_CHANNEL)
            thread_link = f"https://discord.com/channels/{thread.guild.id}/{thread.id}"
            confirm_msg = f"New thread: {thread_link}\nSend New MO thread notification?\n-# Send y or n"
            await self.bot.get_channel(LOUNGE_CHANNEL).send(confirm_msg)

            def is_valid_confirm(m):
                return m.content.lower() in ['y', 'n'] and is_authorized(m)

            try:
                confirm = await self.bot.wait_for('message', check=is_valid_confirm, timeout=600)
            except asyncio.TimeoutError:
                return await self.bot.get_channel(LOUNGE_CHANNEL).send("Timed out, notif not sent.")
            if confirm.content.lower() == 'y':
                return await channel.send(f"```New Major Order detected. Opening discussion thread.```\n{thread_link}")
            else:
                return await self.bot.get_channel(LOUNGE_CHANNEL).send("Notif not sent.")

    # ====================
    # MO Tracking Loops
    # ====================

    @tasks.loop(minutes=10)
    async def mo_loop(self):
        update_mo_tracker()

    @tasks.loop(minutes=30)
    async def mo_archive_loop(self):
        mo_tracker_path = os.path.join(EVENTS_DIR, 'mo_tracker.json')
        if not os.path.isfile(mo_tracker_path):
            return
        with open(mo_tracker_path, 'r') as f:
            data = f.read()
        with open(os.path.join(EVENTS_DIR, 'mo_archive.txt'), 'a') as f:
            f.write(f"{datetime.date.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')} {data}\n")

    # ====================
    # Alert Loop
    # ====================

    @tasks.loop(minutes=1)
    async def alert_loop(self):
        api = api_data()
        planets = planet_data()
        warinfo = warinfo_data()
        new_regions = await update_librate(mode='r')
        if None in [api, planets, warinfo]:
            return
        defenses = api.get('planetEvents')
        decays = {}
        subfactions = {}
        for idx in range(len(api.get('planetStatus'))):
            if int(idx) == 274:
                continue
            subfactions[str(idx)] = []

            effects, _ = get_effects_by_idx(api, idx)
            try:
                stats, _, _ = get_stats_by_name(api, planets, warinfo, idx)
                if 'decay' in stats:
                    decays[idx] = stats['decay']

                for effect in effects:
                    for sub in ['CORPS', 'JET', 'STRAIN', 'CYBORG', 'Appropriator', 'Mindless Mass', 'DRAGONROACH', 'HIVE LORD', 'VOTE SNATCHERS', 'INVASION FLEET']:
                        if sub.lower() in effect.lower() and effect.lower() != "jet brigade factories":
                            subfactions[str(idx)].append(effect)
            except Exception:
                pass

        defenses_path = os.path.join(LIBERATION_DIR, "defenses.txt")
        subfactions_path = os.path.join(LIBERATION_DIR, "subfactions.json")
        decays_path = os.path.join(LIBERATION_DIR, "decays.json")
        init = False
        if not os.path.isfile(defenses_path):
            with open(defenses_path, 'w') as f:
                f.writelines([str(defense['planetIndex']) + '\n' for defense in defenses])
            init = True
        if not os.path.isfile(subfactions_path):
            with open(subfactions_path, 'w') as f:
                json.dump(subfactions, f)
            init = True
        if not os.path.isfile(decays_path):
            with open(decays_path, 'w') as f:
                json.dump(decays, f)
            init = True

        if init:
            return

        with open(defenses_path, 'r') as f:
            prev_defenses = f.read().split('\n')

        for defense in defenses:
            if str(defense['planetIndex']) not in prev_defenses:
                idx, name = name_to_idx(defense['planetIndex'])
                try:
                    stats, _, _ = get_stats_by_name(api, planets, warinfo, name)
                except:
                    continue
                faction = stats['faction']
                effects = get_effects_by_idx(api, idx)[0]

                level, duration = stats['level'], stats['duration']
                rating = get_defense_rating(level, duration)
                msg = "!!=== PRIORITY ALERT: INCOMING "
                if defense['eventType'] == 0:
                    msg += "URGENT LIBERATION ORDERS"
                elif faction == 'Terminid':
                    msg += "BUG INFESTATION"
                elif faction == 'Automaton':
                    msg += "BOT INCURSION"
                else:
                    msg += "SQUID INVASION"

                msg += "  ===!!\n"
                msg += f"Planet: {name}\n"
                msg += f"Level {level} | {duration} Hours\n"
                msg += f"Difficulty Rating: {rating}\n"
                msg += "Planet effects:\n"
                for effect in effects:
                    msg += f"- {effect}\n"

                await self.bot.get_channel(HANGOUT_CHANNEL).send(f"```{msg}```")

        with open(defenses_path, 'w') as f:
            f.writelines([str(i['planetIndex']) + '\n' for i in defenses])

        with open(subfactions_path, 'r') as f:
            prev_subfactions = json.load(f)

        msg = "!!=== PRIORITY ALERT: ENEMY MOVEMENT ===!!\n"
        for idx in subfactions:
            _, name = name_to_idx(int(idx))
            try:
                stats, _, _ = get_stats_by_name(api, planets, warinfo, idx)
            except:
                continue
            if stats['campaign'] != "Already liberated":
                for sub in subfactions[idx]:
                    try:
                        if sub not in prev_subfactions[idx]:
                            msg += f"{sub.upper()} detected on: {name.upper()}\n"
                    except KeyError:
                        continue
                for sub in prev_subfactions[idx]:
                    if sub not in subfactions[idx]:
                        msg += f"{sub.upper()} no longer detected on: {name.upper()}\n"

        if msg.count('\n') > 1:
            await self.bot.get_channel(HANGOUT_CHANNEL).send(f"```{msg}```")
        with open(subfactions_path, 'w') as f:
            json.dump(subfactions, f)

        if new_regions != []:
            msg = "!!== PRIORITY ALERT: NEW REGION DETECTED ==!!\n"
            for rID in new_regions:
                idx = int(rID.split(':')[0])
                idx, name = name_to_idx(idx)
                r_idx = int(rID.split(':')[1])
                regions, _ = get_regions_by_name(api, warinfo, planets, name)
                for region in regions:
                    if region['r_idx'] == r_idx:
                        r_name = region['name']
                        msg += f"{r_name.upper()} on planet {name.upper()}\n"
                        break
            await self.bot.get_channel(HANGOUT_CHANNEL).send(f"```{msg}```")

        with open(decays_path, 'r') as f:
            prev_decays = json.load(f)
        msg = "!!== PRIORITY ALERT: PLANETARY RESISTANCE ==!!\n"
        for idx in decays:
            if str(idx) in prev_decays:
                change = ''
                if prev_decays[str(idx)] > decays[idx]:
                    change = "DECREASED"
                elif prev_decays[str(idx)] < decays[idx]:
                    change = "INCREASED"
                _, name = name_to_idx(int(idx))
                if change != '':
                    msg += f"Decay on {name.upper()} has {change} to {decays[idx]}%\n"

        if msg.count('\n') > 1:
            await self.bot.get_channel(HANGOUT_CHANNEL).send(f"```{msg}```")
        with open(decays_path, 'w') as f:
            json.dump(decays, f)

        try:
            dss_json = dss_donation_data()
            _, action_data = await get_dss_info(dss_json)
        except Exception:
            action_data = None

        if action_data is not None:
            dss_alert_path = os.path.join(LIBERATION_DIR, "dss_alerts.json")
            if os.path.isfile(dss_alert_path):
                with open(dss_alert_path, 'r') as f:
                    dss_state = json.load(f)
            else:
                dss_state = {}

            now = int(time.time())
            dss_msg = ""

            for action in action_data:
                a_name = action['name']
                if a_name not in dss_state:
                    dss_state[a_name] = {'eta_alert_sent': False, 'active_alert_sent': False, 'expires': None}

                state = dss_state[a_name]

                # Reset alerts if the action has expired
                if state['expires'] is not None and now > state['expires']:
                    state['eta_alert_sent'] = False
                    state['active_alert_sent'] = False
                    state['expires'] = None

                if action['is_active']:
                    state['expires'] = action['expires']
                    if not state['active_alert_sent']:
                        dss_msg += f"{a_name.upper()} is now ACTIVE\n"
                        state['active_alert_sent'] = True
                else:
                    eta = action['eta']
                    if eta is not None and (eta - now) <= 3600 and not state['eta_alert_sent']:
                        dss_msg += f"{a_name.upper()} IS CLOSE TO ACTIVATION\n"
                        state['eta_alert_sent'] = True

            if dss_msg:
                alert_text = "!!== PRIORITY ALERT: DEMOCRACY SPACE STATION ==!!\n" + dss_msg
                await self.bot.get_channel(HANGOUT_CHANNEL).send(f"```{alert_text}```")

            with open(dss_alert_path, 'w') as f:
                json.dump(dss_state, f)

    # ====================
    # Reminder Loop
    # ====================

    @tasks.loop(minutes=30)
    async def reminder_loop(self):
        reminder_path = os.path.join(EVENTS_DIR, "reminder_set.pkl")
        with open(reminder_path, 'rb') as f:
            reminder_set = pickle.load(f)
        mo_data = MO_data()
        if mo_data is None:
            return await send_error_msg()
        try:
            mo_ddl = mo_data[0]['expiresIn']
            if mo_ddl > 0:
                reminder_set = False
                with open(reminder_path, 'wb') as f:
                    pickle.dump(reminder_set, f)
            elif not reminder_set:
                lounge_channel = self.bot.get_channel(LOUNGE_CHANNEL)
                await lounge_channel.send(f"<@&{LEADER_ROLE_ID}>\n```MO expiration detected, please close the relevant thread as soon as possible.```")
                reminder_set = True
                with open(reminder_path, 'wb') as f:
                    pickle.dump(reminder_set, f)

        except IndexError:
            if not reminder_set:
                lounge_channel = self.bot.get_channel(LOUNGE_CHANNEL)
                await lounge_channel.send(f"<@&{LEADER_ROLE_ID}>\n```MO expiration detected, please close the relevant thread as soon as possible.```")
                reminder_set = True
                with open(reminder_path, 'wb') as f:
                    pickle.dump(reminder_set, f)

    # ====================
    # Ticker Loop
    # ====================

    @tasks.loop(seconds=UPDATE_INTERVAL)
    async def ticker_loop(self):
        success = False
        while not success:
            try:
                _ = await update_librate(mode='p')
                api = api_data()
                planets = planet_data()
                warinfo = warinfo_data()
                success = True
            except (aiohttp.ClientError, requests.RequestException):
                await asyncio.sleep(1)

        if None in [api, planets, warinfo]:
            return await send_error_msg()
        campaigns = api.get('campaigns')
        libdict = {}
        leaderboard = []
        for campaign in campaigns:
            idx = campaign['planetIndex']
            stats, _, name = get_stats_by_name(api, planets, warinfo, idx)
            defense = 'decay' in stats
            idx = stats['id']
            pop = stats['pop%']
            faction = stats['faction']
            librate = get_librate_from_idx(idx)[1]
            eta = stats['eta']
            if eta is None:
                required = stats['required']
                _, _, weighted_eff = calc_region_eff_from_name(api, warinfo, planets, name)

                if weighted_eff * stats['pop%'] == 0:
                    eta = "N/A"
                else:
                    eta = required / (weighted_eff * stats['pop%'])
            if librate is None:
                print("librate None error")
                return
            leaderboard.append([name, pop, librate, eta, faction[0].lower(), defense])
        leaderboard = sorted(leaderboard, key=lambda x: x[1], reverse=True)[:5]

        for i in leaderboard:
            if not i[-1]:
                positive = i[2] >= 0
            else:
                try:
                    positive = i[3] >= 0
                except TypeError:
                    positive = True

            if isinstance(i[3], str):
                i[3] = 'N/A'
            else:
                i[3] = format_duration(abs(i[3]) * 3600)

            libdict[i[0].upper()] = (f"{abs(i[2])}%", positive, f"ETA {i[3]}", f"POP {i[1]}%", i[4])

        if botconfig.config['TICKER_TOGGLE']['value']:
            thing_to_run = functools.partial(create_stock_ticker_gif, libdict, "/var/www/GWT/gwt-ticker/stock_ticker.gif")
            await self.bot.loop.run_in_executor(process_executor, thing_to_run)

            try:
                gc.collect()
            except Exception:
                pass

            for ticker_channel in botconfig.config['TICKER_CHANNEL']['value']:
                try:
                    channel = self.bot.get_channel(ticker_channel)
                    latest = [msg async for msg in channel.history(limit=1)]
                except AttributeError:
                    print(f"Channel ID {ticker_channel}'s history cannot be accessed")
                    continue
                if len(latest) != 0 and latest[0].author.id == self.bot.user.id and not latest[0].content:
                    try:
                        with open("/var/www/GWT/gwt-ticker/stock_ticker.gif", "rb") as fp:
                            file = discord.File(fp, filename="/var/www/GWT/gwt-ticker/stock_ticker.gif")
                            await latest[0].edit(attachments=[file])
                    except Exception as e:
                        print(e)
                else:
                    try:
                        with open("/var/www/GWT/gwt-ticker/stock_ticker.gif", "rb") as fp:
                            await channel.send(file=discord.File(fp, filename="/var/www/GWT/gwt-ticker/stock_ticker.gif"), silent=True)
                    except Exception:
                        print("Streaming stock ticker GIF failed, using fallback")
                        await channel.send(file=discord.File("/var/www/GWT/gwt-ticker/stock_ticker.gif"), silent=True)
        else:
            liblist = []
            for key in libdict:
                liblist.append([key, libdict[key][0]])
            for ticker_channel in botconfig.config['TICKER_CHANNEL']['value']:
                latest = [msg async for msg in self.bot.get_channel(ticker_channel).history(limit=1)]
                if len(latest) == 0 or latest[0].author.id != self.bot.user.id:
                    await self.bot.get_channel(ticker_channel).send(f"```{tabulate(liblist)}```")
                else:
                    await latest[0].edit(content=f"```{tabulate(liblist)}```")

    # ====================
    # Leaderboard / MO4 Loop
    # ====================

    @tasks.loop(hours=3)
    async def leaderboard_loop(self):
        msg, _ = gen_mo4_progress()
        if msg is None:
            return
        try:
            channel = self.bot.get_channel(1528736305012412487)
            latest = [m async for m in channel.history(limit=1)]
        except AttributeError:
            print("Channel history cannot be accessed")
            return
        if len(latest) != 0 and latest[0].author.id == self.bot.user.id and "MO4: " in latest[0].content:
            try:
                await latest[0].delete()
            except Exception:
                pass
        await channel.send(msg)


async def setup(bot):
    await bot.add_cog(Tasks(bot))
