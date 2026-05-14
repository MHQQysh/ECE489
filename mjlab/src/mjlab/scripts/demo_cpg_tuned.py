"""Tuned CPG demo for Go2 robot."""

import torch

from mjlab.controllers.cpg_baseline import CPGController
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg
from mjlab.viewer import NativeMujocoViewer


def demo_cpg_tuned():
  """Run CPG with tuned parameters for Go2."""
  print("=" * 60)
  print("CPG Controller Demo - Tuned for Go2")
  print("=" * 60)
  print("\nUsing hand-tuned parameters for better walking.\n")

  device = "cuda:0" if torch.cuda.is_available() else "cpu"

  # Load environment
  print("Loading environment...")
  env_cfg = load_env_cfg("Mjlab-Velocity-Flat-Unitree-Go2", play=True)
  env_cfg.scene.num_envs = 1
  base_env = ManagerBasedRlEnv(cfg=env_cfg, device=device)
  env = RslRlVecEnvWrapper(base_env, clip_actions=1.0)

  # Create CPG with tuned parameters
  print("Creating CPG controller with tuned parameters...")
  controller = CPGController(
    num_envs=1,
    device=device,
    gait="trot",
    frequency=1.5,  # Slower for stability
    amplitude_hip=0.2,  # Smaller hip movement
    amplitude_thigh=0.5,  # Moderate thigh movement
    amplitude_calf=0.7,  # Larger calf movement for ground clearance
    offset_hip=0.0,
    offset_thigh=0.8,  # Slightly bent stance
    offset_calf=-1.6,  # Bent legs
  )

  print("\n✅ Tuned CPG Parameters:")
  print(f"  - Gait: trot")
  print(f"  - Frequency: 1.5 Hz (slower for stability)")
  print(f"  - Hip amplitude: 0.2 rad")
  print(f"  - Thigh amplitude: 0.5 rad")
  print(f"  - Calf amplitude: 0.7 rad")
  print(f"  - Control: Open-loop\n")

  # Policy wrapper
  class CPGPolicy:
    def __init__(self, cpg_controller, env):
      self.cpg = cpg_controller
      self.env = env

    def __call__(self, obs):
      return self.cpg.compute_actions(dt=self.env.unwrapped.step_dt)

  policy = CPGPolicy(controller, env)

  # Reset
  env.reset()
  controller.reset()

  print("Starting MuJoCo viewer...")
  print("\nControls:")
  print("  - Space: Pause/Resume")
  print("  - Esc: Exit")
  print("  - Mouse drag: Rotate view")
  print("  - Mouse wheel: Zoom")
  print("\nWatch the robot walk!\n")

  # Run viewer
  try:
    viewer = NativeMujocoViewer(env, policy)
    viewer.run()
  except KeyboardInterrupt:
    print("\nStopped by user.")
  except Exception as e:
    print(f"\nError: {e}")
    print("\nTip: If the robot falls immediately, try:")
    print("  - Lower frequency (slower movement)")
    print("  - Smaller amplitudes")
    print("  - Different gait (walk instead of trot)")

  print("\nDemo complete!")


if __name__ == "__main__":
  demo_cpg_tuned()
