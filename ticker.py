import ctypes
import numpy as np
import imageio.v2 as imageio
from PIL import Image, ImageDraw, ImageFont

def release_memory():
    # Force the C allocator to give back free memory to the OS
    try:
        ctypes.CDLL('libc.so.6').malloc_trim(0)
    except Exception:
        pass
def create_stock_ticker_gif(stock_data, output_path="stock_ticker.gif", fps=50, speed=2):
    """
    Accelerated ticker generation using NumPy slicing.
    - speed: pixels moved per frame.
    - fps: frames per second (50 is recommended for smooth GIFs).
    """
    width, height = 600, 80
    bg_color = (0, 0, 0)
    text_color = (255, 255, 255)
    up_color = (0, 255, 0)
    down_color = (255, 0, 0)
    neutral_color = (128, 128, 128)
    
    # Faction Colors
    faction_map = {
        't': (241, 158, 29),  # bugs
        'a': (236, 107, 105),  # bots
        's': (206, 93, 251)   # squid/illuminate
    }

    # 1. Setup Fonts
    try:
        font = ImageFont.truetype("DOTMATRX.TTF", 30)
        small_font = ImageFont.truetype("DOTMATRX.TTF", 25)
    except Exception as e:
        print(f"{e}\nFalling back to default font")
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # 2. Pre-measure and build the "Ticker Tape"
    temp_draw = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    
    prepared_entries = []
    total_w = 0

    for name, value in stock_data.items():
        change, is_pos, decay, pop, faction = value
        
        # Format strings
        c_str = change
        c_col = up_color if is_pos else down_color
        if str(change) in ("0", "0.0", "0.0%"):
            c_col = neutral_color

        # Measure segments
        nw = temp_draw.textlength(name, font=font)
        cw = temp_draw.textlength(c_str, font=font)
        dw = temp_draw.textlength(decay, font=small_font)
        pw = temp_draw.textlength(pop, font=small_font)
        
        entry_w = int(nw + cw + dw + pw + 62 + 50) # 50px gap between planets
        prepared_entries.append({
            'name': name, 'c_str': c_str, 'decay': decay, 'pop': pop,
            'c_col': c_col, 'f_col': faction_map.get(faction, faction_map['s']),
            'w': entry_w, 'nw': nw, 'cw': cw, 'dw': dw
        })
        total_w += entry_w

    # 3. Draw the full Ticker Tape once
    # We add 'width' to the end to allow for a seamless wrap-around
    tape_width = total_w + width
    tape_img = Image.new('RGB', (tape_width, height), bg_color)
    draw = ImageDraw.Draw(tape_img)
    
    x = 0
    # Draw content
    for e in prepared_entries:
        draw.text((x, 20), e['name'], fill=e['f_col'], font=font)
        curr_x = x + e['nw'] + 10
        draw.text((curr_x, 20), f"{e['c_str']}", fill=e['c_col'], font=font)
        curr_x += e['cw'] + 30
        draw.text((curr_x, 24), f"{e['decay']}", fill=e['f_col'], font=small_font)
        curr_x += e['dw'] + 22
        draw.text((curr_x, 24), e['pop'], fill=text_color, font=small_font)
        x += e['w']
        
    # Draw the beginning again at the end for seamless looping
    tape_img.paste(tape_img.crop((0, 0, width, height)), (total_w, 0))
    
    # 4. Vectorized Frame Generation
    tape_array = np.array(tape_img)
    frames = []
    
    # Calculate steps based on speed
    # We only need to scroll 'total_w' pixels to complete a loop
    for offset in range(0, total_w, speed):
        # High-speed slice of the tape
        frame = tape_array[:, offset : offset + width]
        frames.append(frame)

    # 5. Fast Save
    imageio.mimsave(output_path, frames, fps=fps, loop=0)
    
    release_memory()
    
    return output_path