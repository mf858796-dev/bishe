from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTextEdit, QProgressBar, QPushButton, QGroupBox,
                             QScrollArea, QFrame, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QPointF, QRectF
from PyQt5.QtGui import QFont, QColor, QPalette, QTextCharFormat, QTextCursor, QPainter, QPen, QBrush, QTextBlockUserData
import time
import math

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
    """支持行高亮和视觉引导的代码编辑器"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighted_lines = set()  # 需要高亮的行号
        self.current_guide_line = -1  # 当前引导的行号
        self.gaze_dwell_times = {}  # 每行的注视停留时间 {line_number: total_time}
        self.last_gaze_line = -1  # 上次注视的行号
        self.last_gaze_time = time.time()  # 上次注视时间
        
    def set_highlighted_lines(self, line_numbers):
        """设置需要高亮的行号集合"""
        self.highlighted_lines = set(line_numbers)
        self.viewport().update()
    
    def set_guide_line(self, line_number):
        """设置引导行（下一步该看的行）"""
        self.current_guide_line = line_number
        self.viewport().update()
    
    def update_gaze_dwell(self, line_number, dt):
        """更新某行的注视停留时间"""
        if line_number not in self.gaze_dwell_times:
            self.gaze_dwell_times[line_number] = 0
        self.gaze_dwell_times[line_number] += dt
    
    def get_line_at_position(self, y_pos):
        """根据Y坐标获取行号"""
        cursor = self.cursorForPosition(QPointF(0, y_pos).toPoint())
        return cursor.blockNumber()
    
    def paintEvent(self, event):
        """重写绘制事件，添加行高亮和引导标记"""
        super().paintEvent(event)
        
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 获取文档中的所有文本块
        document = self.document()
        block = document.begin()
        
        # 绘制高亮和引导
        while block.isValid():
            line_number = block.blockNumber()
            
            # 获取该行的矩形区域
            cursor = QTextCursor(block)
            rect = self.cursorRect(cursor)
            
            # 如果矩形无效（不在可见区域），跳过
            if not rect.isValid() or rect.height() <= 0:
                block = block.next()
                continue
            
            # 如果是引导行，绘制特殊标记
            if line_number == self.current_guide_line:
                # 绘制闪烁的边框
                flash_alpha = int(128 + 127 * math.sin(time.time() * 4))
                guide_color = QColor(251, 191, 36, flash_alpha)  # 黄色闪烁
                painter.setPen(QPen(guide_color, 3))
                painter.setBrush(QBrush(QColor(251, 191, 36, 50)))
                painter.drawRect(rect.adjusted(-5, 2, 5, -2))
                
                # 绘制箭头指示
                arrow_x = rect.right() + 10
                arrow_y = rect.center().y()
                painter.setPen(QPen(guide_color, 2))
                painter.drawLine(arrow_x - 8, arrow_y, arrow_x, arrow_y)
                painter.drawLine(arrow_x, arrow_y, arrow_x - 5, arrow_y - 5)
                painter.drawLine(arrow_x, arrow_y, arrow_x - 5, arrow_y + 5)
            
            # 如果是已完成的高亮行，绘制绿色背景
            elif line_number in self.highlighted_lines:
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(16, 185, 129, 40)))  # 半透明绿色
                painter.drawRect(rect.adjusted(-5, 2, 5, -2))
            
            block = block.next()
        
        painter.end()

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
    
    def __init__(self):
        super().__init__()
        
        # 训练状态
        self.current_task = None
        self.is_training = False
        self.gaze_x, self.gaze_y = 0, 0
        self.last_gaze_time = time.time()
        
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
        
    def init_ui(self):
        """初始化用户界面"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
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
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #3b82f6;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
        """)
        
        layout = QVBoxLayout(group)
        
        # 任务标题
        self.task_title_label = QLabel("请选择一个训练任务开始")
        self.task_title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #1e293b;")
        layout.addWidget(self.task_title_label)
        
        # 任务描述
        self.task_desc_label = QLabel("系统包含多个训练关卡,从基础的变量识别到复杂的逻辑理解")
        self.task_desc_label.setStyleSheet("font-size: 14px; color: #64748b;")
        self.task_desc_label.setWordWrap(True)
        layout.addWidget(self.task_desc_label)
        
        return group
    
    def create_code_editor(self):
        """创建代码编辑器"""
        group = QGroupBox("💻 代码阅读区")
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #10b981;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # 使用增强版代码编辑器
        self.code_editor = HighlightedCodeEditor()
        self.code_editor.setFont(QFont("Consolas", 13))
        self.code_editor.setReadOnly(True)
        
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
                background-color: #1e293b;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 12px;
                line-height: 1.6;
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
        self.line_hint_label.setStyleSheet("color: #94a3b8; font-size: 12px; margin-top: 4px;")
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
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                color: #f59e0b;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                margin-top: 10px;
                padding: 10px;
            }
        """)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        
        # 当前步骤
        self.step_label = QLabel("等待开始...")
        self.step_label.setStyleSheet("""
            font-size: 14px;
            color: #1e293b;
            padding: 8px;
            background-color: #f1f5f9;
            border-radius: 6px;
        """)
        self.step_label.setWordWrap(True)
        layout.addWidget(self.step_label)
        
        # 注视进度条
        progress_label = QLabel("注视进度:")
        progress_label.setStyleSheet("font-size: 12px; color: #64748b; margin-top: 4px;")
        layout.addWidget(progress_label)
        
        self.block_progress = QProgressBar()
        self.block_progress.setMinimum(0)
        self.block_progress.setMaximum(100)
        self.block_progress.setValue(0)
        self.block_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #e2e8f0;
                border-radius: 6px;
                text-align: center;
                background-color: #f1f5f9;
                height: 24px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #34d399);
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.block_progress)
        
        # 统计信息
        stats_label = QLabel("实时统计:")
        stats_label.setStyleSheet("font-size: 12px; color: #64748b; margin-top: 8px;")
        layout.addWidget(stats_label)
        
        # 游戏化反馈：得分和连击
        self.feedback_label = QLabel("")
        self.feedback_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #f59e0b;
                padding: 6px;
                background-color: #fef3c7;
                border-radius: 6px;
                qproperty-alignment: AlignCenter;
            }
        """)
        self.feedback_label.hide()  # 初始隐藏
        layout.addWidget(self.feedback_label)
        
        self.stats_text = QTextEdit()
        self.stats_text.setMaximumHeight(150)
        self.stats_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        self.stats_text.setReadOnly(True)
        layout.addWidget(self.stats_text)
        
        layout.addStretch()
        
        return group
    
    def create_control_panel(self):
        """创建控制面板"""
        layout = QHBoxLayout()
        
        # 任务选择按钮
        self.prev_btn = QPushButton("⬅️ 上一关")
        self.prev_btn.setStyleSheet(self.get_button_style("#6366f1"))
        self.prev_btn.clicked.connect(self.previous_task)
        layout.addWidget(self.prev_btn)
        
        self.start_btn = QPushButton("▶️ 开始训练")
        self.start_btn.setStyleSheet(self.get_button_style("#10b981"))
        self.start_btn.clicked.connect(self.toggle_training)
        layout.addWidget(self.start_btn, stretch=2)
        
        self.next_btn = QPushButton("➡️ 下一关")
        self.next_btn.setStyleSheet(self.get_button_style("#6366f1"))
        self.next_btn.clicked.connect(self.next_task)
        layout.addWidget(self.next_btn)
        
        # 重置按钮
        self.reset_btn = QPushButton("🔄 重置")
        self.reset_btn.setStyleSheet(self.get_button_style("#f59e0b"))
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
                CodeBlock("变量初始化", 2, 3, "注视变量 'total' 和 'count'"),
                CodeBlock("循环结构", 5, 7, "注视 'for' 关键字"),
                CodeBlock("累加操作", 6, 6, "注视 'total += i'"),
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
        """开始训练"""
        self.is_training = True
        self.start_btn.setText("⏸️ 暂停训练")
        self.current_task.start_time = time.time()
        self.current_task.current_block_index = 0
        self.total_fixations = 0
        self.valid_fixations = 0
        self.regression_count = 0
        self.last_block_index = -1
        
        # 重置游戏化元素
        self.score = 0
        self.combo_count = 0
        self.max_combo = 0
        self.achievements = []
        self.last_achievement_time = 0
        if hasattr(self, 'feedback_label'):
            self.feedback_label.hide()
        
        # 启动统计定时器
        self.stats_timer.stop()
        self.stats_timer.start(1000)  # 每秒更新一次
        
        if self.gaze_point_widget:
            # 设置为 viewport 的大小
            viewport = self.code_editor.viewport()
            self.gaze_point_widget.setGeometry(0, 0, viewport.width(), viewport.height())
            self.gaze_point_widget.show()
            self.gaze_point_widget.raise_()  # 提升到最上层
            self.gaze_point_widget.clear_points()
        
        # 高亮第一个代码块
        self.highlight_current_block()
        self.update_step_instruction()
        
    def stop_training(self):
        """停止训练"""
        self.is_training = False
        self.start_btn.setText("▶️ 继续训练")
        
        # 隐藏注视点组件
        if self.gaze_point_widget:
            self.gaze_point_widget.hide()
        
        # 停止统计定时器
        if hasattr(self, 'stats_timer'):
            self.stats_timer.stop()
        
        # 清除高亮
        cursor = self.code_editor.textCursor()
        cursor.clearSelection()
    
    def reset_current_task(self):
        """重置当前任务"""
        if self.current_task:
            self.current_task.current_block_index = 0
            for block in self.current_task.blocks:
                block.completed = False
                block.dwell_time = 0
            
            # 清除注视点
            if self.gaze_point_widget:
                self.gaze_point_widget.clear_points()
            
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
            
            # 重置任务状态和统计数据
            self.current_task.current_block_index = 0
            for block in self.current_task.blocks:
                block.completed = False
                block.dwell_time = 0
            
            # 重置统计数据
            self.total_fixations = 0
            self.valid_fixations = 0
            self.regression_count = 0
            self.last_block_index = -1
            
            # 清除注视点
            if self.gaze_point_widget:
                self.gaze_point_widget.clear_points()
            
            # 如果正在训练，重新开始
            if self.is_training:
                self.current_task.start_time = time.time()
                self.highlight_current_block()
            
            # 更新面板显示
            self.update_step_instruction()
            self.update_stats()
    
    def highlight_current_block(self):
        """高亮当前代码块"""
        if not self.current_task or not self.is_training:
            return
        
        block = self.current_task.blocks[self.current_task.current_block_index]
        
        # 选中代码行（优化：使用setPosition代替循环）
        cursor = self.code_editor.textCursor()
        
        # 获取起始行和结束行的位置
        cursor.movePosition(cursor.Start)
        cursor.movePosition(cursor.Down, n=block.start_line - 1)
        start_pos = cursor.position()
        
        cursor.movePosition(cursor.Down, n=block.end_line - block.start_line)
        cursor.movePosition(cursor.EndOfLine)
        end_pos = cursor.position()
        
        # 一次性设置选区
        cursor.setPosition(start_pos)
        cursor.setPosition(end_pos, cursor.KeepAnchor)
        
        # 设置高亮格式
        fmt = QTextCharFormat()
        fmt.setBackground(QColor("#3b82f6"))
        fmt.setForeground(QColor("#ffffff"))
        cursor.setCharFormat(fmt)
    
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
        :param x: viewport X 坐标
        :param y: viewport Y 坐标
        :param dt: 时间间隔（秒）
        """
        if not self.current_task or not self.is_training:
            return
        
        current_block = self.current_task.blocks[self.current_task.current_block_index]
        
        # 获取当前代码块在 viewport 中的坐标（只计算一次）
        cursor = self.code_editor.textCursor()
        cursor.movePosition(cursor.Start)
        cursor.movePosition(cursor.Down, n=current_block.start_line - 1)
        start_rect = self.code_editor.cursorRect(cursor)
        cursor.movePosition(cursor.Down, n=current_block.end_line - current_block.start_line)
        end_rect = self.code_editor.cursorRect(cursor)
        
        tx = 0
        ty = start_rect.y()
        tw = self.code_editor.viewport().width()
        th = end_rect.bottom() - start_rect.top()
        
        # 检查是否在目标区域内
        if tx <= x <= tx + tw and ty <= y <= ty + th:
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
            
            # 降低更新频率
            if not hasattr(self, '_instruction_counter'):
                self._instruction_counter = 0
            self._instruction_counter += 1
            if self._instruction_counter % 5 == 0:
                self.update_step_instruction()
    
    def check_gaze(self, x, y, dt):
        """检查视线位置并更新训练状态（只记录位置，不累加时间）"""
        # 严格检查:必须正在训练且有当前任务
        if not self.is_training or not self.current_task:
            return
        
        # 忽略无效的坐标
        if x <= 0 and y <= 0:
            return
        
        # 保存最新的注视点坐标
        self.last_gaze_x = x
        self.last_gaze_y = y
        self.last_gaze_time = time.time()
        
        # 显示注视点（x, y 已经是 viewport 坐标）
        if self.gaze_point_widget:
            viewport = self.code_editor.viewport()
            # 检查是否在 viewport 范围内
            if (0 <= x < viewport.width() and 
                0 <= y < viewport.height()):
                self.gaze_point_widget.add_gaze_point(x, y)
        
        current_block = self.current_task.blocks[self.current_task.current_block_index]
        
        # 获取当前代码块在 viewport 中的坐标（只计算一次）
        cursor = self.code_editor.textCursor()
        cursor.movePosition(cursor.Start)
        cursor.movePosition(cursor.Down, n=current_block.start_line - 1)
        start_rect = self.code_editor.cursorRect(cursor)
        cursor.movePosition(cursor.Down, n=current_block.end_line - current_block.start_line)
        end_rect = self.code_editor.cursorRect(cursor)
        
        block_top = start_rect.y()
        block_bottom = end_rect.bottom()
        
        # 检测回视：只有当注视点在目标代码块区域内时才检测
        if (hasattr(self, 'prev_gaze_y') and self.prev_gaze_y > 0 and
            block_top <= y <= block_bottom and
            block_top <= self.prev_gaze_y <= block_bottom):
            if y < self.prev_gaze_y - 10:
                self.regression_count += 1
        
        # 只更新在viewport内的Y坐标
        viewport = self.code_editor.viewport()
        if 0 <= y < viewport.height():
            self.prev_gaze_y = y
        
        self.gaze_x = x
        self.gaze_y = y
        self.total_fixations += 1
        
        # 降低统计更新频率，每10次调用更新一次
        if not hasattr(self, '_stats_counter'):
            self._stats_counter = 0
        self._stats_counter += 1
        if self._stats_counter % 10 == 0:
            self.update_stats()
    
    def _check_and_accumulate_gaze(self, x, y, dt):
        """
        检查注视点是否在目标区域内并累计时间
        :param x: viewport X 坐标
        :param y: viewport Y 坐标
        :param dt: 时间间隔（秒）
        """
        if not self.current_task or not self.is_training:
            return
        
        current_block = self.current_task.blocks[self.current_task.current_block_index]
        
        # 获取当前代码块在 viewport 中的坐标（只计算一次）
        cursor = self.code_editor.textCursor()
        cursor.movePosition(cursor.Start)
        cursor.movePosition(cursor.Down, n=current_block.start_line - 1)
        start_rect = self.code_editor.cursorRect(cursor)
        cursor.movePosition(cursor.Down, n=current_block.end_line - current_block.start_line)
        end_rect = self.code_editor.cursorRect(cursor)
        
        tx = 0
        ty = start_rect.y()
        tw = self.code_editor.viewport().width()
        th = end_rect.bottom() - start_rect.top()
        
        # 检查是否在目标区域内
        if tx <= x <= tx + tw and ty <= y <= ty + th:
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
            
            # 降低更新频率
            if not hasattr(self, '_instruction_counter'):
                self._instruction_counter = 0
            self._instruction_counter += 1
            if self._instruction_counter % 5 == 0:
                self.update_step_instruction()
    
    def update_stats(self):
        """更新统计信息 + 累加注视时间（核心入口）"""
        if not self.current_task or not self.is_training:
            return
        
        # 关键：如果有保存的注视点，累加时间
        if hasattr(self, 'last_gaze_x') and hasattr(self, 'last_gaze_y'):
            if self.last_gaze_time > 0:
                current_time = time.time()
                dt = current_time - self.last_gaze_time
                # 只要超过0.1秒就累加（兼容鼠标快速移动的情况）
                if dt >= 0.1:
                    self._check_and_accumulate_gaze(self.last_gaze_x, self.last_gaze_y, min(dt, 1.0))
                    self.last_gaze_time = current_time
        
        elapsed = time.time() - self.current_task.start_time if self.current_task.start_time else 0
        
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
        """完成任务"""
        self.is_training = False
        self.start_btn.setText("✅ 任务完成")
        
        elapsed = time.time() - self.current_task.start_time
        self.current_task.total_time = elapsed
        
        completion_rate = self.get_completion_rate()
        accuracy = (self.valid_fixations / max(1, self.total_fixations)) * 100
        
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
