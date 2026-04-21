"""
使用鼠标位置模拟注视点 - 方便测试训练模块
"""
import sys
from PyQt5.QtWidgets import QApplication, QPushButton, QVBoxLayout
from PyQt5.QtCore import Qt
from training_widget import TrainingWidget

class TestTrainingWidget(TrainingWidget):
    """增强的训练组件，支持鼠标追踪"""
    
    def __init__(self):
        super().__init__()
        self.setMouseTracking(True)
        
        # 添加一个提示标签
        from PyQt5.QtWidgets import QLabel
        hint_label = QLabel("💡 提示: 在代码区域移动鼠标来模拟注视点")
        hint_label.setStyleSheet("""
            background-color: #fef3c7;
            color: #92400e;
            padding: 8px;
            border-radius: 6px;
            font-size: 13px;
        """)
        self.layout().insertWidget(1, hint_label)
        
        # 添加测试按钮
        test_btn_layout = QVBoxLayout()
        self.auto_test_btn = QPushButton("🎯 自动测试（在目标区域模拟注视）")
        self.auto_test_btn.clicked.connect(self.start_auto_test)
        test_btn_layout.addWidget(self.auto_test_btn)
        self.layout().addLayout(test_btn_layout)
        
        self.auto_test_timer = None
        
        # 启用代码编辑器的鼠标追踪
        self.code_editor.setMouseTracking(True)
        
        # 安装事件过滤器，捕获 viewport 的鼠标移动事件
        self.code_editor.viewport().installEventFilter(self)
    
    def eventFilter(self, obj, event):
        """事件过滤器 - 捕获 viewport 的鼠标移动事件"""
        from PyQt5.QtCore import QEvent
        if obj == self.code_editor.viewport() and event.type() == QEvent.MouseMove:
            if self.is_training and self.gaze_point_widget:
                # 获取鼠标相对于 viewport 的位置
                pos = event.pos()
                
                # 直接添加注视点
                self.gaze_point_widget.add_gaze_point(pos.x(), pos.y())
                
                # 调用 check_gaze 更新训练状态
                import time
                dt = 0.016
                self.check_gaze(pos.x(), pos.y(), dt)
        return super().eventFilter(obj, event)
    
    def start_auto_test(self):
        """开始自动测试 - 在目标区域模拟注视"""
        if not self.is_training:
            print("请先点击'开始训练'按钮")
            return
        
        from PyQt5.QtCore import QTimer
        
        # 获取当前目标区域的位置（相对于 viewport）
        viewport = self.code_editor.viewport()
        cursor = self.code_editor.textCursor()
        cursor.movePosition(cursor.Start)
        current_block = self.current_task.blocks[self.current_task.current_block_index]
        cursor.movePosition(cursor.Down, n=current_block.start_line - 1)
        rect = self.code_editor.cursorRect(cursor)
        
        # 计算目标区域中心（相对于 viewport）
        target_x = viewport.width() // 2
        target_y = rect.y() + rect.height() // 2
        
        print(f"[自动测试] 开始在目标区域 ({target_x}, {target_y}) 模拟注视")
        
        # 创建定时器，每100ms调用一次 check_gaze
        self.auto_test_timer = QTimer()
        self.auto_test_timer.timeout.connect(lambda: self.simulate_gaze_at(target_x, target_y))
        self.auto_test_timer.start(100)
        
        # 10秒后停止
        QTimer.singleShot(10000, self.stop_auto_test)
    
    def simulate_gaze_at(self, x, y):
        """在指定位置模拟注视"""
        dt = 0.1  # 100ms
        self.check_gaze(x, y, dt)
        print(f"[自动测试] 模拟注视点: ({x}, {y}), 已注视: {self.current_task.blocks[self.current_task.current_block_index].dwell_time:.1f}s")
    
    def stop_auto_test(self):
        """停止自动测试"""
        if self.auto_test_timer:
            self.auto_test_timer.stop()
            self.auto_test_timer = None
            print("[自动测试] 已停止")
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件 - 模拟注视点"""
        if self.is_training and self.gaze_point_widget:
            # 获取 viewport
            viewport = self.code_editor.viewport()
            
            # 将鼠标位置转换为全局坐标，再转换为 viewport 的本地坐标
            global_pos = self.mapToGlobal(event.pos())
            local_pos = viewport.mapFromGlobal(global_pos)
            
            # 直接添加注视点
            self.gaze_point_widget.add_gaze_point(local_pos.x(), local_pos.y())
            
            # 调用 check_gaze 更新训练状态（也使用 viewport 坐标）
            import time
            dt = 0.016
            self.check_gaze(local_pos.x(), local_pos.y(), dt)
        
        super().mouseMoveEvent(event)

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    widget = TestTrainingWidget()
    widget.setWindowTitle("训练模块测试 - 鼠标模拟注视点")
    widget.resize(1400, 900)
    widget.show()
    
    print("=" * 70)
    print("🎯 训练模块注视点显示测试程序")
    print("=" * 70)
    print("\n使用说明:")
    print("  1. 选择一个训练任务")
    print("  2. 点击'▶️ 开始训练'按钮")
    print("  3. 在代码编辑器区域移动鼠标")
    print("  4. 观察红色注视点的显示效果")
    print("  5. 查看控制台的调试信息")
    print("\n预期效果:")
    print("  ✓ 鼠标位置会显示红色圆点")
    print("  ✓ 最新的点较大且不透明")
    print("  ✓ 旧的点逐渐变小并变透明")
    print("  ✓ 最多显示20个点，每个点存活2秒")
    print("=" * 70)
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
