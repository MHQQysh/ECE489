# CPG Controller with MPC-Style Interface

这是一个参考 `pympc-quadruped` 的 MPC 控制器设计的 CPG（中枢模式发生器）控制器实现。

## 概述

CPG 控制器使用 Hopf 振荡器生成四足机器人的节律性运动模式。与 MPC 控制器相比：

- **MPC**: 基于模型预测控制，求解优化问题计算最优接触力
- **CPG**: 基于生物启发的振荡器，生成周期性关节轨迹

## 主要特性

### 1. MPC 风格的接口设计

参考 `pympc-quadruped` 的结构：

```python
# MPC 控制器
from linear_mpc import ModelPredictiveController, LinearMpcConfig
from robot_configs import AliengoConfig

mpc = ModelPredictiveController(LinearMpcConfig, AliengoConfig)
contact_forces = mpc.update_mpc_if_needed(iter_counter, vel_cmd, yaw_rate, gait_table)

# CPG 控制器（相同的接口模式）
from mjlab.controllers.cpg_mpc_style import CPGController, CPGConfig, Go1CPGConfig

cpg = CPGController(CPGConfig(), Go1CPGConfig())
joint_targets = cpg.compute_joint_targets(dt)
```

### 2. 配置类系统

类似 MPC 的配置结构：

```python
# MPC 配置
class LinearMpcConfig:
    dt_control: float = 0.001
    horizon: int = 16
    Q: np.ndarray  # 状态权重
    R: np.ndarray  # 控制权重

# CPG 配置（对应结构）
class CPGConfig:
    dt_control: float = 0.001
    base_frequency: float = 1.5
    base_amplitude: np.ndarray
    joint_offset: np.ndarray
```

### 3. 步态模式

支持多种步态，类似 MPC 的 Gait 枚举：

| 步态 | 描述 | 相位偏移 [FR, FL, RR, RL] | 占空比 |
|------|------|---------------------------|--------|
| STANDING | 站立 | [0, 0, 0, 0] | [1.0, 1.0, 1.0, 1.0] |
| TROTTING | 对角小跑 | [0, π, π, 0] | [0.5, 0.5, 0.5, 0.5] |
| WALKING | 行走 | [0, π, π/2, 3π/2] | [0.75, 0.75, 0.75, 0.75] |
| PACING | 同侧步态 | [0, π, 0, π] | [0.5, 0.5, 0.5, 0.5] |
| BOUNDING | 跳跃 | [0, 0, π, π] | [0.5, 0.5, 0.5, 0.5] |
| GALLOPING | 奔跑 | [0, π/4, π, 5π/4] | [0.4, 0.4, 0.4, 0.4] |

### 4. Hopf 振荡器

使用非线性 Hopf 振荡器生成稳定的极限环：

```
dx/dt = μ(A² - r²)x - 2πfy
dy/dt = μ(A² - r²)y + 2πfx
```

其中：
- `f`: 频率 (Hz)
- `A`: 振幅
- `μ`: 收敛速率
- `r = √(x² + y²)`: 当前半径

## 文件结构

```
src/mjlab/controllers/
├── cpg_mpc_style.py          # CPG 控制器主实现
│   ├── CPGConfig              # CPG 配置类
│   ├── RobotCPGConfig         # 机器人配置基类
│   ├── Go1CPGConfig           # Go1 机器人配置
│   ├── Go2CPGConfig           # Go2 机器人配置
│   ├── CPGGait                # 步态枚举
│   ├── CPGOscillator          # Hopf 振荡器
│   ├── CPGController          # 主控制器
│   └── CPGLegController       # 腿部控制器（PD 控制）

src/mjlab/scripts/
└── demo_cpg_mpc_style.py      # 演示脚本
```

## 使用方法

### 基本使用

```python
from mjlab.controllers.cpg_mpc_style import (
    CPGController, CPGConfig, CPGGait, Go1CPGConfig
)

# 1. 创建配置
cpg_config = CPGConfig()
cpg_config.base_frequency = 1.5  # Hz
cpg_config.base_amplitude = np.array([0.2, 0.6, 0.5])  # [hip, thigh, calf]

robot_config = Go1CPGConfig()

# 2. 创建控制器
controller = CPGController(cpg_config, robot_config)

# 3. 设置步态
controller.set_gait(CPGGait.TROTTING)

# 4. 设置速度命令
controller.update_velocity_command([0.5, 0.0, 0.0])  # [vx, vy, vyaw]

# 5. 控制循环
dt = 0.001  # 1ms
for step in range(10000):
    # 计算关节目标位置
    joint_targets = controller.compute_joint_targets(dt)
    
    # 获取接触力估计（用于分析）
    contact_forces = controller.get_contact_forces()
    
    # 应用到机器人...
```

### 运行演示

```bash
# 基本仿真（10秒）
uv run python src/mjlab/scripts/demo_cpg_mpc_style.py --robot go1 --duration 10

# 比较不同步态
uv run python src/mjlab/scripts/demo_cpg_mpc_style.py --mode compare

# 分析振荡器动力学
uv run python src/mjlab/scripts/demo_cpg_mpc_style.py --mode analyze
```

### 与 MPC 控制器对比

```python
# MPC 控制器使用方式
from linear_mpc.mpc import ModelPredictiveController
from linear_mpc.gait import Gait

mpc = ModelPredictiveController(mpc_config, robot_config)
mpc.update_robot_state(robot_data)
contact_forces = mpc.update_mpc_if_needed(
    iter_counter, 
    vel_cmd, 
    yaw_rate, 
    gait_table
)

# CPG 控制器使用方式（类似接口）
from mjlab.controllers.cpg_mpc_style import CPGController, CPGGait

cpg = CPGController(cpg_config, robot_config)
cpg.update_velocity_command(vel_cmd)
joint_targets = cpg.compute_joint_targets(dt)
contact_forces = cpg.get_contact_forces()  # 估计值
```

## 参数调优

### 频率调节

```python
# 基础频率（站立时）
cpg_config.base_frequency = 1.5  # Hz

# 频率范围
cpg_config.frequency_range = (0.5, 3.0)  # (min, max)

# 速度到频率的映射增益
cpg_config.velocity_to_frequency_gain = 1.0
```

### 振幅调节

```python
# 基础振幅 [hip, thigh, calf]
cpg_config.base_amplitude = np.array([0.3, 0.8, 0.6])

# 振幅缩放范围
cpg_config.amplitude_scale_range = (0.5, 1.5)

# 速度到振幅的映射增益
cpg_config.velocity_to_amplitude_gain = 0.5
```

### 关节偏移（站立姿态）

```python
# 关节偏移 [hip, thigh, calf]
cpg_config.joint_offset = np.array([0.0, 0.9, -1.78])
```

## 与 MPC 的对比

| 特性 | MPC | CPG |
|------|-----|-----|
| **计算复杂度** | 高（QP 求解） | 低（解析解） |
| **实时性** | 需要优化求解器 | 快速计算 |
| **适应性** | 强（基于模型） | 中等（基于模式） |
| **鲁棒性** | 依赖模型精度 | 对模型误差鲁棒 |
| **能耗** | 优化能耗 | 自然节律 |
| **实现复杂度** | 高 | 低 |
| **调参难度** | 需要调 Q, R 矩阵 | 调频率和振幅 |

## 优势

1. **计算效率高**: 无需求解优化问题，适合实时控制
2. **生物启发**: 模仿动物的中枢模式发生器
3. **自然节律**: 生成平滑的周期性运动
4. **易于调参**: 直观的频率和振幅参数
5. **鲁棒性好**: 对模型误差和扰动鲁棒

## 局限性

1. **无优化**: 不像 MPC 那样优化性能指标
2. **固定模式**: 基于预定义的步态模式
3. **适应性**: 对复杂地形的适应性不如 MPC
4. **接触力**: 只能估计接触力，不能精确计算

## 扩展方向

1. **自适应 CPG**: 根据反馈自动调整参数
2. **混合控制**: CPG + MPC 结合
3. **学习 CPG**: 使用强化学习优化 CPG 参数
4. **地形适应**: 根据地形调整步态
5. **能量优化**: 优化能耗的 CPG 参数

## 参考文献

1. **MPC for Quadrupeds**: 
   - MIT Cheetah: "Dynamic Locomotion in the MIT Cheetah 3 Through Convex Model-Predictive Control"
   - pympc-quadruped: https://github.com/Derek-TH-Wang/pympc-quadruped

2. **CPG for Robotics**:
   - Ijspeert, A. J. (2008). "Central pattern generators for locomotion control in animals and robots"
   - Righetti, L., & Ijspeert, A. J. (2008). "Pattern generators with sensory feedback for the control of quadruped locomotion"

3. **Hopf Oscillators**:
   - Righetti, L., & Ijspeert, A. J. (2006). "Programmable central pattern generators: an application to biped locomotion control"

## 许可证

本代码遵循项目的许可证。

## 作者

基于 pympc-quadruped 的 MPC 控制器接口设计。
