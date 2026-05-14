"""CPG controller with MPC-style interface for quadruped locomotion.

This module implements a Central Pattern Generator (CPG) based controller
that follows the same interface pattern as the MPC controller from pympc-quadruped.
It includes configuration classes, gait patterns, and leg control similar to MPC.
"""

import math
from enum import Enum
from typing import List, Union

import numpy as np
import torch


class CPGConfig:
  """Configuration for CPG controller (similar to LinearMpcConfig)."""

  dt_control: float = 0.001
  iteration_between_update: int = 20
  dt_update: float = 0.02  # dt_control * iteration_between_update

  # CPG oscillator parameters
  base_frequency: float = 1.5  # Hz
  frequency_range: tuple = (0.5, 3.0)  # Min and max frequency

  # Amplitude parameters for [hip, thigh, calf]
  base_amplitude: np.ndarray = np.array([0.3, 0.8, 0.6], dtype=np.float32)
  amplitude_scale_range: tuple = (0.5, 1.5)

  # Joint offsets (standing pose)
  joint_offset: np.ndarray = np.array([0.0, 0.9, -1.78], dtype=np.float32)

  # Velocity mapping parameters
  velocity_to_frequency_gain: float = 1.0
  velocity_to_amplitude_gain: float = 0.5

  # Swing parameters
  swing_height: float = 0.1
  swing_kp: float = 100.0
  swing_kd: float = 10.0


class RobotCPGConfig:
  """Robot-specific configuration for CPG (similar to RobotConfig)."""

  mass_base: float
  base_height_des: float
  leg_length: float

  # Swing control gains
  Kp_swing: np.ndarray
  Kd_swing: np.ndarray


class Go1CPGConfig(RobotCPGConfig):
  """CPG configuration for Unitree Go1."""

  mass_base: float = 12.0
  base_height_des: float = 0.28
  leg_length: float = 0.4

  Kp_swing = np.diag([100.0, 100.0, 100.0])
  Kd_swing = np.diag([10.0, 10.0, 10.0])


class Go2CPGConfig(RobotCPGConfig):
  """CPG configuration for Unitree Go2."""

  mass_base: float = 15.0
  base_height_des: float = 0.32
  leg_length: float = 0.45

  Kp_swing = np.diag([120.0, 120.0, 120.0])
  Kd_swing = np.diag([12.0, 12.0, 12.0])


class CPGGait(Enum):
  """Gait patterns for CPG (similar to MPC Gait enum).

  Each gait is defined by:
  - name: gait name
  - num_segment: number of segments in one gait cycle
  - phase_offsets: phase offset for each leg [FR, FL, RR, RL]
  - duty_factor: fraction of cycle in stance for each leg
  """

  STANDING = (
    "standing",
    16,
    np.array([0.0, 0.0, 0.0, 0.0]),
    np.array([1.0, 1.0, 1.0, 1.0]),
  )
  TROTTING = (
    "trotting",
    16,
    np.array([0.0, math.pi, math.pi, 0.0]),
    np.array([0.5, 0.5, 0.5, 0.5]),
  )
  WALKING = (
    "walking",
    16,
    np.array([0.0, math.pi, math.pi / 2, 3 * math.pi / 2]),
    np.array([0.75, 0.75, 0.75, 0.75]),
  )
  BOUNDING = (
    "bounding",
    16,
    np.array([0.0, 0.0, math.pi, math.pi]),
    np.array([0.5, 0.5, 0.5, 0.5]),
  )
  PACING = (
    "pacing",
    16,
    np.array([0.0, math.pi, 0.0, math.pi]),
    np.array([0.5, 0.5, 0.5, 0.5]),
  )
  GALLOPING = (
    "galloping",
    16,
    np.array([0.0, 0.25 * math.pi, math.pi, 1.25 * math.pi]),
    np.array([0.4, 0.4, 0.4, 0.4]),
  )

  def __init__(
    self,
    name: str,
    num_segment: int,
    phase_offsets: np.ndarray,
    duty_factors: np.ndarray,
  ) -> None:
    self._name = name
    self._num_segment = num_segment
    self._phase_offsets = phase_offsets  # In radians
    self._duty_factors = duty_factors

    # Normalized values
    self.phase_offsets_normalized = phase_offsets / (2 * math.pi)
    self.duty_factors_normalized = duty_factors

  @property
  def name(self) -> str:
    return self._name

  @property
  def num_segment(self) -> int:
    return self._num_segment

  @property
  def phase_offsets(self) -> np.ndarray:
    """Phase offsets in radians for [FR, FL, RR, RL]."""
    return self._phase_offsets

  @property
  def duty_factors(self) -> np.ndarray:
    """Duty factor (stance time / cycle time) for each leg."""
    return self._duty_factors

  def get_leg_phases(self, global_phase: float) -> np.ndarray:
    """Get current phase for each leg.

    Args:
        global_phase: Global phase in [0, 2π]

    Returns:
        Phase for each leg in [0, 2π]
    """
    leg_phases = (global_phase + self._phase_offsets) % (2 * math.pi)
    return leg_phases

  def get_swing_state(self, global_phase: float) -> np.ndarray:
    """Get swing state for each leg (1 = swing, 0 = stance).

    Args:
        global_phase: Global phase in [0, 2π]

    Returns:
        Binary array indicating swing (1) or stance (0) for each leg
    """
    leg_phases = self.get_leg_phases(global_phase)
    # Normalize to [0, 1]
    normalized_phases = leg_phases / (2 * math.pi)

    # Leg is in swing if phase > duty_factor
    swing_state = (normalized_phases > self._duty_factors).astype(np.float32)
    return swing_state

  def get_stance_state(self, global_phase: float) -> np.ndarray:
    """Get stance state for each leg (1 = stance, 0 = swing)."""
    return 1.0 - self.get_swing_state(global_phase)


class CPGOscillator:
  """Hopf oscillator for CPG pattern generation.

  Implements a nonlinear oscillator that generates stable limit cycles
  for rhythmic locomotion patterns.
  """

  def __init__(self, frequency: float = 1.0, amplitude: float = 1.0):
    """Initialize oscillator.

    Args:
        frequency: Oscillation frequency in Hz
        amplitude: Oscillation amplitude
    """
    self.frequency = frequency
    self.amplitude = amplitude
    self.mu = 1.0  # Convergence rate to limit cycle

    # State: [x, y] representing position on limit cycle
    self.state = np.array([amplitude, 0.0], dtype=np.float32)

  def step(
    self, dt: float, target_frequency: float = None, target_amplitude: float = None
  ):
    """Update oscillator state using Hopf dynamics.

    Dynamics:
        dx/dt = mu * (amplitude^2 - r^2) * x - 2π * frequency * y
        dy/dt = mu * (amplitude^2 - r^2) * y + 2π * frequency * x

    Args:
        dt: Time step
        target_frequency: Target frequency (if changing)
        target_amplitude: Target amplitude (if changing)
    """
    if target_frequency is not None:
      self.frequency = target_frequency
    if target_amplitude is not None:
      self.amplitude = target_amplitude

    x, y = self.state
    r_squared = x * x + y * y
    omega = 2 * math.pi * self.frequency

    # Hopf oscillator dynamics
    dx = self.mu * (self.amplitude * self.amplitude - r_squared) * x - omega * y
    dy = self.mu * (self.amplitude * self.amplitude - r_squared) * y + omega * x

    # Euler integration
    self.state[0] += dx * dt
    self.state[1] += dy * dt

  def get_output(self) -> float:
    """Get current oscillator output (x component)."""
    return self.state[0]

  def get_phase(self) -> float:
    """Get current phase in [0, 2π]."""
    return math.atan2(self.state[1], self.state[0]) % (2 * math.pi)

  def reset(self, phase: float = 0.0):
    """Reset oscillator to specific phase."""
    self.state[0] = self.amplitude * math.cos(phase)
    self.state[1] = self.amplitude * math.sin(phase)


class CPGController:
  """Central Pattern Generator controller (MPC-style interface).

  This controller generates rhythmic joint trajectories for quadruped
  locomotion using coupled oscillators. It follows the same interface
  pattern as the MPC controller for easy integration.
  """

  def __init__(self, cpg_config: CPGConfig, robot_config: RobotCPGConfig):
    """Initialize CPG controller.

    Args:
        cpg_config: CPG configuration
        robot_config: Robot-specific configuration
    """
    self.cpg_config = cpg_config
    self.robot_config = robot_config

    self.is_initialized = False
    self.is_first_run = True

    # Create oscillators for each joint (12 total: 3 per leg)
    self.oscillators = []
    for leg_idx in range(4):
      leg_oscillators = []
      for joint_idx in range(3):
        amp = cpg_config.base_amplitude[joint_idx]
        osc = CPGOscillator(frequency=cpg_config.base_frequency, amplitude=amp)
        leg_oscillators.append(osc)
      self.oscillators.append(leg_oscillators)

    # Current gait
    self.current_gait = CPGGait.TROTTING

    # Time tracking
    self.time = 0.0
    self.global_phase = 0.0

    # Velocity commands
    self.target_velocity = np.zeros(3, dtype=np.float32)  # [vx, vy, vyaw]
    self.current_frequency = cpg_config.base_frequency

    # Joint targets
    self.joint_targets = np.zeros(12, dtype=np.float32)

  def set_gait(self, gait: CPGGait):
    """Set the gait pattern.

    Args:
        gait: Desired gait pattern
    """
    self.current_gait = gait

    # Reset oscillators with appropriate phase offsets
    for leg_idx in range(4):
      phase_offset = gait.phase_offsets[leg_idx]
      for joint_idx in range(3):
        self.oscillators[leg_idx][joint_idx].reset(phase_offset)

  def update_velocity_command(self, velocity_cmd: Union[list, np.ndarray]):
    """Update target velocity command.

    Args:
        velocity_cmd: [vx, vy, vyaw] in m/s and rad/s
    """
    self.target_velocity = np.array(velocity_cmd, dtype=np.float32)

    # Map velocity to frequency
    vx = self.target_velocity[0]
    # Linear mapping: v=0 -> f=0.5*base, v=1.0 -> f=2.0*base
    velocity_magnitude = np.linalg.norm(self.target_velocity[:2])
    freq_scale = 0.5 + self.cpg_config.velocity_to_frequency_gain * velocity_magnitude
    self.current_frequency = self.cpg_config.base_frequency * np.clip(
      freq_scale, 0.3, 2.0
    )

  def compute_joint_targets(self, dt: float) -> np.ndarray:
    """Compute joint position targets for current timestep.

    Args:
        dt: Time step in seconds

    Returns:
        Joint position targets (12,) for [FR, FL, RR, RL] legs
    """
    if not self.is_initialized:
      self.is_initialized = True
      self.time = 0.0

    # Update time and global phase
    self.time += dt
    self.global_phase = (2 * math.pi * self.current_frequency * self.time) % (
      2 * math.pi
    )

    # Get swing states for current gait
    swing_states = self.current_gait.get_swing_state(self.global_phase)

    # Compute amplitude scaling based on velocity
    velocity_magnitude = np.linalg.norm(self.target_velocity[:2])
    amp_scale = 0.7 + self.cpg_config.velocity_to_amplitude_gain * velocity_magnitude
    amp_scale = np.clip(amp_scale, 0.5, 1.5)

    # Update oscillators and compute joint targets
    for leg_idx in range(4):
      phase_offset = self.current_gait.phase_offsets[leg_idx]

      for joint_idx in range(3):
        osc = self.oscillators[leg_idx][joint_idx]

        # Scale amplitude for thigh joint (index 1) based on velocity
        if joint_idx == 1:  # Thigh joint
          target_amp = self.cpg_config.base_amplitude[joint_idx] * amp_scale
        else:
          target_amp = self.cpg_config.base_amplitude[joint_idx]

        # Update oscillator
        osc.step(
          dt, target_frequency=self.current_frequency, target_amplitude=target_amp
        )

        # Get output and add offset
        output = osc.get_output()
        joint_target = output + self.cpg_config.joint_offset[joint_idx]

        # Store in joint targets array
        self.joint_targets[leg_idx * 3 + joint_idx] = joint_target

    return self.joint_targets.copy()

  def get_contact_forces(self) -> np.ndarray:
    """Get estimated contact forces (for compatibility with MPC interface).

    Returns:
        Estimated contact forces (12,) - simplified model
    """
    # Simple heuristic: force proportional to stance state
    stance_states = self.current_gait.get_stance_state(self.global_phase)

    # Distribute weight across stance legs
    num_stance = np.sum(stance_states)
    if num_stance > 0:
      fz_per_leg = (self.robot_config.mass_base * 9.81) / num_stance
    else:
      fz_per_leg = 0.0

    # Contact forces: [fx, fy, fz] for each leg
    contact_forces = np.zeros(12, dtype=np.float32)
    for leg_idx in range(4):
      contact_forces[leg_idx * 3 + 2] = stance_states[leg_idx] * fz_per_leg

    return contact_forces

  def reset(self):
    """Reset controller state."""
    self.time = 0.0
    self.global_phase = 0.0
    self.is_first_run = True

    # Reset all oscillators
    for leg_idx in range(4):
      phase_offset = self.current_gait.phase_offsets[leg_idx]
      for joint_idx in range(3):
        self.oscillators[leg_idx][joint_idx].reset(phase_offset)


class CPGLegController:
  """Leg controller for CPG (similar to MPC LegController).

  Computes joint torques from CPG joint targets using PD control.
  """

  def __init__(self, Kp: np.ndarray, Kd: np.ndarray):
    """Initialize leg controller.

    Args:
        Kp: Proportional gains (3,) for [hip, thigh, calf]
        Kd: Derivative gains (3,) for [hip, thigh, calf]
    """
    self.Kp = Kp
    self.Kd = Kd
    self.torque_cmds = np.zeros(12, dtype=np.float32)

  def update(
    self,
    joint_targets: np.ndarray,
    joint_positions: np.ndarray,
    joint_velocities: np.ndarray,
  ) -> np.ndarray:
    """Compute joint torques using PD control.

    Args:
        joint_targets: Target joint positions (12,)
        joint_positions: Current joint positions (12,)
        joint_velocities: Current joint velocities (12,)

    Returns:
        Joint torques (12,)
    """
    for leg_idx in range(4):
      for joint_idx in range(3):
        idx = leg_idx * 3 + joint_idx

        pos_error = joint_targets[idx] - joint_positions[idx]
        vel_error = 0.0 - joint_velocities[idx]

        torque = self.Kp[joint_idx] * pos_error + self.Kd[joint_idx] * vel_error
        self.torque_cmds[idx] = torque

    return self.torque_cmds.copy()


# Example usage and testing
def main():
  """Example usage of CPG controller."""
  # Create configurations
  cpg_config = CPGConfig()
  robot_config = Go1CPGConfig()

  # Create controller
  controller = CPGController(cpg_config, robot_config)

  # Set gait
  controller.set_gait(CPGGait.TROTTING)

  # Set velocity command
  controller.update_velocity_command([0.5, 0.0, 0.0])  # 0.5 m/s forward

  # Simulation loop
  dt = 0.001
  for i in range(1000):
    # Compute joint targets
    joint_targets = controller.compute_joint_targets(dt)

    # Get contact forces (for visualization/analysis)
    contact_forces = controller.get_contact_forces()

    if i % 100 == 0:
      print(
        f"Step {i}: Phase = {controller.global_phase:.2f}, Targets = {joint_targets[:3]}"
      )


if __name__ == "__main__":
  main()
