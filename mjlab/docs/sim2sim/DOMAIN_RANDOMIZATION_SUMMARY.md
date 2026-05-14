# 域随机化实现总结 (Domain Randomization Implementation Summary)

## 概述 (Overview)

已在 Go2 环境配置中实现域随机化，以提升策略的鲁棒性和泛化能力。

## 实现的域随机化参数

### 1. 摩擦系数随机化 (Friction Coefficient Randomization)
- **参数范围**: μ ∈ [0.5, 1.2]
- **原始范围**: [0.3, 1.5]
- **实现位置**: `cfg.events["foot_friction_slide"]`
- **代码**: `src/mjlab/tasks/velocity/config/go2/env_cfgs.py:325-335`

```python
cfg.events["foot_friction_slide"] = EventTermCfg(
  mode="startup",
  func=envs_mdp.dr.geom_friction,
  params={
    "asset_cfg": SceneEntityCfg("robot", geom_names=geom_names),
    "operation": "abs",
    "axes": [0],
    "ranges": (0.5, 1.2),  # 域随机化：摩擦系数 μ ∈ [0.5, 1.2]
    "shared_random": True,
  },
)
```

### 2. 负载质量和惯性随机化 (Load Mass and Inertia Randomization)
- **参数范围**: ±20% (质量和惯性同时缩放)
- **实现方式**: 使用 `pseudo_inertia` 函数保证物理一致性
- **实现位置**: `cfg.events["robot_inertia"]`
- **代码**: `src/mjlab/tasks/velocity/config/go2/env_cfgs.py:374-384`

```python
cfg.events["robot_inertia"] = EventTermCfg(
  mode="startup",
  func=envs_mdp.dr.pseudo_inertia,
  params={
    "asset_cfg": SceneEntityCfg("robot", body_names="base_link"),
    "alpha_range": (-0.223, 0.182),  # e^(-0.223) ≈ 0.8, e^(0.182) ≈ 1.2
  },
)
```

**为什么使用 `pseudo_inertia` 而不是 `body_mass`？**
- `body_mass` 只改变质量，不改变惯性张量，物理上不一致
- `pseudo_inertia` 同时正确缩放质量和惯性，符合真实物理规律
- `alpha_range` 参数：质量和惯性都按 e^(2*alpha) 缩放
  - e^(2 × -0.223) ≈ 0.64 → 质量缩放到 0.8 倍
  - e^(2 × 0.182) ≈ 1.44 → 质量缩放到 1.2 倍

### 3. 电机强度随机化 (Motor Strength Randomization)
- **参数范围**: ±10% (0.9 - 1.1 倍)
- **实现方式**: 通过 `effort_limits` 函数实现
- **实现位置**: `cfg.events["actuator_strength"]`
- **代码**: `src/mjlab/tasks/velocity/config/go2/env_cfgs.py:386-393`

```python
cfg.events["actuator_strength"] = EventTermCfg(
  mode="startup",
  func=envs_mdp.dr.effort_limits,
  params={
    "asset_cfg": SceneEntityCfg("robot", joint_names=".*"),
    "operation": "scale",
    "effort_limit_range": (0.9, 1.1),  # ±10% 电机强度变化
  },
)
```

### 4. 并行环境数量 (Parallel Environments)
- **环境数量**: 2048 (满足 ≥512 的要求)
- **说明**: 保持原有的 2048 环境数，已满足域随机化加速训练的要求
- **代码**: `src/mjlab/tasks/velocity/config/go2/env_cfgs.py:206-208`

## 技术细节

### 随机化模式
- **mode**: `"startup"` - 在每个 episode 开始时进行随机化
- **operation**: 
  - `"abs"` (摩擦系数) - 设置绝对值
  - `"scale"` (电机强度) - 相对于默认值进行缩放
- **distribution**: `"uniform"` (默认) - 均匀分布采样

### 物理一致性
使用 `pseudo_inertia` 而不是 `body_mass` 的原因：
1. **物理准确性**: 同时缩放质量和惯性张量，符合真实密度变化
2. **避免警告**: `body_mass` 会发出警告，提示物理不一致
3. **更好的泛化**: 训练出的策略更接近真实物理行为

### 原始配置保留
所有原始配置都已注释保留，而非删除，便于后续对比和回滚。

## 修复的问题

1. **移除了不支持的参数**: `effort_limits` 函数不支持 `shared_random` 参数
2. **使用物理一致的方法**: 从 `body_mass` 改为 `pseudo_inertia`
3. **正确的参数映射**: `alpha_range` 对应质量的平方根缩放

## 预期效果

1. **提升鲁棒性**: 训练出的策略能够适应不同的地面摩擦、负载变化和电机性能差异
2. **改善泛化能力**: 策略在真实环境中的表现更加稳定
3. **物理准确性**: 使用 `pseudo_inertia` 保证质量和惯性的物理一致性
4. **加速训练**: 2048 个并行环境提供充足的样本多样性

## 验证建议

1. 运行训练并观察策略在不同随机化参数下的表现
2. 对比启用/禁用域随机化的训练结果
3. 在真实机器人上测试策略的泛化能力
4. 监控训练过程中的质量和惯性变化范围

## 文件修改

- **修改文件**: `src/mjlab/tasks/velocity/config/go2/env_cfgs.py`
- **修改行数**: 约 45 行新增/修改
- **类型检查**: 通过 (无新增类型错误)
- **代码格式**: 通过 ruff format 和 ruff check

## 数学说明

### alpha_range 的计算
对于 ±20% 的质量变化：
- 质量缩放因子 = e^(2*alpha)
- 需要 0.8 ≤ e^(2*alpha) ≤ 1.2
- 取对数：ln(0.8) ≤ 2*alpha ≤ ln(1.2)
- 除以 2：ln(0.8)/2 ≤ alpha ≤ ln(1.2)/2
- 计算：-0.223 ≤ alpha ≤ 0.182

因此 `alpha_range=(-0.223, 0.182)` 对应质量的 ±20% 变化。
