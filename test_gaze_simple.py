import asyncio
import sys
from g3pylib import connect_to_glasses

async def test_gaze_connection():
    """测试眼动仪连接并接收数据"""
    
    print("=" * 80)
    print("Tobii Pro Glasses 3 数据接收测试")
    print("=" * 80)
    
    # 尝试不同的连接方式
    connection_methods = [
        ("固定IP (192.168.75.51)", lambda: connect_to_glasses.with_hostname("192.168.75.51", using_zeroconf=False)),
        ("mDNS (TG03B-*.local)", None),  # 需要具体序列号
        ("Zeroconf 自动发现", lambda: connect_to_glasses.with_zeroconf()),
    ]
    
    glasses = None
    
    for method_name, connect_func in connection_methods:
        if connect_func is None:
            print(f"\n跳过: {method_name} (需要提供序列号)")
            continue
            
        print(f"\n尝试连接: {method_name}")
        print("-" * 80)
        
        try:
            glasses = await connect_func()
            print(f"成功连接到设备!")
            
            # 获取设备信息
            serial = await glasses.system.get_recording_unit_serial()
            version = await glasses.system.get_version()
            battery = await glasses.system.battery.get_level()
            
            print(f"  序列号: {serial}")
            print(f"  固件版本: {version}")
            print(f"  电池电量: {battery * 100:.1f}%")
            break
            
        except Exception as e:
            print(f"  失败: {type(e).__name__}: {str(e)[:100]}")
            continue
    
    if glasses is None:
        print("\n" + "=" * 80)
        print("所有连接方式都失败了!")
        print("=" * 80)
        print("\n请检查:")
        print("  1. 眼镜是否已开机")
        print("  2. USB 线是否正确连接")
        print("  3. 是否安装了 Tobii USB 驱动")
        print("  4. 防火墙是否阻止了连接")
        print("\n建议:")
        print("  - 打开设备管理器,检查是否有 Tobii 设备")
        print("  - 尝试 ping 192.168.75.51 看是否能通")
        return False
    
    # 接收 gaze 数据
    print("\n" + "=" * 80)
    print("开始接收 Gaze 数据 (按 Ctrl+C 停止)")
    print("=" * 80)
    
    count = 0
    max_samples = 5
    
    try:
        async with glasses.stream_rtsp(scene_camera=False, gaze=True) as streams:
            async with streams.gaze.decode() as gaze_stream:
                while count < max_samples:
                    try:
                        gaze_data, timestamp = await gaze_stream.get()
                        
                        if timestamp is None or gaze_data is None:
                            continue
                        
                        count += 1
                        print(f"\n[样本 {count}] 时间戳: {timestamp:.6f}s")
                        print("-" * 80)
                        
                        # 显示数据结构
                        if isinstance(gaze_data, dict):
                            for key, value in gaze_data.items():
                                if key == 'gaze2d' and isinstance(value, (list, tuple)):
                                    print(f"  gaze2d: [{value[0]:.4f}, {value[1]:.4f}]")
                                    print(f"    -> 屏幕坐标: [{int(value[0]*1920)}, {int(value[1]*1080)}]")
                                elif key == 'gaze3d' and isinstance(value, (list, tuple)):
                                    print(f"  gaze3d: [{value[0]:.2f}, {value[1]:.2f}, {value[2]:.2f}] mm")
                                elif key == 'pupildiameter':
                                    print(f"  pupildiameter: {value:.2f} mm")
                                elif isinstance(value, dict):
                                    print(f"  {key}:")
                                    for sub_key, sub_value in value.items():
                                        if isinstance(sub_value, float):
                                            print(f"    {sub_key}: {sub_value:.4f}")
                                        elif isinstance(sub_value, (list, tuple)):
                                            print(f"    {sub_key}: {sub_value}")
                                        else:
                                            print(f"    {sub_key}: {sub_value}")
                                else:
                                    print(f"  {key}: {value}")
                        
                        print("-" * 80)
                        
                    except Exception as e:
                        print(f"接收错误: {e}")
                        import traceback
                        traceback.print_exc()
                        break
        
        print(f"\n共接收 {count} 个样本")
        
    except Exception as e:
        print(f"\n流错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await glasses.close()
        print("\n连接已关闭")
    
    return count > 0

if __name__ == "__main__":
    try:
        result = asyncio.run(test_gaze_connection())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(0)
