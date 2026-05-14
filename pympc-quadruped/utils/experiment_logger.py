"""实验数据记录器

用于记录 MPC vs CPG 对比实验的所有指标：
1. 速度跟踪误差 (RMS)
2. 身体稳定性 (RMS roll & pitch)
3. 能量效率 (CoT)
4. 鲁棒性 (推力恢复成功率)
"""

import numpy as np
from scipy.spatial.transform import Rotation
from dataclasses import dataclass
from typing import List, Dict
import json
import csv
from pathlib import Path


@dataclass
class ExperimentMetrics:
    """单次实验的指标"""
    # 实验配置
    method: str  # "MPC" or "CPG"
    terrain: str  # "flat" or "slope"
    speed: float  # m/s
    trial: int

    # 指标 1: 速度跟踪误差 (分开 x, y 方向)
    rms_vel_error_x: float  # m/s - X方向RMS误差
    rms_vel_error_y: float  # m/s - Y方向RMS误差
    rms_vel_error: float  # m/s - 综合RMS误差
    mean_vel_error: float  # m/s
    max_vel_error: float  # m/s

    # 指标 2: 身体稳定性
    rms_roll: float  # rad
    rms_pitch: float  # rad
    max_roll: float  # rad
    max_pitch: float  # rad

    # 指标 3: 能量效率
    cot: float  # Cost of Transport (无量纲)
    total_energy: float  # J
    distance: float  # m

    # 指标 4: 鲁棒性
    recovery_success: bool
    recovery_time: float  # s (恢复到稳定状态的时间)
    max_height_drop: float  # m (推力后最大高度下降)


class ExperimentLogger:
    """实验数据记录器"""

    def __init__(self, robot_config, dt):
        """
        Args:
            robot_config: 机器人配置 (AliengoConfig 或 Go2Config)
            dt: 仿真时间步长 (s)
        """
        self.robot_config = robot_config
        self.dt = dt
        self.mass = robot_config.mass_base

        # 数据缓存
        self.reset()

    def reset(self):
        """重置数据缓存"""
        # 指标 1: 速度跟踪 (分开 x, y 方向)
        self.vel_errors_x = []
        self.vel_errors_y = []
        self.vel_errors = []
        self.actual_vels_x = []
        self.actual_vels_y = []
        self.actual_vels = []
        self.desired_vels_x = []
        self.desired_vels_y = []
        self.desired_vels = []

        # 指标 2: 身体稳定性
        self.rolls = []
        self.pitches = []
        self.yaws = []

        # 指标 3: 能量
        self.powers = []  # 瞬时功率 (W)
        self.positions = []  # 位置历史

        # 指标 4: 鲁棒性
        self.heights = []  # 身体高度
        self.push_applied = False
        self.push_time = None
        self.recovery_success = None
        self.recovery_time = None

    def log_step(self, robot_data, cmd_vel_x, cmd_vel_y=0.0, tau=None):
        """
        记录单步数据

        Args:
            robot_data: RobotData 对象
            cmd_vel_x: 期望X方向速度 (m/s)
            cmd_vel_y: 期望Y方向速度 (m/s)
            tau: 关节力矩 (可选)
        """
        # 1. 速度跟踪误差 (分开 x, y 方向)
        vel_x_actual = robot_data.lin_vel_base[0]  # X方向实际速度
        vel_y_actual = robot_data.lin_vel_base[1]  # Y方向实际速度
        vel_error_x = vel_x_actual - cmd_vel_x  # X方向误差
        vel_error_y = vel_y_actual - cmd_vel_y  # Y方向误差
        vel_error = np.sqrt(vel_x_actual**2 + vel_y_actual**2) - np.sqrt(cmd_vel_x**2 + cmd_vel_y**2)

        self.vel_errors_x.append(vel_error_x)
        self.vel_errors_y.append(vel_error_y)
        self.vel_errors.append(vel_error)
        self.actual_vels_x.append(vel_x_actual)
        self.actual_vels_y.append(vel_y_actual)
        self.desired_vels_x.append(cmd_vel_x)
        self.desired_vels_y.append(cmd_vel_y)

        # 2. 身体姿态 (Roll, Pitch, Yaw)
        quat = robot_data.quat_base  # [w, x, y, z]
        # 转换为 scipy 格式 [x, y, z, w]
        r = Rotation.from_quat([quat[1], quat[2], quat[3], quat[0]])
        roll, pitch, yaw = r.as_euler('xyz', degrees=False)
        self.rolls.append(roll)
        self.pitches.append(pitch)
        self.yaws.append(yaw)

        # 3. 能量 (功率 = Σ|τ_i * q̇_i|)
        if tau is not None:
            power = np.sum(np.abs(tau * robot_data.qdot))
        else:
            power = 0.0
        self.powers.append(power)

        # 位置
        self.positions.append(robot_data.pos_base.copy())

        # 4. 高度 (用于鲁棒性检测)
        self.heights.append(robot_data.pos_base[2])

    def mark_push_applied(self, time):
        """标记推力施加时间"""
        self.push_applied = True
        self.push_time = time

    def check_recovery(self, current_time, height_threshold=0.15):
        """
        检查是否从推力中恢复

        Args:
            current_time: 当前时间 (s)
            height_threshold: 高度阈值，低于此值认为摔倒 (m)

        Returns:
            bool: 是否成功恢复
        """
        if not self.push_applied or self.push_time is None:
            return True

        # 检查推力后的高度
        push_step = int(self.push_time / self.dt)
        if push_step >= len(self.heights):
            return True

        heights_after_push = self.heights[push_step:]

        # 检查是否摔倒
        min_height = np.min(heights_after_push)
        if min_height < height_threshold:
            self.recovery_success = False
            self.recovery_time = None
            self.max_height_drop = self.heights[push_step] - min_height
            return False

        # 检查是否恢复稳定 (高度变化小于阈值)
        if len(heights_after_push) > 50:  # 至少 0.5 秒后
            recent_heights = heights_after_push[-50:]
            height_std = np.std(recent_heights)
            if height_std < 0.01:  # 高度稳定
                self.recovery_success = True
                self.recovery_time = current_time - self.push_time
                self.max_height_drop = self.heights[push_step] - np.min(heights_after_push)
                return True

        return None  # 还在恢复中

    def compute_metrics(self) -> Dict:
        """
        计算所有指标

        Returns:
            dict: 包含所有指标的字典
        """
        # 转换为 numpy 数组
        vel_errors_x = np.array(self.vel_errors_x)
        vel_errors_y = np.array(self.vel_errors_y)
        vel_errors = np.array(self.vel_errors)
        actual_vels_x = np.array(self.actual_vels_x)
        actual_vels_y = np.array(self.actual_vels_y)
        rolls = np.array(self.rolls)
        pitches = np.array(self.pitches)
        powers = np.array(self.powers)
        positions = np.array(self.positions)
        heights = np.array(self.heights)

        # 指标 1: 速度跟踪误差 (分开 x, y 方向)
        rms_vel_error_x = np.sqrt(np.mean(vel_errors_x**2))
        rms_vel_error_y = np.sqrt(np.mean(vel_errors_y**2))
        rms_vel_error = np.sqrt(np.mean(vel_errors**2))
        mean_vel_error = np.mean(np.abs(vel_errors))
        max_vel_error = np.max(np.abs(vel_errors))

        # 指标 2: 身体稳定性
        rms_roll = np.sqrt(np.mean(rolls**2))
        rms_pitch = np.sqrt(np.mean(pitches**2))
        max_roll = np.max(np.abs(rolls))
        max_pitch = np.max(np.abs(pitches))

        # 指标 3: 能量效率 (CoT)
        total_energy = np.sum(powers) * self.dt  # J
        distance = np.linalg.norm(positions[-1, :2] - positions[0, :2])  # m
        g = 9.81  # m/s^2
        cot = total_energy / (self.mass * g * distance) if distance > 0.1 else float('inf')

        # 指标 4: 鲁棒性
        if self.recovery_success is None:
            # 如果没有施加推力，默认成功
            recovery_success = True
            recovery_time = 0.0
            max_height_drop = 0.0
        else:
            recovery_success = self.recovery_success
            recovery_time = self.recovery_time if self.recovery_time else float('inf')
            max_height_drop = self.max_height_drop if hasattr(self, 'max_height_drop') else 0.0

        return {
            # 指标 1 (分开 x, y 方向)
            'rms_vel_error_x': float(rms_vel_error_x),
            'rms_vel_error_y': float(rms_vel_error_y),
            'rms_vel_error': float(rms_vel_error),
            'mean_vel_error': float(mean_vel_error),
            'max_vel_error': float(max_vel_error),

            # 指标 2
            'rms_roll': float(rms_roll),
            'rms_pitch': float(rms_pitch),
            'max_roll': float(max_roll),
            'max_pitch': float(max_pitch),

            # 指标 3
            'cot': float(cot),
            'total_energy': float(total_energy),
            'distance': float(distance),

            # 指标 4
            'recovery_success': bool(recovery_success),
            'recovery_time': float(recovery_time),
            'max_height_drop': float(max_height_drop),
        }

    def save_metrics(self, metrics: ExperimentMetrics, output_dir: str = "experiment_results"):
        """
        保存指标到文件

        Args:
            metrics: ExperimentMetrics 对象
            output_dir: 输出目录
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 1. 保存为 JSON (详细数据)
        json_file = output_path / f"{metrics.method}_{metrics.terrain}_speed{metrics.speed}_trial{metrics.trial}.json"
        with open(json_file, 'w') as f:
            json.dump(metrics.__dict__, f, indent=2)

        # 2. 追加到 CSV (汇总数据)
        csv_file = output_path / "all_results.csv"
        file_exists = csv_file.exists()

        with open(csv_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=metrics.__dict__.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(metrics.__dict__)

        print(f"✅ 结果已保存到: {json_file}")


def apply_push_force(data, trunk_body_id, push_force=40.0, direction='y'):
    """
    施加推力到机器人身体

    Args:
        data: MuJoCo MjData 对象
        trunk_body_id: 身体的 body ID
        push_force: 推力大小 (N)
        direction: 推力方向 ('x', 'y', 'z')
    """
    direction_map = {'x': 0, 'y': 1, 'z': 2}
    axis = direction_map[direction]
    data.xfrc_applied[trunk_body_id, axis] = push_force


# 使用示例
if __name__ == "__main__":
    """使用示例"""

    # 模拟数据
    from config.robot_configs import Go2Config

    robot_config = Go2Config
    dt = 0.001
    logger = ExperimentLogger(robot_config, dt)

    # 模拟 1000 步
    for step in range(1000):
        # 创建模拟的 robot_data
        class MockRobotData:
            vel_base_world = np.array([0.5, 0.0, 0.0])
            quat_base_world = np.array([1.0, 0.0, 0.0, 0.0])
            tau_ff = np.random.randn(12) * 10
            qd_joint = np.random.randn(12) * 0.1
            pos_base_world = np.array([step * 0.001, 0.0, 0.32])

        robot_data = MockRobotData()
        cmd_vel = 0.5

        logger.log_step(robot_data, cmd_vel)

        # 在第 500 步施加推力
        if step == 500:
            logger.mark_push_applied(step * dt)

    # 计算指标
    metrics_dict = logger.compute_metrics()

    # 创建 ExperimentMetrics 对象
    metrics = ExperimentMetrics(
        method="MPC",
        terrain="flat",
        speed=0.5,
        trial=1,
        **metrics_dict
    )

    # 保存结果
    logger.save_metrics(metrics)

    # 打印结果
    print("\n" + "=" * 80)
    print("实验结果")
    print("=" * 80)
    print(f"方法: {metrics.method}")
    print(f"地形: {metrics.terrain}")
    print(f"速度: {metrics.speed} m/s")
    print(f"试验: {metrics.trial}")
    print("\n指标 1: 速度跟踪误差")
    print(f"  RMS 误差: {metrics.rms_vel_error:.4f} m/s")
    print(f"  平均误差: {metrics.mean_vel_error:.4f} m/s")
    print(f"  最大误差: {metrics.max_vel_error:.4f} m/s")
    print("\n指标 2: 身体稳定性")
    print(f"  RMS Roll: {np.rad2deg(metrics.rms_roll):.2f}°")
    print(f"  RMS Pitch: {np.rad2deg(metrics.rms_pitch):.2f}°")
    print(f"  最大 Roll: {np.rad2deg(metrics.max_roll):.2f}°")
    print(f"  最大 Pitch: {np.rad2deg(metrics.max_pitch):.2f}°")
    print("\n指标 3: 能量效率")
    print(f"  CoT: {metrics.cot:.4f}")
    print(f"  总能量: {metrics.total_energy:.2f} J")
    print(f"  行走距离: {metrics.distance:.2f} m")
    print("\n指标 4: 鲁棒性")
    print(f"  恢复成功: {'✅ 是' if metrics.recovery_success else '❌ 否'}")
    print(f"  恢复时间: {metrics.recovery_time:.2f} s")
    print(f"  最大高度下降: {metrics.max_height_drop:.4f} m")
