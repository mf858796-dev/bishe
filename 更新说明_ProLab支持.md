# 更新说明 - 支持 Tobii Pro Lab 模式

## 更新日期
2026-04-13

## 更新内容

### 1. 新增 Tobii Pro Lab 支持

现在系统支持**无需贴标记**的工作模式，利用 Tobii Pro Lab 软件完成校准。

#### 优势
- ✅ **无需在屏幕上贴 ArUco 标记**
- ✅ 使用 Tobii 官方校准流程，精度更高
- ✅ 支持多用户快速切换
- ✅ 自动处理坐标映射

### 2. 代码修改

#### `coordinate_mapper.py`
- 新增 `CoordinateMapperProLab` 类，专门处理 Pro Lab 校准后的数据
- 支持多种 gaze 数据格式：
  - 屏幕坐标 (`screen_x`, `screen_y`)
  - 归一化坐标 (`gaze2d`)
  - 3D 坐标 (`gaze3d`)
- 添加了平滑滤波功能，减少视线抖动
- 保持向后兼容，旧代码仍可正常工作

#### `glasses_manager.py`
- 改进了数据流处理，提取更多 gaze 信息
- 增加了错误处理和异常捕获
- 支持更灵活的数据格式

#### `main_window.py`
- 新增模式选择界面（单选按钮）：
  - **Tobii Pro Lab 模式**（默认，推荐）
  - **ArUco 标记模式**（需要贴标记）
- 连接时显示当前选择的模式
- 添加连接成功提示，指导用户使用 Pro Lab

### 3. 新增文档

#### `Pro_Lab使用指南.md`
完整的使用说明，包括：
- Pro Lab 安装和配置
- 校准流程详解
- 常见问题解答
- Gaze 数据格式说明

#### `更新说明_ProLab支持.md`（本文件）
技术更新 summary

---

## 如何使用

### 方式一：Tobii Pro Lab 模式（推荐）

1. **安装 Tobii Pro Lab**
   - 从 [Tobii 官网](https://www.tobii.com/pro-lab) 下载
   - 申请教育许可证（学生免费）

2. **完成校准**
   - 打开 Pro Lab
   - 创建项目并添加参与者
   - 使用 Screen Calibration 功能完成校准
   - 验证校准精度

3. **启动训练系统**
   ```bash
   cd e:\毕设
   venv\Scripts\activate
   python main_window.py
   ```

4. **连接设备**
   - 确保"Pro Lab 模式"已选中
   - 点击"连接 Tobii Glasses 3"
   - 等待连接成功提示

5. **开始训练**
   - 系统会自动接收 gaze 数据
   - 按照屏幕提示完成训练任务

### 方式二：ArUco 标记模式（备选）

如果你没有 Pro Lab，可以切换到 ArUco 模式，但需要：
1. 打印 4 个 ArUco (4x4) 标记
2. 贴在显示器四角
3. 在界面中选择"ArUco 标记模式"

---

## 技术细节

### Gaze 数据流转

```
Tobii Pro Glasses 3
       │
       ├──(通过 g3pylib)──> GlassesManager
       │                         │
       │                         ├──(原始帧 + gaze数据)──> CoordinateMapper
       │                                                       │
       │                                                       ├──(屏幕坐标 x, y)──> AttentionEvaluator
       │                                                       │                           │
       │                                                       │                           ├──> TrainingWidget
       │                                                       │                           └──> ReportGenerator
```

### 数据格式

从 Tobii 获取的原始数据：
```python
{
    'gaze2d': [0.5, 0.5],           # 归一化坐标 (0-1)
    'gaze3d': [0.0, 0.0, 600.0],    # 3D 坐标 (mm)
    'pupil_diameter': 3.5,          # 瞳孔直径 (mm)
}
```

经过 Pro Lab 校准后（如果有）：
```python
{
    'screen_x': 960,                # 屏幕 X 坐标 (像素)
    'screen_y': 540,                # 屏幕 Y 坐标 (像素)
}
```

### 平滑滤波

系统使用指数移动平均（EMA）来平滑 gaze 数据：
```
smoothed = α * current + (1 - α) * previous
```
默认 `α = 0.3`，可以根据需要调整。

---

## 注意事项

⚠️ **重要提醒**：

1. **Pro Lab 和你的系统可以同时运行**，但不能同时录制
2. **每次更换用户后必须重新校准**
3. **环境光线变化较大时建议重新校准**
4. **校准精度直接影响训练效果**，请务必仔细校准

---

## 测试建议

在没有 Tobii 硬件的情况下，你可以：

1. **模拟数据测试**：
   ```python
   from coordinate_mapper import CoordinateMapper
   mapper = CoordinateMapper()
   mapper.process_gaze_data({'gaze2d': [0.5, 0.5]})
   ```

2. **检查依赖**：
   ```bash
   python check_dependencies.py
   ```

3. **单元测试**：
   ```bash
   python simple_test.py
   ```

---

## 下一步计划

1. 实现离线数据分析功能
2. 添加更多训练任务类型
3. 优化报告生成（HTML 格式）
4. 支持多人协作训练

---

## 反馈与支持

如果遇到问题：
1. 查看 `检测报告.md` 确认环境配置
2. 阅读 `Pro_Lab使用指南.md` 了解详细用法
3. 联系 Tobii 技术支持：support@tobii.com
4. 咨询你的毕业设计指导教师

---

**祝你的毕业设计顺利完成！** 🎓
