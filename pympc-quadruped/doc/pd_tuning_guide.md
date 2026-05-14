# PD控制器参数调优指南

## 1. 基础理论

### 1.1 PD控制器原理

```
τ = Kp * (q_desired - q_actual) + Kd * (q̇_desired - q̇_actual)
```

- **Kp (比例增益)**: 控制位置误差的响应强度
- **Kd (微分增益)**: 控制速度误差的响应强度，提供阻尼

### 1.2 参数影响

| 参数 | 增大效果 | 减小效果 |
|------|---------|---------|
| **Kp** | - 响应更快<br>- 位置跟踪更准确<br>- 容易振荡<br>- 可能不稳定 | - 响应慢<br>- 位置误差大<br>- 更稳定<br>- 更柔顺 |
| **Kd** | - 增加阻尼<br>- 减少振荡<br>- 减少超调<br>- 对噪声敏感 | - 阻尼不足<br>- 容易振荡<br>- 超调大<br>- 对噪声不敏感 |

### 1.3 经验法则

**Kp/Kd 比例关系：**
```
Kd ≈ 2 * sqrt(Kp * I)  （临界阻尼）
Kd ≈ 0.05 ~ 0.1 * Kp   （四足机器人常用）
```

其中 I 是关节的惯性矩。

---

## 2. 调参方法

### 2.1 Ziegler-Nichols 方法（经典方法）

**步骤：**

1. **设置 Kd = 0**，只调 Kp
2. **逐渐增大 Kp**，直到系统开始持续振荡
3. **记录临界增益 Kp_critical** 和振荡周期 T_critical
4. **计算参数：**
   ```
   Kp = 0.6 * Kp_critical
   Kd = 0.075 * Kp_critical * T_critical
   ```

**优点：** 系统化，有理论基础  
**缺点：** 需要让系统振荡，可能损坏硬件

### 2.2 手动调参法（推荐用于仿真）

**步骤1：调 Kp（Kd = 0）**

1. 从小值开始（如 Kp = 1）
2. 逐步增大 Kp（每次翻倍：1 → 2 → 5 → 10 → 20）
3. 观察响应：
   - 太小：响应慢，位置误差大
   - 太大：振荡、不稳定
4. 找到刚好开始振荡的 Kp 值
5. 选择 **Kp = 0.5 ~ 0.7 * Kp_振荡**

**步骤2：调 Kd（固定 Kp）**

1. 从 Kd = 0.05 * Kp 开始
2. 逐步增大 Kd
3. 观察响应：
   - 太小：仍然振荡
   - 合适：快速收敛，无振荡
   - 太大：响应变慢，过阻尼
4. 选择刚好消除振荡的 Kd

**步骤3：微调**

1. 同时微调 Kp 和 Kd
2. 在稳定性和响应速度之间找平衡

### 2.3 基于物理模型的方法（最优）

**考虑关节特性：**

```python
# 基于关节惯性和期望带宽
ω_n = 2 * π * f_desired  # 期望自然频率（Hz）
ζ = 0.7  # 阻尼比（0.7 为临界阻尼）

Kp = I * ω_n²
Kd = 2 * ζ * sqrt(Kp * I)
```

**参数：**
- `I`: 关节惯性矩（kg·m²）
- `f_desired`: 期望响应频率（通常 5-20 Hz）
- `ζ`: 阻尼比（0.7 为临界阻尼，1.0 为过阻尼）

---

## 3. 四足机器人经验值

### 3.1 Unitree Go2 参考值

**当前配置（unitree_go2/go2_constants.py）：**

| 关节 | Kp | Kd | Effort Limit | Armature |
|------|----|----|--------------|----------|
| **Hip** | 20.0 | 1.0 | 23.5 Nm | 0.01 |
| **Thigh** | 20.0 | 1.0 | 23.5 Nm | 0.01 |
| **Calf** | 40.0 | 2.0 | 45.0 Nm | 0.02 |

**分析：**
- Kd/Kp 比例 = 0.05（5%）
- Calf 的 Kp 是 Hip/Thigh 的 2 倍（因为小腿更轻，需要更强的控制）
- Kd 也相应翻倍

### 3.2 典型范围（四足机器人）

| 关节类型 | Kp 范围 | Kd 范围 | Kd/Kp 比例 |
|---------|---------|---------|-----------|
| **Hip (外展/内收)** | 10 - 50 | 0.5 - 5 | 0.05 - 0.1 |
| **Thigh (大腿)** | 15 - 60 | 0.75 - 6 | 0.05 - 0.1 |
| **Calf (小腿)** | 30 - 100 | 1.5 - 10 | 0.05 - 0.1 |

**经验规律：**
- 远端关节（小腿）> 近端关节（大腿）> 髋关节
- 原因：远端关节惯性小，需要更强的控制

### 3.3 其他机器人参考

**MIT Cheetah 3:**
- Hip: Kp = 80, Kd = 2
- Thigh: Kp = 80, Kd = 2
- Calf: Kp = 80, Kd = 2

**ANYmal:**
- Hip: Kp = 40, Kd = 1
- Thigh: Kp = 40, Kd = 1
- Calf: Kp = 40, Kd = 1

**Unitree A1:**
- Hip: Kp = 20, Kd = 0.5
- Thigh: Kp = 20, Kd = 0.5
- Calf: Kp = 20, Kd = 0.5

---

## 4. 调参观察指标

### 4.1 时域指标

| 指标 | 定义 | 理想值 |
|------|------|--------|
| **上升时间 (Rise Time)** | 从 10% 到 90% 的时间 | 越短越好（但不能振荡） |
| **超调量 (Overshoot)** | 超过目标值的百分比 | < 5% |
| **调节时间 (Settling Time)** | 进入 ±2% 误差带的时间 | < 0.5s |
| **稳态误差 (Steady-State Error)** | 最终误差 | < 0.01 rad |

### 4.2 观察方法

**在仿真中：**

```python
import matplotlib.pyplot as plt

# 记录数据
time = []
q_desired = []
q_actual = []
q_error = []
torque = []

# 仿真循环
for i in range(1000):
    mujoco.mj_step(model, data)
    time.append(data.time)
    q_desired.append(target_pos)
    q_actual.append(data.qpos[joint_id])
    q_error.append(target_pos - data.qpos[joint_id])
    torque.append(data.actuator_force[actuator_id])

# 绘图
fig, axes = plt.subplots(3, 1, figsize=(10, 8))

# 位置跟踪
axes[0].plot(time, q_desired, 'r--', label='Desired')
axes[0].plot(time, q_actual, 'b-', label='Actual')
axes[0].set_ylabel('Position (rad)')
axes[0].legend()
axes[0].grid(True)

# 位置误差
axes[1].plot(time, q_error, 'g-')
axes[1].set_ylabel('Error (rad)')
axes[1].grid(True)

# 控制力矩
axes[2].plot(time, torque, 'k-')
axes[2].set_ylabel('Torque (Nm)')
axes[2].set_xlabel('Time (s)')
axes[2].grid(True)

plt.tight_layout()
plt.show()
```

### 4.3 判断标准

**好的参数：**
- ✅ 快速响应（上升时间短）
- ✅ 无振荡或轻微振荡
- ✅ 小超调（< 5%）
- ✅ 稳态误差小
- ✅ 力矩平滑，无高频抖动

**差的参数：**
- ❌ Kp 太小：响应慢，误差大，"软绵绵"
- ❌ Kp 太大：振荡，不稳定，"抖动"
- ❌ Kd 太小：振荡，超调大
- ❌ Kd 太大：响应慢，过阻尼，"迟钝"

---

## 5. 实战调参流程

### 5.1 准备工作

1. **确定测试场景：**
   - 单关节阶跃响应测试
   - 站立平衡测试
   - 步态跟踪测试

2. **设置初始值：**
   ```python
   # 保守的初始值
   Kp_hip = 10.0
   Kd_hip = 0.5
   Kp_thigh = 15.0
   Kd_thigh = 0.75
   Kp_calf = 30.0
   Kd_calf = 1.5
   ```

### 5.2 单关节测试

**测试代码：**
```python
import mujoco
import numpy as np

# 加载模型
model = mujoco.MjModel.from_xml_path('robot/go2/go2.xml')
data = mujoco.MjData(model)

# 设置 PD 参数
actuator_id = 0  # FL_hip
Kp = 20.0
Kd = 1.0

# 阶跃输入
target_pos = 0.5  # rad

# 仿真
for i in range(1000):
    # PD 控制
    q = data.qpos[joint_id]
    qd = data.qvel[joint_id]
    tau = Kp * (target_pos - q) + Kd * (0 - qd)
    
    # 限制力矩
    tau = np.clip(tau, -23.5, 23.5)
    
    # 应用控制
    data.ctrl[actuator_id] = tau
    
    # 仿真一步
    mujoco.mj_step(model, data)
```

### 5.3 调参步骤

**第1轮：粗调 Kp**
```python
Kp_values = [5, 10, 20, 40, 80]
Kd = 0

for Kp in Kp_values:
    # 运行测试
    # 观察响应
    # 记录是否振荡
```

**第2轮：粗调 Kd**
```python
Kp = 20  # 从第1轮选择的值
Kd_values = [0.5, 1.0, 2.0, 4.0]

for Kd in Kd_values:
    # 运行测试
    # 观察振荡是否消除
```

**第3轮：微调**
```python
# 在最优值附近微调
Kp_range = np.linspace(15, 25, 5)
Kd_range = np.linspace(0.75, 1.5, 5)

best_score = float('inf')
best_params = None

for Kp in Kp_range:
    for Kd in Kd_range:
        # 运行测试
        score = calculate_performance(...)
        if score < best_score:
            best_score = score
            best_params = (Kp, Kd)
```

### 5.4 性能评分函数

```python
def calculate_performance(time, q_desired, q_actual, torque):
    """
    计算控制性能评分（越小越好）
    """
    # 位置误差（RMSE）
    error = np.array(q_desired) - np.array(q_actual)
    rmse = np.sqrt(np.mean(error**2))
    
    # 调节时间（进入 ±2% 误差带）
    threshold = 0.02 * abs(q_desired[-1])
    settling_idx = np.where(np.abs(error) < threshold)[0]
    settling_time = time[settling_idx[0]] if len(settling_idx) > 0 else time[-1]
    
    # 超调量
    overshoot = (np.max(q_actual) - q_desired[-1]) / q_desired[-1]
    overshoot = max(0, overshoot)
    
    # 力矩平滑度（变化率）
    torque_smoothness = np.mean(np.abs(np.diff(torque)))
    
    # 综合评分
    score = (
        10.0 * rmse +           # 位置精度权重
        2.0 * settling_time +   # 响应速度权重
        5.0 * overshoot +       # 超调惩罚
        0.1 * torque_smoothness # 平滑度权重
    )
    
    return score
```

---

## 6. 高级技巧

### 6.1 自适应增益

根据运动状态调整增益：

```python
def adaptive_gains(q_error, qd_error, base_Kp, base_Kd):
    """
    根据误差大小自适应调整增益
    """
    # 误差大时增大 Kp，加快响应
    if abs(q_error) > 0.1:
        Kp = base_Kp * 1.5
    else:
        Kp = base_Kp
    
    # 速度大时增大 Kd，增加阻尼
    if abs(qd_error) > 1.0:
        Kd = base_Kd * 1.5
    else:
        Kd = base_Kd
    
    return Kp, Kd
```

### 6.2 前馈补偿

```python
def pd_with_feedforward(q_des, qd_des, qdd_des, q, qd, Kp, Kd, I):
    """
    PD + 前馈控制
    """
    # PD 反馈
    tau_fb = Kp * (q_des - q) + Kd * (qd_des - qd)
    
    # 前馈（基于期望加速度）
    tau_ff = I * qdd_des
    
    # 总控制力矩
    tau = tau_fb + tau_ff
    
    return tau
```

### 6.3 重力补偿

```python
def pd_with_gravity_compensation(q_des, qd_des, q, qd, Kp, Kd, model, data):
    """
    PD + 重力补偿
    """
    # PD 反馈
    tau_fb = Kp * (q_des - q) + Kd * (qd_des - qd)
    
    # 重力补偿
    mujoco.mj_inverse(model, data)
    tau_gravity = data.qfrc_bias[joint_id]
    
    # 总控制力矩
    tau = tau_fb + tau_gravity
    
    return tau
```

### 6.4 不同步态使用不同增益

```python
class GaitDependentGains:
    def __init__(self):
        # 站立时：高刚度
        self.standing_gains = {
            'hip': (40.0, 2.0),
            'thigh': (40.0, 2.0),
            'calf': (80.0, 4.0)
        }
        
        # 行走时：中等刚度
        self.walking_gains = {
            'hip': (20.0, 1.0),
            'thigh': (20.0, 1.0),
            'calf': (40.0, 2.0)
        }
        
        # 跑步时：低刚度（更柔顺）
        self.running_gains = {
            'hip': (10.0, 0.5),
            'thigh': (10.0, 0.5),
            'calf': (20.0, 1.0)
        }
    
    def get_gains(self, gait_type, joint_name):
        if gait_type == 'standing':
            return self.standing_gains[joint_name]
        elif gait_type == 'walking':
            return self.walking_gains[joint_name]
        elif gait_type == 'running':
            return self.running_gains[joint_name]
```

---

## 7. 常见问题

### Q1: 为什么我的机器人一直抖动？
**A:** 
- Kp 太大 → 减小 Kp
- Kd 太小 → 增大 Kd
- 传感器噪声 → 增大 Kd 或添加滤波器
- 时间步长太大 → 减小 timestep

### Q2: 为什么响应很慢？
**A:**
- Kp 太小 → 增大 Kp
- Kd 太大 → 减小 Kd
- 力矩限制太小 → 检查 effort_limit

### Q3: 为什么站不稳？
**A:**
- 增益太小 → 增大 Kp 和 Kd
- 增益不平衡 → 确保各关节增益协调
- 缺少重力补偿 → 添加重力补偿

### Q4: 仿真和实物差异大怎么办？
**A:**
- 仿真中增益通常需要更大（因为没有摩擦、柔性等）
- 实物上从仿真值的 50% 开始，逐步增大
- 考虑添加 armature（电机惯性）和 damping（关节阻尼）

### Q5: 如何处理关节限位？
**A:**
```python
# 接近限位时降低增益，避免冲击
def limit_aware_gains(q, q_min, q_max, base_Kp, base_Kd):
    margin = 0.1  # 10% 的安全裕度
    range_size = q_max - q_min
    
    # 距离限位的归一化距离
    dist_to_min = (q - q_min) / range_size
    dist_to_max = (q_max - q) / range_size
    
    # 接近限位时降低增益
    if dist_to_min < margin or dist_to_max < margin:
        scale = 0.5
    else:
        scale = 1.0
    
    return base_Kp * scale, base_Kd * scale
```

---

## 8. 调参检查清单

**开始调参前：**
- [ ] 确认模型惯性参数正确
- [ ] 确认关节限位设置合理
- [ ] 确认力矩限制合理
- [ ] 设置合适的仿真时间步长（0.001 - 0.002s）

**调参过程中：**
- [ ] 从保守值开始（小 Kp，小 Kd）
- [ ] 先调 Kp，再调 Kd
- [ ] 每次只改变一个参数
- [ ] 记录每次测试结果
- [ ] 绘制响应曲线

**调参完成后：**
- [ ] 测试阶跃响应
- [ ] 测试正弦跟踪
- [ ] 测试站立平衡
- [ ] 测试步态跟踪
- [ ] 检查力矩是否在限制内
- [ ] 检查是否有高频振荡

---

## 9. 推荐工具

### 9.1 可视化工具

```python
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

class PDTuner:
    def __init__(self, model, data):
        self.model = model
        self.data = data
        self.fig, self.axes = plt.subplots(3, 1, figsize=(10, 8))
        
    def test_response(self, Kp, Kd, target_pos, duration=2.0):
        # 运行测试并绘图
        pass
    
    def interactive_tune(self):
        # 交互式调参界面
        from matplotlib.widgets import Slider
        
        # 创建滑块
        ax_Kp = plt.axes([0.2, 0.02, 0.6, 0.03])
        ax_Kd = plt.axes([0.2, 0.06, 0.6, 0.03])
        
        slider_Kp = Slider(ax_Kp, 'Kp', 0, 100, valinit=20)
        slider_Kd = Slider(ax_Kd, 'Kd', 0, 10, valinit=1)
        
        def update(val):
            Kp = slider_Kp.val
            Kd = slider_Kd.val
            self.test_response(Kp, Kd, 0.5)
        
        slider_Kp.on_changed(update)
        slider_Kd.on_changed(update)
        
        plt.show()
```

### 9.2 自动调参工具

```python
from scipy.optimize import minimize

def auto_tune(model, data, joint_id, target_pos):
    """
    使用优化算法自动调参
    """
    def objective(params):
        Kp, Kd = params
        score = run_test_and_score(model, data, joint_id, Kp, Kd, target_pos)
        return score
    
    # 初始猜测
    x0 = [20.0, 1.0]
    
    # 约束
    bounds = [(1, 100), (0.1, 10)]
    
    # 优化
    result = minimize(objective, x0, bounds=bounds, method='L-BFGS-B')
    
    return result.x
```

---

## 10. 参考资料

1. **经典控制理论：**
   - Ziegler-Nichols 调参法
   - 根轨迹法
   - 频域分析

2. **四足机器人论文：**
   - MIT Cheetah: "Proprioceptive Actuator Design in the MIT Cheetah"
   - ANYmal: "ANYmal - a highly mobile and dynamic quadrupedal robot"
   - Unitree: "Design and Control of a Highly Dynamic Quadruped Robot"

3. **MuJoCo 文档：**
   - Actuator modeling
   - Contact dynamics
   - Numerical stability

---

*文档生成时间: 2026-05-12*
*基于四足机器人控制经验总结*
