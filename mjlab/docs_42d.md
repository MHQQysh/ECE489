# 42D Observation Space Configuration

## Overview

This configuration removes `base_lin_vel` and `base_ang_vel` from the observation space, reducing it from 48D to 42D to match the WTW project setup.

## Observation Space Comparison

### Original (48D)
| Component        | Dimension | Description                    |
|------------------|-----------|--------------------------------|
| base_lin_vel     | 3D        | Base linear velocity (IMU)     |
| base_ang_vel     | 3D        | Base angular velocity (IMU)    |
| projected_gravity| 3D        | Gravity vector in base frame   |
| joint_pos        | 12D       | Joint positions                |
| joint_vel        | 12D       | Joint velocities               |
| actions          | 12D       | Previous actions               |
| command          | 3D        | Velocity commands              |
| **Total**        | **48D**   |                                |

### New 42D Configuration
| Component        | Dimension | Description                    |
|------------------|-----------|--------------------------------|
| ~~base_lin_vel~~ | ~~3D~~    | ❌ Removed                     |
| ~~base_ang_vel~~ | ~~3D~~    | ❌ Removed                     |
| projected_gravity| 3D        | Gravity vector in base frame   |
| joint_pos        | 12D       | Joint positions                |
| joint_vel        | 12D       | Joint velocities               |
| actions          | 12D       | Previous actions               |
| command          | 3D        | Velocity commands              |
| **Total**        | **42D**   |                                |

## Task Registration

The new task is registered as: `Mjlab-Velocity-Flat-Unitree-Go2-42`

## Usage

### Training
```bash
./train_42d.sh
```

Or manually:
```bash
MUJOCO_GL=egl uv run train Mjlab-Velocity-Flat-Unitree-Go2-42 \
  --env.scene.num-envs 1024 \
  --agent.max-iterations 300 \
  --agent.save-interval 100 \
  --video True \
  --video-interval 200 \
  --video-length 200
```

### Playing/Evaluation
```bash
./play_42d.sh logs/Mjlab-Velocity-Flat-Unitree-Go2-42/model_100.pt
```

Or manually:
```bash
MUJOCO_GL=egl uv run play Mjlab-Velocity-Flat-Unitree-Go2-42 \
  --checkpoint <checkpoint_path> \
  --num-envs 1 \
  --record-video
```

## Implementation Details

The configuration is implemented in:
- `src/mjlab/tasks/velocity/config/go2/env_cfgs.py`: `unitree_go2_flat_env_cfg_42d()`
- `src/mjlab/tasks/velocity/config/go2/__init__.py`: Task registration

The function removes base velocity observations from both actor and critic observation groups:
```python
cfg.observations["actor"].terms.pop("base_lin_vel", None)
cfg.observations["actor"].terms.pop("base_ang_vel", None)
cfg.observations["critic"].terms.pop("base_lin_vel", None)
cfg.observations["critic"].terms.pop("base_ang_vel", None)
```

## Network Architecture

The policy network will automatically adapt to the 42D input dimension. No manual network configuration changes are needed.

## Comparison with WTW Project

| Project | Observation Space | Notes                          |
|---------|-------------------|--------------------------------|
| WTW     | 42D               | No base velocities             |
| MJLab   | 48D (original)    | Includes base velocities       |
| MJLab   | 42D (new)         | ✅ Matches WTW configuration   |

Both configurations now have identical observation spaces:
- gravity (3D)
- commands (3D) 
- dof_pos (12D)
- dof_vel (12D)
- actions (12D)
