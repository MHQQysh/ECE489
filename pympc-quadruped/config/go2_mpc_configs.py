"""Go2-specific MPC configuration.

This module contains MPC parameters tuned for the Unitree Go2 robot,
which is lighter and more agile than the Aliengo.
"""

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from typing import List
import numpy as np

from config.linear_mpc_configs import LinearMpcConfig


class Go2MpcConfig(LinearMpcConfig):
    """MPC configuration optimized for Unitree Go2.
    
    Key differences from Aliengo:
    - Lower desired velocity for stability
    - Adjusted Q/R weights for lighter mass
    - Different friction parameters
    """
    
    # Control timestep (same as base)
    dt_control: float = 0.001
    
    # MPC update interval (solver frequency)
    # 20 iterations at 1ms = 20ms MPC update rate
    # This is a balance between computation and responsiveness
    iteration_between_mpc: int = 20
    
    # MPC timestep (time between each step in the prediction horizon)
    dt_mpc: float = 0.02  # 20ms steps
    
    # Prediction horizon
    # 16 steps * 20ms = 320ms lookahead
    horizon: int = 16
    
    # Physical parameters
    gravity: np.float32 = 9.81
    
    # Friction coefficient for ground contact
    # Go2 typically operates on flat surfaces
    # Use 0.6-0.7 for rubber feet on smooth floors
    friction_coef: float = 0.6
    
    # QP weights for state and input
    # State: [roll, pitch, yaw, x, y, z, wx, wy, wz, vx, vy, vz, g]
    # 
    # For Go2 stability:
    # - Higher roll/pitch weights to maintain orientation
    # - Moderate velocity tracking weights
    # - Lower Z position weight (we care less about exact height)
    Q: np.ndarray = np.diag([
        8.,    # roll - higher than Aliengo for tighter balance
        8.,    # pitch - higher than Aliengo
        10.,   # yaw
        10.,   # x position
        10.,   # y position  
        30.,   # z position - higher to maintain height
        0.02,  # roll rate (wx)
        0.02,  # pitch rate (wy)
        0.2,   # yaw rate (wz)
        0.3,   # vx - moderate velocity tracking
        0.3,   # vy
        0.2,   # vz
        0.     # gravity (not directly controlled)
    ])
    
    # Input weights - regularize contact forces
    # Lower weights allow larger forces but may cause jitter
    # Higher weights smooth forces but reduce responsiveness
    R: np.ndarray = np.diag([
        1e-5, 1e-5, 1e-5,   # FL foot
        1e-5, 1e-5, 1e-5,   # FR foot
        1e-5, 1e-5, 1e-5,   # RL foot
        1e-5, 1e-5, 1e-5    # RR foot
    ])
    
    # Default velocity commands for Go2
    # Conservative defaults for stability
    cmd_xvel: float = 0.5   # m/s forward (slower than Aliengo's 1.0)
    cmd_yvel: float = 0.0    # m/s lateral
    cmd_yaw_turn_rate: float = 0.0  # rad/s


class Go2MpcConfigFast(Go2MpcConfig):
    """Go2 MPC with faster velocity commands."""
    
    cmd_xvel: float = 1.0   # m/s forward
    cmd_yvel: float = 0.0
    cmd_yaw_turn_rate: float = 0.0


class Go2MpcConfigTurning(Go2MpcConfig):
    """Go2 MPC configured for turning in place."""
    
    cmd_xvel: float = 0.0
    cmd_yvel: float = 0.0
    cmd_yaw_turn_rate: float = 0.5  # rad/s turn rate
