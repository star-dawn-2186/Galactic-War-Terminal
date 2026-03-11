from static_data import biomes
from utils import *


weights = {"MO":0.938,
           "Faction": 0.8,
           "Defense": 0,
           "Biome":0.25,
           "City": 0.15,
           "DSS": 0.8,
           "SE_dist": 0.046,
           "Environmentals": 0.25,
           "Subfaction": 0.4}
W_TOTAL = sum([weights[i] for i in weights])


# biome bias (simple heuristic)
biome_bias = {}
for biome in biomes:
    for i in ['arctic', 'moor', 'sandy']:
        if i in biome:
            biome_bias[biome] = 1
    for i in ['primordial', 'swamp']:
        if i in biome:
            biome_bias[biome] = -1


def horse_predict(static, effects):
    # Patented Horse Predict algorithm to determine blob preference
    # strength of influence, from highest to lowest:
    # MO, faction (bugs~bots>squids at the moment, subject to change), biome, subfaction, city, distance to SE
    # DSS location and PO are modifiers that positively affect influence on planets where present
    
    biome = static['biome']
    environmentals = static['environmentals']
    faction = static['faction']
    se_dist = static['dist']
    city = static['has regions']
    campaign = static['campaign']
    
    w_total = W_TOTAL
    score = 0
    if campaign.lower() == "already liberated" or campaign.lower() == 'currently unreachable':
        return None
    else:
        if campaign.lower() == 'defense':
            score += weights['Defense']
    
    if biome in biome_bias:
        score += biome_bias[biome] * weights['Biome']
    else:
        w_total -= weights['Biome']

    if "fire_tornados" in environmentals:
        score -= weights['Environmentals']
    else:
        w_total -= weights['Environmentals']

    if faction == 'Terminid':
        score += 1.2 * weights['Faction']
    elif faction == "Automaton":
        score += weights['Faction']
    else:
        score += 0.8 * weights['Faction']
    if city:
        score += weights["City"]
    
    DSS = "OPERATIONAL SUPPORT" in effects
    subfaction = False
    for i in ['CORPS', 'BRIGADE', 'STRAIN', 'CYBORGS']:
        if i in effects:
            subfaction = True
            break
    if subfaction:
        score += weights['Subfaction']
    
    if DSS:
        score += weights['DSS']
        
    score += se_dist * weights['SE_dist']
    
    # subfactions are complicated and i have no idea how to comprehensively deal with them rn
    # plus i lack data and plus i think they dont have that much of an impact
    
    # future joe here, i did it, it's easy as shit, i got all the data where you did, you suck
    return score / w_total

