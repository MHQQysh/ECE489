# 本次修复总结 (2026-05-12)

## 修复的问题

### 1. Aliengo MJCF 质量参数错误 ✓
**问题**: Aliengo 的 MJCF 文件中腿部质量是 URDF 的 1/10
- Hip: 0.1993 kg → **1.993 kg**
- Thigh: 0.0639 kg → **0.639 kg**
- Calf: 0.0267 kg → **0.207 kg**

**影响**: 导致 MJCF 和 URDF 模拟结果不一致

**修复文件**: `robot/aliengo/aliengo.xml`

---

### 2. Go2 摩擦参数配置错误 ✓
**问题**: Go2 使用 `condim=6`（过度配置）且没有明确设置摩擦系数

**修复**:
- condim: 6 → **3**
- 添加 friction: **"0.8 0.3 0.3"**

**修复文件**: `robot/go2/go2.xml`

---

### 3. Go2 文档中的质量参数错误 ✓
**问题**: 文档中记录的 Go2 质量与实际 MJCF 文件不符

**实际值**:
- Hip: 0.678 kg (文档错误写成 1.0 kg)
- Thigh: 1.152 kg (文档错误写成 0.7 kg)
- Calf: 0.241 kg (文档错误写成 0.3 kg)

**修复文件**: `doc/aliengo_go2_comparison.md`

---

### 4. Go2 稳定性问题 ✓

#### 4.1 硬编码 AliengoConfig
**问题**: `SwingFootTrajectoryGenerator` 硬编码使用 `AliengoConfig`

**修复**: 
- 构造函数添加 `robot_config` 参数
- 移除硬编码的 `AliengoConfig` 导入
- 动态使用 `robot_config.swing_height` 和 `robot_config.foot_radius`

**修复文件**: 
- `linear_mpc/swing_foot_trajectory_generator.py`
- `scripts/mujoco_aliengo.py`
- `scripts/mujoco_go2.py`

#### 4.2 硬编码脚部着地高度
**问题**: `world_footpos_final[2] = -0.0255` (Aliengo 的脚部半径)

**影响**: Go2 脚部半径是 0.022m，差异 3.5mm 导致接触时机错误

**修复**: `world_footpos_final[2] = -self.__foot_radius`

**修复文件**: `linear_mpc/swing_foot_trajectory_generator.py`

#### 4.3 控制增益不匹配
**问题**: Go2 使用了与 Aliengo 相同的 PD 增益

**原因**: Go2 更轻（15.4kg vs 20.6kg）、腿更短（0.426m vs 0.5m）

**修复**:
- Kp_swing: 200 → **150** (-25%)
- Kd_swing: 20 → **15** (-25%)

**修复文件**: `config/robot_configs.py`

#### 4.4 抬腿高度不合理
**问题**: Go2 使用了与 Aliengo 相同的抬腿高度 0.1m

**原因**: Go2 腿更短，相对抬腿高度过高

**修复**: swing_height: 0.1m → **0.08m** (-20%)

**修复文件**: `config/robot_configs.py`

#### 4.5 缺少 foot_radius 参数
**问题**: RobotConfig 基类没有 `foot_radius` 参数

**修复**: 
- 添加 `foot_radius` 到 `RobotConfig` 基类
- AliengoConfig: `foot_radius = 0.0255`
- Go2Config: `foot_radius = 0.022`

**修复文件**: `config/robot_configs.py`

---

## 修改的文件列表

1. ✅ `robot/aliengo/aliengo.xml` - 修正质量参数
2. ✅ `robot/go2/go2.xml` - 修正摩擦参数
3. ✅ `doc/aliengo_go2_comparison.md` - 更新文档数据
4. ✅ `config/robot_configs.py` - 添加 foot_radius，调整 Go2 参数
5. ✅ `linear_mpc/swing_foot_trajectory_generator.py` - 移除硬编码，支持多机器人
6. ✅ `scripts/mujoco_aliengo.py` - 更新 SwingFootTrajectoryGenerator 调用
7. ✅ `scripts/mujoco_go2.py` - 更新 SwingFootTrajectoryGenerator 调用

---

## 新增的文档

1. ✅ `doc/go2_stability_fixes.md` - Go2 稳定性问题详细分析
2. ✅ `FIXES_SUMMARY.md` - 本文档

---

## 测试建议

### 验证 Aliengo（确保没有回归）
```bash
uv run python scripts/mujoco_aliengo.py
```

### 验证 Go2（确认稳定性改善）
```bash
uv run python scripts/mujoco_go2.py
```

### 如果 Go2 仍不稳定，可以尝试
```python
# 在 config/robot_configs.py 中进一步调整
class Go2Config(RobotConfig):
    # 选项 1: 进一步降低增益
    Kp_swing = np.diag([120., 120., 120.])
    Kd_swing = np.diag([12., 12., 12.])
    
    # 选项 2: 降低抬腿高度
    swing_height = 0.06
    
    # 选项 3: 降低期望速度（在 linear_mpc_configs.py）
    # cmd_xvel: float = 0.8
```

---

## 技术要点

### 为什么脚部半径如此重要？
脚部着地高度决定了：
1. 接触时机 - 脚部何时接触地面
2. 接触力 - 接触时的冲击力大小
3. 步态连续性 - 从摆动到支撑的过渡

3.5mm 的差异看似很小，但在高速运动中会导致：
- 过早接触 → 脚尖拖地 → 摩擦力过大 → 失去平衡
- 过晚接触 → 脚部悬空 → 支撑不足 → 摔倒

### 为什么需要不同的 PD 增益？
PD 控制器增益与系统质量和惯性相关：
- **Kp (比例增益)**: 与质量成正比
- **Kd (微分增益)**: 与 √(质量) 成正比

Go2 质量是 Aliengo 的 75%，因此：
- Kp 应降低到约 75% → 150
- Kd 应降低到约 87% → 15 (更保守)

### condim 参数说明
- **condim=1**: 只有法向力，无摩擦
- **condim=3**: 法向力 + 2个切向摩擦力（适合脚部接触）
- **condim=6**: 完整6自由度接触（过度配置，增加计算开销）

---

## 参数对比

| 参数 | Aliengo | Go2 (修复前) | Go2 (修复后) |
|------|---------|-------------|-------------|
| 总质量 | 20.6 kg | 15.4 kg | 15.4 kg |
| 腿长 | 0.5 m | 0.426 m | 0.426 m |
| 脚部半径 | 0.0255 m | 0.0255 m ❌ | 0.022 m ✓ |
| 抬腿高度 | 0.1 m | 0.1 m ❌ | 0.08 m ✓ |
| Kp_swing | 200 | 200 ❌ | 150 ✓ |
| Kd_swing | 20 | 20 ❌ | 15 ✓ |
| condim | 3 | 6 ❌ | 3 ✓ |
| friction | 1.0 0.3 0.3 | (默认) ❌ | 0.8 0.3 0.3 ✓ |

---

*修复完成日期: 2026-05-12*
*修复人员: Claude (Opus 4.7)*
