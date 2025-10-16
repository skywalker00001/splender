#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
璀璨宝石宝可梦 - Flask后端API
用于微信小程序的后端服务
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import uuid
from datetime import datetime, timedelta
import threading
import time
import sys
import os

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cuicanbaoshi import BallType, Rarity, PokemonCard, Player, SplendorPokemonGame
from ai_player import AIPlayer, create_ai_player

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 游戏房间管理
game_rooms = {}
player_to_room = {}  # 玩家名 -> 房间ID 的映射，防止一个玩家同时在多个房间
room_lock = threading.Lock()

class GameRoom:
    """游戏房间类"""
    def __init__(self, room_id, creator_name):
        self.room_id = room_id
        self.creator_name = creator_name
        self.players = [creator_name]
        self.ai_players = {}  # 存储AI玩家实例 {player_name: AIPlayer}
        self.game = None
        self.status = "waiting"  # waiting, playing, finished
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        # 游戏配置
        self.max_players = 4  # 默认4人
        self.victory_points = 18  # 默认18分胜利
        self.turn_number = 0  # 回合数
        
    def add_player(self, player_name, is_ai=False, ai_difficulty="中等"):
        """添加玩家"""
        if len(self.players) < self.max_players and player_name not in self.players:
            self.players.append(player_name)
            if is_ai:
                self.ai_players[player_name] = create_ai_player(ai_difficulty)
            return True
        return False
    
    def is_ai_player(self, player_name):
        """检查是否是AI玩家"""
        return player_name in self.ai_players
    
    def remove_player(self, player_name):
        """移除玩家"""
        if player_name in self.players:
            self.players.remove(player_name)
            # 如果是AI玩家，也从AI字典中移除
            if player_name in self.ai_players:
                del self.ai_players[player_name]
            return True
        return False
        
    def start_game(self):
        """开始游戏 - 必须达到配置的玩家数量"""
        if len(self.players) == self.max_players:
            self.game = SplendorPokemonGame(self.players, victory_points=self.victory_points)
            self.status = "playing"
            self.turn_number = 1  # 第一回合
            return True
        return False
    
    def update_config(self, max_players=None, victory_points=None):
        """更新游戏配置（仅房主可用）"""
        if max_players is not None:
            self.max_players = max(1, min(4, max_players))  # 限制在1-4人
        if victory_points is not None:
            self.victory_points = max(10, min(30, victory_points))  # 限制在10-30分
        return True
        
    def get_game_state(self):
        """获取游戏状态"""
        if not self.game:
            return {
                "status": self.status,
                "players": self.players,
                "room_id": self.room_id,
                "max_players": self.max_players,
                "victory_points": self.victory_points,
                "creator_name": self.creator_name
            }
            
        current_player = self.game.get_current_player()
        
        return {
            "status": self.status,
            "room_id": self.room_id,
            "players": self.players,
            "current_player": current_player.name,
            "game_over": self.game.game_over,
            "winner": self.game.winner.name if self.game.winner else None,
            "max_players": self.max_players,
            "victory_points": self.victory_points,
            "turn_number": self.turn_number,
            "ball_pool": {ball.value: count for ball, count in self.game.ball_pool.items()},
            "tableau": {
                str(tier): [
                    {
                        "name": card.name,
                        "level": card.level,
                        "rarity": card.rarity.value,
                        "cost": {ball.value: amount for ball, amount in card.cost.items() if amount > 0},
                        "victory_points": card.victory_points,
                        "permanent_balls": {ball.value: amount for ball, amount in card.permanent_balls.items() if amount > 0},
                        # 进化信息（仅1/2级卡牌）
                        "evolution_target": card.evolution.target_name if card.evolution else None,
                        "evolution_requirement": {ball.value: amount for ball, amount in card.evolution.required_balls.items() if amount > 0} if card.evolution else None
                    }
                    for card in cards
                ]
                for tier, cards in self.game.tableau.items()
            },
            "lv1_deck_size": len(self.game.deck_lv1),
            "lv2_deck_size": len(self.game.deck_lv2),
            "lv3_deck_size": len(self.game.deck_lv3),
            "rare_deck_size": len(self.game.rare_deck),
            "legendary_deck_size": len(self.game.legendary_deck),
            "rare_card": {
                "name": self.game.rare_card.name,
                "level": self.game.rare_card.level,
                "rarity": self.game.rare_card.rarity.value,
                "victory_points": self.game.rare_card.victory_points,
                "cost": {ball.value: amount for ball, amount in self.game.rare_card.cost.items() if amount > 0},
                "permanent_balls": {ball.value: amount for ball, amount in self.game.rare_card.permanent_balls.items() if amount > 0}
            } if self.game.rare_card else None,
            "legendary_card": {
                "name": self.game.legendary_card.name,
                "level": self.game.legendary_card.level,
                "rarity": self.game.legendary_card.rarity.value,
                "victory_points": self.game.legendary_card.victory_points,
                "cost": {ball.value: amount for ball, amount in self.game.legendary_card.cost.items() if amount > 0},
                "permanent_balls": {ball.value: amount for ball, amount in self.game.legendary_card.permanent_balls.items() if amount > 0}
            } if self.game.legendary_card else None,
            "player_states": {
                player.name: {
                    "balls": {ball.value: count for ball, count in player.balls.items() if count > 0},
                    "display_area": [
                        {
                            "name": card.name,
                            "level": card.level,
                            "rarity": card.rarity.value,
                            "victory_points": card.victory_points,
                            "permanent_balls": {ball.value: amount for ball, amount in card.permanent_balls.items() if amount > 0},
                            # 进化信息（仅1/2级卡牌）
                            "evolution_target": card.evolution.target_name if card.evolution else None,
                            "evolution_requirement": {ball.value: amount for ball, amount in card.evolution.required_balls.items() if amount > 0} if card.evolution else None
                        }
                        for card in player.display_area
                    ],
                    "reserved_cards": [
                        {
                            "name": card.name,
                            "level": card.level,
                            "cost": {ball.value: amount for ball, amount in card.cost.items() if amount > 0},
                            "victory_points": card.victory_points,
                            "permanent_balls": {ball.value: amount for ball, amount in card.permanent_balls.items() if amount > 0},
                            # 进化信息（仅1/2级卡牌）
                            "evolution_target": card.evolution.target_name if card.evolution else None,
                            "evolution_requirement": {ball.value: amount for ball, amount in card.evolution.required_balls.items() if amount > 0} if card.evolution else None
                        }
                        for card in player.reserved_cards
                    ],
                    "victory_points": player.victory_points,
                    "permanent_balls": {ball.value: count for ball, count in player.get_permanent_balls().items() if count > 0},
                    "needs_return_balls": player.needs_return_balls
                }
                for player in self.game.players
            }
        }

def cleanup_old_rooms():
    """清理过期房间"""
    while True:
        try:
            with room_lock:
                current_time = datetime.now()
                expired_rooms = []
                
                for room_id, room in game_rooms.items():
                    if current_time - room.last_activity > timedelta(hours=2):
                        expired_rooms.append(room_id)
                        
                for room_id in expired_rooms:
                    # 清除房间内所有玩家的映射
                    if room_id in game_rooms:
                        room = game_rooms[room_id]
                        for p in room.players:
                            if p in player_to_room and player_to_room[p] == room_id:
                                del player_to_room[p]
                    
                    del game_rooms[room_id]
                    print(f"清理过期房间: {room_id}")
                    
        except Exception as e:
            print(f"清理房间时出错: {e}")
            
        time.sleep(3600)  # 每小时清理一次

# 启动清理线程
cleanup_thread = threading.Thread(target=cleanup_old_rooms, daemon=True)
cleanup_thread.start()

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({"status": "ok", "message": "璀璨宝石宝可梦API服务正常"})

@app.route('/api/rooms', methods=['POST'])
def create_room():
    """创建游戏房间"""
    data = request.get_json()
    player_name = data.get('player_name')
    
    if not player_name:
        return jsonify({"error": "玩家名称不能为空"}), 400
    
    with room_lock:
        # 检查玩家是否已经在其他房间
        if player_name in player_to_room:
            old_room_id = player_to_room[player_name]
            # 检查旧房间是否还存在且未结束
            if old_room_id in game_rooms and game_rooms[old_room_id].status != "finished":
                return jsonify({
                    "error": f"您已在房间 {old_room_id} 中，请先离开当前房间",
                    "current_room": old_room_id
                }), 400
        
        room_id = str(uuid.uuid4())[:8]
        game_rooms[room_id] = GameRoom(room_id, player_name)
        player_to_room[player_name] = room_id
        
    return jsonify({
        "room_id": room_id,
        "message": "房间创建成功"
    })

@app.route('/api/rooms/<room_id>/join', methods=['POST'])
def join_room(room_id):
    """加入游戏房间"""
    data = request.get_json()
    player_name = data.get('player_name')
    
    if not player_name:
        return jsonify({"error": "玩家名称不能为空"}), 400
    
    with room_lock:
        if room_id not in game_rooms:
            return jsonify({"error": "房间不存在"}), 404
        
        # 检查玩家是否已经在其他房间
        if player_name in player_to_room:
            old_room_id = player_to_room[player_name]
            # 如果不是当前房间，且旧房间还存在且未结束
            if old_room_id != room_id and old_room_id in game_rooms and game_rooms[old_room_id].status != "finished":
                return jsonify({
                    "error": f"您已在房间 {old_room_id} 中，请先离开当前房间",
                    "current_room": old_room_id
                }), 400
        
        room = game_rooms[room_id]
        if room.status != "waiting":
            return jsonify({"error": "房间已开始游戏"}), 400
            
        if not room.add_player(player_name):
            return jsonify({"error": "无法加入房间"}), 400
        
        player_to_room[player_name] = room_id
        room.last_activity = datetime.now()
        
    return jsonify({
        "message": "成功加入房间",
        "players": room.players
    })

@app.route('/api/rooms/<room_id>/add_bot', methods=['POST'])
def add_bot(room_id):
    """添加AI机器人到房间"""
    data = request.get_json()
    difficulty = data.get('difficulty', '中等')  # 简单/中等/困难
    
    with room_lock:
        if room_id not in game_rooms:
            return jsonify({"error": "房间不存在"}), 404
            
        room = game_rooms[room_id]
        if room.status != "waiting":
            return jsonify({"error": "房间已开始游戏"}), 400
        
        if len(room.players) >= room.max_players:
            return jsonify({"error": "房间已满"}), 400
        
        # 生成AI玩家名称
        ai = create_ai_player(difficulty)
        bot_name = ai.generate_name(room.players)
        
        # 添加AI玩家
        if not room.add_player(bot_name, is_ai=True, ai_difficulty=difficulty):
            return jsonify({"error": "无法添加机器人"}), 400
            
        room.last_activity = datetime.now()
        
    return jsonify({
        "message": f"成功添加机器人: {bot_name}",
        "bot_name": bot_name,
        "players": room.players
    })

@app.route('/api/rooms/<room_id>/add_all_bots', methods=['POST'])
def add_all_bots(room_id):
    """一键添加全部机器人（补满到设置的人数）"""
    data = request.get_json()
    difficulty = data.get('difficulty', '中等')  # 简单/中等/困难
    
    with room_lock:
        if room_id not in game_rooms:
            return jsonify({"error": "房间不存在"}), 404
            
        room = game_rooms[room_id]
        if room.status != "waiting":
            return jsonify({"error": "房间已开始游戏"}), 400
        
        # 计算需要添加的机器人数量 - 使用配置的max_players
        needed = room.max_players - len(room.players)
        if needed <= 0:
            return jsonify({"error": "房间已满"}), 400
        
        added_bots = []
        for i in range(needed):
            # 生成AI玩家名称
            ai = create_ai_player(difficulty)
            bot_name = ai.generate_name(room.players)
            
            # 添加AI玩家
            if room.add_player(bot_name, is_ai=True, ai_difficulty=difficulty):
                added_bots.append(bot_name)
        
        room.last_activity = datetime.now()
        
    return jsonify({
        "message": f"成功添加 {len(added_bots)} 个机器人（补满到{room.max_players}人）",
        "added_bots": added_bots,
        "players": room.players
    })

@app.route('/api/rooms/<room_id>/kick_player', methods=['POST'])
def kick_player(room_id):
    """踢出玩家（房主专用）"""
    data = request.get_json()
    kicker_name = data.get('kicker_name')  # 发起踢人的玩家
    target_name = data.get('target_name')  # 被踢的玩家
    
    with room_lock:
        if room_id not in game_rooms:
            return jsonify({"error": "房间不存在"}), 404
            
        room = game_rooms[room_id]
        
        # 检查是否是房主
        if room.creator_name != kicker_name:
            return jsonify({"error": "只有房主可以踢出玩家"}), 403
        
        # 检查游戏状态
        if room.status != "waiting":
            return jsonify({"error": "游戏已开始，无法踢出玩家"}), 400
        
        # 不能踢自己
        if target_name == kicker_name:
            return jsonify({"error": "不能踢出自己"}), 400
        
        # 踢出玩家
        if not room.remove_player(target_name):
            return jsonify({"error": "玩家不在房间中"}), 400
        
        # 清除被踢玩家的映射
        if target_name in player_to_room and player_to_room[target_name] == room_id:
            del player_to_room[target_name]
            
        room.last_activity = datetime.now()
        
    return jsonify({
        "message": f"已踢出玩家: {target_name}",
        "players": room.players
    })

@app.route('/api/rooms/<room_id>/leave', methods=['POST'])
def leave_room(room_id):
    """离开房间"""
    data = request.get_json()
    player_name = data.get('player_name')
    
    with room_lock:
        if room_id not in game_rooms:
            return jsonify({"error": "房间不存在"}), 404
            
        room = game_rooms[room_id]
        
        # 检查游戏状态
        if room.status != "waiting":
            return jsonify({"error": "游戏已开始，无法离开"}), 400
        
        # 如果是房主离开，删除整个房间
        if room.creator_name == player_name:
            # 清除所有玩家的映射
            for p in room.players:
                if p in player_to_room and player_to_room[p] == room_id:
                    del player_to_room[p]
            del game_rooms[room_id]
            return jsonify({
                "message": "房主离开，房间已解散",
                "room_deleted": True
            })
        
        # 普通玩家离开
        if not room.remove_player(player_name):
            return jsonify({"error": "玩家不在房间中"}), 400
        
        # 清除玩家映射
        if player_name in player_to_room and player_to_room[player_name] == room_id:
            del player_to_room[player_name]
            
        room.last_activity = datetime.now()
        
    return jsonify({
        "message": "已离开房间",
        "room_deleted": False,
        "players": room.players
    })

@app.route('/api/rooms/<room_id>', methods=['DELETE'])
def delete_room(room_id):
    """删除房间（房主专用）"""
    data = request.get_json()
    player_name = data.get('player_name')
    
    with room_lock:
        if room_id not in game_rooms:
            return jsonify({"error": "房间不存在"}), 404
            
        room = game_rooms[room_id]
        
        # 检查是否是房主
        if room.creator_name != player_name:
            return jsonify({"error": "只有房主可以删除房间"}), 403
        
        # 清除所有玩家的映射
        for p in room.players:
            if p in player_to_room and player_to_room[p] == room_id:
                del player_to_room[p]
        
        # 删除房间
        del game_rooms[room_id]
        
    return jsonify({
        "message": "房间已删除"
    })

@app.route('/api/rooms/<room_id>/config', methods=['POST'])
def update_room_config(room_id):
    """更新房间配置（房主专用）"""
    data = request.get_json()
    player_name = data.get('player_name')
    max_players = data.get('max_players')
    victory_points = data.get('victory_points')
    
    with room_lock:
        if room_id not in game_rooms:
            return jsonify({"error": "房间不存在"}), 404
            
        room = game_rooms[room_id]
        
        # 检查是否是房主
        if room.creator_name != player_name:
            return jsonify({"error": "只有房主可以修改配置"}), 403
        
        # 检查游戏状态
        if room.status != "waiting":
            return jsonify({"error": "游戏已开始，无法修改配置"}), 400
        
        # 更新配置
        room.update_config(max_players=max_players, victory_points=victory_points)
        room.last_activity = datetime.now()
        
    return jsonify({
        "message": "配置更新成功",
        "max_players": room.max_players,
        "victory_points": room.victory_points
    })

@app.route('/api/rooms/<room_id>/start', methods=['POST'])
def start_game(room_id):
    """开始游戏"""
    data = request.get_json()
    player_name = data.get('player_name')
    
    with room_lock:
        if room_id not in game_rooms:
            return jsonify({"error": "房间不存在"}), 404
            
        room = game_rooms[room_id]
        if room.creator_name != player_name:
            return jsonify({"error": "只有房主可以开始游戏"}), 403
            
        if not room.start_game():
            return jsonify({"error": "玩家数量不足，无法开始游戏"}), 400
            
        room.last_activity = datetime.now()
        
    return jsonify({
        "message": "游戏开始",
        "current_player": room.game.get_current_player().name
    })

@app.route('/api/rooms/<room_id>/state', methods=['GET'])
def get_game_state(room_id):
    """获取游戏状态"""
    with room_lock:
        if room_id not in game_rooms:
            return jsonify({"error": "房间不存在"}), 404
            
        room = game_rooms[room_id]
        room.last_activity = datetime.now()
        
        # 如果游戏进行中且当前玩家是AI，触发AI回合
        if room.game and not room.game.game_over:
            current_player_name = room.game.get_current_player().name
            if room.is_ai_player(current_player_name):
                # 异步执行AI回合
                threading.Thread(target=execute_ai_turn, args=(room_id,), daemon=True).start()
        
    return jsonify(room.get_game_state())

def execute_ai_turn(room_id):
    """执行AI回合"""
    time.sleep(1)  # 延迟1秒，让玩家看到AI在"思考"
    
    with room_lock:
        if room_id not in game_rooms:
            return
            
        room = game_rooms[room_id]
        if not room.game or room.game.game_over:
            return
        
        current_player = room.game.get_current_player()
        if not room.is_ai_player(current_player.name):
            return
        
        # 获取AI实例
        ai = room.ai_players[current_player.name]
        
        # AI做决策
        decision = ai.make_decision(room.game, current_player)
        
        # 验证decision不为None
        if not decision:
            print(f"警告：AI玩家 {current_player.name} 返回了空决策，强制结束回合")
            room.game.end_turn()
            room.last_activity = datetime.now()
            return
        
        try:
            # 执行AI决策
            action = decision.get("action")
            data = decision.get("data", {})
            
            if action == "take_balls" or action == "take_gems":  # 兼容旧名称
                ball_types_str = data.get("ball_types", data.get("gem_types", []))
                
                # 验证ball_types不为空
                if not ball_types_str:
                    print(f"警告：AI玩家 {current_player.name} 尝试拿0个球，跳过此动作")
                    # 强制拿球
                    available_balls = [ball for ball, count in room.game.ball_pool.items() 
                                     if count > 0 and ball != BallType.MASTER]
                    if available_balls:
                        remained_color = len(available_balls)
                        if remained_color >= 3:
                            # 拿3个不同色
                            ball_types_str = [b.value for b in available_balls[:3]]
                        else:
                            # 拿所有可用色
                            ball_types_str = [b.value for b in available_balls]
                    else:
                        # 没有球可拿，跳过
                        print(f"警告：没有可用的球，AI跳过此回合")
                        room.game.end_turn()
                        room.last_activity = datetime.now()
                        return
                
                ball_enum_types = []
                for ball_str in ball_types_str:
                    for ball_type in BallType:
                        if ball_type.value == ball_str:
                            ball_enum_types.append(ball_type)
                            break
                room.game.take_balls(ball_enum_types)
                
            elif action == "buy_card":
                card_info = data.get("card")
                # 查找卡牌
                target_card = None
                # 先检查桌面卡牌
                for tier, cards in room.game.tableau.items():
                    for card in cards:
                        if card.name == card_info['name']:
                            target_card = card
                            break
                    if target_card:
                        break
                
                # 检查稀有/传说
                if not target_card:
                    if room.game.rare_card and room.game.rare_card.name == card_info['name']:
                        target_card = room.game.rare_card
                    elif room.game.legendary_card and room.game.legendary_card.name == card_info['name']:
                        target_card = room.game.legendary_card
                
                # 如果没找到，检查保留卡牌
                if not target_card:
                    for card in current_player.reserved_cards:
                        if card.name == card_info['name']:
                            target_card = card
                            break
                
                if target_card:
                    room.game.buy_card(target_card)
                    
            elif action == "reserve_card":
                card_info = data.get("card")
                # 查找卡牌
                target_card = None
                for tier, cards in room.game.tableau.items():
                    for card in cards:
                        if card.name == card_info['name']:
                            target_card = card
                            break
                    if target_card:
                        break
                
                if target_card:
                    room.game.reserve_card(target_card)
            
            # end_turn 包含了进化检查、球数上限检查等
            room.game.end_turn()
            
            room.last_activity = datetime.now()
            
        except Exception as e:
            print(f"AI执行回合时出错: {e}")
            import traceback
            traceback.print_exc()
            # 出错时也要结束回合，否则会卡住
            try:
                if not room.game.game_over:
                    room.game.end_turn()
            except:
                pass

@app.route('/api/rooms/<room_id>/take_gems', methods=['POST'])
def take_gems(room_id):
    """拿取球（精灵球）"""
    data = request.get_json()
    player_name = data.get('player_name')
    gem_types = data.get('gem_types', [])  # 保持兼容前端接口名
    
    with room_lock:
        if room_id not in game_rooms:
            return jsonify({"error": "房间不存在"}), 404
            
        room = game_rooms[room_id]
        if not room.game or room.game.get_current_player().name != player_name:
            return jsonify({"error": "不是你的回合"}), 400
            
        # 转换球类型
        ball_types = []
        for ball_str in gem_types:
            for ball_type in BallType:
                if ball_type.value == ball_str:
                    ball_types.append(ball_type)
                    break
                    
        if room.game.take_balls(ball_types):
            room.last_activity = datetime.now()
            return jsonify({
                "success": True,
                "message": "成功拿取球"
            })
        else:
            return jsonify({
                "success": False,
                "error": "无法拿取球"
            })

@app.route('/api/rooms/<room_id>/buy_card', methods=['POST'])
def buy_card(room_id):
    """购买卡牌"""
    data = request.get_json()
    player_name = data.get('player_name')
    card_info = data.get('card')
    
    with room_lock:
        if room_id not in game_rooms:
            return jsonify({"error": "房间不存在"}), 404
            
        room = game_rooms[room_id]
        if not room.game or room.game.get_current_player().name != player_name:
            return jsonify({"error": "不是你的回合"}), 400
            
        # 查找卡牌 (场上、稀有、传说、预定手牌)
        target_card = None
        # 检查场上卡牌
        for tier, cards in room.game.tableau.items():
            for card in cards:
                if card.name == card_info['name']:
                    target_card = card
                    break
            if target_card:
                break
        
        # 检查稀有/传说
        if not target_card:
            if room.game.rare_card and room.game.rare_card.name == card_info['name']:
                target_card = room.game.rare_card
            elif room.game.legendary_card and room.game.legendary_card.name == card_info['name']:
                target_card = room.game.legendary_card
        
        # 检查玩家手牌
        if not target_card:
            player = room.game.get_current_player()
            for card in player.reserved_cards:
                if card.name == card_info['name']:
                    target_card = card
                    break
                
        if not target_card:
            return jsonify({"error": "卡牌不存在"}), 400
            
        if room.game.buy_card(target_card):
            room.last_activity = datetime.now()
            return jsonify({
                "success": True,
                "message": "成功购买卡牌"
            })
        else:
            return jsonify({
                "success": False,
                "error": "无法购买卡牌"
            })

@app.route('/api/rooms/<room_id>/reserve_card', methods=['POST'])
def reserve_card(room_id):
    """保留卡牌（包括盲预购牌堆顶）"""
    data = request.get_json()
    player_name = data.get('player_name')
    card_info = data.get('card')
    blind = data.get('blind', False)  # 是否盲预购
    level = data.get('level')  # 盲预购时指定等级
    
    with room_lock:
        if room_id not in game_rooms:
            return jsonify({"error": "房间不存在"}), 404
            
        room = game_rooms[room_id]
        if not room.game or room.game.get_current_player().name != player_name:
            return jsonify({"error": "不是你的回合"}), 400
            
        target_card = None
        
        # 盲预购牌堆顶
        if blind and level:
            # 禁止盲预购Lv4/Lv5
            if level >= 4:
                return jsonify({"error": "稀有/传说卡牌（Lv4/Lv5）不可预购"}), 400
            
            deck_name = f"deck_lv{level}"
            deck = getattr(room.game, deck_name, [])
            if deck:
                target_card = deck.pop(0)  # 从牌堆顶移除卡牌
            else:
                return jsonify({"error": f"Lv{level}牌堆已空"}), 400
        else:
            # 查找场上卡牌
            for tier, cards in room.game.tableau.items():
                for card in cards:
                    if card.name == card_info['name']:
                        target_card = card
                        break
                if target_card:
                    break
            
            # 检查是否找到卡牌
            if not target_card:
                return jsonify({"error": "卡牌不存在"}), 400
            
            # 禁止预购Lv4/Lv5卡牌
            if target_card.level >= 4:
                return jsonify({"error": "稀有/传说卡牌（Lv4/Lv5）不可预购"}), 400
            
        if room.game.reserve_card(target_card):
            room.last_activity = datetime.now()
            return jsonify({
                "success": True,
                "message": "成功保留卡牌"
            })
        else:
            return jsonify({
                "success": False,
                "error": "无法保留卡牌"
            })

@app.route('/api/rooms/<room_id>/evolve_card', methods=['POST'])
def evolve_card(room_id):
    """进化卡牌"""
    data = request.get_json()
    player_name = data.get('player_name')
    base_card_name = data.get('card_name')
    
    with room_lock:
        if room_id not in game_rooms:
            return jsonify({"error": "房间不存在"}), 404
            
        room = game_rooms[room_id]
        if not room.game or room.game.get_current_player().name != player_name:
            return jsonify({"error": "不是你的回合"}), 400
        
        player = room.game.get_current_player()
        
        # 查找基础卡（展示区）
        base_card = None
        for card in player.display_area:
            if card.name == base_card_name:
                base_card = card
                break
        
        if not base_card:
            return jsonify({"error": "未找到要进化的卡牌"}), 400
        
        if not base_card.evolution:
            return jsonify({"error": "该卡牌无法进化"}), 400
        
        # 查找进化目标卡（场上或预购区）
        target_card = None
        target_name = base_card.evolution.target_name
        
        # 先检查场上
        for level, cards in room.game.tableau.items():
            for card in cards:
                if card.name == target_name:
                    target_card = card
                    break
            if target_card:
                break
        
        # 检查稀有/传说
        if not target_card:
            if room.game.rare_card and room.game.rare_card.name == target_name:
                target_card = room.game.rare_card
            elif room.game.legendary_card and room.game.legendary_card.name == target_name:
                target_card = room.game.legendary_card
        
        # 检查预购区
        if not target_card:
            for card in player.reserved_cards:
                if card.name == target_name:
                    target_card = card
                    break
        
        if not target_card:
            return jsonify({"error": f"未找到进化目标卡牌: {target_name}"}), 400
        
        # 执行进化
        if player.evolve(base_card, target_card):
            # 从场上或预购区移除目标卡
            for level, cards in room.game.tableau.items():
                if target_card in cards:
                    cards.remove(target_card)
                    # 补充场上卡牌
                    deck = [room.game.deck_lv1, room.game.deck_lv2, room.game.deck_lv3][level-1]
                    if deck:
                        cards.append(deck.pop())
                    break
            
            if room.game.rare_card == target_card:
                room.game.rare_card = None
                if room.game.rare_deck:
                    room.game.rare_card = room.game.rare_deck.pop()
            
            if room.game.legendary_card == target_card:
                room.game.legendary_card = None
                if room.game.legendary_deck:
                    room.game.legendary_card = room.game.legendary_deck.pop()
            
            if target_card in player.reserved_cards:
                player.reserved_cards.remove(target_card)
            
            room.last_activity = datetime.now()
            
            return jsonify({
                "success": True,
                "message": f"{base_card_name} 进化为 {target_name}！"
            })
        else:
            return jsonify({"error": "进化条件不满足"}), 400

@app.route('/api/rooms/<room_id>/return_balls', methods=['POST'])
def return_balls(room_id):
    """放回球（超过10个时）"""
    data = request.get_json()
    player_name = data.get('player_name')
    balls_to_return = data.get('balls_to_return', {})  # {球类型: 数量}
    
    with room_lock:
        if room_id not in game_rooms:
            return jsonify({"error": "房间不存在"}), 404
            
        room = game_rooms[room_id]
        if not room.game or room.game.get_current_player().name != player_name:
            return jsonify({"error": "不是你的回合"}), 400
        
        # 转换球类型
        balls_dict = {}
        for ball_str, amount in balls_to_return.items():
            for ball_type in BallType:
                if ball_type.value == ball_str:
                    balls_dict[ball_type] = amount
                    break
        
        if room.game.return_balls(balls_dict):
            room.last_activity = datetime.now()
            return jsonify({
                "success": True,
                "message": "成功放回球"
            })
        else:
            return jsonify({
                "success": False,
                "error": "放回球失败"
            })

@app.route('/api/rooms/<room_id>/end_turn', methods=['POST'])
def end_turn(room_id):
    """结束回合"""
    data = request.get_json()
    player_name = data.get('player_name')
    
    with room_lock:
        if room_id not in game_rooms:
            return jsonify({"error": "房间不存在"}), 404
            
        room = game_rooms[room_id]
        if not room.game or room.game.get_current_player().name != player_name:
            return jsonify({"error": "不是你的回合"}), 400
            
        # 记录当前玩家索引
        current_index = room.game.players.index(room.game.get_current_player())
        
        # end_turn 已经包含了进化检查、球数上限检查、胜利检查等
        room.game.end_turn()
        
        # 如果轮到下一轮（最后一个玩家结束回合），回合数+1
        if current_index == len(room.game.players) - 1:
            room.turn_number += 1
        
        # 获取下一个玩家
        if not room.game.game_over:
            next_player = room.game.get_current_player().name
        else:
            next_player = None
            
        room.last_activity = datetime.now()
        
    return jsonify({
        "success": True,
        "next_player": next_player,
        "game_over": room.game.game_over if room.game else False,
        "winner": room.game.winner.name if room.game and room.game.winner else None
    })

@app.route('/api/cards', methods=['GET'])
def get_cards():
    """获取所有卡牌数据（用于卡库展示）"""
    try:
        import csv
        import os
        
        # 读取CSV文件
        csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'card_library', 'cards_data.csv')
        cards = []
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 解析成本
                cost = {}
                for ball_color in ['黑', '粉', '黄', '蓝', '红', '大师球']:
                    key = f'购买成本_{ball_color}'
                    if key in row and row[key] and row[key].strip():
                        amount = int(row[key])
                        if amount > 0:
                            cost[ball_color] = amount
                
                # 解析永久球
                permanent = {}
                if row.get('永久球颜色') and row['永久球颜色'].strip() and row['永久球颜色'] != '无':
                    ball_color = row['永久球颜色']
                    ball_amount = int(row.get('永久球数量', 0))
                    if ball_amount > 0:
                        permanent[ball_color] = ball_amount
                
                # 解析进化信息
                evolution_target = None
                evolution_requirement = {}
                if row.get('进化后卡牌') and row['进化后卡牌'].strip() and row['进化后卡牌'] != '无':
                    evolution_target = row['进化后卡牌']
                    if row.get('进化所需球颜色') and row['进化所需球颜色'] != '无':
                        evo_color = row['进化所需球颜色']
                        evo_amount = int(row.get('进化所需球个数', 0))
                        if evo_amount > 0:
                            evolution_requirement[evo_color] = evo_amount
                
                # 确定稀有度
                level = int(row['卡牌等级'])
                if level == 4:
                    rarity = '稀有'
                elif level == 5:
                    rarity = '传说'
                else:
                    rarity = '普通'
                
                card = {
                    'name': row['卡牌名称'],
                    'level': level,
                    'rarity': rarity,
                    'victory_points': int(row['胜利点数']),
                    'cost': cost,
                    'permanent': permanent,
                    'evolution_target': evolution_target,
                    'evolution_requirement': evolution_requirement
                }
                cards.append(card)
        
        return jsonify({"success": True, "cards": cards})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/rooms', methods=['GET'])
def list_rooms():
    """获取房间列表"""
    with room_lock:
        rooms = []
        for room_id, room in game_rooms.items():
            if room.status == "waiting":
                rooms.append({
                    "room_id": room_id,
                    "creator": room.creator_name,
                    "players": room.players,
                    "player_count": len(room.players),
                    "max_players": room.max_players,
                    "created_at": room.created_at.isoformat()
                })
                
    return jsonify({"rooms": rooms})

if __name__ == '__main__':
    print("🌟 璀璨宝石宝可梦API服务启动中...")
    print("服务地址: http://localhost:5000")
    print("API文档: http://localhost:5000/api/health")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
