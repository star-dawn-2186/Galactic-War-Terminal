import time
import json
import os
from utils import MO_data
from find_planets import name_to_idx
from config import EVENTS_DIR
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
                        try:
                            value = ITEM_NAMES[str(value)]['name']
                        except:
                            value = f'item {value}'
                        
                task_dict[valuetype] = value
            task_list.append(task_dict)
            
        orders.append({'ddl': ddl,
                       'title': title,
                       'desc': desc,
                       'tasks': task_list})
    return orders

def init_mo_tracker():
    mo_data = MO_data()
    orders = parse_mo(mo_data)
    progresses = []
    for order in orders:
        task_progress = [{'progress': task['progress'], 'goal': task['goal'], 'delta': 0} for task in order['tasks']]
        progresses.append(task_progress)
    with open(os.path.join(EVENTS_DIR, 'mo_tracker.json'), 'w') as f:
        json.dump(progresses, f)

def update_mo_tracker():
    mo_data = MO_data()
    if len(mo_data) == 0:
        tracker_path = os.path.join(EVENTS_DIR, 'mo_tracker.json')
        if not os.path.isfile(tracker_path):
            return
        os.rename(tracker_path, os.path.join(EVENTS_DIR, f'mo_{time.time()}.json'))
        return
    tracker_path = os.path.join(EVENTS_DIR, 'mo_tracker.json')
    if not os.path.isfile(tracker_path):
        init_mo_tracker()
        return
    with open(tracker_path, 'r') as f:
        prev_progress = json.load(f)
        
    orders = parse_mo(mo_data)
    progresses = []
    for order in orders:
        task_progress = [{'progress': task['progress'], 'goal': task['goal'], 'delta': 0} for task in order['tasks']]
        progresses.append(task_progress)
        
    for i in range(len(orders)):
        if i >= len(prev_progress):
            break
        for j in range(len(orders[i]['tasks'])):
            delta = orders[i]['tasks'][j]['progress'] - prev_progress[i][j]['progress']
            progresses[i][j]['delta'] = delta
    with open(os.path.join(EVENTS_DIR, 'mo_tracker.json'), 'w') as f:
        json.dump(progresses, f)
            
            
        
        
def main():
    mo_data = MO_data()
    print(json.dumps(parse_mo(mo_data), indent=4))
    
if __name__ == "__main__":
    main()
    
    
                