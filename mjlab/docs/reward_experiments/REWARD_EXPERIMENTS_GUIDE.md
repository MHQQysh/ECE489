# 奖励函数对比实验指南

## 概述

本实验设计了 8 组不同的奖励权重配置，针对以下四个目标进行对比：

1. **(i) Forward velocity tracking**: 前向速度跟踪
2. **(ii) Upright body orientation**: 直立姿态保持
3. **(iii) Smooth joint motions**: 平滑关节运动（惩罚 jerk 和力矩）
4. **(iv) Adequate foot clearance**: 足部离地高度

## 快速开始

### 1. 查看实验配置

```bash
python reward_experiments_config.py
```

输出所有 8 组实验的配置摘要。

### 2. 运行单个实验

```bash
# 运行 baseline 实验
python run_reward_experiments.py --experiment baseline --iterations 1000

# 运行 high_velocity 实验
python run_reward_experiments.py --experiment high_velocity --iterations 1000
```

### 3. 运行所有实验（批量）

```bash
# 运行所有 8 组实验
python run_reward_experiments.py --all --iterations 1000
```

**注意**: 运行所有实验需要较长时间，建议使用 `screen` 或 `tmux`：

```bash
screen -S reward_exp
python run_reward_experiments.py --all --iterations 1000
# Ctrl+A, D 分离会话
```

### 4. 分析结果

```bash
# 生成完整分析报告和图表
python analyze_reward_experiments.py

# 只生成文本报告
python analyze_reward_experiments.py --report

# 只绘制对比图
python analyze_reward_experiments.py --plot

# 绘制雷达图
python analyze_reward_experiments.py --radar
```

### 5. 查看训练曲线

```bash
tensorboard --logdir experiments/reward_comparison
```

在浏览器打开 `http://localhost:6006`

## 实验配置详解

### Experiment 1: Baseline (基线)
当前的默认配置，作为对比基准。

```python
track_linear_velocity: 3.0
track_angular_velocity: 2.5
upright: 0.5
pose: 0.5
action_rate_l2: -0.1
foot_clearance: -2.0
air_time: 2.0
```

### Experiment 2: High Velocity (高速度)
**目标**: 最大化速度跟踪性能

**调整**:
- ↑ 线速度权重: 3.0 → 6.0 (2x)
- ↑ 角速度权重: 2.5 → 4.0 (1.6x)
- ↓ 稳定性权重: 降低以允许更激进的运动
- ↓ 平滑度惩罚: 允许更快的动作变化

**预期**: 最快的速度响应，但可能牺牲稳定性和平滑度

### Experiment 3: High Stability (高稳定性)
**目标**: 最大化直立姿态稳定性

**调整**:
- ↑ 直立权重: 0.5 → 2.0 (4x)
- ↑ 姿态权重: 0.5 → 2.0 (4x)
- ↑ 平滑度惩罚: 更严格的动作约束
- ↓ 速度权重: 降低以优先保持稳定

**预期**: 最稳定的姿态，但速度跟踪可能较慢

### Experiment 4: High Smoothness (高平滑度)
**目标**: 最小化 jerk 和力矩

**调整**:
- ↑ Jerk 惩罚: -0.1 → -0.5 (5x)
- 新增 动作惩罚: -0.01
- ↑ 关节限制惩罚: -1.0 → -2.0 (2x)

**预期**: 最平滑的运动，但响应速度可能较慢

### Experiment 5: High Clearance (高离地高度)
**目标**: 最大化足部离地高度

**调整**:
- ↑ 离地高度惩罚: -2.0 → -4.0 (2x)
- ↑ 目标高度: 0.1m → 0.12m
- ↑ 摆动高度惩罚: -0.25 → -0.5 (2x)
- ↑ 空中时间奖励: 2.0 → 3.0 (1.5x)

**预期**: 最高的足部离地，但能耗可能较高

### Experiment 6: Balanced (平衡)
**目标**: 平衡所有四个目标

**调整**:
- 适度提高所有四个目标的权重
- 新增动作惩罚以改善平滑度

**预期**: 四个目标的最佳平衡

### Experiment 7: Aggressive (激进)
**目标**: 高速高动态运动

**调整**:
- 高速度权重
- 低稳定性约束
- 低平滑度约束

**预期**: 最动态的运动，适合高速场景

### Experiment 8: Conservative (保守)
**目标**: 稳定优先

**调整**:
- 低速度权重
- 高稳定性权重
- 高平滑度约束

**预期**: 最保守稳定的运动，适合精确控制

## 训练参数

### 默认参数
```bash
--env.scene.num-envs 1024      # 并行环境数
--agent.max-iterations 1000    # 最大迭代次数
--agent.save-interval 100      # 保存间隔
--video True                   # 生成视频
--video-interval 200           # 视频生成间隔
--video-length 200             # 视频长度
```

### 推荐参数（完整训练）
```bash
--env.scene.num-envs 2048      # 更多并行环境
--agent.max-iterations 5000    # 更长训练时间
--agent.save-interval 500      # 更大保存间隔
```

### 快速测试参数
```bash
--env.scene.num-envs 512       # 较少环境
--agent.max-iterations 100     # 快速测试
--video False                  # 不生成视频
```

## 评估指标

### 1. 速度跟踪 (Velocity Tracking)
- `Rewards/track_linear_velocity`: 线速度跟踪奖励
- `Rewards/track_angular_velocity`: 角速度跟踪奖励
- `Metrics/velocity_error`: 速度误差（如果有）

**评估**: 奖励越高 = 跟踪越好

### 2. 姿态稳定性 (Orientation Stability)
- `Rewards/upright`: 直立姿态奖励
- `Rewards/pose`: 姿态保持奖励
- 观察视频中的姿态抖动

**评估**: 奖励越高 = 姿态越稳定

### 3. 运动平滑度 (Motion Smoothness)
- `Rewards/action_rate_l2`: 动作变化率（jerk）
- `Metrics/mean_action_acc`: 平均动作加速度
- 观察视频中的运动流畅度

**评估**: 惩罚越小（绝对值）= 运动越平滑

### 4. 足部离地高度 (Foot Clearance)
- `Rewards/foot_clearance`: 离地高度惩罚
- `Rewards/foot_swing_height`: 摆动高度惩罚
- `Metrics/air_time_mean`: 平均空中时间
- `Metrics/peak_height_mean`: 平均峰值高度

**评估**: 
- 惩罚越小（绝对值）= 高度越接近目标
- 空中时间和峰值高度越接近目标越好

### 5. 其他指标
- `Rewards/total`: 总奖励
- `Metrics/slip_velocity_mean`: 平均滑动速度（越小越好）
- `Metrics/landing_force_mean`: 平均着陆力（越小越好）
- Episode length: 回合长度（越长越好）

## 结果对比方法

### 1. TensorBoard 曲线对比
```bash
tensorboard --logdir experiments/reward_comparison
```

在 TensorBoard 中：
- 选择多个实验进行对比
- 关注上述关键指标的曲线
- 观察收敛速度和最终性能

### 2. 视频效果对比
```bash
# 查看所有实验的视频
ls experiments/reward_comparison/*/videos/

# 使用视频播放器并排对比
vlc experiments/reward_comparison/baseline_*/videos/*.mp4 &
vlc experiments/reward_comparison/high_velocity_*/videos/*.mp4 &
```

观察：
- 速度响应速度
- 姿态稳定性
- 运动流畅度
- 足部离地高度
- 步态自然度

### 3. 定量指标表格
运行分析脚本生成对比表格：
```bash
python analyze_reward_experiments.py --report
```

查看 `experiments/reward_comparison/comparison_report.txt`

## 常见问题

### Q1: 训练时间太长怎么办？
A: 
- 减少迭代次数: `--iterations 500`
- 减少环境数: `--num-envs 512`
- 关闭视频生成: `--video False`

### Q2: 如何恢复中断的训练？
A:
```bash
python run_reward_experiments.py --experiment baseline --resume
```

### Q3: 如何只运行部分实验？
A:
```bash
# 运行 3 个关键实验
python run_reward_experiments.py --experiment baseline --iterations 1000
python run_reward_experiments.py --experiment high_velocity --iterations 1000
python run_reward_experiments.py --experiment balanced --iterations 1000
```

### Q4: 如何调整实验配置？
A: 编辑 `reward_experiments_config.py`，修改对应实验的 `RewardWeights` 配置。

### Q5: 如何添加新的实验？
A: 在 `reward_experiments_config.py` 中添加新的配置：
```python
NEW_EXPERIMENT = RewardWeights(
    track_linear_velocity=4.0,
    # ... 其他参数
)

EXPERIMENTS = {
    # ... 现有实验
    'new_experiment': NEW_EXPERIMENT,
}
```

## 预期时间估算

### 单个实验
- 1000 iterations, 1024 envs: ~30-60 分钟
- 5000 iterations, 2048 envs: ~3-5 小时

### 所有实验（8 组）
- 1000 iterations: ~4-8 小时
- 5000 iterations: ~24-40 小时

**建议**: 使用 `screen` 或 `tmux` 在后台运行

## 文件结构

```
experiments/reward_comparison/
├── results.json                          # 实验结果汇总
├── comparison_report.txt                 # 对比报告
├── reward_weights_comparison.png         # 权重对比图
├── radar_chart_comparison.png            # 雷达图
├── EXPERIMENT_SUMMARY.md                 # 实验摘要
├── baseline_20240512_120000/             # Baseline 实验
│   ├── reward_config.json
│   ├── checkpoints/
│   ├── videos/
│   └── tensorboard/
├── high_velocity_20240512_130000/        # High Velocity 实验
│   └── ...
└── ...
```

## 下一步

1. **运行实验**: 选择要运行的实验组
2. **监控训练**: 使用 TensorBoard 实时监控
3. **分析结果**: 运行分析脚本生成报告
4. **对比视频**: 观察不同配置的运动效果
5. **选择最佳**: 根据目标选择最佳配置
6. **微调优化**: 基于最佳配置进行微调

## 参考

- 奖励函数分析: `REWARD_ANALYSIS.md`
- 实验配置代码: `reward_experiments_config.py`
- 运行脚本: `run_reward_experiments.py`
- 分析脚本: `analyze_reward_experiments.py`
