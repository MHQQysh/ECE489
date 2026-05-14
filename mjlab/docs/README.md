# 文档索引 (Documentation Index)

本文档夹包含 mjlab 项目开发过程中积累的所有文档，按主题分类整理。

---

## 目录结构

```
docs/
├── cpg/           # CPG 控制器相关文档
├── evaluation/    # 评估与对比实验文档
├── experiments/   # 实验结果文档 (中文)
├── go2/           # Unitree Go2 机器人集成文档
├── reward_experiments/  # 奖励函数对比实验文档
├── sim2sim/       # Sim2Sim 测试与域随机化文档
├── summaries/      # 任务完成总结文档
├── FILES_CREATED.md    # 创建的文件清单
└── FIX_LOG_ROOT.md     # 修复日志
```

---

## CPG 控制器 (`cpg/`)

| 文件 | 说明 |
|------|------|
| [CPG_EXPLANATION.md](cpg/CPG_EXPLANATION.md) | CPG (Central Pattern Generator) 方法的详细解释，说明其可以直接用于仿真 |
| [CPG_QUICKSTART.md](cpg/CPG_QUICKSTART.md) | CPG 控制器的快速入门指南 |
| [CPG_MPC_STYLE_README.md](cpg/CPG_MPC_STYLE_README.md) | 具有 MPC 风格接口的 CPG 控制器说明 |
| [CPG_VELOCITY_RESPONSE.md](cpg/CPG_VELOCITY_RESPONSE.md) | CPG 如何响应目标速度的完整说明 |
| [CPG_VERIFICATION_SUCCESS.md](cpg/CPG_VERIFICATION_SUCCESS.md) | CPG 方法验证成功的记录 |
| [CPG_VISUALIZATION_GUIDE.md](cpg/CPG_VISUALIZATION_GUIDE.md) | CPG 可视化演示指南 |
| [CPG_vs_MPC_CODE_COMPARISON.md](cpg/CPG_vs_MPC_CODE_COMPARISON.md) | CPG 与 MPC 的代码对比分析 |
| [CPG_vs_MPC_vs_RL.md](cpg/CPG_vs_MPC_vs_RL.md) | CPG、MPC、RL 三种控制方法的完整对比 |

---

## 评估与对比实验 (`evaluation/`)

| 文件 | 说明 |
|------|------|
| [EVALUATION_GUIDE.md](evaluation/EVALUATION_GUIDE.md) | 控制器评估与对比指南 (英文) |
| [EVALUATION_README.md](evaluation/EVALUATION_README.md) | 实验对比系统实现说明 |
| [EVALUATION_IMPLEMENTATION_SUMMARY.md](evaluation/EVALUATION_IMPLEMENTATION_SUMMARY.md) | 实验对比系统的实现总结 |
| [QUICKSTART_EVALUATION.md](evaluation/QUICKSTART_EVALUATION.md) | 评估和对比实验的快速开始指南 |

---

## 奖励函数对比实验 (`reward_experiments/`)

| 文件 | 说明 |
|------|------|
| [README_REWARD_EXPERIMENTS.md](reward_experiments/README_REWARD_EXPERIMENTS.md) | 奖励函数对比实验的文件索引 |
| [REWARD_ANALYSIS.md](reward_experiments/REWARD_ANALYSIS.md) | Go2 速度跟踪任务的奖励函数分析 |
| [REWARD_EXPERIMENTS_GUIDE.md](reward_experiments/REWARD_EXPERIMENTS_GUIDE.md) | 奖励函数对比实验的详细指南 |
| [REWARD_EXPERIMENTS_SUMMARY.md](reward_experiments/REWARD_EXPERIMENTS_SUMMARY.md) | 奖励函数对比实验的完整总结 |
| [REWARD_EXPERIMENTS_FIXED.md](reward_experiments/REWARD_EXPERIMENTS_FIXED.md) | 奖励函数实验脚本的修复总结 |

---

## Unitree Go2 集成 (`go2/`)

| 文件 | 说明 |
|------|------|
| [README_GO2.md](go2/README_GO2.md) | Unitree Go2 集成的使用指南 |
| [GO2_CONFIG_GUIDE.md](go2/GO2_CONFIG_GUIDE.md) | Go2 自定义配置的使用指南 |
| [GO2_INTEGRATION_SUMMARY.md](go2/GO2_INTEGRATION_SUMMARY.md) | Go2 集成的总结 |
| [CONVERT_GO2_TO_MJCF.md](go2/CONVERT_GO2_TO_MJCF.md) | 如何将训练配置改成 Go2 的指南 |

---

## Sim2Sim 与域随机化 (`sim2sim/`)

| 文件 | 说明 |
|------|------|
| [SIM2SIM_README.md](sim2sim/SIM2SIM_README.md) | Sim2Sim 测试指南 |
| [DOMAIN_RANDOMIZATION_SUMMARY.md](sim2sim/DOMAIN_RANDOMIZATION_SUMMARY.md) | 域随机化实现的总结 |

---

## 任务总结 (`summaries/`)

| 文件 | 说明 |
|------|------|
| [COMPLETE_IMPLEMENTATION_SUMMARY.md](summaries/COMPLETE_IMPLEMENTATION_SUMMARY.md) | 实验对比系统的完整实现总结 |
| [FINAL_SUMMARY.md](summaries/FINAL_SUMMARY.md) | 实验系统实现的最终总结 |
| [TASK_COMPLETION_SUMMARY.md](summaries/TASK_COMPLETION_SUMMARY.md) | 各项任务的完成情况总结 |

---

## 实验结果 (`experiments/`)

| 文件 | 说明 |
|------|------|
| [README_评估.md](experiments/README_评估.md) | Go2 速度跟踪综合评估的完成总结 |
| [综合评估报告.md](experiments/综合评估报告.md) | Go2 速度跟踪任务的综合评估报告 |
| [评估完成.md](experiments/评估完成.md) | 评估任务完成记录 |
| [评估结果.md](experiments/评估结果.md) | 训练配置和评估结果 |

---

## 其他文档

| 文件 | 说明 |
|------|------|
| [FILES_CREATED.md](FILES_CREATED.md) | 本次任务创建的所有文件清单 |
| [FIX_LOG_ROOT.md](FIX_LOG_ROOT.md) | 修复日志 |

---

## 根目录核心文件

| 文件 | 说明 |
|------|------|
| [README.md](../README.md) | 项目主 README |
| [CLAUDE.md](../CLAUDE.md) | 开发工作流和编码规范 |
| [CONTRIBUTING.md](../CONTRIBUTING.md) | 贡献指南 |
| [RELEASING.md](../RELEASING.md) | 发布指南 |
| [run.md](../run.md) | 运行说明 |

---

## 项目概述

本项目 `mjlab` 是一个结合了 [Isaac Lab](https://github.com/isaac-sim/IsaacLab) 管理式 API 和 [MuJoCo Warp](https://github.com/google-deepmind/mujoco_warp) 的机器人仿真框架。

主要功能模块：
- **CPG 控制器**: 基于中枢模式生成器的腿式机器人控制器
- **MPC 控制器**: 模型预测控制实现
- **RL 训练**: 强化学习策略训练
- **Go2 集成**: Unitree Go2 四足机器人的仿真支持
- **Sim2Sim**: 仿真到仿真的迁移测试
- **域随机化**: 提高 sim-to-real 迁移的鲁棒性

---

*本文档最后更新于 2026-05-13*
