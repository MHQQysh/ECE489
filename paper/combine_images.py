#!/usr/bin/env python3
"""Combine multiple images into grid layouts."""

import cv2
import numpy as np
import sys

def combine_images_horizontal(image_paths, output_path, max_height=400):
    """Combine images horizontally with consistent height."""
    images = []
    for path in image_paths:
        img = cv2.imread(path)
        if img is None:
            print(f"Error: Cannot read {path}")
            return False

        # Resize to consistent height
        h, w = img.shape[:2]
        new_h = max_height
        new_w = int(w * (new_h / h))
        img_resized = cv2.resize(img, (new_w, new_h))
        images.append(img_resized)

    # Combine horizontally
    combined = np.hstack(images)
    cv2.imwrite(output_path, combined)
    print(f"Created: {output_path}")
    return True

def combine_images_grid(image_paths, output_path, cols=3, max_width=600):
    """Combine images in a grid layout."""
    images = []
    for path in image_paths:
        img = cv2.imread(path)
        if img is None:
            print(f"Error: Cannot read {path}")
            return False

        # Resize to consistent width
        h, w = img.shape[:2]
        new_w = max_width
        new_h = int(h * (new_w / w))
        img_resized = cv2.resize(img, (new_w, new_h))
        images.append(img_resized)

    # Calculate grid dimensions
    rows = (len(images) + cols - 1) // cols

    # Pad with blank images if needed
    while len(images) < rows * cols:
        blank = np.ones_like(images[0]) * 255
        images.append(blank)

    # Create grid
    grid_rows = []
    for i in range(rows):
        row_images = images[i*cols:(i+1)*cols]
        row = np.hstack(row_images)
        grid_rows.append(row)

    combined = np.vstack(grid_rows)
    cv2.imwrite(output_path, combined)
    print(f"Created: {output_path}")
    return True

if __name__ == "__main__":
    base_path = "/home/y/ece489/project"

    # Combine RL flat images (3 in a row)
    print("Combining RL flat terrain images...")
    combine_images_horizontal(
        [f"{base_path}/rl_flat_{i}.png" for i in [1, 2, 3]],
        f"{base_path}/rl_flat_combined.png",
        max_height=350
    )

    # Combine RL slope images (3 in a row)
    print("Combining RL slope terrain images...")
    combine_images_horizontal(
        [f"{base_path}/rl_slope_{i}.png" for i in [1, 2, 3]],
        f"{base_path}/rl_slope_combined.png",
        max_height=350
    )

    # Combine MPC images (4 in 2x2 grid)
    print("Combining MPC images...")
    combine_images_grid(
        [
            f"{base_path}/mpc_xfast_1.png",
            f"{base_path}/mpc_xfast_2.png",
            f"{base_path}/mpc_y_1.png",
            f"{base_path}/mpc_y_2.png",
        ],
        f"{base_path}/mpc_combined.png",
        cols=2,
        max_width=500
    )

    print("\nDone! All combined images created.")
