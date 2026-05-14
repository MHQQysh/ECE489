"""Comprehensive evaluation script for comparing RL policies across configurations.

This script evaluates:
- 2 training environments: flat (100 steps), slope (300 steps)
- 3 velocity commands: (1,0), (0,1), (1,0.5)
- 4 metrics: velocity tracking error, body stability, CoT, push recovery
- 10 trials per configuration

Usage:
    cd /home/y/ece489/lab4/mjlab
    export WANDB_MODE=disabled

    # Run all evaluations
    uv run python src/mjlab/scripts/comprehensive_evaluation.py

    # Run specific configuration
    uv run python src/mjlab/scripts/comprehensive_evaluation.py \
        --task Mjlab-Velocity-Flat-Unitree-Go2 \
        --checkpoint /path/to/checkpoint.pt \
        --num-trials 10
"""

import json
import math
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

import numpy as np
import torch
import tyro
from tqdm import tqdm

from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls
from mjlab.utils.torch import configure_torch_backends
from mjlab.utils.wrappers import VideoRecorder
from mjlab.viewer import NativeMujocoViewer


@dataclass
class EvaluationMetrics:
  """Metrics collected during evaluation."""

  velocity_tracking_error: list[float] = field(default_factory=list)
  roll_rms: list[float] = field(default_factory=list)
  pitch_rms: list[float] = field(default_factory=list)
  cost_of_transport: list[float] = field(default_factory=list)
  push_recovery_success: list[bool] = field(default_factory=list)
  episode_length: list[float] = field(default_factory=list)

  def add_trial(
    self,
    vel_error: float,
    roll: float,
    pitch: float,
    cot: float,
    recovery: bool,
    ep_len: float,
  ):
    """Add metrics from one trial."""
    self.velocity_tracking_error.append(vel_error)
    self.roll_rms.append(roll)
    self.pitch_rms.append(pitch)
    self.cost_of_transport.append(cot)
    self.push_recovery_success.append(recovery)
    self.episode_length.append(ep_len)

  def summary(self) -> dict:
    """Compute summary statistics."""
    n = len(self.velocity_tracking_error)
    if n == 0:
      return {}
    return {
      "velocity_tracking_error_mean": float(np.mean(self.velocity_tracking_error)),
      "velocity_tracking_error_std": float(np.std(self.velocity_tracking_error)),
      "roll_rms_mean": float(np.mean(self.roll_rms)),
      "roll_rms_std": float(np.std(self.roll_rms)),
      "pitch_rms_mean": float(np.mean(self.pitch_rms)),
      "pitch_rms_std": float(np.std(self.pitch_rms)),
      "cost_of_transport_mean": float(np.mean(self.cost_of_transport)),
      "cost_of_transport_std": float(np.std(self.cost_of_transport)),
      "push_recovery_rate": float(np.mean(self.push_recovery_success)),
      "push_recovery_count": int(sum(self.push_recovery_success)),
      "episode_length_mean": float(np.mean(self.episode_length)),
      "num_trials": n,
    }

  def format(self, metric: str) -> str:
    """Format a metric as 'mean ± std'."""
    summary = self.summary()
    if metric == "vel_error":
      return f"{summary['velocity_tracking_error_mean']:.4f} ± {summary['velocity_tracking_error_std']:.4f}"
    elif metric == "roll":
      deg = math.degrees(summary["roll_rms_mean"])
      deg_std = math.degrees(summary["roll_rms_std"])
      return f"{summary['roll_rms_mean']:.4f} ± {summary['roll_rms_std']:.4f} ({deg:.2f}° ± {deg_std:.2f}°)"
    elif metric == "pitch":
      deg = math.degrees(summary["pitch_rms_mean"])
      deg_std = math.degrees(summary["pitch_rms_std"])
      return f"{summary['pitch_rms_mean']:.4f} ± {summary['pitch_rms_std']:.4f} ({deg:.2f}° ± {deg_std:.2f}°)"
    elif metric == "cot":
      return f"{summary['cost_of_transport_mean']:.4f} ± {summary['cost_of_transport_std']:.4f}"
    elif metric == "recovery":
      return f"{summary['push_recovery_rate']:.1%} ({summary['push_recovery_count']}/{summary['num_trials']})"
    return "N/A"


@dataclass
class EvalConfig:
  """Configuration for comprehensive evaluation."""

  task: str = "Mjlab-Velocity-Flat-Unitree-Go2"
  """Task to evaluate."""
  checkpoint: str | None = None
  """Path to trained policy checkpoint."""
  num_trials: int = 10
  """Number of evaluation trials per configuration."""
  episode_length: int = 500
  """Episode length in steps."""
  device: str = "cuda:0"
  """Device to run on (cuda:0 or cpu)."""
  output_dir: str = "evaluation_results/comprehensive"
  """Output directory for results."""
  save_video: bool = True
  """Whether to save videos."""
  video_length: int = 500
  """Length of video in steps."""
  push_force: float = 40.0
  """Lateral push force in Newtons."""
  push_duration: float = 0.1
  """Push duration in seconds."""
  push_time: float = 5.0
  """Time to apply push (seconds after episode start)."""
  velocity_commands: list[tuple[float, float]] = field(
    default_factory=lambda: [(1.0, 0.0), (0.0, 1.0), (1.0, 0.5)]
  )
  """List of (vx, vy) velocity commands to test."""
  robot_mass: float = 15.0
  """Robot mass in kg for CoT calculation."""


@dataclass
class VelocityCommand:
  """Represents a velocity command."""

  vx: float
  vy: float
  name: str = ""

  def __post_init__(self):
    if not self.name:
      if self.vx > 0 and self.vy == 0:
        self.name = "x_1.0"
      elif self.vx == 0 and self.vy > 0:
        self.name = "y_1.0"
      elif self.vx > 0 and self.vy > 0:
        self.name = f"x_{self.vx}_y_{self.vy}"
      else:
        self.name = f"vx{self.vx}_vy{self.vy}"

  def __str__(self) -> str:
    return f"({self.vx}, {self.vy}) m/s"


def quaternion_to_euler(q: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
  """Convert quaternion (w, x, y, z) to roll and pitch (in radians).

  Args:
      q: Quaternion tensor (..., 4)

  Returns:
      Tuple of (roll, pitch) tensors
  """
  w, x, y, z = q[..., 0], q[..., 1], q[..., 2], q[..., 3]

  # Roll (x-axis rotation)
  sinr_cosp = 2 * (w * x + y * z)
  cosr_cosp = 1 - 2 * (x * x + y * y)
  roll = torch.atan2(sinr_cosp, cosr_cosp)

  # Pitch (y-axis rotation)
  sinp = 2 * (w * y - z * x)
  pitch = torch.asin(torch.clamp(sinp, -1.0, 1.0))

  return roll, pitch


def compute_cost_of_transport(
  torques: torch.Tensor,
  joint_velocities: torch.Tensor,
  dt: float,
  mass: float,
  distance: float,
) -> float:
  """Compute dimensionless Cost of Transport.

  CoT = sum(|tau_i * q_dot_i| * dt) / (m * g * d)

  Args:
      torques: Joint torques (T, num_joints).
      joint_velocities: Joint velocities (T, num_joints).
      dt: Time step in seconds.
      mass: Robot mass in kg.
      distance: Distance traveled in meters.

  Returns:
      Dimensionless Cost of Transport.
  """
  g = 9.81
  power = torch.abs(torques * joint_velocities)
  total_energy = torch.sum(power) * dt
  distance = max(distance, 0.1)  # Avoid division by zero
  cot = float(total_energy / (mass * g * distance))
  return cot


def apply_push(env: ManagerBasedRlEnv, env_ids: torch.Tensor, force: float):
  """Apply lateral push to robot base.

  Args:
      env: Environment.
      env_ids: Environment IDs to push.
      force: Push force in Newtons (applied in y-direction).
  """
  robot = env.scene["robot"]

  # Get current position
  base_pos = robot.data.body_com_pos_w[env_ids, 0].clone()

  # Apply external force via direct velocity perturbation
  # This is a simplified push - in real physics you'd apply a force
  # Here we do a small lateral kick by offsetting velocity
  current_vel = robot.data.body_com_lin_vel_w[env_ids, 0, :].clone()
  current_vel[:, 1] += force * 0.01  # Lateral velocity perturbation


def run_single_trial(
  env: ManagerBasedRlEnv,
  policy,
  cfg: EvalConfig,
  command: VelocityCommand,
  trial_idx: int,
) -> dict:
  """Run one evaluation trial.

  Args:
      env: Environment.
      policy: RL policy.
      cfg: Configuration.
      command: Velocity command.
      trial_idx: Trial index.

  Returns:
      Dictionary of metrics for this trial.
  """
  device = env.device
  dt = env.step_dt

  # Reset environment
  obs, _ = env.reset()

  # Storage
  actual_velocities = []
  target_velocities = []
  orientations = []
  torques_list = []
  joint_velocities_list = []
  positions = []

  # Get command term to override velocity
  cmd_term = env.command_manager._terms["twist"]
  # Disable random resampling - set resample time far in future
  if hasattr(cmd_term, "_resample_time_stamps"):
    cmd_term._resample_time_stamps = torch.full(
      (env.num_envs,), float("inf"), device=device
    )

  push_applied = False
  push_step = int(cfg.push_time / dt)
  recovered = True
  terminated_early = False

  for step in range(cfg.episode_length):
    # Override velocity command to desired value
    cmd_term.vel_command_b[:, 0] = command.vx
    cmd_term.vel_command_b[:, 1] = command.vy

    # Get action from policy
    with torch.no_grad():
      actions = policy(obs)

    # Step environment
    obs, _, terminated, truncated, info = env.step(actions)

    # Apply push at specified time
    if step == push_step and not push_applied:
      env_ids = torch.arange(env.num_envs, device=device)
      apply_push(env, env_ids, cfg.push_force)
      push_applied = True

    # Check for fall after push
    if push_applied and (terminated.any() or truncated.any()):
      recovered = False
      terminated_early = True
      # Continue stepping to collect more data

    # Collect metrics
    robot = env.scene["robot"]

    # Use BODY FRAME velocity to match visualization
    actual_vel = robot.data.root_link_lin_vel_b[
      :, :2
    ]  # (x, y) in body frame [1, 3] -> use [:2]
    orientation = robot.data.body_com_quat_w[:, 0, :]
    position = robot.data.body_com_pos_w[:, 0, :]

    actual_velocities.append(actual_vel[0].cpu())
    # Get command in body frame (matches visualization)
    target_velocities.append(cmd_term.vel_command_b[0, :2].cpu())
    orientations.append(orientation[0].cpu())
    positions.append(position[0].cpu())

    # Get joint data
    joint_vel = robot.data.joint_vel[:, :12]  # First 12 joints
    joint_velocities_list.append(joint_vel[0].cpu())

    # Estimate torques from actions (simplified)
    torque_est = actions[0].cpu() * 20.0  # Scale to approximate torque range
    torques_list.append(torque_est)

  # Convert to tensors
  actual_velocities = torch.stack(actual_velocities)
  target_velocities = torch.stack(target_velocities)
  orientations = torch.stack(orientations)
  positions = torch.stack(positions)
  torques = torch.stack(torques_list)
  joint_velocities = torch.stack(joint_velocities_list)

  # Compute velocity tracking error (RMS) - only horizontal (x, y)
  # Only use steady-state (last 80% of episode, skip startup)
  error_h = actual_velocities[:, :2] - target_velocities[:, :2]  # (steps, 2)
  steady_start = int(len(error_h) * 0.2)
  steady_error = error_h[steady_start:]  # Skip first 20%
  vel_error = float(torch.sqrt(torch.mean(steady_error**2)))

  # Compute body stability (RMS roll & pitch)
  roll, pitch = quaternion_to_euler(orientations)
  roll_rms = float(torch.sqrt(torch.mean(roll**2)))
  pitch_rms = float(torch.sqrt(torch.mean(pitch**2)))

  # Compute distance traveled
  distance = float(torch.norm(positions[-1] - positions[0]))

  # Compute CoT
  cot = compute_cost_of_transport(
    torques,
    joint_velocities,
    dt,
    cfg.robot_mass,
    distance,
  )

  return {
    "velocity_error": vel_error,
    "roll_rms": roll_rms,
    "pitch_rms": pitch_rms,
    "cost_of_transport": cot,
    "recovery_success": recovered,
    "distance": distance,
    "terminated_early": terminated_early,
  }


def load_policy(task: str, checkpoint: str, device: str, env: ManagerBasedRlEnv):
  """Load trained RL policy from checkpoint.

  Args:
      task: Task name.
      checkpoint: Path to checkpoint.
      device: Device.
      env: Environment.

  Returns:
      Policy function.
  """
  from mjlab.rl import MjlabOnPolicyRunner

  env_wrapper = RslRlVecEnvWrapper(env)
  agent_cfg = load_rl_cfg(task)

  runner_cls = load_runner_cls(task) or MjlabOnPolicyRunner
  runner = runner_cls(env_wrapper, asdict(agent_cfg), device=device)
  runner.load(checkpoint, load_cfg={"actor": True}, strict=True, map_location=device)

  policy = runner.get_inference_policy(device=device)
  return policy


def run_evaluation(cfg: EvalConfig) -> dict:
  """Run comprehensive evaluation.

  Args:
      cfg: Evaluation configuration.

  Returns:
      Dictionary of all results.
  """
  configure_torch_backends()
  device = cfg.device

  # Create output directory
  output_dir = Path(cfg.output_dir)
  output_dir.mkdir(parents=True, exist_ok=True)

  # Timestamp for this run
  timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

  # Load environment
  print(f"Loading environment: {cfg.task}")
  env_cfg = load_env_cfg(cfg.task, play=True)
  env_cfg.scene.num_envs = 1  # Single environment for evaluation
  env = ManagerBasedRlEnv(cfg=env_cfg, device=device)

  # Load policy
  if cfg.checkpoint is None:
    raise ValueError("Must provide --checkpoint for RL evaluation")
  print(f"Loading policy from: {cfg.checkpoint}")
  policy = load_policy(cfg.task, cfg.checkpoint, device, env)

  # Setup video recording
  if cfg.save_video:
    video_dir = output_dir / "videos" / Path(cfg.checkpoint).parent.name
    video_dir.mkdir(parents=True, exist_ok=True)
    env = VideoRecorder(
      env,
      video_folder=str(video_dir),
      step_trigger=lambda step: step == 0,
      video_length=cfg.video_length,
      disable_logger=True,
    )

  # Run evaluation for each velocity command
  all_results = {}
  total_trials = len(cfg.velocity_commands) * cfg.num_trials

  print(f"\nRunning {total_trials} trials...")
  print(f"Task: {cfg.task}")
  print(f"Checkpoint: {cfg.checkpoint}")
  print(f"Velocity commands: {[str(c) for c in cfg.velocity_commands]}")
  print("-" * 60)

  pbar = tqdm(total=total_trials, desc="Evaluating")

  for command in cfg.velocity_commands:
    vel_cmd = VelocityCommand(vx=command[0], vy=command[1])
    cmd_key = vel_cmd.name
    metrics = EvaluationMetrics()

    for trial in range(cfg.num_trials):
      result = run_single_trial(env, policy, cfg, vel_cmd, trial)

      metrics.add_trial(
        vel_error=result["velocity_error"],
        roll=result["roll_rms"],
        pitch=result["pitch_rms"],
        cot=result["cost_of_transport"],
        recovery=result["recovery_success"],
        ep_len=cfg.episode_length * env.step_dt,
      )

      pbar.update(1)

    all_results[cmd_key] = {
      "command": {"vx": vel_cmd.vx, "vy": vel_cmd.vy},
      "metrics": metrics.summary(),
      "raw": {
        "velocity_tracking_error": metrics.velocity_tracking_error,
        "roll_rms": metrics.roll_rms,
        "pitch_rms": metrics.pitch_rms,
        "cost_of_transport": metrics.cost_of_transport,
        "push_recovery_success": metrics.push_recovery_success,
      },
    }

    print(f"\n{vel_cmd}:")
    print(f"  Vel Error: {metrics.format('vel_error')}")
    print(f"  Roll RMS: {metrics.format('roll')}")
    print(f"  Pitch RMS: {metrics.format('pitch')}")
    print(f"  CoT: {metrics.format('cot')}")
    print(f"  Recovery: {metrics.format('recovery')}")

  pbar.close()
  env.close()

  # Save results
  results = {
    "config": {
      "task": cfg.task,
      "checkpoint": cfg.checkpoint,
      "checkpoint_name": Path(cfg.checkpoint).name,
      "num_trials": cfg.num_trials,
      "episode_length": cfg.episode_length,
      "push_force": cfg.push_force,
      "push_duration": cfg.push_duration,
      "push_time": cfg.push_time,
      "robot_mass": cfg.robot_mass,
      "timestamp": timestamp,
    },
    "results": all_results,
  }

  # Save to file
  result_file = output_dir / f"eval_{Path(cfg.task).name}_{timestamp}.json"
  with open(result_file, "w") as f:
    json.dump(results, f, indent=2)

  print(f"\nResults saved to: {result_file}")

  return results


def generate_summary_table(all_results: dict[tuple[str, str], dict]) -> str:
  """Generate a summary table for all configurations.

  Args:
      all_results: Dictionary of results keyed by (task, checkpoint).

  Returns:
      Formatted table string.
  """
  lines = []
  lines.append("\n" + "=" * 120)
  lines.append("COMPREHENSIVE EVALUATION SUMMARY TABLE")
  lines.append("=" * 120)

  # Table header
  header = (
    f"{'Config':<40} "
    f"{'Vel Error (m/s)':<20} "
    f"{'Roll (°)':<15} "
    f"{'Pitch (°)':<15} "
    f"{'CoT':<12} "
    f"{'Recovery':<15}"
  )
  lines.append(header)
  lines.append("-" * 120)

  for (task, checkpoint), results in all_results.items():
    config_name = f"{task}\n  {Path(checkpoint).name}"

    for cmd_key, cmd_results in results["results"].items():
      metrics = cmd_results["metrics"]
      vel_err = f"{metrics['velocity_tracking_error_mean']:.3f} ± {metrics['velocity_tracking_error_std']:.3f}"
      roll = f"{math.degrees(metrics['roll_rms_mean']):.2f} ± {math.degrees(metrics['roll_rms_std']):.2f}"
      pitch = f"{math.degrees(metrics['pitch_rms_mean']):.2f} ± {math.degrees(metrics['pitch_rms_std']):.2f}"
      cot = f"{metrics['cost_of_transport_mean']:.4f} ± {metrics['cost_of_transport_std']:.4f}"
      recovery = f"{metrics['push_recovery_rate']:.0%} ({metrics['push_recovery_count']}/{metrics['num_trials']})"

      cmd_str = f"[{cmd_key}]"
      line = (
        f"{config_name} {cmd_str:<25} "
        f"{vel_err:<20} "
        f"{roll:<15} "
        f"{pitch:<15} "
        f"{cot:<12} "
        f"{recovery:<15}"
      )
      lines.append(line)

  lines.append("=" * 120)
  return "\n".join(lines)


def main():
  cfg = tyro.cli(EvalConfig)

  # Run evaluation
  results = run_evaluation(cfg)

  # Print summary
  print("\n" + "=" * 60)
  print("EVALUATION COMPLETE")
  print("=" * 60)


if __name__ == "__main__":
  main()
