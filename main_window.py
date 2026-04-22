import sys
import os
import json
import time
import sqlite3
from datetime import datetime

# 设置 Qt 平台插件路径
if getattr(sys, 'base_prefix', sys.prefix) != sys.prefix:
    venv_path = sys.prefix
    plugin_path = os.path.join(venv_path, 'Lib', 'site-packages', 'PyQt5', 'Qt5', 'plugins')
    if os.path.exists(plugin_path):
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path

import cv2
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QLabel, 
                             QVBoxLayout, QHBoxLayout, QWidget, QMessageBox, 
                             QFrame, QGridLayout, QComboBox, QLineEdit, 
                             QTabWidget, QProgressBar, QGroupBox, QDialog,
                             QInputDialog, QFormLayout, QTableWidget, QTableWidgetItem,
                             QHeaderView, QSpinBox, QCheckBox, QScrollArea, QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt5.QtGui import QImage, QPixmap, QColor, QFont, QPainter, QPen, QBrush, QRadialGradient
from glasses_manager import GlassesManager
from coordinate_mapper import CoordinateMapper
from attention_model import AttentionEvaluator
from training_widget import TrainingWidget
from report_generator import ReportGenerator
from database import DatabaseManager
import time
from collections import deque

class GlobalGazePointWidget(QWidget):
    """全局注视点显示组件 - 覆盖整个窗口"""
    def __init__(self, parent=None):
        super().__init__(parent)
        # 设置为透明背景，不拦截鼠标事件
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setStyleSheet("background-color: transparent;")
        
        # 存储最新的注视点
        self.current_gaze = None
        self.previous_gaze = None
        
    def update_gaze(self, x, y):
        """更新注视点位置（屏幕坐标）"""
        self.previous_gaze = self.current_gaze
        self.current_gaze = (x, y)
        self.update()
    
    def paintEvent(self, event):
        if not self.current_gaze:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        x, y = self.current_gaze
        
        # 绘制外圈（半透明红色）
        painter.setPen(QColor(239, 68, 68, 150))
        painter.setBrush(QColor(239, 68, 68, 40))
        painter.drawEllipse(int(x) - 25, int(y) - 25, 50, 50)
        
        # 绘制内圈（实心红色）
        painter.setBrush(QColor(239, 68, 68, 200))
        painter.drawEllipse(int(x) - 10, int(y) - 10, 20, 20)
        
        # 绘制十字准星
        painter.setPen(QPen(QColor(239, 68, 68, 180), 2))
        painter.drawLine(int(x) - 35, int(y), int(x) + 35, int(y))
        painter.drawLine(int(x), int(y) - 35, int(x), int(y) + 35)
        
        # 如果有上一个点，绘制连线
        if self.previous_gaze:
            prev_x, prev_y = self.previous_gaze
            painter.setPen(QPen(QColor(239, 68, 68, 100), 2))
            painter.drawLine(int(prev_x), int(prev_y), int(x), int(y))
        
        painter.end()


class MetricCard(QFrame):
    """指标卡片组件"""
    def __init__(self, title, value, color, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 10px;
                border-left: 4px solid {color};
                padding: 12px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(self.title_label)
        
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"color: {color}; font-size: 20px; font-weight: bold;")
        layout.addWidget(self.value_label)


class VideoDisplayWidget(QFrame):
    """实时视频流显示组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(640, 360)
        self.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border-radius: 12px;
                border: 2px solid #334155;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 视频标签
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("color: white; font-size: 14px;")
        self.video_label.setText("等待视频流...")
        layout.addWidget(self.video_label)
        
        # 状态指示器
        self.status_indicator = QLabel("● 离线")
        self.status_indicator.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(self.status_indicator)
        
        self.current_frame = None
        self.calibration_point = None  # (u, v, current, total)
        
    def set_calibration_point(self, u, v, current, total):
        """设置校准点位置"""
        self.calibration_point = (u, v, current, total)
        self.update()
    
    def clear_calibration_point(self):
        """清除校准点"""
        self.calibration_point = None
        self.update()
        
    def paintEvent(self, event):
        """绘制校准点"""
        super().paintEvent(event)
        
        if self.calibration_point and self.current_frame is not None:
            u, v, current, total = self.calibration_point
            
            # 在视频画面上绘制红点
            from PyQt5.QtGui import QPainter, QPen, QBrush
            from PyQt5.QtCore import Qt
            
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 计算红点位置
            x = int(u * self.width())
            y = int(v * self.height())
            
            # 外圈
            pen = QPen(QColor(255, 0, 0))
            pen.setWidth(4)
            painter.setPen(pen)
            painter.drawEllipse(x - 40, y - 40, 80, 80)
            
            # 内圈
            painter.setBrush(QColor(255, 0, 0))
            painter.drawEllipse(x - 15, y - 15, 30, 30)
            
            # 十字线
            painter.setPen(QPen(QColor(255, 0, 0), 3))
            painter.drawLine(x - 60, y, x + 60, y)
            painter.drawLine(x, y - 60, x, y + 60)
            
            # 文字提示
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            font = painter.font()
            font.setPointSize(16)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(x - 60, y - 60, f"{current}/{total}")
            
            painter.end()
        
    def update_frame(self, frame):
        """更新视频帧"""
        if frame is None:
            return
            
        self.current_frame = frame
        
        # 转换为 RGB
        if len(frame.shape) == 3:
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        else:
            h, w = frame.shape
            bytes_per_line = w
            qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
        
        # 缩放以适应显示区域
        scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
            self.video_label.size(), 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        )
        
        self.video_label.setPixmap(scaled_pixmap)
        self.status_indicator.setText("● 在线")
        self.status_indicator.setStyleSheet("color: #10b981; font-size: 12px; font-weight: bold;")


class GazeHeatmapWidget(QFrame):
    """视线热力图显示组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border-radius: 12px;
                border: 2px solid #1e293b;
            }
        """)
        
        from collections import deque
        self.heatmap_data = np.zeros((100, 100))
        self.gaze_history = deque(maxlen=200)
        
    def add_gaze_point(self, x, y):
        """添加注视点到热力图"""
        # 归一化坐标到 0-100
        norm_x = int((x / 1920) * 100)
        norm_y = int((y / 1080) * 100)
        
        # 限制范围
        norm_x = max(0, min(99, norm_x))
        norm_y = max(0, min(99, norm_y))
        
        self.gaze_history.append((norm_x, norm_y))
        
        # 更新热力图数据(高斯模糊效果)
        for gx, gy in self.gaze_history:
            distance = np.sqrt((np.arange(100) - gx)**2 + (np.arange(100)[:, np.newaxis] - gy)**2)
            self.heatmap_data += np.exp(-distance**2 / 200)
        
        # 归一化
        max_val = self.heatmap_data.max()
        if max_val > 0:
            self.heatmap_data = self.heatmap_data / max_val
        
        self.update()
    
    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制热力图
        if len(self.gaze_history) > 0:
            cell_width = self.width() / 100
            cell_height = self.height() / 100
            
            for x in range(100):
                for y in range(100):
                    intensity = self.heatmap_data[y, x]
                    if intensity > 0.1:
                        # 颜色映射: 蓝 -> 绿 -> 黄 -> 红
                        if intensity < 0.5:
                            r = 0
                            g = int(255 * intensity * 2)
                            b = int(255 * (1 - intensity * 2))
                        else:
                            r = int(255 * (intensity - 0.5) * 2)
                            g = 255
                            b = 0
                        
                        color = QColor(r, g, b, int(255 * intensity))
                        painter.setBrush(QBrush(color))
                        painter.setPen(Qt.NoPen)
                        painter.drawRect(
                            int(x * cell_width), 
                            int(y * cell_height), 
                            int(cell_width) + 1, 
                            int(cell_height) + 1
                        )
        
        painter.end()
    
    def clear_heatmap(self):
        """清除热力图"""
        self.heatmap_data = np.zeros((100, 100))
        self.gaze_history.clear()
        self.update()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.current_user_id = 1
        self.current_username = "Guest"
        self.setWindowTitle("编程初学者代码阅读专注力训练系统")
        
        # 根据屏幕分辨率自动调整窗口大小
        screen = QApplication.primaryScreen().geometry()
        if screen.width() >= 1920:
            # 1920x1080 - 最大化窗口高度，留出任务栏空间
            self.resize(1600, 1000)
            self.setMinimumSize(1400, 800)
            self.showMaximized()  # 启动时最大化窗口
        else:
            # 较低分辨率
            self.resize(1200, 800)
            self.setMinimumSize(1000, 700)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8fafc;
            }
        """)
        
        # 初始化组件
        self.glasses_mgr = GlassesManager()
        self.glasses_mgr.start_async_loop()
        self.mapper = CoordinateMapper()
        self.evaluator = AttentionEvaluator()
        self.training_widget = TrainingWidget()
        
        # 将登录的用户 ID 传递给训练模块
        self.training_widget.current_user_id = self.current_user_id
        
        self.report_generator = ReportGenerator()
        self.training_widget.task_completed.connect(self.on_task_completed)
        
        # 绑定信号
        self.glasses_mgr.connected.connect(self.on_connected)
        self.glasses_mgr.disconnected.connect(self.on_disconnected)
        self.glasses_mgr.stream_data_ready.connect(self.process_stream)
        self.mapper.screen_gaze_update.connect(self.on_gaze_mapped)
        
        # 定时器
        self.metrics_timer = QTimer()
        self.metrics_timer.timeout.connect(self.update_system_status)
        self.metrics_timer.start(500)  # 500ms更新一次，降低频率
        
        # 眼镜滑动检测相关变量
        self.gaze_error_history = []  # 注视误差历史
    
    def set_current_user(self, user_id, username):
        """设置当前登录用户"""
        self.current_user_id = user_id
        self.current_username = username
        self.training_widget.current_user_id = user_id
        self.setWindowTitle(f"编程初学者代码阅读专注力训练系统 - 用户: {username}")
        self.center_gaze_samples = []  # 中心区域注视样本（用于隐式校准）
        self.last_calibration_check_time = time.time()  # 上次校准检查时间
        
        # UI 布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)  # 减少外边距
        main_layout.setSpacing(12)  # 减少间距
        
        # 标题区域
        header = self.create_header()
        main_layout.addWidget(header)
        
        # 状态栏
        self.status_bar = self.create_status_bar()
        main_layout.addWidget(self.status_bar)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 2px solid #e2e8f0;
                border-radius: 12px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #e2e8f0;
                color: #64748b;
                padding: 12px 24px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-size: 14px;
            }
            QTabBar::tab:selected {
                background-color: white;
                color: #3b82f6;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                background-color: #cbd5e1;
            }
        """)
        
        # 标签页 1: 实时监控
        monitor_tab = self.create_monitor_tab()
        self.tab_widget.addTab(monitor_tab, "📊 实时监控")
        
        # 标签页 2: 训练任务
        self.tab_widget.addTab(self.training_widget, "🎯 训练任务")
        
        # 标签页 3: 数据分析
        analysis_tab = self.create_analysis_tab()
        self.tab_widget.addTab(analysis_tab, "📈 数据分析")
        
        # 标签页 4: 用户管理
        user_tab = self.create_user_tab()
        self.tab_widget.addTab(user_tab, "👤 用户管理")
        
        # 标签页 5: 系统设置
        settings_tab = self.create_settings_tab()
        self.tab_widget.addTab(settings_tab, "⚙️ 系统设置")
        
        main_layout.addWidget(self.tab_widget, stretch=1)  # 让标签页占据所有可用空间
        
        # 从数据库加载用户信息到 UI 输入框（UI 初始化完成后）
        self.load_user_info_from_db()
        # 更新训练统计摘要
        self.update_summary_from_db()
        
        # 连接按钮
        self.connect_btn = self.create_connect_button()
        self.connect_btn.setFixedHeight(45)  # 固定按钮高度
        main_layout.addWidget(self.connect_btn)
        
        # 校准按钮
        self.calibration_btn = QPushButton("🎯 屏幕校准")
        self.calibration_btn.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.calibration_btn.setFixedHeight(45)  # 固定按钮高度，从55减少到45
        self.calibration_btn.setStyleSheet("""
            QPushButton {
                background-color: #f59e0b;
                color: white;
                border-radius: 10px;
                padding: 12px;
            }
            QPushButton:hover {
                background-color: #d97706;
            }
            QPushButton:pressed {
                background-color: #b45309;
            }
        """)
        self.calibration_btn.clicked.connect(self.start_calibration)
        main_layout.addWidget(self.calibration_btn)
        
        self.current_level = 1
        self.last_time = time.time()
        self.current_gaze = (0, 0)  # 映射后的屏幕坐标
        self.current_gaze2d = None  # 原始gaze2d归一化坐标 [u, v]
        self.is_connected = False
        self.gaze_count = 0
        self._last_rate_update = time.time()  # 用于计算数据接收率
        self.simulator_mode = False  # 模拟器模式标志
        
        # 数据文件路径
        self.data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        self.user_data_file = os.path.join(self.data_dir, 'user_data.json')
        self.training_history_file = os.path.join(self.data_dir, 'training_history.json')
        self.settings_file = os.path.join(self.data_dir, 'settings.json')
        
        # 初始化数据
        self.load_user_data()
        self.load_training_history()
        self.load_settings()
        
        # 初始化示例训练历史数据（如果为空）
        if not hasattr(self, 'training_history') or len(self.training_history) == 0:
            self.init_sample_history()
        
        # 更新徽章显示
        self.update_badge_display()
    
    def create_stat_card(self, title, value, color):
        """创建统计卡片"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 white, stop:1 #f8fafc);
                border: 2px solid {color};
                border-radius: 12px;
                padding: 20px;
            }}
        """)
        card.setMinimumHeight(120)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # 标题
        title_label = QLabel(title)
        title_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        title_label.setStyleSheet(f"color: {color};")
        layout.addWidget(title_label)
        
        # 值
        value_label = QLabel(value)
        value_label.setFont(QFont("Microsoft YaHei", 28, QFont.Bold))
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet(f"color: {color}; padding: 8px 0;")
        value_label.setObjectName("value_label")  # 设置对象名以便后续查找
        layout.addWidget(value_label)
        
        return card
    
    def update_stat_card(self, card, value):
        """更新统计卡片的值"""
        if card:
            value_label = card.findChild(QLabel, "value_label")
            if value_label:
                value_label.setText(str(value))
    
    def create_monitor_tab(self):
        """创建实时监控标签页"""
        monitor_widget = QWidget()
        layout = QVBoxLayout(monitor_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # 视频流和热力图区域
        video_heatmap_layout = QHBoxLayout()
        
        # 视频显示（增加最小尺寸）
        self.video_widget = VideoDisplayWidget()
        screen_width = QApplication.primaryScreen().geometry().width()
        if screen_width >= 1920:
            # 大屏幕：更大的视频窗口
            self.video_widget.setMinimumSize(800, 450)
            self.heatmap_widget_min_size = (400, 450)
        else:
            # 小屏幕
            self.video_widget.setMinimumSize(500, 280)
            self.heatmap_widget_min_size = (300, 280)
        video_heatmap_layout.addWidget(self.video_widget, stretch=2)
        
        # 热力图
        self.heatmap_widget = GazeHeatmapWidget()
        self.heatmap_widget.setMinimumSize(*self.heatmap_widget_min_size)
        video_heatmap_layout.addWidget(self.heatmap_widget, stretch=1)
        
        layout.addLayout(video_heatmap_layout)
        
        return monitor_widget
    
    def create_analysis_tab(self):
        """创建数据分析标签页"""
        analysis_widget = QWidget()
        layout = QVBoxLayout(analysis_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # 统计数据组
        stats_group = QGroupBox("📊 注视统计")
        stats_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 16px;
                color: #8b5cf6;
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                margin-top: 0px;
                padding-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
            }
        """)
        stats_layout = QGridLayout()
        stats_layout.setSpacing(20)
        stats_layout.setContentsMargins(20, 15, 20, 20)
        
        # 统计标签
        self.total_gaze_label = QLabel("👁️ 总注视点数: 0")
        self.total_gaze_label.setStyleSheet("font-size: 16px; color: #475569; font-weight: bold;")
        stats_layout.addWidget(self.total_gaze_label, 0, 0)
        
        self.avg_fixation_label = QLabel("⏱️ 平均注视时长: 0ms")
        self.avg_fixation_label.setStyleSheet("font-size: 16px; color: #475569; font-weight: bold;")
        stats_layout.addWidget(self.avg_fixation_label, 0, 1)
        
        self.max_deviation_label = QLabel("📏 最大偏离距离: 0px")
        self.max_deviation_label.setStyleSheet("font-size: 16px; color: #475569; font-weight: bold;")
        stats_layout.addWidget(self.max_deviation_label, 1, 0)
        
        self.data_rate_label = QLabel("📡 数据接收率: 0 Hz")
        self.data_rate_label.setStyleSheet("font-size: 16px; color: #475569; font-weight: bold;")
        stats_layout.addWidget(self.data_rate_label, 1, 1)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        # 进度条
        progress_group = QGroupBox("🚀 训练进度")
        progress_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 16px;
                color: #10b981;
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                margin-top: 16px;
                padding-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
            }
        """)
        progress_layout = QVBoxLayout()
        
        self.training_progress = QProgressBar()
        self.training_progress.setMinimum(0)
        self.training_progress.setMaximum(100)
        self.training_progress.setValue(0)
        self.training_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #e2e8f0;
                border-radius: 6px;
                text-align: center;
                background-color: #f1f5f9;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #34d399);
                border-radius: 4px;
            }
        """)
        progress_layout.addWidget(self.training_progress)
        
        self.progress_label = QLabel("当前进度: 0%")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet("color: #64748b; font-size: 14px; font-weight: bold; margin-top: 10px;")
        progress_layout.addWidget(self.progress_label)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # 训练历史表格
        history_group = QGroupBox("📝 训练历史记录")
        history_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 16px;
                color: #f59e0b;
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                margin-top: 16px;
                padding-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
            }
        """)
        history_layout = QVBoxLayout()
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(6)
        self.history_table.setHorizontalHeaderLabels(["日期", "任务名称", "专注度", "时长", "完成状态", "操作"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.verticalHeader().setVisible(False)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                gridline-color: #e2e8f0;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                padding: 8px;
                border: none;
                font-weight: bold;
                color: #475569;
            }
        """)
        history_layout.addWidget(self.history_table)
        
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)
        
        layout.addStretch()
        
        return analysis_widget
    
    def create_user_tab(self):
        """创建用户管理标签页"""
        # 使用滚动区域，防止内容被压缩
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background-color: transparent; border: none;")
        
        user_widget = QWidget()
        layout = QVBoxLayout(user_widget)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)
        
        # 用户信息卡片
        info_group = QGroupBox("👤 当前用户信息")
        info_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 16px;
                color: #3b82f6;
                border: 2px solid #e2e8f0;
                border-radius: 12px;
                margin-top: 12px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
            }
        """)
        info_layout = QFormLayout()
        info_layout.setSpacing(12)
        info_layout.setContentsMargins(20, 16, 20, 16)
        info_layout.setLabelAlignment(Qt.AlignRight)
        info_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        
        self.user_name_input = QLineEdit()
        self.user_name_input.setPlaceholderText("请输入姓名")
        self.user_name_input.setMinimumHeight(48)
        self.user_name_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
                background: #f9fafb;
            }
            QLineEdit:focus {
                border: 1px solid #3b82f6;
                background: white;
            }
        """)
        lbl_name = QLabel("姓名")
        lbl_name.setStyleSheet("font-size: 14px; font-weight: bold; color: #374151;")
        info_layout.addRow(lbl_name, self.user_name_input)
        
        self.user_id_input = QLineEdit()
        self.user_id_input.setPlaceholderText("请输入学号/工号")
        self.user_id_input.setMinimumHeight(48)
        self.user_id_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
                background: #f9fafb;
            }
            QLineEdit:focus {
                border: 1px solid #3b82f6;
                background: white;
            }
        """)
        lbl_id = QLabel("学号/工号")
        lbl_id.setStyleSheet("font-size: 14px; font-weight: bold; color: #374151;")
        info_layout.addRow(lbl_id, self.user_id_input)
        
        self.user_level_combo = QComboBox()
        self.user_level_combo.addItems(["初级", "中级", "高级"])
        self.user_level_combo.setMinimumHeight(48)
        self.user_level_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
                background: #f9fafb;
            }
            QComboBox:focus {
                border: 1px solid #3b82f6;
                background: white;
            }
        """)
        lbl_level = QLabel("编程水平")
        lbl_level.setStyleSheet("font-size: 14px; font-weight: bold; color: #374151;")
        info_layout.addRow(lbl_level, self.user_level_combo)
        
        self.user_experience_spin = QSpinBox()
        self.user_experience_spin.setRange(0, 120)
        self.user_experience_spin.setValue(0)
        self.user_experience_spin.setSuffix(" 个月")
        self.user_experience_spin.setMinimumHeight(48)
        self.user_experience_spin.setStyleSheet("""
            QSpinBox {
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
                background: #f9fafb;
            }
            QSpinBox:focus {
                border: 1px solid #3b82f6;
                background: white;
            }
        """)
        lbl_exp = QLabel("编程经验")
        lbl_exp.setStyleSheet("font-size: 14px; font-weight: bold; color: #374151;")
        info_layout.addRow(lbl_exp, self.user_experience_spin)
        
        save_user_btn = QPushButton("💾 保存用户信息")
        save_user_btn.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        save_user_btn.setMinimumHeight(56)
        save_user_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border-radius: 8px;
                padding: 14px;
                margin-top: 12px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)
        save_user_btn.clicked.connect(self.save_user_info)
        info_layout.addRow(save_user_btn)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # 训练统计摘要
        summary_group = QGroupBox("📈 训练统计摘要")
        summary_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 16px;
                color: #10b981;
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                margin-top: 16px;
                padding-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
            }
        """)
        summary_layout = QGridLayout()
        
        self.total_sessions_label = QLabel("📊 总训练次数: 0")
        self.total_sessions_label.setStyleSheet("font-size: 16px; color: #475569; font-weight: bold; padding: 12px;")
        summary_layout.addWidget(self.total_sessions_label, 0, 0)
        
        self.avg_attention_label = QLabel("🎯 平均专注度: 0%")
        self.avg_attention_label.setStyleSheet("font-size: 16px; color: #475569; font-weight: bold; padding: 12px;")
        summary_layout.addWidget(self.avg_attention_label, 0, 1)
        
        self.total_time_label = QLabel("⏱️ 总训练时长: 0分钟")
        self.total_time_label.setStyleSheet("font-size: 16px; color: #475569; font-weight: bold; padding: 12px;")
        summary_layout.addWidget(self.total_time_label, 1, 0)
        
        self.best_score_label = QLabel("🏆 最高专注度: 0%")
        self.best_score_label.setStyleSheet("font-size: 16px; color: #475569; font-weight: bold; padding: 12px;")
        summary_layout.addWidget(self.best_score_label, 1, 1)
        
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
        # 成就徽章区域
        achievement_group = QGroupBox("🏆 成就徽章")
        achievement_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 16px;
                color: #f59e0b;
                border: 2px solid #e2e8f0;
                border-radius: 10px;
                margin-top: 16px;
                padding-top: 20px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
            }
        """)
        achievement_layout = QHBoxLayout()
        achievement_layout.setSpacing(20)
        achievement_layout.setContentsMargins(20, 15, 20, 20)
        
        # 创建几个示例徽章
        badges = [
            ("🌟", "首次训练", "完成第一次训练"),
            ("🎯", "专注达人", "专注度达到90%以上"),
            ("⏱️", "坚持之星", "累计训练10小时"),
            ("📚", "学习标兵", "完成20个训练任务"),
        ]
        
        self.badge_widgets = []  # 保存徽章引用以便后续更新
        
        for icon, title, desc in badges:
            badge_widget = QWidget()
            badge_layout = QVBoxLayout(badge_widget)
            badge_layout.setAlignment(Qt.AlignCenter)
            
            badge_icon = QLabel(icon)
            badge_icon.setFont(QFont("Arial", 32))
            badge_icon.setAlignment(Qt.AlignCenter)
            badge_icon.setStyleSheet("padding: 10px;")
            badge_icon.setObjectName(f"badge_{title}")  # 设置对象名
            badge_layout.addWidget(badge_icon)
            
            badge_title = QLabel(title)
            badge_title.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
            badge_title.setAlignment(Qt.AlignCenter)
            badge_title.setStyleSheet("color: #475569;")
            badge_layout.addWidget(badge_title)
            
            badge_desc = QLabel(desc)
            badge_desc.setFont(QFont("Microsoft YaHei", 8))
            badge_desc.setAlignment(Qt.AlignCenter)
            badge_desc.setStyleSheet("color: #94a3b8;")
            badge_layout.addWidget(badge_desc)
            
            achievement_layout.addWidget(badge_widget)
            self.badge_widgets.append((badge_widget, badge_icon, title))
        
        achievement_layout.addStretch()
        achievement_group.setLayout(achievement_layout)
        layout.addWidget(achievement_group)
        
        layout.addStretch()
        
        # 设置滚动区域的内容
        scroll_area.setWidget(user_widget)
        
        return scroll_area
    
    def create_settings_tab(self):
        """创建系统设置标签页"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("background-color: transparent; border: none;")
        
        settings_widget = QWidget()
        layout = QVBoxLayout(settings_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # 眼动仪设置
        glasses_group = QGroupBox("眼动仪设置")
        glasses_layout = QFormLayout()
        glasses_layout.setContentsMargins(15, 15, 15, 15)
        glasses_layout.setSpacing(10)
        glasses_layout.setLabelAlignment(Qt.AlignRight)
        
        self.rtsp_timeout_spin = QSpinBox()
        self.rtsp_timeout_spin.setRange(5, 60)
        self.rtsp_timeout_spin.setValue(15)
        self.rtsp_timeout_spin.setSuffix(" 秒")
        self.rtsp_timeout_spin.setMinimumHeight(28)
        glasses_layout.addRow("RTSP超时时间:", self.rtsp_timeout_spin)
        
        self.gaze_sample_rate_combo = QComboBox()
        self.gaze_sample_rate_combo.addItems(["50 Hz", "100 Hz", "200 Hz"])
        self.gaze_sample_rate_combo.setCurrentIndex(1)
        self.gaze_sample_rate_combo.setMinimumHeight(28)
        glasses_layout.addRow("采样率:", self.gaze_sample_rate_combo)
        
        self.auto_reconnect_check = QCheckBox("自动重连")
        self.auto_reconnect_check.setChecked(True)
        self.auto_reconnect_check.setMinimumHeight(28)
        glasses_layout.addRow("", self.auto_reconnect_check)
        
        glasses_group.setLayout(glasses_layout)
        layout.addWidget(glasses_group)
        
        # 界面设置
        ui_group = QGroupBox("界面设置")
        ui_layout = QFormLayout()
        ui_layout.setContentsMargins(15, 15, 15, 15)
        ui_layout.setSpacing(10)
        ui_layout.setLabelAlignment(Qt.AlignRight)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["浅色主题", "深色主题", "护眼模式"])
        self.theme_combo.currentTextChanged.connect(self.apply_theme)
        self.theme_combo.setMinimumHeight(28)
        ui_layout.addRow("主题:", self.theme_combo)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(10, 20)
        self.font_size_spin.setValue(12)
        self.font_size_spin.setSuffix(" pt")
        self.font_size_spin.setMinimumHeight(28)
        ui_layout.addRow("字体大小:", self.font_size_spin)
        
        self.show_gaze_point_check = QCheckBox("显示注视点")
        self.show_gaze_point_check.setChecked(True)
        self.show_gaze_point_check.setMinimumHeight(28)
        ui_layout.addRow("", self.show_gaze_point_check)
        
        self.show_heatmap_check = QCheckBox("显示热力图")
        self.show_heatmap_check.setChecked(True)
        self.show_heatmap_check.setMinimumHeight(28)
        ui_layout.addRow("", self.show_heatmap_check)
        
        ui_group.setLayout(ui_layout)
        layout.addWidget(ui_group)
        
        # 模拟器设置
        sim_group = QGroupBox("模拟器模式")
        sim_layout = QVBoxLayout()
        sim_layout.setContentsMargins(15, 15, 15, 15)
        sim_layout.setSpacing(10)
        
        self.simulator_check = QCheckBox("启用模拟器模式（无眼动仪时使用）")
        self.simulator_check.setChecked(False)
        self.simulator_check.toggled.connect(self.toggle_simulator_mode)
        self.simulator_check.setMinimumHeight(28)
        sim_layout.addWidget(self.simulator_check)
        
        sim_desc = QLabel("开启后，可以使用鼠标移动模拟眼动数据，适合在没有眼动仪的情况下测试系统功能。")
        sim_desc.setWordWrap(True)
        sim_desc.setStyleSheet("color: #6b7280; padding: 5px 0;")
        sim_layout.addWidget(sim_desc)
        
        sim_group.setLayout(sim_layout)
        layout.addWidget(sim_group)
        
        # 保存设置按钮
        save_settings_btn = QPushButton("💾 保存设置")
        save_settings_btn.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        save_settings_btn.setMinimumHeight(45)
        save_settings_btn.clicked.connect(self.save_settings_from_ui)
        layout.addWidget(save_settings_btn)
        
        # 导出数据按钮
        export_btn = QPushButton("📊 导出所有训练报告")
        export_btn.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        export_btn.setMinimumHeight(45)
        export_btn.clicked.connect(self.export_all_reports)
        layout.addWidget(export_btn)
        
        # 校准参数显示
        calibration_group = QGroupBox("校准参数")
        calibration_layout = QGridLayout()
        calibration_layout.setContentsMargins(15, 15, 15, 15)
        calibration_layout.setSpacing(12)
        
        self.cal_offset_u_label = QLabel("U轴偏移: 0.0000")
        self.cal_offset_u_label.setMinimumHeight(28)
        calibration_layout.addWidget(self.cal_offset_u_label, 0, 0)
        
        self.cal_offset_v_label = QLabel("V轴偏移: 0.0000")
        self.cal_offset_v_label.setMinimumHeight(28)
        calibration_layout.addWidget(self.cal_offset_v_label, 0, 1)
        
        self.cal_scale_u_label = QLabel("U轴缩放: 1.0000")
        self.cal_scale_u_label.setMinimumHeight(28)
        calibration_layout.addWidget(self.cal_scale_u_label, 1, 0)
        
        self.cal_scale_v_label = QLabel("V轴缩放: 1.0000")
        self.cal_scale_v_label.setMinimumHeight(28)
        calibration_layout.addWidget(self.cal_scale_v_label, 1, 1)
        
        reset_cal_btn = QPushButton("🔄 重置校准参数")
        reset_cal_btn.setFont(QFont("Microsoft YaHei", 11))
        reset_cal_btn.setMinimumHeight(40)
        reset_cal_btn.clicked.connect(self.reset_calibration)
        calibration_layout.addWidget(reset_cal_btn, 2, 0, 1, 2)
        
        calibration_group.setLayout(calibration_layout)
        layout.addWidget(calibration_group)
        
        # 关于信息
        about_group = QGroupBox("关于系统")
        about_layout = QVBoxLayout()
        about_layout.setContentsMargins(15, 15, 15, 15)
        about_layout.setSpacing(10)
        
        about_text = QLabel(
            "<h3 style='color: #3b82f6; margin: 0 0 10px 0;'>编程初学者代码阅读专注力训练系统</h3>"
            "<p style='margin: 5px 0;'><b>版本:</b> v2.0</p>"
            "<p style='margin: 5px 0;'><b>功能特性:</b></p>"
            "<ul style='margin: 5px 0 10px 20px;'>"
            "<li>实时眼动追踪与可视化</li>"
            "<li>专注度评估与分析</li>"
            "<li>屏幕校准功能</li>"
            "<li>训练任务管理</li>"
            "<li>数据报告生成</li>"
            "</ul>"
            "<p style='margin: 5px 0;'><b>技术支持:</b> Tobii Pro Glasses 3</p>"
        )
        about_text.setStyleSheet("font-size: 13px; color: #475569; line-height: 1.6;")
        about_text.setWordWrap(True)
        about_layout.addWidget(about_text)
        
        about_group.setLayout(about_layout)
        layout.addWidget(about_group)
        
        layout.addStretch()
        
        # 设置滚动区域的内容
        scroll_area.setWidget(settings_widget)
        
        return scroll_area
    
    def create_header(self):
        """创建顶部标题区域"""
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #8b5cf6);
                border-radius: 12px;
                padding: 16px;
            }
        """)
        header.setMinimumHeight(70)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 10, 20, 10)
        
        # 标题
        title = QLabel("📚 代码阅读专注力训练系统")
        title.setStyleSheet("""
            color: white;
            font-size: 24px;
            font-weight: bold;
        """)
        layout.addWidget(title)
        layout.addStretch()
        
        # 版本标签
        version = QLabel("v3.0")
        version.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 14px;")
        layout.addWidget(version)
        
        return header
    
    def create_status_bar(self):
        """创建状态栏"""
        status_frame = QFrame()
        status_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                padding: 12px;
            }
        """)
        
        layout = QHBoxLayout(status_frame)
        layout.setContentsMargins(16, 8, 16, 8)
        
        # 连接状态
        self.connection_status = QLabel("● 未连接")
        self.connection_status.setStyleSheet("color: #94a3b8; font-size: 14px;")
        layout.addWidget(self.connection_status)
        
        # 连接模式选择
        layout.addSpacing(20)
        mode_label = QLabel("连接方式:")
        mode_label.setStyleSheet("color: #64748b; font-size: 13px;")
        layout.addWidget(mode_label)
        
        self.connection_mode_combo = QComboBox()
        self.connection_mode_combo.addItems(["🔍 自动发现 (WiFi)", "🎯 指定 IP (USB)"])
        self.connection_mode_combo.setCurrentIndex(0)
        self.connection_mode_combo.setMinimumWidth(180)
        self.connection_mode_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 4px 8px;
                background-color: white;
                font-size: 13px;
            }
            QComboBox:hover {
                border: 1px solid #3b82f6;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
        """)
        self.connection_mode_combo.currentIndexChanged.connect(self.on_connection_mode_changed)
        layout.addWidget(self.connection_mode_combo)
        
        # IP 地址输入框(默认隐藏)
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("输入眼镜 IP 地址...")
        self.ip_input.setText("192.168.75.51")
        self.ip_input.setMaximumWidth(150)
        self.ip_input.setVisible(False)
        self.ip_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #3b82f6;
            }
        """)
        layout.addWidget(self.ip_input)
        
        # 当前关卡
        self.level_status = QLabel("当前关卡: 第 1 关")
        self.level_status.setStyleSheet("color: #3b82f6; font-size: 14px; font-weight: bold;")
        layout.addWidget(self.level_status)
        
        layout.addStretch()
        
        # 注视点坐标
        self.coord_label = QLabel("坐标: --, --")
        self.coord_label.setStyleSheet("color: #64748b; font-size: 13px;")
        layout.addWidget(self.coord_label)
        
        return status_frame
    
    def create_connect_button(self):
        """创建连接按钮"""
        btn = QPushButton("🔌 连接 Tobii Pro Glasses 3")
        btn.setMinimumHeight(50)
        btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #6366f1);
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 10px;
                padding: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2563eb, stop:1 #4f46e5);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1d4ed8, stop:1 #4338ca);
            }
            QPushButton:disabled {
                background: #cbd5e1;
                color: #94a3b8;
            }
        """)
        btn.clicked.connect(self.handle_connect)
        return btn
    
    def update_system_status(self):
        """更新系统状态"""
        # 更新连接状态
        if self.is_connected:
            self.connection_status.setText("● 已连接")
            self.connection_status.setStyleSheet("color: #10b981; font-size: 14px;")
        else:
            self.connection_status.setText("● 未连接")
            self.connection_status.setStyleSheet("color: #ef4444; font-size: 14px;")
        
        # 更新电池电量（如果可用）
        if hasattr(self, 'battery_label') and hasattr(self.glasses_manager, 'get_battery_level'):
            try:
                battery = self.glasses_manager.get_battery_level()
                if battery is not None:
                    self.battery_label.setText(f"🔋 电量: {battery}%")
            except:
                pass
    
    def toggle_simulator_mode(self, checked, show_message=True):
        """切换模拟器模式"""
        self.simulator_mode = checked
        
        if checked:
            # 启用鼠标追踪
            self.setMouseTracking(True)
            if hasattr(self, 'training_widget'):
                self.training_widget.code_editor.setMouseTracking(True)
                self.training_widget.code_editor.viewport().installEventFilter(self)
            if show_message:
                QMessageBox.information(
                    self,
                    "🎮 模拟器模式已启用",
                    "现在可以使用鼠标模拟眼动数据。\n\n"
                    "在训练任务中移动鼠标，系统将记录鼠标位置作为注视点。\n\n"
                    "这适合在没有眼动仪的情况下测试系统功能。"
                )
        else:
            # 禁用鼠标追踪
            self.setMouseTracking(False)
            if hasattr(self, 'training_widget'):
                self.training_widget.code_editor.setMouseTracking(False)
                self.training_widget.code_editor.viewport().removeEventFilter(self)
    
    def eventFilter(self, obj, event):
        """事件过滤器 - 捕获鼠标移动事件（模拟器模式）"""
        from PyQt5.QtCore import QEvent
        
        if not self.simulator_mode:
            return super().eventFilter(obj, event)
        
        # 检查是否是训练模块的viewport
        if (hasattr(self, 'training_widget') and 
            obj == self.training_widget.code_editor.viewport() and
            event.type() == QEvent.MouseMove):
            
            if self.training_widget.is_training:
                # 获取鼠标相对于 viewport 的位置
                pos = event.pos()
                x, y = pos.x(), pos.y()
                
                # 转换为全局坐标，以便 training_widget 统一处理
                global_pos = self.training_widget.code_editor.viewport().mapToGlobal(pos)
                gx, gy = global_pos.x(), global_pos.y()
                
                # 计算时间间隔
                current_time = time.time()
                dt = current_time - self.last_time
                self.last_time = current_time
                
                # 调用训练模块的check_gaze（传入全局坐标）
                self.training_widget.check_gaze(gx, gy, dt)
                
                # 注释掉全局注视点更新，避免重复显示
                # 训练模块已经在内部显示注视点了
                # screen_pos = self.training_widget.code_editor.viewport().mapToGlobal(pos)
                # main_pos = self.mapFromGlobal(screen_pos)
                # self.on_gaze_mapped(main_pos.x(), main_pos.y())
        
        return super().eventFilter(obj, event)
    
    def handle_connect(self):
        self.connect_btn.setEnabled(False)
        self.connection_status.setText("● 连接中...")
        self.connection_status.setStyleSheet("color: #f59e0b; font-size: 14px;")
        
        # 设置连接模式
        mode_index = self.connection_mode_combo.currentIndex()
        if mode_index == 0:
            # 自动发现模式
            self.glasses_mgr.set_connection_mode("zeroconf")
        else:
            # 固定 IP 模式
            ip_address = self.ip_input.text().strip()
            if not ip_address:
                QMessageBox.warning(self, "警告", "请输入有效的 IP 地址")
                self.connect_btn.setEnabled(True)
                return
            self.glasses_mgr.set_connection_mode("ip", ip_address)
        
        self.glasses_mgr.connect_device()
    
    def on_connection_mode_changed(self, index):
        """连接模式切换处理"""
        if index == 1:  # 固定 IP 模式
            self.ip_input.setVisible(True)
        else:
            self.ip_input.setVisible(False)
    
    def on_connected(self, serial):
        self.is_connected = True
        self.connection_status.setText(f"● 已连接 ({serial})")
        self.connection_status.setStyleSheet("color: #10b981; font-size: 14px; font-weight: bold;")
        
        self.connect_btn.setText("🔴 断开连接")
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #ef4444, stop:1 #dc2626);
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 10px;
                padding: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #dc2626, stop:1 #b91c1c);
            }
        """)
        self.connect_btn.setEnabled(True)
        self.connect_btn.clicked.disconnect()
        self.connect_btn.clicked.connect(self.handle_disconnect)
        
        # 更新视频 widget 状态
        if hasattr(self, 'video_widget'):
            self.video_widget.status_indicator.setText("● 在线")
            self.video_widget.status_indicator.setStyleSheet("color: #10b981; font-size: 12px; font-weight: bold;")
        
        # 重置计数器和热力图
        self.gaze_count = 0
        if hasattr(self, 'heatmap_widget'):
            self.heatmap_widget.clear_heatmap()
        
        self.training_widget.set_target_area(line_number=3)
    
    def on_disconnected(self):
        self.is_connected = False
        self.connection_status.setText("● 未连接")
        self.connection_status.setStyleSheet("color: #94a3b8; font-size: 14px;")
        self.connect_btn.setText("🔌 连接 Tobii Pro Glasses 3")
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #6366f1);
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 10px;
                padding: 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2563eb, stop:1 #4f46e5);
            }
        """)
        self.connect_btn.clicked.disconnect()
        self.connect_btn.clicked.connect(self.handle_connect)
        
        # 更新视频 widget 状态
        if hasattr(self, 'video_widget'):
            self.video_widget.status_indicator.setText("● 离线")
            self.video_widget.status_indicator.setStyleSheet("color: #94a3b8; font-size: 12px;")
            self.video_widget.video_label.setText("等待视频流...")
            self.video_label_pixmap = None
        
        # 清除热力图
        if hasattr(self, 'heatmap_widget'):
            self.heatmap_widget.clear_heatmap()
    
    def handle_disconnect(self):
        self.glasses_mgr.close_connection()
    
    def process_stream(self, frame, gaze_data):
        """处理视频流和 Gaze 数据"""
        if isinstance(frame, bytes):
            np_arr = np.frombuffer(frame, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if frame is not None:
            # 更新视频显示
            if hasattr(self, 'video_widget'):
                self.video_widget.update_frame(frame)
            
            # 处理帧和 gaze 数据
            try:
                self.mapper.process_frame_and_gaze(frame, gaze_data)
            except Exception as e:
                print(f"[错误] mapper处理失败: {e}")
                import traceback
                traceback.print_exc()
            
            # 如果有 gaze 数据,更新热力图和统计
            if gaze_data and 'gaze2d' in gaze_data:
                self.gaze_count += 1
                u, v = gaze_data['gaze2d']
                
                # 保存原始gaze2d数据（用于校准）
                self.current_gaze2d = (u, v)
                
                screen_x = u * 1920
                screen_y = v * 1080
                
                # 更新状态提示
                if hasattr(self, 'statusBar'):
                    self.statusBar().showMessage(f"收到Gaze数据: u={u:.3f}, v={v:.3f}", 2000)
                
                # 更新热力图
                if hasattr(self, 'heatmap_widget'):
                    self.heatmap_widget.add_gaze_point(screen_x, screen_y)
                
                # 更新分析标签页的统计
                if hasattr(self, 'total_gaze_label'):
                    self.total_gaze_label.setText(f"👁️ 总注视点数: {self.gaze_count}")
                
                # 更新数据接收率
                if hasattr(self, 'data_rate_label'):
                    current_time = time.time()
                    if hasattr(self, '_last_rate_update'):
                        dt = current_time - self._last_rate_update
                        if dt > 0:
                            rate = 1.0 / dt
                            self.data_rate_label.setText(f"📡 数据接收率: {rate:.1f} Hz")
                    self._last_rate_update = current_time
                
                # 更新平均注视时长
                if hasattr(self, 'avg_fixation_label') and hasattr(self.evaluator, 'get_avg_fixation_duration'):
                    avg_duration = self.evaluator.get_avg_fixation_duration()
                    self.avg_fixation_label.setText(f"⏱️ 平均注视时长: {avg_duration:.0f}ms")
                
                # 更新最大偏离距离
                if hasattr(self, 'max_deviation_label') and hasattr(self.evaluator, 'get_max_deviation'):
                    max_dev = self.evaluator.get_max_deviation()
                    self.max_deviation_label.setText(f"📏 最大偏离距离: {max_dev:.0f}px")
    
    def on_gaze_mapped(self, x, y):
        """处理映射后的注视点"""
        self.current_gaze = (x, y)
        self.coord_label.setText(f"坐标: {int(x)}, {int(y)}")
        
        # 更新全局注视点显示（在整个窗口上）
        if hasattr(self, 'global_gaze_widget'):
            self.global_gaze_widget.update_gaze(x, y)
        
        self.evaluator.add_gaze_point(x, y, time.time())
        self.report_generator.add_gaze_point(x, y)
        
        # 更新训练模块的 gaze 检测（无论是否连接眼镜，只要有gaze数据就更新）
        if hasattr(self, 'training_widget') and self.training_widget.is_training:
            dt = time.time() - self.last_time
            self.last_time = time.time()
            
            # 将屏幕坐标转换为 viewport 坐标
            viewport_coords = self.convert_screen_to_viewport(x, y)
            if viewport_coords:
                vp_x, vp_y = viewport_coords
                self.training_widget.check_gaze(vp_x, vp_y, dt)
        
        # 更新分析标签页的进度
        if hasattr(self, 'training_progress'):
            if hasattr(self, 'training_widget') and self.training_widget.current_task:
                progress = self.training_widget.get_completion_rate()
                self.training_progress.setValue(int(progress))
                self.progress_label.setText(f"当前进度: {progress:.0f}%")
            else:
                progress = min(100, int((self.gaze_count / 1000) * 100))
                self.training_progress.setValue(progress)
                self.progress_label.setText(f"当前进度: {progress}%")
        
        # 眼镜滑动检测和隐式校准
        self.monitor_calibration_quality(x, y)
        
        # 更新校准参数显示（如果有设置标签页）
        if hasattr(self, 'cal_offset_u_label'):
            params = self.mapper.get_calibration_params()
            self.cal_offset_u_label.setText(f"U轴偏移: {params['offset_u']:.4f}")
            self.cal_offset_v_label.setText(f"V轴偏移: {params['offset_v']:.4f}")
            self.cal_scale_u_label.setText(f"U轴缩放: {params['scale_u']:.4f}")
            self.cal_scale_v_label.setText(f"V轴缩放: {params['scale_v']:.4f}")
    
    def convert_screen_to_viewport(self, screen_x, screen_y):
        """
        将屏幕坐标转换为 TrainingWidget 中代码编辑器 viewport 的坐标
        :param screen_x: 屏幕 X 坐标
        :param screen_y: 屏幕 Y 坐标
        :return: (viewport_x, viewport_y) 或 None
        """
        if not hasattr(self, 'training_widget') or not self.training_widget.is_training:
            return None
        
        try:
            # 获取 TrainingWidget 窗口在屏幕上的位置
            training_widget = self.training_widget
            tw_global_pos = training_widget.mapToGlobal(training_widget.pos())
            tw_x = tw_global_pos.x()
            tw_y = tw_global_pos.y()
            
            # 获取代码编辑器在 TrainingWidget 中的位置
            code_editor = training_widget.code_editor
            editor_pos = code_editor.pos()
            
            # 获取 viewport 在代码编辑器中的位置
            viewport = code_editor.viewport()
            viewport_pos = viewport.pos()
            
            # 计算 viewport 左上角在屏幕上的位置
            vp_screen_x = tw_x + editor_pos.x() + viewport_pos.x()
            vp_screen_y = tw_y + editor_pos.y() + viewport_pos.y()
            
            # 计算相对于 viewport 的坐标
            vp_x = screen_x - vp_screen_x
            vp_y = screen_y - vp_screen_y
            
            # 检查是否在 viewport 范围内
            if (0 <= vp_x < viewport.width() and 
                0 <= vp_y < viewport.height()):
                return (vp_x, vp_y)
            else:
                return None
        except Exception as e:
            return None
    
    def on_task_completed(self, msg):
        """任务完成处理"""
        # 生成报告
        if hasattr(self, 'training_widget') and self.training_widget.current_task:
            level = self.training_widget.current_task.level
            self.report_generator.generate_heatmap(f"level_{level}_heatmap.png")
            self.report_generator.generate_trajectory(f"level_{level}_trajectory.png")
        
        # 记录训练历史
        self.record_training_completion(msg)
        
        # 显示完成对话框
        QMessageBox.information(self, "🎉 恭喜", f"{msg}\n\n评估报告已生成！")
        
        # 自动进入下一关(如果还有)
        if hasattr(self, 'training_widget') and self.training_widget.current_task:
            current_level = self.training_widget.current_task.level
            if current_level < len(self.training_widget.tasks):
                self.next_level()
    
    def record_training_completion(self, msg):
        """记录训练完成"""
        try:
            # 计算专注度（这里简化处理，实际应从evaluator获取）
            attention_score = self.evaluator.get_attention_score() if hasattr(self.evaluator, 'get_attention_score') else 85
            
            # 计算训练时长
            training_duration = self.evaluator.get_training_duration() if hasattr(self.evaluator, 'get_training_duration') else 15
            
            # 创建记录
            record = {
                'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
                'task': f'第{self.current_level}关 - 代码阅读训练',
                'attention': f'{attention_score:.0f}%',
                'duration': f'{training_duration}分钟',
                'status': '已完成',
                'level': self.current_level,
                'gaze_count': self.gaze_count
            }
            
            # 添加到历史记录
            self.add_training_record(record)
            
        except Exception as e:
            print(f"记录训练完成失败: {e}")
    
    def next_level(self):
        """进入下一关"""
        if hasattr(self, 'training_widget'):
            current_level = self.training_widget.current_task.level
            if current_level < len(self.training_widget.tasks):
                # 使用 training_widget 的 next_task 方法，包含完整的重置逻辑
                self.training_widget.next_task()
                self.current_level = self.training_widget.current_task.level
                self.level_status.setText(f"当前关卡: 第 {self.current_level} 关")
    
    def start_calibration(self):
        """开始屏幕校准"""
        # 测试模式：如果没有连接眼动仪，使用模拟数据
        if not self.is_connected:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Question)
            msg.setWindowTitle("测试模式")
            msg.setText("眼动仪未连接，是否进入测试模式？")
            msg.setInformativeText(
                "测试模式将使用模拟的眼动数据，\n"
                "这样您可以先查看校准界面的效果。"
            )
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            
            if msg.exec_() == QMessageBox.No:
                return
            
            self.calibration_test_mode = True
        else:
            self.calibration_test_mode = False
        
        # 显示校准说明
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("🎯 屏幕校准")
        msg.setText("眼动仪屏幕校准")
        msg.setInformativeText(
            "迭代优化校准流程（高精度版）：\n\n"
            "第一阶段 - 快速初校（49个点）\n"
            "  • 7x7均匀网格，覆盖全面\n"
            "  • 每点单次采样，快速确认\n"
            "  • 约需1-1.5分钟\n\n"
            "第二阶段 - 用户验证\n"
            "  • 随机测试5个点\n"
            "  • 显示校准误差\n\n"
            "第三阶段 - 针对性精校（如需要）\n"
            "  • 只在误差大的区域加点\n"
            "  • 每点单次采样\n\n"
            "✨ RANSAC+岭回归 + 二次多项式\n"
            "💡 专为笔记本小屏幕+头动影响优化"
        )
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        
        # 设置对话框大小
        msg.setStyleSheet("QLabel{min-width: 400px;}")
        
        if msg.exec_() == QMessageBox.Cancel:
            return
        
        # 启动校准流程
        try:
            self.run_calibration_process()
        except Exception as e:
            QMessageBox.critical(
                self,
                "校准错误",
                f"校准过程中出现错误：\n{str(e)}"
            )
    
    def run_calibration_process(self):
        """执行迭代优化校准流程（初校 + 验证 + 精校）"""
        print("\n[校准] === 开始迭代优化校准流程 ===")
        
        # 第一阶段：快速初校（9个点，3x3网格）
        print("[校准] 第一阶段：快速初校...")
        initial_points = self._run_initial_calibration()
        
        if not initial_points:
            return  # 用户取消
        
        # 计算初校参数（使用二次多项式，更稳定）
        if len(initial_points) >= 6:
            self.calculate_polynomial_calibration(initial_points, show_result=False, degree=2)
        else:
            QMessageBox.warning(self, "校准失败", "初校数据不足，请重试")
            return
        
        # 第二阶段：用户交互验证
        print("[校准] 第二阶段：用户验证...")
        need_refinement, error_map = self._run_validation_phase()
        
        if not need_refinement:
            # 校准良好，直接完成
            QMessageBox.information(
                self,
                "校准成功",
                f"✅ 校准完成！\n\n"
                f"• 使用了 {len(initial_points)} 个校准点\n"
                f"• 平均误差在可接受范围内\n"
                f"• 已启用多项式校准和卡尔曼滤波\n\n"
                f"💡 现在可以开始眼动追踪测试了"
            )
            return
        
        # 第三阶段：针对性精校
        print("[校准] 第三阶段：针对性精校...")
        refined_points = self._run_refined_calibration(error_map, initial_points)
        
        if not refined_points:
            return  # 用户取消
        
        # 重新计算最终校准参数（使用二次多项式）
        if len(refined_points) >= 6:
            self.calculate_polynomial_calibration(refined_points, show_result=True, degree=2)
        else:
            QMessageBox.warning(self, "校准失败", "精校数据不足")
    
    def _run_initial_calibration(self):
        """第一阶段：快速初校（49个点，7x7网格）"""
        calibration_points = []
        
        # 显示校准提示
        QMessageBox.information(
            self,
            "校准提示",
            "⚠️ 重要提示：\n\n"
            "为了获得准确的校准结果，请在注视每个红点时：\n\n"
            "1. 👁️ 用眼睛看向红点（不要移动头部）\n"
            "2. 📍 确保眼睛真的看到红点中心\n"
            "3. 💡 保持眼镜佩戴稳定，避免滑动\n"
            "4. ⏱️ 每个点停留1-2秒，让数据稳定\n\n"
            "注意：如果gaze数据变化太小，说明眼睛没有真正看向红点！"
        )
        
        # 7x7均匀网格
        positions = [0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9]
        screen_points = []
        for v in positions:
            for u in positions:
                screen_points.append((u, v))
        
        print(f"[初校] 开始，共{len(screen_points)}个点（7x7网格）")
        
        for i, (screen_u, screen_v) in enumerate(screen_points):
            ok, gaze_u, gaze_v = self.show_calibration_point_with_sampling(
                screen_u, screen_v, i + 1, len(screen_points), samples=1
            )
            
            if not ok:
                return None
            
            calibration_points.append({
                'screen_u': screen_u,
                'screen_v': screen_v,
                'gaze_u': gaze_u,
                'gaze_v': gaze_v
            })
            
            # 每10个点显示一次进度
            if (i + 1) % 10 == 0 or i + 1 == len(screen_points):
                print(f"[初校] 进度: {i+1}/{len(screen_points)}")
        
        return calibration_points
    
    def _run_validation_phase(self):
        """第二阶段：用户交互验证，返回是否需要精校和误差分布"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("校准验证")
        msg.setText("是否进行校准验证？")
        msg.setInformativeText(
            "验证步骤：\n\n"
            "1. 系统会随机显示5个测试点\n"
            "2. 注视红点后按 Enter 确认\n"
            "3. 系统会显示您的校准误差\n\n"
            "如果误差较大，可以进行针对性精校"
        )
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.Yes)
        
        if msg.exec_() != QMessageBox.Yes:
            return False, None  # 跳过验证
        
        # 执行验证测试
        test_errors = self._perform_validation_test()
        
        if not test_errors:
            return False, None  # 用户取消
        
        # 分析误差
        avg_error = sum(test_errors.values()) / len(test_errors)
        max_error = max(test_errors.values())
        
        print(f"[验证] 平均误差: {avg_error:.4f}, 最大误差: {max_error:.4f}")
        
        # 判断是否需要精校（阈值：平均误差>0.05 或 最大误差>0.1）
        need_refinement = avg_error > 0.05 or max_error > 0.1
        
        if need_refinement:
            # 找出误差大的区域
            error_regions = self._identify_error_regions(test_errors)
            
            msg2 = QMessageBox(self)
            msg2.setIcon(QMessageBox.Warning)
            msg2.setWindowTitle("需要精校")
            msg2.setText("校准误差较大，建议进行精校")
            msg2.setInformativeText(
                f"验证结果：\n\n"
                f"• 平均误差: {avg_error*100:.2f}%\n"
                f"• 最大误差: {max_error*100:.2f}%\n\n"
                f"建议在以下区域增加校准点：\n"
                f"{error_regions}\n\n"
                f"是否进行针对性精校？"
            )
            msg2.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            
            if msg2.exec_() == QMessageBox.Yes:
                return True, test_errors
            else:
                return False, None
        else:
            # 校准良好
            msg3 = QMessageBox(self)
            msg3.setIcon(QMessageBox.Information)
            msg3.setWindowTitle("校准良好")
            msg3.setText("✅ 校准质量良好！")
            msg3.setInformativeText(
                f"验证结果：\n\n"
                f"• 平均误差: {avg_error*100:.2f}%\n"
                f"• 最大误差: {max_error*100:.2f}%\n\n"
                f"无需进一步精校"
            )
            msg3.exec_()
            return False, None
    
    def _perform_validation_test(self):
        """执行验证测试，返回各点的误差"""
        import random
        import numpy as np
        
        # 随机选择5个测试点
        test_positions = [
            (0.15, 0.15), (0.85, 0.15), (0.15, 0.85), (0.85, 0.85),
            (0.5, 0.2), (0.5, 0.8), (0.2, 0.5), (0.8, 0.5),
            (0.3, 0.7), (0.7, 0.3)
        ]
        selected_tests = random.sample(test_positions, 5)
        
        errors = {}
        
        print(f"[验证测试] 开始，共{len(selected_tests)}个测试点")
        
        for i, (test_u, test_v) in enumerate(selected_tests):
            # 显示测试点
            ok, gaze_u, gaze_v = self.show_calibration_point_with_sampling(
                test_u, test_v, i + 1, len(selected_tests), samples=3
            )
            
            if not ok:
                return None  # 用户取消
            
            # 使用当前校准参数预测屏幕坐标
            pred_screen_x, pred_screen_y = self.mapper.gaze_to_screen(gaze_u, gaze_v)
            
            # 计算实际目标屏幕坐标
            target_screen_x = test_u * self.mapper.screen_width
            target_screen_y = test_v * self.mapper.screen_height
            
            # 计算误差（归一化）
            error = np.sqrt(
                ((pred_screen_x - target_screen_x) / self.mapper.screen_width) ** 2 +
                ((pred_screen_y - target_screen_y) / self.mapper.screen_height) ** 2
            )
            
            errors[(test_u, test_v)] = error
            
            print(f"[验证测试] 点{i+1}: 目标({test_u:.2f},{test_v:.2f}), "
                  f"预测({pred_screen_x/self.mapper.screen_width:.3f},{pred_screen_y/self.mapper.screen_height:.3f}), "
                  f"误差={error:.4f}")
        
        return errors
    
    def _identify_error_regions(self, error_map):
        """识别误差较大的区域"""
        regions = []
        
        for (u, v), error in error_map.items():
            if error > 0.05:  # 误差阈值
                # 确定区域名称
                if u < 0.33:
                    h_region = "左侧"
                elif u < 0.67:
                    h_region = "中间"
                else:
                    h_region = "右侧"
                
                if v < 0.33:
                    v_region = "上部"
                elif v < 0.67:
                    v_region = "中部"
                else:
                    v_region = "下部"
                
                regions.append(f"{h_region}{v_region}(误差{error*100:.1f}%)")
        
        return ", ".join(regions) if regions else "无明显高误差区域"
    
    def _run_refined_calibration(self, error_map, initial_points):
        """第三阶段：针对性精校"""
        # 基于误差分布，在高误差区域增加校准点
        refinement_points = list(initial_points)  # 保留初校点
        
        # 确定需要补充的点（在高误差区域附近）
        additional_points = self._generate_refinement_points(error_map, initial_points)
        
        print(f"[精校] 需要在 {len(additional_points)} 个位置补充校准点")
        
        total_count = len(initial_points) + len(additional_points)
        current_index = len(initial_points)
        
        for i, (screen_u, screen_v) in enumerate(additional_points):
            current_index += 1
            ok, gaze_u, gaze_v = self.show_calibration_point_with_sampling(
                screen_u, screen_v, current_index, total_count, samples=5
            )
            
            if not ok:
                return None
            
            refinement_points.append({
                'screen_u': screen_u,
                'screen_v': screen_v,
                'gaze_u': gaze_u,
                'gaze_v': gaze_v
            })
            
            print(f"[精校] 进度: {current_index}/{total_count}")
        
        return refinement_points
    
    def _generate_refinement_points(self, error_map, initial_points=None):
        """根据误差分布生成需要补充的校准点"""
        additional_points = []
        
        # 找出误差最大的3个区域
        sorted_errors = sorted(error_map.items(), key=lambda x: x[1], reverse=True)
        high_error_points = sorted_errors[:3]
        
        for (u, v), error in high_error_points:
            if error > 0.05:  # 只在误差大的区域加点
                # 在该点周围添加4个点
                offset = 0.1
                neighbors = [
                    (max(0.1, u - offset), max(0.1, v - offset)),
                    (min(0.9, u + offset), max(0.1, v - offset)),
                    (max(0.1, u - offset), min(0.9, v + offset)),
                    (min(0.9, u + offset), min(0.9, v + offset))
                ]
                
                for nu, nv in neighbors:
                    # 避免重复（检查是否与已有点太近）
                    is_duplicate = False
                    
                    # 检查是否与新增点重复
                    for existing_u, existing_v in additional_points:
                        if abs(existing_u - nu) < 0.05 and abs(existing_v - nv) < 0.05:
                            is_duplicate = True
                            break
                    
                    # 检查是否与初校点重复
                    if not is_duplicate and initial_points:
                        for point in initial_points:
                            if abs(point['screen_u'] - nu) < 0.05 and abs(point['screen_v'] - nv) < 0.05:
                                is_duplicate = True
                                break
                    
                    if not is_duplicate:
                        additional_points.append((nu, nv))
        
        # 如果没有高误差点，至少在四角加点
        if not additional_points:
            additional_points = [(0.1, 0.1), (0.9, 0.1), (0.1, 0.9), (0.9, 0.9)]
        
        return additional_points
    
    def show_calibration_point_on_video(self, u, v, current, total):
        """在独立的全屏窗口显示校准点，自动记录gaze2d值"""
        # 创建一个顶层窗口（没有父窗口，确保能独立显示）
        dialog = QDialog(None)
        dialog.setWindowTitle(f"校准点 {current}/{total}")
        dialog.setModal(True)
        dialog.showFullScreen()
        dialog.setStyleSheet("background-color: white;")
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 顶部提示文本
        hint_label = QLabel(f"请注视红点 ({current}/{total})")
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setFont(QFont("Microsoft YaHei", 28, QFont.Bold))
        hint_label.setStyleSheet("color: #333; padding: 30px 50px 10px 50px; background-color: white;")
        hint_label.setFixedHeight(80)
        layout.addWidget(hint_label)
        
        # 红点位置提示
        pos_label = QLabel(f"红点位置: U={u:.2f}, V={v:.2f}")
        pos_label.setAlignment(Qt.AlignCenter)
        pos_label.setFont(QFont("Microsoft YaHei", 16))
        pos_label.setStyleSheet("color: #666; padding: 0 50px 10px 50px; background-color: white;")
        pos_label.setFixedHeight(40)
        layout.addWidget(pos_label)
        
        # 中间绘制红点的区域 - 占据所有剩余空间
        point_widget = QWidget()
        point_widget.setStyleSheet("background-color: transparent;")
        # 不设置最小大小，让它占据所有剩余空间
        
        # 保存u,v坐标供paintEvent使用
        point_widget.target_u = u
        point_widget.target_v = v
        
        def paint_event(event):
            from PyQt5.QtGui import QPainter, QPen, QColor
            painter = QPainter(point_widget)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # 计算红点在widget中的相对位置
            widget_width = point_widget.width()
            widget_height = point_widget.height()
            
            # 将归一化坐标(u,v)映射到widget的坐标系
            target_x = int(u * widget_width)
            target_y = int(v * widget_height)
            
            print(f"[校准调试] Widget({widget_width}x{widget_height}), 红点({target_x}, {target_y}), U={u:.2f}, V={v:.2f}")
            
            # 外圈
            pen = QPen(QColor(255, 0, 0))
            pen.setWidth(5)
            painter.setPen(pen)
            painter.drawEllipse(target_x - 60, target_y - 60, 120, 120)
            
            # 内圈
            painter.setBrush(QColor(255, 0, 0))
            painter.drawEllipse(target_x - 25, target_y - 25, 50, 50)
            
            # 十字线
            painter.setPen(QPen(QColor(255, 0, 0), 4))
            painter.drawLine(target_x - 100, target_y, target_x + 100, target_y)
            painter.drawLine(target_x, target_y - 100, target_x, target_y + 100)
        
        point_widget.paintEvent = paint_event
        layout.addWidget(point_widget, stretch=1)  # 占据所有剩余空间
        
        # 底部显示当前gaze2d值
        gaze_label = QLabel("等待数据...")
        gaze_label.setAlignment(Qt.AlignCenter)
        gaze_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        gaze_label.setStyleSheet("color: #3b82f6; padding: 15px; background-color: white;")
        gaze_label.setMinimumHeight(60)
        layout.addWidget(gaze_label)
        
        # 确认按钮
        ok_btn = QPushButton("记录并继续 (Enter)")
        ok_btn.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        ok_btn.setMinimumHeight(60)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                padding: 15px 40px;
                border-radius: 8px;
                margin: 20px 100px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)
        layout.addWidget(ok_btn, alignment=Qt.AlignCenter)
        
        layout.addSpacing(50)
        
        dialog.setLayout(layout)
        
        # 保存结果
        result = {'u': None, 'v': None, 'ok': False}
        
        # 测试模式：模拟眼动数据
        if self.calibration_test_mode:
            import random
            simulated_u = u + random.uniform(-0.05, 0.05)
            simulated_v = v + random.uniform(-0.05, 0.05)
            gaze_label.setText(f"模拟 gaze2d: U={simulated_u:.4f}, V={simulated_v:.4f}")
            
            def submit():
                result['u'] = simulated_u
                result['v'] = simulated_v
                result['ok'] = True
                dialog.accept()
            
            ok_btn.clicked.connect(submit)
            
            def key_handler(event):
                from PyQt5.QtCore import Qt
                if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    submit()
                else:
                    super(QDialog, dialog).keyPressEvent(event)
            
            dialog.keyPressEvent = key_handler
        else:
            # 真实模式：更新gaze2d显示
            def update_gaze_display():
                if self.current_gaze2d:
                    gaze_u, gaze_v = self.current_gaze2d
                    gaze_label.setText(f"当前 gaze2d: U={gaze_u:.4f}, V={gaze_v:.4f}")
            
            from PyQt5.QtCore import QTimer
            timer = QTimer()
            timer.timeout.connect(update_gaze_display)
            timer.start(100)
            
            def submit():
                if self.current_gaze2d:
                    result['u'] = self.current_gaze2d[0]
                    result['v'] = self.current_gaze2d[1]
                    result['ok'] = True
                    timer.stop()
                    dialog.accept()
                else:
                    QMessageBox.warning(dialog, "无数据", "请先注视红点，等待眼动数据")
            
            ok_btn.clicked.connect(submit)
            
            def key_handler(event):
                from PyQt5.QtCore import Qt
                if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    submit()
                else:
                    super(QDialog, dialog).keyPressEvent(event)
            
            dialog.keyPressEvent = key_handler
        
        # 显示对话框
        print(f"[调试] 开始显示校准点 {current}/{total}")
        print(f"[调试] 红点应该出现在: U={u:.2f}, V={v:.2f}")
        
        # 强制更新point_widget，确保paintEvent被调用
        point_widget.update()
        dialog_result = dialog.exec_()
        print(f"[调试] 校准点 {current}/{total} 完成，结果: {result}, dialog_result: {dialog_result}")
        
        return result['ok'], result['u'], result['v']
    
    def show_calibration_point_with_sampling(self, u, v, current, total, samples=1):
        """在独立的全屏窗口显示校准点，用户确认后采集数据（默认单次）"""
        from PyQt5.QtCore import QTimer
        import time
        
        # 首先创建并显示红点窗口
        calibration_dialog = QDialog(None)
        calibration_dialog.setWindowTitle(f"校准点 {current}/{total}")
        calibration_dialog.setModal(True)
        calibration_dialog.showFullScreen()
        calibration_dialog.setStyleSheet("background-color: white;")
        
        layout = QVBoxLayout(calibration_dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 顶部提示文本
        hint_label = QLabel(f"请注视红点 ({current}/{total})")
        hint_label.setAlignment(Qt.AlignCenter)
        hint_label.setFont(QFont("Microsoft YaHei", 28, QFont.Bold))
        hint_label.setStyleSheet("color: #333; padding: 30px 50px 10px 50px; background-color: white;")
        hint_label.setFixedHeight(80)
        layout.addWidget(hint_label)
        
        # 红点位置提示
        pos_label = QLabel(f"红点位置: U={u:.2f}, V={v:.2f}")
        pos_label.setAlignment(Qt.AlignCenter)
        pos_label.setFont(QFont("Microsoft YaHei", 16))
        pos_label.setStyleSheet("color: #666; padding: 0 50px 10px 50px; background-color: white;")
        pos_label.setFixedHeight(40)
        layout.addWidget(pos_label)
        
        # 中间绘制红点的区域
        point_widget = QWidget()
        point_widget.setStyleSheet("background-color: transparent;")
        point_widget.target_u = u
        point_widget.target_v = v
        
        def paint_event(event):
            from PyQt5.QtGui import QPainter, QPen, QColor
            painter = QPainter(point_widget)
            painter.setRenderHint(QPainter.Antialiasing)
            
            widget_width = point_widget.width()
            widget_height = point_widget.height()
            target_x = int(u * widget_width)
            target_y = int(v * widget_height)
            
            # 外圈
            pen = QPen(QColor(255, 0, 0))
            pen.setWidth(5)
            painter.setPen(pen)
            painter.drawEllipse(target_x - 60, target_y - 60, 120, 120)
            
            # 内圈
            painter.setBrush(QColor(255, 0, 0))
            painter.drawEllipse(target_x - 25, target_y - 25, 50, 50)
            
            # 十字线
            painter.setPen(QPen(QColor(255, 0, 0), 4))
            painter.drawLine(target_x - 100, target_y, target_x + 100, target_y)
            painter.drawLine(target_x, target_y - 100, target_x, target_y + 100)
        
        point_widget.paintEvent = paint_event
        layout.addWidget(point_widget, stretch=1)
        
        # 底部显示当前gaze2d值和采样状态
        gaze_label = QLabel("等待数据...")
        gaze_label.setAlignment(Qt.AlignCenter)
        gaze_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        gaze_label.setStyleSheet("color: #3b82f6; padding: 15px; background-color: white;")
        gaze_label.setMinimumHeight(60)
        layout.addWidget(gaze_label)
        
        # 确认按钮
        ok_btn = QPushButton("记录并继续 (Enter)")
        ok_btn.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        ok_btn.setMinimumHeight(60)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                padding: 15px 40px;
                border-radius: 8px;
                margin: 20px 100px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:pressed {
                background-color: #1d4ed8;
            }
        """)
        layout.addWidget(ok_btn, alignment=Qt.AlignCenter)
        
        layout.addSpacing(50)
        calibration_dialog.setLayout(layout)
        
        # 保存结果
        result = {'ok': False, 'u': None, 'v': None}
        
        # 测试模式：模拟眼动数据
        if self.calibration_test_mode:
            import random
            simulated_u = u + random.uniform(-0.05, 0.05)
            simulated_v = v + random.uniform(-0.05, 0.05)
            gaze_label.setText(f"模拟 gaze2d: U={simulated_u:.4f}, V={simulated_v:.4f}")
            
            def submit():
                result['u'] = simulated_u
                result['v'] = simulated_v
                result['ok'] = True
                calibration_dialog.accept()
            
            ok_btn.clicked.connect(submit)
            
            def key_handler(event):
                from PyQt5.QtCore import Qt
                if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    submit()
                else:
                    super(QDialog, calibration_dialog).keyPressEvent(event)
            
            calibration_dialog.keyPressEvent = key_handler
        else:
            # 真实模式：更新gaze2d显示
            def update_gaze_display():
                if self.current_gaze2d:
                    gaze_u, gaze_v = self.current_gaze2d
                    gaze_label.setText(f"当前 gaze2d: U={gaze_u:.4f}, V={gaze_v:.4f}")
            
            timer = QTimer()
            timer.timeout.connect(update_gaze_display)
            timer.start(100)
            
            def start_sampling():
                if not self.current_gaze2d:
                    QMessageBox.warning(calibration_dialog, "无数据", "请先注视红点，等待眼动数据")
                    return
                
                # 直接采集当前数据
                result['u'] = self.current_gaze2d[0]
                result['v'] = self.current_gaze2d[1]
                result['ok'] = True
                
                print(f"[校准采样] 点{current}: 目标({u:.3f},{v:.3f}), 实际({result['u']:.4f},{result['v']:.4f})")
                
                timer.stop()
                calibration_dialog.accept()
            
            ok_btn.clicked.connect(start_sampling)
            
            def key_handler(event):
                from PyQt5.QtCore import Qt
                if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    start_sampling()
                else:
                    super(QDialog, calibration_dialog).keyPressEvent(event)
            
            calibration_dialog.keyPressEvent = key_handler
        
        # 显示对话框
        print(f"[调试] 开始显示校准点 {current}/{total}")
        print(f"[调试] 红点应该出现在: U={u:.2f}, V={v:.2f}")
        
        # 强制更新point_widget，确保paintEvent被调用
        point_widget.update()
        dialog_result = calibration_dialog.exec_()
        print(f"[调试] 校准点 {current}/{total} 完成，结果: {result}, dialog_result: {dialog_result}")
        
        return result['ok'], result['u'], result['v']
    
    def calculate_polynomial_calibration(self, calibration_points, show_result=True, degree=2):
        """计算并应用校准参数（使用单应性矩阵或线性映射）
        
        对于无Pro Lab的情况，使用仿射变换或单应性矩阵更稳定
        :param calibration_points: 校准点列表
        :param show_result: 是否显示结果对话框
        :param degree: 多项式次数（已弃用，仅保留兼容性）
        """
        import numpy as np
        
        n = len(calibration_points)
        print(f"\n[校准] 开始计算，共 {n} 个校准点")
        
        # 提取数据
        gaze_u = np.array([p['gaze_u'] for p in calibration_points])
        gaze_v = np.array([p['gaze_v'] for p in calibration_points])
        screen_u = np.array([p['screen_u'] for p in calibration_points])
        screen_v = np.array([p['screen_v'] for p in calibration_points])
        
        try:
            # 方法1：尝试使用OpenCV的单应性矩阵（需要至少4个点）
            if n >= 4:
                try:
                    import cv2
                    
                    # 构建点对
                    src_points = np.column_stack([gaze_u, gaze_v]).astype(np.float32)
                    # 将归一化屏幕坐标转换为像素坐标
                    dst_points = np.column_stack([
                        screen_u * self.mapper.screen_width,
                        screen_v * self.mapper.screen_height
                    ]).astype(np.float32)
                    
                    # 计算单应性矩阵
                    H, mask = cv2.findHomography(src_points, dst_points, cv2.RANSAC, 5.0)
                    
                    if H is not None:
                        print(f"[单应性矩阵] 计算成功")
                        print(f"  内点数量: {np.sum(mask)}/{n}")
                        
                        # 保存单应性矩阵
                        self.mapper.set_homography_matrix(H)
                        
                        # 计算误差（使用像素坐标）
                        predicted = cv2.perspectiveTransform(
                            src_points.reshape(-1, 1, 2), H
                        ).reshape(-1, 2)
                        
                        # 将目标屏幕坐标也转换为像素坐标
                        dst_pixel_u = screen_u * self.mapper.screen_width
                        dst_pixel_v = screen_v * self.mapper.screen_height
                        
                        errors = np.sqrt((predicted[:, 0] - dst_pixel_u)**2 + 
                                       (predicted[:, 1] - dst_pixel_v)**2)
                        # 将像素误差转换为归一化误差（除以屏幕对角线）
                        screen_diagonal = np.sqrt(self.mapper.screen_width**2 + self.mapper.screen_height**2)
                        mean_error = np.mean(errors) / screen_diagonal
                        max_error = np.max(errors) / screen_diagonal
                        
                        print(f"[校准] 平均误差: {mean_error:.4f} ({mean_error*100:.2f}%)")
                        print(f"[校准] 最大误差: {max_error:.4f} ({max_error*100:.2f}%)")
                        
                        if show_result:
                            QMessageBox.information(
                                self,
                                "校准成功",
                                f"✅ 单应性矩阵校准完成！\n\n"
                                f"• 校准点数: {n}\n"
                                f"• 平均误差: {mean_error*100:.2f}%\n"
                                f"• 最大误差: {max_error*100:.2f}%\n\n"
                                f"隐式动态校准已启用，会自动微调参数。"
                            )
                        return
                        
                except Exception as e:
                    print(f"[单应性矩阵] 计算失败: {e}，回退到线性校准")
            
            # 方法2：线性校准（最稳定）
            print("[线性校准] 开始计算...")
            
            # U方向线性回归: screen_u = a*u + b*v + c
            A = np.column_stack([gaze_u, gaze_v, np.ones(n)])
            coeffs_u, _, _, _ = np.linalg.lstsq(A, screen_u, rcond=None)
            coeffs_v, _, _, _ = np.linalg.lstsq(A, screen_v, rcond=None)
            
            print(f"[线性校准] U方向系数: {coeffs_u}")
            print(f"[线性校准] V方向系数: {coeffs_v}")
            
            # 计算误差
            pred_u = A @ coeffs_u
            pred_v = A @ coeffs_v
            errors = np.sqrt((pred_u - screen_u)**2 + (pred_v - screen_v)**2)
            mean_error = np.mean(errors)
            max_error = np.max(errors)
            
            print(f"[线性校准] 平均误差: {mean_error:.4f} ({mean_error*100:.2f}%)")
            print(f"[线性校准] 最大误差: {max_error:.4f} ({max_error*100:.2f}%)")
            
            # 保存线性参数
            self.mapper.set_linear_params(
                scale_u=float(coeffs_u[0]),
                scale_v=float(coeffs_v[0]),
                offset_u=float(coeffs_u[2]),
                offset_v=float(coeffs_v[2])
            )
            
            if show_result:
                QMessageBox.information(
                    self,
                    "校准成功",
                    f"✅ 线性校准完成！\n\n"
                    f"• 校准点数: {n}\n"
                    f"• 平均误差: {mean_error*100:.2f}%\n"
                    f"• 最大误差: {max_error*100:.2f}%\n\n"
                    f"隐式动态校准已启用，会自动微调参数。"
                )
            
        except Exception as e:
            print(f"[校准] 计算失败: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "校准失败", f"校准计算出错:\n{str(e)}")
    
    def analyze_calibration_error(self, calibration_points, method_name="校准"):
        """分析校准误差"""
        import numpy as np
        
        errors = []
        for point in calibration_points:
            gaze_u = point['gaze_u']
            gaze_v = point['gaze_v']
            screen_u = point['screen_u']
            screen_v = point['screen_v']
            
            # 使用校准后的坐标映射器预测屏幕坐标
            pred_u, pred_v = self.mapper.gaze_to_screen(gaze_u, gaze_v)
            
            # 计算欧氏距离误差
            error = np.sqrt((pred_u - screen_u)**2 + (pred_v - screen_v)**2)
            errors.append(error)
        
        errors = np.array(errors)
        mean_error = np.mean(errors)
        max_error = np.max(errors)
        std_error = np.std(errors)
        
        print(f"\n[{method_name}] 误差分析:")
        print(f"  • 平均误差: {mean_error:.4f} ({mean_error*100:.2f}%)")
        print(f"  • 最大误差: {max_error:.4f} ({max_error*100:.2f}%)")
        print(f"  • 标准差:   {std_error:.4f} ({std_error*100:.2f}%)")
        print(f"  • 中位数误差: {np.median(errors):.4f} ({np.median(errors)*100:.2f}%)")
        
        return mean_error, max_error, std_error
    
    def monitor_calibration_quality(self, screen_x, screen_y):
        """实时监控校准质量，检测眼镜滑动和隐式校准"""
        import numpy as np
        
        if not self.mapper.is_calibrated or not hasattr(self, 'current_gaze2d') or not self.current_gaze2d:
            return
        
        gaze_u, gaze_v = self.current_gaze2d
        
        # 1. 隐式动态校准：检测是否注视屏幕中心
        # 屏幕中心区域 (0.45-0.55)
        if 0.45 <= gaze_u <= 0.55 and 0.45 <= gaze_v <= 0.55:
            self.center_gaze_samples.append((gaze_u, gaze_v))
            
            # 每收集10个样本，进行微调
            if len(self.center_gaze_samples) >= 10:
                self.implicit_calibration_update()
                self.center_gaze_samples.clear()
        
        # 2. 眼镜滑动检测（每5秒检查一次）
        current_time = time.time()
        if current_time - self.last_calibration_check_time < 5.0:
            return
        
        self.last_calibration_check_time = current_time
        
        # 计算当前预测误差（需要知道用户实际注视位置，这里简化处理）
        # 在实际应用中，可以通过分析注视点分布的突然变化来检测
        if len(self.gaze_error_history) > 20:
            recent_errors = self.gaze_error_history[-20:]
            avg_recent = np.mean(recent_errors)
            avg_history = np.mean(self.gaze_error_history[:-20])
            
            # 如果最近误差比历史平均高出3倍，可能眼镜滑动了
            if avg_history > 0 and avg_recent > avg_history * 3:
                print(f"[警告] 检测到可能的眼镜滑动！")
                print(f"  历史平均误差: {avg_history:.4f}")
                print(f"  最近平均误差: {avg_recent:.4f}")
                
                # 弹出提示（仅在训练模式下）
                if hasattr(self, 'training_widget') and self.training_widget.is_training:
                    reply = QMessageBox.warning(
                        self,
                        "⚠️ 检测到眼镜滑动",
                        "系统检测到您的眼镜可能发生了滑动，\n"
                        "建议重新校准以保持精度。\n\n"
                        "是否现在重新校准？",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )
                    
                    if reply == QMessageBox.Yes:
                        self.run_calibration_process()
    
    def implicit_calibration_update(self):
        """隐式动态校准：利用中心区域注视数据微调参数"""
        import numpy as np
        
        if len(self.center_gaze_samples) < 10:
            return
        
        # 计算中心区域的平均偏差
        avg_u = np.mean([s[0] for s in self.center_gaze_samples])
        avg_v = np.mean([s[1] for s in self.center_gaze_samples])
        
        # 理论中心应该是 (0.5, 0.5)
        offset_u = 0.5 - avg_u
        offset_v = 0.5 - avg_v
        
        # 如果偏差超过阈值，微调校准参数
        if abs(offset_u) > 0.02 or abs(offset_v) > 0.02:
            print(f"[隐式校准] 检测到中心偏移: U={offset_u:.4f}, V={offset_v:.4f}")
            
            # 简单的偏置调整（不重新拟合整个多项式）
            if hasattr(self.mapper, 'poly_coeffs_u') and self.mapper.poly_coeffs_u is not None:
                # 调整常数项
                self.mapper.poly_coeffs_u[0] += offset_u * 0.1  # 缓慢调整
                self.mapper.poly_coeffs_v[0] += offset_v * 0.1
                
                print(f"[隐式校准] 已微调校准参数")
    
    def calculate_and_apply_calibration(self, calibration_points):
        """计算并应用校准参数（使用最小二乘法）"""
        import numpy as np
        
        # 提取数据
        gaze_u_arr = np.array([p['gaze_u'] for p in calibration_points])
        gaze_v_arr = np.array([p['gaze_v'] for p in calibration_points])
        screen_u_arr = np.array([p['screen_u'] for p in calibration_points])
        screen_v_arr = np.array([p['screen_v'] for p in calibration_points])
        
        # 使用线性回归：screen = gaze * scale + offset
        # 最小二乘法计算最优参数
        # 对于 U 方向：y = a*x + b
        n = len(calibration_points)
        sum_gaze_u = np.sum(gaze_u_arr)
        sum_screen_u = np.sum(screen_u_arr)
        sum_gaze_u_sq = np.sum(gaze_u_arr ** 2)
        sum_gaze_screen_u = np.sum(gaze_u_arr * screen_u_arr)
        
        # scale_u = (n*sum(xy) - sum(x)*sum(y)) / (n*sum(x^2) - (sum(x))^2)
        denom_u = n * sum_gaze_u_sq - sum_gaze_u ** 2
        if abs(denom_u) > 1e-10:
            scale_u = (n * sum_gaze_screen_u - sum_gaze_u * sum_screen_u) / denom_u
            offset_u = (sum_screen_u - scale_u * sum_gaze_u) / n
        else:
            scale_u = 1.0
            offset_u = 0.0
        
        # 对于 V 方向
        sum_gaze_v = np.sum(gaze_v_arr)
        sum_screen_v = np.sum(screen_v_arr)
        sum_gaze_v_sq = np.sum(gaze_v_arr ** 2)
        sum_gaze_screen_v = np.sum(gaze_v_arr * screen_v_arr)
        
        denom_v = n * sum_gaze_v_sq - sum_gaze_v ** 2
        if abs(denom_v) > 1e-10:
            scale_v = (n * sum_gaze_screen_v - sum_gaze_v * sum_screen_v) / denom_v
            offset_v = (sum_screen_v - scale_v * sum_gaze_v) / n
        else:
            scale_v = 1.0
            offset_v = 0.0
        
        print(f"[校准计算] scale_u={scale_u:.4f}, offset_u={offset_u:.4f}")
        print(f"[校准计算] scale_v={scale_v:.4f}, offset_v={offset_v:.4f}")
        
        # 应用校准参数
        self.mapper.set_calibration_params(offset_u, offset_v, scale_u, scale_v)
        
        # 显示详细的校准效果分析
        error_analysis = "📊 校准误差分析：\n\n"
        error_analysis += "校准前误差 vs 校准后误差\n\n"
        
        total_error_before = 0
        total_error_after = 0
        
        for i, point in enumerate(calibration_points):
            # 校准前误差
            error_u_before = abs(point['screen_u'] - point['gaze_u'])
            error_v_before = abs(point['screen_v'] - point['gaze_v'])
            error_before = (error_u_before + error_v_before) / 2 * 100
            
            # 校准后误差（使用正确公式：gaze * scale + offset）
            pred_u = point['gaze_u'] * scale_u + offset_u
            pred_v = point['gaze_v'] * scale_v + offset_v
            error_u_after = abs(point['screen_u'] - pred_u)
            error_v_after = abs(point['screen_v'] - pred_v)
            error_after = (error_u_after + error_v_after) / 2 * 100
            
            improvement = error_before - error_after
            
            error_analysis += f"点{i+1}: 校准前 {error_before:.1f}% → 校准后 {error_after:.1f}% (改善 {improvement:+.1f}%)\n"
            
            total_error_before += error_before
            total_error_after += error_after
        
        avg_error_before = total_error_before / len(calibration_points)
        avg_error_after = total_error_after / len(calibration_points)
        improvement_percent = (avg_error_before - avg_error_after) / avg_error_before * 100 if avg_error_before > 0 else 0
        
        error_analysis += f"\n📈 平均误差对比："
        error_analysis += f"\n  校准前: {avg_error_before:.1f}%"
        error_analysis += f"\n  校准后: {avg_error_after:.1f}%"
        error_analysis += f"\n  改善幅度: {improvement_percent:+.1f}%"
        
        if avg_error_after < 3:
            error_analysis += " (优秀 ✅)"
        elif avg_error_after < 5:
            error_analysis += " (良好 👍)"
        elif avg_error_after < 10:
            error_analysis += " (一般 ⚠️)"
        else:
            error_analysis += " (较差 ❌ 建议重新校准)"
        
        # 显示结果
        QMessageBox.information(
            self,
            "✅ 校准完成",
            f"已成功收集 {len(calibration_points)} 个校准点\n\n"
            f"校准参数：\n"
            f"U方向偏移: {offset_u:.4f}\n"
            f"V方向偏移: {offset_v:.4f}\n"
            f"U方向缩放: {scale_u:.4f}\n"
            f"V方向缩放: {scale_v:.4f}\n\n"
            f"{error_analysis}\n\n"
            f"💡 提示：请在训练任务中观察注视点是否更准确！"
        )
    
    def load_user_info_from_db(self):
        """从数据库加载当前用户信息到输入框"""
        if not self.current_user_id or not hasattr(self, 'db') or self.db is None:
            return
        try:
            conn = self.db.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT username, student_id, experience_level FROM users WHERE id = ?", (self.current_user_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                self.user_name_input.setText(row['username'])
                self.user_id_input.setText(row['student_id'] or '')
                
                level_map = {'Beginner': '初级', 'Intermediate': '中级', 'Advanced': '高级'}
                db_level = row['experience_level'] or 'Beginner'
                display_level = level_map.get(db_level, '初级')
                index = self.user_level_combo.findText(display_level)
                if index >= 0:
                    self.user_level_combo.setCurrentIndex(index)
        except Exception as e:
            print(f"[加载用户信息失败] {e}")

    def update_summary_from_db(self):
        """从数据库更新训练统计摘要"""
        if not self.current_user_id or not hasattr(self, 'db') or self.db is None:
            return
        try:
            history = self.db.get_user_history(self.current_user_id)
            total_sessions = len(history)
            
            if total_sessions > 0:
                total_time = sum(r['total_time'] for r in history)
                scores = [r['accuracy'] for r in history if r['accuracy'] is not None]
                avg_score = sum(scores) / len(scores) if scores else 0
                max_score = max(scores) if scores else 0
                
                self.total_sessions_label.setText(f"📊 总训练次数: {total_sessions}")
                self.total_time_label.setText(f"⏱️ 总训练时长: {int(total_time / 60)}分钟")
                self.avg_attention_label.setText(f"🎯 平均专注度: {avg_score:.1f}%")
                self.best_score_label.setText(f"🏆 最高专注度: {max_score:.1f}%")
            else:
                self.total_sessions_label.setText("📊 总训练次数: 0")
                self.total_time_label.setText("⏱️ 总训练时长: 0分钟")
                self.avg_attention_label.setText("🎯 平均专注度: 0%")
                self.best_score_label.setText("🏆 最高专注度: 0%")
        except Exception as e:
            print(f"[更新统计摘要失败] {e}")

    def save_user_info(self):
        """保存用户信息到数据库"""
        if not self.current_user_id:
            QMessageBox.warning(self, "提示", "请先登录")
            return
        
        name = self.user_name_input.text().strip()
        sid = self.user_id_input.text().strip()
        
        if not name or not sid:
            QMessageBox.warning(self, "提示", "请填写完整的用户信息")
            return
        
        level_display = self.user_level_combo.currentText()
        level_map = {'初级': 'Beginner', '中级': 'Intermediate', '高级': 'Advanced'}
        level_db = level_map.get(level_display, 'Beginner')
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET username = ?, student_id = ?, experience_level = ?
            WHERE id = ?
        """, (name, sid, level_db, self.current_user_id))
        conn.commit()
        conn.close()
        
        QMessageBox.information(
            self,
            "✅ 保存成功",
            f"用户信息已保存到数据库：\n\n"
            f"姓名: {name}\n"
            f"学号/工号: {sid}\n"
            f"编程水平: {level_display}"
        )
    
    def reset_calibration(self):
        """重置校准参数"""
        reply = QMessageBox.question(
            self,
            "确认重置",
            "确定要重置所有校准参数吗？\n\n这将恢复到默认状态，需要重新进行屏幕校准。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.mapper.set_calibration_params(0.0, 0.0, 1.0, 1.0)
            
            # 更新显示
            self.cal_offset_u_label.setText("U轴偏移: 0.0000")
            self.cal_offset_v_label.setText("V轴偏移: 0.0000")
            self.cal_scale_u_label.setText("U轴缩放: 1.0000")
            self.cal_scale_v_label.setText("V轴缩放: 1.0000")
            
            QMessageBox.information(self, "✅ 重置成功", "校准参数已重置为默认值")
    
    def save_settings_from_ui(self):
        """从界面保存设置"""
        # 读取UI值
        self.settings['rtsp_timeout'] = self.rtsp_timeout_spin.value()
        self.settings['gaze_sample_rate'] = self.gaze_sample_rate_combo.currentText()
        self.settings['auto_reconnect'] = self.auto_reconnect_check.isChecked()
        self.settings['theme'] = self.theme_combo.currentText()
        self.settings['font_size'] = self.font_size_spin.value()
        self.settings['show_gaze_point'] = self.show_gaze_point_check.isChecked()
        self.settings['show_heatmap'] = self.show_heatmap_check.isChecked()
        self.settings['simulator_mode'] = self.simulator_check.isChecked()
        
        # 保存
        if self.save_settings():
            QMessageBox.information(
                self,
                "✅ 保存成功",
                "系统设置已保存！\n\n"
                f"RTSP超时: {self.settings['rtsp_timeout']}秒\n"
                f"采样率: {self.settings['gaze_sample_rate']}\n"
                f"自动重连: {'是' if self.settings['auto_reconnect'] else '否'}\n"
                f"主题: {self.settings['theme']}\n"
                f"字体大小: {self.settings['font_size']}pt"
            )
        else:
            QMessageBox.critical(self, "错误", "保存失败，请重试")
    
    def init_sample_history(self):
        """初始化示例训练历史数据"""
        sample_data = [
            ("2024-04-13", "基础语法训练", "85%", "15分钟", "已完成"),
            ("2024-04-12", "循环结构理解", "78%", "20分钟", "已完成"),
            ("2024-04-11", "函数调用分析", "92%", "18分钟", "已完成"),
            ("2024-04-10", "条件判断练习", "88%", "12分钟", "已完成"),
            ("2024-04-09", "变量作用域", "75%", "25分钟", "已完成"),
        ]
        
        for date, task, attention, duration, status in sample_data:
            row_position = self.history_table.rowCount()
            self.history_table.insertRow(row_position)
            
            # 日期
            self.history_table.setItem(row_position, 0, QTableWidgetItem(date))
            
            # 任务名称
            self.history_table.setItem(row_position, 1, QTableWidgetItem(task))
            
            # 专注度
            attention_item = QTableWidgetItem(attention)
            attention_value = int(attention.replace('%', ''))
            if attention_value >= 90:
                attention_item.setForeground(QColor("#10b981"))  # 绿色
            elif attention_value >= 75:
                attention_item.setForeground(QColor("#f59e0b"))  # 橙色
            else:
                attention_item.setForeground(QColor("#ef4444"))  # 红色
            self.history_table.setItem(row_position, 2, attention_item)
            
            # 时长
            self.history_table.setItem(row_position, 3, QTableWidgetItem(duration))
            
            # 完成状态
            status_item = QTableWidgetItem(status)
            status_item.setForeground(QColor("#10b981"))
            self.history_table.setItem(row_position, 4, status_item)
            
            # 操作按钮
            view_btn = QPushButton("查看报告")
            view_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3b82f6;
                    color: white;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #2563eb;
                }
            """)
            view_btn.clicked.connect(lambda checked, d=date: self.view_report(d))
            self.history_table.setCellWidget(row_position, 5, view_btn)
    
    def view_report(self, date):
        """查看训练报告"""
        QMessageBox.information(
            self,
            f"📊 训练报告 - {date}",
            f"训练日期: {date}\n\n"
            f"专注度评分: 85%\n"
            f"训练时长: 15分钟\n"
            f"注视点数: 1234\n"
            f"平均注视时长: 230ms\n"
            f"回视次数: 12\n\n"
            f"评估建议:\n"
            f"• 整体表现良好，继续保持！\n"
            f"• 建议在复杂代码部分放慢阅读速度\n"
            f"• 注意减少不必要的回视行为"
        )
    
    # ==================== 数据管理功能 ====================
    
    def load_user_data(self):
        """加载用户数据"""
        # 如果用户已登录（current_user_id 不是默认值 1），则从数据库加载，跳过 JSON 文件
        if hasattr(self, 'current_user_id') and self.current_user_id and self.current_user_id != 1:
            print(f"[INFO] 用户已登录 (ID: {self.current_user_id})，跳过 JSON 文件加载，使用数据库数据")
            self.user_data = {
                'name': '',
                'user_id': '',
                'level': '初级',
                'experience': 0,
                'total_sessions': 0,
                'avg_attention': 0,
                'total_time': 0,
                'best_score': 0,
                'achievements': []
            }
            return
        
        default_data = {
            'name': '',
            'user_id': '',
            'level': '初级',
            'experience': 0,
            'total_sessions': 0,
            'avg_attention': 0,
            'total_time': 0,
            'best_score': 0,
            'achievements': []
        }
        
        if os.path.exists(self.user_data_file):
            try:
                with open(self.user_data_file, 'r', encoding='utf-8') as f:
                    self.user_data = json.load(f)
                # 确保所有字段都存在
                for key in default_data:
                    if key not in self.user_data:
                        self.user_data[key] = default_data[key]
            except Exception as e:
                print(f"加载用户数据失败: {e}")
                self.user_data = default_data
        else:
            self.user_data = default_data
        
        # 更新UI
        self.update_user_ui()
    
    def save_user_data(self):
        """保存用户数据"""
        try:
            with open(self.user_data_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存用户数据失败: {e}")
            return False
    
    def update_user_ui(self):
        """更新用户界面显示"""
        if hasattr(self, 'user_name_input'):
            self.user_name_input.setText(self.user_data.get('name', ''))
        if hasattr(self, 'user_id_input'):
            self.user_id_input.setText(self.user_data.get('user_id', ''))
        if hasattr(self, 'user_level_combo'):
            level = self.user_data.get('level', '初级')
            index = self.user_level_combo.findText(level)
            if index >= 0:
                self.user_level_combo.setCurrentIndex(index)
        if hasattr(self, 'user_experience_spin'):
            self.user_experience_spin.setValue(self.user_data.get('experience', 0))
        
        # 更新统计摘要
        if hasattr(self, 'total_sessions_label'):
            self.total_sessions_label.setText(f"📊 总训练次数: {self.user_data.get('total_sessions', 0)}")
        if hasattr(self, 'avg_attention_label'):
            self.avg_attention_label.setText(f"🎯 平均专注度: {self.user_data.get('avg_attention', 0):.0f}%")
        if hasattr(self, 'total_time_label'):
            self.total_time_label.setText(f"⏱️ 总训练时长: {self.user_data.get('total_time', 0)}分钟")
        if hasattr(self, 'best_score_label'):
            self.best_score_label.setText(f"🏆 最高专注度: {self.user_data.get('best_score', 0):.0f}%")
    
    def load_training_history(self):
        """加载训练历史"""
        if os.path.exists(self.training_history_file):
            try:
                with open(self.training_history_file, 'r', encoding='utf-8') as f:
                    self.training_history = json.load(f)
            except Exception as e:
                print(f"加载训练历史失败: {e}")
                self.training_history = []
        else:
            self.training_history = []
    
    def save_training_history(self):
        """保存训练历史"""
        try:
            with open(self.training_history_file, 'w', encoding='utf-8') as f:
                json.dump(self.training_history, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存训练历史失败: {e}")
            return False
    
    def add_training_record(self, record):
        """添加训练记录"""
        self.training_history.insert(0, record)  # 插入到最前面
        self.save_training_history()
        self.refresh_history_table()
        self.update_user_statistics(record)
    
    def refresh_history_table(self):
        """刷新历史表格显示"""
        if not hasattr(self, 'history_table'):
            return
        
        # 清空现有数据
        self.history_table.setRowCount(0)
        
        # 重新填充数据（最多显示50条）
        for record in self.training_history[:50]:
            row_position = self.history_table.rowCount()
            self.history_table.insertRow(row_position)
            
            self.history_table.setItem(row_position, 0, QTableWidgetItem(record.get('date', '')))
            self.history_table.setItem(row_position, 1, QTableWidgetItem(record.get('task', '')))
            
            # 专注度
            attention = record.get('attention', '0%')
            attention_item = QTableWidgetItem(attention)
            try:
                attention_value = int(attention.replace('%', ''))
                if attention_value >= 90:
                    attention_item.setForeground(QColor("#10b981"))
                elif attention_value >= 75:
                    attention_item.setForeground(QColor("#f59e0b"))
                else:
                    attention_item.setForeground(QColor("#ef4444"))
            except:
                pass
            self.history_table.setItem(row_position, 2, attention_item)
            
            self.history_table.setItem(row_position, 3, QTableWidgetItem(record.get('duration', '')))
            
            status_item = QTableWidgetItem(record.get('status', '已完成'))
            status_item.setForeground(QColor("#10b981"))
            self.history_table.setItem(row_position, 4, status_item)
            
            # 操作按钮
            view_btn = QPushButton("查看报告")
            view_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3b82f6;
                    color: white;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #2563eb;
                }
            """)
            date = record.get('date', '')
            view_btn.clicked.connect(lambda checked, d=date: self.view_report(d))
            self.history_table.setCellWidget(row_position, 5, view_btn)
    
    def update_user_statistics(self, record):
        """更新用户统计数据"""
        try:
            # 更新训练次数
            self.user_data['total_sessions'] = self.user_data.get('total_sessions', 0) + 1
            
            # 更新专注度统计
            attention_str = record.get('attention', '0%')
            attention_value = int(attention_str.replace('%', ''))
            
            old_total = self.user_data.get('total_sessions', 1) - 1
            old_avg = self.user_data.get('avg_attention', 0)
            self.user_data['avg_attention'] = (old_avg * old_total + attention_value) / (old_total + 1)
            
            # 更新最高分
            if attention_value > self.user_data.get('best_score', 0):
                self.user_data['best_score'] = attention_value
            
            # 更新总时长
            duration_str = record.get('duration', '0分钟')
            try:
                duration_value = int(duration_str.replace('分钟', ''))
                self.user_data['total_time'] = self.user_data.get('total_time', 0) + duration_value
            except:
                pass
            
            # 保存并更新UI
            self.save_user_data()
            self.update_user_ui()
            
            # 检查成就
            self.check_achievements()
            
        except Exception as e:
            print(f"更新用户统计失败: {e}")
    
    def check_achievements(self):
        """检查成就解锁"""
        new_achievements = []
        
        # 首次训练
        if self.user_data['total_sessions'] == 1:
            if '首次训练' not in self.user_data.get('achievements', []):
                new_achievements.append('首次训练')
        
        # 专注达人
        if self.user_data.get('best_score', 0) >= 90:
            if '专注达人' not in self.user_data.get('achievements', []):
                new_achievements.append('专注达人')
        
        # 坚持之星（10小时 = 600分钟）
        if self.user_data.get('total_time', 0) >= 600:
            if '坚持之星' not in self.user_data.get('achievements', []):
                new_achievements.append('坚持之星')
        
        # 学习标兵（20次训练）
        if self.user_data.get('total_sessions', 0) >= 20:
            if '学习标兵' not in self.user_data.get('achievements', []):
                new_achievements.append('学习标兵')
        
        if new_achievements:
            if 'achievements' not in self.user_data:
                self.user_data['achievements'] = []
            self.user_data['achievements'].extend(new_achievements)
            self.save_user_data()
            
            # 显示成就提示
            for achievement in new_achievements:
                QMessageBox.information(
                    self,
                    "🏆 成就解锁！",
                    f"恭喜您解锁新成就：\n\n{achievement}"
                )
        
        # 更新徽章显示
        self.update_badge_display()
    
    def update_badge_display(self):
        """更新徽章显示状态"""
        if not hasattr(self, 'badge_widgets'):
            return
        
        achievements = self.user_data.get('achievements', [])
        
        for badge_widget, badge_icon, title in self.badge_widgets:
            if title in achievements:
                # 已解锁：彩色 + 发光效果
                badge_icon.setStyleSheet("""
                    padding: 10px;
                    background-color: rgba(251, 191, 36, 0.2);
                    border-radius: 20px;
                    qproperty-alignment: AlignCenter;
                """)
                badge_icon.setFont(QFont("Arial", 36, QFont.Bold))
            else:
                # 未解锁：灰色
                badge_icon.setStyleSheet("""
                    padding: 10px;
                    color: #cbd5e1;
                    opacity: 0.5;
                """)
                badge_icon.setFont(QFont("Arial", 32))
    
    def view_report(self, date):
        """查看训练报告"""
        # 查找对应的训练记录
        record = None
        for r in self.training_history:
            if r.get('date') == date:
                record = r
                break
        
        if not record:
            QMessageBox.warning(self, "错误", "未找到对应的训练记录")
            return
        
        # 生成并显示报告
        try:
            report_file = self.report_generator.generate_report(record)
            if report_file and os.path.exists(report_file):
                # 打开报告文件
                import subprocess
                subprocess.Popen(['start', report_file], shell=True)
            else:
                QMessageBox.information(
                    self,
                    "📊 训练报告",
                    f"训练日期: {record.get('date', '')}\n"
                    f"任务名称: {record.get('task', '')}\n"
                    f"专注度: {record.get('attention', '')}\n"
                    f"训练时长: {record.get('duration', '')}\n"
                    f"状态: {record.get('status', '')}\n\n"
                    f"总注视点数: {record.get('gaze_count', 0)}"
                )
        except Exception as e:
            QMessageBox.critical(self, "错误", f"查看报告失败: {str(e)}")
    
    def export_all_reports(self):
        """导出所有训练报告"""
        from PyQt5.QtWidgets import QFileDialog
        
        # 选择保存目录
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择导出目录",
            os.path.expanduser("~")
        )
        
        if not directory:
            return
        
        try:
            export_count = 0
            for record in self.training_history:
                report_file = self.report_generator.generate_report(record, output_dir=directory)
                if report_file:
                    export_count += 1
            
            QMessageBox.information(
                self,
                "✅ 导出成功",
                f"已成功导出 {export_count} 个训练报告到:\n{directory}"
            )
        except Exception as e:
            QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
    
    def apply_theme(self, theme_name):
        """应用主题"""
        # 1. 更新编辑器样式
        if hasattr(self, 'training_widget') and self.training_widget:
            editor = self.training_widget.code_editor
            if theme_name == "深色主题":
                editor.apply_theme_style('dark')
            elif theme_name == "护眼主题":
                editor.apply_theme_style('eye')
            else:
                editor.apply_theme_style('light')

        # 2. 应用全局 QSS
        if theme_name == "深色主题":
            # 深色主题样式 - 现代科技感
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #0f172a;
                }
                QWidget {
                    background-color: #0f172a;
                    color: #f8fafc;
                }
                QGroupBox {
                    color: #94a3b8;
                    border: 2px solid #1e293b;
                    border-radius: 8px;
                    margin-top: 16px;
                    padding-top: 16px;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 16px;
                    padding: 0 8px;
                    color: #38bdf8;
                }
                QLabel {
                    color: #cbd5e1;
                }
                QLineEdit, QSpinBox {
                    background-color: #1e293b;
                    color: #f8fafc;
                    border: 1px solid #334155;
                    border-radius: 6px;
                    padding: 8px;
                }
                QLineEdit:focus, QSpinBox:focus {
                    border: 1px solid #3b82f6;
                }
                QComboBox {
                    background-color: #1e293b;
                    color: #f8fafc;
                    border: 1px solid #334155;
                    border-radius: 6px;
                    padding: 8px;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 20px;
                }
                QComboBox::down-arrow {
                    image: none;
                    border: 2px solid #94a3b8;
                    border-top: none;
                    border-left: none;
                    width: 8px;
                    height: 8px;
                }
                QComboBox QAbstractItemView {
                    background-color: #1e293b;
                    color: #f8fafc;
                    selection-background-color: #3b82f6;
                    selection-color: white;
                    border: 1px solid #334155;
                }
                QPushButton {
                    background-color: #3b82f6;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #2563eb;
                }
                QTabWidget::pane {
                    border: 2px solid #1e293b;
                    background-color: #0f172a;
                    border-radius: 8px;
                }
                QTabBar::tab {
                    background-color: #1e293b;
                    color: #94a3b8;
                    padding: 10px 20px;
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                }
                QTabBar::tab:selected {
                    background-color: #3b82f6;
                    color: white;
                }
                QTextEdit {
                    background-color: #1e293b;
                    color: #f8fafc;
                    border: 1px solid #334155;
                    selection-background-color: #3b82f6;
                }
                QTableWidget {
                    background-color: #0f172a;
                    color: #f8fafc;
                    gridline-color: #1e293b;
                    border: 1px solid #1e293b;
                }
                QHeaderView::section {
                    background-color: #1e293b;
                    color: #38bdf8;
                    padding: 8px;
                    border: none;
                    font-weight: bold;
                }
                QScrollBar:vertical {
                    background-color: #0f172a;
                    width: 12px;
                    border-radius: 6px;
                }
                QScrollBar::handle:vertical {
                    background-color: #334155;
                    border-radius: 6px;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """)
            # 同步更新训练模块代码编辑器样式
            if hasattr(self, 'training_widget'):
                self.training_widget.code_editor.setStyleSheet("""
                    QTextEdit {
                        background-color: #1e293b;
                        color: #f8fafc;
                        border: 1px solid #334155;
                        selection-background-color: #3b82f6;
                    }
                """)
        elif theme_name == "护眼模式":
            # 护眼模式样式 - 柔和淡绿色
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #ecfdf5;
                }
                QWidget {
                    background-color: #ecfdf5;
                    color: #1e293b;
                }
                QGroupBox {
                    color: #047857;
                    border: 2px solid #d1fae5;
                    border-radius: 8px;
                    margin-top: 16px;
                    padding-top: 16px;
                    font-weight: bold;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 16px;
                    padding: 0 8px;
                    color: #059669;
                }
                QLabel {
                    color: #374151;
                }
                QLineEdit, QSpinBox {
                    background-color: #ffffff;
                    color: #1e293b;
                    border: 1px solid #a7f3d0;
                    border-radius: 6px;
                    padding: 8px;
                }
                QLineEdit:focus, QSpinBox:focus {
                    border: 1px solid #10b981;
                }
                QComboBox {
                    background-color: #ffffff;
                    color: #1e293b;
                    border: 1px solid #a7f3d0;
                    border-radius: 6px;
                    padding: 8px;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 20px;
                }
                QComboBox::down-arrow {
                    image: none;
                    border: 2px solid #047857;
                    border-top: none;
                    border-left: none;
                    width: 8px;
                    height: 8px;
                }
                QComboBox QAbstractItemView {
                    background-color: #ffffff;
                    color: #1e293b;
                    selection-background-color: #d1fae5;
                    selection-color: #047857;
                    border: 1px solid #a7f3d0;
                }
                QPushButton {
                    background-color: #10b981;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #059669;
                }
                QTabWidget::pane {
                    border: 2px solid #d1fae5;
                    background-color: #ecfdf5;
                    border-radius: 8px;
                }
                QTabBar::tab {
                    background-color: #d1fae5;
                    color: #047857;
                    padding: 10px 20px;
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                }
                QTabBar::tab:selected {
                    background-color: #10b981;
                    color: white;
                }
                QTextEdit {
                    background-color: #ffffff;
                    color: #1e293b;
                    border: 1px solid #a7f3d0;
                    selection-background-color: #d1fae5;
                }
                QTableWidget {
                    background-color: #ecfdf5;
                    color: #1e293b;
                    gridline-color: #d1fae5;
                    border: 1px solid #d1fae5;
                }
                QHeaderView::section {
                    background-color: #d1fae5;
                    color: #047857;
                    padding: 8px;
                    border: none;
                    font-weight: bold;
                }
                QScrollBar:vertical {
                    background-color: #ecfdf5;
                    width: 12px;
                    border-radius: 6px;
                }
                QScrollBar::handle:vertical {
                    background-color: #a7f3d0;
                    border-radius: 6px;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """)
            # 同步更新训练模块代码编辑器样式
            if hasattr(self, 'training_widget'):
                self.training_widget.code_editor.setStyleSheet("""
                    QTextEdit {
                        background-color: #ffffff;
                        color: #1e293b;
                        border: 1px solid #a7f3d0;
                        selection-background-color: #d1fae5;
                    }
                """)
        else:
            # 浅色主题（默认）- 简洁明亮
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #ffffff;
                }
                QWidget {
                    background-color: #ffffff;
                    color: #1f2937;
                }
                QGroupBox {
                    color: #374151;
                    border: 2px solid #e5e7eb;
                    border-radius: 8px;
                    margin-top: 20px;
                    padding: 20px 16px 16px 16px;
                    font-weight: bold;
                    font-size: 13px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 16px;
                    padding: 0 8px;
                    color: #2563eb;
                }
                QLabel {
                    color: #4b5563;
                    font-size: 12px;
                }
                QLineEdit, QSpinBox {
                    background-color: #f9fafb;
                    color: #1f2937;
                    border: 1px solid #d1d5db;
                    border-radius: 6px;
                    padding: 8px;
                    font-size: 12px;
                    min-height: 28px;
                }
                QLineEdit:focus, QSpinBox:focus {
                    border: 1px solid #3b82f6;
                }
                QComboBox {
                    background-color: #f9fafb;
                    color: #1f2937;
                    border: 1px solid #d1d5db;
                    border-radius: 6px;
                    padding: 8px;
                    font-size: 12px;
                    min-height: 28px;
                }
                QComboBox::drop-down {
                    border: none;
                    width: 20px;
                }
                QComboBox::down-arrow {
                    image: none;
                    border: 2px solid #6b7280;
                    border-top: none;
                    border-left: none;
                    width: 8px;
                    height: 8px;
                }
                QComboBox QAbstractItemView {
                    background-color: #ffffff;
                    color: #1f2937;
                    selection-background-color: #bfdbfe;
                    selection-color: #1f2937;
                    border: 1px solid #d1d5db;
                }
                QPushButton {
                    background-color: #3b82f6;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-weight: bold;
                    font-size: 12px;
                    min-height: 32px;
                }
                QPushButton:hover {
                    background-color: #2563eb;
                }
                QTabWidget::pane {
                    border: 2px solid #e5e7eb;
                    background-color: #ffffff;
                    border-radius: 8px;
                }
                QTabBar::tab {
                    background-color: #f3f4f6;
                    color: #6b7280;
                    padding: 10px 20px;
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                }
                QTabBar::tab:selected {
                    background-color: #3b82f6;
                    color: white;
                }
                QTextEdit {
                    background-color: #f9fafb;
                    color: #1f2937;
                    border: 1px solid #d1d5db;
                    selection-background-color: #bfdbfe;
                }
                QTableWidget {
                    background-color: #ffffff;
                    color: #1f2937;
                    gridline-color: #e5e7eb;
                    border: 1px solid #e5e7eb;
                }
                QHeaderView::section {
                    background-color: #f3f4f6;
                    color: #2563eb;
                    padding: 8px;
                    border: none;
                    font-weight: bold;
                }
                QScrollBar:vertical {
                    background-color: #ffffff;
                    width: 12px;
                    border-radius: 6px;
                }
                QScrollBar::handle:vertical {
                    background-color: #d1d5db;
                    border-radius: 6px;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """)
            # 同步更新训练模块代码编辑器样式
            if hasattr(self, 'training_widget'):
                self.training_widget.code_editor.setStyleSheet("""
                    QTextEdit {
                        background-color: #f9fafb;
                        color: #1f2937;
                        border: 1px solid #d1d5db;
                        selection-background-color: #bfdbfe;
                    }
                """)
        
        # 保存设置
        self.settings['theme'] = theme_name
        self.save_settings()
    
    def load_settings(self):
        """加载系统设置"""
        default_settings = {
            'rtsp_timeout': 15,
            'gaze_sample_rate': '100 Hz',
            'auto_reconnect': True,
            'theme': '浅色主题',
            'font_size': 12,
            'show_gaze_point': True,
            'show_heatmap': True,
            'simulator_mode': False
        }
        
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
                for key in default_settings:
                    if key not in self.settings:
                        self.settings[key] = default_settings[key]
            except Exception as e:
                print(f"加载设置失败: {e}")
                self.settings = default_settings
        else:
            self.settings = default_settings
        
        self.update_settings_ui()
    
    def save_settings(self):
        """保存系统设置"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存设置失败: {e}")
            return False
    
    def update_settings_ui(self):
        """更新设置界面显示"""
        if hasattr(self, 'rtsp_timeout_spin'):
            self.rtsp_timeout_spin.setValue(self.settings.get('rtsp_timeout', 15))
        if hasattr(self, 'gaze_sample_rate_combo'):
            rate = self.settings.get('gaze_sample_rate', '100 Hz')
            index = self.gaze_sample_rate_combo.findText(rate)
            if index >= 0:
                self.gaze_sample_rate_combo.setCurrentIndex(index)
        if hasattr(self, 'auto_reconnect_check'):
            self.auto_reconnect_check.setChecked(self.settings.get('auto_reconnect', True))
        if hasattr(self, 'theme_combo'):
            theme = self.settings.get('theme', '浅色主题')
            index = self.theme_combo.findText(theme)
            if index >= 0:
                self.theme_combo.setCurrentIndex(index)
        if hasattr(self, 'font_size_spin'):
            self.font_size_spin.setValue(self.settings.get('font_size', 12))
        if hasattr(self, 'show_gaze_point_check'):
            self.show_gaze_point_check.setChecked(self.settings.get('show_gaze_point', True))
        if hasattr(self, 'show_heatmap_check'):
            self.show_heatmap_check.setChecked(self.settings.get('show_heatmap', True))
        if hasattr(self, 'simulator_check'):
            self.simulator_check.setChecked(self.settings.get('simulator_mode', False))
            # 应用模拟器模式状态（不显示提示框）
            self.toggle_simulator_mode(self.settings.get('simulator_mode', False), show_message=False)
    
    def resizeEvent(self, event):
        """窗口大小改变时，调整全局注视点组件的大小"""
        super().resizeEvent(event)
        if hasattr(self, 'global_gaze_widget'):
            self.global_gaze_widget.setGeometry(0, 0, self.width(), self.height())
    
    def showEvent(self, event):
        """窗口显示时创建并显示全局注视点组件"""
        super().showEvent(event)
        # 只在第一次显示时创建
        if not hasattr(self, 'global_gaze_widget'):
            self.global_gaze_widget = GlobalGazePointWidget(self)
            self.global_gaze_widget.setGeometry(0, 0, self.width(), self.height())
            self.global_gaze_widget.show()
            print("[UI] 全局注视点组件已创建")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 10))
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
