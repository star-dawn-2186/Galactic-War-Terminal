from static_data import region_names, planet_names, effect_names, planet_info
from libcalc import get_librate_from_idx, get_region_librate_from_idx
import math
import time
from utils import convert_time
def get_campaign_for_planet(api_data, idx):
    campaigns = api_data.get("campaigns")
    for campaign in campaigns:
        if str(campaign['planetIndex']) == str(idx):
            return campaign
def find_planet_or_region_by_name(api_data, warinfo_data, name, planet_names=planet_names,  region_names=region_names):
    # Search planets
    planet_matches = [(int(idx), pname) for idx, pname in planet_names.items() if name.lower() in pname.lower()]
    # Search regions
    region_matches = []
    warinfo_regions = warinfo_data.get("planetRegions", [])
    for region in warinfo_regions:
        settings_hash = str(region.get("settingsHash", ""))
        region_name = region_names.get(settings_hash, None)
        if region_name and name.lower() in region_name.lower():
            region_matches.append((region["planetIndex"], region["regionIndex"], region_name))

    # Handle matches
    if planet_matches and not region_matches:
        if len(planet_matches) == 1:
            idx, pname = planet_matches[0]
            campaign = get_campaign_for_planet(api_data, idx)
            campaign_type_map = {
                0: "Liberation",
                1: "Recon",
                2: "High Priority Campaign",
                3: "Attrition",
                4: "Event"
            }
            campaign_type_num = campaign["type"] if campaign else "Unknown"
            campaign_type_str = campaign_type_map.get(campaign_type_num, "Unknown")
            print(f"Selected planet: {pname} ({campaign_type_str})")
            return ("planet", idx)
        else:
            print(f"\n{len(planet_matches)} planets with \"{name}\" found:")
            for i, (idx, pname) in enumerate(planet_matches, 1):
                print(f"  {i}: {pname}")
            while True:
                selection = input(f"Select a planet by number (1-{len(planet_matches)}), or type 'cancel' to abort: ").strip()
                if selection.lower() == 'cancel':
                    return None
                if selection.isdigit():
                    selection = int(selection)
                    if 1 <= selection <= len(planet_matches):
                        return ("planet", planet_matches[selection - 1][0])
                print("Invalid selection.")
    elif region_matches and not planet_matches:
        if len(region_matches) == 1:
            pi, ri, rname = region_matches[0]
            print(f"Selected region: {rname} (Planet Index: {pi}, Region Index: {ri})")
            return ("region", pi, ri)
        else:
            print(f"\n{len(region_matches)} regions with \"{name}\" found:")
            for i, (pi, ri, rname) in enumerate(region_matches, 1):
                print(f"  {i}: {rname} (Planet Index: {pi}, Region Index: {ri})")
            while True:
                selection = input(f"Select a region by number (1-{len(region_matches)}), or type 'cancel' to abort: ").strip()
                if selection.lower() == 'cancel':
                    return None
                if selection.isdigit():
                    selection = int(selection)
                    if 1 <= selection <= len(region_matches):
                        pi, ri, _ = region_matches[selection - 1]
                        return ("region", pi, ri)
                print("Invalid selection.")
    elif planet_matches and region_matches:
        print(f"\nMatches found in both planets and regions for \"{name}\":")
        print("Planets:")
        for i, (idx, pname) in enumerate(planet_matches, 1):
            print(f"  P{i}: {pname}")
        print("Regions:")
        for i, (pi, ri, rname) in enumerate(region_matches, 1):
            print(f"  R{i}: {rname} (Planet Index: {pi}, Region Index: {ri})")
        while True:
            selection = input(f"Select 'P#' for planet or 'R#' for region, or type 'cancel' to abort: ").strip().lower()
            if selection == 'cancel':
                return None
            if selection.startswith('p') and selection[1:].isdigit():
                idx = int(selection[1:]) - 1
                if 0 <= idx < len(planet_matches):
                    return ("planet", planet_matches[idx][0])
            if selection.startswith('r') and selection[1:].isdigit():
                idx = int(selection[1:]) - 1
                if 0 <= idx < len(region_matches):
                    pi, ri, _ = region_matches[idx]
                    return ("region", pi, ri)
            print("Invalid selection.")
    else:
        print(f"No planet or region found matching \"{name}\".")
        return None

def name_to_idx(name):
    """Resolve a planet name or numeric index to (int_index, str_name).
    
    Accepts either a string planet name (case-insensitive) or an integer index.
    Returns (idx, name) tuple, or (None, None) if not found.
    """
    idx = -1
    try:
        idx = int(name)
        if idx in [263, 264, 265]:
            return idx, None
        try:
            name = planet_names[str(idx)]
        except:
            print(name, idx)
            return None, None
    except:
        for pID in planet_names:
            if planet_names[pID].lower() == name.lower():
                idx = pID
                break
        if idx == -1:
            print(name, idx)
            return None, None
    return int(idx), name


def calc_required_hp(stats, api_data, planet_data, warinfo, idx):
    health = stats['health']
    dmg_mirroring = stats['campaign'] == 'Defense'
    required = 0
    health_copy = health
    bypass = False
    if stats['has regions']: 
        regions, _ = get_regions_by_name(api_data, warinfo, planet_data, idx)
        regions = sorted(regions, key=lambda x: x['availabilityFactor'], reverse=True)
        if all(region['eta'] == "**Liberty Secured**" for region in regions):
            bypass = True
    else:
        bypass = True
        
    if not bypass:
        for region in regions:
            if region['eta'] != "**Liberty Secured**":
                required += (region['health'])
                if dmg_mirroring:
                    health -= (region['health'])
                    if health < 0:
                        required += health
                        health = 0
                        break
                health -= region['libbomb'] * stats['maxhealth']
                if health < 0:
                    required += health
                    health = 0
                    break
        required += health
    else:
        required = health
    return min([required,health_copy])

def get_stats_by_name(api_data, planet_data, warinfo_data, name_in):
    
    idx, name = name_to_idx(name_in)
    if idx is None:
        print(f"{name_in}: name or idx not found")
        return None
    
    total_players = 0    
    factions = ["","Human", "Terminid", "Automaton", "Illuminate"]    
    warinfo = warinfo_data.get('planetInfos')
    
    pop = api_data.get('planetStatus')[int(idx)]['players']
    for planet in api_data.get('planetStatus'):
        total_players += planet['players']
    pop = round(pop / total_players * 100)
    
    campaign = get_campaign_for_planet(api_data, idx)
    if campaign == None:
        if api_data.get('planetStatus')[int(idx)]['owner'] == 1:
            campaign_type = "Already liberated"
        else:
            campaign_type = "Currently unreachable"
    else:
        campaign_type_map = {
                    0: "Liberation",
                    1: "Recon",
                    2: "High Priority Campaign",
                    3: "Attrition",
                    4: "Defense"
                }
        campaign_type = campaign_type_map[campaign['type']]
    
    events = api_data.get('planetEvents')
    
    flag = False
    
    for event in events:
        if str(event['planetIndex']) == str(idx):
            faction = factions[campaign['race']]
            health = event['health']
            maxhealth = event['maxHealth']
            level = maxhealth // 50000
            ddl = convert_time(event['expireTime'], api_data)
            duration = (event['expireTime'] - event['startTime']) // 3600
            progress = round((1 - health / maxhealth) * 100, 2)
            flag = True
            break

        
    if not flag:
        faction = factions[api_data.get('planetStatus')[int(idx)]['owner']]  
        regen = api_data.get('planetStatus')[int(idx)]['regenPerSecond']
        health = api_data.get('planetStatus')[int(idx)]['health']
        maxhealth = warinfo[int(idx)]['maxHealth']
        decay = round(regen * 3600 / maxhealth * 100, 2)
        progress = round((1 - health / maxhealth) * 100, 2)
    
    position = api_data.get('planetStatus')[int(idx)]['position']
    x, y = position['x'], position['y']
    dist_to_se = round(math.sqrt(x**2 + y**2), 4)
   
    try:
        biome = planet_info[str(idx)]['biome']
    except: # backup from weird unstable training manual API
        try:
            biome = planet_data.get(idx)['biome']['slug']
        except:
            biome = "Unknown"
    try:
        environmentals = '\n'.join(planet_info[str(idx)]['environmentals'])
    except:
        environmentals = '\n'.join([i['name'] for i in planet_data.get(str(idx))['environmentals']])
    
    try:
        names = planet_info[str(idx)]['names']
        localized_names = ' // '.join([names['en-US'], names['es-ES'], names['fr-FR'], names['ru-RU'], names['zh-Hans']])
    except:
        localized_names = "N/A"
        
    if name == '':
        name = f"Planet {idx}"
    
    planet_regions = warinfo_data.get('planetRegions')
    city = False
    for region in planet_regions:
        if str(region['planetIndex']) == str(idx):
            city = True
            break
    
    use_alg = False
    if city:
        regions, _ = get_regions_by_name(api_data, warinfo_data, planet_data, idx)
        if not all(region['eta'] == "**Liberty Secured**" for region in regions):
            use_alg = True
    
    if campaign_type in ['Already liberated', 'Currently unreachable']:
        librate = 0
        eta = 'N/A'
        
    elif not use_alg: # no regions, simple eta calc
        librate = get_librate_from_idx(idx)[1]
        if librate is None:
            eta = "**UNCERTAIN**"
        elif librate > 0:
            eta = (100 - progress) / librate
        elif librate < 0:
            eta = progress / librate
        else:
            eta = "**STALEMATE**" 
    else:
        eta = None
    
    if flag:
        stats = {"id": idx, 
                "faction": faction, 
                "campaign": campaign_type, 
                "biome": biome, 
                "environmentals": environmentals, 
                "dist": dist_to_se, 
                "has regions": city,
                "pop%": pop,
                "level": level,
                "duration": duration,
                "ddl": ddl,
                "progress": progress,
                "eta": eta,
                "health": health,
                "maxhealth": maxhealth}
    else:
        stats = {"id": idx, 
                "faction": faction, 
                "campaign": campaign_type, 
                "biome": biome, 
                "environmentals": environmentals, 
                "dist": dist_to_se, 
                "has regions": city,
                "pop%": pop,
                "decay": decay, 
                "regen": regen,
                "progress": progress,
                "eta": eta,
                "health": health,
                "maxhealth": maxhealth}
        
    required_hp = calc_required_hp(stats, api_data, planet_data, warinfo_data, idx)
    stats['required'] = required_hp
    
    return stats, localized_names, name
        

def get_effects_by_idx(api_data, idx):
    active_effects = api_data.get('planetActiveEffects')
    effect_lst = []
    effect_ids = []
    for effect in active_effects:
        if str(effect['index']) == str(idx):
            try:
                effect_lst.append(effect_names[str(effect['galacticEffectId'])])
            except:
                effect_lst.append(f"Unknown effect: {effect['galacticEffectId']}")
                    
            effect_ids.append(effect['galacticEffectId'])
    global_events = api_data.get('globalEvents')
    for event in global_events:
        if int(idx) in event['planetIndices'] or event['planetIndices'] == []:
            for effect in event['effectIds']:
                try:
                    effect_lst.append(effect_names[str(effect)])
                except:
                    effect_lst.append(f"Unknown effect: {effect}")
    try:
        dss = api_data.get('spaceStations')[0]
        if str(dss['planetIndex']) == str(idx):
            for effect in dss['activeEffectIds']:
                if str(effect) not in ['1384', '1385']:
                    effect_lst.append(effect_names[str(effect)])
    except IndexError:
        pass
    
    
    # absolute cinema
    effect_lst = [i for i in effect_lst if not (i.lower().endswith('(enemies)') or i.lower().endswith('(marker)'))]
    effect_lst = list(set(effect_lst))
    return effect_lst, effect_ids

def get_regions_by_name(api_data, warinfo_data, planet_data, name):
    idx, Pname = name_to_idx(name)
    if idx is None:
        return None
    warinfo = warinfo_data.get('planetInfos')
    planet_event = api_data.get('planetEvents')

    planet_health = api_data.get('planetStatus')[idx]['health']
    planet_maxhealth = warinfo[idx]['maxHealth']
    for event in planet_event:
        if event['planetIndex'] == idx and event['eventType'] == 1: # Defense campaigns
            planet_health = event['health']
            planet_maxhealth = event['maxHealth']
            break
    
    
    region_status = [region for region in api_data.get('planetRegions') if region['planetIndex'] == idx]
    region_info = [region for region in warinfo_data.get('planetRegions') if region['planetIndex'] == idx]
    planet_players = api_data.get('planetStatus')[idx]['players']
    region_dicts = []
    for region in region_status:
        region_idx = region['regionIndex']
        
        for r in region_info:
            if r['regionIndex'] == region_idx:
                maxhealth = r['maxHealth']
                dmg = r['damageMultiplier']
                lib_bomb = maxhealth * dmg / planet_maxhealth
                region_hash = r['settingsHash']
                break
        rID = f"{idx}:{region_idx}"
        
        eq_size = round(maxhealth / 1e6, 2)
        health = region['health']
        progress = round((1 - (health / maxhealth)) * 100, 2)
        regen = region['regerPerSecond'] # istg i did not make a typo there, the API literally says regerpersecond instead of regen, what the fuck
        decay = round(regen * 3600 / maxhealth * 100, 2)
        name = region_names[str(region_hash)]
        players = region['players']
        pop = 0 if planet_players == 0 else round(players / planet_players * 100, 2)
        
        aF = region['availabilityFactor']
        is_available = region['isAvailable']
        owner = region['owner'] # 1 = Super Earth / Humans, 2 = Terminids, 3 = Automatons, 4 = Illuminate
        
        librate = get_region_librate_from_idx(rID)[1]
        if librate is None: # no data found -> something went wrong
            eta = "[CORRUPTED DATA, POSSIBLE AUTOMATON INTEFERENCE]"
        elif owner == 1: # no need to do any calculations if the region is already ours, NEEDS CONFIRMATION WHETHER THIS BREAKS REGIONS ON A PLANET WITH AN ACTIVE DEFENSE
            eta = "**Liberty Secured**"
        elif librate > 0: # liberation rate greater than 0 -> calculate time to 100% liberation
            eta = (100 - progress) / librate
        elif librate < 0: # liberation rate lesser than 0 -> calculate time to 0% liberation
            eta = progress / librate
        elif is_available: # if region is available, AND not ours, AND we're neither losing nor gaining liberation, we're most likely at 0% liberation without enough divers to get a positive liberation rate
            eta = "Stalemate"
        else:
            eta = "Unavailable"
            
        
        region_dicts.append({'name': name,
                             'p_idx': idx,
                             'r_idx': region_idx,
                             'eq_size': eq_size,
                             'decay': decay,
                             'regen': regen,
                             'progress': progress,
                             'pop': pop,
                             'players': players,
                             'eta': eta,
                             'libbomb': lib_bomb,
                             'health': health,
                             'maxhealth': maxhealth,
                             'availabilityFactor': aF})
    return region_dicts, Pname

def get_defense_rating(level, duration):
    diff_idx = level / duration
    if diff_idx <= 0.7:
        rating = "Easy"
    elif diff_idx < 1:
        rating = "Routine"
    elif diff_idx < 1.3:
        rating = "Hard"
    else:
        rating = "IMPOSSIBLE"
        
    return rating


