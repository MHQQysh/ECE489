# 奖励函数对比实验 - 完整总结

## 📋 任务完成情况

### 1. ✅ 奖励函数分析
已完成对当前所有奖励函数的详细分析，包括：

- **速度跟踪** (i): `track_linear_velocity`, `track_angular_velocity`
- **直立姿态** (ii): `upright`, `pose`
- **平滑运动** (iii): `action_rate_l2`, `dof_pos_limits`
- **足部离地** (iv): `foot_clearance`, `foot_swing_height`, `air_time`

详见: `REWARD_ANALYSIS.md`

### 2. ✅ 实验配置设计
设计了 8 组对比实验：

| 实验名称 | 重点目标 | 描述 |
|---------|---------|------|
| baseline | 平衡 | 当前默认配置 |
| high_velocity | (i) | 最大化速度跟踪 |
| high_stability | (ii) | 最大化姿态稳定性 |
| high_smoothness | (iii) | 最小化 jerk 和力矩 |
| high_clearance | (iv) | 最大化足部离地高度 |
| balanced | (i)+(ii)+(iii)+(iv) | 平衡所有目标 |
| aggressive | (i) | 高速高动态 |
| conservative | (ii)+(iii) | 稳定优先 |

详见: `reward_experiments_config.py`

### 3. ✅ 自动化训练脚本
创建了完整的自动化工具链：

- `run_reward_experiments.py`: 运行单个或所有实验
- `run_all_experiments.sh`: Bash 批量运行脚本
- `analyze_reward_experiments.py`: 结果分析和可视化
- `reward_experiments_config.py`: 实验配置定义

## 🚀 快速开始

### 方法 1: 运行单个实验
```bash
python run_reward_experiments.py --experiment baseline --iterations 1000
```

### 方法 2: 运行所有实验（Python）
```bash
python run_reward_experiments.py --all --iterations 1000
```

### 方法 3: 运行所有实验（Bash）
```bash
bash run_all_experiments.sh
```

### 分析结果
```bash
# 生成完整分析
python analyze_reward_experiments.py

# 查看训练曲线
tensorboard --logdir experiments/reward_comparison
```

## 📊 实验配置对比

### 权重对比表

| 实验 | 线速度 | 角速度 | 直立 | 姿态 | Jerk | 动作 | 离地高度 | 摆动高度 | 空中时间 |
|------|--------|--------|------|------|------|------|----------|----------|----------|
| baseline | 3.0 | 2.5 | 0.5 | 0.5 | -0.1 | 0.0 | -2.0 | -0.25 | 2.0 |
| high_velocity | **6.0** | **4.0** | 0.3 | 0.3 | -0.05 | 0.0 | -1.0 | -0.1 | 1.0 |
| high_stability | 2.0 | 1.5 | **2.0** | **2.0** | -0.15 | 0.0 | -1.5 | -0.2 | 1.5 |
| high_smoothness | 2.5 | 2.0 | 0.5 | 0.5 | **-0.5** | **-0.01** | -2.0 | -0.25 | 2.0 |
| high_clearance | 2.5 | 2.0 | 0.5 | 0.5 | -0.1 | 0.0 | **-4.0** | **-0.5** | **3.0** |
| balanced | 3.5 | 2.5 | 1.0 | 1.0 | -0.2 | -0.005 | -2.5 | -0.3 | 2.5 |
| aggressive | 5.0 | 3.5 | 0.3 | 0.3 | -0.05 | 0.0 | -1.5 | -0.15 | 2.5 |
| conservative | 2.0 | 1.5 | 1.5 | 1.5 | -0.3 | -0.01 | -2.5 | -0.3 | 1.5 |

### 四个目标的权重分布

```
(i) Velocity Tracking:
  high_velocity > aggressive > balanced > baseline > high_smoothness > high_clearance > high_stability = conservative

(ii) Upright Orientation:
  high_stability = conservative > balanced > baseline = high_smoothness = high_clearance > high_velocity = aggressive

(iii) Smooth Motions:
  high_smoothness > conservative > balanced > baseline = high_clearance > high_stability > high_velocity = aggressive

(iv) Foot Clearance:
  high_clearance > balanced > conservative > baseline = high_smoothness > high_stability > high_velocity > aggressive
```

## 📈 评估指标

### 主要指标

#### (i) 速度跟踪
- `Rewards/track_linear_velocity` ↑
- `Rewards/track_angular_velocity` ↑
- 速度误差 ↓

#### (ii) 姿态稳定性
- `Rewards/upright` ↑
- `Rewards/pose` ↑
- 姿态抖动 ↓

#### (iii) 运动平滑度
- `Rewards/action_rate_l2` (绝对值) ↓
- `Metrics/mean_action_acc` ↓
- 运动流畅度 ↑

#### (iv) 足部离地高度
- `Rewards/foot_clearance` (绝对值) ↓
- `Metrics/air_time_mean` → 目标范围
- `Metrics/peak_height_mean` → 0.1-0.12m

### 次要指标
- `Rewards/total`: 总奖励
- `Metrics/slip_velocity_mean`: 滑动速度
- `Metrics/landing_force_mean`: 着陆力
- Episode length: 回合长度

## 🎯 预期结果

### high_velocity
- ✅ 最快的速度响应
- ⚠️ 可能牺牲稳定性
- ⚠️ 可能有较大的动作变化

### high_stability
- ✅ 最稳定的姿态
- ⚠️ 速度跟踪可能较慢
- ✅ 运动较平滑

### high_smoothness
- ✅ 最平滑的运动
- ⚠️ 响应速度可能较慢
- ✅ 能耗较低

### high_clearance
- ✅ 最高的足部离地
- ⚠️ 能耗可能较高
- ✅ 适合崎岖地形

### balanced
- ✅ 四个目标的最佳平衡
- ✅ 综合性能最优
- 推荐作为最终配置

## 📁 文件清单

### 配置和脚本
- ✅ `reward_experiments_config.py` - 实验配置定义
- ✅ `run_reward_experiments.py` - Python 运行脚本
- ✅ `run_all_experiments.sh` - Bash 批量运行脚本
- ✅ `analyze_reward_experiments.py` - 结果分析脚本

### 文档
- ✅ `REWARD_ANALYSIS.md` - 奖励函数详细分析
- ✅ `REWARD_EXPERIMENTS_GUIDE.md` - 实验指南
- ✅ `REWARD_EXPERIMENTS_SUMMARY.md` - 本文档

### 输出（运行后生成）
- `experiments/reward_comparison/results.json` - 实验结果
- `experiments/reward_comparison/comparison_report.txt` - 对比报告
- `experiments/reward_comparison/reward_weights_comparison.png` - 权重对比图
- `experiments/reward_comparison/radar_chart_comparison.png` - 雷达图
- `experiments/reward_comparison/EXPERIMENT_SUMMARY.md` - 实验摘要
- `experiments/reward_comparison/*/` - 各实验的训练结果

## 🔧 训练命令示例

### 标准训练（推荐）
```bash
MUJOCO_GL=egl uv run train Mjlab-Velocity-Flat-Unitree-Go2 \
  --env.scene.num-envs 1024 \
  --agent.max-iterations 1000 \
  --agent.save-interval 100 \
  --video True \
  --video-interval 200 \
  --video-length 200 \
  --env.rewards.track_linear_velocity.weight=3.0 \
  --env.rewards.track_angular_velocity.weight=2.5 \
  --env.rewards.upright.weight=0.5 \
  --env.rewards.pose.weight=0.5 \
  --env.rewards.action_rate_l2.weight=-0.1 \
  --env.rewards.foot_clearance.weight=-2.0 \
  --env.rewards.foot_swing_height.weight=-0.25 \
  --env.rewards.air_time.weight=2.0
```

### 完整训练
```bash
MUJOCO_GL=egl uv run train Mjlab-Velocity-Flat-Unitree-Go2 \
  --env.scene.num-envs 2048 \
  --agent.max-iterations 5000 \
  --agent.save-interval 500 \
  --video True \
  --video-interval 500 \
  --video-length 200
```

### 快速测试
```bash
MUJOCO_GL=egl uv run train Mjlab-Velocity-Flat-Unitree-Go2 \
  --env.scene.num-envs 512 \
  --agent.max-iterations 100 \
  --video False
```

## 📊 结果分析流程

### 1. 训练监控
```bash
# 实时监控训练曲线
tensorboard --logdir experiments/reward_comparison

# 在浏览器打开
http://localhost:6006
```

### 2. 生成分析报告
```bash
# 完整分析（报告 + 图表）
python analyze_reward_experiments.py

# 只生成报告
python analyze_reward_experiments.py --report

# 只绘制图表
python analyze_reward_experiments.py --plot

# 绘制雷达图
python analyze_reward_experiments.py --radar
```

### 3. 对比视频
```bash
# 查看所有视频
ls experiments/reward_comparison/*/videos/

# 并排播放对比
vlc experiments/reward_comparison/baseline_*/videos/*.mp4 &
vlc experiments/reward_comparison/high_velocity_*/videos/*.mp4 &
```

### 4. 导出指标
从 TensorBoard 导出 CSV：
1. 打开 TensorBoard
2. 选择要导出的指标
3. 点击右上角的下载按钮
4. 保存为 CSV 文件

## ⏱️ 时间估算

### 单个实验
- 1000 iterations, 1024 envs: **~30-60 分钟**
- 5000 iterations, 2048 envs: **~3-5 小时**

### 所有实验（8 组）
- 1000 iterations: **~4-8 小时**
- 5000 iterations: **~24-40 小时**

**建议**: 使用 `screen` 或 `tmux` 在后台运行

```bash
# 使用 screen
screen -S reward_exp
bash run_all_experiments.sh
# Ctrl+A, D 分离会话

# 重新连接
screen -r reward_exp
```

## 🎓 学习要点

### 奖励函数设计原则
1. **权重平衡**: 不同目标的权重需要平衡
2. **标准差调节**: `std` 参数控制奖励的敏感度
3. **惩罚 vs 奖励**: 负权重是惩罚，正权重是奖励
4. **速度自适应**: 根据速度调整约束（如 `variable_posture`）

### 实验设计原则
1. **单变量控制**: 每组实验重点调整一个目标
2. **对比基线**: 始终保留 baseline 作为对比
3. **平衡配置**: 设计一个平衡所有目标的配置
4. **极端测试**: 测试极端配置以了解边界

### 结果分析原则
1. **多指标评估**: 不只看总奖励，要看各个子奖励
2. **视频验证**: 定量指标 + 定性观察
3. **收敛分析**: 观察训练曲线的收敛速度和稳定性
4. **泛化测试**: 在不同地形上测试

## 🔍 常见问题

### Q: 如何选择最佳配置？
A: 根据应用场景：
- 高速场景 → `high_velocity` 或 `aggressive`
- 精确控制 → `high_stability` 或 `conservative`
- 崎岖地形 → `high_clearance`
- 通用场景 → `balanced`

### Q: 如何微调配置？
A: 基于最佳配置，小幅调整权重（±20%），观察效果。

### Q: 训练不收敛怎么办？
A: 
1. 检查权重是否过大或过小
2. 增加训练时间
3. 调整学习率
4. 检查奖励函数是否冲突

### Q: 如何添加新的奖励项？
A: 
1. 在 `mdp/rewards.py` 中实现奖励函数
2. 在配置中添加奖励项
3. 在实验配置中设置权重

## 📚 参考资料

- 奖励函数详细分析: `REWARD_ANALYSIS.md`
- 实验操作指南: `REWARD_EXPERIMENTS_GUIDE.md`
- 配置代码: `reward_experiments_config.py`
- Go2 环境配置: `src/mjlab/tasks/velocity/config/go2/env_cfgs.py`
- 奖励函数实现: `src/mjlab/tasks/velocity/mdp/rewards.py`

## ✅ 下一步行动

1. **运行实验**: 选择要运行的实验组
   ```bash
   python run_reward_experiments.py --experiment baseline --iterations 1000
   ```

2. **监控训练**: 使用 TensorBoard 实时监控
   ```bash
   tensorboard --logdir experiments/reward_comparison
   ```

3. **分析结果**: 运行分析脚本
   ```bash
   python analyze_reward_experiments.py
   ```

4. **对比视频**: 观察运动效果

5. **选择最佳**: 根据目标选择最佳配置

6. **微调优化**: 基于最佳配置进行微调

---

**创建时间**: 2026-05-12  
**作者**: Claude (Opus 4.7)  
**项目**: mjlab - Go2 速度跟踪任务
