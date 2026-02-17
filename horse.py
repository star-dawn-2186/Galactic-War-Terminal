from static_data import biomes
from utils import *
import json
import os
import pickle

# default manual weights (fallback)
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

# load learned weights if available
LEARNED = {}
if os.path.isfile('learned_weights.json'):
    try:
        with open('learned_weights.json','r') as f:
            LEARNED = json.load(f)
    except Exception:
        LEARNED = {}

# biome bias (simple heuristic)
biome_bias = {}
for biome in biomes:
    for i in ['arctic', 'moor', 'sandy','bug_hiveworld']:
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
    
    # Prefer using a saved sklearn pipeline if available, else fall back to learned weights
    # BEST_PIPELINE = None
    # if os.path.isfile('horse_model.pkl'):
    #     try:
    #         with open('horse_model.pkl','rb') as pf:
    #             BEST_PIPELINE = pickle.load(pf)
    #     except Exception:
    #         BEST_PIPELINE = None

    # if BEST_PIPELINE is not None:
    #     try:
    #         row = {
    #             'dist': float(static.get('dist', 0) or 0),
    #             'has_regions': 1 if static.get('has regions') else 0,
    #             'pop%': float(static.get('pop%', 0) or 0),
    #             'environmentals_any': 1 if static.get('environmentals') else 0,
    #             'faction': static.get('faction', ''),
    #             'biome': static.get('biome', ''),
    #             'dss': 1 if 'OPERATIONAL SUPPORT' in effects else 0,
    #             'subfaction': 1 if any(t in effects for t in ['CORPS','BRIGADE','STRAIN']) else 0
    #         }
    #         df_row = pd.DataFrame([row])
    #         pred = BEST_PIPELINE.predict(df_row)[0]
    #         return float(pred) / 100.0
    #     except Exception:
    #         pass

    if LEARNED and 'weights' in LEARNED:
        try:
            w = LEARNED['weights']
            intercept = LEARNED.get('intercept', 0.0)
            # map features similar to train_horse.py
            feat = {}
            feat['dist'] = float(static.get('dist', 0) or 0)
            feat['has_regions'] = 1 if static.get('has regions') else 0
            feat['pop%'] = float(static.get('pop%', 0) or 0)
            feat['environmentals_any'] = 1 if static.get('environmentals') else 0
            feat['dss'] = 1 if 'OPERATIONAL SUPPORT' in effects else 0
            feat['subfaction'] = 1 if any(t in effects for t in ['CORPS','BRIGADE','STRAIN']) else 0

            score = intercept
            for k in ['dist','has_regions','pop%','environmentals_any','dss','subfaction']:
                score += feat.get(k, 0) * w.get(k, 0)
            for key, val in w.items():
                if key.startswith('faction_') and static.get('faction') and key == f"faction_{static.get('faction')}":
                    score += val
                if key.startswith('biome_') and static.get('biome') and key == f"biome_{static.get('biome')}":
                    score += val
            return score / 100.0
        except Exception:
            pass

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
        score -= 0.5 * weights['Faction']
    if city:
        score += weights["City"]
    
    DSS = "OPERATIONAL SUPPORT" in effects
    subfaction = False
    for i in ['CORPS', 'BRIGADE', 'STRAIN']:
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


def horse_predict_with_details(static, effects):
    """Wrapper around horse_predict that returns both raw model prediction and human-friendly score.
    
    Returns:
        dict with keys:
        - 'raw_prediction': raw model prediction delta (may be None if campaign unwinnable)
        - 'model_type': 'pipeline', 'learned_weights', or 'manual'
    """
    raw = horse_predict(static, effects)
    
    # determine which model was used by checking if files exist
    model_type = 'manual'
    if os.path.isfile('horse_model.pkl'):
        try:
            with open('horse_model.pkl','rb'):
                model_type = 'pipeline'
        except Exception:
            pass
    elif os.path.isfile('learned_weights.json'):
        try:
            with open('learned_weights.json','r'):
                model_type = 'learned_weights'
        except Exception:
            pass
    
    return {
        'raw_prediction': raw,
        'model_type': model_type
    }
