# 添加复杂地形（斜坡）指南

## 1. 已创建的地形文件

**文件位置：** `robot/go2/go2_slope.xml`

这个文件包含了一个有坡度的复杂地形。

---

## 2. 地形设计

### 2.1 地形布局

```
起点 → 平地1 → 上坡 → 平台 → 下坡 → 平地2 → 终点
(0m)   (2m)   (4m)   (6m)   (8m)   (10m)
```

### 2.2 各段详情

| 段落 | 位置 (X) | 类型 | 参数 |
|------|---------|------|------|
| **平地1** | 0-2m | 平地 | 高度 0m |
| **上坡** | 2-4m | 斜坡 | 10° 上坡 |
| **平台** | 4-6m | 平地 | 高度 0.3m |
| **下坡** | 6-8m | 斜坡 | 10° 下坡 |
| **平地2** | 8-10m | 平地 | 高度 0m |

### 2.3 额外障碍物

- **台阶1**: 位于 (3.0, 0.8) - 平台上的小台阶
- **台阶2**: 位于 (5.0, -0.8) - 平台上的小台阶

---

## 3. 使用方法

### 3.1 方法1: 修改现有脚本

在 `scripts/mujoco_go2.py` 中修改 XML 路径：

```python
# 原来
mujoco_xml_path = os.path.join(cur_path, '../robot/go2/go2.xml')

# 改为
mujoco_xml_path = os.path.join(cur_path, '../robot/go2/go2_slope.xml')
```

### 3.2 方法2: 创建新脚本

复制 `mujoco_go2.py` 为 `mujoco_go2_slope.py`：

```bash
cp scripts/mujoco_go2.py scripts/mujoco_go2_slope.py
```

然后修改 XML 路径。

### 3.3 运行

```bash
cd /home/y/ece489/lab4/pympc-quadruped
uv run python scripts/mujoco_go2_slope.py
```

---

## 4. 调整地形参数

### 4.1 修改坡度

在 `go2_slope.xml` 中修改 `euler` 参数：

```xml
<!-- 当前: 10度 (0.1745 rad) -->
<geom name="slope_up" euler="0.1745 0 0" .../>

<!-- 改为 15度 (0.2618 rad) -->
<geom name="slope_up" euler="0.2618 0 0" .../>

<!-- 改为 20度 (0.3491 rad) -->
<geom name="slope_up" euler="0.3491 0 0" .../>
```

**角度转弧度：**
```
弧度 = 角度 × π / 180
10° = 0.1745 rad
15° = 0.2618 rad
20° = 0.3491 rad
30° = 0.5236 rad
```

### 4.2 修改斜坡长度

修改 `size` 和 `pos` 参数：

```xml
<!-- 当前: 2m 长 -->
<geom name="slope_up" type="box" size="1.0 2.0 0.05" pos="2.0 0 0.125" .../>

<!-- 改为 3m 长 -->
<geom name="slope_up" type="box" size="1.5 2.0 0.05" pos="2.5 0 0.188" .../>
```

### 4.3 添加更多障碍物

```xml
<!-- 添加石头 -->
<geom name="rock1" type="sphere" size="0.1" pos="3.5 0.5 0.4" rgba="0.6 0.6 0.6 1" condim="3"/>

<!-- 添加台阶 -->
<geom name="step3" type="box" size="0.5 1.0 0.1" pos="7.0 0 0.1" rgba="0.5 0.5 0.5 1" condim="3"/>
```

---

## 5. 更复杂的地形选项

### 5.1 高度图地形 (Heightfield)

使用高度图可以创建更复杂的地形：

```xml
<asset>
  <hfield name="terrain" nrow="100" ncol="100" size="10 10 1 0.1"/>
</asset>

<worldbody>
  <geom type="hfield" hfield="terrain" rgba="0.7 0.7 0.7 1"/>
</worldbody>
```

### 5.2 随机地形

可以用 Python 生成随机高度图：

```python
import numpy as np

# 生成随机地形
nrow, ncol = 100, 100
terrain = np.random.randn(nrow, ncol) * 0.05  # 随机高度
terrain = np.clip(terrain, -0.2, 0.2)  # 限制高度范围

# 保存为文件
np.save('terrain.npy', terrain)
```

### 5.3 楼梯地形

```xml
<!-- 楼梯 -->
<geom name="stair1" type="box" size="0.5 1.0 0.05" pos="2.0 0 0.05" rgba="0.7 0.7 0.7 1" condim="3"/>
<geom name="stair2" type="box" size="0.5 1.0 0.05" pos="2.5 0 0.15" rgba="0.7 0.7 0.7 1" condim="3"/>
<geom name="stair3" type="box" size="0.5 1.0 0.05" pos="3.0 0 0.25" rgba="0.7 0.7 0.7 1" condim="3"/>
<geom name="stair4" type="box" size="0.5 1.0 0.05" pos="3.5 0 0.35" rgba="0.7 0.7 0.7 1" condim="3"/>
```

---

## 6. 实验建议

### 6.1 测试场景

| 场景 | 地形 | 坡度 | 难度 |
|------|------|------|------|
| **简单** | 平地 | 0° | ⭐ |
| **中等** | 缓坡 | 10° | ⭐⭐ |
| **困难** | 陡坡 | 20° | ⭐⭐⭐ |
| **极难** | 陡坡+障碍 | 30° | ⭐⭐⭐⭐ |

### 6.2 评估指标

在斜坡上测试时，额外关注：

1. **爬坡能力**: 能否成功爬上斜坡
2. **下坡稳定性**: 下坡时是否稳定
3. **足部滑动**: 是否有足部打滑
4. **能量消耗**: 爬坡时的能量消耗

### 6.3 对比 MPC vs CPG

**预期结果：**

| 指标 | MPC (斜坡) | CPG (斜坡) |
|------|-----------|-----------|
| **成功率** | 高 | 低 |
| **稳定性** | 好 | 差 |
| **适应性** | 强 | 弱 |

**原因：**
- MPC 使用反馈，能适应地形变化
- CPG 是开环，无法适应斜坡

---

## 7. 可视化地形

### 7.1 在 MuJoCo Viewer 中查看

```bash
# 直接查看地形
python -c "import mujoco; import mujoco.viewer; \
model = mujoco.MjModel.from_xml_path('robot/go2/go2_slope.xml'); \
data = mujoco.MjData(model); \
mujoco.viewer.launch(model, data)"
```

### 7.2 调整相机视角

在脚本中添加：

```python
# 设置相机跟随机器人
viewer.cam.lookat[:] = data.qpos[:3]  # 看向机器人
viewer.cam.distance = 3.0  # 距离
viewer.cam.elevation = -20  # 俯视角度
```

---

## 8. 故障排除

### 8.1 机器人穿透地形

**原因：** 碰撞检测问题

**解决：**
```xml
<!-- 确保地形有 condim -->
<geom name="slope_up" condim="3" .../>
```

### 8.2 机器人在斜坡上滑动

**原因：** 摩擦系数太低

**解决：**
```xml
<!-- 增加摩擦 -->
<geom name="slope_up" friction="0.8 0.1 0.1" .../>
```

### 8.3 机器人无法爬坡

**原因：** 坡度太陡或控制器不适应

**解决：**
1. 降低坡度 (10° → 5°)
2. 调整 MPC 参数
3. 增加足部摩擦

---

## 9. 下一步

1. **测试基本斜坡**
   ```bash
   uv run python scripts/mujoco_go2_slope.py
   ```

2. **调整坡度**
   - 从 5° 开始
   - 逐步增加到 10°, 15°, 20°

3. **记录数据**
   - 成功率
   - 稳定性
   - 能量消耗

4. **对比 MPC vs CPG**
   - 在相同地形上测试
   - 记录所有指标

需要我创建测试脚本吗？
