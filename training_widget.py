from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTextEdit, QProgressBar, QPushButton, QGroupBox,
                             QScrollArea, QFrame, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPointF, QRectF, QPoint
from PyQt5.QtGui import QFont, QColor, QPalette, QTextCharFormat, QTextCursor, QPainter, QPen, QBrush, QTextBlockUserData, QTextFormat
import time
import math
from database import DatabaseManager

class GazePointWidget(QWidget):
    """注视点显示组件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)  # 不阻挡鼠标事件
        self.setAttribute(Qt.WA_NoSystemBackground)  # 无背景
        self.setStyleSheet("background-color: transparent;")  # 完全透明
        self.current_gaze_point = None  # 只存储当前注视点 (x, y, timestamp)
        self.last_update_time = 0  # 上次更新时间
        self.update_interval = 0.05  # 最小更新间隔50ms（20fps）
        
    def add_gaze_point(self, x, y):
        """添加新的注视点（替换旧的）"""
        current_time = time.time()
        self.current_gaze_point = (x, y, current_time)
        
        # 限制重绘频率，避免过度刷新
        if current_time - self.last_update_time >= self.update_interval:
            self.update()  # 触发重绘
            self.last_update_time = current_time
    
    def clear_points(self):
        """清除注视点"""
        self.current_gaze_point = None
        self.update()
    
    def paintEvent(self, event):
        """绘制注视点"""
        if not self.current_gaze_point:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        x, y, timestamp = self.current_gaze_point
        
        # 检查注视点是否过期（超过2秒不更新）
        current_time = time.time()
        if current_time - timestamp > 2.0:
            self.current_gaze_point = None
            return
        
        # 绘制外圈（红色）
        color = QColor(255, 50, 50, 255)
        pen = QPen(color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(QBrush(color))
        painter.drawEllipse(QPointF(x, y), 10, 10)
        
        # 绘制中心点（白色）
        center_color = QColor(255, 255, 255, 255)
        painter.setPen(QPen(center_color))
        painter.setBrush(QBrush(center_color))
        painter.drawEllipse(QPointF(x, y), 4, 4)


class HighlightedCodeEditor(QTextEdit):
    """支持行高亮和视觉引导的代码编辑器（基于 ExtraSelection）"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)  # 代码阅读模式，不可编辑
        self.setMouseTracking(True)  # 开启鼠标追踪，用于无设备时的模拟测试
        
        # 核心状态变量
        self.highlighted_lines = set()  # 已完成的高亮行号
        self.current_guide_line = -1  # 当前引导的行号
        self.current_guide_start = -1  # 引导范围起始行
        self.current_guide_end = -1  # 引导范围结束行
        self.current_gaze_line = -1  # 用户当前视线落在哪一行
        self.gaze_dwell_times = {}  # 每行的注视停留时间
        self.last_gaze_time = time.time()
        
        # 默认样式（浅色主题）
        self.apply_theme_style('light')
    
    def apply_theme_style(self, theme):
        """应用主题样式"""
        font = QFont("Consolas", 13)
        self.setFont(font)
        
        if theme == 'dark':
            self.setStyleSheet("""
                QTextEdit {
                    background-color: #1E1E1E;
                    color: #D4D4D4;
                    border: 2px solid #333333;
                    border-radius: 8px;
                    padding: 10px;
                    line-height: 1.5;
                }
            """)
        elif theme == 'eye':
            self.setStyleSheet("""
                QTextEdit {
                    background-color: #F0FDF4;
                    color: #1F2937;
                    border: 2px solid #A7F3D0;
                    border-radius: 8px;
                    padding: 10px;
                    line-height: 1.5;
                }
            """)
        else:  # light
            self.setStyleSheet("""
                QTextEdit {
                    background-color: #F9FAFB;
                    color: #1F2937;
                    border: 2px solid #E5E7EB;
                    border-radius: 8px;
                    padding: 10px;
                    line-height: 1.5;
                }
            """)
    
    def set_highlighted_lines(self, line_numbers):
        """设置已完成的高亮行号集合"""
        self.highlighted_lines = set(line_numbers)
        self.highlight_lines()
    
    def set_guide_line(self, line_number):
        """设置引导行（下一步该看的行）"""
        self.current_guide_line = line_number
        self.highlight_lines()
    
    def set_guide_range(self, start_line, end_line):
        """设置引导范围（多行高亮）"""
        self.current_guide_start = start_line
        self.current_guide_end = end_line
        self.highlight_lines()
    
    def set_current_gaze_line(self, line_number):
        """设置当前注视行"""
        if line_number != self.current_gaze_line:
            self.current_gaze_line = line_number
            self.highlight_lines()
    
    def update_gaze_dwell(self, line_number, dt):
        """更新某行的注视停留时间"""
        if line_number not in self.gaze_dwell_times:
            self.gaze_dwell_times[line_number] = 0
        self.gaze_dwell_times[line_number] += dt
    
    def process_gaze_coordinate(self, global_x, global_y):
        """
        AOI (兴趣区) 映射引擎：
        将屏幕绝对坐标 (x,y) 转化为代码行号
        """
        local_pos = self.mapFromGlobal(QPoint(global_x, global_y))
        
        if not self.rect().contains(local_pos):
            if self.current_gaze_line != -1:
                self.current_gaze_line = -1
                self.highlight_lines()
            return
        
        cursor = self.cursorForPosition(local_pos)
        line_number = cursor.blockNumber()
        
        if line_number != self.current_gaze_line:
            self.current_gaze_line = line_number
            self.highlight_lines()
    
    def highlight_lines(self):
        """执行视觉高亮渲染（使用 ExtraSelection）"""
        extra_selections = []
        
        # 渲染 1: 引导范围的高亮（黄色闪烁背景）- 支持多行
        if self.current_guide_start >= 0 and self.current_guide_end >= 0:
            for line_num in range(self.current_guide_start, self.current_guide_end + 1):
                guide_selection = QTextEdit.ExtraSelection()
                guide_format = guide_selection.format
                # 黄色闪烁效果
                flash_alpha = int(180 + 75 * math.sin(time.time() * 4))
                guide_format.setBackground(QColor(251, 191, 36, flash_alpha))
                guide_format.setProperty(QTextFormat.FullWidthSelection, True)
                
                cursor = QTextCursor(self.document().findBlockByNumber(line_num))
                guide_selection.cursor = cursor
                extra_selections.append(guide_selection)
        elif self.current_guide_line >= 0:
            guide_selection = QTextEdit.ExtraSelection()
            guide_format = guide_selection.format
            flash_alpha = int(180 + 75 * math.sin(time.time() * 4))
            guide_format.setBackground(QColor(251, 191, 36, flash_alpha))
            guide_format.setProperty(QTextFormat.FullWidthSelection, True)
            
            cursor = QTextCursor(self.document().findBlockByNumber(self.current_guide_line))
            guide_selection.cursor = cursor
            extra_selections.append(guide_selection)
        
        # 渲染 2: 当前注视行的高亮（蓝色跟随）
        if self.current_gaze_line >= 0:
            gaze_selection = QTextEdit.ExtraSelection()
            gaze_format = gaze_selection.format
            gaze_format.setBackground(QColor(59, 130, 246, 80))  # 半透明蓝色
            gaze_format.setProperty(QTextFormat.FullWidthSelection, True)
            
            cursor = QTextCursor(self.document().findBlockByNumber(self.current_gaze_line))
            gaze_selection.cursor = cursor
            extra_selections.append(gaze_selection)
        
        # 渲染 3: 已完成行的高亮（绿色背景）
        for line_num in self.highlighted_lines:
            if line_num != self.current_guide_line:  # 避免覆盖引导行
                completed_selection = QTextEdit.ExtraSelection()
                completed_format = completed_selection.format
                completed_format.setBackground(QColor(16, 185, 129, 60))  # 半透明绿色
                completed_format.setProperty(QTextFormat.FullWidthSelection, True)
                
                cursor = QTextCursor(self.document().findBlockByNumber(line_num))
                completed_selection.cursor = cursor
                extra_selections.append(completed_selection)
        
        self.setExtraSelections(extra_selections)

class CodeBlock:
    """代码块定义"""
    def __init__(self, name, start_line, end_line, description):
        self.name = name
        self.start_line = start_line
        self.end_line = end_line
        self.description = description
        self.completed = False
        self.dwell_time = 0
        self.required_time = 3.0  # 默认需要注视3秒

class TrainingTask:
    """训练任务"""
    def __init__(self, level, title, code, blocks, description):
        self.level = level
        self.title = title
        self.code = code
        self.blocks = blocks
        self.description = description
        self.current_block_index = 0
        self.start_time = None
        self.total_time = 0

class TrainingWidget(QWidget):
    # 任务完成信号
    task_completed = pyqtSignal(str)
    # 进度更新信号
    progress_updated = pyqtSignal(int)
    # 训练状态信号
    training_started = pyqtSignal()
    training_paused = pyqtSignal()
    training_resumed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        
        # 初始化数据库
        self.db = DatabaseManager()
        self.current_user_id = 1  # 默认用户ID，后续可由主界面传入
        self.current_record_id = None # 当前训练记录的ID，用于存储原始数据
        
        # 训练状态
        self.current_task = None
        self.is_training = False
        self.is_paused = False
        self.gaze_x, self.gaze_y = 0, 0
        self.last_gaze_time = time.time()
        self.pause_started_at = None
        self.total_paused_duration = 0.0
        self.is_inside_target_block = False
        self._stats_counter = 0
        self.debug_enabled = False
        
        # 统计数据
        self.total_fixations = 0
        self.valid_fixations = 0
        self.regression_count = 0
        self.last_block_index = -1
        
        # 最新注视点信息（用于持续计时）
        self.last_gaze_x = 0
        self.last_gaze_y = 0
        self.prev_gaze_y = 0  # 上一次注视点的Y坐标（用于检测回视）
        
        # 游戏化元素
        self.score = 0  # 当前得分
        self.combo_count = 0  # 连击数
        self.max_combo = 0  # 最大连击
        self.achievements = []  # 已获得的成就
        self.last_achievement_time = 0  # 上次成就时间（防止重复提示）
        
        # UI更新控制
        self.last_stats_update = 0
        self.stats_update_interval = 0.5  # 每0.5秒更新一次统计
        
        # 注视点显示组件
        self.gaze_point_widget = None
        
        # 初始化统计定时器（复用，避免重复创建）
        from PyQt5.QtCore import QTimer
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        
        # 初始化UI
        self.init_ui()
        
        # 加载示例任务
        self.load_sample_tasks()

    def _group_style(self, accent, surface="#ffffff"):
        return f"""
            QGroupBox {{
                font-weight: 700;
                font-size: 15px;
                color: {accent};
                border: 1px solid #dbe4f0;
                border-radius: 18px;
                margin-top: 12px;
                padding: 22px 18px 18px 18px;
                background-color: {surface};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 10px;
                background-color: {surface};
            }}
        """

    def _button_style(self, start_color, end_color=None):
        end_color = end_color or start_color
        return f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {start_color}, stop:1 {end_color});
                color: white;
                font-size: 14px;
                font-weight: 700;
                border-radius: 14px;
                padding: 12px 18px;
                min-height: 42px;
                border: none;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {end_color}, stop:1 {start_color});
            }}
            QPushButton:pressed {{
                padding-top: 13px;
            }}
            QPushButton:disabled {{
                background: #cbd5e1;
                color: #94a3b8;
            }}
        """

    def _info_card_style(self):
        return """
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
            padding: 12px 14px;
        """

    def _log(self, message, force=False):
        """统一训练模块日志输出"""
        if force or self.debug_enabled:
            print(message)

    def _reset_task_progress(self):
        """重置当前任务的块进度和统计状态"""
        if not self.current_task:
            return

        self.current_task.current_block_index = 0
        for block in self.current_task.blocks:
            block.completed = False
            block.dwell_time = 0

        self.total_fixations = 0
        self.valid_fixations = 0
        self.regression_count = 0
        self.last_block_index = -1
        self.score = 0
        self.combo_count = 0
        self.max_combo = 0
        self.achievements = []
        self.last_achievement_time = 0
        self.is_inside_target_block = False
        self._stats_counter = 0

        if hasattr(self, 'feedback_label'):
            self.feedback_label.hide()

    def _show_gaze_overlay(self, clear_points=False):
        """显示代码区注视点覆盖层"""
        if not self.gaze_point_widget:
            return

        viewport = self.code_editor.viewport()
        self.gaze_point_widget.setGeometry(0, 0, viewport.width(), viewport.height())
        if clear_points:
            self.gaze_point_widget.clear_points()
        self.gaze_point_widget.show()
        self.gaze_point_widget.raise_()

    def _hide_gaze_overlay(self, clear_points=False):
        """隐藏代码区注视点覆盖层"""
        if not self.gaze_point_widget:
            return

        if clear_points:
            self.gaze_point_widget.clear_points()
        self.gaze_point_widget.hide()

    def _restart_stats_timer(self):
        self.stats_timer.stop()
        self.stats_timer.start(1000)
        
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # 任务信息区域
        self.task_info_group = self.create_task_info_group()
        layout.addWidget(self.task_info_group)
        
        # 主内容区域(代码 + 指导)
        content_layout = QHBoxLayout()
        
        # 左侧: 代码编辑器
        code_group = self.create_code_editor()
        content_layout.addWidget(code_group, stretch=3)
        
        # 右侧: 训练指导
        guide_group = self.create_guide_panel()
        content_layout.addWidget(guide_group, stretch=1)
        
        layout.addLayout(content_layout, stretch=1)  # 让内容区域占据更多空间
        
        # 底部: 进度和控制
        control_layout = self.create_control_panel()
        layout.addLayout(control_layout)
        
    def create_task_info_group(self):
        """创建任务信息组"""
        group = QGroupBox("📋 当前任务")
        group.setStyleSheet(self._group_style("#3b82f6"))
        
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        
        # 任务标题
        self.task_title_label = QLabel("请选择一个训练任务开始")
        self.task_title_label.setStyleSheet("font-size: 20px; font-weight: 800; color: #0f172a;")
        layout.addWidget(self.task_title_label)
        
        # 任务描述
        self.task_desc_label = QLabel("系统包含多个训练关卡,从基础的变量识别到复杂的逻辑理解")
        self.task_desc_label.setStyleSheet(self._info_card_style() + " color: #475569; font-size: 14px; line-height: 1.6;")
        self.task_desc_label.setWordWrap(True)
        layout.addWidget(self.task_desc_label)
        
        return group
    
    def create_code_editor(self):
        """创建代码编辑器"""
        group = QGroupBox("💻 代码阅读区")
        group.setStyleSheet(self._group_style("#10b981", "#ffffff"))
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        
        # 使用增强版代码编辑器
        self.code_editor = HighlightedCodeEditor()
        self.code_editor.setFont(QFont("Consolas", 13))
        self.code_editor.setReadOnly(True)
        
        # 默认样式（浅色主题）
        # 根据屏幕分辨率设置最小尺寸
        from PyQt5.QtWidgets import QApplication
        screen_width = QApplication.primaryScreen().geometry().width()
        if screen_width >= 1920:
            self.code_editor.setMinimumHeight(500)  # 大屏幕更高
        else:
            self.code_editor.setMinimumHeight(350)  # 小屏幕
        
        # 注释掉鼠标追踪，只使用真实眼动仪数据
        # self.code_editor.setMouseTracking(True)  # 启用鼠标追踪
        self.code_editor.setStyleSheet("""
            QTextEdit {
                background-color: #0f172a;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 16px;
                padding: 16px;
                line-height: 1.7;
                selection-background-color: #475569;
            }
        """)
        self.code_editor.setText("-- 请选择任务开始训练 --")
        layout.addWidget(self.code_editor)
        
        # 创建注视点显示组件(作为 code_editor.viewport() 的子组件)
        # viewport 是 QTextEdit 实际显示内容的区域，子组件不会被遮挡
        self.gaze_point_widget = GazePointWidget(self.code_editor.viewport())
        self.gaze_point_widget.hide()  # 初始隐藏
        
        # 注释掉事件过滤器，只使用真实眼动仪数据
        # self.code_editor.viewport().installEventFilter(self)
        
        # 行号显示(简化版)
        self.line_hint_label = QLabel("提示: 注视目标区域3秒即可完成该步骤")
        self.line_hint_label.setStyleSheet("color: #64748b; font-size: 12px; margin-top: 2px; padding: 0 4px;")
        layout.addWidget(self.line_hint_label)
        
        return group
    
    def showEvent(self, event):
        """窗口显示时设置注视点组件大小和位置"""
        super().showEvent(event)
        if self.gaze_point_widget:
            # 注视点组件是 viewport 的子组件，所以直接设置为 viewport 的大小
            viewport = self.code_editor.viewport()
            self.gaze_point_widget.setGeometry(0, 0, viewport.width(), viewport.height())
    
    # 注释掉鼠标事件过滤器，只使用真实眼动仪数据
    # def eventFilter(self, obj, event):
    #     """事件过滤器 - 捕获 viewport 的鼠标移动事件"""
    #     from PyQt5.QtCore import QEvent
    #     if obj == self.code_editor.viewport() and event.type() == QEvent.MouseMove:
    #         if self.is_training and self.gaze_point_widget:
    #             # 获取鼠标相对于 viewport 的位置
    #             pos = event.pos()
    #             # 直接添加注视点
    #             self.gaze_point_widget.add_gaze_point(pos.x(), pos.y())
    #     return super().eventFilter(obj, event)
    
    def create_guide_panel(self):
        """创建训练指导面板"""
        group = QGroupBox("🎯 训练指导")
        group.setStyleSheet(self._group_style("#f59e0b"))
        
        layout = QVBoxLayout(group)
        layout.setSpacing(10)
        
        # 当前步骤
        self.step_label = QLabel("等待开始...")
        self.step_label.setStyleSheet("""
            font-size: 14px;
            color: #0f172a;
            font-weight: 600;
            padding: 12px 14px;
            background-color: #fff7ed;
            border: 1px solid #fed7aa;
            border-radius: 14px;
            line-height: 1.6;
        """)
        self.step_label.setWordWrap(True)
        layout.addWidget(self.step_label)
        
        # 注视进度条
        progress_label = QLabel("注视进度:")
        progress_label.setStyleSheet("font-size: 12px; color: #64748b; margin-top: 4px; font-weight: 600;")
        layout.addWidget(progress_label)
        
        self.block_progress = QProgressBar()
        self.block_progress.setMinimum(0)
        self.block_progress.setMaximum(100)
        self.block_progress.setValue(0)
        self.block_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                text-align: center;
                background-color: #f8fafc;
                height: 24px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #f59e0b, stop:0.5 #f97316, stop:1 #ef4444);
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.block_progress)
        
        # 统计信息
        stats_label = QLabel("实时统计:")
        stats_label.setStyleSheet("font-size: 12px; color: #64748b; margin-top: 8px; font-weight: 600;")
        layout.addWidget(stats_label)
        
        # 游戏化反馈：得分和连击
        self.feedback_label = QLabel("")
        self.feedback_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: 700;
                color: #b45309;
                padding: 8px;
                background-color: #fef3c7;
                border: 1px solid #fcd34d;
                border-radius: 12px;
                qproperty-alignment: AlignCenter;
            }
        """)
        self.feedback_label.hide()  # 初始隐藏
        layout.addWidget(self.feedback_label)
        
        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(170)
        self.stats_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 14px;
                padding: 10px;
                font-size: 12px;
                line-height: 1.6;
            }
        """)
        self.stats_text.setReadOnly(True)
        layout.addWidget(self.stats_text)
        
        layout.addStretch()
        
        return group
    
    def create_control_panel(self):
        """创建控制面板"""
        layout = QHBoxLayout()
        layout.setSpacing(12)
        
        # 任务选择按钮
        self.prev_btn = QPushButton("⬅️ 上一关")
        self.prev_btn.setStyleSheet(self._button_style("#6366f1", "#8b5cf6"))
        self.prev_btn.clicked.connect(self.previous_task)
        layout.addWidget(self.prev_btn)
        
        self.start_btn = QPushButton("▶️ 开始训练")
        self.start_btn.setStyleSheet(self._button_style("#10b981", "#06b6d4"))
        self.start_btn.clicked.connect(self.toggle_training)
        layout.addWidget(self.start_btn, stretch=2)
        
        self.next_btn = QPushButton("➡️ 下一关")
        self.next_btn.setStyleSheet(self._button_style("#6366f1", "#8b5cf6"))
        self.next_btn.clicked.connect(self.next_task)
        layout.addWidget(self.next_btn)
        
        # 重置按钮
        self.reset_btn = QPushButton("🔄 重置")
        self.reset_btn.setStyleSheet(self._button_style("#f59e0b", "#ef4444"))
        self.reset_btn.clicked.connect(self.reset_current_task)
        layout.addWidget(self.reset_btn)
        
        return layout
    
    def get_button_style(self, color):
        """获取按钮样式"""
        return f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color}, stop:1 {color}dd);
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 8px;
                padding: 10px 20px;
                min-height: 40px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {color}dd, stop:1 {color});
            }}
            QPushButton:pressed {{
                background: {color};
            }}
            QPushButton:disabled {{
                background: #cbd5e1;
                color: #94a3b8;
            }}
        """
    
    def load_sample_tasks(self):
        """加载示例训练任务"""
        self.tasks = []
        
        # 任务 1: 基础变量识别
        task1 = TrainingTask(
            level=1,
            title="基础: 变量识别",
            code="""def calculate_sum(n):
    total = 0
    count = 0
    
    for i in range(n):
        total += i
        count += 1
    
    average = total / count
    return average

if __name__ == "__main__":
    result = calculate_sum(100)
    print(f"结果: {result}")""",
            blocks=[
                CodeBlock("函数定义", 1, 1, "注视函数名 'calculate_sum'"),
                CodeBlock("变量初始化", 2, 2, "注视变量 'total' 和 'count'"),
                CodeBlock("for 循环", 5, 5, "注视 'for' 关键字"),
                CodeBlock("循环体", 6, 7, "注视循环体内的累加操作"),
                CodeBlock("返回值", 10, 10, "注视 'return' 语句"),
            ],
            description="学习识别代码中的基本变量和函数结构"
        )
        self.tasks.append(task1)
        
        # 任务 2: 条件判断理解
        task2 = TrainingTask(
            level=2,
            title="进阶: 条件判断",
            code="""def check_grade(score):
    if score >= 90:
        grade = 'A'
    elif score >= 80:
        grade = 'B'
    elif score >= 70:
        grade = 'C'
    elif score >= 60:
        grade = 'D'
    else:
        grade = 'F'
    
    return grade

# 测试
scores = [85, 92, 78, 65, 55]
for s in scores:
    print(f"{s}分 -> {check_grade(s)}级")""",
            blocks=[
                CodeBlock("函数入口", 1, 1, "注视函数名 'check_grade'"),
                CodeBlock("条件判断链", 2, 9, "注视 'if-elif-else' 结构"),
                CodeBlock("返回结果", 11, 11, "注视 'return grade'"),
                CodeBlock("测试数据", 14, 14, "注视 'scores' 列表"),
                CodeBlock("循环调用", 15, 16, "注视 'for' 循环"),
            ],
            description="理解多层条件判断逻辑"
        )
        self.tasks.append(task2)
        
        # 任务 3: 循环与数据结构
        task3 = TrainingTask(
            level=3,
            title="高级: 数据处理",
            code="""def process_data(data_list):
    result = {}
    
    for item in data_list:
        key = item['category']
        value = item['value']
        
        if key not in result:
            result[key] = []
        
        result[key].append(value)
    
    # 计算每类平均值
    averages = {}
    for key, values in result.items():
        averages[key] = sum(values) / len(values)
    
    return averages

# 示例数据
data = [
    {'category': 'A', 'value': 10},
    {'category': 'B', 'value': 20},
    {'category': 'A', 'value': 30},
]
print(process_data(data))""",
            blocks=[
                CodeBlock("字典初始化", 2, 2, "注视 'result = {}'"),
                CodeBlock("数据遍历", 4, 4, "注视 'for item' 循环"),
                CodeBlock("键值提取", 5, 6, "注视字典访问操作"),
                CodeBlock("条件添加", 8, 10, "注视 'if key not in'"),
                CodeBlock("平均值计算", 14, 16, "注视第二个 'for' 循环"),
                CodeBlock("函数返回", 18, 18, "注视 'return averages'"),
            ],
            description="掌握复杂数据结构的处理流程"
        )
        self.tasks.append(task3)
        
        # 默认显示第一个任务
        if self.tasks:
            self.display_task(self.tasks[0])
    
    def display_task(self, task):
        """显示任务内容"""
        self.current_task = task
        self.task_title_label.setText(f"第 {task.level} 关: {task.title}")
        self.task_desc_label.setText(task.description)
        self.code_editor.setText(task.code)
        
        # 重置状态
        self.is_training = False
        self.start_btn.setText("▶️ 开始训练")
        self.update_stats()
    
    def toggle_training(self):
        """切换训练状态"""
        if not self.current_task:
            return
        
        if not self.is_training:
            self.start_training()
        else:
            self.stop_training()
    
    def start_training(self):
        """开始训练并创建数据库记录"""
        if self.is_paused and self.current_task and self.current_record_id:
            self.is_training = True
            self.is_paused = False
            self.start_btn.setText("⏸️ 暂停训练")
            if self.pause_started_at is not None:
                self.total_paused_duration += max(0.0, time.time() - self.pause_started_at)
                self.pause_started_at = None

            self._restart_stats_timer()
            self._show_gaze_overlay()

            self.highlight_current_block()
            self.update_step_instruction()
            self.training_resumed.emit()
            return

        self.db.flush_raw_gaze_data()
        self.is_training = True
        self.is_paused = False
        self.start_btn.setText("⏸️ 暂停训练")
        self.current_task.start_time = time.time()
        self.pause_started_at = None
        self.total_paused_duration = 0.0
        self._reset_task_progress()
        
        # 在数据库中创建一条新的训练记录，获取 ID 用于后续存储原始数据
        try:
            self.current_record_id = self.db.save_training_record(
                user_id=self.current_user_id,
                task_level=self.current_task.level,
                task_title=self.current_task.title,
                completion_rate=0.0,
                total_time=0.0,
                regression_count=0,
                accuracy=0.0,
                score=0
            )
            self._log(f"[数据库] 开启新训练记录，ID: {self.current_record_id}")
        except Exception as e:
            self._log(f"[数据库错误] 创建记录失败: {e}", force=True)
            self.current_record_id = None
        
        # 启动统计定时器
        self._restart_stats_timer()
        self._show_gaze_overlay(clear_points=True)
        
        # 高亮第一个代码块
        self.highlight_current_block()
        self.update_step_instruction()
        self.training_started.emit()
        
    def stop_training(self):
        """停止训练"""
        if not self.is_training:
            return

        self.is_training = False
        self.is_paused = True
        self.pause_started_at = time.time()
        self.start_btn.setText("▶️ 继续训练")
        self.db.flush_raw_gaze_data()
        
        # 隐藏注视点组件
        self._hide_gaze_overlay()
        
        # 停止统计定时器
        if hasattr(self, 'stats_timer'):
            self.stats_timer.stop()
        
        # 清除高亮
        cursor = self.code_editor.textCursor()
        cursor.clearSelection()
        self.training_paused.emit()
    
    def reset_current_task(self):
        """重置当前任务"""
        if self.current_task:
            self._reset_task_progress()
            self._hide_gaze_overlay(clear_points=True)
            
            if self.is_training:
                self.start_training()
            else:
                self.update_step_instruction()
            
            # 更新统计面板显示
            self.update_stats()
    
    def previous_task(self):
        """上一个任务"""
        if self.current_task and self.current_task.level > 1:
            self.display_task(self.tasks[self.current_task.level - 2])
    
    def next_task(self):
        """下一个任务"""
        if self.current_task and self.current_task.level < len(self.tasks):
            self.display_task(self.tasks[self.current_task.level])
            self._reset_task_progress()
            self._hide_gaze_overlay(clear_points=True)
            
            # 如果正在训练，重新开始
            if self.is_training:
                self.current_task.start_time = time.time()
                self.highlight_current_block()
            
            # 更新面板显示
            self.update_step_instruction()
            self.update_stats()
    
    def highlight_current_block(self):
        """高亮当前代码块（高亮整个代码块范围）"""
        if not self.current_task or not self.is_training:
            return
        
        block = self.current_task.blocks[self.current_task.current_block_index]
        
        # 高亮整个代码块范围（start_line 到 end_line）
        self.code_editor.set_guide_range(block.start_line - 1, block.end_line - 1)
        
        # 更新已完成的高亮行
        completed_lines = []
        for i, b in enumerate(self.current_task.blocks):
            if i < self.current_task.current_block_index:
                # 已完成的高亮整个代码块
                for line_num in range(b.start_line - 1, b.end_line):
                    completed_lines.append(line_num)
        
        self.code_editor.set_highlighted_lines(completed_lines)
    
    def update_step_instruction(self):
        """更新步骤指导"""
        if not self.current_task:
            return
        
        if self.current_task.current_block_index >= len(self.current_task.blocks):
            self.step_label.setText("✅ 所有步骤已完成!")
            self.block_progress.setValue(100)
            return
        
        block = self.current_task.blocks[self.current_task.current_block_index]
        progress = int((block.dwell_time / block.required_time) * 100)
        self.block_progress.setValue(min(100, progress))
        
        self.step_label.setText(
            f"步骤 {self.current_task.current_block_index + 1}/{len(self.current_task.blocks)}:\n"
            f"{block.description}\n"
            f"已注视: {block.dwell_time:.1f}s / {block.required_time:.1f}s"
        )
    
    def _check_and_accumulate_gaze(self, x, y, dt):
        """
        检查注视点是否在目标区域内并累计时间
        :param x: viewport X 坐标 (局部坐标)
        :param y: viewport Y 坐标 (局部坐标)
        :param dt: 时间间隔（秒）
        """
        if not self.current_task or not self.is_training:
            return
        
        current_block = self.current_task.blocks[self.current_task.current_block_index]
        
        # 获取当前代码块在 viewport 中的精确坐标
        cursor = self.code_editor.textCursor()
        cursor.movePosition(cursor.Start)
        cursor.movePosition(cursor.Down, n=current_block.start_line - 1)
        start_rect = self.code_editor.cursorRect(cursor)
        
        # 计算多行的高度
        cursor.movePosition(cursor.Down, n=current_block.end_line - current_block.start_line)
        end_rect = self.code_editor.cursorRect(cursor)
        
        # 定义判定区域：以黄色高亮行为准
        tx = 0
        ty = start_rect.y()
        tw = self.code_editor.viewport().width()
        th = end_rect.bottom() - start_rect.top()
        
        # 增加一点垂直方向的容错空间（上下各加 5px），防止红点边缘判定失效
        ty -= 5
        th += 10
        
        # 检查是否在目标区域内
        if tx <= x <= tx + tw and ty <= y <= ty + th:
            # 核心修复：无论 UI 是否更新，时间必须实时累加
            current_block.dwell_time += dt
            self.valid_fixations += 1
            
            # 增加连击数
            self.combo_count += 1
            if self.combo_count > self.max_combo:
                self.max_combo = self.combo_count
            
            # 计算得分（基础分 + 连击奖励）
            base_score = dt * 10
            combo_bonus = min(self.combo_count * 2, 20)
            self.score += int(base_score + combo_bonus)
            
            # 检查是否完成当前块
            if current_block.dwell_time >= current_block.required_time:
                current_block.completed = True
                self.score += 50
                self.combo_count = 0
                self.last_block_index = self.current_task.current_block_index
                self.current_task.current_block_index += 1
                
                if self.current_task.current_block_index >= len(self.current_task.blocks):
                    self.complete_task()
                else:
                    self.highlight_current_block()
            
            # 实时更新提示文字
            self.update_step_instruction()
        else:
            # 如果不在目标区域，重置连击数
            self.combo_count = 0
    
    def check_gaze(self, x, y, dt):
        """检查视线位置并更新训练状态（实时累加时间）"""
        if not self.is_training or not self.current_task:
            return
        
        # 确保 dt 是正数且合理
        if dt <= 0 or dt > 1.0:
            dt = 0.016
        
        # 核心修复：统一将传入的坐标转换为 Viewport 局部坐标
        # 无论传入的是全局坐标还是局部坐标，我们都通过 mapFromGlobal 进行标准化
        local_pos = self.code_editor.mapFromGlobal(QPoint(int(x), int(y)))
        local_x, local_y = local_pos.x(), local_pos.y()

        # 更新编辑器内的注视行显示（process_gaze_coordinate 内部也会做转换）
        self.code_editor.process_gaze_coordinate(x, y)
        
        # 累计当前注视行的停留时间
        current_line = self.code_editor.current_gaze_line
        if current_line >= 0:
            self.code_editor.update_gaze_dwell(current_line, dt)
            
            # 2. 实时存储原始眼动数据（每帧都存，用于回放）
            if self.current_record_id:
                try:
                    self.db.save_raw_gaze_data(
                        record_id=self.current_record_id,
                        timestamp=time.time(),
                        gaze_x=local_x,
                        gaze_y=local_y,
                        line_number=current_line
                    )
                except Exception as e:
                    pass # 避免频繁打印影响性能
            
            # 核心修复：基于“当前高亮块”的相对回视判定
            current_block = self.current_task.blocks[self.current_task.current_block_index]
            block_start = current_block.start_line
            block_end = current_block.end_line
            
            # 状态机逻辑：
            # 1. 如果视线在高亮块内，标记为“在区域内”
            if block_start <= current_line + 1 <= block_end: # current_line 是 0-based，代码行号是 1-based
                self.is_inside_target_block = True
            
            # 2. 如果之前在区域内，现在跑到了区域上方，算一次回视
            if hasattr(self, 'is_inside_target_block') and self.is_inside_target_block:
                if current_line + 1 < block_start:
                    self.regression_count += 1
                    self.is_inside_target_block = False # 标记已离开，防止重复计数
                    self._log(f"[回视] 从高亮块({block_start}-{block_end})跳出到第 {current_line + 1} 行")
            
            # 3. 如果视线回到了高亮块，重置状态，准备捕捉下一次回视
            elif hasattr(self, 'is_inside_target_block') and not self.is_inside_target_block:
                if block_start <= current_line + 1 <= block_end:
                    self.is_inside_target_block = True
                    self._log(f"[重置] 视线回到高亮块，准备捕捉下一次回视")
        
        # 执行核心的逻辑判断（使用统一的局部坐标）
        self._check_and_accumulate_gaze(local_x, local_y, dt)
        self.last_gaze_time = time.time()
        
        # 显示注视点（使用局部坐标绘制）
        if self.gaze_point_widget:
            viewport = self.code_editor.viewport()
            if (0 <= local_x < viewport.width() and 
                0 <= local_y < viewport.height()):
                self.gaze_point_widget.add_gaze_point(local_x, local_y)
        
        self.gaze_x = x
        self.gaze_y = y
        self.total_fixations += 1
        
        # 降低统计更新频率，每10次调用更新一次
        if not hasattr(self, '_stats_counter'):
            self._stats_counter = 0
        self._stats_counter += 1
        if self._stats_counter % 10 == 0:
            self.update_stats()
    
    def update_stats(self):
        """更新统计信息（只负责UI显示，不再累加时间）"""
        if not self.current_task or (not self.is_training and not self.is_paused):
            return
        
        elapsed = self.get_elapsed_training_time()
        
        # 简化统计信息显示，减少字符串拼接开销
        stats = (f"总注视点: {self.total_fixations}\n"
                 f"有效注视: {self.valid_fixations}\n"
                 f"回视次数: {self.regression_count}\n"
                 f"训练时长: {elapsed:.0f}秒\n\n"
                 f"完成率: {self.get_completion_rate():.0f}%")
        
        self.stats_text.setText(stats)
    
    def get_completion_rate(self):
        """计算完成率"""
        if not self.current_task:
            return 0
        
        completed = sum(1 for b in self.current_task.blocks if b.completed)
        return (completed / len(self.current_task.blocks)) * 100
    
    def set_target_area(self, line_number=None, block_index=None):
        """设置目标注视区域
        
        Args:
            line_number: 目标行号(从1开始)
            block_index: 或者直接指定代码块索引
        """
        if not self.current_task:
            return
        
        # 如果指定了代码块索引,直接设置
        if block_index is not None:
            if 0 <= block_index < len(self.current_task.blocks):
                self.current_task.current_block_index = block_index
                if self.is_training:
                    self.highlight_current_block()
                    self.update_step_instruction()
            return
        
        # 如果指定了行号,找到对应的代码块
        if line_number is not None:
            for i, block in enumerate(self.current_task.blocks):
                if block.start_line <= line_number <= block.end_line:
                    self.current_task.current_block_index = i
                    if self.is_training:
                        self.highlight_current_block()
                        self.update_step_instruction()
                    break
    
    def complete_task(self):
        """完成任务并自动保存到数据库"""
        self.is_training = False
        self.is_paused = False
        self.start_btn.setText("✅ 任务完成")
        
        self.db.flush_raw_gaze_data()
        elapsed = self.get_elapsed_training_time()
        self.current_task.total_time = elapsed
        
        completion_rate = self.get_completion_rate()
        accuracy = (self.valid_fixations / max(1, self.total_fixations)) * 100
        
        # 1. 更新训练摘要记录到数据库
        try:
            if self.current_record_id:
                self.db.update_training_record(
                    record_id=self.current_record_id,
                    completion_rate=completion_rate,
                    total_time=elapsed,
                    regression_count=self.regression_count,
                    accuracy=accuracy,
                    score=self.score
                )
                self._log(f"[数据库] 训练记录已更新，ID: {self.current_record_id}")
        except Exception as e:
            self._log(f"[数据库错误] 更新记录失败: {e}", force=True)
        
        message = (
            f"🎉 恭喜完成第 {self.current_task.level} 关!\n\n"
            f"用时: {elapsed:.1f}秒\n"
            f"准确率: {accuracy:.1f}%\n"
            f"回视次数: {self.regression_count}\n"
            f"完成率: {completion_rate:.0f}%"
        )
        
        self.step_label.setText("✅ 任务完成!")
        self.block_progress.setValue(100)
        
        self.task_completed.emit(message)

    def get_elapsed_training_time(self):
        """获取扣除暂停时长后的实际训练时间"""
        if not self.current_task or not self.current_task.start_time:
            return 0.0

        elapsed = time.time() - self.current_task.start_time - self.total_paused_duration
        if self.is_paused and self.pause_started_at is not None:
            elapsed -= max(0.0, time.time() - self.pause_started_at)
        return max(0.0, elapsed)
