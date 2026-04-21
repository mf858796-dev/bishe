import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from matplotlib.patches import Rectangle
import os
from datetime import datetime

class ReportGenerator:
    def __init__(self, code_image_path=None):
        """
        :param code_image_path: 代码截图的路径，用于作为热力图的背景
        """
        self.code_image_path = code_image_path
        self.gaze_data = []  # 存储 (x, y) 坐标
        self.training_metrics = {}  # 存储训练指标
        self.start_time = None
        self.end_time = None

    def add_gaze_point(self, x, y):
        self.gaze_data.append((x, y))
    
    def set_metrics(self, metrics):
        """设置训练指标"""
        self.training_metrics = metrics
    
    def set_training_time(self, start_time, end_time=None):
        """设置训练时间"""
        self.start_time = start_time
        self.end_time = end_time or datetime.now()

    def generate_heatmap(self, save_path="heatmap.png"):
        """生成代码注视热力图"""
        if not self.gaze_data:
            return

        points = np.array(self.gaze_data)
        x = points[:, 0]
        y = points[:, 1]

        plt.figure(figsize=(12, 8))
        
        # 如果有代码背景图，先显示背景
        if self.code_image_path:
            img = plt.imread(self.code_image_path)
            plt.imshow(img, extent=[min(x), max(x), min(y), max(y)], aspect='auto', alpha=0.5)

        # 绘制热力图
        sns.kdeplot(x=x, y=y, fill=True, cmap="Reds", alpha=0.6)
        plt.title("Code Reading Attention Heatmap")
        plt.xlabel("Screen X Coordinate")
        plt.ylabel("Screen Y Coordinate")
        plt.savefig(save_path)
        plt.close()
        print(f"Heatmap saved to {save_path}")

    def generate_trajectory(self, save_path="trajectory.png"):
        """生成视线轨迹图"""
        if not self.gaze_data:
            return

        points = np.array(self.gaze_data)
        x = points[:, 0]
        y = points[:, 1]

        plt.figure(figsize=(12, 8))
        plt.plot(x, y, '-o', markersize=2, linewidth=0.5, color='blue', alpha=0.6)
        plt.title("Gaze Trajectory during Code Reading")
        plt.xlabel("Screen X Coordinate")
        plt.ylabel("Screen Y Coordinate")
        
        # 标记起点和终点
        plt.scatter([x[0]], [y[0]], c='green', s=100, label='Start')
        plt.scatter([x[-1]], [y[-1]], c='red', s=100, label='End')
        plt.legend()
        
        plt.savefig(save_path)
        plt.close()
        print(f"Trajectory saved to {save_path}")
    
    def generate_statistics_chart(self, save_path="statistics.png"):
        """生成多维度统计图表"""
        if not self.training_metrics:
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # 1. 有效注视率饼图
        ax1 = axes[0, 0]
        effective_rate = self.training_metrics.get('effective_fixation_rate', 0)
        ax1.pie([effective_rate, 1-effective_rate], 
                labels=['有效注视', '无效注视'],
                colors=['#2ecc71', '#e74c3c'],
                autopct='%1.1f%%')
        ax1.set_title('有效注视率')
        
        # 2. 回视次数柱状图
        ax2 = axes[0, 1]
        regression_count = self.training_metrics.get('regression_count', 0)
        ax2.bar(['回视次数'], [regression_count], color='#f39c12')
        ax2.set_ylabel('次数')
        ax2.set_title('回视分析')
        
        # 3. 扫视熵指标
        ax3 = axes[1, 0]
        entropy = self.training_metrics.get('saccade_entropy', 0)
        ax3.bar(['扫视熵'], [entropy], color='#9b59b6')
        ax3.set_ylabel('熵值')
        ax3.set_title('阅读路径混乱度')
        
        # 4. 数据质量评分
        ax4 = axes[1, 1]
        quality = self.training_metrics.get('data_quality_score', 0)
        ax4.bar(['数据质量'], [quality], color='#3498db')
        ax4.set_ylabel('评分 (0-1)')
        ax4.set_title('数据质量评估')
        ax4.set_ylim(0, 1)
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=150)
        plt.close()
        print(f"Statistics chart saved to {save_path}")
    
    def generate_full_report(self, save_dir="reports"):
        """生成完整的多维度分析报告"""
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 生成各种图表
        heatmap_path = os.path.join(save_dir, f"heatmap_{timestamp}.png")
        trajectory_path = os.path.join(save_dir, f"trajectory_{timestamp}.png")
        statistics_path = os.path.join(save_dir, f"statistics_{timestamp}.png")
        
        self.generate_heatmap(heatmap_path)
        self.generate_trajectory(trajectory_path)
        self.generate_statistics_chart(statistics_path)
        
        # 生成文本报告
        report_path = os.path.join(save_dir, f"report_{timestamp}.txt")
        self._generate_text_report(report_path)
        
        print(f"完整报告已生成至 {save_dir} 目录")
        return {
            'heatmap': heatmap_path,
            'trajectory': trajectory_path,
            'statistics': statistics_path,
            'text_report': report_path
        }
    
    def _generate_text_report(self, save_path):
        """生成文本格式的详细报告"""
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("代码阅读专注力训练分析报告\n")
            f.write("=" * 60 + "\n\n")
            
            # 训练时间
            if self.start_time and self.end_time:
                duration = (self.end_time - self.start_time).total_seconds()
                f.write(f"训练时长: {duration:.0f} 秒\n\n")
            
            # 核心指标
            f.write("一、核心指标分析\n")
            f.write("-" * 40 + "\n")
            
            if self.training_metrics:
                effective_rate = self.training_metrics.get('effective_fixation_rate', 0)
                f.write(f"有效注视率: {effective_rate:.1%}\n")
                
                regression_count = self.training_metrics.get('regression_count', 0)
                f.write(f"回视次数: {regression_count}\n")
                
                entropy = self.training_metrics.get('saccade_entropy', 0)
                f.write(f"扫视熵: {entropy:.3f}\n")
                
                avg_duration = self.training_metrics.get('average_fixation_duration', 0)
                f.write(f"平均注视时长: {avg_duration:.2f} 秒\n")
                
                scanpath_length = self.training_metrics.get('scanpath_length', 0)
                f.write(f"扫视路径总长度: {scanpath_length:.0f} 像素\n")
                
                quality = self.training_metrics.get('data_quality_score', 0)
                f.write(f"数据质量评分: {quality:.1%}\n")
            
            f.write("\n二、可视化图表\n")
            f.write("-" * 40 + "\n")
            f.write("- 热力图: 显示注视点分布密度\n")
            f.write("- 轨迹图: 显示视线移动路径\n")
            f.write("- 统计图: 多维度指标对比\n")
            
            f.write("\n三、改进建议\n")
            f.write("-" * 40 + "\n")
            
            # 根据指标给出建议
            if self.training_metrics:
                effective_rate = self.training_metrics.get('effective_fixation_rate', 0)
                if effective_rate < 0.6:
                    f.write("- 有效注视率较低，建议提高注意力集中度\n")
                
                regression_count = self.training_metrics.get('regression_count', 0)
                if regression_count > 10:
                    f.write("- 回视次数较多，建议改善代码阅读顺序\n")
                
                entropy = self.training_metrics.get('saccade_entropy', 0)
                if entropy > 0.7:
                    f.write("- 阅读路径较为混乱，建议采用结构化阅读方法\n")
            
            f.write("\n" + "=" * 60 + "\n")
    
    def generate_report(self, record, output_dir=None):
        """
        从训练记录生成报告
        :param record: 训练记录字典
        :param output_dir: 输出目录，默认为当前目录下的reports文件夹
        :return: 报告文件路径
        """
        if output_dir is None:
            output_dir = os.path.join(os.path.dirname(__file__), 'reports')
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 使用时间戳生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = os.path.join(output_dir, f"report_{timestamp}.txt")
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("=" * 60 + "\n")
                f.write("编程初学者代码阅读专注力训练报告\n")
                f.write("=" * 60 + "\n\n")
                
                # 基本信息
                f.write("一、基本信息\n")
                f.write("-" * 40 + "\n")
                f.write(f"训练日期: {record.get('date', '未知')}\n")
                f.write(f"任务名称: {record.get('task', '未知')}\n")
                f.write(f"训练时长: {record.get('duration', '未知')}\n")
                f.write(f"完成状态: {record.get('status', '未知')}\n\n")
                
                # 专注度分析
                f.write("二、专注度分析\n")
                f.write("-" * 40 + "\n")
                attention = record.get('attention', '0%')
                f.write(f"专注度评分: {attention}\n")
                
                try:
                    attention_value = int(attention.replace('%', ''))
                    if attention_value >= 90:
                        level = "优秀"
                        comment = "您的专注度非常出色！"
                    elif attention_value >= 75:
                        level = "良好"
                        comment = "您的专注度不错，继续保持！"
                    else:
                        level = "待提升"
                        comment = "建议改善阅读环境，提高注意力集中度。"
                    f.write(f"专注等级: {level}\n")
                    f.write(f"评价: {comment}\n\n")
                except:
                    pass
                
                # 眼动数据
                f.write("三、眼动数据统计\n")
                f.write("-" * 40 + "\n")
                gaze_count = record.get('gaze_count', 0)
                f.write(f"总注视点数: {gaze_count}\n")
                
                if self.gaze_data:
                    points = np.array(self.gaze_data)
                    f.write(f"数据采集量: {len(points)} 个点\n")
                    
                    # 计算覆盖区域
                    if len(points) > 0:
                        x_range = np.max(points[:, 0]) - np.min(points[:, 0])
                        y_range = np.max(points[:, 1]) - np.min(points[:, 1])
                        f.write(f"注视区域范围: {x_range:.0f} x {y_range:.0f} 像素\n")
                
                f.write("\n四、改进建议\n")
                f.write("-" * 40 + "\n")
                f.write("1. 保持稳定的头部位置，避免频繁移动\n")
                f.write("2. 采用结构化阅读方法，从上到下、从左到右\n")
                f.write("3. 遇到难点时适当放慢速度，深入理解\n")
                f.write("4. 定期休息，避免视觉疲劳\n")
                
                f.write("\n" + "=" * 60 + "\n")
                f.write(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 60 + "\n")
            
            print(f"报告已生成: {report_file}")
            return report_file
        
        except Exception as e:
            print(f"生成报告失败: {e}")
            import traceback
            traceback.print_exc()
            return None
