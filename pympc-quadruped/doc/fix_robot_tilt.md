# 修复机器人倾斜问题

## 问题描述

机器人向右倾斜，身体不平衡。

## 原因分析

### 1. 前后腿关节范围不一致

**修改前**：
```
前腿 (FL/FR) thigh: 0.5382 ~ 1.0618 (中心 0.8 rad)
后腿 (RL/RR) thigh: 0.7382 ~ 1.2618 (中心 1.0 rad)
```

这导致前后腿高度不同，机器人前倾或后倾。

### 2. 初始姿态不对称

**修改前**：
```python
# 前腿
0.1, 0.8, -1.5   # FL: hip=0.1, thigh=0.8
-0.1, 0.8, -1.5  # FR: hip=-0.1, thigh=0.8

# 后腿
0.1, 1.0, -1.5   # RL: hip=0.1, thigh=1.0
-0.1, 1.0, -1.5  # RR: hip=-0.1, thigh=1.0
```

Hip 关节的 ±0.1 rad 会导致左右不对称。

---

## 解决方案

### 修改 1: 统一关节范围

**文件**: `robot/go2/go2.xml`

所有腿的 thigh 关节都改为：
```xml
<joint name="XX_thigh_joint" axis="0 1 0" range="0.5382 1.0618"/>
```

### 修改 2: 统一初始姿态

**文件**: `utils/mujoco_simulation_utils.py`

所有腿的初始角度都改为：
```python
q_pos_init = np.array([
    0, 0, robot_config.base_height_des,
    1, 0, 0, 0,
    0, 0.8, -1.5,   # FL: hip=0, thigh=0.8, calf=-1.5
    0, 0.8, -1.5,   # FR: hip=0, thigh=0.8, calf=-1.5
    0, 0.8, -1.5,   # RL: hip=0, thigh=0.8, calf=-1.5
    0, 0.8, -1.5    # RR: hip=0, thigh=0.8, calf=-1.5
])
```

**关键变化**：
- Hip: 全部改为 0（完全对称）
- Thigh: 全部改为 0.8（前后一致）
- Calf: 全部改为 -1.5（保持不变）

---

## 验证

运行以下命令验证修复：

```bash
cd /home/y/ece489/lab4/pympc-quadruped

unset PYTHONPATH
unset LD_LIBRARY_PATH
unset PKG_CONFIG_PATH
unset CMAKE_PREFIX_PATH

# 运行 Go2 演示
uv run python scripts/mujoco_go2.py
```

**检查要点**：
1. ✅ 机器人站立时身体水平
2. ✅ 四条腿高度一致
3. ✅ 行走时不向一侧倾斜
4. ✅ Roll 角度接近 0°

---

## 修改总结

| 项目 | 修改前 | 修改后 |
|------|--------|--------|
| **FL thigh 范围** | 0.5382 ~ 1.0618 | 0.5382 ~ 1.0618 ✅ |
| **FR thigh 范围** | 0.5382 ~ 1.0618 | 0.5382 ~ 1.0618 ✅ |
| **RL thigh 范围** | 0.7382 ~ 1.2618 ❌ | 0.5382 ~ 1.0618 ✅ |
| **RR thigh 范围** | 0.7382 ~ 1.2618 ❌ | 0.5382 ~ 1.0618 ✅ |
| **FL hip 初始** | 0.1 ❌ | 0 ✅ |
| **FR hip 初始** | -0.1 ❌ | 0 ✅ |
| **RL hip 初始** | 0.1 ❌ | 0 ✅ |
| **RR hip 初始** | -0.1 ❌ | 0 ✅ |
| **FL thigh 初始** | 0.8 ✅ | 0.8 ✅ |
| **FR thigh 初始** | 0.8 ✅ | 0.8 ✅ |
| **RL thigh 初始** | 1.0 ❌ | 0.8 ✅ |
| **RR thigh 初始** | 1.0 ❌ | 0.8 ✅ |

---

## 如果还有倾斜

如果修改后仍然倾斜，可能是以下原因：

### 1. 质量分布不对称

检查 `robot/go2/go2.xml` 中的 inertial 参数是否对称。

### 2. 摩擦系数不一致

检查四个足端的摩擦系数是否相同。

### 3. MPC 权重不对称

检查 `config/linear_mpc_configs.py` 中的权重矩阵。

### 4. 传感器噪声

如果使用状态估计，检查 IMU 数据是否有偏差。

---

## 相关文件

- `robot/go2/go2.xml` - 机器人模型和关节范围
- `utils/mujoco_simulation_utils.py` - 初始姿态设置
- `config/robot_configs.py` - 机器人参数配置

---

**修改完成时间**: 2026-05-13  
**状态**: ✅ 已修复对称性问题
