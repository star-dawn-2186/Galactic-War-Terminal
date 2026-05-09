import time
import json
from utils import MO_data
from find_planets import name_to_idx
with open("json_data/assignments/tasks/task/type.json") as f:
    TYPES = json.load(f)
with open("json_data/assignments/tasks/task/valueTypes.json") as f:
    VALUETYPES = json.load(f)
with open("json_data/items/item_names.json") as f:
    ITEM_NAMES = json.load(f)

def parse_mo(mo_data):
    if len(mo_data) == 0:
        return []
    orders = []
    for order in mo_data:
        ddl = int(time.time()) + order['expiresIn']
        progress = order['progress']
        setting = order['setting']
        title = setting['overrideTitle']
        desc = setting['overrideBrief']
        tasks = setting['tasks']
        task_list = []
        for task in tasks:
            task_progress = progress[tasks.index(task)]
            task_type = TYPES[str(task['type'])]
            task_dict = {'type': task_type, 'progress': task_progress}
            for i in range(len(task['values'])):
                try:
                    value, valuetype = int(task['values'][i]), VALUETYPES[str(task['valueTypes'][i])]
                except KeyError:
                    continue
                if value == 0 and valuetype != 'location_index':
                    continue
                match valuetype:
                    case 'race':
                        value = ['', 'Human', 'Terminid', 'Automaton', 'Illuminate'][value]
                    case 'location_type':
                        value = 'Planet' if value == 1 else 'Sector'
                    case 'location_index':
                        if 'location_type' not in task_dict:
                            continue
                        if task_dict['location_type'] == 'Planet':
                            _, value = name_to_idx(value)
                    case 'item_id':
                        value = ITEM_NAMES[str(value)]['name']
                        
                task_dict[valuetype] = value
            task_list.append(task_dict)
            
        orders.append({'ddl': ddl,
                       'title': title,
                       'desc': desc,
                       'tasks': task_list})
    return orders

def main():
    mo_data = MO_data()
    print(json.dumps(parse_mo(mo_data), indent=4))
    
if __name__ == "__main__":
    main()
    
    
                