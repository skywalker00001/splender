#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
璀璨宝石宝可梦 - 完整规则版本
包含进化机制、稀有/传说卡、18分胜利等完整规则
"""

import csv
import os
import random
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

class BallType(Enum):
    """精灵球类型（对应原游戏中的宝石）"""
    BLACK = "黑"    # 黑色/岩地系
    PINK = "粉"     # 粉色/超能系
    YELLOW = "黄"   # 黄色/电系
    BLUE = "蓝"     # 蓝色/水系
    RED = "红"      # 红色/火系
    MASTER = "大师球"  # 万能球（只能通过预定获得）

class Rarity(Enum):
    """稀有度"""
    NORMAL = "普通"
    RARE = "稀有"
    LEGENDARY = "传说"

@dataclass
class Evolution:
    """进化信息"""
    target_name: str  # 进化目标名称
    required_balls: Dict[BallType, int]  # 需要的永久球（展示区）

@dataclass
class PokemonCard:
    """宝可梦卡牌"""
    card_id: int  # 唯一ID（1-90）
    name: str
    level: int  # 1-3 或特殊（稀有/传说）
    rarity: Rarity
    victory_points: int
    cost: Dict[BallType, int]  # 购买成本
    permanent_balls: Dict[BallType, int]  # 提供的永久球（折扣）
    evolution: Optional[Evolution] = None  # 进化信息（Lv1/Lv2可进化）
    needs_master_ball: bool = False  # 稀有/传说需要额外大师球
    
    def __str__(self):
        cost_str = ", ".join([f"{ball.value}{amount}" for ball, amount in self.cost.items() if amount > 0])
        perm_str = ", ".join([f"{ball.value}{amount}" for ball, amount in self.permanent_balls.items() if amount > 0])
        return f"{self.name} (Lv{self.level}) VP:{self.victory_points} 费用:{cost_str} 永久:{perm_str}"

class Player:
    """训练家玩家"""
    def __init__(self, name: str):
        self.name = name
        self.balls: Dict[BallType, int] = {ball: 0 for ball in BallType}
        self.display_area: List[PokemonCard] = []  # 展示区（已抓宝可梦）
        self.evolved_cards: List[PokemonCard] = []  # 被替换的进化前卡（用于平分判定）
        self.reserved_cards: List[PokemonCard] = []  # 手牌（预定的卡）
        self.victory_points = 0
        self.has_evolved_this_turn = False  # 本回合是否已进化
        self.needs_return_balls = False  # 是否需要放回球（超过10个）
        
    def get_permanent_balls(self) -> Dict[BallType, int]:
        """获取展示区永久球数量"""
        permanent = {ball: 0 for ball in BallType if ball != BallType.MASTER}
        for card in self.display_area:
            for ball, count in card.permanent_balls.items():
                if ball != BallType.MASTER:
                    permanent[ball] += count
        return permanent
    
    def get_total_balls(self) -> int:
        """获取手上球总数"""
        return sum(self.balls.values())
    
    def can_afford(self, card: PokemonCard) -> bool:
        """检查是否能购买卡牌"""
        permanent = self.get_permanent_balls()
        needed_master_balls = 0
        
        for ball, cost in card.cost.items():
            # 大师球成本直接累加
            if ball == BallType.MASTER:
                needed_master_balls += cost
                continue
            
            # 永久球提供折扣
            discount = permanent.get(ball, 0)
            actual_cost = max(0, cost - discount)
            # 需要用手上的球支付（可用大师球替代）
            if self.balls[ball] < actual_cost:
                needed_master_balls += actual_cost - self.balls[ball]
        
        return self.balls[BallType.MASTER] >= needed_master_balls
    
    def buy_card(self, card: PokemonCard, return_balls_to_pool) -> bool:
        """购买卡牌"""
        if not self.can_afford(card):
            return False
        
        permanent = self.get_permanent_balls()
        
        # 支付球
        for ball, cost in card.cost.items():
            # 大师球成本直接扣除
            if ball == BallType.MASTER:
                self.balls[BallType.MASTER] -= cost
                return_balls_to_pool(BallType.MASTER, cost)
                continue
            
            discount = permanent.get(ball, 0)
            actual_cost = max(0, cost - discount)
            
            # 先用对应颜色的球
            paid_from_ball = min(actual_cost, self.balls[ball])
            self.balls[ball] -= paid_from_ball
            return_balls_to_pool(ball, paid_from_ball)
            
            # 不够用大师球补
            remaining = actual_cost - paid_from_ball
            if remaining > 0:
                self.balls[BallType.MASTER] -= remaining
                return_balls_to_pool(BallType.MASTER, remaining)
        
        # 添加到展示区
        self.display_area.append(card)
        self.victory_points += card.victory_points
        return True
    
    def can_evolve(self, target_card: PokemonCard, base_card: PokemonCard) -> bool:
        """检查是否能进化"""
        if not base_card.evolution:
            return False
        if base_card.evolution.target_name != target_card.name:
            return False
        if self.has_evolved_this_turn:
            return False
        
        # 检查展示区永久球是否满足进化门槛
        permanent = self.get_permanent_balls()
        for ball, required in base_card.evolution.required_balls.items():
            if permanent.get(ball, 0) < required:
                return False
        return True
    
    def evolve(self, base_card: PokemonCard, target_card: PokemonCard) -> bool:
        """执行进化"""
        if not self.can_evolve(target_card, base_card):
            return False
        
        # 从展示区移除基础卡
        if base_card in self.display_area:
            self.display_area.remove(base_card)
            self.evolved_cards.append(base_card)  # 收到训练家板下
        
        # 添加进化后的卡
        self.display_area.append(target_card)
        self.victory_points = self.victory_points - base_card.victory_points + target_card.victory_points
        self.has_evolved_this_turn = True
        return True
    
    def check_ball_limit(self, return_balls_to_pool):
        """检查并处理10球上限"""
        total = self.get_total_balls()
        if total > 10:
            excess = total - 10
            print(f"{self.name} 超过10球上限，需要弃{excess}个球")
            # 简化处理：优先弃非大师球
            for ball in BallType:
                if ball != BallType.MASTER and excess > 0:
                    discard = min(self.balls[ball], excess)
                    if discard > 0:
                        self.balls[ball] -= discard
                        return_balls_to_pool(ball, discard)
                        excess -= discard

def load_cards_from_csv(csv_path: str) -> List[PokemonCard]:
    """从CSV文件加载卡牌数据
    
    CSV格式：
    卡牌名称,卡牌等级,永久球颜色,永久球数量,胜利点数,购买成本_黑,购买成本_粉,购买成本_黄,购买成本_蓝,购买成本_红,购买成本_大师球,进化后卡牌,进化所需球颜色,进化所需球个数
    """
    cards = []
    
    # 颜色到BallType的映射
    color_map = {
        '黑': BallType.BLACK,
        '粉': BallType.PINK,
        '黄': BallType.YELLOW,
        '蓝': BallType.BLUE,
        '红': BallType.RED,
    }
    
    if not os.path.exists(csv_path):
        print(f"警告：CSV文件不存在: {csv_path}")
        return cards
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 解析基础信息
                card_id = int(row['卡牌ID'])  # 读取唯一ID
                name = row['卡牌名称']
                level = int(row['卡牌等级'])
                perm_color = row['永久球颜色']
                perm_count = int(row['永久球数量'])
                victory_points = int(row['胜利点数'])
                
                # 解析购买成本
                cost = {}
                if int(row['购买成本_黑']) > 0:
                    cost[BallType.BLACK] = int(row['购买成本_黑'])
                if int(row['购买成本_粉']) > 0:
                    cost[BallType.PINK] = int(row['购买成本_粉'])
                if int(row['购买成本_黄']) > 0:
                    cost[BallType.YELLOW] = int(row['购买成本_黄'])
                if int(row['购买成本_蓝']) > 0:
                    cost[BallType.BLUE] = int(row['购买成本_蓝'])
                if int(row['购买成本_红']) > 0:
                    cost[BallType.RED] = int(row['购买成本_红'])
                if int(row['购买成本_大师球']) > 0:
                    cost[BallType.MASTER] = int(row['购买成本_大师球'])
                
                # 解析永久球
                permanent_balls = {}
                if perm_color in color_map:
                    permanent_balls[color_map[perm_color]] = perm_count
                
                # 解析进化信息
                evolution = None
                evo_target = row['进化后卡牌'].strip()
                if evo_target and evo_target != '无':
                    evo_color = row['进化所需球颜色'].strip()
                    evo_count = int(row['进化所需球个数'])
                    if evo_color in color_map and evo_count > 0:
                        evolution = Evolution(
                            target_name=evo_target,
                            required_balls={color_map[evo_color]: evo_count}
                        )
                
                # 确定稀有度
                if level <= 3:
                    rarity = Rarity.NORMAL
                elif level == 4:
                    rarity = Rarity.RARE
                else:  # level == 5
                    rarity = Rarity.LEGENDARY
                
                # 是否需要大师球（4/5级卡牌）
                needs_master_ball = (int(row['购买成本_大师球']) > 0)
                
                # 创建卡牌
                card = PokemonCard(
                    card_id=card_id,  # 唯一ID
                    name=name,
                    level=level,
                    rarity=rarity,
                    victory_points=victory_points,
                    cost=cost,
                    permanent_balls=permanent_balls,
                    evolution=evolution,
                    needs_master_ball=needs_master_ball
                )
                cards.append(card)
                
    except Exception as e:
        print(f"加载CSV文件出错: {e}")
        import traceback
        traceback.print_exc()
    
    return cards

class SplendorPokemonGame:
    """璀璨宝石宝可梦游戏"""
    
    CSV_PATH = os.path.join(os.path.dirname(__file__), 'card_library', 'cards_data.csv')
    
    def __init__(self, player_names: List[str], victory_points: int = 18):
        self.players = [Player(name) for name in player_names]
        self.current_player_index = 0
        self.game_over = False
        self.winner = None
        self.final_round_triggered = False
        self.final_round_starter = None
        self.victory_points_goal = victory_points  # 胜利目标分数
        
        # 初始化球池
        self.ball_pool = self._init_ball_pool()
        
        # 初始化卡牌
        self.deck_lv1, self.deck_lv2, self.deck_lv3 = self._init_decks()
        self.rare_deck, self.legendary_deck = self._init_special_decks()
        
        # 场面（12宫格 + 稀有 + 传说）
        self.tableau = {1: [], 2: [], 3: []}
        self.rare_card = None
        self.legendary_card = None
        
        self._setup_tableau()
    
    def _init_ball_pool(self) -> Dict[BallType, int]:
        """初始化球池"""
        num_players = len(self.players)
        color_balls = 4 if num_players == 2 else (5 if num_players == 3 else 7)
        
        pool = {}
        for ball in BallType:
            if ball == BallType.MASTER:
                pool[ball] = 5  # 大师球固定5个
            else:
                pool[ball] = color_balls
        return pool
    
    def _init_decks(self) -> Tuple[List[PokemonCard], List[PokemonCard], List[PokemonCard]]:
        """从CSV加载Lv1/Lv2/Lv3牌堆"""
        all_cards = load_cards_from_csv(self.CSV_PATH)
        
        lv1 = [card for card in all_cards if card.level == 1]
        lv2 = [card for card in all_cards if card.level == 2]
        lv3 = [card for card in all_cards if card.level == 3]
        
        random.shuffle(lv1)
        random.shuffle(lv2)
        random.shuffle(lv3)
        
        print(f"✅ 从CSV加载卡牌: Lv1={len(lv1)}张, Lv2={len(lv2)}张, Lv3={len(lv3)}张")
        return lv1, lv2, lv3
    
    def _init_special_decks(self) -> Tuple[List[PokemonCard], List[PokemonCard]]:
        """从CSV加载稀有和传说牌堆"""
        all_cards = load_cards_from_csv(self.CSV_PATH)
        
        rares = [card for card in all_cards if card.level == 4]
        legendaries = [card for card in all_cards if card.level == 5]
        
        random.shuffle(rares)
        random.shuffle(legendaries)
        
        print(f"✅ 从CSV加载特殊卡牌: 稀有={len(rares)}张, 传说={len(legendaries)}张")
        return rares, legendaries
    
    def _setup_tableau(self):
        """设置场面"""
        for level in [1, 2, 3]:
            deck = [self.deck_lv1, self.deck_lv2, self.deck_lv3][level-1]
            self.tableau[level] = [deck.pop() for _ in range(min(4, len(deck)))]
        
        if self.rare_deck:
            self.rare_card = self.rare_deck.pop()
        if self.legendary_deck:
            self.legendary_card = self.legendary_deck.pop()
    
    def get_current_player(self) -> Player:
        """获取当前玩家"""
        return self.players[self.current_player_index]
    
    def find_card_by_id(self, card_id: int, player: Player = None) -> Optional[PokemonCard]:
        """根据card_id查找卡牌
        
        Args:
            card_id: 卡牌唯一ID
            player: 如果提供，也会在该玩家的预购区查找
        
        Returns:
            找到的卡牌，如果未找到返回None
        """
        # 在场上tableau中查找
        for tier, cards in self.tableau.items():
            for card in cards:
                if card.card_id == card_id:
                    return card
        
        # 在稀有/传说卡中查找
        if self.rare_card and self.rare_card.card_id == card_id:
            return self.rare_card
        if self.legendary_card and self.legendary_card.card_id == card_id:
            return self.legendary_card
        
        # 如果提供了玩家，在预购区查找
        if player:
            for card in player.reserved_cards:
                if card.card_id == card_id:
                    return card
        
        return None
    
    def _check_ball_limit_after_action(self):
        """检查并处理10球上限"""
        player = self.get_current_player()
        
        # 如果玩家球数超过10个
        if player.get_total_balls() > 10:
            # AI玩家自动弃球
            if "机器人" in player.name:
                def return_balls_to_pool(ball_type, amount):
                    self.ball_pool[ball_type] += amount
                player.check_ball_limit(return_balls_to_pool)
                print(f"🤖 {player.name} 球数超过10个，已自动弃球")
            # 人类玩家需要手动选择放回
            else:
                player.needs_return_balls = True
                print(f"⚠️ {player.name} 球数超过10个({player.get_total_balls()})，需要手动放回{player.get_total_balls() - 10}个球")
    
    def return_balls(self, balls_to_return: Dict[BallType, int]) -> bool:
        """玩家手动放回球（超过10个时）"""
        player = self.get_current_player()
        
        # 检查是否需要放回球
        if not player.needs_return_balls:
            return False
        
        total_balls = player.get_total_balls()
        if total_balls <= 10:
            player.needs_return_balls = False
            return False
        
        # 计算需要放回的数量
        needed_return = total_balls - 10
        actual_return = sum(balls_to_return.values())
        
        # 检查放回数量是否正确
        if actual_return != needed_return:
            print(f"❌ 放回数量不正确：需要放回{needed_return}个，实际{actual_return}个")
            return False
        
        # 检查玩家是否有足够的球
        for ball_type, amount in balls_to_return.items():
            if amount > 0 and player.balls.get(ball_type, 0) < amount:
                print(f"❌ {ball_type.value}球不足：需要{amount}个，只有{player.balls.get(ball_type, 0)}个")
                return False
        
        # 执行放回
        for ball_type, amount in balls_to_return.items():
            if amount > 0:
                player.balls[ball_type] -= amount
                self.ball_pool[ball_type] += amount
                print(f"  放回 {ball_type.value} × {amount}")
        
        player.needs_return_balls = False
        print(f"✅ {player.name} 成功放回{actual_return}个球，当前球数：{player.get_total_balls()}")
        return True
    
    def take_balls(self, ball_types: List[BallType]) -> bool:
        """
        拿取球（支持完整规则）
        
        规则：
        1. 球池充足（≥3种颜色）：拿3个不同颜色 OR 拿2个同色（该颜色≥4个）
        2. 球池只剩2种颜色：
           - 有颜色≥4个：拿2个同色 OR 拿2个不同色各1个
           - 所有颜色都<4个：拿2个不同色各1个
        3. 球池只剩1种颜色：
           - ≥4个：拿2个同色
           - <4个：拿1个
        """
        player = self.get_current_player()
        
        # 计算球池中有多少种颜色可用
        available_colors = [bt for bt in BallType 
                          if bt != BallType.MASTER and self.ball_pool[bt] > 0]
        num_colors = len(available_colors)
        
        # 规则1：拿3种不同颜色（球池充足时）
        if len(ball_types) == 3:
            if len(set(ball_types)) != 3:
                return False
            for ball in ball_types:
                if ball == BallType.MASTER or self.ball_pool[ball] < 1:
                    return False
            # 执行
            for ball in ball_types:
                self.ball_pool[ball] -= 1
                player.balls[ball] += 1
            
            self._check_ball_limit_after_action()
            return True
        
        # 规则2：拿2个球
        elif len(ball_types) == 2:
            # 情况A：拿2个同色（该颜色≥4个）
            if ball_types[0] == ball_types[1]:
                ball = ball_types[0]
                if ball == BallType.MASTER or self.ball_pool[ball] < 4:
                    return False
                # 执行
                self.ball_pool[ball] -= 2
                player.balls[ball] += 2
                
                self._check_ball_limit_after_action()
                return True
            
            # 情况B：拿2个不同色各1个（球池不充足时）
            else:
                if len(set(ball_types)) != 2:
                    return False
                
                # 验证：只有当球池只剩这2种颜色时才允许
                if num_colors != 2:
                    return False
                
                # 验证：这2个球必须是仅有的2种颜色
                if set(ball_types) != set(available_colors):
                    return False
                
                # 执行
                for ball in ball_types:
                    if self.ball_pool[ball] < 1:
                        return False
                    self.ball_pool[ball] -= 1
                    player.balls[ball] += 1
                
                self._check_ball_limit_after_action()
                return True
        
        # 规则3：拿1个球（球池只剩1种颜色且<4个时）
        elif len(ball_types) == 1:
            ball = ball_types[0]
            
            # 验证：只有当球池只剩这1种颜色且<4个时才允许
            if num_colors != 1:
                return False
            if available_colors[0] != ball:
                return False
            if self.ball_pool[ball] >= 4:
                return False  # 如果≥4个，应该拿2个
            if self.ball_pool[ball] < 1:
                return False
            
            # 执行
            self.ball_pool[ball] -= 1
            player.balls[ball] += 1
            
            self._check_ball_limit_after_action()
            return True
        
        return False
    
    def reserve_card(self, card: PokemonCard) -> bool:
        """预定卡牌"""
        player = self.get_current_player()
        
        # 稀有/传说不能预定
        if card.rarity != Rarity.NORMAL:
            return False
        
        # 手牌上限3张
        if len(player.reserved_cards) >= 3:
            return False
        
        # 执行预定
        player.reserved_cards.append(card)
        # 获得1个大师球
        if self.ball_pool[BallType.MASTER] > 0:
            self.ball_pool[BallType.MASTER] -= 1
            player.balls[BallType.MASTER] += 1
        
        # 从场上移除并补充
        for level, cards in self.tableau.items():
            if card in cards:
                cards.remove(card)
                deck = [self.deck_lv1, self.deck_lv2, self.deck_lv3][level-1]
                if deck:
                    cards.append(deck.pop())
                break
        
        # 检查球数上限（预购获得大师球后可能超过10个）
        self._check_ball_limit_after_action()
        return True
    
    def buy_card(self, card: PokemonCard) -> bool:
        """抓宝可梦（购买卡牌）"""
        player = self.get_current_player()
        
        def return_balls(ball_type, amount):
            self.ball_pool[ball_type] += amount
        
        if not player.buy_card(card, return_balls):
            return False
        
        # 从场上或手牌移除
        for level, cards in self.tableau.items():
            if card in cards:
                cards.remove(card)
                deck = [self.deck_lv1, self.deck_lv2, self.deck_lv3][level-1]
                if deck:
                    cards.append(deck.pop())
                break
        
        if card in player.reserved_cards:
            player.reserved_cards.remove(card)
        
        # 稀有/传说补充
        if card == self.rare_card and self.rare_deck:
            self.rare_card = self.rare_deck.pop()
        elif card == self.legendary_card and self.legendary_deck:
            self.legendary_card = self.legendary_deck.pop()
        
        return True
    
    def check_evolution(self):
        """检查并执行进化（回合结束时）"""
        player = self.get_current_player()
        
        if player.has_evolved_this_turn:
            return
        
        # 检查展示区每张卡是否可进化
        for base_card in player.display_area[:]:  # 复制列表避免修改时出错
            if not base_card.evolution:
                continue
            
            # 查找进化目标卡（场上或手牌）
            target_card = None
            for level, cards in self.tableau.items():
                for card in cards:
                    if card.name == base_card.evolution.target_name:
                        target_card = card
                        break
                if target_card:
                    break
            
            # 也检查手牌
            if not target_card:
                for card in player.reserved_cards:
                    if card.name == base_card.evolution.target_name:
                        target_card = card
                        break
            
            if target_card and player.can_evolve(target_card, base_card):
                # 执行进化
                if player.evolve(base_card, target_card):
                    # 从场上或手牌移除进化后的卡
                    for level, cards in self.tableau.items():
                        if target_card in cards:
                            cards.remove(target_card)
                            break
                    if target_card in player.reserved_cards:
                        player.reserved_cards.remove(target_card)
                    print(f"{player.name} 进化：{base_card.name} → {target_card.name}")
                    return  # 每回合最多进化1次
    
    def end_turn(self):
        """结束回合（自动调用，不需要手动触发）
        
        流程：分数检查 → 切换玩家 → 检查游戏结束
        注意：进化检查应该在动作完成后、调用end_turn前完成
        """
        player = self.get_current_player()
        current_player_idx = self.current_player_index
        
        # 1. 优先检查是否已是最后一轮
        if self.final_round_triggered:
            # 已经是最后一轮，跳过分数检查
            pass
        else:
            # 不是最后一轮，检查当前玩家分数
            if player.victory_points >= self.victory_points_goal:
                # 首次触发胜利分数
                is_last_player = (current_player_idx == len(self.players) - 1)  # 是否是最后一个玩家
                
                if is_last_player:
                    # 最后一个玩家触发胜利分数，游戏直接结束
                    print(f"{player.name}（最后玩家）达到{player.victory_points}分，游戏结束！")
                    self.game_over = True
                    self._calculate_final_rankings()
                    return  # 直接结束，不切换玩家
                else:
                    # 非最后玩家触发胜利分数，进入最后一轮
                    self.final_round_triggered = True
                    self.final_round_starter = current_player_idx
                    print(f"{player.name} 达到{player.victory_points}分！游戏进入最后一轮")
        
        # 2. 重置回合状态
        player.has_evolved_this_turn = False
        
        # 3. 切换到下一个玩家
        self.current_player_index = (self.current_player_index + 1) % len(self.players)
        
        # 4. 检查游戏是否结束（最后一轮且回到起始玩家）
        if self.final_round_triggered:
            # 如果当前玩家回到索引0，说明最后一个玩家已经完成了回合
            if self.current_player_index == 0:  # 回到第一个玩家，说明最后一个玩家刚结束
                self.game_over = True
                self._calculate_final_rankings()
                print(f"最后一轮结束！游戏结束")
    
    def _calculate_final_rankings(self):
        """计算最终排名
        
        排序规则：
        1. 分数高的在前
        2. 同分时，玩家序号大的在前（后手优先）
        """
        # 为每个玩家记录原始索引
        players_with_index = [(i, p) for i, p in enumerate(self.players)]
        
        # 排序：分数降序，同分时索引降序
        players_with_index.sort(key=lambda x: (x[1].victory_points, x[0]), reverse=True)
        
        # 设置winner为第一名
        self.winner = players_with_index[0][1]
        
        # 打印排名
        print("\n=== 最终排名 ===")
        for rank, (original_idx, player) in enumerate(players_with_index, 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}️⃣")
            print(f"{medal} 第{rank}名：{player.name}（玩家{original_idx + 1}），{player.victory_points}分")
    
    def next_player(self):
        """切换到下一个玩家"""
        self.end_turn()

