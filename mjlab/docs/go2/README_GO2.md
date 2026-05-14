# Unitree Go2 集成 - 使用指南

## 📁 文件说明

### 配置文件
- **`my_go2_config.py`** - 你的自定义配置文件（修改这个文件来调整参数）
- **`run_go2_custom.py`** - 使用自定义配置运行Go2的主脚本
- **`GO2_CONFIG_GUIDE.md`** - 详细的配置参数说明文档

### 测试文件
- **`test_go2_env.py`** - 简单的环境测试脚本
- **`run_go2.py`** - 通用的Go2运行脚本（不使用自定义配置）

### 文档
- **`GO2_INTEGRATION_SUMMARY.md`** - Go2集成总结
- **`GO2_CONFIG_GUIDE.md`** - 配置参数详细指南

## 🚀 快速开始

### 1️⃣ 修改配置
编辑 `my_go2_config.py`：
```python
ENV_CONFIG = {
    "num_envs": 4096,      # 环境数量
    "terrain": "flat",     # 地形类型
    ...
}
```

### 2️⃣ 测试配置
```bash
uv run python run_go2_custom.py --mode test
```

### 3️⃣ 开始训练
```bash
uv run python run_go2_custom.py --mode train
```

### 4️⃣ 播放模型
```bash
uv run python run_go2_custom.py --mode play --checkpoint logs/go2_velocity_custom/model_5000.pt
```

## 📊 配置示例

### 快速测试（少量环境）
```python
ENV_CONFIG["num_envs"] = 256
RL_CONFIG["max_iterations"] = 100
```

### 完整训练（大量环境）
```python
ENV_CONFIG["num_envs"] = 4096
RL_CONFIG["max_iterations"] = 10000
RUN_CONFIG["headless"] = True
```

### 调整机器人行为
```python
# 更快的速度
ENV_CONFIG["rewards"]["track_linear_velocity"] = 3.0

# 更平滑的动作
ENV_CONFIG["rewards"]["action_rate_l2"] = -0.5

# 更多跳跃
ENV_CONFIG["rewards"]["air_time"] = 3.0
```

## 🎯 主要配置参数

### 环境配置 (ENV_CONFIG)
- `num_envs`: 并行环境数量（4096推荐）
- `terrain`: 地形类型（"flat" 或 "rough"）
- `rewards`: 奖励权重字典
- `velocity_command`: 速度命令范围

### 强化学习配置 (RL_CONFIG)
- `learning_rate`: 学习率（1e-3）
- `max_iterations`: 训练迭代次数（10000）
- `actor_hidden_dims`: Actor网络结构
- `num_steps_per_env`: 每环境步数（24）

### 运行配置 (RUN_CONFIG)
- `device`: 运行设备（"cuda:0"）
- `headless`: 无界面模式（False/True）

## 📈 训练监控

查看训练进度：
```bash
tensorboard --logdir logs/go2_velocity_custom/summaries
```

## 🔧 性能调优

### GPU内存不足
- 减少 `num_envs`: 4096 → 2048 → 1024
- 减小网络: `(512,256,128)` → `(256,128,64)`

### 训练太慢
- 增加 `num_envs`
- 设置 `headless = True`
- 减少 `num_learning_epochs`

### 学习不稳定
- 降低 `learning_rate`: 1e-3 → 5e-4
- 增加 `num_mini_batches`: 4 → 8

## 📚 更多信息

详细的配置说明请查看 **`GO2_CONFIG_GUIDE.md`**

## ✅ 已验证

- ✓ 环境初始化成功
- ✓ 4096个并行环境运行正常
- ✓ GPU (cuda:0) 加速
- ✓ 观察空间: actor (48维), critic (72维)
- ✓ 动作空间: 12维关节控制
- ✓ 代码质量检查通过（ruff + pyright）

## 🎮 运行模式

### test - 测试模式
快速测试环境是否正常工作
```bash
uv run python run_go2_custom.py --mode test
```

### train - 训练模式
使用自定义配置训练Go2策略
```bash
uv run python run_go2_custom.py --mode train
```

### play - 播放模式
加载训练好的模型并可视化
```bash
uv run python run_go2_custom.py --mode play --checkpoint <path>
```

---

**开始使用**: 修改 `my_go2_config.py` → 运行 `uv run python run_go2_custom.py --mode test` ✨
