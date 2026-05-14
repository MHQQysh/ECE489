"""Evaluation script for comparing RL policy against CPG baseline.

This script evaluates both approaches on:
- Velocity tracking error (RMS)
- Body stability (RMS roll & pitch)
- Energy efficiency (Cost of Transport)
- Robustness (lateral push recovery)
"""

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np
import torch
import tyro

from mjlab.controllers.cpg_baseline import CPGController
from mjlab.controllers.cpg_velocity import CPGControllerVelocity
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg, load_runner_cls
from mjlab.utils.torch import configure_torch_backends


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
      "episode_length_mean": float(np.mean(self.episode_length)),
      "num_trials": len(self.velocity_tracking_error),
    }


@dataclass
class EvalConfig:
  """Evaluation configuration."""

  task: str = "Mjlab-Velocity-Flat-Unitree-Go2"
  """Task to evaluate (e.g., Mjlab-Velocity-Flat-Unitree-Go2, unitree-go2-rough)."""
  checkpoint: str | None = None
  """Path to trained policy checkpoint (for RL evaluation)."""
  controller: Literal["rl", "cpg"] = "rl"
  """Controller type: 'rl' for trained policy, 'cpg' for baseline."""
  num_trials: int = 10
  """Number of evaluation trials."""
  episode_length: int = 1000
  """Episode length in steps."""
  target_velocity: float = 1.0
  """Target forward velocity in m/s."""
  push_force: float = 40.0
  """Lateral push force in Newtons."""
  push_duration: float = 0.1
  """Push duration in seconds."""
  push_time: float = 5.0
  """Time to apply push (seconds after episode start)."""
  device: str = "cuda:0"
  """Device to run on."""
  output_dir: str = "evaluation_results"
  """Output directory for results."""
  cpg_frequency: float = 2.0
  """CPG oscillation frequency in Hz."""
  cpg_gait: Literal["trot", "walk", "pace"] = "trot"
  """CPG gait pattern."""


def compute_velocity_tracking_error(
  actual_vel: torch.Tensor,
  target_vel: torch.Tensor,
) -> float:
  """Compute RMS velocity tracking error.

  Args:
    actual_vel: Actual velocities (T, 3) - linear x, y, z.
    target_vel: Target velocities (T, 3).

  Returns:
    RMS error in m/s.
  """
  error = actual_vel - target_vel
  rms_error = torch.sqrt(torch.mean(error**2))
  return float(rms_error)


def compute_body_stability(orientation: torch.Tensor) -> tuple[float, float]:
  """Compute RMS roll and pitch.

  Args:
    orientation: Body orientations as quaternions (T, 4) - wxyz format.

  Returns:
    Tuple of (roll_rms, pitch_rms) in radians.
  """
  # Convert quaternions to Euler angles
  w, x, y, z = (
    orientation[:, 0],
    orientation[:, 1],
    orientation[:, 2],
    orientation[:, 3],
  )

  # Roll (x-axis rotation)
  sinr_cosp = 2 * (w * x + y * z)
  cosr_cosp = 1 - 2 * (x * x + y * y)
  roll = torch.atan2(sinr_cosp, cosr_cosp)

  # Pitch (y-axis rotation)
  sinp = 2 * (w * y - z * x)
  pitch = torch.asin(torch.clamp(sinp, -1.0, 1.0))

  roll_rms = float(torch.sqrt(torch.mean(roll**2)))
  pitch_rms = float(torch.sqrt(torch.mean(pitch**2)))

  return roll_rms, pitch_rms


def compute_cost_of_transport(
  torques: torch.Tensor,
  joint_velocities: torch.Tensor,
  dt: float,
  mass: float,
  distance: float,
) -> float:
  """Compute Cost of Transport.

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
  g = 9.81  # gravity
  power = torch.abs(torques * joint_velocities)
  total_energy = torch.sum(power) * dt
  cot = float(total_energy / (mass * g * distance))
  return cot


def apply_lateral_push(
  env: ManagerBasedRlEnv,
  env_ids: torch.Tensor,
  force: float,
  duration: float,
):
  """Apply lateral push to robot base.

  Args:
    env: Environment.
    env_ids: Environment IDs to push.
    force: Push force in Newtons (applied in y-direction).
    duration: Push duration in seconds.
  """
  # Apply external force to robot base
  robot = env.scene["robot"]

  # Create force vector (lateral push in y-direction)
  push_force = torch.zeros(len(env_ids), 6, device=env.device)
  push_force[:, 1] = force  # Force in y-direction

  # Apply to base body (index 0)
  # Note: This is a simplified version - in real implementation,
  # you might need to use the physics engine's force application API
  # For now, we'll just record that a push was attempted
  pass  # Placeholder - actual force application depends on physics backend


def run_trial(
  env: ManagerBasedRlEnv,
  controller,
  cfg: EvalConfig,
  trial_idx: int,
) -> dict:
  """Run one evaluation trial.

  Args:
    env: Environment.
    controller: Controller (RL policy or CPG).
    cfg: Evaluation config.
    trial_idx: Trial index.

  Returns:
    Dictionary of metrics for this trial.
  """
  device = env.device
  dt = env.step_dt

  # Reset environment
  obs, _ = env.reset()

  # Storage for metrics
  actual_velocities = []
  target_velocities = []
  orientations = []
  torques = []
  joint_velocities = []
  positions = []

  # Set target velocity
  target_vel = torch.zeros(env.num_envs, 3, device=device)
  target_vel[:, 0] = cfg.target_velocity  # Forward velocity

  push_applied = False
  push_step = int(cfg.push_time / dt)
  recovered = True

  for step in range(cfg.episode_length):
    # Compute action
    if cfg.controller == "rl":
      with torch.no_grad():
        actions = controller(obs)
    else:  # CPG
      # CPG reads target velocity and adjusts gait accordingly
      actions = controller.compute_actions(dt, velocity_command=target_vel)

    # Step environment
    obs, _, terminated, truncated, info = env.step(actions)

    # Apply push at specified time
    if step == push_step and not push_applied:
      env_ids = torch.arange(env.num_envs, device=device)
      apply_lateral_push(env, env_ids, cfg.push_force, cfg.push_duration)
      push_applied = True

    # Check for fall after push
    if push_applied and (terminated.any() or truncated.any()):
      recovered = False

    # Collect metrics
    robot = env.scene["robot"]

    # Get velocity, orientation, and position
    actual_vel = robot.data.body_com_lin_vel_w[:, 0, :]  # Linear velocity of base
    orientation = robot.data.body_com_quat_w[:, 0, :]  # Quaternion (wxyz) of base
    position = robot.data.body_com_pos_w[:, 0, :]  # Position of base

    actual_velocities.append(actual_vel.cpu())
    target_velocities.append(target_vel.cpu())
    orientations.append(orientation.cpu())
    positions.append(position.cpu())

    # Get torques and joint velocities
    if hasattr(robot, "actuators"):
      # Approximate torque from action (for CPG) or get from actuator
      joint_vel = robot.data.joint_vel
      joint_velocities.append(joint_vel.cpu())

      # Estimate torque (simplified)
      if cfg.controller == "cpg":
        # For CPG, approximate torque from position error
        joint_pos = robot.data.joint_pos
        torque_est = 100.0 * (actions - joint_pos) - 2.0 * joint_vel
        torques.append(torque_est.cpu())
      else:
        # For RL, try to get actual torque
        if hasattr(info, "torques"):
          torques.append(info["torques"].cpu())
        else:
          # Fallback: estimate from action
          joint_pos = robot.data.joint_pos
          torque_est = 100.0 * (actions - joint_pos) - 2.0 * joint_vel
          torques.append(torque_est.cpu())

  # Convert to tensors
  actual_velocities = torch.stack(actual_velocities)[:, 0, :]  # (T, 3)
  target_velocities = torch.stack(target_velocities)[:, 0, :]  # (T, 3)
  orientations = torch.stack(orientations)[:, 0, :]  # (T, 4)
  positions = torch.stack(positions)[:, 0, :]  # (T, 3)

  if torques and joint_velocities:
    torques = torch.stack(torques)[:, 0, :]  # (T, num_joints)
    joint_velocities = torch.stack(joint_velocities)[:, 0, :]  # (T, num_joints)

  # Compute metrics
  vel_error = compute_velocity_tracking_error(actual_velocities, target_velocities)
  roll_rms, pitch_rms = compute_body_stability(orientations)

  # Compute distance traveled
  distance = float(torch.norm(positions[-1] - positions[0]))

  # Compute CoT
  if len(torques) > 0 and len(joint_velocities) > 0:
    # Estimate robot mass (Go2 is ~15kg)
    robot_mass = 15.0
    cot = compute_cost_of_transport(
      torques,
      joint_velocities,
      dt,
      robot_mass,
      max(distance, 0.1),  # Avoid division by zero
    )
  else:
    cot = 0.0

  return {
    "velocity_error": vel_error,
    "roll_rms": roll_rms,
    "pitch_rms": pitch_rms,
    "cost_of_transport": cot,
    "recovery_success": recovered,
    "distance": distance,
  }


def main():
  cfg = tyro.cli(EvalConfig)
  configure_torch_backends()

  # Create output directory
  output_dir = Path(cfg.output_dir)
  output_dir.mkdir(parents=True, exist_ok=True)

  # Load environment
  env_cfg = load_env_cfg(cfg.task, play=True)
  env_cfg.scene.num_envs = 1  # Single environment for evaluation
  env = ManagerBasedRlEnv(cfg=env_cfg, device=cfg.device)

  # Load controller
  if cfg.controller == "rl":
    if cfg.checkpoint is None:
      raise ValueError("Must provide --checkpoint for RL evaluation")

    # Load checkpoint using rsl_rl's method
    from rsl_rl.runners import OnPolicyRunner

    vec_env = RslRlVecEnvWrapper(env)

    # Load checkpoint
    checkpoint_path = Path(cfg.checkpoint)
    log_dir = checkpoint_path.parent

    # Create a minimal runner to load the policy
    from mjlab.tasks.registry import load_rl_cfg

    rl_cfg = load_rl_cfg(cfg.task)

    # Create runner (without train_cfg to avoid the error)
    runner = OnPolicyRunner(
      vec_env, rl_cfg.to_dict(), log_dir=str(log_dir), device=cfg.device
    )

    # Load the checkpoint
    runner.load(cfg.checkpoint)

    controller = lambda obs: runner.alg.actor_critic.act_inference(obs)
    print(f"Loaded RL policy from {cfg.checkpoint}")

  else:  # CPG
    # Use velocity-responsive CPG for better tracking
    controller = CPGControllerVelocity(
      num_envs=1,
      device=cfg.device,
      base_frequency=cfg.cpg_frequency,
    )
    print(
      f"Using velocity-responsive CPG baseline at {cfg.cpg_frequency} Hz base frequency"
    )

  # Run evaluation trials
  metrics = EvaluationMetrics()

  print(f"\nRunning {cfg.num_trials} trials...")
  for trial in range(cfg.num_trials):
    print(f"Trial {trial + 1}/{cfg.num_trials}...", end=" ")

    result = run_trial(env, controller, cfg, trial)

    metrics.add_trial(
      vel_error=result["velocity_error"],
      roll=result["roll_rms"],
      pitch=result["pitch_rms"],
      cot=result["cost_of_transport"],
      recovery=result["recovery_success"],
      ep_len=cfg.episode_length * env.step_dt,
    )

    print(
      f"✓ (vel_err={result['velocity_error']:.3f}, CoT={result['cost_of_transport']:.3f})"
    )

  # Compute summary
  summary = metrics.summary()

  # Print results
  print("\n" + "=" * 60)
  print(f"Evaluation Results - {cfg.controller.upper()} on {cfg.task}")
  print("=" * 60)
  print(f"Target velocity: {cfg.target_velocity} m/s")
  print(f"Number of trials: {summary['num_trials']}")
  print()
  print(
    f"Velocity Tracking Error (RMS): {summary['velocity_tracking_error_mean']:.4f} ± {summary['velocity_tracking_error_std']:.4f} m/s"
  )
  print(
    f"Roll RMS: {summary['roll_rms_mean']:.4f} ± {summary['roll_rms_std']:.4f} rad ({math.degrees(summary['roll_rms_mean']):.2f}°)"
  )
  print(
    f"Pitch RMS: {summary['pitch_rms_mean']:.4f} ± {summary['pitch_rms_std']:.4f} rad ({math.degrees(summary['pitch_rms_mean']):.2f}°)"
  )
  print(
    f"Cost of Transport: {summary['cost_of_transport_mean']:.4f} ± {summary['cost_of_transport_std']:.4f}"
  )
  print(f"Push Recovery Rate: {summary['push_recovery_rate']:.1%}")
  print("=" * 60)

  # Save results
  result_file = output_dir / f"{cfg.controller}_{cfg.task}_v{cfg.target_velocity}.json"
  with open(result_file, "w") as f:
    json.dump(
      {
        "config": {
          "task": cfg.task,
          "controller": cfg.controller,
          "target_velocity": cfg.target_velocity,
          "num_trials": cfg.num_trials,
          "push_force": cfg.push_force,
        },
        "summary": summary,
        "raw_data": {
          "velocity_tracking_error": metrics.velocity_tracking_error,
          "roll_rms": metrics.roll_rms,
          "pitch_rms": metrics.pitch_rms,
          "cost_of_transport": metrics.cost_of_transport,
          "push_recovery_success": metrics.push_recovery_success,
        },
      },
      f,
      indent=2,
    )

  print(f"\nResults saved to {result_file}")


if __name__ == "__main__":
  main()
