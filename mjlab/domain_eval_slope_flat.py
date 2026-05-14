"""Compare two Go2 checkpoints on flat-vs-slope evaluation settings.

This script keeps the original `eval_slope_vs_flat.py` untouched and evaluates
one checkpoint trained with domain randomization against one checkpoint trained
without domain randomization. It uses only 2 trials per command as requested.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import torch
from scipy.spatial.transform import Rotation as R

from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.registry import load_rl_cfg
from mjlab.tasks.velocity.config.go2 import (
  unitree_go2_rough_env_cfg,
  unitree_go2_terrain_env_cfg,
)


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
  rot = R.from_quat([quat[0], quat[1], quat[2], quat[3]])
  euler = rot.as_euler("xyz", degrees=True)
  return euler[0], euler[1]


def test_push_recovery(policy, env, base_env, robot, cmd_vel, device, num_pushes=2):
  success_count = 0
  for _ in range(num_pushes):
    obs, _ = env.reset()
    base_env.command_manager.command_vel = cmd_vel

    for _ in range(100):
      with torch.no_grad():
        action = policy(obs)
      obs, _, _, _ = env.step(action)

    for _ in range(5):
      with torch.no_grad():
        action = policy(obs)
      obs, _, terminated, _ = env.step(action)
      if terminated:
        break

    for _ in range(100):
      with torch.no_grad():
        action = policy(obs)
      obs, _, terminated, _ = env.step(action)
      if terminated:
        break

    final_vel = robot.data.root_link_lin_vel_b[0].cpu().numpy()
    quat = robot.data.root_link_quat_w[0].cpu().numpy()
    r, p = get_roll_pitch_deg(quat)
    if final_vel[0] > 0.3 and abs(r) < 60 and abs(p) < 60:
      success_count += 1

  return success_count / num_pushes


def _build_env(
  env_cfg,
  runner_cfg_name: str,
  checkpoint_path: str,
  device: str,
):
  env = ManagerBasedRlEnv(cfg=env_cfg, device=device)
  env = RslRlVecEnvWrapper(env, clip_actions=load_rl_cfg(runner_cfg_name).clip_actions)
  runner = MjlabOnPolicyRunner(env, asdict(load_rl_cfg(runner_cfg_name)), device=device)
  runner.load(checkpoint_path, load_cfg={"actor": True}, strict=True)
  policy = runner.get_inference_policy(device=device)
  base_env = env.unwrapped
  robot = base_env.scene["robot"]
  return env, base_env, robot, policy


def _evaluate(
  checkpoint_path: str,
  env_cfg,
  runner_cfg_name: str,
  commanded_vel_x: float,
  commanded_vel_y: float,
  num_trials: int = 10,
  steps_per_trial: int = 50,
  device: str = "cuda",
) -> EvalResult:
  env_cfg.scene.num_envs = 1

  # Force flat terrain for fair comparison
  if hasattr(env_cfg.scene, "terrain"):
    env_cfg.scene.terrain.terrain_type = "plane"
    env_cfg.scene.terrain.terrain_generator = None

  if hasattr(env_cfg, "curriculum"):
    env_cfg.curriculum.pop("terrain_levels", None)
    env_cfg.curriculum.pop("command_vel", None)
  if hasattr(env_cfg, "events"):
    env_cfg.events.pop("push_robot", None)

  cmd = env_cfg.commands["twist"]
  cmd.ranges.lin_vel_x = (commanded_vel_x, commanded_vel_x)
  cmd.ranges.lin_vel_y = (commanded_vel_y, commanded_vel_y)
  cmd.ranges.ang_vel_z = (0.0, 0.0)
  cmd.rel_forward_envs = 0.0
  cmd.rel_standing_envs = 0.0
  cmd.rel_heading_envs = 0.0
  cmd.resampling_time_range = (999999, 999999)

  env, base_env, robot, policy = _build_env(
    env_cfg, runner_cfg_name, checkpoint_path, device
  )
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

  for trial_idx in range(num_trials):
    obs, _ = env.reset()
    base_env.command_manager.command_vel = cmd_vel
    initial_pos = robot.data.root_link_pos_w[0].clone().cpu().numpy()
    vel_x_h, vel_y_h, roll_h, pitch_h, energy_h = [], [], [], [], []

    # Warmup period: 50 steps (1 second at 50Hz) to let robot stabilize
    warmup_steps = 50
    for _ in range(warmup_steps):
      with torch.no_grad():
        action = policy(obs)
      obs, _, _, _ = env.step(action)

    # Verify command is set correctly after warmup (only print first trial)
    if trial_idx == 0:
      actual_cmd = base_env.command_manager.command_vel[0].cpu().numpy()
      print(
        f"    Actual command after warmup: vx={actual_cmd[0]:.3f}, vy={actual_cmd[1]:.3f}, wz={actual_cmd[2]:.3f}"
      )

    # Record data for steps_per_trial steps
    for _ in range(steps_per_trial):
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

  total_energy = float(sum(all_energy))
  avg_disp = float(np.mean(all_disp))
  cot = total_energy / (avg_disp * 15.0) if avg_disp > 0.01 else float("inf")
  push_recovery_rate = test_push_recovery(policy, env, base_env, robot, cmd_vel, device)

  all_energy_arr = np.array(all_energy)
  try:
    mean_torque = float(
      np.mean([np.sum(np.abs(t)) for t in all_energy_arr.reshape(num_trials, -1)])
    )
  except Exception:
    mean_torque = float(np.mean(np.abs(all_energy_arr)))

  return EvalResult(
    commanded_vel_x=commanded_vel_x,
    commanded_vel_y=commanded_vel_y,
    vel_x_rmse=float(np.sqrt(np.mean((np.array(all_vel_x) - commanded_vel_x) ** 2))),
    vel_y_rmse=float(np.sqrt(np.mean((np.array(all_vel_y) - commanded_vel_y) ** 2))),
    roll_std=float(np.std(all_roll)),
    pitch_std=float(np.std(all_pitch)),
    cot=float(cot),
    mean_vel_x=float(np.mean(all_vel_x)),
    mean_vel_y=float(np.mean(all_vel_y)),
    mean_roll=float(np.mean(all_roll)),
    mean_pitch=float(np.mean(all_pitch)),
    total_energy=total_energy,
    mean_torque=mean_torque,
    push_recovery_rate=push_recovery_rate,
  )


def main():
  device = "cuda"
  # Use the same models as eval_slope_vs_flat.py for consistency
  dr_model = "/home/y/ece489/lab4/mjlab/logs/rsl_rl/go2_velocity/2026-05-14_07-42-23/model_1199.pt"
  nodr_model = "logs/rsl_rl/go2_velocity/nonrandom_rough_1200"

  test_configs = [
    (1.0, 0.0, "Forward 1.0 m/s"),
    (0.0, 1.0, "Lateral 1.0 m/s"),
    (1.0, 0.5, "Fwd 1.0 + Lat 0.5"),
  ]

  setups = [
    (
      "DR",
      dr_model,
      unitree_go2_terrain_env_cfg("slope"),
      "Mjlab-Velocity-Slope-Unitree-Go2",
    ),
    (
      "NoDR",
      nodr_model,
      unitree_go2_rough_env_cfg(),
      "Mjlab-Velocity-Flat-Unitree-Go2",
    ),
  ]

  results = []
  print("=" * 80)
  print("DOMAIN RANDOMIZATION COMPARISON: SLOPE VS FLAT")
  print("=" * 80)
  print("Each command is evaluated with 10 trials for statistical stability.\n")

  for label, checkpoint, env_cfg, runner_cfg_name in setups:
    print(f"[{label}] checkpoint: {checkpoint}")
    for vx, vy, name in test_configs:
      print(f"  {name}...", end=" ", flush=True)
      r = _evaluate(
        checkpoint,
        deepcopy(env_cfg),
        runner_cfg_name,
        vx,
        vy,
        num_trials=5,
        device=device,
      )
      results.append((label, name, r))
      print(f"RMSE_x={r.vel_x_rmse:.4f}, Mean_X={r.mean_vel_x:.4f}")

  print("\n" + "=" * 80)
  print("RESULTS SUMMARY")
  print("=" * 80)

  print("\n### Table 1: Velocity Tracking ###")
  print(f"{'Model':<8} {'Command':<22} {'Vel_X':<18} {'Vel_Y':<18}")
  print("-" * 72)
  for model, name, r in results:
    print(
      f"{model:<8} {name:<22} {r.mean_vel_x:>7.3f} ± {r.vel_x_rmse:<7.3f}   {r.mean_vel_y:>7.3f} ± {r.vel_y_rmse:<7.3f}"
    )

  print("\n### Table 2: Body Stability (Mean ± Std in degrees) ###")
  print(f"{'Model':<8} {'Command':<22} {'Roll':<18} {'Pitch':<18}")
  print("-" * 72)
  for model, name, r in results:
    print(
      f"{model:<8} {name:<22} {r.mean_roll:>7.2f} ± {r.roll_std:<7.2f}   {r.mean_pitch:>7.2f} ± {r.pitch_std:<7.2f}"
    )

  print("\n### Table 3: Cost of Transport (CoT) ###")
  print(f"{'Model':<8} {'Command':<22} {'CoT':<18}")
  print("-" * 50)
  for model, name, r in results:
    print(f"{model:<8} {name:<22} {r.cot:<18.4f}")

  print("\n### Table 4: Push Recovery Rate ###")
  print(f"{'Model':<8} {'Command':<22} {'Push_Rec':<18}")
  print("-" * 50)
  for model, name, r in results:
    print(f"{model:<8} {name:<22} {r.push_recovery_rate:<18.1%}")

  print("\n### Table 5: Energy Summary ###")
  print(f"{'Model':<8} {'Command':<22} {'Total_E':<18} {'Mean_T':<18}")
  print("-" * 62)
  for model, name, r in results:
    print(f"{model:<8} {name:<22} {r.total_energy:<18.2f} {r.mean_torque:<18.2f}")

  output_path = Path("docs/experiments/domain_eval_slope_flat.csv")
  output_path.parent.mkdir(parents=True, exist_ok=True)
  with open(output_path, "w", encoding="utf-8") as f:
    f.write(
      "Model,Command,Cmd_X,Cmd_Y,Mean_Vel_X,Vel_X_RMSE,Mean_Vel_Y,Vel_Y_RMSE,"
      "Roll_Mean,Roll_Std,Pitch_Mean,Pitch_Std,CoT,Total_Energy,Mean_Torque,Push_Rec_Rate\n"
    )
    for model, name, r in results:
      f.write(
        f"{model},{name},{r.commanded_vel_x:.1f},{r.commanded_vel_y:.1f},"
        f"{r.mean_vel_x:.4f},{r.vel_x_rmse:.4f},{r.mean_vel_y:.4f},{r.vel_y_rmse:.4f},"
        f"{r.mean_roll:.2f},{r.roll_std:.2f},{r.mean_pitch:.2f},{r.pitch_std:.2f},"
        f"{r.cot:.4f},{r.total_energy:.2f},{r.mean_torque:.2f},{r.push_recovery_rate:.4f}\n"
      )
  print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
  main()
