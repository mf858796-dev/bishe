import asyncio
import sys
from g3pylib import connect_to_glasses

async def receive_gaze_data():
    """接收并显示 Tobii Pro Glasses 3 的 gaze 数据格式"""
    
    print("=" * 80)
    print("Tobii Pro Glasses 3 Gaze 数据格式测试")
    print("=" * 80)
    
    try:
        # 连接设备
        print("\n正在连接到设备 (192.168.75.51)...")
        glasses = await connect_to_glasses.with_hostname(
            "192.168.75.51", 
            using_zeroconf=False
        )
        
        print("✓ 连接成功!")
        
        # 获取设备信息
        serial = await glasses.system.get_recording_unit_serial()
        version = await glasses.system.get_version()
        print(f"  序列号: {serial}")
        print(f"  固件版本: {version}")
        
        # 使用 RTSP 流接收 gaze 数据
        print("\n正在启动 RTSP 流...")
        print("按 Ctrl+C 停止接收\n")
        
        count = 0
        max_samples = 10  # 只接收前10个样本
        
        async with glasses.stream_rtsp(scene_camera=False, gaze=True) as streams:
            async with streams.gaze.decode() as gaze_stream:
                print("-" * 80)
                
                while count < max_samples:
                    try:
                        # 接收 gaze 数据
                        gaze_data, timestamp = await gaze_stream.get()
                        
                        if timestamp is None:
                            continue
                        
                        count += 1
                        print(f"\n[样本 {count}] 时间戳: {timestamp:.6f} 秒")
                        print("-" * 80)
                        
                        # 显示完整的数据结构
                        print(f"数据类型: {type(gaze_data)}")
                        print(f"数据内容:")
                        
                        if isinstance(gaze_data, dict):
                            for key, value in gaze_data.items():
                                print(f"  ├─ {key}:")
                                
                                if isinstance(value, dict):
                                    for sub_key, sub_value in value.items():
                                        if isinstance(sub_value, (list, tuple)):
                                            if len(sub_value) <= 3:
                                                print(f"  │  └─ {sub_key}: {sub_value}")
                                            else:
                                                print(f"  │  └─ {sub_key}: [{len(sub_value)} 个元素]")
                                        else:
                                            print(f"  │  └─ {sub_key}: {sub_value}")
                                elif isinstance(value, (list, tuple)):
                                    print(f"  │  └─ {value}")
                                else:
                                    print(f"  │  └─ {value}")
                        
                        # 特别标注常用字段
                        if 'gaze2d' in gaze_data:
                            print(f"\n  ★ gaze2d (归一化坐标): {gaze_data['gaze2d']}")
                            print(f"    - 格式: [x, y], 范围: [0.0-1.0, 0.0-1.0]")
                            print(f"    - (0,0) = 左上角, (1,1) = 右下角")
                        
                        if 'gaze3d' in gaze_data:
                            print(f"\n  ★ gaze3d (3D 坐标): {gaze_data['gaze3d']}")
                            print(f"    - 单位: 毫米 (mm)")
                            print(f"    - 坐标系: X向左, Y向上, Z向前")
                        
                        if 'pupildiameter' in gaze_data:
                            print(f"\n  ★ 瞳孔直径: {gaze_data['pupildiameter']} mm")
                        
                        print("-" * 80)
                        
                    except Exception as e:
                        print(f"接收错误: {e}")
                        import traceback
                        traceback.print_exc()
                        break
        
        print(f"\n共接收 {count} 个 gaze 数据样本")
        await glasses.close()
        
    except asyncio.TimeoutError:
        print("✗ 连接超时,请检查:")
        print("  1. 眼镜是否已开机")
        print("  2. USB 连接是否正常")
        print("  3. IP 地址是否正确 (192.168.75.51)")
    except Exception as e:
        print(f"✗ 错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(receive_gaze_data())
