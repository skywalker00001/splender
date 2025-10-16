/**
 * 历史对局列表 - 前端逻辑
 */

const API_BASE = '';

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadHistoryList();
});

/**
 * 加载历史记录列表
 */
async function loadHistoryList() {
    const contentDiv = document.getElementById('history-content');
    
    try {
        const response = await fetch(`${API_BASE}/api/history/list`);
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || '加载失败');
        }
        
        if (data.histories.length === 0) {
            contentDiv.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">🎮</div>
                    <h2>暂无历史记录</h2>
                    <p>开始你的第一场游戏吧！</p>
                </div>
            `;
            return;
        }
        
        // 渲染历史记录列表
        renderHistoryList(data.histories);
        
    } catch (error) {
        console.error('加载历史记录失败:', error);
        contentDiv.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">❌</div>
                <h2>加载失败</h2>
                <p>${error.message}</p>
                <button class="btn btn-primary" onclick="loadHistoryList()">重试</button>
            </div>
        `;
    }
}

/**
 * 渲染历史记录列表
 */
function renderHistoryList(histories) {
    const contentDiv = document.getElementById('history-content');
    
    const listHTML = histories.map(history => {
        const startTime = new Date(history.start_time);
        const endTime = history.end_time ? new Date(history.end_time) : null;
        
        // 格式化时间
        const formatTime = (date) => {
            return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
        };
        
        // 计算游戏时长
        let duration = '未知';
        if (endTime) {
            const durationMs = endTime - startTime;
            const minutes = Math.floor(durationMs / 60000);
            const seconds = Math.floor((durationMs % 60000) / 1000);
            duration = `${minutes}分${seconds}秒`;
        }
        
        return `
            <div class="history-item" onclick="viewReplay('${history.game_id}')">
                <div class="history-item-header">
                    <span class="history-game-id">游戏ID: ${history.game_id}</span>
                    <span class="history-winner">🏆 ${history.winner || '未知'}</span>
                </div>
                
                <div class="history-item-body">
                    <div class="history-players">
                        ${history.players.map(player => `
                            <span class="history-player-tag">👤 ${player}</span>
                        `).join('')}
                    </div>
                </div>
                
                <div class="history-item-footer">
                    <span class="history-info-item">
                        🕐 ${formatTime(startTime)}
                    </span>
                    <span class="history-info-item">
                        ⏱️ ${duration}
                    </span>
                    <span class="history-info-item">
                        🔄 ${history.total_turns} 回合
                    </span>
                </div>
            </div>
        `;
    }).join('');
    
    contentDiv.innerHTML = `<div class="history-list">${listHTML}</div>`;
}

/**
 * 跳转到复盘页面
 */
function viewReplay(gameId) {
    window.location.href = `/replay.html?game_id=${gameId}`;
}

