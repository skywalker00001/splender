#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI玩家决策引擎
实现智能AI来玩璀璨宝石宝可梦
"""

import random
import sys
import os
from typing import List, Dict, Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cuicanbaoshi import BallType, PokemonCard, Player, SplendorPokemonGame


class AIPlayer:
    """AI玩家类 - 实现智能决策"""
    
    # AI难度级别
    EASY = "简单"
    MEDIUM = "中等"
    HARD = "困难"
    
    def __init__(self, difficulty: str = MEDIUM):
        self.difficulty = difficulty
        self.name_prefix = {
            self.EASY: "机器人·初学者",
            self.MEDIUM: "机器人·训练家",
            self.HARD: "机器人·大师"
        }.get(difficulty, "机器人")
        
    def generate_name(self, existing_players: List[str]) -> str:
        """生成AI玩家名称"""
        bot_names = [
            "小智", "小霞", "小刚", "小建", 
            "莉佳", "娜姿", "阿杏", "马志士",
            "坂木", "渡", "希罗娜", "大吾"
        ]
        
        # 找一个未使用的名字
        for name in bot_names:
            full_name = f"{self.name_prefix}·{name}"
            if full_name not in existing_players:
                return full_name
                
        # 如果都用完了，用数字
        i = 1
        while True:
            full_name = f"{self.name_prefix}{i}"
            if full_name not in existing_players:
                return full_name
            i += 1
    
    def make_decision(self, game: SplendorPokemonGame, player: Player) -> Dict:
        """
        AI做出决策
        返回: {"action": "take_balls/buy_card/reserve_card", "data": {...}}
        """
        # 根据难度调整策略
        if self.difficulty == self.EASY:
            return self._easy_strategy(game, player)
        elif self.difficulty == self.HARD:
            return self._hard_strategy(game, player)
        else:
            return self._medium_strategy(game, player)
    
    def _easy_strategy(self, game: SplendorPokemonGame, player: Player) -> Dict:
        """简单策略 - 随机但合法的决策"""
        actions = []
        
        # 40% 概率尝试购买卡牌
        buyable_cards = self._get_buyable_cards(game, player)
        if buyable_cards and random.random() < 0.4:
            card = random.choice(buyable_cards)
            actions.append({
                "action": "buy_card",
                "data": {
                    "card": {
                        "name": card.name
                    }
                }
            })
        
        # 30% 概率保留卡牌（仅Lv1-3）
        if not actions and len(player.reserved_cards) < 3 and random.random() < 0.3:
            reservable_cards = self._get_all_tableau_cards(game)
            if reservable_cards:
                card = random.choice(reservable_cards)
                actions.append({
                    "action": "reserve_card",
                    "data": {
                        "card": {
                            "name": card.name
                        }
                    }
                })
        
        # 否则拿球（确保总是有一个有效的动作）
        if not actions:
            balls = self._get_random_balls(game)
            if balls:  # 确保有球可拿
                actions.append({
                    "action": "take_balls",
                    "data": {"ball_types": [b.value for b in balls]}
                })
        
        # 如果仍然没有动作，强制拿球
        if not actions:
            print(f"警告：AI玩家 {player.name} 没有可用的动作，尝试拿球")
            # 尝试找任何可用的球
            available_balls = [ball for ball, count in game.ball_pool.items() 
                             if count > 0 and ball != BallType.MASTER]
            if available_balls:
                balls = list(available_balls)[:min(3, len(available_balls))]
                actions.append({
                    "action": "take_balls",
                    "data": {"ball_types": [b.value for b in balls]}
                })
        
        return actions[0] if actions else None
    
    def _medium_strategy(self, game: SplendorPokemonGame, player: Player) -> Dict:
        """中等策略 - 较为合理的决策"""
        
        # 优先级1: 购买高分卡牌
        buyable_cards = self._get_buyable_cards(game, player)
        if buyable_cards:
            # 按胜利点数排序
            buyable_cards.sort(key=lambda c: c.victory_points, reverse=True)
            best_card = buyable_cards[0]
            
            # 如果有高分卡，优先购买
            if best_card.victory_points > 0:
                return {
                    "action": "buy_card",
                    "data": {
                        "card": {
                            "name": best_card.name
                        }
                    }
                }
        
        # 优先级2: 购买便宜的卡牌（积累资源）
        if buyable_cards:
            # 选择成本最低的卡
            buyable_cards.sort(key=lambda c: sum(c.cost.values()))
            return {
                "action": "buy_card",
                "data": {
                    "card": {
                        "name": buyable_cards[0].name
                    }
                }
            }
        
        # 优先级3: 保留高价值卡牌
        if len(player.reserved_cards) < 3:
            valuable_card = self._find_valuable_card(game, player)
            if valuable_card:
                return {
                    "action": "reserve_card",
                    "data": {
                        "card": {
                            "name": valuable_card.name
                        }
                    }
                }
        
        # 优先级4: 智能拿球
        balls = self._get_smart_balls(game, player)
        if balls:
            return {
                "action": "take_balls",
                "data": {"ball_types": [b.value for b in balls]}
            }
        
        # 兜底：如果实在没有球可拿，尝试盲预购
        if len(player.reserved_cards) < 3:
            # 盲预购一张Lv1卡
            return {
                "action": "reserve_card",
                "data": {
                    "level": 1,
                    "blind": True
                }
            }
        
        # 最后的兜底：空过回合（不应该发生）
        print(f"警告：AI玩家 {player.name} 无法决策，跳过回合")
        return None
    
    def _hard_strategy(self, game: SplendorPokemonGame, player: Player) -> Dict:
        """困难策略 - 高级AI决策"""
        
        # 计算当前局势
        leader_points = max([p.victory_points for p in game.players])
        my_points = player.victory_points
        # 接近胜利定义为达到目标分数的80%以上（动态计算）
        is_close_to_win = my_points >= (game.victory_points_goal * 0.8)
        
        # 如果接近胜利，优先购买高分卡
        if is_close_to_win:
            buyable_cards = self._get_buyable_cards(game, player)
            high_point_cards = [c for c in buyable_cards if c.victory_points >= 2]
            if high_point_cards:
                best = max(high_point_cards, key=lambda c: c.victory_points)
                return {
                    "action": "buy_card",
                    "data": {
                        "card": {
                            "name": best.name
                        }
                    }
                }
        
        # 评估所有可购买卡牌的价值
        buyable_cards = self._get_buyable_cards(game, player)
        if buyable_cards:
            best_card = self._evaluate_best_card(buyable_cards, player, game)
            if best_card:
                return {
                    "action": "buy_card",
                    "data": {
                        "card": {
                            "name": best_card.name
                        }
                    }
                }
        
        # 战略性保留卡牌
        if len(player.reserved_cards) < 3:
            # 保留对手可能需要的高分卡
            threat_card = self._find_threat_card(game, player)
            if threat_card:
                return {
                    "action": "reserve_card",
                    "data": {
                        "card": {
                            "name": threat_card.name
                        }
                    }
                }
        
        # 最优球选择
        balls = self._get_optimal_balls(game, player)
        if balls:
            return {
                "action": "take_balls",
                "data": {"ball_types": [b.value for b in balls]}
            }
        
        # 兜底：如果实在没有球可拿，尝试盲预购
        if len(player.reserved_cards) < 3:
            # 盲预购一张Lv2卡（困难模式更激进）
            return {
                "action": "reserve_card",
                "data": {
                    "level": 2,
                    "blind": True
                }
            }
        
        # 最后的兜底：空过回合（不应该发生）
        print(f"警告：AI玩家 {player.name} 无法决策，跳过回合")
        return None
    
    # ===== 辅助方法 =====
    
    def _get_buyable_cards(self, game: SplendorPokemonGame, player: Player) -> List[PokemonCard]:
        """获取所有可购买的卡牌"""
        buyable = []
        
        # 检查场上卡牌
        for tier, cards in game.tableau.items():
            for card in cards:
                if self._can_afford(player, card, game):
                    buyable.append(card)
        
        # 检查稀有/传说卡
        if game.rare_card and self._can_afford(player, game.rare_card, game):
            buyable.append(game.rare_card)
        if game.legendary_card and self._can_afford(player, game.legendary_card, game):
            buyable.append(game.legendary_card)
        
        # 检查保留的卡牌
        for card in player.reserved_cards:
            if self._can_afford(player, card, game):
                buyable.append(card)
        
        return buyable
    
    def _can_afford(self, player: Player, card: PokemonCard, game: SplendorPokemonGame) -> bool:
        """检查是否能支付卡牌"""
        try:
            # 使用game的_check_can_buy方法
            return game._check_can_buy(player, card)[0]
        except:
            return False
    
    def _get_all_tableau_cards(self, game: SplendorPokemonGame) -> List[PokemonCard]:
        """获取桌面所有可预定的卡牌"""
        all_cards = []
        for tier, cards in game.tableau.items():
            for card in cards:
                # 稀有和传说卡不能预定
                if card.rarity.value == "normal":
                    all_cards.append(card)
        return all_cards
    
    def _get_random_balls(self, game: SplendorPokemonGame) -> List[BallType]:
        """随机获取球"""
        available_balls = [ball for ball, count in game.ball_pool.items() 
                          if count > 0 and ball != BallType.MASTER]
        
        if not available_balls:
            return []
        
        # 计算场上有多少种颜色的球大于0
        remained_color = len(available_balls)
        
        if remained_color >= 3:
            # 球充足：随机选择拿2个同色(如果某色≥4)或3个不同色
            # 先尝试找>=4个的颜色
            colors_with_4_plus = [ball for ball in available_balls 
                                 if game.ball_pool.get(ball, 0) >= 4]
            
            if colors_with_4_plus and random.random() < 0.3:
                # 30%概率拿2个同色
                ball_type = random.choice(colors_with_4_plus)
                return [ball_type, ball_type]
            else:
                # 否则拿3个不同色
                return random.sample(available_balls, 3)
        else:
            # 球不充足：拿所有可用颜色各1个
            return list(available_balls)
    
    def _get_smart_balls(self, game: SplendorPokemonGame, player: Player) -> List[BallType]:
        """智能选择球 - 基于需要"""
        # 统计需要哪些球
        ball_needs = {ball: 0 for ball in BallType if ball != BallType.MASTER}
        
        # 看看桌面上有哪些卡牌值得买
        for tier, cards in game.tableau.items():
            for card in cards:
                if not self._can_afford(player, card, game):
                    # 计算还需要多少球
                    for ball_type, cost in card.cost.items():
                        if ball_type != BallType.MASTER:
                            has = player.balls.get(ball_type, 0)
                            permanent = player.get_permanent_balls().get(ball_type, 0)
                            needed = max(0, cost - has - permanent)
                            ball_needs[ball_type] += needed * (card.victory_points + 1)
        
        # 选择需求最高的球
        available_balls = [(ball, need) for ball, need in ball_needs.items() 
                          if game.ball_pool.get(ball, 0) > 0]
        
        if not available_balls:
            return self._get_random_balls(game)
        
        # 按需求排序
        available_balls.sort(key=lambda x: x[1], reverse=True)
        
        # 计算场上有多少种颜色的球大于0
        remained_color = len(available_balls)
        
        if remained_color >= 3:
            # 球充足：选择需求最高的3个不同色
            selected = [ball for ball, _ in available_balls[:3]]
            return selected if len(selected) == 3 else self._get_random_balls(game)
        else:
            # 球不充足：拿所有可用颜色各1个
            return [ball for ball, _ in available_balls]
    
    def _get_optimal_balls(self, game: SplendorPokemonGame, player: Player) -> List[BallType]:
        """最优球选择（困难模式）"""
        return self._get_smart_balls(game, player)  # 简化版本，后续可以优化
    
    def _find_valuable_card(self, game: SplendorPokemonGame, player: Player) -> Optional[PokemonCard]:
        """找到最有价值的卡牌用于保留"""
        all_cards = self._get_all_tableau_cards(game)
        if not all_cards:
            return None
        
        # 优先保留高分卡或高级卡
        valuable = [c for c in all_cards if c.victory_points >= 2 or c.level >= 2]
        if valuable:
            return max(valuable, key=lambda c: c.victory_points * 2 + c.level)
        
        return random.choice(all_cards) if all_cards else None
    
    def _evaluate_best_card(self, cards: List[PokemonCard], player: Player, game: SplendorPokemonGame) -> Optional[PokemonCard]:
        """评估最佳卡牌"""
        if not cards:
            return None
        
        best_score = -1
        best_card = None
        
        for card in cards:
            score = 0
            # 胜利点数权重最高
            score += card.victory_points * 10
            
            # 卡牌等级也重要
            score += card.level * 2
            
            # 永久球的价值
            score += sum(card.permanent_balls.values()) * 3
            
            if score > best_score:
                best_score = score
                best_card = card
        
        return best_card
    
    def _find_threat_card(self, game: SplendorPokemonGame, player: Player) -> Optional[PokemonCard]:
        """找到对其他玩家威胁最大的卡牌"""
        all_cards = self._get_all_tableau_cards(game)
        
        # 优先保留高分卡
        high_point_cards = [c for c in all_cards if c.victory_points >= 3]
        if high_point_cards:
            return random.choice(high_point_cards)
        
        # 其次保留高级别卡
        high_level_cards = [c for c in all_cards if c.level >= 2]
        if high_level_cards:
            return random.choice(high_level_cards)
        
        return random.choice(all_cards) if all_cards else None


# 创建不同难度的AI实例
def create_ai_player(difficulty: str = AIPlayer.MEDIUM) -> AIPlayer:
    """创建AI玩家"""
    return AIPlayer(difficulty)
