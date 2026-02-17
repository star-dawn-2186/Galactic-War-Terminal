import json
import os
HISTORY = []
for file in os.listdir("SUPER EARTH DEFENSE_eO_anLpvxm"):
    filename = os.path.join("SUPER EARTH DEFENSE_eO_anLpvxm",file)
    with open(filename, 'r', encoding='utf-8') as f:
        hist = json.load(f)
    for i in range(len(hist)):
        msg = {'name': hist[i]['userName'],
               'time': hist[i]['timestamp'],
               'content': hist[i]['content']}
        HISTORY.insert(0,msg)
        
with open("SE_defense.json",'w') as f:
    json.dump(HISTORY, f)