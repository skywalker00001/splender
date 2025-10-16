/**
 * 主应用逻辑
 */

// 全局变量
let currentRoom = null;
let playerName = null;
let isCreator = false;
let roomPollingInterval = null;

// localStorage 键名
const STORAGE_KEY = 'splendor_game_session';

/**
 * 保存游戏会话到localStorage
 */
function saveGameSession(roomId, playerName) {
    const session = {
        roomId: roomId,
        playerName: playerName,
        timestamp: Date.now()
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

/**
 * 获取游戏会话
 */
function getGameSession() {
    try {
        const data = localStorage.getItem(STORAGE_KEY);
        if (!data) return null;
        
        const session = JSON.parse(data);
        const now = Date.now();
        const twoHours = 2 * 60 * 60 * 1000;
        
        // 超过2小时的会话失效
        if (now - session.timestamp > twoHours) {
            clearGameSession();
            return null;
        }
        
        return session;
    } catch (error) {
        console.error('读取游戏会话失败:', error);
        return null;
    }
}

/**
 * 清除游戏会话
 */
function clearGameSession() {
    localStorage.removeItem(STORAGE_KEY);
}

/**
 * 切换屏幕
 */
function switchScreen(screenId) {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    document.getElementById(screenId).classList.add('active');
}

/**
 * 显示提示消息
 */
function showToast(message, type = 'info') {
    // 创建新的toast元素
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('show');
    }, 10);
    
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => {
            if (toast.parentNode) {
                document.body.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

/**
 * 初始化应用
 */
async function initApp() {
    // 检查API连接
    try {
        await api.healthCheck();
        console.log('API连接正常');
    } catch (error) {
        showToast('无法连接到服务器，请检查后端服务是否启动', 'error');
        return;
    }

    // 绑定事件监听器
    bindEventListeners();
    
    // 检查是否有未完成的游戏
    await checkUnfinishedGame();
}

/**
 * 检查未完成的游戏
 */
async function checkUnfinishedGame() {
    const session = getGameSession();
    if (!session) return;
    
    try {
        // 验证房间是否还存在
        const state = await api.getGameState(session.roomId);
        
        // 房间不存在或游戏已结束
        if (!state || state.status === 'finished' || state.game_over) {
            clearGameSession();
            return;
        }
        
        // 检查玩家是否还在房间中
        if (!state.players || !state.players.includes(session.playerName)) {
            clearGameSession();
            return;
        }
        
        // 显示重连弹窗
        showReconnectModal(session, state);
        
    } catch (error) {
        // 房间不存在或出错，清除会话
        console.log('检查游戏会话失败:', error);
        clearGameSession();
    }
}

/**
 * 显示重连弹窗
 */
function showReconnectModal(session, gameState) {
    const modal = document.createElement('div');
    modal.className = 'card-action-modal';
    modal.style.zIndex = '10000';
    
    const statusText = gameState.status === 'waiting' ? '等待中' : '进行中';
    const playerCount = gameState.players?.length || 0;
    const maxPlayers = gameState.max_players || 4;
    
    modal.innerHTML = `
        <div class="modal-content" style="max-width: 450px;">
            <h3>🎮 检测到未完成的游戏</h3>
            <div style="margin: 20px 0; padding: 15px; background: rgba(0,0,0,0.3); border-radius: 8px;">
                <p style="margin: 8px 0;"><strong>房间号：</strong>${session.roomId}</p>
                <p style="margin: 8px 0;"><strong>玩家名：</strong>${session.playerName}</p>
                <p style="margin: 8px 0;"><strong>状态：</strong>${statusText}</p>
                <p style="margin: 8px 0;"><strong>玩家数：</strong>${playerCount}/${maxPlayers}</p>
            </div>
            <p style="color: #f1c40f; margin-bottom: 15px;">
                ${gameState.status === 'waiting' ? '游戏尚未开始' : '游戏正在进行中'}
            </p>
            <div class="modal-buttons">
                <button id="continue-game-btn" class="btn btn-primary">
                    ✅ 继续游戏
                </button>
                <button id="new-game-btn" class="btn btn-secondary">
                    🆕 开始新游戏
                </button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // 绑定事件
    document.getElementById('continue-game-btn').addEventListener('click', () => {
        document.body.removeChild(modal);
        reconnectToGame(session, gameState);
    });
    
    document.getElementById('new-game-btn').addEventListener('click', () => {
        document.body.removeChild(modal);
        clearGameSession();
        showToast('已清除上次游戏记录，可以开始新游戏', 'info');
    });
}

/**
 * 重连到游戏
 */
async function reconnectToGame(session, gameState) {
    currentRoom = session.roomId;
    playerName = session.playerName;
    
    if (gameState.status === 'waiting') {
        // 游戏还在等待，进入房间界面
        // 检查是否是房主
        isCreator = (gameState.creator_name === playerName);
        showRoomScreen();
        startRoomPolling();
        showToast('已重新连接到房间', 'success');
    } else if (gameState.status === 'playing') {
        // 游戏进行中，直接进入游戏界面
        switchScreen('game-screen');
        gameUI.startPolling(currentRoom, playerName);
        showToast('已重新连接到游戏', 'success');
    }
}

/**
 * 绑定事件监听器
 */
function bindEventListeners() {
    // 大厅界面
    document.getElementById('create-room-btn').addEventListener('click', handleCreateRoom);
    document.getElementById('show-rooms-btn').addEventListener('click', handleShowRooms);
    document.getElementById('refresh-rooms-btn').addEventListener('click', loadRoomsList);
    
    // 房间界面
    document.getElementById('copy-room-id-btn').addEventListener('click', handleCopyRoomId);
    document.getElementById('start-game-btn').addEventListener('click', handleStartGame);
    document.getElementById('leave-room-btn').addEventListener('click', handleLeaveRoom);
    document.getElementById('delete-room-btn').addEventListener('click', handleDeleteRoom);
    
    // AI机器人按钮
    document.getElementById('add-bot-easy-btn').addEventListener('click', () => handleAddBot('简单'));
    document.getElementById('add-bot-medium-btn').addEventListener('click', () => handleAddBot('中等'));
    document.getElementById('add-bot-hard-btn').addEventListener('click', () => handleAddBot('困难'));
    
    // 一键添加全部机器人按钮
    document.getElementById('add-all-bots-easy-btn').addEventListener('click', () => handleAddAllBots('简单'));
    document.getElementById('add-all-bots-medium-btn').addEventListener('click', () => handleAddAllBots('中等'));
    document.getElementById('add-all-bots-hard-btn').addEventListener('click', () => handleAddAllBots('困难'));
    
    // 游戏界面
    document.getElementById('clear-selection-btn').addEventListener('click', () => {
        gameUI.clearBallSelection();
    });
    document.getElementById('take-gems-btn').addEventListener('click', () => gameUI.takeBalls());
    document.getElementById('quit-game-btn').addEventListener('click', handleQuitGame);
    
    // 游戏结束界面
    document.getElementById('back-to-lobby-btn').addEventListener('click', () => {
        // 清除游戏会话
        clearGameSession();
        
        switchScreen('lobby-screen');
        resetGame();
    });

    // 回车键提交玩家名字
    document.getElementById('player-name-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleCreateRoom();
        }
    });
}

/**
 * 创建房间
 */
async function handleCreateRoom() {
    const nameInput = document.getElementById('player-name-input');
    playerName = nameInput.value.trim();
    
    if (!playerName) {
        showToast('请输入你的名字', 'error');
        return;
    }

    try {
        const result = await api.createRoom(playerName);
        currentRoom = result.room_id;
        isCreator = true;
        
        // 保存游戏会话
        saveGameSession(currentRoom, playerName);
        
        showToast('房间创建成功！', 'success');
        showRoomScreen();
        startRoomPolling();
    } catch (error) {
        showToast(`创建房间失败: ${error.message}`, 'error');
    }
}

/**
 * 显示房间列表
 */
async function handleShowRooms() {
    const nameInput = document.getElementById('player-name-input');
    playerName = nameInput.value.trim();
    
    if (!playerName) {
        showToast('请输入你的名字', 'error');
        return;
    }

    document.getElementById('rooms-list').style.display = 'block';
    await loadRoomsList();
}

/**
 * 加载房间列表
 */
async function loadRoomsList() {
    try {
        const result = await api.getRooms();
        const container = document.getElementById('rooms-container');
        container.innerHTML = '';

        if (result.rooms.length === 0) {
            container.innerHTML = '<p style="text-align: center; opacity: 0.7;">暂无可用房间</p>';
            return;
        }

        result.rooms.forEach(room => {
            const roomDiv = document.createElement('div');
            roomDiv.className = 'room-item';
            const maxPlayers = room.max_players || 4;  // 默认4人，兼容旧数据
            roomDiv.innerHTML = `
                <div class="room-item-info">
                    <strong>房间号: ${room.room_id}</strong><br>
                    <span>房主: ${room.creator} | 玩家: ${room.player_count}/${maxPlayers}</span>
                </div>
                <button class="btn btn-primary btn-small" onclick="joinRoom('${room.room_id}')">加入</button>
            `;
            container.appendChild(roomDiv);
        });
    } catch (error) {
        showToast(`加载房间列表失败: ${error.message}`, 'error');
    }
}

/**
 * 加入房间
 */
window.joinRoom = async function(roomId) {
    try {
        await api.joinRoom(roomId, playerName);
        currentRoom = roomId;
        isCreator = false;
        
        // 保存游戏会话
        saveGameSession(currentRoom, playerName);
        
        showToast('成功加入房间！', 'success');
        showRoomScreen();
        startRoomPolling();
    } catch (error) {
        showToast(`加入房间失败: ${error.message}`, 'error');
    }
}

/**
 * 显示房间界面
 */
function showRoomScreen() {
    document.getElementById('room-id-display').textContent = currentRoom;
    
    // 如果是房主，显示删除房间按钮
    const creatorControls = document.getElementById('creator-controls');
    if (isCreator) {
        creatorControls.style.display = 'block';
    } else {
        creatorControls.style.display = 'none';
    }
    
    switchScreen('room-screen');
}

/**
 * 开始房间轮询
 */
function startRoomPolling() {
    updateRoomInfo();
    
    roomPollingInterval = setInterval(() => {
        updateRoomInfo();
    }, 1000);
}

/**
 * 停止房间轮询
 */
function stopRoomPolling() {
    if (roomPollingInterval) {
        clearInterval(roomPollingInterval);
        roomPollingInterval = null;
    }
}

/**
 * 更新房间信息
 */
async function updateRoomInfo() {
    try {
        const state = await api.getGameState(currentRoom);
        
        // 更新玩家列表
        const playersList = document.getElementById('players-list');
        playersList.innerHTML = '';
        state.players.forEach((player, index) => {
            const li = document.createElement('li');
            li.className = 'player-item';
            
            // 玩家名称
            const nameSpan = document.createElement('span');
            nameSpan.textContent = player;
            if (index === 0) {
                nameSpan.textContent += ' 👑';  // 房主标记
            }
            // 机器人标记
            if (player.includes('机器人')) {
                nameSpan.textContent += ' 🤖';
            }
            li.appendChild(nameSpan);
            
            // 如果是房主，且不是自己，显示踢出按钮
            if (isCreator && player !== playerName) {
                const kickBtn = document.createElement('button');
                kickBtn.className = 'btn btn-small btn-danger';
                kickBtn.textContent = '踢出';
                kickBtn.style.marginLeft = '10px';
                kickBtn.onclick = () => handleKickPlayer(player);
                li.appendChild(kickBtn);
            }
            
            playersList.appendChild(li);
        });
        
        // 更新玩家计数显示
        const maxPlayers = state.max_players || 4;  // 后端应该总是返回，这里只是兜底
        const victoryPoints = state.victory_points || 18;  // 后端应该总是返回，这里只是兜底
        document.getElementById('player-count').textContent = `${state.players.length}/${maxPlayers}`;
        
        // 显示/隐藏配置面板（仅房主可见）
        const configPanel = document.getElementById('game-config-panel');
        const maxPlayersSelect = document.getElementById('max-players-select');
        const victoryPointsInput = document.getElementById('victory-points-input');
        
        if (isCreator) {
            configPanel.style.display = 'block';
            // 只在未被用户修改时更新（检查是否聚焦）
            if (document.activeElement !== maxPlayersSelect && document.activeElement !== victoryPointsInput) {
                maxPlayersSelect.value = maxPlayers;
                victoryPointsInput.value = victoryPoints;
            }
        } else {
            configPanel.style.display = 'none';
        }
        
        // 更新开始游戏按钮 - 必须达到设置的人数才能开始
        const startBtn = document.getElementById('start-game-btn');
        if (isCreator && state.players.length === maxPlayers) {
            startBtn.disabled = false;
        } else {
            startBtn.disabled = true;
        }
        
        // 如果游戏已经开始，切换到游戏界面
        if (state.status === 'playing') {
            stopRoomPolling();
            switchScreen('game-screen');
            gameUI.startPolling(currentRoom, playerName);
            showToast(`游戏开始！当前玩家: ${state.current_player}`, 'success');
        }
    } catch (error) {
        console.error('更新房间信息失败:', error);
        // 如果房间不存在了（可能被删除），返回大厅
        if (error.message.includes('房间不存在')) {
            showToast('房间已被解散', 'info');
            stopRoomPolling();
            switchScreen('lobby-screen');
            resetGame();
        }
    }
}

/**
 * 复制房间号
 */
function handleCopyRoomId() {
    const roomId = document.getElementById('room-id-display').textContent;
    navigator.clipboard.writeText(roomId).then(() => {
        showToast('房间号已复制到剪贴板', 'success');
    }).catch(() => {
        showToast('复制失败，请手动复制', 'error');
    });
}

/**
 * 开始游戏
 */
async function handleStartGame() {
    try {
        await api.startGame(currentRoom, playerName);
        showToast('游戏开始！', 'success');
    } catch (error) {
        showToast(`开始游戏失败: ${error.message}`, 'error');
    }
}

/**
 * 添加AI机器人
 */
async function handleAddBot(difficulty) {
    if (!currentRoom) {
        showToast('当前不在房间中', 'error');
        return;
    }

    try {
        const result = await api.addBot(currentRoom, difficulty);
        showToast(result.message, 'success');
        // 立即更新房间状态
        await updateRoomInfo();
    } catch (error) {
        showToast(`添加机器人失败: ${error.message}`, 'error');
    }
}

/**
 * 一键添加全部机器人（补满到4人）
 */
async function handleAddAllBots(difficulty) {
    if (!currentRoom) {
        showToast('当前不在房间中', 'error');
        return;
    }

    try {
        const result = await api.addAllBots(currentRoom, difficulty);
        showToast(result.message, 'success');
        // 立即更新房间状态
        await updateRoomInfo();
    } catch (error) {
        showToast(`一键添加机器人失败: ${error.message}`, 'error');
    }
}

/**
 * 踢出玩家
 */
async function handleKickPlayer(targetPlayer) {
    if (!confirm(`确定要踢出玩家 ${targetPlayer} 吗？`)) {
        return;
    }

    try {
        const result = await api.kickPlayer(currentRoom, playerName, targetPlayer);
        showToast(result.message, 'success');
        // 立即更新房间状态
        await updateRoomInfo();
    } catch (error) {
        showToast(`踢出玩家失败: ${error.message}`, 'error');
    }
}

/**
 * 离开房间
 */
async function handleLeaveRoom() {
    try {
        const result = await api.leaveRoom(currentRoom, playerName);
        showToast(result.message, 'info');
        
        // 清除游戏会话
        clearGameSession();
        
        stopRoomPolling();
        switchScreen('lobby-screen');
        resetGame();
    } catch (error) {
        // 即使出错也返回大厅
        console.error('离开房间失败:', error);
        
        // 清除游戏会话
        clearGameSession();
        
        stopRoomPolling();
        switchScreen('lobby-screen');
        resetGame();
        showToast('已离开房间', 'info');
    }
}

/**
 * 删除房间
 */
async function handleDeleteRoom() {
    if (!confirm('确定要删除房间吗？所有玩家将被移除。')) {
        return;
    }

    try {
        await api.deleteRoom(currentRoom, playerName);
        showToast('房间已删除', 'success');
        
        // 清除游戏会话
        clearGameSession();
        
        stopRoomPolling();
        switchScreen('lobby-screen');
        resetGame();
    } catch (error) {
        showToast(`删除房间失败: ${error.message}`, 'error');
    }
}

// 拿取球和结束回合已移至game.js中的gameUI对象

/**
 * 退出游戏
 */
function handleQuitGame() {
    if (confirm('确定要退出游戏吗？')) {
        // 清除游戏会话
        clearGameSession();
        
        gameUI.stopPolling();
        switchScreen('lobby-screen');
        resetGame();
        showToast('已退出游戏', 'info');
    }
}

/**
 * 重置游戏状态
 */
function resetGame() {
    currentRoom = null;
    isCreator = false;
    gameUI.clearGemSelection();
    gameUI.selectedCard = null;
    gameUI.stopPolling();
    document.getElementById('rooms-list').style.display = 'none';
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', initApp);




// 自动保存配置 - 当玩家数量或胜利分数改变时
document.getElementById('max-players-select')?.addEventListener('change', async (e) => {
    if (!currentRoom) return;
    
    const maxPlayers = parseInt(e.target.value);
    const victoryPoints = parseInt(document.getElementById('victory-points-input').value);
    
    try {
        await api.updateRoomConfig(currentRoom, playerName, maxPlayers, victoryPoints);
        showToast(`玩家数量已更新为${maxPlayers}人`, 'success');
    } catch (error) {
        showToast('更新配置失败: ' + error.message, 'error');
    }
});

document.getElementById('victory-points-input')?.addEventListener('change', async (e) => {
    if (!currentRoom) return;
    
    const maxPlayers = parseInt(document.getElementById('max-players-select').value);
    const victoryPoints = parseInt(e.target.value);
    
    // 验证范围
    if (victoryPoints < 10 || victoryPoints > 30) {
        showToast('胜利分数必须在10-30之间', 'error');
        e.target.value = 18; // 重置为默认值
        return;
    }
    
    try {
        await api.updateRoomConfig(currentRoom, playerName, maxPlayers, victoryPoints);
        showToast(`胜利分数已更新为${victoryPoints}分`, 'success');
    } catch (error) {
        showToast('更新配置失败: ' + error.message, 'error');
    }
});

