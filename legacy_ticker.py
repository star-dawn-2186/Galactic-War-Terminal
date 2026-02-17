import os
from PIL import Image, ImageDraw, ImageFont
import imageio.v2 as imageio
import numpy as np
import gc


def create_stock_ticker_gif(stock_data, output_path="stock_ticker.gif", duration=50, loop=0, fps=120, pixels_per_frame=None):
    """Create a low-memory scrolling stock ticker GIF.

    - Streams frames to disk with imageio to avoid keeping them in memory.
    - Pads content by one screen width so the visual wrap is smooth.
    - Ensures cycle length is a multiple of `pixels_per_frame` so the
      final frame is exactly one step before the first frame.
    """

    # Configuration
    width, height = 600, 80
    background_color = (0, 0, 0)
    text_color = (255, 255, 255)
    up_color = (0, 255, 0)
    down_color = (255, 0, 0)
    neutral_color = (128, 128, 128)
    bug_color = (241, 158, 29)
    bot_color = (236, 107, 105)
    squid_color = (206, 93, 251)
    # Base scroll speed (pixels per step). Increased to 3 for faster scroll.
    scroll_speed = 3

    # Load fonts
    try:
        font = ImageFont.truetype("arial.ttf", 30)
        small_font = ImageFont.truetype("arial.ttf", 25)
    except Exception:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()

    # Measure text
    temp_img = Image.new('RGB', (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)

    stock_entries = []
    total_content_width = 0

    # Normalize stock_data formats and measure widths
    small_spacer = ' // '
    for name, value in stock_data.items():
        if isinstance(value, (list, tuple)) and len(value) == 2:
            change, is_positive = value
            decay = ""
            pop = ""
            faction = None
        else:
            try:
                change, is_positive, decay, pop, faction = value
            except Exception:
                change = str(value)
                is_positive = True
                decay = pop = ""
                faction = None

        change_str = f"▲{change}" if is_positive else f"▼{change}"
        color = up_color if is_positive else down_color
        if str(change) in ("0", "0.0", "0.0%"):
            change_str = f"-{change}"
            color = neutral_color

        if faction == 't':
            decay_color = bug_color
        elif faction == 'a':
            decay_color = bot_color
        else:
            decay_color = squid_color

        stock_w = temp_draw.textlength(name, font=font)
        change_w = temp_draw.textlength(change_str, font=small_font)
        decay_w = temp_draw.textlength(decay, font=small_font)
        pop_w = temp_draw.textlength(pop, font=small_font)
        spacer_w = temp_draw.textlength("   ", font=font)
        small_spacer_w = temp_draw.textlength(small_spacer, font=small_font)

        entry_w = int(stock_w + change_w + small_spacer_w + decay_w + small_spacer_w + pop_w + spacer_w)

        stock_entries.append({
            'name': name,
            'change_str': change_str,
            'decay': decay,
            'pop': pop,
            'color': color,
            'decay_color': decay_color,
            'total_w': entry_w,
            'change_x': int(stock_w),
            'spacer1_x': int(stock_w) + int(change_w),
            'decay_x': int(stock_w) + int(change_w) + int(small_spacer_w),
            'spacer2_x': int(stock_w) + int(change_w) + int(small_spacer_w) + int(decay_w),
            'pop_x': int(stock_w) + int(change_w) + int(small_spacer_w) + int(decay_w) + int(small_spacer_w)
        })

        total_content_width += entry_w

    del temp_img, temp_draw

    if total_content_width <= 0:
        return None

    # Padding so wrap looks natural; do not render extra content, just blank padding
    pad = width
    cycle_length = total_content_width + pad

    # Default pixels_per_frame: make visual speed noticeably faster by
    # moving multiple pixels per frame. Use twice the base scroll_speed
    # when caller doesn't provide a value.
    if pixels_per_frame is None or pixels_per_frame < 1:
        pixels_per_frame = max(1, scroll_speed * 2)

    # Align cycle to a multiple of pixels_per_frame so the loop lands exactly
    cycle_steps = (cycle_length + pixels_per_frame - 1) // pixels_per_frame
    cycle = cycle_steps * pixels_per_frame

    # Build tile sized to full cycle (content + padding)
    tile_width = cycle
    tile_img = Image.new('RGB', (tile_width, height), background_color)
    tile_draw = ImageDraw.Draw(tile_img)

    # Draw entries and repeat from the start into the padding area so the
    # wrap uses real content instead of a blank screen. This doesn't
    # increase per-frame memory because tile_img size is unchanged.
    cur_x = 0
    i = 0
    n = len(stock_entries)
    # First pass: draw entries in order
    for e in stock_entries:
        tile_draw.text((cur_x, 20), e['name'], fill=e['decay_color'], font=font)
        tile_draw.text((cur_x + e['change_x'], 22), e['change_str'], fill=e['color'], font=small_font)
        tile_draw.text((cur_x + e['spacer1_x'], 22), small_spacer, fill=text_color, font=small_font)
        tile_draw.text((cur_x + e['decay_x'], 22), e['decay'], fill=e['decay_color'], font=small_font)
        tile_draw.text((cur_x + e['spacer2_x'], 22), small_spacer, fill=text_color, font=small_font)
        tile_draw.text((cur_x + e['pop_x'], 22), e['pop'], fill=text_color, font=small_font)
        cur_x += e['total_w']
        i += 1

    # Fill remaining tile area by repeating entries from the start
    idx = 0
    while cur_x < tile_width:
        e = stock_entries[idx % n]
        tile_draw.text((cur_x, 20), e['name'], fill=e['decay_color'], font=font)
        tile_draw.text((cur_x + e['change_x'], 22), e['change_str'], fill=e['color'], font=small_font)
        tile_draw.text((cur_x + e['spacer1_x'], 22), small_spacer, fill=text_color, font=small_font)
        tile_draw.text((cur_x + e['decay_x'], 22), e['decay'], fill=e['decay_color'], font=small_font)
        tile_draw.text((cur_x + e['spacer2_x'], 22), small_spacer, fill=text_color, font=small_font)
        tile_draw.text((cur_x + e['pop_x'], 22), e['pop'], fill=text_color, font=small_font)
        cur_x += e['total_w']
        idx += 1

    # Writer setup
    if fps is not None and fps > 0:
        seconds_per_frame = 1.0 / float(fps)
    else:
        seconds_per_frame = max(0.001, duration / 1000.0)

    with imageio.get_writer(output_path, mode='I', duration=seconds_per_frame, loop=loop) as writer:
        for step in range(cycle_steps):
            x_offset = (step * pixels_per_frame) % cycle

            frame = Image.new('RGB', (width, height), background_color)

            # Paste as many tile copies as needed to cover viewport
            copies_needed = (width // tile_width) + 2
            for copy in range(copies_needed):
                src_x = (copy * tile_width) - x_offset
                if src_x + tile_width > 0 and src_x < width:
                    dst_x = max(0, src_x)
                    src_start = max(0, -src_x)
                    copy_w = min(tile_width - src_start, width - dst_x)
                    if copy_w > 0:
                        region = tile_img.crop((src_start, 0, src_start + copy_w, height))
                        frame.paste(region, (dst_x, 0))

            writer.append_data(np.asarray(frame))
            frame.close()

    tile_img.close()

    # Help free large image buffers promptly
    try:
        del tile_img
    except Exception:
        pass
    try:
        del frame
    except Exception:
        pass
    try:
        del region
    except Exception:
        pass
    gc.collect()

    return output_path


