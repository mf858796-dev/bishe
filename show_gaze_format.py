"""
Tobii Pro Glasses 3 Gaze 数据格式说明

根据 Tobii Pro Glasses 3 Developer Guide v1.6 官方文档:

## Gaze 数据字段说明

### 1. gaze2d (2D 凝视坐标)
- 格式: [x, y]
- 类型: 浮点数数组
- 范围: [0.0, 1.0] (归一化视频坐标)
- 说明: 
  - (0, 0) = 场景摄像机视频的左上角
  - (1, 1) = 场景摄像机视频的右下角
  - 例如: [0.535, 0.477] 表示在屏幕中间偏左上的位置

### 2. gaze3d (3D 凝视坐标)
- 格式: [x, y, z]
- 类型: 浮点数数组
- 单位: 毫米 (mm)
- 坐标系:
  - X: 正向向左
  - Y: 正向向上
  - Z: 正向向前(从场景摄像机出发)
- 例如: [-32.499, -4.491, 345.359]

### 3. gazeorigin (凝视原点)
- 格式: [x, y, z]
- 类型: 浮点数数组
- 单位: 毫米 (mm)
- 说明: 与 gaze3d 在同一坐标系中,表示眼睛的位置
- 分为:
  - eyeleft.gazeorigin: 左眼凝视原点
  - eyeright.gazeorigin: 右眼凝视原点

### 4. gazedirection (凝视方向)
- 格式: [x, y, z]
- 类型: 浮点数数组
- 说明: 归一化向量,从各自眼睛的凝视原点开始
- 坐标系: 与 gaze3d 相同

### 5. pupildiameter (瞳孔直径)
- 格式: 单个浮点数
- 单位: 毫米 (mm)
- 说明: 瞳孔直径测量值
- 分为:
  - eyeleft.pupildiameter: 左眼瞳孔直径
  - eyeright.pupildiameter: 右眼瞳孔直径

## 完整数据结构示例

```json
{
  "type": "gaze",
  "timestamp": 681.751,
  "data": {
    "gaze2d": [0.535, 0.477],
    "gaze3d": [-32.499, -4.491, 345.359],
    "eyeleft": {
      "gazeorigin": [30.221, -11.798, -23.935],
      "gazedirection": [-0.160, 0.0432, 0.986],
      "pupildiameter": 2.653
    },
    "eyeright": {
      "gazeorigin": [-31.116, -12.392, -21.406],
      "gazedirection": [-0.011, -0.00270, 0.9999],
      "pupildiameter": 2.374
    }
  }
}
```

## RTSP 流中的数据

通过 RTSP 接收时,gaze 数据作为数据通道(payload type 99)传输:
- 时间戳: 与视频帧时间戳同步
- 频率: 50Hz 或 100Hz (可配置)

## 在 Python 代码中的使用

```python
# 从 glasses_manager 接收数据
async with glasses.stream_rtsp(scene_camera=True, gaze=True) as streams:
    async with streams.gaze.decode() as gaze_stream:
        gaze_data, timestamp = await gaze_stream.get()
        
        # 提取 2D 坐标 (最常用)
        if 'gaze2d' in gaze_data:
            x, y = gaze_data['gaze2d']
            screen_x = x * 1920  # 转换为像素坐标
            screen_y = y * 1080
        
        # 提取 3D 坐标
        if 'gaze3d' in gaze_data:
            x_3d, y_3d, z_3d = gaze_data['gaze3d']
        
        # 提取瞳孔直径
        if 'pupildiameter' in gaze_data:
            pupil_size = gaze_data['pupildiameter']
```

## 注意事项

1. **归一化坐标**: gaze2d 是归一化的,需要乘以屏幕尺寸才能得到像素坐标
2. **时间同步**: RTSP 流中的 gaze 数据有时间戳,可以与视频帧精确同步
3. **数据频率**: 可以是 50Hz 或 100Hz,取决于设备配置
4. **有效性**: 不是所有样本都有效,需要检查数据是否存在
5. **双眼数据**: 如果只检测到一只眼睛,另一只眼睛的数据可能缺失
"""

print(__doc__)

# 创建一个模拟数据示例
print("\n" + "=" * 80)
print("模拟 Gaze 数据示例")
print("=" * 80)

sample_data = {
    'timestamp': 123.456789,
    'gaze2d': [0.535, 0.477],
    'gaze3d': [-32.499, -4.491, 345.359],
    'eyeleft': {
        'gazeorigin': [30.221, -11.798, -23.935],
        'gazedirection': [-0.160, 0.0432, 0.986],
        'pupildiameter': 2.653
    },
    'eyeright': {
        'gazeorigin': [-31.116, -12.392, -21.406],
        'gazedirection': [-0.011, -0.00270, 0.9999],
        'pupildiameter': 2.374
    }
}

import json
print(json.dumps(sample_data, indent=2, ensure_ascii=False))

print("\n" + "=" * 80)
print("坐标转换示例")
print("=" * 80)

x_norm, y_norm = sample_data['gaze2d']
screen_width = 1920
screen_height = 1080

screen_x = x_norm * screen_width
screen_y = y_norm * screen_height

print(f"归一化坐标: [{x_norm:.3f}, {y_norm:.3f}]")
print(f"屏幕坐标 (1920x1080): [{screen_x:.0f}, {screen_y:.0f}]")
print(f"3D 坐标: {sample_data['gaze3d']} mm")
print(f"左眼瞳孔直径: {sample_data['eyeleft']['pupildiameter']:.2f} mm")
print(f"右眼瞳孔直径: {sample_data['eyeright']['pupildiameter']:.2f} mm")
