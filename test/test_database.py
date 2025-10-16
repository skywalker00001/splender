#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试数据库功能 - 带超时保护
"""
import sys
import os
import signal
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import GameDatabase
from datetime import datetime

# 超时处理
class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("测试超时！")

def test_database():
    """测试数据库基本功能"""
    print("="*70)
    print("玩家数据库系统测试")
    print("="*70)
    
    # 创建测试数据库（使用临时文件）
    test_db_path = os.path.join(os.path.dirname(__file__), 'test_game.db')
    db = GameDatabase(test_db_path)
    
    # 清除所有数据（确保测试环境干净）
    print("\n[准备] 清除测试数据...")
    db.clear_all_data()
    
    # 测试1: 创建用户
    print("\n[测试1] 创建/获取用户")
    user1 = db.get_or_create_user("小智")
    print(f"  ✓ 创建用户: {user1['username']}")
    print(f"    - ID: {user1['id']}")
    print(f"    - 创建时间: {user1['created_at']}")
    print(f"    - 总局数: {user1['total_games']}")
    
    user2 = db.get_or_create_user("小茂")
    print(f"  ✓ 创建用户: {user2['username']}")
    
    # 再次获取应该返回相同用户
    user1_again = db.get_or_create_user("小智")
    assert user1_again['id'] == user1['id']
    print(f"  ✓ 再次获取用户，ID相同")
    
    # 测试2: 记录游戏参与
    print("\n[测试2] 记录游戏参与")
    game_id = "test_game_001"
    game_history_file = "game_history/test_game_001.json"
    game_start_time = datetime.now().isoformat()
    game_end_time = datetime.now().isoformat()
    
    # 记录小智的游戏（胜利，第1名）
    db.record_game_participation(
        username="小智",
        game_id=game_id,
        game_history_file=game_history_file,
        player_name="小智",
        final_rank=1,
        final_score=20,
        is_winner=True,
        game_start_time=game_start_time,
        game_end_time=game_end_time,
        total_turns=50
    )
    print(f"  ✓ 记录小智的游戏: 第1名，20分，胜利")
    
    # 记录小茂的游戏（失败，第2名）
    db.record_game_participation(
        username="小茂",
        game_id=game_id,
        game_history_file=game_history_file,
        player_name="小茂",
        final_rank=2,
        final_score=15,
        is_winner=False,
        game_start_time=game_start_time,
        game_end_time=game_end_time,
        total_turns=50
    )
    print(f"  ✓ 记录小茂的游戏: 第2名，15分，失败")
    
    # 测试3: 获取用户游戏历史
    print("\n[测试3] 获取用户游戏历史")
    history = db.get_user_game_history("小智")
    print(f"  ✓ 小智的游戏历史: {len(history)} 局")
    if history:
        game = history[0]
        print(f"    - 游戏ID: {game['game_id']}")
        print(f"    - 最终排名: 第{game['final_rank']}名")
        print(f"    - 最终分数: {game['final_score']}分")
        print(f"    - 是否胜利: {'是' if game['is_winner'] else '否'}")
    
    # 测试4: 获取用户统计信息
    print("\n[测试4] 获取用户统计信息")
    stats = db.get_user_statistics("小智")
    if stats:
        print(f"  ✓ 小智的统计:")
        print(f"    - 总局数: {stats['total_games']}")
        print(f"    - 胜利次数: {stats['total_wins']}")
        print(f"    - 胜率: {stats['win_rate']*100:.1f}%")
        print(f"    - 总分数: {stats['total_points']}")
        print(f"    - 平均分: {stats['avg_score']:.1f}")
        if 'highest_score' in stats:
            print(f"    - 最高分: {stats['highest_score']}")
        print(f"    - 排名分布: {stats['rank_distribution']}")
    
    # 测试5: 获取游戏详情
    print("\n[测试5] 获取游戏详情")
    game_details = db.get_game_details(game_id)
    if game_details:
        print(f"  ✓ 游戏 {game_details['game_id']} 的详情:")
        print(f"    - 总回合数: {game_details['total_turns']}")
        print(f"    - 参与玩家:")
        for player in game_details['players']:
            print(f"      • {player['player_name']}: 第{player['final_rank']}名, {player['final_score']}分")
    
    # 测试6: 多局游戏记录
    print("\n[测试6] 记录多局游戏")
    for i in range(3):
        game_id_i = f"test_game_00{i+2}"
        db.record_game_participation(
            username="小智",
            game_id=game_id_i,
            game_history_file=f"game_history/{game_id_i}.json",
            player_name="小智",
            final_rank=(i % 3) + 1,
            final_score=18 + i * 2,
            is_winner=(i == 0),
            game_start_time=game_start_time,
            game_end_time=game_end_time,
            total_turns=40 + i * 5
        )
    print(f"  ✓ 记录了3局额外游戏")
    
    # 再次获取统计
    stats = db.get_user_statistics("小智")
    print(f"  ✓ 更新后的统计:")
    print(f"    - 总局数: {stats['total_games']}")
    print(f"    - 胜利次数: {stats['total_wins']}")
    print(f"    - 胜率: {stats['win_rate']*100:.1f}%")
    print(f"    - 排名分布: {stats['rank_distribution']}")
    
    # 测试7: 获取用户信息
    print("\n[测试7] 获取用户信息")
    user_info = db.get_user_by_username("小智")
    if user_info:
        print(f"  ✓ 用户信息:")
        print(f"    - 用户名: {user_info['username']}")
        print(f"    - 总局数: {user_info['total_games']}")
        print(f"    - 总胜场: {user_info['total_wins']}")
        print(f"    - 总分数: {user_info['total_points']}")
    
    print("\n" + "="*70)
    print("✅ 所有数据库测试通过！")
    print("="*70)
    
    # 清理测试数据库文件
    print(f"\n[清理] 删除测试数据库文件: {test_db_path}")
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    print("  ✓ 清理完成")

if __name__ == '__main__':
    # 设置30秒超时
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(30)
    
    try:
        test_database()
        signal.alarm(0)  # 取消超时
    except TimeoutError as e:
        print(f"\n❌ {e}")
        print("测试超过30秒，已终止")
        sys.exit(1)
    except Exception as e:
        signal.alarm(0)
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

