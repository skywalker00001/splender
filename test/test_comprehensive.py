#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
璀璨宝石宝可梦 - 全面测试套件
包含完整游戏流程测试和各种边缘案例测试
"""

import sys
import os
import random

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from splendor_pokemon import *
from backend.ai_player import AIPlayer
from backend.game_history import GameHistory

class TestLogger:
    """测试日志记录器"""
    def __init__(self):
        self.test_count = 0
        self.passed_count = 0
        self.failed_count = 0
        
    def start_test(self, name):
        """开始一个测试"""
        self.test_count += 1
        print("\n" + "=" * 80)
        print(f"🧪 测试 #{self.test_count}: {name}")
        print("=" * 80)
        
    def assert_true(self, condition, message):
        """断言为真"""
        if condition:
            print(f"  ✅ {message}")
            self.passed_count += 1
        else:
            print(f"  ❌ {message}")
            self.failed_count += 1
            
    def assert_equal(self, actual, expected, message):
        """断言相等"""
        if actual == expected:
            print(f"  ✅ {message}: {actual}")
            self.passed_count += 1
        else:
            print(f"  ❌ {message}: 期望{expected}, 实际{actual}")
            self.failed_count += 1
            
    def print_summary(self):
        """打印测试摘要"""
        print("\n" + "=" * 80)
        print("📊 测试总结")
        print("=" * 80)
        print(f"  总测试数: {self.test_count}")
        print(f"  通过断言: {self.passed_count}")
        print(f"  失败断言: {self.failed_count}")
        if self.failed_count == 0:
            print(f"  🎉 所有测试通过！")
        else:
            print(f"  ⚠️  有 {self.failed_count} 个断言失败")
        print("=" * 80)

logger = TestLogger()

# ============================================================================
# 测试1: 完整游戏流程 - 4个AI玩家从开始到结束
# ============================================================================

def test_complete_game_with_ai():
    """测试完整游戏流程：模拟游戏进行到胜利 - 使用中等AI"""
    logger.start_test("完整游戏流程 - 中等AI对局")
    
    # 创建游戏
    player_names = ["玩家1", "玩家2", "玩家3", "玩家4"]
    game = SplendorPokemonGame(player_names, victory_points=18)
    
    # 创建中等AI
    ai_players = {}
    for name in player_names:
        ai_players[name] = AIPlayer("中等")
    
    logger.assert_equal(len(game.players), 4, "玩家数量")
    logger.assert_equal(game.victory_points_goal, 18, "胜利分数")
    
    # 初始化历史记录
    import time
    game_id = f"test_{int(time.time())}"
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
    
    print(f"\n初始状态:")
    print(f"  球池: {sum(game.ball_pool.values())} 个球")
    print(f"  牌堆: Lv1={len(game.deck_lv1)}, Lv2={len(game.deck_lv2)}, Lv3={len(game.deck_lv3)}")
    print(f"  场面: Lv1={len(game.tableau[1])}, Lv2={len(game.tableau[2])}, Lv3={len(game.tableau[3])}")
    print(f"  AI难度: 中等")
    print(f"  📝 历史记录ID: {game_id}")
    
    # 模拟游戏进行（使用中等AI决策）
    turn_count = 0
    max_turns = 1000  # 防止无限循环
    history.start_turn(1, player_names[0])
    
    while not game.game_over and turn_count < max_turns:
        turn_count += 1
        current_player = game.get_current_player()
        
        if turn_count % 20 == 1:  # 每20回合打印一次状态
            print(f"\n--- 回合 {turn_count} ---")
            print(f"  当前玩家: {current_player.name}")
            print(f"  分数: {[f'{p.name}:{p.victory_points}' for p in game.players]}")
            print(f"  剩余牌: Lv1={len(game.deck_lv1)}, Lv2={len(game.deck_lv2)}, Lv3={len(game.deck_lv3)}")
            print(f"  球池: {[f'{bt.value}:{game.ball_pool[bt]}' for bt in [BallType.RED, BallType.BLUE, BallType.YELLOW, BallType.PINK, BallType.BLACK]]}")
        
        # 记录动作前状态
        player_state_before = {
            "balls": {bt.value: count for bt, count in current_player.balls.items()},
            "victory_points": current_player.victory_points,
            "owned_cards_count": len(current_player.display_area),
            "reserved_cards_count": len(current_player.reserved_cards)
        }
        ball_pool_before = {bt.value: count for bt, count in game.ball_pool.items()}
        history.record_state_before_action(current_player.name, player_state_before, ball_pool_before)
        
        # 使用AI做决策
        ai = ai_players[current_player.name]
        action = ai.make_decision(game, current_player)
        
        if turn_count <= 5:  # 打印前5回合的详细信息
            print(f"  AI决策: {action}")
        
        if action:
            try:
                if action["action"] == "buy_card":
                    # 从卡牌名称找到卡牌对象
                    card_name = action["data"]["card"]["name"]
                    found_card = None
                    
                    # 在场上找卡
                    for tier in [1, 2, 3]:
                        for card in game.tableau[tier]:
                            if card.name == card_name:
                                found_card = card
                                break
                        if found_card:
                            break
                    
                    # 在预购区找卡
                    if not found_card:
                        for card in current_player.reserved_cards:
                            if card.name == card_name:
                                found_card = card
                                break
                    
                    # 在稀有/传说卡找
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
                    
                    # 在场上找卡
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
                    # 将字符串转回BallType
                    balls = [BallType(bt) for bt in ball_types]
                    result = game.take_balls(balls)
                    history.record_action("take_balls", {
                        "ball_types": ball_types
                    }, result, "拿取球" if result else "拿取球失败")
                    
            except Exception as e:
                print(f"  ⚠️ 动作执行失败: {e}")
        
        # 处理球数限制（AI自动处理）
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
    
    # 检查游戏结果
    print(f"\n🏁 游戏结束!")
    print(f"  总回合数: {turn_count}")
    logger.assert_true(game.game_over, "游戏已结束")
    logger.assert_true(turn_count < max_turns, f"游戏在{max_turns}回合内结束")
    
    # 检查胜者
    winner = game.winner
    logger.assert_true(winner is not None, "有胜利者")
    if winner:
        print(f"\n🏆 胜利者: {winner.name}, {winner.victory_points}分")
        logger.assert_true(winner.victory_points >= game.victory_points_goal, "胜利者分数达标")
    
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

# ============================================================================
# 测试2: 边缘案例 - 牌堆耗尽
# ============================================================================

def test_deck_exhaustion():
    """测试牌堆耗尽的情况"""
    logger.start_test("边缘案例 - 牌堆耗尽")
    
    game = SplendorPokemonGame(["玩家1", "玩家2"])
    player = game.players[0]
    
    # 记录初始牌堆数量
    initial_lv1 = len(game.deck_lv1)
    initial_lv2 = len(game.deck_lv2)
    
    print(f"\n初始牌堆: Lv1={initial_lv1}, Lv2={initial_lv2}, Lv3={len(game.deck_lv3)}")
    
    # 清空Lv1牌堆
    game.deck_lv1.clear()
    logger.assert_equal(len(game.deck_lv1), 0, "Lv1牌堆已清空")
    
    # 尝试补充场面（模拟买卡后的补充）
    if game.tableau[1]:
        card_to_buy = game.tableau[1][0]
        # 给玩家足够的资源
        for ball_type in BallType:
            player.balls[ball_type] = 10
        
        print(f"\n购买Lv1卡牌: {card_to_buy.name}")
        result = game.buy_card(card_to_buy)
        
        logger.assert_true(result, "购买成功")
        
        # 检查场面补充
        if len(game.deck_lv1) == 0:
            print(f"  Lv1牌堆已空，场面不补充")
            logger.assert_true(len(game.tableau[1]) < 4, "场面卡牌少于4张")
        else:
            logger.assert_equal(len(game.tableau[1]), 4, "场面维持4张")
    
    # 注释：游戏不支持盲预购功能（预购牌堆顶），只能预购场上可见的卡
    # 因此跳过这个测试
    print(f"\n跳过盲预购测试（游戏不支持此功能）")

# ============================================================================
# 测试3: 最后一轮机制 - 不同玩家触发
# ============================================================================

def test_final_round_trigger():
    """测试最后一轮触发机制"""
    logger.start_test("最后一轮机制 - 不同玩家触发")
    
    # 测试玩家1触发
    print(f"\n场景1: 玩家1触发18分")
    game = SplendorPokemonGame(["P1", "P2", "P3", "P4"], victory_points=18)
    game.players[0].victory_points = 18
    game.current_player_index = 0
    
    game.end_turn()
    
    logger.assert_true(game.final_round_triggered, "最后一轮已触发")
    logger.assert_true(not game.game_over, "游戏继续(等P2/P3/P4)")
    
    # 测试玩家4触发
    print(f"\n场景2: 玩家4触发18分")
    game2 = SplendorPokemonGame(["P1", "P2", "P3", "P4"], victory_points=18)
    game2.players[3].victory_points = 18
    game2.current_player_index = 3
    
    game2.end_turn()
    
    logger.assert_true(game2.game_over, "游戏直接结束")
    logger.assert_equal(game2.winner.name, "P4", "玩家4获胜")
    
    # 测试玩家2触发，然后玩家3超过
    print(f"\n场景3: 玩家2触发18分，玩家3超过")
    game3 = SplendorPokemonGame(["P1", "P2", "P3", "P4"], victory_points=18)
    game3.players[1].victory_points = 18
    game3.current_player_index = 1
    game3.end_turn()
    
    # 玩家3得19分
    game3.players[2].victory_points = 19
    game3.end_turn()
    
    # 玩家4回合
    game3.end_turn()
    
    logger.assert_true(game3.game_over, "游戏结束")
    logger.assert_equal(game3.winner.name, "P3", "玩家3获胜(分数最高)")

# ============================================================================
# 测试4: 同分排名规则
# ============================================================================

def test_tie_breaking():
    """测试同分时的排名规则（后手优先）"""
    logger.start_test("同分排名规则")
    
    game = SplendorPokemonGame(["P1", "P2", "P3", "P4"], victory_points=18)
    
    # 所有玩家都是20分
    for player in game.players:
        player.victory_points = 20
    
    # 触发游戏结束
    game.current_player_index = 3  # 玩家4回合
    game.end_turn()
    
    logger.assert_true(game.game_over, "游戏结束")
    
    # 检查胜者是玩家4（后手优先）
    logger.assert_equal(game.winner.name, "P4", "同分时后手获胜")
    
    print(f"\n同分情况:")
    print(f"  所有玩家: 20分")
    print(f"  胜利者: {game.winner.name} (玩家序号最大)")

# ============================================================================
# 测试5: 预购区满3张限制
# ============================================================================

def test_reserve_limit():
    """测试预购区3张上限"""
    logger.start_test("预购区3张上限")
    
    game = SplendorPokemonGame(["玩家1"])
    player = game.players[0]
    
    # 预购3张卡
    for i in range(3):
        if game.tableau[1]:
            card = game.tableau[1][0]
            print(f"\n预购第{i+1}张: {card.name}")
            result = game.reserve_card(card)
            logger.assert_true(result, f"第{i+1}张预购成功")
    
    logger.assert_equal(len(player.reserved_cards), 3, "预购区有3张")
    logger.assert_equal(player.balls[BallType.MASTER], 3, "获得3个大师球")
    
    # 尝试预购第4张
    if game.tableau[1]:
        print(f"\n尝试预购第4张...")
        result = game.reserve_card(game.tableau[1][0])
        logger.assert_true(not result, "预购区满，无法预购第4张")

# ============================================================================
# 测试6: 完整进化链 (1→2→3)
# ============================================================================

def test_complete_evolution_chain():
    """测试完整进化链：1级→2级→3级"""
    logger.start_test("完整进化链 1→2→3")
    
    game = SplendorPokemonGame(["训练家"])
    player = game.players[0]
    
    # 创建完整的妙蛙系列进化链
    # Lv1: 妙蛙种子
    bulbasaur = PokemonCard(
        "妙蛙种子", 1, Rarity.NORMAL, 0,
        {BallType.PINK: 1},  # 成本
        {BallType.PINK: 1},  # 永久球
        Evolution("妙蛙草", {BallType.PINK: 2})  # 需要2粉进化
    )
    
    # Lv2: 妙蛙草
    ivysaur = PokemonCard(
        "妙蛙草", 2, Rarity.NORMAL, 1,
        {BallType.PINK: 3},
        {BallType.PINK: 1},
        Evolution("妙蛙花", {BallType.PINK: 3})  # 需要3粉进化
    )
    
    # Lv3: 妙蛙花
    venusaur = PokemonCard(
        "妙蛙花", 3, Rarity.NORMAL, 3,
        {BallType.PINK: 5},
        {BallType.PINK: 2}
    )
    
    # 给玩家资源
    player.balls[BallType.PINK] = 10
    
    # Step 1: 购买妙蛙种子
    print(f"\nStep 1: 购买 {bulbasaur.name}")
    game.tableau[1].append(bulbasaur)
    result = game.buy_card(bulbasaur)
    logger.assert_true(result, "购买妙蛙种子")
    logger.assert_equal(player.victory_points, 0, "0分")
    
    # Step 2: 获得第二个粉色永久球
    print(f"\nStep 2: 获得额外粉色永久球")
    pink_card = PokemonCard("粉叶卡", 1, Rarity.NORMAL, 0,
                            {BallType.PINK: 1}, {BallType.PINK: 1})
    game.tableau[1].append(pink_card)
    game.buy_card(pink_card)
    
    permanent_pink = player.get_permanent_balls()[BallType.PINK]
    logger.assert_true(permanent_pink >= 2, f"粉色永久球≥2 (实际{permanent_pink})")
    
    # Step 3: 进化到妙蛙草
    print(f"\nStep 3: 进化 {bulbasaur.name} → {ivysaur.name}")
    game.tableau[2].append(ivysaur)
    can_evolve = player.can_evolve(ivysaur, bulbasaur)
    logger.assert_true(can_evolve, "满足进化条件")
    
    if can_evolve:
        result = player.evolve(bulbasaur, ivysaur)
        logger.assert_true(result, "进化到妙蛙草")
        logger.assert_equal(player.victory_points, 1, "1分")
    
    # Step 4: 获得第三个粉色永久球
    print(f"\nStep 4: 获得更多粉色永久球")
    for i in range(2):
        card = PokemonCard(f"粉叶卡{i+2}", 1, Rarity.NORMAL, 0,
                          {BallType.PINK: 1}, {BallType.PINK: 1})
        game.tableau[1].append(card)
        game.buy_card(card)
    
    permanent_pink = player.get_permanent_balls()[BallType.PINK]
    logger.assert_true(permanent_pink >= 3, f"粉色永久球≥3 (实际{permanent_pink})")
    
    # Step 5: 进化到妙蛙花
    print(f"\nStep 5: 进化 {ivysaur.name} → {venusaur.name}")
    game.tableau[3].append(venusaur)
    can_evolve = player.can_evolve(venusaur, ivysaur)
    logger.assert_true(can_evolve, "满足进化条件")
    
    if can_evolve:
        result = player.evolve(ivysaur, venusaur)
        logger.assert_true(result, "进化到妙蛙花")
        logger.assert_equal(player.victory_points, 3, "3分")
        
    print(f"\n✨ 完整进化链完成!")
    print(f"  展示区: {[c.name for c in player.display_area]}")
    print(f"  进化历史: {[c.name for c in player.evolved_cards]}")

# ============================================================================
# 测试7: 拿球规则的各种情况
# ============================================================================

def test_take_balls_rules():
    """测试拿球的各种规则"""
    logger.start_test("拿球规则测试")
    
    game = SplendorPokemonGame(["玩家1"])
    
    # 场景1: 拿3个不同色
    print(f"\n场景1: 拿3个不同颜色")
    result = game.take_balls([BallType.RED, BallType.BLUE, BallType.YELLOW])
    logger.assert_true(result, "拿3个不同色成功")
    
    game.end_turn()
    
    # 场景2: 拿2个同色（球池≥4）
    print(f"\n场景2: 拿2个同色（球池≥4）")
    red_count = game.ball_pool[BallType.RED]
    print(f"  红球数量: {red_count}")
    
    if red_count >= 4:
        result = game.take_balls([BallType.RED, BallType.RED])
        logger.assert_true(result, "球池≥4，拿2个同色成功")
    else:
        result = game.take_balls([BallType.RED, BallType.RED])
        logger.assert_true(not result, "球池<4，拿2个同色失败")
    
    game.end_turn()
    
    # 场景3: 球池不足3种颜色
    print(f"\n场景3: 球池只剩2种颜色")
    # 清空大部分球
    for ball_type in [BallType.BLACK, BallType.YELLOW, BallType.PINK]:
        game.ball_pool[ball_type] = 0
    
    available_colors = [bt for bt in BallType if game.ball_pool[bt] > 0 and bt != BallType.MASTER]
    print(f"  可用颜色: {len(available_colors)}种")
    
    if len(available_colors) == 2:
        # 必须拿所有可用颜色各1个
        result = game.take_balls(available_colors)
        logger.assert_true(result, "球不足时拿所有可用颜色")

# ============================================================================
# 测试8: 大师球支付方案
# ============================================================================

def test_master_ball_payment():
    """测试大师球的多种支付方案"""
    logger.start_test("大师球支付方案")
    
    game = SplendorPokemonGame(["玩家1"])
    player = game.players[0]
    
    # 创建需要多种颜色的卡牌
    card = PokemonCard(
        "复杂卡", 2, Rarity.NORMAL, 2,
        {BallType.RED: 2, BallType.BLUE: 2, BallType.YELLOW: 1},  # 需要红2蓝2黄1
        {BallType.RED: 1}
    )
    
    # 玩家只有部分颜色球+大师球
    player.balls[BallType.RED] = 1      # 红色缺1个
    player.balls[BallType.BLUE] = 1     # 蓝色缺1个
    player.balls[BallType.YELLOW] = 0   # 黄色缺1个
    player.balls[BallType.MASTER] = 3   # 3个大师球
    
    print(f"\n卡牌需求: 红2 蓝2 黄1")
    print(f"持有球: 红1 蓝1 黄0 大师3")
    print(f"差值: 红1 蓝1 黄1 = 总共缺3个")
    
    # 检查是否可以购买
    can_buy = player.can_afford(card)
    logger.assert_true(can_buy, "大师球足够，可以购买")
    
    # 游戏会自动使用大师球补足
    # 预期：用红1+大师1，蓝1+大师1，黄0+大师1 = 消耗3个大师球
    print(f"购买前大师球: {player.balls[BallType.MASTER]}")
    
    game.tableau[2].append(card)
    result = game.buy_card(card)  # 自动支付，不需要指定payment
    
    print(f"购买后大师球: {player.balls[BallType.MASTER]}")
    logger.assert_true(result, "支付成功")
    logger.assert_equal(player.balls[BallType.MASTER], 0, "大师球用完（自动补足缺少的3个球）")
    logger.assert_equal(len(player.display_area), 1, "卡牌已加入展示区")
    logger.assert_equal(player.display_area[0].name, "复杂卡", "购买的是目标卡牌")

# ============================================================================
# 测试9: 球数上限与放回
# ============================================================================

def test_ball_limit_and_return():
    """测试球数上限和放回机制"""
    logger.start_test("球数上限与放回")
    
    game = SplendorPokemonGame(["玩家1"])
    player = game.players[0]
    
    # 给玩家9个球
    player.balls[BallType.RED] = 3
    player.balls[BallType.BLUE] = 3
    player.balls[BallType.YELLOW] = 3
    total = player.get_total_balls()
    logger.assert_equal(total, 9, f"初始球数: {total}")
    
    # 拿3个球（会超过10个）
    print(f"\n拿3个球（当前9个，拿后12个）")
    result = game.take_balls([BallType.YELLOW, BallType.PINK, BallType.BLACK])
    logger.assert_true(result, "拿球成功")
    
    total = player.get_total_balls()
    logger.assert_equal(total, 12, f"拿球后: {total}")
    logger.assert_true(player.needs_return_balls, "触发放回球标志")
    
    # 模拟放回2个球
    print(f"\n放回2个红球")
    balls_to_return = {BallType.RED: 2}
    result = game.return_balls(balls_to_return)
    logger.assert_true(result, "放回成功")
    
    total = player.get_total_balls()
    logger.assert_equal(total, 10, f"放回后: {total}")
    logger.assert_true(not player.needs_return_balls, "放回球标志清除")

# ============================================================================
# 测试10: 稀有/传说卡牌不可预购
# ============================================================================

def test_rare_legendary_reserve():
    """测试稀有/传说卡不可预购"""
    logger.start_test("稀有/传说卡不可预购")
    
    game = SplendorPokemonGame(["玩家1"])
    
    # 尝试预购稀有卡
    if game.rare_card:
        print(f"\n尝试预购稀有卡: {game.rare_card.name}")
        result = game.reserve_card(game.rare_card)
        logger.assert_true(not result, "稀有卡不可预购")
    
    # 尝试预购传说卡
    if game.legendary_card:
        print(f"\n尝试预购传说卡: {game.legendary_card.name}")
        result = game.reserve_card(game.legendary_card)
        logger.assert_true(not result, "传说卡不可预购")
    
    # 普通卡可以预购
    if game.tableau[1]:
        print(f"\n预购普通Lv1卡: {game.tableau[1][0].name}")
        result = game.reserve_card(game.tableau[1][0])
        logger.assert_true(result, "普通卡可以预购")

# ============================================================================
# 测试11: 预购区卡牌进化
# ============================================================================

def test_evolution_from_reserved():
    """测试从预购区进化"""
    logger.start_test("从预购区进化")
    
    game = SplendorPokemonGame(["玩家1"])
    player = game.players[0]
    
    # 创建小火龙和火恐龙
    charmander = PokemonCard(
        "小火龙", 1, Rarity.NORMAL, 0,
        {BallType.RED: 1},
        {BallType.RED: 1},
        Evolution("火恐龙", {BallType.RED: 2})
    )
    
    charmeleon = PokemonCard(
        "火恐龙", 2, Rarity.NORMAL, 1,
        {BallType.RED: 3},
        {BallType.RED: 1},
        Evolution("喷火龙", {BallType.RED: 3})
    )
    
    # 给玩家足够的资源
    player.balls[BallType.RED] = 10
    
    # 购买小火龙
    game.tableau[1].append(charmander)
    game.buy_card(charmander)
    logger.assert_true(charmander in player.display_area, "小火龙在展示区")
    
    # 预购火恐龙（放到预购区）
    game.tableau[2].append(charmeleon)
    game.reserve_card(charmeleon)
    logger.assert_true(charmeleon in player.reserved_cards, "火恐龙在预购区")
    
    # 获得额外的红色永久球
    red_card = PokemonCard("红卡", 1, Rarity.NORMAL, 0,
                          {BallType.RED: 1}, {BallType.RED: 1})
    game.tableau[1].append(red_card)
    game.buy_card(red_card)
    
    permanent_red = player.get_permanent_balls()[BallType.RED]
    print(f"\n红色永久球: {permanent_red}")
    logger.assert_true(permanent_red >= 2, "红色永久球足够")
    
    # 从预购区进化
    print(f"\n从预购区进化: {charmander.name} → {charmeleon.name}")
    can_evolve = player.can_evolve(charmeleon, charmander)
    logger.assert_true(can_evolve, "可以从预购区进化")
    
    if can_evolve:
        result = player.evolve(charmander, charmeleon)
        logger.assert_true(result, "进化成功")
        logger.assert_true(charmeleon in player.display_area, "火恐龙在展示区")
        logger.assert_true(charmeleon not in player.reserved_cards, "火恐龙离开预购区")

# ============================================================================
# 主测试执行
# ============================================================================

def run_all_tests():
    """运行所有测试"""
    print("🚀 璀璨宝石宝可梦 - 全面测试套件")
    print("=" * 80)
    
    try:
        # 完整游戏流程测试
        test_complete_game_with_ai()
        
        # 边缘案例测试
        test_deck_exhaustion()
        test_final_round_trigger()
        test_tie_breaking()
        test_reserve_limit()
        
        # 复杂场景测试
        test_complete_evolution_chain()
        test_take_balls_rules()
        test_master_ball_payment()
        test_ball_limit_and_return()
        test_rare_legendary_reserve()
        test_evolution_from_reserved()
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    # 打印测试总结
    logger.print_summary()

if __name__ == "__main__":
    run_all_tests()

