# 42D 观测空间配置说明

## ✅ 已完成

成功创建了新的 42D 观测空间配置，去掉了 `base_lin_vel` 和 `base_ang_vel`，与 WTW 项目保持一致。

## 📊 观测空间对比

### 原始配置 (48D)
```
base_lin_vel      : 3D  ❌ 已移除
base_ang_vel      : 3D  ❌ 已移除
projected_gravity : 3D  ✅
joint_pos         : 12D ✅
joint_vel         : 12D ✅
actions           : 12D ✅
command           : 3D  ✅
─────────────────────────
总计              : 48D
```

### 新配置 (42D)
```
projected_gravity : 3D  ✅
joint_pos         : 12D ✅
joint_vel         : 12D ✅
actions           : 12D ✅
command           : 3D  ✅
─────────────────────────
总计              : 42D
```

## 🚀 使用方法

### 1. 训练
```bash
# 使用提供的脚本
./train_42d.sh

# 或手动运行
MUJOCO_GL=egl uv run train Mjlab-Velocity-Flat-Unitree-Go2-42 \
  --env.scene.num-envs 1024 \
  --agent.max-iterations 300 \
  --agent.save-interval 100 \
  --video True \
  --video-interval 200 \
  --video-length 200
```

### 2. 测试/播放
```bash
# 使用提供的脚本
./play_42d.sh logs/Mjlab-Velocity-Flat-Unitree-Go2-42/model_100.pt

# 或手动运行
MUJOCO_GL=egl uv run play Mjlab-Velocity-Flat-Unitree-Go2-42 \
  --checkpoint <checkpoint_path> \
  --num-envs 1 \
  --record-video
```

### 3. 验证配置
```bash
# 验证观测空间维度
uv run python verify_42d_env.py

# 查看配置差异
uv run python test_42d_obs.py
```

## 📁 修改的文件

1. **src/mjlab/tasks/velocity/config/go2/env_cfgs.py**
   - 添加了 `unitree_go2_flat_env_cfg_42d()` 函数
   - 从 actor 和 critic 观测中移除 base_lin_vel 和 base_ang_vel

2. **src/mjlab/tasks/velocity/config/go2/__init__.py**
   - 注册新任务: `Mjlab-Velocity-Flat-Unitree-Go2-42`
   - 导出新配置函数

3. **新增文件**
   - `train_42d.sh`: 训练脚本
   - `play_42d.sh`: 测试脚本
   - `verify_42d_env.py`: 验证脚本
   - `test_42d_obs.py`: 配置对比脚本
   - `docs_42d.md`: 详细文档

## 🔍 验证结果

运行 `verify_42d_env.py` 的输出确认：
```
Actor observation shape: torch.Size([4, 42])
Expected: (4, 42)
Match: True

Observation components:
------------------------------------------------------------
  projected_gravity   : 3D
  joint_pos           : 12D
  joint_vel           : 12D
  actions             : 12D
  command             : 3D
------------------------------------------------------------
  Total               : 42D

✅ 42D configuration verified successfully!
```

## 🎯 与 WTW 项目对比

| 项目     | 观测空间 | base_lin_vel | base_ang_vel | 状态 |
|---------|---------|--------------|--------------|------|
| WTW     | 42D     | ❌ 不包含    | ❌ 不包含    | -    |
| MJLab   | 48D     | ✅ 包含      | ✅ 包含      | 原始 |
| MJLab   | 42D     | ❌ 不包含    | ❌ 不包含    | ✅ 新 |

现在两个项目的观测空间完全一致！

## 💡 技术细节

- 网络会自动适应 42D 输入维度，无需手动修改网络结构
- Critic 观测空间为 66D (42D + 额外的足部信息)
- 所有其他配置（奖励、终止条件等）保持不变
- 支持训练和推理模式

## 📝 任务 ID

- 原始 48D 任务: `Mjlab-Velocity-Flat-Unitree-Go2`
- 新 42D 任务: `Mjlab-Velocity-Flat-Unitree-Go2-42`
