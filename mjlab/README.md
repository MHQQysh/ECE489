# mjlab 实验说明

本文档整理了当前在 `mjlab` 中完成的主要工作、训练/测试命令，以及后续实验记录方式。内容基于原来的 `总结.md`，并补充整理为更适合作为项目说明的 `README.md`。

## 0. 已完成的主要工作

1. 将 Unitree Go2 机器人迁移到项目中，位置在：
   - `src/mjlab/asset_zoo/robots/unitree_go2`

2. 完成了两类地形的训练与测试：
   - Flat 平地
   - Slope 斜坡

3. 编写了带外力推搡测试的脚本：
   - `play_flat_withpush.py`
   - `play_slope_withpush.py`

4. 编写了平地/斜坡对比评估脚本：
   - `eval_slope_vs_flat.py`

5. 编写了跨域泛化评估脚本：
   - `domain_eval_slope_flat.py`

6. 进行了 reward 相关实验探索：
   - `run_reward_experiments.py`
   - `run_all_experiments.sh`
   - `reward_experiments_config.py`


---

## 1. 训练命令

### 1.1 平地训练

```bash
cd /home/y/ece489/lab4/mjlab
export WANDB_MODE=disabled

MUJOCO_GL=egl uv run train Mjlab-Velocity-Flat-Unitree-Go2 \
  --env.scene.num-envs 1024 \
  --agent.max-iterations 300 \
  --agent.save-interval 100 \
  --video True \
  --video-interval 200 \
  --video-length 200
```

### 1.2 斜坡训练

```bash
cd /home/y/ece489/lab4/mjlab
export WANDB_MODE=disabled

MUJOCO_GL=egl uv run train Mjlab-Velocity-Slope-Unitree-Go2 \
  --env.scene.num-envs 512 \
  --agent.max-iterations 300 \
  --agent.save-interval 100 \
  --video True \
  --video-interval 200 \
  --video-length 200
```

### 1.3 斜坡无域随机训练（用于跨域评估）

```bash
cd /home/y/ece489/lab4/mjlab
export WANDB_MODE=disabled

MUJOCO_GL=egl uv run train Mjlab-Velocity-Rough-NoDR-Unitree-Go2 \
  --env.scene.num-envs 512 \
  --agent.max-iterations 1200 \
  --agent.save-interval 200 \
  --video True \
  --video-interval 200 \
  --video-length 200
```

---

## 2. 运行与可视化

### 2.1 平地策略播放

```bash
uv run play Mjlab-Velocity-Flat-Unitree-Go2 \
  --checkpoint_file /home/y/ece489/lab4/mjlab/logs/rsl_rl/go2_velocity/2026-05-12_05-41-56/model_500.pt \
  --num-envs 1 \
  --viewer viser
```

### 2.2 斜坡策略播放

```bash
uv run play Mjlab-Velocity-Slope-Unitree-Go2 \
  --checkpoint-file /home/y/ece489/lab4/mjlab/logs/rsl_rl/go2_velocity/2026-05-12_05-17-00/model_500.pt \
  --num-envs 10 \
  --device cuda:0 \
  --viewer viser
```

### 2.3 无域随机策略播放

```bash
export WANDB_MODE=disabled
MUJOCO_GL=egl uv run play Mjlab-Velocity-Rough-Unitree-Go2 \
  --checkpoint_file logs/rsl_rl/go2_velocity/rough_1200/model_1199.pt \
  --num-envs 10 \
  --viewer viser
```

### 2.4 TensorBoard

```bash
cd /home/y/ece489/lab4/mjlab
uv run tensorboard --logdir logs/rsl_rl/go1_velocity --port 6006
uv run tensorboard --logdir logs/rsl_rl/go2_velocity --port 6006
```

---

## 3. 带推力测试

相关脚本：

- `play_flat_withpush.py`
- `play_slope_withpush.py`

运行方式：

```bash
uv run python play_flat_withpush.py
```

操作说明：

1. 先点击 `enable control`
2. 然后可以自行调节方向和速度
3. 也可以按动 `push` 施加外力

这部分主要用于观察策略在受到扰动后的恢复能力和稳定性。

---

## 4. Reward 实验

相关文件：

- `run_reward_experiments.py`
- `run_all_experiments.sh`
- `reward_experiments_config.py`

### 4.1 实验目标

尝试对比不同 reward 设计对训练效果的影响，总体上可以从以下角度理解：

1. **速度跟踪能力**：是否更准确地跟踪目标线速度和角速度
2. **姿态稳定性**：是否更平稳，是否减少 roll / pitch 波动
3. **能耗表现**：是否用更少的能量完成相同运动
4. **抗扰能力**：受到外部推力后是否更容易恢复
5. **训练收敛速度**：不同 reward 是否导致更快/更慢收敛

### 4.2 可对比的 reward 维度

虽然具体实现以代码里的配置为准，但一般可以从下面几类项进行对照：

- 速度跟踪项：鼓励机器人跟踪目标 `vx` / `vy`
- 姿态惩罚项：约束 `roll` / `pitch` 过大
- 角速度惩罚项：抑制机身剧烈转动
- 足端接触/滑动惩罚：减少打滑和不稳定接触
- 关节动作惩罚：限制过大的动作幅度
- 力矩/功率惩罚：降低能耗
- 生存/倒地相关项：鼓励持续站立和行走
- 平滑项：提升动作连续性，减少抖动

### 4.3 建议记录方式

每组 reward 实验建议记录：

- 最终回报曲线
- 速度跟踪误差
- 姿态波动
- 能耗或 torque 统计
- 失败率或倒地率
- 视频样例

---

## 5. 平地 vs 斜坡评估

相关脚本：

- `eval_slope_vs_flat.py`

运行方式：

```bash
uv run eval_slope_vs_flat.py
```

### 5.1 实验设置

- 测试环境：
  1. 平地，训练约 500 iter
  2. 斜坡，训练约 1000 iter

- 测试速度指令：
  1. `x = 1 m/s`
  2. `y = 1 m/s`
  3. `x = 1 m/s, y = 0.5 m/s`

- 每组实验重复 10 次

### 5.2 指标

1. **速度跟踪误差**：RMS
2. **身体稳定性**：RMS roll / pitch
3. **能量消耗**：Cost of Transport, `CoT = 总能耗 / 位移`
4. **鲁棒性**：施加横向推力（30–50 N，持续 0.1 s）后恢复成功次数

### 5.3 结果表建议格式

最终结果可整理为类似下面的表格：

| Training Command | vx (m/s) | vy (m/s) | Roll (deg) | Pitch (deg) | CoT | Recovery |
|---|---:|---:|---:|---:|---:|---:|
| Flat Forward (500 iter) | 1.0 | 0.0 | ... | ... | ... | ... |
| Flat Lateral (500 iter) | 0.0 | 1.0 | ... | ... | ... | ... |
| Flat Combined (500 iter) | 1.0 | 0.5 | ... | ... | ... | ... |
| Slope Forward (1000 iter) | 1.0 | 0.0 | ... | ... | ... | ... |
| Slope Lateral (1000 iter) | 0.0 | 1.0 | ... | ... | ... | ... |
| Slope Combined (1000 iter) | 1.0 | 0.5 | ... | ... | ... | ... |

---

## 6. 跨域评估

相关脚本：

- `domain_eval_slope_flat.py`

运行流程：

1. 先训练无域随机版本的斜坡策略
2. 再加载 checkpoint 进行播放验证
3. 最后运行跨域评估脚本，比较平地与斜坡表现

```bash
uv run python domain_eval_slope_flat.py
```

### 6.1 目的

该实验主要用于观察：

- 在训练域外，策略是否还能保持基本行走能力
- 平地策略在斜坡上的退化情况
- 斜坡策略在平地上的泛化情况
- 域随机化是否提升鲁棒性和迁移能力

---

## 7. 后续可以继续补充的内容

- 各个脚本的参数说明
- reward 配置的具体公式
- 训练曲线截图
- 视频链接
- 不同 checkpoint 的定量对比结果
- 最终论文/报告中的表格与结论

---

## 8. 备注

如果你希望，这个 `README.md` 后面还可以继续整理成更正式的实验报告格式，例如：

- `Abstract`
- `Method`
- `Experiment Setup`
- `Results`
- `Conclusion`

这样可以直接用于课程报告或实验汇报。
