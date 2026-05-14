# 快速开始：评估和对比实验

## ✅ 系统已就绪

所有测试通过！评估系统已准备好使用。

## 📋 实验步骤

### 1. 训练 RL 策略（如果还没有）

```bash
# 平地训练
uv run train Mjlab-Velocity-Flat-Unitree-Go2

# 复杂地形训练
uv run train Mjlab-Velocity-Rough-Unitree-Go2
```

训练完成后，检查点保存在：`logs/rsl_rl/*/model_XXXX.pt`

### 2. 快速测试单个评估

```bash
# 测试 CPG 基线（无需训练）
uv run python src/mjlab/scripts/evaluate_controller.py \
  --task Mjlab-Velocity-Flat-Unitree-Go2 \
  --controller cpg \
  --target-velocity 1.0 \
  --num-trials 3 \
  --cpg-frequency 2.0

# 测试 RL 策略（需要检查点）
uv run python src/mjlab/scripts/evaluate_controller.py \
  --task Mjlab-Velocity-Flat-Unitree-Go2 \
  --controller rl \
  --checkpoint logs/rsl_rl/YOUR_CHECKPOINT.pt \
  --target-velocity 1.0 \
  --num-trials 3
```

### 3. 完整评估（推荐）

#### 步骤 A: 编辑自动化脚本

```bash
vim scripts/run_evaluation.sh
```

更新检查点路径：
```bash
CHECKPOINT="logs/rsl_rl/YOUR_ACTUAL_CHECKPOINT.pt"
```

#### 步骤 B: 运行完整评估

```bash
cd /home/y/ece489/lab4/mjlab
./scripts/run_evaluation.sh
```

这将：
- 在平地和复杂地形上测试
- 测试两个速度（1.0 m/s 和 1.5 m/s）
- 每个条件运行 10 次试验
- 自动生成对比报告

### 4. 查看结果

```bash
# 查看报告
cat evaluation_results/flat_v1.0/comparison_report.md

# 查看图表
xdg-open evaluation_results/flat_v1.0/comparison_plots.png
xdg-open evaluation_results/flat_v1.0/recovery_comparison.png
```

## 📊 评估指标

系统会自动测量：

1. **速度跟踪误差** - 实际速度与目标速度的 RMS 误差
2. **身体稳定性** - Roll 和 Pitch 的 RMS 值
3. **能量效率** - Cost of Transport (CoT)
4. **鲁棒性** - 40N 侧向推力恢复成功率

## 🎯 预期结果

典型的 RL 策略应该：
- ✅ 速度跟踪误差 < 0.1 m/s
- ✅ Roll/Pitch RMS < 5°
- ✅ CoT < 0.5
- ✅ 推力恢复率 > 80%

CPG 基线通常：
- ⚠️ 速度跟踪误差 > 0.15 m/s
- ⚠️ 稳定性较差
- ⚠️ 推力恢复率 < 50%

## 🔧 调试技巧

### 如果 CPG 不稳定

```bash
# 降低频率
--cpg-frequency 1.5

# 或尝试不同步态
--cpg-gait walk
```

### 如果 RL 策略失败

```bash
# 检查检查点路径
ls -lh logs/rsl_rl/*/model_*.pt

# 确认任务名称
uv run python -c "from mjlab.tasks.registry import list_tasks; print([t for t in list_tasks() if 'Go2' in t])"
```

### 查看详细日志

```bash
# 单次评估，查看详细输出
uv run python src/mjlab/scripts/evaluate_controller.py \
  --task Mjlab-Velocity-Flat-Unitree-Go2 \
  --controller cpg \
  --num-trials 1 \
  --episode-length 500
```

## 📝 论文写作

### 实验设置示例

```
We evaluated our RL policy against a CPG baseline on flat and rough terrain
at commanded velocities of 1.0 m/s and 1.5 m/s. Each condition was tested
for 10 trials. We measured velocity tracking error (RMS), body stability
(RMS roll and pitch), energy efficiency (Cost of Transport), and robustness
(40N lateral push recovery rate).
```

### 结果表格示例

```
| Metric              | RL Policy | CPG Baseline | Improvement |
|---------------------|-----------|--------------|-------------|
| Vel. Error (m/s)    | 0.052     | 0.125        | 58%         |
| Roll RMS (deg)      | 1.34      | 3.45         | 61%         |
| Pitch RMS (deg)     | 1.79      | 4.12         | 57%         |
| CoT                 | 0.32      | 0.58         | 45%         |
| Recovery Rate (%)   | 90        | 40           | +50pp       |
```

## 📚 文档

- **详细指南**: `EVALUATION_GUIDE.md`
- **实现总结**: `EVALUATION_IMPLEMENTATION_SUMMARY.md`
- **域随机化**: `DOMAIN_RANDOMIZATION_SUMMARY.md`

## 🆘 需要帮助？

1. 运行测试：`uv run python src/mjlab/scripts/test_evaluation_system.py`
2. 查看帮助：`uv run python src/mjlab/scripts/evaluate_controller.py --help`
3. 检查文档：`cat EVALUATION_GUIDE.md`

---

**祝实验顺利！** 🚀

如果遇到问题，请检查：
- 检查点路径是否正确
- 任务名称是否匹配
- CUDA 是否可用
- 依赖是否安装完整
