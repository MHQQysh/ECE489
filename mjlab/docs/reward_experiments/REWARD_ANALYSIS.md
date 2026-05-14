# Go2 速度跟踪任务奖励函数分析

## 当前奖励函数配置

基于 `src/mjlab/tasks/velocity/config/go2/env_cfgs.py` 和 `velocity_env_cfg.py`

### 1. 速度跟踪奖励 (Velocity Tracking)

#### (i) 前向速度跟踪 `track_linear_velocity`
```python
RewardTermCfg(
    func=mdp.track_linear_velocity,
    weight=3.0,  # Flat: 4.0, Rough: 3.0
    params={"command_name": "twist", "std": math.sqrt(0.25)}  # Flat: sqrt(0.15)
)
```
- **公式**: `exp(-(xy_error + z_error) / std²)`
- **作用**: 奖励机器人跟踪 x-y 平面的线速度命令，惩罚 z 方向速度
- **当前权重**: 
  - Flat terrain: **4.0** (最高优先级)
  - Rough terrain: **3.0**

#### (i) 角速度跟踪 `track_angular_velocity`
```python
RewardTermCfg(
    func=mdp.track_angular_velocity,
    weight=2.5,  # Flat: 0.5, Rough: 2.5
    params={"command_name": "twist", "std": math.sqrt(0.5)}
)
```
- **公式**: `exp(-(z_error + xy_error) / std²)`
- **作用**: 奖励机器人跟踪 z 轴角速度（转向），惩罚 x-y 轴角速度
- **当前权重**:
  - Flat terrain: **0.5** (低优先级，主要前进)
  - Rough terrain: **2.5**

### 2. 姿态控制奖励 (Orientation & Posture)

#### (ii) 直立姿态 `upright`
```python
RewardTermCfg(
    func=mdp.upright,
    weight=0.5,  # Flat: 0.5, Rough: 0.5
    params={
        "std": math.sqrt(0.2),
        "asset_cfg": SceneEntityCfg("robot", body_names=("base_link",)),
        "terrain_sensor_names": ("terrain_scan",)  # Rough terrain only
    }
)
```
- **公式**: `exp(-xy_squared / std²)`
- **作用**: 
  - Flat: 惩罚相对世界坐标系的倾斜
  - Rough: 惩罚相对地形法向量的倾斜（更智能）
- **当前权重**: **0.5** (中等优先级)

#### (ii) 姿态保持 `pose`
```python
RewardTermCfg(
    func=mdp.variable_posture,
    weight=0.5,  # Flat: 0.5, Rough: 0.5
    params={
        "asset_cfg": SceneEntityCfg("robot", joint_names=(".*",)),
        "command_name": "twist",
        "std_standing": {  # 站立时严格
            r".*(FR|FL|RR|RL)_(hip|thigh)_joint.*": 0.05,
            r".*(FR|FL|RR|RL)_calf_joint.*": 0.1,
        },
        "std_walking": {  # 行走时宽松
            r".*(FR|FL|RR|RL)_(hip|thigh)_joint.*": 0.3,
            r".*(FR|FL|RR|RL)_calf_joint.*": 0.6,
        },
        "std_running": {  # 奔跑时更宽松
            r".*(FR|FL|RR|RL)_(hip|thigh)_joint.*": 0.3,
            r".*(FR|FL|RR|RL)_calf_joint.*": 0.6,
        },
        "walking_threshold": 0.05,
        "running_threshold": 1.5,
    }
)
```
- **公式**: `exp(-mean(error² / std²))`
- **作用**: 根据速度自适应调整关节姿态约束
- **当前权重**: **0.5**

### 3. 平滑运动奖励 (Smooth Motion)

#### (iii) 动作变化率 `action_rate_l2`
```python
RewardTermCfg(
    func=mdp.action_rate_l2,
    weight=-0.05,  # Flat: -0.05, Rough: -0.1
)
```
- **公式**: `sum((action_t - action_{t-1})²)`
- **作用**: 惩罚动作的剧烈变化（jerk）
- **当前权重**: 
  - Flat: **-0.05**
  - Rough: **-0.1**

#### (iii) 关节位置限制 `dof_pos_limits`
```python
RewardTermCfg(
    func=mdp.joint_pos_limits,
    weight=-1.0
)
```
- **作用**: 惩罚关节接近位置限制
- **当前权重**: **-1.0**

### 4. 足部运动奖励 (Foot Clearance & Air Time)

#### (iv) 足部离地高度 `foot_clearance`
```python
RewardTermCfg(
    func=mdp.feet_clearance,
    weight=-0.75,  # Flat: -0.75, Rough: -2.0
    params={
        "target_height": 0.1,  # 目标离地高度 10cm
        "height_sensor_name": "foot_height_scan",
        "command_name": "twist",
        "command_threshold": 0.05,
        "asset_cfg": SceneEntityCfg("robot", site_names=("FR", "FL", "RR", "RL")),
    }
)
```
- **公式**: `sum(|height - target| * vel_norm)`
- **作用**: 惩罚摆动腿偏离目标高度，按足部速度加权
- **当前权重**:
  - Flat: **-0.75**
  - Rough: **-2.0** (更重要)

#### (iv) 摆动高度 `foot_swing_height`
```python
RewardTermCfg(
    func=mdp.feet_swing_height,
    weight=-0.1,  # Flat: -0.1, Rough: -0.25
    params={
        "sensor_name": "feet_ground_contact",
        "height_sensor_name": "foot_height_scan",
        "target_height": 0.1,
        "command_name": "twist",
        "command_threshold": 0.05,
    }
)
```
- **公式**: `sum((peak_height / target - 1)² * first_contact)`
- **作用**: 在着地时评估摆动峰值高度
- **当前权重**:
  - Flat: **-0.1**
  - Rough: **-0.25**

#### 空中时间 `air_time`
```python
RewardTermCfg(
    func=mdp.feet_air_time,
    weight=0.25,  # Flat: 0.25, Rough: 2.0
    params={
        "sensor_name": "feet_ground_contact",
        "threshold_min": 0.05,
        "threshold_max": 0.5,
        "command_name": "twist",
        "command_threshold": 0.5,  # Flat: 0.1
    }
)
```
- **作用**: 奖励足部在合理范围内的空中时间
- **当前权重**:
  - Flat: **0.25**
  - Rough: **2.0** (鼓励动态步态)

### 5. 其他奖励

#### 足部滑动 `foot_slip`
```python
RewardTermCfg(
    func=mdp.feet_slip,
    weight=-0.1,
    params={
        "sensor_name": "feet_ground_contact",
        "command_name": "twist",
        "command_threshold": 0.05,
        "asset_cfg": SceneEntityCfg("robot", site_names=("FR", "FL", "RR", "RL")),
    }
)
```
- **公式**: `sum(vel_xy² * in_contact)`
- **作用**: 惩罚支撑腿滑动

#### 软着陆 `soft_landing`
```python
RewardTermCfg(
    func=mdp.soft_landing,
    weight=-1e-5,
    params={
        "sensor_name": "feet_ground_contact",
        "command_name": "twist",
        "command_threshold": 0.05,
    }
)
```
- **作用**: 惩罚着地冲击力过大

#### 碰撞惩罚 (Rough terrain only)
```python
# 自碰撞
RewardTermCfg(func=mdp.self_collision_cost, weight=-0.1, 
              params={"sensor_name": "self_collision"})

# 小腿碰撞地面
RewardTermCfg(func=mdp.self_collision_cost, weight=-0.1,
              params={"sensor_name": "shank_ground_touch"})

# 躯干碰撞地面
RewardTermCfg(func=mdp.self_collision_cost, weight=-0.1,
              params={"sensor_name": "trunk_ground_touch"})
```

## 奖励权重总结

### Flat Terrain
| 奖励类型 | 权重 | 优先级 |
|---------|------|--------|
| track_linear_velocity | **4.0** | 最高 |
| track_angular_velocity | 0.5 | 低 |
| upright | 0.5 | 中 |
| pose | 0.5 | 中 |
| air_time | 0.25 | 低 |
| action_rate_l2 | -0.05 | 低惩罚 |
| foot_clearance | -0.75 | 中惩罚 |
| foot_swing_height | -0.1 | 低惩罚 |
| foot_slip | -0.1 | 低惩罚 |
| dof_pos_limits | -1.0 | 高惩罚 |

### Rough Terrain
| 奖励类型 | 权重 | 优先级 |
|---------|------|--------|
| track_linear_velocity | **3.0** | 最高 |
| track_angular_velocity | **2.5** | 高 |
| air_time | **2.0** | 高 |
| upright | 0.5 | 中 |
| pose | 0.5 | 中 |
| action_rate_l2 | -0.1 | 中惩罚 |
| foot_clearance | **-2.0** | 高惩罚 |
| foot_swing_height | -0.25 | 中惩罚 |
| foot_slip | -0.1 | 低惩罚 |
| self_collisions | -0.1 | 中惩罚 |
| shank_collision | -0.1 | 中惩罚 |
| trunk_head_collision | -0.1 | 中惩罚 |
| dof_pos_limits | -1.0 | 高惩罚 |

## 针对四个目标的奖励设计

### (i) Forward Velocity Tracking
**当前设置**: 
- `track_linear_velocity`: weight=3.0-4.0, std=sqrt(0.15)-sqrt(0.25)

**影响因素**:
- `std` 越小 → 对误差越敏感 → 更严格的跟踪
- `weight` 越大 → 优先级越高

### (ii) Upright Body Orientation
**当前设置**:
- `upright`: weight=0.5, std=sqrt(0.2)

**影响因素**:
- Rough terrain 使用地形法向量（更智能）
- `std` 控制允许的倾斜范围

### (iii) Smooth Joint Motions
**当前设置**:
- `action_rate_l2`: weight=-0.05 to -0.1 (惩罚 jerk)
- `dof_pos_limits`: weight=-1.0 (惩罚关节限制)
- 没有直接的力矩惩罚

**缺失**:
- 没有显式的力矩平滑度惩罚
- 可以添加 `action_l2` 或 `torque_l2`

### (iv) Adequate Foot Clearance
**当前设置**:
- `foot_clearance`: weight=-0.75 to -2.0, target=0.1m
- `foot_swing_height`: weight=-0.1 to -0.25, target=0.1m
- `air_time`: weight=0.25 to 2.0

**影响因素**:
- `target_height` 控制期望离地高度
- `foot_clearance` 在整个摆动过程中评估
- `foot_swing_height` 只在着地时评估峰值

## 下一步：对比实验设计

见 `REWARD_EXPERIMENTS.md`
