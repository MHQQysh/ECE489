# 如何将训练改成Go2配置

## 方法一：使用现有的Go2 URDF转换为MuJoCo格式（推荐）

Go2的URDF文件已经存在于：`/home/y/ece489/lab4/go2_deploy/resources/robots/go2/urdf/go2.urdf`

### 步骤1：转换URDF到MuJoCo XML

```bash
cd /home/y/ece489/lab4/mjlab

# 使用MuJoCo的转换工具
uv run python -c "
import mujoco
from pathlib import Path

# 加载Go2 URDF
urdf_path = '/home/y/ece489/lab4/go2_deploy/resources/robots/go2/urdf/go2.urdf'
spec = mujoco.MjSpec()
spec.from_file(urdf_path)

# 保存为MuJoCo XML
output_path = 'src/mjlab/asset_zoo/robots/unitree_go2/xmls/go2.xml'
Path(output_path).parent.mkdir(parents=True, exist_ok=True)
spec.to_xml(output_path)
print(f'Converted to: {output_path}')
"
```

### 步骤2：创建Go2常量配置文件

创建 `src/mjlab/asset_zoo/robots/unitree_go2/go2_constants.py`，参考Go1的配置，修改以下参数：

**Go1 vs Go2 主要差异：**

| 参数 | Go1 | Go2 | 说明 |
|------|-----|-----|------|
| 质量 | ~12kg | ~15kg | Go2更重 |
| 髋关节扭矩 | 23.7 Nm | 45 Nm | Go2扭矩更大 |
| 膝关节扭矩 | 35.55 Nm | 45 Nm | Go2扭矩更大 |
| 髋关节速度 | 30.1 rad/s | 30 rad/s | 相似 |
| 膝关节速度 | 20.06 rad/s | 30 rad/s | Go2更快 |
| 站立高度 | ~0.28m | ~0.32m | Go2稍高 |
| 电机型号 | 8108 | 8108 Pro | Go2电机升级 |

### 步骤3：创建Go2环境配置

创建 `src/mjlab/tasks/velocity/config/go2/env_cfgs.py`，基于Go1配置修改。

### 步骤4：创建Go2 RL配置

创建 `src/mjlab/tasks/velocity/config/go2/rl_cfg.py`，可以直接复制Go1的配置。

### 步骤5：注册Go2任务

在 `src/mjlab/tasks/velocity/config/go2/__init__.py` 中注册任务。

## 方法二：直接修改现有配置（快速测试）

如果只是想快速测试，可以直接修改Go1的配置文件：

### 修改电机参数

编辑 `src/mjlab/tasks/velocity/config/go1/env_cfgs.py`：

```python
# 在文件开头导入时，修改为：
from mjlab.asset_zoo.robots import (
  GO1_ACTION_SCALE,  # 保持不变
  get_go1_robot_cfg,  # 保持不变
)

# 然后在函数内部修改电机参数：
def unitree_go2_rough_env_cfg(play: bool = False):
  cfg = make_velocity_env_cfg()
  
  # 使用Go1的模型，但调整参数以匹配Go2
  cfg.scene.entities = {"robot": get_go1_robot_cfg()}
  
  # 调整动作缩放以匹配Go2的更大扭矩
  joint_pos_action = cfg.actions["joint_pos"]
  joint_pos_action.scale = {
    ".*hip_joint": 0.5,    # Go2扭矩更大，增加动作范围
    ".*thigh_joint": 0.5,
    ".*calf_joint": 0.5,
  }
  
  # 其他配置保持不变...
```

## 方法三：使用我提供的自动化脚本（最简单）

我可以为你创建一个自动化脚本，一键完成所有配置。

## Go1和Go2的关键差异

### 1. 硬件差异
- **电机**: Go2使用8108 Pro电机，扭矩从23.7/35.55 Nm提升到45 Nm
- **质量**: Go2约15kg，Go1约12kg
- **尺寸**: Go2略大，站立高度约32cm vs Go1的28cm
- **SDK**: Go2使用unitree_sdk2（基于DDS），Go1使用unitree_legged_sdk（基于UDP）

### 2. 训练时需要调整的参数
- **动作缩放**: 由于扭矩更大，需要调整action scale
- **初始姿态**: 站立高度从0.278m调整到约0.32m
- **奖励权重**: 可能需要微调，因为动力学特性不同
- **碰撞检测**: Go2的碰撞几何可能略有不同

### 3. 部署差异
- **通信协议**: Go2使用DDS而非UDP
- **SDK接口**: 完全不同的API
- **控制频率**: 可能有差异

## 推荐流程

1. **先用方法一创建完整的Go2配置**（最正确）
2. **训练Go2 policy**：
   ```bash
   uv run python -m mjlab.scripts.train go2-velocity-flat
   ```
3. **Sim2Sim测试**：
   ```bash
   uv run python scripts/sim2sim_test.py --checkpoint logs/.../model_xxx.pt
   ```
4. **真机部署**：使用go2_deploy项目

## 需要我帮你做什么？

我可以帮你：
1. ✅ 自动转换Go2 URDF到MuJoCo XML
2. ✅ 创建完整的Go2配置文件（constants, env_cfgs, rl_cfg）
3. ✅ 注册Go2任务到mjlab
4. ✅ 提供训练脚本

你想让我现在就帮你创建完整的Go2配置吗？
