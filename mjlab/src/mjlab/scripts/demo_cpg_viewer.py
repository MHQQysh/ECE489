"""Demo script to visualize CPG controller with MuJoCo viewer."""

import torch

from mjlab.controllers.cpg_baseline import CPGController
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg
from mjlab.viewer import NativeMujocoViewer


def demo_cpg_with_viewer():
  """Run CPG controller with MuJoCo visualization."""
  print("=" * 60)
  print("CPG Controller Demo with Visualization")
  print("=" * 60)
  print("\nThis will show the Go2 robot walking using CPG control.")
  print("The CPG generates sinusoidal joint trajectories (open-loop).")
  print("\nControls:")
  print("  - Space: Pause/Resume")
  print("  - Esc: Exit")
  print("  - Mouse: Rotate view")
  print("\nPress any key to start...\n")

  device = "cuda:0" if torch.cuda.is_available() else "cpu"

  # Load environment
  print("Loading environment...")
  env_cfg = load_env_cfg("Mjlab-Velocity-Flat-Unitree-Go2", play=True)
  env_cfg.scene.num_envs = 1  # Single robot for visualization
  base_env = ManagerBasedRlEnv(cfg=env_cfg, device=device)

  # Wrap environment for viewer compatibility
  env = RslRlVecEnvWrapper(base_env, clip_actions=1.0)

  # Create CPG controller
  print("Creating CPG controller...")
  controller = CPGController(
    num_envs=1,
    device=device,
    gait="trot",
    frequency=2.0,
  )

  print("\nCPG Parameters:")
  print(f"  Gait: trot")
  print(f"  Frequency: 2.0 Hz")
  print(f"  Control: Open-loop (no feedback)\n")

  # Create policy wrapper for viewer
  class CPGPolicy:
    def __init__(self, cpg_controller, env):
      self.cpg = cpg_controller
      self.env = env

    def __call__(self, obs):
      # CPG doesn't use observations
      return self.cpg.compute_actions(dt=self.env.unwrapped.step_dt)

  policy = CPGPolicy(controller, env)

  # Reset environment
  env.reset()
  controller.reset()

  print("Starting MuJoCo viewer...")
  print("Watch the robot walk!\n")

  # Run with native MuJoCo viewer
  viewer = NativeMujocoViewer(env, policy)
  viewer.run()

  print("\nDemo complete!")


if __name__ == "__main__":
  demo_cpg_with_viewer()
