import json
from datetime import datetime
from utils import api_data, warinfo_data
import os
UPDATE_INTERVAL = 600
FILENAME = "prev_health.json"
# logic:
# get current health from status
# get past health from stored
# delta health
# get max health from warinfo
# delta health / max health = health%
# health% / time = lib rate

# omg thank you past joe i had no fucking clue what you wrote

async def update_librate(filename=FILENAME):
    status = await api_data()
    warinfo = await warinfo_data()
    
    if None in [status, warinfo]:
        print("api error")
        return
    status = status.get('planetStatus')
    warinfo = warinfo.get('planetInfos')
    
    if not os.path.isfile(filename):
        await init_savedhealth(filename)
        print("Logs missing or corrupted, rebuilding...")
        return 
    
    with open(filename,'r') as f:
        healthdict = json.load(f)
    for planet in status:
        health = int(planet['health'])
        prev_health = healthdict[str(planet['index'])][0]
        delta_health = prev_health - health
        maxhealth = int(warinfo[planet['index']]['maxHealth'])
        healthp = delta_health / maxhealth * 100
        librate = round(healthp / (UPDATE_INTERVAL / 3600),2)
        healthdict[str(planet['index'])] = [health, librate]
    with open(filename,'w') as f:
        json.dump(healthdict, f, indent=4)
        
    now = datetime.now()
    print(f"{now}: updated librates")

async def init_savedhealth(filename=FILENAME):
    status = await api_data()
    if status is None:
        return
    
    status = status.get('planetStatus')
    healthdict = {}
    for planet in status:
        healthdict[str(planet['index'])] = [planet['health'], 0]
    with open(filename,'w') as f:
        json.dump(healthdict, f, indent=4)

def get_librate_from_idx(idx, filename=FILENAME):
    if not os.path.isfile(filename):
        print("Logs missing or corrupted, rebuilding...")
        return None
    with open(filename,'r') as f:
        healthdict = json.load(f)
    return healthdict[str(idx)][1]

# librate * 1% * total HP / planet pop% / region pop % = eff
# TODO: implement that somehow

# Regionless planets
# Regions are left as an exercise to the reader
async def calc_eff_from_idx(idx, filename=FILENAME):
    if not os.path.isfile(filename):
        print("Logs missing or corrupted, rebuilding...")
        return None
    librate = get_librate_from_idx(idx, FILENAME)
    warinfo = await warinfo_data()
    status = await api_data()
    if None in [warinfo, status]:
        print("api error")
        return
    status = status.get('planetStatus')
    warinfo = warinfo.get('planetInfos')
    maxhealth = int(warinfo[idx]['maxHealth'])
    pop = status[idx]['players']
    for planet in status:
        total_players += planet['players']
    pop = round(pop / total_players * 100)
    
    return librate * 0.01 * maxhealth / pop