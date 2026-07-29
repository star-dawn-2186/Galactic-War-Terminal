import numpy as np
import cv2
import math

def display_bgr_range(bgr1, bgr2):
    """
    Takes two BGR tuples/lists and displays an image containing 
    all colors that fall within the range of those two values.
    """
    # 1. Determine the minimum and maximum for each channel (B, G, R)
    b_min, b_max = min(bgr1[0], bgr2[0]), max(bgr1[0], bgr2[0])
    g_min, g_max = min(bgr1[1], bgr2[1]), max(bgr1[1], bgr2[1])
    r_min, r_max = min(bgr1[2], bgr2[2]), max(bgr1[2], bgr2[2])

    # 2. Generate all individual values within the channel boundaries
    b_vals = np.arange(b_min, b_max + 1, dtype=np.uint8)
    g_vals = np.arange(g_min, g_max + 1, dtype=np.uint8)
    r_vals = np.arange(r_min, r_max + 1, dtype=np.uint8)

    # 3. Create a 3D grid of all possible combinations using meshgrid
    B, G, R = np.meshgrid(b_vals, g_vals, r_vals, indexing='ij')
    
    # Flatten and stack them into a 1D list of BGR pixels: shape (N, 3)
    colors = np.stack((B.flatten(), G.flatten(), R.flatten()), axis=-1)
    num_colors = len(colors)
    
    if num_colors == 0:
        print("No colors found in this range.")
        return

    print(f"Generating an image with {num_colors} colors...")

    # 4. Calculate dimensions to fit these colors into a roughly square image
    side = math.ceil(math.sqrt(num_colors))

    # Pad the 1D array with black pixels (0,0,0) so it perfectly forms a square
    padding_size = (side * side) - num_colors
    if padding_size > 0:
        padding = np.zeros((padding_size, 3), dtype=np.uint8)
        colors = np.vstack((colors, padding))

    # 5. Reshape the 1D array of pixels into a 2D image: shape (side, side, 3)
    color_image = colors.reshape((side, side, 3))



    cv2.imwrite('img.png', color_image)
    


# --- Example Usage ---
if __name__ == "__main__":
    # Define two BGR colors. 
    # Example: A dark blue-green to a lighter blue-green
    color1 = (190, 190, 70)   # rgb(126, 239, 254)
    color2 = (255, 255, 150) # B, G, R
    
    display_bgr_range(color1, color2)
    