#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试困难AI死锁修复效果
"""

import sys
import os
import time

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from splendor_pokemon import *
from backend.ai_player import AIPlayer
from backend.game_history import GameHistory

def test_hard_ai_2players():
    """测试2人困难AI是否能正常完成游戏"""
    
    print("=" * 80)
    print("🧪 测试2人困难AI死锁修复")
    print("=" * 80)
    
    player_names = ["AI·赤红", "AI·青绿"]
    game = SplendorPokemonGame(player_names, victory_points=18)
    
    # 创建困难AI
    ai_players = {
        "AI·赤红": AIPlayer("困难"),
        "AI·青绿": AIPlayer("困难")
    }
    
    # 初始化历史记录
    game_id = f"deadlock_fix_test_{int(time.time())}"
    history = GameHistory(
        game_id=game_id,
        room_id="test_room",
        players=player_names.copy(),
        victory_points_goal=18
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
    print(f"  玩家: {', '.join(player_names)}")
    print(f"  球池: {sum(game.ball_pool.values())} 个球")
    print(f"  牌堆: Lv1={len(game.deck_lv1)}, Lv2={len(game.deck_lv2)}, Lv3={len(game.deck_lv3)}")
    print(f"  📝 游戏ID: {game_id}")
    
    history.start_turn(1, player_names[0])
    
    # 游戏循环
    turn_count = 0
    max_turns = 300  # 降低上限，期望能在300回合内完成
    deadlock_detections = 0
    successful_actions = 0
    
    while not game.game_over and turn_count < max_turns:
        turn_count += 1
        current_player = game.get_current_player()
        
        # 定期打印进度
        if turn_count % 20 == 1:
            print(f"\n回合 {turn_count}: {current_player.name}")
            print(f"  分数: {' | '.join([f'{p.name}:{p.victory_points}VP' for p in game.players])}")
            print(f"  球池彩色球: {sum(v for k, v in game.ball_pool.items() if k != BallType.MASTER)}")
        
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
        
        # 执行动作
        action_success = False
        if action:
            try:
                if action["action"] == "buy_card":
                    card_name = action["data"]["card"]["name"]
                    found_card = None
                    
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
                        if result:
                            action_success = True
                            successful_actions += 1
                    
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
                        if result:
                            action_success = True
                            successful_actions += 1
                    
                elif action["action"] == "take_balls":
                    ball_types = action["data"]["ball_types"]
                    balls = [BallType(bt) for bt in ball_types]
                    result = game.take_balls(balls)
                    history.record_action("take_balls", {
                        "ball_types": ball_types
                    }, result, "拿取球" if result else "拿取球失败")
                    if result:
                        action_success = True
                        successful_actions += 1
                    
            except Exception as e:
                if turn_count <= 10:
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
    print(f"\n" + "=" * 80)
    print(f"🏁 游戏结束！")
    print(f"=" * 80)
    print(f"总回合数: {turn_count}")
    print(f"成功动作数: {successful_actions}")
    
    winner = game.winner
    if winner:
        print(f"🏆 胜利者: {winner.name} ({winner.victory_points}分)")
    else:
        print("⚠️ 未达到胜利条件（可能超时）")
    
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
    
    # 评估修复效果
    print(f"\n" + "=" * 80)
    print(f"📈 修复效果评估")
    print(f"=" * 80)
    
    if turn_count < max_turns and winner:
        print(f"✅ 测试通过！")
        print(f"  - 游戏在{turn_count}回合内完成")
        print(f"  - 有明确的胜者: {winner.name}")
        print(f"  - 成功动作数: {successful_actions}")
        return True
    else:
        print(f"❌ 测试失败！")
        print(f"  - 达到回合上限: {turn_count}/{max_turns}")
        print(f"  - 可能仍存在死锁问题")
        return False

if __name__ == "__main__":
    success = test_hard_ai_2players()
    sys.exit(0 if success else 1)

