"""CPG controller that responds to velocity commands."""

import math

import torch


class CPGControllerVelocity:
  """CPG controller that adjusts gait based on commanded velocity."""

  def __init__(
    self,
    num_envs: int,
    device: str,
    base_frequency: float = 1.5,
  ):
    """Initialize velocity-responsive CPG.

    Args:
      num_envs: Number of parallel environments.
      device: Device to run on.
      base_frequency: Base oscillation frequency in Hz.
    """
    self.num_envs = num_envs
    self.device = device
    self.base_frequency = base_frequency
    self.current_frequency = base_frequency

    # Trot gait phase offsets
    self.phase_offset = torch.tensor(
      [
        0.0,
        0.0,
        0.0,  # FR leg (phase 0)
        math.pi,
        math.pi,
        math.pi,  # FL leg (phase π)
        math.pi,
        math.pi,
        math.pi,  # RR leg (phase π)
        0.0,
        0.0,
        0.0,  # RL leg (phase 0)
      ],
      device=device,
    )

    # Base amplitudes (will be scaled by velocity)
    self.base_amplitude = torch.tensor(
      [0.3, 0.8, 0.6] * 4,  # hip, thigh, calf for each leg
      device=device,
    )

    # Joint offsets
    self.offset = torch.tensor(
      [0.0, 0.9, -1.78] * 4,  # Standing pose
      device=device,
    )

    # Time counter
    self.time = torch.zeros(num_envs, device=device)

    # Target velocity (will be updated)
    self.target_velocity = torch.zeros(num_envs, 3, device=device)

  def reset(self, env_ids: torch.Tensor | None = None):
    """Reset time counter."""
    if env_ids is None:
      self.time.zero_()
    else:
      self.time[env_ids] = 0.0

  def set_target_velocity(self, velocity: torch.Tensor):
    """Set target velocity for the robot.

    Args:
      velocity: Target velocity (num_envs, 3) - [vx, vy, vyaw]
    """
    self.target_velocity = velocity

  def compute_actions(
    self, dt: float, velocity_command: torch.Tensor | None = None
  ) -> torch.Tensor:
    """Compute joint position targets based on velocity command.

    Args:
      dt: Time step in seconds.
      velocity_command: Optional velocity command (num_envs, 3).
                       If None, uses stored target_velocity.

    Returns:
      Joint position targets of shape (num_envs, 12).
    """
    # Update target velocity if provided
    if velocity_command is not None:
      self.target_velocity = velocity_command

    # Extract forward velocity (x-axis)
    vx = self.target_velocity[:, 0]  # (num_envs,)

    # Map velocity to frequency: v = 0 → f = 0.5, v = 1.0 → f = 2.0
    # frequency = base_frequency * (0.5 + velocity)
    frequency = self.base_frequency * (0.5 + torch.clamp(vx, 0.0, 1.5))

    # Map velocity to stride length (thigh amplitude)
    # Higher velocity → larger stride
    stride_scale = 0.7 + torch.clamp(vx, 0.0, 1.0) * 0.5  # 0.7 to 1.2

    # Update time
    self.time += dt

    # Compute phase for each joint
    # Use per-env frequency
    phase = 2 * math.pi * frequency.unsqueeze(1) * self.time.unsqueeze(
      1
    ) + self.phase_offset.unsqueeze(0)

    # Scale amplitude based on velocity
    # Only scale thigh (index 1, 4, 7, 10) for stride length
    amplitude = self.base_amplitude.unsqueeze(0).repeat(self.num_envs, 1)
    thigh_indices = [1, 4, 7, 10]
    for idx in thigh_indices:
      amplitude[:, idx] = amplitude[:, idx] * stride_scale

    # Compute sinusoidal trajectory
    actions = amplitude * torch.sin(phase) + self.offset.unsqueeze(0)

    return actions

  def set_frequency(self, frequency: float):
    """Update base oscillation frequency."""
    self.base_frequency = frequency
