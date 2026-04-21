"""
Tobii Pro Glasses 3 连接测试脚本
用于验证眼动仪是否能正常连接和获取数据
"""
import asyncio
from g3pylib import connect_to_glasses

async def test_connection():
    """测试连接到Glasses 3"""
    print("=" * 60)
    print("Tobii Pro Glasses 3 连接测试")
    print("=" * 60)
    
    try:
        # 尝试自动发现设备
        print("\n[1/4] 正在搜索设备...")
        glasses = await connect_to_glasses.with_zeroconf()
        
        if not glasses:
            print("❌ 未找到设备")
            return False
        
        print("✅ 设备发现成功")
        
        # 获取设备信息
        print("\n[2/4] 获取设备信息...")
        serial = await glasses.system.get_recording_unit_serial()
        version = await glasses.system.get_version()
        battery = await glasses.system.battery.get_level()
        
        print(f"✅ 序列号: {serial}")
        print(f"✅ 固件版本: {version}")
        print(f"✅ 电池电量: {battery}%")
        
        # 测试RTSP流
        print("\n[3/4] 测试视频流...")
        async with glasses.stream_rtsp(scene_camera=True, gaze=True) as streams:
            print("✅ RTSP流连接成功")
            
            # 获取几帧数据
            print("\n[4/4] 获取样例数据...")
            async with streams.scene_camera.decode() as scene_stream, \
                       streams.gaze.decode() as gaze_stream:
                
                for i in range(5):
                    frame, frame_ts = await scene_stream.get()
                    gaze, gaze_ts = await gaze_stream.get()
                    
                    print(f"\n样本 {i+1}:")
                    print(f"  帧时间戳: {frame_ts}")
                    print(f"  Gaze时间戳: {gaze_ts}")
                    
                    if gaze and 'gaze2d' in gaze:
                        u, v = gaze['gaze2d']
                        print(f"  Gaze2D坐标: u={u:.4f}, v={v:.4f}")
                    else:
                        print(f"  Gaze2D坐标: 无数据")
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！设备工作正常。")
        print("=" * 60)
        return True
        
    except asyncio.TimeoutError:
        print("\n❌ 连接超时")
        print("\n可能的原因：")
        print("  1. 眼镜未开机")
        print("  2. WiFi未正确连接")
        print("  3. 防火墙阻止了连接")
        return False
        
    except Exception as e:
        print(f"\n❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("\n请确保：")
    print("  ✓ Tobii Pro Glasses 3 已开机")
    print("  ✓ 电脑已连接到眼镜的WiFi或通过USB连接")
    print("  ✓ 眼镜已完成校准\n")
    
    input("按回车键开始测试...")
    
    # 运行异步测试
    result = asyncio.run(test_connection())
    
    if result:
        print("\n🎉 您可以开始在程序中使用眼动仪了！")
    else:
        print("\n⚠️  请检查上述问题后重试")
    
    input("\n按回车键退出...")

if __name__ == "__main__":
    main()
