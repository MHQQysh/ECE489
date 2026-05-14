# ECE489 四足机器人控制项目

本项目包含两个独立的四足机器人控制方法实现：**强化学习 (RL)** 和 **模型预测控制 (MPC)**，均基于 Unitree Go2 机器人在 MuJoCo 仿真环境中进行。

---
## 0. 任务汇报

1. **强化学习方法 (mjlab/)**
   1. 将 Unitree Go2 机器人迁移到项目中，位置在：
      - `src/mjlab/asset_zoo/robots/unitree_go2`
   2. 完成了两类地形的训练与测试：
      - Flat 平地
      - Slope 斜坡
   3. 编写了带外力推搡测试的脚本：
      - `play_flat_withpush.py`
      - `play_slope_withpush.py`
   4. 编写了平地/斜坡对比评估脚本：
      - `eval_slope_vs_flat.py`
   5. 编写了跨域泛化评估脚本：
      - `domain_eval_slope_flat.py`
   6. 进行了 reward 相关实验探索：
      - `run_reward_experiments.py`
      - `run_all_experiments.sh`
      - `reward_experiments_config.py`
   7. 待完成
      - sim2real
         
   详细文档: [`mjlab/README.md`](mjlab/README.md)

2. **模型预测控制 (pympc-quadruped/)**
   1. 环境配置 + 替换模型为 Go2
      - 解决 Pinocchio 冲突
      - 摩擦系数、PD 控制器增益调整
      - Go2 机器人模型迁移到 `robot/go2/`
   2. MPC 仿真 + 速度可视化
      - 实现速度跟踪可视化
      - 运行脚本：`scripts/go2_mpc.py`
   3. 评估测试 - 三种运动模式（平地）
      - Forward 1.0 m/s
      - Lateral 1.0 m/s
      - Fwd 1.0 + Lat 0.5
      - 运行脚本：`scripts/eval_mpc_go2.py`
   4. 推力扰动测试
      - 外部推力干扰鲁棒性测试
      - 运行脚本：`scripts/demo_push_test.py`
   5. 待完成
      - 步态优化
      - 斜坡地形测试
   
   详细文档: [`pympc-quadruped/README.md`](pympc-quadruped/README.md)

---

## 1. 环境配置

两个子项目使用独立的 Python 环境，需要分别进行配置：

```bash
# 配置 RL 项目环境
cd mjlab
uv sync

# 配置 MPC 项目环境
cd ../pympc-quadruped
uv sync
```

---

## 许可证

请参考各子项目的许可证文件。
