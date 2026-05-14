# MuJoCo 传感器分析文档

## 1. 触觉传感器 (Touch Sensor)

### 1.1 工作原理

**测量内容：** 接触力的标量大小（scalar contact force magnitude）

**返回值：** 单个浮点数，单位：牛顿 (N)

**计算公式：**
```
F_touch = ||Σ(F_normal + F_friction)||
```
对指定 site 上所有接触点的法向力和摩擦力进行矢量求和，然后取模。

**特点：**
- ✅ 返回接触力的总大小
- ❌ 不包含力的方向信息
- ✅ 适合检测是否接触和接触力大小
- ❌ 不适合需要力矢量的应用

### 1.2 robot/go2/go2.xml 配置分析

**传感器定义（第210-213行）：**
```xml
<touch name="fl_touch" site="FL"/>
<touch name="fr_touch" site="FR"/>
<touch name="rl_touch" site="RL"/>
<touch name="rr_touch" site="RR"/>
```

**Site 定义（第81, 107, 133, 159行）：**
```xml
<site name="FL" pos="0 0 -0.213" type="sphere" size="0.022"/>
<site name="FR" pos="0 0 -0.213" type="sphere" size="0.022"/>
<site name="RL" pos="0 0 -0.213" type="sphere" size="0.022"/>
<site name="RR" pos="0 0 -0.213" type="sphere" size="0.022"/>
```

**碰撞几何体（每条腿有两个足部几何体）：**
```xml
<!-- 产生碰撞的几何体 -->
<geom name="FL_foot_collision" pos="0 0 -0.213" type="sphere" size="0.022" class="collision"/>

<!-- 仅用于可视化的几何体 -->
<geom name="fl_foot" pos="0 0 -0.213" type="sphere" size="0.022" contype="0" conaffinity="0"/>
```

**碰撞类默认配置：**
```xml
<default class="collision">
  <geom priority="1" condim="3" friction="0.8 0.3 0.3" group="3"/>
</default>
```

### 1.3 配置正确性验证

| 检查项 | 状态 | 说明 |
|--------|------|------|
| **Site 位置** | ✅ 正确 | 与碰撞几何体中心完全重合 (0, 0, -0.213) |
| **碰撞属性** | ✅ 正确 | condim=3, friction=0.8 0.3 0.3, priority=1 |
| **传感器类型** | ✅ 正确 | touch sensor 适合测量接触力 |
| **Site 尺寸** | ✅ 正确 | size=0.022 与碰撞球体相同 |

**结论：robot/go2/go2.xml 的触觉传感器配置完全正确。**

### 1.4 数据有效性

在 MuJoCo 仿真中，触觉传感器返回的数据是**物理引擎计算的真实接触力**：

- **足部接触地面时：** 返回接触力大小（通常 10-50N，取决于机器人重量和运动状态）
- **足部离地时：** 返回 0
- **数据来源：** MuJoCo 物理引擎的接触求解器
- **精度：** 取决于仿真时间步长和求解器设置

**数据是正确的，可以用于：**
- 步态检测（判断哪只脚接触地面）
- 接触力估计
- 平衡控制
- 地形识别

---

## 2. 关节力矩传感器 (Joint Actuator Force Sensor)

### 2.1 工作原理

**测量内容：** 关节执行器施加的力或力矩（scalar actuator force/torque）

**返回值：** 单个浮点数，单位：牛顿米 (Nm) 或牛顿 (N)

**特点：**
- ✅ 测量执行器实际输出的力/力矩
- ✅ 可以添加噪声模拟真实传感器
- ✅ 适合力矩控制和力反馈
- ❌ robot/go2 和 robot/aliengo 都没有配置

### 2.2 unitree_go2/xmls/scene_go2.xml 配置

**传感器定义（第264-275行）：**
```xml
<jointactuatorfrc name="FR_hip_torque" joint="FR_hip_joint" noise="0.01" />
<jointactuatorfrc name="FR_thigh_torque" joint="FR_thigh_joint" noise="0.01" />
<jointactuatorfrc name="FR_calf_torque" joint="FR_calf_joint" noise="0.01" />
<!-- ... 共12个关节 ... -->
```

**特点：**
- 每个关节一个力矩传感器
- 噪声水平：0.01 Nm（模拟真实传感器噪声）
- 可以实时监测执行器输出

---

## 3. 传感器对比总结

### 3.1 各模型传感器配置

| 传感器类型 | robot/go2 | robot/aliengo | unitree_go2/scene |
|-----------|-----------|---------------|-------------------|
| **IMU（四元数）** | ✅ Body_Quat | ✅ Body_Quat | ✅ imu_quat |
| **IMU（陀螺仪）** | ✅ Body_Gyro | ✅ Body_Gyro | ✅ imu_gyro |
| **IMU（加速度）** | ✅ Body_Acc | ✅ Body_Acc | ✅ imu_acc |
| **关节位置** | ✅ 12个 | ✅ 12个 | ✅ 12个 |
| **关节速度** | ✅ 12个 | ✅ 12个 | ✅ 12个 |
| **触觉传感器** | ✅ 4个 | ✅ 4个 | ❌ 无 |
| **关节力矩** | ❌ 无 | ❌ 无 | ✅ 12个 |
| **帧位置** | ❌ 无 | ❌ 无 | ✅ frame_pos |
| **帧速度** | ❌ 无 | ❌ 无 | ✅ frame_vel |
| **总数** | 31 | 31 | 41 |

### 3.2 传感器类型对比

| 传感器类型 | 返回值 | 单位 | 用途 |
|-----------|--------|------|------|
| **touch** | 标量（力大小） | N | 接触检测、接触力估计 |
| **force** | 3D矢量 (Fx, Fy, Fz) | N | 力矢量测量 |
| **torque** | 3D矢量 (Tx, Ty, Tz) | Nm | 力矩矢量测量 |
| **jointactuatorfrc** | 标量（关节力矩） | Nm | 执行器力矩反馈 |
| **jointpos** | 标量（关节角度） | rad | 关节位置 |
| **jointvel** | 标量（关节速度） | rad/s | 关节速度 |
| **gyro** | 3D矢量（角速度） | rad/s | 姿态估计 |
| **accelerometer** | 3D矢量（加速度） | m/s² | 运动估计 |

---

## 4. 使用建议

### 4.1 选择 robot/go2/go2.xml 或 robot/aliengo/aliengo.xml 当需要：
- ✅ 触觉传感器（足部接触力）
- ✅ 步态检测和接触状态估计
- ✅ 基于接触力的控制
- ✅ 完整的 IMU + 关节传感器套件

### 4.2 选择 unitree_go2/xmls/scene_go2.xml 当需要：
- ✅ 关节力矩传感器（执行器反馈）
- ✅ 力矩控制
- ✅ 传感器噪声模拟
- ✅ 帧位置和速度传感器
- ❌ 但缺少触觉传感器

### 4.3 如何同时获得触觉和力矩传感器？

**方案1：修改 scene_go2.xml，添加触觉传感器**
```xml
<sensor>
  <!-- 现有的传感器 -->
  ...
  
  <!-- 添加触觉传感器 -->
  <touch name="fl_touch" site="FL"/>
  <touch name="fr_touch" site="FR"/>
  <touch name="rl_touch" site="RL"/>
  <touch name="rr_touch" site="RR"/>
</sensor>
```

**方案2：修改 go2.xml，添加力矩传感器**
```xml
<sensor>
  <!-- 现有的传感器 -->
  ...
  
  <!-- 添加力矩传感器 -->
  <jointactuatorfrc name="FL_hip_torque" joint="FL_hip_joint" noise="0.01"/>
  <jointactuatorfrc name="FL_thigh_torque" joint="FL_thigh_joint" noise="0.01"/>
  <!-- ... 其他关节 ... -->
</sensor>
```

---

## 5. 常见问题

### Q1: 触觉传感器返回的数据准确吗？
**A:** 是的。MuJoCo 的触觉传感器返回的是物理引擎计算的真实接触力，精度取决于：
- 仿真时间步长（timestep）
- 接触求解器设置（solver iterations）
- 碰撞几何体的精度

### Q2: 为什么有两个足部几何体？
**A:** 
- `FL_foot_collision`: contype≠0，产生碰撞，用于物理计算
- `fl_foot`: contype=0，不产生碰撞，仅用于可视化

### Q3: 触觉传感器能测量力的方向吗？
**A:** 不能。touch sensor 只返回力的大小（标量）。如果需要力矢量，使用 force sensor。

### Q4: 关节力矩传感器和触觉传感器有什么区别？
**A:**
- **触觉传感器：** 测量外部接触力（如足部与地面的接触）
- **力矩传感器：** 测量内部执行器力矩（电机输出）

### Q5: 如何在代码中读取传感器数据？
**A:**
```python
import mujoco

# 加载模型
model = mujoco.MjModel.from_xml_path('robot/go2/go2.xml')
data = mujoco.MjData(model)

# 仿真一步
mujoco.mj_step(model, data)

# 读取触觉传感器（假设 fl_touch 是第28个传感器）
fl_touch_force = data.sensordata[28]

# 读取关节位置（假设 FL_hip_pos 是第3个传感器）
fl_hip_pos = data.sensordata[3]

# 或者通过名称查找
sensor_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SENSOR, 'fl_touch')
fl_touch_force = data.sensordata[model.sensor_adr[sensor_id]]
```

---

## 6. Go2 vs Aliengo 足部差异

| 参数 | Go2 | Aliengo |
|------|-----|---------|
| **足部位置** | (0, 0, -0.213) | (0, 0, -0.25) |
| **足部半径** | 0.022 m | 0.0255 m |
| **Site 半径** | 0.022 m | 0.0265 m |
| **小腿长度** | 0.213 m | 0.25 m |

**注意：** Aliengo 的腿更长，足部更大。

---

*文档生成时间: 2026-05-12*
*基于 MuJoCo 3.x 文档*
