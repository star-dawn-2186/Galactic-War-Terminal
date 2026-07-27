from utils import convert_time, api_data, format_duration
from find_planets import name_to_idx
async def get_dss_info(dss_json):
    planet_id = dss_json['planetIndex']
    _, planet = name_to_idx(planet_id)
    planet = planet.upper()
    api = await api_data()
    vote_ddl = convert_time(dss_json['currentElectionEndWarTime'], api)
    
    actions = dss_json['tacticalActions']
    active_effect = 'None'
    for action in actions:
        if action['activeEffectIds'] != []:
            active_effect = action['name']
            expires = convert_time(action['statusExpireAtWarTimeSeconds'], api)
            
    donation_text = ''
    if active_effect == 'None':
        for action in actions:
            name = action['name']
            donation = action['cost'][0]
            current, target, delta = donation['currentValue'], donation['targetValue'], donation['deltaPerSecond']
            progress = round(current / target * 100, 2)
            eta = format_duration(int((target - current) / delta))
            donation_text += f"### {name}\n - Progress: {progress}%\n - Time until activation: {eta}\n"
    else:
        donation_text = f'### -{active_effect} ACTIVE-\n> Expires <t:{expires}:R>'
    text = f"## DSS: Above {planet}\n> Moves: <t:{vote_ddl}:R>\n" + donation_text
    
    return text
            