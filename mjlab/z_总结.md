



现在我新写的代码主要就是

1. 将go2 迁移进来 放在了src/mjlab/asset_zoo/robots/unitree_go2里面


先训练一个flat 一个slope


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

## tensorboard看训练效果
cd /home/y/ece489/lab4/mjlab
uv run tensorboard --logdir logs/rsl_rl/go1_velocity --port 6006
uv run tensorboard --logdir logs/rsl_rl/go2_velocity --port 6006





2. play_flat_withpush.py lay_slope_withpush.py




uv run python  play_flat_withpush.py

先按enable control然后可以自行调节方向速度 
并且可以按动push实现力量



2. run_reward_experiments.py  run_all_experiments.sh reward_experiments_config.py

尝试八种reward类型 【这里ai请你详细补充一下】



3.eval_slope_vs_flat.py

uv run eval_slope_vs_flat.py

实现对两个类型数据的10次实验 得到rms 

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


最终输出类似下图

Table 4: RL Controller Performance (mjlab/MuJoCo PPO Training)
Training Command vx vy Roll Pitch CoT Recovery
(m/s) (m/s) (deg) (deg)
Flat Forward 1.0 0.963 -0.003 2.50 0.82 133.13 40.0%
(500 iter) ±0.090 ±0.042 ±103.08 ±7.26
Flat Lateral 1.0 -0.049 0.947 -15.67 -0.84 103.43 0.0%
(500 iter) ±0.068 ±0.130 ±96.72 ±7.84
Flat Combined 0.954 0.476 47.98 0.09 78.69 60.0%
(500 iter) ±0.097 ±0.073 ±111.37 ±6.52
Slope Forward 1.0 0.933 -0.060 -27.37 0.26 76.73 40.0%
(1000 iter) ±0.183 ±0.128 ±76.23 ±2.91
Slope Lateral 1.0 0.072 0.841 -5.99 1.65 171.32 0.0%
(1000 iter) ±0.110 ±0.232 ±100.46 ±5.29
Slope Combined 0.894 0.453 -32.31 1.43 81.75 20.0%



4. domain_eval_slope_flat.py

先需要运行指令训练得到

export WANDB_MODE=disabled
MUJOCO_GL=egl uv run train Mjlab-Velocity-Rough-NoDR-Unitree-Go2 --env.scene.num-envs 512 --agent.max-iterations 1200 --agent.save-interval 200   --video True \
  --video-interval 200 \
  --video-length 200

然后可以进行

export WANDB_MODE=disabled
MUJOCO_GL=egl uv run play Mjlab-Velocity-Rough-Unitree-Go2 --checkpoint_file logs/rsl_rl/go2_velocity/rough_1200/model_1199.pt \
--num-envs 10 \
--viewer viser

最后
uv run python domain_eval_slope_flat.py
得到数据对比

