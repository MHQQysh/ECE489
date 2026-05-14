#!/usr/bin/env python3
"""Run comprehensive evaluation for all trained checkpoints.

This script automatically discovers checkpoints and runs evaluation
for all training configurations (flat and slope).

Usage:
    cd /home/y/ece489/lab4/mjlab
    export WANDB_MODE=disabled

    # Run all evaluations
    uv run python src/mjlab/scripts/run_comprehensive_eval.py

    # Run specific task
    uv run python src/mjlab/scripts/run_comprehensive_eval.py --task Mjlab-Velocity-Flat-Unitree-Go2

    # Check results
    python src/mjlab/scripts/generate_summary_table.py
"""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
import tyro


def _has_cuda() -> bool:
  """Check if CUDA is available."""
  try:
    return torch.cuda.is_available()
  except Exception:
    return False


def get_checkpoint_obs_dim(checkpoint_path: str) -> int | None:
  """Get the observation dimension from a checkpoint."""
  try:
    ckpt = torch.load(checkpoint_path, map_location="cpu")
    actor = ckpt.get("actor_state_dict", ckpt.get("model_state_dict", {}))
    for k, v in actor.items():
      if "weight" in k and "mlp.0" in k:
        return v.shape[1]
  except Exception:
    pass
  return None


def find_latest_checkpoint(
  log_dir: Path, task: str, eval_iter: int | None = None
) -> Path | None:
  """Find the latest checkpoint for a given task."""
  if task not in [
    "Mjlab-Velocity-Flat-Unitree-Go2",
    "Mjlab-Velocity-Slope-Unitree-Go2",
  ]:
    return None

  if "Flat" in task:
    expected_obs_dim = 48
  elif "Slope" in task:
    expected_obs_dim = 235
  else:
    expected_obs_dim = 48

  exp_dir = log_dir / "go2_velocity"
  if not exp_dir.exists():
    return None

  timestamps = []
  for d in exp_dir.iterdir():
    if d.is_dir() and d.name.startswith("202"):
      timestamps.append(d)

  if not timestamps:
    return None

  timestamps.sort(key=lambda x: x.name, reverse=True)

  best_checkpoint = None
  best_iter = -1

  for ts_dir in timestamps:
    checkpoints = sorted(ts_dir.glob("model_*.pt"))
    for ckpt in checkpoints:
      try:
        iter_num = int(ckpt.stem.split("_")[1])
      except ValueError:
        continue

      # If eval_iter specified, only use that exact iteration
      if eval_iter is not None and iter_num != eval_iter:
        continue

      obs_dim = get_checkpoint_obs_dim(str(ckpt))
      if obs_dim != expected_obs_dim:
        continue

      # Skip early iterations unless eval_iter is explicitly specified
      meets_min_iter = eval_iter is not None or (
        ("Flat" in task and iter_num >= 100) or ("Slope" in task and iter_num >= 300)
      )

      if meets_min_iter and iter_num > best_iter:
        best_checkpoint = ckpt
        best_iter = iter_num

    if best_checkpoint is not None:
      break

  return best_checkpoint


def run_evaluation(
  task: str,
  checkpoint: str | Path,
  num_trials: int = 10,
  save_video: bool = True,
) -> bool:
  """Run evaluation for a single configuration."""
  checkpoint_str = str(checkpoint)
  output_dir = f"evaluation_results/comprehensive/{Path(task).name}"

  cmd = [
    "uv",
    "run",
    "python",
    "src/mjlab/scripts/comprehensive_evaluation.py",
    "--task",
    task,
    "--checkpoint",
    checkpoint_str,
    "--num-trials",
    str(num_trials),
    "--output-dir",
    output_dir,
    "--device",
    "cuda:0" if _has_cuda() else "cpu",
  ]

  if save_video:
    cmd.append("--save-video")

  print(f"\n{'=' * 60}")
  print(f"Running: {task}")
  print(f"Checkpoint: {checkpoint}")
  print(f"{'=' * 60}")

  result = subprocess.run(cmd, cwd=Path(__file__).parent.parent.parent.parent)
  return result.returncode == 0


@dataclass
class MainConfig:
  """Configuration for the evaluation runner."""

  log_dir: Path = Path("logs/rsl_rl")
  num_trials: int = 10
  save_video: bool = True
  task: str | None = None
  eval_iter: int | None = None
  """If set, evaluate specific iteration (e.g. 199 for training at 200)."""


def main(cfg: MainConfig) -> None:
  """Run comprehensive evaluation for all tasks."""
  device = "cuda:0" if _has_cuda() else "cpu"
  print("=" * 60)
  print("COMPREHENSIVE EVALUATION RUNNER")
  print("=" * 60)
  print(f"Log directory: {cfg.log_dir}")
  print(f"Number of trials per configuration: {cfg.num_trials}")
  print(f"Save videos: {cfg.save_video}")
  print(f"Device: {device}")

  if cfg.task is not None:
    task_configs = [(cfg.task, cfg.task)]
  else:
    task_configs = [
      ("Flat terrain", "Mjlab-Velocity-Flat-Unitree-Go2"),
      ("Slope terrain", "Mjlab-Velocity-Slope-Unitree-Go2"),
    ]

  results: dict[str, Any] = {}

  for task_name, task_id in task_configs:
    print(f"\n>>> Task: {task_name}")
    checkpoint = find_latest_checkpoint(cfg.log_dir, task_id, cfg.eval_iter)

    if checkpoint is None:
      print(f"WARNING: No checkpoint found for {task_id}")
      if cfg.eval_iter is not None:
        print(f"  (tried to find iteration {cfg.eval_iter})")
      print(f"  Searched in: {cfg.log_dir}")
      results[task_id] = None
      continue

    print(f"  Checkpoint: {checkpoint}")
    results[task_id] = str(checkpoint)

    success = run_evaluation(task_id, checkpoint, cfg.num_trials, cfg.save_video)
    results[task_id] = "SUCCESS" if success else "FAILED"

  print("\n" + "=" * 60)
  print("EVALUATION SUMMARY")
  print("=" * 60)

  for task_id, status in results.items():
    if status is None:
      print(f"{task_id}: SKIPPED (no checkpoint)")
    else:
      print(f"{task_id}: {status}")

  print("\nResults saved in: evaluation_results/comprehensive/")


if __name__ == "__main__":
  cfg = tyro.cli(MainConfig)
  main(cfg)
