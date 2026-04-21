import numpy as np
from collections import deque

class AttentionEvaluator:
    def __init__(self, window_size=50, fixation_threshold_ms=200):
        """
        :param window_size: 滑动窗口大小（保留最近的 N 个采样点）
        :param fixation_threshold_ms: 判定为"有效注视"的最小停留时间阈值
        """
        self.window_size = window_size
        self.fixation_threshold_ms = fixation_threshold_ms
        self.gaze_history = deque(maxlen=window_size)  # 存储 (x, y, timestamp)
        
        # 数据清洗：过滤异常值
        self.filtered_history = deque(maxlen=window_size)  # 清洗后的数据
        
        # 关键代码区定义 (示例：左上角区域代表关键逻辑区)
        # 实际开发中这些坐标应由 UI 动态传入
        self.key_areas = [
            {'name': 'Header', 'rect': (0, 0, 800, 100)},
            {'name': 'Logic_Block_1', 'rect': (100, 200, 400, 300)}
        ]

    def add_gaze_point(self, x, y, timestamp):
        """添加一个新的视线点（包含数据清洗）"""
        # 过滤无效数据（眨眼、追踪丢失）
        if not self._is_valid_gaze_point(x, y):
            return
        
        self.gaze_history.append((x, y, timestamp))
        
        # 应用数据清洗算法
        cleaned_point = self._clean_gaze_data(x, y, timestamp)
        if cleaned_point:
            self.filtered_history.append(cleaned_point)
    
    def _is_valid_gaze_point(self, x, y):
        """检查视线点是否有效"""
        # 过滤负坐标或超出屏幕范围的点
        if x < 0 or y < 0 or x > 4000 or y > 4000:
            return False
        # 过滤(0,0)等异常点
        if x == 0 and y == 0:
            return False
        return True
    
    def _clean_gaze_data(self, x, y, timestamp):
        """数据清洗：去除噪声和异常值"""
        if len(self.filtered_history) < 2:
            return (x, y, timestamp)
        
        # 获取前一个有效点
        prev_x, prev_y, prev_ts = self.filtered_history[-1]
        
        # 计算移动速度（像素/秒）
        dt = timestamp - prev_ts
        if dt <= 0:
            return None
        
        distance = np.sqrt((x - prev_x)**2 + (y - prev_y)**2)
        velocity = distance / dt
        
        # 如果移动速度过快（可能是眨眼或追踪丢失），使用平滑处理
        max_velocity = 2000  # 最大合理速度 2000 像素/秒
        if velocity > max_velocity:
            # 使用前一点作为当前位置（保持平滑）
            return (prev_x, prev_y, timestamp)
        
        return (x, y, timestamp)

    def get_metrics(self):
        """计算并返回当前的专注力指标"""
        if len(self.gaze_history) < 5:
            return None

        points = np.array([(p[0], p[1]) for p in self.gaze_history])
        timestamps = np.array([p[2] for p in self.gaze_history])

        # 使用清洗后的数据计算指标
        if len(self.filtered_history) >= 5:
            filtered_points = np.array([(p[0], p[1]) for p in self.filtered_history])
            filtered_timestamps = np.array([p[2] for p in self.filtered_history])
        else:
            filtered_points = points
            filtered_timestamps = timestamps

        metrics = {
            "effective_fixation_rate": self._calc_effective_fixation(filtered_points, filtered_timestamps),
            "regression_count": self._calc_regression_count(filtered_points),
            "saccade_entropy": self._calc_saccade_entropy(filtered_points),
            "average_fixation_duration": self._calc_average_fixation_duration(filtered_timestamps),
            "scanpath_length": self._calc_scanpath_length(filtered_points),
            "data_quality_score": self._calc_data_quality_score()
        }
        return metrics

    def _calc_effective_fixation(self, points, timestamps):
        """计算有效注视率：落在关键区域的时长占比"""
        total_duration = timestamps[-1] - timestamps[0]
        if total_duration <= 0:
            return 0.0
        
        key_duration = 0
        # 简单的离散点统计：如果点在关键区内，累加其平均采样间隔
        avg_interval = total_duration / len(points)
        for x, y in points:
            for area in self.key_areas:
                rx, ry, rw, rh = area['rect']
                if rx <= x <= rx + rw and ry <= y <= ry + rh:
                    key_duration += avg_interval
                    break
        
        return min(1.0, key_duration / total_duration)

    def _calc_regression_count(self, points):
        """计算回视次数：Y轴坐标显著向上移动的次数（假设代码从上到下）"""
        regressions = 0
        threshold = 20  # 像素阈值，防止微小抖动被误判
        for i in range(1, len(points)):
            if points[i-1][1] - points[i][1] > threshold:
                regressions += 1
        return regressions

    def _calc_saccade_entropy(self, points):
        """计算视线跳跃熵：衡量阅读路径的混乱程度"""
        if len(points) < 2:
            return 0.0
        
        # 计算相邻点之间的欧氏距离（跳跃幅度）
        distances = []
        for i in range(1, len(points)):
            dist = np.linalg.norm(points[i] - points[i-1])
            distances.append(dist)
        
        if not distances:
            return 0.0

        # 将距离离散化到几个区间（bins）来计算熵
        hist, _ = np.histogram(distances, bins=10, range=(0, 500))
        probs = hist / np.sum(hist)
        
        # 计算香农熵
        entropy = -np.sum(probs * np.log2(probs + 1e-9))
        # 归一化熵值 (0-1)，最大值取决于 bins 数量
        max_entropy = np.log2(10)
        return entropy / max_entropy
    
    def _calc_average_fixation_duration(self, timestamps):
        """计算平均注视时长（秒）"""
        if len(timestamps) < 2:
            return 0.0
        
        # 计算相邻采样点的时间间隔
        intervals = np.diff(timestamps)
        # 过滤过短的间隔（可能是噪声）
        valid_intervals = intervals[intervals > 0.01]  # 大于10ms
        
        if len(valid_intervals) == 0:
            return 0.0
        
        return np.mean(valid_intervals)
    
    def _calc_scanpath_length(self, points):
        """计算扫视路径总长度（像素）"""
        if len(points) < 2:
            return 0.0
        
        total_length = 0
        for i in range(1, len(points)):
            total_length += np.linalg.norm(points[i] - points[i-1])
        
        return total_length
    
    def _calc_data_quality_score(self):
        """计算数据质量分数（0-1）"""
        if len(self.gaze_history) == 0:
            return 0.0
        
        # 数据质量 = 清洗后的数据量 / 原始数据量
        quality = len(self.filtered_history) / len(self.gaze_history)
        return quality
    
    def get_attention_score(self):
        """获取专注度评分 (0-100)"""
        metrics = self.get_metrics()
        if metrics is None:
            return 85  # 默认值
        
        # 基于多个指标计算专注度
        # 1. 有效注视率（越高越好）
        fixation_rate = metrics.get('effective_fixation_rate', 0) * 100
        
        # 2. 回视次数（越少越好）
        regression_count = metrics.get('regression_count', 0)
        regression_penalty = min(30, regression_count * 2)
        
        # 3. 视线熵（越低越专注）
        entropy = metrics.get('saccade_entropy', 0.5)
        entropy_penalty = entropy * 20
        
        # 4. 数据质量
        data_quality = metrics.get('data_quality_score', 1) * 10
        
        # 综合计算
        score = fixation_rate - regression_penalty - entropy_penalty + data_quality
        score = max(0, min(100, score))  # 限制在 0-100 范围
        
        return score
    
    def get_avg_fixation_duration(self):
        """获取平均注视时长（毫秒）"""
        metrics = self.get_metrics()
        if metrics is None:
            return 230
        
        avg_duration = metrics.get('average_fixation_duration', 0.23)
        return avg_duration * 1000  # 转换为毫秒
    
    def get_regression_count(self):
        """获取回视次数"""
        metrics = self.get_metrics()
        if metrics is None:
            return 12
        
        return metrics.get('regression_count', 0)
    
    def get_training_duration(self):
        """获取训练时长（分钟）"""
        if len(self.gaze_history) < 2:
            return 0
        
        first_time = self.gaze_history[0][2]
        last_time = self.gaze_history[-1][2]
        duration_seconds = last_time - first_time
        
        return max(1, duration_seconds / 60)  # 至少 1 分钟
    
    def get_max_deviation(self):
        """获取最大偏离距离（像素）"""
        if len(self.gaze_history) < 2:
            return 0
        
        points = np.array([(g[0], g[1]) for g in self.gaze_history])
        if len(points) < 2:
            return 0
        
        # 计算所有点之间的最大距离
        max_dist = 0
        center = np.mean(points, axis=0)
        
        for point in points:
            dist = np.sqrt(np.sum((point - center) ** 2))
            max_dist = max(max_dist, dist)
        
        return max_dist
