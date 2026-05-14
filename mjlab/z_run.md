


codex --dangerously-bypass-approvals-and-sandbox
claude --dangerously-skip-permissions








task

1. 讲出来我的observation和action都是什么 
2. 写出来我有哪些奖励函数 然后有关 Design a reward that encourages: (i) forward velocity tracking, (ii) upright body orientation, (iii) smooth joint motions (penalize jerk and torque), (iv) adequate foot clearance
during swing.这厮方面的奖励函数我设置的多少 训练的时候不同大小效果怎么样 可以多跑几组 然后对比curve曲线 已经 video效果

3.域随机化（Domain Randomization）
训练时随机化环境参数，提升策略鲁棒性：
摩擦系数 μ ∈ [0.5, 1.2]；
负载质量 ±20%；
电机强度 ±10%。
加了前后的曲线对比 reward 和分支reward

4. 
基本的cpg like 步态 手动调频 视频效果

测试环境：平地​ + 挑战性地形（比如斜坡、台阶、粗糙地面）；
测试速度：两种命令速度（比如 0.5m/s、1.0m/s）；
每个场景测试 ≥10次，记录指标：
速度跟踪误差（RMS）；
身体稳定性（RMS roll & pitch，即横滚/俯仰角波动）；
能量消耗（Cost of Transport, CoT = 总能耗 / 位移，越小越节能）；
鲁棒性：施加横向推力（30-50N，持续0.1s），记录“恢复成功次数”（被推后能不能站稳继续走）。

分析 RL 方法 vs 基准方法的：
优势（比如速度更稳、地形适应强、能耗低）；
失败模式（比如极端地形/推力下会不会倒、动作是否僵硬）


5. 
额外步态（Additional gaits）
实现 walk（走）、pace（溜蹄）、bound（蹦跳）​ 等步态，并展示“步态切换”（比如从走到跑，或从走切换到爬坡步态）


MPC 替换（Model Predictive Control）
把“单步QP（二次规划）”换成 滚动时域MPC（用 SRBD 模型，参考 Quadruped-PyMPC），让控制更具前瞻性（比如提前规划几步的轨迹）。








#######################################
agent1 sim2sim

##########################################
agent2 运行各种reward 看总体的曲线和视频效果



2. 写出来我有哪些奖励函数 然后有关 Design a reward that encourages: (i) forward velocity tracking, (ii) upright body orientation, (iii) smooth joint motions (penalize jerk and torque), (iv) adequate foot clearance
during swing.这厮方面的奖励函数我设置的多少 训练的时候不同大小效果怎么样 可以多跑几组 然后对比curve曲线 已经 video效果


Hint:
1. 这个好像可以对比
export WANDB_MODE=disabled
bash run_all_experiments.sh
python analyze_reward_experiments.py

tensorboard --logdir experiments/reward_comparison

##########################################
agent3
运行domain randomization和不运行的区别

成果要求
1. 加了前后然后各种reward loss对比 

Hint
1. ## tensorboard看训练效果
cd /home/y/ece489/lab4/mjlab
uv run tensorboard --logdir logs/rsl_rl/go1_velocity --port 6006
uv run tensorboard --logdir logs/rsl_rl/go2_velocity --port 6006
uv run tensorboard --logdir logs/rsl_rl/go2_reward_velocity --port 6006

这个board可以看reward对比


export WANDB_MODE=disabled
MUJOCO_GL=egl uv run train Mjlab-Velocity-Rough-Unitree-Go2 --env.scene.num-envs 512 --agent.max-iterations 1200 --agent.save-interval 200 


export WANDB_MODE=disabled
MUJOCO_GL=egl uv run train Mjlab-Velocity-Rough-NoDR-Unitree-Go2 --env.scene.num-envs 512 --agent.max-iterations 1200 --agent.save-interval 200   --video True \
  --video-interval 200 \
  --video-length 200


MUJOCO_GL=egl uv run play Mjlab-Velocity-Rough-Unitree-Go2 --checkpoint_file /home/y/ece489/lab4/mjlab/logs/rsl_rl/go2_velocity/2026-05-14_07-58-52/model_1199.pt \
--num-envs 10 \
--viewer viser


MUJOCO_GL=egl uv run train Mjlab-Velocity-Slope-Unitree-Go2 \
  --env.scene.num-envs 512 \
  --agent.max-iterations 300 \
  --agent.save-interval 100 \
  --video True \
  --video-interval 200 \
  --video-length 200


###########################################
agent4

要求：

测试环境
1. 平地​  训练500step
2. slope 训练1000step

测试速度：两种命令速度
1. x 1m/s
2. y 1m/s
3. x 1m/s y 0.5m/s

测试指标（每个都10次）
1. 速度跟踪误差（RMS）；
2. 身体稳定性（RMS roll & pitch，即横滚/俯仰角波动）；
3. 能量消耗（Cost of Transport, CoT = 总能耗 / 位移，越小越节能）；
4. 鲁棒性：施加横向推力（30-50N，持续0.1s），记录“恢复成功次数”（被推后能不能站稳继续走）。



### 评估脚本输出表格

运行 `eval_slope_vs_flat.py` 会生成以下汇总表格：

1. **Table 1: Velocity Tracking** - 速度跟踪误差（Vel_X_RMSE, Mean_X）
2. **Table 2: Body Stability** - 身体稳定性标准差（Roll_Std, Pitch_Std）
3. **Table 3: Cost of Transport** - 能耗效率（CoT）
4. **Table 4: Push Recovery Rate** - 推力恢复成功率
5. **Table 5: Roll/Pitch Stability** - 平均姿态角（Mean_Roll, Mean_Pitch）
6. **Table 6: Energy Summary** - 能量消耗详情（Total_Energy, Mean_Torque）

成果要求：
1. 10次就直接取均值 变成1.115 ± 0.20 这种样式的  然后6种配置 分别各自指标汇总一个表格 
2. 每个配置的video 保存一下 checkpoint十组中保存一组就行 


Hint
1. train的代码如下 
cd /home/y/ece489/lab4/mjlab
export WANDB_MODE=disabled

MUJOCO_GL=egl uv run train Mjlab-Velocity-Flat-Unitree-Go2 \
  --env.scene.num-envs 1024 \
  --agent.max-iterations 200 \
  --agent.save-interval 100 \
  --video True \
  --video-interval 200 \
  --video-length 200



#####################################


MUJOCO_GL=egl uv run python domain_eval_slope_flat.py为什么这个运行出来效果这么差
### Table 1: Velocity Tracking ###
Model    Command                Vel_X              Vel_Y             
------------------------------------------------------------------------
DR       Forward 1.0 m/s          0.747 ± 0.345       0.003 ± 0.107  
DR       Lateral 1.0 m/s          0.145 ± 0.276       0.567 ± 0.455  
DR       Fwd 1.0 + Lat 0.5        0.751 ± 0.349       0.287 ± 0.298  
NoDR     Forward 1.0 m/s          0.786 ± 0.304       0.147 ± 0.167  
NoDR     Lateral 1.0 m/s          0.183 ± 0.286       0.626 ± 0.397  
NoDR     Fwd 1.0 + Lat 0.5        0.845 ± 0.278       0.406 ± 0.145  

感觉非常不准 但是/home/y/ece489/lab4/mjlab/eval_slope_vs_flat.py

Model,Terrain,Command,Velocity_X_m_per_s,Velocity_Y_m_per_s,Roll_deg,Pitch_deg,CoT,Total_Energy_J,Mean_Torque_Nm,Push_Recovery
Flat,Flat,Forward 1.0 m/s,"0.9632 ± 0.0897","-0.0034 ± 0.0422","2.50 ± 103.08","0.82 ± 7.26",133.1285,12814.77,1281.48,40.0%
Flat,Flat,Lateral 1.0 m/s,"-0.0487 ± 0.0675","0.9472 ± 0.1300","-15.67 ± 96.72","-0.84 ± 7.84",103.4327,14000.97,1400.10,0.0%
Flat,Flat,Fwd 1.0 + Lat 0.5,"0.9543 ± 0.0966","0.4762 ± 0.0728","47.98 ± 111.37","0.09 ± 6.52",78.6910,12040.02,1204.00,60.0%
跑出来还是非常准的

##########################################
# mpc版本

unset PYTHONPATH
unset LD_LIBRARY_PATH
unset PKG_CONFIG_PATH
unset CMAKE_PREFIX_PATH
cd /home/y/ece489/lab4/pympc-quadruped
uv run python scripts/mujoco_cpg.py 


unset PYTHONPATH
unset LD_LIBRARY_PATH
unset PKG_CONFIG_PATH
unset CMAKE_PREFIX_PATH
cd /home/y/ece489/lab4/pympc-quadruped

uv run python scripts/mujoco_aliengo.py 
uv run python scripts/mujoco_mpc.py 

 

uv run python scripts/mujoco_aliengo.py 


# go2 仿真 (MPC)
unset PYTHONPATH
unset LD_LIBRARY_PATH
unset PKG_CONFIG_PATH
unset CMAKE_PREFIX_PATH
cd /home/y/ece489/lab4/pympc-quadruped
uv run python scripts/mujoco_go2.py



# go2 训练

## train代码

cd /home/y/ece489/lab4/mjlab
export WANDB_MODE=disabled

MUJOCO_GL=egl uv run train Mjlab-Velocity-Flat-Unitree-Go2 \
  --env.scene.num-envs 1024 \
  --agent.max-iterations 300 \
  --agent.save-interval 100 \
  --video True \
  --video-interval 200 \
  --video-length 200

## play部分
uv run play Mjlab-Velocity-Flat-Unitree-Go2 \
--checkpoint_file /home/y/ece489/lab4/mjlab/logs/rsl_rl/go2_velocity/2026-05-12_05-41-56/model_500.pt \
--num-envs 1 \
--viewer viser


## tensorboard看训练效果
cd /home/y/ece489/lab4/mjlab
uv run tensorboard --logdir logs/rsl_rl/go1_velocity --port 6006
uv run tensorboard --logdir logs/rsl_rl/go2_velocity --port 6006


# 地形
export WANDB_MODE=disabled

 MUJOCO_GL=egl uv run train Mjlab-Velocity-Slope-Unitree-Go2 \
  --env.scene.num-envs 512 \
  --agent.max-iterations 300 \
  --agent.save-interval 100 \
  --video True \
  --video-interval 200 \
  --video-length 200


uv run play Mjlab-Velocity-Slope-Unitree-Go2 \
--checkpoint-file /home/y/ece489/lab4/mjlab/logs/rsl_rl/go2_velocity/2026-05-12_05-17-00/model_500.pt \
--num-envs 10 \
--device cuda:0 \
--viewer viser



# cpg

cd /home/y/ece489/lab4/mjlab
uv run python src/mjlab/scripts/demo_cpg.py





# 部署sim2sim
cd /home/y/ece489/lab4/go2_deploy/scripts

python play_mujoco_sim2sim.py \
    --urdf /home/y/ece489/lab4/mjlab/src/mjlab/asset_zoo/robots/unitree_go2/xmls/scene_go2.xml \
    --num_steps 500



# 部署


cd /home/y/ece489/lab4/go2_deploy/go2_gym_deploy/build
sudo ./lcm_receive

cd 
sudo. ./






# isaacgym训练
cd /home/y/ece489/lab4/go2_deploy/scripts
source ~/isaacgym_env/bin/activate
python train.py


