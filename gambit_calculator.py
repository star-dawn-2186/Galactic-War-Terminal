from utils import *
from find_planets import *
from horse import horse_predict




def calc_gambit(idx, api_data, planet_data, warinfo):
    idx, name = name_to_idx(idx)
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
    
    target_names = [name_to_idx(target_idx)[1] for target_idx in targets]
    
    
    source_stats, _, source_name = get_stats_by_name(api_data, planet_data, warinfo, source_idx)
    
    # target hp calc
    target_required = 0
    for target_idx in targets:
        target_required += calc_required_hp(api_data, planet_data, warinfo, target_idx)
              
    # source hp calc
    source_required = calc_required_hp(api_data, planet_data, warinfo, source_idx)

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
        result['source']['horse'] = round(source_horse, 2)
        result['targets']['horse'] = round(target_horse, 2)
    
    return result