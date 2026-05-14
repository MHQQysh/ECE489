# CPG vs MPC 代码对比

本文档对比了 CPG 控制器和 MPC 控制器的代码实现，展示了相似的接口设计。

## 1. 配置类对比

### MPC 配置 (pympc-quadruped)

```python
# linear_mpc_configs.py
class LinearMpcConfig:
    dt_control: float = 0.001
    iteration_between_mpc: int = 20
    dt_mpc: float = 0.05
    
    horizon: int = 16
    gravity: np.float32 = 9.81
    friction_coef: float = 0.7
    
    # QP 权重矩阵
    Q: np.ndarray = np.diag([5., 5., 10., 10., 10., 50., 
                              0.01, 0.01, 0.2, 0.2, 0.2, 0.2, 0.])
    R: np.ndarray = np.diag([1e-5] * 12)
```

### CPG 配置 (mjlab)

```python
# cpg_mpc_style.py
class CPGConfig:
    dt_control: float = 0.001
    iteration_between_update: int = 20
    dt_update: float = 0.02
    
    # CPG 振荡器参数
    base_frequency: float = 1.5  # Hz
    frequency_range: tuple = (0.5, 3.0)
    
    # 振幅参数 [hip, thigh, calf]
    base_amplitude: np.ndarray = np.array([0.3, 0.8, 0.6])
    
    # 关节偏移（站立姿态）
    joint_offset: np.ndarray = np.array([0.0, 0.9, -1.78])
    
    # 速度映射参数
    velocity_to_frequency_gain: float = 1.0
    velocity_to_amplitude_gain: float = 0.5
```

**对比**:
- MPC 使用 QP 权重矩阵 (Q, R) 来优化性能
- CPG 使用频率和振幅参数来生成节律运动
- 两者都有相似的时间步长配置

## 2. 机器人配置对比

### MPC 机器人配置

```python
# robot_configs.py
class RobotConfig:
    mass_base: float
    base_height_des: float
    base_inertia_base: np.ndarray  # 惯性矩阵
    fz_max: float                   # 最大垂直力
    swing_height: float
    Kp_swing: np.ndarray
    Kd_swing: np.ndarray

class AliengoConfig(RobotConfig):
    mass_base: float = 9.042
    base_height_des: float = 0.38
    base_inertia_base = make_com_inertial_matrix(...)
    fz_max = 500.
    swing_height = 0.1
    Kp_swing = np.diag([200., 200., 200.])
    Kd_swing = np.diag([20., 20., 20.])
```

### CPG 机器人配置

```python
# cpg_mpc_style.py
class RobotCPGConfig:
    mass_base: float
    base_height_des: float
    leg_length: float
    Kp_swing: np.ndarray
    Kd_swing: np.ndarray

class Go1CPGConfig(RobotCPGConfig):
    mass_base: float = 12.0
    base_height_des: float = 0.28
    leg_length: float = 0.4
    Kp_swing = np.diag([100.0, 100.0, 100.0])
    Kd_swing = np.diag([10.0, 10.0, 10.0])
```

**对比**:
- MPC 需要惯性矩阵和最大接触力（用于优化）
- CPG 只需要基本的机器人参数
- 两者都有摆动腿的 PD 控制增益

## 3. 步态定义对比

### MPC 步态

```python
# gait.py
class Gait(Enum):
    STANDING = 'standing', 16, np.array([0, 0, 0, 0]), np.array([16, 16, 16, 16])
    TROTTING16 = 'trotting', 16, np.array([0, 8, 8, 0]), np.array([8, 8, 8, 8])
    PACING16 = 'pacing', 16, np.array([8, 0, 8, 0]), np.array([8, 8, 8, 8])
    
    def __init__(self, name, num_segment, stance_offsets, stance_durations):
        self.__name = name
        self.__num_segment = num_segment
        self.__stance_offsets = stance_offsets      # 离散时间偏移
        self.__stance_durations = stance_durations  # 离散时间持续
    
    def get_gait_table(self) -> np.ndarray:
        """返回步态表用于 MPC 约束 (1=支撑, 0=摆动)"""
        gait_table = np.zeros(4 * self.__mpc_horizon)
        for i in range(self.__mpc_horizon):
            i_horizon = (i + 1 + self.iteration) % self.num_segment
            cur_segment = i_horizon - self.stance_offsets
            for j in range(4):
                if cur_segment[j] < 0:
                    cur_segment[j] += self.num_segment
                if cur_segment[j] < self.stance_durations[j]:
                    gait_table[i*4+j] = 1
        return gait_table
```

### CPG 步态

```python
# cpg_mpc_style.py
class CPGGait(Enum):
    STANDING = "standing", 16, np.array([0.0, 0.0, 0.0, 0.0]), np.array([1.0, 1.0, 1.0, 1.0])
    TROTTING = "trotting", 16, np.array([0.0, π, π, 0.0]), np.array([0.5, 0.5, 0.5, 0.5])
    PACING = "pacing", 16, np.array([0.0, π, 0.0, π]), np.array([0.5, 0.5, 0.5, 0.5])
    
    def __init__(self, name, num_segment, phase_offsets, duty_factors):
        self._name = name
        self._num_segment = num_segment
        self._phase_offsets = phase_offsets  # 连续相位偏移（弧度）
        self._duty_factors = duty_factors    # 占空比（0-1）
    
    def get_swing_state(self, global_phase: float) -> np.ndarray:
        """返回摆动状态 (1=摆动, 0=支撑)"""
        leg_phases = (global_phase + self._phase_offsets) % (2 * π)
        normalized_phases = leg_phases / (2 * π)
        swing_state = (normalized_phases > self._duty_factors).astype(float)
        return swing_state
```

**对比**:
- MPC: 离散时间步态表，用于 QP 约束
- CPG: 连续相位步态，用于振荡器同步
- MPC 步态表是预测的（horizon 步），CPG 是即时的

## 4. 控制器主类对比

### MPC 控制器

```python
# mpc.py
class ModelPredictiveController:
    def __init__(self, mpc_config: LinearMpcConfig, robot_config: RobotConfig):
        self.num_state = 13   # [θ, p, ω, ṗ, g]
        self.num_input = 12   # [f1, f2, f3, f4]
        self.horizon = mpc_config.horizon
        self.Qbar = np.kron(np.identity(self.horizon), mpc_config.Q)
        self.Rbar = np.kron(np.identity(self.horizon), mpc_config.R)
    
    def update_robot_state(self, robot_data: RobotData):
        """更新机器人状态"""
        rpy_base = quat2ZYXangle(robot_data.quat_base)
        self.current_state[0:3] = rpy_base
        self.current_state[3:6] = robot_data.pos_base
        self.current_state[6:9] = robot_data.ang_vel_base
        self.current_state[9:12] = robot_data.lin_vel_base
        self.current_state[12] = -self.gravity
    
    def update_mpc_if_needed(self, iter_counter, vel_cmd, yaw_rate, gait_table):
        """更新 MPC（如果需要）"""
        if iter_counter % self.iterations_between_mpc == 0:
            ref_traj = self.generate_reference_trajectory(vel_cmd, yaw_rate)
            self.__contact_forces = self._solve_mpc(ref_traj, gait_table)
        return self.__contact_forces
    
    def _solve_mpc(self, ref_traj, gait_table):
        """求解 QP 问题"""
        Ac, Bc = self._generate_state_space_model()
        Ad, Bd = self._discretize_continuous_model(Ac, Bc)
        qpH, qpg = self._generate_QP_cost(Ad, Bd, self.current_state, ref_traj)
        qp_C, C_lb, C_ub = self._generate_QP_constraints(gait_table)
        
        # 使用 Drake 或 qpsolvers 求解
        result = Solve(qp_problem)
        return result.GetSolution(contact_forces)
```

### CPG 控制器

```python
# cpg_mpc_style.py
class CPGController:
    def __init__(self, cpg_config: CPGConfig, robot_config: RobotCPGConfig):
        # 为每个关节创建振荡器（12 个）
        self.oscillators = []
        for leg_idx in range(4):
            leg_oscillators = []
            for joint_idx in range(3):
                amp = cpg_config.base_amplitude[joint_idx]
                osc = CPGOscillator(frequency=cpg_config.base_frequency, amplitude=amp)
                leg_oscillators.append(osc)
            self.oscillators.append(leg_oscillators)
        
        self.current_gait = CPGGait.TROTTING
        self.time = 0.0
        self.global_phase = 0.0
    
    def update_velocity_command(self, velocity_cmd):
        """更新速度命令"""
        self.target_velocity = np.array(velocity_cmd)
        
        # 速度到频率的映射
        velocity_magnitude = np.linalg.norm(self.target_velocity[:2])
        freq_scale = 0.5 + self.cpg_config.velocity_to_frequency_gain * velocity_magnitude
        self.current_frequency = self.cpg_config.base_frequency * np.clip(freq_scale, 0.3, 2.0)
    
    def compute_joint_targets(self, dt: float) -> np.ndarray:
        """计算关节目标位置"""
        self.time += dt
        self.global_phase = (2 * π * self.current_frequency * self.time) % (2 * π)
        
        # 获取振幅缩放
        velocity_magnitude = np.linalg.norm(self.target_velocity[:2])
        amp_scale = 0.7 + self.cpg_config.velocity_to_amplitude_gain * velocity_magnitude
        
        # 更新振荡器
        for leg_idx in range(4):
            for joint_idx in range(3):
                osc = self.oscillators[leg_idx][joint_idx]
                
                # 大腿关节根据速度缩放振幅
                if joint_idx == 1:
                    target_amp = self.cpg_config.base_amplitude[joint_idx] * amp_scale
                else:
                    target_amp = self.cpg_config.base_amplitude[joint_idx]
                
                # 更新振荡器（Hopf 动力学）
                osc.step(dt, target_frequency=self.current_frequency, target_amplitude=target_amp)
                
                # 获取输出并添加偏移
                output = osc.get_output()
                joint_target = output + self.cpg_config.joint_offset[joint_idx]
                self.joint_targets[leg_idx * 3 + joint_idx] = joint_target
        
        return self.joint_targets.copy()
```

**对比**:
- **MPC**: 求解优化问题 → 接触力 → 通过雅可比转换为关节力矩
- **CPG**: 更新振荡器 → 关节位置目标 → 通过 PD 控制转换为关节力矩
- **MPC**: 计算密集（QP 求解），但能优化性能指标
- **CPG**: 计算轻量（解析解），但基于预定义模式

## 5. Hopf 振荡器实现

CPG 的核心是 Hopf 振荡器：

```python
class CPGOscillator:
    def __init__(self, frequency: float = 1.0, amplitude: float = 1.0):
        self.frequency = frequency
        self.amplitude = amplitude
        self.mu = 1.0  # 收敛速率
        self.state = np.array([amplitude, 0.0])  # [x, y]
    
    def step(self, dt: float, target_frequency=None, target_amplitude=None):
        """Hopf 振荡器动力学"""
        if target_frequency is not None:
            self.frequency = target_frequency
        if target_amplitude is not None:
            self.amplitude = target_amplitude
        
        x, y = self.state
        r_squared = x * x + y * y
        omega = 2 * π * self.frequency
        
        # Hopf 动力学方程
        dx = self.mu * (self.amplitude**2 - r_squared) * x - omega * y
        dy = self.mu * (self.amplitude**2 - r_squared) * y + omega * x
        
        # 欧拉积分
        self.state[0] += dx * dt
        self.state[1] += dy * dt
    
    def get_output(self) -> float:
        return self.state[0]
    
    def get_phase(self) -> float:
        return math.atan2(self.state[1], self.state[0]) % (2 * π)
```

**特性**:
- 自动收敛到稳定的极限环
- 可以平滑改变频率和振幅
- 对扰动鲁棒

## 6. 腿部控制器对比

### MPC 腿部控制器

```python
# leg_controller.py
class LegController:
    def update(self, robot_data, contact_forces, swing_states, 
               pos_targets_swingfeet, vel_targets_swingfeet):
        """计算关节力矩"""
        for leg_idx in range(4):
            Jvi = robot_data.Jv_feet[leg_idx]
            
            if swing_states[leg_idx]:  # 摆动腿
                swing_err = Kp @ (pos_des - pos_cur) + Kd @ (vel_des - vel_cur)
                tau_i = Jvi.T @ swing_err
            else:  # 支撑腿
                tau_i = Jvi.T @ -contact_forces[3*leg_idx:3*(leg_idx+1)]
            
            self.__torque_cmds[3*leg_idx:3*(leg_idx+1)] = tau_i[6+3*leg_idx:6+3*(leg_idx+1)]
        
        return self.__torque_cmds
```

### CPG 腿部控制器

```python
# cpg_mpc_style.py
class CPGLegController:
    def update(self, joint_targets, joint_positions, joint_velocities):
        """使用 PD 控制计算关节力矩"""
        for leg_idx in range(4):
            for joint_idx in range(3):
                idx = leg_idx * 3 + joint_idx
                
                pos_error = joint_targets[idx] - joint_positions[idx]
                vel_error = 0.0 - joint_velocities[idx]
                
                torque = self.Kp[joint_idx] * pos_error + self.Kd[joint_idx] * vel_error
                self.torque_cmds[idx] = torque
        
        return self.torque_cmds.copy()
```

**对比**:
- **MPC**: 支撑腿使用接触力（通过雅可比），摆动腿使用 PD 控制
- **CPG**: 所有关节都使用 PD 控制跟踪目标位置
- **MPC**: 需要雅可比矩阵计算
- **CPG**: 直接的关节空间控制

## 7. 使用示例对比

### MPC 使用

```python
# 初始化
mpc = ModelPredictiveController(LinearMpcConfig, AliengoConfig)
leg_controller = LegController(Kp_swing, Kd_swing)
gait = Gait.TROTTING16

# 控制循环
for iter_counter in range(10000):
    # 更新机器人状态
    robot_data = get_robot_data()
    mpc.update_robot_state(robot_data)
    
    # 更新步态
    gait.set_iteration(iterations_between_mpc, iter_counter)
    gait_table = gait.get_gait_table()
    
    # 求解 MPC
    contact_forces = mpc.update_mpc_if_needed(
        iter_counter, vel_cmd, yaw_rate, gait_table
    )
    
    # 计算关节力矩
    swing_states = gait.get_swing_state()
    torques = leg_controller.update(
        robot_data, contact_forces, swing_states, 
        pos_targets, vel_targets
    )
    
    # 应用力矩
    apply_torques(torques)
```

### CPG 使用

```python
# 初始化
cpg = CPGController(CPGConfig(), Go1CPGConfig())
leg_controller = CPGLegController(Kp, Kd)
cpg.set_gait(CPGGait.TROTTING)

# 控制循环
for step in range(10000):
    # 更新速度命令
    cpg.update_velocity_command(vel_cmd)
    
    # 计算关节目标
    joint_targets = cpg.compute_joint_targets(dt)
    
    # 获取当前关节状态
    joint_positions = get_joint_positions()
    joint_velocities = get_joint_velocities()
    
    # 计算关节力矩
    torques = leg_controller.update(
        joint_targets, joint_positions, joint_velocities
    )
    
    # 应用力矩
    apply_torques(torques)
```

**对比**:
- **MPC**: 需要完整的机器人状态（位置、速度、姿态等）
- **CPG**: 只需要关节状态
- **MPC**: 更新频率可以低于控制频率
- **CPG**: 每个控制周期都更新

## 8. 性能对比

| 指标 | MPC | CPG |
|------|-----|-----|
| **计算时间** | ~3-10ms (QP 求解) | <0.1ms (解析) |
| **内存使用** | 高（矩阵运算） | 低（简单状态） |
| **实时性** | 需要优化求解器 | 易于实时 |
| **可预测性** | 预测 horizon 步 | 即时响应 |
| **适应性** | 强（基于模型） | 中等（基于模式） |
| **鲁棒性** | 依赖模型精度 | 对模型误差鲁棒 |
| **调参难度** | 高（Q, R 矩阵） | 低（频率、振幅） |

## 9. 总结

### MPC 的优势
- 优化性能指标（能耗、稳定性等）
- 考虑约束（摩擦锥、力限制）
- 预测未来状态
- 理论基础扎实

### CPG 的优势
- 计算效率高
- 生物启发，自然节律
- 易于实现和调参
- 对模型误差鲁棒
- 平滑的运动模式

### 混合方法
可以结合两者的优势：
- 使用 CPG 生成参考轨迹
- 使用 MPC 优化接触力
- 或者使用 CPG 作为 MPC 的初始猜测

## 10. 参考代码位置

### MPC (pympc-quadruped)
```
/home/y/ece489/lab4/pympc-quadruped/
├── linear_mpc/
│   ├── mpc.py                    # MPC 控制器
│   ├── leg_controller.py         # 腿部控制器
│   └── gait.py                   # 步态定义
├── config/
│   ├── linear_mpc_configs.py     # MPC 配置
│   └── robot_configs.py          # 机器人配置
└── scripts/
    └── mujoco_aliengo.py         # 使用示例
```

### CPG (mjlab)
```
/home/y/ece489/lab4/mjlab/
├── src/mjlab/controllers/
│   └── cpg_mpc_style.py          # CPG 控制器（MPC 风格接口）
└── src/mjlab/scripts/
    └── demo_cpg_mpc_style.py     # 使用示例
```
