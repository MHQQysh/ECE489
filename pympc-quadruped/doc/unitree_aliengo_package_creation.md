# Unitree Aliengo Python 配置包创建说明

## 1. 创建内容

已为 Aliengo 创建了与 Go2 对应的 Python 配置包：

```
unitree_aliengo/
├── __init__.py
├── aliengo_constants.py
└── xmls/
    ├── aliengo.xml          # 简化版（无场景）
    ├── scene_aliengo.xml    # 完整场景版
    └── assets/
        └── *.stl            # 网格文件
```

## 2. 配置参数对比

### 2.1 执行器参数 (PD 控制器)

| 关节 | Go2 | Aliengo | 说明 |
|------|-----|---------|------|
| **Hip Kp** | 20.0 | 25.0 | Aliengo 更大（更重） |
| **Hip Kd** | 1.0 | 1.25 | 比例保持 5% |
| **Hip Effort** | 23.5 Nm | 33.5 Nm | Aliengo 更大 |
| **Thigh Kp** | 20.0 | 25.0 | 同上 |
| **Thigh Kd** | 1.0 | 1.25 | 同上 |
| **Thigh Effort** | 23.5 Nm | 33.5 Nm | 同上 |
| **Calf Kp** | 40.0 | 50.0 | Aliengo 更大 |
| **Calf Kd** | 2.0 | 2.5 | 比例保持 5% |
| **Calf Effort** | 45.0 Nm | 50.0 Nm | Aliengo 更大 |

**原因：**
- Aliengo 更重（9.042 kg vs 6.921 kg）
- 需要更大的控制增益和力矩

### 2.2 初始状态

| 参数 | Go2 | Aliengo |
|------|-----|---------|
| **高度** | 0.32 m | 0.4 m |
| **Thigh** | 0.9 rad | 0.9 rad |
| **Calf** | -1.8 rad | -1.8 rad |
| **Hip (R)** | 0.1 rad | 0.1 rad |
| **Hip (L)** | -0.1 rad | -0.1 rad |

**差异：**
- Aliengo 站立高度更高（腿更长）

### 2.3 碰撞配置

| 参数 | Go2 | Aliengo |
|------|-----|---------|
| **足部摩擦** | 0.6 | 1.0 |
| **足部 condim** | 3 | 3 |
| **其他 condim** | 1 | 1 |
| **足部 priority** | 1 | 1 |

**差异：**
- Aliengo 使用更高的摩擦系数（1.0 vs 0.6）
- 与原始 aliengo.xml 保持一致

### 2.4 关节范围

| 关节 | Go2 | Aliengo |
|------|-----|---------|
| **Hip** | ±60° (±1.0472 rad) | ±70° (±1.22173 rad) |
| **Thigh (前腿)** | -90° ~ 200° | 无限制 |
| **Thigh (后腿)** | -30° ~ 260° | 无限制 |
| **Calf** | -156° ~ -48° | -159° ~ -37° |

**差异：**
- Aliengo Hip 范围更大
- Aliengo Thigh 无限制（更灵活）

## 3. 文件对比

### 3.1 aliengo_constants.py vs go2_constants.py

**相同点：**
- 结构完全相同
- 使用相同的 mjlab 框架
- 提供相同的接口

**不同点：**
- 路径指向 `unitree_aliengo`
- 执行器参数更大（适应更重的机器人）
- 摩擦系数更高（1.0 vs 0.6）

### 3.2 scene_aliengo.xml vs scene_go2.xml

**相同点：**
- 都包含完整的场景配置
- 都有关节力矩传感器（12个）
- 都有帧位置和速度传感器
- 都有关键帧定义

**不同点：**
- Aliengo 使用 STL 网格，Go2 使用 OBJ 网格
- Aliengo 摩擦系数 1.0，Go2 为 0.4
- Aliengo 腿更长（小腿 0.25m vs 0.213m）
- Aliengo 更重（9.042 kg vs 6.921 kg）

## 4. 使用方法

### 4.1 导入配置

```python
# Go2
from unitree_go2.go2_constants import get_go2_robot_cfg

# Aliengo
from unitree_aliengo.aliengo_constants import get_aliengo_robot_cfg
```

### 4.2 创建机器人实例

```python
from mjlab.entity.entity import Entity

# Go2
go2_cfg = get_go2_robot_cfg()
go2_robot = Entity(go2_cfg)

# Aliengo
aliengo_cfg = get_aliengo_robot_cfg()
aliengo_robot = Entity(aliengo_cfg)
```

### 4.3 加载场景

```python
import mujoco

# Go2 场景
model_go2 = mujoco.MjModel.from_xml_path(
    'unitree_go2/xmls/scene_go2.xml'
)

# Aliengo 场景
model_aliengo = mujoco.MjModel.from_xml_path(
    'unitree_aliengo/xmls/scene_aliengo.xml'
)
```

## 5. 传感器配置

### 5.1 传感器数量对比

| 传感器类型 | Go2 (scene) | Aliengo (scene) |
|-----------|-------------|-----------------|
| **IMU** | 3 | 3 |
| **关节位置** | 12 | 12 |
| **关节速度** | 12 | 12 |
| **关节力矩** | 12 | 12 |
| **帧位置/速度** | 2 | 2 |
| **总数** | 41 | 41 |

**完全相同！**

### 5.2 IMU 位置

| 机器人 | IMU 位置 (相对 trunk) |
|--------|---------------------|
| **Go2** | (-0.02557, 0, 0.04232) |
| **Aliengo** | (0, 0, 0) |

**差异：**
- Go2 使用真实硬件位置
- Aliengo 简化为中心位置

## 6. 关键差异总结

### 6.1 物理参数

| 参数 | Go2 | Aliengo | 差异 |
|------|-----|---------|------|
| **质量** | 6.921 kg | 9.042 kg | +30.6% |
| **站立高度** | 0.445 m | 0.6 m | +34.8% |
| **小腿长度** | 0.213 m | 0.25 m | +17.4% |
| **足部半径** | 0.022 m | 0.0255 m | +15.9% |

### 6.2 控制参数

| 参数 | Go2 | Aliengo | 比例 |
|------|-----|---------|------|
| **Hip Kp** | 20.0 | 25.0 | 1.25× |
| **Calf Kp** | 40.0 | 50.0 | 1.25× |
| **Hip Effort** | 23.5 Nm | 33.5 Nm | 1.43× |
| **Calf Effort** | 45.0 Nm | 50.0 Nm | 1.11× |

### 6.3 摩擦参数

| 参数 | Go2 | Aliengo |
|------|-----|---------|
| **mu1** | 0.6 | 1.0 |
| **mu2** | - | 0.3 |
| **mu3** | - | 0.3 |

## 7. 验证测试

### 7.1 测试加载

```python
# 测试 Aliengo 配置
from unitree_aliengo.aliengo_constants import get_aliengo_robot_cfg
from mjlab.entity.entity import Entity

cfg = get_aliengo_robot_cfg()
robot = Entity(cfg)
print(f"Aliengo loaded: {robot.spec.compile().nq} DOF")
```

### 7.2 测试仿真

```python
import mujoco
import mujoco.viewer as viewer

# 加载场景
model = mujoco.MjModel.from_xml_path(
    'unitree_aliengo/xmls/scene_aliengo.xml'
)
data = mujoco.MjData(model)

# 启动查看器
viewer.launch(model)
```

## 8. 文件清单

### 8.1 新创建的文件

```
unitree_aliengo/
├── __init__.py                    # 包初始化
├── aliengo_constants.py           # 配置常量（主文件）
└── xmls/
    ├── aliengo.xml                # 简化模型
    ├── scene_aliengo.xml          # 完整场景
    └── assets/
        ├── trunk.stl
        ├── hip.stl
        ├── thigh.stl
        ├── thigh_mirror.stl
        └── calf.stl
```

### 8.2 修改的文件

- `unitree_aliengo/xmls/aliengo.xml`: 修改 meshdir 为 "assets"

## 9. 与原始文件的关系

### 9.1 保留原始文件

```
robot/aliengo/
├── aliengo.xml          # 原始文件，保持不变
├── urdf/
│   └── aliengo.urdf     # 原始 URDF，保持不变
└── meshes/
    └── *.stl            # 原始网格，保持不变
```

### 9.2 新包的优势

**unitree_aliengo 包的优势：**
- ✅ 程序化配置（Python）
- ✅ 与 mjlab 框架集成
- ✅ 灵活的碰撞配置
- ✅ 完整的传感器套件（包括力矩传感器）
- ✅ 关键帧定义
- ✅ 与 Go2 配置一致的接口

**原始 robot/aliengo 的优势：**
- ✅ 简单直接
- ✅ 兼容性好
- ✅ 独立使用

## 10. 下一步

### 10.1 测试建议

1. **加载测试**：验证所有文件可以正确加载
2. **仿真测试**：运行基本的站立和行走测试
3. **传感器测试**：验证所有传感器数据正确
4. **对比测试**：对比 Go2 和 Aliengo 的行为差异

### 10.2 可能的改进

1. **添加更多碰撞配置**：类似 Go2 的多种碰撞模式
2. **优化执行器参数**：根据实际测试调整 Kp/Kd
3. **添加文档**：详细的使用说明和示例
4. **创建测试脚本**：自动化测试配置正确性

## 11. 配置对比表（完整版）

| 配置项 | Go2 | Aliengo | 备注 |
|--------|-----|---------|------|
| **包名** | unitree_go2 | unitree_aliengo | - |
| **主文件** | go2_constants.py | aliengo_constants.py | - |
| **XML 路径** | unitree_go2/xmls/ | unitree_aliengo/xmls/ | - |
| **网格格式** | OBJ | STL | - |
| **质量** | 6.921 kg | 9.042 kg | +30.6% |
| **Hip Kp** | 20.0 | 25.0 | +25% |
| **Hip Kd** | 1.0 | 1.25 | +25% |
| **Calf Kp** | 40.0 | 50.0 | +25% |
| **Calf Kd** | 2.0 | 2.5 | +25% |
| **摩擦 mu1** | 0.6 | 1.0 | +66.7% |
| **IMU 位置** | 偏移 | 中心 | 不同策略 |
| **传感器数** | 41 | 41 | 相同 |

---

*文档生成时间: 2026-05-12*
*创建者: Claude Code*
