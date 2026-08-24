import cv2
import numpy as np
import os
import json
from ocr import process_img, ocr_space_file

def prepare_svg_template(svg_file_path, scale=5.0):
    import cairosvg
    png_bytes = cairosvg.svg2png(url=svg_file_path, scale=scale, background_color='black')

    nparr = np.frombuffer(png_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)


    if img.shape[2] == 4:  
        alpha_channel = img[:, :, 3]
        _, binary_template = cv2.threshold(alpha_channel, 127, 255, cv2.THRESH_BINARY)
    else:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary_template = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    
    binary_template = cv2.bitwise_not(binary_template)
    
    points = cv2.findNonZero(binary_template)
    x, y, w, h = cv2.boundingRect(points)
    cropped = binary_template[y:y+h, x:x+w]

    filename = svg_file_path.split('\\')[-1].replace('svg', 'png')
    output_path = os.path.join('mission_templates',filename)
    cv2.imwrite(output_path, cropped)
    print(f"Template saved to {output_path}")
    
    return binary_template


def detect_helldiver_icon(image_path, debug = False):
    img = cv2.imread(image_path)
    
    process_img(image_path)
    imgname = image_path.split('.')[0]
    hivelord_path = imgname + '_processed.jpeg'
    try:
        stats = json.loads(ocr_space_file(hivelord_path))
        txt = stats['ParsedResults'][0]['ParsedText']
        if 'HIGH-VALUE TARGET DESTROYED' in txt or 'Killed Hive Lord' in txt:
            os.remove(hivelord_path)
            return {}, {'Hive_Lord': 1}
    except KeyError:
        pass
    
    
    height, width = img.shape[:2]
    upper = int(height * 0.35)
    lower = int(height * 0.65)
    upper2 = int(height * 0.2)
    lower2 = int(height * 0.5)
    left = int(width * 0.4)
    right = int(width * 0.6)
    
    to_img = img[upper:lower, left:right]
    obj_img = img[upper2:lower2, left:right]

    # hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    template_paths = [f"templates/{file}" for file in os.listdir("templates")]
    templates = {}
    for t in template_paths:
        templates[t.split('/')[-1][:-12]] = cv2.imread(t, 0)
        
    mission_template_paths = [f"mission_templates/{file}" for file in os.listdir("mission_templates")]
    mission_templates = {}
    for t in mission_template_paths:
        mission_templates[t.split('/')[-1][:-17]] = cv2.imread(t, 0)

    lower_cyan = np.array([190, 190, 90])   
    upper_cyan = np.array([255, 255, 180]) 
    lower_orange = np.array([0, 100, 215])
    upper_orange = np.array([100, 170, 255])
    
    mask = cv2.inRange(to_img, lower_cyan, upper_cyan)
    mask2 = cv2.inRange(obj_img, lower_orange, upper_orange)
    if debug:
        cv2.imwrite('mask.png', mask)    
        cv2.imwrite('orange_mask.png', mask2)
    
    kernel_size = 10
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    dilated = cv2.dilate(mask, kernel, iterations=1)

    orange_dilated = cv2.dilate(mask2, kernel, iterations=1)
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    obj_contours, _ = cv2.findContours(orange_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    boxes = []
    iconsize = 30
    
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > iconsize // 1.5 and h > iconsize:
            boxes.append((x, y, w, h))    
    matches = {}
    for name, _ in templates.items():
        matches[name] = 0
    i = 0
    for box in boxes:
        x, y, w, h = box
        icon = mask[y:y+h, x:x+w]
        points = cv2.findNonZero(icon)
        x2, y2, w2, h2 = cv2.boundingRect(points)
        icon = icon[y2:y2+h2, x2:x2+w2]
        if debug:
            cv2.imwrite(f'icon_test/icon_{i}.png', icon)
        i += 1
        
        scores = {}
        for name in templates:
            scores[name] = 0
        for name, template in templates.items():
            resized_template = cv2.resize(template, (w2, h2), interpolation=cv2.INTER_AREA)
            _, icon = cv2.threshold(icon, 127, 255, cv2.THRESH_BINARY)
            _, resized_template = cv2.threshold(resized_template, 127, 255, cv2.THRESH_BINARY)
            
            
            intersection = np.logical_and(icon, resized_template)
            union = np.logical_or(icon, resized_template)
            
            iou_score = np.sum(intersection) / np.sum(union)
            
            scores[name] = iou_score
        if debug:
            print(scores)
       
        most_likely_match = max(scores, key=scores.get)
        matches[most_likely_match] += 1
    matches = {k: v for k, v in matches.items() if v != 0}
    
    boxes = []

    for cnt in obj_contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > iconsize and h > iconsize:
            boxes.append((x, y, w, h))    
    obj_matches = {}
    for name, _ in mission_templates.items():
        obj_matches[name] = 0
    for box in boxes:
        x, y, w, h = box
        icon = cv2.bitwise_not(mask2[y:y+h, x:x+w])
        points = cv2.findNonZero(icon)
        x2, y2, w2, h2 = cv2.boundingRect(points)
        icon = icon[y2:y2+h2, x2:x2+w2]
        
        scores = {}
        for name in mission_templates:
            scores[name] = 0
        for name, template in mission_templates.items():
            resized_template = cv2.resize(template, (w2, h2), interpolation=cv2.INTER_AREA)
            _, icon = cv2.threshold(icon, 127, 255, cv2.THRESH_BINARY)
            _, resized_template = cv2.threshold(resized_template, 127, 255, cv2.THRESH_BINARY)
            
            intersection = np.logical_and(icon, resized_template)
            union = np.logical_or(icon, resized_template)
            
            iou_score = np.sum(intersection) / np.sum(union)
            
            scores[name] = iou_score
       
        most_likely_match = max(scores, key=scores.get)
        if scores[most_likely_match] <= 0.6:
            continue
        obj_matches[most_likely_match] += 1
    obj_matches = {k: v for k, v in obj_matches.items() if v != 0}
    if not debug:
        os.remove(image_path)
    return matches, obj_matches

def init_templates():
    svg_path = 'mission_icons'
    filenames = os.listdir(svg_path)
    for filename in filenames:
        path = os.path.join(svg_path, filename)
        # print(path)
        prepare_svg_template(path)

if __name__ == '__main__':
    # init_templates()
    matches = detect_helldiver_icon("202E5D1.JPG", debug = True)
    print(matches)