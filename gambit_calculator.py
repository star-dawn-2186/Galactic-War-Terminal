from utils import *
from find_planets import *
from horse import horse_predict

def calc_gambit(idx, api_data, planet_data, warinfo):
    idx, name = name_to_idx(idx, planet_data)
    target_stats, _, _ = get_stats_by_name(api_data, planet_data, warinfo, idx)
    
    
    if target_stats['campaign'] != 'Defense': # Not a defense, wdym gambit
        return None
    
    attacks = api_data.get('planetAttacks')
    planet_info = warinfo.get('planetInfos')
    sources = []
    for attack in attacks:
        if attack['target'] == idx:
            sources.append(attack['source'])
    
    if sources == []: 
        return "SWEET LIBERTY IT'S CALYPSO ALL OVER AGAIN" # Pray to Lady Liberty
    
    elif len(sources) > 1:
        return "Multiple attack sources, gambit highly discouraged"
    
    source_idx = sources[0]
    targets = [idx]
    
    for attack in attacks:
        if attack['source'] == source_idx and attack['target'] != idx:
            targets.append(attack['target'])
    
    target_names = [name_to_idx(target_idx, planet_data)[1] for target_idx in targets]
    
    
    source_stats, _, source_name = get_stats_by_name(api_data, planet_data, warinfo, source_idx)
    
    # target hp calc
    target_required = 0
    for target_idx in targets:
        defenses = api_data.get('planetEvents')
        for defense in defenses:
            if defense['planetIndex'] == target_idx:
                target_health = defense['health']
                break
        
        # without regions
        t_stats, _, _ = get_stats_by_name(api_data, planet_data, warinfo, target_idx)
        if not t_stats['has regions']:
            target_required += target_health
        else: # with regions
            target_regions, _ = get_regions_by_name(api_data, warinfo, planet_data, target_idx)
            target_regions = sorted(target_regions, key=lambda x: x['availabilityFactor'], reverse=True)
            for region in target_regions:
                if region['eta'] != "**Liberty Secured**":
                    target_required += region['eq_size'] * 1e6
                    target_health -= region['eq_size'] * 1e6 # damage mirroring
                    
                    if target_health < 0:
                        target_required += target_health
                        break
                    
                    target_health -= region['libbomb'] * target_stats['level'] * 50000
                    if target_health <= 0:
                        break
              
    # source hp calc
    planet_status = api_data.get('planetStatus')
    source_health = planet_status[source_idx]['health']
    
    # without regions
    source_maxhealth = planet_info[source_idx]['maxHealth']
    if not source_stats['has regions']:
        source_required = source_health
    
    else: # with regions
        source_required = 0
        source_regions, _ = get_regions_by_name(api_data, warinfo, planet_data, source_idx)
        for region in source_regions:
            if region['eta'] != "**Liberty Secured**":
                source_required += region['eq_size'] * 1e6
                target_health -= region['libbomb'] * source_maxhealth
                if target_health <= 0:
                    break
        source_required = min([source_required, source_health]) # for scenarios where liberating a region requires more hp than just liberating the base planet
    

    source_effects = get_effects_by_idx(api_data, source_idx)
    target_effects = []
    for target_idx in targets:
        target_effects += get_effects_by_idx(api_data, target_idx)
    
    if len(targets) > 1:
        source_horse, target_horse = 999, 999
    else:
        source_horse = horse_predict(source_stats, source_effects)
        target_horse = horse_predict(target_stats, target_effects)
        
        
    if 'OPERATIONAL SUPPORT' in source_effects: # DSS already on gambit planet (positive)
        dss = 'source'
    elif 'OPERATIONAL SUPPORT' in target_effects: # DSS already on defense planet (negative)
        dss = 'target'
    else:
        dss = 'neither'
        
    if source_required > target_required: # more work to gambit than not
        score = 0
    elif source_required < target_required * 0.75: # really good idea to gambit
        score = 1 
    else:
        score = 1 - source_required / target_required

    if score < 0:
            score = 0
    if len(targets) > 1:  
        score += 0.3 * (len(targets) - 1)
    if score != 0:
        if dss == 'source':
            score += 0.2
        elif dss == 'target':
            score -= 0.1
        score += source_horse / target_horse - 1
        
    result = {"score": score,
            "source": {"name": source_name,
                       "required": source_required},
            "targets": {"names": target_names,
                        "required": target_required},
            "dss": dss}
    if source_horse != 999:
        result['source']['horse'] = source_horse
        result['targets']['horse'] = target_horse
    
    return result