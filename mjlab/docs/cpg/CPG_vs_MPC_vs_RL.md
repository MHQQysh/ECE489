# CPG vs MPC vs RL - 完整对比

## 🎯 你的核心问题

> "CPG 和 MPC 不一样吗？我们不能用 MPC 来实现速度控制吗？"

**答案**: CPG、MPC、RL 是三种**完全不同**的控制方法！

## 📊 三种方法对比

| 特性 | CPG | MPC | RL |
|------|-----|-----|-----|
| **全称** | Central Pattern Generator | Model Predictive Control | Reinforcement Learning |
| **中文** | 中枢模式发生器 | 模型预测控制 | 强化学习 |
| **控制类型** | 开环 | 闭环 | 闭环 |
| **需要模型** | ❌ 不需要 | ✅ 需要精确模型 | ❌ 不需要 |
| **需要训练** | ❌ 不需要 | ❌ 不需要 | ✅ 需要 |
| **计算复杂度** | 很低 | 高 | 中等 |
| **实时性** | 极好 | 一般 | 好 |
| **适应性** | 差 | 好 | 很好 |

## 1️⃣ CPG (Central Pattern Generator)

### 原理
```python
# 纯数学公式，周期性运动
joint_angle = amplitude * sin(2π * frequency * time + phase) + offset
```

### 特点
- ✅ **极简单**: 就是正弦波
- ✅ **极快**: 几乎无计算
- ✅ **不需要模型**: 不需要知道机器人动力学
- ❌ **开环**: 不看传感器
- ❌ **不适应**: 不能应对干扰

### 代码示例
```python
# CPG 控制器
class CPGController:
    def compute_actions(self, dt, velocity_command):
        # 速度 → 频率映射
        frequency = base_freq * (0.5 + velocity)
        
        # 生成正弦轨迹
        phase = 2 * π * frequency * time
        actions = amplitude * sin(phase) + offset
        return actions
```

### 适用场景
- 平坦地面
- 无干扰环境
- 作为基线对比
- 快速原型

## 2️⃣ MPC (Model Predictive Control)

### 原理
```python
# 每一步都优化未来 N 步的轨迹
for each timestep:
    # 1. 预测未来 N 步
    predicted_states = model.predict(current_state, actions)
    
    # 2. 优化目标函数
    optimal_actions = optimize(
        minimize: cost(predicted_states, target),
        subject to: constraints
    )
    
    # 3. 执行第一步
    execute(optimal_actions[0])
```

### 特点
- ✅ **闭环**: 使用传感器反馈
- ✅ **最优**: 每步都优化
- ✅ **处理约束**: 可以加入关节限制、稳定性约束
- ✅ **可解释**: 知道为什么这样做
- ❌ **需要模型**: 必须有精确的动力学模型
- ❌ **计算量大**: 每步都要解优化问题
- ❌ **模型误差**: 模型不准确会导致失败

### 代码示例（概念）
```python
# MPC 控制器
class MPCController:
    def compute_actions(self, current_state, target_velocity):
        # 1. 预测未来轨迹
        horizon = 10  # 预测 10 步
        predicted_states = []
        for i in range(horizon):
            next_state = self.model.predict(state, action)
            predicted_states.append(next_state)
        
        # 2. 优化
        def cost_function(actions):
            states = self.rollout(current_state, actions)
            # 速度跟踪 + 稳定性 + 能量
            cost = (
                ||velocity - target||^2 +
                ||orientation - upright||^2 +
                ||torques||^2
            )
            return cost
        
        optimal_actions = scipy.optimize.minimize(cost_function)
        
        # 3. 执行第一步
        return optimal_actions[0]
```

### 适用场景
- 有精确模型
- 计算资源充足
- 需要最优性保证
- 工业机器人

### pympc-quadruped 项目

你提到的 `/home/y/ece489/lab4/pympc-quadruped` 就是用 MPC 的！

```python
# 从 pympc-quadruped/scripts/mujoco_aliengo.py
predictive_controller = ModelPredictiveController(...)
contact_forces = predictive_controller.update_mpc_if_needed(
    iter_counter, vel_base_des, yaw_turn_rate_des, gait_table
)
```

**关键**: MPC 需要：
1. 机器人动力学模型（质量、惯性、摩擦）
2. 优化求解器（Drake、OSQP）
3. 每步解优化问题

## 3️⃣ RL (Reinforcement Learning)

### 原理
```python
# 训练阶段：学习策略
for episode in training:
    state = env.reset()
    for step in episode:
        action = policy(state)  # 神经网络
        next_state, reward = env.step(action)
        # 更新策略以最大化奖励
        policy.update(state, action, reward)

# 推理阶段：使用策略
action = policy(observation)  # 直接输出
```

### 特点
- ✅ **闭环**: 使用传感器
- ✅ **不需要模型**: 从数据学习
- ✅ **适应性强**: 可以应对各种情况
- ✅ **端到端**: 观察 → 动作
- ❌ **需要训练**: 2-4 小时
- ❌ **黑盒**: 不知道为什么这样做
- ❌ **Sim2Real**: 仿真到现实有差距

### 代码示例
```python
# RL 策略
class RLPolicy:
    def __init__(self):
        self.network = NeuralNetwork([512, 256, 128])
    
    def compute_actions(self, observation):
        # 观察: [速度, 角速度, 姿态, 关节位置, 关节速度, ...]
        # 直接输出动作，无需优化
        actions = self.network(observation)
        return actions
```

### 适用场景
- 复杂环境
- 难以建模
- 需要适应性
- 有训练资源

## 🔍 为什么不用 MPC？

### MPC 的优势
1. **最优性**: 理论上最优
2. **可解释**: 知道为什么
3. **处理约束**: 明确的约束

### MPC 的问题
1. **需要精确模型**: 
   ```
   机器人质量、惯性、摩擦系数、地面接触模型...
   任何一个不准确都会导致失败
   ```

2. **计算量大**:
   ```
   每 20ms 要解一个优化问题
   预测 10 步 × 12 关节 = 120 维优化
   ```

3. **实时性差**:
   ```
   优化求解可能需要 10-50ms
   控制频率只有 20-100Hz
   ```

4. **模型误差累积**:
   ```
   预测 10 步，每步都有误差
   误差会累积，导致预测不准
   ```

### 为什么选择 RL？

1. **不需要模型**: 从数据学习，自动发现动力学
2. **快速推理**: 神经网络前向传播 < 1ms
3. **适应性**: 训练时见过各种情况
4. **端到端**: 直接从观察到动作

## 📈 实际性能对比

| 方法 | 速度跟踪 | 稳定性 | 鲁棒性 | 计算时间 |
|------|---------|--------|--------|---------|
| **CPG** | ⭐⭐ | ⭐⭐ | ⭐ | < 0.1ms |
| **MPC** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | 10-50ms |
| **RL** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 1-2ms |

## 🎯 你的作业应该用什么？

### 作业要求
- 对比 RL 策略和基线方法
- 证明 RL 的优势

### 推荐方案
✅ **RL vs CPG**
- CPG 简单，容易实现
- 对比明显，RL 优势大
- 符合作业要求

❌ **RL vs MPC**
- MPC 实现复杂
- 需要精确模型
- 可能 MPC 也很好，对比不明显

## 💡 总结

### CPG
```
优点: 简单、快速
缺点: 开环、不适应
用途: 基线对比
```

### MPC
```
优点: 最优、可解释
缺点: 需要模型、计算量大
用途: 工业应用
```

### RL
```
优点: 适应性强、不需要模型
缺点: 需要训练、黑盒
用途: 复杂环境
```

## 🚀 你的实验

```bash
# 1. 使用 CPG 作为基线
uv run python src/mjlab/scripts/evaluate_controller.py \
  --controller cpg --num-trials 10

# 2. 评估 RL 策略
uv run python src/mjlab/scripts/evaluate_controller.py \
  --controller rl \
  --checkpoint YOUR_CHECKPOINT.pt \
  --num-trials 10

# 3. 生成对比报告
uv run python src/mjlab/scripts/generate_comparison_report.py \
  --rl-result evaluation_results/rl_*.json \
  --cpg-result evaluation_results/cpg_*.json
```

**结论**: 用 CPG 作为基线，简单有效，对比明显！

---

**CPG ≠ MPC ≠ RL，三种完全不同的方法！** 🎯
