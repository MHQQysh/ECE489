# Go2 稳定性问题修复总结

## 问题描述

Aliengo 可以稳定前行，但 Go2 非常不稳定、容易摔倒。

## 根本原因分析

通过完整代码审查，发现了 **4 个关键问题**：

### 1. SwingFootTrajectoryGenerator 硬编码了 AliengoConfig ⚠️

**位置**: `linear_mpc/swing_foot_trajectory_generator.py`

**问题**:
```python
from config.robot_configs import AliengoConfig

def __load_parameters(self):
    self.__swing_height = AliengoConfig.swing_height  # 硬编码！
```

**影响**: Go2 无法使用自己的 `swing_height` 配置，被强制使用 Aliengo 的 0.1m 抬腿高度。

**修复**:
```python
def __init__(self, leg_id, robot_config):
    self.__load_parameters(robot_config)

def __load_parameters(self, robot_config):
    self.__swing_height = robot_config.swing_height
    self.__foot_radius = robot_config.foot_radius
```

---

### 2. 硬编码的脚部着地高度 ⚠️⚠️⚠️

**位置**: `linear_mpc/swing_foot_trajectory_generator.py:194`

**问题**:
```python
world_footpos_final[2] = -0.0255  # Aliengo 的脚部半径！
```

**影响**: 
- Aliengo 脚部半径: 0.0255m
- Go2 脚部半径: 0.022m
- 差异: 3.5mm

这会导致 Go2 的脚部着地位置错误，脚尖过早或过晚接触地面，破坏步态稳定性。

**修复**:
```python
world_footpos_final[2] = -self.__foot_radius
```

---

### 3. 控制增益不匹配 ⚠️

**位置**: `config/robot_configs.py`

**问题**: Go2 使用了与 Aliengo 相同的 PD 增益：
```python
Kp_swing = np.diag([200., 200., 200.])
Kd_swing = np.diag([20., 20., 20.])
```

**为什么不合适**:
- Go2 更轻: 15.4kg vs Aliengo 20.6kg (轻 25%)
- Go2 腿更短: 0.426m vs Aliengo 0.5m (短 15%)
- 更轻的机器人需要更小的增益以避免过度振荡

**修复**:
```python
# Go2Config
Kp_swing = np.diag([150., 150., 150.])  # 降低 25%
Kd_swing = np.diag([15., 15., 15.])      # 降低 25%
```

---

### 4. 抬腿高度不合理

**问题**: Go2 使用了与 Aliengo 相同的 `swing_height = 0.1m`

**为什么不合适**:
- Go2 腿更短 (0.426m vs 0.5m)
- 相对抬腿高度: 0.1/0.426 = 23.5% vs 0.1/0.5 = 20%
- Go2 的相对抬腿高度更高，消耗更多能量，增加不稳定性

**修复**:
```python
# Go2Config
swing_height = 0.08  # 降低到 0.08m
```

---

## 修改的文件

### 1. `config/robot_configs.py`
- 添加 `foot_radius` 参数到 `RobotConfig` 基类
- AliengoConfig: `foot_radius = 0.0255`
- Go2Config: 
  - `foot_radius = 0.022`
  - `swing_height = 0.08` (从 0.1 降低)
  - `Kp_swing = np.diag([150., 150., 150.])` (从 200 降低)
  - `Kd_swing = np.diag([15., 15., 15.])` (从 20 降低)

### 2. `linear_mpc/swing_foot_trajectory_generator.py`
- 构造函数添加 `robot_config` 参数
- 移除硬编码的 `AliengoConfig` 导入
- 使用 `robot_config.swing_height` 和 `robot_config.foot_radius`
- 修复 `world_footpos_final[2] = -self.__foot_radius`

### 3. `scripts/mujoco_aliengo.py`
- 更新调用: `SwingFootTrajectoryGenerator(leg_idx, robot_config)`

### 4. `scripts/mujoco_go2.py`
- 更新调用: `SwingFootTrajectoryGenerator(leg_idx, robot_config)`

---

## 参数对比表

| 参数 | Aliengo | Go2 (修复前) | Go2 (修复后) |
|------|---------|-------------|-------------|
| 总质量 | 20.6 kg | 15.4 kg | 15.4 kg |
| 腿长 | 0.5 m | 0.426 m | 0.426 m |
| 脚部半径 | 0.0255 m | **0.0255 m** ❌ | **0.022 m** ✓ |
| 抬腿高度 | 0.1 m | **0.1 m** ❌ | **0.08 m** ✓ |
| Kp_swing | 200 | **200** ❌ | **150** ✓ |
| Kd_swing | 20 | **20** ❌ | **15** ✓ |

### 质量分布（MJCF 已修正）

| 连杆 | Aliengo MJCF | Go2 MJCF |
|------|--------------|----------|
| Trunk | 9.042 kg | 6.921 kg |
| Hip | 1.993 kg | 0.678 kg |
| Thigh | 0.639 kg | 1.152 kg |
| Calf | 0.207 kg | 0.241 kg |
| **总计** | **~20.6 kg** | **~15.4 kg** |

**注**: Aliengo 的 MJCF 质量参数已在本次修复中更正为与 URDF 一致。

---

## 测试建议

1. **运行 Aliengo 验证没有回归**:
   ```bash
   uv run python scripts/mujoco_aliengo.py
   ```

2. **运行 Go2 验证稳定性改善**:
   ```bash
   uv run python scripts/mujoco_go2.py
   ```

3. **如果 Go2 仍然不稳定，可以尝试**:
   - 进一步降低 Kp/Kd: `Kp=120, Kd=12`
   - 降低抬腿高度: `swing_height=0.06`
   - 降低期望速度: `cmd_xvel=0.8` (在 `linear_mpc_configs.py`)

---

## 技术要点

### 为什么脚部半径如此重要？

脚部着地高度 `world_footpos_final[2]` 决定了：
1. **接触时机**: 脚部何时接触地面
2. **接触力**: 接触时的冲击力大小
3. **步态连续性**: 从摆动到支撑的过渡是否平滑

错误的脚部半径会导致：
- 过早接触 → 脚尖拖地 → 摩擦力过大 → 失去平衡
- 过晚接触 → 脚部悬空 → 支撑不足 → 摔倒

### 为什么需要不同的 PD 增益？

PD 控制器的增益与系统的质量和惯性直接相关：
- **Kp (比例增益)**: 与质量成正比
- **Kd (微分增益)**: 与 √(质量) 成正比

Go2 质量是 Aliengo 的 75%，因此：
- Kp 应该降低到约 75% → 150
- Kd 应该降低到约 87% → 17 (我们用 15 更保守)

---

## 后续优化方向

1. **自适应增益**: 根据机器人状态动态调整 Kp/Kd
2. **地形感知**: 根据地面摩擦系数调整脚部着地策略
3. **能量优化**: 优化抬腿高度以减少能量消耗
4. **鲁棒性测试**: 在不同速度、转向率下测试稳定性

---

*修复日期: 2026-05-12*
*修复人员: Claude (Opus 4.7)*
