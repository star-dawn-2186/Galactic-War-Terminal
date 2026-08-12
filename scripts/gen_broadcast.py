import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
from utils import api_data, planet_data, warinfo_data
from find_planets import name_to_idx, get_regions_by_name
import asyncio
async def get_locations():
    api = api_data()
    planet = planet_data()
    warinfo = warinfo_data()
    if None in [api, planet, warinfo]:
        return None
    campaigns = api.get('campaigns')
    planets = [name_to_idx(campaign['planetIndex'], planet)[1].title() for campaign in campaigns]
    regions = []
    for i in planets:
        planet_regions, _ =  get_regions_by_name(api, warinfo, planet, i)
        regions += [region['name'] for region in planet_regions]
    return planets, regions
def count_nums(num):
    if str(num).endswith('1') and num != 11:
        suffix = "st"
    elif str(num).endswith('2') and num != 12:
        suffix = "nd"
    elif str(num).endswith('3'):
        suffix = "rd"
    else:
        suffix = "th"
        
    return str(num)+suffix

TEMPLATES = {"SEAF_NEWS":["The {c_num} {adj} {branch} {class} {unit} has {situation} {location}."],
             #"GWR_SUBUNIT_NEWS": ["The {subunit} have {situation} at {location}"],
            "ECONOMY":["{merchandise} prices {change} by {amount} following the {event} of {location}.",
                    "{merchandise} stocks {change} due to {reason}.",
                    "Experts agree that {merchandise} sales {change} because of {reason}."],
            "SPOTLIGHT":["Heroic {soldier} {neg_action} {num} {enemy_plural} single-handedly despite {injury}.",
                        "Citizens thank {soldier} after they reportedly {pos_action}.",
                        "{soldier} hailed as hero, receives {award} after they {neg_action} {num} {enemy_plural} with only a {injury}."],
            "PSAS":["PSA: Due to the destruction of Administrative Center 02, processing times for all {form_id} permits will be delayed by {num} business days.",
                    "PSA: Switching to your pistol is faster than reloading. Unless, of course, your pistol isn't reloaded either.",
                    "PSA: Thinking is dangerous. Leave that to us.",
                    "PSA: Remember to fill in your {form_id} form at least {num} months prior to {form_action}.",
                    "PSA: {minor_bad_thing} is bad. Dissidence is bad. Therefore, {minor_bad_thing} makes you a dissident."],
            # "ADMIN_INFO":[],
            # "SCIENCE":[],
            # "WEATHER":[],
            # "HISTORY":[],
            # "PROPAGANDA":[]
            }

POOLS = {"num": [str(i) for i in range(2,501)],
         "c_num": [count_nums(i) for i in range(1, 501)],
         "adj": ["", "Armored", "Mechanized", "Augmented", "Reinforced"],
         "branch": ["Ground", "Aerial", "Orbital", "Naval", "Marine", "Cyber-warfare"],
         "class": ["Assault", "Support", "Recon", "Breakthrough", "Shock", "Heavy", "Vanguard", "Repair", "Logistics"],
         "unit": ["Battalion", "Company", "Group", "Army", "Division", "Brigade", "Squadron", "Corps", "Regiment", "Wing", "Detachment"],
         "situation":["established a beachhead on", "broken through the defenses at", "held off an assault from", "successfully relocated to", "occupied",\
                      "been pinned down at", "have failed to hold", "retreated from", "sustained heavy casualties at", "been held back from reaching",\
                      "started a siege at", "faced significant resistance from", "chosen to press on towards"],
         "subunit": ["S.T.I.M. Units", "R.A.T. Units", "A.R.C. Units", "Wild Weasels"],
         "merchandise":["crayon", "goldfish", "bug spray", "General Brasch poster", "Helldiver plushie"],
         "change":["soar", "rise", "increase", "skyrocket", "fall", "plummet", "drop"],
         "amount":[str(i)+'%' for i in (1,100)],
         "event": ["liberation", "property damage", "loss", "siege", "encirclement", "assault", "evacuation"],
         "reason": ["sheer Democratic fervor", "dissident sabotage", "Automaton cyberattacks", "Illuminate mind-control", "reasons definitively unknowable", "flawless decision-making from the Ministry of Commerce"],
         "soldier": ["SEAF soldier", "Helldiver", "Eagle pilot", "Pelican pilot", "Democracy Officer", "Truth Enforcer", "SEAF technician", "janitor"],
         "neg_action":["kill", "maim", "severely injure", "seriously inconvenience", "distract", "scream at"],
         "enemy_plural":["Terminids", "Automatons", "Illuminate", "Bile Titans", "Scavangers", "Alpha Commanders", "Hive Lords", "Rocket Devastators", "Berserkers", "Vox Engines", "Factory Striders", "Voteless", "Overseers", "Fleshmobs", "Leviathans"],
         "injury": ["broken arm", "broken leg", "twisted ankle", "grazed knee", "cervical fracture", "minor brain injury", "slight concussion", "sore trigger finger"],
         "pos_action": ["helped a granny across the street", "rescued local settlement from dissident radio broadcast", "executed all traitors in the region", "detonated hellbomb to fumigate an entire colony at once"],
         "award": ["Medal of Honor", "custom cape signed by General Brasch", "a gold star sticker", "verbal commendation from the Ministry of Defense", "pat on the back", "cordial handshake", "several hundred Super Credits", "an extra doctor's visit allowance"],
         "form_id": ["C-01 Procreation", "B-02 Funeral Services", "G-04 Open Non-carry", "K-22 Urgent Medical Care"],
         "form_action": ["dying", "going outdoors", "doing any action considered \"risky\" (like not carrying a sidearm)"],
         "minor_bad_thing": ["dying too fast", "not recycling properly", "missing your shots", "singing the Super Earth anthem out of tune", "thinking too hard", "questioning", "taking a break exceeding 4 minutes", "expressing curiosity", "reloading prematurely", "complaining about your equipment"]
         }


def generate_broadcast():
    
    try:
        category = random.choice(list(TEMPLATES.keys()))
        
        template = random.choice(TEMPLATES[category])
        fills = {key: random.choice(values) for key, values in POOLS.items()}
        

        message = template.format(**fills)
        message = message[:1].upper() + message[1:]

        return message
    except Exception as e:
        print(e)
        return ''
    
if __name__ == '__main__':
    import asyncio
    locations = asyncio.run(get_locations())
    locations = locations[0] + locations[1]
    POOLS['location'] = locations
    while True:
        input()
        print(generate_broadcast())
    
