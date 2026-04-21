import asyncio
from g3pylib import connect_to_glasses

async def test_zeroconf():
    """测试自动发现模式"""
    print("=" * 50)
    print("测试 1: 使用 Zeroconf 自动发现")
    print("=" * 50)
    try:
        print("正在搜索 Tobii Pro Glasses 3...")
        glasses = await connect_to_glasses.with_zeroconf()
        
        if glasses:
            serial = await glasses.system.get_recording_unit_serial()
            fw_version = await glasses.system.get_version()
            print(f"成功连接到设备! 序列号: {serial}")
            print(f"固件版本: {fw_version}")
            
            # 检查电池状态
            battery_level = await glasses.system.battery.get_level()
            print(f"当前电量: {battery_level * 100:.1f}%")
            
            await glasses.close()
            return True
        else:
            print("未找到设备。请确保眼镜已开启并连接到同一网络。")
            return False
    except asyncio.TimeoutError:
        print("连接超时，请确认眼镜已开机并正确连接。")
        return False
    except Exception as e:
        print(f"连接失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_ip_connection(ip_address="192.168.75.51"):
    """测试固定 IP 连接模式"""
    print("\n" + "=" * 50)
    print(f"测试 2: 使用固定 IP 连接 ({ip_address})")
    print("=" * 50)
    try:
        print(f"正在连接到 {ip_address}...")
        glasses = await connect_to_glasses.with_hostname(
            ip_address, using_zeroconf=False
        )
        
        if glasses:
            serial = await glasses.system.get_recording_unit_serial()
            fw_version = await glasses.system.get_version()
            print(f"成功连接到设备! 序列号: {serial}")
            print(f"固件版本: {fw_version}")
            
            # 检查电池状态
            battery_level = await glasses.system.battery.get_level()
            print(f"当前电量: {battery_level * 100:.1f}%")
            
            await glasses.close()
            return True
        else:
            print(f"无法连接到 {ip_address}")
            return False
    except asyncio.TimeoutError:
        print(f"连接超时，请确认 IP 地址是否正确: {ip_address}")
        return False
    except Exception as e:
        print(f"连接失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    print("\nTobii Pro Glasses 3 连接测试工具\n")
    
    # 测试 1: Zeroconf 自动发现
    result1 = await test_zeroconf()
    
    # 测试 2: 固定 IP 连接
    result2 = await test_ip_connection()
    
    # 总结
    print("\n" + "=" * 50)
    print("测试总结")
    print("=" * 50)
    if result1:
        print("Zeroconf 自动发现: 成功")
    else:
        print("Zeroconf 自动发现: 失败")
    
    if result2:
        print("固定 IP 连接: 成功")
    else:
        print("固定 IP 连接: 失败")
    
    if not result1 and not result2:
        print("\n提示:")
        print("   1. 确认眼镜已开机")
        print("   2. 检查 USB/WiFi 连接是否正常")
        print("   3. 如果使用 USB,确认 IP 地址是否为 192.168.75.51")
        print("   4. 检查防火墙是否阻止了连接")

if __name__ == "__main__":
    asyncio.run(main())
