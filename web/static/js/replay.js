/**
 * 对局复盘 - 前端逻辑
 */

const API_BASE = '';
let currentHistory = null;
let currentTurnIndex = 0;

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    const gameId = params.get('game_id');
    
    if (!gameId) {
        showError('缺少游戏ID参数');
        return;
    }
    
    loadGameHistory(gameId);
});

/**
 * 加载游戏历史记录
 */
async function loadGameHistory(gameId) {
    try {
        const response = await fetch(`${API_BASE}/api/history/${gameId}`);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || '加载失败');
        }
        
        currentHistory = data.history;
        currentTurnIndex = 0;
        
        renderReplay();
        
    } catch (error) {
        console.error('加载历史记录失败:', error);
        showError(error.message);
    }
}

/**
 * 渲染复盘界面
 */
function renderReplay() {
    const contentDiv = document.getElementById('replay-content');
    
    // 格式化时间
    const formatTime = (dateStr) => {
        const date = new Date(dateStr);
        return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
    };
    
    // 计算时长
    let duration = '未知';
    if (currentHistory.start_time && currentHistory.end_time) {
        const start = new Date(currentHistory.start_time);
        const end = new Date(currentHistory.end_time);
        const durationMs = end - start;
        const minutes = Math.floor(durationMs / 60000);
        const seconds = Math.floor((durationMs % 60000) / 1000);
        duration = `${minutes}分${seconds}秒`;
    }
    
    contentDiv.innerHTML = `
        <div class="replay-header">
            <div class="replay-game-info">
                <h2>对局复盘</h2>
                <div class="replay-game-meta">
                    <span>🎮 游戏ID: ${currentHistory.game_id}</span>
                    <span>🏆 胜者: ${currentHistory.winner || '未知'}</span>
                    <span>🕐 开始: ${formatTime(currentHistory.start_time)}</span>
                    <span>⏱️ 时长: ${duration}</span>
                    <span>🔄 总回合: ${currentHistory.total_turns}</span>
                </div>
            </div>
            <div class="replay-controls">
                <button class="replay-nav-button" onclick="previousTurn()" id="prev-btn">⬅️ 上一回合</button>
                <select class="replay-turn-selector" id="turn-selector" onchange="jumpToTurn(this.value)">
                    ${currentHistory.turns.map((turn, index) => `
                        <option value="${index}">回合 ${turn.turn} - ${turn.player}</option>
                    `).join('')}
                </select>
                <button class="replay-nav-button" onclick="nextTurn()" id="next-btn">下一回合 ➡️</button>
            </div>
        </div>
        
        <div class="replay-content">
            <div class="replay-sidebar">
                <div class="replay-turn-list">
                    <h3>📋 回合列表</h3>
                    <div id="turn-list"></div>
                </div>
            </div>
            
            <div class="replay-main">
                <div id="turn-detail"></div>
            </div>
        </div>
    `;
    
    renderTurnList();
    showTurn(currentTurnIndex);
}

/**
 * 渲染回合列表
 */
function renderTurnList() {
    const turnListDiv = document.getElementById('turn-list');
    
    const listHTML = currentHistory.turns.map((turn, index) => {
        const isActive = index === currentTurnIndex;
        return `
            <div class="replay-turn-item ${isActive ? 'active' : ''}" onclick="jumpToTurn(${index})">
                <div class="replay-turn-item-title">回合 ${turn.turn}</div>
                <div class="replay-turn-item-player">👤 ${turn.player}</div>
            </div>
        `;
    }).join('');
    
    turnListDiv.innerHTML = listHTML;
}

/**
 * 显示指定回合
 */
function showTurn(index) {
    if (index < 0 || index >= currentHistory.turns.length) {
        return;
    }
    
    currentTurnIndex = index;
    const turn = currentHistory.turns[index];
    
    // 更新选择器
    document.getElementById('turn-selector').value = index;
    
    // 更新按钮状态
    document.getElementById('prev-btn').disabled = (index === 0);
    document.getElementById('next-btn').disabled = (index === currentHistory.turns.length - 1);
    
    // 更新回合列表高亮
    renderTurnList();
    
    // 渲染回合详情
    renderTurnDetail(turn);
}

/**
 * 渲染回合详情
 */
function renderTurnDetail(turn) {
    const turnDetailDiv = document.getElementById('turn-detail');
    
    // 渲染动作列表
    const actionsHTML = turn.actions.length > 0 ? turn.actions.map(action => {
        const isSuccess = action.result;
        let dataDisplay = '';
        
        // 根据动作类型格式化数据
        if (action.type === 'take_balls') {
            dataDisplay = `拿取球: ${action.data.ball_types.join(', ')}`;
        } else if (action.type === 'buy_card') {
            dataDisplay = `购买卡牌: ${action.data.card_name} (Lv${action.data.card_level}, ${action.data.card_vp}VP)`;
        } else if (action.type === 'reserve_card') {
            dataDisplay = `预购卡牌: ${action.data.card_name} (Lv${action.data.card_level})${action.data.blind ? ' [盲预购]' : ''}`;
        } else if (action.type === 'evolve') {
            dataDisplay = `进化: ${action.data.base_card || '基础卡'} → ${action.data.target_card || '目标卡'}`;
        } else if (action.type === 'return_balls') {
            const balls = Object.entries(action.data).map(([k, v]) => `${k}×${v}`).join(', ');
            dataDisplay = `放回球: ${balls}`;
        } else {
            dataDisplay = JSON.stringify(action.data);
        }
        
        return `
            <div class="replay-action-item ${!isSuccess ? 'failed' : ''}">
                <div class="replay-action-type">${isSuccess ? '✅' : '❌'} ${action.type.toUpperCase()}</div>
                <div class="replay-action-data">${dataDisplay}</div>
                ${action.message ? `<div class="replay-action-message">${action.message}</div>` : ''}
            </div>
        `;
    }).join('') : '<p style="color: #95a5a6;">本回合无动作记录</p>';
    
    // 渲染状态对比
    const stateBeforeHTML = turn.states_before && turn.states_before.player ? `
        <div class="replay-state-box">
            <h4>动作前</h4>
            <div class="replay-state-item">
                <span class="replay-state-label">玩家</span>
                <span class="replay-state-value">${turn.states_before.player.name}</span>
            </div>
            <div class="replay-state-item">
                <span class="replay-state-label">胜利点数</span>
                <span class="replay-state-value">${turn.states_before.player.victory_points} VP</span>
            </div>
            <div class="replay-state-item">
                <span class="replay-state-label">持球</span>
                <span class="replay-state-value">${formatBalls(turn.states_before.player.balls)}</span>
            </div>
            <div class="replay-state-item">
                <span class="replay-state-label">拥有卡牌</span>
                <span class="replay-state-value">${turn.states_before.player.owned_cards_count} 张</span>
            </div>
            <div class="replay-state-item">
                <span class="replay-state-label">预购卡牌</span>
                <span class="replay-state-value">${turn.states_before.player.reserved_cards_count} 张</span>
            </div>
        </div>
    ` : '<div class="replay-state-box"><p>无数据</p></div>';
    
    const stateAfterHTML = turn.states_after && turn.states_after.player ? `
        <div class="replay-state-box">
            <h4>动作后</h4>
            <div class="replay-state-item">
                <span class="replay-state-label">玩家</span>
                <span class="replay-state-value">${turn.states_after.player.name}</span>
            </div>
            <div class="replay-state-item">
                <span class="replay-state-label">胜利点数</span>
                <span class="replay-state-value">${turn.states_after.player.victory_points} VP</span>
            </div>
            <div class="replay-state-item">
                <span class="replay-state-label">持球</span>
                <span class="replay-state-value">${formatBalls(turn.states_after.player.balls)}</span>
            </div>
            <div class="replay-state-item">
                <span class="replay-state-label">拥有卡牌</span>
                <span class="replay-state-value">${turn.states_after.player.owned_cards_count} 张</span>
            </div>
            <div class="replay-state-item">
                <span class="replay-state-label">预购卡牌</span>
                <span class="replay-state-value">${turn.states_after.player.reserved_cards_count} 张</span>
            </div>
        </div>
    ` : '<div class="replay-state-box"><p>无数据</p></div>';
    
    turnDetailDiv.innerHTML = `
        <div class="replay-turn-detail">
            <div class="replay-turn-header">
                <h3 class="replay-turn-title">回合 ${turn.turn}</h3>
                <div class="replay-player-badge">👤 ${turn.player}</div>
            </div>
            
            <div class="replay-actions">
                <h4>🎯 动作记录</h4>
                ${actionsHTML}
            </div>
            
            <div class="replay-state-comparison">
                ${stateBeforeHTML}
                ${stateAfterHTML}
            </div>
        </div>
    `;
}

/**
 * 格式化球数显示
 */
function formatBalls(balls) {
    if (!balls || Object.keys(balls).length === 0) {
        return '无';
    }
    
    const ballEmojis = {
        '黑': '⚫',
        '粉': '🌸',
        '黄': '🟡',
        '蓝': '🔵',
        '红': '🔴',
        '大师球': '🟣'
    };
    
    return Object.entries(balls)
        .filter(([_, count]) => count > 0)
        .map(([ball, count]) => `${ballEmojis[ball] || ball}×${count}`)
        .join(' ');
}

/**
 * 上一回合
 */
function previousTurn() {
    if (currentTurnIndex > 0) {
        showTurn(currentTurnIndex - 1);
    }
}

/**
 * 下一回合
 */
function nextTurn() {
    if (currentTurnIndex < currentHistory.turns.length - 1) {
        showTurn(currentTurnIndex + 1);
    }
}

/**
 * 跳转到指定回合
 */
function jumpToTurn(index) {
    showTurn(parseInt(index));
}

/**
 * 显示错误
 */
function showError(message) {
    const contentDiv = document.getElementById('replay-content');
    contentDiv.innerHTML = `
        <div class="loading">
            <div style="font-size: 64px; margin-bottom: 20px;">❌</div>
            <div style="color: #e74c3c;">加载失败</div>
            <p style="color: #95a5a6; margin-top: 10px;">${message}</p>
            <a href="/history.html" class="btn btn-primary" style="margin-top: 20px; display: inline-block;">返回历史列表</a>
        </div>
    `;
}

