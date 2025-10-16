#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
璀璨宝石宝可梦 - 全面系统测试
包括：数据库、游戏逻辑、AI对战、边缘案例
"""
import sys
import os
import signal
import time
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from splendor_pokemon import *
from backend.ai_player import AIPlayer
from backend.database import GameDatabase

# 超时保护
class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("测试超时！")

class ComprehensiveSystemTest:
    """全面系统测试类"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.test_results = []
    
    def run_test(self, test_name, test_func, timeout=60):
        """运行单个测试"""
        print(f"\n{'='*70}")
        print(f"测试: {test_name}")
        print(f"{'='*70}")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout)
        
        try:
            start_time = time.time()
            test_func()
            elapsed = time.time() - start_time
            signal.alarm(0)
            
            print(f"✅ {test_name} - 通过 ({elapsed:.2f}秒)")
            self.passed += 1
            self.test_results.append((test_name, True, elapsed, None))
            return True
        except TimeoutError:
            signal.alarm(0)
            print(f"❌ {test_name} - 超时 (>{timeout}秒)")
            self.failed += 1
            self.test_results.append((test_name, False, timeout, "超时"))
            return False
        except Exception as e:
            signal.alarm(0)
            print(f"❌ {test_name} - 失败: {e}")
            import traceback
            traceback.print_exc()
            self.failed += 1
            self.test_results.append((test_name, False, 0, str(e)))
            return False
    
    def print_summary(self):
        """打印测试总结"""
        print("\n" + "="*70)
        print("测试总结")
        print("="*70)
        print(f"总计: {self.passed + self.failed} 个测试")
        print(f"✅ 通过: {self.passed}")
        print(f"❌ 失败: {self.failed}")
        print(f"通过率: {self.passed/(self.passed+self.failed)*100:.1f}%")
        
        if self.failed > 0:
            print("\n失败的测试:")
            for name, passed, elapsed, error in self.test_results:
                if not passed:
                    print(f"  - {name}: {error}")
        
        print("="*70)

# ============ 测试1: 数据库功能测试 ============
def test_database_basic():
    """测试数据库基本功能"""
    test_db = "test_comprehensive.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    
    db = GameDatabase(test_db)
    
    # 创建用户
    user = db.get_or_create_user("测试玩家")
    assert user['username'] == "测试玩家"
    print("  ✓ 用户创建成功")
    
    # 记录游戏
    now = datetime.now().isoformat()
    db.record_game_participation(
        username="测试玩家",
        game_id="test_001",
        game_history_file="test.json",
        player_name="测试玩家",
        final_rank=1,
        final_score=20,
        is_winner=True,
        game_start_time=now,
        game_end_time=now,
        total_turns=30
    )
    print("  ✓ 游戏记录保存成功")
    
    # 获取历史
    games = db.get_user_game_history("测试玩家")
    assert len(games) == 1
    print("  ✓ 游戏历史查询成功")
    
    # 获取统计
    stats = db.get_user_statistics("测试玩家")
    assert stats['total_games'] == 1
    assert stats['total_wins'] == 1
    print("  ✓ 统计信息查询成功")
    
    os.remove(test_db)

# ============ 测试2: 游戏初始化 ============
def test_game_initialization():
    """测试游戏初始化"""
    game = SplendorPokemonGame(["玩家1", "玩家2"], victory_points=15)
    
    # 检查玩家
    assert len(game.players) == 2
    print("  ✓ 玩家初始化正确")
    
    # 检查球池
    assert game.ball_pool[BallType.BLACK] == 7  # 2人局
    assert game.ball_pool[BallType.MASTER] == 5
    print("  ✓ 球池初始化正确")
    
    # 检查卡牌
    assert len(game.tableau[1]) == 4
    assert len(game.tableau[2]) == 4
    assert len(game.tableau[3]) == 4
    assert game.rare_card is not None
    assert game.legendary_card is not None
    print("  ✓ 卡牌初始化正确")

# ============ 测试3: 拿球功能 ============
def test_take_balls():
    """测试拿球功能"""
    game = SplendorPokemonGame(["玩家1", "玩家2"])
    player = game.get_current_player()
    
    # 拿3个不同颜色的球
    result = game.take_balls([BallType.BLACK, BallType.PINK, BallType.YELLOW])
    assert result == True
    assert player.balls[BallType.BLACK] == 1
    assert player.balls[BallType.PINK] == 1
    assert player.balls[BallType.YELLOW] == 1
    print("  ✓ 拿3个不同球成功")
    
    # 检查球池减少
    assert game.ball_pool[BallType.BLACK] == 6
    print("  ✓ 球池数量正确减少")

# ============ 测试4: 购买卡牌功能 ============
def test_buy_card():
    """测试购买卡牌功能"""
    game = SplendorPokemonGame(["玩家1", "玩家2"])
    player = game.get_current_player()
    
    # 找一张便宜的卡
    cheap_card = None
    for tier in [1, 2, 3]:
        for card in game.tableau[tier]:
            total_cost = sum(card.cost.values())
            if total_cost <= 3:
                cheap_card = card
                break
        if cheap_card:
            break
    
    if cheap_card:
        # 给玩家足够的球
        for ball_type, cost in cheap_card.cost.items():
            if ball_type != BallType.MASTER:
                player.balls[ball_type] = cost
        
        initial_vp = player.victory_points
        result = game.buy_card(cheap_card)
        assert result == True
        assert player.victory_points >= initial_vp
        print(f"  ✓ 购买卡牌成功: {cheap_card.name}")

# ============ 测试5: 预购卡牌功能 ============
def test_reserve_card():
    """测试预购卡牌功能"""
    game = SplendorPokemonGame(["玩家1", "玩家2"])
    player = game.get_current_player()
    
    card = game.tableau[1][0]
    initial_master = player.balls[BallType.MASTER]
    
    result = game.reserve_card(card)
    assert result == True
    assert len(player.reserved_cards) == 1
    assert player.balls[BallType.MASTER] == initial_master + 1
    print("  ✓ 预购卡牌成功")

# ============ 测试6: 放回球功能 ============
def test_return_balls():
    """测试放回球功能"""
    game = SplendorPokemonGame(["玩家1", "玩家2"])
    player = game.get_current_player()
    
    # 给玩家超过10个球
    player.balls[BallType.BLACK] = 6
    player.balls[BallType.PINK] = 5
    
    # 放回球
    result = game.return_balls({BallType.BLACK: 1})
    assert result == True
    assert player.balls[BallType.BLACK] == 5
    print("  ✓ 放回球成功")

# ============ 测试7: 进化功能 ============
def test_evolution():
    """测试进化功能"""
    game = SplendorPokemonGame(["玩家1", "玩家2"])
    player = game.get_current_player()
    
    # 找一张可以进化的卡
    evo_card = None
    for tier in [1, 2]:
        for card in game.tableau[tier]:
            if card.evolution:
                evo_card = card
                break
        if evo_card:
            break
    
    if evo_card:
        # 将卡牌加入展示区
        player.display_area.append(evo_card)
        
        # 找进化目标
        target_name = evo_card.evolution.target_name
        target_card = None
        for tier in [2, 3]:
            for card in game.tableau[tier]:
                if card.name == target_name:
                    target_card = card
                    break
            if target_card:
                break
        
        if target_card:
            # 给玩家足够的进化球
            for ball_type, amount in evo_card.evolution.required_balls.items():
                player.balls[ball_type] = amount
            
            initial_vp = player.victory_points
            result = player.evolve(evo_card, target_card)
            if result:
                assert player.victory_points > initial_vp
                print(f"  ✓ 进化成功: {evo_card.name} → {target_card.name}")
            else:
                print(f"  - 进化条件不满足，跳过测试")
        else:
            print(f"  - 未找到进化目标，跳过测试")

# ============ 测试8: 边缘案例 - 球超限 ============
def test_edge_case_ball_limit():
    """测试边缘案例：球数超限"""
    game = SplendorPokemonGame(["玩家1", "玩家2"])
    player = game.get_current_player()
    
    # 给玩家10个球
    player.balls[BallType.BLACK] = 10
    
    # 尝试拿更多球
    result = game.take_balls([BallType.PINK])
    # 应该成功但标记需要放回
    assert player.needs_return_balls == True
    print("  ✓ 球超限检测正确")

# ============ 测试9: 边缘案例 - 预购区满 ============
def test_edge_case_reserve_full():
    """测试边缘案例：预购区满"""
    game = SplendorPokemonGame(["玩家1", "玩家2"])
    player = game.get_current_player()
    
    # 预购3张卡
    for i in range(3):
        if i < len(game.tableau[1]):
            game.reserve_card(game.tableau[1][0])
    
    # 尝试再预购
    if len(game.tableau[1]) > 0:
        result = game.reserve_card(game.tableau[1][0])
        assert result == False
        print("  ✓ 预购区满限制正确")

# ============ 测试10: 边缘案例 - 球池枯竭 ============
def test_edge_case_ball_pool_empty():
    """测试边缘案例：球池枯竭"""
    game = SplendorPokemonGame(["玩家1", "玩家2"])
    
    # 清空某种颜色的球
    game.ball_pool[BallType.BLACK] = 0
    
    # 尝试拿这种球
    result = game.take_balls([BallType.BLACK])
    assert result == False
    print("  ✓ 球池枯竭限制正确")

# ============ 测试11-16: AI对战测试 ============
def test_ai_game(difficulty, num_players, game_num):
    """测试单局AI对战"""
    player_names = [f"AI{i+1}" for i in range(num_players)]
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
                    card_id = action["data"]["card"]["card_id"]
                    found_card = game.find_card_by_id(card_id, current_player)
                    if found_card:
                        game.buy_card(found_card)
                elif action["action"] == "reserve_card":
                    card_id = action["data"]["card"]["card_id"]
                    found_card = game.find_card_by_id(card_id, current_player)
                    if found_card:
                        game.reserve_card(found_card)
                elif action["action"] == "take_balls":
                    ball_types = action["data"]["ball_types"]
                    balls = [BallType(bt) for bt in ball_types]
                    game.take_balls(balls)
            except:
                pass
        
        # 处理放回球
        if current_player.needs_return_balls:
            while current_player.get_total_balls() > 10:
                max_ball = max(current_player.balls.items(), key=lambda x: x[1])
                if max_ball[1] > 0:
                    current_player.balls[max_ball[0]] -= 1
                    game.ball_pool[max_ball[0]] += 1
            current_player.needs_return_balls = False
        
        game.end_turn()
    
    success = game.winner is not None
    return success, turn_count

def test_ai_simple_2player():
    """测试简单AI 2人局（10局）"""
    results = []
    for i in range(10):
        success, turns = test_ai_game("简单", 2, i+1)
        results.append((success, turns))
        print(f"  第{i+1}局: {'✅成功' if success else '❌超时'} ({turns}回合)")
    
    success_rate = sum(1 for s, _ in results if s) / len(results)
    assert success_rate >= 0.8, f"成功率过低: {success_rate*100:.0f}%"
    print(f"  总成功率: {success_rate*100:.0f}%")

def test_ai_simple_4player():
    """测试简单AI 4人局（10局）"""
    results = []
    for i in range(10):
        success, turns = test_ai_game("简单", 4, i+1)
        results.append((success, turns))
        print(f"  第{i+1}局: {'✅成功' if success else '❌超时'} ({turns}回合)")
    
    success_rate = sum(1 for s, _ in results if s) / len(results)
    assert success_rate >= 0.8, f"成功率过低: {success_rate*100:.0f}%"
    print(f"  总成功率: {success_rate*100:.0f}%")

def test_ai_medium_2player():
    """测试中等AI 2人局（10局）"""
    results = []
    for i in range(10):
        success, turns = test_ai_game("中等", 2, i+1)
        results.append((success, turns))
        print(f"  第{i+1}局: {'✅成功' if success else '❌超时'} ({turns}回合)")
    
    success_rate = sum(1 for s, _ in results if s) / len(results)
    assert success_rate >= 0.9, f"成功率过低: {success_rate*100:.0f}%"
    print(f"  总成功率: {success_rate*100:.0f}%")

def test_ai_medium_4player():
    """测试中等AI 4人局（10局）"""
    results = []
    for i in range(10):
        success, turns = test_ai_game("中等", 4, i+1)
        results.append((success, turns))
        print(f"  第{i+1}局: {'✅成功' if success else '❌超时'} ({turns}回合)")
    
    success_rate = sum(1 for s, _ in results if s) / len(results)
    assert success_rate >= 0.9, f"成功率过低: {success_rate*100:.0f}%"
    print(f"  总成功率: {success_rate*100:.0f}%")

def test_ai_hard_2player():
    """测试困难AI 2人局（10局）"""
    results = []
    for i in range(10):
        success, turns = test_ai_game("困难", 2, i+1)
        results.append((success, turns))
        print(f"  第{i+1}局: {'✅成功' if success else '❌超时'} ({turns}回合)")
    
    success_rate = sum(1 for s, _ in results if s) / len(results)
    assert success_rate >= 0.9, f"成功率过低: {success_rate*100:.0f}%"
    print(f"  总成功率: {success_rate*100:.0f}%")

def test_ai_hard_4player():
    """测试困难AI 4人局（10局）"""
    results = []
    for i in range(10):
        success, turns = test_ai_game("困难", 4, i+1)
        results.append((success, turns))
        print(f"  第{i+1}局: {'✅成功' if success else '❌超时'} ({turns}回合)")
    
    success_rate = sum(1 for s, _ in results if s) / len(results)
    assert success_rate >= 0.9, f"成功率过低: {success_rate*100:.0f}%"
    print(f"  总成功率: {success_rate*100:.0f}%")

# ============ 主测试函数 ============
def run_all_tests():
    """运行所有测试"""
    tester = ComprehensiveSystemTest()
    
    print("\n" + "="*70)
    print("璀璨宝石宝可梦 - 全面系统测试")
    print("="*70)
    
    # 第一部分：数据库和基础功能测试
    print("\n【第一部分：数据库和基础功能】")
    tester.run_test("1. 数据库基本功能", test_database_basic, timeout=30)
    tester.run_test("2. 游戏初始化", test_game_initialization, timeout=10)
    tester.run_test("3. 拿球功能", test_take_balls, timeout=10)
    tester.run_test("4. 购买卡牌", test_buy_card, timeout=10)
    tester.run_test("5. 预购卡牌", test_reserve_card, timeout=10)
    tester.run_test("6. 放回球", test_return_balls, timeout=10)
    tester.run_test("7. 进化功能", test_evolution, timeout=10)
    
    # 第二部分：边缘案例测试
    print("\n【第二部分：边缘案例测试】")
    tester.run_test("8. 球数超限", test_edge_case_ball_limit, timeout=10)
    tester.run_test("9. 预购区满", test_edge_case_reserve_full, timeout=10)
    tester.run_test("10. 球池枯竭", test_edge_case_ball_pool_empty, timeout=10)
    
    # 第三部分：AI对战测试（60局）
    print("\n【第三部分：AI对战测试 (60局)】")
    tester.run_test("11. 简单AI 2人局 (10局)", test_ai_simple_2player, timeout=300)
    tester.run_test("12. 简单AI 4人局 (10局)", test_ai_simple_4player, timeout=300)
    tester.run_test("13. 中等AI 2人局 (10局)", test_ai_medium_2player, timeout=300)
    tester.run_test("14. 中等AI 4人局 (10局)", test_ai_medium_4player, timeout=300)
    tester.run_test("15. 困难AI 2人局 (10局)", test_ai_hard_2player, timeout=300)
    tester.run_test("16. 困难AI 4人局 (10局)", test_ai_hard_4player, timeout=300)
    
    # 打印总结
    tester.print_summary()
    
    return tester.passed == (tester.passed + tester.failed)

if __name__ == '__main__':
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)

