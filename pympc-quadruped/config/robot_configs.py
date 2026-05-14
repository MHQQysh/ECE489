import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import numpy as np

from utils.dynamics import make_com_inertial_matrix

class RobotConfig:
    mass_base: float
    base_height_des: float
    base_inertia_base: np.ndarray

    fz_max: float

    swing_height: float
    foot_radius: float
    Kp_swing: np.ndarray
    Kd_swing: np.ndarray


class AliengoConfig(RobotConfig):
    mass_base: float = 9.042
    base_height_des: float = 0.38
    base_inertia_base = make_com_inertial_matrix(
        ixx=0.033260231,
        ixy=-0.000451628,
        ixz=0.000487603,
        iyy=0.16117211,
        iyz=4.8356e-05,
        izz=0.17460442
    )

    fz_max = 500.

    swing_height = 0.1
    foot_radius = 0.0255
    Kp_swing = np.diag([200., 200., 200.])
    Kd_swing = np.diag([20., 20., 20.])


class Go2Config(RobotConfig):
    """Unitree Go2 robot configuration.
    
    Physical parameters from Unitree specifications:
    - Mass: ~6.9 kg (lighter than Aliengo's 9.0 kg)
    - Leg length: 0.213 m (calf) + thigh proportions
    - Foot radius: 0.022 m
    - Base inertia is anisotropic (ixx > iyy > izz)
    """
    
    # Mass and geometry
    mass_base: float = 6.921  # kg
    
    # Desired base height - Go2 stands lower than Aliengo
    # With default joint angles (thigh ~0.9 rad, calf ~-1.8 rad), 
    # the feet reach approximately 0.32m above ground
    base_height_des: float = 0.32
    
    # Inertia matrix in base frame (body-fixed)
    # Note: ixx > iyy > izz due to elongated trunk shape
    base_inertia_base = make_com_inertial_matrix(
        ixx=0.107027,  # About x-axis (roll)
        ixy=0.,
        ixz=0.,
        iyy=0.0980771,  # About y-axis (pitch)
        iyz=0.,
        izz=0.0244531   # About z-axis (yaw)
    )

    # Maximum vertical contact force per foot
    # Conservative limit to prevent excessive penetration
    fz_max = 350.  # N (Go2 is lighter than Aliengo)

    # Swing foot parameters
    swing_height = 0.05   # Lower swing for smaller robot (was 0.06)
    foot_radius = 0.022   # Go2 foot radius

    # Swing leg PD gains - tuned for Go2's lighter mass
    # Lower gains than Aliengo since Go2 has less mass/inertia
    # Too high gains cause oscillation, too low causes sluggish response
    # Kp_swing = np.diag([150.0, 150.0, 300.0])
    # Kd_swing = np.diag([15.0, 15.0, 30.0])
    Kp_swing = np.diag([400.0, 400.0, 400.0])
    Kd_swing = np.diag([40.0, 40.0, 40.0])


class Go2ConfigAggressive(Go2Config):
    """Go2 configuration with more aggressive gains for faster response."""
    
    Kp_swing = np.diag([200.0, 200.0, 200.0])
    Kd_swing = np.diag([20.0, 20.0, 20.0])


class Go2ConfigConservative(Go2Config):
    """Go2 configuration with conservative gains for debugging."""
    
    Kp_swing = np.diag([80.0, 80.0, 80.0])
    Kd_swing = np.diag([8.0, 8.0, 8.0])
