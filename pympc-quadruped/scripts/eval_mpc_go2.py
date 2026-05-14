"""MuJoCo Go2 evaluation for the linear MPC quadruped controller.

Evaluates the MPC controller with the same metrics as the RL evaluation:
1. Velocity tracking (separate x and y RMSE)
2. Body stability (roll/pitch std)
3. Energy efficiency (CoT)

Visualization includes velocity arrows (green=desired, red=actual).
"""

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import argparse
import time
import numpy as np
from dataclasses import dataclass
from pathlib import Path
from scipy.spatial.transform import Rotation

import mujoco
from mujoco import viewer as mujoco_viewer

from linear_mpc.gait import Gait
from linear_mpc.leg_controller import LegController
from config.linear_mpc_configs import LinearMpcConfig
from linear_mpc.mpc import ModelPredictiveController
from utils.mujoco_foot_trajectory_visualization import update_viewer_foot_trajectories
from utils.mujoco_simulation_utils import (
    get_simulated_sensor_data,
    get_true_simulation_data,
    reset_robot_state,
)
from utils.mujoco_viewer_utils import (
    center_viewer_on_robot,
    get_viewer_update_interval,
    update_viewer_monitor,
)
from config.robot_configs import Go2Config
from utils.robot_data import RobotData
from linear_mpc.swing_foot_trajectory_generator import SwingFootTrajectoryGenerator


STATE_ESTIMATION = False


@dataclass
class EvalResult:
    """Evaluation results matching RL eval format."""
    terrain: str
    commanded_vel_x: float
    commanded_vel_y: float
    vel_x_rmse: float = 0.0
    vel_y_rmse: float = 0.0
    roll_std: float = 0.0
    pitch_std: float = 0.0
    cot: float = 0.0
    mean_vel_x: float = 0.0
    mean_vel_y: float = 0.0
    mean_roll: float = 0.0
    mean_pitch: float = 0.0
    total_energy: float = 0.0
    mean_torque: float = 0.0
    distance: float = 0.0


def get_roll_pitch_deg(quat):
    """Convert quaternion [w,x,y,z] to roll, pitch in degrees."""
    rot = Rotation.from_quat([quat[1], quat[2], quat[3], quat[0]])
    euler = rot.as_euler("xyz", degrees=True)
    return euler[0], euler[1]


def parse_args():
    """Parse evaluation options."""
    parser = argparse.ArgumentParser(
        description="Run the Go2 MPC evaluation with velocity tracking metrics."
    )
    parser.add_argument(
        "--terrain",
        type=str,
        default="flat",
        choices=["flat", "slope"],
        help="Terrain type (flat or slope)",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=0,
        help="Number of simulation steps. Use 0 to run until interrupted.",
    )
    parser.add_argument(
        "--no-viewer",
        action="store_true",
        help="Run without opening the MuJoCo passive viewer.",
    )
    parser.add_argument(
        "--monitor-rate",
        type=float,
        default=5.0,
        help="Viewer monitor overlay refresh rate in Hz.",
    )
    parser.add_argument(
        "--foot-traj-rate",
        type=float,
        default=40.0,
        help="Viewer swing-foot trajectory redraw rate in Hz.",
    )
    parser.add_argument(
        "--foot-traj-samples",
        type=int,
        default=64,
        help="Samples across the MPC horizon for each visualized foot trajectory.",
    )
    parser.add_argument(
        "--gait",
        type=str,
        default="trotting10",
        choices=["standing", "trotting10", "trotting16", "pacing10", "pacing16", "jumping16"],
        help="Gait pattern to use.",
    )
    parser.add_argument(
        "--xvel",
        type=float,
        default=None,
        help="Desired forward velocity in m/s. Default: uses LinearMpcConfig value.",
    )
    parser.add_argument(
        "--yvel",
        type=float,
        default=None,
        help="Desired lateral velocity in m/s. Default: uses LinearMpcConfig value.",
    )
    parser.add_argument(
        "--yaw-rate",
        type=float,
        default=None,
        help="Desired yaw turn rate in rad/s. Default: uses LinearMpcConfig value.",
    )
    # Evaluation specific args
    parser.add_argument(
        "--eval-trials",
        type=int,
        default=10,
        help="Number of trials for evaluation.",
    )
    parser.add_argument(
        "--eval-steps",
        type=int,
        default=1000,
        help="Steps per trial for evaluation. With 3s delay, ~1s of recording at 1ms dt.",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=100,
        help="Warmup steps before recording.",
    )
    parser.add_argument(
        "--eval-delay",
        type=float,
        default=3.0,
        help="Delay before starting evaluation (seconds). Default: 3.0",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="doc/mpc_go2_eval_results.csv",
        help="Output CSV path for evaluation results.",
    )
    return parser.parse_args()


def run_control_loop(
    model,
    data,
    robot_config,
    robot_data,
    steps=0,
    viewer=None,
    monitor_rate=20.0,
    foot_traj_rate=20.0,
    foot_traj_samples=256,
    gait_name="trotting10",
    xvel=1.2,
    yvel=0.0,
    yaw_rate=0.0,
):
    """Run the closed-loop locomotion controller with visualization."""
    predictive_controller = ModelPredictiveController(LinearMpcConfig, robot_config)
    leg_controller = LegController(robot_config.Kp_swing, robot_config.Kd_swing)

    gait_map = {
        "standing": Gait.STANDING,
        "trotting10": Gait.TROTTING10,
        "trotting16": Gait.TROTTING16,
        "pacing10": Gait.PACING10,
        "pacing16": Gait.PACING16,
        "jumping16": Gait.JUMPING16,
    }
    gait = gait_map[gait_name]
    swing_foot_trajs = [SwingFootTrajectoryGenerator(leg_idx, robot_config) for leg_idx in range(4)]

    vel_base_des = np.array([xvel, yvel, 0.])
    yaw_turn_rate_des = yaw_rate

    iter_counter = 0
    monitor_update_interval = get_viewer_update_interval(model, monitor_rate)
    foot_traj_update_interval = get_viewer_update_interval(model, foot_traj_rate)
    wall_start = time.monotonic()
    sim_start = data.time

    while steps == 0 or iter_counter < steps:
        if viewer is not None and not viewer.is_running():
            break

        if not STATE_ESTIMATION:
            sensor_data = get_true_simulation_data(model, data)
        else:
            sensor_data = get_simulated_sensor_data(data)

        robot_data.update(
            pos_base=sensor_data[0],
            lin_vel_base=sensor_data[1],
            quat_base=sensor_data[2],
            ang_vel_base=sensor_data[3],
            q=sensor_data[4],
            qdot=sensor_data[5],
        )

        gait.set_iteration(predictive_controller.iterations_between_mpc, iter_counter)
        swing_states = gait.get_swing_state()
        gait_table = gait.get_gait_table()

        predictive_controller.update_robot_state(robot_data)
        contact_forces = predictive_controller.update_mpc_if_needed(
            iter_counter,
            vel_base_des,
            yaw_turn_rate_des,
            gait_table,
            solver='drake',
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
                base_pos, base_vel = swing_foot_trajs[leg_idx].compute_traj_swingfoot(
                    robot_data, gait
                )
                pos_targets_swingfeet[leg_idx, :] = base_pos
                vel_targets_swingfeet[leg_idx, :] = base_vel

        torque_cmds = leg_controller.update(
            robot_data,
            contact_forces,
            swing_states,
            pos_targets_swingfeet,
            vel_targets_swingfeet,
        )
        data.ctrl[:] = torque_cmds

        mujoco.mj_step(model, data)

        if viewer is not None:
            center_viewer_on_robot(viewer, data)

            # Compute velocity in world frame for visualization
            vel_base_des_world = robot_data.R_base @ vel_base_des
            lin_vel_base_world = robot_data.lin_vel_base

            if (
                foot_traj_update_interval is not None
                and iter_counter % foot_traj_update_interval == 0
            ):
                update_viewer_foot_trajectories(
                    viewer,
                    robot_data,
                    swing_foot_trajs,
                    gait,
                    iter_counter,
                    predictive_controller.iterations_between_mpc,
                    predictive_controller.horizon,
                    predictive_controller.dt,
                    vel_base_des,
                    yaw_turn_rate_des,
                    swing_states,
                    contact_forces,
                    foot_traj_samples,
                    vel_base_des_world,
                    lin_vel_base_world,
                )

            if (
                monitor_update_interval is not None
                and iter_counter % monitor_update_interval == 0
            ):
                elapsed_wall_time = max(time.monotonic() - wall_start, 1e-9)
                real_time_factor = (data.time - sim_start) / elapsed_wall_time
                update_viewer_monitor(
                    viewer,
                    data,
                    robot_data,
                    predictive_controller,
                    gait,
                    swing_states,
                    contact_forces,
                    vel_base_des,
                    yaw_turn_rate_des,
                    iter_counter,
                    monitor_rate,
                    real_time_factor,
                    vel_base_des_world,
                    lin_vel_base_world,
                )
            viewer.sync()

        iter_counter += 1
        time.sleep(0.0002)

        if iter_counter == 50000:
            reset_robot_state(model, data, robot_config)
            if viewer is not None:
                viewer.user_scn.ngeom = 0
            iter_counter = 0


def run_evaluation(
    model,
    data,
    robot_config,
    robot_data,
    commanded_vel_x,
    commanded_vel_y,
    gait_name="trotting10",
    num_trials=10,
    steps_per_trial=1000,
    warmup_steps=100,
    eval_delay=2.0,
):
    """Run evaluation trials and return metrics.

    Recording starts after warmup_steps + eval_delay seconds to let the robot reach steady state.
    Total steps per trial = warmup_steps + eval_delay_steps + steps_per_trial.
    """
    predictive_controller = ModelPredictiveController(LinearMpcConfig, robot_config)
    leg_controller = LegController(robot_config.Kp_swing, robot_config.Kd_swing)

    gait_map = {
        "standing": Gait.STANDING,
        "trotting10": Gait.TROTTING10,
        "trotting16": Gait.TROTTING16,
        "pacing10": Gait.PACING10,
        "pacing16": Gait.PACING16,
        "jumping16": Gait.JUMPING16,
    }
    gait = gait_map[gait_name]
    swing_foot_trajs = [SwingFootTrajectoryGenerator(leg_idx, robot_config) for leg_idx in range(4)]

    vel_base_des = np.array([commanded_vel_x, commanded_vel_y, 0.0])
    yaw_turn_rate_des = 0.0
    dt = model.opt.timestep

    # Calculate steps for eval_delay
    eval_delay_steps = int(eval_delay / dt)
    # Recording starts after warmup + eval_delay
    recording_start_step = warmup_steps + eval_delay_steps

    all_vel_x, all_vel_y, all_roll, all_pitch, all_energy, all_displacement = [], [], [], [], [], []

    for trial in range(num_trials):
        reset_robot_state(model, data, robot_config)
        mujoco.mj_step(model, data)

        iter_counter = 0

        # Warmup + transient phase (before recording)
        for step in range(recording_start_step):
            sensor_data = get_true_simulation_data(model, data)
            robot_data.update(
                pos_base=sensor_data[0],
                lin_vel_base=sensor_data[1],
                quat_base=sensor_data[2],
                ang_vel_base=sensor_data[3],
                q=sensor_data[4],
                qdot=sensor_data[5],
            )

            gait.set_iteration(predictive_controller.iterations_between_mpc, iter_counter)
            swing_states = gait.get_swing_state()
            gait_table = gait.get_gait_table()

            predictive_controller.update_robot_state(robot_data)
            contact_forces = predictive_controller.update_mpc_if_needed(
                iter_counter, vel_base_des, yaw_turn_rate_des, gait_table,
                solver='drake', debug=False, iter_debug=0,
            )

            pos_targets_swingfeet = np.zeros((4, 3))
            vel_targets_swingfeet = np.zeros((4, 3))
            for leg_idx in range(4):
                if swing_states[leg_idx] > 0:
                    swing_foot_trajs[leg_idx].set_foot_placement(
                        robot_data, gait, vel_base_des, yaw_turn_rate_des
                    )
                    base_pos, base_vel = swing_foot_trajs[leg_idx].compute_traj_swingfoot(
                        robot_data, gait
                    )
                    pos_targets_swingfeet[leg_idx, :] = base_pos
                    vel_targets_swingfeet[leg_idx, :] = base_vel

            tau = leg_controller.update(
                robot_data, contact_forces, swing_states,
                pos_targets_swingfeet, vel_targets_swingfeet,
            )
            data.ctrl[:] = tau
            mujoco.mj_step(model, data)
            iter_counter += 1

        # Recording phase
        initial_pos = robot_data.pos_base.copy()
        vel_x_h, vel_y_h, roll_h, pitch_h, energy_h = [], [], [], [], []

        for step in range(steps_per_trial):
            sensor_data = get_true_simulation_data(model, data)
            robot_data.update(
                pos_base=sensor_data[0],
                lin_vel_base=sensor_data[1],
                quat_base=sensor_data[2],
                ang_vel_base=sensor_data[3],
                q=sensor_data[4],
                qdot=sensor_data[5],
            )

            gait.set_iteration(predictive_controller.iterations_between_mpc, iter_counter)
            swing_states = gait.get_swing_state()
            gait_table = gait.get_gait_table()

            predictive_controller.update_robot_state(robot_data)
            contact_forces = predictive_controller.update_mpc_if_needed(
                iter_counter, vel_base_des, yaw_turn_rate_des, gait_table,
                solver='drake', debug=False, iter_debug=0,
            )

            pos_targets_swingfeet = np.zeros((4, 3))
            vel_targets_swingfeet = np.zeros((4, 3))
            for leg_idx in range(4):
                if swing_states[leg_idx] > 0:
                    swing_foot_trajs[leg_idx].set_foot_placement(
                        robot_data, gait, vel_base_des, yaw_turn_rate_des
                    )
                    base_pos, base_vel = swing_foot_trajs[leg_idx].compute_traj_swingfoot(
                        robot_data, gait
                    )
                    pos_targets_swingfeet[leg_idx, :] = base_pos
                    vel_targets_swingfeet[leg_idx, :] = base_vel

            tau = leg_controller.update(
                robot_data, contact_forces, swing_states,
                pos_targets_swingfeet, vel_targets_swingfeet,
            )
            data.ctrl[:] = tau

            # Record world-frame velocity
            lin_vel_world = robot_data.lin_vel_base
            vel_x_h.append(lin_vel_world[0])
            vel_y_h.append(lin_vel_world[1])

            quat = robot_data.quat_base
            r, p = get_roll_pitch_deg(quat)
            roll_h.append(r)
            pitch_h.append(p)

            power = np.sum(np.abs(tau * robot_data.qdot))
            energy_h.append(power * dt)

            mujoco.mj_step(model, data)
            iter_counter += 1

        final_pos = robot_data.pos_base
        displacement = np.sqrt(
            (final_pos[0] - initial_pos[0])**2 + (final_pos[1] - initial_pos[1])**2
        )

        all_vel_x.extend(vel_x_h)
        all_vel_y.extend(vel_y_h)
        all_roll.extend(roll_h)
        all_pitch.extend(pitch_h)
        all_energy.extend(energy_h)
        all_displacement.append(displacement)

    # Calculate metrics
    all_vel_x = np.array(all_vel_x)
    all_vel_y = np.array(all_vel_y)
    all_roll = np.array(all_roll)
    all_pitch = np.array(all_pitch)
    all_energy = np.array(all_energy)

    total_energy = np.sum(all_energy)
    avg_displacement = np.mean(all_displacement)
    mass = robot_config.mass_base
    g = 9.81
    cot = total_energy / (avg_displacement * mass * g) if avg_displacement > 0.01 else float('inf')

    vel_x_rmse = np.sqrt(np.mean((all_vel_x - commanded_vel_x)**2))
    vel_y_rmse = np.sqrt(np.mean((all_vel_y - commanded_vel_y)**2))

    return EvalResult(
        terrain="flat",
        commanded_vel_x=commanded_vel_x,
        commanded_vel_y=commanded_vel_y,
        vel_x_rmse=vel_x_rmse,
        vel_y_rmse=vel_y_rmse,
        roll_std=np.std(all_roll),
        pitch_std=np.std(all_pitch),
        cot=cot,
        mean_vel_x=np.mean(all_vel_x),
        mean_vel_y=np.mean(all_vel_y),
        mean_roll=np.mean(all_roll),
        mean_pitch=np.mean(all_pitch),
        total_energy=total_energy,
        mean_torque=np.mean(np.sum(all_energy.reshape(num_trials, -1), axis=1)),
        distance=avg_displacement,
    )


def main():
    args = parse_args()

    cur_path = os.path.dirname(__file__)

    # Load model based on terrain
    if args.terrain == "slope":
        mujoco_xml_path = os.path.join(cur_path, '../robot/go2/go2_slope.xml')
    else:
        mujoco_xml_path = os.path.join(cur_path, '../robot/go2/go2.xml')

    model = mujoco.MjModel.from_xml_path(mujoco_xml_path)
    data = mujoco.MjData(model)
    robot_config = Go2Config

    reset_robot_state(model, data, robot_config)
    mujoco.mj_step(model, data)

    urdf_path = os.path.join(cur_path, '../robot/go2/urdf/go2.urdf')
    robot_data = RobotData(urdf_path, state_estimation=STATE_ESTIMATION)

    xvel = args.xvel if args.xvel is not None else LinearMpcConfig.cmd_xvel
    yvel = args.yvel if args.yvel is not None else LinearMpcConfig.cmd_yvel
    yaw_rate = args.yaw_rate if args.yaw_rate is not None else LinearMpcConfig.cmd_yaw_turn_rate

    print("=" * 60)
    print("MPC EVALUATION - Go2 Robot")
    print("=" * 60)
    print(f"Terrain: {args.terrain}")
    print(f"Gait: {args.gait}")
    print(f"Desired velocity: X={xvel:.2f} m/s, Y={yvel:.2f} m/s")
    print(f"Desired yaw rate: {yaw_rate:.2f} rad/s")
    print("=" * 60)

    if args.no_viewer:
        # Run headless evaluation
        results = []
        test_configs = [
            (1.0, 0.0, "Forward 1.0 m/s"),
            (0.0, 1.0, "Lateral 1.0 m/s"),
            (1.0, 0.5, "Fwd 1.0 + Lat 0.5"),
        ]

        print("\nRunning evaluation trials...")
        for vx, vy, name in test_configs:
            print(f"\n### {name} (vx={vx}, vy={vy}) ###")
            r = run_evaluation(
                model, data, robot_config, robot_data,
                vx, vy,
                gait_name=args.gait,
                num_trials=args.eval_trials,
                steps_per_trial=args.eval_steps,
                warmup_steps=args.warmup,
                eval_delay=args.eval_delay,
            )
            r.terrain = args.terrain
            results.append((args.terrain, name, r))
            print(f"  Vel_X RMSE: {r.vel_x_rmse:.4f} m/s")
            print(f"  Vel_Y RMSE: {r.vel_y_rmse:.4f} m/s")
            print(f"  Mean Vel (world): X={r.mean_vel_x:.4f}, Y={r.mean_vel_y:.4f}")
            print(f"  Roll Std: {r.roll_std:.2f} deg, Pitch Std: {r.pitch_std:.2f} deg")
            print(f"  CoT: {r.cot:.4f}, Distance: {r.distance:.4f} m")

        # Print summary
        print("\n" + "=" * 60)
        print("RESULTS SUMMARY")
        print("=" * 60)

        print("\n### Velocity Tracking ###")
        print(f"{'Terrain':<10} {'Command':<22} {'Vel_X_RMSE':<12} {'Vel_Y_RMSE':<12} {'Mean_X':<10} {'Mean_Y':<10}")
        print("-" * 80)
        for terrain, name, r in results:
            print(f"{terrain:<10} {name:<22} {r.vel_x_rmse:<12.4f} {r.vel_y_rmse:<12.4f} {r.mean_vel_x:<10.4f} {r.mean_vel_y:<10.4f}")

        print("\n### Body Stability ###")
        print(f"{'Terrain':<10} {'Command':<22} {'Roll_Std':<10} {'Pitch_Std':<10} {'Mean_R':<10} {'Mean_P':<10}")
        print("-" * 80)
        for terrain, name, r in results:
            print(f"{terrain:<10} {name:<22} {r.roll_std:<10.2f} {r.pitch_std:<10.2f} {r.mean_roll:<10.2f} {r.mean_pitch:<10.2f}")

        print("\n### Energy Efficiency ###")
        print(f"{'Terrain':<10} {'Command':<22} {'CoT':<12} {'Distance':<10}")
        print("-" * 60)
        for terrain, name, r in results:
            print(f"{terrain:<10} {name:<22} {r.cot:<12.4f} {r.distance:<10.4f}")

        # Save CSV
        output_path = Path(args.output)
        output_path.parent.mkdir(exist_ok=True, parents=True)
        with open(output_path, "w") as f:
            f.write(
                "Terrain,Command,Vel_X_RMSE,Vel_Y_RMSE,Mean_Vel_X,Mean_Vel_Y,"
                "Roll_Std,Pitch_Std,Mean_Roll,Mean_Pitch,CoT,Total_Energy,"
                "Mean_Torque,Distance\n"
            )
            for terrain, name, r in results:
                f.write(
                    f"{r.terrain},{name},{r.vel_x_rmse:.4f},{r.vel_y_rmse:.4f},"
                    f"{r.mean_vel_x:.4f},{r.mean_vel_y:.4f},"
                    f"{r.roll_std:.2f},{r.pitch_std:.2f},"
                    f"{r.mean_roll:.2f},{r.mean_pitch:.2f},"
                    f"{r.cot:.4f},{r.total_energy:.2f},{r.mean_torque:.2f},{r.distance:.4f}\n"
                )
        print(f"\nResults saved to {output_path}")

    else:
        # Run with viewer for visualization
        with mujoco_viewer.launch_passive(model, data) as viewer:
            run_control_loop(
                model,
                data,
                robot_config,
                robot_data,
                steps=args.steps,
                viewer=viewer,
                monitor_rate=args.monitor_rate,
                foot_traj_rate=args.foot_traj_rate,
                foot_traj_samples=args.foot_traj_samples,
                gait_name=args.gait,
                xvel=xvel,
                yvel=yvel,
                yaw_rate=yaw_rate,
            )


if __name__ == '__main__':
    main()
