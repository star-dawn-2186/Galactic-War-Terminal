from tabulate import tabulate
import time
import json
import aiohttp
import requests
from aiohttp import TCPConnector
from static_data import environmental_info


status_link = "https://api.live.prod.thehelldiversgame.com/api/warseason/801/status"
warinfo_link = "https://api.live.prod.thehelldiversgame.com/api/warseason/801/warinfo"
planet_link = "https://helldiverstrainingmanual.com/api/v1/planets"
campaign_link = "https://helldiverstrainingmanual.com/api/v1/war/campaign"
MO_link = "https://helldiverstrainingmanual.com/api/v1/war/major-orders"
dss_vote_link = 'https://redivivus-nixon-uncomplicated.ngrok-free.dev/election/'

_session = None

async def get_session():
    global _session
    if _session is None or _session.closed:
        connector = TCPConnector(ssl=False)
        _session = aiohttp.ClientSession(connector=connector)

    return _session

async def fetch_json(url):
    session = await get_session()
    try:
        async with session.get(url, timeout=10, allow_redirects=True) as response:
            
            if response.status == 200:
                return await response.json()
            error_text = await response.text()
            print(f"Response Body: {error_text}")
            return None
    except Exception as e:
        print(f"API Error: {e}")
        return None

async def api_data():
    return await fetch_json(status_link)
async def warinfo_data():
    return await fetch_json(warinfo_link)
async def planet_data():
    return await fetch_json(planet_link)
async def campaign_data():
    return await fetch_json(campaign_link)
async def MO_data():
    return await fetch_json(MO_link)
def DSS_voting_data(): # "What a great way to solve this issue, Joe. Well done. :3" - THD
    
    cookies = {
        'abuse_interstitial': 'redivivus-nixon-uncomplicated.ngrok-free.dev',
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:148.0) Gecko/20100101 Firefox/148.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        # 'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Connection': 'keep-alive',
        # 'Cookie': 'abuse_interstitial=redivivus-nixon-uncomplicated.ngrok-free.dev',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'DNT': '1',
        'Sec-GPC': '1',
        'Priority': 'u=0, i',
    }

    response = requests.get('https://redivivus-nixon-uncomplicated.ngrok-free.dev/election/', cookies=cookies, headers=headers)
    return response.json()


def format_planet_data(names, static_txt, effects):
    print(names)
    print(tabulate(static_txt))

    print('-'*20)
    print("Active planet effects: ")
    for effect in effects:
        print(effect)
    print('-'*20)

def format_environmental_data(env_list):
    msg = ''
    for env in env_list:
        if env in environmental_info:
            name, desc = environmental_info[env]["name"], environmental_info[env]["description"]
            msg += f"> {name}\n-# {desc}\n"
    return msg

def format_region_data(regions, name):
    result = f"## Region data for: {name.upper()}\n"
    for region in regions:
        eq_size = region['eq_size']
        decay = region['decay']
        progress = region['progress']
        eta = region['eta']
        current = time.time()
        lib_bomb = region['libbomb']
        pop = region['pop']
        
        region_txt = '### ' + region['name'].upper() + f' - {int(eq_size * 1e3)}K HP\n'
        region_txt += f' - Current relative pop%: **{pop}%**\n'  
        region_txt += f' - Decay: **{decay}%**\n'
        region_txt += f" - Liberation boost: **{int(lib_bomb * 100)}%**\n"
        
        
        if progress == 0:
            if eta == "**Liberty Secured**":
                progress = "100% Liberated"
            elif eta == 'Unavailable':
                progress = "N/A"
        else:
            progress = str(progress) + "% " + "Liberated"
            
        region_txt += f' - Current status: **{progress}**\n'     
        if type(eta) == str:
            etamsg = eta
        elif float(eta) > 0:
            etamsg = f"Full Liberation **<t:{int(current + eta * 3600)}:R>**"
        elif float(eta) < 0:
            etamsg = f"Full Withdrawal **<t:{int(current - eta * 3600)}:R>**"
        region_txt += ' - ' + etamsg + '\n'
        result += region_txt
    return result

def format_dss_votes(secret = False):
    dss_data = DSS_voting_data()
    data = sorted(dss_data['Options'], key = lambda d: d['Percentage'], reverse=True)
    tab = []
    for planet in data:
        if secret:
            tab.append([planet['Name'], str(planet['Votes']), str(planet['Percentage'])+'%'])
        else:
            tab.append([planet['Name'],str(planet['Percentage'])+'%'])
    headers = ['Planet', 'Votes', 'Percentage'] if secret else ['Planet', 'Percentage']
    txt = tabulate(tab, numalign='left', headers=headers)
    total = 'Total Votes: '+str(dss_data['Total Votes'])+'\n' if secret else ''
    return f"{total}```{txt}```"

def convert_time(t, api):
    wartime = api.get('time')
    current = int(time.time())
    deviation = current - wartime 
    return t + deviation

def format_duration(seconds):
    if seconds == 0:
        return "0S"

    units = [
        ('Y', 365 * 24 * 3600),
        ('M', 30 * 24 * 3600),
        ('D', 24 * 3600),
        ('H', 3600),
        ('m', 60),  
        ('s', 1)
    ]

    parts = []
    for unit_name, unit_seconds in units:
        if seconds >= unit_seconds:
            value, seconds = divmod(seconds, unit_seconds)
            parts.append(f"{int(value)}{unit_name}")

    return " ".join(parts)

def format_gambitcalc(result):
    if result is None:
        return None
    if type(result) == str:
        return result
    score = result['score']
    source_name, source_required = result['source']['name'].upper(), result['source']['required']
    target_names = [name.upper() for name in result['targets']['names']]
    target_required = result['targets']['required']
    
    msg = f"### Gambit feasibility rating: {score}\n"
    msg += f"Attacking planet: **{source_name}**\n"
    for name in target_names:
        msg += f"Defending planet: **{name}**\n"
    
    msg += f" - Minimum required HP for Gambit: {source_required}\n"
    
    msg += f" - Minimum required HP for Defense: {target_required}\n"    

    if 'horse' in result['source']:
        source_horse = result['source']['horse']
        target_horse = result['targets']['horse']
        msg += f" - H.O.R.S.E. Comparison: **{source_horse}** (Gambit) vs. **{target_horse}** (Defense)\n"
        
    if result['dss'] == 'source':
        msg += " - DSS Location: at Gambit planet"
    elif result['dss'] == 'target':
        msg += " - DSS Location: at Defense planet"
    
    return msg

async def fetch_im():
    api = await api_data()
    if api is None: return None
    return api.get('impactMultiplier')


class BotConfig():
    def __init__(self):
        try:
            with open("config.json",'r') as f:
                self.config = json.load(f)       
        except:
            print("Config file missing or corrupted, reverting to default")
            self.config = {}
            self.config["MAX_LINE"] =  {"value": 4, "description": "Maximum lines allowed for Advisory Summary messages."}
            self.config["ICON_LIST"] =  {"value": ['▪️/▫️','🔺','🔶','🟨','🟢','💙'], "description": "Icons for ACECON statuses, separate with spaces."}
            self.config["EMOJI_LIST"] =  {"value": ['🔺','🔶','🟨','🟢','💙'], "description": "Allowed emojis for Standard Reactions, separate with spaces."} # testing
            self.config["REACT_TOGGLE"] =  {"value": False, "description": "Toggle for Standard Reactions, off by default."}
            self.config["COOLDOWN"] =  {"value": 300, "description": "Cooldown for $sitrep messages, in seconds."}
            self.config["GWR_CHANNEL"] =  {"value": 1438119785522004039, "description": "Channel ID for the GWR Announcements channel, for sending Orders Summaries."} # mockup
            self.config["TICKER_CHANNEL"] =  {"value": [1444362504510636062], "description": "Channel IDs for stock-ticker-style updates."} # mockup
            self.config["TICKER_TOGGLE"] =  {"value": True, "description": "Toggle for stock-ticker-style updates, on by default."}
            with open("config.json",'w') as f:
                json.dump(self.config, f)
            print("New config file created.")
            
    def update_config(self, name, value):
        self.config[name]['value'] = value
        with open("config.json",'w') as f:
            json.dump(self.config, f, indent=4)
    
    def __str__(self):
        msg = ""
        for cfg in self.config.keys():
            desc = self.config[cfg]["description"]
            value = self.config[cfg]['value']
            msg += f"**{cfg}**\n-# {desc}\nCurrent value: {value}\n"
        return msg
    
