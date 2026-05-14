"""Demo with forward-walking CPG."""

import torch

from mjlab.controllers.cpg_forward import CPGControllerForward
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg
from mjlab.viewer import NativeMujocoViewer


def demo_cpg_forward():
  """Run CPG optimized for forward walking."""
  print("=" * 60)
  print("CPG Forward Walking Demo")
  print("=" * 60)
  print("\nUsing optimized parameters for forward locomotion.\n")

  device = "cuda:0" if torch.cuda.is_available() else "cpu"

  # Load environment
  print("Loading environment...")
  env_cfg = load_env_cfg("Mjlab-Velocity-Flat-Unitree-Go2", play=True)
  env_cfg.scene.num_envs = 1
  base_env = ManagerBasedRlEnv(cfg=env_cfg, device=device)
  env = RslRlVecEnvWrapper(base_env, clip_actions=1.0)

  # Create forward-walking CPG
  print("Creating forward-walking CPG controller...")
  controller = CPGControllerForward(
    num_envs=1,
    device=device,
    frequency=1.5,  # 1.5 Hz for stable walking
  )

  print("\n✅ Forward Walking CPG:")
  print(f"  - Frequency: 1.5 Hz")
  print(f"  - Gait: Trot (diagonal legs)")
  print(f"  - Thigh amplitude: 0.8 rad (large stride)")
  print(f"  - Calf amplitude: 1.0 rad (ground clearance)")
  print(f"  - Optimized for forward motion\n")

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
  print("  - Mouse: Rotate/Zoom view")
  print("\n🚶 Watch the robot walk forward!\n")

  # Run viewer
  try:
    viewer = NativeMujocoViewer(env, policy)
    viewer.run()
  except KeyboardInterrupt:
    print("\nStopped by user.")
  except Exception as e:
    print(f"\nError: {e}")

  print("\nDemo complete!")
  print("\nWhat you should see:")
  print("  ✓ Robot moves forward (not just in place)")
  print("  ✓ Diagonal legs swing together (trot gait)")
  print("  ✓ Stable walking on flat ground")


if __name__ == "__main__":
  demo_cpg_forward()
