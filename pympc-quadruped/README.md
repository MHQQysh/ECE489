# 四足机器人 MPC 控制器 (Go2)

基于模型预测控制(MPC)的四足机器人运动控制，使用 Unitree Go2 机器人在 MuJoCo 仿真环境中实现。

## 0. 个人任务汇报

### 已完成工作

1. **环境配置 + 替换模型为 Go2**（详见第 1 节）
   - 解决 Pinocchio 冲突
   - 摩擦系数、PD 控制器增益调整
   - Go2 机器人模型迁移到 `robot/go2/`

2. **MPC 仿真 + 速度可视化**（详见第 2 节）
   - 实现速度跟踪可视化
   - 运行脚本：`scripts/go2_mpc.py`

3. **评估测试 - 三种运动模式（平地）**（详见第 3 节）
   - Forward 1.0 m/s
   - Lateral 1.0 m/s
   - Fwd 1.0 + Lat 0.5
   - 运行脚本：`scripts/eval_mpc_go2.py`

4. **推力扰动测试**（详见第 4 节）
   - 外部推力干扰鲁棒性测试
   - 运行脚本：`scripts/demo_push_test.py`

### 待完成

- 步态优化
- 斜坡地形测试

## 1. 环境配置 + 替换模型为 Go2

本地如果安装了 Pinocchio 可能会产生冲突。项目使用 `uv` 自动配置了pin=3.9 ，因此每次运行前需要清除本机环境变量：

```bash
unset PYTHONPATH
unset LD_LIBRARY_PATH
unset PKG_CONFIG_PATH
unset CMAKE_PREFIX_PATH
```

**已完成的配置调整：**
- 摩擦系数配置
- PD 控制器增益调整 (Kp, Kd)
- Go2 机器人模型参数

## 2. MPC 仿真 + 速度可视化

运行 Go2 MPC 控制器，包含实时速度跟踪可视化：

```bash
uv run python /home/y/ece489/lab4/pympc-quadruped/scripts/go2_mpc.py
```

需要修改的文件是`config/robot_configs.py`

**新增功能：** 速度可视化显示

## 3. 评估测试 - 三种运动模式（平地）

运行完整评估，测试三种运动指令在平地地形下的表现：

```bash
uv run python /home/y/ece489/lab4/pympc-quadruped/scripts/eval_mpc_go2.py
```

### 速度跟踪性能

| 地形 | 指令 | Vel_X_RMSE | Vel_Y_RMSE | Mean_X | Mean_Y |
|------|------|-----------|-----------|--------|--------|
| flat | Forward 1.0 m/s | 0.0415 | 0.0505 | 1.0172 | 0.0212 |
| flat | Lateral 1.0 m/s | 0.1364 | 0.0969 | 0.0686 | 1.0862 |
| flat | Fwd 1.0 + Lat 0.5 | 0.0764 | 0.1789 | 0.9809 | 0.6678 |

### 机身稳定性

| 地形 | 指令 | Roll_Std | Pitch_Std | Mean_R | Mean_P |
|------|------|----------|-----------|--------|--------|
| flat | Forward 1.0 m/s | 0.57 | 0.39 | -0.12 | 6.08 |
| flat | Lateral 1.0 m/s | 1.23 | 1.66 | -4.50 | 0.65 |
| flat | Fwd 1.0 + Lat 0.5 | 1.07 | 1.14 | -1.34 | 6.02 |

### 能量效率

| 地形 | 指令 | CoT | Distance |
|------|------|-----|----------|
| flat | Forward 1.0 m/s | 3.8658 | 0.5091 |
| flat | Lateral 1.0 m/s | 6.6671 | 0.5435 |
| flat | Fwd 1.0 + Lat 0.5 | 5.3980 | 0.5948 |

## 4. 推力扰动测试

测试机器人对外部推力干扰的鲁棒性：

```bash
uv run python scripts/demo_push_test.py
```

## 5. 待完成

- 步态
- slope

## 项目结构

详细代码架构说明见 `doc/code_architecture.md`