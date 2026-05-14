# 修复说明

## 问题
运行 `bash run_all_experiments.sh` 时失败，错误信息：
```
Unrecognized options: --logdir=experiments/reward_comparison/baseline_20260512_093835
```

## 原因
使用了错误的参数名 `--logdir`，正确的参数名应该是 `--log-root`。

## 修复
已修复 `run_reward_experiments.py` 第 103 行：
```python
# 修复前
f"--logdir={exp_dir}",

# 修复后
f"--log-root={exp_dir}",
```

## 验证
已测试通过，训练可以正常启动。

## 现在可以使用

### 方法 1: 运行单个实验
```bash
python run_reward_experiments.py --experiment baseline --iterations 1000
```

### 方法 2: 运行所有实验
```bash
bash run_all_experiments.sh
```

### 方法 3: Python 批量运行
```bash
python run_reward_experiments.py --all --iterations 1000
```

## 快速测试（推荐先测试）
```bash
# 快速测试（10 iterations, 2 envs, 无视频）
python run_reward_experiments.py \
  --experiment baseline \
  --iterations 10 \
  --num-envs 2 \
  --video False
```

如果测试成功，再运行完整实验：
```bash
# 完整实验（1000 iterations, 1024 envs）
python run_reward_experiments.py --experiment baseline --iterations 1000
```

---

**状态**: ✅ 已修复，可以正常使用
