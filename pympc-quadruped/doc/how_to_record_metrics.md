# 如何记录实验的 4 个指标

## 快速开始

### 1. 运行单次实验

```bash
cd /home/y/ece489/lab4/pympc-quadruped

# 平地，0.5 m/s，试验 1
uv run python scripts/experiment_mpc.py --terrain flat --speed 0.5 --trial 1

# 斜坡，1.0 m/s，试验 2
uv run python scripts/experiment_mpc.py --terrain slope --speed 1.0 --trial 2
```

### 2. 查看结果

结果会自动保存在 `experiment_results/` 目录：

```bash
# 查看所有结果汇总
cat experiment_results/all_results.csv

# 查看单次实验详细结果
cat experiment_results/MPC_flat_speed0.5_trial1.json
```

---

## 4 个指标详解

### 指标 1: 速度跟踪误差 (Velocity Tracking Error)

**定义：** 实际速度与期望速度的差异

**计算公式：**
```
RMS 误差 = sqrt(mean((v_actual - v_desired)^2))
```

**记录方式：**
```python
# 在每个控制步记录
logger.log_step(robot_data, cmd_vel)

# 自动计算
metrics = logger.compute_metrics()
print(f"RMS 速度误差: {metrics['rms_vel_error']:.4f} m/s")
```

**输出示例：**
```
指标 1: 速度跟踪误差
  RMS 误差:  0.0234 m/s
  平均误差:  0.0189 m/s
  最大误差:  0.0567 m/s
```

**解读：**
- RMS < 0.05 m/s: 优秀
- RMS < 0.10 m/s: 良好
- RMS > 0.15 m/s: 较差

---

### 指标 2: 身体稳定性 (Body Stability)

**定义：** 身体 Roll 和 Pitch 角度的 RMS 值

**计算公式：**
```
RMS Roll = sqrt(mean(roll^2))
RMS Pitch = sqrt(mean(pitch^2))
```

**记录方式：**
```python
# 自动从四元数提取 Roll/Pitch
logger.log_step(robot_data, cmd_vel)

# 自动计算
metrics = logger.compute_metrics()
print(f"RMS Roll: {np.rad2deg(metrics['rms_roll']):.2f}°")
print(f"RMS Pitch: {np.rad2deg(metrics['rms_pitch']):.2f}°")
```

**输出示例：**
```
指标 2: 身体稳定性
  RMS Roll:  2.34°
  RMS Pitch: 3.12°
  最大 Roll:  5.67°
  最大 Pitch: 7.89°
```

**解读：**
- RMS < 3°: 非常稳定
- RMS < 5°: 稳定
- RMS > 10°: 不稳定

---

### 指标 3: 能量效率 (Cost of Transport, CoT)

**定义：** 单位重量移动单位距离所需的能量

**计算公式：**
```
CoT = Σ|τ_i * q̇_i| * Δt / (m * g * d)
```

其中：
- τ_i: 关节 i 的力矩
- q̇_i: 关节 i 的速度
- Δt: 时间步长
- m: 机器人质量
- g: 重力加速度 (9.81 m/s²)
- d: 行走距离

**记录方式：**
```python
# 自动记录功率和位置
logger.log_step(robot_data, cmd_vel)

# 自动计算
metrics = logger.compute_metrics()
print(f"CoT: {metrics['cot']:.4f}")
print(f"总能量: {metrics['total_energy']:.2f} J")
print(f"行走距离: {metrics['distance']:.2f} m")
```

**输出示例：**
```
指标 3: 能量效率
  CoT:       0.8234
  总能量:    456.78 J
  行走距离:  5.67 m
```

**解读：**
- CoT < 0.5: 非常高效
- CoT < 1.0: 高效
- CoT < 2.0: 一般
- CoT > 2.0: 低效

**参考值：**
- 人类行走: CoT ≈ 0.2
- 四足机器人: CoT ≈ 0.5-1.5

---

### 指标 4: 鲁棒性 (Robustness)

**定义：** 受到外部推力后能否恢复

**测试方法：**
1. 在 t=5s 时施加 40N 侧向推力
2. 持续 0.1 秒
3. 观察机器人是否恢复

**记录方式：**
```python
# 施加推力
if step == push_step:
    apply_push_force(data, trunk_body_id, 40.0, direction='y')
    logger.mark_push_applied(current_time)

# 检查恢复
recovery_status = logger.check_recovery(current_time)
```

**输出示例：**
```
指标 4: 鲁棒性
  恢复成功:     ✅ 是
  恢复时间:     1.23 s
  最大高度下降: 0.0234 m
```

**判断标准：**
- 恢复成功: 身体高度 > 0.15 m，且高度稳定
- 恢复失败: 身体高度 < 0.15 m (摔倒)

**解读：**
- 恢复时间 < 1s: 优秀
- 恢复时间 < 2s: 良好
- 恢复时间 > 3s: 较差
- 未恢复: 失败

---

## 完整实验流程

### 步骤 1: 运行实验

```bash
# 实验矩阵: 2 地形 × 2 速度 × 10 试验 = 40 次

# 平地实验
for trial in {1..10}; do
    uv run python scripts/experiment_mpc.py --terrain flat --speed 0.5 --trial $trial
    uv run python scripts/experiment_mpc.py --terrain flat --speed 1.0 --trial $trial
done

# 斜坡实验
for trial in {1..10}; do
    uv run python scripts/experiment_mpc.py --terrain slope --speed 0.5 --trial $trial
    uv run python scripts/experiment_mpc.py --terrain slope --speed 1.0 --trial $trial
done
```

### 步骤 2: 查看结果

```bash
# 查看 CSV 汇总
cat experiment_results/all_results.csv

# 或用 Python 分析
python << 'EOF'
import pandas as pd
df = pd.read_csv('experiment_results/all_results.csv')

# 按地形和速度分组
grouped = df.groupby(['terrain', 'speed'])

# 计算平均值和标准差
print(grouped[['rms_vel_error', 'rms_roll', 'rms_pitch', 'cot']].agg(['mean', 'std']))

# 计算恢复成功率
print(grouped['recovery_success'].mean())
EOF
```

### 步骤 3: 生成报告

结果会包含：

1. **速度跟踪误差**
   - RMS, 平均, 最大

2. **身体稳定性**
   - RMS Roll/Pitch
   - 最大 Roll/Pitch

3. **能量效率**
   - CoT
   - 总能量
   - 行走距离

4. **鲁棒性**
   - 恢复成功率
   - 恢复时间
   - 高度下降

---

## 命令行参数

```bash
python scripts/experiment_mpc.py \
    --terrain flat \          # 地形: flat 或 slope
    --speed 0.5 \             # 速度 (m/s)
    --trial 1 \               # 试验编号
    --duration 10.0 \         # 持续时间 (s)
    --push-time 5.0 \         # 推力时间 (s)
    --push-force 40.0 \       # 推力大小 (N)
    --no-viewer \             # 不显示可视化
    --output-dir results      # 输出目录
```

---

## 数据文件格式

### JSON 文件 (详细数据)

```json
{
  "method": "MPC",
  "terrain": "flat",
  "speed": 0.5,
  "trial": 1,
  "rms_vel_error": 0.0234,
  "mean_vel_error": 0.0189,
  "max_vel_error": 0.0567,
  "rms_roll": 0.0408,
  "rms_pitch": 0.0545,
  "max_roll": 0.0989,
  "max_pitch": 0.1378,
  "cot": 0.8234,
  "total_energy": 456.78,
  "distance": 5.67,
  "recovery_success": true,
  "recovery_time": 1.23,
  "max_height_drop": 0.0234
}
```

### CSV 文件 (汇总数据)

```csv
method,terrain,speed,trial,rms_vel_error,rms_roll,rms_pitch,cot,recovery_success,...
MPC,flat,0.5,1,0.0234,0.0408,0.0545,0.8234,True,...
MPC,flat,0.5,2,0.0245,0.0412,0.0551,0.8345,True,...
...
```

---

## 常见问题

### Q1: 如何只记录某些指标？

**A:** 修改 `experiment_logger.py` 中的 `log_step()` 方法，注释掉不需要的部分。

### Q2: 如何修改推力参数？

**A:** 使用命令行参数：
```bash
python scripts/experiment_mpc.py --push-force 50.0 --push-time 3.0
```

### Q3: 如何不施加推力？

**A:** 设置推力时间为负数：
```bash
python scripts/experiment_mpc.py --push-time -1
```

### Q4: 如何导出图表？

**A:** 使用 Python 分析脚本（稍后创建）。

---

## 下一步

1. **运行实验**
   ```bash
   uv run python scripts/experiment_mpc.py --terrain flat --speed 0.5 --trial 1
   ```

2. **检查结果**
   ```bash
   cat experiment_results/all_results.csv
   ```

3. **创建 CPG baseline** (下一步)

4. **对比 MPC vs CPG**

需要我创建数据分析和可视化脚本吗？
