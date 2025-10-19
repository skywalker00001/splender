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

from splendor_pokemon import BallType, Rarity, PokemonCard, Player, SplendorPokemonGame
from ai_player import AIPlayer, create_ai_player
from game_history import GameHistory
from database import game_db

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 用户数据管理
class UserStatus:
    """用户状态枚举"""
    OFFLINE = "offline"      # 离线
    ONLINE = "online"        # 在线（大厅）
    IN_ROOM = "in_room"      # 在房间中
    IN_GAME = "in_game"      # 游戏中

class User:
    """用户类"""
    def __init__(self, username):
        self.username = username
        self.current_room_id = None  # 当前所在房间ID
        self.status = UserStatus.OFFLINE  # 用户状态
        self.created_at = datetime.now()
        self.last_login = datetime.now()
        self.is_online = False  # 是否在线
    
    def to_dict(self):
        return {
            "username": self.username,
            "current_room_id": self.current_room_id,
            "status": self.status,
            "is_online": self.is_online,
            "created_at": self.created_at.isoformat(),
            "last_login": self.last_login.isoformat()
        }

users = {}  # username -> User
user_lock = threading.Lock()

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
        # 历史记录
        self.history = None  # GameHistory实例
        
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
            # 随机打乱玩家顺序（座位随机化）
            import random
            random.shuffle(self.players)
            
            self.game = SplendorPokemonGame(self.players, victory_points=self.victory_points)
            self.status = "playing"
            self.turn_number = 1  # 第一回合
            
            # 初始化历史记录
            game_id = f"{self.room_id}_{int(datetime.now().timestamp())}"
            self.history = GameHistory(
                game_id=game_id,
                room_id=self.room_id,
                players=self.players.copy(),
                victory_points_goal=self.victory_points
            )
            # 记录初始状态 - 直接调用实例方法，避免死锁
            initial_state = self.get_game_state()
            self.history.record_initial_state(initial_state)
            # 开始第一回合
            current_player = self.game.get_current_player()
            self.history.start_turn(1, current_player.name)
            
            return True
        return False
    
    def record_action(self, action_type: str, action_data: dict, result: bool, message: str = ""):
        """记录游戏动作到历史"""
        if self.history and self.game:
            current_player = self.game.get_current_player()
            player_state = self._get_player_state_dict(current_player)
            ball_pool = {bt.value: count for bt, count in self.game.ball_pool.items()}
            
            # 如果是新的回合，开始新回合记录
            if action_type in ["take_balls", "buy_card", "reserve_card"] and not self.history.turns[-1].get("states_before"):
                self.history.record_state_before_action(current_player.name, player_state, ball_pool)
            
            self.history.record_action(action_type, action_data, result, message)
            
            # 记录动作后状态（在end_turn时统一记录）
    
    def record_turn_end(self):
        """记录回合结束时的状态"""
        if self.history and self.game:
            current_player = self.game.get_current_player()
            player_state = self._get_player_state_dict(current_player)
            ball_pool = {bt.value: count for bt, count in self.game.ball_pool.items()}
            
            self.history.record_state_after_action(current_player.name, player_state, ball_pool)
            
            # 开始下一回合
            if not self.game.game_over:
                self.turn_number += 1
                next_player = self.game.get_current_player()
                self.history.start_turn(self.turn_number, next_player.name)
    
    def end_game_and_save_history(self, winner: str, rankings: list) -> str:
        """结束游戏并保存历史记录，并保存到数据库"""
        if self.history:
            self.history.end_game(winner, rankings)
            filepath = self.history.save_to_file()
            print(f"✅ 游戏历史已保存到: {filepath}")
            
            # 保存到数据库（只为真人玩家，不包括AI）
            try:
                game_id = self.history.game_id
                game_start_time = self.history.start_time
                game_end_time = self.history.end_time
                total_turns = len(self.history.turns)
                
                # 为每个玩家保存参与记录
                for rank_info in rankings:
                    player_name = rank_info['player_name']
                    
                    # 跳过AI玩家（AI玩家名称通常包含"AI·"）
                    if self.is_ai_player(player_name):
                        continue
                    
                    # 保存真人玩家的参与记录
                    game_db.record_game_participation(
                        username=player_name,  # 使用玩家名作为用户名
                        game_id=game_id,
                        game_history_file=filepath,
                        player_name=player_name,
                        final_rank=rank_info['rank'],
                        final_score=rank_info['victory_points'],
                        is_winner=(player_name == winner),
                        game_start_time=game_start_time,
                        game_end_time=game_end_time,
                        total_turns=total_turns
                    )
                    print(f"  💾 玩家 {player_name} 的数据已保存到数据库")
            except Exception as e:
                print(f"⚠️ 保存到数据库时出错: {e}")
            
            return filepath
        return None
    
    def _get_player_state_dict(self, player: Player) -> dict:
        """获取玩家状态字典"""
        return {
            "balls": {bt.value: count for bt, count in player.balls.items()},
            "victory_points": player.victory_points,
            "owned_cards_count": len(player.display_area),
            "reserved_cards_count": len(player.reserved_cards)
        }
    
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
            "rankings": self.game.get_final_rankings() if self.game.game_over else None,
            "final_round": self.game.final_round_triggered,
            "max_players": self.max_players,
            "victory_points": self.victory_points,
            "turn_number": self.turn_number,
            "ball_pool": {ball.value: count for ball, count in self.game.ball_pool.items()},
            "tableau": {
                str(tier): [
                    {
                        "card_id": card.card_id,  # 唯一ID
                        "name": card.name,  # 显示名称
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
                "card_id": self.game.rare_card.card_id,  # 唯一ID
                "name": self.game.rare_card.name,
                "level": self.game.rare_card.level,
                "rarity": self.game.rare_card.rarity.value,
                "victory_points": self.game.rare_card.victory_points,
                "cost": {ball.value: amount for ball, amount in self.game.rare_card.cost.items() if amount > 0},
                "permanent_balls": {ball.value: amount for ball, amount in self.game.rare_card.permanent_balls.items() if amount > 0}
            } if self.game.rare_card else None,
            "legendary_card": {
                "card_id": self.game.legendary_card.card_id,  # 唯一ID
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
                            "card_id": card.card_id,  # 唯一ID
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
                        for card in player.display_area
                    ],
                    "reserved_cards": [
                        {
                            "card_id": card.card_id,  # 唯一ID
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
                    "needs_return_balls": player.needs_return_balls,
                    "last_action": player.last_action
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

@app.route('/api/login', methods=['POST'])
def login():
    """用户登录（不存在则创建）"""
    data = request.get_json()
    username = data.get('username', '').strip()
    force_reconnect = data.get('force_reconnect', False)  # 是否强制重连（用于页面刷新）
    
    if not username:
        return jsonify({"success": False, "error": "用户名不能为空"}), 400
    
    if len(username) > 20:
        return jsonify({"success": False, "error": "用户名不能超过20个字符"}), 400
    
    with user_lock:
        # 如果用户不存在，创建新用户
        if username not in users:
            users[username] = User(username)
            # 同时保存到数据库
            game_db.get_or_create_user(username)
            is_new_user = True
            users[username].is_online = True
            users[username].status = UserStatus.ONLINE
        else:
            # 用户已存在，检查是否可以登录
            user = users[username]
            
            # 如果用户有活跃游戏且不是强制重连，拒绝登录
            if user.current_room_id and user.current_room_id in game_rooms and not force_reconnect:
                room = game_rooms[user.current_room_id]
                if username in room.players and room.status != "finished":
                    return jsonify({
                        "success": False,
                        "error": "此玩家已登陆（游戏中）",
                        "code": "USER_IN_GAME"
                    }), 409
            
            # 允许登录
            user.is_online = True
            user.last_login = datetime.now()
            # 同时更新数据库中的最后登录时间
            game_db.get_or_create_user(username)
            is_new_user = False
        
        user = users[username]
        
        # 检查用户是否有进行中的游戏（只返回playing状态，waiting状态不算活跃游戏）
        current_room_status = None
        if user.current_room_id and user.current_room_id in game_rooms:
            room = game_rooms[user.current_room_id]
            # 检查房间状态和用户是否还在房间中
            if username in room.players and room.status != "finished":
                # 更新用户状态
                if room.status == "playing":
                    user.status = UserStatus.IN_GAME
                    # 只有游戏进行中才返回活跃游戏信息
                    current_room_status = {
                        "room_id": room.room_id,
                        "status": room.status,
                        "players": room.players,
                        "max_players": room.max_players,
                        "victory_points": room.victory_points,
                        "is_creator": (room.creator_name == username)
                    }
                else:
                    # waiting状态不算活跃游戏，不返回
                    user.status = UserStatus.IN_ROOM
            else:
                # 房间不存在或已结束，清除用户的房间记录
                user.current_room_id = None
                user.status = UserStatus.ONLINE
        else:
            # 房间不存在或已结束，清除用户的房间记录
            user.current_room_id = None
            user.status = UserStatus.ONLINE
    
    return jsonify({
        "success": True,
        "message": "登录成功" if not is_new_user else "欢迎新玩家！",
        "user": user.to_dict(),
        "is_new_user": is_new_user,
        "has_active_game": current_room_status is not None,
        "active_game": current_room_status
    })

@app.route('/api/logout', methods=['POST'])
def logout():
    """用户登出"""
    data = request.get_json()
    username = data.get('username', '').strip()
    
    if not username:
        return jsonify({"success": False, "error": "用户名不能为空"}), 400
    
    with user_lock:
        if username not in users:
            return jsonify({"success": False, "error": "用户不存在"}), 404
        
        user = users[username]
        user.is_online = False
        user.status = UserStatus.OFFLINE
    
    return jsonify({
        "success": True,
        "message": "登出成功"
    })

@app.route('/api/users/<username>/status', methods=['GET'])
def get_user_status(username):
    """获取用户当前状态"""
    with user_lock:
        if username not in users:
            return jsonify({"success": False, "error": "用户不存在"}), 404
        
        user = users[username]
        
        # 检查用户是否有进行中的游戏
        current_room_status = None
        if user.current_room_id and user.current_room_id in game_rooms:
            room = game_rooms[user.current_room_id]
            if username in room.players and room.status != "finished":
                current_room_status = {
                    "room_id": room.room_id,
                    "status": room.status,
                    "players": room.players,
                    "max_players": room.max_players,
                    "victory_points": room.victory_points,
                    "is_creator": (room.creator_name == username)
                }
    
    return jsonify({
        "success": True,
        "user": user.to_dict(),
        "has_active_game": current_room_status is not None,
        "active_game": current_room_status
    })

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
            # 检查旧房间是否还存在
            if old_room_id in game_rooms:
                old_room = game_rooms[old_room_id]
                # 只有在等待状态的房间才阻止创建
                if old_room.status == "waiting":
                    return jsonify({
                        "error": f"您已在房间 {old_room_id} 中，请先离开当前房间",
                        "current_room": old_room_id
                    }), 400
                # 如果旧房间是playing或finished状态，自动清理映射
                else:
                    print(f"ℹ️ 自动清理玩家 {player_name} 在旧房间 {old_room_id}（状态: {old_room.status}）的映射")
                    del player_to_room[player_name]
                    with user_lock:
                        if player_name in users:
                            users[player_name].current_room_id = None
            else:
                # 旧房间已不存在，清理映射
                print(f"ℹ️ 清理玩家 {player_name} 的无效房间映射: {old_room_id}")
                del player_to_room[player_name]
                with user_lock:
                    if player_name in users:
                        users[player_name].current_room_id = None
        
        room_id = str(uuid.uuid4())[:8]
        game_rooms[room_id] = GameRoom(room_id, player_name)
        player_to_room[player_name] = room_id
        
        # 更新用户的当前房间和状态
        with user_lock:
            if player_name in users:
                users[player_name].current_room_id = room_id
                users[player_name].status = UserStatus.IN_ROOM
        
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
            # 如果不是当前房间
            if old_room_id != room_id:
                # 检查旧房间是否还存在
                if old_room_id in game_rooms:
                    old_room = game_rooms[old_room_id]
                    # 只有在等待状态的房间才阻止加入
                    if old_room.status == "waiting":
                        return jsonify({
                            "error": f"您已在房间 {old_room_id} 中，请先离开当前房间",
                            "current_room": old_room_id
                        }), 400
                    # 如果旧房间是playing或finished状态，自动清理映射
                    else:
                        print(f"ℹ️ 自动清理玩家 {player_name} 在旧房间 {old_room_id}（状态: {old_room.status}）的映射")
                        del player_to_room[player_name]
                        with user_lock:
                            if player_name in users:
                                users[player_name].current_room_id = None
                else:
                    # 旧房间已不存在，清理映射
                    print(f"ℹ️ 清理玩家 {player_name} 的无效房间映射: {old_room_id}")
                    del player_to_room[player_name]
                    with user_lock:
                        if player_name in users:
                            users[player_name].current_room_id = None
        
        room = game_rooms[room_id]
        if room.status != "waiting":
            return jsonify({"error": "房间已开始游戏"}), 400
            
        if not room.add_player(player_name):
            return jsonify({"error": "无法加入房间"}), 400
        
        player_to_room[player_name] = room_id
        room.last_activity = datetime.now()
        
        # 更新用户的当前房间和状态
        with user_lock:
            if player_name in users:
                users[player_name].current_room_id = room_id
                users[player_name].status = UserStatus.IN_ROOM
        
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
    print(f"\n{'='*60}")
    print(f"🚀 收到一键补满请求")
    print(f"{'='*60}")
    
    data = request.get_json()
    difficulty = data.get('difficulty', '中等')  # 简单/中等/困难
    
    print(f"房间ID: {room_id}")
    print(f"难度: {difficulty}")
    
    with room_lock:
        if room_id not in game_rooms:
            print(f"❌ 房间不存在: {room_id}")
            return jsonify({"error": "房间不存在"}), 404
            
        room = game_rooms[room_id]
        print(f"房间信息:")
        print(f"  - 当前玩家数: {len(room.players)}")
        print(f"  - 配置玩家数: {room.max_players}")
        print(f"  - 房间状态: {room.status}")
        
        if room.status != "waiting":
            print(f"❌ 房间已开始游戏")
            return jsonify({"error": "房间已开始游戏"}), 400
        
        # 计算需要添加的机器人数量 - 使用配置的max_players
        needed = room.max_players - len(room.players)
        print(f"需要添加的机器人数量: {needed}")
        
        if needed <= 0:
            print(f"❌ 房间已满")
            return jsonify({"error": "房间已满"}), 400
        
        added_bots = []
        for i in range(needed):
            # 生成AI玩家名称
            ai = create_ai_player(difficulty)
            bot_name = ai.generate_name(room.players)
            print(f"  尝试添加机器人 {i+1}/{needed}: {bot_name}")
            
            # 添加AI玩家
            if room.add_player(bot_name, is_ai=True, ai_difficulty=difficulty):
                added_bots.append(bot_name)
                print(f"  ✅ 成功添加: {bot_name}")
            else:
                print(f"  ❌ 添加失败: {bot_name}")
        
        print(f"✅ 一键补满完成，添加了 {len(added_bots)} 个机器人")
        print(f"{'='*60}\n")
        
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
        
        # 清除被踢玩家的映射和用户的当前房间
        if target_name in player_to_room and player_to_room[target_name] == room_id:
            del player_to_room[target_name]
        with user_lock:
            if target_name in users:
                users[target_name].current_room_id = None
            
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
        
        # 等待状态：正常离开逻辑
        if room.status == "waiting":
            # 如果是房主离开，删除整个房间
            if room.creator_name == player_name:
                # 清除所有玩家的映射和用户的当前房间
                for p in room.players:
                    if p in player_to_room and player_to_room[p] == room_id:
                        del player_to_room[p]
                    with user_lock:
                        if p in users:
                            users[p].current_room_id = None
                            users[p].status = UserStatus.ONLINE
                del game_rooms[room_id]
                return jsonify({
                    "message": "房主离开，房间已解散",
                    "room_deleted": True
                })
            
            # 普通玩家离开
            if not room.remove_player(player_name):
                return jsonify({"error": "玩家不在房间中"}), 400
            
            # 清除玩家映射和用户的当前房间
            if player_name in player_to_room and player_to_room[player_name] == room_id:
                del player_to_room[player_name]
            with user_lock:
                if player_name in users:
                    users[player_name].current_room_id = None
                    users[player_name].status = UserStatus.ONLINE
                
            room.last_activity = datetime.now()
            
            return jsonify({
                "message": "已离开房间",
                "room_deleted": False,
                "players": room.players
            })
        
        # 游戏进行中或已结束：允许退出，清除玩家的房间映射
        else:
            # 如果游戏还在进行中，保存当前进度作为"未完成"的历史记录
            if room.status == "playing" and room.history and room.game and not room.game.game_over:
                try:
                    # 保存未完成的游戏历史（不包含最终排名）
                    # 先记录当前状态
                    room.history.end_time = datetime.now().isoformat()
                    room.history.winner = "游戏未完成"
                    filepath = room.history.save_to_file()
                    print(f"💾 游戏未完成，保存进度到: {filepath}")
                except Exception as e:
                    print(f"⚠️ 保存游戏进度失败: {e}")
            
            # 清除玩家映射和用户的当前房间
            if player_name in player_to_room and player_to_room[player_name] == room_id:
                del player_to_room[player_name]
            with user_lock:
                if player_name in users:
                    users[player_name].current_room_id = None
                    users[player_name].status = UserStatus.ONLINE
            
            # 注意：不从room.players中移除，保持游戏完整性
            # 只是让玩家可以创建/加入新房间
            
            return jsonify({
                "message": "已退出游戏（游戏将继续进行）",
                "room_deleted": False,
                "game_abandoned": True
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
        
        # 清除所有玩家的映射和用户的当前房间
        for p in room.players:
            if p in player_to_room and player_to_room[p] == room_id:
                del player_to_room[p]
            with user_lock:
                if p in users:
                    users[p].current_room_id = None
        
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
    print(f"\n{'='*60}")
    print(f"🎮 收到开始游戏请求")
    print(f"{'='*60}")
    
    data = request.get_json()
    player_name = data.get('player_name')
    
    print(f"房间ID: {room_id}")
    print(f"玩家名: {player_name}")
    
    with room_lock:
        if room_id not in game_rooms:
            print(f"❌ 房间不存在: {room_id}")
            return jsonify({"error": "房间不存在"}), 404
            
        room = game_rooms[room_id]
        print(f"房间信息:")
        print(f"  - 房主: {room.creator_name}")
        print(f"  - 当前玩家数: {len(room.players)}")
        print(f"  - 配置玩家数: {room.max_players}")
        print(f"  - 玩家列表: {room.players}")
        print(f"  - 房间状态: {room.status}")
        
        if room.creator_name != player_name:
            print(f"❌ 权限验证失败: {player_name} 不是房主 {room.creator_name}")
            return jsonify({"error": "只有房主可以开始游戏"}), 403
            
        print(f"✅ 权限验证通过")
        print(f"🚀 尝试开始游戏...")
        
        try:
            start_result = room.start_game()
            print(f"start_game() 返回值: {start_result}")
            
            if not start_result:
                print(f"❌ 开始游戏失败: 玩家数量({len(room.players)}) != 配置数量({room.max_players})")
                return jsonify({"error": "玩家数量不足，无法开始游戏"}), 400
            
            print(f"✅ 游戏开始成功!")
            print(f"当前玩家: {room.game.get_current_player().name}")
            print(f"{'='*60}\n")
            
            room.last_activity = datetime.now()
            
            # 更新所有玩家状态为游戏中
            with user_lock:
                for pname in room.players:
                    if pname in users and not pname.startswith('AI_'):
                        users[pname].status = UserStatus.IN_GAME
            
            return jsonify({
                "message": "游戏开始",
                "current_player": room.game.get_current_player().name
            })
        except Exception as e:
            print(f"❌❌❌ 开始游戏时发生异常:")
            print(f"异常类型: {type(e).__name__}")
            print(f"异常信息: {str(e)}")
            import traceback
            print(f"堆栈跟踪:")
            traceback.print_exc()
            print(f"{'='*60}\n")
            return jsonify({"error": f"开始游戏失败: {str(e)}"}), 500

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
            current_player.last_action = "⚠️ 无有效决策，跳过行动"
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
                
                # 记录AI行动
                ball_emoji_map = {
                    "红": "🔴",
                    "蓝": "🔵",
                    "黄": "🟡",
                    "粉": "🌸",
                    "黑": "⚫",
                    "大师球": "🟣"
                }
                from collections import Counter
                ball_counts = Counter([bt.value for bt in ball_enum_types])
                ball_desc = " ".join([f"{ball_emoji_map.get(ball, ball)}×{count}" for ball, count in ball_counts.items()])
                current_player.last_action = f"🎨 拿取球: {ball_desc}"
                
            elif action == "buy_card":
                card_info = data.get("card")
                # 使用card_id查找卡牌
                card_id = card_info.get('card_id')
                target_card = room.game.find_card_by_id(card_id, current_player)
                
                if target_card:
                    success = room.game.buy_card(target_card)
                    if success:
                        # 记录AI行动
                        current_player.last_action = f"💰 购买卡牌: {target_card.name} (Lv{target_card.level}, {target_card.victory_points}VP)"
                    else:
                        current_player.last_action = f"❌ 购买失败: {target_card.name}"
                else:
                    current_player.last_action = "❌ 购买失败: 卡牌不存在"
                    
            elif action == "reserve_card":
                card_info = data.get("card")
                # 使用card_id查找卡牌
                card_id = card_info.get('card_id')
                target_card = room.game.find_card_by_id(card_id, current_player)
                
                if target_card:
                    success = room.game.reserve_card(target_card)
                    if success:
                        # 记录AI行动
                        blind = data.get('blind', False)
                        if blind:
                            current_player.last_action = f"📦 盲预购: Lv{target_card.level}牌堆 → {target_card.name}"
                        else:
                            current_player.last_action = f"📦 预购卡牌: {target_card.name} (Lv{target_card.level})"
                    else:
                        current_player.last_action = f"❌ 预购失败: {target_card.name}"
                else:
                    current_player.last_action = "❌ 预购失败: 卡牌不存在"
            else:
                # 未知的行动类型
                current_player.last_action = f"❓ 未知行动: {action}"
            
            # 如果执行到这里last_action还是空的，说明没有执行任何行动
            if not current_player.last_action or current_player.last_action.strip() == "":
                current_player.last_action = "⚠️ 未执行任何行动"
            
            # end_turn 包含了进化检查、球数上限检查等
            room.game.end_turn()
            
            room.last_activity = datetime.now()
            
        except Exception as e:
            print(f"AI执行回合时出错: {e}")
            import traceback
            traceback.print_exc()
            # 记录错误
            current_player.last_action = f"❌ 执行出错: {str(e)[:50]}"
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
                    
        result = room.game.take_balls(ball_types)
        
        # 记录历史
        room.record_action("take_balls", {
            "ball_types": [bt.value for bt in ball_types]
        }, result, "拿取球" if result else "拿取球失败")
        
        if result:
            # 记录玩家行动描述
            ball_emoji_map = {
                "红": "🔴",
                "蓝": "🔵",
                "黄": "🟡",
                "粉": "🌸",
                "黑": "⚫",
                "大师球": "🟣"
            }
            from collections import Counter
            ball_counts = Counter([bt.value for bt in ball_types])
            ball_desc = " ".join([f"{ball_emoji_map.get(ball, ball)}×{count}" for ball, count in ball_counts.items()])
            room.game.get_current_player().last_action = f"🎨 拿取球: {ball_desc}"
            
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
            
        # 使用card_id查找卡牌
        card_id = card_info.get('card_id')
        if not card_id:
            # 兼容旧的name方式（如果前端还在使用name）
            card_name = card_info.get('name')
            if card_name:
                # 通过name查找（向后兼容）
                target_card = None
                for tier, cards in room.game.tableau.items():
                    for card in cards:
                        if card.name == card_name:
                            target_card = card
                            break
                    if target_card:
                        break
                
                if not target_card and room.game.rare_card and room.game.rare_card.name == card_name:
                    target_card = room.game.rare_card
                elif not target_card and room.game.legendary_card and room.game.legendary_card.name == card_name:
                    target_card = room.game.legendary_card
                
                if not target_card:
                    player = room.game.get_current_player()
                    for card in player.reserved_cards:
                        if card.name == card_name:
                            target_card = card
                            break
            else:
                return jsonify({"error": "缺少card_id或name"}), 400
        else:
            player = room.game.get_current_player()
            target_card = room.game.find_card_by_id(card_id, player)
                
        if not target_card:
            return jsonify({"error": "卡牌不存在"}), 400
            
        result = room.game.buy_card(target_card)
        
        # 记录历史（包含card_id用于准确回放）
        room.record_action("buy_card", {
            "card": {
                "card_id": target_card.card_id,
                "name": target_card.name,
                "level": target_card.level,
                "victory_points": target_card.victory_points
            }
        }, result, f"购买{target_card.name}" if result else "购买卡牌失败")
        
        if result:
            # 记录玩家行动描述
            player = room.game.get_current_player()
            player.last_action = f"💰 购买卡牌: {target_card.name} (Lv{target_card.level}, {target_card.victory_points}VP)"
            
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
            # 使用card_id查找卡牌
            card_id = card_info.get('card_id')
            if not card_id:
                # 兼容旧的name方式
                card_name = card_info.get('name')
                if card_name:
                    for tier, cards in room.game.tableau.items():
                        for card in cards:
                            if card.name == card_name:
                                target_card = card
                                break
                        if target_card:
                            break
                else:
                    return jsonify({"error": "缺少card_id或name"}), 400
            else:
                target_card = room.game.find_card_by_id(card_id)
            
            # 检查是否找到卡牌
            if not target_card:
                return jsonify({"error": "卡牌不存在"}), 400
            
            # 禁止预购Lv4/Lv5卡牌
            if target_card.level >= 4:
                return jsonify({"error": "稀有/传说卡牌（Lv4/Lv5）不可预购"}), 400
            
        result = room.game.reserve_card(target_card)
        
        # 记录历史（包含card_id用于准确回放）
        room.record_action("reserve_card", {
            "card": {
                "card_id": target_card.card_id,
                "name": target_card.name,
                "level": target_card.level
            },
            "blind": blind
        }, result, f"预购{target_card.name}" if result else "预购卡牌失败")
        
        if result:
            # 记录玩家行动描述
            player = room.game.get_current_player()
            if blind:
                player.last_action = f"📦 盲预购: Lv{target_card.level}牌堆 → {target_card.name}"
            else:
                player.last_action = f"📦 预购卡牌: {target_card.name} (Lv{target_card.level})"
            
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
    
    # 优先使用card_id，fallback到card_name（向后兼容）
    base_card_id = data.get('card_id')
    base_card_name = data.get('card_name')
    
    with room_lock:
        if room_id not in game_rooms:
            return jsonify({"error": "房间不存在"}), 404
            
        room = game_rooms[room_id]
        if not room.game or room.game.get_current_player().name != player_name:
            return jsonify({"error": "不是你的回合"}), 400
        
        player = room.game.get_current_player()
        
        # 查找基础卡（展示区）- 优先使用card_id
        base_card = None
        if base_card_id:
            for card in player.display_area:
                if card.card_id == base_card_id:
                    base_card = card
                    break
        elif base_card_name:
            # fallback: 使用name查找（向后兼容）
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
            # 从场上或预购区移除目标卡（在原位置补充新牌）
            for level, cards in room.game.tableau.items():
                if target_card in cards:
                    card_index = cards.index(target_card)  # 记录原位置
                    cards.remove(target_card)
                    # 补充场上卡牌
                    deck = [room.game.deck_lv1, room.game.deck_lv2, room.game.deck_lv3][level-1]
                    if deck:
                        cards.insert(card_index, deck.pop())  # 在原位置插入
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
            
            # 记录进化历史（包含card_id用于准确回放）
            room.record_action("evolve_card", {
                "base_card": {
                    "card_id": base_card.card_id,
                    "name": base_card.name,
                    "level": base_card.level
                },
                "target_card": {
                    "card_id": target_card.card_id,
                    "name": target_card.name,
                    "level": target_card.level,
                    "victory_points": target_card.victory_points
                }
            }, True, f"{base_card.name} 进化为 {target_card.name}")
            
            # 记录玩家行动描述 - 注意：进化是行动之外的额外步骤，这里记录但前端会在进化通知中单独展示
            # 这个记录主要用于后续回顾
            # 使用 ║ 作为步骤分隔符，避免与进化内部的 → 冲突
            player.last_action += f" ║ ⚡ 进化: {base_card.name} → {target_card.name}"
            
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
            # 记录历史
            room.record_action("return_balls", {
                "balls_returned": {ball.value: amount for ball, amount in balls_dict.items()}
            }, True, f"放回{sum(balls_dict.values())}个球")
            
            # 记录玩家行动描述
            ball_emoji_map = {
                "红": "🔴",
                "蓝": "🔵",
                "黄": "🟡",
                "粉": "🌸",
                "黑": "⚫",
                "大师球": "🟣"
            }
            ball_desc = " ".join([f"{ball_emoji_map.get(ball.value, ball.value)}×{amount}" 
                                 for ball, amount in balls_dict.items() if amount > 0])
            player = room.game.get_current_player()
            # 使用 ║ 作为步骤分隔符
            player.last_action += f" ║ ↩️ 放回球: {ball_desc}"
            
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
        
        # 记录回合结束状态
        room.record_turn_end()
        
        # 如果轮到下一轮（最后一个玩家结束回合），回合数+1
        # (已在record_turn_end中处理)
        
        # 获取下一个玩家
        if not room.game.game_over:
            next_player = room.game.get_current_player().name
            # 清空新玩家的上一次行动记录，为新行动做准备
            room.game.get_current_player().last_action = ""
        else:
            next_player = None
            # 游戏结束，保存历史
            if room.history:
                rankings = room.game.get_final_rankings()
                room.end_game_and_save_history(
                    winner=room.game.winner.name,
                    rankings=rankings
                )
            
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

# =======================
# 历史记录API
# =======================

@app.route('/api/history/list', methods=['GET'])
def list_game_histories():
    """获取所有历史记录列表"""
    try:
        histories = GameHistory.list_all_histories()
        return jsonify({
            "success": True,
            "histories": histories
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/history/<game_id>', methods=['GET'])
def get_game_history(game_id):
    """获取指定游戏的详细历史记录"""
    try:
        # 查找对应的历史文件
        histories = GameHistory.list_all_histories()
        target_file = None
        for history in histories:
            if history['game_id'] == game_id:
                target_file = history['filepath']
                break
        
        if not target_file:
            return jsonify({
                "success": False,
                "error": "历史记录不存在"
            }), 404
        
        # 加载完整历史
        history = GameHistory.load_from_file(target_file)
        return jsonify({
            "success": True,
            "history": history.to_dict()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/history/<game_id>/turn/<int:turn_number>', methods=['GET'])
def get_game_history_turn(game_id, turn_number):
    """获取指定游戏的某一回合详细信息"""
    try:
        histories = GameHistory.list_all_histories()
        target_file = None
        for history in histories:
            if history['game_id'] == game_id:
                target_file = history['filepath']
                break
        
        if not target_file:
            return jsonify({
                "success": False,
                "error": "历史记录不存在"
            }), 404
        
        history = GameHistory.load_from_file(target_file)
        
        # 查找指定回合
        turn_data = None
        for turn in history.turns:
            if turn['turn'] == turn_number:
                turn_data = turn
                break
        
        if not turn_data:
            return jsonify({
                "success": False,
                "error": f"回合{turn_number}不存在"
            }), 404
        
        return jsonify({
            "success": True,
            "turn": turn_data
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ============ 用户数据库API ============

@app.route('/api/users/<username>', methods=['GET'])
def get_user_info(username):
    """获取用户信息和统计数据"""
    try:
        user = game_db.get_user_by_username(username)
        if not user:
            return jsonify({
                "success": False,
                "error": "用户不存在"
            }), 404
        
        # 获取统计信息
        stats = game_db.get_user_statistics(username)
        
        return jsonify({
            "success": True,
            "user": {
                "username": user['username'],
                "created_at": user['created_at'],
                "last_login": user['last_login'],
                "total_games": user['total_games'],
                "total_wins": user['total_wins'],
                "total_points": user['total_points']
            },
            "statistics": stats
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/users/<username>/games', methods=['GET'])
def get_user_games(username):
    """获取用户的游戏历史列表"""
    try:
        # 获取分页参数
        limit = request.args.get('limit', 20, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # 获取游戏历史
        games = game_db.get_user_game_history(username, limit=limit, offset=offset)
        
        return jsonify({
            "success": True,
            "total": len(games),
            "games": games
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/users/<username>/statistics', methods=['GET'])
def get_user_statistics_api(username):
    """获取用户详细统计信息"""
    try:
        stats = game_db.get_user_statistics(username)
        if not stats:
            return jsonify({
                "success": False,
                "error": "用户不存在"
            }), 404
        
        return jsonify({
            "success": True,
            "statistics": stats
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/games/<game_id>/details', methods=['GET'])
def get_game_details(game_id):
    """获取游戏详细信息（包括所有参与玩家）"""
    try:
        details = game_db.get_game_details(game_id)
        if not details:
            return jsonify({
                "success": False,
                "error": "游戏不存在"
            }), 404
        
        return jsonify({
            "success": True,
            "game": details
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/users/login', methods=['POST'])
def user_login():
    """用户登录（如果不存在则自动创建）"""
    try:
        data = request.get_json()
        username = data.get('username')
        
        if not username:
            return jsonify({
                "success": False,
                "error": "用户名不能为空"
            }), 400
        
        # 获取或创建用户
        user = game_db.get_or_create_user(username)
        
        return jsonify({
            "success": True,
            "user": {
                "username": user['username'],
                "created_at": user['created_at'],
                "last_login": user['last_login'],
                "total_games": user['total_games'],
                "total_wins": user['total_wins'],
                "total_points": user['total_points']
            },
            "message": "登录成功" if user['total_games'] > 0 else "欢迎新玩家！"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# =======================
# 调试API
# =======================

@app.route('/api/rooms/<room_id>/debug/adjust_balls', methods=['POST'])
def debug_adjust_balls(room_id):
    """调整玩家持有球（调试用）"""
    data = request.get_json()
    player_name = data.get('player_name')
    ball_type_str = data.get('ball_type')
    delta = data.get('delta', 0)
    
    with room_lock:
        if room_id not in game_rooms:
            return jsonify({"error": "房间不存在"}), 404
        
        room = game_rooms[room_id]
        if not room.game:
            return jsonify({"error": "游戏未开始"}), 400
        
        # 找到玩家
        player = None
        for p in room.game.players:
            if p.name == player_name:
                player = p
                break
        
        if not player:
            return jsonify({"error": "玩家不存在"}), 404
        
        # 转换球类型
        ball_type = None
        for bt in BallType:
            if bt.value == ball_type_str:
                ball_type = bt
                break
        
        if not ball_type:
            return jsonify({"error": "球类型无效"}), 400
        
        # 调整球数（从球池拿或放回球池）
        new_count = max(0, player.balls.get(ball_type, 0) + delta)
        old_count = player.balls.get(ball_type, 0)
        actual_delta = new_count - old_count
        
        player.balls[ball_type] = new_count
        
        # 更新球池（如果增加球，从球池拿；如果减少球，放回球池）
        if actual_delta > 0:
            room.game.ball_pool[ball_type] = max(0, room.game.ball_pool[ball_type] - actual_delta)
        else:
            room.game.ball_pool[ball_type] += abs(actual_delta)
        
        room.last_activity = datetime.now()
        
        return jsonify({
            "success": True,
            "message": f"已调整{ball_type_str}: {old_count} → {new_count}",
            "new_count": new_count
        })

@app.route('/api/rooms/<room_id>/debug/adjust_permanent_balls', methods=['POST'])
def debug_adjust_permanent_balls(room_id):
    """调整玩家永久折扣（调试用）
    注意：这个不会真的添加卡牌，只是直接修改永久折扣数值
    """
    data = request.get_json()
    player_name = data.get('player_name')
    ball_type_str = data.get('ball_type')
    delta = data.get('delta', 0)
    
    with room_lock:
        if room_id not in game_rooms:
            return jsonify({"error": "房间不存在"}), 404
        
        room = game_rooms[room_id]
        if not room.game:
            return jsonify({"error": "游戏未开始"}), 400
        
        # 找到玩家
        player = None
        for p in room.game.players:
            if p.name == player_name:
                player = p
                break
        
        if not player:
            return jsonify({"error": "玩家不存在"}), 404
        
        # 转换球类型
        ball_type = None
        for bt in BallType:
            if bt.value == ball_type_str:
                ball_type = bt
                break
        
        if not ball_type or ball_type == BallType.MASTER:
            return jsonify({"error": "球类型无效（永久折扣不包括大师球）"}), 400
        
        # 创建一个虚拟卡牌来提供永久折扣
        # 实际上直接在已有的卡牌上修改会更合理，但为了简化，我们添加一个隐形卡牌
        if delta > 0:
            # 添加虚拟卡牌
            from copy import deepcopy
            virtual_card = PokemonCard(
                card_id=9999,  # 使用特殊ID
                name=f"调试折扣({ball_type_str})",
                level=1,
                rarity=Rarity.NORMAL,
                victory_points=0,
                cost={},
                permanent_balls={ball_type: abs(delta)}
            )
            player.display_area.append(virtual_card)
        else:
            # 减少折扣：移除虚拟卡牌
            for card in player.display_area[:]:
                if card.card_id == 9999 and ball_type in card.permanent_balls:
                    if card.permanent_balls[ball_type] <= abs(delta):
                        player.display_area.remove(card)
                        break
                    else:
                        card.permanent_balls[ball_type] -= abs(delta)
                        break
        
        # 重新计算永久折扣
        permanent = player.get_permanent_balls()
        
        room.last_activity = datetime.now()
        
        return jsonify({
            "success": True,
            "message": f"已调整{ball_type_str}永久折扣",
            "new_count": permanent.get(ball_type, 0)
        })

@app.route('/api/rooms/<room_id>/debug/add_card', methods=['POST'])
def debug_add_card(room_id):
    """从场上添加卡牌到玩家（调试用）"""
    data = request.get_json()
    player_name = data.get('player_name')
    card_id = data.get('card_id')
    card_type = data.get('card_type')  # 'owned' or 'reserved'
    source = data.get('source')  # 'tableau'
    
    with room_lock:
        if room_id not in game_rooms:
            return jsonify({"error": "房间不存在"}), 404
        
        room = game_rooms[room_id]
        if not room.game:
            return jsonify({"error": "游戏未开始"}), 400
        
        # 找到玩家
        player = None
        for p in room.game.players:
            if p.name == player_name:
                player = p
                break
        
        if not player:
            return jsonify({"error": "玩家不存在"}), 404
        
        # 找到卡牌
        target_card = room.game.find_card_by_id(card_id, player)
        
        if not target_card:
            return jsonify({"error": "卡牌不存在"}), 404
        
        # 复制卡牌（避免引用问题）
        from copy import deepcopy
        card_copy = deepcopy(target_card)
        
        # 添加到玩家
        if card_type == 'owned':
            player.display_area.append(card_copy)
            player.victory_points += card_copy.victory_points
        else:  # reserved
            if len(player.reserved_cards) >= 3:
                return jsonify({"error": "预定卡牌已满（最多3张）"}), 400
            player.reserved_cards.append(card_copy)
        
        # 从场上移除并补充（在原位置补充新牌）
        removed = False
        for level, cards in room.game.tableau.items():
            if target_card in cards:
                card_index = cards.index(target_card)  # 记录原位置
                cards.remove(target_card)
                # 补充卡牌
                deck = [room.game.deck_lv1, room.game.deck_lv2, room.game.deck_lv3][level-1]
                if deck:
                    cards.insert(card_index, deck.pop())  # 在原位置插入
                removed = True
                break
        
        # 检查稀有/传说卡
        if not removed:
            if room.game.rare_card == target_card:
                if room.game.rare_deck:
                    room.game.rare_card = room.game.rare_deck.pop()
                else:
                    room.game.rare_card = None
                removed = True
            elif room.game.legendary_card == target_card:
                if room.game.legendary_deck:
                    room.game.legendary_card = room.game.legendary_deck.pop()
                else:
                    room.game.legendary_card = None
                removed = True
        
        room.last_activity = datetime.now()
        
        return jsonify({
            "success": True,
            "message": f"已添加卡牌: {card_copy.name}",
            "card_name": card_copy.name
        })

@app.route('/api/rooms/<room_id>/debug/add_card_from_deck', methods=['POST'])
def debug_add_card_from_deck(room_id):
    """从牌堆添加卡牌到玩家（调试用）"""
    data = request.get_json()
    player_name = data.get('player_name')
    level = data.get('level')
    card_type = data.get('card_type')  # 'owned' or 'reserved'
    
    with room_lock:
        if room_id not in game_rooms:
            return jsonify({"error": "房间不存在"}), 404
        
        room = game_rooms[room_id]
        if not room.game:
            return jsonify({"error": "游戏未开始"}), 400
        
        # 找到玩家
        player = None
        for p in room.game.players:
            if p.name == player_name:
                player = p
                break
        
        if not player:
            return jsonify({"error": "玩家不存在"}), 404
        
        # 获取对应等级的牌堆
        if level == 1:
            deck = room.game.deck_lv1
        elif level == 2:
            deck = room.game.deck_lv2
        elif level == 3:
            deck = room.game.deck_lv3
        else:
            return jsonify({"error": "等级无效"}), 400
        
        if not deck:
            return jsonify({"error": f"Lv{level}牌堆已空"}), 400
        
        # 从牌堆顶抽取卡牌
        from copy import deepcopy
        card = deepcopy(deck.pop(0))
        
        # 添加到玩家
        if card_type == 'owned':
            player.display_area.append(card)
            player.victory_points += card.victory_points
        else:  # reserved
            if len(player.reserved_cards) >= 3:
                # 放回牌堆
                deck.insert(0, card)
                return jsonify({"error": "预定卡牌已满（最多3张）"}), 400
            player.reserved_cards.append(card)
        
        room.last_activity = datetime.now()
        
        return jsonify({
            "success": True,
            "message": f"已从Lv{level}牌堆添加: {card.name}",
            "card_name": card.name
        })


def load_users_from_database():
    """从数据库加载所有用户到内存"""
    print("📚 正在从数据库加载用户...")
    try:
        # 获取数据库中的所有用户
        conn = game_db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT username, created_at, last_login FROM users')
        db_users = cursor.fetchall()
        conn.close()
        
        # 加载到内存
        with user_lock:
            for row in db_users:
                username = row['username']
                if username not in users:
                    user = User(username)
                    # 恢复时间戳
                    user.created_at = datetime.fromisoformat(row['created_at'])
                    user.last_login = datetime.fromisoformat(row['last_login'])
                    users[username] = user
        
        print(f"✅ 成功加载 {len(db_users)} 个用户")
    except Exception as e:
        print(f"⚠️  加载用户时出错: {e}")

if __name__ == '__main__':
    print("🌟 璀璨宝石宝可梦API服务启动中...")
    
    # 从数据库加载用户
    load_users_from_database()
    
    print("服务地址: http://localhost:5000")
    print("API文档: http://localhost:5000/api/health")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
