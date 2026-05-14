


agent4

要求：

测试环境
1. 平地​  训练100step
2. slope 训练300step

测试速度：两种命令速度
1. x 1m/s
2. y 1m/s
3. x 1m/s y 0.5m/s

测试指标（每个都10次）
1. 速度跟踪误差（RMS）；
2. 身体稳定性（RMS roll & pitch，即横滚/俯仰角波动）；
3. 能量消耗（Cost of Transport, CoT = 总能耗 / 位移，越小越节能）；
4. 鲁棒性：施加横向推力（30-50N，持续0.1s），记录“恢复成功次数”（被推后能不能站稳继续走）。

成果要求：
1. 10次就直接取均值 变成1.115 ± 0.20 这种样式的  然后6种配置 分别各自指标汇总一个表格 
2. 每个配置的video 保存一下 checkpoint十组中保存一组就行 


unset PYTHONPATH
unset LD_LIBRARY_PATH
unset PKG_CONFIG_PATH
unset CMAKE_PREFIX_PATH
uv run python scripts/eval_mpc_go2.py \
      --no-viewer \
      --gait trotting10 \
      --eval-trials 3 \
      --eval-steps 500 \
      --warmup 100 \
      --eval-delay 1.0 \
      --output doc/mpc_go2_eval_results.csv


uv run python scripts/go2_slope_mpc.py --gait trotting10

uv run python scripts/eval_mpc_go2.py


/home/y/ece489/lab4/pympc-quadruped/scripts/go2_mpc.py                                                                         
  根据这个生成一版slope地形的mpc如果要改mpc.py你自己生成一个slope_mpc.py不要改现在已经有了的文件                                 
❯ /home/y/ece489/lab4/pympc-quadruped/scripts/go2_mpc.py 根据这个生成一版slope地形的mpc如果要改mpc.py你自己生成一个slope_mpc.py不要改现在已经有了的文件   


uv run python scripts/go2_mpc_slope.py
uv run python scripts/go2_mpc.py



uv run python scripts/mujoco_mpc.py 

unset PYTHONPATH
unset LD_LIBRARY_PATH
unset PKG_CONFIG_PATH
unset CMAKE_PREFIX_PATH

cd /home/y/ece489/lab4/pympc-quadruped

 uv run python scripts/demo_push_test.py




# 测试

unset PYTHONPATH
unset LD_LIBRARY_PATH
unset PKG_CONFIG_PATH
unset CMAKE_PREFIX_PATH
uv run python scripts/eval_mpc_aliengo.py --steps 3000
uv run python scripts/eval_mpc_aliengo.py --no-viewer --eval-steps 3000 --eval-trials 1



uv run python /home/y/ece489/lab4/pympc-quadruped/scripts/eval_go2_trotting.py


uv run python scripts/mujoco_aliengo.py 

uv run python scripts/eval_mpc_aliengo.py
uv run python /home/y/ece489/lab4/pympc-quadruped/scripts/eval_mpc.py

uv run python scripts/demo_push_test_trajectory.py
# go2 仿真 (MPC)
unset PYTHONPATH
unset LD_LIBRARY_PATH
unset PKG_CONFIG_PATH
unset CMAKE_PREFIX_PATH
cd /home/y/ece489/lab4/pympc-quadruped
uv run python scripts/go2_mpc.py



uv run python scripts/mujoco_aliengo.py --log-file /tmp/robot_data.txt --steps 200



uv run python scripts/mujoco_aliengo.py --no-viewer --steps 2000 --log-file robot_data_log1.txt --log-interval 100


# 每步详细记录（和 Aliengo 一样）
uv run python scripts/mujoco_go2.py --steps 2000 --log-file go2_data_log.txt --log-interval 100





# 基础用法
uv run python scripts/mujoco_aliengo.py --gait trotting10

# 调整速度
uv run python scripts/mujoco_aliengo.py --gait pacing16 --xvel 0.8 --yvel 0.3 --yaw-rate 0.5

# 站立测试
uv run python scripts/mujoco_aliengo.py --gait standing --steps 500

# 快速小跑 (10步周期)
uv run python scripts/mujoco_aliengo.py --gait trotting10 --xvel 2

# 稳定小跑 (16步周期)
uv run python scripts/mujoco_aliengo.py --gait trotting16 --xvel 1.0

# 无GUI测试
uv run python scripts/mujoco_aliengo.py --gait trotting10 --no-viewer --steps 2000