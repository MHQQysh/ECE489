"""Unitree Go2 velocity environment configurations."""

import math
from copy import deepcopy
from typing import Literal

from mjlab.asset_zoo.robots import (
  GO2_ACTION_SCALE,
  get_go2_robot_cfg,
)
from mjlab.envs import ManagerBasedRlEnvCfg
from mjlab.envs import mdp as envs_mdp
from mjlab.envs.mdp.actions import JointPositionActionCfg
from mjlab.managers import TerminationTermCfg
from mjlab.managers.event_manager import EventTermCfg
from mjlab.managers.reward_manager import RewardTermCfg
from mjlab.managers.scene_entity_config import SceneEntityCfg
from mjlab.sensor import (
  ContactMatch,
  ContactSensorCfg,
  ObjRef,
  RayCastSensorCfg,
  RingPatternCfg,
  TerrainHeightSensorCfg,
)
from mjlab.tasks.velocity import mdp
from mjlab.tasks.velocity.mdp import UniformVelocityCommandCfg
from mjlab.tasks.velocity.velocity_env_cfg import make_velocity_env_cfg
from mjlab.terrains.config import (
  ROUGH_TERRAINS_CFG,
  discrete_obstacles,
  flat,
  hf_pyramid_slope,
  hf_pyramid_slope_inv,
  pyramid_stairs,
  pyramid_stairs_inv,
  random_rough,
)
from mjlab.terrains.terrain_generator import TerrainGeneratorCfg

Go2TerrainType = Literal["flat", "rough", "slope", "stairs", "bumps", "random"]
GO2_TERRAIN_CHOICES: tuple[str, ...] = (
  "flat",
  "rough",
  "slope",
  "stairs",
  "bumps",
  "random",
)


def make_go2_terrain_generator_cfg(
  terrain: Go2TerrainType,
  play: bool = False,
) -> TerrainGeneratorCfg:
  """Create a procedural terrain generator for Go2 terrain variants."""
  if terrain == "flat":
    raise ValueError("Flat terrain uses a plane and has no terrain generator.")

  if terrain == "rough":
    cfg = deepcopy(ROUGH_TERRAINS_CFG)
  else:
    common_kwargs = dict(
      size=(8.0, 8.0),
      border_width=20.0,
      num_rows=10,
      curriculum=True,
      add_lights=True,
    )
    if terrain == "slope":
      cfg = TerrainGeneratorCfg(
        **common_kwargs,
        num_cols=3,
        sub_terrains={
          "flat": flat(proportion=0.15),
          "slope_up": hf_pyramid_slope(
            proportion=0.45,
            slope_range=(0.05, 0.55),
            platform_width=2.0,
            border_width=0.5,
          ),
          "slope_down": hf_pyramid_slope_inv(
            proportion=0.40,
            slope_range=(0.05, 0.55),
            platform_width=2.0,
            border_width=0.5,
          ),
        },
      )
    elif terrain == "stairs":
      cfg = TerrainGeneratorCfg(
        **common_kwargs,
        num_cols=4,
        sub_terrains={
          "flat": flat(proportion=0.15),
          "easy_stairs": pyramid_stairs(
            proportion=0.35,
            step_height_range=(0.02, 0.07),
            step_width=0.45,
            platform_width=2.5,
          ),
          "stairs_up": pyramid_stairs(
            proportion=0.25,
            step_height_range=(0.05, 0.12),
            step_width=0.35,
            platform_width=2.0,
          ),
          "stairs_down": pyramid_stairs_inv(
            proportion=0.25,
            step_height_range=(0.05, 0.12),
            step_width=0.35,
            platform_width=2.0,
          ),
        },
      )
    elif terrain == "bumps":
      cfg = TerrainGeneratorCfg(
        **common_kwargs,
        num_cols=3,
        sub_terrains={
          "flat": flat(proportion=0.15),
          "low_bumps": discrete_obstacles(
            proportion=0.45,
            obstacle_height_mode="fixed",
            obstacle_width_range=(0.15, 0.45),
            obstacle_height_range=(0.03, 0.10),
            num_obstacles=70,
            platform_width=1.5,
            border_width=0.5,
            origin_z_offset=0.03,
          ),
          "tall_bumps": discrete_obstacles(
            proportion=0.40,
            obstacle_height_mode="fixed",
            obstacle_width_range=(0.20, 0.60),
            obstacle_height_range=(0.05, 0.16),
            num_obstacles=90,
            platform_width=1.5,
            border_width=0.5,
            origin_z_offset=0.05,
          ),
        },
      )
    elif terrain == "random":
      cfg = TerrainGeneratorCfg(
        **common_kwargs,
        num_cols=2,
        sub_terrains={
          "flat": flat(proportion=0.10),
          "random_hfield": random_rough(
            proportion=0.90,
            noise_range=(0.02, 0.12),
            noise_step=0.02,
            downsampled_scale=0.30,
            border_width=0.5,
          ),
        },
      )
    else:
      raise ValueError(f"Unsupported Go2 terrain: {terrain}")

  if play:
    cfg.curriculum = False
    cfg.num_rows = 5
    cfg.num_cols = max(5, len(cfg.sub_terrains))
    cfg.border_width = 10.0

  return cfg


def unitree_go2_terrain_env_cfg(
  terrain: Go2TerrainType,
  play: bool = False,
) -> ManagerBasedRlEnvCfg:
  """Create a Unitree Go2 velocity config for a named terrain variant."""
  if terrain == "flat":
    return unitree_go2_flat_env_cfg(play=play)

  cfg = unitree_go2_rough_env_cfg(play=play)
  if terrain != "rough":
    assert cfg.scene.terrain is not None
    cfg.scene.terrain.terrain_type = "generator"
    cfg.scene.terrain.terrain_generator = make_go2_terrain_generator_cfg(
      terrain,
      play=play,
    )
    cfg.scene.terrain.max_init_terrain_level = 5

  # Reduce num_envs for memory-intensive terrains (slope needs less due to larger obs)
  if terrain in ("slope", "stairs"):
    cfg.scene.num_envs = 512

  return cfg


def unitree_go2_rough_env_cfg(
  play: bool = False,
) -> ManagerBasedRlEnvCfg:
  """Create Unitree Go2 rough terrain velocity configuration."""
  cfg = make_velocity_env_cfg()

  cfg.sim.mujoco.ccd_iterations = 500
  cfg.sim.mujoco.impratio = 10  # 恢复成功版本的配置
  cfg.sim.mujoco.cone = "elliptic"  # 恢复成功版本的配置
  cfg.sim.nconmax = 128
  cfg.sim.contact_sensor_maxmatch = 500

  cfg.scene.entities = {"robot": get_go2_robot_cfg()}

  # 设置默认环境数量（域随机化需要 ≥512 并行环境加速训练）
  # cfg.scene.num_envs = 2048  # 原始值
  cfg.scene.num_envs = 2048  # 保持 2048 以满足 ≥512 的要求

  # Set raycast sensor frame to Go2 base (trunk equivalent).
  for sensor in cfg.scene.sensors or ():
    if sensor.name == "terrain_scan":
      assert isinstance(sensor, RayCastSensorCfg)
      assert isinstance(sensor.frame, ObjRef)
      sensor.frame.name = "base_link"

  foot_names = ("FR", "FL", "RR", "RL")
  site_names = ("FR", "FL", "RR", "RL")
  # unitree_rl_mjlab Go2 XML uses *_foot_collision for foot contact
  geom_names = tuple(f"{name}_foot_collision" for name in foot_names)

  # Wire foot height scan to per-foot sites.
  for sensor in cfg.scene.sensors or ():
    if sensor.name == "foot_height_scan":
      assert isinstance(sensor, TerrainHeightSensorCfg)
      sensor.frame = tuple(
        ObjRef(type="site", name=s, entity="robot") for s in site_names
      )
      sensor.pattern = RingPatternCfg.single_ring(radius=0.04, num_samples=4)

  feet_ground_cfg = ContactSensorCfg(
    name="feet_ground_contact",
    primary=ContactMatch(mode="geom", pattern=geom_names, entity="robot"),
    secondary=ContactMatch(mode="body", pattern="terrain"),
    fields=("found", "force"),
    reduce="netforce",
    num_slots=1,
    track_air_time=True,
  )
  self_collision_cfg = ContactSensorCfg(
    name="self_collision",
    primary=ContactMatch(mode="subtree", pattern="base_link", entity="robot"),
    secondary=ContactMatch(mode="subtree", pattern="base_link", entity="robot"),
    fields=("found", "force"),
    reduce="none",
    num_slots=1,
    history_length=4,
  )
  thigh_geom_names = tuple(f"{leg}_thigh_collision" for leg in foot_names)
  thigh_ground_cfg = ContactSensorCfg(
    name="thigh_ground_touch",
    primary=ContactMatch(
      mode="geom",
      entity="robot",
      pattern=thigh_geom_names,
    ),
    secondary=ContactMatch(mode="body", pattern="terrain"),
    fields=("found", "force"),
    reduce="none",
    num_slots=1,
    history_length=4,
  )
  calf_geom_names = tuple(
    f"{leg}_calf{i}_collision" for leg in foot_names for i in ("1", "2")
  )
  shank_ground_cfg = ContactSensorCfg(
    name="shank_ground_touch",
    primary=ContactMatch(
      mode="geom",
      entity="robot",
      pattern=calf_geom_names,
    ),
    secondary=ContactMatch(mode="body", pattern="terrain"),
    fields=("found", "force"),
    reduce="none",
    num_slots=1,
    history_length=4,
  )
  trunk_head_ground_cfg = ContactSensorCfg(
    name="trunk_ground_touch",
    primary=ContactMatch(
      mode="geom",
      entity="robot",
      pattern=("base1_collision", "base2_collision", "base3_collision"),
    ),
    secondary=ContactMatch(mode="body", pattern="terrain"),
    fields=("found", "force"),
    reduce="none",
    num_slots=1,
    history_length=4,
  )
  cfg.scene.sensors = (cfg.scene.sensors or ()) + (
    feet_ground_cfg,
    self_collision_cfg,
    thigh_ground_cfg,
    shank_ground_cfg,
    trunk_head_ground_cfg,
  )

  if cfg.scene.terrain is not None and cfg.scene.terrain.terrain_generator is not None:
    cfg.scene.terrain.terrain_generator.curriculum = True

  joint_pos_action = cfg.actions["joint_pos"]
  assert isinstance(joint_pos_action, JointPositionActionCfg)
  joint_pos_action.scale = GO2_ACTION_SCALE  # 恢复成功版本的配置

  cfg.viewer.body_name = "base_link"
  cfg.viewer.distance = 1.5
  cfg.viewer.elevation = -10.0

  # Replace the base foot_friction with per-axis friction events for condim 6.
  del cfg.events["foot_friction"]
  # 域随机化：摩擦系数 μ ∈ [0.5, 1.2]
  # cfg.events["foot_friction_slide"] = EventTermCfg(  # 原始配置
  #   mode="startup",
  #   func=envs_mdp.dr.geom_friction,
  #   params={
  #     "asset_cfg": SceneEntityCfg("robot", geom_names=geom_names),
  #     "operation": "abs",
  #     "axes": [0],
  #     "ranges": (0.3, 1.5),
  #     "shared_random": True,
  #   },
  # )

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

  cfg.events["foot_friction_spin"] = EventTermCfg(
    mode="startup",
    func=envs_mdp.dr.geom_friction,
    params={
      "asset_cfg": SceneEntityCfg("robot", geom_names=geom_names),
      "operation": "abs",
      "distribution": "log_uniform",
      "axes": [1],
      "ranges": (1e-4, 2e-2),
      "shared_random": True,
    },
  )

  cfg.events["foot_friction_roll"] = EventTermCfg(
    mode="startup",
    func=envs_mdp.dr.geom_friction,
    params={
      "asset_cfg": SceneEntityCfg("robot", geom_names=geom_names),
      "operation": "abs",
      "distribution": "log_uniform",
      "axes": [2],
      "ranges": (1e-5, 5e-3),
      "shared_random": True,
    },
  )
  cfg.events["base_com"].params["asset_cfg"].body_names = ("base_link",)

  # 域随机化：负载质量 ±20% (使用 pseudo_inertia 保证物理一致性)
  # 原始实现（仅改变质量，不改变惯性）：
  # cfg.events["robot_mass"] = EventTermCfg(
  #   mode="startup",
  #   func=envs_mdp.dr.body_mass,
  #   params={
  #     "asset_cfg": SceneEntityCfg("robot", body_names="base_link"),
  #     "operation": "scale",
  #     "ranges": (0.8, 1.2),
  #     "shared_random": True,
  #   },
  # )
  # 使用 pseudo_inertia 同时正确缩放质量和惯性张量
  # alpha_range: e^(-0.223) ≈ 0.8, e^(0.182) ≈ 1.2 (对应 ±20%)
  cfg.events["robot_inertia"] = EventTermCfg(
    mode="startup",
    func=envs_mdp.dr.pseudo_inertia,
    params={
      "asset_cfg": SceneEntityCfg("robot", body_names="base_link"),
      "alpha_range": (-0.223, 0.182),  # ±20% 质量和惯性变化
    },
  )

  # 域随机化：电机强度 ±10% (通过 effort_limits 实现)
  cfg.events["actuator_strength"] = EventTermCfg(
    mode="startup",
    func=envs_mdp.dr.effort_limits,
    params={
      "asset_cfg": SceneEntityCfg("robot", joint_names=".*"),
      "operation": "scale",
      "effort_limit_range": (0.9, 1.1),  # ±10% 电机强度变化
    },
  )

  cfg.rewards["pose"].params["std_standing"] = {
    r".*(FR|FL|RR|RL)_(hip|thigh)_joint.*": 0.05,
    r".*(FR|FL|RR|RL)_calf_joint.*": 0.1,
  }
  cfg.rewards["pose"].params["std_walking"] = {
    r".*(FR|FL|RR|RL)_(hip|thigh)_joint.*": 0.3,
    r".*(FR|FL|RR|RL)_calf_joint.*": 0.6,
  }
  cfg.rewards["pose"].params["std_running"] = {
    r".*(FR|FL|RR|RL)_(hip|thigh)_joint.*": 0.3,
    r".*(FR|FL|RR|RL)_calf_joint.*": 0.6,
  }

  cfg.rewards["upright"].params["asset_cfg"].body_names = ("base_link",)
  cfg.rewards["upright"].params["terrain_sensor_names"] = ("terrain_scan",)
  cfg.rewards["body_ang_vel"].params["asset_cfg"].body_names = ("base_link",)

  for reward_name in ["foot_clearance", "foot_slip"]:
    cfg.rewards[reward_name].params["asset_cfg"].site_names = site_names

  cfg.rewards["body_ang_vel"].weight = 0.0
  cfg.rewards["angular_momentum"].weight = 0.0
  cfg.rewards["air_time"].weight = 3.0  # Increased from 2.0 to encourage trotting gait
  cfg.rewards["air_time"].params["threshold_min"] = 0.1  # Minimum air time for trotting
  cfg.rewards["air_time"].params["threshold_max"] = (
    0.3  # Maximum air time to prevent jumping
  )

  # 提高速度跟踪权重
  cfg.rewards["track_linear_velocity"].weight = 3.0  # 从 2.0 提高到 3.0
  cfg.rewards["track_angular_velocity"].weight = 2.5  # 从 2.0 提高到 2.5

  # 降低其他奖励权重，让机器人更专注于速度跟踪
  cfg.rewards["upright"].weight = 0.5  # 从 1.0 降低到 0.5
  cfg.rewards["pose"].weight = 0.5  # 从 1.0 降低到 0.5

  # Per-body-group collision penalties.
  cfg.rewards["self_collisions"] = RewardTermCfg(
    func=mdp.self_collision_cost,
    weight=-0.1,
    params={"sensor_name": self_collision_cfg.name},
  )
  cfg.rewards["shank_collision"] = RewardTermCfg(
    func=mdp.self_collision_cost,
    weight=-0.1,
    params={"sensor_name": shank_ground_cfg.name},
  )
  cfg.rewards["trunk_head_collision"] = RewardTermCfg(
    func=mdp.self_collision_cost,
    weight=-0.1,
    params={"sensor_name": trunk_head_ground_cfg.name},
  )

  # On rough terrain the quadruped tilts significantly; don't terminate on
  # orientation alone. Let out_of_terrain_bounds handle resets.
  cfg.terminations.pop("fell_over", None)

  cfg.terminations["illegal_contact"] = TerminationTermCfg(
    func=mdp.illegal_contact,
    params={"sensor_name": thigh_ground_cfg.name},
  )

  # Apply play mode overrides.
  if play:
    # Effectively infinite episode length.
    cfg.episode_length_s = int(1e9)

    cfg.observations["actor"].enable_corruption = False
    cfg.events.pop("push_robot", None)
    cfg.terminations.pop("out_of_terrain_bounds", None)
    cfg.curriculum = {}
    cfg.events["randomize_terrain"] = EventTermCfg(
      func=envs_mdp.randomize_terrain,
      mode="reset",
      params={},
    )

    if cfg.scene.terrain is not None:
      if cfg.scene.terrain.terrain_generator is not None:
        cfg.scene.terrain.terrain_generator.curriculum = False
        cfg.scene.terrain.terrain_generator.num_cols = 5
        cfg.scene.terrain.terrain_generator.num_rows = 5
        cfg.scene.terrain.terrain_generator.border_width = 10.0

  return cfg


def unitree_go2_flat_env_cfg(play: bool = False) -> ManagerBasedRlEnvCfg:
  """Create Unitree Go1 flat terrain velocity configuration."""
  cfg = unitree_go2_rough_env_cfg(play=play)

  cfg.sim.njmax = 300
  cfg.sim.mujoco.ccd_iterations = 50
  cfg.sim.contact_sensor_maxmatch = 64
  cfg.sim.nconmax = None

  # Switch to flat terrain.
  assert cfg.scene.terrain is not None
  cfg.scene.terrain.terrain_type = "plane"
  cfg.scene.terrain.terrain_generator = None

  # Remove raycast sensors and collision sensors not needed on flat.
  remove_sensors = {
    "terrain_scan",
    "self_collision",
    "thigh_ground_touch",
    "shank_ground_touch",
    "trunk_ground_touch",
  }
  cfg.scene.sensors = tuple(
    s for s in (cfg.scene.sensors or ()) if s.name not in remove_sensors
  )
  del cfg.observations["actor"].terms["height_scan"]
  del cfg.observations["critic"].terms["height_scan"]
  cfg.rewards["upright"].params.pop("terrain_sensor_names", None)

  # Remove granular collision rewards (not useful on flat ground).
  for key in ("self_collisions", "shank_collision", "trunk_head_collision"):
    cfg.rewards.pop(key, None)

  # On flat terrain fell_over is sufficient; thigh contact implies fallen.
  cfg.terminations.pop("illegal_contact", None)
  cfg.terminations.pop("out_of_terrain_bounds", None)
  cfg.terminations["fell_over"] = TerminationTermCfg(
    func=mdp.bad_orientation,
    params={"limit_angle": math.radians(70.0)},
  )

  # Disable terrain curriculum (not present in play mode since rough clears all).
  cfg.curriculum.pop("terrain_levels", None)

  # Previous flat training setup kept push_robot enabled and used reset z
  # perturbation (0.28, 0.32), which is added on top of the robot init height.
  cfg.events.pop("push_robot", None)

  reset_base = cfg.events["reset_base"]
  reset_base.params["pose_range"]["z"] = (-0.01, 0.01)

  twist_cmd = cfg.commands["twist"]
  assert isinstance(twist_cmd, UniformVelocityCommandCfg)
  # Previous command setup:
  # twist_cmd.rel_standing_envs = 0.1
  # twist_cmd.rel_heading_envs = 0.3
  # twist_cmd.rel_forward_envs = 0.2
  # twist_cmd.heading_command = True
  twist_cmd.ranges.lin_vel_x = (-1.0, 1.0)
  twist_cmd.ranges.lin_vel_y = (-1.0, 1.0)
  twist_cmd.ranges.ang_vel_z = (-0.5, 0.5)
  # twist_cmd.ranges.heading = (-math.pi, math.pi)
  twist_cmd.resampling_time_range = (2.0, 4.0)
  twist_cmd.rel_standing_envs = 0.05
  twist_cmd.rel_heading_envs = 0.0
  twist_cmd.rel_forward_envs = 0.8
  twist_cmd.heading_command = False
  twist_cmd.ranges.heading = None
  # twist_cmd.ranges.lin_vel_x = (0.2, 1.2)
  # twist_cmd.ranges.lin_vel_y = (0.0, 0.0)
  # twist_cmd.ranges.ang_vel_z = (0.0, 0.0)

  # Previous rewards: linear=3.0, angular=2.0, pose=1.0, air_time=2.0,
  # foot_clearance=-2.0, foot_swing_height=-0.25, action_rate_l2=-0.1.
  cfg.rewards["track_linear_velocity"].weight = 4.0
  cfg.rewards["track_linear_velocity"].params["std"] = math.sqrt(0.15)
  cfg.rewards["track_angular_velocity"].weight = 0.5
  cfg.rewards["pose"].weight = 0.5
  cfg.rewards["air_time"].weight = 0.25
  cfg.rewards["air_time"].params["command_threshold"] = 0.1
  cfg.rewards["foot_clearance"].weight = -0.75
  cfg.rewards["foot_swing_height"].weight = -0.1
  cfg.rewards["action_rate_l2"].weight = -0.05

  if "command_vel" in cfg.curriculum:
    # Previous curriculum started immediately with full omnidirectional commands:
    # step 0: lin_vel_x=(-1.0, 1.0), ang_vel_z=(-0.5, 0.5)
    # step 120000: lin_vel_x=(-1.5, 2.0), ang_vel_z=(-0.7, 0.7)
    # step 240000: lin_vel_x=(-2.0, 3.0)
    cfg.curriculum["command_vel"].params["velocity_stages"] = [
      {
        "step": 0,
        "lin_vel_x": (0.2, 1.2),
        "lin_vel_y": (0.0, 0.0),
        "ang_vel_z": (0.0, 0.0),
      },
      {
        "step": 50 * 24,
        "lin_vel_x": (-0.5, 1.5),
        "lin_vel_y": (-0.4, 0.4),
        "ang_vel_z": (-0.4, 0.4),
      },
      {
        "step": 100 * 24,
        "lin_vel_x": (-1.0, 2.0),
        "lin_vel_y": (-0.8, 0.8),
        "ang_vel_z": (-0.7, 0.7),
      },
    ]

  if play:
    twist_cmd.ranges.lin_vel_x = (-1.5, 2.0)
    twist_cmd.ranges.lin_vel_y = (-1.0, 1.0)
    twist_cmd.ranges.ang_vel_z = (-0.7, 0.7)
    twist_cmd.heading_command = False
    twist_cmd.ranges.heading = None

  return cfg


def unitree_go2_rough_no_height_env_cfg(
  play: bool = False,
) -> ManagerBasedRlEnvCfg:
  """Create Unitree Go2 rough terrain velocity config WITHOUT height_scan observation.

  This is the same as unitree_go2_rough_env_cfg but removes height_scan from
  both actor and critic observation groups. Useful for ablation studies or
  comparing with models trained without terrain information.
  """
  cfg = unitree_go2_rough_env_cfg(play=play)

  # Reduce num_envs to save memory (no height_scan, smaller observation)
  cfg.scene.num_envs = 512

  # Remove height_scan from observations
  cfg.observations["actor"].terms.pop("height_scan", None)
  cfg.observations["critic"].terms.pop("height_scan", None)

  return cfg


def unitree_go2_rough_no_dr_env_cfg(
  play: bool = False,
) -> ManagerBasedRlEnvCfg:
  """Create Unitree Go2 rough terrain velocity config with domain randomization disabled.

  Keeps the same terrain, rewards, sensors, and command setup as the rough
  baseline, but removes startup/reset randomization events so we can compare
  training with and without domain randomization.
  """
  cfg = unitree_go2_rough_env_cfg(play=play)

  # Remove domain randomization events for a clean comparison run.
  for event_name in (
    "foot_friction_slide",
    "foot_friction_spin",
    "foot_friction_roll",
    "robot_inertia",
    "actuator_strength",
    "randomize_terrain",
  ):
    cfg.events.pop(event_name, None)

  return cfg


def unitree_go2_flat_env_cfg_42d(play: bool = False) -> ManagerBasedRlEnvCfg:
  """Create Unitree Go2 flat terrain velocity config with 42D observation space.

  This configuration removes base_lin_vel and base_ang_vel from observations,
  reducing the observation space from 48D to 42D to match WTW project setup:
  - gravity (3D)
  - commands (3D)
  - dof_pos (12D)
  - dof_vel (12D)
  - actions (12D)
  Total: 42D
  """
  cfg = unitree_go2_flat_env_cfg(play=play)

  # Remove base velocities from actor observations
  cfg.observations["actor"].terms.pop("base_lin_vel", None)
  cfg.observations["actor"].terms.pop("base_ang_vel", None)

  # Remove base velocities from critic observations
  cfg.observations["critic"].terms.pop("base_lin_vel", None)
  cfg.observations["critic"].terms.pop("base_ang_vel", None)

  return cfg
