#!/usr/bin/env python3
"""
数据库查询工具 - 直接在后台查看玩家和对局信息
使用方法：python query_database.py
"""
import sqlite3
from pathlib import Path
from datetime import datetime
import json

# 数据库路径
DB_PATH = Path(__file__).parent / "backend" / "splendor_game.db"


class DatabaseViewer:
    """数据库查看器"""
    
    def __init__(self):
        self.db_path = str(DB_PATH)
        if not Path(self.db_path).exists():
            print(f"❌ 数据库文件不存在: {self.db_path}")
            exit(1)
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def show_all_users(self):
        """显示所有用户"""
        print("\n" + "="*100)
        print("👥 所有用户列表")
        print("="*100)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                id,
                username,
                created_at,
                last_login,
                total_games,
                total_wins,
                total_points
            FROM users
            ORDER BY created_at DESC
        ''')
        
        users = cursor.fetchall()
        conn.close()
        
        if not users:
            print("📭 暂无用户数据")
            return
        
        print(f"\n共有 {len(users)} 个用户：\n")
        print(f"{'ID':<5} {'用户名':<20} {'注册时间':<20} {'最后登录':<20} {'总对局':<8} {'胜场':<8} {'总分':<8} {'胜率':<8}")
        print("-" * 100)
        
        for user in users:
            win_rate = f"{user['total_wins']/user['total_games']*100:.1f}%" if user['total_games'] > 0 else "N/A"
            print(f"{user['id']:<5} {user['username']:<20} {user['created_at']:<20} {user['last_login']:<20} "
                  f"{user['total_games']:<8} {user['total_wins']:<8} {user['total_points']:<8} {win_rate:<8}")
    
    def show_user_detail(self, username):
        """显示用户详细信息"""
        print("\n" + "="*100)
        print(f"🔍 用户详细信息: {username}")
        print("="*100)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 获取用户基本信息
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        
        if not user:
            print(f"❌ 用户不存在: {username}")
            conn.close()
            return
        
        print(f"\n📋 基本信息：")
        print(f"  ID: {user['id']}")
        print(f"  用户名: {user['username']}")
        print(f"  注册时间: {user['created_at']}")
        print(f"  最后登录: {user['last_login']}")
        print(f"  总对局数: {user['total_games']}")
        print(f"  胜场: {user['total_wins']}")
        print(f"  总积分: {user['total_points']}")
        if user['total_games'] > 0:
            print(f"  胜率: {user['total_wins']/user['total_games']*100:.1f}%")
        
        # 获取用户的游戏历史
        try:
            cursor.execute('''
                SELECT * FROM game_history 
                WHERE players LIKE ?
                ORDER BY end_time DESC
                LIMIT 20
            ''', (f'%{username}%',))
            
            games = cursor.fetchall()
        except sqlite3.OperationalError:
            games = []
        
        conn.close()
        
        if games:
            print(f"\n🎮 最近20场对局：")
            print(f"\n{'对局ID':<10} {'结束时间':<20} {'轮次':<6} {'获胜者':<20} {'玩家数':<6}")
            print("-" * 100)
            
            for game in games:
                players = json.loads(game['players'])
                print(f"{game['game_id']:<10} {game['end_time']:<20} {game['total_turns']:<6} "
                      f"{game['winner']:<20} {len(players):<6}")
    
    def show_recent_games(self, limit=20):
        """显示最近的对局"""
        print("\n" + "="*100)
        print(f"🎮 最近 {limit} 场对局")
        print("="*100)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM game_history
                ORDER BY end_time DESC
                LIMIT ?
            ''', (limit,))
            
            games = cursor.fetchall()
        except sqlite3.OperationalError:
            print("⚠️  对局历史表还未初始化")
            print("💡 提示：需要先完成至少一局游戏")
            conn.close()
            return
        
        conn.close()
        
        if not games:
            print("📭 暂无对局记录")
            return
        
        print(f"\n{'对局ID':<15} {'房间ID':<15} {'结束时间':<20} {'获胜者':<20} {'轮次':<6} {'玩家':<30}")
        print("-" * 100)
        
        for game in games:
            players = json.loads(game['players'])
            players_str = ", ".join(players[:3])
            if len(players) > 3:
                players_str += "..."
            
            print(f"{game['game_id']:<15} {game['room_id']:<15} {game['end_time']:<20} "
                  f"{game['winner']:<20} {game['total_turns']:<6} {players_str:<30}")
    
    def show_game_detail(self, game_id):
        """显示对局详细信息"""
        print("\n" + "="*100)
        print(f"🎮 对局详细信息: {game_id}")
        print("="*100)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM game_history WHERE game_id = ?', (game_id,))
            game = cursor.fetchone()
        except sqlite3.OperationalError:
            print("⚠️  对局历史表还未初始化")
            print("💡 提示：需要先完成至少一局游戏")
            conn.close()
            return
        
        conn.close()
        
        if not game:
            print(f"❌ 对局不存在: {game_id}")
            return
        
        players = json.loads(game['players'])
        final_scores = json.loads(game['final_scores'])
        
        print(f"\n📋 基本信息：")
        print(f"  对局ID: {game['game_id']}")
        print(f"  房间ID: {game['room_id']}")
        print(f"  开始时间: {game['start_time']}")
        print(f"  结束时间: {game['end_time']}")
        print(f"  总轮次: {game['total_turns']}")
        print(f"  获胜者: {game['winner']}")
        
        print(f"\n👥 玩家列表 ({len(players)}人)：")
        for player in players:
            print(f"  - {player}")
        
        print(f"\n🏆 最终分数：")
        for player, score in final_scores.items():
            winner_mark = "👑" if player == game['winner'] else "  "
            print(f"  {winner_mark} {player}: {score}分")
    
    def show_statistics(self):
        """显示统计信息"""
        print("\n" + "="*100)
        print("📊 数据库统计")
        print("="*100)
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 用户统计
            cursor.execute('SELECT COUNT(*) as count FROM users')
            user_count = cursor.fetchone()['count']
            
            cursor.execute('SELECT SUM(total_games) as total FROM users')
            total_games = cursor.fetchone()['total'] or 0
            
            # 对局统计
            try:
                cursor.execute('SELECT COUNT(*) as count FROM game_history')
                game_count = cursor.fetchone()['count']
                
                cursor.execute('SELECT AVG(total_turns) as avg_turns FROM game_history')
                avg_turns = cursor.fetchone()['avg_turns'] or 0
            except sqlite3.OperationalError:
                game_count = 0
                avg_turns = 0
            
            # 最活跃玩家
            cursor.execute('''
                SELECT username, total_games, total_wins, total_points
                FROM users
                ORDER BY total_games DESC
                LIMIT 5
            ''')
            top_players = cursor.fetchall()
            
            conn.close()
            
            print(f"\n📈 总体数据：")
            print(f"  注册用户数: {user_count}")
            print(f"  完成对局数: {game_count}")
            print(f"  平均轮次: {avg_turns:.1f}")
        except sqlite3.OperationalError as e:
            print(f"\n⚠️  数据库表还未完全初始化: {e}")
            print("💡 提示：需要先启动游戏并完成至少一局游戏")
            conn.close()
            return
        
        if top_players:
            print(f"\n🏆 最活跃玩家 TOP 5：")
            print(f"  {'排名':<6} {'用户名':<20} {'对局数':<10} {'胜场':<10} {'总分':<10} {'胜率':<10}")
            print("  " + "-" * 80)
            for i, player in enumerate(top_players, 1):
                win_rate = f"{player['total_wins']/player['total_games']*100:.1f}%" if player['total_games'] > 0 else "N/A"
                print(f"  {i:<6} {player['username']:<20} {player['total_games']:<10} "
                      f"{player['total_wins']:<10} {player['total_points']:<10} {win_rate:<10}")


def show_menu():
    """显示菜单"""
    print("\n" + "="*100)
    print("🎮 璀璨宝石宝可梦 - 数据库查询工具")
    print("="*100)
    print("\n请选择操作：")
    print("  1. 查看所有用户")
    print("  2. 查看用户详情")
    print("  3. 查看最近对局")
    print("  4. 查看对局详情")
    print("  5. 查看统计信息")
    print("  0. 退出")
    print("\n" + "="*100)


def main():
    """主函数"""
    viewer = DatabaseViewer()
    
    while True:
        show_menu()
        choice = input("\n请输入选项 (0-5): ").strip()
        
        if choice == '0':
            print("\n👋 再见！")
            break
        
        elif choice == '1':
            viewer.show_all_users()
        
        elif choice == '2':
            username = input("请输入用户名: ").strip()
            if username:
                viewer.show_user_detail(username)
        
        elif choice == '3':
            limit = input("显示多少场对局? (默认20): ").strip()
            limit = int(limit) if limit.isdigit() else 20
            viewer.show_recent_games(limit)
        
        elif choice == '4':
            game_id = input("请输入对局ID: ").strip()
            if game_id:
                viewer.show_game_detail(game_id)
        
        elif choice == '5':
            viewer.show_statistics()
        
        else:
            print("❌ 无效选项，请重新选择")
        
        input("\n按回车键继续...")


if __name__ == "__main__":
    main()

