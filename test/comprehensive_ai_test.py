#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面AI对局测试
测试所有难度和人数组合，分析问题并统计
"""

import sys
import os
import time
import json
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from splendor_pokemon import *
from backend.ai_player import AIPlayer
from backend.game_history import GameHistory


def run_single_game(difficulty, num_players, test_id):
    """运行单局游戏"""
    
    # 生成玩家名称
    if num_players == 2:
        player_names = ["AI·赤红", "AI·青绿"]
    else:
        player_names = ["AI·小智", "AI·小茂", "AI·小霞", "AI·小刚"]
    
    game = SplendorPokemonGame(player_names, victory_points=18)
    
    # 创建AI玩家
    ai_players = {name: AIPlayer(difficulty) for name in player_names}
    
    # 初始化历史记录
    game_id = f"{difficulty}_{num_players}P_test{test_id}_{int(time.time())}"
    history = GameHistory(
        game_id=game_id,
        room_id=f"test_{difficulty}_{num_players}P",
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
    history.start_turn(1, player_names[0])
    
    # 游戏循环
    turn_count = 0
    max_turns = 300
    successful_actions = 0
    
    start_time = time.time()
    
    while not game.game_over and turn_count < max_turns:
        turn_count += 1
        current_player = game.get_current_player()
        
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
                pass
        
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
    
    elapsed_time = time.time() - start_time
    
    # 游戏结束
    winner = game.winner
    rankings = []
    for i, player in enumerate(game.players, 1):
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
    
    # 返回测试结果
    return {
        "difficulty": difficulty,
        "num_players": num_players,
        "test_id": test_id,
        "game_id": game_id,
        "success": turn_count < max_turns and winner is not None,
        "turn_count": turn_count,
        "winner": winner.name if winner else None,
        "final_scores": {p.name: p.victory_points for p in game.players},
        "successful_actions": successful_actions,
        "elapsed_time": elapsed_time,
        "history_file": filepath
    }


def main():
    """主测试流程"""
    
    print("=" * 80)
    print("🚀 全面AI对局测试")
    print("=" * 80)
    print("测试配置：3个难度 × 2种人数 × 10次 = 60局")
    print()
    
    difficulties = ["简单", "中等", "困难"]
    player_counts = [2, 4]
    tests_per_config = 10
    
    all_results = []
    stats = defaultdict(lambda: {"success": 0, "total": 0, "turns": [], "times": []})
    
    total_tests = len(difficulties) * len(player_counts) * tests_per_config
    current_test = 0
    
    for difficulty in difficulties:
        for num_players in player_counts:
            config_key = f"{difficulty}_{num_players}P"
            
            print(f"\n{'='*80}")
            print(f"📊 测试配置: {difficulty}AI × {num_players}人")
            print(f"{'='*80}")
            
            for test_id in range(1, tests_per_config + 1):
                current_test += 1
                print(f"\n[{current_test}/{total_tests}] {config_key} - 测试 {test_id}/10 ", end="", flush=True)
                
                try:
                    result = run_single_game(difficulty, num_players, test_id)
                    all_results.append(result)
                    
                    # 更新统计
                    stats[config_key]["total"] += 1
                    if result["success"]:
                        stats[config_key]["success"] += 1
                        stats[config_key]["turns"].append(result["turn_count"])
                        stats[config_key]["times"].append(result["elapsed_time"])
                        print(f"✅ {result['turn_count']}回合, {result['elapsed_time']:.1f}秒")
                    else:
                        print(f"❌ 超时({result['turn_count']}回合)")
                    
                except Exception as e:
                    print(f"❌ 异常: {str(e)[:50]}")
                    all_results.append({
                        "difficulty": difficulty,
                        "num_players": num_players,
                        "test_id": test_id,
                        "success": False,
                        "error": str(e)
                    })
                
                # 间隔避免文件冲突
                time.sleep(0.1)
    
    # 生成统计报告
    print(f"\n\n{'='*80}")
    print("📈 测试结果统计")
    print(f"{'='*80}\n")
    
    report = []
    report.append("# 全面AI对局测试报告\n")
    report.append(f"**测试时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append(f"**总测试数**: {total_tests}局\n\n")
    
    report.append("## 总体统计\n\n")
    report.append("| 配置 | 成功率 | 平均回合数 | 平均时间 |\n")
    report.append("|------|--------|------------|----------|\n")
    
    for config_key in sorted(stats.keys()):
        stat = stats[config_key]
        success_rate = (stat["success"] / stat["total"] * 100) if stat["total"] > 0 else 0
        avg_turns = sum(stat["turns"]) / len(stat["turns"]) if stat["turns"] else 0
        avg_time = sum(stat["times"]) / len(stat["times"]) if stat["times"] else 0
        
        status_emoji = "✅" if success_rate >= 80 else "⚠️" if success_rate >= 50 else "❌"
        
        print(f"{status_emoji} {config_key:15s}: {stat['success']:2d}/{stat['total']:2d} ({success_rate:5.1f}%) "
              f"平均 {avg_turns:5.1f}回合, {avg_time:4.1f}秒")
        
        report.append(f"| {config_key} | {success_rate:.1f}% ({stat['success']}/{stat['total']}) | "
                     f"{avg_turns:.1f} | {avg_time:.1f}s |\n")
    
    # 问题分析
    report.append("\n## 问题分析\n\n")
    
    failed_configs = []
    for config_key, stat in stats.items():
        success_rate = (stat["success"] / stat["total"] * 100) if stat["total"] > 0 else 0
        if success_rate < 80:
            failed_configs.append((config_key, success_rate, stat))
    
    if failed_configs:
        report.append("### ⚠️ 需要关注的配置\n\n")
        for config_key, success_rate, stat in sorted(failed_configs, key=lambda x: x[1]):
            report.append(f"- **{config_key}**: 成功率仅{success_rate:.1f}%\n")
            
            # 分析失败原因
            failed_results = [r for r in all_results 
                            if r.get("difficulty", "") + "_" + str(r.get("num_players", "")) + "P" == config_key 
                            and not r["success"]]
            
            if failed_results:
                report.append(f"  - 失败次数: {len(failed_results)}\n")
                report.append(f"  - 典型问题: 超时300回合\n")
        report.append("\n")
    else:
        report.append("✅ 所有配置成功率都在80%以上！\n\n")
    
    # 保存结果
    report_content = "".join(report)
    
    with open("test/AI_TEST_COMPREHENSIVE_REPORT.md", "w", encoding="utf-8") as f:
        f.write(report_content)
    
    with open("test/ai_test_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n\n{'='*80}")
    print("📁 报告已保存:")
    print("  - test/AI_TEST_COMPREHENSIVE_REPORT.md")
    print("  - test/ai_test_results.json")
    print(f"{'='*80}\n")
    
    # 返回是否所有测试都成功
    total_success = sum(stat["success"] for stat in stats.values())
    return total_success == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

