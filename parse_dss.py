from utils import convert_time, api_data
from find_planets import name_to_idx
import time

async def get_dss_info(dss_json):
    planet_id = dss_json['planetIndex']
    _, planet = name_to_idx(planet_id)
    planet = planet.upper()
    api = api_data()
    vote_ddl = convert_time(dss_json['currentElectionEndWarTime'], api)
    
    actions = dss_json['tacticalActions']
    active_effect = 'None'
    expires = None
    for action in actions:
        if action['activeEffectIds'] != []:
            active_effect = action['name']
            expires = convert_time(action['statusExpireAtWarTimeSeconds'], api)
            
    # Build structured action data for alerts
    action_data = []
    for action in actions:
        name = action['name']
        is_active = action['activeEffectIds'] != []
        donation = action['cost'][0]
        current, target, delta = donation['currentValue'], donation['targetValue'], donation['deltaPerSecond']
        progress = round(current / target * 100, 2)
        if delta != 0 and not is_active:
            eta = int(time.time() + (target - current) / delta)
        else:
            eta = None
        action_data.append({
            'name': name,
            'eta': eta,
            'is_active': is_active,
            'expires': expires if is_active else None,
            'progress': progress,
        })

    donation_text = ''
    if active_effect == 'None':
        for action in actions:
            name = action['name']
            donation = action['cost'][0]
            current, target, delta = donation['currentValue'], donation['targetValue'], donation['deltaPerSecond']
            progress = round(current / target * 100, 2)
            if delta != 0:
                eta = int(time.time() + (target - current) / delta)
                donation_text += f"### {name}\n - Progress: {progress}%\n - Activated: <t:{eta}:R>\n"
            else: 
                eta = 'N/A'
                donation_text += f"### {name}\n - Progress: {progress}%\n\n -PROGRESS HALTED-\n"
    else:
        donation_text = f'### -{active_effect} ACTIVE-\n> Expires <t:{expires}:R>'
    text = f"## DSS: Above {planet}\n> Moves: <t:{vote_ddl}:R>\n" + donation_text
    
    return text, action_data
            