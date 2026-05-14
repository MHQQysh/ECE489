"""带完整轨迹可视化的推力测试脚本

可视化内容：
1. 身体运动轨迹（红色线条）
2. 四个足端轨迹（不同颜色）
3. 推力方向箭头
4. 接触点和接触力
"""

import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import argparse
import time
import mujoco
import mujoco.viewer
import numpy as np

from linear_mpc.gait import Gait
from linear_mpc.leg_controller import LegController
from config.linear_mpc_configs import LinearMpcConfig
from linear_mpc.mpc import ModelPredictiveController
from utils.mujoco_simulation_utils import (
    get_true_simulation_data,
    reset_robot_state,
)
from config.robot_configs import Go2Config
from utils.robot_data import RobotData
from linear_mpc.swing_foot_trajectory_generator import SwingFootTrajectoryGenerator


def run_push_test_with_trajectory():
    """运行带轨迹可视化的推力测试"""

    # 1. 加载模型
    cur_path = os.path.dirname(os.path.abspath(__file__))
    xml_path = os.path.join(cur_path, '../robot/go2/go2.xml')

    model = mujoco.MjModel.from_xml_path(xml_path)
    data = mujoco.MjData(model)
    robot_config = Go2Config

    # 2. 初始化控制器
    predictive_controller = ModelPredictiveController(LinearMpcConfig, robot_config)
    gait = Gait.TROTTING10
    leg_controller = LegController(robot_config.Kp_swing, robot_config.Kd_swing)
    swing_foot_trajs = [SwingFootTrajectoryGenerator(leg_idx, robot_config) for leg_idx in range(4)]

    # 3. 重置机器人状态
    reset_robot_state(model, data, robot_config)
    mujoco.mj_step(model, data)

    # 初始化 RobotData
    urdf_path = os.path.join(cur_path, '../robot/go2/urdf/go2.urdf')
    robot_data = RobotData(urdf_path, state_estimation=False)

    # 4. 启动 viewer
    viewer = mujoco.viewer.launch_passive(model, data)

    # 启用可视化选项
    viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTPOINT] = True
    viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTFORCE] = True

    # 轨迹记录
    body_trajectory = []
    foot_trajectories = [[], [], [], []]
    foot_names = ["FL", "FR", "RL", "RR"]
    foot_colors = [
        [0, 1, 0, 0.8],  # FL: 绿色
        [0, 0, 1, 0.8],  # FR: 蓝色
        [1, 1, 0, 0.8],  # RL: 黄色
        [1, 0, 1, 0.8],  # RR: 紫色
    ]

    # 5. 控制参数
    dt = model.opt.timestep
    duration = 15.0
    num_steps = int(duration / dt)

    push_time = 5.0
    push_duration = 0.1
    push_force = 40.0
    push_step = int(push_time / dt)
    push_end_step = push_step + int(push_duration / dt)

    trunk_body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "trunk")

    vel_base_des = np.array([0.5, 0.0, 0.0])
    yaw_turn_rate_des = 0.0

    iter_counter = 0
    push_applied = False

    print("\n" + "="*80)
    print("推力测试 - 带轨迹可视化")
    print("="*80)
    print(f"持续时间: {duration} 秒")
    print(f"推力时间: {push_time} 秒")
    print(f"推力大小: {push_force} N (侧向)")
    print(f"推力持续: {push_duration} 秒")
    print("\n可视化说明:")
    print("  🔴 红色轨迹: 机器人身体中心")
    print("  🟢 绿色轨迹: FL 足端 (左前)")
    print("  🔵 蓝色轨迹: FR 足端 (右前)")
    print("  🟡 黄色轨迹: RL 足端 (左后)")
    print("  🟣 紫色轨迹: RR 足端 (右后)")
    print("  ⚡ 红色球体: 推力施加点")
    print("  🔵 蓝色点: 接触点")
    print("  🔴 红色箭头: 接触力")
    print("="*80 + "\n")

    # 6. 控制循环
    for step in range(num_steps):
        current_time = step * dt

        # 获取机器人状态
        sensor_data = get_true_simulation_data(model, data)
        robot_data.update(
            pos_base=sensor_data[0],
            lin_vel_base=sensor_data[1],
            quat_base=sensor_data[2],
            ang_vel_base=sensor_data[3],
            q=sensor_data[4],
            qdot=sensor_data[5],
        )

        # 更新步态
        gait.set_iteration(predictive_controller.iterations_between_mpc, iter_counter)
        swing_states = gait.get_swing_state()
        gait_table = gait.get_gait_table()

        # MPC 计算接触力
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

        # 摆动足轨迹
        pos_targets_swingfeet = np.zeros((4, 3))
        vel_targets_swingfeet = np.zeros((4, 3))

        for leg_idx in range(4):
            if swing_states[leg_idx] > 0:
                swing_foot_trajs[leg_idx].set_foot_placement(
                    robot_data, gait, vel_base_des, yaw_turn_rate_des
                )
                base_pos_base_swingfoot_des, base_vel_base_swingfoot_des = \
                    swing_foot_trajs[leg_idx].compute_traj_swingfoot(
                        robot_data, gait
                    )
                pos_targets_swingfeet[leg_idx, :] = base_pos_base_swingfoot_des
                vel_targets_swingfeet[leg_idx, :] = base_vel_base_swingfoot_des

        # 腿部控制
        tau = leg_controller.update(
            robot_data,
            contact_forces,
            swing_states,
            pos_targets_swingfeet,
            vel_targets_swingfeet,
        )

        # 应用控制
        data.ctrl[:] = tau

        # ========== 记录轨迹 ==========
        if step % 5 == 0:  # 每 5 步记录一次
            body_trajectory.append(robot_data.pos_base.copy())
            for leg_idx in range(4):
                foot_trajectories[leg_idx].append(robot_data.pos_feet[leg_idx].copy())

        # ========== 绘制轨迹 ==========
        # 绘制身体轨迹（红色线条）
        if len(body_trajectory) > 1:
            for i in range(len(body_trajectory) - 1):
                p1 = body_trajectory[i]
                p2 = body_trajectory[i + 1]
                mid = (p1 + p2) / 2
                length = np.linalg.norm(p2 - p1)
                if length > 0.001:
                    viewer.add_marker(
                        pos=mid,
                        size=[length/2, 0.003, 0.003],
                        rgba=[1, 0, 0, 0.6],
                        type=mujoco.mjtGeom.mjGEOM_CAPSULE,
                        label=""
                    )

        # 绘制足端轨迹（彩色线条）
        for leg_idx in range(4):
            if len(foot_trajectories[leg_idx]) > 1:
                for i in range(len(foot_trajectories[leg_idx]) - 1):
                    p1 = foot_trajectories[leg_idx][i]
                    p2 = foot_trajectories[leg_idx][i + 1]
                    mid = (p1 + p2) / 2
                    length = np.linalg.norm(p2 - p1)
                    if length > 0.001:
                        viewer.add_marker(
                            pos=mid,
                            size=[length/2, 0.002, 0.002],
                            rgba=foot_colors[leg_idx],
                            type=mujoco.mjtGeom.mjGEOM_CAPSULE,
                            label=""
                        )

        # 绘制当前足端位置（大球）
        for leg_idx in range(4):
            viewer.add_marker(
                pos=robot_data.pos_feet[leg_idx],
                size=[0.02, 0.02, 0.02],
                rgba=foot_colors[leg_idx],
                type=mujoco.mjtGeom.mjGEOM_SPHERE,
                label=foot_names[leg_idx]
            )

        # ========== 施加推力 ==========
        if step == push_step:
            data.xfrc_applied[trunk_body_id, 1] = push_force
            push_applied = True
            print(f"\n{'='*80}")
            print(f"⚡⚡⚡ 在 {current_time:.2f}s 施加 {push_force}N 侧向推力！")
            print(f"{'='*80}\n")

        elif step == push_end_step:
            data.xfrc_applied[trunk_body_id, :] = 0.0
            print(f"\n{'='*80}")
            print(f"✋ 在 {current_time:.2f}s 移除推力")
            print(f"{'='*80}\n")

        # 可视化推力
        if push_step <= step < push_end_step:
            push_pos = robot_data.pos_base.copy()

            # 推力起点（大红球）
            viewer.add_marker(
                pos=push_pos,
                size=[0.06, 0.06, 0.06],
                rgba=[1, 0, 0, 1],
                type=mujoco.mjtGeom.mjGEOM_SPHERE,
                label="PUSH!"
            )

            # 推力方向箭头
            arrow_length = 0.3
            arrow_end = push_pos + np.array([0, arrow_length, 0])

            # 箭头杆
            viewer.add_marker(
                pos=(push_pos + arrow_end) / 2,
                size=[arrow_length/2, 0.01, 0.01],
                rgba=[1, 0.5, 0, 1],
                type=mujoco.mjtGeom.mjGEOM_CAPSULE,
                label=""
            )

            # 箭头头
            viewer.add_marker(
                pos=arrow_end,
                size=[0.04, 0.04, 0.04],
                rgba=[1, 0.5, 0, 1],
                type=mujoco.mjtGeom.mjGEOM_SPHERE,
                label=""
            )

        # 显示状态信息
        if step % 500 == 0:
            height = robot_data.pos_base[2]
            vel = np.linalg.norm(robot_data.lin_vel_base[:2])
            roll = np.rad2deg(robot_data.rpy_base[0])
            pitch = np.rad2deg(robot_data.rpy_base[1])

            if push_applied and step > push_step:
                time_after_push = current_time - push_time
                print(f"[{current_time:.1f}s] 推力后 {time_after_push:.1f}s | "
                      f"高度: {height:.3f}m | 速度: {vel:.2f}m/s | "
                      f"Roll: {roll:.1f}° | Pitch: {pitch:.1f}°")
            else:
                print(f"[{current_time:.1f}s] 正常行走 | "
                      f"高度: {height:.3f}m | 速度: {vel:.2f}m/s | "
                      f"Roll: {roll:.1f}° | Pitch: {pitch:.1f}°")

        # 仿真步进
        mujoco.mj_step(model, data)

        # 更新 viewer
        if viewer is not None:
            viewer.sync()

        iter_counter += 1

    print("\n" + "="*80)
    print("演示结束")
    print(f"身体轨迹点数: {len(body_trajectory)}")
    print(f"总行走距离: {np.linalg.norm(body_trajectory[-1][:2] - body_trajectory[0][:2]):.2f} m")
    print("="*80)

    # 关闭 viewer
    if viewer is not None:
        viewer.close()


if __name__ == "__main__":
    print("\n启动推力测试 - 带轨迹可视化...")
    print("请观察 MuJoCo viewer 中的彩色轨迹\n")

    run_push_test_with_trajectory()
