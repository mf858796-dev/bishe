import sqlite3
import os
from datetime import datetime

class DatabaseManager:
    def __init__(self, db_name="gaze_training.db"):
        self.db_path = os.path.join(os.path.dirname(__file__), db_name)
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 让结果可以通过列名访问
        return conn

    def init_db(self):
        """初始化数据库表结构"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 1. 用户信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT DEFAULT '',
                student_id TEXT,
                experience_level TEXT DEFAULT 'Beginner',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 兼容旧数据库：如果表已存在但缺少 password 列，则添加
        try:
            cursor.execute("SELECT password FROM users LIMIT 1")
        except sqlite3.OperationalError:
            print("[数据库升级] 检测到旧版本 users 表，正在添加 password 列...")
            cursor.execute("ALTER TABLE users ADD COLUMN password TEXT DEFAULT ''")
            conn.commit()
        
        # 2. 训练记录表 (Summary)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS training_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                task_level INTEGER,
                task_title TEXT,
                completion_rate REAL,
                total_time REAL,
                regression_count INTEGER,
                accuracy REAL,
                score INTEGER,
                trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # 3. 成就与徽章表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS achievements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                badge_name TEXT,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        # 4. 关卡题库表 (支持动态增删题目)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS levels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level_num INTEGER UNIQUE,
                title TEXT,
                code_content TEXT,
                target_lines TEXT, -- 存储目标注视行，如 "1,5-7,10"
                description TEXT
            )
        ''')

        # 5. 原始眼动时序数据 (高阶回放功能)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gaze_raw_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id INTEGER, -- 关联到 training_records 的 ID
                timestamp REAL,
                gaze_x REAL,
                gaze_y REAL,
                line_number INTEGER,
                FOREIGN KEY (record_id) REFERENCES training_records (id)
            )
        ''')
        
        conn.commit()
        conn.close()

    def add_user(self, username, password="", student_id=""):
        """添加新用户"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password, student_id) VALUES (?, ?, ?)", (username, password, student_id))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return self.get_user_id(username)
        finally:
            conn.close()

    def verify_password(self, username, password):
        """验证用户密码"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, password))
        result = cursor.fetchone()
        conn.close()
        return result['id'] if result else None

    def get_user_id(self, username):
        """获取用户ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()
        return result['id'] if result else None

    def save_training_record(self, user_id, task_level, task_title, completion_rate, 
                             total_time, regression_count, accuracy, score):
        """保存一次训练记录并返回记录ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO training_records 
            (user_id, task_level, task_title, completion_rate, total_time, 
             regression_count, accuracy, score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, task_level, task_title, completion_rate, total_time, 
              regression_count, accuracy, score))
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return record_id

    def save_raw_gaze_data(self, record_id, timestamp, gaze_x, gaze_y, line_number):
        """保存单帧原始眼动数据"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO gaze_raw_data 
            (record_id, timestamp, gaze_x, gaze_y, line_number)
            VALUES (?, ?, ?, ?, ?)
        ''', (record_id, timestamp, gaze_x, gaze_y, line_number))
        conn.commit()
        conn.close()

    def update_training_record(self, record_id, completion_rate, total_time, regression_count, accuracy, score):
        """更新已有的训练记录（用于任务完成时）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE training_records 
            SET completion_rate = ?, total_time = ?, regression_count = ?, 
                accuracy = ?, score = ?
            WHERE id = ?
        ''', (completion_rate, total_time, regression_count, accuracy, score, record_id))
        conn.commit()
        conn.close()

    def get_user_history(self, user_id, limit=10):
        """获取用户最近的训练历史"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM training_records 
            WHERE user_id = ? 
            ORDER BY trained_at DESC 
            LIMIT ?
        ''', (user_id, limit))
        records = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return records
