"""
简单的眼动仪屏幕校准工具
用于校正gaze2d坐标到屏幕坐标的映射
"""
import sys
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, 
                             QVBoxLayout, QHBoxLayout, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor, QFont

class CalibrationWidget(QWidget):
    """校准点显示组件"""
    calibration_complete = pyqtSignal(dict)  # 发送校准结果
    
    def __init__(self):
        super().__init__()
        self.calibration_points = []  # 存储校准点数据
        self.current_point_index = 0
        self.gaze_samples = []  # 当前点的gaze样本
        
        # 校准点位置（9点校准）
        self.points = [
            (0.1, 0.1), (0.5, 0.1), (0.9, 0.1),  # 上排
            (0.1, 0.5), (0.5, 0.5), (0.9, 0.5),  # 中排
            (0.1, 0.9), (0.5, 0.9), (0.9, 0.9),  # 下排
        ]
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle("眼动仪屏幕校准")
        self.showFullScreen()
        self.setStyleSheet("background-color: white;")
        
        # 提示标签
        self.hint_label = QLabel("请注视红点，按空格键记录数据")
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.hint_label.setFont(QFont("Arial", 16))
        self.hint_label.setStyleSheet("color: #333; padding: 20px;")
        
        # 进度标签
        self.progress_label = QLabel(f"校准进度: 0/{len(self.points)}")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setFont(QFont("Arial", 14))
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        
        self.record_btn = QPushButton("记录当前点 (空格键)")
        self.record_btn.setFont(QFont("Arial", 12))
        self.record_btn.setFixedHeight(50)
        self.record_btn.clicked.connect(self.record_current_point)
        
        self.skip_btn = QPushButton("跳过")
        self.skip_btn.setFont(QFont("Arial", 12))
        self.skip_btn.setFixedHeight(50)
        self.skip_btn.clicked.connect(self.skip_current_point)
        
        self.cancel_btn = QPushButton("取消校准")
        self.cancel_btn.setFont(QFont("Arial", 12))
        self.cancel_btn.setFixedHeight(50)
        self.cancel_btn.clicked.connect(self.close)
        
        btn_layout.addWidget(self.record_btn)
        btn_layout.addWidget(self.skip_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        # 主布局
        layout = QVBoxLayout()
        layout.addWidget(self.hint_label)
        layout.addStretch()
        layout.addWidget(self.progress_label)
        layout.addLayout(btn_layout)
        layout.setContentsMargins(50, 50, 50, 50)
        
        self.setLayout(layout)
        
    def paintEvent(self, event):
        """绘制校准点"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.current_point_index < len(self.points):
            # 获取当前校准点的屏幕位置
            u, v = self.points[self.current_point_index]
            x = int(u * self.width())
            y = int(v * self.height())
            
            # 绘制外圈
            pen = QPen(QColor(255, 0, 0))
            pen.setWidth(3)
            painter.setPen(pen)
            painter.drawEllipse(x - 30, y - 30, 60, 60)
            
            # 绘制内圈
            painter.setBrush(QColor(255, 0, 0))
            painter.drawEllipse(x - 10, y - 10, 20, 20)
            
            # 绘制十字线
            painter.drawLine(x - 40, y, x + 40, y)
            painter.drawLine(x, y - 40, x, y + 40)
    
    def keyPressEvent(self, event):
        """键盘事件"""
        if event.key() == Qt.Key_Space:
            self.record_current_point()
        elif event.key() == Qt.Key_Escape:
            self.close()
    
    def record_current_point(self):
        """记录当前校准点"""
        if self.current_point_index >= len(self.points):
            return
        
        # 这里需要从眼动仪获取当前的gaze2d值
        # 由于我们无法直接访问眼动仪，这里只是示例
        # 实际使用时需要集成到主程序中
        screen_u, screen_v = self.points[self.current_point_index]
        
        # 提示用户输入实际的gaze2d读数
        from PyQt5.QtWidgets import QInputDialog
        
        gaze_u, ok1 = QInputDialog.getDouble(
            self, "输入Gaze U坐标", 
            f"请查看眼动仪数据，输入当前注视点的U值 (目标屏幕位置: {screen_u:.1f}):",
            0.0, 0.0, 1.0, 4
        )
        
        if not ok1:
            return
        
        gaze_v, ok2 = QInputDialog.getDouble(
            self, "输入Gaze V坐标",
            f"请查看眼动仪数据，输入当前注视点的V值 (目标屏幕位置: {screen_v:.1f}):",
            0.0, 0.0, 1.0, 4
        )
        
        if not ok2:
            return
        
        # 保存校准数据
        self.calibration_points.append({
            'screen_u': screen_u,
            'screen_v': screen_v,
            'gaze_u': gaze_u,
            'gaze_v': gaze_v
        })
        
        self.current_point_index += 1
        self.progress_label.setText(f"校准进度: {self.current_point_index}/{len(self.points)}")
        
        # 检查是否完成
        if self.current_point_index >= len(self.points):
            self.finish_calibration()
        else:
            self.update()  # 重绘下一个点
    
    def skip_current_point(self):
        """跳过当前点"""
        self.current_point_index += 1
        self.progress_label.setText(f"校准进度: {self.current_point_index}/{len(self.points)}")
        
        if self.current_point_index >= len(self.points):
            if len(self.calibration_points) >= 4:
                self.finish_calibration()
            else:
                QMessageBox.warning(self, "警告", "至少需要4个校准点！")
                self.current_point_index = len(self.calibration_points)
                self.progress_label.setText(f"校准进度: {self.current_point_index}/{len(self.points)}")
        else:
            self.update()
    
    def finish_calibration(self):
        """完成校准，计算映射参数"""
        if len(self.calibration_points) < 4:
            QMessageBox.warning(self, "警告", "校准点不足，无法计算映射！")
            return
        
        # 计算线性映射参数（简化版）
        # 实际应该使用更复杂的映射算法
        gaze_us = [p['gaze_u'] for p in self.calibration_points]
        gaze_vs = [p['gaze_v'] for p in self.calibration_points]
        screen_us = [p['screen_u'] for p in self.calibration_points]
        screen_vs = [p['screen_v'] for p in self.calibration_points]
        
        # 计算平均值作为偏移和缩放
        avg_gaze_u = sum(gaze_us) / len(gaze_us)
        avg_gaze_v = sum(gaze_vs) / len(gaze_vs)
        avg_screen_u = sum(screen_us) / len(screen_us)
        avg_screen_v = sum(screen_vs) / len(screen_vs)
        
        offset_u = avg_screen_u - avg_gaze_u
        offset_v = avg_screen_v - avg_gaze_v
        
        # 发送校准结果
        calibration_data = {
            'offset_u': offset_u,
            'offset_v': offset_v,
            'points': self.calibration_points
        }
        
        self.calibration_complete.emit(calibration_data)
        
        QMessageBox.information(self, "校准完成", 
                               f"已收集 {len(self.calibration_points)} 个校准点\n"
                               f"偏移量: U={offset_u:.4f}, V={offset_v:.4f}")
        self.close()


def main():
    app = QApplication(sys.argv)
    
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    msg.setText("眼动仪屏幕校准工具")
    msg.setInformativeText(
        "使用说明：\n\n"
        "1. 确保眼动仪已连接并正常工作\n"
        "2. 坐在正常的使用位置\n"
        "3. 依次注视屏幕上出现的红点\n"
        "4. 每次注视稳定后，按空格键或点击'记录'按钮\n"
        "5. 系统会提示您输入眼动仪显示的gaze2d坐标值\n"
        "6. 完成所有点后，系统会计算校准参数\n\n"
        "注意：这个工具需要配合主程序使用，\n"
        "校准后的参数需要手动应用到coordinate_mapper.py中"
    )
    msg.exec_()
    
    widget = CalibrationWidget()
    widget.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
