#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终测试 - 中等AI完整对局
"""

import sys
import os
import random

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from splendor_pokemon import *
from backend.ai_player import AIPlayer

# 设置随机种子
random.seed(42)

# 创建游戏（2人局，降低难度）
player_names = ['玩家1', '玩家2']
game = SplendorPokemonGame(player_names, victory_points=12)

# 创建中等AI
ai_players = {}
for name in player_names:
    ai_players[name] = AIPlayer('中等')

print('='*80)
print('🎮 2人对局 - 目标12分 - 中等AI测试')
print('='*80)
print(f'初始球池: 每种颜色4个球\n')

turn_count = 0
max_turns = 500

while not game.game_over and turn_count < max_turns:
    turn_count += 1
    current_player = game.get_current_player()
    
    if turn_count % 10 == 1:
        print(f'\n回合 {turn_count}: {[f"{p.name}:{p.victory_points}" for p in game.players]}')
    
    # 详细打印前20回合
    if turn_count <= 20:
        print(f'  回合{turn_count} - {current_player.name}: 持球{current_player.get_total_balls()}个')
    
    ai = ai_players[current_player.name]
    action = ai.make_decision(game, current_player)
    
    # 详细打印前20回合的决策
    if turn_count <= 20:
        print(f'    AI决策: {action["action"] if action else "None"}')
    
    if action:
        try:
            if action['action'] == 'buy_card':
                card_name = action['data']['card']['name']
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
                if found_card:
                    game.buy_card(found_card)
            elif action['action'] == 'reserve_card':
                card_name = action['data']['card']['name']
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
            elif action['action'] == 'take_balls':
                ball_types = action['data']['ball_types']
                balls = [BallType(bt) for bt in ball_types]
                result = game.take_balls(balls)
                if turn_count <= 20:
                    if result:
                        print(f'      ✅ 拿球成功: {ball_types}')
                    else:
                        print(f'      ❌ 拿球失败: {ball_types}, 球池:{[f"{bt.value}:{game.ball_pool[bt]}" for bt in [BallType.RED, BallType.BLUE, BallType.YELLOW, BallType.PINK, BallType.BLACK]]}')
        except Exception as e:
            if turn_count <= 20:
                print(f'  ⚠️ 动作执行失败: {e}')
    
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

print('\n' + '='*80)
print('🏁 游戏结束！')
print('='*80)
print(f'  总回合数: {turn_count}')
print(f'  游戏完成: {game.game_over}')
print(f'  最终分数: {[f"{p.name}:{p.victory_points}" for p in game.players]}')

if game.game_over:
    rankings = game.get_rankings()
    print(f'\n  🥇 胜利者: {rankings[0][0].name} ({rankings[0][1]}分)')
    print(f'  🥈 第二名: {rankings[1][0].name} ({rankings[1][1]}分)')
    print('\n  ✅ 测试成功！AI能够完成游戏！')
else:
    print(f'\n  ❌ 未在{max_turns}回合内完成')
print('='*80)

