# CPG 控制器快速入门

基于 pympc-quadruped 的 MPC 控制器接口设计的 CPG 控制器。

## 快速开始

### 1. 基本使用（5 分钟）

```python
from mjlab.controllers.cpg_mpc_style import (
    CPGController, CPGConfig, CPGGait, Go1CPGConfig
)
import numpy as np

# 创建控制器
cpg_config = CPGConfig()
robot_config = Go1CPGConfig()
controller = CPGController(cpg_config, robot_config)

# 设置步态
controller.set_gait(CPGGait.TROTTING)

# 设置速度命令 [vx, vy, vyaw]
controller.update_velocity_command([0.5, 0.0, 0.0])  # 前进 0.5 m/s

# 控制循环
dt = 0.001  # 1ms
for step in range(1000):
    joint_targets = controller.compute_joint_targets(dt)
    # 应用 joint_targets 到机器人...
```

### 2. 运行演示

```bash
# 基本仿真
uv run python src/mjlab/scripts/demo_cpg_mpc_style.py --robot go1 --duration 10

# 比较不同步态
uv run python src/mjlab/scripts/demo_cpg_mpc_style.py --mode compare

# 分析振荡器
uv run python src/mjlab/scripts/demo_cpg_mpc_style.py --mode analyze
```

## 核心概念

### 1. CPG (Central Pattern Generator)
中枢模式发生器 - 生物启发的节律运动生成器

### 2. Hopf 振荡器
非线性振荡器，生成稳定的极限环：
```
dx/dt = μ(A² - r²)x - 2πfy
dy/dt = μ(A² - r²)y + 2πfx
```

### 3. 步态模式
- **TROTTING**: 对角小跑 [FR-RL, FL-RR]
- **WALKING**: 四足行走
- **PACING**: 同侧步态 [FR-RR, FL-RL]
- **BOUNDING**: 跳跃 [FR-FL, RR-RL]

## 参数调优

### 频率调节
```python
cpg_config.base_frequency = 1.5  # Hz，控制步频
cpg_config.velocity_to_frequency_gain = 1.0  # 速度到频率的增益
```

### 振幅调节
```python
# [hip, thigh, calf] 关节振幅
cpg_config.base_amplitude = np.array([0.3, 0.8, 0.6])
cpg_config.velocity_to_amplitude_gain = 0.5  # 速度到振幅的增益
```

### 站立姿态
```python
# [hip, thigh, calf] 关节偏移
cpg_config.joint_offset = np.array([0.0, 0.9, -1.78])
```

## 与 MPC 对比

| 特性 | MPC | CPG |
|------|-----|-----|
| 计算复杂度 | 高 (QP) | 低 (解析) |
| 实时性 | 需优化 | 易实时 |
| 调参 | Q, R 矩阵 | 频率、振幅 |
| 适应性 | 强 | 中等 |

## 常见问题

### Q: 如何改变步态？
```python
controller.set_gait(CPGGait.TROTTING)  # 或 WALKING, PACING 等
```

### Q: 如何调整速度？
```python
controller.update_velocity_command([vx, vy, vyaw])
```

### Q: 如何获取接触力？
```python
contact_forces = controller.get_contact_forces()  # 估计值
```

### Q: 如何重置控制器？
```python
controller.reset()
```

## 下一步

- 阅读 `CPG_MPC_STYLE_README.md` 了解详细信息
- 查看 `CPG_vs_MPC_CODE_COMPARISON.md` 了解与 MPC 的对比
- 运行 `demo_cpg_mpc_style.py` 查看示例

## 文件位置

```
src/mjlab/controllers/cpg_mpc_style.py       # 主实现
src/mjlab/scripts/demo_cpg_mpc_style.py      # 演示脚本
CPG_MPC_STYLE_README.md                      # 详细文档
CPG_vs_MPC_CODE_COMPARISON.md                # 代码对比
```

## 参考

- pympc-quadruped: https://github.com/Derek-TH-Wang/pympc-quadruped
- Hopf oscillators: Righetti & Ijspeert (2006)
- CPG for robotics: Ijspeert (2008)
