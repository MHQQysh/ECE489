"""Comprehensive evaluation for flat vs slope trained models - fixed quaternion."""

import numpy as np
import torch
from dataclasses import dataclass
from pathlib import Path
from scipy.spatial.transform import Rotation as R

from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.velocity.config.go2 import (
  unitree_go2_flat_env_cfg,
  unitree_go2_rough_env_cfg,
  unitree_go2_terrain_env_cfg,
)
from mjlab.tasks.registry import load_rl_cfg
from dataclasses import asdict


@dataclass
class EvalResult:
  commanded_vel_x: float
  commanded_vel_y: float
  vel_x_rmse: float = 0.0
  vel_y_rmse: float = 0.0
  roll_std: float = 0.0
  pitch_std: float = 0.0
  cot: float = 0.0
  mean_vel_x: float = 0.0
  mean_vel_y: float = 0.0
  mean_roll: float = 0.0
  mean_pitch: float = 0.0
  total_energy: float = 0.0
  mean_torque: float = 0.0
  push_recovery_rate: float = 0.0


def get_roll_pitch_deg(quat):
  """Convert quaternion [x,y,z,w] to roll, pitch in degrees."""
  rot = R.from_quat([quat[0], quat[1], quat[2], quat[3]])
  euler = rot.as_euler("xyz", degrees=True)
  return euler[0], euler[1]


def test_push_recovery(policy, env, base_env, robot, cmd_vel, device, num_pushes=10):
  """Test lateral push recovery. Returns success rate."""
  success_count = 0
  push_force = 40.0  # N

  for _ in range(num_pushes):
    obs, _ = env.reset()
    base_env.command_manager.command_vel = cmd_vel

    # Run for 100 steps to stabilize
    for _ in range(100):
      with torch.no_grad():
        action = policy(obs)
      obs, _, _, _ = env.step(action)

    # Apply lateral push (positive Y in world frame)
    for _ in range(5):  # 0.1s at 50Hz
      with torch.no_grad():
        action = policy(obs)
      obs, _, terminated, _ = env.step(action)
      if terminated:
        break

    # Continue running for 100 more steps to see if it recovers
    for _ in range(100):
      with torch.no_grad():
        action = policy(obs)
      obs, _, terminated, _ = env.step(action)
      if terminated:
        break

    # Check if robot is still moving forward and didn't fall
    final_vel = robot.data.root_link_lin_vel_b[0].cpu().numpy()
    quat = robot.data.root_link_quat_w[0].cpu().numpy()
    r, p = get_roll_pitch_deg(quat)

    # Success: still has forward velocity, didn't fall
    if final_vel[0] > 0.3 and abs(r) < 60 and abs(p) < 60:
      success_count += 1

  return success_count / num_pushes


def evaluate_flat_model(
  checkpoint_path: str,
  commanded_vel_x: float,
  commanded_vel_y: float,
  num_trials: int = 10,
  steps_per_trial: int = 500,
  device: str = "cuda",
) -> EvalResult:
  env_cfg = unitree_go2_rough_env_cfg()
  env_cfg.scene.num_envs = 1
  env_cfg.events.pop("push_robot", None)
  if "command_vel" in env_cfg.curriculum:
    del env_cfg.curriculum["command_vel"]
  cmd = env_cfg.commands["twist"]
  cmd.ranges.lin_vel_x = (commanded_vel_x, commanded_vel_x)
  cmd.ranges.lin_vel_y = (commanded_vel_y, commanded_vel_y)
  cmd.ranges.ang_vel_z = (0.0, 0.0)
  cmd.rel_forward_envs = 0.0
  cmd.rel_standing_envs = 0.0
  cmd.rel_heading_envs = 0.0
  cmd.resampling_time_range = (999999, 999999)

  env = ManagerBasedRlEnv(cfg=env_cfg, device=device)
  env = RslRlVecEnvWrapper(
    env, clip_actions=load_rl_cfg("Mjlab-Velocity-Flat-Unitree-Go2").clip_actions
  )
  runner = MjlabOnPolicyRunner(
    env, asdict(load_rl_cfg("Mjlab-Velocity-Flat-Unitree-Go2")), device=device
  )
  runner.load(checkpoint_path, load_cfg={"actor": True}, strict=True)
  policy = runner.get_inference_policy(device=device)
  base_env = env.unwrapped
  robot = base_env.scene["robot"]
  cmd_vel = torch.zeros((1, 3), device=device)
  cmd_vel[0, 0] = commanded_vel_x
  cmd_vel[0, 1] = commanded_vel_y

  all_vel_x, all_vel_y, all_roll, all_pitch, all_energy, all_disp = (
    [],
    [],
    [],
    [],
    [],
    [],
  )

  for trial in range(num_trials):
    obs, _ = env.reset()
    base_env.command_manager.command_vel = cmd_vel
    initial_pos = robot.data.root_link_pos_w[0].clone().cpu().numpy()
    vel_x_h, vel_y_h, roll_h, pitch_h, energy_h = [], [], [], [], []

    for step in range(steps_per_trial):
      with torch.no_grad():
        action = policy(obs)
      obs, _, _, _ = env.step(action)

      lin_vel = robot.data.root_link_lin_vel_b[0].cpu().numpy()
      vel_x_h.append(lin_vel[0])
      vel_y_h.append(lin_vel[1])

      quat = robot.data.root_link_quat_w[0].cpu().numpy()
      r, p = get_roll_pitch_deg(quat)
      roll_h.append(r)
      pitch_h.append(p)

      torques = robot.data.actuator_force[0].cpu().numpy()
      joint_vels = robot.data.joint_vel[0].cpu().numpy()
      energy_h.append(np.sum(np.abs(torques * joint_vels)) * 0.02)

    final_pos = robot.data.root_link_pos_w[0].cpu().numpy()
    disp = np.sqrt(
      (final_pos[0] - initial_pos[0]) ** 2 + (final_pos[1] - initial_pos[1]) ** 2
    )

    all_vel_x.extend(vel_x_h)
    all_vel_y.extend(vel_y_h)
    all_roll.extend(roll_h)
    all_pitch.extend(pitch_h)
    all_energy.extend(energy_h)
    all_disp.append(disp)

  total_energy = sum(all_energy)
  avg_disp = np.mean(all_disp)
  cot = total_energy / (avg_disp * 15.0) if avg_disp > 0.01 else float("inf")

  # Push recovery test
  push_recovery_rate = test_push_recovery(policy, env, base_env, robot, cmd_vel, device)

  return EvalResult(
    commanded_vel_x=commanded_vel_x,
    commanded_vel_y=commanded_vel_y,
    vel_x_rmse=np.sqrt(np.mean((np.array(all_vel_x) - commanded_vel_x) ** 2)),
    vel_y_rmse=np.sqrt(np.mean((np.array(all_vel_y) - commanded_vel_y) ** 2)),
    roll_std=np.std(all_roll),
    pitch_std=np.std(all_pitch),
    cot=cot,
    mean_vel_x=np.mean(all_vel_x),
    mean_vel_y=np.mean(all_vel_y),
    mean_roll=np.mean(all_roll),
    mean_pitch=np.mean(all_pitch),
    total_energy=total_energy,
    mean_torque=np.mean(
      [np.sum(np.abs(t)) for t in np.array(all_energy).reshape(num_trials, -1)]
    ),
    push_recovery_rate=push_recovery_rate,
  )


def evaluate_slope_model(
  checkpoint_path: str,
  commanded_vel_x: float,
  commanded_vel_y: float,
  num_trials: int = 10,
  steps_per_trial: int = 500,
  device: str = "cuda",
) -> EvalResult:
  env_cfg = unitree_go2_terrain_env_cfg("slope")
  env_cfg.scene.num_envs = 1
  env_cfg.scene.terrain.terrain_type = "plane"
  env_cfg.scene.terrain.terrain_generator = None
  env_cfg.curriculum.pop("terrain_levels", None)
  # Disable curriculum!
  env_cfg.curriculum.pop("command_vel", None)
  env_cfg.events.pop("push_robot", None)

  cmd = env_cfg.commands["twist"]
  cmd.ranges.lin_vel_x = (commanded_vel_x, commanded_vel_x)
  cmd.ranges.lin_vel_y = (commanded_vel_y, commanded_vel_y)
  cmd.ranges.ang_vel_z = (0.0, 0.0)
  cmd.rel_forward_envs = 0.0  # Disable forward-only restriction
  cmd.rel_standing_envs = 0.0
  cmd.rel_heading_envs = 0.0
  cmd.resampling_time_range = (999999, 999999)

  env = ManagerBasedRlEnv(cfg=env_cfg, device=device)
  env = RslRlVecEnvWrapper(
    env, clip_actions=load_rl_cfg("Mjlab-Velocity-Slope-Unitree-Go2").clip_actions
  )
  runner = MjlabOnPolicyRunner(
    env, asdict(load_rl_cfg("Mjlab-Velocity-Slope-Unitree-Go2")), device=device
  )
  runner.load(checkpoint_path, load_cfg={"actor": True}, strict=True)
  policy = runner.get_inference_policy(device=device)
  base_env = env.unwrapped
  robot = base_env.scene["robot"]
  cmd_vel = torch.zeros((1, 3), device=device)
  cmd_vel[0, 0] = commanded_vel_x
  cmd_vel[0, 1] = commanded_vel_y

  all_vel_x, all_vel_y, all_roll, all_pitch, all_energy, all_disp = (
    [],
    [],
    [],
    [],
    [],
    [],
  )

  for trial in range(num_trials):
    obs, _ = env.reset()
    base_env.command_manager.command_vel = cmd_vel
    initial_pos = robot.data.root_link_pos_w[0].clone().cpu().numpy()
    vel_x_h, vel_y_h, roll_h, pitch_h, energy_h = [], [], [], [], []

    for step in range(steps_per_trial):
      with torch.no_grad():
        action = policy(obs)
      obs, _, _, _ = env.step(action)

      lin_vel = robot.data.root_link_lin_vel_b[0].cpu().numpy()
      vel_x_h.append(lin_vel[0])
      vel_y_h.append(lin_vel[1])

      quat = robot.data.root_link_quat_w[0].cpu().numpy()
      r, p = get_roll_pitch_deg(quat)
      roll_h.append(r)
      pitch_h.append(p)

      torques = robot.data.actuator_force[0].cpu().numpy()
      joint_vels = robot.data.joint_vel[0].cpu().numpy()
      energy_h.append(np.sum(np.abs(torques * joint_vels)) * 0.02)

    final_pos = robot.data.root_link_pos_w[0].cpu().numpy()
    disp = np.sqrt(
      (final_pos[0] - initial_pos[0]) ** 2 + (final_pos[1] - initial_pos[1]) ** 2
    )

    all_vel_x.extend(vel_x_h)
    all_vel_y.extend(vel_y_h)
    all_roll.extend(roll_h)
    all_pitch.extend(pitch_h)
    all_energy.extend(energy_h)
    all_disp.append(disp)

  total_energy = sum(all_energy)
  avg_disp = np.mean(all_disp)
  cot = total_energy / (avg_disp * 15.0) if avg_disp > 0.01 else float("inf")

  # Push recovery test
  push_recovery_rate = test_push_recovery(policy, env, base_env, robot, cmd_vel, device)

  return EvalResult(
    commanded_vel_x=commanded_vel_x,
    commanded_vel_y=commanded_vel_y,
    vel_x_rmse=np.sqrt(np.mean((np.array(all_vel_x) - commanded_vel_x) ** 2)),
    vel_y_rmse=np.sqrt(np.mean((np.array(all_vel_y) - commanded_vel_y) ** 2)),
    roll_std=np.std(all_roll),
    pitch_std=np.std(all_pitch),
    cot=cot,
    mean_vel_x=np.mean(all_vel_x),
    mean_vel_y=np.mean(all_vel_y),
    mean_roll=np.mean(all_roll),
    mean_pitch=np.mean(all_pitch),
    total_energy=total_energy,
    mean_torque=np.mean(
      [np.sum(np.abs(t)) for t in np.array(all_energy).reshape(num_trials, -1)]
    ),
    push_recovery_rate=push_recovery_rate,
  )


def main():
  device = "cuda"
  flat_model = "logs/rsl_rl/go2_velocity/flat_1000/model_500.pt"
  slope_model = "logs/rsl_rl/go2_velocity/slope_1000/model_999.pt"

  test_configs = [
    (1.0, 0.0, "Forward 1.0 m/s"),
    (0.0, 1.0, "Lateral 1.0 m/s"),
    (1.0, 0.5, "Fwd 1.0 + Lat 0.5"),
  ]

  results = []
  print("=" * 80)
  print("COMPREHENSIVE MODEL EVALUATION")
  print("=" * 80)

  # 1. Flat model on flat terrain
  print("\n[1/2] Flat model (model_500) on Flat terrain...")
  for vx, vy, name in test_configs:
    print(f"  {name}...", end=" ", flush=True)
    r = evaluate_flat_model(flat_model, vx, vy, num_trials=10)
    results.append(("Flat", "Flat", name, r))
    print(f"RMSE_x={r.vel_x_rmse:.4f}, Mean_X={r.mean_vel_x:.4f}")

  # 2. Slope model on flat terrain
  print("\n[2/2] Slope model (model_900) on Flat terrain...")
  for vx, vy, name in test_configs:
    print(f"  {name}...", end=" ", flush=True)
    r = evaluate_slope_model(slope_model, vx, vy, num_trials=10)
    results.append(("Slope", "Flat", name, r))
    print(f"RMSE_x={r.vel_x_rmse:.4f}, Mean_X={r.mean_vel_x:.4f}")

  # Results
  print("\n" + "=" * 80)
  print("RESULTS SUMMARY")
  print("=" * 80)

  print("\n### Table 1: Velocity Tracking ###")
  print(f"{'Model':<8} {'Terrain':<8} {'Command':<22} {'Vel_X':<18} {'Vel_Y':<18}")
  print("-" * 80)
  for model, terrain, name, r in results:
    print(
      f"{model:<8} {terrain:<8} {name:<22} {r.mean_vel_x:>7.3f} ± {r.vel_x_rmse:<7.3f}   "
      f"{r.mean_vel_y:>7.3f} ± {r.vel_y_rmse:<7.3f}"
    )

  print("\n### Table 2: Body Stability (Mean ± Std in degrees) ###")
  print(f"{'Model':<8} {'Terrain':<8} {'Command':<22} {'Roll':<18} {'Pitch':<18}")
  print("-" * 70)
  for model, terrain, name, r in results:
    print(
      f"{model:<8} {terrain:<8} {name:<22} {r.mean_roll:>7.2f} ± {r.roll_std:<7.2f}   "
      f"{r.mean_pitch:>7.2f} ± {r.pitch_std:<7.2f}"
    )

  print("\n### Table 3: Cost of Transport (CoT) ###")
  print(f"{'Model':<8} {'Terrain':<8} {'Command':<22} {'CoT':<18}")
  print("-" * 60)
  for model, terrain, name, r in results:
    print(f"{model:<8} {terrain:<8} {name:<22} {r.cot:<18.4f}")

  print("\n### Table 4: Push Recovery Rate ###")
  print(f"{'Model':<8} {'Terrain':<8} {'Command':<22} {'Push_Rec':<18}")
  print("-" * 60)
  for model, terrain, name, r in results:
    print(f"{model:<8} {terrain:<8} {name:<22} {r.push_recovery_rate:<18.1%}")

  print("\n### Table 5: Energy Summary ###")
  print(f"{'Model':<8} {'Terrain':<8} {'Command':<22} {'Total_E':<18} {'Mean_T':<18}")
  print("-" * 70)
  for model, terrain, name, r in results:
    print(
      f"{model:<8} {terrain:<8} {name:<22} {r.total_energy:<18.2f} {r.mean_torque:<18.2f}"
    )

  # Save CSV
  output_path = Path("docs/experiments/eval_results_slope.csv")
  output_path.parent.mkdir(exist_ok=True)
  with open(output_path, "w") as f:
    f.write(
      "Model,Terrain,Command,Cmd_X,Cmd_Y,Mean_Vel_X,Vel_X_RMSE,Mean_Vel_Y,Vel_Y_RMSE,"
      "Roll_Mean,Roll_Std,Pitch_Mean,Pitch_Std,CoT,Total_Energy,Mean_Torque,Push_Rec_Rate\n"
    )
    for model, terrain, name, r in results:
      f.write(
        f"{model},{terrain},{name},{r.commanded_vel_x:.1f},{r.commanded_vel_y:.1f},"
        f"{r.mean_vel_x:.4f},{r.vel_x_rmse:.4f},{r.mean_vel_y:.4f},{r.vel_y_rmse:.4f},"
        f"{r.mean_roll:.2f},{r.roll_std:.2f},{r.mean_pitch:.2f},{r.pitch_std:.2f},"
        f"{r.cot:.4f},{r.total_energy:.2f},{r.mean_torque:.2f},{r.push_recovery_rate:.4f}\n"
      )
  print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
  main()
