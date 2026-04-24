import sqlite3
import os
from datetime import datetime
from contextlib import closing

class DatabaseManager:
    def __init__(self, db_name="gaze_training.db"):
        self.db_path = os.path.join(os.path.dirname(__file__), db_name)
        self._raw_gaze_buffer = []
        self._raw_gaze_buffer_limit = 50
        self.debug_enabled = False
        self.init_db()

    def _log(self, message, force=False):
        if force or self.debug_enabled:
            print(message)

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """初始化数据库表结构"""
        with closing(self.get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")

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

            try:
                cursor.execute("SELECT password FROM users LIMIT 1")
            except sqlite3.OperationalError:
                self._log("[数据库升级] 检测到旧版本 users 表，正在添加 password 列...", force=True)
                cursor.execute("ALTER TABLE users ADD COLUMN password TEXT DEFAULT ''")
                conn.commit()

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

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS achievements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    badge_name TEXT,
                    unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS levels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level_num INTEGER UNIQUE,
                    title TEXT,
                    code_content TEXT,
                    target_lines TEXT,
                    description TEXT
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS gaze_raw_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    record_id INTEGER,
                    timestamp REAL,
                    gaze_x REAL,
                    gaze_y REAL,
                    line_number INTEGER,
                    FOREIGN KEY (record_id) REFERENCES training_records (id)
                )
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_training_records_user_time
                ON training_records (user_id, trained_at DESC)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_gaze_raw_record_time
                ON gaze_raw_data (record_id, timestamp)
            ''')

            conn.commit()

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

    def get_user_by_id(self, user_id):
        """根据 ID 获取用户信息"""
        with closing(self.get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_user_profile(self, user_id, username=None, student_id=None, experience_level=None):
        """更新用户档案信息"""
        fields = []
        values = []

        if username is not None:
            fields.append("username = ?")
            values.append(username)
        if student_id is not None:
            fields.append("student_id = ?")
            values.append(student_id)
        if experience_level is not None:
            fields.append("experience_level = ?")
            values.append(experience_level)

        if not fields:
            return False

        values.append(user_id)

        with closing(self.get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE users SET {', '.join(fields)} WHERE id = ?",
                values
            )
            conn.commit()
            return cursor.rowcount > 0

    def save_training_record(self, user_id, task_level, task_title, completion_rate,
                             total_time, regression_count, accuracy, score):
        """保存一次训练记录并返回记录ID"""
        with closing(self.get_connection()) as conn:
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
            return record_id

    def save_raw_gaze_data(self, record_id, timestamp, gaze_x, gaze_y, line_number):
        """缓冲保存单帧原始眼动数据，降低高频提交开销"""
        self._raw_gaze_buffer.append((record_id, timestamp, gaze_x, gaze_y, line_number))
        if len(self._raw_gaze_buffer) >= self._raw_gaze_buffer_limit:
            self.flush_raw_gaze_data()

    def flush_raw_gaze_data(self):
        """批量落盘原始眼动数据"""
        if not self._raw_gaze_buffer:
            return

        batch = self._raw_gaze_buffer
        self._raw_gaze_buffer = []

        try:
            with closing(self.get_connection()) as conn:
                cursor = conn.cursor()
                cursor.executemany('''
                    INSERT INTO gaze_raw_data
                    (record_id, timestamp, gaze_x, gaze_y, line_number)
                    VALUES (?, ?, ?, ?, ?)
                ''', batch)
                conn.commit()
        except Exception:
            self._raw_gaze_buffer = batch + self._raw_gaze_buffer
            raise

    def update_training_record(self, record_id, completion_rate, total_time, regression_count, accuracy, score):
        """更新已有的训练记录（用于任务完成时）"""
        self.flush_raw_gaze_data()
        with closing(self.get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE training_records
                SET completion_rate = ?, total_time = ?, regression_count = ?,
                    accuracy = ?, score = ?
                WHERE id = ?
            ''', (completion_rate, total_time, regression_count, accuracy, score, record_id))
            conn.commit()

    def get_user_history(self, user_id, limit=10):
        """获取用户最近的训练历史"""
        with closing(self.get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM training_records
                WHERE user_id = ?
                ORDER BY trained_at DESC
                LIMIT ?
            ''', (user_id, limit))
            return [dict(row) for row in cursor.fetchall()]

    def get_user_training_summary(self, user_id):
        """聚合获取用户训练统计摘要"""
        with closing(self.get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT
                    COUNT(*) AS total_sessions,
                    COALESCE(AVG(score), 0) AS avg_score,
                    COALESCE(MAX(score), 0) AS best_score,
                    COALESCE(SUM(total_time), 0) AS total_time
                FROM training_records
                WHERE user_id = ?
            ''', (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else {
                'total_sessions': 0,
                'avg_score': 0,
                'best_score': 0,
                'total_time': 0,
            }
