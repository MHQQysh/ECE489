"""Demo script to visualize CPG controller in action."""

import torch

from mjlab.controllers.cpg_baseline import CPGController
from mjlab.envs import ManagerBasedRlEnv
from mjlab.tasks.registry import load_env_cfg


def demo_cpg():
  """Run CPG controller and show the robot walking."""
  print("=" * 60)
  print("CPG Controller Demo")
  print("=" * 60)
  print("\nThis will show the Go2 robot walking using CPG control.")
  print("The CPG generates sinusoidal joint trajectories (open-loop).")
  print("\nPress Ctrl+C to stop.\n")

  device = "cuda:0" if torch.cuda.is_available() else "cpu"

  # Load environment
  print("Loading environment...")
  env_cfg = load_env_cfg("Mjlab-Velocity-Flat-Unitree-Go2", play=True)
  env_cfg.scene.num_envs = 1  # Single robot for visualization
  env = ManagerBasedRlEnv(cfg=env_cfg, device=device, render_mode="human")

  # Create CPG controller
  print("Creating CPG controller...")
  controller = CPGController(
    num_envs=1,
    device=device,
    gait="trot",  # Try: trot, walk, pace
    frequency=2.0,  # Hz
  )

  print("\nCPG Parameters:")
  print(f"  Gait: trot")
  print(f"  Frequency: 2.0 Hz")
  print(f"  This generates sinusoidal joint angles")
  print(f"  No feedback - purely open-loop!\n")

  # Reset
  obs, _ = env.reset()
  controller.reset()

  print("Running CPG controller...")
  print("Watch the robot walk with periodic leg movements!\n")

  step = 0
  try:
    while True:
      # CPG generates actions based on time (no observation needed!)
      actions = controller.compute_actions(dt=env.step_dt)

      # Step environment
      obs, reward, terminated, truncated, info = env.step(actions)

      # Print info every 50 steps
      if step % 50 == 0:
        robot = env.scene["robot"]
        vel = robot.data.body_com_lin_vel_w[0, 0, :]  # Linear velocity of base
        print(
          f"Step {step:4d} | Velocity: [{vel[0]:.2f}, {vel[1]:.2f}, {vel[2]:.2f}] m/s"
        )

      step += 1

      # Reset if terminated
      if terminated.any() or truncated.any():
        print("\nRobot fell! Resetting...")
        obs, _ = env.reset()
        controller.reset()
        step = 0

  except KeyboardInterrupt:
    print("\n\nDemo stopped by user.")
    print(f"Total steps: {step}")

  env.close()
  print("\nDemo complete!")


if __name__ == "__main__":
  demo_cpg()
