# 🎥 CPG 可视化演示说明

## ✅ 如何查看 MuJoCo 仿真图像

### 方法 1：带可视化的演示（推荐）

```bash
uv run python src/mjlab/scripts/demo_cpg_viewer.py
```

**这会打开 MuJoCo 可视化窗口，你可以看到机器人走路！**

### 窗口控制

- **空格键**: 暂停/继续
- **Esc**: 退出
- **鼠标拖动**: 旋转视角
- **鼠标滚轮**: 缩放
- **右键拖动**: 平移视角

### 方法 2：无可视化演示（仅数据）

```bash
uv run python src/mjlab/scripts/demo_cpg_simple.py
```

**这个不会打开窗口，只显示数据（位置、速度）**

## 🎬 你应该看到什么

### MuJoCo 窗口中：

1. **Go2 机器人** - 四足机器人模型
2. **地面** - 平坦的地板
3. **腿部运动** - 周期性摆动
   - 前右腿 + 后左腿 一起动（对角步态）
   - 前左腿 + 后右腿 一起动
4. **前进运动** - 机器人缓慢向前移动

### 运动特征：

- **速度**: 约 0.13 m/s（比较慢）
- **步态**: Trot（小跑步态）
- **稳定性**: 在平地上不会摔倒
- **控制**: 完全开环，不看传感器

## 🔧 如果看不到窗口

### 检查 1：确认程序在运行

```bash
ps aux | grep demo_cpg_viewer
```

如果看到进程，说明程序在运行。

### 检查 2：确认显示器可用

```bash
echo $DISPLAY
```

应该输出 `:0` 或类似的值。

### 检查 3：尝试其他可视化方式

```bash
# 使用 play 脚本（如果有训练好的模型）
uv run play Mjlab-Velocity-Flat-Unitree-Go2 \
  --checkpoint YOUR_CHECKPOINT.pt \
  --viewer native
```

## 📊 对比：有/无可视化

| 脚本 | 可视化 | 用途 |
|------|--------|------|
| `demo_cpg_viewer.py` | ✅ 有 | 看机器人走路 |
| `demo_cpg_simple.py` | ❌ 无 | 快速验证功能 |
| `evaluate_controller.py` | ❌ 无 | 性能评估 |

## 🎯 演示视频（如果需要录制）

### 录制视频

```bash
# 使用 play 脚本录制
uv run play Mjlab-Velocity-Flat-Unitree-Go2 \
  --agent zero \
  --video \
  --video-length 500
```

视频会保存在 `logs/` 目录下。

## 💡 调整可视化

### 改变步态

编辑 `demo_cpg_viewer.py`：

```python
controller = CPGController(
    gait="walk",  # 改为 walk 或 pace
    frequency=2.0,
)
```

### 改变速度

```python
controller = CPGController(
    gait="trot",
    frequency=3.0,  # 增加频率 = 更快
)
```

### 改变视角

在 MuJoCo 窗口中：
- 鼠标拖动旋转
- 滚轮缩放
- 右键平移

## 🎉 成功标志

如果你看到：
- ✅ MuJoCo 窗口打开
- ✅ Go2 机器人模型
- ✅ 腿部周期性摆动
- ✅ 机器人向前移动

**恭喜！CPG 可视化成功！**

## 📝 常见问题

### Q: 窗口一闪而过？

**A**: 可能是程序出错。查看终端输出：
```bash
uv run python src/mjlab/scripts/demo_cpg_viewer.py
```

### Q: 机器人不动？

**A**: 检查 CPG 参数，可能频率太低或幅度太小。

### Q: 机器人摔倒？

**A**: 正常现象！CPG 是开环控制，在复杂地形容易摔倒。
可以尝试：
- 降低频率
- 改用 walk 步态
- 只在平地测试

### Q: 想看 RL 策略的可视化？

**A**: 训练完成后运行：
```bash
uv run play Mjlab-Velocity-Flat-Unitree-Go2 \
  --checkpoint logs/rsl_rl/YOUR_CHECKPOINT.pt \
  --viewer native
```

## 🚀 下一步

1. ✅ 看到 CPG 可视化
2. ⏭️ 评估 CPG 性能
3. ⏭️ 训练 RL 策略
4. ⏭️ 对比 RL vs CPG
5. ⏭️ 撰写论文

---

**享受观看机器人走路！** 🤖
