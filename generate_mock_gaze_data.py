"""
眼动仪数据模拟器
用于在没有真实眼动仪的情况下生成模拟数据

"""

import time
import random
import json


def generate_mock_gaze_data(count=100, sampling_rate=60):
    """
    生成模拟眼动数据
    
    :param count: 生成的数据点数量
    :param sampling_rate: 采样率（Hz），默认60Hz
    :return: 包含gaze2d和timestamp的字典列表
    """
    data = []
    base_time = time.time()
    
    # 模拟阅读代码时的眼动模式
    current_u, current_v = 0.5, 0.3  # 起始位置（屏幕中央偏上）
    
    interval = 1.0 / sampling_rate  # 采样间隔（秒）
    
    for i in range(count):
        # 添加随机噪声（模拟真实眼动的微小抖动）
        noise_u = random.gauss(0, 0.005)
        noise_v = random.gauss(0, 0.005)
        
        # 偶尔进行扫视（大跳跃）- 10%概率
        if random.random() < 0.1:
            current_u += random.uniform(-0.2, 0.2)
            current_v += random.uniform(-0.15, 0.15)
        else:
            # 正常阅读时的缓慢移动
            current_u += random.uniform(0, 0.02)
            current_v += random.uniform(-0.005, 0.005)
        
        # 限制在有效范围内 [0, 1]
        current_u = max(0.0, min(1.0, current_u))
        current_v = max(0.0, min(1.0, current_v))
        
        gaze_point = {
            'gaze2d': [
                round(current_u + noise_u, 6), 
                round(current_v + noise_v, 6)
            ],
            'timestamp': round(base_time + i * interval, 6)
        }
        data.append(gaze_point)
    
    return data


def simulate_reading_behavior(duration_seconds=10, sampling_rate=60):
    """
    模拟更真实的代码阅读行为
    
    :param duration_seconds: 模拟时长（秒）
    :param sampling_rate: 采样率（Hz）
    :return: 模拟数据列表
    """
    data = []
    base_time = time.time()
    total_points = int(duration_seconds * sampling_rate)
    
    # 定义几个关键区域（模拟代码的不同部分）
    key_areas = [
        {'name': '函数定义', 'u': 0.1, 'v': 0.1},
        {'name': '循环结构', 'u': 0.3, 'v': 0.4},
        {'name': '条件判断', 'u': 0.5, 'v': 0.6},
        {'name': '变量声明', 'u': 0.2, 'v': 0.3},
        {'name': '返回语句', 'u': 0.7, 'v': 0.8},
    ]
    
    current_area_idx = 0
    fixation_duration = 0
    is_fixating = True  # True=注视，False=扫视
    
    for i in range(total_points):
        timestamp = base_time + i / sampling_rate
        
        target_area = key_areas[current_area_idx]
        
        if is_fixating:
            # 注视阶段：在目标区域附近小范围抖动
            noise_u = random.gauss(0, 0.02)
            noise_v = random.gauss(0, 0.02)
            
            u = target_area['u'] + noise_u
            v = target_area['v'] + noise_v
            
            fixation_duration += 1 / sampling_rate
            
            # 注视持续0.2-0.5秒后切换到下一个区域
            if fixation_duration > random.uniform(0.2, 0.5):
                is_fixating = False
                fixation_duration = 0
        else:
            # 扫视阶段：快速移动到下一个区域
            next_area_idx = (current_area_idx + 1) % len(key_areas)
            next_area = key_areas[next_area_idx]
            
            # 线性插值实现平滑移动
            progress = fixation_duration / 0.05  # 扫视持续约50ms
            if progress >= 1.0:
                current_area_idx = next_area_idx
                is_fixating = True
                fixation_duration = 0
                u = next_area['u']
                v = next_area['v']
            else:
                prev_area = key_areas[current_area_idx]
                u = prev_area['u'] + (next_area['u'] - prev_area['u']) * progress
                v = prev_area['v'] + (next_area['v'] - prev_area['v']) * progress
            
            fixation_duration += 1 / sampling_rate
        
        # 确保坐标在有效范围内
        u = max(0.0, min(1.0, u))
        v = max(0.0, min(1.0, v))
        
        gaze_point = {
            'gaze2d': [round(u, 6), round(v, 6)],
            'timestamp': round(timestamp, 6),
            'area': key_areas[current_area_idx]['name'] if is_fixating else 'saccade'
        }
        data.append(gaze_point)
    
    return data


def save_to_json(data, filename='mock_gaze_data.json'):
    """保存数据到JSON文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            'description': '模拟眼动仪数据',
            'data_points': len(data),
            'format': 'gaze2d: 归一化坐标 [u, v], 范围 [0, 1]',
            'timestamp': 'Unix时间戳（秒）',
            'data': data
        }, f, ensure_ascii=False, indent=2)
    print(f"✅ 已保存 {len(data)} 个数据点到 {filename}")


def print_sample_data(data, num_samples=10):
    """打印示例数据"""
    print("\n" + "="*80)
    print("眼动数据格式说明")
    print("="*80)
    print(f"\n总数据点数: {len(data)}")
    print(f"数据格式: {{'gaze2d': [u, v], 'timestamp': t}}")
    print(f"gaze2d范围: [0.0, 1.0] x [0.0, 1.0]（归一化坐标）")
    print(f"转换为屏幕坐标: screen_x = u * 1920, screen_y = v * 1080")
    print("\n" + "-"*80)
    print("前10个数据点示例:")
    print("-"*80)
    
    for i, point in enumerate(data[:num_samples]):
        u, v = point['gaze2d']
        screen_x = int(u * 1920)
        screen_y = int(v * 1080)
        print(f"点 {i+1:3d}: gaze2d=[{u:.6f}, {v:.6f}] | "
              f"屏幕坐标=({screen_x:4d}, {screen_y:4d}) | "
              f"时间戳={point['timestamp']:.6f}")
    
    print("="*80)


if __name__ == '__main__':
    print("🔬 眼动仪数据模拟器")
    print("="*80)
    
    # 方式1：简单随机游走模式
    print("\n【方式1】简单随机游走模式")
    simple_data = generate_mock_gaze_data(count=100, sampling_rate=60)
    print_sample_data(simple_data)
    save_to_json(simple_data, 'mock_gaze_simple.json')
    
    # 方式2：模拟真实阅读行为
    print("\n\n【方式2】模拟代码阅读行为（更真实）")
    reading_data = simulate_reading_behavior(duration_seconds=5, sampling_rate=60)
    print_sample_data(reading_data)
    save_to_json(reading_data, 'mock_gaze_reading.json')
    
    print("\n💡 提示:")
    print("   - mock_gaze_simple.json: 简单随机数据，适合快速测试")
    print("   - mock_gaze_reading.json: 模拟真实阅读行为，包含注视和扫视")
    print("   - 可以在代码中加载这些JSON文件来模拟眼动仪数据")
    print("\n📖 使用方法:")
    print("   import json")
    print("   with open('mock_gaze_reading.json', 'r') as f:")
    print("       data = json.load(f)['data']")
    print("   for point in data:")
    print("       gaze2d = point['gaze2d']  # [u, v]")
    print("       timestamp = point['timestamp']")
    print("       # 处理数据...")
