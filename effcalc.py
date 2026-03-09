from find_planets import *
from utils import *
from libcalc import *

# (delta_health + regen * time) / pop% / (time / 1h)
def calc_region_eff_from_name(api_data, warinfo_data, planet_data, name):
    idx, name = name_to_idx(name, planet_data)
    if None in [idx, name]:
        return None, None
    
    regions, _ = get_regions_by_name(api_data, warinfo_data, planet_data, idx)
    if regions == []:
        return calc_planet_eff_from_idx(api_data, warinfo_data, planet_data, idx)
    total_players = 0   
    for planet in api_data.get('planetStatus'):
        total_players += planet['players']
    
    result = []
    region_players = 0
    for region in regions:
        rID = str(region['p_idx']) + ':' + str(region['r_idx'])
        name = region['name']
        _, _, delta_health, players = get_region_librate_from_idx(rID)
        region_players += players
        regen = region['regen']
        pop = players / total_players * 100
        state = type(region['eta']) != str
        if state:
            eff = int((delta_health + regen * UPDATE_INTERVAL) / pop / (UPDATE_INTERVAL / 3600))
        else:
            eff = 'N/A' 
        result.append([name, eff])
    
    _, _, planet_dhealth, planet_players = get_librate_from_idx(idx)
    stats, _, _ = get_stats_by_name(api_data, planet_data, warinfo_data, idx)
    if "regen" in stats:
        planet_regen = stats['regen']
    else:
        planet_regen = 0
        
    if planet_dhealth > 0:
        non_region_players = planet_players - region_players
        non_region_pop = non_region_players / total_players * 100
        non_region_eff = int((planet_dhealth + planet_regen * UPDATE_INTERVAL) / non_region_pop / (UPDATE_INTERVAL / 3600))
    
    else:
        non_region_eff = 'N/A'
    
    return result, non_region_eff

def calc_planet_eff_from_idx(api_data, warinfo_data, planet_data, idx):
    
    _, _, delta_health, players = get_librate_from_idx(idx)
    total_players = 0   
    for planet in api_data.get('planetStatus'):
        total_players += planet['players']
        
    stats, _, _ = get_stats_by_name(api_data, planet_data, warinfo_data, idx)
    if "regen" in stats:
        regen = stats['regen']
    else:
        regen = 0
        
    if delta_health > 0:
        pop = players / total_players * 100
        eff = int((delta_health + regen * UPDATE_INTERVAL) / pop / (UPDATE_INTERVAL / 3600))
    
    else:
        eff = 'N/A'
    
    return None, eff