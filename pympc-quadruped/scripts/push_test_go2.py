"""MuJoCo push test for the Go2 linear MPC controller.

This script applies an external impulse/force disturbance during closed-loop
MPC walking and records simple recovery metrics.
"""

import argparse
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import mujoco
import numpy as np
from mujoco import viewer as mujoco_viewer
from scipy.spatial.transform import Rotation

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.linear_mpc_configs import LinearMpcConfig
from config.robot_configs import Go2Config
from linear_mpc.gait import Gait
from linear_mpc.leg_controller import LegController
from linear_mpc.mpc import ModelPredictiveController
from linear_mpc.swing_foot_trajectory_generator import SwingFootTrajectoryGenerator
from utils.mujoco_simulation_utils import get_true_simulation_data, reset_robot_state
from utils.robot_data import RobotData


STATE_ESTIMATION = False


@dataclass
class PushTestResult:
    push_time_s: float
    push_duration_s: float
    force_n: float
    direction_world_x: float
    direction_world_y: float
    command_vx: float
    command_vy: float
    max_base_speed: float = 0.0
    max_roll_deg: float = 0.0
    max_pitch_deg: float = 0.0
    max_yaw_rate: float = 0.0
    min_base_height: float = 0.0
    max_base_height_drop: float = 0.0
    recovery_time_s: float = 0.0
    fell: bool = False


def get_roll_pitch_yaw_deg(quat):
    rot = Rotation.from_quat([quat[1], quat[2], quat[3], quat[0]])
    return rot.as_euler("xyz", degrees=True)


def parse_args():
    parser = argparse.ArgumentParser(description="Run a push test for Go2 MPC walking.")
    parser.add_argument("--terrain", type=str, default="flat", choices=["flat", "slope"])
    parser.add_argument("--gait", type=str, default="trotting10", choices=["standing", "trotting10", "trotting16", "pacing10", "pacing16", "jumping16"])
    parser.add_argument("--steps", type=int, default=8000, help="Maximum simulation steps.")
    parser.add_argument("--no-viewer", action="store_true", help="Run without the MuJoCo viewer.")
    parser.add_argument("--xvel", type=float, default=None, help="Desired forward velocity in m/s.")
    parser.add_argument("--yvel", type=float, default=None, help="Desired lateral velocity in m/s.")
    parser.add_argument("--yaw-rate", type=float, default=None, help="Desired yaw rate in rad/s.")
    parser.add_argument("--push-time", type=float, default=0.2, help="Time in seconds to start pushing.")
    parser.add_argument("--push-duration", type=float, default=0.08, help="How long the push force is applied.")
    parser.add_argument("--push-force", type=float, default=80.0, help="Magnitude of the horizontal force in newtons.")
    parser.add_argument("--push-angle-deg", type=float, default=180.0, help="Push direction in world frame, degrees. 0=x+, 90=y+.")
    parser.add_argument("--push-height-fraction", type=float, default=0.5, help="Apply force at this fraction of base height (0=ground, 1=base center).")
    parser.add_argument("--recovery-speed-threshold", type=float, default=0.15, help="Speed threshold to consider recovered.")
    parser.add_argument("--recovery-roll-threshold", type=float, default=10.0, help="Roll threshold in degrees for recovery.")
    parser.add_argument("--recovery-pitch-threshold", type=float, default=10.0, help="Pitch threshold in degrees for recovery.")
    parser.add_argument("--output", type=str, default="doc/push_test_go2_results.csv", help="CSV output path.")
    return parser.parse_args()


def apply_push(data, force_world, application_point_world):
    mujoco.mj_applyFT(
        data.model,
        data,
        force_world.reshape(3, 1),
        np.zeros((3, 1)),
        application_point_world.reshape(3, 1),
        0,
        data.qfrc_applied,
    )


def run_push_test(model, data, robot_config, robot_data, args, viewer=None):
    predictive_controller = ModelPredictiveController(LinearMpcConfig, robot_config)
    leg_controller = LegController(robot_config.Kp_swing, robot_config.Kd_swing)
    gait = {
        "standing": Gait.STANDING,
        "trotting10": Gait.TROTTING10,
        "trotting16": Gait.TROTTING16,
        "pacing10": Gait.PACING10,
        "pacing16": Gait.PACING16,
        "jumping16": Gait.JUMPING16,
    }[args.gait]
    swing_foot_trajs = [SwingFootTrajectoryGenerator(i, robot_config) for i in range(4)]

    vel_base_des = np.array([
        args.xvel if args.xvel is not None else LinearMpcConfig.cmd_xvel,
        args.yvel if args.yvel is not None else LinearMpcConfig.cmd_yvel,
        0.0,
    ])
    yaw_turn_rate_des = args.yaw_rate if args.yaw_rate is not None else LinearMpcConfig.cmd_yaw_turn_rate

    dt = model.opt.timestep
    push_start_step = int(args.push_time / dt)
    push_end_step = push_start_step + max(1, int(args.push_duration / dt))
    push_dir = np.deg2rad(args.push_angle_deg)
    force_world = np.array([np.cos(push_dir), np.sin(push_dir), 0.0]) * args.push_force

    max_speed = 0.0
    max_roll = 0.0
    max_pitch = 0.0
    max_yaw_rate = 0.0
    min_height = float("inf")
    base_height_ref = None
    pushed = False
    recovered_at = None
    fell = False

    for step in range(args.steps):
        if viewer is not None and not viewer.is_running():
            break

        sensor_data = get_true_simulation_data(model, data)
        robot_data.update(
            pos_base=sensor_data[0],
            lin_vel_base=sensor_data[1],
            quat_base=sensor_data[2],
            ang_vel_base=sensor_data[3],
            q=sensor_data[4],
            qdot=sensor_data[5],
        )

        if base_height_ref is None:
            base_height_ref = robot_data.pos_base[2]

        gait.set_iteration(predictive_controller.iterations_between_mpc, step)
        swing_states = gait.get_swing_state()
        gait_table = gait.get_gait_table()

        predictive_controller.update_robot_state(robot_data)
        contact_forces = predictive_controller.update_mpc_if_needed(
            step,
            vel_base_des,
            yaw_turn_rate_des,
            gait_table,
            solver="drake",
            debug=False,
            iter_debug=0,
        )

        pos_targets_swingfeet = np.zeros((4, 3))
        vel_targets_swingfeet = np.zeros((4, 3))
        for leg_idx in range(4):
            if swing_states[leg_idx] > 0:
                swing_foot_trajs[leg_idx].set_foot_placement(
                    robot_data, gait, vel_base_des, yaw_turn_rate_des
                )
                base_pos, base_vel = swing_foot_trajs[leg_idx].compute_traj_swingfoot(robot_data, gait)
                pos_targets_swingfeet[leg_idx, :] = base_pos
                vel_targets_swingfeet[leg_idx, :] = base_vel

        tau = leg_controller.update(
            robot_data,
            contact_forces,
            swing_states,
            pos_targets_swingfeet,
            vel_targets_swingfeet,
        )
        data.ctrl[:] = tau

        if push_start_step <= step < push_end_step:
            pushed = True
            application_point_world = robot_data.pos_base.copy()
            application_point_world[2] -= robot_config.base_height_des * (1.0 - args.push_height_fraction)
            apply_push(data, force_world, application_point_world)
        else:
            data.xfrc_applied[:] = 0.0

        roll_deg, pitch_deg, yaw_deg = get_roll_pitch_yaw_deg(robot_data.quat_base)
        speed = np.linalg.norm(robot_data.lin_vel_base[:2])
        yaw_rate = abs(robot_data.ang_vel_base[2])

        max_speed = max(max_speed, speed)
        max_roll = max(max_roll, abs(roll_deg))
        max_pitch = max(max_pitch, abs(pitch_deg))
        max_yaw_rate = max(max_yaw_rate, yaw_rate)
        min_height = min(min_height, robot_data.pos_base[2])

        if viewer is not None:
            viewer.sync()

        mujoco.mj_step(model, data)

        if robot_data.pos_base[2] < 0.18 or abs(roll_deg) > 45 or abs(pitch_deg) > 45:
            fell = True
            break

        if pushed:
            recovered = (
                speed < args.recovery_speed_threshold
                and abs(roll_deg) < args.recovery_roll_threshold
                and abs(pitch_deg) < args.recovery_pitch_threshold
            )
            if recovered and recovered_at is None and step > push_end_step:
                recovered_at = step * dt

    if recovered_at is None:
        recovery_time = float("inf") if not fell else float("nan")
    else:
        recovery_time = recovered_at - args.push_time

    return PushTestResult(
        push_time_s=args.push_time,
        push_duration_s=args.push_duration,
        force_n=args.push_force,
        direction_world_x=float(force_world[0]),
        direction_world_y=float(force_world[1]),
        command_vx=float(vel_base_des[0]),
        command_vy=float(vel_base_des[1]),
        max_base_speed=max_speed,
        max_roll_deg=max_roll,
        max_pitch_deg=max_pitch,
        max_yaw_rate=max_yaw_rate,
        min_base_height=min_height,
        max_base_height_drop=base_height_ref - min_height if base_height_ref is not None else 0.0,
        recovery_time_s=recovery_time,
        fell=fell,
    )


def main():
    args = parse_args()
    cur_path = os.path.dirname(__file__)

    if args.terrain == "slope":
        mujoco_xml_path = os.path.join(cur_path, "..", "robot", "go2", "go2_slope.xml")
    else:
        mujoco_xml_path = os.path.join(cur_path, "..", "robot", "go2", "go2.xml")

    model = mujoco.MjModel.from_xml_path(mujoco_xml_path)
    data = mujoco.MjData(model)
    robot_config = Go2Config

    reset_robot_state(model, data, robot_config)
    mujoco.mj_step(model, data)

    urdf_path = os.path.join(cur_path, "..", "robot", "go2", "urdf", "go2.urdf")
    robot_data = RobotData(urdf_path, state_estimation=STATE_ESTIMATION)

    print("=" * 60)
    print("GO2 PUSH TEST")
    print("=" * 60)
    print(f"Terrain: {args.terrain}")
    print(f"Gait: {args.gait}")
    print(f"Command: vx={args.xvel if args.xvel is not None else LinearMpcConfig.cmd_xvel:.2f} m/s, vy={args.yvel if args.yvel is not None else LinearMpcConfig.cmd_yvel:.2f} m/s")
    print(f"Push: {args.push_force:.1f} N for {args.push_duration:.3f} s at t={args.push_time:.2f} s")
    print(f"Push direction: {args.push_angle_deg:.1f} deg in world frame")
    print("=" * 60)

    if args.no_viewer:
        result = run_push_test(model, data, robot_config, robot_data, args, viewer=None)
    else:
        with mujoco_viewer.launch_passive(model, data) as viewer:
            result = run_push_test(model, data, robot_config, robot_data, args, viewer=viewer)

    print("\nRESULTS")
    print(f"Max base speed: {result.max_base_speed:.3f} m/s")
    print(f"Max roll: {result.max_roll_deg:.2f} deg")
    print(f"Max pitch: {result.max_pitch_deg:.2f} deg")
    print(f"Max yaw rate: {result.max_yaw_rate:.3f} rad/s")
    print(f"Min base height: {result.min_base_height:.3f} m")
    print(f"Base height drop: {result.max_base_height_drop:.3f} m")
    print(f"Recovery time: {result.recovery_time_s}")
    print(f"Fell: {result.fell}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(
            "push_time_s,push_duration_s,force_n,dir_x,dir_y,command_vx,command_vy," 
            "max_base_speed,max_roll_deg,max_pitch_deg,max_yaw_rate,min_base_height," 
            "base_height_drop,recovery_time_s,fell\n"
        )
        f.write(
            f"{result.push_time_s:.4f},{result.push_duration_s:.4f},{result.force_n:.4f},"
            f"{result.direction_world_x:.6f},{result.direction_world_y:.6f},"
            f"{result.command_vx:.4f},{result.command_vy:.4f},"
            f"{result.max_base_speed:.4f},{result.max_roll_deg:.4f},{result.max_pitch_deg:.4f},"
            f"{result.max_yaw_rate:.4f},{result.min_base_height:.4f},"
            f"{result.max_base_height_drop:.4f},{result.recovery_time_s},{int(result.fell)}\n"
        )
    print(f"Saved results to {output_path}")


if __name__ == "__main__":
    main()
