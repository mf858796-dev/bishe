import asyncio
import sys
from g3pylib import connect_to_glasses

async def test_connection():
    """测试 Tobii Pro Glasses 3 连接"""
    
    print("=" * 60)
    print("Tobii Pro Glasses 3 连接诊断工具")
    print("=" * 60)
    
    # 测试 1: 固定 IP 连接 (USB 模式)
    print("\n[测试 1] 尝试通过固定 IP 连接 (192.168.75.51)...")
    try:
        print("  - 正在建立 WebSocket 连接...")
        glasses = await connect_to_glasses.with_hostname(
            "192.168.75.51", 
            using_zeroconf=False
        )
        
        print("  - WebSocket 连接成功!")
        
        # 获取设备信息
        print("  - 正在获取设备信息...")
        serial = await glasses.system.get_recording_unit_serial()
        print(f"  - 序列号: {serial}")
        
        version = await glasses.system.get_version()
        print(f"  - 固件版本: {version}")
        
        # 检查电池状态
        battery_level = await glasses.system.battery.get_level()
        print(f"  - 电池电量: {battery_level * 100:.1f}%")
        
        # 检查 SD 卡状态
        card_state = await glasses.system.storage.card_state()
        print(f"  - SD 卡状态: {card_state}")
        
        # 关闭连接
        await glasses.close()
        print("\n[结果] 固定 IP 连接: 成功")
        return True
        
    except asyncio.TimeoutError:
        print("  - 错误: 连接超时")
        print("\n[结果] 固定 IP 连接: 失败")
        print("\n可能的原因:")
        print("  1. 眼镜未开机或未连接到电脑")
        print("  2. USB 驱动未正确安装")
        print("  3. IP 地址不是 192.168.75.51")
        print("  4. 防火墙阻止了连接")
        return False
        
    except Exception as e:
        print(f"  - 错误: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        print("\n[结果] 固定 IP 连接: 失败")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_connection())
    sys.exit(0 if result else 1)
