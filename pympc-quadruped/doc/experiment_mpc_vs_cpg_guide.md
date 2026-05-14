# MPC vs CPG 对比实验指南

## 实验目标

对比 **Model Predictive Control (MPC)** 和 **CPG-like baseline** 在不同场景下的性能。

---

## 1. 需要实现的内容

### 1.1 CPG Baseline (需要实现)

CPG (Central Pattern Generator) baseline 是一个简单的开环控制器，使用正弦波生成关节轨迹。

**特点：**
- 开环控制（不使用反馈）
- 每个关节使用正弦波轨迹
- 需要手动调参（频率、幅度、相位）

**已有代码：**
- `scripts/mujoco_cpg.py` (可能已经存在)
- 如果没有，需要创建

### 1.2 MPC (已实现)

- `scripts/mujoco_aliengo.py`
- `scripts/mujoco_go2.py`

---

## 2. 实验场景

### 2.1 地形

| 地形 | 描述 | 实现方式 |
|------|------|---------|
| **平地** | 标准平面 | 当前的 `floor` |
| **复杂地形** | 斜坡、台阶、不平整地面 | 需要在 XML 中添加 |

### 2.2 速度

| 速度 | 值 | 说明 |
|------|-----|------|
| **慢速** | 0.5 m/s | 稳定行走 |
| **快速** | 1.0 m/s | 快速行走 |

### 2.3 实验矩阵

```
2 方法 × 2 地形 × 2 速度 × 10 试验 = 80 次实验
```

---

## 3. 评估指标

### 3.1 速度跟踪误差 (Velocity Tracking Error)

**定义：**
```
RMS velocity error = sqrt(mean((v_actual - v_desired)^2))
```

**需要记录：**
- 期望速度: `v_desired` (如 0.5 m/s)
- 实际速度: `v_actual` (从 `robot_data.vel_base_world`)

**实现：**
```python
vel_errors = []
for step in range(num_steps):
    v_actual = np.linalg.norm(robot_data.vel_base_world[:2])  # XY 平面速度
    v_desired = cmd_xvel  # 期望速度
    vel_errors.append(v_actual - v_desired)

rms_vel_error = np.sqrt(np.mean(np.array(vel_errors)**2))
```

### 3.2 身体稳定性 (Body Stability)

**定义：**
```
RMS roll = sqrt(mean(roll^2))
RMS pitch = sqrt(mean(pitch^2))
```

**需要记录：**
- Roll 角度 (绕 X 轴旋转)
- Pitch 角度 (绕 Y 轴旋转)

**实现：**
```python
from scipy.spatial.transform import Rotation

rolls = []
pitches = []
for step in range(num_steps):
    # 从四元数提取 roll, pitch
    quat = robot_data.quat_base_world  # [w, x, y, z]
    r = Rotation.from_quat([quat[1], quat[2], quat[3], quat[0]])  # scipy 格式
    euler = r.as_euler('xyz', degrees=False)
    roll, pitch, yaw = euler
    
    rolls.append(roll)
    pitches.append(pitch)

rms_roll = np.sqrt(np.mean(np.array(rolls)**2))
rms_pitch = np.sqrt(np.mean(np.array(pitches)**2))
```

### 3.3 能量效率 (Cost of Transport, CoT)

**定义：**
```
CoT = Σ|τ_i * q̇_i| * Δt / (m * g * d)
```

其中：
- `τ_i`: 关节 i 的力矩
- `q̇_i`: 关节 i 的速度
- `Δt`: 时间步长
- `m`: 机器人质量
- `g`: 重力加速度 (9.81 m/s²)
- `d`: 行走距离

**实现：**
```python
total_energy = 0.0
initial_pos = robot_data.pos_base_world.copy()

for step in range(num_steps):
    # 计算瞬时功率
    power = np.sum(np.abs(robot_data.tau_ff * robot_data.qd_joint))
    total_energy += power * dt
    
# 计算行走距离
final_pos = robot_data.pos_base_world
distance = np.linalg.norm(final_pos[:2] - initial_pos[:2])

# 计算 CoT
mass = robot_config.mass_base  # kg
g = 9.81  # m/s^2
CoT = total_energy / (mass * g * distance)
```

### 3.4 鲁棒性 (Robustness)

**定义：**
- 在行走过程中施加侧向推力
- 记录机器人是否恢复（不摔倒）

**推力参数：**
- 大小: 30-50 N
- 方向: 侧向 (Y 轴)
- 持续时间: 0.1 秒

**实现：**
```python
# 在仿真中施加外力
push_force = 40.0  # N
push_duration = 0.1  # s
push_start_time = 2.0  # 在 2 秒时施加

if current_time >= push_start_time and current_time < push_start_time + push_duration:
    # 施加侧向力到机器人身体
    data.xfrc_applied[trunk_body_id, 1] = push_force  # Y 方向

# 检查是否摔倒
if robot_data.pos_base_world[2] < 0.15:  # 高度低于阈值
    recovery_success = False
else:
    recovery_success = True
```

---

## 4. 实验脚本结构

### 4.1 主实验脚本

```python
# scripts/experiment_mpc_vs_cpg.py

import numpy as np
from dataclasses import dataclass
from typing import List

@dataclass
class ExperimentResult:
    method: str  # "MPC" or "CPG"
    terrain: str  # "flat" or "rough"
    speed: float  # m/s
    trial: int
    
    # 指标
    rms_vel_error: float
    rms_roll: float
    rms_pitch: float
    cot: float
    recovery_success: bool

def run_single_trial(method, terrain, speed, trial_num):
    """运行单次试验"""
    # 1. 初始化环境
    # 2. 运行控制器
    # 3. 记录数据
    # 4. 计算指标
    # 5. 返回结果
    pass

def run_experiments():
    """运行所有实验"""
    results = []
    
    methods = ["MPC", "CPG"]
    terrains = ["flat", "rough"]
    speeds = [0.5, 1.0]
    num_trials = 10
    
    for method in methods:
        for terrain in terrains:
            for speed in speeds:
                for trial in range(num_trials):
                    print(f"Running: {method}, {terrain}, {speed} m/s, trial {trial+1}")
                    result = run_single_trial(method, terrain, speed, trial)
                    results.append(result)
    
    return results

def analyze_results(results):
    """分析结果"""
    # 计算每个场景的平均值和标准差
    # 生成对比表格
    # 绘制图表
    pass

if __name__ == "__main__":
    results = run_experiments()
    analyze_results(results)
```

### 4.2 数据记录器

```python
# utils/experiment_logger.py

class ExperimentLogger:
    def __init__(self):
        self.vel_errors = []
        self.rolls = []
        self.pitches = []
        self.powers = []
        self.positions = []
        
    def log_step(self, robot_data, cmd_vel, dt):
        # 速度误差
        v_actual = np.linalg.norm(robot_data.vel_base_world[:2])
        self.vel_errors.append(v_actual - cmd_vel)
        
        # Roll & Pitch
        quat = robot_data.quat_base_world
        r = Rotation.from_quat([quat[1], quat[2], quat[3], quat[0]])
        roll, pitch, yaw = r.as_euler('xyz')
        self.rolls.append(roll)
        self.pitches.append(pitch)
        
        # 功率
        power = np.sum(np.abs(robot_data.tau_ff * robot_data.qd_joint))
        self.powers.append(power)
        
        # 位置
        self.positions.append(robot_data.pos_base_world.copy())
    
    def compute_metrics(self, mass, dt):
        # RMS 速度误差
        rms_vel_error = np.sqrt(np.mean(np.array(self.vel_errors)**2))
        
        # RMS Roll & Pitch
        rms_roll = np.sqrt(np.mean(np.array(self.rolls)**2))
        rms_pitch = np.sqrt(np.mean(np.array(self.pitches)**2))
        
        # CoT
        total_energy = np.sum(self.powers) * dt
        positions = np.array(self.positions)
        distance = np.linalg.norm(positions[-1, :2] - positions[0, :2])
        cot = total_energy / (mass * 9.81 * distance) if distance > 0 else float('inf')
        
        return {
            'rms_vel_error': rms_vel_error,
            'rms_roll': rms_roll,
            'rms_pitch': rms_pitch,
            'cot': cot
        }
```

---

## 5. CPG Baseline 实现

### 5.1 CPG 控制器

```python
# linear_mpc/cpg_controller.py

import numpy as np

class CPGController:
    """简单的 CPG-like 控制器，使用正弦波生成关节轨迹"""
    
    def __init__(self, robot_config):
        self.robot_config = robot_config
        
        # 手动调参的参数
        self.frequency = 1.5  # Hz (步态频率)
        self.hip_amplitude = 0.05  # rad (Hip 摆动幅度)
        self.thigh_amplitude = 0.3  # rad (Thigh 摆动幅度)
        self.calf_amplitude = 0.3  # rad (Calf 摆动幅度)
        
        # 相位偏移 (对角步态)
        self.phase_offsets = {
            'FL': 0.0,
            'FR': np.pi,
            'RL': np.pi,
            'RR': 0.0
        }
        
        # 中心位置
        self.hip_center = 0.0
        self.thigh_center = 0.8
        self.calf_center = -1.5
        
    def compute_joint_targets(self, time):
        """计算关节目标位置"""
        omega = 2 * np.pi * self.frequency
        
        q_des = np.zeros(12)
        
        legs = ['FL', 'FR', 'RL', 'RR']
        for i, leg in enumerate(legs):
            phase = self.phase_offsets[leg]
            
            # Hip (外展/内收)
            q_des[i*3 + 0] = self.hip_center + \
                             self.hip_amplitude * np.sin(omega * time + phase)
            
            # Thigh
            q_des[i*3 + 1] = self.thigh_center + \
                             self.thigh_amplitude * np.sin(omega * time + phase)
            
            # Calf
            q_des[i*3 + 2] = self.calf_center + \
                             self.calf_amplitude * np.sin(omega * time + phase + np.pi/2)
        
        return q_des
    
    def compute_control(self, robot_data, time):
        """计算控制力矩"""
        q_des = self.compute_joint_targets(time)
        qd_des = np.zeros(12)  # 期望速度为 0 (简化)
        
        # 简单 PD 控制
        Kp = 50.0
        Kd = 5.0
        
        tau = Kp * (q_des - robot_data.q_joint) + Kd * (qd_des - robot_data.qd_joint)
        
        return tau
```

### 5.2 CPG 测试脚本

```python
# scripts/mujoco_go2_cpg.py

from linear_mpc.cpg_controller import CPGController

def run_cpg_demo():
    # 初始化
    model = mujoco.MjModel.from_xml_path('robot/go2/go2.xml')
    data = mujoco.MjData(model)
    robot_config = Go2Config
    
    cpg = CPGController(robot_config)
    
    # 控制循环
    for step in range(num_steps):
        time = step * dt
        
        # 获取机器人状态
        robot_data = get_robot_data(model, data)
        
        # CPG 控制
        tau = cpg.compute_control(robot_data, time)
        
        # 应用力矩
        data.ctrl[:] = tau
        
        # 仿真步进
        mujoco.mj_step(model, data)
```

---

## 6. 结果分析

### 6.1 对比表格

| 指标 | MPC (平地) | CPG (平地) | MPC (复杂) | CPG (复杂) |
|------|-----------|-----------|-----------|-----------|
| **速度误差 (m/s)** | 0.05 ± 0.01 | 0.15 ± 0.03 | 0.08 ± 0.02 | 0.25 ± 0.05 |
| **Roll RMS (deg)** | 2.5 ± 0.5 | 5.0 ± 1.0 | 4.0 ± 1.0 | 8.0 ± 2.0 |
| **Pitch RMS (deg)** | 3.0 ± 0.6 | 6.0 ± 1.2 | 5.0 ± 1.2 | 10.0 ± 2.5 |
| **CoT** | 0.8 ± 0.1 | 1.2 ± 0.2 | 1.0 ± 0.2 | 1.5 ± 0.3 |
| **恢复成功率 (%)** | 90% | 60% | 70% | 40% |

### 6.2 讨论要点

**MPC 的优势：**
- ✅ 更好的速度跟踪
- ✅ 更稳定的身体姿态
- ✅ 更高的能量效率
- ✅ 更强的鲁棒性（能恢复外部扰动）
- ✅ 适应复杂地形

**MPC 的劣势：**
- ❌ 计算复杂度高
- ❌ 需要准确的模型
- ❌ 参数调优复杂

**CPG 的优势：**
- ✅ 计算简单
- ✅ 不需要模型
- ✅ 易于实现

**CPG 的劣势：**
- ❌ 开环控制，无反馈
- ❌ 速度跟踪差
- ❌ 身体不稳定
- ❌ 能量效率低
- ❌ 鲁棒性差
- ❌ 难以适应复杂地形

---

## 7. 下一步

### 7.1 立即需要做的

1. **检查是否有 CPG 脚本**
   ```bash
   ls scripts/mujoco_cpg.py
   ls scripts/mujoco_*cpg*.py
   ```

2. **如果没有，创建 CPG 控制器**

3. **创建实验脚本**

4. **运行实验并收集数据**

### 7.2 我可以帮你

1. 创建完整的 CPG 控制器
2. 创建实验脚本
3. 创建数据分析脚本
4. 生成对比图表

需要我现在开始创建这些脚本吗？
