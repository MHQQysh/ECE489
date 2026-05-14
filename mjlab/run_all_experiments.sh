#!/bin/bash
# 批量运行奖励函数对比实验
# 用法: bash run_all_experiments.sh

set -e  # 遇到错误立即退出

echo "========================================"
echo "奖励函数对比实验 - 批量运行"
echo "========================================"
echo ""

# 配置参数
NUM_ENVS=1024
ITERATIONS=100
SAVE_INTERVAL=100
VIDEO=True
VIDEO_INTERVAL=2000
VIDEO_LENGTH=200

# 实验列表
EXPERIMENTS=(
    "baseline"
    "high_velocity"
    "high_stability"
    "high_smoothness"
    "high_clearance"
    "balanced"
    "aggressive"
    "conservative"
)

echo "配置:"
echo "  并行环境数: $NUM_ENVS"
echo "  迭代次数: $ITERATIONS"
echo "  保存间隔: $SAVE_INTERVAL"
echo "  生成视频: $VIDEO"
echo ""
echo "实验列表 (共 ${#EXPERIMENTS[@]} 个):"
for exp in "${EXPERIMENTS[@]}"; do
    echo "  - $exp"
done
echo ""

read -p "确认开始运行? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消"
    exit 0
fi

# 记录开始时间
START_TIME=$(date +%s)

# 运行每个实验
for i in "${!EXPERIMENTS[@]}"; do
    exp="${EXPERIMENTS[$i]}"
    num=$((i + 1))
    total=${#EXPERIMENTS[@]}

    echo ""
    echo "========================================"
    echo "[$num/$total] 运行实验: $exp"
    echo "========================================"
    echo ""

    # 运行实验
    python run_reward_experiments.py \
        --experiment "$exp" \
        --num-envs "$NUM_ENVS" \
        --iterations "$ITERATIONS" \
        --save-interval "$SAVE_INTERVAL" \
        --video "$VIDEO" \
        --video-interval "$VIDEO_INTERVAL" \
        --video-length "$VIDEO_LENGTH"

    if [ $? -eq 0 ]; then
        echo ""
        echo "✓ 实验 $exp 完成"
    else
        echo ""
        echo "✗ 实验 $exp 失败"
    fi
done

# 记录结束时间
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
HOURS=$((DURATION / 3600))
MINUTES=$(((DURATION % 3600) / 60))
SECONDS=$((DURATION % 60))

echo ""
echo "========================================"
echo "所有实验完成!"
echo "========================================"
echo ""
echo "总耗时: ${HOURS}h ${MINUTES}m ${SECONDS}s"
echo ""
echo "下一步:"
echo "  1. 查看结果: python analyze_reward_experiments.py"
echo "  2. TensorBoard: tensorboard --logdir experiments/reward_comparison"
echo "  3. 查看视频: ls experiments/reward_comparison/*/videos/"
echo ""
