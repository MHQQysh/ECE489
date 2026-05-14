"""Train Unitree Go2 velocity policies on selectable terrain variants."""

from __future__ import annotations

import argparse
from typing import Literal, cast

from mjlab.scripts.train import TrainConfig, launch_training
from mjlab.tasks.registry import load_env_cfg, load_rl_cfg
from mjlab.tasks.velocity.config.go2 import GO2_TERRAIN_CHOICES, Go2TerrainType

_TASK_BY_TERRAIN: dict[str, str] = {
  "flat": "Mjlab-Velocity-Flat-Unitree-Go2",
  "rough": "Mjlab-Velocity-Rough-Unitree-Go2",
  "slope": "Mjlab-Velocity-Slope-Unitree-Go2",
  "stairs": "Mjlab-Velocity-Stairs-Unitree-Go2",
  "bumps": "Mjlab-Velocity-Bumps-Unitree-Go2",
  "random": "Mjlab-Velocity-Random-Unitree-Go2",
}


def _parse_gpu_ids(value: str) -> list[int] | Literal["all"] | None:
  value = value.strip().lower()
  if value in {"", "cpu", "none"}:
    return None
  if value == "all":
    return "all"
  return [int(item.strip()) for item in value.split(",") if item.strip()]


def main() -> None:
  parser = argparse.ArgumentParser(
    description="Train Unitree Go2 velocity policies on selected terrain."
  )
  parser.add_argument(
    "--terrain",
    choices=GO2_TERRAIN_CHOICES,
    default="flat",
    help="Terrain variant to train on.",
  )
  parser.add_argument(
    "--num-envs",
    type=int,
    default=None,
    help="Override the number of parallel environments.",
  )
  parser.add_argument(
    "--max-iterations",
    type=int,
    default=None,
    help="Override PPO training iterations.",
  )
  parser.add_argument(
    "--run-name",
    default=None,
    help="Optional run label appended to the timestamped log directory.",
  )
  parser.add_argument(
    "--gpu-ids",
    default="0",
    help="GPU ids as comma-separated list, 'all', or 'cpu'.",
  )
  parser.add_argument(
    "--log-root",
    default="logs/rsl_rl",
    help="Root directory for training logs.",
  )
  args = parser.parse_args()

  terrain = cast(Go2TerrainType, args.terrain)
  task_id = _TASK_BY_TERRAIN[terrain]
  env_cfg = load_env_cfg(task_id)
  agent_cfg = load_rl_cfg(task_id)

  if args.num_envs is not None:
    env_cfg.scene.num_envs = args.num_envs
  if args.max_iterations is not None:
    agent_cfg.max_iterations = args.max_iterations
  if args.run_name is not None:
    agent_cfg.run_name = args.run_name
  else:
    agent_cfg.run_name = f"terrain_{terrain}"

  train_cfg = TrainConfig(
    env=env_cfg,
    agent=agent_cfg,
    log_root=args.log_root,
    gpu_ids=_parse_gpu_ids(args.gpu_ids),
  )

  print(f"[INFO] Go2 terrain: {terrain}")
  print(f"[INFO] Task: {task_id}")
  print(f"[INFO] Num envs: {env_cfg.scene.num_envs}")
  print(f"[INFO] Max iterations: {agent_cfg.max_iterations}")
  launch_training(task_id=task_id, args=train_cfg)


if __name__ == "__main__":
  main()
