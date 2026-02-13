/**
 * 游戏调试系统
 * 用于开发和测试
 */

class DebugPanel {
    constructor() {
        this.isVisible = false;
        this.currentTab = 'owned'; // owned or reserved
        this.currentSource = 'tableau'; // tableau or deck
        this.currentLevel = 1; // for deck selection
        this.debugEnabled = false; // 调试模式开关
        
        this.init();
    }
    
    init() {
        // 绑定按钮事件
        const toggleBtn = document.getElementById('toggle-debug-btn');
        const closeBtn = document.getElementById('close-debug-btn');
        const overlay = document.getElementById('debug-overlay');
        
        if (toggleBtn) {
            toggleBtn.addEventListener('click', () => this.toggle());
        }
        
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.hide());
        }
        
        // 点击遮罩层关闭面板
        if (overlay) {
            overlay.addEventListener('click', () => this.hide());
        }
        
        // 绑定Tab切换
        document.querySelectorAll('.debug-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                document.querySelectorAll('.debug-tab').forEach(t => t.classList.remove('active'));
                e.target.classList.add('active');
                this.currentTab = e.target.dataset.tab;
                this.updateCardList();
            });
        });
        
        // 绑定卡牌来源切换
        document.querySelectorAll('input[name="card-source"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.currentSource = e.target.value;
                this.updateCardList();
            });
        });
        
        // 监听键盘快捷键：Ctrl+Shift+D 显示/隐藏调试按钮
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.shiftKey && e.key === 'D') {
                e.preventDefault();
                this.toggleDebugMode();
            }
        });
    }
    
    /**
     * 切换调试模式（显示/隐藏调试按钮）
     */
    toggleDebugMode() {
        this.debugEnabled = !this.debugEnabled;
        const toggleBtn = document.getElementById('toggle-debug-btn');
        if (toggleBtn) {
            toggleBtn.style.display = this.debugEnabled ? 'inline-block' : 'none';
        }
        showToast(this.debugEnabled ? '🔧 调试模式已启用' : '🔧 调试模式已关闭', 'info');
    }
    
    /**
     * 切换调试面板显示
     */
    toggle() {
        if (this.isVisible) {
            this.hide();
        } else {
            this.show();
        }
    }
    
    /**
     * 显示调试面板
     */
    show() {
        if (!gameUI.currentGameState || !gameUI.currentRoomId) {
            showToast('请先开始游戏', 'error');
            return;
        }
        
        const panel = document.getElementById('debug-panel');
        const overlay = document.getElementById('debug-overlay');
        
        if (panel && overlay) {
            overlay.style.display = 'block';
            panel.style.display = 'flex';
            this.isVisible = true;
            this.render();
        }
    }
    
    /**
     * 隐藏调试面板
     */
    hide() {
        const panel = document.getElementById('debug-panel');
        const overlay = document.getElementById('debug-overlay');
        
        if (panel && overlay) {
            panel.style.display = 'none';
            overlay.style.display = 'none';
            this.isVisible = false;
        }
    }
    
    /**
     * 渲染调试面板
     */
    render() {
        this.renderScoreControl();
        this.renderBallControls();
        this.renderPermanentBallControls();
        this.updateCardList();
    }
    
    /**
     * 渲染分数控制
     */
    renderScoreControl() {
        const container = document.getElementById('debug-score-control');
        if (!container) return;
        
        const currentPlayer = gameUI.currentGameState.player_states[gameUI.currentPlayerName];
        if (!currentPlayer) return;
        
        const currentScore = currentPlayer.victory_points || 0;
        
        container.innerHTML = `
            <div class="debug-score-item">
                <div class="debug-score-display">
                    <span class="debug-score-label">当前分数:</span>
                    <span class="debug-score-value">${currentScore}</span>
                </div>
                <div class="debug-ball-controls">
                    <button onclick="debugPanel.adjustScore(-5)">-5</button>
                    <button onclick="debugPanel.adjustScore(-1)">-1</button>
                    <button onclick="debugPanel.adjustScore(1)">+1</button>
                    <button onclick="debugPanel.adjustScore(5)">+5</button>
                </div>
            </div>
        `;
    }
    
    /**
     * 渲染持有球控制
     */
    renderBallControls() {
        const container = document.getElementById('debug-add-balls');
        if (!container) return;
        
        const currentPlayer = gameUI.currentGameState.player_states[gameUI.currentPlayerName];
        if (!currentPlayer) return;
        
        const ballOrder = ['黑', '粉', '黄', '蓝', '红', '大师球'];
        const ballConfig = BALL_CONFIG;
        
        container.innerHTML = ballOrder.map(ball => {
            const count = currentPlayer.balls[ball] || 0;
            const config = ballConfig[ball];
            
            return `
                <div class="debug-ball-item">
                    <div class="debug-ball-emoji">${config.emoji}</div>
                    <div class="debug-ball-name">${config.name}</div>
                    <div class="debug-ball-controls">
                        <button onclick="debugPanel.adjustBall('${ball}', -1)">-</button>
                        <span>${count}</span>
                        <button onclick="debugPanel.adjustBall('${ball}', 1)">+</button>
                    </div>
                </div>
            `;
        }).join('');
    }
    
    /**
     * 渲染永久折扣控制
     */
    renderPermanentBallControls() {
        const container = document.getElementById('debug-permanent-balls');
        if (!container) return;
        
        const currentPlayer = gameUI.currentGameState.player_states[gameUI.currentPlayerName];
        if (!currentPlayer) return;
        
        const ballOrder = ['黑', '粉', '黄', '蓝', '红']; // 永久折扣不包括大师球
        const ballConfig = BALL_CONFIG;
        
        const ballsHtml = ballOrder.map(ball => {
            const count = currentPlayer.permanent_balls[ball] || 0;
            const config = ballConfig[ball];
            
            return `
                <div class="debug-ball-item">
                    <div class="debug-ball-emoji">${config.emoji}</div>
                    <div class="debug-ball-name">${config.name}</div>
                    <div class="debug-ball-controls">
                        <button onclick="debugPanel.adjustPermanentBall('${ball}', -1)">-</button>
                        <span>${count}</span>
                        <button onclick="debugPanel.adjustPermanentBall('${ball}', 1)">+</button>
                    </div>
                </div>
            `;
        }).join('');
        
        // 添加快捷按钮
        const quickButtonsHtml = `
            <div class="debug-quick-buttons">
                <button class="debug-quick-btn" onclick="debugPanel.addAllPermanentBalls(10)">🚀 全部 +10</button>
                <button class="debug-quick-btn danger" onclick="debugPanel.addAllPermanentBalls(-10)">💨 全部 -10</button>
            </div>
        `;
        
        container.innerHTML = ballsHtml + quickButtonsHtml;
    }
    
    /**
     * 批量调整所有永久折扣
     */
    async addAllPermanentBalls(delta) {
        const ballOrder = ['黑', '粉', '黄', '蓝', '红'];
        
        showToast(`正在调整所有永久折扣...`, 'info');
        
        try {
            // 并行调用所有API
            const promises = ballOrder.map(ball => 
                api.debugAdjustPermanentBalls(
                    gameUI.currentRoomId,
                    gameUI.currentPlayerName,
                    ball,
                    delta
                )
            );
            
            await Promise.all(promises);
            
            showToast(`成功${delta > 0 ? '增加' : '减少'}所有永久折扣 ${Math.abs(delta)}`, 'success');
            
            // 刷新游戏状态和控件
            await gameUI.pollGameState();
            this.renderPermanentBallControls();
        } catch (error) {
            showToast('操作失败: ' + error.message, 'error');
        }
    }
    
    /**
     * 更新卡牌列表
     */
    updateCardList() {
        const container = document.getElementById('debug-card-selection');
        if (!container) return;
        
        if (this.currentSource === 'tableau') {
            this.renderTableauCards(container);
        } else {
            this.renderDeckCards(container);
        }
    }
    
    /**
     * 渲染场上卡牌
     */
    renderTableauCards(container) {
        const gameState = gameUI.currentGameState;
        if (!gameState) return;
        
        let cards = [];
        
        // 收集所有场上的卡牌
        for (let level = 1; level <= 3; level++) {
            const levelCards = gameState.tableau[level.toString()] || [];
            cards = cards.concat(levelCards.map(card => ({ ...card, source: `tableau-${level}` })));
        }
        
        // 添加稀有和传说卡牌
        if (gameState.rare_card) {
            cards.push({ ...gameState.rare_card, source: 'rare' });
        }
        if (gameState.legendary_card) {
            cards.push({ ...gameState.legendary_card, source: 'legendary' });
        }
        
        this.renderCardList(container, cards);
    }
    
    /**
     * 渲染牌堆卡牌
     */
    renderDeckCards(container) {
        const gameState = gameUI.currentGameState;
        if (!gameState) return;
        
        // 显示等级选择器
        const levelSelector = `
            <div class="debug-level-selector">
                ${[1, 2, 3].map(level => `
                    <button class="debug-level-btn ${this.currentLevel === level ? 'active' : ''}" 
                            onclick="debugPanel.selectLevel(${level})">
                        等级 ${level} (剩余: ${gameState['lv' + level + '_deck_size'] || 0})
                    </button>
                `).join('')}
            </div>
        `;
        
        container.innerHTML = levelSelector + '<div id="deck-card-list"></div>';
        
        // 从牌堆只能看到数量，不能看到具体卡牌
        const deckSize = gameState[`lv${this.currentLevel}_deck_size`] || 0;
        const listContainer = document.getElementById('deck-card-list');
        
        if (deckSize > 0) {
            listContainer.innerHTML = `
                <div class="debug-card-item">
                    <div class="debug-card-info">
                        <div class="debug-card-name">Lv${this.currentLevel} 牌堆顶</div>
                        <div class="debug-card-details">随机抽取一张添加到${this.currentTab === 'owned' ? '已拥有' : '预定'}卡牌</div>
                    </div>
                    <button class="debug-card-action" onclick="debugPanel.addCardFromDeck(${this.currentLevel})">
                        添加
                    </button>
                </div>
            `;
        } else {
            listContainer.innerHTML = '<div style="text-align: center; color: #95a5a6; padding: 20px;">牌堆已空</div>';
        }
    }
    
    /**
     * 渲染卡牌列表
     */
    renderCardList(container, cards) {
        if (cards.length === 0) {
            container.innerHTML = '<div style="text-align: center; color: #95a5a6; padding: 20px;">暂无卡牌</div>';
            return;
        }
        
        const html = `
            <div class="debug-card-list">
                ${cards.map(card => this.renderCardItem(card)).join('')}
            </div>
        `;
        
        container.innerHTML = html;
    }
    
    /**
     * 渲染单个卡牌项
     */
    renderCardItem(card) {
        const costStr = Object.entries(card.cost || {})
            .filter(([_, amount]) => amount > 0)
            .map(([ball, amount]) => `${BALL_CONFIG[ball]?.emoji || ball}×${amount}`)
            .join(' ');
        
        return `
            <div class="debug-card-item">
                <div class="debug-card-info">
                    <div class="debug-card-name">${card.name} (Lv${card.level})</div>
                    <div class="debug-card-details">
                        ${card.victory_points}VP | 成本: ${costStr || '无'}
                    </div>
                </div>
                <button class="debug-card-action" onclick='debugPanel.addCard(${JSON.stringify(card).replace(/'/g, "&apos;")})'>
                    添加到${this.currentTab === 'owned' ? '已拥有' : '预定'}
                </button>
            </div>
        `;
    }
    
    /**
     * 选择牌堆等级
     */
    selectLevel(level) {
        this.currentLevel = level;
        this.updateCardList();
    }
    
    /**
     * 调整分数
     */
    async adjustScore(delta) {
        try {
            const response = await api.debugAdjustScore(
                gameUI.currentRoomId,
                gameUI.currentPlayerName,
                delta
            );
            
            if (response.success) {
                showToast(`分数${delta > 0 ? '+' : ''}${delta}，当前: ${response.new_score}`, 'success');
                // 先刷新游戏状态，再重新渲染控件
                await gameUI.pollGameState();
                this.renderScoreControl();
            } else {
                showToast(response.error || '操作失败', 'error');
            }
        } catch (error) {
            showToast('操作失败: ' + error.message, 'error');
        }
    }
    
    /**
     * 调整持有球
     */
    async adjustBall(ballType, delta) {
        try {
            const response = await api.debugAdjustBalls(
                gameUI.currentRoomId,
                gameUI.currentPlayerName,
                ballType,
                delta
            );
            
            if (response.success) {
                showToast(`成功${delta > 0 ? '增加' : '减少'}${BALL_CONFIG[ballType].name}`, 'success');
                // 先刷新游戏状态，再重新渲染控件
                await gameUI.pollGameState();
                this.renderBallControls();
            } else {
                showToast(response.error || '操作失败', 'error');
            }
        } catch (error) {
            showToast('操作失败: ' + error.message, 'error');
        }
    }
    
    /**
     * 调整永久折扣
     */
    async adjustPermanentBall(ballType, delta) {
        try {
            const response = await api.debugAdjustPermanentBalls(
                gameUI.currentRoomId,
                gameUI.currentPlayerName,
                ballType,
                delta
            );
            
            if (response.success) {
                showToast(`成功${delta > 0 ? '增加' : '减少'}${BALL_CONFIG[ballType].name}永久折扣`, 'success');
                // 先刷新游戏状态，再重新渲染控件
                await gameUI.pollGameState();
                this.renderPermanentBallControls();
            } else {
                showToast(response.error || '操作失败', 'error');
            }
        } catch (error) {
            showToast('操作失败: ' + error.message, 'error');
        }
    }
    
    /**
     * 从场上添加卡牌
     */
    async addCard(card) {
        try {
            const cardType = this.currentTab; // 'owned' or 'reserved'
            const response = await api.debugAddCard(
                gameUI.currentRoomId,
                gameUI.currentPlayerName,
                card.card_id,
                cardType,
                'tableau'
            );
            
            if (response.success) {
                showToast(`成功添加卡牌: ${card.name}`, 'success');
                // 先刷新游戏状态，再重新渲染控件
                await gameUI.pollGameState();
                this.updateCardList();
            } else {
                showToast(response.error || '添加失败', 'error');
            }
        } catch (error) {
            showToast('操作失败: ' + error.message, 'error');
        }
    }
    
    /**
     * 从牌堆添加卡牌
     */
    async addCardFromDeck(level) {
        try {
            const cardType = this.currentTab; // 'owned' or 'reserved'
            const response = await api.debugAddCardFromDeck(
                gameUI.currentRoomId,
                gameUI.currentPlayerName,
                level,
                cardType
            );
            
            if (response.success) {
                const cardName = response.card_name || '未知卡牌';
                showToast(`成功从Lv${level}牌堆添加: ${cardName}`, 'success');
                // 先刷新游戏状态，再重新渲染控件
                await gameUI.pollGameState();
                this.updateCardList();
            } else {
                showToast(response.error || '添加失败', 'error');
            }
        } catch (error) {
            showToast('操作失败: ' + error.message, 'error');
        }
    }
}

// 创建全局调试面板实例
const debugPanel = new DebugPanel();

