import discord
import pickle
import asyncio
from discord.ext import commands, tasks
import time
import gc
import os
import sys
import functools
from concurrent.futures import ProcessPoolExecutor
import ast
import datetime
import json
import numpy as np
from tabulate import tabulate
from utils import *
from find_planets import * 
from horse import horse_predict
from ticker import create_stock_ticker_gif, release_memory
from libcalc import get_librate_from_idx, update_librate
from ocr import img_to_stats, summary_from_stats
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

process_executor = ProcessPoolExecutor(max_workers=1)

TOKEN = pickle.load(open('token.pkl','rb')) #not gonna show my token to ya :)
acecon_msg_link = 'https://discord.com/channels/1261556132640456764/1427786162272997526/1430116186967904427'
advisory_link = 'https://discord.com/channels/1261556132640456764/1427786162272997526'
LEADER_ROLE_ID = 1372466615798726707
HQ_CHANNEL = 1369361948336062685
LOUNGE_CHANNEL = 1427787543394385930
NEWS_CHANNEL = 1379181040731422822

if not os.path.isfile("reminder_set.pkl"):
    reminder_set = False
    with open("reminder_set.pkl",'wb') as f:
        pickle.dump(reminder_set, f)
else:
    with open("reminder_set.pkl", 'rb') as f:
        reminder_set = pickle.load(f)
        
joe = 803676742639550544

from libcalc import UPDATE_INTERVAL

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="$", intents=intents)
botconfig = BotConfig()

def custom_cooldown(message):
    COOLDOWN = botconfig.config['COOLDOWN']['value']
    if is_authorized(message):
        return None
    else:
        return commands.Cooldown(1,COOLDOWN)

def safe_parse_config(input_str):
    clean_input = input_str.strip()
    if clean_input.lower() == 'true':
        return True
    if clean_input.lower() == 'false':
        return False
    try:
        return ast.literal_eval(clean_input)
    except (ValueError, SyntaxError):
        return clean_input


def is_authorized(ctx):
    try:
        for role in ['galactic war leader', 'galactic war advisor', 'turbo nerd', 'commander🎱']:
            if role in [y.name.lower() for y in ctx.author.roles] or ctx.author.id == joe:
                return True
    except AttributeError:
        return False

async def format_dss_votes():
    dss_data = await DSS_voting_data()
    data = sorted(dss_data['Options'], key = lambda d: d['Percentage'], reverse=True)
    tab = []
    for planet in data:
        tab.append([planet['Name'],str(planet['Percentage'])+'%'])
    txt = tabulate(tab, numalign='left')
    return f"```{txt}```"

async def send_error_msg(ctx=None):
    if ctx is None:
        print("network error detected")
        return
    return await ctx.reply("```Network error detected.\nPossible Automaton interference, please report to your nearest Democracy Officer.```")

def acecon_format(num):
    icon = botconfig.config['ICON_LIST']['value'][num]
    return f"We are at: \n## {icon} [ACECON {str(num)}]({acecon_msg_link}) {icon}\nSee [Advisory]({advisory_link}) for more details."

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')

    ticker_loop.start()
    eta_loop.start()
    reminder_loop.start()
    


# Notification when a new MO thread is created
@bot.event
async def on_thread_create(thread):
    if thread.parent.id == HQ_CHANNEL:
        GWR_channel = bot.get_channel(botconfig.config['GWR_CHANNEL']['value'])
        thread_link = f"https://discord.com/channels/{thread.guild.id}/{thread.id}"
        await GWR_channel.send(f"```New Major Order detected. Opening discussion thread.```\n{thread_link}")


# --- CYBERSTAN SPECIAL ---
@tasks.loop(minutes = 60)
async def eta_loop():
    api = await api_data()
    if api is None:
        return
    
    # Cyberstan Offensive Special
    if not datetime.datetime.now().minute == 0:
        return
    if api.get("globalResources"):
        health_bar = api.get("globalResources")[0]
        reinforcements_left = health_bar['currentValue'] / 2000000
        total_players = 0
        for planet in api.get('planetStatus'):
            total_players += planet['players']
            
        if not os.path.isfile('health_bar_log.txt'):
            with open('health_bar_log.txt', 'w') as f:
                f.write(f"{reinforcements_left}\t{total_players}\n")
                
        else:
            with open('health_bar_log.txt', 'a+') as f:
                f.write(f"{reinforcements_left}\t{total_players}\n")
                
            with open('health_bar_log.txt', 'r') as f:
                lines = f.read().split('\n')
                data = [float(i.split('\t')[0]) for i in lines if i != '']
                pop = [int(i.split('\t')[1]) for i in lines if i != '' and '\t' in i]
                
            if len(data) < 25:
                return
            
            d_data = [(data[i-1] - data[i])*2e6 for i in range(1, len(data))]
            
            dateax = [datetime.datetime.now() - datetime.timedelta(hours = i) for i in range(24)]
            dateax.reverse()
            
            fig, (ax1, ax3) = plt.subplots(2, 1, figsize=(15, 12), sharex=True, constrained_layout=True)
            
            ax1.set_ylabel("Reserve Forces, %")
            ax1.plot(dateax, data[-24:])
            
            
            if len(d_data) >= 25:
                ax2 = ax1.twinx()
                ax2.set_ylabel("Forces drain rate")
                ax2.plot(dateax, d_data[-24:], linestyle = 'dashed', color='red', label='')

            if len(pop) < 25:
                pop = [np.nan] * (25 - len(pop)) + pop
            
            ax3.set_ylabel("Total diver population")
            ax3.plot(dateax, pop[-24:])
            
            regions = [
                        (1, 5, 'red', 'NA Peak'),
                        (9, 13, 'gold', 'AU Peak'),
                        (13, 16, 'cyan', 'SEA Peak'),
                        (19, 23, 'limegreen', 'EU Peak')
                    ]

            unique_days = sorted(list(set([d.date() for d in dateax])))

            for day in unique_days:
                for start_h, end_h, color, label in regions:
                    # Create datetime objects for the start and end of the peak on this day
                    span_start = datetime.datetime.combine(day, datetime.time(hour=start_h))
                    span_end = datetime.datetime.combine(day, datetime.time(hour=end_h))
                    
                    # Only draw if the span overlaps with our visible x-axis range
                    if span_start < dateax[-1] and span_end > dateax[0]:
                        # Clip the span to the actual axis limits
                        actual_start = max(span_start, dateax[0])
                        actual_end = min(span_end, dateax[-1])
                        
                        # Draw the span
                        ax3.axvspan(actual_start, actual_end, color=color, alpha=0.2, label=label)

            handles, labels = ax3.get_legend_handles_labels()
            by_label = dict(zip(labels, handles))
            ax3.legend(by_label.values(), by_label.keys(), loc='upper right', bbox_to_anchor=(1, 1))
            
            date_form = mdates.DateFormatter('%H:%M')
            ax1.xaxis.set_major_formatter(date_form)
            ax1.grid(True)
            ax3.xaxis.set_major_formatter(date_form)
            fig.autofmt_xdate()
            plt.savefig('imgcache/health_logs.png',bbox_inches='tight')
            plt.close()
            
            if datetime.datetime.now().hour == 18:
                d_health = (data[-25] - data[-1]) / 24
                lab_channel = bot.get_channel(LOUNGE_CHANNEL)
                await lab_channel.send(f"```24-hour average drain rate: {d_health:.4f}%, or {int(d_health * 2000)}k per hour```", file=discord.File('imgcache/health_logs.png'))



# Reminder to close threads when MO ends
@tasks.loop(minutes = 30)
async def reminder_loop():
    with open("reminder_set.pkl",'rb') as f:
        reminder_set = pickle.load(f)
    mo_data = await MO_data()
    if mo_data is None:
        return await send_error_msg()
    try:
        mo_ddl = mo_data[0]['expiresIn']
        if mo_ddl > 0:
            reminder_set = False
            with open('reminder_set.pkl','wb') as f:
                pickle.dump(reminder_set, f)
        elif not reminder_set:
            lounge_channel = bot.get_channel(LOUNGE_CHANNEL)
            await lounge_channel.send(f"<@&{LEADER_ROLE_ID}>\n```MO expiration detected, please close the relevant thread as soon as possible.```")
            reminder_set = True
            with open('reminder_set.pkl','wb') as f:
                pickle.dump(reminder_set, f)
                
    except IndexError:
        if not reminder_set:
            lounge_channel = bot.get_channel(LOUNGE_CHANNEL)
            await lounge_channel.send(f"<@&{LEADER_ROLE_ID}>\n```MO expiration detected, please close the relevant thread as soon as possible.```")
            reminder_set = True
            with open('reminder_set.pkl','wb') as f:
                pickle.dump(reminder_set, f)

# Periodic ticker GIF generation
@tasks.loop(seconds=UPDATE_INTERVAL)
async def ticker_loop():
    success = False
    while not success:
        try:
            await update_librate()
            api = await api_data()
            planets = await planet_data()
            warinfo = await warinfo_data()
            success = True
        except aiohttp.ClientError:
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
        librate = get_librate_from_idx(idx)
        eta = stats['eta']
        if librate is None:
            return
        leaderboard.append([name,pop,librate,eta,faction[0].lower(),defense])
    leaderboard = sorted(leaderboard, key = lambda x: x[1], reverse=True)[:5]
    
    for i in leaderboard:
        if not i[-1]:
            positive = i[2] >= 0
        else:
            try:
                positive = i[3] >= 0
            except:
                positive = True
            
        if type(i[3]) == str:
            i[3] = 'N/A'
        else:
            i[3] = format_duration(abs(i[3])*3600)
        
        libdict[i[0].upper()] = (f"{abs(i[2])}%", positive, f"ETA {i[3]}", f"POP {i[1]}%", i[4])
    
    if botconfig.config['TICKER_TOGGLE']['value']:
        
        thing_to_run = functools.partial(create_stock_ticker_gif, libdict, "stock_ticker.gif")
        await bot.loop.run_in_executor(process_executor, thing_to_run)
        
        # Attempt to free large image buffers ASAP before sending
        try:
            gc.collect()
        except Exception:
            pass

        for ticker_channel in botconfig.config['TICKER_CHANNEL']['value']:
            try:
                channel = bot.get_channel(ticker_channel)
                latest = [msg async for msg in channel.history(limit=1)]
            except AttributeError:
                print(f"Channel ID {ticker_channel}'s history cannot be accessed")
                continue
            # Stream the file from disk to avoid building large in-memory payloads.
            # If a previous bot message exists, delete it and send a fresh upload.
            if len(latest) != 0 and latest[0].author.id == bot.user.id:
                try:
                    await latest[0].delete()
                except Exception:
                    pass

            try:
                with open("stock_ticker.gif", "rb") as fp:
                    await channel.send(file=discord.File(fp, filename="stock_ticker.gif"))
            except Exception:
                print("Streaming stock ticker GIF failed, using fallback")
                # Fallback to previous behavior if streaming fails
                await channel.send(file=discord.File("stock_ticker.gif"))
    else:
        liblist = []
        for key in libdict:
            # if libdict[key][1]:
            #     liblist.append([key, "▲"+libdict[key][0]])
            # else:
            #     liblist.append([key, "▼"+libdict[key][0]])
            liblist.append([key, libdict[key][0]])
        for ticker_channel in botconfig.config['TICKER_CHANNEL']['value']:
            latest = [msg async for msg in bot.get_channel(ticker_channel).history(limit=1)]
            if len(latest) == 0 or latest[0].author.id != bot.user.id:
                await bot.get_channel(ticker_channel).send(f"```{tabulate(liblist)}```")
            else:
                await latest[0].edit(content = f"```{tabulate(liblist)}```")
                
# Config command
@bot.command(name="config")
@commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
async def config_command(ctx):
    await ctx.reply("Current configuration:\n" + botconfig.__str__() + 
                    "\nType the name and value (e.g., COOLDOWN 600)")

    def check(m):
        if not (m.author == ctx.author and m.channel == ctx.channel): return False
        parts = m.content.split(' ', 1)
        if len(parts) < 2:
            return False
        name, raw_value = parts[0], parts[1]
        if name not in botconfig.config:
            return False
        return True

    try:
        msg = await bot.wait_for('message', check=check, timeout=300)
        parts = msg.content.split(' ', 1)
        
        name, raw_value = parts[0], parts[1]
        
        # Safe Parsing Logic
        if "LIST" in name:
            value = raw_value.split(' ')
        else:
            value = safe_parse_config(raw_value)

        botconfig.update_config(name, value)
        await ctx.reply(f"Config updated:\n{botconfig.__str__()}")

    except asyncio.TimeoutError:
        await ctx.reply("Config session timed out.")
            
# Kill command
@bot.command(name="kill")
async def kill_command(ctx):
    if ctx.author.id == joe:
        await ctx.reply("Powering down.")
        sys.exit()  
    

# Get DSS Voting data (Thanks Beef!)
@bot.command(name='dss_vote')
@commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
async def dss_voting_command(ctx):
    api = await api_data()
    if api is None:
        return await send_error_msg(ctx)
    try:
        dss_dll = convert_time(api.get('spaceStations')[0]['currentElectionEndWarTime'], api)
        dss_txt = await format_dss_votes()
        await ctx.reply(f"DSS moves: <t:{dss_dll}:R>\n"+dss_txt)
    except:
        await ctx.reply("DSS data offline.")

# Get Planet stats (Thanks Beef!)
@bot.command(name="get")
@commands.dynamic_cooldown(custom_cooldown, commands.BucketType.user)
async def get_command(ctx, *, name: str):
    data = await api_data()
    planet = await planet_data()
    warinfo = await warinfo_data()
    if None in [data, planet, warinfo]:
        return await send_error_msg(ctx)
    stats = get_stats_by_name(data, planet, warinfo, name)
    if stats is None:
        return await ctx.reply("Unable to find planet.")
    static, names, name = stats
    id = static['id']
    
    has_region = static['has regions']
    if not is_authorized(ctx):
        for key in ['id', 'environmentals', 'dist', 'has regions']:
            try:
                static.pop(key)
            except:
                continue

    static_txt = []
    for key in static:
        if not (key == 'progress' or key == 'eta'):
            static_txt.append([key,str(static[key])])
    effects = get_effects_by_idx(data, id)[0]
    
    
    
    eta = static['eta']
    progress = static['progress']
    current = time.time()
    campaign = static['campaign']
    defense = campaign == 'Defense'
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
    elif float(eta) < 0:
        etamsg = f"**Full Withdrawal <t:{int(current - eta * 3600)}:R>**"
    if has_region:
        etamsg += "\n-# Regions detected, liberation calculator w/ Regions WIP"
    
    msg = f"## Planet Summary: {name.upper()}\n"
    
    if is_authorized(ctx):
        msg += f"### {names}\n\n"
    
    msg += f"### {campaign.upper()}\n"
    if not defense:
        msg += "-"*20 + '\n'
        msg += f"**{progress}% LIBERATED**\n{etamsg}\n"
    else:
        level = static['level']
        duration = static['duration']
        msg += f"LEVEL **{level}** | **{duration}** HOURS\n"
        msg += "-"*20 + '\n'
        diff_idx = level / duration
        if diff_idx <= 0.7:
            rating = "Easy"
        elif diff_idx < 1:
            rating = "Routine"
        elif diff_idx < 1.3:
            rating = "Hard"
        else:
            rating = "IMPOSSIBLE"
        msg += f"Difficulty rating: __{rating}__\n"
        msg += f"**{progress}% DEFENDED**\n{etamsg}\n"
        
    msg += "-"*20 + '\n'
    msg += "### Planet stats:\n"
    msg += f"```{tabulate(static_txt, colalign=('left',))}```\n"
    if not is_authorized(ctx):
        
        return await ctx.reply(msg)
    
    
    score = horse_predict(static, effects)
    msg += "### Planet Effects:\n - "
    if effects == []:
        msg += "No current effects detected.\n"
    else:
        msg += '\n - '.join(effects) + '\n'
    if score is not None:
        msg += f"### Holistic Overall Reallocation Sequence Evaluator (H.O.R.S.E.) score:\n{round(score * 100, 1)}"
    else:
        msg += "-# Planet unreachable or already liberated, H.O.R.S.E. not available"
            

    return await ctx.reply(msg)
    
    
@get_command.error
async def get_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.reply(f"\n-# Command on cooldown, try again after {error.retry_after:.2f}s.")
    else:
        print(error)

# Get Region stats from planet 
@bot.command(name='get_region')
@commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
async def getregion_command(ctx, *, name: str):
    data = await api_data()
    planet = await planet_data()
    warinfo = await warinfo_data()
    if None in [data, planet, warinfo]:
        return await send_error_msg(ctx)
    try:
        regions, name = get_regions_by_name(data, warinfo, planet, name)
    except:
        return await ctx.reply("Unable to find planet.")
    if regions == []:
        return await ctx.reply("No currently active regions on this planet.")
    result = format_region_data(regions, name)
    return await ctx.reply(result)    
    
# Get Top Ten planet stats
@bot.command(name="get_top")
@commands.dynamic_cooldown(custom_cooldown, commands.BucketType.user)
async def gettop_command(ctx):
    api = await api_data()
    planets = await planet_data()
    warinfo = await warinfo_data()
    if None in [api, planets, warinfo]:
        return await send_error_msg(ctx)
    campaigns = api.get('campaigns')
    leaderboard = []
    for campaign in campaigns:
        idx = campaign['planetIndex']
        stats, _, name = get_stats_by_name(api, planets, warinfo, idx)
        effects = get_effects_by_idx(api, idx)
        score = round(horse_predict(stats, effects) * 100, 1)
        leaderboard.append([name.upper(), stats['progress'], stats['pop%'], score])
    leaderboard = sorted(leaderboard, key = lambda x: x[2], reverse=True)
    leaderboard.insert(0,['Planet', 'Progress', 'pop%', 'H.O.R.S.E.'])
    if is_authorized(ctx):
        await ctx.reply(f"## Top Ten Deployed Planets: \n```{tabulate(leaderboard[:11])}```")
    else:
        await ctx.reply(f"## Top Three Deployed Planets: \n```{tabulate(leaderboard[:4])}```")

@gettop_command.error
async def gettop_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.reply(f"\n-# Command on cooldown, try again after {error.retry_after:.2f}s.")

# Set ACECON
@bot.command(name='set_acecon')
@commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
async def acecon_command(ctx, ACECON: str):
    with open('ACECON.txt','w') as f:
        f.write(ACECON)
    await ctx.reply(f"ACECON set to: {int(ACECON)}")

# Set Advisory Summary
@bot.command(name='set_advisory')
@commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
async def advisory_comand(ctx):
    await ctx.reply("Your next message will be set as the current Advisory Summary.\n-# Send !cancel to cancel.")
    def is_valid_advisory(m):
        return m.author == ctx.author
    try:
        advisory = await bot.wait_for('message',check=is_valid_advisory, timeout = 300)
        ADVISORY = advisory.content
    except asyncio.TimeoutError:
        return await ctx.reply("Timed out, advisory has not been updated.",mention_author=False)
    
    if ADVISORY == '!cancel':
        await ctx.reply("Action cancelled, advisory has not been updated.",mention_author=False)
    else:
        line_cnt = ADVISORY.count('\n')
        
        if line_cnt > botconfig.config['MAX_LINE']['value']:
            await ctx.reply("Too many lines detected. Please be succinct with Advisory Summaries.\nAdvisory has not been updated.",mention_author=False)
        
        await ctx.reply(f"New Advisory:\n {ADVISORY}\nConfirm reset advisory?\n-# Send y or n")
        def is_valid_confirm(m):
            return m.content.lower() in ['y','n'] and m.author == ctx.author
        try:
            confirm = await bot.wait_for('message', check=is_valid_confirm, timeout = 120)
            confirm = confirm.content.lower()
        except asyncio.TimeoutError:
            return await ctx.reply("Timed out, advisory has not been updated.",mention_author=False)
    if confirm == 'y':
        with open ("ADVISORY.txt",'w') as f:
            f.write(ADVISORY)
        await ctx.reply("Advisory has been set.",mention_author=False)
    else:
        await ctx.reply("Action cancelled, advisory has not been updated.",mention_author=False)

# Set Orders
@bot.command(name='set_orders')
@commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
async def set_orders(ctx):
    await ctx.reply("Your next message will be set as the current Orders Summary.\n-# Send \'cancel\' to cancel.")
    def is_valid_order(m):
        return m.author == ctx.author
    try:
        order = await bot.wait_for('message',check=is_valid_order, timeout = 300)
        ORDER = order.content
    except asyncio.TimeoutError:
        await ctx.reply("Timed out, order has not been updated.",mention_author=False)
    
    if ORDER == 'cancel':
        await ctx.reply("Action cancelled, order has not been updated.",mention_author=False)
    else:
        await ctx.reply(f"New Order:\n {ORDER}\nConfirm reset order?\n-# Send y or n")
        def is_valid_confirm(m):
            return m.content.lower() in ['y','n'] and m.author == ctx.author
        try:
            confirm = await bot.wait_for('message', check=is_valid_confirm, timeout = 120)
            confirm = confirm.content.lower()
        except asyncio.TimeoutError:
            return await ctx.reply("Timed out, order has not been updated.",mention_author=False)
        
    if confirm == 'y':
        latest = [msg async for msg in bot.get_channel(botconfig.config['GWR_CHANNEL']['value']).history(limit=1)][0]

        if latest.author.id != bot.user.id:
            await bot.get_channel(botconfig.config['GWR_CHANNEL']['value']).send(ORDER)
        else:
            await latest.edit(content = ORDER)
        await ctx.reply("Order has been set.",mention_author=False)
    else:
        await ctx.reply("Action cancelled, order has not been updated.",mention_author=False)

# Standard Reactions
@bot.event
async def on_message(message):
    if message.channel == bot.get_channel(botconfig.config['GWR_CHANNEL']['value']) and botconfig.config['REACT_TOGGLE']['value']:
        dms = await message.author.create_dm()
        await dms.send("New Orders detected. Initiate Standard Reaction Protocol? y/n")
        def is_valid_confirm(m):
            return m.content.lower() in ['y','n'] and m.author == message.author and m.channel == dms
        try:
            confirm = await bot.wait_for('message', check=is_valid_confirm, timeout = 600)
            confirm = confirm.content.lower()
        except asyncio.TimeoutError:
             return await dms.send("Timed out, no reactions are sent.")
        if confirm == 'y':
            for emoji in botconfig.config['EMOJI_LIST']['value']:
                await message.add_reaction(emoji)
            await dms.send("Standard Reactions added.")
        else:
            await dms.send("Action cancelled, Standard Reactions have not been added")
    await bot.process_commands(message)
    
    

# Sitrep
@bot.command(name="sitrep")
@commands.dynamic_cooldown(custom_cooldown, commands.BucketType.user)
async def sitrep(ctx):
    with open('ACECON.txt','r') as f:
        ACECON = int(f.read())
    with open('ADVISORY.txt','r') as f:
        ADVISORY = f.read()
        
    api = await api_data()
    if api is None:
        return await send_error_msg(ctx)
    
    # Cyberstan Offensive Special
    if api.get("globalResources"):
        health_bar = api.get("globalResources")[0]
        reinforcements_left = health_bar['currentValue'] / 2000000
        drain_rate = health_bar["changePerSecond"] * -3600 / 2000000
        eta = reinforcements_left / drain_rate * 3600
        failure_ddl = int(time.time() + eta)
        formatted_health = f"\n## ///FORCES IN RESERVE///\n**{reinforcements_left:.4f}%** | Draining at: **{drain_rate:.4f}%/h**\nProjected Operation Failure: <t:{failure_ddl}:R>"
    else:
        formatted_health = ''
        
    return await ctx.reply(acecon_format(ACECON) + formatted_health + f"\n## __Advisory Summary__\n{ADVISORY}")

@sitrep.error
async def sitrep_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.reply(f"Look up.\n-# Command on cooldown, try again after {error.retry_after:.2f}s.")

# Get DDLs
@bot.command(name='ddl')
@commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
async def ddl(ctx):
    api = await api_data()
    mo_data = await MO_data()
    if None in [api, mo_data]:
        return await send_error_msg(ctx)
    
    try:
        dss_dll = convert_time(api.get('spaceStations')[0]['currentElectionEndWarTime'], api)
        
        mo_ddl = int(time.time()) + mo_data[0]['expiresIn']
        await ctx.reply(f"Current MO ends: <t:{mo_ddl}:R>\n```<t:{mo_ddl}:R>```\nDSS moves: <t:{dss_dll}:R>\n```<t:{dss_dll}:R>```")
    except:
        await ctx.reply("DSS data offline.")
# Send messages in selected channel
@bot.command(name='send')
@commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
async def send_msg(ctx):
    await ctx.reply("Paste the channel (starting with #) you want the message to send to.")
    def is_valid_channel(m):
        msg = m.content
        is_channel_tag = msg.startswith("<#") and msg.endswith(">")
        is_channel_link = msg.startswith("https://discord.com/channels/")
        return (is_channel_tag or is_channel_link) and m.author == ctx.author 
    try:
        channel_id = await bot.wait_for('message', check = is_valid_channel, timeout = 120)
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
        if not leader in ctx.author.roles:
            return await ctx.reply("You're not authorized to send messages in that channel.")
    try:
        channel = await bot.fetch_channel(channel_id)
        if not channel:
            return await ctx.reply("Invalid channel name. Please retry.")
    except discord.errors.Forbidden:
        return await ctx.reply("Access forbidden.")
    
    await ctx.reply("Your next message will be sent to that channel.\n-# type \'cancel\' to cancel")
    def is_valid_msg(m):
        return m.author == ctx.author
    try:
        msg = await bot.wait_for('message', check = is_valid_msg, timeout = 120)
        msg = msg.content
    except asyncio.TimeoutError:
        return await ctx.reply("Timed out.", mention_author=False)
    if msg == 'cancel':
        return await ctx.reply("Cancelled.")
    else:
        await ctx.reply("Confirm send message?\n-# Send y or n")
        def is_valid_confirm(m):
            return m.content.lower() in ['y','n'] and m.author == ctx.author
        try:
            confirm = await bot.wait_for('message', check=is_valid_confirm, timeout = 120)
            confirm = confirm.content.lower()
        except asyncio.TimeoutError:
            return await ctx.reply("Timed out.", mention_author=False)
    if confirm == 'y':
        await channel.send(f"```{msg}```")
        return await ctx.reply("Message sent.")
        
    else:
        await ctx.reply("Action cancelled.", mention_author=False)


#--------------- EVENT COMMANDS ----------------
@bot.command(name='event_start')
@commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
async def event_start(ctx):
    init_json = {}
    with open('event.json','w') as f:
        json.dump(init_json, f)
    return await ctx.reply("Event initiated.")
    
@bot.command(name='event_end')
@commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
async def event_end(ctx):
    archive = f"archived_event_{datetime.datetime.now()}.json"
    os.rename("event.json", archive)
    return await ctx.reply("Event ended.")
        
        
@bot.command(name='submit')
async def submit_stats(ctx, idx:str):
    if idx not in ['1', '2', '3', '4']:
        return await ctx.reply("```Incorrect format. Please indicate which are your stats (counting from the left) in the screenshot, e.g. $submit 2```")
    idx = int(idx) - 1
    if not os.path.isfile('event.json'):
        return await ctx.reply("```No ongoing event.```")
    usr = str(ctx.author.id)
    if not ctx.message.attachments:
        return await ctx.reply("```No image attachment detected, please retry.```")
    if len(ctx.message.attachments) > 1:
        return await ctx.reply("```More than one attachment detected, please retry.```")
    
    if not os.path.isdir('imgcache'):
        os.mkdir('imgcache')
        
    img = ctx.message.attachments[0]
    content_type = img.content_type
    if not content_type.startswith('image'): 
        return await ctx.reply("```No image attachment detected, please retry.```")
    suffix = content_type.split('/')[1]
    filename = os.path.join('imgcache', f"{usr}.{suffix}")
    await img.save(fp=filename)
    stats = img_to_stats(filename)
    summary = summary_from_stats(stats)
    player = ctx.author.display_name
    player_stats = {}
    for stat in stats:
        player_stats[stat] = stats[stat][idx]
    with open('event.json', 'r') as f:
        LOGS = json.load(f)
    if player not in LOGS:
        LOGS[player] = {}
        for stat in player_stats:
            LOGS[player][stat] = [player_stats[stat]]
    else:
        for stat in LOGS[player]:
            LOGS[player][stat].append(player_stats[stat])
    # melee kills 
    # score = player_stats['MELEE KILLS']
    
    # kills - deaths
    score = player_stats['KILLS'] * (1 - 0.1 * player_stats['DEATHS'])
    if score < 0:
        score = 0
    with open('event.json','w') as f:
        json.dump(LOGS, f)
    return await ctx.reply(f"```{summary}```\nYour stats have been logged for analysis.\n\n**Your score is:** ```{score}```")
    
    

intents.message_content = True
intents.guilds = True

if __name__ == '__main__':
    bot.run(TOKEN)

