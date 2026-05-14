# 项目代码架构详解 (Code Architecture Documentation)

## 一、项目概述 (Project Overview)

这是一个**凸模型预测控制 (Convex MPC) 四足机器人 locomotion** 的 Python 实现。项目参考了 MIT Cheetah 3 的工作，通过凸优化来解决四足机器人的动态行走问题。

### 核心论文参考
- **Di Carlo et al., 2018**: "Dynamic Locomotion in the MIT Cheetah 3 Through Convex Model-Predictive Control" - IROS
- **Bledt et al., 2018**: "MIT Cheetah 3: Design and Control of a Robust, Dynamic Quadruped Robot" - IROS

---

## 二、整体数据流 (Data Flow)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MuJoCo 物理仿真器                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  qpos (位置), qvel (速度), sensor (IMU/关节编码器/接触传感器)            │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                          utils/robot_data.py                                │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  1. 接收原始传感器数据 (四元数、位置、速度等)                              │  │
│  │  2. 调用 Pinocchio 进行正运动学计算                                        │  │
│  │  3. 计算足端位置、足端雅可比矩阵、相对速度等                              │  │
│  │  4. 输出: pos_feet, Jv_feet, base_pos_base_feet, base_vel_base_feet     │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                          linear_mpc/gait.py                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  1. 根据步态类型 (TROTTING/PACING 等) 生成接触调度表                     │  │
│  │  2. 计算每条腿当前是 swing 还是 stance 状态                              │  │
│  │  3. 输出: gait_table (MPC用), swing_states (控制用)                       │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
                    ┌───────────────┬───────────────┐
                    ↓               ↓               ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                          linear_mpc/mpc.py                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  MPC 控制器: 用 QP 求解地面反作用力                                       │  │
│  │  输入: 机器人状态 + 参考轨迹 + gait_table                                 │  │
│  │  输出: 12维接触力向量 [f_FL, f_FR, f_RL, f_RR] (每腿3维)                  │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│               linear_mpc/swing_foot_trajectory_generator.py                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  摆动腿轨迹生成器:                                                       │  │
│  │  1. 根据步态时机确定抬腿/落腿时刻                                         │  │
│  │  2. 计算摆动落足点位置 (基于速度、偏航角速度、剩余摆动时间)                │  │
│  │  3. 用三次 Hermite 样条 生成足端轨迹                                      │  │
│  │  输出: swing 腿 的目标位置和速度 (base frame)                             │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                          linear_mpc/leg_controller.py                       │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  腿部控制器: 将力/轨迹目标转换为关节力矩                                   │  │
│  │                                                                          │  │
│  │  Stance 腿: τ = Jᵀ @ (-f)                                              │  │
│  │  (将 MPC 计算的接触力映射到关节力矩)                                       │  │
│  │                                                                          │  │
│  │  Swing 腿: τ = Jᵀ @ (Kp @ pos_err + Kd @ vel_err)                        │  │
│  │  (PD 控制跟踪摆动轨迹)                                                    │  │
│  │                                                                          │  │
│  │  输出: 12维关节力矩命令                                                   │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MuJoCo 物理仿真器                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │  data.ctrl[:] = torque_cmds                                             │  │
│  │  mujoco.mj_step(model, data) → 物理仿真一步                              │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 三、核心模块详解 (Core Modules)

### 3.1 config/ — 配置文件 (Configuration)

#### `linear_mpc_configs.py`: MPC 控制器参数

| 参数 | 值 | 说明 |
|------|-----|------|
| `dt_control` | 0.001s | 低层控制周期 (1kHz) |
| `iteration_between_mpc` | 20 | 每隔20次控制周期更新一次MPC |
| `dt_mpc` | 0.05s | MPC 更新时间间隔 (50ms) |
| `horizon` | 16 | 预测时域 (16 × 50ms = 800ms) |
| `gravity` | 9.81 | 重力加速度 |
| `friction_coef` | 0.7 | 摩擦系数 μ |
| `Q` | diag([5,5,10,10,10,50,0.01,0.01,0.2,0.2,0.2,0.2,0]) | 状态权重矩阵 |
| `R` | diag([1e-5 × 12]) | 输入权重矩阵 (力最小化) |
| `cmd_xvel`, `cmd_yvel`, `cmd_yaw_turn_rate` | 1.2, 0, 0 | 默认速度命令 |

**Q 权重矩阵说明** (13维状态):
```
[roll, pitch, yaw, x, y, z, ωx, ωy, ωz, vx, vy, vz, g]
 5     5     10  10 10 50  0.01 0.01 0.2  0.2 0.2 0.2  0
```
- z 位置权重最高 (50)，保持高度稳定
- yaw 角权重高 (10)，保持方向稳定
- 重力状态 g 权重为 0 (不惩罚)

#### `robot_configs.py`: 机器人物理参数

**AliengoConfig**:
- `mass_base = 9.042 kg`
- `base_height_des = 0.38 m` (期望基体高度)
- `base_inertia_base`: 3×3 惯性矩阵
- `fz_max = 500 N` (单腿最大垂直力)
- `swing_height = 0.1 m` (摆动腿抬腿高度)
- `Kp_swing = diag([200,200,200])`, `Kd_swing = diag([20,20,20])`

**Go2Config**: 类似 Aliengo 但参数不同

---

### 3.2 utils/ — 数学工具与数据抽象

#### `robot_data.py`: RobotData — 机器人状态抽象层

**核心功能**:
1. 接收原始传感器数据 (位置、速度、四元数、角速度、关节角度/速度)
2. 调用 Pinocchio 进行正运动学
3. 计算各种参考系下的足端位置和速度

**关键输出**:
```python
self.pos_base          # 世界坐标系下的基体位置
self.R_base            # 基体旋转矩阵 (quat → matrix)
self.rpy_base          # ZYX 欧拉角
self.lin_vel_base      # 基体线速度 (世界系)
self.ang_vel_base      # 基体角速度 (世界系)

self.pos_feet          # 4个足端的世界坐标
self.Jv_feet          # 4个足端的几何雅可比矩阵 (3×18)
self.base_pos_base_feet # 足端相对基体的位置 (世界系表达)
self.base_pos_base_thighs # 大腿相对基体的位置 (世界系表达)
self.base_vel_base_feet  # 足端相对基体的速度 (基体系表达)
```

**坐标转换约定**:
```
变量命名格式: <表达系>_<量>_<参考系>_<目标>
- 世界坐标系省略前缀
- 默认参考系是世界坐标系

示例:
- base_pos_base_foot: 足端相对基体, 基体系表达
- pos_base_foot: 足端相对基体, 世界系表达  
- pos_foot: 足端位置, 世界系表达
```

**四元数约定**:
- MuJoCo: `[w, x, y, z]` (实部在前)
- Pinocchio: `[x, y, z, w]` (实部在后)
- RobotData 会自动转换

#### `kinematics.py`: 李群李代数与运动学工具

**主要函数**:
| 函数 | 功能 |
|------|------|
| `quat2matrix(quat)` | 四元数 → 旋转矩阵 |
| `quat2ZYXangle(quat)` | 四元数 → ZYX欧拉角 |
| `matrix2quat(R)` | 旋转矩阵 → 四元数 |
| `ZYXangles2matrix(angles)` | ZYX欧拉角 → 旋转矩阵 |
| `vec2so3(vec)` | 向量 → so(3) 反对称矩阵 |
| `exp_so3(omega, theta)` | so(3) 指数映射 |
| `adSE3_Rp(R, p)` | SE(3) 的 adjoint 伴随矩阵 |
| `Rp2T(R, p)` | (R, p) → 4×4 齐次变换矩阵 |
| `exp_se3(screw, theta)` | se(3) 指数映射 |
| `fk_open_chain(...)` | 开链正运动学 (指数积公式) |

#### `dynamics.py`: 动力学工具

```python
def make_com_inertial_matrix(ixx, ixy, ixz, iyy, iyz, izz):
    """从 URDF 的 6 个惯性参数构建 3×3 惯性矩阵"""
    return np.array([[ixx, ixy, ixz],
                     [ixy, iyy, iyz],
                     [ixz, iyz, izz]], dtype=np.float32)
```

#### `mujoco_simulation_utils.py`: MuJoCo 仿真辅助

**关键函数**:
- `reset_robot_state(model, data, robot_config)`: 初始化机器人状态
- `get_true_simulation_data(model, data)`: 获取仿真器真值状态
- `get_simulated_sensor_data(data)`: 模拟传感器数据
- `_detect_robot_config(model)`: 自动检测机器人类型

#### `mujoco_viewer_utils.py`: Viewer 显示辅助

**关键函数**:
- `center_viewer_on_robot(viewer, data)`: 相机跟随机器人
- `get_viewer_update_interval(model, rate_hz)`: 计算更新间隔
- `update_viewer_monitor(...)`: 更新监控面板显示

#### `mujoco_foot_trajectory_visualization.py`: 轨迹可视化

**功能**: 在 MuJoCo viewer 中绘制调试几何体
- 摆动腿轨迹线 (彩色)
- 落足点标记
- 支撑多边形
- 接触力向量

---

### 3.3 linear_mpc/ — 核心 MPC 控制模块

#### `gait.py`: 步态调度 (Gait Scheduling)

**步态枚举**:
```python
class Gait(Enum):
    STANDING    = (16, [0,0,0,0], [16,16,16,16])      # 站立
    TROTTING16  = (16, [0,8,8,0], [8,8,8,8])          # 小跑 (16步周期)
    TROTTING10  = (10, [0,5,5,0], [5,5,5,5])          # 小跑 (10步周期)
    JUMPING16   = (16, [0,0,0,0], [4,4,4,4])          # 跳跃
    PACING16    = (16, [8,0,8,0], [8,8,8,8])          # 踱步
    PACING10    = (10, [5,0,5,0], [5,5,5,5])          # 踱步 (10步周期)
```

**TROTTING 步态时序图**:
```
周期 = 10 步态
stance_offsets = [0, 5, 5, 0]  (FL, FR, RL, RR)
stance_durations = [5, 5, 5, 5]

时间:    0  1  2  3  4  5  6  7  8  9
FL:      S  S  S  S  S  _  _  _  _  _  (stance, swing)
FR:      _  _  _  _  _  S  S  S  S  S  (swing, stance)
RL:      _  _  _  _  _  S  S  S  S  S  (swing, stance)
RR:      S  S  S  S  S  _  _  _  _  _  (stance, swing)

对角线配对: (FL,RR) 和 (FR,RL) 交替触地
```

**关键方法**:
```python
gait.set_iteration(iterations_between_mpc, cur_iteration)
# 设置当前步态周期和相位

gait.get_gait_table() → np.ndarray  # 形状 (4×horizon,)
# 返回 MPC 约束表: 1=stance(着地), 0=swing(摆动)

gait.get_swing_state() → np.ndarray  # 形状 (4,)
# 返回每条腿的摆动进度: 0=stance, 0~1=swing中, 1=刚着地

gait.get_stance_state() → np.ndarray  # 形状 (4,)
# 返回每条腿的支撑进度
```

#### `mpc.py`: 线性 MPC 控制器 (Model Predictive Controller)

**状态空间模型** (13维):
```
x = [roll, pitch, yaw, x, y, z, ωx, ωy, ωz, vx, vy, vz, g]ᵀ
    ─────   ───────   ────────────────────   ─────
     角度     位置        角速度/线速度       重力状态
```

**输入** (12维):
```
u = [f1x, f1y, f1z, f2x, f2y, f2z, f3x, f3y, f3z, f4x, f4y, f4z]ᵀ
    ─────────────── ─────────────── ─────────────── ───────────────
       FL力           FR力            RL力            RR力
```

**连续时间状态方程**:
```
ẋ = Ac·x + Bc·u + [0,0,0,0,0,-g,0,0,0,0,0,0,0]ᵀ

Ac[0:3, 6:9] = Rz.T        # 角速度 → 欧拉角
Ac[3:6, 9:12] = I          # 速度 → 位置
Ac[11, 12] = 1             # 重力状态

Bc[6:9, 3*i:3*i+3] = I⁻¹ · [r_i×]  # 力 → 角加速度
Bc[9:12, 3*i:3*i+3] = I/m          # 力 → 线加速度
```

**QP 求解**:
```python
min  ½·Uᵀ·H·U + Uᵀ·g
U

s.t. C·U ≤ ub              # 摩擦锥约束
     lb ≤ C·U              # 下界约束
```

**摩擦锥约束** (每条腿5个约束):
```
[f_x]        [∞]
[f_y] ≤ μ·  [∞]
[-f_x]        [∞]
[-f_y]        [∞]
[f_z]        [fz_max]
────────    ≤  ──────
  Cx·u         ub
```

**求解器选项**:
- `solver='drake'`: 使用 Drake MathematicalProgram
- `solver='qpsolvers'`: 使用 OSQP

#### `swing_foot_trajectory_generator.py`: 摆动腿轨迹生成

**核心功能**:
1. **计算目标落足点**:
```python
# 世界坐标系下的落足点
world_footpos_final = pos_base 
    + R_base @ (pos_thigh_corrected + base_vel_des · remaining_swing_time)
    + 0.5 · stance_time · vel_base
    + 0.03 · (vel_base - vel_base_des)
    + 偏航补偿项
```

2. **生成三次 Hermite 样条轨迹**:
```python
# 三个断点: 起始点、中间点(抬腿)、终止点
break_points = [0, total_swing_time/2, total_swing_time]

# 位置断点
pos_break_points = [footpos_init, footpos_middle, footpos_final]
# 中间点 Z 坐标 += swing_height

# 速度断点: 中间点速度为水平方向(保持腾空时的动量)
mid_velocity = (footpos_final - footpos_init) / total_swing_time
mid_velocity[2] = 0.0  # Z方向为0

# 三次 Hermite 插值
trajectory = PiecewisePolynomial.CubicHermite(
    break_points, pos_break_points, vel_break_points
)
```

**关键方法**:
```python
set_foot_placement(robot_data, gait, base_vel_des, yaw_rate)
# 设置当前摆动腿的起点和终点

compute_traj_swingfoot(robot_data, gait)
# 计算摆动腿在当前时刻的目标位置和速度

sample_remaining_swing_trajectory(gait, num_samples)
# 采样剩余摆动轨迹 (用于可视化)
```

#### `leg_controller.py`: 腿部控制器

**控制逻辑**:

```python
def update(robot_data, contact_forces, swing_states, 
           pos_targets_swingfeet, vel_targets_swingfeet):
    
    for leg_idx in range(4):
        Jvi = robot_data.Jv_feet[leg_idx]  # 3×18 雅可比
        
        if swing_states[leg_idx] > 0:  # 摆动腿
            # 任务空间 PD 控制
            pos_err = R_base @ (pos_target - pos_foot)
            vel_err = R_base @ (vel_target - vel_foot)
            wrench = Kp_swing @ pos_err + Kd_swing @ vel_err
            tau = Jvi.T @ wrench
        else:  # 支撑腿
            # 力映射
            tau = Jvi.T @ (-contact_force)
        
        # 提取关节力矩 (雅可比的前6列对应浮基, 后12列是关节)
        tau_joints = tau[6 + 3*leg_idx : 6 + 3*(leg_idx+1)]
        torque_cmds[3*leg_idx : 3*(leg_idx+1)] = tau_joints
    
    return torque_cmds
```

**公式解释**:
- **Stance**: τ = Jᵀ · (-f), 其中 J 是几何雅可比
- **Swing**: τ = Jᵀ · (Kp·Δp + Kd·Δv), 任务空间 PD

---

### 3.4 scripts/ — 仿真入口

#### `mujoco_aliengo.py`: 主程序

**程序流程**:
```python
def main():
    # 1. 加载 MuJoCo 模型
    model = mujoco.MjModel.from_xml_path('robot/aliengo/aliengo.xml')
    data = mujoco.MjData(model)
    
    # 2. 初始化
    reset_robot_state(model, data, robot_config)
    robot_data = RobotData(urdf_path)
    
    # 3. 创建控制器
    mpc = ModelPredictiveController(config, robot_config)
    leg_ctrl = LegController(Kp, Kd)
    gait = Gait.TROTTING10
    swing_trajs = [SwingFootTrajectoryGenerator(i) for i in range(4)]
    
    # 4. 主循环
    while running:
        # 获取仿真器状态
        sensor_data = get_true_simulation_data(model, data)
        
        # 更新 RobotData
        robot_data.update(...)
        
        # 步态调度
        gait.set_iteration(...)
        swing_states = gait.get_swing_state()
        gait_table = gait.get_gait_table()
        
        # MPC 计算接触力
        mpc.update_robot_state(robot_data)
        contact_forces = mpc.update_mpc_if_needed(...)
        
        # 摆动腿轨迹
        for leg_idx in range(4):
            if swing_states[leg_idx] > 0:
                swing_trajs[leg_idx].set_foot_placement(...)
                pos, vel = swing_trajs[leg_idx].compute_traj_swingfoot(...)
                pos_targets[leg_idx] = pos
                vel_targets[leg_idx] = vel
        
        # 关节力矩
        torque_cmds = leg_ctrl.update(...)
        
        # 执行
        data.ctrl[:] = torque_cmds
        mujoco.mj_step(model, data)
```

**命令行参数**:
- `--steps N`: 运行 N 步后停止 (0=无限)
- `--no-viewer`: 无 GUI 运行
- `--monitor-rate HZ`: 监控面板刷新率
- `--foot-traj-rate HZ`: 轨迹可视化刷新率
- `--foot-traj-samples N`: 轨迹采样点数

---

## 四、MPC 数学推导概要

### 4.1 单刚体动力学简化

原始动力学:
```
m·p̈ = Σf_i - m·g           (线动量)
I·ω̇ + ω×(I·ω) = Σr_i×f_i  (角动量)
```

**简化假设**:
1. 忽略 ω×(I·ω) 项 (角速度较小时影响小)
2. 惯性矩阵用 yaw 旋转对齐: Î = Rz(ψ)·I_b·Rz(ψ)ᵀ
3. 用欧拉角近似角速度: θ̇ ≈ Rz(ψ)ᵀ·ω

得到 **线性时变** 系统:
```
θ̇ = Rz(ψ)ᵀ·ω
ṗ = v
ω̇ = Î⁻¹·Σ[r_i×]·f_i
v̇ = Σf_i/m - [0,0,g]ᵀ
```

### 4.2 离散化

使用零阶保持 + 矩阵指数:
```
[[Ac, Bc],    ]           [[Ad, Bd],  ]
exp( [ 0,   0]] · dt)  =   [ 0,   I ]]
```

得到离散系统:
```
x[k+1] = Ad·x[k] + Bd·u[k]
```

### 4.3 QP 批量形式

构建批量状态序列:
```
X = Sx·x₀ + Su·U
X = [x[1], x[2], ..., x[N]]ᵀ
U = [u[0], u[1], ..., u[N-1]]ᵀ
```

最小化:
```
J = ½·Uᵀ·(Suᵀ·Qbar·Su + Rbar)·U + Uᵀ·Suᵀ·Qbar·(Sx·x₀ - Xref)
```

---

## 五、文件索引表 (File Index)

| 文件路径 | 主要功能 | 关键类/函数 |
|----------|----------|-------------|
| `config/linear_mpc_configs.py` | MPC 参数配置 | `LinearMpcConfig` |
| `config/robot_configs.py` | 机器人物理参数 | `RobotConfig`, `AliengoConfig`, `Go2Config` |
| `utils/robot_data.py` | 状态抽象层 | `RobotData` |
| `utils/kinematics.py` | 数学工具 | `quat2matrix`, `vec2so3`, `fk_open_chain` 等 |
| `utils/dynamics.py` | 动力学工具 | `make_com_inertial_matrix` |
| `utils/mujoco_simulation_utils.py` | MuJoCo 辅助 | `get_true_simulation_data`, `reset_robot_state` |
| `utils/mujoco_viewer_utils.py` | 显示辅助 | `update_viewer_monitor` |
| `utils/mujoco_foot_trajectory_visualization.py` | 轨迹可视化 | `update_viewer_foot_trajectories` |
| `linear_mpc/gait.py` | 步态调度 | `Gait` (STANDING, TROTTING, PACING) |
| `linear_mpc/mpc.py` | MPC 求解 | `ModelPredictiveController` |
| `linear_mpc/swing_foot_trajectory_generator.py` | 轨迹生成 | `SwingFootTrajectoryGenerator` |
| `linear_mpc/leg_controller.py` | 力矩计算 | `LegController` |
| `scripts/mujoco_aliengo.py` | 仿真入口 | `main`, `run_control_loop` |

---

## 六、关键符号约定 (Symbol Conventions)

### 坐标轴约定
- **世界坐标系**: 右手系, Z 轴向上
- **基体坐标系**: 与机器人基体固连, X 前, Y 左, Z 上

### 腿部索引
```
FL = Front-Left  (左前)
FR = Front-Right (右前)
RL = Rear-Left  (左后)
RR = Rear-Right (右后)
```

### 变量命名
```
<前缀>_<量>_<参考系>_<目标>

示例:
base_pos_base_foot   = 基体系表达的, 相对基体的, 足端位置
world_vel_base_foot  = 世界系表达的, 相对基体的, 足端速度
```

### 四元数格式
- **MuJoCo**: [w, x, y, z] (实部在前)
- **Pinocchio**: [x, y, z, w] (实部在后)
- 转换: `RobotData` 自动处理

### 关节顺序
```
MuJoCo actuator / q 顺序:
FL_hip, FL_thigh, FL_calf,
FR_hip, FR_thigh, FR_calf,
RL_hip, RL_thigh, RL_calf,
RR_hip, RR_thigh, RR_calf
```

---

## 七、依赖关系图 (Dependency Graph)

```
scripts/mujoco_aliengo.py (入口)
    │
    ├── config/linear_mpc_configs.py (配置)
    ├── config/robot_configs.py (配置)
    │
    ├── utils/robot_data.py
    │       └── utils/kinematics.py (数学工具)
    │       └── utils/dynamics.py (惯性矩阵)
    │
    ├── linear_mpc/gait.py (步态)
    │
    ├── linear_mpc/mpc.py (MPC)
    │       └── utils/kinematics.py
    │       └── config/linear_mpc_configs.py
    │       └── config/robot_configs.py
    │       └── utils/robot_data.py
    │
    ├── linear_mpc/swing_foot_trajectory_generator.py (摆动轨迹)
    │       └── linear_mpc/gait.py
    │       └── config/linear_mpc_configs.py
    │       └── config/robot_configs.py
    │
    ├── linear_mpc/leg_controller.py (力矩控制)
    │       └── utils/robot_data.py
    │
    └── utils/mujoco_simulation_utils.py (仿真辅助)
    └── utils/mujoco_viewer_utils.py (显示辅助)
    └── utils/mujoco_foot_trajectory_visualization.py (可视化)
```

---

## 八、运行流程总结 (Execution Summary)

```python
# 初始化阶段 (一次)
1. 加载 MuJoCo MJCF 模型
2. 加载 Pinocchio URDF 模型
3. 创建控制器实例 (MPC, LegController, Gait, SwingTraj)
4. 重置仿真器状态

# 主循环 (每控制周期 ~1ms)
for iter_counter in range(max_iterations):

    # === 状态获取 (2-3ms) ===
    sensor_data = get_true_simulation_data(model, data)
    robot_data.update(...)

    # === 步态调度 (~0.1ms) ===
    gait.set_iteration(iterations_between_mpc, iter_counter)
    swing_states = gait.get_swing_state()       # [0,0,1,1] 格式
    gait_table = gait.get_gait_table()           # 4×16 张量

    # === MPC 求解 (10-50ms, 每20次迭代一次) ===
    if iter_counter % iterations_between_mpc == 0:
        mpc.update_robot_state(robot_data)
        contact_forces = mpc.solve(X_ref, gait_table)

    # === 摆动轨迹生成 (~0.5ms) ===
    for leg in swing_legs:
        swing_trajs[leg].set_foot_placement(...)
        pos_target[leg], vel_target[leg] = \
            swing_trajs[leg].compute_traj_swingfoot(...)

    # === 力矩计算 (~0.2ms) ===
    torque_cmds = leg_controller.update(
        robot_data, contact_forces, swing_states,
        pos_target, vel_target
    )

    # === 执行 ===
    data.ctrl[:] = torque_cmds
    mujoco.mj_step(model, data)  # ~1ms

    # === 可视化更新 (GUI模式) ===
    if viewer and update_needed:
        update_viewer_monitor(...)
        update_viewer_foot_trajectories(...)
        viewer.sync()
```

---

## 九、调试与可视化

### GUI 模式监控面板显示内容
- 仿真时间、实时因子
- 当前步态类型和相位
- 命令速度/偏航角速度
- 基体高度、姿态角 (RPY)
- 基体线速度、角速度
- 各腿接触状态 (0=swing, 1=stance)
- MPC 求解时间和迭代次数
- 各腿 Z 方向接触力

### 轨迹可视化
- **彩色线**: 每条腿的摆动轨迹 (FL=蓝, FR=橙, RL=黄, RR=紫)
- **圆球**: 落足点标记
- **粗线**: 当前支撑多边形
- **箭头**: 接触力向量

---

## 十、扩展建议

### 添加新步态
在 `gait.py` 的 `Gait` 枚举中添加新模式:
```python
BOUNDING = 'bounding', 8, np.array([4,4,0,0]), np.array([4,4,4,4])
```

### 添加新机器人
在 `robot_configs.py` 添加新配置类:
```python
class NewRobotConfig(RobotConfig):
    mass_base = 8.0
    base_height_des = 0.35
    # ... 其他参数
```

### 添加状态估计
目前使用仿真器真值 (`get_true_simulation_data`)。
要使用传感器模拟，设置 `STATE_ESTIMATION = True`。
`RobotData.update(state_estimation=True)` 会触发 `NotImplementedError`。
需要实现 IMU 滤波 + 腿式里程计 (见 `doc/state_estimation_kf.md`)。
