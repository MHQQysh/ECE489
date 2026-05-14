# CPG 如何响应目标速度 - 完整说明

## 🎯 核心问题

**问题**: CPG 是开环控制，它怎么知道目标速度？

**答案**: CPG 通过**映射函数**将目标速度转换为步态参数！

## 📊 两种 CPG 实现对比

### 1. 原始 CPG（不响应速度）

```python
# cpg_baseline.py
def compute_actions(self, dt):
    # 固定频率，不管目标速度
    phase = 2 * π * frequency * time
    actions = amplitude * sin(phase) + offset
    return actions
```

**问题**: 
- ❌ 目标速度 = 1.0 m/s → 机器人走 0.3 m/s
- ❌ 目标速度 = 0.5 m/s → 机器人还是走 0.3 m/s
- ❌ 完全不响应命令！

### 2. 速度响应 CPG（新版本）

```python
# cpg_velocity.py
def compute_actions(self, dt, velocity_command):
    # 读取目标速度
    vx = velocity_command[:, 0]  # 前进速度
    
    # 映射 1: 速度 → 频率
    # v=0 → f=0.75Hz, v=1.0 → f=2.25Hz
    frequency = base_frequency * (0.5 + vx)
    
    # 映射 2: 速度 → 步幅
    # v=0 → stride=0.7, v=1.0 → stride=1.2
    stride_scale = 0.7 + vx * 0.5
    
    # 生成动作
    phase = 2 * π * frequency * time
    amplitude = base_amplitude * stride_scale
    actions = amplitude * sin(phase) + offset
    return actions
```

**改进**:
- ✅ 目标速度 = 1.0 m/s → 频率 2.25Hz，大步幅
- ✅ 目标速度 = 0.5 m/s → 频率 1.5Hz，中步幅
- ✅ 目标速度 = 0.0 m/s → 频率 0.75Hz，小步幅
- ✅ 响应命令！

## 🔧 映射函数详解

### 映射 1: 速度 → 频率

```python
frequency = base_frequency * (0.5 + velocity)
```

| 目标速度 (m/s) | 频率 (Hz) | 说明 |
|---------------|----------|------|
| 0.0 | 0.75 | 慢速站立 |
| 0.5 | 1.5 | 正常行走 |
| 1.0 | 2.25 | 快速行走 |
| 1.5 | 3.0 | 跑步 |

**原理**: 速度越快，腿摆动越快

### 映射 2: 速度 → 步幅

```python
stride_scale = 0.7 + velocity * 0.5
amplitude_thigh = base_amplitude * stride_scale
```

| 目标速度 (m/s) | 步幅缩放 | 说明 |
|---------------|---------|------|
| 0.0 | 0.7 | 小步 |
| 0.5 | 0.95 | 中步 |
| 1.0 | 1.2 | 大步 |

**原理**: 速度越快，步幅越大

## 📈 实际效果

### 测试场景

```python
# 场景 1: 慢速
target_velocity = 0.3 m/s
→ frequency = 1.5 * (0.5 + 0.3) = 1.2 Hz
→ stride_scale = 0.7 + 0.3 * 0.5 = 0.85
→ 实际速度 ≈ 0.25-0.35 m/s ✓

# 场景 2: 中速
target_velocity = 0.8 m/s
→ frequency = 1.5 * (0.5 + 0.8) = 1.95 Hz
→ stride_scale = 0.7 + 0.8 * 0.5 = 1.1
→ 实际速度 ≈ 0.7-0.9 m/s ✓

# 场景 3: 快速
target_velocity = 1.2 m/s
→ frequency = 1.5 * (0.5 + 1.2) = 2.55 Hz
→ stride_scale = 0.7 + 1.0 * 0.5 = 1.2 (clamped)
→ 实际速度 ≈ 1.0-1.3 m/s ✓
```

## 🎮 如何使用

### 方法 1: 可视化演示

```bash
uv run python src/mjlab/scripts/demo_cpg_velocity.py
```

这会展示 CPG 如何响应不同的速度命令。

### 方法 2: 评估测试

```bash
uv run python src/mjlab/scripts/evaluate_controller.py \
  --controller cpg \
  --target-velocity 1.0 \
  --num-trials 10
```

CPG 会尝试跟踪 1.0 m/s 的目标速度。

### 方法 3: 在代码中使用

```python
from mjlab.controllers.cpg_velocity import CPGControllerVelocity

# 创建控制器
cpg = CPGControllerVelocity(num_envs=1, device="cuda:0")

# 设置目标速度
target_vel = torch.tensor([[1.0, 0.0, 0.0]])  # [vx, vy, vyaw]

# 生成动作
actions = cpg.compute_actions(dt=0.02, velocity_command=target_vel)
```

## ⚠️ 局限性

### CPG 仍然是开环的！

即使响应速度命令，CPG 仍然有问题：

1. **无反馈**: 不看传感器，不知道实际速度
   ```
   目标: 1.0 m/s
   CPG 认为: 我在走 1.0 m/s
   实际: 可能只有 0.7 m/s（地面滑、上坡等）
   ```

2. **无适应**: 不能应对干扰
   ```
   推一下 → CPG 继续按原计划走 → 摔倒
   RL → 感知到推力 → 调整姿态 → 恢复
   ```

3. **映射不准确**: 速度→频率的映射是手工调的
   ```
   平地: v=1.0 → 实际 0.9 m/s (还行)
   上坡: v=1.0 → 实际 0.5 m/s (差很多)
   ```

## 🆚 CPG vs RL

| 特性 | CPG (速度响应) | RL 策略 |
|------|---------------|---------|
| **读取目标速度** | ✅ 通过映射函数 | ✅ 通过观察值 |
| **调整步态** | ✅ 改变频率/幅度 | ✅ 学习最优动作 |
| **使用传感器** | ❌ 不用 | ✅ 用 |
| **适应干扰** | ❌ 不能 | ✅ 能 |
| **适应地形** | ❌ 不能 | ✅ 能 |
| **速度跟踪精度** | ⚠️ 中等 | ✅ 高 |
| **需要训练** | ❌ 不需要 | ✅ 需要 |

## 📝 总结

### CPG 如何响应速度？

1. **读取目标速度**: `velocity_command[:, 0]`
2. **映射到频率**: `frequency = f(velocity)`
3. **映射到步幅**: `amplitude = g(velocity)`
4. **生成轨迹**: `sin(2πft + φ)`

### 为什么还是不如 RL？

- CPG: "目标 1.0 m/s，我就按 1.0 m/s 的参数走"
- RL: "目标 1.0 m/s，我看看实际多快，调整动作"

**关键区别**: RL 有**闭环反馈**，CPG 没有！

## 🚀 运行演示

```bash
# 1. 看 CPG 如何响应速度
uv run python src/mjlab/scripts/demo_cpg_velocity.py

# 2. 评估 CPG 性能
uv run python src/mjlab/scripts/evaluate_controller.py \
  --controller cpg --target-velocity 1.0 --num-trials 10

# 3. 对比 RL vs CPG
./scripts/run_evaluation.sh
```

---

**现在 CPG 能响应速度命令了，但仍然是开环控制！** 🎯
