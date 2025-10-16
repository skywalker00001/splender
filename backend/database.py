"""
玩家数据库系统 - 使用SQLite保存玩家数据和游戏历史
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import threading

# 数据库文件路径
DB_PATH = Path(__file__).parent / "splendor_game.db"

# 线程锁，确保数据库操作线程安全
db_lock = threading.Lock()


class GameDatabase:
    """游戏数据库管理类"""
    
    def __init__(self, db_path: str = None):
        """初始化数据库连接"""
        self.db_path = db_path or str(DB_PATH)
        self.init_database()
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使查询结果可以像字典一样访问
        return conn
    
    def init_database(self):
        """初始化数据库表结构"""
        with db_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 创建用户表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_games INTEGER DEFAULT 0,
                    total_wins INTEGER DEFAULT 0,
                    total_points INTEGER DEFAULT 0
                )
            ''')
            
            # 创建游戏参与记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS game_participations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    game_id TEXT NOT NULL,
                    game_history_file TEXT NOT NULL,
                    player_name TEXT NOT NULL,
                    final_rank INTEGER,
                    final_score INTEGER,
                    is_winner BOOLEAN DEFAULT 0,
                    game_start_time TIMESTAMP,
                    game_end_time TIMESTAMP,
                    total_turns INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            
            # 创建索引
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_games 
                ON game_participations(user_id, game_end_time DESC)
            ''')
            
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_game_id 
                ON game_participations(game_id)
            ''')
            
            conn.commit()
            conn.close()
    
    def get_or_create_user(self, username: str) -> Dict[str, Any]:
        """获取或创建用户"""
        with db_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 尝试获取用户
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
            
            if user:
                # 更新最后登录时间
                cursor.execute(
                    'UPDATE users SET last_login = ? WHERE username = ?',
                    (datetime.now().isoformat(), username)
                )
                conn.commit()
                user_dict = dict(user)
            else:
                # 创建新用户
                cursor.execute(
                    'INSERT INTO users (username) VALUES (?)',
                    (username,)
                )
                conn.commit()
                user_id = cursor.lastrowid
                
                # 获取新创建的用户
                cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
                user = cursor.fetchone()
                user_dict = dict(user)
            
            conn.close()
            return user_dict
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """根据用户名获取用户信息"""
        with db_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
            
            conn.close()
            return dict(user) if user else None
    
    def record_game_participation(
        self, 
        username: str,
        game_id: str,
        game_history_file: str,
        player_name: str,
        final_rank: int,
        final_score: int,
        is_winner: bool,
        game_start_time: str,
        game_end_time: str,
        total_turns: int
    ) -> bool:
        """记录用户参与的游戏"""
        with db_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 获取用户ID（直接在此查询，避免嵌套锁）
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
            
            if not user:
                # 创建新用户
                cursor.execute('INSERT INTO users (username) VALUES (?)', (username,))
                conn.commit()
                user_id = cursor.lastrowid
            else:
                user_id = user['id']
            
            # 记录游戏参与
            cursor.execute('''
                INSERT INTO game_participations 
                (user_id, game_id, game_history_file, player_name, 
                 final_rank, final_score, is_winner, 
                 game_start_time, game_end_time, total_turns)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, game_id, game_history_file, player_name,
                final_rank, final_score, is_winner,
                game_start_time, game_end_time, total_turns
            ))
            
            # 更新用户统计
            cursor.execute('''
                UPDATE users 
                SET total_games = total_games + 1,
                    total_wins = total_wins + ?,
                    total_points = total_points + ?
                WHERE id = ?
            ''', (1 if is_winner else 0, final_score, user_id))
            
            conn.commit()
            conn.close()
            return True
    
    def get_user_game_history(
        self, 
        username: str, 
        limit: int = 50, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取用户的游戏历史"""
        with db_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 获取用户ID（直接查询，避免嵌套锁）
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
            if not user:
                conn.close()
                return []
            
            user_id = user['id']
            
            # 查询游戏历史
            cursor.execute('''
                SELECT * FROM game_participations 
                WHERE user_id = ? 
                ORDER BY game_end_time DESC 
                LIMIT ? OFFSET ?
            ''', (user_id, limit, offset))
            
            games = cursor.fetchall()
            conn.close()
            
            return [dict(game) for game in games]
    
    def get_user_statistics(self, username: str) -> Optional[Dict[str, Any]]:
        """获取用户统计信息"""
        with db_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # 获取用户（直接查询，避免嵌套锁）
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            user = cursor.fetchone()
            if not user:
                conn.close()
                return None
            
            user_id = user['id']
            
            # 基本统计
            stats = {
                'username': username,
                'total_games': user['total_games'],
                'total_wins': user['total_wins'],
                'total_points': user['total_points'],
                'win_rate': user['total_wins'] / user['total_games'] if user['total_games'] > 0 else 0,
                'avg_score': user['total_points'] / user['total_games'] if user['total_games'] > 0 else 0
            }
            
            # 最高分数
            cursor.execute('''
                SELECT MAX(final_score) as highest_score,
                       MIN(final_score) as lowest_score,
                       AVG(final_score) as avg_score
                FROM game_participations
                WHERE user_id = ?
            ''', (user_id,))
            score_stats = cursor.fetchone()
            if score_stats:
                stats['highest_score'] = score_stats['highest_score']
                stats['lowest_score'] = score_stats['lowest_score']
            
            # 排名分布
            cursor.execute('''
                SELECT final_rank, COUNT(*) as count
                FROM game_participations
                WHERE user_id = ?
                GROUP BY final_rank
                ORDER BY final_rank
            ''', (user_id,))
            rank_distribution = cursor.fetchall()
            stats['rank_distribution'] = {
                row['final_rank']: row['count'] 
                for row in rank_distribution
            }
            
            conn.close()
            return stats
    
    def get_game_details(self, game_id: str) -> Optional[Dict[str, Any]]:
        """获取特定游戏的详细信息"""
        with db_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM game_participations 
                WHERE game_id = ?
                ORDER BY final_rank
            ''', (game_id,))
            
            participations = cursor.fetchall()
            conn.close()
            
            if not participations:
                return None
            
            # 返回游戏详情
            return {
                'game_id': game_id,
                'game_history_file': participations[0]['game_history_file'],
                'game_start_time': participations[0]['game_start_time'],
                'game_end_time': participations[0]['game_end_time'],
                'total_turns': participations[0]['total_turns'],
                'players': [
                    {
                        'player_name': p['player_name'],
                        'final_rank': p['final_rank'],
                        'final_score': p['final_score'],
                        'is_winner': bool(p['is_winner'])
                    }
                    for p in participations
                ]
            }
    
    def clear_all_data(self):
        """清除所有数据（仅用于测试）"""
        with db_lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM game_participations')
            cursor.execute('DELETE FROM users')
            
            conn.commit()
            conn.close()


# 创建全局数据库实例
game_db = GameDatabase()

