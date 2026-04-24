import cv2
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal

class CoordinateMapper(QObject):
    # 信号：发送映射后的屏幕坐标 (x, y)
    screen_gaze_update = pyqtSignal(float, float)
    # 信号：发送调试用的视频帧（带标记框）
    debug_frame_ready = pyqtSignal(object)

    def __init__(self, screen_width=1920, screen_height=1080):
        super().__init__()
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.homography_matrix = None
        
        # 校准参数（用于修正 gaze2d 到屏幕坐标的映射）
        # 线性校准参数
        self.calibration_offset_u = 0.0  # U方向偏移
        self.calibration_offset_v = 0.0  # V方向偏移
        self.calibration_scale_u = 1.0   # U方向缩放
        self.calibration_scale_v = 1.0   # V方向缩放
        
        # 多项式校准参数（二次项）
        self.poly_coeffs_u = None  # U方向多项式系数
        self.poly_coeffs_v = None  # V方向多项式系数
        self.use_polynomial = False  # 是否使用多项式校准
        
        # 单应性矩阵（用于无Pro Lab情况下的直接映射）
        self.homography_matrix = None  # 3x3 单应性矩阵
        self.use_homography = False  # 是否使用单应性矩阵
        
        self.is_calibrated = False       # 是否已校准
        
        # 卡尔曼滤波器参数（用于平滑眼动数据）
        self.kalman_u = None  # U方向卡尔曼滤波器
        self.kalman_v = None  # V方向卡尔曼滤波器
        self.kalman_initialized = False  # 卡尔曼滤波器是否已初始化
        
        self.use_kalman_filter = True    # 是否启用卡尔曼滤波
        
        # 调试计数器
        self._debug_counter = 0
        self.debug_enabled = False
        
        # 定义 ArUco 字典 (4x4) - 兼容不同版本的 OpenCV
        try:
            # OpenCV 4.8+ 最新 API
            self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
            self.detector_params = cv2.aruco.DetectorParameters()
            self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.detector_params)
            self.use_new_api = True
        except AttributeError:
            try:
                # OpenCV 4.7 API
                self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
                self.parameters = cv2.aruco.DetectorParameters()
                self.use_new_api = False
            except AttributeError:
                # OpenCV 4.6 及更早版本
                self.aruco_dict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_4X4_50)
                self.parameters = cv2.aruco.DetectorParameters_create()
                self.use_new_api = False

        # 目标点：屏幕的四个角 (左上, 右上, 右下, 左下)
        self.dst_points = np.array([
            [0, 0],
            [screen_width, 0],
            [screen_width, screen_height],
            [0, screen_height]
        ], dtype=np.float32)

    def _log(self, message, force=False):
        """统一调试输出，避免高频路径中散落 print"""
        if force or self.debug_enabled:
            print(message)

    def _clip_to_screen(self, screen_x, screen_y):
        """裁剪屏幕坐标到有效范围"""
        clipped_x = max(0, min(self.screen_width, screen_x))
        clipped_y = max(0, min(self.screen_height, screen_y))
        return clipped_x, clipped_y

    def _init_kalman_filter(self):
        """初始化卡尔曼滤波器（优化参数，减少抖动）"""
        # 使用OpenCV的KalmanFilter
        try:
            kalman = cv2.KalmanFilter(4, 2)  # 4个状态变量，2个测量值
            
            # 状态转移矩阵: [pos, vel]
            kalman.transitionMatrix = np.array([
                [1, 0, 1, 0],
                [0, 1, 0, 1],
                [0, 0, 1, 0],
                [0, 0, 0, 1]
            ], dtype=np.float32)
            
            # 测量矩阵
            kalman.measurementMatrix = np.array([
                [1, 0, 0, 0],
                [0, 1, 0, 0]
            ], dtype=np.float32)
            
            # 过程噪声协方差（降低，表示相信模型预测）
            kalman.processNoiseCov = np.eye(4, dtype=np.float32) * 0.01
            
            # 测量噪声协方差（降低，表示相信测量数据）
            kalman.measurementNoiseCov = np.eye(2, dtype=np.float32) * 0.1
            
            # 估计误差协方差
            kalman.errorCovPost = np.eye(4, dtype=np.float32) * 0.5
            
            self._log("[卡尔曼滤波] 参数已优化：processNoise=0.01, measurementNoise=0.1")
            return kalman
        except Exception as e:
            self._log(f"[卡尔曼滤波器] 初始化失败: {e}，将使用简单平滑", force=True)
            return None
    
    def _smooth_gaze(self, u, v):
        """平滑眼动数据（卡尔曼滤波或移动平均）"""
        if not self.use_kalman_filter:
            return u, v
        
        # 初始化卡尔曼滤波器
        if self.kalman_u is None:
            self.kalman_u = self._init_kalman_filter()
            self.kalman_v = self._init_kalman_filter()
        
        if self.kalman_u is not None and self.kalman_v is not None:
            # 使用卡尔曼滤波
            measurement_u = np.array([[u], [0]], dtype=np.float32)
            measurement_v = np.array([[v], [0]], dtype=np.float32)
            
            # 预测
            self.kalman_u.predict()
            self.kalman_v.predict()
            
            # 更新
            corrected_u = self.kalman_u.correct(measurement_u)
            corrected_v = self.kalman_v.correct(measurement_v)
            
            return float(corrected_u[0, 0]), float(corrected_v[0, 0])
        else:
            # 简单指数移动平均作为备选
            if not hasattr(self, '_smooth_u'):
                self._smooth_u = u
                self._smooth_v = v
            else:
                alpha = 0.7  # 平滑系数
                self._smooth_u = alpha * u + (1 - alpha) * self._smooth_u
                self._smooth_v = alpha * v + (1 - alpha) * self._smooth_v
            
            return self._smooth_u, self._smooth_v
    
    def process_frame_and_gaze(self, frame, gaze_data):
        """
        处理单帧视频和对应的 gaze 数据（不使用ArUco标记）
        :param frame: 场景摄像头捕获的 BGR 图像
        :param gaze_data: 包含 'gaze2d' (归一化坐标 [u, v]) 的字典
        :return: 映射后的屏幕坐标 (x, y) 或 None
        """
        if frame is not None:
            # 发送调试帧给 UI
            self.debug_frame_ready.emit(frame)

        # 直接映射 Gaze 坐标（不使用 ArUco 标记）
        if gaze_data and 'gaze2d' in gaze_data:
            try:
                # gaze2d 是归一化坐标 (0-1)，应用校准参数后转换为屏幕像素坐标
                u, v = gaze_data['gaze2d']
                
                # 应用校准参数
                if self.is_calibrated:
                    if self.use_homography and self.homography_matrix is not None:
                        # 使用单应性矩阵映射（直接输出像素坐标）
                        point = np.array([[u, v]], dtype=np.float32)
                        mapped = cv2.perspectiveTransform(point.reshape(-1, 1, 2), self.homography_matrix)
                        screen_x = mapped[0, 0, 0]
                        screen_y = mapped[0, 0, 1]
                        
                        # 调试输出
                        self._debug_counter += 1
                        if self._debug_counter % 50 == 0:
                            self._log(f"[单应性映射] gaze({u:.3f}, {v:.3f}) -> screen({screen_x:.0f}, {screen_y:.0f})")
                        
                        # 检查是否在屏幕范围内
                        if 0 <= screen_x <= self.screen_width and 0 <= screen_y <= self.screen_height:
                            self.screen_gaze_update.emit(screen_x, screen_y)
                            return (screen_x, screen_y)
                        else:
                            # 坐标超出范围，裁剪到边界
                            clipped_x, clipped_y = self._clip_to_screen(screen_x, screen_y)
                            
                            if self._debug_counter % 100 == 0:
                                self._log(
                                    f"[映射警告] 单应性坐标超出范围 ({screen_x:.0f}, {screen_y:.0f})，已裁剪到 ({clipped_x:.0f}, {clipped_y:.0f})"
                                )
                            
                            self.screen_gaze_update.emit(clipped_x, clipped_y)
                            return (clipped_x, clipped_y)
                    elif self.use_polynomial and self.poly_coeffs_u is not None:
                        # 使用多项式校准（支持非线性畸变）
                        if len(self.poly_coeffs_u) == 10:
                            # 三次多项式：10个系数
                            calibrated_u = (
                                self.poly_coeffs_u[0] +
                                self.poly_coeffs_u[1] * u +
                                self.poly_coeffs_u[2] * v +
                                self.poly_coeffs_u[3] * u * u +
                                self.poly_coeffs_u[4] * u * v +
                                self.poly_coeffs_u[5] * v * v +
                                self.poly_coeffs_u[6] * u * u * u +
                                self.poly_coeffs_u[7] * u * u * v +
                                self.poly_coeffs_u[8] * u * v * v +
                                self.poly_coeffs_u[9] * v * v * v
                            )
                            calibrated_v = (
                                self.poly_coeffs_v[0] +
                                self.poly_coeffs_v[1] * u +
                                self.poly_coeffs_v[2] * v +
                                self.poly_coeffs_v[3] * u * u +
                                self.poly_coeffs_v[4] * u * v +
                                self.poly_coeffs_v[5] * v * v +
                                self.poly_coeffs_v[6] * u * u * u +
                                self.poly_coeffs_v[7] * u * u * v +
                                self.poly_coeffs_v[8] * u * v * v +
                                self.poly_coeffs_v[9] * v * v * v
                            )
                        else:
                            # 二次多项式：6个系数
                            calibrated_u = (
                                self.poly_coeffs_u[0] +
                                self.poly_coeffs_u[1] * u +
                                self.poly_coeffs_u[2] * v +
                                self.poly_coeffs_u[3] * u * u +
                                self.poly_coeffs_u[4] * u * v +
                                self.poly_coeffs_u[5] * v * v
                            )
                            calibrated_v = (
                                self.poly_coeffs_v[0] +
                                self.poly_coeffs_v[1] * u +
                                self.poly_coeffs_v[2] * v +
                                self.poly_coeffs_v[3] * u * u +
                                self.poly_coeffs_v[4] * u * v +
                                self.poly_coeffs_v[5] * v * v
                            )
                    else:
                        # 使用线性校准
                        calibrated_u = u * self.calibration_scale_u + self.calibration_offset_u
                        calibrated_v = v * self.calibration_scale_v + self.calibration_offset_v
                    
                    # 应用卡尔曼滤波平滑
                    calibrated_u, calibrated_v = self._smooth_gaze(calibrated_u, calibrated_v)
                else:
                    calibrated_u = u
                    calibrated_v = v
                
                # 转换为屏幕坐标
                if self.is_calibrated and self.use_polynomial:
                    # 已校准：使用多项式映射
                    screen_x = calibrated_u * self.screen_width
                    screen_y = calibrated_v * self.screen_height
                elif self.is_calibrated and self.use_homography:
                    # 单应性矩阵已经在上面处理并return了，这里不会执行到
                    # 但为了安全，添加一个fallback
                    screen_x = u * self.screen_width
                    screen_y = v * self.screen_height
                else:
                    # 未校准或无多项式：使用简化的透视投影模型
                    # gaze2d (u, v) 是归一化的眼球注视方向
                    # 根据实际采样数据调整参数：
                    # - 实测gaze2d U范围: 0.29-0.60 (跨度0.31)
                    # - 实测gaze2d V范围: 0.29-0.53 (跨度0.24)
                    # - 目标屏幕范围: 0.10-0.90 (跨度0.80)
                    
                    # 中心点偏移（根据实测数据调整）
                    center_u = 0.45  # 从0.5调整为0.45
                    center_v = 0.42  # 从0.5调整为0.42
                    
                    # 缩放因子（根据实测数据计算）
                    # U方向: 0.80/0.31 ≈ 2.58, V方向: 0.80/0.24 ≈ 3.33
                    scale_factor_u = 2.8  # U方向缩放
                    scale_factor_v = 3.5  # V方向缩放（笔记本屏幕V方向更敏感）
                    
                    # 计算相对于中心的偏移
                    offset_u = (u - center_u) * scale_factor_u
                    offset_v = (v - center_v) * scale_factor_v
                    
                    # 映射到屏幕坐标（中心为原点）
                    screen_x = (0.5 + offset_u) * self.screen_width
                    screen_y = (0.5 + offset_v) * self.screen_height
                
                # 调试输出：每100帧输出一次
                self._debug_counter += 1
                if self._debug_counter % 100 == 0:
                    self._log(
                        f"[映射调试] Raw({u:.3f}, {v:.3f}) -> Calib({calibrated_u:.3f}, {calibrated_v:.3f}) -> Screen({screen_x:.0f}, {screen_y:.0f}), Range: ({self.screen_width}x{self.screen_height})"
                    )
                
                # 检查是否在屏幕范围内
                if 0 <= screen_x <= self.screen_width and 0 <= screen_y <= self.screen_height:
                    self.screen_gaze_update.emit(screen_x, screen_y)
                    return (screen_x, screen_y)
                else:
                    # 坐标超出范围，裁剪到边界后仍然发送信号
                    clipped_x, clipped_y = self._clip_to_screen(screen_x, screen_y)
                    
                    if self._debug_counter % 100 == 0:
                        self._log(
                            f"[映射警告] 坐标超出范围 ({screen_x:.0f}, {screen_y:.0f})，已裁剪到 ({clipped_x:.0f}, {clipped_y:.0f})"
                        )
                    
                    self.screen_gaze_update.emit(clipped_x, clipped_y)
                    return (clipped_x, clipped_y)
            except Exception as e:
                self._log(f"Gaze mapping error: {e}", force=True)
                import traceback
                traceback.print_exc()
        
        return None

    def _calculate_homography(self, corners, ids):
        """根据检测到的标记角点计算单应性矩阵"""
        src_points = []
        # 假设标记 ID 0, 1, 2, 3 分别对应 左上, 右上, 右下, 左下
        # 实际使用时需要根据你贴标记的顺序调整
        target_ids = [0, 1, 2, 3] 
        
        for tid in target_ids:
            idx = np.where(ids == tid)[0]
            if len(idx) > 0:
                # 获取标记的中心点
                corner = corners[idx[0]][0]
                center = np.mean(corner, axis=0)
                src_points.append(center)
            else:
                return # 如果没找齐4个点，暂时不计算

        if len(src_points) == 4:
            src_points = np.array(src_points, dtype=np.float32)
            # 计算单应性矩阵
            self.homography_matrix, _ = cv2.findHomography(src_points, self.dst_points)
            self._log("Homography matrix calculated successfully.", force=True)

    def reset_mapping(self):
        """重置映射矩阵（例如当用户移动头部后）"""
        self.homography_matrix = None
    
    def set_calibration_params(self, offset_u, offset_v, scale_u=1.0, scale_v=1.0):
        """
        设置线性校准参数
        :param offset_u: U方向偏移量
        :param offset_v: V方向偏移量
        :param scale_u: U方向缩放比例
        :param scale_v: V方向缩放比例
        """
        self.calibration_offset_u = offset_u
        self.calibration_offset_v = offset_v
        self.calibration_scale_u = scale_u
        self.calibration_scale_v = scale_v
        self.is_calibrated = True
        self.use_polynomial = False  # 使用线性校准
        self._log(
            f"[校准] 参数已设置: offset_u={offset_u:.4f}, offset_v={offset_v:.4f}, "
            f"scale_u={scale_u:.4f}, scale_v={scale_v:.4f}",
            force=True
        )
    
    def set_polynomial_params(self, coeffs_u, coeffs_v, degree=2):
        """
        设置多项式校准参数（二次或三次）
        :param coeffs_u: U方向多项式系数
        :param coeffs_v: V方向多项式系数
        :param degree: 多项式次数（2或3）
        二次模型: screen = c0 + c1*u + c2*v + c3*u² + c4*u*v + c5*v²
        三次模型: screen = c0 + c1*u + c2*v + c3*u² + c4*u*v + c5*v² + c6*u³ + c7*u²*v + c8*u*v² + c9*v³
        """
        self.poly_coeffs_u = coeffs_u
        self.poly_coeffs_v = coeffs_v
        self.is_calibrated = True
        self.use_polynomial = True
        
        # 重置卡尔曼滤波器
        self.kalman_u = None
        self.kalman_v = None
        self.kalman_initialized = False
        
        self._log(f"[校准] {degree}次多项式参数已设置", force=True)
        self._log(f"  U方向系数数: {len(coeffs_u)}", force=True)
        self._log(f"  V方向系数数: {len(coeffs_v)}", force=True)
    
    def set_homography_matrix(self, H):
        """
        设置单应性矩阵（用于无Pro Lab情况）
        :param H: 3x3 单应性矩阵
        """
        self.homography_matrix = H
        self.is_calibrated = True
        self.use_homography = True
        self.use_polynomial = False  # 禁用多项式
        
        # 重置卡尔曼滤波器
        self.kalman_u = None
        self.kalman_v = None
        self.kalman_initialized = False
        
        self._log(f"[校准] 单应性矩阵已设置", force=True)
        self._log(f"  矩阵:\n{H}", force=True)
    
    def set_linear_params(self, scale_u, scale_v, offset_u, offset_v):
        """
        设置线性校准参数
        :param scale_u: U方向缩放
        :param scale_v: V方向缩放
        :param offset_u: U方向偏移
        :param offset_v: V方向偏移
        """
        self.calibration_scale_u = scale_u
        self.calibration_scale_v = scale_v
        self.calibration_offset_u = offset_u
        self.calibration_offset_v = offset_v
        self.is_calibrated = True
        self.use_polynomial = False
        self.use_homography = False  # 禁用单应性
        
        # 重置卡尔曼滤波器
        self.kalman_u = None
        self.kalman_v = None
        self.kalman_initialized = False
        
        self._log(f"[校准] 线性参数已设置", force=True)
        self._log(f"  scale_u={scale_u:.4f}, scale_v={scale_v:.4f}", force=True)
        self._log(f"  offset_u={offset_u:.4f}, offset_v={offset_v:.4f}", force=True)
    
    def reset_calibration(self):
        """重置校准参数"""
        self.calibration_offset_u = 0.0
        self.calibration_offset_v = 0.0
        self.calibration_scale_u = 1.0
        self.calibration_scale_v = 1.0
        self.poly_coeffs_u = None
        self.poly_coeffs_v = None
        self.use_polynomial = False
        self.is_calibrated = False
        
        # 重置卡尔曼滤波器
        self.kalman_u = None
        self.kalman_v = None
        self.kalman_initialized = False
        
        # 重置平滑变量
        if hasattr(self, '_smooth_u'):
            del self._smooth_u
            del self._smooth_v
        
        self._log("[校准] 参数已重置", force=True)
    
    def get_calibration_params(self):
        """
        获取当前校准参数
        :return: 包含校准参数的字典
        """
        return {
            'offset_u': self.calibration_offset_u,
            'offset_v': self.calibration_offset_v,
            'scale_u': self.calibration_scale_u,
            'scale_v': self.calibration_scale_v,
            'is_calibrated': self.is_calibrated
        }
    
    def gaze_to_screen(self, u, v):
        """
        将归一化 gaze 坐标转换为屏幕坐标（用于误差分析）
        :param u: 归一化 U 坐标 (0-1)
        :param v: 归一化 V 坐标 (0-1)
        :return: (screen_x, screen_y) 屏幕像素坐标
        """
        # 应用校准参数
        if self.is_calibrated:
            if self.use_polynomial and self.poly_coeffs_u is not None:
                # 使用多项式校准
                if len(self.poly_coeffs_u) == 10:
                    # 三次多项式：10个系数
                    calibrated_u = (
                        self.poly_coeffs_u[0] +
                        self.poly_coeffs_u[1] * u +
                        self.poly_coeffs_u[2] * v +
                        self.poly_coeffs_u[3] * u * u +
                        self.poly_coeffs_u[4] * u * v +
                        self.poly_coeffs_u[5] * v * v +
                        self.poly_coeffs_u[6] * u * u * u +
                        self.poly_coeffs_u[7] * u * u * v +
                        self.poly_coeffs_u[8] * u * v * v +
                        self.poly_coeffs_u[9] * v * v * v
                    )
                    calibrated_v = (
                        self.poly_coeffs_v[0] +
                        self.poly_coeffs_v[1] * u +
                        self.poly_coeffs_v[2] * v +
                        self.poly_coeffs_v[3] * u * u +
                        self.poly_coeffs_v[4] * u * v +
                        self.poly_coeffs_v[5] * v * v +
                        self.poly_coeffs_v[6] * u * u * u +
                        self.poly_coeffs_v[7] * u * u * v +
                        self.poly_coeffs_v[8] * u * v * v +
                        self.poly_coeffs_v[9] * v * v * v
                    )
                else:
                    # 二次多项式：6个系数
                    calibrated_u = (
                        self.poly_coeffs_u[0] +
                        self.poly_coeffs_u[1] * u +
                        self.poly_coeffs_u[2] * v +
                        self.poly_coeffs_u[3] * u * u +
                        self.poly_coeffs_u[4] * u * v +
                        self.poly_coeffs_u[5] * v * v
                    )
                    calibrated_v = (
                        self.poly_coeffs_v[0] +
                        self.poly_coeffs_v[1] * u +
                        self.poly_coeffs_v[2] * v +
                        self.poly_coeffs_v[3] * u * u +
                        self.poly_coeffs_v[4] * u * v +
                        self.poly_coeffs_v[5] * v * v
                    )
            else:
                # 使用线性校准
                calibrated_u = u * self.calibration_scale_u + self.calibration_offset_u
                calibrated_v = v * self.calibration_scale_v + self.calibration_offset_v
        else:
            calibrated_u = u
            calibrated_v = v
        
        # 转换为屏幕坐标
        screen_x = calibrated_u * self.screen_width
        screen_y = calibrated_v * self.screen_height
        
        return screen_x, screen_y
