"""Demo script for CPG controller with MPC-style interface.

This script demonstrates how to use the CPG controller in a MuJoCo simulation,
following the same pattern as the MPC controller from pympc-quadruped.
"""

import numpy as np

try:
  import mujoco
  import mujoco.viewer

  MUJOCO_AVAILABLE = True
except ImportError:
  MUJOCO_AVAILABLE = False
  print("Warning: MuJoCo not available. Install with: pip install mujoco")

from mjlab.controllers.cpg_mpc_style import (
  CPGConfig,
  CPGController,
  CPGGait,
  CPGLegController,
  Go1CPGConfig,
  Go2CPGConfig,
)


def create_go1_controller():
  """Create CPG controller for Go1 robot."""
  cpg_config = CPGConfig()
  cpg_config.base_frequency = 1.5
  cpg_config.base_amplitude = np.array([0.2, 0.6, 0.5], dtype=np.float32)
  cpg_config.joint_offset = np.array([0.0, 0.9, -1.8], dtype=np.float32)

  robot_config = Go1CPGConfig()

  controller = CPGController(cpg_config, robot_config)
  controller.set_gait(CPGGait.TROTTING)

  return controller


def create_go2_controller():
  """Create CPG controller for Go2 robot."""
  cpg_config = CPGConfig()
  cpg_config.base_frequency = 1.5
  cpg_config.base_amplitude = np.array([0.25, 0.7, 0.55], dtype=np.float32)
  cpg_config.joint_offset = np.array([0.0, 0.85, -1.75], dtype=np.float32)

  robot_config = Go2CPGConfig()

  controller = CPGController(cpg_config, robot_config)
  controller.set_gait(CPGGait.TROTTING)

  return controller


def run_cpg_simulation_mujoco(robot_type: str = "go1", duration: float = 10.0):
  """Run CPG controller in MuJoCo simulation.

  Args:
      robot_type: "go1" or "go2"
      duration: Simulation duration in seconds
  """
  if not MUJOCO_AVAILABLE:
    print("MuJoCo not available. Running without visualization.")
    run_cpg_without_mujoco(robot_type, duration)
    return

  # Create controller
  if robot_type == "go1":
    controller = create_go1_controller()
    # You would load the Go1 MuJoCo model here
    print("Go1 controller created")
  elif robot_type == "go2":
    controller = create_go2_controller()
    # You would load the Go2 MuJoCo model here
    print("Go2 controller created")
  else:
    raise ValueError(f"Unknown robot type: {robot_type}")

  # Create leg controller for torque computation
  Kp = np.array([50.0, 50.0, 50.0], dtype=np.float32)
  Kd = np.array([5.0, 5.0, 5.0], dtype=np.float32)
  leg_controller = CPGLegController(Kp, Kd)

  # Simulation parameters
  dt = 0.001  # 1ms control loop
  num_steps = int(duration / dt)

  # Velocity command profile
  print(f"\nRunning {duration}s simulation with CPG controller...")
  print("Velocity profile:")
  print("  0-3s: Standing")
  print("  3-6s: Forward 0.5 m/s")
  print("  6-8s: Forward 0.8 m/s + Turn 0.3 rad/s")
  print("  8-10s: Slow down")

  # Simulation loop
  for step in range(num_steps):
    t = step * dt

    # Update velocity command based on time
    if t < 3.0:
      # Standing
      velocity_cmd = [0.0, 0.0, 0.0]
      if step == 0:
        controller.set_gait(CPGGait.STANDING)
    elif t < 6.0:
      # Forward walking
      velocity_cmd = [0.5, 0.0, 0.0]
      if step == int(3.0 / dt):
        controller.set_gait(CPGGait.TROTTING)
    elif t < 8.0:
      # Forward + turning
      velocity_cmd = [0.8, 0.0, 0.3]
    else:
      # Slow down
      velocity_cmd = [0.2, 0.0, 0.0]

    # Update controller
    controller.update_velocity_command(velocity_cmd)

    # Compute joint targets
    joint_targets = controller.compute_joint_targets(dt)

    # In a real simulation, you would:
    # 1. Get current joint positions and velocities from MuJoCo
    # 2. Compute torques using leg_controller
    # 3. Apply torques to the robot
    # 4. Step the simulation

    # For this demo, we just simulate joint state
    joint_positions = joint_targets  # Assume perfect tracking
    joint_velocities = np.zeros(12, dtype=np.float32)

    # Compute torques (would be applied in real sim)
    torques = leg_controller.update(joint_targets, joint_positions, joint_velocities)

    # Get contact forces for analysis
    contact_forces = controller.get_contact_forces()

    # Print status every second
    if step % int(1.0 / dt) == 0:
      print(f"\nTime: {t:.1f}s")
      print(
        f"  Velocity cmd: [{velocity_cmd[0]:.2f}, {velocity_cmd[1]:.2f}, {velocity_cmd[2]:.2f}]"
      )
      print(f"  Frequency: {controller.current_frequency:.2f} Hz")
      print(f"  Phase: {controller.global_phase:.2f} rad")
      print(f"  Joint targets (FR leg): {joint_targets[:3]}")
      print(f"  Contact forces (z): {contact_forces[2::3]}")

  print("\nSimulation complete!")


def run_cpg_without_mujoco(robot_type: str = "go1", duration: float = 10.0):
  """Run CPG controller without MuJoCo (pure Python simulation).

  Args:
      robot_type: "go1" or "go2"
      duration: Simulation duration in seconds
  """
  # Create controller
  if robot_type == "go1":
    controller = create_go1_controller()
  elif robot_type == "go2":
    controller = create_go2_controller()
  else:
    raise ValueError(f"Unknown robot type: {robot_type}")

  print(f"\nRunning {duration}s CPG simulation (no visualization)...")

  dt = 0.001
  num_steps = int(duration / dt)

  # Test different gaits
  gaits_to_test = [
    (CPGGait.STANDING, 2.0, [0.0, 0.0, 0.0]),
    (CPGGait.TROTTING, 3.0, [0.5, 0.0, 0.0]),
    (CPGGait.WALKING, 2.0, [0.3, 0.0, 0.0]),
    (CPGGait.PACING, 2.0, [0.5, 0.0, 0.0]),
    (CPGGait.BOUNDING, 1.0, [0.6, 0.0, 0.0]),
  ]

  current_time = 0.0
  for gait, gait_duration, velocity in gaits_to_test:
    print(f"\n{'=' * 60}")
    print(f"Testing {gait.name} gait for {gait_duration}s")
    print(f"Velocity: {velocity}")
    print(f"{'=' * 60}")

    controller.set_gait(gait)
    controller.update_velocity_command(velocity)

    gait_steps = int(gait_duration / dt)
    for step in range(gait_steps):
      joint_targets = controller.compute_joint_targets(dt)
      current_time += dt

      # Print every 0.5s
      if step % int(0.5 / dt) == 0:
        contact_forces = controller.get_contact_forces()
        swing_states = gait.get_swing_state(controller.global_phase)
        print(
          f"  t={current_time:.1f}s | Phase={controller.global_phase:.2f} | "
          f"Swing=[{swing_states[0]:.0f},{swing_states[1]:.0f},"
          f"{swing_states[2]:.0f},{swing_states[3]:.0f}] | "
          f"FR_joints={joint_targets[:3]}"
        )

  print("\n" + "=" * 60)
  print("All gaits tested successfully!")
  print("=" * 60)


def compare_gaits():
  """Compare different gait patterns."""
  print("\n" + "=" * 60)
  print("GAIT COMPARISON")
  print("=" * 60)

  cpg_config = CPGConfig()
  robot_config = Go1CPGConfig()
  controller = CPGController(cpg_config, robot_config)

  gaits = [
    CPGGait.STANDING,
    CPGGait.TROTTING,
    CPGGait.WALKING,
    CPGGait.PACING,
    CPGGait.BOUNDING,
    CPGGait.GALLOPING,
  ]

  for gait in gaits:
    print(f"\n{gait.name.upper()}:")
    print(f"  Phase offsets: {gait.phase_offsets}")
    print(f"  Duty factors: {gait.duty_factors}")

    # Sample at different phases
    print("  Swing states at different phases:")
    for phase in [0.0, np.pi / 2, np.pi, 3 * np.pi / 2]:
      swing = gait.get_swing_state(phase)
      print(f"    Phase {phase:.2f}: {swing}")


def analyze_oscillator_dynamics():
  """Analyze Hopf oscillator dynamics."""
  from mjlab.controllers.cpg_mpc_style import CPGOscillator

  print("\n" + "=" * 60)
  print("HOPF OSCILLATOR ANALYSIS")
  print("=" * 60)

  # Create oscillator
  osc = CPGOscillator(frequency=1.0, amplitude=1.0)

  print("\nOscillator parameters:")
  print(f"  Frequency: {osc.frequency} Hz")
  print(f"  Amplitude: {osc.amplitude}")
  print(f"  Initial state: {osc.state}")

  # Run for one period
  dt = 0.01
  period = 1.0 / osc.frequency
  steps = int(period / dt)

  print(f"\nRunning for one period ({period}s):")
  outputs = []
  phases = []

  for step in range(steps):
    osc.step(dt)
    output = osc.get_output()
    phase = osc.get_phase()
    outputs.append(output)
    phases.append(phase)

    if step % (steps // 4) == 0:
      print(f"  t={step * dt:.2f}s: output={output:.3f}, phase={phase:.3f}")

  print(f"\nFinal state: {osc.state}")
  print(f"Max output: {max(outputs):.3f}")
  print(f"Min output: {min(outputs):.3f}")


def main():
  """Main demo function."""
  import argparse

  parser = argparse.ArgumentParser(description="CPG Controller Demo")
  parser.add_argument(
    "--robot",
    type=str,
    default="go1",
    choices=["go1", "go2"],
    help="Robot type",
  )
  parser.add_argument(
    "--duration",
    type=float,
    default=10.0,
    help="Simulation duration in seconds",
  )
  parser.add_argument(
    "--mode",
    type=str,
    default="simulate",
    choices=["simulate", "compare", "analyze"],
    help="Demo mode",
  )

  args = parser.parse_args()

  if args.mode == "simulate":
    run_cpg_simulation_mujoco(args.robot, args.duration)
  elif args.mode == "compare":
    compare_gaits()
  elif args.mode == "analyze":
    analyze_oscillator_dynamics()


if __name__ == "__main__":
  main()
