# Go2 自定义配置使用指南

## 快速开始

### 1. 修改配置
编辑 `my_go2_config.py` 文件来自定义你的参数：

```python
# 修改环境数量
ENV_CONFIG = {
    "num_envs": 4096,  # 改成你想要的数量
    "terrain": "flat",  # 或 "rough"
    ...
}

# 修改奖励权重
ENV_CONFIG["rewards"] = {
    "track_linear_velocity": 2.0,  # 调整这个值
    "air_time": 2.0,  # Go2专用，调整跳跃奖励
    ...
}

# 修改学习率
RL_CONFIG = {
    "learning_rate": 1e-3,  # 调整学习率
    "max_iterations": 10000,  # 训练迭代次数
    ...
}
```

### 2. 运行测试
测试你的配置是否正常工作：
```bash
uv run python run_go2_custom.py --mode test
```

### 3. 开始训练
使用你的自定义配置训练Go2：
```bash
uv run python run_go2_custom.py --mode train
```

### 4. 播放训练好的模型
```bash
uv run python run_go2_custom.py --mode play --checkpoint logs/go2_velocity_custom/model_5000.pt
```

## 配置文件详解

### ENV_CONFIG - 环境配置

#### 基础设置
- `terrain`: 地形类型
  - `"flat"`: 平坦地形（适合初学者）
  - `"rough"`: 粗糙地形（更有挑战性）
- `num_envs`: 并行环境数量（越多训练越快，但需要更多GPU内存）
  - 推荐: 4096 (RTX 4060 8GB)
  - 如果内存不足，可以降到 2048 或 1024
- `episode_length_s`: 每个episode的时长（秒）

#### 仿真参数
- `physics_dt`: 物理仿真步长（秒）
  - 默认: 0.005 (200Hz)
  - 更小的值更精确但更慢
- `control_dt`: 控制频率步长（秒）
  - 默认: 0.02 (50Hz)
  - 必须是 physics_dt 的整数倍

#### 奖励权重
调整这些权重来改变机器人的行为：

- `track_linear_velocity`: 跟踪线速度命令（正值，越大越重视速度跟踪）
- `track_angular_velocity`: 跟踪角速度命令（正值）
- `upright`: 保持直立（正值）
- `pose`: 保持合理姿态（正值）
- `air_time`: 鼓励跳跃/腾空（正值，Go2使用2.0）
- `dof_pos_limits`: 惩罚关节超限（负值）
- `action_rate_l2`: 惩罚动作变化率（负值，平滑动作）
- `foot_clearance`: 惩罚足部拖地（负值）
- `foot_slip`: 惩罚足部滑动（负值）

**调参建议**：
- 想要更快的速度：增大 `track_linear_velocity`
- 想要更稳定：增大 `upright` 和 `pose`
- 想要更平滑的动作：增大 `action_rate_l2` 的绝对值（更负）
- 想要更多跳跃：增大 `air_time`

#### 速度命令范围
- `lin_vel_x`: 前进速度范围 (m/s)
  - 默认: (-1.0, 2.0) 表示可以后退1m/s，前进2m/s
- `lin_vel_y`: 侧向速度范围 (m/s)
- `ang_vel_z`: 旋转速度范围 (rad/s)

### RL_CONFIG - 强化学习配置

#### 网络结构
- `actor_hidden_dims`: Actor网络隐藏层维度
  - 默认: (512, 256, 128)
  - 更大的网络可能学得更好但更慢
- `critic_hidden_dims`: Critic网络隐藏层维度
- `activation`: 激活函数 ("elu", "relu", "tanh")

#### PPO算法参数
- `learning_rate`: 学习率
  - 默认: 1e-3
  - 太大可能不稳定，太小学得慢
- `num_learning_epochs`: 每次更新的训练轮数
  - 默认: 5
- `num_mini_batches`: 小批次数量
  - 默认: 4
- `clip_param`: PPO裁剪参数
  - 默认: 0.2
- `entropy_coef`: 熵系数（鼓励探索）
  - 默认: 0.01
- `gamma`: 折扣因子
  - 默认: 0.99
- `lam`: GAE lambda
  - 默认: 0.95

#### 训练参数
- `num_steps_per_env`: 每个环境每次收集的步数
  - 默认: 24
- `max_iterations`: 最大训练迭代次数
  - 默认: 10000
  - 每次迭代 = num_envs × num_steps_per_env 步
- `save_interval`: 保存checkpoint的间隔
  - 默认: 50 (每50次迭代保存一次)
- `experiment_name`: 实验名称（日志保存路径）

### RUN_CONFIG - 运行配置
- `device`: 运行设备
  - `"cuda:0"`: 使用第一块GPU
  - `"cpu"`: 使用CPU（很慢，不推荐）
- `headless`: 是否无界面运行
  - `False`: 显示可视化界面
  - `True`: 无界面（训练时推荐）
- `seed`: 随机种子（用于复现实验）

## 常见使用场景

### 场景1: 快速测试（少量环境）
```python
ENV_CONFIG["num_envs"] = 256
RL_CONFIG["max_iterations"] = 100
```
```bash
uv run python run_go2_custom.py --mode train
```

### 场景2: 完整训练（大量环境）
```python
ENV_CONFIG["num_envs"] = 4096
RL_CONFIG["max_iterations"] = 10000
RUN_CONFIG["headless"] = True
```
```bash
uv run python run_go2_custom.py --mode train
```

### 场景3: 调整速度范围
```python
ENV_CONFIG["velocity_command"] = {
    "lin_vel_x": (-0.5, 3.0),  # 更快的前进速度
    "lin_vel_y": (-0.3, 0.3),  # 更小的侧向速度
    "ang_vel_z": (-1.5, 1.5),  # 更快的旋转
}
```

### 场景4: 更平滑的动作
```python
ENV_CONFIG["rewards"]["action_rate_l2"] = -0.5  # 从-0.1增加到-0.5
```

### 场景5: 粗糙地形训练
```python
ENV_CONFIG["terrain"] = "rough"
ENV_CONFIG["rewards"]["air_time"] = 3.0  # 增加跳跃奖励
```

## 训练监控

训练日志保存在 `logs/go2_velocity_custom/` 目录下：
- `model_*.pt`: 模型checkpoint
- `summaries/`: TensorBoard日志

查看训练曲线：
```bash
tensorboard --logdir logs/go2_velocity_custom/summaries
```

## 性能优化建议

### GPU内存不足
- 减少 `num_envs` (4096 → 2048 → 1024)
- 减小网络大小 `hidden_dims` ((512,256,128) → (256,128,64))

### 训练太慢
- 增加 `num_envs` (更多并行环境)
- 设置 `headless = True` (关闭可视化)
- 减少 `num_learning_epochs` (5 → 3)

### 学习不稳定
- 降低 `learning_rate` (1e-3 → 5e-4)
- 增加 `num_mini_batches` (4 → 8)
- 调整 `clip_param` (0.2 → 0.1)

## 对比Go1和Go2

主要差异：
1. **主体名称**: Go2使用`base`，Go1使用`trunk`
2. **足部碰撞**: Go2的足部碰撞几何合并到小腿
3. **空中时间奖励**: Go2默认2.0，Go1默认1.0（Go2更擅长跳跃）

你可以通过修改 `my_go2_config.py` 来调整这些参数！
