/**
 * 主应用逻辑
 */

// 检查用户是否已登录
function checkLoginStatus() {
    const currentPlayerName = sessionStorage.getItem('currentPlayerName');
    if (!currentPlayerName) {
        // 未登录，跳转到登录页面
        window.location.href = '/login.html';
        return false;
    }
    return true;
}

// 页面加载时检查登录状态
if (!checkLoginStatus()) {
    // 如果未登录，停止执行后续代码
    throw new Error('Please login first');
}

// 全局变量
let currentRoom = null;
let playerName = null;
let isCreator = false;
let roomPollingInterval = null;
let userActiveGame = null;  // 用户的活跃游戏信息

// 房间列表分页状态
let allRooms = [];  // 所有房间
let filteredRooms = [];  // 过滤后的房间
let currentPage = 1;
const ROOMS_PER_PAGE = 10;

// sessionStorage 键名（每个标签页独立，支持多开）
const STORAGE_KEY = 'splendor_game_session';

/**
 * 保存游戏会话到sessionStorage
 */
function saveGameSession(roomId, playerName) {
    const session = {
        roomId: roomId,
        playerName: playerName,
        timestamp: Date.now()
    };
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

/**
 * 获取游戏会话
 */
function getGameSession() {
    try {
        const data = sessionStorage.getItem(STORAGE_KEY);
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
    sessionStorage.removeItem(STORAGE_KEY);
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
    
    // 检查localStorage中是否有保存的用户名
    const savedUsername = localStorage.getItem('splendor_username');
    if (savedUsername) {
        // 尝试自动登录（重连）
        try {
            const result = await api.login(savedUsername, true);  // force_reconnect = true
            if (result.success) {
                await handleLoginSuccess(result);
                return;
            }
        } catch (error) {
            console.log('自动重连失败:', error);
            // 清除无效的用户名
            localStorage.removeItem('splendor_username');
        }
    }
    
    // 显示登录界面
    switchScreen('login-screen');
}

/**
 * 处理用户登录
 */
async function handleLogin() {
    const usernameInput = document.getElementById('username-input');
    const username = usernameInput.value.trim();
    
    if (!username) {
        showToast('请输入用户名', 'error');
        return;
    }
    
    if (username.length > 20) {
        showToast('用户名不能超过20个字符', 'error');
        return;
    }
    
    try {
        const result = await api.login(username, false);
        
        if (result.success) {
            await handleLoginSuccess(result);
        }
    } catch (error) {
        if (error.message.includes('此玩家已登陆') || error.message.includes('USER_IN_GAME')) {
            showToast('此玩家正在游戏中，请使用其他用户名', 'error');
        } else {
            showToast(`登录失败: ${error.message}`, 'error');
        }
    }
}

/**
 * 处理登录成功
 */
async function handleLoginSuccess(loginResult) {
    playerName = loginResult.user.username;
    userActiveGame = loginResult.active_game;
    
    // 保存到localStorage
    localStorage.setItem('splendor_username', playerName);
    
    // 更新UI
    const userNameElement = document.getElementById('current-user-name');
    if (userNameElement) {
        userNameElement.textContent = playerName;
    }
    
    // 切换到大厅
    switchScreen('lobby-screen');
    
    // 检查是否有活跃游戏
    if (loginResult.has_active_game && userActiveGame) {
        showRejoinGameButton(userActiveGame);
        
        if (userActiveGame.status === 'playing') {
            showToast('检测到未完成的游戏，点击"重新加入游戏"继续', 'info');
        } else {
            showToast('检测到未完成的房间，点击"重新加入游戏"返回', 'info');
        }
    } else {
        hideRejoinGameButton();
    }
    
    showToast(loginResult.message, 'success');
}

/**
 * 处理登出
 */
async function handleLogout() {
    if (!playerName) return;
    
    try {
        await api.logout(playerName);
        
        // 清除本地数据
        localStorage.removeItem('splendor_username');
        playerName = null;
        userActiveGame = null;
        
        // 切换到登录界面
        switchScreen('login-screen');
        
        showToast('已退出登录', 'info');
    } catch (error) {
        showToast(`登出失败: ${error.message}`, 'error');
    }
}

/**
 * 显示重新加入游戏按钮
 */
function showRejoinGameButton(gameInfo) {
    const container = document.getElementById('rejoin-game-container');
    if (container) {
        container.style.display = 'block';
    }
}

/**
 * 隐藏重新加入游戏按钮
 */
function hideRejoinGameButton() {
    const container = document.getElementById('rejoin-game-container');
    if (container) {
        container.style.display = 'none';
    }
}

/**
 * 重新加入游戏
 */
async function handleRejoinGame() {
    if (!userActiveGame) {
        showToast('没有找到活跃的游戏', 'error');
        return;
    }
    
    currentRoom = userActiveGame.room_id;
    isCreator = userActiveGame.is_creator;
    
    if (userActiveGame.status === 'playing') {
        // 游戏进行中，直接进入游戏界面
        switchScreen('game-screen');
        gameUI.startPolling(currentRoom, playerName);
        showToast('已重新加入游戏', 'success');
    } else {
        // 游戏在等待状态，进入房间界面
        showRoomScreen();
        startRoomPolling();
        showToast('已返回房间', 'success');
    }
    
    hideRejoinGameButton();
    userActiveGame = null;
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
    // 登录界面
    const loginBtn = document.getElementById('login-btn');
    if (loginBtn) {
        loginBtn.addEventListener('click', handleLogin);
    }
    
    const usernameInput = document.getElementById('username-input');
    if (usernameInput) {
        usernameInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                handleLogin();
            }
        });
    }
    
    // 大厅界面
    document.getElementById('logout-btn').addEventListener('click', handleLogout);
    document.getElementById('create-room-btn').addEventListener('click', handleCreateRoom);
    document.getElementById('show-rooms-btn').addEventListener('click', handleShowRooms);
    
    // 重新加入游戏按钮
    const rejoinBtn = document.getElementById('rejoin-game-btn');
    if (rejoinBtn) {
        rejoinBtn.addEventListener('click', handleRejoinGame);
    }
    document.getElementById('refresh-rooms-btn').addEventListener('click', () => loadRoomsList(true));
    document.getElementById('search-rooms-btn').addEventListener('click', handleSearchRooms);
    document.getElementById('back-to-lobby-from-rooms-btn').addEventListener('click', handleBackToLobby);
    
    // 搜索框回车搜索
    document.getElementById('room-search-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSearchRooms();
        }
    });
    
    // 分页按钮
    document.getElementById('prev-page-btn').addEventListener('click', () => changePage(-1));
    document.getElementById('next-page-btn').addEventListener('click', () => changePage(1));
    
    // 大厅规则和卡库按钮
    const viewRulesLobbyBtn = document.getElementById('view-rules-lobby-btn');
    const viewCardsLobbyBtn = document.getElementById('view-cards-lobby-btn');
    const viewHistoryBtn = document.getElementById('view-history-btn');
    if (viewRulesLobbyBtn) viewRulesLobbyBtn.addEventListener('click', () => showRulesModal());
    if (viewCardsLobbyBtn) viewCardsLobbyBtn.addEventListener('click', () => showCardsModal());
    if (viewHistoryBtn) viewHistoryBtn.addEventListener('click', () => window.location.href = '/history.html');
    
    // 房间界面
    document.getElementById('copy-room-id-btn').addEventListener('click', handleCopyRoomId);
    
    // 开始游戏按钮 - 添加详细调试
    const startGameBtn = document.getElementById('start-game-btn');
    console.log('🔗 绑定开始游戏按钮:', startGameBtn);
    startGameBtn.addEventListener('click', function(e) {
        console.log('🖱️ 开始游戏按钮点击事件触发!', e);
        handleStartGame();
    });
    
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
 * 处理退出登录
 */
function handleLogout() {
    // 确认退出
    if (confirm('确定要退出登录吗？')) {
        // 清除sessionStorage
        sessionStorage.removeItem('currentPlayerName');
        sessionStorage.removeItem('userData');
        clearGameSession();
        
        // 跳转到登录页面
        window.location.href = '/login.html';
    }
}

/**
 * 创建房间
 */
async function handleCreateRoom() {
    if (!playerName) {
        showToast('未登录，请先登录', 'error');
        return;
    }
    
    // 检查用户是否有活跃游戏
    if (userActiveGame) {
        showToast('你有未完成的游戏，请先完成或退出', 'error');
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
    if (!checkLoginStatus()) {
        return;
    }
    
    // 清空搜索框
    document.getElementById('room-search-input').value = '';
    currentPage = 1;

    document.getElementById('rooms-list').style.display = 'block';
    await loadRoomsList(true);
}

/**
 * 返回大厅
 */
function handleBackToLobby() {
    document.getElementById('rooms-list').style.display = 'none';
}

/**
 * 处理搜索房间
 */
function handleSearchRooms() {
    currentPage = 1;  // 搜索时重置到第一页
    filterAndDisplayRooms();
}

/**
 * 切换页码
 */
function changePage(delta) {
    const totalPages = Math.ceil(filteredRooms.length / ROOMS_PER_PAGE) || 1;
    currentPage = Math.max(1, Math.min(currentPage + delta, totalPages));
    displayRoomsPage();
}

/**
 * 加载房间列表
 * @param {boolean} refresh - 是否从服务器刷新数据
 */
async function loadRoomsList(refresh = false) {
    try {
        if (refresh) {
            showToast('正在刷新房间列表...', 'info');
            const result = await api.getRooms();
            allRooms = result.rooms || [];
        }
        
        // 应用搜索过滤
        filterAndDisplayRooms();
    } catch (error) {
        console.error('加载房间列表失败:', error);
        showToast('加载房间列表失败', 'error');
    }
}

/**
 * 过滤并显示房间
 */
function filterAndDisplayRooms() {
    const searchTerm = document.getElementById('room-search-input').value.trim().toLowerCase();
    
    // 过滤房间
    if (searchTerm) {
        filteredRooms = allRooms.filter(room => {
            const roomId = room.room_id.toLowerCase();
            const creator = room.creator.toLowerCase();
            return roomId.includes(searchTerm) || creator.includes(searchTerm);
        });
    } else {
        filteredRooms = [...allRooms];
    }
    
    // 重置到第一页
    currentPage = 1;
    displayRoomsPage();
}

/**
 * 显示当前页的房间
 */
function displayRoomsPage() {
    const container = document.getElementById('rooms-container');
    container.innerHTML = '';
    
    // 计算总页数
    const totalPages = Math.ceil(filteredRooms.length / ROOMS_PER_PAGE) || 1;
    
    // 显示房间
    if (filteredRooms.length === 0) {
        container.innerHTML = '<p style="text-align: center; opacity: 0.7; font-size: 1.5em; padding: 30px;">暂无可用房间</p>';
    } else {
        const startIndex = (currentPage - 1) * ROOMS_PER_PAGE;
        const endIndex = Math.min(startIndex + ROOMS_PER_PAGE, filteredRooms.length);
        const currentRooms = filteredRooms.slice(startIndex, endIndex);
        
        currentRooms.forEach((room, index) => {
            const roomDiv = document.createElement('div');
            roomDiv.className = 'room-item';
            const maxPlayers = room.max_players || 4;
            const victoryPoints = room.victory_points || 18;
            const statusBadge = room.status === 'playing' ? '<span style="color: #e74c3c;">🎮 游戏中</span>' : '<span style="color: #2ecc71;">⏳ 等待中</span>';
            
            roomDiv.innerHTML = `
                <div class="room-item-info">
                    <div style="margin-bottom: 10px;">
                        <strong style="font-size: 1.3em;">房间号: ${room.room_id}</strong>
                        <span style="margin-left: 15px;">${statusBadge}</span>
                    </div>
                    <div style="color: rgba(255,255,255,0.8);">
                        <span>👤 房主: ${room.creator}</span> | 
                        <span>👥 玩家: ${room.player_count}/${maxPlayers}</span> | 
                        <span>🏆 目标: ${victoryPoints}分</span>
                    </div>
                </div>
                <button class="btn btn-primary btn-small" onclick="joinRoom('${room.room_id}')" ${room.status === 'playing' ? 'disabled' : ''}>
                    ${room.status === 'playing' ? '进行中' : '加入'}
                </button>
            `;
            container.appendChild(roomDiv);
        });
    }
    
    // 更新分页控件
    updatePaginationControls(totalPages);
}

/**
 * 更新分页控件
 */
function updatePaginationControls(totalPages) {
    const prevBtn = document.getElementById('prev-page-btn');
    const nextBtn = document.getElementById('next-page-btn');
    const pageInfo = document.getElementById('page-info');
    
    prevBtn.disabled = (currentPage <= 1);
    nextBtn.disabled = (currentPage >= totalPages);
    
    pageInfo.textContent = `第 ${currentPage} 页 / 共 ${totalPages} 页 (共 ${filteredRooms.length} 个房间)`;
}

/**
 * 加入房间
 */
window.joinRoom = async function(roomId) {
    if (!playerName) {
        showToast('未登录，请先登录', 'error');
        return;
    }
    
    // 检查用户是否有活跃游戏
    if (userActiveGame) {
        showToast('你有未完成的游戏，请先完成或退出', 'error');
        return;
    }
    
    try{
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
        console.log('=== 检查开始按钮状态 ===');
        console.log('当前玩家名:', playerName);
        console.log('房主名称:', state.creator_name);
        console.log('isCreator变量:', isCreator);
        console.log('玩家数量:', state.players.length);
        console.log('最大玩家数:', maxPlayers);
        console.log('玩家列表:', state.players);
        console.log('房间状态:', state.status);
        
        // 从服务器返回的状态判断是否为房主（更可靠）
        const actuallyIsCreator = (state.creator_name === playerName);
        if (actuallyIsCreator !== isCreator) {
            console.warn('⚠️ isCreator变量与服务器状态不一致！');
            console.warn('isCreator变量:', isCreator);
            console.warn('服务器判断:', actuallyIsCreator);
            // 修正isCreator变量
            isCreator = actuallyIsCreator;
        }
        
        if (isCreator && state.players.length === maxPlayers) {
            console.log('✅ 启用开始按钮');
            startBtn.disabled = false;
            // 如果不是正在启动中，确保按钮文本正确
            if (!isStartingGame) {
                startBtn.textContent = '开始游戏';
            }
        } else {
            console.log('❌ 禁用开始按钮, 原因:', !isCreator ? '不是房主' : '人数不足');
            startBtn.disabled = true;
            // 如果不是正在启动中，确保按钮文本正确
            if (!isStartingGame) {
                startBtn.textContent = '开始游戏';
            }
        }
        
        // 如果游戏已经开始，切换到游戏界面
        if (state.status === 'playing') {
            console.log('🎮 检测到游戏已开始，准备跳转到游戏界面');
            stopRoomPolling();
            isStartingGame = false;  // 重置标志
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

// 防止重复点击的标志
let isStartingGame = false;

/**
 * 开始游戏
 */
async function handleStartGame() {
    console.log('=== 🎮 开始游戏按钮被点击 ===');
    
    // 防止重复点击
    if (isStartingGame) {
        console.warn('⚠️ 游戏正在启动中，请勿重复点击');
        return;
    }
    
    console.log('当前房间:', currentRoom);
    console.log('玩家名:', playerName);
    console.log('isCreator:', isCreator);
    
    // 检查按钮状态
    const startBtn = document.getElementById('start-game-btn');
    console.log('按钮disabled状态:', startBtn ? startBtn.disabled : 'null');
    
    if (!currentRoom || !playerName) {
        console.error('❌ 缺少必要信息:', { currentRoom, playerName });
        showToast('房间信息或玩家信息缺失', 'error');
        return;
    }
    
    try {
        isStartingGame = true;  // 设置标志，防止重复点击
        if (startBtn) {
            startBtn.disabled = true;  // 禁用按钮
            startBtn.textContent = '🔄 启动中...';
        }
        
        console.log('📡 正在调用API...');
        console.log('API路径:', `/api/rooms/${currentRoom}/start`);
        console.log('请求参数:', { player_name: playerName });
        
        const result = await api.startGame(currentRoom, playerName);
        console.log('✅ 开始游戏成功:', result);
        showToast('游戏开始！正在加载...', 'success');
        
        // 等待轮询检测到游戏状态变化并自动跳转
        // updateRoomInfo 会检测 status === 'playing' 并自动跳转
        
    } catch (error) {
        console.error('❌ 开始游戏失败:', error);
        console.error('错误详情:', error.message, error.stack);
        showToast(`开始游戏失败: ${error.message}`, 'error');
        
        // 恢复按钮状态
        isStartingGame = false;
        if (startBtn) {
            startBtn.textContent = '开始游戏';
            // 根据条件恢复按钮状态（会被下次轮询更新）
        }
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
 * 一键添加全部机器人（补满到配置的人数）
 */
async function handleAddAllBots(difficulty) {
    console.log('=== 🚀 一键补满按钮被点击 ===');
    console.log('难度:', difficulty);
    console.log('当前房间:', currentRoom);
    
    if (!currentRoom) {
        console.error('❌ 当前不在房间中');
        showToast('当前不在房间中', 'error');
        return;
    }

    try {
        console.log('📡 正在调用一键补满API...');
        const result = await api.addAllBots(currentRoom, difficulty);
        console.log('✅ 一键补满成功:', result);
        showToast(result.message, 'success');
        // 立即更新房间状态
        await updateRoomInfo();
    } catch (error) {
        console.error('❌ 一键添加机器人失败:', error);
        showToast(`一键添加机器人失败: ${error.message}`, 'error');
    }
}

/**
 * 踢出玩家
 */
async function handleKickPlayer(targetPlayer) {
    console.log('=== 👢 踢出玩家被点击 ===');
    console.log('目标玩家:', targetPlayer);
    console.log('房主:', playerName);
    console.log('当前房间:', currentRoom);
    
    if (!confirm(`确定要踢出玩家 ${targetPlayer} 吗？`)) {
        console.log('❌ 用户取消踢出');
        return;
    }
    
    console.log('✅ 用户确认踢出');

    try {
        console.log('📡 正在调用踢出玩家API...');
        const result = await api.kickPlayer(currentRoom, playerName, targetPlayer);
        console.log('✅ 踢出成功:', result);
        showToast(result.message, 'success');
        // 立即更新房间状态
        await updateRoomInfo();
    } catch (error) {
        console.error('❌ 踢出玩家失败:', error);
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
        
        // 清除活跃游戏标记
        userActiveGame = null;
        hideRejoinGameButton();
    } catch (error) {
        // 即使出错也返回大厅
        console.error('离开房间失败:', error);
        
        // 清除游戏会话
        clearGameSession();
        
        stopRoomPolling();
        switchScreen('lobby-screen');
        resetGame();
        
        // 清除活跃游戏标记
        userActiveGame = null;
        hideRejoinGameButton();
        
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

// 拿取球和结束行动已移至game.js中的gameUI对象

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
        
        // 清除活跃游戏标记
        userActiveGame = null;
        hideRejoinGameButton();
        
        showToast('已退出游戏', 'info');
    }
}

/**
 * 重置游戏状态
 */
function resetGame() {
    currentRoom = null;
    isCreator = false;
    isStartingGame = false;  // 重置开始游戏标志
    gameUI.clearBallSelection();  // 修正：清除精灵球选择
    gameUI.selectedCard = null;
    gameUI.stopPolling();
    document.getElementById('rooms-list').style.display = 'none';
    
    // 重置开始游戏按钮状态
    const startBtn = document.getElementById('start-game-btn');
    if (startBtn) {
        startBtn.textContent = '开始游戏';
        startBtn.disabled = false;
    }
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

