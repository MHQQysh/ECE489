#!/usr/bin/env python3
"""
自动化奖励函数对比实验脚本

用法:
  # 运行单个实验
  python run_reward_experiments.py --experiment baseline --iterations 1000

  # 运行所有实验
  python run_reward_experiments.py --all --iterations 1000

  # 继续之前的实验
  python run_reward_experiments.py --experiment baseline --resume

  # 生成对比报告
  python run_reward_experiments.py --analyze
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from reward_experiments_config import EXPERIMENTS, get_experiment_config


class ExperimentRunner:
  """实验运行器"""

  def __init__(self, base_dir: str = "experiments/reward_comparison"):
    self.base_dir = Path(base_dir)
    self.base_dir.mkdir(parents=True, exist_ok=True)
    self.results_file = self.base_dir / "results.json"
    self.load_results()

  def load_results(self):
    """加载实验结果"""
    if self.results_file.exists():
      with open(self.results_file, "r") as f:
        self.results = json.load(f)
    else:
      self.results = {}

  def save_results(self):
    """保存实验结果"""
    with open(self.results_file, "w") as f:
      json.dump(self.results, f, indent=2)

  def create_experiment_config(self, exp_name: str, output_dir: Path):
    """创建实验配置文件"""
    config = get_experiment_config(exp_name)
    config_dict = config.to_dict()

    # 保存配置
    config_file = output_dir / "reward_config.json"
    with open(config_file, "w") as f:
      json.dump(config_dict, f, indent=2)

    return config_file

  def run_experiment(
    self,
    exp_name: str,
    num_envs: int = 1024,
    max_iterations: int = 1000,
    save_interval: int = 100,
    video: bool = True,
    video_interval: int = 200,
    video_length: int = 200,
    resume: bool = False,
  ):
    """运行单个实验"""
    print(f"\n{'=' * 80}")
    print(f"运行实验: {exp_name}")
    print(f"{'=' * 80}\n")

    # 创建实验目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    exp_dir = self.base_dir / f"{exp_name}_{timestamp}"
    exp_dir.mkdir(parents=True, exist_ok=True)

    # 创建配置文件
    config_file = self.create_experiment_config(exp_name, exp_dir)
    print(f"配置文件: {config_file}")

    # 构建训练命令
    cmd = [
      "MUJOCO_GL=egl",
      "uv",
      "run",
      "train",
      "Mjlab-Velocity-Flat-Unitree-Go2",
      f"--env.scene.num-envs={num_envs}",
      f"--agent.max-iterations={max_iterations}",
      f"--agent.save-interval={save_interval}",
      f"--video={str(video)}",
      f"--video-interval={video_interval}",
      f"--video-length={video_length}",
      f"--log-root={exp_dir}",
    ]

    if resume:
      # 查找最新的检查点
      checkpoints = list(exp_dir.glob("*.pt"))
      if checkpoints:
        latest_checkpoint = max(checkpoints, key=lambda p: p.stat().st_mtime)
        cmd.append(f"--resume={latest_checkpoint}")
        print(f"从检查点恢复: {latest_checkpoint}")

    # 添加自定义奖励权重
    config = get_experiment_config(exp_name)
    cmd.extend(
      [
        f"--env.rewards.track-linear-velocity.weight={config.track_linear_velocity}",
        f"--env.rewards.track-angular-velocity.weight={config.track_angular_velocity}",
        f"--env.rewards.upright.weight={config.upright}",
        f"--env.rewards.pose.weight={config.pose}",
        f"--env.rewards.action-rate-l2.weight={config.action_rate_l2}",
        f"--env.rewards.foot-clearance.weight={config.foot_clearance}",
        f"--env.rewards.foot-swing-height.weight={config.foot_swing_height}",
        f"--env.rewards.air-time.weight={config.air_time}",
      ]
    )

    print(f"\n命令: {' '.join(cmd)}\n")

    # 运行训练
    start_time = datetime.now()
    try:
      result = subprocess.run(
        " ".join(cmd),
        shell=True,
        check=True,
        cwd=os.getcwd(),
      )
      success = True
      error_msg = None
    except subprocess.CalledProcessError as e:
      success = False
      error_msg = str(e)
      print(f"\n实验失败: {error_msg}")

    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # 记录结果
    self.results[exp_name] = {
      "timestamp": timestamp,
      "directory": str(exp_dir),
      "config": config.to_dict(),
      "success": success,
      "error": error_msg,
      "duration_seconds": duration,
      "num_envs": num_envs,
      "max_iterations": max_iterations,
    }
    self.save_results()

    print(f"\n实验完成: {exp_name}")
    print(f"耗时: {duration:.1f}秒")
    print(f"结果目录: {exp_dir}\n")

    return success

  def run_all_experiments(self, **kwargs):
    """运行所有实验"""
    print(f"\n{'=' * 80}")
    print(f"运行所有实验 (共 {len(EXPERIMENTS)} 个)")
    print(f"{'=' * 80}\n")

    results = {}
    for exp_name in EXPERIMENTS.keys():
      success = self.run_experiment(exp_name, **kwargs)
      results[exp_name] = success

    # 打印总结
    print(f"\n{'=' * 80}")
    print("实验总结")
    print(f"{'=' * 80}\n")

    for exp_name, success in results.items():
      status = "✓ 成功" if success else "✗ 失败"
      print(f"  {exp_name:20s}: {status}")

    successful = sum(results.values())
    print(f"\n总计: {successful}/{len(results)} 个实验成功")

  def analyze_results(self):
    """分析实验结果"""
    print(f"\n{'=' * 80}")
    print("实验结果分析")
    print(f"{'=' * 80}\n")

    if not self.results:
      print("没有找到实验结果")
      return

    # 打印每个实验的配置和结果
    for exp_name, result in self.results.items():
      print(f"\n{exp_name.upper()}:")
      print(f"  时间: {result['timestamp']}")
      print(f"  目录: {result['directory']}")
      print(f"  状态: {'成功' if result['success'] else '失败'}")
      print(f"  耗时: {result['duration_seconds']:.1f}秒")

      config = result["config"]
      print(f"  配置:")
      print(
        f"    (i) Velocity: lin={config['track_linear_velocity']:.1f}, ang={config['track_angular_velocity']:.1f}"
      )
      print(
        f"    (ii) Stability: upright={config['upright']:.1f}, pose={config['pose']:.1f}"
      )
      print(f"    (iii) Smoothness: jerk={config['action_rate_l2']:.2f}")
      print(
        f"    (iv) Clearance: clear={config['foot_clearance']:.1f}, swing={config['foot_swing_height']:.2f}, air={config['air_time']:.1f}"
      )

    print(f"\n{'=' * 80}")
    print("下一步:")
    print("  1. 使用 TensorBoard 查看训练曲线:")
    print(f"     tensorboard --logdir {self.base_dir}")
    print("  2. 比较视频效果:")
    print(f"     ls {self.base_dir}/*/videos/")
    print("  3. 生成对比报告:")
    print("     python analyze_reward_experiments.py")
    print(f"{'=' * 80}\n")


def main():
  parser = argparse.ArgumentParser(description="奖励函数对比实验")

  parser.add_argument(
    "--experiment", type=str, choices=list(EXPERIMENTS.keys()), help="实验名称"
  )
  parser.add_argument("--all", action="store_true", help="运行所有实验")
  parser.add_argument("--analyze", action="store_true", help="分析实验结果")
  parser.add_argument(
    "--num-envs", type=int, default=1024, help="并行环境数量 (默认: 1024)"
  )
  parser.add_argument(
    "--iterations", type=int, default=1000, help="最大迭代次数 (默认: 1000)"
  )
  parser.add_argument(
    "--save-interval", type=int, default=100, help="保存间隔 (默认: 100)"
  )
  parser.add_argument(
    "--video", type=bool, default=True, help="是否生成视频 (默认: True)"
  )
  parser.add_argument(
    "--video-interval", type=int, default=200, help="视频生成间隔 (默认: 200)"
  )
  parser.add_argument(
    "--video-length", type=int, default=200, help="视频长度 (默认: 200)"
  )
  parser.add_argument("--resume", action="store_true", help="从检查点恢复训练")
  parser.add_argument(
    "--base-dir",
    type=str,
    default="experiments/reward_comparison",
    help="实验基础目录 (默认: experiments/reward_comparison)",
  )

  args = parser.parse_args()

  runner = ExperimentRunner(base_dir=args.base_dir)

  if args.analyze:
    runner.analyze_results()
  elif args.all:
    runner.run_all_experiments(
      num_envs=args.num_envs,
      max_iterations=args.iterations,
      save_interval=args.save_interval,
      video=args.video,
      video_interval=args.video_interval,
      video_length=args.video_length,
      resume=args.resume,
    )
  elif args.experiment:
    runner.run_experiment(
      args.experiment,
      num_envs=args.num_envs,
      max_iterations=args.iterations,
      save_interval=args.save_interval,
      video=args.video,
      video_interval=args.video_interval,
      video_length=args.video_length,
      resume=args.resume,
    )
  else:
    parser.print_help()
    print("\n可用的实验:")
    for exp_name in EXPERIMENTS.keys():
      print(f"  - {exp_name}")


if __name__ == "__main__":
  main()
