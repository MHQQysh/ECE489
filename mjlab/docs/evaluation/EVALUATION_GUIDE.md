# Controller Evaluation and Comparison Guide

本指南说明如何评估和对比 RL 策略与 CPG 基线控制器。

## 概述

评估系统包含以下组件：

1. **CPG 基线控制器** (`src/mjlab/controllers/cpg_baseline.py`)
   - 开环正弦关节轨迹生成器
   - 支持 trot、walk、pace 步态
   - 可调节频率和幅度

2. **评估脚本** (`src/mjlab/scripts/evaluate_controller.py`)
   - 测量速度跟踪误差（RMS）
   - 测量身体稳定性（Roll & Pitch RMS）
   - 计算能量效率（Cost of Transport）
   - 测试鲁棒性（侧向推力恢复）

3. **对比报告生成器** (`src/mjlab/scripts/generate_comparison_report.py`)
   - 生成可视化对比图表
   - 生成 Markdown 格式报告
   - 分析优缺点

4. **自动化脚本** (`scripts/run_evaluation.sh`)
   - 一键运行所有评估
   - 自动生成报告

## 快速开始

### 1. 准备训练好的模型

确保你有训练好的 RL 策略检查点：

```bash
# 训练模型（如果还没有）
uv run train unitree-go2-flat

# 检查点通常保存在：
# logs/rsl_rl/unitree_go2_flat/model_XXXX.pt
```

### 2. 运行单个评估

#### 评估 RL 策略

```bash
uv run python src/mjlab/scripts/evaluate_controller.py \
  --task unitree-go2-flat \
  --controller rl \
  --checkpoint logs/rsl_rl/unitree_go2_flat/model_4000.pt \
  --target-velocity 1.0 \
  --num-trials 10 \
  --output-dir evaluation_results
```

#### 评估 CPG 基线

```bash
uv run python src/mjlab/scripts/evaluate_controller.py \
  --task unitree-go2-flat \
  --controller cpg \
  --target-velocity 1.0 \
  --num-trials 10 \
  --cpg-frequency 2.0 \
  --cpg-gait trot \
  --output-dir evaluation_results
```

### 3. 生成对比报告

```bash
uv run python src/mjlab/scripts/generate_comparison_report.py \
  --rl-result evaluation_results/rl_unitree-go2-flat_v1.0.json \
  --cpg-result evaluation_results/cpg_unitree-go2-flat_v1.0.json \
  --output-dir evaluation_results/comparison \
  --terrain flat \
  --velocities "1.0"
```

### 4. 自动化完整评估

编辑 `scripts/run_evaluation.sh` 中的配置：

```bash
# 更新检查点路径
CHECKPOINT="logs/rsl_rl/unitree_go2_flat/model_4000.pt"

# 设置测试速度
VELOCITIES=(1.0 1.5)

# 设置地形类型
TERRAINS=("flat" "rough")
```

然后运行：

```bash
cd /home/y/ece489/lab4/mjlab
./scripts/run_evaluation.sh
```

## 评估指标详解

### 1. 速度跟踪误差 (Velocity Tracking Error)

**定义**: 实际速度与目标速度之间的 RMS 误差

```
RMS_error = sqrt(mean((v_actual - v_target)^2))
```

**单位**: m/s

**越低越好**: 表示控制器能更准确地跟踪命令速度

### 2. 身体稳定性 (Body Stability)

**定义**: Roll 和 Pitch 角度的 RMS 值

```
Roll_RMS = sqrt(mean(roll^2))
Pitch_RMS = sqrt(mean(pitch^2))
```

**单位**: 弧度（报告中也显示度数）

**越低越好**: 表示机器人身体更稳定，倾斜更小

### 3. 能量效率 (Cost of Transport, CoT)

**定义**: 单位距离的能量消耗

```
CoT = sum(|tau_i * q_dot_i| * dt) / (m * g * d)
```

其中：
- `tau_i`: 关节 i 的力矩
- `q_dot_i`: 关节 i 的速度
- `m`: 机器人质量
- `g`: 重力加速度 (9.81 m/s²)
- `d`: 行走距离

**单位**: 无量纲

**越低越好**: 表示更节能的步态

### 4. 鲁棒性 (Robustness)

**测试方法**: 在运动过程中施加侧向推力

- **推力大小**: 30-50 N
- **持续时间**: 0.1 秒
- **施加时间**: episode 开始后 5 秒

**指标**: 恢复成功率（未摔倒的比例）

**越高越好**: 表示更好的抗干扰能力

## 参数调优

### CPG 控制器参数

#### 频率 (Frequency)

```bash
--cpg-frequency 2.0  # Hz
```

- **低频 (1.0-1.5 Hz)**: 慢速行走，更稳定但速度慢
- **中频 (2.0-2.5 Hz)**: 正常 trot，平衡速度和稳定性
- **高频 (3.0+ Hz)**: 快速运动，但可能不稳定

#### 步态 (Gait)

```bash
--cpg-gait trot  # 或 walk, pace
```

- **trot**: 对角腿同步，适合中速
- **walk**: 顺序步态，最稳定但最慢
- **pace**: 同侧腿同步，不太自然但有趣

#### 幅度调整

在 `cpg_baseline.py` 中修改：

```python
amplitude_hip=0.3,    # 髋关节幅度
amplitude_thigh=0.6,  # 大腿关节幅度
amplitude_calf=0.8,   # 小腿关节幅度
```

**调优建议**:
1. 先在平地上调整频率，找到稳定的速度
2. 调整幅度以改善步态质量
3. 在复杂地形上测试鲁棒性

### 推力测试参数

```bash
--push-force 40.0      # 推力大小 (N)
--push-duration 0.1    # 持续时间 (s)
--push-time 5.0        # 施加时间 (s)
```

**调优建议**:
- Go2 机器人 (~15kg): 30-50 N 是合理范围
- 更大的机器人需要更大的推力
- 可以测试不同时间点的推力

## 输出文件结构

```
evaluation_results/
├── rl_unitree-go2-flat_v1.0.json          # RL 评估原始数据
├── cpg_unitree-go2-flat_v1.0.json         # CPG 评估原始数据
├── flat_v1.0/
│   ├── comparison_report.md               # 对比报告
│   ├── comparison_plots.png               # 指标对比图
│   └── recovery_comparison.png            # 恢复率对比图
├── flat_v1.5/
│   └── ...
└── rough_v1.0/
    └── ...
```

## 结果解读

### 示例报告片段

```markdown
### Velocity Tracking Error (RMS)

| Controller | Mean (m/s) | Std Dev | Improvement |
|-----------|-----------|---------|-------------|
| **RL Policy** | 0.0523 | 0.0089 | - |
| **CPG Baseline** | 0.1247 | 0.0234 | 58.1% |

**Winner**: ✅ RL Policy
```

**解读**:
- RL 策略的速度跟踪误差比 CPG 低 58.1%
- RL 的标准差也更小，说明更稳定
- RL 在速度跟踪方面明显优于 CPG

### 典型结果模式

#### RL 策略通常优势：
- ✅ 速度跟踪更准确
- ✅ 身体更稳定
- ✅ 抗干扰能力更强
- ✅ 能适应不同地形

#### CPG 基线通常优势：
- ✅ 实现简单，无需训练
- ✅ 计算开销小
- ✅ 行为可预测
- ✅ 易于调试

## 常见问题

### Q1: CPG 控制器不稳定，机器人摔倒

**解决方案**:
1. 降低频率：`--cpg-frequency 1.5`
2. 减小幅度：修改 `cpg_baseline.py` 中的 amplitude 参数
3. 调整偏移量：确保初始姿态合理

### Q2: RL 策略评估时出错

**检查**:
1. 检查点路径是否正确
2. 任务名称是否匹配训练时的任务
3. 设备是否可用（CUDA）

### Q3: CoT 计算结果异常

**可能原因**:
1. 力矩估计不准确（CPG 使用简化估计）
2. 距离太短导致除零
3. 机器人质量设置不正确

**解决方案**:
- 增加 episode 长度
- 检查 `evaluate_controller.py` 中的 `robot_mass` 设置

### Q4: 推力测试全部失败

**调整**:
1. 减小推力：`--push-force 30.0`
2. 延后推力时间：`--push-time 10.0`
3. 检查控制器是否正常工作

## 扩展实验

### 1. 多速度测试

```bash
for vel in 0.5 1.0 1.5 2.0; do
  uv run python src/mjlab/scripts/evaluate_controller.py \
    --task unitree-go2-flat \
    --controller rl \
    --checkpoint YOUR_CHECKPOINT.pt \
    --target-velocity $vel \
    --num-trials 10
done
```

### 2. 不同地形测试

```bash
for terrain in flat rough slope stairs; do
  uv run python src/mjlab/scripts/evaluate_controller.py \
    --task unitree-go2-$terrain \
    --controller rl \
    --checkpoint YOUR_CHECKPOINT.pt \
    --target-velocity 1.0 \
    --num-trials 10
done
```

### 3. CPG 参数扫描

```bash
for freq in 1.5 2.0 2.5 3.0; do
  uv run python src/mjlab/scripts/evaluate_controller.py \
    --task unitree-go2-flat \
    --controller cpg \
    --cpg-frequency $freq \
    --target-velocity 1.0 \
    --num-trials 10 \
    --output-dir evaluation_results/cpg_freq_sweep
done
```

## 论文写作建议

### 实验设置部分

```markdown
We evaluated our RL policy against a CPG baseline on both flat and rough
terrain at two commanded speeds (1.0 m/s and 1.5 m/s). Each condition was
tested for 10 trials. We measured:

1. Velocity tracking error (RMS)
2. Body stability (RMS roll and pitch)
3. Energy efficiency (Cost of Transport)
4. Robustness (40N lateral push recovery rate)
```

### 结果部分

```markdown
Table 1 shows the comparison results. The RL policy achieved 58% lower
velocity tracking error (0.052 vs 0.125 m/s) and 45% better energy
efficiency (CoT: 0.32 vs 0.58) compared to the CPG baseline. The RL
policy also demonstrated superior robustness with 90% push recovery rate
versus 40% for the CPG baseline.
```

### 讨论部分

```markdown
The RL policy's superior performance can be attributed to:
1. Closed-loop feedback control vs open-loop CPG
2. Learned terrain adaptation through domain randomization
3. Explicit reward shaping for stability and efficiency

However, the CPG baseline offers advantages in simplicity and
predictability, making it suitable for initial prototyping.
```

## 参考资料

- **CPG 理论**: Ijspeert, A. J. (2008). Central pattern generators for locomotion control in animals and robots.
- **Cost of Transport**: Tucker, V. A. (1970). Energetic cost of locomotion in animals.
- **RL for Locomotion**: Hwangbo et al. (2019). Learning agile and dynamic motor skills for legged robots.

## 联系与支持

如有问题，请查看：
- 代码注释
- 错误日志
- GitHub Issues

---

**祝评估顺利！** 🚀
