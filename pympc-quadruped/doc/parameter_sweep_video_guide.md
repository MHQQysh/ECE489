# Go2 参数扫描 - 视频网格版本

## 功能

自动测试不同的 Kp 和 Kd 组合，为每个测试录制视频，生成一个 **HTML 网页**，包含所有视频的网格布局（类似 MATLAB 的 subplot）。

## 安装依赖

```bash
# 安装视频录制库
uv pip install mediapy
```

## 快速开始

### 基本用法（3x3 网格，推荐）

```bash
uv run python scripts/parameter_sweep_video.py
```

这会生成 9 个视频（约 5-10 分钟）。

### 自定义参数

```bash
# 4x4 网格
uv run python scripts/parameter_sweep_video.py \
    --kp-min 80 --kp-max 180 --kp-steps 4 \
    --kd-min 10 --kd-max 20 --kd-steps 4

# 快速测试（2x2 网格，短视频）
uv run python scripts/parameter_sweep_video.py \
    --kp-min 100 --kp-max 150 --kp-steps 2 \
    --kd-min 12 --kd-max 18 --kd-steps 2 \
    --sim-steps 1000

# 高质量视频
uv run python scripts/parameter_sweep_video.py \
    --video-width 1280 --video-height 720 --fps 60
```

## 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--kp-min` | 80 | Kp 最小值 |
| `--kp-max` | 180 | Kp 最大值 |
| `--kp-steps` | 3 | Kp 测试点数量 |
| `--kd-min` | 10 | Kd 最小值 |
| `--kd-max` | 20 | Kd 最大值 |
| `--kd-steps` | 3 | Kd 测试点数量 |
| `--sim-steps` | 2000 | 仿真步数（约 2 秒） |
| `--fps` | 30 | 视频帧率 |
| `--video-width` | 640 | 视频宽度 |
| `--video-height` | 480 | 视频高度 |
| `--output-dir` | parameter_sweep_videos | 输出目录 |

## 输出结果

运行后会在 `parameter_sweep_videos/` 目录下生成：

```
parameter_sweep_videos/
├── index.html              # 主页面（在浏览器中打开）
├── kp80_kd10.mp4          # 每个测试的视频
├── kp80_kd15.mp4
├── kp80_kd20.mp4
├── kp130_kd10.mp4
├── ...
├── kp80_kd10.log          # 每个测试的日志
├── kp80_kd15.log
└── results_summary.json    # 结果汇总
```

## 查看结果

### 方法 1: 直接打开 HTML（推荐）

```bash
# Linux
xdg-open parameter_sweep_videos/index.html

# macOS
open parameter_sweep_videos/index.html

# Windows
start parameter_sweep_videos/index.html

# 或者手动在浏览器中打开
firefox parameter_sweep_videos/index.html
```

### 方法 2: 使用本地服务器

```bash
cd parameter_sweep_videos
python -m http.server 8000

# 然后在浏览器中打开
# http://localhost:8000
```

## HTML 页面功能

打开 `index.html` 后，你会看到：

1. **视频网格**: 所有参数组合的视频排列成网格
2. **控制按钮**:
   - ▶ Play All - 同时播放所有视频
   - ⏸ Pause All - 暂停所有视频
   - ⟲ Restart All - 重新播放所有视频
3. **每个格子显示**:
   - Kp 和 Kd 值
   - 视频播放器（可独立控制）
   - 运行时间
   - 成功/失败状态

## 示例

### 快速测试（2x2 网格）

```bash
uv run python scripts/parameter_sweep_video.py \
    --kp-min 100 --kp-max 150 --kp-steps 2 \
    --kd-min 12 --kd-max 18 --kd-steps 2 \
    --sim-steps 1000
```

**预计时间**: 约 3-5 分钟（4 个视频）

**结果**: 
```
┌─────────────┬─────────────┐
│ Kp=100      │ Kp=100      │
│ Kd=12       │ Kd=18       │
│ [视频]      │ [视频]      │
├─────────────┼─────────────┤
│ Kp=150      │ Kp=150      │
│ Kd=12       │ Kd=18       │
│ [视频]      │ [视频]      │
└─────────────┴─────────────┘
```

### 标准测试（3x3 网格）

```bash
uv run python scripts/parameter_sweep_video.py
```

**预计时间**: 约 10-15 分钟（9 个视频）

### 详细测试（4x4 网格）

```bash
uv run python scripts/parameter_sweep_video.py \
    --kp-min 80 --kp-max 180 --kp-steps 4 \
    --kd-min 10 --kd-max 20 --kd-steps 4 \
    --sim-steps 3000
```

**预计时间**: 约 30-40 分钟（16 个视频）

## 视频质量设置

### 标准质量（默认）
```bash
--video-width 640 --video-height 480 --fps 30
```
- 文件大小: 约 2-5 MB/视频
- 适合快速预览

### 高质量
```bash
--video-width 1280 --video-height 720 --fps 60
```
- 文件大小: 约 10-20 MB/视频
- 适合详细分析

### 低质量（快速测试）
```bash
--video-width 320 --video-height 240 --fps 15
```
- 文件大小: 约 0.5-1 MB/视频
- 适合大规模扫描

## 如何选择最佳参数

1. **打开 HTML 页面**
2. **点击 "Play All"** 同时观看所有视频
3. **观察哪些参数组合**:
   - 机器人稳定行走
   - 没有摔倒
   - 行走距离最远
   - 步态平滑
4. **记录最佳参数**
5. **在该区域进行精细扫描**

## 故障排除

### 问题：ImportError: No module named 'mediapy'

**解决方法**:
```bash
uv pip install mediapy
```

### 问题：视频文件很大

**解决方法**: 降低分辨率或帧率
```bash
--video-width 480 --video-height 360 --fps 20
```

### 问题：某些视频录制失败

**原因**: 仿真崩溃或超时

**解决方法**: 查看对应的 `.log` 文件了解详情

### 问题：HTML 页面视频无法播放

**原因**: 浏览器安全限制

**解决方法**: 使用本地服务器
```bash
cd parameter_sweep_videos
python -m http.server 8000
# 打开 http://localhost:8000
```

## 高级用法

### 只测试特定区域

如果你发现 Kp=120, Kd=15 附近效果好：

```bash
uv run python scripts/parameter_sweep_video.py \
    --kp-min 110 --kp-max 130 --kp-steps 5 \
    --kd-min 13 --kd-max 17 --kd-steps 5
```

### 对比不同仿真时长

```bash
# 短时间（1秒）
uv run python scripts/parameter_sweep_video.py --sim-steps 1000 --output-dir sweep_1s

# 中等时间（2秒）
uv run python scripts/parameter_sweep_video.py --sim-steps 2000 --output-dir sweep_2s

# 长时间（5秒）
uv run python scripts/parameter_sweep_video.py --sim-steps 5000 --output-dir sweep_5s
```

## 注意事项

- ⏱️ 每个视频录制约 1-2 分钟
- 💾 每个视频约 2-5 MB（标准质量）
- 🔄 脚本会修改 `config/robot_configs.py`
- ⚠️ 确保有足够的磁盘空间
- 🎥 视频使用 H.264 编码，兼容所有现代浏览器

## 与原始版本的区别

| 特性 | parameter_sweep.py | parameter_sweep_video.py |
|------|-------------------|-------------------------|
| 输出 | 静态图片 | 视频网格 |
| 可视化 | PNG 热力图 | HTML 交互式页面 |
| 文件大小 | 小（几 MB） | 大（几十到几百 MB） |
| 时间 | 快 | 慢（需要录制视频） |
| 适用场景 | 快速筛选 | 详细分析 |

## 推荐工作流程

1. **粗略扫描**: 使用 `parameter_sweep.py` 快速找到大致范围
2. **视频验证**: 使用 `parameter_sweep_video.py` 在该范围内录制视频
3. **精细调整**: 根据视频选择最佳参数
4. **最终测试**: 手动测试最佳参数

---

*工具版本: 1.0*
*创建日期: 2026-05-12*
