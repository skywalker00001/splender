/**
 * API请求封装
 */

// 配置API基础URL - 根据你的服务器配置修改
const API_BASE_URL = window.location.origin + '/api';

class SplendorAPI {
    constructor() {
        this.baseURL = API_BASE_URL;
    }

    /**
     * 发送HTTP请求
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(url, config);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || '请求失败');
            }
            
            return data;
        } catch (error) {
            console.error('API请求错误:', error);
            throw error;
        }
    }

    /**
     * 健康检查
     */
    async healthCheck() {
        return this.request('/health');
    }

    /**
     * 创建房间
     */
    async createRoom(playerName) {
        return this.request('/rooms', {
            method: 'POST',
            body: JSON.stringify({ player_name: playerName })
        });
    }

    /**
     * 获取房间列表
     */
    async getRooms() {
        return this.request('/rooms');
    }

    /**
     * 加入房间
     */
    async joinRoom(roomId, playerName) {
        return this.request(`/rooms/${roomId}/join`, {
            method: 'POST',
            body: JSON.stringify({ player_name: playerName })
        });
    }

    /**
     * 添加机器人
     */
    async addBot(roomId, difficulty = '中等') {
        return this.request(`/rooms/${roomId}/add_bot`, {
            method: 'POST',
            body: JSON.stringify({ difficulty: difficulty })
        });
    }

    /**
     * 一键添加全部机器人（补满到4人）
     */
    async addAllBots(roomId, difficulty = '中等') {
        return this.request(`/rooms/${roomId}/add_all_bots`, {
            method: 'POST',
            body: JSON.stringify({ difficulty: difficulty })
        });
    }

    /**
     * 踢出玩家
     */
    async kickPlayer(roomId, kickerName, targetName) {
        return this.request(`/rooms/${roomId}/kick_player`, {
            method: 'POST',
            body: JSON.stringify({ 
                kicker_name: kickerName,
                target_name: targetName
            })
        });
    }

    /**
     * 离开房间
     */
    async leaveRoom(roomId, playerName) {
        return this.request(`/rooms/${roomId}/leave`, {
            method: 'POST',
            body: JSON.stringify({ player_name: playerName })
        });
    }

    /**
     * 删除房间
     */
    async deleteRoom(roomId, playerName) {
        return this.request(`/rooms/${roomId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ player_name: playerName })
        });
    }

    /**
     * 更新房间配置
     */
    async updateRoomConfig(roomId, playerName, maxPlayers, victoryPoints) {
        return this.request(`/rooms/${roomId}/config`, {
            method: 'POST',
            body: JSON.stringify({
                player_name: playerName,
                max_players: maxPlayers,
                victory_points: victoryPoints
            })
        });
    }

    /**
     * 开始游戏
     */
    async startGame(roomId, playerName) {
        return this.request(`/rooms/${roomId}/start`, {
            method: 'POST',
            body: JSON.stringify({ player_name: playerName })
        });
    }

    /**
     * 获取游戏状态
     */
    async getGameState(roomId) {
        return this.request(`/rooms/${roomId}/state`);
    }

    /**
     * 拿取精灵球
     */
    async takeGems(roomId, playerName, gemTypes) {
        return this.request(`/rooms/${roomId}/take_gems`, {
            method: 'POST',
            body: JSON.stringify({
                player_name: playerName,
                gem_types: gemTypes
            })
        });
    }

    /**
     * 购买卡牌
     */
    async buyCard(roomId, playerName, card) {
        return this.request(`/rooms/${roomId}/buy_card`, {
            method: 'POST',
            body: JSON.stringify({
                player_name: playerName,
                card: card
            })
        });
    }

    /**
     * 保留卡牌（支持普通预购和盲预购）
     */
    async reserveCard(roomId, playerName, cardOrData) {
        // 如果是盲预购，cardOrData包含 {blind: true, level: X}
        // 如果是普通预购，cardOrData是卡牌对象 {name: "..."}
        const requestBody = {
            player_name: playerName,
            ...cardOrData
        };
        
        return this.request(`/rooms/${roomId}/reserve_card`, {
            method: 'POST',
            body: JSON.stringify(requestBody)
        });
    }

    /**
     * 进化卡牌
     */
    async evolveCard(roomId, data) {
        return this.request(`/rooms/${roomId}/evolve_card`, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    /**
     * 放回球（超过10个时）
     */
    async returnBalls(roomId, playerName, ballsToReturn) {
        return this.request(`/rooms/${roomId}/return_balls`, {
            method: 'POST',
            body: JSON.stringify({
                player_name: playerName,
                balls_to_return: ballsToReturn
            })
        });
    }

    /**
     * 结束行动
     */
    async endTurn(roomId, playerName) {
        return this.request(`/rooms/${roomId}/end_turn`, {
            method: 'POST',
            body: JSON.stringify({ player_name: playerName })
        });
    }
}

// 创建全局API实例
const api = new SplendorAPI();



