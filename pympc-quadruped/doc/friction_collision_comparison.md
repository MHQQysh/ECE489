# Aliengo vs Go2 摩擦和碰撞参数详细对比

## 1. 摩擦系数对比

### 1.1 实际数值

| 模型文件 | friction (mu1, mu2, mu3) | condim | 说明 |
|---------|-------------------------|--------|------|
| **Aliengo (aliengo.xml)** | **1.0, 0.3, 0.3** | 未定义（继承） | 默认几何体 |
| **Go2 (robot/go2/go2.xml)** | **0.8, 0.3, 0.3** | **3** | 碰撞类默认 |
| **Go2 (unitree_go2/go2.xml)** | 未定义 | **6** | 碰撞类默认 |
| **Go2 (scene_go2.xml)** | **0.4** (默认)<br>**0.4, 0.02, 0.01** (足部) | **1** (默认)<br>**6** (足部) | 分层配置 |
| **Go2 (Python config)** | **0.6** (足部) | **3** (足部)<br>**1** (其他) | 程序化配置 |

### 1.2 修正后的对比表

**您的表格需要修正：**

| 参数 | Aliengo | Go2 (robot/go2) | Go2 (unitree_go2) | 说明 |
|------|---------|----------------|------------------|------|
| **mu1 (滑动摩擦)** | ✅ 1.0 | ✅ 0.8 | ❌ **0.4 或 0.6** | 不同文件不同值 |
| **mu2 (滚动摩擦)** | ✅ 0.3 | ✅ 0.3 | ❌ **0.02 (足部)** | 足部更小 |
| **mu3 (扭转摩擦)** | ✅ 0.3 | ✅ 0.3 | ❌ **0.01 (足部)** | 足部更小 |
| **condim** | ✅ 3 | ✅ 3 | ❌ **6 (足部), 1 (其他)** | 更复杂的接触模型 |

---

## 2. 详细参数解释

### 2.1 摩擦系数 (friction)

**MuJoCo 摩擦模型：**
```
friction = "mu1 mu2 mu3"
```

- **mu1 (滑动摩擦系数)**: 切向滑动摩擦，最重要的参数
- **mu2 (滚动摩擦系数)**: 滚动阻力（可选）
- **mu3 (扭转摩擦系数)**: 绕法向轴的扭转阻力（可选）

**典型值范围：**
- 橡胶-混凝土: mu1 = 0.6 - 1.0
- 金属-金属: mu1 = 0.15 - 0.3
- 冰面: mu1 = 0.02 - 0.05

### 2.2 接触维度 (condim)

| condim | 含义 | 自由度 | 适用场景 |
|--------|------|--------|---------|
| **1** | 仅法向力 | 1 | 简化碰撞，非接触面 |
| **3** | 法向力 + 2D 摩擦 | 3 | 标准接触（点接触） |
| **4** | condim=3 + 滚动摩擦 | 4 | 考虑滚动 |
| **6** | 完整接触 | 6 | 面接触，最精确 |

---

## 3. 各模型详细配置

### 3.1 Aliengo (robot/aliengo/aliengo.xml)

**默认几何体配置：**
```xml
<default>
  <geom contype="1" conaffinity="1" 
        friction="1.0 0.3 0.3" 
        rgba="0.5 0.6 0.7 0" 
        margin="0.001" 
        group="0"/>
</default>
```

**地面配置：**
```xml
<geom name="floor" pos="0 0 0" euler="0 0 0" size="0 0 1" 
      type="plane" material="plane" 
      condim="3" conaffinity="1" contype="1"/>
```

**特点：**
- ✅ 高摩擦系数 (mu1=1.0)
- ✅ condim=3（标准点接触）
- ✅ 所有几何体使用相同配置
- 简单统一的碰撞模型

### 3.2 Go2 (robot/go2/go2.xml)

**碰撞类默认配置：**
```xml
<default class="collision">
  <geom priority="1" condim="3" friction="0.8 0.3 0.3" group="3"/>
</default>
```

**地面配置：**
```xml
<geom name="floor" pos="0 0 0" euler="0 0 0" size="0 0 1" 
      type="plane" material="plane" 
      condim="3" conaffinity="1" contype="1"/>
```

**特点：**
- ✅ 中等摩擦系数 (mu1=0.8)
- ✅ condim=3（标准点接触）
- ✅ 与 Aliengo 类似，但摩擦略小
- 更接近真实硬件

### 3.3 Go2 (unitree_go2/xmls/go2.xml)

**碰撞类配置：**
```xml
<default class="collision">
  <geom priority="1" condim="6" group="3"/>
</default>
```

**特点：**
- ❌ 未定义摩擦系数（使用父类或默认值）
- ✅ condim=6（完整接触模型）
- 更精确的接触动力学

### 3.4 Go2 (unitree_go2/xmls/scene_go2.xml)

**分层配置：**

```xml
<!-- 默认 go2 类 -->
<default class="go2">
  <geom friction="0.4" margin="0.001" condim="1"/>
  
  <!-- 碰撞子类 -->
  <default class="collision">
    <geom group="3"/>
    
    <!-- 足部子类 -->
    <default class="foot">
      <geom size="0.022" pos="-0.002 0 -0.213" 
            priority="1" condim="6"
            friction="0.4 0.02 0.01"/>
    </default>
  </default>
</default>
```

**特点：**
- ✅ 分层配置（默认 → 碰撞 → 足部）
- ✅ 足部特殊摩擦：0.4, 0.02, 0.01
- ✅ 足部 condim=6（完整接触）
- ✅ 其他部位 condim=1（简化）
- 最复杂和精确的配置

### 3.5 Go2 (Python 配置 - go2_constants.py)

**FEET_ONLY_COLLISION:**
```python
FEET_ONLY_COLLISION = CollisionCfg(
    geom_names_expr=(_foot_regex,),
    contype=0,
    conaffinity=1,
    condim=3,
    priority=1,
    friction=(0.6,),  # 仅 mu1
    solimp=(0.9, 0.95, 0.023),
)
```

**FULL_COLLISION:**
```python
FULL_COLLISION = CollisionCfg(
    geom_names_expr=(".*_collision",),
    condim={_foot_regex: 3, ".*_collision": 1},
    priority={_foot_regex: 1},
    friction={_foot_regex: (0.6,)},
    solimp={_foot_regex: (0.9, 0.95, 0.023)},
    contype=1,
    conaffinity=0,
)
```

**特点：**
- ✅ 程序化配置，灵活切换
- ✅ 足部摩擦 0.6（介于 0.4 和 0.8 之间）
- ✅ 足部 condim=3，其他 condim=1
- ✅ 可以选择仅足部碰撞或全身碰撞

---

## 4. 摩擦系数差异分析

### 4.1 mu1 (滑动摩擦) 对比

| 模型 | mu1 | 物理意义 | 适用场景 |
|------|-----|---------|---------|
| **Aliengo** | 1.0 | 高摩擦（橡胶足） | 稳定站立，不易滑动 |
| **Go2 (robot)** | 0.8 | 中高摩擦 | 平衡稳定性和灵活性 |
| **Go2 (scene)** | 0.4 | 中等摩擦 | 更真实的地面 |
| **Go2 (Python)** | 0.6 | 中等摩擦 | 折中方案 |

**影响：**
- **mu1 大** → 不易滑动，站立稳定，但转向困难
- **mu1 小** → 容易滑动，转向灵活，但站立不稳

### 4.2 mu2/mu3 (滚动/扭转摩擦) 对比

| 模型 | mu2 | mu3 | 说明 |
|------|-----|-----|------|
| **Aliengo** | 0.3 | 0.3 | 标准值 |
| **Go2 (robot)** | 0.3 | 0.3 | 与 Aliengo 相同 |
| **Go2 (scene 足部)** | 0.02 | 0.01 | 非常小（更真实） |
| **Go2 (Python)** | 未定义 | 未定义 | 仅使用 mu1 |

**Go2 scene 的小 mu2/mu3 意味着：**
- 足部可以更容易滚动和旋转
- 更接近真实的点接触
- 减少不必要的阻力

---

## 5. condim 差异分析

### 5.1 各模型的 condim 配置

| 模型 | condim | 接触模型 | 计算复杂度 |
|------|--------|---------|-----------|
| **Aliengo** | 3 | 点接触 + 2D 摩擦 | 中等 |
| **Go2 (robot)** | 3 | 点接触 + 2D 摩擦 | 中等 |
| **Go2 (unitree/go2)** | 6 | 完整接触 | 高 |
| **Go2 (scene)** | 1 (默认)<br>6 (足部) | 分层：简化 + 精确 | 优化 |
| **Go2 (Python)** | 1 (默认)<br>3 (足部) | 分层：简化 + 标准 | 中等 |

### 5.2 condim=3 vs condim=6

**condim=3 (标准点接触):**
```
自由度: 3 (法向力 + 2D 切向摩擦)
适用: 点接触、球形足部
优点: 计算快，稳定
缺点: 不考虑接触面积和力矩
```

**condim=6 (完整接触):**
```
自由度: 6 (3D 力 + 3D 力矩)
适用: 面接触、复杂接触
优点: 最精确，考虑接触力矩
缺点: 计算慢，可能不稳定
```

**为什么 Go2 使用 condim=6？**
- 更精确的足部接触模拟
- 考虑足部的旋转阻力
- 更接近真实物理

---

## 6. 实际影响分析

### 6.1 对步态的影响

**高摩擦 (Aliengo, mu1=1.0):**
- ✅ 站立更稳定
- ✅ 不易滑倒
- ❌ 转向需要更大力矩
- ❌ 足部磨损大（真实硬件）

**中等摩擦 (Go2, mu1=0.4-0.8):**
- ✅ 平衡稳定性和灵活性
- ✅ 转向更自然
- ⚠️ 需要更好的平衡控制
- ✅ 更接近真实地面

### 6.2 对仿真性能的影响

| 配置 | 仿真速度 | 稳定性 | 精度 |
|------|---------|--------|------|
| **Aliengo (condim=3, mu1=1.0)** | 快 | 高 | 中 |
| **Go2 robot (condim=3, mu1=0.8)** | 快 | 高 | 中 |
| **Go2 unitree (condim=6)** | 慢 | 中 | 高 |
| **Go2 scene (分层)** | 中 | 中 | 高 |

### 6.3 对控制算法的影响

**需要调整的参数：**

```python
# Aliengo (高摩擦)
Kp_stance = 40.0  # 站立相高刚度
Kd_stance = 2.0

# Go2 (中等摩擦)
Kp_stance = 30.0  # 需要略低的刚度
Kd_stance = 1.5

# 原因：低摩擦需要更柔顺的控制，避免滑动
```

---

## 7. 推荐配置

### 7.1 根据使用场景选择

**学习和算法开发：**
```
推荐: Aliengo 或 Go2 (robot/go2)
摩擦: mu1=0.8-1.0
condim: 3
原因: 简单、稳定、快速
```

**精确仿真和产品开发：**
```
推荐: Go2 (unitree_go2/scene)
摩擦: mu1=0.4-0.6 (足部)
condim: 6 (足部), 1 (其他)
原因: 精确、真实、可配置
```

**性能优先：**
```
推荐: Go2 (Python config - FEET_ONLY_COLLISION)
摩擦: mu1=0.6
condim: 3 (足部), 其他禁用碰撞
原因: 快速、足够精确
```

### 7.2 不同地形的摩擦系数

| 地形 | mu1 | mu2 | mu3 | 说明 |
|------|-----|-----|-----|------|
| **混凝土** | 0.6-0.8 | 0.02 | 0.01 | 标准地面 |
| **橡胶地板** | 0.8-1.0 | 0.05 | 0.02 | 高摩擦 |
| **湿滑地面** | 0.3-0.5 | 0.01 | 0.005 | 低摩擦 |
| **冰面** | 0.02-0.05 | 0.001 | 0.001 | 极低摩擦 |
| **草地** | 0.4-0.6 | 0.03 | 0.02 | 中等摩擦 |

---

## 8. 如何统一配置

### 8.1 修改 XML 文件

**统一为 Aliengo 的配置：**
```xml
<!-- robot/go2/go2.xml -->
<default class="collision">
  <geom priority="1" condim="3" friction="1.0 0.3 0.3" group="3"/>
</default>
```

**统一为中等摩擦：**
```xml
<default class="collision">
  <geom priority="1" condim="3" friction="0.6 0.3 0.3" group="3"/>
</default>
```

### 8.2 程序化配置

```python
# 在运行时修改摩擦系数
import mujoco

model = mujoco.MjModel.from_xml_path('robot/go2/go2.xml')

# 修改所有几何体的摩擦系数
for i in range(model.ngeom):
    model.geom_friction[i] = [0.8, 0.3, 0.3]

# 修改特定几何体
foot_geom_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_GEOM, 'FL_foot_collision')
model.geom_friction[foot_geom_id] = [0.6, 0.02, 0.01]
```

---

## 9. 完整对比表

### 9.1 摩擦系数

| 模型 | mu1 | mu2 | mu3 | 备注 |
|------|-----|-----|-----|------|
| **Aliengo** | 1.0 | 0.3 | 0.3 | 高摩擦，稳定 |
| **Go2 (robot/go2)** | 0.8 | 0.3 | 0.3 | 中高摩擦 |
| **Go2 (unitree/go2)** | 未定义 | 未定义 | 未定义 | 继承默认值 |
| **Go2 (scene 默认)** | 0.4 | - | - | 仅 mu1 |
| **Go2 (scene 足部)** | 0.4 | 0.02 | 0.01 | 低滚动/扭转摩擦 |
| **Go2 (Python)** | 0.6 | - | - | 仅 mu1 |

### 9.2 接触维度

| 模型 | condim (默认) | condim (足部) | 备注 |
|------|--------------|--------------|------|
| **Aliengo** | 3 | 3 | 统一配置 |
| **Go2 (robot/go2)** | 3 | 3 | 统一配置 |
| **Go2 (unitree/go2)** | 6 | 6 | 完整接触 |
| **Go2 (scene)** | 1 | 6 | 分层优化 |
| **Go2 (Python)** | 1 | 3 | 分层优化 |

---

## 10. 常见问题

### Q1: 为什么 Go2 有这么多不同的配置？
**A:** 
- `robot/go2`: 基础配置，兼容性好
- `unitree_go2/go2.xml`: 简化配置，用于快速加载
- `unitree_go2/scene_go2.xml`: 完整配置，最精确
- Python 配置: 程序化配置，灵活切换

### Q2: 应该使用哪个摩擦系数？
**A:**
- 学习/开发: 0.8-1.0（稳定）
- 真实仿真: 0.4-0.6（接近真实地面）
- 性能测试: 0.6（折中）

### Q3: condim=3 和 condim=6 哪个更好？
**A:**
- condim=3: 更快，更稳定，适合大多数情况
- condim=6: 更精确，适合需要考虑接触力矩的场景

### Q4: 如何测试不同的摩擦系数？
**A:**
```python
# 测试不同摩擦系数
friction_values = [0.4, 0.6, 0.8, 1.0]

for mu in friction_values:
    model.geom_friction[:, 0] = mu
    # 运行仿真
    # 记录滑动距离、稳定性等指标
```

---

## 11. 总结

### 11.1 您的表格修正

**原表格（部分正确）：**
| 参数 | Aliengo | Go2 |
|------|---------|-----|
| mu1 | ✅ 1.0 | ⚠️ 0.8 (robot) 或 0.4-0.6 (unitree) |
| mu2 | ✅ 0.3 | ⚠️ 0.3 (robot) 或 0.02 (scene 足部) |
| mu3 | ✅ 0.3 | ⚠️ 0.3 (robot) 或 0.01 (scene 足部) |
| condim | ✅ 3 | ⚠️ 3 (robot) 或 1/6 (scene) |

**修正后：需要指明具体的 Go2 配置文件**

### 11.2 关键差异
1. **摩擦系数**: Aliengo 更高（1.0 vs 0.4-0.8）
2. **接触模型**: Go2 更复杂（分层 condim）
3. **配置方式**: Go2 更灵活（多种配置选项）

### 11.3 建议
- 明确使用哪个 Go2 配置文件
- 根据场景选择合适的摩擦系数
- 优先使用 condim=3（除非需要极高精度）

---

*文档生成时间: 2026-05-12*
*基于实际模型文件分析*
