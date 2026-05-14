"""Sim2Sim test script: Load trained policy and run in MuJoCo simulation.

This script loads a trained policy checkpoint (e.g., model_299.pt) and runs it
in a MuJoCo simulation environment for testing before real robot deployment.

Usage:
    uv run python scripts/sim2sim_test.py --checkpoint /path/to/model_299.pt
    uv run python scripts/sim2sim_test.py  # Uses default checkpoint path
"""

import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import torch
import tyro

from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import MjlabOnPolicyRunner, RslRlVecEnvWrapper
from mjlab.tasks.velocity.config.go1.env_cfgs import unitree_go1_flat_env_cfg
from mjlab.tasks.velocity.config.go1.rl_cfg import unitree_go1_ppo_runner_cfg
from mjlab.utils.torch import configure_torch_backends
from mjlab.viewer import NativeMujocoViewer


@dataclass
class Sim2SimConfig:
  checkpoint: str = "logs/rsl_rl/go1_velocity/2026-05-06_02-13-54/model_299.pt"
  """Path to the trained policy checkpoint (.pt file)."""

  num_envs: int = 1
  """Number of parallel environments to run."""

  device: str | None = None
  """Device to run on (cuda:0, cpu, etc). Auto-detected if None."""

  terrain: str = "flat"
  """Terrain type: 'flat' or 'rough'."""

  viewer: str = "native"
  """Viewer backend: 'native' for local display."""


def main():
  # Parse command line arguments
  cfg = tyro.cli(Sim2SimConfig)

  # Configure PyTorch backends
  configure_torch_backends()

  # Auto-detect device
  device = cfg.device or ("cuda:0" if torch.cuda.is_available() else "cpu")
  print(f"[INFO] Using device: {device}")

  # Check if checkpoint exists
  checkpoint_path = Path(cfg.checkpoint)
  if not checkpoint_path.exists():
    print(f"[ERROR] Checkpoint not found: {checkpoint_path}")
    print(f"[INFO] Please provide a valid checkpoint path using --checkpoint")
    sys.exit(1)

  print(f"[INFO] Loading checkpoint: {checkpoint_path}")

  # Load environment configuration (play mode = True for infinite episode)
  if cfg.terrain == "flat":
    env_cfg = unitree_go1_flat_env_cfg(play=True)
    print("[INFO] Using flat terrain configuration")
  else:
    from mjlab.tasks.velocity.config.go1.env_cfgs import unitree_go1_rough_env_cfg

    env_cfg = unitree_go1_rough_env_cfg(play=True)
    print("[INFO] Using rough terrain configuration")

  # Override number of environments
  env_cfg.scene.num_envs = cfg.num_envs

  # Load RL agent configuration
  agent_cfg = unitree_go1_ppo_runner_cfg()

  # Create environment
  print("[INFO] Creating MuJoCo environment...")
  env = ManagerBasedRlEnv(cfg=env_cfg, device=device, render_mode=None)
  env = RslRlVecEnvWrapper(env, clip_actions=agent_cfg.clip_actions)

  # Create runner and load checkpoint
  print("[INFO] Loading trained policy...")
  runner = MjlabOnPolicyRunner(env, asdict(agent_cfg), device=device)
  runner.load(
    str(checkpoint_path),
    load_cfg={"actor": True},
    strict=True,
    map_location=device,
  )

  # Get inference policy
  policy = runner.get_inference_policy(device=device)
  print("[INFO] Policy loaded successfully!")

  # Run simulation with viewer
  print("[INFO] Starting simulation...")
  print("[INFO] Controls:")
  print("  - Use keyboard/mouse to control camera")
  print("  - Close window to exit")
  print("=" * 60)

  if cfg.viewer == "native":
    viewer = NativeMujocoViewer(env, policy)
    viewer.run()
  else:
    print(f"[ERROR] Unsupported viewer: {cfg.viewer}")
    sys.exit(1)

  # Cleanup
  env.close()
  print("[INFO] Simulation ended.")


if __name__ == "__main__":
  main()
