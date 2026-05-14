"""
奖励函数对比实验设计

针对四个目标设计不同的奖励权重配置，对比训练效果：
(i) Forward velocity tracking
(ii) Upright body orientation
(iii) Smooth joint motions (penalize jerk and torque)
(iv) Adequate foot clearance during swing

实验组设计：
1. Baseline: 当前配置
2. High Velocity Focus: 提高速度跟踪权重
3. High Stability Focus: 提高直立和姿态权重
4. High Smoothness Focus: 提高平滑度惩罚
5. High Clearance Focus: 提高足部离地高度权重
6. Balanced: 平衡所有四个目标
"""

import math
from dataclasses import dataclass
from typing import Dict


@dataclass
class RewardWeights:
  """奖励权重配置"""

  # (i) Velocity tracking
  track_linear_velocity: float = 3.0
  track_linear_velocity_std: float = math.sqrt(0.25)
  track_angular_velocity: float = 2.5
  track_angular_velocity_std: float = math.sqrt(0.5)

  # (ii) Upright orientation
  upright: float = 0.5
  upright_std: float = math.sqrt(0.2)
  pose: float = 0.5

  # (iii) Smooth motions
  action_rate_l2: float = -0.1  # Jerk penalty
  dof_pos_limits: float = -1.0

  # (iv) Foot clearance
  foot_clearance: float = -2.0
  foot_clearance_target: float = 0.1
  foot_swing_height: float = -0.25
  air_time: float = 2.0

  # Other
  foot_slip: float = -0.1
  soft_landing: float = -1e-5
  self_collisions: float = -0.1
  shank_collision: float = -0.1
  trunk_head_collision: float = -0.1

  def to_dict(self) -> Dict[str, float]:
    """转换为字典格式"""
    return {
      "track_linear_velocity": self.track_linear_velocity,
      "track_linear_velocity_std": self.track_linear_velocity_std,
      "track_angular_velocity": self.track_angular_velocity,
      "track_angular_velocity_std": self.track_angular_velocity_std,
      "upright": self.upright,
      "upright_std": self.upright_std,
      "pose": self.pose,
      "action_rate_l2": self.action_rate_l2,
      "dof_pos_limits": self.dof_pos_limits,
      "foot_clearance": self.foot_clearance,
      "foot_clearance_target": self.foot_clearance_target,
      "foot_swing_height": self.foot_swing_height,
      "air_time": self.air_time,
      "foot_slip": self.foot_slip,
      "soft_landing": self.soft_landing,
      "self_collisions": self.self_collisions,
      "shank_collision": self.shank_collision,
      "trunk_head_collision": self.trunk_head_collision,
    }


# ============================================================================
# 实验组配置
# ============================================================================

# Experiment 1: Baseline (当前配置)
BASELINE = RewardWeights(
  track_linear_velocity=3.0,
  track_angular_velocity=2.5,
  upright=0.5,
  pose=0.5,
  action_rate_l2=-0.1,
  foot_clearance=-2.0,
  foot_swing_height=-0.25,
  air_time=2.0,
)

# Experiment 2: High Velocity Focus
# 目标：最大化速度跟踪性能
HIGH_VELOCITY = RewardWeights(
  track_linear_velocity=6.0,  # ↑ 2x
  track_linear_velocity_std=math.sqrt(0.15),  # ↓ 更严格
  track_angular_velocity=4.0,  # ↑ 1.6x
  track_angular_velocity_std=math.sqrt(0.3),  # ↓ 更严格
  upright=0.3,  # ↓ 降低
  pose=0.3,  # ↓ 降低
  action_rate_l2=-0.05,  # ↓ 允许更激进的动作
  foot_clearance=-1.0,  # ↓ 降低
  foot_swing_height=-0.1,  # ↓ 降低
  air_time=1.0,  # ↓ 降低
)

# Experiment 3: High Stability Focus
# 目标：最大化直立姿态稳定性
HIGH_STABILITY = RewardWeights(
  track_linear_velocity=2.0,  # ↓ 降低
  track_angular_velocity=1.5,  # ↓ 降低
  upright=2.0,  # ↑ 4x
  upright_std=math.sqrt(0.1),  # ↓ 更严格
  pose=2.0,  # ↑ 4x
  action_rate_l2=-0.15,  # ↑ 更平滑
  foot_clearance=-1.5,
  foot_swing_height=-0.2,
  air_time=1.5,
)

# Experiment 4: High Smoothness Focus
# 目标：最小化 jerk 和力矩
HIGH_SMOOTHNESS = RewardWeights(
  track_linear_velocity=2.5,
  track_angular_velocity=2.0,
  upright=0.5,
  pose=0.5,
  action_rate_l2=-0.5,  # ↑ 5x jerk penalty
  dof_pos_limits=-2.0,  # ↑ 2x
  foot_clearance=-2.0,
  foot_swing_height=-0.25,
  air_time=2.0,
)

# Experiment 5: High Clearance Focus
# 目标：最大化足部离地高度
HIGH_CLEARANCE = RewardWeights(
  track_linear_velocity=2.5,
  track_angular_velocity=2.0,
  upright=0.5,
  pose=0.5,
  action_rate_l2=-0.1,
  foot_clearance=-4.0,  # ↑ 2x
  foot_clearance_target=0.12,  # ↑ 提高目标高度
  foot_swing_height=-0.5,  # ↑ 2x
  air_time=3.0,  # ↑ 1.5x
)

# Experiment 6: Balanced
# 目标：平衡所有四个目标
BALANCED = RewardWeights(
  track_linear_velocity=3.5,  # 中等偏高
  track_linear_velocity_std=math.sqrt(0.2),
  track_angular_velocity=2.5,
  upright=1.0,  # ↑ 2x
  upright_std=math.sqrt(0.15),
  pose=1.0,  # ↑ 2x
  action_rate_l2=-0.2,  # ↑ 2x
  foot_clearance=-2.5,  # ↑ 1.25x
  foot_clearance_target=0.11,
  foot_swing_height=-0.3,  # ↑ 1.2x
  air_time=2.5,  # ↑ 1.25x
)

# Experiment 7: Aggressive (高速高动态)
AGGRESSIVE = RewardWeights(
  track_linear_velocity=5.0,
  track_linear_velocity_std=math.sqrt(0.2),
  track_angular_velocity=3.5,
  upright=0.3,
  pose=0.3,
  action_rate_l2=-0.05,
  foot_clearance=-1.5,
  foot_swing_height=-0.15,
  air_time=2.5,
)

# Experiment 8: Conservative (稳定优先)
CONSERVATIVE = RewardWeights(
  track_linear_velocity=2.0,
  track_angular_velocity=1.5,
  upright=1.5,
  upright_std=math.sqrt(0.1),
  pose=1.5,
  action_rate_l2=-0.3,
  foot_clearance=-2.5,
  foot_swing_height=-0.3,
  air_time=1.5,
)


# ============================================================================
# 实验配置字典
# ============================================================================

EXPERIMENTS = {
  "baseline": BASELINE,
  "high_velocity": HIGH_VELOCITY,
  "high_stability": HIGH_STABILITY,
  "high_smoothness": HIGH_SMOOTHNESS,
  "high_clearance": HIGH_CLEARANCE,
  "balanced": BALANCED,
  "aggressive": AGGRESSIVE,
  "conservative": CONSERVATIVE,
}


def get_experiment_config(name: str) -> RewardWeights:
  """获取实验配置"""
  if name not in EXPERIMENTS:
    raise ValueError(
      f"Unknown experiment: {name}. Available: {list(EXPERIMENTS.keys())}"
    )
  return EXPERIMENTS[name]


def print_experiment_summary():
  """打印所有实验配置摘要"""
  print("=" * 80)
  print("奖励函数对比实验配置")
  print("=" * 80)

  for name, config in EXPERIMENTS.items():
    print(f"\n{name.upper()}:")
    print(
      f"  (i) Velocity: lin={config.track_linear_velocity:.1f}, ang={config.track_angular_velocity:.1f}"
    )
    print(f"  (ii) Stability: upright={config.upright:.1f}, pose={config.pose:.1f}")
    print(f"  (iii) Smoothness: jerk={config.action_rate_l2:.2f}")
    print(
      f"  (iv) Clearance: clear={config.foot_clearance:.1f}, swing={config.foot_swing_height:.2f}, air={config.air_time:.1f}"
    )


if __name__ == "__main__":
  print_experiment_summary()
