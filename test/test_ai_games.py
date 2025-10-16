#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI对局完整测试 - 生成历史记录
"""

import sys
import os
import time

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from splendor_pokemon import *
from backend.ai_player import AIPlayer
from backend.game_history import GameHistory

def run_ai_game(player_names, ai_difficulty="中等", victory_points=18, game_tag=""):
    """运行一局AI游戏并保存历史记录"""
    
    print("\n" + "=" * 80)
    print(f"🎮 开始游戏: {game_tag}")
    print("=" * 80)
    print(f"玩家数: {len(player_names)}")
    print(f"AI难度: {ai_difficulty}")
    print(f"胜利分数: {victory_points}")
    
    # 创建游戏
    game = SplendorPokemonGame(player_names, victory_points=victory_points)
    
    # 创建AI玩家
    ai_players = {}
    for name in player_names:
        ai_players[name] = AIPlayer(ai_difficulty)
    
    # 初始化历史记录
    game_id = f"{game_tag}_{int(time.time())}"
    history = GameHistory(
        game_id=game_id,
        room_id=f"{game_tag}_room",
        players=player_names.copy(),
        victory_points_goal=victory_points
    )
    
    # 记录初始状态
    initial_state = {
        "ball_pool": {bt.value: count for bt, count in game.ball_pool.items()},
        "tableau": {level: [{"name": c.name, "level": c.level} for c in cards] 
                   for level, cards in game.tableau.items()},
        "player_states": {p.name: {
            "balls": {bt.value: count for bt, count in p.balls.items()},
            "victory_points": p.victory_points
        } for p in game.players}
    }
    history.record_initial_state(initial_state)
    
    print(f"\n初始设置:")
    print(f"  球池: {sum(game.ball_pool.values())} 个球")
    print(f"  牌堆: Lv1={len(game.deck_lv1)}, Lv2={len(game.deck_lv2)}, Lv3={len(game.deck_lv3)}")
    print(f"  📝 游戏ID: {game_id}")
    
    # 开始第一回合
    history.start_turn(1, player_names[0])
    
    # 游戏循环
    turn_count = 0
    max_turns = 500  # 防止无限循环
    
    while not game.game_over and turn_count < max_turns:
        turn_count += 1
        current_player = game.get_current_player()
        
        # 定期打印进度
        if turn_count % 30 == 1 or turn_count <= 3:
            print(f"\n回合 {turn_count}: {current_player.name}")
            print(f"  分数: {' | '.join([f'{p.name}:{p.victory_points}VP' for p in game.players])}")
        
        # 记录动作前状态
        player_state_before = {
            "balls": {bt.value: count for bt, count in current_player.balls.items()},
            "victory_points": current_player.victory_points,
            "owned_cards_count": len(current_player.display_area),
            "reserved_cards_count": len(current_player.reserved_cards)
        }
        ball_pool_before = {bt.value: count for bt, count in game.ball_pool.items()}
        history.record_state_before_action(current_player.name, player_state_before, ball_pool_before)
        
        # AI决策
        ai = ai_players[current_player.name]
        action = ai.make_decision(game, current_player)
        
        # 执行动作并记录
        if action:
            try:
                if action["action"] == "buy_card":
                    card_name = action["data"]["card"]["name"]
                    found_card = None
                    
                    # 查找卡牌
                    for tier in [1, 2, 3]:
                        for card in game.tableau[tier]:
                            if card.name == card_name:
                                found_card = card
                                break
                        if found_card:
                            break
                    
                    if not found_card:
                        for card in current_player.reserved_cards:
                            if card.name == card_name:
                                found_card = card
                                break
                    
                    if not found_card:
                        if game.rare_card and game.rare_card.name == card_name:
                            found_card = game.rare_card
                        elif game.legendary_card and game.legendary_card.name == card_name:
                            found_card = game.legendary_card
                    
                    if found_card:
                        result = game.buy_card(found_card)
                        history.record_action("buy_card", {
                            "card_name": found_card.name,
                            "card_level": found_card.level,
                            "card_vp": found_card.victory_points
                        }, result, f"购买{found_card.name}" if result else "购买失败")
                    
                elif action["action"] == "reserve_card":
                    card_name = action["data"]["card"]["name"]
                    found_card = None
                    
                    for tier in [1, 2, 3]:
                        for card in game.tableau[tier]:
                            if card.name == card_name:
                                found_card = card
                                break
                        if found_card:
                            break
                    
                    if found_card:
                        result = game.reserve_card(found_card)
                        history.record_action("reserve_card", {
                            "card_name": found_card.name,
                            "card_level": found_card.level
                        }, result, f"预购{found_card.name}" if result else "预购失败")
                    
                elif action["action"] == "take_balls":
                    ball_types = action["data"]["ball_types"]
                    balls = [BallType(bt) for bt in ball_types]
                    result = game.take_balls(balls)
                    history.record_action("take_balls", {
                        "ball_types": ball_types
                    }, result, "拿取球" if result else "拿取球失败")
                    
            except Exception as e:
                if turn_count <= 5:
                    print(f"  ⚠️ 动作执行失败: {e}")
        
        # 处理球数限制
        if current_player.needs_return_balls:
            total_balls = current_player.get_total_balls()
            while total_balls > 10:
                max_ball_type = max(current_player.balls.items(), key=lambda x: x[1])[0]
                if current_player.balls[max_ball_type] > 0:
                    current_player.balls[max_ball_type] -= 1
                    game.ball_pool[max_ball_type] += 1
                    total_balls -= 1
            current_player.needs_return_balls = False
        
        # 记录动作后状态
        player_state_after = {
            "balls": {bt.value: count for bt, count in current_player.balls.items()},
            "victory_points": current_player.victory_points,
            "owned_cards_count": len(current_player.display_area),
            "reserved_cards_count": len(current_player.reserved_cards)
        }
        ball_pool_after = {bt.value: count for bt, count in game.ball_pool.items()}
        history.record_state_after_action(current_player.name, player_state_after, ball_pool_after)
        
        # 结束回合
        game.end_turn()
        
        # 开始新回合
        if not game.game_over and turn_count < max_turns:
            next_player = game.get_current_player()
            history.start_turn(turn_count + 1, next_player.name)
    
    # 游戏结束
    print(f"\n🏁 游戏结束！")
    print(f"总回合数: {turn_count}")
    
    winner = game.winner
    if winner:
        print(f"🏆 胜利者: {winner.name} ({winner.victory_points}分)")
    else:
        print("⚠️ 未达到胜利条件")
    
    # 打印最终排名
    print(f"\n📊 最终排名:")
    rankings = []
    for i, player in enumerate(game.players, 1):
        print(f"  {i}. {player.name}: {player.victory_points}分, "
              f"{len(player.display_area)}张卡, {player.get_total_balls()}个球")
        rankings.append({
            "rank": i,
            "player_name": player.name,
            "victory_points": player.victory_points,
            "cards_count": len(player.display_area),
            "balls_count": player.get_total_balls()
        })
    
    # 保存历史记录
    history.end_game(winner.name if winner else "未知", rankings)
    filepath = history.save_to_file()
    print(f"\n💾 游戏历史已保存: {filepath}")
    
    return filepath

# ============================================================================
# 主测试流程
# ============================================================================

if __name__ == "__main__":
    print("🚀 AI对局完整测试")
    print("=" * 80)
    
    saved_files = []
    
    # 测试1: 4个AI玩家 - 中等难度
    print("\n" + "🎲" * 40)
    print("测试场景1: 4个AI玩家 (中等难度)")
    print("🎲" * 40)
    filepath1 = run_ai_game(
        player_names=["机器人·小智", "机器人·小茂", "机器人·小霞", "机器人·小刚"],
        ai_difficulty="中等",
        victory_points=18,
        game_tag="4AI_medium"
    )
    saved_files.append(filepath1)
    
    # 等待一秒确保文件名不重复
    time.sleep(1)
    
    # 测试2: 2个AI玩家 - 困难难度
    print("\n" + "🎲" * 40)
    print("测试场景2: 2个AI玩家 (困难难度)")
    print("🎲" * 40)
    filepath2 = run_ai_game(
        player_names=["AI·赤红", "AI·青绿"],
        ai_difficulty="困难",
        victory_points=18,
        game_tag="2AI_hard"
    )
    saved_files.append(filepath2)
    
    # 等待一秒
    time.sleep(1)
    
    # 测试3: 4个AI玩家 - 简单难度（快速游戏）
    print("\n" + "🎲" * 40)
    print("测试场景3: 4个AI玩家 (简单难度)")
    print("🎲" * 40)
    filepath3 = run_ai_game(
        player_names=["新手·波波", "新手·小拉达", "新手·鲤鱼王", "新手·绿毛虫"],
        ai_difficulty="简单",
        victory_points=15,  # 降低胜利分数加快游戏
        game_tag="4AI_easy"
    )
    saved_files.append(filepath3)
    
    # 总结
    print("\n" + "=" * 80)
    print("✅ 所有测试完成！")
    print("=" * 80)
    print(f"\n📁 保存的历史记录文件:")
    for i, filepath in enumerate(saved_files, 1):
        file_size = os.path.getsize(filepath) / 1024  # KB
        print(f"  {i}. {filepath}")
        print(f"     大小: {file_size:.1f} KB")
    
    print(f"\n🎉 共生成 {len(saved_files)} 个游戏历史记录！")
    print(f"📂 位置: game_history/")

