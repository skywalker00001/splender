#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
历史记录功能单元测试
"""

import sys
import os
import json
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.game_history import GameHistory
from splendor_pokemon import *

print("=" * 80)
print("🧪 历史记录功能单元测试")
print("=" * 80)

# 测试1: 创建和保存历史记录
print("\n测试1: 创建GameHistory对象")
try:
    history = GameHistory(
        game_id="test_unit_001",
        room_id="test_room",
        players=["玩家1", "玩家2", "玩家3", "玩家4"],
        victory_points_goal=18
    )
    print("✅ GameHistory对象创建成功")
    print(f"   游戏ID: {history.game_id}")
    print(f"   玩家数: {len(history.players)}")
except Exception as e:
    print(f"❌ 创建失败: {e}")
    sys.exit(1)

# 测试2: 记录初始状态
print("\n测试2: 记录初始状态")
try:
    initial_state = {
        "ball_pool": {"红": 7, "蓝": 7, "黄": 7, "粉": 7, "黑": 7, "大师球": 5},
        "tableau": {},
        "player_states": {}
    }
    history.record_initial_state(initial_state)
    print("✅ 初始状态记录成功")
    print(f"   球池总数: {sum(initial_state['ball_pool'].values())}")
except Exception as e:
    print(f"❌ 记录失败: {e}")
    sys.exit(1)

# 测试3: 记录回合
print("\n测试3: 记录回合和动作")
try:
    # 开始第一回合
    history.start_turn(1, "玩家1")
    
    # 记录动作前状态
    player_state = {
        "balls": {"红": 0, "蓝": 0, "黄": 0},
        "victory_points": 0,
        "owned_cards_count": 0,
        "reserved_cards_count": 0
    }
    ball_pool = {"红": 7, "蓝": 7, "黄": 7}
    history.record_state_before_action("玩家1", player_state, ball_pool)
    
    # 记录动作
    history.record_action("take_balls", {
        "ball_types": ["红", "蓝", "黄"]
    }, True, "拿取球")
    
    # 记录动作后状态
    player_state_after = {
        "balls": {"红": 1, "蓝": 1, "黄": 1},
        "victory_points": 0,
        "owned_cards_count": 0,
        "reserved_cards_count": 0
    }
    ball_pool_after = {"红": 6, "蓝": 6, "黄": 6}
    history.record_state_after_action("玩家1", player_state_after, ball_pool_after)
    
    print("✅ 回合记录成功")
    print(f"   总回合数: {len(history.turns)}")
    print(f"   第1回合动作数: {len(history.turns[0]['actions'])}")
except Exception as e:
    print(f"❌ 记录失败: {e}")
    sys.exit(1)

# 测试4: 记录更多回合
print("\n测试4: 记录多个回合")
try:
    for turn in range(2, 6):  # 记录5回合
        player_name = f"玩家{(turn-1) % 4 + 1}"
        history.start_turn(turn, player_name)
        
        # 简单记录
        history.record_state_before_action(player_name, player_state, ball_pool)
        history.record_action("take_balls", {"ball_types": ["红", "蓝"]}, True, "拿球")
        history.record_state_after_action(player_name, player_state_after, ball_pool_after)
    
    print("✅ 多回合记录成功")
    print(f"   总回合数: {len(history.turns)}")
except Exception as e:
    print(f"❌ 记录失败: {e}")
    sys.exit(1)

# 测试5: 结束游戏
print("\n测试5: 结束游戏")
try:
    rankings = [
        {"rank": 1, "player_name": "玩家1", "victory_points": 20, "cards_count": 10, "balls_count": 5},
        {"rank": 2, "player_name": "玩家2", "victory_points": 18, "cards_count": 9, "balls_count": 6},
        {"rank": 3, "player_name": "玩家3", "victory_points": 15, "cards_count": 8, "balls_count": 7},
        {"rank": 4, "player_name": "玩家4", "victory_points": 12, "cards_count": 7, "balls_count": 4}
    ]
    history.end_game("玩家1", rankings)
    print("✅ 游戏结束记录成功")
    print(f"   胜者: {history.winner}")
    print(f"   结束时间: {history.end_time}")
except Exception as e:
    print(f"❌ 记录失败: {e}")
    sys.exit(1)

# 测试6: 保存到文件
print("\n测试6: 保存到文件")
try:
    filepath = history.save_to_file()
    print("✅ 文件保存成功")
    print(f"   文件路径: {filepath}")
    
    # 验证文件存在
    if os.path.exists(filepath):
        file_size = os.path.getsize(filepath)
        print(f"   文件大小: {file_size} 字节")
    else:
        print("❌ 文件不存在")
        sys.exit(1)
except Exception as e:
    print(f"❌ 保存失败: {e}")
    sys.exit(1)

# 测试7: 加载历史记录
print("\n测试7: 从文件加载历史记录")
try:
    loaded_history = GameHistory.load_from_file(filepath)
    print("✅ 历史记录加载成功")
    print(f"   游戏ID: {loaded_history.game_id}")
    print(f"   玩家数: {len(loaded_history.players)}")
    print(f"   总回合数: {len(loaded_history.turns)}")
    print(f"   胜者: {loaded_history.winner}")
    
    # 验证数据完整性
    assert loaded_history.game_id == history.game_id
    assert loaded_history.winner == history.winner
    assert len(loaded_history.turns) == len(history.turns)
    print("✅ 数据完整性验证通过")
except Exception as e:
    print(f"❌ 加载失败: {e}")
    sys.exit(1)

# 测试8: 列出所有历史记录
print("\n测试8: 列出所有历史记录")
try:
    histories = GameHistory.list_all_histories()
    print("✅ 历史记录列表获取成功")
    print(f"   总记录数: {len(histories)}")
    
    if len(histories) > 0:
        print("\n   最近的3条记录:")
        for i, h in enumerate(histories[:3], 1):
            print(f"   {i}. 游戏ID: {h['game_id']}")
            print(f"      玩家: {', '.join(h['players'])}")
            print(f"      胜者: {h['winner']}")
            print(f"      回合数: {h['total_turns']}")
except Exception as e:
    print(f"❌ 列表获取失败: {e}")
    sys.exit(1)

# 测试9: 验证JSON格式
print("\n测试9: 验证JSON格式正确性")
try:
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    required_fields = ['game_id', 'room_id', 'players', 'victory_points_goal', 
                      'start_time', 'end_time', 'winner', 'total_turns', 
                      'initial_state', 'turns', 'final_rankings']
    
    for field in required_fields:
        if field not in data:
            print(f"❌ 缺少字段: {field}")
            sys.exit(1)
    
    print("✅ JSON格式验证通过")
    print(f"   包含所有必需字段: {len(required_fields)} 个")
except Exception as e:
    print(f"❌ JSON验证失败: {e}")
    sys.exit(1)

# 测试10: to_dict() 方法
print("\n测试10: 测试to_dict()方法")
try:
    dict_data = history.to_dict()
    print("✅ to_dict()方法执行成功")
    print(f"   返回类型: {type(dict_data)}")
    print(f"   键数量: {len(dict_data)}")
    
    # 验证可以序列化为JSON
    json_str = json.dumps(dict_data, ensure_ascii=False, indent=2)
    print(f"   JSON字符串长度: {len(json_str)} 字符")
except Exception as e:
    print(f"❌ to_dict()失败: {e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("✅ 所有单元测试通过！")
print("=" * 80)
print(f"\n📁 测试文件位置: {filepath}")
print("🎉 历史记录功能运行正常！")

