#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速AI测试 - 每个配置3局
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from splendor_pokemon import *
from backend.ai_player import AIPlayer
from backend.game_history import GameHistory

def run_single_game(difficulty, num_players, test_id):
    """运行单局游戏"""
    if num_players == 2:
        player_names = ["AI·赤红", "AI·青绿"]
    else:
        player_names = ["AI·小智", "AI·小茂", "AI·小霞", "AI·小刚"]
    
    game = SplendorPokemonGame(player_names, victory_points=18)
    ai_players = {name: AIPlayer(difficulty) for name in player_names}
    
    turn_count = 0
    max_turns = 300
    
    while not game.game_over and turn_count < max_turns:
        turn_count += 1
        current_player = game.get_current_player()
        ai = ai_players[current_player.name]
        action = ai.make_decision(game, current_player)
        
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
                        game.buy_card(found_card)
                    
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
                        game.reserve_card(found_card)
                    
                elif action["action"] == "take_balls":
                    ball_types = action["data"]["ball_types"]
                    balls = [BallType(bt) for bt in ball_types]
                    game.take_balls(balls)
                    
            except Exception as e:
                pass
        
        if current_player.needs_return_balls:
            total_balls = current_player.get_total_balls()
            while total_balls > 10:
                max_ball_type = max(current_player.balls.items(), key=lambda x: x[1])[0]
                if current_player.balls[max_ball_type] > 0:
                    current_player.balls[max_ball_type] -= 1
                    game.ball_pool[max_ball_type] += 1
                    total_balls -= 1
            current_player.needs_return_balls = False
        
        game.end_turn()
    
    winner = game.winner
    success = turn_count < max_turns and winner is not None
    
    return {
        "difficulty": difficulty,
        "num_players": num_players,
        "success": success,
        "turn_count": turn_count,
        "winner": winner.name if winner else None
    }

def main():
    print("=" * 80)
    print("🚀 快速AI测试（每配置3局）")
    print("=" * 80)
    
    difficulties = ["简单", "中等", "困难"]
    player_counts = [2, 4]
    tests_per_config = 3
    
    results = {}
    
    for difficulty in difficulties:
        for num_players in player_counts:
            config_key = f"{difficulty}_{num_players}P"
            print(f"\n{'='*80}")
            print(f"📊 测试: {config_key}")
            print(f"{'='*80}")
            
            success_count = 0
            turns_list = []
            
            for test_id in range(1, tests_per_config + 1):
                print(f"[{test_id}/3] ", end="", flush=True)
                
                try:
                    result = run_single_game(difficulty, num_players, test_id)
                    if result["success"]:
                        success_count += 1
                        turns_list.append(result["turn_count"])
                        print(f"✅ {result['turn_count']}回合")
                    else:
                        print(f"❌ 超时({result['turn_count']}回合)")
                except Exception as e:
                    print(f"❌ 异常: {str(e)[:30]}")
                
                time.sleep(0.1)
            
            results[config_key] = {
                "success": success_count,
                "total": tests_per_config,
                "avg_turns": sum(turns_list) / len(turns_list) if turns_list else 0
            }
    
    print(f"\n\n{'='*80}")
    print("📈 测试结果汇总")
    print(f"{'='*80}\n")
    
    for config_key, stat in sorted(results.items()):
        success_rate = (stat["success"] / stat["total"] * 100) if stat["total"] > 0 else 0
        status_emoji = "✅" if success_rate >= 80 else "⚠️" if success_rate >= 50 else "❌"
        
        print(f"{status_emoji} {config_key:15s}: {stat['success']:2d}/{stat['total']:2d} ({success_rate:5.1f}%) "
              f"平均 {stat['avg_turns']:5.1f}回合")
    
    print()

if __name__ == "__main__":
    main()

