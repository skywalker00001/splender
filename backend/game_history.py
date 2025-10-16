"""
游戏历史记录系统 - 用于保存和回放对局
"""
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path


class GameHistory:
    """游戏历史记录类"""
    
    def __init__(self, game_id: str, room_id: str, players: List[str], victory_points_goal: int):
        """
        初始化游戏历史
        
        Args:
            game_id: 游戏唯一ID（使用时间戳）
            room_id: 房间ID
            players: 玩家列表
            victory_points_goal: 胜利分数目标
        """
        self.game_id = game_id
        self.room_id = room_id
        self.players = players
        self.victory_points_goal = victory_points_goal
        self.start_time = datetime.now().isoformat()
        self.end_time = None
        self.winner = None
        
        # 回合历史记录
        self.turns: List[Dict[str, Any]] = []
        self.current_turn = 0
        
        # 初始状态快照
        self.initial_state = {}
        
    def start_turn(self, turn_number: int, current_player: str):
        """开始新回合"""
        self.current_turn = turn_number
        self.turns.append({
            "turn": turn_number,
            "player": current_player,
            "actions": [],
            "states_before": {},
            "states_after": {}
        })
    
    def record_initial_state(self, game_state: Dict[str, Any]):
        """记录游戏初始状态"""
        self.initial_state = {
            "timestamp": datetime.now().isoformat(),
            "ball_pool": game_state.get("ball_pool", {}),
            "tableau": game_state.get("tableau", {}),
            "players": game_state.get("player_states", {})
        }
    
    def record_state_before_action(self, player_name: str, player_state: Dict[str, Any], 
                                   ball_pool: Dict[str, int]):
        """记录动作前的状态"""
        if not self.turns:
            return
        
        current_turn_data = self.turns[-1]
        current_turn_data["states_before"] = {
            "player": {
                "name": player_name,
                "balls": player_state.get("balls", {}),
                "victory_points": player_state.get("victory_points", 0),
                "owned_cards_count": player_state.get("owned_cards_count", 0),
                "reserved_cards_count": player_state.get("reserved_cards_count", 0)
            },
            "ball_pool": dict(ball_pool)
        }
    
    def record_action(self, action_type: str, action_data: Dict[str, Any], 
                     result: bool, message: str = ""):
        """
        记录玩家动作
        
        Args:
            action_type: 动作类型 (take_balls, buy_card, reserve_card, return_balls, evolve)
            action_data: 动作详细数据
            result: 动作是否成功
            message: 附加消息
        """
        if not self.turns:
            return
        
        current_turn_data = self.turns[-1]
        current_turn_data["actions"].append({
            "timestamp": datetime.now().isoformat(),
            "type": action_type,
            "data": action_data,
            "result": result,
            "message": message
        })
    
    def record_state_after_action(self, player_name: str, player_state: Dict[str, Any], 
                                  ball_pool: Dict[str, int]):
        """记录动作后的状态"""
        if not self.turns:
            return
        
        current_turn_data = self.turns[-1]
        current_turn_data["states_after"] = {
            "player": {
                "name": player_name,
                "balls": player_state.get("balls", {}),
                "victory_points": player_state.get("victory_points", 0),
                "owned_cards_count": player_state.get("owned_cards_count", 0),
                "reserved_cards_count": player_state.get("reserved_cards_count", 0)
            },
            "ball_pool": dict(ball_pool)
        }
    
    def end_game(self, winner: str, final_rankings: List[Dict[str, Any]]):
        """结束游戏并记录最终结果"""
        self.end_time = datetime.now().isoformat()
        self.winner = winner
        self.final_rankings = final_rankings
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "game_id": self.game_id,
            "room_id": self.room_id,
            "players": self.players,
            "victory_points_goal": self.victory_points_goal,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "winner": self.winner,
            "total_turns": len(self.turns),
            "initial_state": self.initial_state,
            "turns": self.turns,
            "final_rankings": getattr(self, 'final_rankings', [])
        }
    
    def save_to_file(self, history_dir: str = "game_history") -> str:
        """
        保存历史记录到文件
        
        Args:
            history_dir: 历史记录目录
            
        Returns:
            保存的文件路径
        """
        # 创建历史记录目录
        history_path = Path(history_dir)
        history_path.mkdir(exist_ok=True)
        
        # 生成文件名：game_YYYYMMDD_HHMMSS_gameid.json
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"game_{timestamp}_{self.game_id}.json"
        filepath = history_path / filename
        
        # 保存为JSON
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        
        return str(filepath)
    
    @staticmethod
    def load_from_file(filepath: str) -> 'GameHistory':
        """
        从文件加载历史记录
        
        Args:
            filepath: 文件路径
            
        Returns:
            GameHistory对象
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 重建GameHistory对象
        history = GameHistory(
            game_id=data["game_id"],
            room_id=data["room_id"],
            players=data["players"],
            victory_points_goal=data["victory_points_goal"]
        )
        history.start_time = data["start_time"]
        history.end_time = data["end_time"]
        history.winner = data["winner"]
        history.turns = data["turns"]
        history.initial_state = data.get("initial_state", {})
        history.final_rankings = data.get("final_rankings", [])
        
        return history
    
    @staticmethod
    def list_all_histories(history_dir: str = "game_history") -> List[Dict[str, Any]]:
        """
        列出所有历史记录
        
        Args:
            history_dir: 历史记录目录
            
        Returns:
            历史记录摘要列表
        """
        history_path = Path(history_dir)
        if not history_path.exists():
            return []
        
        histories = []
        for filepath in sorted(history_path.glob("game_*.json"), reverse=True):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 只返回摘要信息
                histories.append({
                    "game_id": data["game_id"],
                    "room_id": data["room_id"],
                    "players": data["players"],
                    "winner": data["winner"],
                    "start_time": data["start_time"],
                    "end_time": data["end_time"],
                    "total_turns": data["total_turns"],
                    "filepath": str(filepath)
                })
            except Exception as e:
                print(f"读取历史记录文件失败 {filepath}: {e}")
                continue
        
        return histories
    
    def get_summary(self) -> Dict[str, Any]:
        """获取游戏摘要"""
        return {
            "game_id": self.game_id,
            "room_id": self.room_id,
            "players": self.players,
            "winner": self.winner,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_turns": len(self.turns),
            "duration_seconds": self._calculate_duration()
        }
    
    def _calculate_duration(self) -> Optional[int]:
        """计算游戏时长（秒）"""
        if not self.start_time or not self.end_time:
            return None
        
        try:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            return int((end - start).total_seconds())
        except:
            return None

