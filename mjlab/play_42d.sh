#!/bin/bash
# Play script for 42D observation space model

# Usage: ./play_42d.sh <checkpoint_path>
# Example: ./play_42d.sh logs/rsl_rl/go2_velocity/2026-05-14_14-30-02/model_500.pt

if [ -z "$1" ]; then
    echo "Usage: $0 <checkpoint_path>"
    echo "Example: $0 logs/rsl_rl/go2_velocity/2026-05-14_14-30-02/model_500.pt"
    exit 1
fi

CHECKPOINT_PATH=$1

export WANDB_MODE=disabled
MUJOCO_GL=egl uv run play Mjlab-Velocity-Flat-Unitree-Go2-42 \
  --checkpoint-file "$CHECKPOINT_PATH" \
  --num-envs 1 \
  --device cuda:0 \
  --viewer viser

cd /home/y/ece489/ECE489-RL-MPC/mjlab
uv run play Mjlab-Velocity-Flat-Unitree-Go2 \
  --checkpoint_file /home/y/ece489/ECE489-RL-MPC/mjlab/logs/rsl_rl/go2_velocity/2026-05-14_13-40-46/model_1999.pt \
  --num-envs 1 \
  --viewer viser