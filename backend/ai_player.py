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
from splendor_pokemon import BallType, PokemonCard, Player, Rarity, SplendorPokemonGame


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
        # 追踪购买失败的卡牌，避免重复尝试
        self.failed_purchase_attempts = {}  # {card_name: fail_count}
        self.last_action = None  # 记录上次动作
        
    def generate_name(self, existing_players: List[str]) -> str:
        """生成AI玩家名称"""
        bot_names = [
            "小智", "小霞", "小刚", "小建", 
            "莉佳", "娜姿", "阿杏", "马志士",
            "坂木", "渡", "希罗娜", "大吾"
        ]
        
        # 随机打乱名字顺序
        import random
        random.shuffle(bot_names)
        
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
                        "card_id": card.card_id
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
                            "card_id": card.card_id
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
        """中等策略 - 智能锚定目标 + 随机因素，防止死锁"""
        
        # === 新增：球池枯竭检测与破局策略 ===
        # 计算球池中的彩色球总数（排除大师球）
        colored_balls_in_pool = sum([count for ball_type, count in game.ball_pool.items() 
                                     if ball_type != BallType.MASTER])
        
        # DEBUG: 关键状态输出
        total_balls = player.get_total_balls()
        if total_balls >= 7 or colored_balls_in_pool <= 6:
            print(f"  🔍 [中等AI调试] {player.name}: 持球={total_balls}, 球池彩球={colored_balls_in_pool}, 预购={len(player.reserved_cards)}")
        
        # 如果球池彩色球<=6，启动简化版破局策略（与困难AI一致）
        if colored_balls_in_pool <= 6:
            print(f"  ⚠️ [中等AI] 球池枯竭(彩球={colored_balls_in_pool})，启动破局策略")
            
            # 破局策略1：如果预购区未满，优先预购获取大师球
            if len(player.reserved_cards) < 3:
                best_card = self._find_best_card_to_reserve(game, player, favor_high_points=False)
                if best_card:
                    print(f"  → 预购 {best_card.name} 获取大师球")
                    return {
                        "action": "reserve_card",
                        "data": {
                            "card": {
                                "card_id": best_card.card_id
                            }
                        }
                    }
            
            # 破局策略2：购买真正能买的卡（优先级：离目标更近 > 分数高）
            buyable_cards = self._get_buyable_cards(game, player)
            
            if buyable_cards:
                # 计算目标卡（预购区最有价值的卡）
                target_card = None
                if player.reserved_cards:
                    # 选择预购区分数最高的卡作为目标
                    target_card = max(player.reserved_cards, key=lambda c: c.victory_points)
                
                # 为每张可买的卡评分
                def score_card(card):
                    score = 0
                    
                    # 优先级1：如果有目标卡，计算这张卡能让我们离目标更近多少
                    if target_card:
                        # 计算购买这张卡后，目标卡的成本降低多少
                        current_permanent = player.get_permanent_balls()
                        new_permanent = dict(current_permanent)
                        # 这张卡会提供的永久球
                        for ball_type, amount in card.permanent_balls.items():
                            new_permanent[ball_type] = new_permanent.get(ball_type, 0) + amount
                        
                        # 计算目标卡在当前永久折扣下的实际成本
                        current_cost = 0
                        for ball_type, cost in target_card.cost.items():
                            if ball_type != BallType.MASTER:
                                actual = max(0, cost - current_permanent.get(ball_type, 0))
                                current_cost += actual
                        
                        # 计算目标卡在新永久折扣下的实际成本
                        new_cost = 0
                        for ball_type, cost in target_card.cost.items():
                            if ball_type != BallType.MASTER:
                                actual = max(0, cost - new_permanent.get(ball_type, 0))
                                new_cost += actual
                        
                        # 成本降低的越多，分数越高（每降低1个球+100分）
                        cost_reduction = current_cost - new_cost
                        score += cost_reduction * 100
                    
                    # 优先级2：分数越高越好（每1分+10分）
                    score += card.victory_points * 10
                    
                    # 附加：如果在预购区，额外加分（释放预购槽位）
                    # 使用card_id比较，避免引用问题
                    if any(c.card_id == card.card_id for c in player.reserved_cards):
                        score += 5
                    
                    return score
                
                # 选择得分最高的卡
                best = max(buyable_cards, key=score_card)
                best_score = score_card(best)
                
                print(f"  → 买 {best.name}({best.victory_points}分, 评分{best_score:.0f}) {'[目标友好]' if best_score >= 100 else '[加分]' if best.victory_points > 0 else '[折扣]'}")
                return {
                    "action": "buy_card",
                    "data": {"card": {"card_id": best.card_id}}
                }
            
            # 破局策略3：如果持球<9，尝试拿球（避免循环）
            if player.get_total_balls() < 9:
                balls = self._get_smart_balls(game, player)
                if balls:
                    print(f"  → 拿球（持球数<9）")
                    return {
                        "action": "take_balls",
                        "data": {"ball_types": [b.value for b in balls]}
                    }
        
        # === 优先级1: 购买卡牌（预购区优先，高分优先） ===
        buyable_cards = self._get_buyable_cards(game, player)
        
        # DEBUG: 输出buyable_cards
        if total_balls >= 7 and buyable_cards:
            print(f"  🔍 [中等AI] buyable_cards: {[c.name for c in buyable_cards]}")
        
        if buyable_cards:
            # 标记哪些卡在预购区
            reserved_card_names = {c.name for c in player.reserved_cards}
            
            # 策略1：如果有高分卡(>0VP)，优先买预购区的高分卡
            high_point_cards = [c for c in buyable_cards if c.victory_points > 0]
            if high_point_cards:
                # 预购区的卡优先（加10分虚拟权重）
                best_card = max(high_point_cards, key=lambda c: (
                    c.victory_points + (10 if c.name in reserved_card_names else 0)
                ))
                return {
                    "action": "buy_card",
                    "data": {
                        "card": {
                            "card_id": best_card.card_id
                        }
                    }
                }
            
            # 策略2：如果持球>7个，买最便宜的卡释放资源（防死锁关键）
            # 优先买预购区的卡，释放预购席位
            if player.get_total_balls() > 7:
                reserved_buyable = [c for c in buyable_cards if c.name in reserved_card_names]
                if reserved_buyable:
                    # 优先买预购区最便宜的卡
                    cheapest = min(reserved_buyable, key=lambda c: sum(c.cost.values()))
                else:
                    # 没有预购区的卡，买场上最便宜的
                    cheapest = min(buyable_cards, key=lambda c: sum(c.cost.values()))
                return {
                    "action": "buy_card",
                    "data": {
                        "card": {
                            "card_id": cheapest.card_id
                        }
                    }
                }
            
            # 策略3：30%概率买便宜卡（增加随机性），优先预购区
            if random.random() < 0.3:
                reserved_buyable = [c for c in buyable_cards if c.name in reserved_card_names]
                if reserved_buyable:
                    cheapest = min(reserved_buyable, key=lambda c: sum(c.cost.values()))
                else:
                    cheapest = min(buyable_cards, key=lambda c: sum(c.cost.values()))
                return {
                    "action": "buy_card",
                    "data": {
                        "card": {
                            "card_id": cheapest.card_id
                        }
                    }
                }
        
        # === 优先级2: 智能预购（防止持球过多死锁） ===
        # 如果持球≥7个且预购区未满，应该预购而不是继续拿球
        if player.get_total_balls() >= 7 and len(player.reserved_cards) < 3:
            best_card = self._find_best_card_to_reserve(game, player)
            if best_card:
                return {
                    "action": "reserve_card",
                    "data": {
                        "card": {
                            "card_id": best_card.card_id
                        }
                    }
                }
        
        # === 优先级3: 智能拿球（锚定目标卡牌） ===
        target_card = self._find_target_card_for_balls(game, player)
        if target_card:
            # 计算目标卡牌还需要哪些球
            needed_balls = self._calculate_needed_balls(player, target_card)
            
            # 检查球池中有哪些目标球
            available_needed = [b for b in needed_balls if game.ball_pool.get(b, 0) > 0]
            
            if len(available_needed) >= 3:
                # 目标球充足，选前3个（必须3个不同颜色）
                selected = available_needed[:3]
                # 加入20%随机因素，打乱顺序
                if random.random() < 0.2:
                    random.shuffle(selected)
                return {
                    "action": "take_balls",
                    "data": {"ball_types": [b.value for b in selected]}
                }
            
            # 如果目标球不足3个，不能用这个策略（会违反拿球规则）
            # 直接跳到智能拿球策略
        
        # === 优先级4: 随机智能拿球（加入变化） ===
        balls = self._get_smart_balls(game, player)
        if balls:
            # 30%概率改变拿球顺序，增加随机性
            if random.random() < 0.3:
                random.shuffle(balls)
            return {
                "action": "take_balls",
                "data": {"ball_types": [b.value for b in balls]}
            }
        
        # === 优先级5: 智能预购卡牌（最后兜底） ===
        if len(player.reserved_cards) < 3:
            # 使用性价比算法找最优预购卡
            best_card = self._find_best_card_to_reserve(game, player)
            if best_card:
                return {
                    "action": "reserve_card",
                    "data": {
                        "card": {
                            "card_id": best_card.card_id
                        }
                    }
                }
        
        # 最后的兜底：空过回合
        print(f"警告：AI玩家 {player.name} 无法决策，跳过回合")
        print(f"  - 预购区: {len(player.reserved_cards)}/3")
        print(f"  - 持球数: {player.get_total_balls()}")
        print(f"  - 球池状态: {dict(game.ball_pool)}")
        return None
    
    def _hard_strategy(self, game: SplendorPokemonGame, player: Player) -> Dict:
        """困难策略 - 高级AI决策"""
        
        # ⚠️ 2人局特殊处理：使用调整后的策略
        num_players = len(game.players)
        if num_players == 2:
            return self._hard_2player_strategy(game, player)
        
        # === 死锁检测与破局机制 ===
        if self._detect_deadlock(player, game):
            print(f"⚠️ 检测到死锁状态，启动破局策略: {player.name}")
            deadlock_action = self._break_deadlock(player, game)
            if deadlock_action:
                return deadlock_action
        
        # 计算当前局势
        leader_points = max([p.victory_points for p in game.players])
        my_points = player.victory_points
        # 接近胜利定义为达到目标分数的80%以上（动态计算）
        is_close_to_win = my_points >= (game.victory_points_goal * 0.8)
        
        # 如果接近胜利，优先购买高分卡（预购区优先）
        if is_close_to_win:
            buyable_cards = self._get_buyable_cards(game, player)
            reserved_card_names = {c.name for c in player.reserved_cards}
            high_point_cards = [c for c in buyable_cards if c.victory_points >= 2]
            if high_point_cards:
                # 预购区的高分卡优先（加20分虚拟权重）
                best = max(high_point_cards, key=lambda c: (
                    c.victory_points + (20 if c.name in reserved_card_names else 0)
                ))
                return {
                    "action": "buy_card",
                    "data": {
                        "card": {
                            "card_id": best.card_id
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
                            "card_id": best_card.card_id
                        }
                    }
                }
        
        # ⚠️ 特殊策略：如果预购区满了且持球>=9，必须买卡释放资源（避免死循环）
        if len(player.reserved_cards) == 3 and player.get_total_balls() >= 9:
            print(f"  💡 {player.name}: 预购区满+持球多({player.get_total_balls()})，必须买卡释放资源")
            
            # 策略1：检查是否有距离<=1的卡可以立即买（预购区优先）
            reserved_cards_with_distance = [(c, self._calculate_card_distance(c, player)) 
                                           for c in player.reserved_cards]
            very_close_reserved = [c for c, d in reserved_cards_with_distance if d <= 1]
            
            if very_close_reserved:
                # 优先买预购区中距离<=1的卡（有分数的优先）
                best = max(very_close_reserved, key=lambda c: c.victory_points)
                print(f"  → 买预购区的 {best.name}({best.victory_points}分，距离<=1)")
                return {
                    "action": "buy_card",
                    "data": {"card": {"card_id": best.card_id}}
                }
            
            # 策略2：检查场上是否有距离<=1的卡可以买
            all_buyable = self._get_buyable_cards(game, player)
            if all_buyable:
                # 买有分数的卡，或者最便宜的卡
                with_points = [c for c in all_buyable if c.victory_points > 0]
                if with_points:
                    best = max(with_points, key=lambda c: c.victory_points)
                    print(f"  → 买场上的 {best.name}({best.victory_points}分) 释放资源")
                    return {
                        "action": "buy_card",
                        "data": {"card": {"card_id": best.card_id}}
                    }
                else:
                    # 买最便宜的0分卡，获得永久折扣
                    cheapest = min(all_buyable, key=lambda c: sum(c.cost.values()))
                    print(f"  → 买最便宜的 {cheapest.name} 获得永久折扣")
                    return {
                        "action": "buy_card",
                        "data": {"card": {"card_id": cheapest.card_id}}
                    }
            
            # 策略3：如果买不起任何卡，找最接近的目标
            cheapest_reserved = min(player.reserved_cards, 
                                   key=lambda c: self._calculate_card_distance(c, player))
            min_distance = self._calculate_card_distance(cheapest_reserved, player)
            
            if min_distance > 1:
                # 目标卡距离>1，拿球会导致还球循环，跳过回合
                print(f"  → 目标 {cheapest_reserved.name} 距离={min_distance}>1，跳过拿球避免循环")
                # 不拿球，直接跳到预购逻辑（如果预购区未满）或跳过回合
        
        # 战略性保留卡牌
        if len(player.reserved_cards) < 3:
            # 保留对手可能需要的高分卡
            threat_card = self._find_threat_card(game, player)
            if threat_card:
                return {
                    "action": "reserve_card",
                    "data": {
                        "card": {
                            "card_id": threat_card.card_id
                        }
                    }
                }
        
        # ⚠️ 拿球前检查：如果持球>=9且预购区满，不要拿球（避免还球循环）
        if player.get_total_balls() >= 9 and len(player.reserved_cards) == 3:
            print(f"  ⚠️ {player.name}: 持球({player.get_total_balls()})>=9且预购区满，跳过拿球")
            # 跳过拿球，尝试预购或跳过回合
        else:
            # 最优球选择
            balls = self._get_optimal_balls(game, player)
            if balls:
                return {
                    "action": "take_balls",
                    "data": {"ball_types": [b.value for b in balls]}
                }
        
        # 兜底：如果实在没有球可拿，智能预购
        if len(player.reserved_cards) < 3:
            # 困难模式：使用性价比算法，但权重更倾向高分卡
            best_card = self._find_best_card_to_reserve(game, player, favor_high_points=True)
            if best_card:
                return {
                    "action": "reserve_card",
                    "data": {
                        "card": {
                            "card_id": best_card.card_id
                        }
                    }
                }
        
        # 最后的兜底：空过回合（不应该发生）
        print(f"警告：AI玩家 {player.name} 无法决策，跳过回合")
        print(f"  - 预购区: {len(player.reserved_cards)}/3")
        print(f"  - 持球数: {player.get_total_balls()}")
        return None
    
    def _hard_2player_strategy(self, game: SplendorPokemonGame, player: Player) -> Dict:
        """困难策略 - 2人局特殊版本，避免死锁"""
        
        # === 死锁检测与破局机制（最高优先级） ===
        if self._detect_deadlock(player, game):
            print(f"⚠️ 检测到死锁状态，启动破局策略: {player.name}")
            deadlock_action = self._break_deadlock(player, game)
            if deadlock_action:
                return deadlock_action
        
        # === 球池枯竭检测（新增）===
        # 计算球池中的彩色球总数
        colored_balls_in_pool = sum([count for ball_type, count in game.ball_pool.items() 
                                      if ball_type != BallType.MASTER])
        
        # 如果球池彩色球<=6，说明资源严重短缺，必须通过预购或购买来破局
        if colored_balls_in_pool <= 6:
            print(f"  ⚠️ 球池枯竭(彩球={colored_balls_in_pool})，启动破局策略")
            
            # 策略1：优先预购（获得大师球）
            if len(player.reserved_cards) < 3:
                reservable_cards = self._get_all_tableau_cards(game)
                if reservable_cards:
                    # 选择最有价值的卡牌预购
                    best_card = self._find_best_card_to_reserve(game, player, favor_high_points=False)
                    if best_card:
                        print(f"  → 预购 {best_card.name} 获取大师球")
                        return {
                            "action": "reserve_card",
                            "data": {
                                "card": {
                                    "card_id": best_card.card_id
                                }
                            }
                        }
            
            # 策略2：购买任何能买的卡（优先有分数的卡）
            buyable_cards = self._get_buyable_cards(game, player)
            if buyable_cards:
                reserved_card_names = {c.name for c in player.reserved_cards}
                
                # 优先买预购区的卡（释放槽位）
                reserved_buyable = [c for c in buyable_cards if c.name in reserved_card_names]
                if reserved_buyable:
                    # 预购区有分数的优先，否则选最便宜的
                    with_points = [c for c in reserved_buyable if c.victory_points > 0]
                    if with_points:
                        best = max(with_points, key=lambda c: c.victory_points)
                        print(f"  → 买预购区的 {best.name}({best.victory_points}分) 释放槽位")
                        return {
                            "action": "buy_card",
                            "data": {"card": {"card_id": best.card_id}}
                        }
                    else:
                        cheapest = min(reserved_buyable, key=lambda c: sum(c.cost.values()))
                        print(f"  → 买预购区的 {cheapest.name} 释放槽位")
                        return {
                            "action": "buy_card",
                            "data": {"card": {"card_id": cheapest.card_id}}
                        }
                
                # 场上的卡：优先买有分数的
                with_points = [c for c in buyable_cards if c.victory_points > 0]
                if with_points:
                    # 买性价比最高的：分数/成本
                    best = max(with_points, key=lambda c: (
                        c.victory_points * 10 + 
                        c.level * 2 - 
                        sum(c.cost.values()) * 0.5
                    ))
                    print(f"  → 买 {best.name}({best.victory_points}分) 获得分数")
                else:
                    # 没有分数的卡，买最便宜的获得永久折扣
                    cheapest = min(buyable_cards, key=lambda c: sum(c.cost.values()))
                    print(f"  → 买 {cheapest.name} 增加永久折扣")
                
                return {
                    "action": "buy_card",
                    "data": {"card": {"card_id": best.card_id if with_points else cheapest.card_id}}
                }
            
            # 策略3：实在不行才拿球（但要小心循环）
            if player.get_total_balls() < 9:  # 只有持球<9时才拿球
                balls = self._get_optimal_balls(game, player)
                if balls:
                    print(f"  → 拿球（持球数<9）")
                    return {
                        "action": "take_balls",
                        "data": {"ball_types": [b.value for b in balls]}
                    }
            
            # 策略4：无法操作，跳过回合
            print(f"  → 无可行操作，跳过回合")
            return None
        
        # === 优先级1: 购买卡牌（更激进，预购区优先） ===
        buyable_cards = self._get_buyable_cards(game, player)
        if buyable_cards:
            reserved_card_names = {c.name for c in player.reserved_cards}
            
            # 2人局特殊规则：如果预购区满了，必须优先买预购区的卡
            if len(player.reserved_cards) == 3:
                reserved_buyable = [c for c in buyable_cards if c.name in reserved_card_names]
                if reserved_buyable:
                    # 直接买预购区中分数最高的卡（释放预购槽位）
                    best = max(reserved_buyable, key=lambda c: c.victory_points * 10 + c.level)
                    return {
                        "action": "buy_card",
                        "data": {
                            "card": {
                                "card_id": best.card_id
                            }
                        }
                    }
            
            # 策略1：优先买高分卡(>=2VP)
            high_point_cards = [c for c in buyable_cards if c.victory_points >= 2]
            if high_point_cards:
                # 预购区的卡额外加权
                best_card = max(high_point_cards, key=lambda c: (
                    c.victory_points * 10 + 
                    c.level * 2 +
                    (15 if c.name in reserved_card_names else 0)
                ))
                return {
                    "action": "buy_card",
                    "data": {
                        "card": {
                            "card_id": best_card.card_id
                        }
                    }
                }
            
            # 策略2：如果持球>=7，必须买卡释放资源（防死锁关键）
            if player.get_total_balls() >= 7:
                # 优先买预购区的卡
                reserved_buyable = [c for c in buyable_cards if c.name in reserved_card_names]
                if reserved_buyable:
                    cheapest = min(reserved_buyable, key=lambda c: sum(c.cost.values()))
                else:
                    cheapest = min(buyable_cards, key=lambda c: sum(c.cost.values()))
                return {
                    "action": "buy_card",
                    "data": {
                        "card": {
                            "card_id": cheapest.card_id
                        }
                    }
                }
            
            # 策略3：买中等分数的卡（1-2分）
            mid_point_cards = [c for c in buyable_cards if 1 <= c.victory_points <= 2]
            if mid_point_cards:
                best = max(mid_point_cards, key=lambda c: (
                    c.victory_points * 8 + 
                    c.level * 2 +
                    (12 if c.name in reserved_card_names else 0)
                ))
                return {
                    "action": "buy_card",
                    "data": {
                        "card": {
                            "card_id": best.card_id
                        }
                    }
                }
        
        # === 优先级2: 智能预购（但要控制，避免预购区太快填满） ===
        if len(player.reserved_cards) < 3:
            # 如果持球>=7，优先拿球而不是预购（避免资源死锁）
            if player.get_total_balls() < 7:
                # 只在前2张预购时使用
                if len(player.reserved_cards) < 2:
                    threat_card = self._find_threat_card(game, player)
                    if threat_card:
                        return {
                            "action": "reserve_card",
                            "data": {
                                "card": {
                                    "card_id": threat_card.card_id
                                }
                            }
                        }
        
        # === 优先级3: 智能拿球 ===
        balls = self._get_optimal_balls(game, player)
        if balls:
            return {
                "action": "take_balls",
                "data": {"ball_types": [b.value for b in balls]}
            }
        
        # === 优先级4: 第3张预购（兜底） ===
        if len(player.reserved_cards) < 3:
            best_card = self._find_best_card_to_reserve(game, player, favor_high_points=True)
            if best_card:
                return {
                    "action": "reserve_card",
                    "data": {
                        "card": {
                            "card_id": best_card.card_id
                        }
                    }
                }
        
        # 最后的兜底：空过回合
        print(f"警告：2人局困难AI {player.name} 无法决策，跳过回合")
        print(f"  - 预购区: {len(player.reserved_cards)}/3")
        print(f"  - 持球数: {player.get_total_balls()}")
        print(f"  - 可购买卡: {len(self._get_buyable_cards(game, player))}")
        return None
    
    # ===== 辅助方法 =====
    
    def _get_buyable_cards(self, game: SplendorPokemonGame, player: Player) -> List[PokemonCard]:
        """获取所有可购买的卡牌 - 使用Player的can_afford作为唯一判断标准"""
        buyable = []
        
        # 检查场上卡牌
        for tier, cards in game.tableau.items():
            for card in cards:
                # 只使用Player.can_afford判断（与game.buy_card一致）
                if player.can_afford(card):
                    buyable.append(card)
        
        # 检查稀有/传说卡
        if game.rare_card and player.can_afford(game.rare_card):
            buyable.append(game.rare_card)
        if game.legendary_card and player.can_afford(game.legendary_card):
            buyable.append(game.legendary_card)
        
        # 检查保留的卡牌
        for card in player.reserved_cards:
            if player.can_afford(card):
                buyable.append(card)
        
        return buyable
    
    def _can_really_afford(self, player: Player, card: PokemonCard) -> bool:
        """
        二次检查是否真的能买卡牌
        解决can_afford因永久球折扣导致的误判问题
        """
        permanent = player.get_permanent_balls()
        needed_master_balls = 0
        
        for ball_type, cost in card.cost.items():
            if ball_type == BallType.MASTER:
                needed_master_balls += cost
                continue
            
            # 计算扣除永久球后的实际成本
            discount = permanent.get(ball_type, 0)
            actual_cost = max(0, cost - discount)
            
            # 计算需要从手上支付的球数
            has_this_color = player.balls.get(ball_type, 0)
            need_from_hand = min(actual_cost, has_this_color)  # 能从这个颜色支付的
            need_from_master = actual_cost - need_from_hand  # 需要用大师球补的
            needed_master_balls += need_from_master
        
        # 检查大师球是否足够
        has_master_balls = player.balls.get(BallType.MASTER, 0)
        
        # 额外检查：如果needed_master_balls > 持球总数，肯定买不起
        total_balls = player.get_total_balls()
        if needed_master_balls > total_balls:
            return False
        
        return has_master_balls >= needed_master_balls
    
    def _can_afford(self, player: Player, card: PokemonCard, game: SplendorPokemonGame) -> bool:
        """检查是否能支付卡牌"""
        # 直接使用Player的can_afford方法
        return player.can_afford(card)
    
    def _get_all_tableau_cards(self, game: SplendorPokemonGame) -> List[PokemonCard]:
        """获取桌面所有可预定的卡牌"""
        all_cards = []
        for tier, cards in game.tableau.items():
            for card in cards:
                # 稀有和传说卡不能预定
                if card.rarity == Rarity.NORMAL:
                    all_cards.append(card)
        return all_cards
    
    def _get_random_balls(self, game: SplendorPokemonGame) -> List[BallType]:
        """随机获取球（遵守新规则）"""
        available_balls = [ball for ball, count in game.ball_pool.items() 
                          if count > 0 and ball != BallType.MASTER]
        
        if not available_balls:
            return []
        
        # 计算场上有多少种颜色的球大于0
        remained_color = len(available_balls)
        
        if remained_color >= 3:
            # 球充足：随机选择拿2个同色(如果某色≥4)或3个不同色
            colors_with_4_plus = [ball for ball in available_balls 
                                 if game.ball_pool.get(ball, 0) >= 4]
            
            if colors_with_4_plus and random.random() < 0.3:
                # 30%概率拿2个同色
                ball_type = random.choice(colors_with_4_plus)
                return [ball_type, ball_type]
            else:
                # 否则拿3个不同色
                return random.sample(available_balls, 3)
        
        elif remained_color == 2:
            # 2个颜色：检查是否有≥4个的
            colors_with_4_plus = [ball for ball in available_balls 
                                 if game.ball_pool.get(ball, 0) >= 4]
            
            if colors_with_4_plus:
                # 有≥4个的颜色，随机选择拿2个同色或2个不同色各1个
                if random.random() < 0.5:
                    # 50%概率拿2个同色
                    ball_type = random.choice(colors_with_4_plus)
                    return [ball_type, ball_type]
                else:
                    # 50%概率拿2个不同色各1个
                    return list(available_balls)
            else:
                # 所有颜色都<4个：拿2个不同色各1个
                return list(available_balls)
        
        elif remained_color == 1:
            # 1个颜色
            ball_type = available_balls[0]
            count = game.ball_pool.get(ball_type, 0)
            
            if count >= 4:
                # ≥4个：拿2个同色
                return [ball_type, ball_type]
            else:
                # <4个：拿1个
                return [ball_type]
        
        return []
    
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
        elif remained_color == 2:
            # 只剩2种需要的颜色
            needed_balls = [ball for ball, _ in available_balls]
            all_available = [bt for bt in BallType 
                           if bt != BallType.MASTER and game.ball_pool.get(bt, 0) > 0]
            other_balls = [bt for bt in all_available if bt not in needed_balls]
            
            if other_balls:
                # 有其他颜色可以凑成3个：拿需要的2个+随机1个其他颜色
                selected = needed_balls + [random.choice(other_balls)]
                return selected
            else:
                # 只有这2种颜色，检查是否有≥4个的
                colors_with_4_plus = [ball for ball, _ in available_balls 
                                     if game.ball_pool.get(ball, 0) >= 4]
                
                if colors_with_4_plus:
                    # 有≥4个的颜色，智能判断：拿2个同色好还是2个不同色各1个好
                    # 策略：如果最需要的颜色≥4个，就拿2个同色；否则拿2个不同色
                    most_needed = available_balls[0][0]  # 需求最高的颜色
                    if game.ball_pool.get(most_needed, 0) >= 4:
                        return [most_needed, most_needed]
                    else:
                        # 最需要的颜色<4个，但另一个颜色≥4个
                        # 权衡：拿2个不同色更灵活
                        return all_available  # 2个不同色各1个
                else:
                    # 所有颜色都<4个：拿2个不同色各1个
                    return all_available
        elif remained_color == 1:
            # 只剩1种需要的颜色
            needed_ball = available_balls[0][0]
            all_available = [bt for bt in BallType 
                           if bt != BallType.MASTER and game.ball_pool.get(bt, 0) > 0]
            other_balls = [bt for bt in all_available if bt != needed_ball]
            
            if len(other_balls) >= 2:
                # 有至少2种其他颜色，凑成3个不同色
                selected = [needed_ball] + random.sample(other_balls, 2)
                return selected
            elif len(other_balls) == 1:
                # 有1种其他颜色（总共2种颜色）
                # 检查是否有≥4个的
                colors_with_4_plus = []
                if game.ball_pool.get(needed_ball, 0) >= 4:
                    colors_with_4_plus.append(needed_ball)
                if game.ball_pool.get(other_balls[0], 0) >= 4:
                    colors_with_4_plus.append(other_balls[0])
                
                if colors_with_4_plus:
                    # 有≥4个的颜色，智能判断
                    # 优先拿最需要的颜色（如果它≥4个）
                    if game.ball_pool.get(needed_ball, 0) >= 4:
                        return [needed_ball, needed_ball]
                    else:
                        # 最需要的<4个，另一个≥4个
                        # 权衡：拿2个不同色更灵活
                        return all_available  # 2个不同色各1个
                else:
                    # 所有颜色都<4个：拿2个不同色各1个
                    return all_available
            else:
                # 只有这1种颜色
                count = game.ball_pool.get(needed_ball, 0)
                if count >= 4:
                    # ≥4个：拿2个同色
                    return [needed_ball, needed_ball]
                else:
                    # <4个：拿1个
                    return [needed_ball]
        else:
            # 没有可用球
            return []
    
    def _get_optimal_balls(self, game: SplendorPokemonGame, player: Player) -> List[BallType]:
        """最优球选择（困难模式）- 带降级机制"""
        # 首先尝试智能拿球
        balls = self._get_smart_balls(game, player)
        
        # 如果智能拿球失败，降级为"拿任何可用球"
        if not balls:
            balls = self._get_any_available_balls(game)
            if balls:
                print(f"  ℹ️ {player.name}: 智能拿球失败，降级为强制拿球")
        
        return balls
    
    def _detect_deadlock(self, player: Player, game: SplendorPokemonGame) -> bool:
        """检测是否陷入死锁状态"""
        # 死锁特征：
        # 1. 预购区满了（无法获取新的大师球）
        # 2. 没有大师球
        # 3. 买不起任何卡牌
        # 4. 持球数>=7（资源囤积）
        
        reserve_full = len(player.reserved_cards) == 3
        no_master_balls = player.balls.get(BallType.MASTER, 0) == 0
        has_too_many_balls = player.get_total_balls() >= 7  # 降低阈值，更早触发
        cannot_buy = len(self._get_buyable_cards(game, player)) == 0
        
        # 满足以下条件认为是死锁：
        # - 预购区满了
        # - 没有大师球
        # - 买不起任何卡
        # - 持球数>=7（囤积资源但无法使用）
        is_deadlocked = (
            reserve_full and 
            no_master_balls and 
            cannot_buy and 
            has_too_many_balls
        )
        
        # 新增：检测"虚假可买"的死锁情况
        # 如果_get_buyable_cards返回了卡牌，但实际上持球很少（<5个），
        # 且没有大师球，可能是因为永久球折扣导致的误判
        if not is_deadlocked:
            buyable_cards = self._get_buyable_cards(game, player)
            if buyable_cards and player.get_total_balls() < 5 and no_master_balls:
                # 检查是否真的能买：至少有一张卡的实际成本<=持球数
                has_affordable = False
                for card in buyable_cards:
                    actual_cost = self._calculate_card_distance(card, player)
                    if actual_cost == 0:  # 真的能买
                        has_affordable = True
                        break
                
                # 如果没有真正能买的卡，也算死锁
                if not has_affordable:
                    print(f"  ⚠️ 检测到虚假可买死锁: buyable={len(buyable_cards)}, 持球={player.get_total_balls()}")
                    is_deadlocked = True
        
        return is_deadlocked
    
    def _break_deadlock(self, player: Player, game: SplendorPokemonGame) -> Optional[Dict]:
        """破局策略 - 当检测到死锁时采取的行动"""
        
        # 策略1: 尝试买预购区最便宜的卡（释放预购槽位）
        if player.reserved_cards:
            # 找到最便宜（距离最近）的预购卡
            cheapest = None
            min_distance = float('inf')
            
            for card in player.reserved_cards:
                distance = self._calculate_card_distance(card, player)
                if distance < min_distance:
                    min_distance = distance
                    cheapest = card
            
            # 如果有勉强能买的卡（距离<=玩家持有的大师球+可用球数）
            if cheapest and min_distance <= 5:
                print(f"  → 破局策略1: 尝试买预购区的卡 {cheapest.name} (距离: {min_distance})")
                # 即使买不起，也返回这个动作（让游戏逻辑判断）
                # 注意：这里不会真的买成功，只是表达意图
        
        # 策略2: 强制拿取任何可用的球（降低标准）
        # ⚠️ 关键修复：避免"拿球-还球"死循环
        current_balls = player.get_total_balls()
        reserve_full = len(player.reserved_cards) == 3
        
        # 如果持球数==10且预购区满，拿球会被立即还球，形成死循环
        # 或者持球数>=9且预购区满，拿球也会很快导致还球
        if current_balls >= 9 and reserve_full:
            print(f"  → 破局策略2跳过: 持球={current_balls}>=9且预购区满，拿球会循环")
            # 直接跳到策略3
        else:
            balls = self._get_any_available_balls(game)
            if balls and len(balls) >= 1:
                # 检查拿球后是否会超过10个
                balls_after = current_balls + len(balls)
                if balls_after > 10:
                    # 会超过10个，尝试少拿一些球
                    while len(balls) > 1 and (current_balls + len(balls)) > 10:
                        balls = balls[:-1]
                
                if balls and (current_balls + len(balls)) <= 10:
                    print(f"  → 破局策略2: 强制拿球 {[b.value for b in balls]}")
                    return {
                        "action": "take_balls",
                        "data": {"ball_types": [b.value for b in balls]}
                    }
        
        # 策略3: 如果实在无法拿球，跳过回合（让对手有机会释放资源）
        print(f"  → 破局策略3: 跳过回合，等待对手释放资源")
        print(f"警告：AI玩家 {player.name} 无法决策，跳过回合")
        print(f"  - 预购区: {len(player.reserved_cards)}/3")
        print(f"  - 持球数: {player.get_total_balls()}")
        return None
    
    def _calculate_card_distance(self, card: PokemonCard, player: Player) -> int:
        """计算购买卡牌所需的额外球数（考虑永久折扣）"""
        distance = 0
        permanent = player.get_permanent_balls()
        
        for ball_type, cost in card.cost.items():
            if ball_type != BallType.MASTER:
                has = player.balls.get(ball_type, 0)
                discount = permanent.get(ball_type, 0)
                needed = max(0, cost - has - discount)
                distance += needed
        
        return distance
    
    def _get_any_available_balls(self, game: SplendorPokemonGame) -> List[BallType]:
        """获取任何可用的球（破局用，不考虑最优性）"""
        available = [bt for bt in BallType 
                     if bt != BallType.MASTER and game.ball_pool[bt] > 0]
        
        if not available:
            return []
        
        # 按照游戏规则拿球
        if len(available) >= 3:
            # 优先拿3个不同色
            return available[:3]
        elif len(available) == 2:
            # 检查是否有≥4个的颜色，如果有就拿2个同色
            for bt in available:
                if game.ball_pool[bt] >= 4:
                    return [bt, bt]
            # 否则拿2个不同色各1个
            return available
        elif len(available) == 1:
            # 只剩1种颜色
            bt = available[0]
            if game.ball_pool[bt] >= 4:
                return [bt, bt]
            else:
                return [bt]
        
        return []
    
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
        """评估最佳卡牌（预购区的卡优先）"""
        if not cards:
            return None
        
        best_score = -1
        best_card = None
        reserved_card_names = {c.name for c in player.reserved_cards}
        
        # 2人局特殊处理：如果预购区满了，强制优先买预购区的卡
        num_players = len(game.players)
        if num_players == 2 and len(player.reserved_cards) == 3:
            reserved_cards = [c for c in cards if c.name in reserved_card_names]
            if reserved_cards:
                # 直接返回预购区中分数最高的卡（必须买掉）
                return max(reserved_cards, key=lambda c: c.victory_points * 10 + c.level)
        
        for card in cards:
            score = 0
            # 胜利点数权重最高
            score += card.victory_points * 10
            
            # 卡牌等级也重要
            score += card.level * 2
            
            # 永久球的价值
            score += sum(card.permanent_balls.values()) * 3
            
            # 预购区的卡额外加分（释放预购席位的价值）
            if card.name in reserved_card_names:
                score += 25  # 提高到25分，确保优先
            
            if score > best_score:
                best_score = score
                best_card = card
        
        return best_card
    
    def _find_threat_card(self, game: SplendorPokemonGame, player: Player) -> Optional[PokemonCard]:
        """找到对其他玩家威胁最大的卡牌（2人局时更灵活）"""
        all_cards = self._get_all_tableau_cards(game)
        if not all_cards:
            return None
        
        num_players = len(game.players)
        
        # 2人局特殊策略：混合预购高中低分卡
        if num_players == 2:
            # 如果已经有2张预购卡了，优先预购能买得起的卡
            if len(player.reserved_cards) >= 2:
                # 找距离<=5的卡牌（比较容易买到）
                affordable_soon = []
                for card in all_cards:
                    distance = self._calculate_card_distance(card, player)
                    if distance <= 5:
                        affordable_soon.append((card, distance))
                
                if affordable_soon:
                    # 选择距离最近的高分卡
                    affordable_soon.sort(key=lambda x: (-x[0].victory_points, x[1]))
                    return affordable_soon[0][0]
            
            # 前2张预购：70%概率选高分卡，30%概率选中分卡
            if random.random() < 0.7:
                high_point_cards = [c for c in all_cards if c.victory_points >= 3]
                if high_point_cards:
                    return random.choice(high_point_cards)
            
            # 选择中分卡（1-2分）
            mid_point_cards = [c for c in all_cards if 1 <= c.victory_points <= 2]
            if mid_point_cards:
                return random.choice(mid_point_cards)
        
        # 4人局：保持原有策略
        # 优先保留高分卡
        high_point_cards = [c for c in all_cards if c.victory_points >= 3]
        if high_point_cards:
            return random.choice(high_point_cards)
        
        # 其次保留高级别卡
        high_level_cards = [c for c in all_cards if c.level >= 2]
        if high_level_cards:
            return random.choice(high_level_cards)
        
        return random.choice(all_cards) if all_cards else None
    
    def _find_target_card_for_balls(self, game: SplendorPokemonGame, player: Player) -> Optional[PokemonCard]:
        """找到最接近能买的高分卡作为拿球目标"""
        all_cards = []
        
        # 收集场上所有卡牌（不含稀有和传说）
        for tier in [1, 2, 3]:
            all_cards.extend(game.tableau.get(tier, []))
        
        if not all_cards:
            return None
        
        # 过滤掉已经能买的卡
        unaffordable_cards = [c for c in all_cards if not self._can_afford(player, c, game)]
        
        if not unaffordable_cards:
            return None
        
        # 计算每张卡的"距离"（还需要多少个球，考虑大师球）
        card_distances = []
        for card in unaffordable_cards:
            distance = 0
            for ball_type, cost in card.cost.items():
                if ball_type != BallType.MASTER:
                    has = player.balls.get(ball_type, 0)
                    permanent = player.get_permanent_balls().get(ball_type, 0)
                    needed = max(0, cost - has - permanent)
                    distance += needed
            
            # 综合评分：距离越近越好，分数越高越好
            # 使用 (分数+1)*10 - 距离 作为评分
            score = (card.victory_points + 1) * 10 - distance
            card_distances.append((card, distance, score))
        
        # 按评分排序，选择最佳目标
        card_distances.sort(key=lambda x: x[2], reverse=True)
        
        # 返回距离最近的高分卡
        return card_distances[0][0] if card_distances else None
    
    def _calculate_needed_balls(self, player: Player, card: PokemonCard) -> List[BallType]:
        """计算购买指定卡牌还需要哪些球（按需求量排序）"""
        needed = {}
        permanent = player.get_permanent_balls()
        
        for ball_type, cost in card.cost.items():
            if ball_type != BallType.MASTER:
                has = player.balls.get(ball_type, 0)
                perm = permanent.get(ball_type, 0)
                need = max(0, cost - has - perm)
                if need > 0:
                    needed[ball_type] = need
        
        # 按需求量排序，需求多的优先
        sorted_balls = sorted(needed.items(), key=lambda x: x[1], reverse=True)
        
        # 返回球类型列表（重复次数=需求量，但最多返回前10个）
        result = []
        for ball_type, count in sorted_balls:
            result.extend([ball_type] * min(count, 3))  # 每种球最多重复3次
        
        # 去重但保持需求顺序
        seen = set()
        unique_result = []
        for ball in result:
            if ball not in seen:
                seen.add(ball)
                unique_result.append(ball)
        
        return unique_result
    
    def _find_best_card_to_reserve(self, game: SplendorPokemonGame, player: Player, favor_high_points: bool = False) -> Optional[PokemonCard]:
        """
        智能找最优预购卡 - 综合性价比算法
        
        考虑因素：
        1. 卡牌分数（victory_points）- 越高越好
        2. 球差距（ball_gap）- 还需要多少个球，越少越好
        3. 球池可得性（pool_availability）- 需要的球在球池的剩余数量，越多越好
        
        Args:
            game: 游戏实例
            player: 当前玩家
            favor_high_points: 是否更倾向高分卡（困难模式）
        
        Returns:
            最优预购卡，如果没有则返回None
        """
        all_cards = self._get_all_tableau_cards(game)
        if not all_cards:
            print(f"⚠️ {player.name}: 场上没有可预购的普通卡牌")
            print(f"   场面状态: Lv1={len(game.tableau.get(1,[]))}, Lv2={len(game.tableau.get(2,[]))}, Lv3={len(game.tableau.get(3,[]))}")
            return None
        
        best_card = None
        best_score = -float('inf')
        
        permanent_balls = player.get_permanent_balls()
        
        for card in all_cards:
            # 计算还需要多少个球（球差距）
            ball_gap = 0
            needed_balls_detail = {}  # 记录每种球需要多少
            
            for ball_type, cost in card.cost.items():
                if ball_type != BallType.MASTER:
                    has = player.balls.get(ball_type, 0)
                    perm = permanent_balls.get(ball_type, 0)
                    needed = max(0, cost - has - perm)
                    ball_gap += needed
                    if needed > 0:
                        needed_balls_detail[ball_type] = needed
            
            # 计算球池可得性（需要的球在球池的剩余数量）
            pool_availability = 0
            for ball_type, needed in needed_balls_detail.items():
                available_in_pool = game.ball_pool.get(ball_type, 0)
                # 如果球池有这种球，加分；球越多加分越高
                if available_in_pool > 0:
                    # 归一化：可用性得分 = min(needed, available) / needed
                    availability_ratio = min(needed, available_in_pool) / needed
                    pool_availability += availability_ratio
                # 如果球池没有这种球，严重扣分
                else:
                    pool_availability -= 2.0
            
            # 计算综合性价比分数
            vp_weight = 15 if favor_high_points else 10  # 分数权重
            gap_penalty = 2.0  # 球差距惩罚
            pool_bonus = 5.0  # 球池可得性奖励
            level_bonus = 1.0  # 等级奖励
            
            score = (
                vp_weight * (card.victory_points + 1) +  # +1避免0分卡被完全忽略
                level_bonus * card.level +
                pool_bonus * pool_availability -
                gap_penalty * ball_gap
            )
            
            # 特殊加成：如果球差距很小（≤3），额外加分
            if ball_gap <= 3:
                score += 8
            
            # 特殊加成：如果是进化卡，根据进化价值加分
            if hasattr(card, 'evolution') and card.evolution:
                score += 3  # 进化卡有额外价值
            
            if score > best_score:
                best_score = score
                best_card = card
        
        return best_card


# 创建不同难度的AI实例
def create_ai_player(difficulty: str = AIPlayer.MEDIUM) -> AIPlayer:
    """创建AI玩家"""
    return AIPlayer(difficulty)
