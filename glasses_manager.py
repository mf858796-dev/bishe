import asyncio
import threading
import numpy as np
import cv2
from g3pylib import Glasses3, connect_to_glasses
from PyQt5.QtCore import QObject, pyqtSignal

class GlassesManager(QObject):
    # 定义信号用于与 UI 通信
    connected = pyqtSignal(str)  # 发送序列号
    disconnected = pyqtSignal()
    error_occurred = pyqtSignal(str)
    status_update = pyqtSignal(str)
    
    # 数据流信号
    stream_data_ready = pyqtSignal(object, dict)  # (frame, gaze_data)

    def __init__(self):
        super().__init__()
        self.glasses = None
        self._loop = None
        self._thread = None
        self._streaming_task = None
        # 连接配置
        self.connection_mode = "zeroconf"  # "zeroconf" 或 "ip"
        self.device_ip = "192.168.75.51"  # 默认 IP 地址

    def start_async_loop(self):
        """启动异步事件循环线程"""
        def run_loop():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_forever()
        
        self._thread = threading.Thread(target=run_loop, daemon=True)
        self._thread.start()

    async def _find_and_connect(self):
        try:
            if self.connection_mode == "ip":
                # 使用固定 IP 连接(适用于 USB 连接)
                self.status_update.emit(f"正在连接到 {self.device_ip}...")
                try:
                    self.glasses = await connect_to_glasses.with_hostname(
                        self.device_ip, using_zeroconf=False
                    )
                except Exception as ip_error:
                    self.status_update.emit(f"IP 连接失败,尝试自动发现...")
                    # 如果 IP 连接失败,回退到 zeroconf
                    self.glasses = await connect_to_glasses.with_zeroconf()
            else:
                # 使用 Zeroconf 自动发现(适用于 WiFi 连接)
                self.status_update.emit("正在搜索 Tobii Pro Glasses 3...")
                self.glasses = await connect_to_glasses.with_zeroconf()
            
            if self.glasses:
                serial = await self.glasses.system.get_recording_unit_serial()
                fw_version = await self.glasses.system.get_version()
                self.status_update.emit(f"已连接: {serial} (FW: {fw_version})")
                self.connected.emit(serial)
                # 启动数据流订阅
                self._streaming_task = asyncio.create_task(self._start_streaming())
            else:
                self.error_occurred.emit("未找到设备，请检查网络连接。")
        except asyncio.TimeoutError:
            self.error_occurred.emit("连接超时，请确认眼镜已开机并正确连接。")
        except Exception as e:
            self.error_occurred.emit(f"连接失败: {str(e)}")

    async def _start_streaming(self):
        """订阅场景视频和 Gaze 数据"""
        try:
            self.status_update.emit("正在启动视频流...")
            print("[调试] 开始启动RTSP视频流...")
            
            # 使用 RTSP 流(正确的方式)
            async with self.glasses.stream_rtsp(scene_camera=True, gaze=True) as streams:
                self.status_update.emit("视频流已启动，正在接收数据...")
                print("[调试] RTSP连接成功，开始接收数据流")
                
                async with streams.scene_camera.decode() as scene_stream, \
                           streams.gaze.decode() as gaze_stream:
                    
                    frame_count = 0
                    while True:
                        # 获取视频帧
                        frame, frame_timestamp = await scene_stream.get()
                        # 获取 gaze 数据
                        gaze, gaze_timestamp = await gaze_stream.get()
                        
                        frame_count += 1
                        if frame_count % 100 == 0:
                            print(f"[调试] 已接收 {frame_count} 帧数据")
                        
                        # 等待时间戳对齐
                        while gaze_timestamp is None or frame_timestamp is None:
                            if frame_timestamp is None:
                                frame, frame_timestamp = await scene_stream.get()
                            if gaze_timestamp is None:
                                gaze, gaze_timestamp = await gaze_stream.get()
                        
                        # 确保 gaze 时间戳不早于帧时间戳
                        while gaze_timestamp < frame_timestamp:
                            gaze, gaze_timestamp = await gaze_stream.get()
                            while gaze_timestamp is None:
                                gaze, gaze_timestamp = await gaze_stream.get()
                        
                        # 转换帧为 numpy 数组
                        frame_array = frame.to_ndarray(format="bgr24")
                        
                        # 提取 gaze 数据
                        gaze_data = {}
                        if "gaze2d" in gaze:
                            gaze2d = gaze["gaze2d"]
                            gaze_data = {
                                'gaze2d': gaze2d,  # 归一化坐标 [x, y]
                                'timestamp': gaze_timestamp,
                            }
                        
                        # 发送原始数据和解析后的 gaze
                        self.stream_data_ready.emit(frame_array, gaze_data)
                        
        except asyncio.CancelledError:
            print("Streaming task cancelled")
        except Exception as e:
            import traceback
            error_msg = f"数据流错误: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            
            # 发送错误信号，让UI显示友好提示
            if "RTSP server failed to answer in time" in str(e):
                self.error_occurred.emit(
                    "眼动仪视频流连接超时！\n\n"
                    "可能的原因：\n"
                    "1. 眼动仪已断开连接\n"
                    "2. WiFi信号不稳定\n"
                    "3. 眼动仪已关机\n\n"
                    "请检查眼动仪状态后重新连接。"
                )
            else:
                self.error_occurred.emit(f"数据流错误: {str(e)}")

    def connect_device(self):
        """触发连接过程"""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._find_and_connect(), self._loop)

    async def _get_battery_level(self):
        if self.glasses:
            level = await self.glasses.system.battery.get_level()
            return level * 100
        return 0

    def get_battery_status(self):
        """获取电池电量"""
        if self._loop and self._loop.is_running():
            future = asyncio.run_coroutine_threadsafe(self._get_battery_level(), self._loop)
            return future.result(timeout=5)
        return -1

    def set_connection_mode(self, mode: str, ip_address: str = None):
        """设置连接模式
        
        Args:
            mode: "zeroconf" (自动发现) 或 "ip" (固定IP)
            ip_address: 当 mode 为 "ip" 时指定的 IP 地址
        """
        if mode not in ["zeroconf", "ip"]:
            raise ValueError("连接模式必须是 'zeroconf' 或 'ip'")
        
        self.connection_mode = mode
        if ip_address:
            self.device_ip = ip_address

    def close_connection(self):
        """关闭连接"""
        if self._streaming_task:
            self._streaming_task.cancel()
        if self.glasses:
            if self._loop and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(self.glasses.close(), self._loop)
            self.glasses = None
            self.disconnected.emit()
