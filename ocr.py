import requests
from PIL import Image, ImageEnhance
import json
import os
import numpy as np
from tabulate import tabulate
def process_img(imgpath, quality=75):

    try:
        with Image.open(imgpath) as img:
            
            img = img.convert('L')
            width, height = img.size
            upper = int(height * 0.27)
            lower = int(height * 0.9)
            stats_img = img.crop((0, upper, width, lower))
            
            contrast_enhancer = ImageEnhance.Contrast(stats_img)
            stats_img = contrast_enhancer.enhance(1.5)
            
            img_array = np.array(stats_img)
            mask = (img_array < 210)
            img_array[mask] = 0
            stats_img = Image.fromarray(np.uint8(img_array))
            
            
            imgname = imgpath.split('.')[0]
            stats_path = imgname + '_processed.jpeg'
            stats_img.save(stats_path, "JPEG", quality=quality, optimize=True)
    except IOError as e:
        print(f"Error compressing image: {e}")

def ocr_space_file(filename, overlay=False, api_key='K87463386188957', language='eng'):

    payload = {'isOverlayRequired': overlay,
               'apikey': api_key,
               'language': language,
               'isTable': True,
               'OCREngine': 2
               }
    with open(filename, 'rb') as f:
        r = requests.post('https://api.ocr.space/parse/image',
                          files={filename: f},
                          data=payload,
                          )
    return r.content.decode()

def is_num(s):
    num = s.replace('%','').replace(',','').replace('.','')
    return num.isdigit()
    
def img_to_stats(imgpath, debug = False):
    process_img(imgpath)
    imgname = imgpath.split('.')[0]
    stats_path = imgname + '_processed.jpeg'
    stats = json.loads(ocr_space_file(stats_path))
    txt = stats['ParsedResults'][0]['ParsedText'].split('\n')

    stats = {}
    for line in txt:
        try:
            l = line.split('\t')[:-1]
            if debug:
                print(l)
            stat_name = l[0].rstrip(':').upper()
        except IndexError:
            continue
        if 'ILLS' in stat_name and 'MELEE' not in stat_name: # lmao
            stat_name = 'KILLS'
        if stat_name not in ['KILLS', 'ACCURACY', 'SHOTS FIRED', 'SHOTS HIT', 'DEATHS', 'STIMS USED', 'ACCIDENTALS', 'SAMPLES EXTRACTED', 'STRATAGEMS USED', 'MELEE KILLS']:
            continue
        values = []
        for i in range(len(l)):
            if i == len(l) - 1 and not is_num(l[i]):
                values.append(0)
            elif not is_num(l[i]) and not is_num(l[i+1]):
                values.append(0)
            elif is_num(l[i]):
                num = l[i].replace('%','').replace(',','')
                if stat_name == 'ACCURACY':
                    values.append(float(num))
                else:
                    values.append(int(num))

        stats[stat_name] = values
    
    if not debug:
        os.remove(imgpath)
        os.remove(stats_path)
    return stats
        
def summary_from_stats(stats):
    table_data = []
    for stat, values in stats.items():
        row = [stat] + values
        table_data.append(row)
    return tabulate(table_data)
        

if __name__ == '__main__':
    players= img_to_stats('207B071.JPG', debug=True)
    print(summary_from_stats(players))