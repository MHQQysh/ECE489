#!/usr/bin/env python3
"""Extract frames from video files for report."""

import cv2
import sys
import os

def extract_frames(video_path, output_prefix, num_frames=3):
    """Extract evenly spaced frames from video."""
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        print(f"Error: Cannot open video {video_path}")
        return False

    # Get video properties
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration = total_frames / fps if fps > 0 else 0

    print(f"Video: {video_path}")
    print(f"  Total frames: {total_frames}")
    print(f"  FPS: {fps:.2f}")
    print(f"  Duration: {duration:.2f}s")

    # Calculate frame indices to extract (skip first 10% and last 10%)
    start_frame = int(total_frames * 0.1)
    end_frame = int(total_frames * 0.9)
    frame_indices = []

    if num_frames == 1:
        frame_indices = [total_frames // 2]
    else:
        step = (end_frame - start_frame) // (num_frames - 1)
        frame_indices = [start_frame + i * step for i in range(num_frames)]

    # Extract frames
    for i, frame_idx in enumerate(frame_indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()

        if ret:
            output_path = f"{output_prefix}_{i+1}.png"
            cv2.imwrite(output_path, frame)
            timestamp = frame_idx / fps if fps > 0 else 0
            print(f"  Extracted frame {i+1} at {timestamp:.2f}s -> {output_path}")
        else:
            print(f"  Failed to extract frame {i+1}")

    cap.release()
    return True

if __name__ == "__main__":
    # RL videos
    print("=" * 60)
    print("Extracting RL Flat terrain frames...")
    print("=" * 60)
    extract_frames(
        "/home/y/ece489/project/rl_flat_alldirection_force.webm",
        "/home/y/ece489/project/rl_flat",
        num_frames=3
    )

    print("\n" + "=" * 60)
    print("Extracting RL Slope terrain frames...")
    print("=" * 60)
    extract_frames(
        "/home/y/ece489/project/rl_slope_alldirection_withpush.webm",
        "/home/y/ece489/project/rl_slope",
        num_frames=3
    )

    # MPC videos
    print("\n" + "=" * 60)
    print("Extracting MPC flat xfast frames...")
    print("=" * 60)
    extract_frames(
        "/home/y/ece489/project/mpc_flat_xfast.webm",
        "/home/y/ece489/project/mpc_xfast",
        num_frames=2
    )

    print("\n" + "=" * 60)
    print("Extracting MPC flat xy frames...")
    print("=" * 60)
    extract_frames(
        "/home/y/ece489/project/mpc_flat_xy.webm",
        "/home/y/ece489/project/mpc_xy",
        num_frames=2
    )

    print("\n" + "=" * 60)
    print("Extracting MPC flat y frames...")
    print("=" * 60)
    extract_frames(
        "/home/y/ece489/project/mpx_flat_y.webm",
        "/home/y/ece489/project/mpc_y",
        num_frames=2
    )

    print("\n" + "=" * 60)
    print("Done! All frames extracted.")
    print("=" * 60)
