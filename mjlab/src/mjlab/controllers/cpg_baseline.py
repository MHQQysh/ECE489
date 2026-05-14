"""CPG-like baseline controller with sinusoidal joint trajectories."""

import math
from typing import Literal

import torch


class CPGController:
  """Central Pattern Generator baseline controller.

  Generates open-loop sinusoidal joint trajectories for quadruped locomotion.
  """

  def __init__(
    self,
    num_envs: int,
    device: str,
    gait: Literal["trot", "walk", "pace"] = "trot",
    frequency: float = 2.0,
    amplitude_hip: float = 0.3,
    amplitude_thigh: float = 0.6,
    amplitude_calf: float = 0.8,
    offset_hip: float = 0.0,
    offset_thigh: float = 0.9,
    offset_calf: float = -1.8,
  ):
    """Initialize CPG controller.

    Args:
      num_envs: Number of parallel environments.
      device: Device to run on.
      gait: Gait pattern (trot, walk, or pace).
      frequency: Oscillation frequency in Hz.
      amplitude_hip: Hip joint amplitude in radians.
      amplitude_thigh: Thigh joint amplitude in radians.
      amplitude_calf: Calf joint amplitude in radians.
      offset_hip: Hip joint offset in radians.
      offset_thigh: Thigh joint offset in radians.
      offset_calf: Calf joint offset in radians.
    """
    self.num_envs = num_envs
    self.device = device
    self.gait = gait
    self.frequency = frequency

    # Joint amplitudes and offsets
    self.amplitude = torch.tensor(
      [amplitude_hip, amplitude_thigh, amplitude_calf] * 4,
      device=device,
    )
    self.offset = torch.tensor(
      [offset_hip, offset_thigh, offset_calf] * 4,
      device=device,
    )

    # Phase offsets for different gaits
    # Leg order: FR, FL, RR, RL
    if gait == "trot":
      # Diagonal pairs move together: (FR, RL) and (FL, RR)
      self.phase_offset = torch.tensor(
        [0.0, math.pi, math.pi, 0.0],
        device=device,
      )
    elif gait == "walk":
      # Sequential: FR -> RR -> FL -> RL
      self.phase_offset = torch.tensor(
        [0.0, math.pi, 0.5 * math.pi, 1.5 * math.pi],
        device=device,
      )
    elif gait == "pace":
      # Lateral pairs: (FR, FL) and (RR, RL)
      self.phase_offset = torch.tensor(
        [0.0, 0.0, math.pi, math.pi],
        device=device,
      )
    else:
      raise ValueError(f"Unknown gait: {gait}")

    # Expand phase offset to all joints (3 per leg)
    self.phase_offset = self.phase_offset.repeat_interleave(3)

    # Time counter
    self.time = torch.zeros(num_envs, device=device)

  def reset(self, env_ids: torch.Tensor | None = None):
    """Reset time counter for specified environments."""
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

  def set_amplitude(
    self, amplitude_hip: float, amplitude_thigh: float, amplitude_calf: float
  ):
    """Update joint amplitudes."""
    self.amplitude = torch.tensor(
      [amplitude_hip, amplitude_thigh, amplitude_calf] * 4,
      device=self.device,
    )
