# robot/go2 摩擦参数修改完成报告

## 修改总结

已成功将 `robot/go2/go2.xml` 的摩擦和碰撞参数修改为与 `unitree_go2/xmls/scene_go2.xml` 完全一致。

## 修改详情

### 1. 默认 go2 类配置

**修改前：**
```xml
<default class="go2">
  <default class="visual">
    <geom type="mesh" contype="0" conaffinity="0" density="0" group="2"/>
  </default>
  <default class="collision">
    <geom priority="1" condim="3" friction="0.6 0.3 0.3" group="3"/>
  </default>
  <site rgba="1 0 0 1" group="5"/>
</default>
```

**修改后：**
```xml
<default class="go2">
  <geom friction="0.4" margin="0.001" condim="1"/>
  <default class="visual">
    <geom type="mesh" contype="0" conaffinity="0" density="0" group="2"/>
  </default>
  <default class="collision">
    <geom group="3"/>
    <default class="foot">
      <geom priority="1" condim="6" friction="0.4 0.02 0.01"/>
    </default>
  </default>
  <site rgba="1 0 0 1" group="5"/>
</default>
```

### 2. 足部几何体类引用

**修改前（所有4个足部）：**
```xml
<geom name="FL_foot_collision" pos="0 0 -0.213" type="sphere" size="0.022" class="collision"/>
<geom name="FR_foot_collision" pos="0 0 -0.213" type="sphere" size="0.022" class="collision"/>
<geom name="RL_foot_collision" pos="0 0 -0.213" type="sphere" size="0.022" class="collision"/>
<geom name="RR_foot_collision" pos="0 0 -0.213" type="sphere" size="0.022" class="collision"/>
```

**修改后（所有4个足部）：**
```xml
<geom name="FL_foot_collision" pos="0 0 -0.213" type="sphere" size="0.022" class="foot"/>
<geom name="FR_foot_collision" pos="0 0 -0.213" type="sphere" size="0.022" class="foot"/>
<geom name="RL_foot_collision" pos="0 0 -0.213" type="sphere" size="0.022" class="foot"/>
<geom name="RR_foot_collision" pos="0 0 -0.213" type="sphere" size="0.022" class="foot"/>
```

## 参数变化对比

### mu1 (滑动摩擦系数)

| 部位 | 修改前 | 修改后 | 变化 |
|------|--------|--------|------|
| **默认** | 0.6 | 0.4 | -33.3% |
| **足部** | 0.6 | 0.4 | -33.3% |

### mu2 (滚动摩擦系数)

| 部位 | 修改前 | 修改后 | 变化 |
|------|--------|--------|------|
| **默认** | 0.3 | - | 移除 |
| **足部** | 0.3 | 0.02 | -93.3% |

### mu3 (扭转摩擦系数)

| 部位 | 修改前 | 修改后 | 变化 |
|------|--------|--------|------|
| **默认** | 0.3 | - | 移除 |
| **足部** | 0.3 | 0.01 | -96.7% |

### condim (接触维度)

| 部位 | 修改前 | 修改后 | 变化 |
|------|--------|--------|------|
| **默认** | 3 | 1 | 简化 |
| **足部** | 3 | 6 | 完整接触 |

### 其他参数

| 参数 | 修改前 | 修改后 |
|------|--------|--------|
| **margin** | 未定义 | 0.001 |
| **priority (足部)** | 1 | 1 (不变) |

## 修改原因

### 1. 与 unitree_go2 配置统一

现在 `robot/go2/go2.xml` 与 `unitree_go2/xmls/scene_go2.xml` 使用完全相同的摩擦和碰撞参数。

### 2. 分层配置策略

- **默认几何体**: condim=1 (简化，仅法向力)
- **足部**: condim=6 (完整接触，6自由度)
- 优化计算性能，同时保持足部精度

### 3. 更真实的摩擦模型

**足部摩擦 (0.4, 0.02, 0.01):**
- mu1=0.4: 中等滑动摩擦（真实地面）
- mu2=0.02: 极低滚动摩擦（接近点接触）
- mu3=0.01: 极低扭转摩擦（允许足部旋转）

## 影响分析

### 对仿真的影响

**稳定性：**
- mu1 从 0.6 降到 0.4：站立稳定性略微降低
- 但 condim=6 提供更精确的接触模型，补偿了稳定性

**灵活性：**
- 更低的摩擦系数：转向更灵活
- 极低的 mu2/mu3：足部可以更自由地滚动和旋转

**真实性：**
- 更接近真实的室内地面
- 更容易迁移到实物机器人

**性能：**
- 默认 condim=1：非足部碰撞计算更快
- 足部 condim=6：足部接触更精确

### 对控制的影响

**需要注意：**
1. 更低的摩擦可能需要调整 PD 增益
2. 足部可能更容易滑动，需要更好的平衡控制
3. condim=6 提供更丰富的接触信息

**建议：**
- 监测足部滑动情况
- 如果不稳定，可以增加 Kp/Kd
- 利用 condim=6 的完整接触信息改进控制

## 验证结果

### ✅ 配置一致性检查

| 参数 | robot/go2 | unitree_go2 | 状态 |
|------|-----------|-------------|------|
| **默认 friction** | 0.4 | 0.4 | ✅ 一致 |
| **默认 condim** | 1 | 1 | ✅ 一致 |
| **默认 margin** | 0.001 | 0.001 | ✅ 一致 |
| **足部 friction** | 0.4 0.02 0.01 | 0.4 0.02 0.01 | ✅ 一致 |
| **足部 condim** | 6 | 6 | ✅ 一致 |
| **足部 priority** | 1 | 1 | ✅ 一致 |

### ✅ 足部几何体检查

| 足部 | 使用的类 | 状态 |
|------|---------|------|
| **FL_foot_collision** | foot | ✅ 正确 |
| **FR_foot_collision** | foot | ✅ 正确 |
| **RL_foot_collision** | foot | ✅ 正确 |
| **RR_foot_collision** | foot | ✅ 正确 |

## 最终配置总结

### Go2 配置（修改后）

```
默认几何体:
  friction: 0.4 (仅 mu1)
  condim: 1 (仅法向力)
  margin: 0.001

足部几何体:
  friction: 0.4 0.02 0.01 (mu1, mu2, mu3)
  condim: 6 (完整接触)
  priority: 1
```

### Aliengo 配置（保持不变）

```
默认几何体:
  friction: 1.0 0.3 0.3
  condim: 3
  margin: 0.001
```

**原因：** Aliengo 更重，需要更高摩擦保持稳定。

## 测试建议

### 1. 基础稳定性测试

```python
import mujoco

model = mujoco.MjModel.from_xml_path('robot/go2/go2.xml')
data = mujoco.MjData(model)

# 设置初始姿态
data.qpos[2] = 0.32
data.qpos[3:7] = [1, 0, 0, 0]

# 仿真 5 秒
for i in range(5000):
    mujoco.mj_step(model, data)

# 检查稳定性
print(f"最终高度: {data.qpos[2]:.4f} m")
print(f"高度变化: {abs(data.qpos[2] - 0.32):.4f} m")
```

### 2. 足部滑动测试

```python
# 检查足部是否滑动
import numpy as np

# 记录足部位置
foot_positions = []
for i in range(1000):
    mujoco.mj_step(model, data)
    # 获取足部位置
    fl_pos = data.site_xpos[model.site('FL').id]
    foot_positions.append(fl_pos.copy())

# 计算滑动距离
foot_positions = np.array(foot_positions)
sliding = np.linalg.norm(foot_positions[-1] - foot_positions[0])
print(f"足部滑动距离: {sliding:.4f} m")
```

### 3. 接触力测试

```python
# 利用 condim=6 的完整接触信息
for i in range(100):
    mujoco.mj_step(model, data)
    
    # 获取接触信息
    for j in range(data.ncon):
        contact = data.contact[j]
        print(f"接触 {j}:")
        print(f"  法向力: {contact.force[0]:.2f} N")
        print(f"  切向力: {contact.force[1]:.2f}, {contact.force[2]:.2f} N")
        print(f"  力矩: {contact.force[3]:.2f}, {contact.force[4]:.2f}, {contact.force[5]:.2f} Nm")
```

## 回滚方法

如果需要恢复原始配置：

```bash
# 使用 git 恢复
git checkout robot/go2/go2.xml

# 或手动修改
# 将 friction 改回 0.6 0.3 0.3
# 将 condim 改回 3
# 将足部 class 改回 collision
```

## 相关文件

- ✅ 已修改: `robot/go2/go2.xml`
- ✅ 参考配置: `unitree_go2/xmls/scene_go2.xml`
- ✅ Python 配置: `unitree_go2/go2_constants.py`
- ✅ 文档: `doc/friction_parameter_correction.md`

## 总结

### 修改内容
1. ✅ 默认摩擦: 0.6 → 0.4
2. ✅ 默认 condim: 3 → 1
3. ✅ 足部摩擦: 0.6 0.3 0.3 → 0.4 0.02 0.01
4. ✅ 足部 condim: 3 → 6
5. ✅ 添加 margin: 0.001
6. ✅ 足部使用 foot 类

### 预期效果
- 更真实的物理模拟
- 更灵活的运动
- 更精确的足部接触
- 与 unitree_go2 配置完全一致

### 下一步
1. 运行测试验证稳定性
2. 根据需要调整 PD 增益
3. 监测足部滑动情况
4. 利用 condim=6 改进控制算法

---

*修改完成时间: 2026-05-12*
*修改者: Claude Code*
*参考: unitree_go2/xmls/scene_go2.xml*
