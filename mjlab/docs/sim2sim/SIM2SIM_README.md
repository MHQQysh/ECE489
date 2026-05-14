# Sim2Sim 测试指南

这个文档说明如何在MuJoCo仿真环境中测试训练好的Go1机器狗policy，然后再部署到真实机器人。

## 当前状态

- **机器人配置**: Unitree Go1（不是Go2）
- **训练好的Policy位置**: `/home/y/ece489/lab4/mjlab/logs/rsl_rl/go1_velocity/2026-05-06_02-13-54/model_299.pt`
- **训练轮数**: 299轮
- **可用的checkpoint**: model_0.pt, model_100.pt, model_200.pt, model_299.pt

## 快速开始

### 1. 在MuJoCo中测试Policy（Sim2Sim）

使用默认checkpoint（model_299.pt）：

```bash
cd /home/y/ece489/lab4/mjlab
uv run python scripts/sim2sim_test.py
```

指定其他checkpoint：

```bash
uv run python scripts/sim2sim_test.py --checkpoint logs/rsl_rl/go1_velocity/2026-05-06_02-13-54/model_200.pt
```

使用粗糙地形：

```bash
uv run python scripts/sim2sim_test.py --terrain rough
```

运行多个并行环境：

```bash
uv run python scripts/sim2sim_test.py --num-envs 4
```

### 2. 使用mjlab自带的play脚本

mjlab也提供了官方的play脚本：

```bash
cd /home/y/ece489/lab4/mjlab
uv run python -m mjlab.scripts.play go1-velocity-flat \
    --checkpoint-file logs/rsl_rl/go1_velocity/2026-05-06_02-13-54/model_299.pt
```

## 部署到真实机器人

### 注意事项

1. **机器人型号不匹配**: 你训练的是Go1的policy，但`go2_deploy`项目是为Go2设计的
2. **SDK差异**: Go1使用`unitree_legged_sdk`，Go2使用`unitree_sdk2`
3. **建议**: 
   - 如果你有Go1机器人，使用原始的[walk-these-ways](https://github.com/Improbable-AI/walk-these-ways)项目部署
   - 如果你有Go2机器人，需要用Go2的配置重新训练policy

### Go2部署流程（如果重新训练Go2 policy）

参考 `/home/y/ece489/lab4/go2_deploy/README.md`：

1. **安装LCM通信库**:
```bash
git clone https://github.com/lcm-proj/lcm.git
cd lcm
mkdir build && cd build
cmake ..
make
sudo make install
```

2. **编译unitree_sdk2和lcm_position_go2**:
```bash
cd /home/y/ece489/lab4/go2_deploy/go2_gym_deploy/unitree_sdk2_bin/library/unitree_sdk2
sudo ./install.sh
mkdir build && cd build
cmake ..
make

cd /home/y/ece489/lab4/go2_deploy/go2_gym_deploy
mkdir build && cd build
cmake ..
make -j
```

3. **连接Go2机器人**:
```bash
# 用网线连接电脑和Go2
ping 192.168.123.161

# 查看网络接口
ifconfig  # 记下接口名称，如 eth0
```

4. **启动LCM通信**:
```bash
cd /home/y/ece489/lab4/go2_deploy/go2_gym_deploy/build
sudo ./lcm_position_go2 eth0  # 替换eth0为你的网络接口
# 按Enter键几次建立连接
```

5. **运行Policy**（新终端）:
```bash
cd /home/y/ece489/lab4/go2_deploy/go2_gym_deploy/scripts
python deploy_policy.py
# 按遥控器R2键启动
```

### 遥控器按键映射

- **R2**: 启动控制器
- **L2+B**: 紧急停止（切换到阻尼模式）
- **左摇杆**: 控制前进/后退和左右平移
- **右摇杆**: 控制转向

## 文件说明

### 训练相关文件

- `model_299.pt`: 最终训练的policy（推荐使用）
- `2026-05-06_02-13-54.onnx`: ONNX格式的模型（用于部署）
- `events.out.tfevents.*`: TensorBoard训练日志
- `params/`: 训练参数配置
- `videos/`: 训练过程录制的视频

### 配置文件

- `src/mjlab/tasks/velocity/config/go1/env_cfgs.py`: Go1环境配置
- `src/mjlab/tasks/velocity/config/go1/rl_cfg.py`: RL算法配置

## 故障排除

### Sim2Sim测试问题

1. **找不到checkpoint**:
```bash
# 检查文件是否存在
ls -lh /home/y/ece489/lab4/mjlab/logs/rsl_rl/go1_velocity/2026-05-06_02-13-54/
```

2. **CUDA内存不足**:
```bash
# 使用CPU运行
uv run python scripts/sim2sim_test.py --device cpu
```

3. **显示问题**:
```bash
# 确保DISPLAY环境变量已设置
echo $DISPLAY
```

### 真机部署问题

1. **无法ping通机器人**: 检查网线连接和网络配置
2. **LCM连接失败**: 确保网络接口名称正确
3. **机器人行为异常**: 立即按L2+B切换到阻尼模式

## 下一步

1. ✅ 在MuJoCo中测试policy（sim2sim）
2. 如果效果好，考虑：
   - 使用Go1机器人 + walk-these-ways部署
   - 或者用Go2配置重新训练 + go2_deploy部署
3. 真机测试时务必小心，准备好紧急停止

## 参考资料

- [walk-these-ways (Go1)](https://github.com/Improbable-AI/walk-these-ways)
- [go2_deploy (Go2)](https://github.com/Teddy-Liao/walk-these-ways-go2)
- [unitree_sdk2](https://github.com/unitreerobotics/unitree_sdk2)
