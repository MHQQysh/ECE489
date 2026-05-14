"""Simple CPG demo without rendering - just shows it works."""

import torch

from mjlab.controllers.cpg_baseline import CPGController
from mjlab.envs import ManagerBasedRlEnv
from mjlab.tasks.registry import load_env_cfg


def demo_cpg_simple():
  """Run CPG controller without rendering."""
  print("=" * 60)
  print("CPG Controller Simple Demo (No Rendering)")
  print("=" * 60)
  print("\nThis demonstrates that CPG works in simulation.")
  print("CPG generates sinusoidal joint trajectories (open-loop).\n")

  device = "cuda:0" if torch.cuda.is_available() else "cpu"

  # Load environment (no rendering)
  print("Loading environment...")
  env_cfg = load_env_cfg("Mjlab-Velocity-Flat-Unitree-Go2", play=True)
  env_cfg.scene.num_envs = 1
  env = ManagerBasedRlEnv(cfg=env_cfg, device=device)

  # Create CPG controller
  print("Creating CPG controller...")
  controller = CPGController(
    num_envs=1,
    device=device,
    gait="trot",
    frequency=2.0,
  )

  print("\n✅ CPG Controller Parameters:")
  print(f"  - Gait: trot (diagonal legs move together)")
  print(f"  - Frequency: 2.0 Hz")
  print(f"  - Control: Open-loop (no sensor feedback)")
  print(f"  - Method: Sinusoidal joint trajectories\n")

  # Reset
  obs, _ = env.reset()
  controller.reset()

  print("Running simulation for 500 steps...")
  print("-" * 60)

  for step in range(500):
    # CPG generates actions (no observation needed!)
    actions = controller.compute_actions(dt=env.step_dt)

    # Step environment
    obs, reward, terminated, truncated, info = env.step(actions)

    # Print info every 100 steps
    if step % 100 == 0:
      robot = env.scene["robot"]
      vel = robot.data.body_com_lin_vel_w[0, 0, :]
      pos = robot.data.body_com_pos_w[0, 0, :]
      print(
        f"Step {step:3d} | "
        f"Pos: [{pos[0]:5.2f}, {pos[1]:5.2f}, {pos[2]:5.2f}] m | "
        f"Vel: [{vel[0]:5.2f}, {vel[1]:5.2f}, {vel[2]:5.2f}] m/s"
      )

    # Reset if terminated
    if terminated.any() or truncated.any():
      print(f"\n⚠️  Robot fell at step {step}. Resetting...")
      obs, _ = env.reset()
      controller.reset()

  print("-" * 60)
  print("\n✅ Demo complete!")
  print("\nWhat just happened:")
  print("  1. CPG generated sinusoidal joint angles")
  print("  2. Robot walked in simulation (no training needed!)")
  print("  3. This is the baseline for comparison with RL\n")

  print("Next steps:")
  print(
    "  - Run evaluation: uv run python src/mjlab/scripts/evaluate_controller.py --controller cpg --num-trials 3"
  )
  print("  - Compare with RL: ./scripts/run_evaluation.sh\n")

  env.close()


if __name__ == "__main__":
  demo_cpg_simple()
