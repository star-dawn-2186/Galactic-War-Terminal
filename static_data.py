import json

# region_names, planet_names, effect_names, planet_info, biomes


with open('json_data/planets/planets.json','r') as f:
    planet_info = json.load(f)
with open('json_data/planets/planetRegion.json','r') as f:
    regions = json.load(f)
with open('json_data/effects/planetEffects.json','r') as f:
    effects = json.load(f)
with open('json_data/planets/biomes.json', 'r') as f:
    biomes = json.load(f)
with open('json_data/planets/environmentals.json', 'r') as f:
    environmental_info = json.load(f)    

region_names = {}
for idx in regions:
    region_names[idx] = regions[idx]['name']

planet_names = {}
for idx in planet_info:
    planet_names[idx] = planet_info[str(idx)]['name'] 

effect_names = {}
for idx in effects:
    effect_names[idx] = effects[idx]['name']
        