"""Record joint data from trained RL policy to understand the motion pattern."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch

from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls


def record_rl_joint_data(checkpoint_path: str, num_steps: int = 500):
  """Record joint positions and velocities from RL policy.

  Args:
    checkpoint_path: Path to trained model checkpoint.
    num_steps: Number of steps to record.
  """
  print("=" * 60)
  print("Recording RL Policy Joint Data")
  print("=" * 60)

  device = "cuda:0" if torch.cuda.is_available() else "cpu"

  # Load environment
  print("\nLoading environment...")
  env_cfg = load_env_cfg("Mjlab-Velocity-Flat-Unitree-Go2", play=True)
  env_cfg.scene.num_envs = 1
  base_env = ManagerBasedRlEnv(cfg=env_cfg, device=device)
  env = RslRlVecEnvWrapper(base_env)

  # Load RL policy
  print("Loading RL policy...")
  rl_cfg = load_rl_cfg("Mjlab-Velocity-Flat-Unitree-Go2")
  runner_cls = load_runner_cls("Mjlab-Velocity-Flat-Unitree-Go2")

  # Create runner without train_cfg
  from mjlab.rl import MjlabOnPolicyRunner

  runner = MjlabOnPolicyRunner(env, rl_cfg, device=device)

  checkpoint = torch.load(checkpoint_path, map_location=device)
  runner.alg.actor_critic.load_state_dict(checkpoint["model_state_dict"])
  runner.alg.actor_critic.eval()

  print(f"Loaded checkpoint: {checkpoint_path}")

  # Storage for data
  joint_positions = []
  joint_velocities = []
  joint_targets = []
  base_velocities = []
  timestamps = []

  # Reset and run
  print(f"\nRecording {num_steps} steps...")
  obs = env.reset()

  robot = base_env.scene["robot"]

  for step in range(num_steps):
    # Get action from policy
    with torch.no_grad():
      actions = runner.alg.actor_critic.act_inference(obs)

    # Step environment
    obs, reward, done, info = env.step(actions)

    # Record data
    joint_pos = robot.data.joint_pos[0].cpu().numpy()  # (12,)
    joint_vel = robot.data.joint_vel[0].cpu().numpy()  # (12,)
    joint_target = actions[0].cpu().numpy()  # (12,)
    base_vel = robot.data.body_com_lin_vel_w[0, 0, :].cpu().numpy()  # (3,)

    joint_positions.append(joint_pos)
    joint_velocities.append(joint_vel)
    joint_targets.append(joint_target)
    base_velocities.append(base_vel)
    timestamps.append(step * base_env.step_dt)

    if step % 100 == 0:
      print(f"  Step {step}/{num_steps} | Base vel: {base_vel[0]:.3f} m/s")

  # Convert to numpy arrays
  joint_positions = np.array(joint_positions)  # (T, 12)
  joint_velocities = np.array(joint_velocities)  # (T, 12)
  joint_targets = np.array(joint_targets)  # (T, 12)
  base_velocities = np.array(base_velocities)  # (T, 3)
  timestamps = np.array(timestamps)  # (T,)

  print("\n✅ Recording complete!")

  # Analyze data
  print("\n" + "=" * 60)
  print("Data Analysis")
  print("=" * 60)

  # Joint names
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

  print("\nJoint Position Statistics:")
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

  print(f"\nBase Velocity:")
  print(f"  Mean: {np.mean(base_velocities[:, 0]):.3f} m/s")
  print(f"  Std:  {np.std(base_velocities[:, 0]):.3f} m/s")

  # Save data
  output_dir = Path("rl_joint_analysis")
  output_dir.mkdir(exist_ok=True)

  data = {
    "timestamps": timestamps.tolist(),
    "joint_positions": joint_positions.tolist(),
    "joint_velocities": joint_velocities.tolist(),
    "joint_targets": joint_targets.tolist(),
    "base_velocities": base_velocities.tolist(),
    "joint_names": joint_names,
    "dt": float(base_env.step_dt),
  }

  with open(output_dir / "rl_joint_data.json", "w") as f:
    json.dump(data, f, indent=2)

  print(f"\n💾 Data saved to {output_dir / 'rl_joint_data.json'}")

  # Create plots
  print("\n📊 Creating plots...")
  create_plots(timestamps, joint_positions, joint_names, base_velocities, output_dir)

  print(f"\n✅ Analysis complete! Check {output_dir}/ for results.")

  return data


def create_plots(timestamps, joint_positions, joint_names, base_velocities, output_dir):
  """Create visualization plots."""

  # Plot 1: All joint positions over time
  fig, axes = plt.subplots(4, 3, figsize=(15, 12))
  fig.suptitle("RL Policy Joint Positions Over Time", fontsize=16, fontweight="bold")

  for i, (ax, name) in enumerate(zip(axes.flat, joint_names)):
    ax.plot(timestamps, joint_positions[:, i], linewidth=1.5)
    ax.set_title(name, fontsize=10)
    ax.set_xlabel("Time (s)", fontsize=8)
    ax.set_ylabel("Position (rad)", fontsize=8)
    ax.grid(alpha=0.3)

  plt.tight_layout()
  plt.savefig(output_dir / "joint_positions.png", dpi=300, bbox_inches="tight")
  print(f"  Saved: {output_dir / 'joint_positions.png'}")

  # Plot 2: Compare legs (hip, thigh, calf separately)
  fig, axes = plt.subplots(1, 3, figsize=(15, 4))
  fig.suptitle("RL Policy Joint Patterns by Type", fontsize=14, fontweight="bold")

  joint_types = ["Hip", "Thigh", "Calf"]
  leg_names = ["FR", "FL", "RR", "RL"]
  colors = ["#e74c3c", "#3498db", "#2ecc71", "#f39c12"]

  for joint_idx, (ax, joint_type) in enumerate(zip(axes, joint_types)):
    for leg_idx, (leg_name, color) in enumerate(zip(leg_names, colors)):
      col_idx = leg_idx * 3 + joint_idx
      ax.plot(
        timestamps,
        joint_positions[:, col_idx],
        label=leg_name,
        color=color,
        linewidth=1.5,
        alpha=0.8,
      )

    ax.set_title(f"{joint_type} Joints", fontsize=12)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Position (rad)")
    ax.legend()
    ax.grid(alpha=0.3)

  plt.tight_layout()
  plt.savefig(output_dir / "joint_comparison.png", dpi=300, bbox_inches="tight")
  print(f"  Saved: {output_dir / 'joint_comparison.png'}")

  # Plot 3: Base velocity
  fig, ax = plt.subplots(figsize=(12, 4))
  ax.plot(timestamps, base_velocities[:, 0], label="Forward (x)", linewidth=2)
  ax.plot(timestamps, base_velocities[:, 1], label="Lateral (y)", linewidth=2)
  ax.set_title("Base Velocity Over Time", fontsize=14, fontweight="bold")
  ax.set_xlabel("Time (s)")
  ax.set_ylabel("Velocity (m/s)")
  ax.legend()
  ax.grid(alpha=0.3)

  plt.tight_layout()
  plt.savefig(output_dir / "base_velocity.png", dpi=300, bbox_inches="tight")
  print(f"  Saved: {output_dir / 'base_velocity.png'}")

  plt.close("all")


if __name__ == "__main__":
  checkpoint = "/home/y/ece489/lab4/mjlab/logs/rsl_rl/go2_velocity/2026-05-12_05-41-56/model_500.pt"
  record_rl_joint_data(checkpoint, num_steps=500)
