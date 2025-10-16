#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
璀璨宝石宝可梦 - 游戏测试套件
测试核心游戏机制和边缘案例
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from splendor_pokemon import *

def print_header(title):
    """打印测试标题"""
    print("\n" + "=" * 80)
    print(f"🧪 {title}")
    print("=" * 80)

def print_result(condition, message):
    """打印测试结果"""
    if condition:
        print(f"  ✅ {message}")
    else:
        print(f"  ❌ {message}")
    return condition

# ============================================================================
# 测试1: 基本游戏初始化
# ============================================================================

def test_game_initialization():
    """测试游戏初始化"""
    print_header("测试1: 游戏初始化")
    
    game = SplendorPokemonGame(["P1", "P2", "P3", "P4"], victory_points=18)
    
    print_result(len(game.players) == 4, f"4个玩家创建成功")
    print_result(game.victory_points_goal == 18, f"胜利分数=18")
    print_result(sum(game.ball_pool.values()) == 40, f"球池40个球")
    print_result(len(game.tableau[1]) <= 4, f"场面Lv1卡≤4张")
    print_result(len(game.tableau[2]) <= 4, f"场面Lv2卡≤4张")
    print_result(len(game.tableau[3]) <= 4, f"场面Lv3卡≤4张")
    print_result(game.rare_card is not None, f"有稀有卡")
    print_result(game.legendary_card is not None, f"有传说卡")
    print_result(not game.game_over, f"游戏未结束")

# ============================================================================
# 测试2: 拿球规则
# ============================================================================

def test_take_balls():
    """测试拿球规则"""
    print_header("测试2: 拿球规则")
    
    game = SplendorPokemonGame(["玩家1"])
    player = game.players[0]
    
    # 测试拿3个不同颜色
    print("\n场景1: 拿3个不同颜色")
    result = game.take_balls([BallType.RED, BallType.BLUE, BallType.YELLOW])
    print_result(result, "拿3个不同色成功")
    print_result(player.balls[BallType.RED] == 1, f"红球=1")
    print_result(player.balls[BallType.BLUE] == 1, f"蓝球=1")
    print_result(player.balls[BallType.YELLOW] == 1, f"黄球=1")
    
    game.end_turn()
    
    # 测试拿2个同色
    print("\n场景2: 拿2个同色（需要≥4个）")
    red_in_pool = game.ball_pool[BallType.RED]
    print(f"  池中红球数: {red_in_pool}")
    
    if red_in_pool >= 4:
        result = game.take_balls([BallType.RED, BallType.RED])
        print_result(result, "池≥4，拿2个同色成功")
    else:
        result = game.take_balls([BallType.RED, BallType.RED])
        print_result(not result, "池<4，拿2个同色失败（正确）")

# ============================================================================
# 测试3: 买卡和积分
# ============================================================================

def test_buy_card():
    """测试买卡功能"""
    print_header("测试3: 买卡和积分")
    
    game = SplendorPokemonGame(["玩家1"])
    player = game.players[0]
    
    # 给玩家足够的资源
    for ball_type in BallType:
        player.balls[ball_type] = 5
    
    # 买一张Lv1卡
    if game.tableau[1]:
        card = game.tableau[1][0]
        initial_vp = player.victory_points
        
        print(f"\n购买卡牌: {card.name} (Lv{card.level}, {card.victory_points}VP)")
        result = game.buy_card(card)
        
        print_result(result, "购买成功")
        print_result(card in player.display_area, "卡牌在展示区")
        print_result(player.victory_points == initial_vp + card.victory_points, 
                    f"分数增加{card.victory_points}")

# ============================================================================
# 测试4: 预购功能
# ============================================================================

def test_reserve_card():
    """测试预购功能"""
    print_header("测试4: 预购功能")
    
    game = SplendorPokemonGame(["玩家1"])
    player = game.players[0]
    
    # 预购3张卡
    print("\n预购3张卡:")
    for i in range(3):
        if game.tableau[1]:
            card = game.tableau[1][0]
            result = game.reserve_card(card)
            print_result(result, f"第{i+1}张预购成功: {card.name}")
    
    print_result(len(player.reserved_cards) == 3, f"预购区有3张")
    print_result(player.balls[BallType.MASTER] == 3, f"获得3个大师球")
    
    # 尝试预购第4张
    print("\n尝试预购第4张:")
    if game.tableau[1]:
        result = game.reserve_card(game.tableau[1][0])
        print_result(not result, "预购区满，无法预购（正确）")

# ============================================================================
# 测试5: 球数上限
# ============================================================================

def test_ball_limit():
    """测试10球上限"""
    print_header("测试5: 球数上限")
    
    game = SplendorPokemonGame(["玩家1"])
    player = game.players[0]
    
    # 给玩家9个球
    player.balls[BallType.RED] = 3
    player.balls[BallType.BLUE] = 3
    player.balls[BallType.YELLOW] = 3
    
    initial_total = player.get_total_balls()
    print(f"\n初始球数: {initial_total}")
    
    # 拿3个球
    game.take_balls([BallType.YELLOW, BallType.PINK, BallType.BLACK])
    
    after_take = player.get_total_balls()
    print(f"拿球后: {after_take}")
    print_result(after_take == 12, "拿球后=12个")
    print_result(player.needs_return_balls, "触发需要放回球标志")
    
    # 放回2个球
    balls_to_return = {BallType.RED: 2}
    game.return_balls(balls_to_return)
    
    final_total = player.get_total_balls()
    print(f"放回后: {final_total}")
    print_result(final_total == 10, "放回后=10个")
    print_result(not player.needs_return_balls, "放回球标志清除")

# ============================================================================
# 测试6: 最后一轮机制
# ============================================================================

def test_final_round():
    """测试最后一轮触发机制"""
    print_header("测试6: 最后一轮机制")
    
    # 场景1: 玩家1触发
    print("\n场景1: 玩家1达到18分")
    game1 = SplendorPokemonGame(["P1", "P2", "P3", "P4"], victory_points=18)
    game1.players[0].victory_points = 18
    game1.current_player_index = 0
    game1.end_turn()
    
    print_result(game1.final_round_triggered, "最后一轮标志")
    print_result(not game1.game_over, "游戏继续(等P2/3/4)")
    
    # 场景2: 玩家4触发
    print("\n场景2: 玩家4达到18分")
    game2 = SplendorPokemonGame(["P1", "P2", "P3", "P4"], victory_points=18)
    game2.players[3].victory_points = 18
    game2.current_player_index = 3
    game2.end_turn()
    
    print_result(game2.game_over, "游戏直接结束")
    print_result(game2.winner.name == "P4", "玩家4获胜")

# ============================================================================
# 测试7: 同分排名
# ============================================================================

def test_tie_breaking():
    """测试同分排名规则"""
    print_header("测试7: 同分排名（后手优先）")
    
    game = SplendorPokemonGame(["P1", "P2", "P3", "P4"], victory_points=18)
    
    # 所有玩家20分
    for player in game.players:
        player.victory_points = 20
    
    # 触发游戏结束
    game.current_player_index = 3
    game.end_turn()
    
    print(f"\n同分情况: 所有玩家20分")
    print_result(game.game_over, "游戏结束")
    print_result(game.winner.name == "P4", "玩家4获胜（后手优先）")

# ============================================================================
# 测试8: 进化功能
# ============================================================================

def test_evolution():
    """测试进化功能"""
    print_header("测试8: 进化功能")
    
    game = SplendorPokemonGame(["训练家"])
    player = game.players[0]
    
    # 创建测试卡牌
    charmander = PokemonCard(
        "小火龙", 1, Rarity.NORMAL, 0,
        {BallType.RED: 1},
        {BallType.RED: 1},
        Evolution("火恐龙", {BallType.RED: 2})
    )
    
    charmeleon = PokemonCard(
        "火恐龙", 2, Rarity.NORMAL, 1,
        {BallType.RED: 3},
        {BallType.RED: 1}
    )
    
    # 给玩家资源
    player.balls[BallType.RED] = 10
    
    # 购买小火龙
    game.tableau[1].append(charmander)
    game.buy_card(charmander)
    print_result(charmander in player.display_area, "购买小火龙")
    
    # 购买额外红色永久球卡
    red_card = PokemonCard("红卡", 1, Rarity.NORMAL, 0,
                          {BallType.RED: 1}, {BallType.RED: 1})
    game.tableau[1].append(red_card)
    game.buy_card(red_card)
    
    permanent_red = player.get_permanent_balls()[BallType.RED]
    print_result(permanent_red >= 2, f"红色永久球≥2 (实际{permanent_red})")
    
    # 进化
    game.tableau[2].append(charmeleon)
    can_evolve = player.can_evolve(charmeleon, charmander)
    print_result(can_evolve, "满足进化条件")
    
    if can_evolve:
        initial_vp = player.victory_points
        result = player.evolve(charmander, charmeleon)
        print_result(result, "进化成功")
        print_result(charmeleon in player.display_area, "火恐龙在展示区")
        print_result(charmander not in player.display_area, "小火龙已移除")
        print_result(player.victory_points == initial_vp + 1, "分数+1")

# ============================================================================
# 测试9: 稀有/传说卡不可预购
# ============================================================================

def test_rare_legendary():
    """测试稀有/传说卡不可预购"""
    print_header("测试9: 稀有/传说卡不可预购")
    
    game = SplendorPokemonGame(["玩家1"])
    
    if game.rare_card:
        print(f"\n尝试预购稀有卡: {game.rare_card.name}")
        result = game.reserve_card(game.rare_card)
        print_result(not result, "稀有卡不可预购（正确）")
    
    if game.legendary_card:
        print(f"\n尝试预购传说卡: {game.legendary_card.name}")
        result = game.reserve_card(game.legendary_card)
        print_result(not result, "传说卡不可预购（正确）")

# ============================================================================
# 测试10: 完整游戏流程模拟
# ============================================================================

def test_complete_game():
    """测试完整游戏流程"""
    print_header("测试10: 完整游戏模拟")
    
    game = SplendorPokemonGame(["P1", "P2"], victory_points=15)  # 降低胜利分数加快测试
    
    turn_count = 0
    max_turns = 1000
    
    print(f"\n开始游戏模拟...")
    
    while not game.game_over and turn_count < max_turns:
        turn_count += 1
        player = game.get_current_player()
        
        # 简单策略：买得起就买，买不起就拿球
        action_done = False
        
        # 尝试买卡
        for tier in [1, 2, 3]:
            for card in game.tableau[tier][:]:
                if player.can_afford(card):
                    try:
                        game.buy_card(card)
                        action_done = True
                        break
                    except:
                        pass
            if action_done:
                break
        
        # 拿球
        if not action_done:
            available = [bt for bt in [BallType.RED, BallType.BLUE, BallType.YELLOW]
                        if game.ball_pool[bt] > 0]
            if len(available) >= 3:
                try:
                    game.take_balls(available[:3])
                except:
                    pass
        
        # 处理超球
        if player.needs_return_balls:
            while player.get_total_balls() > 10:
                max_type = max(player.balls.items(), key=lambda x: x[1])[0]
                if player.balls[max_type] > 0:
                    player.balls[max_type] -= 1
                    game.ball_pool[max_type] += 1
            player.needs_return_balls = False
        
        game.end_turn()
    
    print(f"\n游戏在{turn_count}回合后结束")
    print_result(game.game_over, "游戏结束")
    print_result(turn_count < max_turns, f"在{max_turns}回合内完成")
    
    if game.winner:
        print(f"\n🏆 胜利者: {game.winner.name}, {game.winner.victory_points}分")
        print_result(game.winner.victory_points >= game.victory_points_goal, "分数达标")

# ============================================================================
# 主测试执行
# ============================================================================

def run_all_tests():
    """运行所有测试"""
    print("🚀 璀璨宝石宝可梦 - 游戏测试套件")
    print("=" * 80)
    
    try:
        test_game_initialization()
        test_take_balls()
        test_buy_card()
        test_reserve_card()
        test_ball_limit()
        test_final_round()
        test_tie_breaking()
        test_evolution()
        test_rare_legendary()
        test_complete_game()
        
        print("\n" + "=" * 80)
        print("🎉 所有测试完成！")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_all_tests()

