"""Demo showing CPG responding to velocity commands."""

import torch

from mjlab.controllers.cpg_velocity import CPGControllerVelocity
from mjlab.envs import ManagerBasedRlEnv
from mjlab.rl import RslRlVecEnvWrapper
from mjlab.tasks.registry import load_env_cfg
from mjlab.viewer import NativeMujocoViewer


def demo_cpg_velocity():
  """Run CPG that responds to velocity commands."""
  print("=" * 60)
  print("CPG with Velocity Control Demo")
  print("=" * 60)
  print("\nThis CPG adjusts its gait based on commanded velocity!")
  print("  - Higher velocity → faster frequency + larger stride")
  print("  - Lower velocity → slower frequency + smaller stride\n")

  device = "cuda:0" if torch.cuda.is_available() else "cpu"

  # Load environment
  print("Loading environment...")
  env_cfg = load_env_cfg("Mjlab-Velocity-Flat-Unitree-Go2", play=True)
  env_cfg.scene.num_envs = 1
  base_env = ManagerBasedRlEnv(cfg=env_cfg, device=device)
  env = RslRlVecEnvWrapper(base_env, clip_actions=1.0)

  # Create velocity-responsive CPG
  print("Creating velocity-responsive CPG...")
  controller = CPGControllerVelocity(
    num_envs=1,
    device=device,
    base_frequency=1.5,
  )

  print("\n✅ Velocity-Responsive CPG:")
  print(f"  - Base frequency: 1.5 Hz")
  print(f"  - Frequency adapts to velocity command")
  print(f"  - Stride length adapts to velocity command")
  print(f"  - Still open-loop (no feedback)\n")

  # Policy wrapper that reads velocity commands from environment
  class CPGVelocityPolicy:
    def __init__(self, cpg_controller, env):
      self.cpg = cpg_controller
      self.env = env
      self.step_count = 0

    def __call__(self, obs):
      # Get velocity command from environment
      # The environment has a command manager that generates velocity commands
      base_env = self.env.unwrapped

      # Get the commanded velocity from the environment
      if hasattr(base_env, "command_manager"):
        # Extract velocity command (vx, vy, vyaw)
        velocity_cmd = base_env.command_manager.get_command("twist")
      else:
        # Fallback: use a test velocity that changes over time
        if self.step_count < 500:
          velocity_cmd = torch.tensor([[0.5, 0.0, 0.0]], device=self.env.device)
        elif self.step_count < 1000:
          velocity_cmd = torch.tensor([[1.0, 0.0, 0.0]], device=self.env.device)
        else:
          velocity_cmd = torch.tensor([[0.3, 0.0, 0.0]], device=self.env.device)

      self.step_count += 1

      # CPG generates actions based on velocity command
      return self.cpg.compute_actions(
        dt=self.env.unwrapped.step_dt, velocity_command=velocity_cmd
      )

  policy = CPGVelocityPolicy(controller, env)

  # Reset
  env.reset()
  controller.reset()

  print("Starting MuJoCo viewer...")
  print("\n📊 Watch how the gait changes with velocity:")
  print("  - Steps 0-500: v=0.5 m/s (slow)")
  print("  - Steps 500-1000: v=1.0 m/s (fast)")
  print("  - Steps 1000+: v=0.3 m/s (very slow)")
  print("\nControls:")
  print("  - Space: Pause/Resume")
  print("  - Esc: Exit\n")

  # Run viewer
  try:
    viewer = NativeMujocoViewer(env, policy)
    viewer.run()
  except KeyboardInterrupt:
    print("\nStopped by user.")
  except Exception as e:
    print(f"\nError: {e}")

  print("\nDemo complete!")
  print("\n💡 Key insight:")
  print("  CPG can respond to velocity commands by adjusting:")
  print("  1. Frequency (how fast legs swing)")
  print("  2. Amplitude (how far legs swing)")
  print("  But it's still open-loop - no feedback from sensors!")


if __name__ == "__main__":
  demo_cpg_velocity()
