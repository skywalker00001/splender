/**
 * 主应用逻辑
 */

// 全局变量
let currentRoom = null;
let playerName = null;
let isCreator = false;
let roomPollingInterval = null;

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
            roomDiv.innerHTML = `
                <div class="room-item-info">
                    <strong>房间号: ${room.room_id}</strong><br>
                    <span>房主: ${room.creator} | 玩家: ${room.player_count}/4</span>
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
        
        document.getElementById('player-count').textContent = state.players.length;
        
        // 更新开始游戏按钮
        const startBtn = document.getElementById('start-game-btn');
        if (isCreator && state.players.length >= 2) {
            startBtn.disabled = false;
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
        
        stopRoomPolling();
        switchScreen('lobby-screen');
        resetGame();
    } catch (error) {
        // 即使出错也返回大厅
        console.error('离开房间失败:', error);
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



