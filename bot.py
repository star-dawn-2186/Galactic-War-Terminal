from dotenv import load_dotenv
import discord
import traceback
import pickle
import asyncio
from discord.ext import commands, tasks
import time
import random
import gc
import os
import sys
import functools
from concurrent.futures import ProcessPoolExecutor
import ast
import datetime
import json
import math
from tabulate import tabulate
from utils import *
from find_planets import * 
from render_mo4 import *
from parse_assignment import parse_mo, update_mo_tracker
from horse import horse_predict
from gambit_calculator import calc_gambit
from ticker import create_stock_ticker_gif
from libcalc import get_librate_from_idx, update_librate
from effcalc import calc_region_eff_from_name, diff_to_dmg
from ocr import img_to_stats, summary_from_stats
from icon_detect import detect_helldiver_icon

process_executor = ProcessPoolExecutor(max_workers=1)
load_dotenv()

TOKEN = os.getenv("TOKEN") #not gonna show my token to ya :)
acecon_msg_link = 'https://discord.com/channels/1261556132640456764/1427786162272997526/1430116186967904427'
advisory_link = 'https://discord.com/channels/1261556132640456764/1427786162272997526'
LEADER_ROLE_ID = 1372466615798726707
HQ_CHANNEL = 1369361948336062685
LOUNGE_CHANNEL = 1427787543394385930
LAB_CHANNEL = 1439653037554798612
ADVISORY_CHANNEL = 1427786162272997526
HANGOUT_CHANNEL = 1386338755882913906 
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
    alert_loop.start()
    ticker_loop.start()
    
    mo_archive_loop.start()
    reminder_loop.start()
    leaderboard_loop.start()
    mo_loop.start()

# Notification when a new MO thread is created
@bot.event
async def on_thread_create(thread):
    if thread.parent.id == HQ_CHANNEL:
        channel = bot.get_channel(NEWS_CHANNEL)
        thread_link = f"https://discord.com/channels/{thread.guild.id}/{thread.id}"
        confirm_msg = f"New thread: {thread_link}\nSend New MO thread notification?\n-# Send y or n"
        await bot.get_channel(LOUNGE_CHANNEL).send(confirm_msg)
        def is_valid_confirm(m):
            return m.content.lower() in ['y','n'] and is_authorized(m)
        try:
            confirm = await bot.wait_for('message', check=is_valid_confirm, timeout = 600)
        except asyncio.TimeoutError:
            return await bot.get_channel(LOUNGE_CHANNEL).send("Timed out, notif not sent.")
        if confirm.content.lower() == 'y':
            return await channel.send(f"```New Major Order detected. Opening discussion thread.```\n{thread_link}")
        else:
            return await bot.get_channel(LOUNGE_CHANNEL).send("Notif not sent.")

@tasks.loop(minutes=10)
async def mo_loop():
    update_mo_tracker()

@tasks.loop(minutes = 30)
async def mo_archive_loop():
    if not os.path.isfile('mo_tracker.json'):
        return
    with open('mo_tracker.json', 'r') as f:
        data = f.read()
    with open('mo_archive.txt', 'a') as f:
        f.write(f"{datetime.date.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')} {data}\n")

@tasks.loop(minutes = 1)
async def alert_loop():
    api = await api_data()
    planets = await planet_data()
    warinfo = await warinfo_data()
    new_regions = await update_librate(mode='r')
    if None in [api, planets, warinfo]:
        return
    defenses = api.get('planetEvents')
    decays = {}
    subfactions = {}
    for idx in range(len(api.get('planetStatus'))):
        subfactions[str(idx)] = []
        
        effects, _ = get_effects_by_idx(api, idx)
        try:
            stats, _, _ = get_stats_by_name(api, planets, warinfo, idx)
            if 'decay' in stats:
                decays[idx] = stats['decay']
            
            for effect in effects:
                for sub in ['CORPS', 'JET', 'STRAIN', 'CYBORG', 'Appropriator', 'Mindless Mass', 'DRAGONROACH', 'HIVE LORD']: 
                    if sub.lower() in effect.lower() and effect.lower() != "jet brigade factories":
                        subfactions[str(idx)].append(effect)
        except:
            pass
        
    init = False
    if not os.path.isfile("defenses.txt"):
        with open("defenses.txt", 'w') as f:
            f.writelines([str(defense['planetIndex']) + '\n' for defense in defenses])
        init = True
    if not os.path.isfile("subfactions.json"):
        with open("subfactions.json",'w') as f:
            json.dump(subfactions, f)
        init = True
    if not os.path.isfile("decays.json"):
        with open("decays.json",'w') as f:
            json.dump(decays, f)
        init = True
    
    if init: return
    
    
    with open("defenses.txt", 'r') as f:
        prev_defenses = f.read().split('\n')

    for defense in defenses:
        if str(defense['planetIndex']) not in prev_defenses: # New defense
            
            idx, name = name_to_idx(defense['planetIndex'])
            stats, _, _ = get_stats_by_name(api, planets, warinfo, name)
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
                
            await bot.get_channel(HANGOUT_CHANNEL).send(f"```{msg}```")
    with open("defenses.txt",'w') as f:
        f.writelines([str(i['planetIndex']) + '\n' for i in defenses])
    
    with open("subfactions.json", 'r') as f:
        prev_subfactions = json.load(f)
        
    msg = "!!=== PRIORITY ALERT: ENEMY MOVEMENT ===!!\n"
    for idx in subfactions:
        _, name = name_to_idx(int(idx))
        stats, _, _ = get_stats_by_name(api, planets, warinfo, idx)
        if stats['campaign'] != "Already liberated":
            for sub in subfactions[idx]:
                try:
                    if sub not in prev_subfactions[idx]: # new subfaction
                        msg += f"{sub.upper()} detected on: {name.upper()}\n"
                except KeyError:
                    continue
            for sub in prev_subfactions[idx]:
                if sub not in subfactions[idx]: # removed subfaction
                    msg += f"{sub.upper()} no longer detected on: {name.upper()}\n"
    
    if msg.count('\n') > 1:
        await bot.get_channel(HANGOUT_CHANNEL).send(f"```{msg}```")
    with open("subfactions.json", 'w') as f:
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
        await bot.get_channel(HANGOUT_CHANNEL).send(f"```{msg}```")
    
    with open("decays.json", 'r') as f:
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
            # at this point, i have realized that me calling those functions that return way more data
            # than is needed is extremely inefficient and will probably give all my past coding teachers an aneurysm
            # however, i dare not fix what aint broken, for it is, and pun fully intended, the code we live by
            if change != '':
                msg += f"Decay on {name.upper()} has {change} to {decays[idx]}%\n"

    if msg.count('\n') > 1:
        await bot.get_channel(HANGOUT_CHANNEL).send(f"```{msg}```")
    with open("decays.json", 'w') as f:
        json.dump(decays, f)
            
# Reminder to close threads when MO ends
@tasks.loop(minutes = 30)
async def reminder_loop():
    with open("reminder_set.pkl",'rb') as f:
        reminder_set = pickle.load(f)
    mo_data = MO_data()
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
            _ = await update_librate(mode='p')
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
        
        thing_to_run = functools.partial(create_stock_ticker_gif, libdict, "/var/www/GWT/gwt-ticker/stock_ticker.gif")
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
            if len(latest) != 0 and latest[0].author.id == bot.user.id and not latest[0].content:
                try:
                    with open("/var/www/GWT/gwt-ticker/stock_ticker.gif", "rb") as fp:
                        file = discord.File(fp, filename="/var/www/GWT/gwt-ticker/stock_ticker.gif")
                        await latest[0].edit(attachments=[file])
                except Exception:
                    pass
                
            else:
                try:
                    with open("/var/www/GWT/gwt-ticker/stock_ticker.gif", "rb") as fp:
                        await channel.send(file=discord.File(fp, filename="/var/www/GWT/gwt-ticker/stock_ticker.gif"), silent=True)
                except Exception:
                    print("Streaming stock ticker GIF failed, using fallback")
                    # Fallback to previous behavior if streaming fails
                    await channel.send(file=discord.File("/var/www/GWT/gwt-ticker/stock_ticker.gif"),silent=True)
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
    if ctx.author.id == joe: # because some idiot's gonna try and kill the GWT at some point
        await ctx.reply("Powering down.")
        sys.exit()  
    

# ====================
# Info Commands
# ====================

# Get DSS Voting data (Thanks Beef!)
@bot.command(name='dss_vote')
@commands.dynamic_cooldown(custom_cooldown, commands.BucketType.user)
async def dss_voting_command(ctx):
    api = await api_data()
    if api is None:
        return await send_error_msg(ctx)
    secret = ctx.channel.id in [LOUNGE_CHANNEL, LAB_CHANNEL]
    try:
        dss_dll = convert_time(api.get('spaceStations')[0]['currentElectionEndWarTime'], api)
        dss_txt = format_dss_votes(secret)
        ddl_txt = f"DSS moves: <t:{dss_dll}:R>\n"
        await ctx.reply(ddl_txt+dss_txt)
    except Exception as e:
        print(e)
        await ctx.reply("DSS data offline.")
    
@dss_voting_command.error
async def dss_voting_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.reply(f"Look up.\n-# Command on cooldown, try again after {error.retry_after:.2f}s.")
    else:
        print(error)
    
@bot.command(name='progress')
@commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
async def progress_command(ctx):
    mo_data = MO_data()
    orders = parse_mo(mo_data)
    if os.path.isfile('mo_tracker.json'):
        with open('mo_tracker.json', 'r') as f:
            deltas = json.load(f)
    for order in orders:
        if os.path.isfile('mo_tracker.json'):
            for task in order['tasks']:
                delta = deltas[orders.index(order)][order['tasks'].index(task)]['delta']
                goal = task['goal']
                task['rate'] = round(delta / goal * 600, 2)
        await ctx.reply(format_mo_progress(order))

# Get Planet stats (Thanks Beef!)
@bot.command(name="get", help="Fetches real-time info about a planet.")
@commands.dynamic_cooldown(custom_cooldown, commands.BucketType.user)
async def get_command(ctx, *, name: str = commands.parameter(description="- Name (case insensitive) or ID of the desired planet.")):
    data = await api_data()
    planet = await planet_data()
    warinfo = await warinfo_data()
    if None in [data, planet, warinfo]:
        return await send_error_msg(ctx)
    stats = get_stats_by_name(data, planet, warinfo, name)
    if stats is None:
        return await ctx.reply("Unable to find planet.")
    static, names, name = stats
    idx = static['id']
    
    has_region = static['has regions']
    environmentals = static['environmentals']
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
    effects = get_effects_by_idx(data, idx)[0]
      
    
    eta = static['eta']
    progress = static['progress']
    current = time.time()
    campaign = static['campaign']
    flag = 'level' in static
    usealg = eta is None
    if usealg:
        required = static['required']
        _, _, weighted_eff = calc_region_eff_from_name(data, warinfo, planet, name)
        if weighted_eff * static['pop%'] == 0:
            eta = "**STALEMATE**"
        else:
            eta = required / (weighted_eff * static['pop%'])
 
    
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
        msg += "-"*20 + '\n'
        msg += f"**{progress}% LIBERATED**\n{etamsg}\n"
    else:
        
        msg += "-"*20 + '\n'
        level = static['level']
        duration = static['duration']
        msg += f"LEVEL **{level}** | **{duration}** HOURS\n"
        rating = get_defense_rating(level, duration)
        msg += f"Difficulty rating: __{rating}__\n"
        if campaign.upper() == 'LIBERATION':
            msg += f"**{progress}% LIBERATED**\n{etamsg}\n"
        else:
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
        traceback.print_exc()

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
@bot.command(name="get_top", help="Fetches info about the planets with the most amount of divers deployed.")
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
        leaderboard.append([name.upper(), stats['progress'], stats['pop%']])
    leaderboard = sorted(leaderboard, key = lambda x: x[2], reverse=True)
    leaderboard.insert(0,['Planet', 'Progress', 'pop%'])
    if is_authorized(ctx):
        await ctx.reply(f"## Top Ten Deployed Planets: \n```{tabulate(leaderboard[:11])}```")
    else:
        await ctx.reply(f"## Top Three Deployed Planets: \n```{tabulate(leaderboard[:4])}```")

@gettop_command.error
async def gettop_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.reply(f"\n-# Command on cooldown, try again after {error.retry_after:.2f}s.")

# ====================
# Calculation Commands
# ====================

# Eff calcs
@bot.command(name='effcalc')
@commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
async def effcalc_command(ctx, *, name: str):
    api = await api_data()
    planets = await planet_data()
    warinfo = await warinfo_data()
    if None in [api, planets, warinfo]:
        return await send_error_msg(ctx)

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

# Gambit calcs
@bot.command(name="gambit", help="Calculates feasibility of a gambit.")
@commands.dynamic_cooldown(custom_cooldown, commands.BucketType.user)
async def gambitcalc(ctx, *, name: str):
    api = await api_data()
    planets = await planet_data()
    warinfo = await warinfo_data()
    print('gambit')
    if None in [api, planets, warinfo]:
        print('error')
        return await send_error_msg(ctx)
     
    response = calc_gambit(name, api, planets, warinfo)
    msg = format_gambitcalc(response)
    if msg is None:
        msg = "This is not a defense."
    return await ctx.reply(msg)

@gambitcalc.error
async def gambitcalc_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.reply(f"\n-# Command on cooldown, try again after {error.retry_after:.2f}s.")


@bot.command(name="dmg", help="Fetches a list of damage dealt per difficulty with the current IM.")
@commands.dynamic_cooldown(custom_cooldown, commands.BucketType.user)
async def dmgcalc(ctx):
    im = await fetch_im()
    if im is None: return await send_error_msg(ctx)
    results = []
    for diff in diff_to_dmg:
        name = diff[0]
        avg_mission_dmg = round(sum([math.floor(im * dmg) for dmg in diff[1:]]) / (len(diff)-1), 2)
        non_ocb_dmg = math.floor(im * diff[1]) if len(diff) > 2 else 'N/A'
        ocb_dmg = math.floor(im * diff[-1])
        results.append([name, avg_mission_dmg, non_ocb_dmg, ocb_dmg])
    table = tabulate(results, headers=["", "Avg", "Non-OCB", "OCB"], stralign="left")
    msg = f"### Current Impact Modifier: {im}\n```{table}```"
    return await ctx.reply(msg)
@dmgcalc.error
async def dmgcalc_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.reply(f"\n-# Command on cooldown, try again after {error.retry_after:.2f}s.")

# ====================
# Administrative Commands
# ====================

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
        with open("ACECON.txt",'r') as f:
            ACECON = int(f.read())
        await bot.get_channel(ADVISORY_CHANNEL).send(acecon_format(ACECON) + f"\n## __Advisory Summary__\n{ADVISORY}")
        await ctx.reply("Advisory has been set.",mention_author=False)
    else:
        await ctx.reply("Action cancelled, advisory has not been updated.",mention_author=False)

# Sitrep
@bot.command(name="sitrep", help="Fetches a short summary of the current orders and situation.")
@commands.dynamic_cooldown(custom_cooldown, commands.BucketType.user)
async def sitrep(ctx):
    with open('ACECON.txt','r') as f:
        ACECON = int(f.read())
    with open('ADVISORY.txt','r') as f:
        ADVISORY = f.read()
        
    api = await api_data()
    if api is None:
        return await send_error_msg(ctx)
        
    return await ctx.reply(acecon_format(ACECON) + f"\n## __Advisory Summary__\n{ADVISORY}")

@sitrep.error
async def sitrep_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.reply(f"Look up.\n-# Command on cooldown, try again after {error.retry_after:.2f}s.")

# Get DDLs
@bot.command(name='ddl')
@commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
async def ddl(ctx):
    api = await api_data()
    mo_data = MO_data()
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

# ====================
# MO4 Commands
# ====================

def gen_mo4_progress():
    mo4_ddl = 1783595320
    start = 1783395151
    multiplier = 1.33 if time.time() <= start + 24*3600 else 1
    # if not os.path.isfile('event.json') and not os.path.isfile('event_to.json'): return
    
    if os.path.isfile('event.json'):
        with open('event.json','r') as f:
            LOGS = json.load(f)
        if len(LOGS) != 0:
            subgoal_count = []
            for player in LOGS:
                if 'SHOTS FIRED' in LOGS[player]: 
                    shots = LOGS[player]['SHOTS FIRED']
                    total_subgoal = sum([int(i * multiplier) for i in shots if i != 'N/A'])
                    avg_subgoal = total_subgoal / len(shots)
                    subgoal_count.append((player, total_subgoal, round(avg_subgoal, 2)))

            subgoal_count = sorted(subgoal_count, key=lambda x: x[1], reverse=True)
            table = tabulate(subgoal_count[:5], headers=["Name", "Shots Fired", "Average"])
            if os.path.isfile('shots.txt'):
                with open('shots.txt', 'r') as f:
                    total_kills = int(f.read())
            else: return
        else:
            total_kills = 0
            
    if os.path.isfile('event_to.json'):
        with open('event_to.json','r') as f:
            TO_LOGS = json.load(f)
        airbase_count = 0
        gunships = 0
        if len(TO_LOGS) != 0:
            for player in TO_LOGS:
                if 'Sabotage_Air_Base' in TO_LOGS[player]:
                    airbase_count += int(TO_LOGS[player]['Sabotage_Air_Base']) * multiplier
                if 'Gunship_Facility'in TO_LOGS[player]:
                    gunships += int(TO_LOGS[player]['Gunship_Facility']) * multiplier
    elif not os.path.isfile('event.json'):
        return
    
    score1 = int(gunships + airbase_count * 4)
    goal1 = 300
    score2 = int(total_kills)
    goal2 = 350000
    state = 'Ongoing'
    if score1 >= goal1 * 1.75 and score2 >= goal2 * 1.2:
        state = 'Overwhelming Success'
    elif score1 >= goal1 and score2 >= goal2 and time.time() >= mo4_ddl:
        state = 'Success'
    elif (score1 >= goal1 * 0.8 or score2 >= goal2 * 0.8) and time.time() >= mo4_ddl:
        state = 'Partial Failure'
    elif time.time() >= mo4_ddl:
        state = 'Failure'

    msg = f"## MO4: {state}\nEnds: <t:{mo4_ddl}:R>\n- Automaton fleet assets destroyed: **{score1}**/{goal1}\n-# Air Bases destroyed: {airbase_count}\n-# Gunship Facilities destroyed: {gunships}\n- Shots Fired: **{total_kills}**/{goal2} \n\n```{table}```"
    
    if state != 'Ongoing':
        os.rename('event.json',f'm04_10_{state.lower()}.json')
        os.rename('event_to.json', f'mo4_10_to.json')
    
    return msg, subgoal_count

# Periodically announce MO4 progress
@tasks.loop(hours=3)
async def leaderboard_loop():
    
    msg, _ = gen_mo4_progress()
    try:
        channel = bot.get_channel(1521738410216263752)
        latest = [msg async for msg in channel.history(limit=1)]
    except AttributeError:
        print("Channel history cannot be accessed")
        return
    if len(latest) != 0 and latest[0].author.id == bot.user.id and "MO4: " in latest[0].content:
        try:
            await latest[0].delete()
        except Exception:
            pass
    await channel.send(msg)

# Manual MO4 progress check
@bot.command(name='mo4')
@commands.dynamic_cooldown(custom_cooldown, commands.BucketType.user)
async def mo4_progress_command(ctx):
    msg, subgoal_count = gen_mo4_progress()
    player = ctx.author.display_name
    names = [i[0] for i in subgoal_count]
    if player in names:
        rank = names.index(player) 
    else:
        rank = -1
    if rank != -1:
        stats = [[rank+1, subgoal_count[rank][1],subgoal_count[rank][2]]]
        stats_table = tabulate(stats, headers=["Rank", "Shots fired", "Average"])
        txt = f"\n**Your stats:**\n ```{stats_table}```"
    else: 
        txt = "\n-# You haven't submitted a mission yet."
    msg += txt
    await ctx.reply(msg)
    
# Generates official-style MO dispatch
@bot.command(name='dispatch')
@commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
async def gen_dispatch(ctx, title:str, body:str):
    if not ctx.message.attachments:
        content = format_html(title, body)
    else:
        img = ctx.message.attachments[0]
        content_type = img.content_type
        if not content_type.startswith('image'): 
            return await ctx.reply("```No image attachment detected, please retry.```")
        await img.save(fp='render_img/header.png')
        content = format_html(title, body, 'render_img/header.png')
    
    with open('render_img/temp.html','w') as f:
        f.write(content)
    img_stream = await render_html_to_image(content)
    img_file = discord.File(fp=img_stream, filename='render.png')
    await ctx.reply(file=img_file)
    
# Starts a tracker
@bot.command(name='event_start')
@commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
async def event_start(ctx, to:str):
    start_time = time.time()
    with open('start.txt','w') as f:
        f.write(str(int(start_time)))
    init_json = {}
    if to == 'to':
        with open('event_to.json','w') as f:
            json.dump(init_json, f)
        return await ctx.reply("TO Event initiated.")
    with open('event.json','w') as f:
        json.dump(init_json, f)
    return await ctx.reply("Event initiated.")

# Ends both trackers
@bot.command(name='event_end')
@commands.has_any_role("Galactic War Leader", "Galactic War Advisor", "Turbo Nerd")
async def event_end(ctx):
    archive = f"archived_event_{datetime.datetime.now()}.json"
    archive_to = f"archived_event_to_{datetime.datetime.now()}.json"
    if os.path.isfile('event.json'):
        os.rename("event.json", archive)
        await ctx.reply('Event ended.')
    if os.path.isfile('event_to.json'):
        os.rename("event_to.json", archive_to)
        await ctx.reply("TO Event ended.")


# Submitting a mission objective
@bot.command(name='submit_to')
async def submit_to_command(ctx):
    if not os.path.isfile('event_to.json'):
        return await ctx.reply("```No ongoing TO-based MO4.```")
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
    matches, obj_matches = detect_helldiver_icon(filename)
    for icon, value in obj_matches.items():
        if icon in matches:
            matches[icon] += value 
        else:
            matches[icon] = value
    if 'Sabotage_Air_Base_2' in matches:
        matches['Sabotage_Air_Base'] = 1
    player = ctx.author.display_name
    with open('event_to.json', 'r') as f:
        LOGS = json.load(f)
    if player not in LOGS:
        LOGS[player] = matches
    else:
        for to in matches:
            if to not in LOGS[player]:
                LOGS[player][to] = matches[to]
            else:
                LOGS[player][to] += matches[to]
    with open('event_to.json','w') as f:
        json.dump(LOGS, f)
    formatted = '\n'.join([f"{name}:\t{count}"  for name, count in matches.items()])
    return await ctx.reply(f"```{formatted}```\nMission logged.")

# Submitting mission stats
@bot.command(name='submit')
async def submit_stats(ctx, idx:str):
    if idx not in ['1', '2', '3', '4']:
        return await ctx.reply("```Incorrect format. Please indicate which are your stats (counting from the left) in the screenshot, e.g. $submit 2```")
    idx = int(idx) - 1
    if not os.path.isfile('event.json'):
        return await ctx.reply("```No ongoing stats-based MO4.```")
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
    
    
    start = 1783395151
    multiplier = 1.33 if time.time() <= start + 24*3600 else 1
    
    player_stats = {}
    for stat in stats:
        player_stats[stat] = stats[stat][idx]
    
    kills = int(sum([int(i) for i in stats['SHOTS FIRED']]) * multiplier)
    if not os.path.isfile('shots.txt'):
        with open('shots.txt', 'w') as f:
            f.write(str(kills))
    else:
        with open('shots.txt','r') as f:
            prev_kills = int(f.read())
        kills += prev_kills
        with open('shots.txt','w') as f:
            f.write(str(kills))
    
    with open('event.json', 'r') as f:
        LOGS = json.load(f)
    
    if player not in LOGS:
        LOGS[player] = {}
        for stat in player_stats:
            LOGS[player][stat] = [player_stats[stat]]
    else:
        for stat in LOGS[player]:
            if stat not in player_stats:
                LOGS[player][stat].append('N/A')
            else:
                LOGS[player][stat].append(player_stats[stat])
                              
   
    with open('event.json','w') as f:
        json.dump(LOGS, f)
    return await ctx.reply(f"```{summary}```\nYour stats have been logged for analysis.")

intents.message_content = True
intents.guilds = True

if __name__ == '__main__':
    bot.run(TOKEN)
# there once were a couple of users
# with brainrotted senses of humor
# they had an obsession
# with the numbers six-seven
# so i obliged them with this maneuver