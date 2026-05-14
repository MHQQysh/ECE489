# 奖励函数对比实验 - 文件索引

本文档索引了所有与奖励函数对比实验相关的文件。

## 📚 文档类

### 1. 主要文档
- **`REWARD_EXPERIMENTS_SUMMARY.md`** ⭐ - **从这里开始！** 完整总结文档
  - 任务完成情况
  - 快速开始指南
  - 实验配置对比
  - 预期结果
  - 时间估算

- **`REWARD_EXPERIMENTS_GUIDE.md`** - 详细操作指南
  - 实验配置详解
  - 训练参数说明
  - 评估指标定义
  - 结果对比方法
  - 常见问题解答

- **`REWARD_ANALYSIS.md`** - 奖励函数分析
  - 当前所有奖励函数列表
  - 每个奖励函数的公式和作用
  - 权重配置总结
  - 针对四个目标的奖励设计

## 🔧 代码类

### 2. 配置文件
- **`reward_experiments_config.py`** - 实验配置定义
  - `RewardWeights` 数据类
  - 8 组实验配置
  - `EXPERIMENTS` 字典
  - 配置摘要打印函数

### 3. 运行脚本
- **`run_reward_experiments.py`** - Python 运行脚本
  - `ExperimentRunner` 类
  - 单个实验运行
  - 批量实验运行
  - 结果记录和保存
  - 命令行参数解析

- **`run_all_experiments.sh`** - Bash 批量运行脚本
  - 循环运行所有实验
  - 进度显示
  - 时间统计
  - 简单易用

### 4. 分析脚本
- **`analyze_reward_experiments.py`** - 结果分析和可视化
  - `ExperimentAnalyzer` 类
  - 生成对比报告
  - 绘制权重对比图
  - 绘制雷达图
  - 创建实验摘要

## 📊 实验配置

### 8 组实验

| 文件中的名称 | 描述 | 重点目标 |
|-------------|------|----------|
| `baseline` | 当前默认配置 | 平衡 |
| `high_velocity` | 高速度跟踪权重 | (i) 速度跟踪 |
| `high_stability` | 高稳定性权重 | (ii) 直立姿态 |
| `high_smoothness` | 高平滑度惩罚 | (iii) 平滑运动 |
| `high_clearance` | 高离地高度权重 | (iv) 足部离地 |
| `balanced` | 平衡所有目标 | (i)+(ii)+(iii)+(iv) |
| `aggressive` | 激进高速 | (i) 速度 |
| `conservative` | 保守稳定 | (ii)+(iii) 稳定性 |

## 🚀 快速开始

### 最简单的方式
```bash
# 1. 查看配置
python reward_experiments_config.py

# 2. 运行一个实验
python run_reward_experiments.py --experiment baseline --iterations 1000

# 3. 分析结果
python analyze_reward_experiments.py
```

### 运行所有实验
```bash
# 方式 1: Python
python run_reward_experiments.py --all --iterations 1000

# 方式 2: Bash
bash run_all_experiments.sh
```

### 查看训练曲线
```bash
tensorboard --logdir experiments/reward_comparison
```

## 📁 输出文件结构

运行实验后会生成以下文件：

```
experiments/reward_comparison/
├── results.json                          # 实验结果汇总 JSON
├── comparison_report.txt                 # 文本对比报告
├── reward_weights_comparison.png         # 权重对比柱状图
├── radar_chart_comparison.png            # 雷达图
├── EXPERIMENT_SUMMARY.md                 # 自动生成的实验摘要
│
├── baseline_20240512_120000/             # Baseline 实验目录
│   ├── reward_config.json                # 该实验的配置
│   ├── checkpoints/                      # 模型检查点
│   │   ├── model_100.pt
│   │   ├── model_200.pt
│   │   └── ...
│   ├── videos/                           # 训练视频
│   │   ├── video_200.mp4
│   │   ├── video_400.mp4
│   │   └── ...
│   └── tensorboard/                      # TensorBoard 日志
│       └── events.out.tfevents...
│
├── high_velocity_20240512_130000/        # High Velocity 实验
│   └── ...
│
└── ... (其他 6 个实验)
```

## 🎯 四个目标

### (i) Forward Velocity Tracking
**相关奖励**:
- `track_linear_velocity` (weight: 2.0-6.0)
- `track_angular_velocity` (weight: 0.5-4.0)

**评估指标**:
- `Rewards/track_linear_velocity`
- `Rewards/track_angular_velocity`

### (ii) Upright Body Orientation
**相关奖励**:
- `upright` (weight: 0.3-2.0)
- `pose` (weight: 0.3-2.0)

**评估指标**:
- `Rewards/upright`
- `Rewards/pose`

### (iii) Smooth Joint Motions
**相关奖励**:
- `action_rate_l2` (weight: -0.05 to -0.5) - Jerk penalty
- `action_l2` (weight: 0.0 to -0.01) - Torque penalty
- `dof_pos_limits` (weight: -1.0 to -2.0)

**评估指标**:
- `Rewards/action_rate_l2`
- `Metrics/mean_action_acc`

### (iv) Adequate Foot Clearance
**相关奖励**:
- `foot_clearance` (weight: -1.0 to -4.0)
- `foot_swing_height` (weight: -0.1 to -0.5)
- `air_time` (weight: 1.0-3.0)

**评估指标**:
- `Rewards/foot_clearance`
- `Metrics/air_time_mean`
- `Metrics/peak_height_mean`

## 📖 使用流程

### 第一次使用
1. 阅读 `REWARD_EXPERIMENTS_SUMMARY.md` 了解全貌
2. 查看 `reward_experiments_config.py` 了解配置
3. 运行一个测试实验验证环境
4. 阅读 `REWARD_EXPERIMENTS_GUIDE.md` 了解详细操作

### 运行实验
1. 选择要运行的实验（或全部）
2. 使用 `run_reward_experiments.py` 或 `run_all_experiments.sh`
3. 使用 TensorBoard 监控训练
4. 等待实验完成

### 分析结果
1. 运行 `analyze_reward_experiments.py` 生成报告和图表
2. 查看 TensorBoard 曲线对比
3. 观看视频对比运动效果
4. 阅读生成的 `EXPERIMENT_SUMMARY.md`

### 选择最佳配置
1. 根据应用场景选择重点目标
2. 对比相关实验的结果
3. 选择性能最好的配置
4. 可选：基于最佳配置进行微调

## 🔗 相关源代码

### 环境配置
- `src/mjlab/tasks/velocity/velocity_env_cfg.py` - 基础配置
- `src/mjlab/tasks/velocity/config/go2/env_cfgs.py` - Go2 配置

### 奖励函数实现
- `src/mjlab/tasks/velocity/mdp/rewards.py` - 奖励函数实现
- `src/mjlab/tasks/velocity/mdp/__init__.py` - MDP 模块

### 训练脚本
- 使用 `uv run train` 命令
- 配置通过命令行参数传递

## 💡 提示

### 推荐阅读顺序
1. `REWARD_EXPERIMENTS_SUMMARY.md` - 快速了解
2. `REWARD_ANALYSIS.md` - 理解奖励函数
3. `reward_experiments_config.py` - 查看配置
4. `REWARD_EXPERIMENTS_GUIDE.md` - 详细操作

### 推荐实验顺序
1. `baseline` - 了解基线性能
2. `balanced` - 测试平衡配置
3. 根据需求选择其他实验

### 时间规划
- 快速测试: 100 iterations, 512 envs (~10 分钟/实验)
- 标准训练: 1000 iterations, 1024 envs (~1 小时/实验)
- 完整训练: 5000 iterations, 2048 envs (~4 小时/实验)

## 📞 获取帮助

### 查看帮助信息
```bash
# 运行脚本帮助
python run_reward_experiments.py --help

# 分析脚本帮助
python analyze_reward_experiments.py --help

# 查看配置
python reward_experiments_config.py
```

### 常见问题
参见 `REWARD_EXPERIMENTS_GUIDE.md` 的"常见问题"部分

## ✅ 检查清单

### 运行实验前
- [ ] 已阅读 `REWARD_EXPERIMENTS_SUMMARY.md`
- [ ] 已查看 `reward_experiments_config.py` 的配置
- [ ] 已确认训练参数（iterations, num_envs）
- [ ] 已准备足够的磁盘空间（每个实验 ~1-5GB）
- [ ] 已准备足够的时间（参考时间估算）

### 运行实验中
- [ ] 使用 TensorBoard 监控训练
- [ ] 定期检查实验状态
- [ ] 观察是否有异常（如不收敛）

### 运行实验后
- [ ] 运行 `analyze_reward_experiments.py` 生成报告
- [ ] 查看 TensorBoard 曲线对比
- [ ] 观看视频对比
- [ ] 记录关键发现
- [ ] 选择最佳配置

---

**创建时间**: 2026-05-12  
**版本**: 1.0  
**项目**: mjlab - Go2 速度跟踪任务奖励函数对比实验
