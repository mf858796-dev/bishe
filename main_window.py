import sys
import os
import json
import time
import sqlite3
from datetime import datetime
from collections import deque

if getattr(sys, 'base_prefix', sys.prefix) != sys.prefix:
    venv_path = sys.prefix
    plugin_path = os.path.join(venv_path, 'Lib', 'site-packages', 'PyQt5', 'Qt5', 'plugins')
    if os.path.exists(plugin_path):
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = plugin_path

import cv2
import numpy as np
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QMessageBox,
    QFrame,
    QGridLayout,
    QComboBox,
    QLineEdit,
    QTabWidget,
    QProgressBar,
    QGroupBox,
    QDialog,
    QInputDialog,
    QFormLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QSpinBox,
    QCheckBox,
    QScrollArea,
    QSpacerItem,
    QSizePolicy,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt5.QtGui import QImage, QPixmap, QColor, QFont, QPainter, QPen, QBrush, QRadialGradient
from glasses_manager import GlassesManager
from coordinate_mapper import CoordinateMapper
from attention_model import AttentionEvaluator
from training_widget import TrainingWidget
from report_generator import ReportGenerator
from database import DatabaseManager
from theme_manager import ThemeManager
from settings_panel import SettingsPanelController
from user_panel import UserPanelController


class GlobalGazePointWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setStyleSheet("background-color: transparent;")
        self.current_gaze = None
        self.previous_gaze = None

    def update_gaze(self, x, y):
        self.previous_gaze = self.current_gaze
        self.current_gaze = (x, y)
        self.update()

    def paintEvent(self, event):
        if not self.current_gaze:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        x, y = self.current_gaze
        painter.setPen(QColor(239, 68, 68, 150))
        painter.setBrush(QColor(239, 68, 68, 40))
        painter.drawEllipse(int(x) - 25, int(y) - 25, 50, 50)
        painter.setBrush(QColor(239, 68, 68, 200))
        painter.drawEllipse(int(x) - 10, int(y) - 10, 20, 20)
        painter.setPen(QPen(QColor(239, 68, 68, 180), 2))
        painter.drawLine(int(x) - 35, int(y), int(x) + 35, int(y))
        painter.drawLine(int(x), int(y) - 35, int(x), int(y) + 35)

        if self.previous_gaze:
            prev_x, prev_y = self.previous_gaze
            painter.setPen(QPen(QColor(239, 68, 68, 100), 2))
            painter.drawLine(int(prev_x), int(prev_y), int(x), int(y))

        painter.end()


class MetricCard(QFrame):
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
        self.value_label.setObjectName("value_label")
        self.value_label.setStyleSheet(f"color: {color}; font-size: 20px; font-weight: bold;")
        layout.addWidget(self.value_label)


class VideoDisplayWidget(QFrame):
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
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("color: white; font-size: 14px;")
        self.video_label.setText("等待视频流...")
        layout.addWidget(self.video_label)
        self.status_indicator = QLabel("● 离线")
        self.status_indicator.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(self.status_indicator)
        self.current_frame = None
        self.calibration_point = None

    def set_calibration_point(self, u, v, current, total):
        self.calibration_point = (u, v, current, total)
        self.update()

    def clear_calibration_point(self):
        self.calibration_point = None
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)

        if self.calibration_point and self.current_frame is not None:
            u, v, current, total = self.calibration_point
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            x = int(u * self.width())
            y = int(v * self.height())
            pen = QPen(QColor(255, 0, 0))
            pen.setWidth(4)
            painter.setPen(pen)
            painter.drawEllipse(x - 40, y - 40, 80, 80)
            painter.setBrush(QColor(255, 0, 0))
            painter.drawEllipse(x - 15, y - 15, 30, 30)
            painter.setPen(QPen(QColor(255, 0, 0), 3))
            painter.drawLine(x - 60, y, x + 60, y)
            painter.drawLine(x, y - 60, x, y + 60)
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            font = painter.font()
            font.setPointSize(16)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(x - 60, y - 60, f"{current}/{total}")
            painter.end()

    def update_frame(self, frame):
        if frame is None:
            return

        self.current_frame = frame
        if len(frame.shape) == 3:
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888).rgbSwapped()
        else:
            h, w = frame.shape
            bytes_per_line = w
            qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_Grayscale8)

        scaled_pixmap = QPixmap.fromImage(qt_image).scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

        self.video_label.setPixmap(scaled_pixmap)
        self.status_indicator.setText("● 在线")
        self.status_indicator.setStyleSheet("color: #10b981; font-size: 12px; font-weight: bold;")


class GazeHeatmapWidget(QFrame):
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

        self.heatmap_data = np.zeros((100, 100))
        self.gaze_history = deque(maxlen=200)
        self._kernel_radius = 8
        self._kernel = self._build_kernel(self._kernel_radius)

    def _build_kernel(self, radius):
        y, x = np.ogrid[-radius:radius + 1, -radius:radius + 1]
        distance_sq = x * x + y * y
        kernel = np.exp(-distance_sq / 18.0)
        kernel /= np.max(kernel)
        return kernel

    def _apply_kernel(self, center_x, center_y, weight=1.0):
        radius = self._kernel_radius
        x0 = max(0, center_x - radius)
        x1 = min(100, center_x + radius + 1)
        y0 = max(0, center_y - radius)
        y1 = min(100, center_y + radius + 1)

        kernel_x0 = x0 - (center_x - radius)
        kernel_x1 = kernel_x0 + (x1 - x0)
        kernel_y0 = y0 - (center_y - radius)
        kernel_y1 = kernel_y0 + (y1 - y0)

        self.heatmap_data[y0:y1, x0:x1] += self._kernel[kernel_y0:kernel_y1, kernel_x0:kernel_x1] * weight

    def add_gaze_point(self, x, y):
        if 0 <= x <= 1 and 0 <= y <= 1:
            heatmap_x = int(x * 99)
            heatmap_y = int(y * 99)
            self._apply_kernel(heatmap_x, heatmap_y)
            self.gaze_history.append((heatmap_x, heatmap_y))
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if np.max(self.heatmap_data) == 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        width = self.width()
        height = self.height()
        cell_width = width / 100
        cell_height = height / 100
        normalized_heatmap = self.heatmap_data / np.max(self.heatmap_data)

        for y in range(100):
            for x in range(100):
                intensity = normalized_heatmap[y, x]
                if intensity > 0.1:
                    alpha = int(intensity * 180)
                    color = QColor(255, 100, 100, alpha)
                    painter.fillRect(
                        int(x * cell_width),
                        int(y * cell_height),
                        int(cell_width) + 1,
                        int(cell_height) + 1,
                        color,
                    )
        painter.end()

    def clear_heatmap(self):
        self.heatmap_data = np.zeros((100, 100))
        self.gaze_history.clear()
        self.update()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = DatabaseManager()
        self.db_manager = self.db
        self.current_user_id = 1
        self.current_username = "Guest"
        self.setWindowTitle("编程初学者代码阅读专注力训练系统")

        screen = QApplication.primaryScreen().geometry()
        if screen.width() >= 1920:
            self.resize(1600, 1000)
            self.setMinimumSize(1400, 800)
            self.showMaximized()
        else:
            self.resize(1200, 800)
            self.setMinimumSize(1000, 700)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8fafc;
            }
        """)

        self.theme_manager = ThemeManager()
        self.settings_controller = SettingsPanelController(self)
        self.user_controller = UserPanelController(self)
        self.glasses_mgr = GlassesManager()
        self.glasses_mgr.start_async_loop()
        self.mapper = CoordinateMapper()
        self.evaluator = AttentionEvaluator()
        self.training_widget = TrainingWidget()
        self.training_widget.current_user_id = self.current_user_id
        self.report_generator = ReportGenerator()
        self.training_widget.task_completed.connect(self.on_task_completed)
        self.training_widget.training_started.connect(self.on_training_session_started)
        self.training_widget.training_resumed.connect(self.on_training_session_resumed)
        self.training_widget.training_paused.connect(self.on_training_session_paused)
        self.glasses_mgr.connected.connect(self.on_connected)
        self.glasses_mgr.disconnected.connect(self.on_disconnected)
        self.glasses_mgr.error_occurred.connect(self.on_glasses_error)
        self.glasses_mgr.status_update.connect(self.on_glasses_status)
        self.glasses_mgr.stream_data_ready.connect(self.process_stream)
        self.mapper.screen_gaze_update.connect(self.on_gaze_mapped)
        self.mapper.debug_frame_ready.connect(self.on_debug_frame_ready)
        self.metrics_timer = QTimer()
        self.metrics_timer.timeout.connect(self.update_system_status)
        self.metrics_timer.start(500)
        self.gaze_error_history = []
        self.center_gaze_samples = []
        self._training_session_active = False
        self._last_stream_ui_update = 0.0
        self._stream_ui_interval = 0.15
        self._last_training_ui_update = 0.0
        self._training_ui_interval = 0.15
        self.last_calibration_check_time = time.time()
        self.debug_enabled = False
        self.current_level = 1
        self.last_time = time.time()
        self.current_gaze = (0, 0)
        self.current_gaze2d = None
        self.is_connected = False
        self.gaze_count = 0
        self._last_rate_update = time.time()
        self.simulator_mode = False

        self.data_dir = os.path.join(os.path.dirname(__file__), 'data')
        os.makedirs(self.data_dir, exist_ok=True)
        self.user_data_file = os.path.join(self.data_dir, 'user_data.json')
        self.training_history_file = os.path.join(self.data_dir, 'training_history.json')
        self.settings_file = os.path.join(self.data_dir, 'settings.json')
        self.settings = {}

    def _log(self, message, force=False):
        if force or self.debug_enabled:
            print(message)

    def _group_style(self, accent):
        return f"""
            QGroupBox {{
                font-weight: 700;
                font-size: 15px;
                color: {accent};
                border: 1px solid #dbe4f0;
                border-radius: 18px;
                margin-top: 12px;
                padding: 22px 18px 18px 18px;
                background-color: #ffffff;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
                color: {accent};
            }}
        """

    def _input_style(self):
        return """
            QLineEdit, QComboBox, QSpinBox {
                border: 1px solid #dbe4f0;
                border-radius: 14px;
                padding: 12px 14px;
                font-size: 14px;
                background-color: #ffffff;
                color: #0f172a;
            }
            QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
                border: 1px solid #3b82f6;
                background-color: #f8fbff;
            }
        """

    def _action_button_style(self, color_start, color_end):
        return f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color_start}, stop:1 {color_end});
                color: white;
                border: none;
                border-radius: 16px;
                padding: 10px 18px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                opacity: 0.92;
            }}
            QPushButton:pressed {{
                padding-top: 11px;
                padding-bottom: 9px;
            }}
        """

    def _metric_text_style(self):
        return "color: #0f172a; font-size: 14px; font-weight: 600; padding: 8px 4px;"

    def _muted_text_style(self):
        return "color: #64748b; font-size: 13px; line-height: 1.6;"

    def set_current_user(self, user_id, username):
        self.current_user_id = user_id
        self.current_username = username
        self.training_widget.current_user_id = user_id
        self.setWindowTitle(f"编程初学者代码阅读专注力训练系统 - 用户: {username}")
        self.center_gaze_samples = []
        self.last_calibration_check_time = time.time()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        header = self.create_header()
        main_layout.addWidget(header)

        self.status_bar = self.create_status_bar()
        main_layout.addWidget(self.status_bar)

        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e2e8f0;
                border-radius: 18px;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f1f5f9;
                color: #64748b;
                border: none;
                border-top-left-radius: 14px;
                border-top-right-radius: 14px;
                padding: 12px 20px;
                margin-right: 6px;
                font-size: 14px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                color: #2563eb;
            }
            QTabBar::tab:hover:!selected {
                background-color: #e2e8f0;
                color: #334155;
            }
        """)

        monitor_tab = self.create_monitor_tab()
        self.tab_widget.addTab(monitor_tab, "📊 实时监控")
        self.tab_widget.addTab(self.training_widget, "🎯 训练任务")
        analysis_tab = self.create_analysis_tab()
        self.tab_widget.addTab(analysis_tab, "📈 数据分析")
        user_tab = self.create_user_tab()
        self.tab_widget.addTab(user_tab, "👤 用户管理")
        settings_tab = self.create_settings_tab()
        self.tab_widget.addTab(settings_tab, "⚙️ 系统设置")
        main_layout.addWidget(self.tab_widget, stretch=1)

        self.connect_btn = self.create_connect_button()
        self.connect_btn.setFixedHeight(45)
        main_layout.addWidget(self.connect_btn)

        self.calibration_btn = QPushButton("🎯 屏幕校准")
        self.calibration_btn.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        self.calibration_btn.setFixedHeight(45)
        self.calibration_btn.setStyleSheet(self._action_button_style("#f59e0b", "#fb7185"))
        self.calibration_btn.clicked.connect(self.start_calibration)
        main_layout.addWidget(self.calibration_btn)

        self.global_gaze_widget = GlobalGazePointWidget(self)
        self.global_gaze_widget.setGeometry(0, 0, self.width(), self.height())
        self.global_gaze_widget.raise_()
        self.global_gaze_widget.hide()

        self.load_user_data()
        self.load_training_history()
        self.load_settings()
        self.load_user_info_from_db()
        self.update_summary_from_db()

        if not hasattr(self, 'training_history') or len(self.training_history) == 0:
            self.init_sample_history()
        self.update_badge_display()
        self.refresh_history_table()
        self.update_calibration_labels()
        self.update_system_status()

    def update_stat_card(self, card, value):
        if card:
            value_label = card.findChild(QLabel, "value_label")
            if value_label:
                value_label.setText(str(value))

    def create_monitor_tab(self):
        monitor_widget = QWidget()
        layout = QVBoxLayout(monitor_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        metric_layout = QGridLayout()
        self.device_metric_card = MetricCard("设备状态", "未连接", "#64748b")
        self.rate_metric_card = MetricCard("眼动频率", "0 Hz", "#3b82f6")
        self.gaze_metric_card = MetricCard("注视点数量", "0", "#10b981")
        self.calibration_metric_card = MetricCard("校准状态", "未校准", "#f59e0b")
        metric_layout.addWidget(self.device_metric_card, 0, 0)
        metric_layout.addWidget(self.rate_metric_card, 0, 1)
        metric_layout.addWidget(self.gaze_metric_card, 1, 0)
        metric_layout.addWidget(self.calibration_metric_card, 1, 1)
        layout.addLayout(metric_layout)

        video_heatmap_layout = QHBoxLayout()
        self.video_widget = VideoDisplayWidget()
        screen_width = QApplication.primaryScreen().geometry().width()
        if screen_width >= 1920:
            self.video_widget.setMinimumSize(800, 450)
            self.heatmap_widget_min_size = (400, 450)
        else:
            self.video_widget.setMinimumSize(500, 280)
            self.heatmap_widget_min_size = (300, 280)
        video_heatmap_layout.addWidget(self.video_widget, stretch=2)

        self.heatmap_widget = GazeHeatmapWidget()
        self.heatmap_widget.setMinimumSize(*self.heatmap_widget_min_size)
        video_heatmap_layout.addWidget(self.heatmap_widget, stretch=1)
        layout.addLayout(video_heatmap_layout)

        self.gaze_position_label = QLabel("当前视线：--, --")
        self.gaze_position_label.setStyleSheet(self._muted_text_style())
        layout.addWidget(self.gaze_position_label)

        return monitor_widget

    def create_user_tab(self):
        return self.user_controller.create_user_tab()

    def create_settings_tab(self):
        return self.settings_controller.create_settings_tab()

    def create_header(self):
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2563eb, stop:0.55 #6366f1, stop:1 #8b5cf6);
                border-radius: 18px;
                padding: 18px;
            }
        """)
        header.setMinimumHeight(84)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 10, 20, 10)
        title = QLabel("📚 代码阅读专注力训练系统")
        title.setStyleSheet("""
            color: white;
            font-size: 25px;
            font-weight: 800;
        """)
        layout.addWidget(title)
        layout.addStretch()
        version = QLabel("v3.0")
        version.setStyleSheet("color: rgba(255,255,255,0.85); font-size: 14px; font-weight: 600;")
        layout.addWidget(version)
        return header

    def create_status_bar(self):
        status_widget = QFrame()
        layout = QHBoxLayout(status_widget)
        self.connection_status = QLabel("设备状态：未连接")
        self.user_status = QLabel(f"当前用户：{self.current_username}")
        self.system_status = QLabel("系统状态：待机")
        for label in (self.connection_status, self.user_status, self.system_status):
            label.setStyleSheet(self._muted_text_style())
            layout.addWidget(label)
        layout.addStretch()
        return status_widget

    def create_analysis_tab(self):
        analysis_widget = QWidget()
        layout = QVBoxLayout(analysis_widget)
        self.history_table = QTableWidget(0, 6)
        self.history_table.setHorizontalHeaderLabels(["日期", "任务", "专注度", "时长", "状态", "操作"])
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.history_table)
        return analysis_widget

    def create_connect_button(self):
        button = QPushButton("🔌 连接眼镜")
        button.setStyleSheet(self._action_button_style("#10b981", "#14b8a6"))
        button.clicked.connect(self.toggle_connection)
        return button

    def toggle_connection(self):
        if self.is_connected:
            self.glasses_mgr.close_connection()
        else:
            self.glasses_mgr.connect_device()
            self.system_status.setText("系统状态：正在连接设备")

    def start_calibration(self):
        self.mapper.is_calibrated = False
        self.mapper.calibration_offset_u = 0.0
        self.mapper.calibration_offset_v = 0.0
        self.mapper.calibration_scale_u = 1.0
        self.mapper.calibration_scale_v = 1.0
        if hasattr(self, 'video_widget'):
            self.video_widget.clear_calibration_point()
        self.update_stat_card(self.calibration_metric_card, "待重新校准")
        self.update_calibration_labels()
        QMessageBox.information(self, "屏幕校准", "当前版本已重置为待校准状态，请继续按照训练引导进行视线定位。")

    def reset_calibration(self):
        self.start_calibration()

    def update_calibration_labels(self):
        if hasattr(self, 'cal_offset_u_label'):
            self.cal_offset_u_label.setText(f"U轴偏移: {self.mapper.calibration_offset_u:.4f}")
        if hasattr(self, 'cal_offset_v_label'):
            self.cal_offset_v_label.setText(f"V轴偏移: {self.mapper.calibration_offset_v:.4f}")
        if hasattr(self, 'cal_scale_u_label'):
            self.cal_scale_u_label.setText(f"U轴缩放: {self.mapper.calibration_scale_u:.4f}")
        if hasattr(self, 'cal_scale_v_label'):
            self.cal_scale_v_label.setText(f"V轴缩放: {self.mapper.calibration_scale_v:.4f}")

    def update_system_status(self):
        if hasattr(self, 'user_status'):
            self.user_status.setText(f"当前用户：{self.current_username}")

        system_text = "训练中" if self._training_session_active else "待机"
        if self.is_connected:
            system_text = f"{system_text} / 设备在线"
        else:
            system_text = f"{system_text} / 设备离线"
        if hasattr(self, 'system_status'):
            self.system_status.setText(f"系统状态：{system_text}")

        if hasattr(self, 'device_metric_card'):
            self.update_stat_card(self.device_metric_card, "已连接" if self.is_connected else "未连接")
        if hasattr(self, 'gaze_metric_card'):
            self.update_stat_card(self.gaze_metric_card, str(self.gaze_count))
        if hasattr(self, 'calibration_metric_card'):
            self.update_stat_card(self.calibration_metric_card, "已校准" if self.mapper.is_calibrated else "未校准")

        now = time.time()
        elapsed = max(now - self._last_rate_update, 0.001)
        rate = self.gaze_count / elapsed if self.gaze_count > 0 else 0
        if hasattr(self, 'rate_metric_card'):
            self.update_stat_card(self.rate_metric_card, f"{rate:.1f} Hz")

    def on_connected(self, serial=None):
        self.is_connected = True
        if hasattr(self, 'connection_status'):
            self.connection_status.setText("设备状态：已连接")
        if hasattr(self, 'connect_btn'):
            self.connect_btn.setText("🔌 断开眼镜")
        if hasattr(self, 'device_metric_card'):
            self.update_stat_card(self.device_metric_card, "已连接")
        self.system_status.setText("系统状态：设备已连接")
        if serial:
            self._log(f"设备已连接: {serial}")

    def on_disconnected(self):
        self.is_connected = False
        if hasattr(self, 'connection_status'):
            self.connection_status.setText("设备状态：未连接")
        if hasattr(self, 'connect_btn'):
            self.connect_btn.setText("🔌 连接眼镜")
        if hasattr(self, 'device_metric_card'):
            self.update_stat_card(self.device_metric_card, "未连接")
        self.system_status.setText("系统状态：设备已断开")
        if hasattr(self, 'global_gaze_widget'):
            self.global_gaze_widget.hide()

    def on_glasses_error(self, message):
        self.system_status.setText("系统状态：设备异常")
        QMessageBox.warning(self, "设备提示", message)

    def on_glasses_status(self, message):
        self.system_status.setText(f"系统状态：{message}")

    def on_debug_frame_ready(self, frame):
        now = time.time()
        if now - self._last_stream_ui_update >= self._stream_ui_interval:
            self.video_widget.update_frame(frame)
            self._last_stream_ui_update = now

    def process_stream(self, frame, gaze_data):
        if frame is not None:
            self.mapper.process_frame_and_gaze(frame, gaze_data)

        if gaze_data and 'gaze2d' in gaze_data:
            self.current_gaze2d = gaze_data['gaze2d']
            self.gaze_count += 1
            if hasattr(self.training_widget, 'is_training') and self.training_widget.is_training:
                self.training_widget.process_gaze_data(gaze_data['gaze2d'])

    def on_gaze_mapped(self, x, y):
        self.current_gaze = (x, y)
        if hasattr(self, 'gaze_position_label'):
            self.gaze_position_label.setText(f"当前视线：{int(x)}, {int(y)}")

        screen_width = max(self.mapper.screen_width, 1)
        screen_height = max(self.mapper.screen_height, 1)
        norm_x = min(max(x / screen_width, 0), 1)
        norm_y = min(max(y / screen_height, 0), 1)

        if hasattr(self, 'heatmap_widget') and self.settings.get('show_heatmap', True):
            self.heatmap_widget.show()
            self.heatmap_widget.add_gaze_point(norm_x, norm_y)
        elif hasattr(self, 'heatmap_widget'):
            self.heatmap_widget.hide()

        if hasattr(self, 'global_gaze_widget'):
            if self.settings.get('show_gaze_point', True):
                self.global_gaze_widget.show()
                self.global_gaze_widget.update_gaze(x, y)
            else:
                self.global_gaze_widget.hide()

        now = time.time()
        if now - self._last_training_ui_update >= self._training_ui_interval:
            if hasattr(self.training_widget, 'update_gaze_point'):
                self.training_widget.update_gaze_point(x, y)
            self._last_training_ui_update = now

    def on_task_completed(self, message):
        record = self._build_training_record_from_message(message)
        self.add_training_record(record)

    def _build_training_record_from_message(self, message):
        task_title = getattr(getattr(self.training_widget, 'current_task', None), 'title', '训练任务')
        elapsed = 0
        if hasattr(self.training_widget, 'get_elapsed_training_time'):
            elapsed = self.training_widget.get_elapsed_training_time()
        score = getattr(self.training_widget, 'score', 0)
        return {
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'task': task_title,
            'attention': f"{round(score)}%",
            'duration': f"{max(1, int(round(elapsed / 60)))}分钟",
            'status': '已完成',
            'gaze_count': self.gaze_count,
            'summary': message,
            'record_id': getattr(self.training_widget, 'current_record_id', None),
        }

    def on_training_session_started(self):
        self._training_session_active = True
        self.gaze_count = 0
        self._last_rate_update = time.time()
        if hasattr(self, 'heatmap_widget'):
            self.heatmap_widget.clear_heatmap()

    def on_training_session_resumed(self):
        self._training_session_active = True

    def on_training_session_paused(self):
        self._training_session_active = False

    def toggle_simulator_mode(self, enabled, show_message=True):
        self.simulator_mode = enabled
        if hasattr(self.training_widget, 'setMouseTracking'):
            self.training_widget.setMouseTracking(enabled)
        if show_message:
            message = "已启用模拟器模式，可使用鼠标模拟眼动。" if enabled else "已关闭模拟器模式。"
            QMessageBox.information(self, "模拟器模式", message)

    def save_settings_from_ui(self):
        self.settings['rtsp_timeout'] = self.rtsp_timeout_spin.value()
        self.settings['gaze_sample_rate'] = self.gaze_sample_rate_combo.currentText()
        self.settings['auto_reconnect'] = self.auto_reconnect_check.isChecked()
        self.settings['theme'] = self.theme_combo.currentText()
        self.settings['font_size'] = self.font_size_spin.value()
        self.settings['show_gaze_point'] = self.show_gaze_point_check.isChecked()
        self.settings['show_heatmap'] = self.show_heatmap_check.isChecked()
        self.settings['simulator_mode'] = self.simulator_check.isChecked()
        self.save_settings()
        self.apply_theme(self.settings['theme'])
        self.toggle_simulator_mode(self.settings['simulator_mode'], show_message=False)
        if hasattr(self.training_widget, 'code_editor'):
            font = self.training_widget.code_editor.font()
            font.setPointSize(self.settings['font_size'])
            self.training_widget.code_editor.setFont(font)
        QMessageBox.information(self, "设置保存", "系统设置已保存。")

    def load_user_info_from_db(self):
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
            self._log(f"[加载用户信息失败] {e}", force=True)

    def update_summary_from_db(self):
        return self.user_controller.update_summary_from_db()

    def save_user_info(self):
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
        cursor.execute(
            """
            UPDATE users
            SET username = ?, student_id = ?, experience_level = ?
            WHERE id = ?
            """,
            (name, sid, level_db, self.current_user_id),
        )
        conn.commit()
        conn.close()
        QMessageBox.information(
            self,
            "✅ 保存成功",
            f"用户信息已保存到数据库：\n\n"
            f"姓名: {name}\n"
            f"学号/工号: {sid}\n"
            f"编程水平: {level_display}",
        )
        self.update_user_ui()

    def load_user_data(self):
        return self.user_controller.load_user_data()

    def save_user_data(self):
        return self.user_controller.save_user_data()

    def update_user_ui(self):
        return self.user_controller.update_user_ui()

    def load_training_history(self):
        self.training_history = []
        if getattr(self, 'current_user_id', None):
            try:
                db_history = self.db_manager.get_user_history(self.current_user_id, limit=50)
                for item in db_history:
                    self.training_history.append({
                        'date': item.get('trained_at', ''),
                        'task': item.get('task_title', ''),
                        'attention': f"{round(item.get('score', 0))}%",
                        'duration': f"{max(1, int(round((item.get('total_time', 0) or 0) / 60)))}分钟",
                        'status': '已完成',
                        'gaze_count': 0,
                        'record_id': item.get('id'),
                    })
                return
            except Exception as e:
                self._log(f"[加载训练历史失败] {e}", force=True)
        if os.path.exists(self.training_history_file):
            try:
                with open(self.training_history_file, 'r', encoding='utf-8') as f:
                    self.training_history = json.load(f)
            except Exception:
                self.training_history = []

    def save_training_history(self):
        try:
            with open(self.training_history_file, 'w', encoding='utf-8') as f:
                json.dump(self.training_history, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self._log(f"保存训练历史失败: {e}", force=True)
            return False

    def add_training_record(self, record):
        self.training_history.insert(0, record)
        self.save_training_history()
        self.refresh_history_table()
        self.update_user_statistics(record)
        self.update_summary_from_db()

    def refresh_history_table(self):
        return self.user_controller.refresh_history_table()

    def update_user_statistics(self, record):
        return self.user_controller.update_user_statistics(record)

    def check_achievements(self):
        return self.user_controller.check_achievements()

    def update_badge_display(self):
        return self.user_controller.update_badge_display()

    def view_report(self, date):
        record = None
        for r in self.training_history:
            if r.get('date') == date:
                record = r
                break
        if not record:
            QMessageBox.warning(self, "错误", "未找到对应的训练记录")
            return
        try:
            report_file = self.report_generator.generate_report(record)
            if report_file and os.path.exists(report_file):
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
                    f"总注视点数: {record.get('gaze_count', 0)}",
                )
        except Exception as e:
            QMessageBox.critical(self, "错误", f"查看报告失败: {str(e)}")

    def export_all_reports(self):
        QMessageBox.information(self, "导出报告", "当前版本暂未启用批量导出。")

    def init_sample_history(self):
        self.training_history = []

    def apply_theme(self, theme_name):
        return self.settings_controller.apply_theme(theme_name)

    def load_settings(self):
        return self.settings_controller.load_settings()

    def save_settings(self):
        return self.settings_controller.save_settings()

    def update_settings_ui(self):
        return self.settings_controller.update_settings_ui()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'global_gaze_widget'):
            self.global_gaze_widget.setGeometry(0, 0, self.width(), self.height())
