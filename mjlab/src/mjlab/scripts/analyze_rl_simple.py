"""Simple script to analyze RL joint patterns."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch

from mjlab.envs import ManagerBasedRlEnv
from mjlab.tasks.registry import load_env_cfg


def analyze_rl_joints(checkpoint_path: str, num_steps: int = 500):
  """Analyze joint patterns from RL policy."""
  print("=" * 60)
  print("RL Joint Pattern Analysis")
  print("=" * 60)

  device = "cuda:0" if torch.cuda.is_available() else "cpu"

  # Load environment
  print("\nLoading environment...")
  env_cfg = load_env_cfg("Mjlab-Velocity-Flat-Unitree-Go2", play=True)
  env_cfg.scene.num_envs = 1
  env = ManagerBasedRlEnv(cfg=env_cfg, device=device)

  # Load checkpoint directly
  print("Loading checkpoint...")
  checkpoint = torch.load(checkpoint_path, map_location=device)

  # Extract policy network
  from mjlab.rl.algorithms.ppo import ActorCritic

  # Get observation and action dimensions
  obs_shape = env.observation_space["actor"].shape[0]
  action_shape = env.action_space.shape[0]

  # Create actor-critic
  actor_critic = ActorCritic(
    num_actor_obs=obs_shape,
    num_critic_obs=env.observation_space["critic"].shape[0],
    num_actions=action_shape,
    actor_hidden_dims=[512, 256, 128],
    critic_hidden_dims=[512, 256, 128],
    activation="elu",
  ).to(device)

  actor_critic.load_state_dict(checkpoint["model_state_dict"])
  actor_critic.eval()

  print(f"✅ Loaded policy from {checkpoint_path}")

  # Storage
  joint_positions = []
  joint_targets = []
  base_velocities = []
  timestamps = []

  # Run
  print(f"\nRecording {num_steps} steps...")
  obs_dict, _ = env.reset()
  obs = obs_dict["actor"]

  robot = env.scene["robot"]

  for step in range(num_steps):
    # Get action
    with torch.no_grad():
      actions = actor_critic.act_inference(obs)

    # Step
    obs_dict, _, _, _, _ = env.step(actions)
    obs = obs_dict["actor"]

    # Record
    joint_pos = robot.data.joint_pos[0].cpu().numpy()
    joint_target = actions[0].cpu().numpy()
    base_vel = robot.data.body_com_lin_vel_w[0, 0, :].cpu().numpy()

    joint_positions.append(joint_pos)
    joint_targets.append(joint_target)
    base_velocities.append(base_vel)
    timestamps.append(step * env.step_dt)

    if step % 100 == 0:
      print(f"  Step {step}/{num_steps} | Vel: {base_vel[0]:.3f} m/s")

  # Convert
  joint_positions = np.array(joint_positions)
  joint_targets = np.array(joint_targets)
  base_velocities = np.array(base_velocities)
  timestamps = np.array(timestamps)

  print("\n✅ Recording complete!")

  # Analyze
  joint_names = [
    "FR_hip",
    "FR_thigh",
    "FR_calf",
    "FL_hip",
    "FL_thigh",
    "FL_calf",
    "RR_hip",
    "RR_thigh",
    "RR_calf",
    "RL_hip",
    "RL_thigh",
    "RL_calf",
  ]

  print("\n" + "=" * 60)
  print("Joint Statistics")
  print("=" * 60)
  print(f"{'Joint':<12} {'Mean':>8} {'Std':>8} {'Min':>8} {'Max':>8} {'Range':>8}")
  print("-" * 60)

  for i, name in enumerate(joint_names):
    mean = np.mean(joint_positions[:, i])
    std = np.std(joint_positions[:, i])
    min_val = np.min(joint_positions[:, i])
    max_val = np.max(joint_positions[:, i])
    range_val = max_val - min_val
    print(
      f"{name:<12} {mean:>8.3f} {std:>8.3f} {min_val:>8.3f} {max_val:>8.3f} {range_val:>8.3f}"
    )

  print(
    f"\nBase Velocity: {np.mean(base_velocities[:, 0]):.3f} ± {np.std(base_velocities[:, 0]):.3f} m/s"
  )

  # Save
  output_dir = Path("rl_joint_analysis")
  output_dir.mkdir(exist_ok=True)

  data = {
    "timestamps": timestamps.tolist(),
    "joint_positions": joint_positions.tolist(),
    "joint_targets": joint_targets.tolist(),
    "base_velocities": base_velocities.tolist(),
    "joint_names": joint_names,
  }

  with open(output_dir / "rl_data.json", "w") as f:
    json.dump(data, f)

  print(f"\n💾 Saved to {output_dir / 'rl_data.json'}")

  # Plot
  create_plots(timestamps, joint_positions, joint_names, base_velocities, output_dir)

  return data


def create_plots(timestamps, joint_positions, joint_names, base_velocities, output_dir):
  """Create plots."""
  # All joints
  fig, axes = plt.subplots(4, 3, figsize=(15, 12))
  fig.suptitle("RL Policy Joint Positions", fontsize=16, fontweight="bold")

  for i, (ax, name) in enumerate(zip(axes.flat, joint_names)):
    ax.plot(timestamps, joint_positions[:, i], linewidth=1.5)
    ax.set_title(name)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Position (rad)")
    ax.grid(alpha=0.3)

  plt.tight_layout()
  plt.savefig(output_dir / "joints.png", dpi=300)
  print(f"  📊 {output_dir / 'joints.png'}")

  # By type
  fig, axes = plt.subplots(1, 3, figsize=(15, 4))
  fig.suptitle("Joint Patterns by Type", fontsize=14)

  types = ["Hip", "Thigh", "Calf"]
  legs = ["FR", "FL", "RR", "RL"]
  colors = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12"]

  for j, (ax, jtype) in enumerate(zip(axes, types)):
    for i, (leg, color) in enumerate(zip(legs, colors)):
      idx = i * 3 + j
      ax.plot(
        timestamps, joint_positions[:, idx], label=leg, color=color, linewidth=1.5
      )

    ax.set_title(f"{jtype} Joints")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Position (rad)")
    ax.legend()
    ax.grid(alpha=0.3)

  plt.tight_layout()
  plt.savefig(output_dir / "by_type.png", dpi=300)
  print(f"  📊 {output_dir / 'by_type.png'}")

  plt.close("all")


if __name__ == "__main__":
  checkpoint = "/home/y/ece489/lab4/mjlab/logs/rsl_rl/go2_velocity/2026-05-12_05-41-56/model_500.pt"
  analyze_rl_joints(checkpoint, num_steps=500)
