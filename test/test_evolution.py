#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试进化机制和新规则
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from splendor_pokemon import *

def test_basic_game():
    """测试基本游戏流程"""
    print("=" * 60)
    print("🧪 测试基本游戏流程")
    print("=" * 60)
    
    game = SplendorPokemonGame(["测试玩家1", "测试玩家2"])
    player1 = game.players[0]
    player2 = game.players[1]
    
    print(f"\n初始状态:")
    print(f"  胜利目标: {game.victory_points_goal}分")
    print(f"  球池: {[(b.value, c) for b, c in game.ball_pool.items()]}")
    print(f"  场面卡牌数: Lv1={len(game.tableau[1])}, Lv2={len(game.tableau[2])}, Lv3={len(game.tableau[3])}")
    print(f"  稀有卡: {game.rare_card.name if game.rare_card else '无'}")
    print(f"  传说卡: {game.legendary_card.name if game.legendary_card else '无'}")
    
    # 测试拿球
    print("\n🎲 测试拿球规则:")
    print(f"  玩家1尝试拿3种不同颜色的球...")
    result = game.take_balls([BallType.RED, BallType.BLUE, BallType.YELLOW])
    print(f"  {'✅ 成功' if result else '❌ 失败'}")
    print(f"  玩家1的球: {[(b.value, c) for b, c in player1.balls.items() if c > 0]}")
    
    # 测试预定卡牌（获得大师球）
    print("\n📖 测试预定卡牌:")
    if game.tableau[1]:
        card = game.tableau[1][0]
        print(f"  玩家1预定卡牌: {card.name}")
        result = game.reserve_card(card)
        print(f"  {'✅ 成功' if result else '❌ 失败'}")
        print(f"  手牌数: {len(player1.reserved_cards)}")
        print(f"  获得大师球: {player1.balls[BallType.MASTER]}")

def test_evolution():
    """测试进化机制"""
    print("\n" + "=" * 60)
    print("🔄 测试进化机制")
    print("=" * 60)
    
    # 创建测试场景
    game = SplendorPokemonGame(["训练家"])
    player = game.players[0]
    
    # 给玩家一些资源来测试
    player.balls[BallType.RED] = 5
    player.balls[BallType.BLUE] = 5
    player.balls[BallType.YELLOW] = 5
    
    print("\n设置测试场景:")
    print(f"  玩家球数: 红{player.balls[BallType.RED]} 蓝{player.balls[BallType.BLUE]} 黄{player.balls[BallType.YELLOW]}")
    
    # 找一张小火龙
    charmander = None
    for card in game.tableau[1]:
        if card.name == "小火龙":
            charmander = card
            break
    
    if not charmander:
        print("  ⚠️  场上没有小火龙，创建测试卡")
        charmander = PokemonCard("小火龙", 1, Rarity.NORMAL, 0,
                                {BallType.RED: 2}, {BallType.RED: 1},
                                Evolution("火恐龙", {BallType.YELLOW: 3}))
        game.tableau[1].append(charmander)
    
    print(f"\n1️⃣ 购买小火龙:")
    print(f"  卡牌: {charmander}")
    print(f"  进化目标: {charmander.evolution.target_name if charmander.evolution else '无'}")
    print(f"  进化门槛: {[(b.value, c) for b, c in charmander.evolution.required_balls.items()] if charmander.evolution else '无'}")
    
    result = game.buy_card(charmander)
    print(f"  {'✅ 购买成功' if result else '❌ 购买失败'}")
    if result:
        print(f"  展示区: {[c.name for c in player.display_area]}")
        print(f"  永久球: {[(b.value, c) for b, c in player.get_permanent_balls().items() if c > 0]}")
        print(f"  当前分数: {player.victory_points}")
    
    # 积累足够的黄色永久球来进化
    print(f"\n2️⃣ 积累黄色永久球（需要3个）:")
    for i in range(3):
        # 添加一些黄色永久球的卡牌
        yellow_card = PokemonCard(f"黄色测试卡{i+1}", 1, Rarity.NORMAL, 0,
                                 {BallType.YELLOW: 1}, {BallType.YELLOW: 1})
        player.display_area.append(yellow_card)
        print(f"  添加测试卡 -> 黄色永久球: {player.get_permanent_balls()[BallType.YELLOW]}")
    
    # 将火恐龙加入场面
    charmeleon = PokemonCard("火恐龙", 2, Rarity.NORMAL, 1,
                            {BallType.RED: 3, BallType.YELLOW: 1}, {BallType.RED: 1},
                            Evolution("喷火龙", {BallType.PINK: 2}))
    game.tableau[2].append(charmeleon)
    
    print(f"\n3️⃣ 检查进化条件:")
    permanent = player.get_permanent_balls()
    can_evolve = player.can_evolve(charmeleon, charmander)
    print(f"  永久球: 黄色={permanent[BallType.YELLOW]}")
    print(f"  需要: 黄色≥3")
    print(f"  {'✅ 可以进化' if can_evolve else '❌ 无法进化'}")
    
    if can_evolve:
        print(f"\n4️⃣ 执行进化:")
        print(f"  {charmander.name} (Lv1, {charmander.victory_points}分) → {charmeleon.name} (Lv2, {charmeleon.victory_points}分)")
        result = player.evolve(charmander, charmeleon)
        print(f"  {'✅ 进化成功' if result else '❌ 进化失败'}")
        if result:
            print(f"  展示区: {[c.name for c in player.display_area]}")
            print(f"  进化前卡牌已扣到训练家板下: {[c.name for c in player.evolved_cards]}")
            print(f"  当前分数: {player.victory_points}")

def test_ball_limit():
    """测试10球上限"""
    print("\n" + "=" * 60)
    print("⚖️  测试10球上限")
    print("=" * 60)
    
    game = SplendorPokemonGame(["测试玩家"])
    player = game.players[0]
    
    # 给玩家超过10个球
    player.balls[BallType.RED] = 4
    player.balls[BallType.BLUE] = 3
    player.balls[BallType.YELLOW] = 2
    player.balls[BallType.YELLOW] = 2
    player.balls[BallType.MASTER] = 1
    
    print(f"\n当前球数: {player.get_total_balls()}")
    print(f"  详细: {[(b.value, c) for b, c in player.balls.items() if c > 0]}")
    
    if player.get_total_balls() > 10:
        print(f"\n❗ 超过10球上限，需要弃球")
        def return_balls(ball_type, amount):
            game.ball_pool[ball_type] += amount
            print(f"  弃回 {ball_type.value} × {amount}")
        
        player.check_ball_limit(return_balls)
        print(f"\n处理后球数: {player.get_total_balls()}")
        print(f"  详细: {[(b.value, c) for b, c in player.balls.items() if c > 0]}")

def test_18_victory():
    """测试18分胜利"""
    print("\n" + "=" * 60)
    print("🏆 测试18分胜利条件")
    print("=" * 60)
    
    game = SplendorPokemonGame(["玩家1", "玩家2"])
    player1 = game.players[0]
    player2 = game.players[1]
    
    # 模拟玩家1达到18分
    player1.victory_points = 17
    print(f"  玩家1: {player1.victory_points}分")
    print(f"  玩家2: {player2.victory_points}分")
    
    # 玩家1获得1分卡牌
    high_card = PokemonCard("测试高分卡", 3, Rarity.NORMAL, 1,
                           {BallType.RED: 1}, {BallType.RED: 1})
    player1.display_area.append(high_card)
    player1.victory_points += 1
    
    print(f"\n  玩家1获得1分，达到 {player1.victory_points}分！")
    print(f"  触发最终回合...")
    
    game.end_turn()
    
    print(f"  {'✅ 最终回合已触发' if game.final_round_triggered else '❌ 未触发'}")
    print(f"  {'✅ 游戏结束' if game.game_over else '⏳ 等待补完本轮'}")

if __name__ == "__main__":
    test_basic_game()
    test_evolution()
    test_ball_limit()
    test_18_victory()
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")
    print("=" * 60)
    print("\n💡 提示: 等待完整卡牌CSV数据后，可以导入真实的90张卡牌")

