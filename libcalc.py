import json
from datetime import datetime
from utils import api_data, warinfo_data
from config import LIBERATION_DIR
import os
UPDATE_INTERVAL = 600
p_FILENAME = os.path.join(LIBERATION_DIR, "prev_health.json")
r_FILENAME = os.path.join(LIBERATION_DIR, "region_health.json")
# logic:
# get current health from status
# get past health from stored
# delta health
# get max health from warinfo
# delta health / max health = health%
# health% / time = lib rate

# omg thank you past joe i had no fucking clue what you wrote

async def update_librate(p_filename=p_FILENAME, r_filename = r_FILENAME, mode='both'):
    status = await api_data()
    warinfo = await warinfo_data()
    
    if None in [status, warinfo]:
        print("api error")
        return

    planet_status = status.get('planetStatus')
    region_status = status.get('planetRegions')
    planet_info = warinfo.get('planetInfos')
    region_info = warinfo.get('planetRegions')
    planet_events = status.get('planetEvents')
    
    if not os.path.isfile(p_filename):
        await init_savedhealth(p_filename,'p')
        print("Planet logs missing or corrupted, rebuilding...")
        return 
    
    if not os.path.isfile(r_filename):
        await init_savedhealth(r_filename,'r')
        print("Region logs missing or corrupted, rebuilding...")
        return
        
    with open(p_filename,'r') as f:
        healthdict = json.load(f)
    
    if mode in ['both', 'p']:
        events = []
        for event in planet_events:
            if 'planetIndex' in event:
                idx = event['planetIndex']
                events.append(int(idx))
                players = planet_status[idx]['players']
                health = int(event['health'])
                prev_health = healthdict[str(idx)][0]
                maxhealth = int(event['maxHealth'])
                if prev_health % 10000 == 0: # previously liberated, new defense
                    librate = None
                    delta_health = 0
                else:
                    delta_health = prev_health - health
                    healthp = delta_health / maxhealth * 100
                    librate = round(healthp / (UPDATE_INTERVAL / 3600),2)

                    
                healthdict[str(idx)] = [health, librate, delta_health, players]
                
        for planet in planet_status:
            if int(planet['index']) in events:
                continue
            
            players = planet['players']
            health = int(planet['health'])
            try:
                prev_health = healthdict[str(planet['index'])][0]
            except KeyError:
                continue
            delta_health = prev_health - health
            for p in planet_info:
                if p['index'] == planet['index']:
                    maxhealth = int(p['maxHealth'])
                    break
            healthp = delta_health / maxhealth * 100
            librate = round(healthp / (UPDATE_INTERVAL / 3600),2)
            healthdict[str(planet['index'])] = [health, librate, delta_health, players]
            
        with open(p_filename,'w') as f:
            json.dump(healthdict, f, indent=4)
            
    new_regions = []
    if mode in ['both', 'r']:
        
        with open(r_filename, 'r') as f:
            regiondict = json.load(f)
        
        for region in region_status:
            # regions fluctuate much more frequently than planets, and not all regions are shown in status
            # so dynamically update regions? until all existing regions are in there
            # shouldnt be too much for file size
            pID = region['planetIndex']
            idx = region['regionIndex']
            health = region['health']
            players = region['players']
            for r in region_info:
                if r['planetIndex'] == pID and r['regionIndex'] == idx:
                    maxhealth = r['maxHealth']
                    break
                
            rID = f"{pID}:{idx}"
            if rID not in regiondict:
                new_regions.append(rID)
                regiondict[rID] = [health, 0, 0, 0]
            prev_health = regiondict[rID][0]
            delta_health = prev_health - health
            healthp = delta_health / maxhealth * 100
            if delta_health > 0.9 * maxhealth:
                librate = 0
                delta_health = 0
            else:
                librate = round(healthp / (60 / 3600),2)
            regiondict[rID] = [health, librate, delta_health, players]
        
    
        with open(r_filename, 'w') as f:
            json.dump(regiondict, f, indent=4)
        
    now = datetime.now()
    print(f"{now}: updated librates | mode: {mode}")
    return new_regions

async def init_savedhealth(filename=p_FILENAME, mode = 'p'):
    status = await api_data()
    if status is None:
        return
    if mode == 'p':
        planet_status = status.get('planetStatus')
        planet_events = status.get('planetEvents')
        healthdict = {}
        for planet in planet_status:
            healthdict[str(planet['index'])] = [planet['health'], 0, 0, 0]
        for event in planet_events:
            if event['eventType'] == 1:
                idx = event['planetIndex']
                health = int(event['health'])
                healthdict[str(idx)] = [health, 0, 0, 0]
        with open(filename,'w') as f:
            json.dump(healthdict, f, indent=4)
            
    elif mode == 'r':
        region_status = status.get('planetRegions')
        regiondict = {}
        for region in region_status:
            pID = region['planetIndex']
            idx = region['regionIndex']
            health = region['health']
            rID = f"{pID}:{idx}"
            regiondict[rID] = [health, 0, 0, 0]
        with open(filename, 'w') as f:
            json.dump(regiondict, f, indent=4)
                
        

def get_librate_from_idx(idx, filename=p_FILENAME):
    if not os.path.isfile(filename):
        print("Logs missing or corrupted, rebuilding...")
        return None
    with open(filename,'r') as f:
        healthdict = json.load(f)
    return healthdict[str(idx)]

def get_region_librate_from_idx(rID, filename=r_FILENAME):
    if not os.path.isfile(filename):
        print("Logs missing or corrupted, rebuilding...")
        return None
    with open(filename, 'r') as f:
        regiondict = json.load(f)
    return regiondict[rID]

