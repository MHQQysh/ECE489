"""CPG controller with forward locomotion for Go2."""

import math

import torch


class CPGControllerForward:
  """CPG controller optimized for forward walking."""

  def __init__(
    self,
    num_envs: int,
    device: str,
    frequency: float = 1.5,
  ):
    """Initialize CPG for forward walking.

    Args:
      num_envs: Number of parallel environments.
      device: Device to run on.
      frequency: Oscillation frequency in Hz.
    """
    self.num_envs = num_envs
    self.device = device
    self.frequency = frequency

    # Leg order: FR, FL, RR, RL (前右、前左、后右、后左)
    # Each leg has 3 joints: hip, thigh, calf

    # Trot gait: diagonal legs move together
    # FR and RL swing together (phase 0)
    # FL and RR swing together (phase π)
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

    # Joint amplitudes - WITHIN joint limits!
    # Go2 joint ranges:
    # Hip: [-1.05, 1.05] rad
    # Thigh: [-1.57, 3.49] rad
    # Calf: [-2.72, -0.84] rad (MUST BE NEGATIVE!)
    self.amplitude = torch.tensor(
      [
        0.3,
        0.8,
        0.6,  # FR: calf amplitude must keep it in [-2.72, -0.84]
        0.3,
        0.8,
        0.6,  # FL
        0.3,
        0.8,
        0.6,  # RR
        0.3,
        0.8,
        0.6,  # RL
      ],
      device=device,
    )

    # Joint offsets - centered in valid range
    # Calf offset: center of [-2.72, -0.84] = -1.78
    self.offset = torch.tensor(
      [
        0.0,
        0.9,
        -1.78,  # FR: calf stays in valid range
        0.0,
        0.9,
        -1.78,  # FL
        0.0,
        0.9,
        -1.78,  # RR
        0.0,
        0.9,
        -1.78,  # RL
      ],
      device=device,
    )

    # Time counter
    self.time = torch.zeros(num_envs, device=device)

  def reset(self, env_ids: torch.Tensor | None = None):
    """Reset time counter."""
    if env_ids is None:
      self.time.zero_()
    else:
      self.time[env_ids] = 0.0

  def compute_actions(self, dt: float) -> torch.Tensor:
    """Compute joint position targets.

    Args:
      dt: Time step in seconds.

    Returns:
      Joint position targets of shape (num_envs, 12).
    """
    # Update time
    self.time += dt

    # Compute phase for each joint
    phase = 2 * math.pi * self.frequency * self.time.unsqueeze(
      1
    ) + self.phase_offset.unsqueeze(0)

    # Compute sinusoidal trajectory
    actions = self.amplitude * torch.sin(phase) + self.offset

    return actions

  def set_frequency(self, frequency: float):
    """Update oscillation frequency."""
    self.frequency = frequency
