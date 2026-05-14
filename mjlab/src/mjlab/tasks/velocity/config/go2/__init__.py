from mjlab.tasks.registry import register_mjlab_task
from mjlab.tasks.velocity.rl import VelocityOnPolicyRunner

from .env_cfgs import (
  GO2_TERRAIN_CHOICES,
  Go2TerrainType,
  unitree_go2_flat_env_cfg,
  unitree_go2_rough_env_cfg,
  unitree_go2_rough_no_dr_env_cfg,
  unitree_go2_rough_no_height_env_cfg,
  unitree_go2_terrain_env_cfg,
)
from .rl_cfg import unitree_go2_ppo_runner_cfg

_GO2_TERRAIN_TASKS = {
  "Slope": "slope",
  "Stairs": "stairs",
  "Bumps": "bumps",
  "Random": "random",
}

register_mjlab_task(
  task_id="Mjlab-Velocity-Rough-Unitree-Go2",
  env_cfg=unitree_go2_rough_env_cfg(),
  play_env_cfg=unitree_go2_rough_env_cfg(play=True),
  rl_cfg=unitree_go2_ppo_runner_cfg(),
  runner_cls=VelocityOnPolicyRunner,
)

register_mjlab_task(
  task_id="Mjlab-Velocity-Rough-NoDR-Unitree-Go2",
  env_cfg=unitree_go2_rough_no_dr_env_cfg(),
  play_env_cfg=unitree_go2_rough_no_dr_env_cfg(play=True),
  rl_cfg=unitree_go2_ppo_runner_cfg(),
  runner_cls=VelocityOnPolicyRunner,
)

register_mjlab_task(
  task_id="Mjlab-Velocity-Flat-Unitree-Go2",
  env_cfg=unitree_go2_flat_env_cfg(),
  play_env_cfg=unitree_go2_flat_env_cfg(play=True),
  rl_cfg=unitree_go2_ppo_runner_cfg(),
  runner_cls=VelocityOnPolicyRunner,
)

register_mjlab_task(
  task_id="Mjlab-Velocity-Rough-NoHeight-Unitree-Go2",
  env_cfg=unitree_go2_rough_no_height_env_cfg(),
  play_env_cfg=unitree_go2_rough_no_height_env_cfg(play=True),
  rl_cfg=unitree_go2_ppo_runner_cfg(),
  runner_cls=VelocityOnPolicyRunner,
)

for task_suffix, terrain in _GO2_TERRAIN_TASKS.items():
  register_mjlab_task(
    task_id=f"Mjlab-Velocity-{task_suffix}-Unitree-Go2",
    env_cfg=unitree_go2_terrain_env_cfg(terrain),
    play_env_cfg=unitree_go2_terrain_env_cfg(terrain, play=True),
    rl_cfg=unitree_go2_ppo_runner_cfg(),
    runner_cls=VelocityOnPolicyRunner,
  )

__all__ = [
  "GO2_TERRAIN_CHOICES",
  "Go2TerrainType",
  "unitree_go2_flat_env_cfg",
  "unitree_go2_rough_env_cfg",
  "unitree_go2_rough_no_dr_env_cfg",
  "unitree_go2_rough_no_height_env_cfg",
  "unitree_go2_terrain_env_cfg",
  "unitree_go2_ppo_runner_cfg",
]
