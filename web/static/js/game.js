/**
 * 游戏状态管理和UI渲染 - V2版本（适配新规则）
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

// 球类型配置（BallType）- 5种颜色球 + 大师球
const BALL_CONFIG = {
    '黑': { emoji: '⚫', class: 'ball-black', name: '黑球' },
    '粉': { emoji: '🌸', class: 'ball-pink', name: '粉球' },
    '黄': { emoji: '🟡', class: 'ball-yellow', name: '黄球' },
    '蓝': { emoji: '🔵', class: 'ball-blue', name: '蓝球' },
    '红': { emoji: '🔴', class: 'ball-red', name: '红球' },
    '大师球': { emoji: '🟣', class: 'ball-master', name: '大师球' }  // 紫色
};

class GameUI {
    constructor() {
        this.selectedBalls = [];
        this.selectedCard = null;
        this.currentGameState = null;
        this.currentRoomId = null;
        this.currentPlayerName = null;
        this.pollingInterval = null;
        this.controlledAI = null;  // 当前控制的AI玩家名称
        this.aiPlayers = [];  // 所有AI玩家列表
        this.hasPerformedMainAction = false;  // 是否已执行主要操作（买/拿/预购）
        this.hasPerformedEvolution = false;  // 是否已进化
        this.ballsToReturn = {};  // 选择要放回的球 {球类型: 数量}
        this.waitingForReturnBalls = false;  // 是否在等待放回球
        this.currentActionSteps = [];  // 记录当前行动的所有步骤
        this.lastActionPlayer = null;  // 上一个行动的玩家，用于检测行动切换
    }

    /**
     * 渲染球池
     */
    renderBallPool(ballPool) {
        const container = document.getElementById('gem-pool');
        container.innerHTML = '';

        // 按顺序显示所有球类型
        const ballOrder = ['红', '蓝', '绿', '黄', '粉', '黑', '大师球'];
        
        ballOrder.forEach(ballType => {
            const count = ballPool[ballType] || 0;
            const config = BALL_CONFIG[ballType];
            if (!config) return;

            const ballDiv = document.createElement('div');
            ballDiv.className = `gem-item ${config.class}`;
            ballDiv.dataset.ballType = ballType;
            
            // 大师球不能直接拿取
            if (count === 0 || ballType === '大师球') {
                ballDiv.classList.add('gem-disabled');
            }

            ballDiv.innerHTML = `
                <div class="gem-emoji">${config.emoji}</div>
                <div class="gem-name">${config.name}</div>
                <div class="gem-count">${count}</div>
            `;

            if (count > 0 && ballType !== '大师球') {
                ballDiv.addEventListener('click', () => this.selectBall(ballType, ballDiv));
            }

            container.appendChild(ballDiv);
        });
    }

    /**
     * 选择球
     */
    selectBall(ballType, element) {
        const ballPool = this.currentGameState.ball_pool;
        
        // 统计已选择的颜色种类
        const uniqueColors = [...new Set(this.selectedBalls)];
        const selectedCountOfThisType = this.selectedBalls.filter(b => b === ballType).length;
        
        // 判断当前选择模式
        const isSameColorMode = this.selectedBalls.length === 2 && uniqueColors.length === 1;
        const isDifferentColorMode = this.selectedBalls.length > 0 && uniqueColors.length > 1;
        
        // 检查是否已经选了2个同色球（同色模式完成）
        if (isSameColorMode) {
            // 已选2个同色球，不允许再选任何球
            if (confirm('最多拿同一个颜色的2个球，点击确定清空重新选择')) {
                this.clearBallSelection();
                this.updateTakeBallsButtonState();
            }
            return;
        }
        
        // 如果已经是不同色模式，不允许选择同一颜色的第2个球
        if (isDifferentColorMode && selectedCountOfThisType >= 1) {
            showToast('不同色拿球模式下，每种颜色只能拿1个！点击确定清空重新选择', 'error');
            if (confirm('当前是不同色拿球模式（每种颜色1个）。要切换到同色拿球模式（同色2个）吗？')) {
                this.clearBallSelection();
                this.updateTakeBallsButtonState();
            }
            return;
        }
        
        // 如果已经选了1个该颜色，尝试选第2个同色球
        if (selectedCountOfThisType === 1 && this.selectedBalls.length === 1) {
            // 只有在只选了1个球时，才允许选第2个同色球
            // 检查拿完2个后是否还剩至少2个（即拿之前至少有4个）
            const remainingAfterTake = ballPool[ballType] - 2;
            if (remainingAfterTake < 2) {
                // 拿完后剩余不足2个，不满足规则
                alert(`${BALL_CONFIG[ballType]?.emoji || ballType}色球所剩不大于等于4的时候无法拿取2个（当前只有${ballPool[ballType]}个）`);
                this.clearBallSelection();
                return;
            }
            
            this.selectedBalls.push(ballType);
            this.updateSelectedBallsDisplay();
            this.updateTakeBallsButtonState();
            return;
        }
        
        // 以下是选择新颜色的逻辑
        if (this.selectedBalls.length === 0) {
            // 第一个球
            this.selectedBalls.push(ballType);
            element.classList.add('selected');
        } else if (this.selectedBalls.length === 1 && selectedCountOfThisType === 0) {
            // 第二个球（不同颜色） - 确保不是选已选的颜色
            this.selectedBalls.push(ballType);
            element.classList.add('selected');
        } else if (this.selectedBalls.length === 2) {
            // 此时已经是2个不同色球，拿第3个不同颜色的球
            if (this.selectedBalls.includes(ballType)) {
                showToast('已选择该颜色，不能重复选择', 'error');
                return;
            }
            this.selectedBalls.push(ballType);
            element.classList.add('selected');
        } else if (this.selectedBalls.length >= 3) {
            // 已选满3个不同色球
            if (confirm('最多拿三个不同颜色的各1个球，点击确定清空重新选择')) {
                this.clearBallSelection();
                this.updateTakeBallsButtonState();
            }
            return;
        }

        this.updateSelectedBallsDisplay();
        this.updateTakeBallsButtonState();
    }

    /**
     * 更新已选择球显示
     */
    updateSelectedBallsDisplay() {
        const display = document.getElementById('selected-gems-display');
        if (this.selectedBalls.length === 0) {
            display.textContent = '无';
        } else {
            display.textContent = this.selectedBalls.map(b => BALL_CONFIG[b].emoji + b).join(', ');
        }
    }

    /**
     * 更新"拿取精灵球"按钮状态
     */
    updateTakeBallsButtonState() {
        const isMyTurn = this.currentGameState && 
                         this.currentGameState.current_player === this.currentPlayerName;
        const takeBallsBtn = document.getElementById('take-gems-btn');
        if (!takeBallsBtn) return;
        
        if (!isMyTurn) {
            takeBallsBtn.disabled = true;
            return;
        }
        
        // 检查选择是否符合规则
        const isValidSelection = this.checkBallSelectionValid();
        takeBallsBtn.disabled = !isValidSelection;
    }
    
    /**
     * 检查球选择是否有效（符合拿球规则）
     */
    checkBallSelectionValid() {
        if (!this.currentGameState || !this.currentGameState.ball_pool) return false;
        
        const ballPool = this.currentGameState.ball_pool;
        const selectedCount = this.selectedBalls.length;
        
        // 未选择任何球
        if (selectedCount === 0) return false;
        
        // 统计场上有多少种颜色的球大于0（不包括大师球）- remained_color
        const remainedColor = Object.entries(ballPool)
            .filter(([ball, count]) => ball !== 'MASTER' && count > 0)
            .length;
        
        // 球充足时（remained_color >= 3）
        if (remainedColor >= 3) {
            // 情况1: 选了2个球
            if (selectedCount === 2) {
                // 必须是同色球，且该颜色池≥4
                if (this.selectedBalls[0] === this.selectedBalls[1]) {
                    const ballType = this.selectedBalls[0];
                    return ballPool[ballType] >= 4;
                }
                // 2个不同色球在球充足时是不合法的
                return false;
            }
            
            // 情况2: 选了3个球，必须是3个不同色球
            if (selectedCount === 3) {
                const uniqueSelected = new Set(this.selectedBalls);
                return uniqueSelected.size === 3;
            }
            
            // 其他情况（选了1个或4+个）都不合法
            return false;
        }
        
        // 球不充足时（remained_color < 3）
        // 必须拿取栏的数目 == remained_color
        if (selectedCount !== remainedColor) return false;
        
        // 检查是否都是不同颜色
        const uniqueSelected = new Set(this.selectedBalls);
        if (uniqueSelected.size !== selectedCount) return false;
        
        // 检查每个选择的颜色在场上都有
        for (const ball of this.selectedBalls) {
            if (!ballPool[ball] || ballPool[ball] <= 0) return false;
        }
        
        return true;
    }

    /**
     * 清除球选择
     */
    clearBallSelection() {
        this.selectedBalls = [];
        document.querySelectorAll('.gem-item.selected').forEach(el => {
            el.classList.remove('selected');
        });
        this.updateSelectedBallsDisplay();
        this.updateTakeBallsButtonState();
    }

    /**
     * 渲染桌面卡牌
     */
    renderTableauCards(tableau, lv1Deck, lv2Deck, lv3Deck, rareCard, legendaryCard, rareDeckSize, legendaryDeckSize) {
        // 渲染Lv1-3卡牌
        for (let level = 1; level <= 3; level++) {
            const container = document.getElementById(`tier-${level}-cards`);
            container.innerHTML = '';

            // 显示牌堆（可以盲预购）
            const deckSize = level === 1 ? lv1Deck : (level === 2 ? lv2Deck : lv3Deck);
            if (deckSize > 0) {
                const deckDiv = document.createElement('div');
                deckDiv.className = 'deck-card';
                
                // 检查是否是当前玩家的回合
                const isMyTurn = this.currentGameState && 
                                 this.currentGameState.current_player === this.currentPlayerName;
                if (!isMyTurn) {
                    deckDiv.classList.add('not-my-turn');
                }
                
                deckDiv.innerHTML = `
                    <div class="deck-emoji">🎴</div>
                    <div class="deck-level">Lv${level}</div>
                    <div class="deck-count">剩余: ${deckSize}</div>
                `;
                deckDiv.addEventListener('click', () => this.blindReserve(level));
                container.appendChild(deckDiv);
            }

            // 显示场面上的卡牌
            const cards = tableau[level.toString()] || [];
            cards.forEach(card => {
                const cardDiv = this.createCardElement(card);
                container.appendChild(cardDiv);
            });
        }

        // 显示稀有卡牌（Lv4）
        const rareDisplay = document.getElementById('rare-card-display');
        const rareDeckInfo = document.getElementById('rare-deck-info');
        rareDisplay.innerHTML = '';
        
        // 显示稀有牌堆
        if (rareDeckSize > 0) {
            const deckDiv = document.createElement('div');
            deckDiv.className = 'deck-card';
            deckDiv.innerHTML = `
                <div class="deck-emoji">🎴</div>
                <div class="deck-level">稀有牌堆</div>
                <div class="deck-count">剩余: ${rareDeckSize}</div>
            `;
            rareDisplay.appendChild(deckDiv);
        }
        
        // 显示稀有卡牌
        if (rareCard) {
            const cardDiv = this.createCardElement(rareCard, true);
            rareDisplay.appendChild(cardDiv);
        }
        
        // 显示传说卡牌（Lv5）
        const legendaryDisplay = document.getElementById('legendary-card-display');
        const legendaryDeckInfo = document.getElementById('legendary-deck-info');
        legendaryDisplay.innerHTML = '';
        
        // 显示传说牌堆
        if (legendaryDeckSize > 0) {
            const deckDiv = document.createElement('div');
            deckDiv.className = 'deck-card';
            deckDiv.innerHTML = `
                <div class="deck-emoji">🎴</div>
                <div class="deck-level">传说牌堆</div>
                <div class="deck-count">剩余: ${legendaryDeckSize}</div>
            `;
            legendaryDisplay.appendChild(deckDiv);
        }
        
        // 显示传说卡牌
        if (legendaryCard) {
            const cardDiv = this.createCardElement(legendaryCard, true);
            legendaryDisplay.appendChild(cardDiv);
        }
    }

    /**
     * 创建卡牌元素
     */
    createCardElement(card, isSpecial = false) {
        const cardDiv = document.createElement('div');
        const rarityClass = card.rarity === 'rare' ? 'rare-card' : 
                           (card.rarity === 'legendary' ? 'legendary-card' : 'pokemon-card');
        cardDiv.className = rarityClass;
        cardDiv.dataset.cardData = JSON.stringify(card);
        
        // 检查是否是当前玩家的回合，如果不是则添加禁用样式
        const isMyTurn = this.currentGameState && 
                         this.currentGameState.current_player === this.currentPlayerName;
        if (!isMyTurn) {
            cardDiv.classList.add('not-my-turn');
        }

        // 成本显示
        const costStr = Object.entries(card.cost || {})
            .filter(([_, amount]) => amount > 0)
            .map(([ball, amount]) => `${BALL_CONFIG[ball]?.emoji || ball}×${amount}`)
            .join(' ');

        // 永久球显示
        const permanentStr = Object.entries(card.permanent_balls || {})
            .filter(([_, amount]) => amount > 0)
            .map(([ball, amount]) => `${BALL_CONFIG[ball]?.emoji || ball}×${amount}`)
            .join(' ');

        // 进化信息显示（仅1/2级卡牌）
        let evolutionStr = '';
        if ((card.level === 1 || card.level === 2) && card.evolution_target && card.evolution_requirement) {
            // 将进化需求转换为显示文本
            const requirementStr = Object.entries(card.evolution_requirement)
                .map(([ball, amount]) => `${BALL_CONFIG[ball]?.emoji || ball}×${amount}`)
                .join(' ');
            evolutionStr = `<div class="card-evolution">🔄 ${card.evolution_target} (${requirementStr})</div>`;
        }

        cardDiv.innerHTML = `
            <div class="card-header">
                <div class="card-name-level">
                    <div class="card-name">${card.name}</div>
                    <div class="card-level">Lv${card.level}</div>
                </div>
                <div class="card-permanent">抵扣: ${permanentStr || '无'}</div>
            </div>
            <div class="card-cost">成本: ${costStr || '无'}</div>
            <div class="card-points">⭐ ${card.victory_points}VP</div>
            ${evolutionStr}
        `;

        cardDiv.addEventListener('click', () => this.selectCard(card, cardDiv));

        return cardDiv;
    }

    /**
     * 选择卡牌 - 显示买卡/预购选项
     */
    selectCard(card, element) {
        // 检查是否是当前玩家的回合
        const isMyTurn = this.currentGameState && 
                         this.currentGameState.current_player === this.currentPlayerName;
        
        if (!isMyTurn) {
            // 不是我的回合，不做任何操作
            return;
        }
        
        // 清除之前的选择
        document.querySelectorAll('.pokemon-card.selected, .rare-card.selected, .legendary-card.selected').forEach(el => {
            el.classList.remove('selected');
        });

        this.selectedCard = card;
        element.classList.add('selected');
        
        // 显示操作选项
        this.showCardActions(card);
    }
    
    /**
     * 显示卡牌操作选项（买卡/预购）
     */
    showCardActions(card) {
        const currentPlayer = this.currentGameState?.player_states?.[this.currentPlayerName];
        if (!currentPlayer) return;
        
        // 检查是否能买卡
        const canBuy = this.canAffordCard(card, currentPlayer);
        
        // 检查是否能预购
        // 1. 预购区必须<3张
        // 2. 卡牌等级必须<=3（Lv4/Lv5不可预购）
        const reserveSlotAvailable = (currentPlayer.reserved_cards?.length || 0) < 3;
        const canReserveLevel = card.level <= 3;
        const canReserve = reserveSlotAvailable && canReserveLevel;
        
        // 预购按钮的提示文本
        let reserveDisabledReason = '';
        if (!reserveSlotAvailable) {
            reserveDisabledReason = '(预购区已满)';
        } else if (!canReserveLevel) {
            reserveDisabledReason = '(稀有/传说不可预购)';
        }
        
        // 创建弹窗
        const modal = document.createElement('div');
        modal.className = 'card-action-modal';
        
        // 格式化成本显示
        const costDisplay = Object.entries(card.cost || {})
                .filter(([_, amount]) => amount > 0)
            .map(([ball, amount]) => `${BALL_CONFIG[ball]?.emoji || ball}×${amount}`)
            .join(' ') || '无';
        
        modal.innerHTML = `
            <div class="modal-content">
                <h3>选择操作: ${card.name}</h3>
                <p>成本: ${costDisplay}</p>
                <div class="modal-buttons">
                    <button id="buy-card-btn" class="btn btn-primary" ${!canBuy ? 'disabled' : ''}>
                        💰 买卡 ${!canBuy ? '(资源不足)' : ''}
                    </button>
                    <button id="reserve-card-btn" class="btn btn-secondary" ${!canReserve ? 'disabled' : ''}>
                        📦 预购 ${!canReserve ? reserveDisabledReason : ''}
                    </button>
                    <button id="cancel-card-btn" class="btn btn-danger">❌ 取消</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // 绑定事件
        document.getElementById('buy-card-btn').addEventListener('click', () => {
            if (canBuy) this.buyCard(card);
            document.body.removeChild(modal);
        });
        
        document.getElementById('reserve-card-btn').addEventListener('click', () => {
            if (canReserve) this.reserveCard(card);
            document.body.removeChild(modal);
        });
        
        document.getElementById('cancel-card-btn').addEventListener('click', () => {
            document.body.removeChild(modal);
        });
    }

    /**
     * 显示预购区卡牌操作选项（只有买卡按钮）
     */
    showReservedCardActions(card) {
        const currentPlayer = this.currentGameState?.player_states?.[this.currentPlayerName];
        if (!currentPlayer) return;
        
        // 检查是否能买卡
        const canBuy = this.canAffordCard(card, currentPlayer);
        
        // 创建弹窗
        const modal = document.createElement('div');
        modal.className = 'card-action-modal';
        
        // 格式化成本显示
        const costDisplay = Object.entries(card.cost || {})
                .filter(([_, amount]) => amount > 0)
            .map(([ball, amount]) => `${BALL_CONFIG[ball]?.emoji || ball}×${amount}`)
            .join(' ') || '无';
        
        modal.innerHTML = `
            <div class="modal-content">
                <h3>预购卡牌: ${card.name}</h3>
                <p>成本: ${costDisplay}</p>
                <div class="modal-buttons">
                    <button id="buy-card-btn" class="btn btn-primary" ${!canBuy ? 'disabled' : ''}>
                        💰 购买 ${!canBuy ? '(资源不足)' : ''}
                    </button>
                    <button id="cancel-card-btn" class="btn btn-danger">❌ 取消</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // 绑定事件
        document.getElementById('buy-card-btn').addEventListener('click', () => {
            if (canBuy) this.buyCard(card);
            document.body.removeChild(modal);
        });
        
        document.getElementById('cancel-card-btn').addEventListener('click', () => {
            document.body.removeChild(modal);
        });
    }

    /**
     * 检查是否能买得起卡牌
     */
    canAffordCard(card, playerState) {
        const playerBalls = playerState.balls || {};
        const permanentBalls = playerState.permanent_balls || {};
        const masterBalls = playerBalls['大师球'] || 0;
        
        let neededMasterBalls = 0;
        
        // 检查各颜色球成本
        for (const [ballType, cost] of Object.entries(card.cost || {})) {
            // 大师球成本单独处理
            if (ballType === '大师球') {
                neededMasterBalls += cost;
                continue;
            }
            
            const owned = playerBalls[ballType] || 0;
            const discount = permanentBalls[ballType] || 0;
            const actualCost = Math.max(0, cost - discount);
            
            // 如果该颜色的球不够，需要用大师球补
            if (owned < actualCost) {
                neededMasterBalls += (actualCost - owned);
            }
        }
        
        return masterBalls >= neededMasterBalls;
    }

    /**
     * 购买卡牌
     */
    buyCard(card) {
        // 使用唯一card_id而不是name（避免重名卡牌混淆）
        api.buyCard(this.currentRoomId, this.currentPlayerName, { card_id: card.card_id })
            .then(response => {
                if (response.success) {
                    showToast('购买成功！', 'success');
                    // 记录动作
                    this.currentActionSteps.push(`💰 购买卡牌: ${card.name} (Lv${card.level}, ${card.victory_points}VP)`);
                    
                    this.selectedCard = null;
                    this.hasPerformedMainAction = true;
                    this.checkAndShowEvolution();
                } else {
                    showToast(response.error || '购买失败', 'error');
                }
            })
            .catch(error => {
                showToast('操作失败: ' + error.message, 'error');
            });
    }
    
    /**
     * 预购卡牌
     */
    reserveCard(card) {
        // 使用唯一card_id而不是name（避免重名卡牌混淆）
        api.reserveCard(this.currentRoomId, this.currentPlayerName, { card: { card_id: card.card_id } })
            .then(response => {
                if (response.success) {
                    showToast('预购成功！', 'success');
                    // 记录动作
                    this.currentActionSteps.push(`📦 预购卡牌: ${card.name} (Lv${card.level})`);
                    
                    this.selectedCard = null;
                    this.hasPerformedMainAction = true;
                    this.waitingForReturnBalls = true;  // 预购会送大师球，可能需要放回
                } else {
                    showToast(response.error || '预购失败', 'error');
                }
            })
            .catch(error => {
                showToast('操作失败: ' + error.message, 'error');
            });
    }

    /**
     * 盲预购牌堆顶
     */
    blindReserve(level) {
        // 检查是否是当前玩家的回合
        const isMyTurn = this.currentGameState && 
                         this.currentGameState.current_player === this.currentPlayerName;
        
        if (!isMyTurn) {
            // 不是我的回合，不做任何操作
            return;
        }
        
        if (!confirm(`确定要盲预购Lv${level}牌堆顶的卡牌吗？`)) {
            return;
        }

        api.reserveCard(this.currentRoomId, this.currentPlayerName, { level: level, blind: true })
            .then(response => {
                if (response.success) {
                    showToast('盲预购成功！', 'success');
                    // 记录动作
                    this.currentActionSteps.push(`📦 盲预购: Lv${level}牌堆顶`);
                    
                    this.clearBallSelection();
                    this.hasPerformedMainAction = true;
                    this.waitingForReturnBalls = true;  // 预购会送大师球，可能需要放回
                } else {
                    showToast(response.error || '盲预购失败', 'error');
                }
            })
            .catch(error => {
                showToast('操作失败: ' + error.message, 'error');
            });
    }

    /**
     * 渲染玩家信息（按玩家顺序1-4独立显示）
     */
    renderPlayerInfo(playerStates, currentPlayer, players) {
        const container = document.getElementById('all-players-info');
        container.innerHTML = '';

        // 按照游戏中的玩家顺序（players数组）显示
        (players || Object.keys(playerStates)).forEach((playerName, index) => {
            const state = playerStates[playerName];
            if (!state) return;
            
            const isCurrentTurn = playerName === currentPlayer;
            const isMe = playerName === this.currentPlayerName;
            const playerNumber = index + 1;
            
            const playerCard = document.createElement('div');
            playerCard.className = 'card player-card';
            if (isCurrentTurn) playerCard.classList.add('current-turn-player');
            if (isMe) playerCard.classList.add('my-player');
            
            const titleHTML = `
                <h3>
                    ${isCurrentTurn ? '▶️ ' : ''}
                    玩家${playerNumber}${isMe ? '（我）' : ''}: ${playerName}
                    ${isMe ? ' 👤' : ''}
                </h3>
            `;
            
            const playerInfoDiv = this.createPlayerInfoElement(playerName, state, isCurrentTurn);
            
            playerCard.innerHTML = titleHTML;
            playerCard.appendChild(playerInfoDiv);
            
            // 移动端：点击标题展开/折叠详细信息
            const title = playerCard.querySelector('h3');
            title.addEventListener('click', () => {
                if (window.innerWidth <= 900) {
                    playerCard.classList.toggle('expanded');
                }
            });
            
            // 默认只展开自己的卡片（移动端）
            if (isMe && window.innerWidth <= 900) {
                playerCard.classList.add('expanded');
            }
            
            container.appendChild(playerCard);
        });
    }

    /**
     * 格式化卡牌信息（用于显示已拥有/预购卡牌）
     */
    formatCardInfo(card, isReserved = false, isClickable = false) {
        const miniCardClass = isClickable ? 'mini-card mini-card-clickable' : 'mini-card';
        const cardDataAttr = isClickable ? ` data-card='${JSON.stringify(card)}'` : '';
        
        let info = `<div class="${miniCardClass}"${cardDataAttr}>`;
        
        // 基本信息：名称 + 分数
        info += `<strong>${card.name}</strong> (${card.victory_points}VP)`;
        
        // 等级 - 干净显示，不加框
        if (card.level) {
            info += ` <span style="color: #bbb;">Lv${card.level}</span>`;
        }
        
        // 成本信息
        if (card.cost && Object.keys(card.cost).length > 0) {
            const costStr = Object.entries(card.cost)
                .filter(([_, amount]) => amount > 0)
                .map(([ball, amount]) => {
                    const config = BALL_CONFIG[ball];
                    return `${config?.emoji || ball}×${amount}`;
                })
                .join(' ');
            info += `<br><span style="color: #aaa; font-size: 0.9em;">成本: ${costStr}</span>`;
        }
        
        // 提供的抵扣颜色 - 加上"抵扣："文字说明
        if (card.permanent_balls && Object.keys(card.permanent_balls).length > 0) {
            const permanentStr = Object.entries(card.permanent_balls)
                .filter(([_, amount]) => amount > 0)
                .map(([ball, amount]) => {
                    const config = BALL_CONFIG[ball];
                    return `${config?.emoji || ball}${amount > 1 ? '×' + amount : ''}`;
                })
                .join('');
            info += ` <span style="color: #bbb;">抵扣：${permanentStr}</span>`;
        }
        
        // 进化信息（仅1/2级卡牌）
        if (card.evolution_target && card.evolution_requirement) {
            const evolutionReq = Object.entries(card.evolution_requirement)
                .map(([ball, amount]) => {
                    const config = BALL_CONFIG[ball];
                    return `${amount}${config?.emoji || ball}`;
                })
                .join('');
            info += `<br><small class="evolution-info">🔄 进化：${card.evolution_target}（${evolutionReq}进化）</small>`;
        }
        
        info += `</div>`;
        return info;
    }

    /**
     * 创建玩家信息元素
     */
    createPlayerInfoElement(playerName, state, isCurrentTurn) {
        const playerDiv = document.createElement('div');
        playerDiv.className = 'player-info';

        const nameClass = isCurrentTurn ? 'player-name current-turn' : 'player-name';
        const turnIndicator = isCurrentTurn ? '▶️ ' : '';

        // 检查是否是当前玩家自己
        const isMyself = playerName === this.currentPlayerName;
        // 检查是否是我的回合
        const isMyTurn = this.currentGameState && 
                         this.currentGameState.current_player === this.currentPlayerName;

        // 球信息 - 按固定顺序显示所有颜色（包括0）
        const ballOrder = ['黑', '粉', '黄', '蓝', '红', '大师球'];
        const ballBadges = ballOrder.map(ball => {
            const count = (state.balls || {})[ball] || 0;
            const config = BALL_CONFIG[ball];
            const opacity = count === 0 ? 'opacity: 0.3;' : '';
            return `<span class="gem-badge ${config?.class || ''}" style="${opacity}">${config?.emoji || ball} ${count}</span>`;
        }).join('');

        // 永久球（折扣）- 按固定顺序显示所有颜色（不包括大师球）
        const permanentOrder = ['黑', '粉', '黄', '蓝', '红'];
        const permanentBadges = permanentOrder.map(ball => {
            const count = (state.permanent_balls || {})[ball] || 0;
            const config = BALL_CONFIG[ball];
            const opacity = count === 0 ? 'opacity: 0.3;' : '';
            return `<span class="gem-badge ${config?.class || ''}" style="${opacity}">${config?.emoji || ball} ${count}</span>`;
        }).join('');

        // 已拥有卡牌
        const cardsDisplay = (state.display_area || [])
            .map(card => this.formatCardInfo(card))
            .join('') || '<div class="no-cards">暂无</div>';

        // 预定卡牌 - 只有在我的回合且是我自己的预购区时才可以点击
        const canClickReserved = isMyself && isMyTurn;
        const reservedDisplay = (state.reserved_cards || [])
            .map(card => this.formatCardInfo(card, true, canClickReserved))
            .join('') || '<div class="no-cards">暂无</div>';

        playerDiv.innerHTML = `
            <div class="${nameClass}">${turnIndicator}${playerName}</div>
            <div class="player-stats">
                <div class="stat-item">
                    <span class="stat-label">胜利点数:</span>
                    <span class="stat-value">${state.victory_points}VP</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">球数:</span>
                    <span class="stat-value">${Object.values(state.balls || {}).reduce((a, b) => a + b, 0)}</span>
                </div>
            </div>
            <div class="player-balls">
                <h4>🎨 持有球</h4>
                <div class="ball-list">${ballBadges || '无'}</div>
            </div>
            <div class="player-permanent">
                <h4>💎 永久折扣</h4>
                <div class="ball-list">${permanentBadges || '无'}</div>
            </div>
            <div class="player-cards">
                <h4>🎴 已拥有卡牌 (${(state.display_area || []).length}张)</h4>
                <div class="cards-grid">${cardsDisplay}</div>
            </div>
            <div class="player-reserved">
                <h4>📋 预定卡牌 (${(state.reserved_cards || []).length}/3)</h4>
                <div class="cards-grid cards-grid-reserved">${reservedDisplay}</div>
            </div>
        `;

        // 如果是我自己的预购区，添加点击事件委托
        if (canClickReserved) {
            const reservedGrid = playerDiv.querySelector('.cards-grid-reserved');
            if (reservedGrid) {
                reservedGrid.addEventListener('click', (e) => {
                    const miniCard = e.target.closest('.mini-card-clickable');
                    if (miniCard) {
                        const cardData = miniCard.dataset.card;
                        if (cardData) {
                            try {
                                const card = JSON.parse(cardData);
                                this.showReservedCardActions(card);
                            } catch (error) {
                                console.error('解析卡牌数据失败:', error);
                            }
                        }
                    }
                });
            }
        }

        return playerDiv;
    }

    /**
     * 更新游戏界面
     */
    updateGameUI(gameState) {
        this.currentGameState = gameState;

        // 检测行动切换，显示上一个玩家的行动总结
        if (this.lastActionPlayer && this.lastActionPlayer !== gameState.current_player) {
            // 行动切换了，显示上一个玩家的行动总结
            const isMyAction = this.lastActionPlayer === this.currentPlayerName;
            
            // 只有当上一个行动不是我的时候才显示总结（我的行动在autoEndAction中已经显示了）
            if (!isMyAction) {
                // 其他玩家（包括AI）的行动结束，显示详细总结
                // 从游戏状态中获取上一个玩家的行动记录
                this.showActionEndNotificationForOthers(this.lastActionPlayer, gameState);
            }
            
            // 清空步骤记录
            this.clearActionSteps();
        }
        this.lastActionPlayer = gameState.current_player;

        // 更新回合数和胜利目标显示
        document.getElementById('turn-number').textContent = gameState.turn_number || 1;
        document.getElementById('victory-goal').textContent = gameState.victory_points || '-';  // 后端应该总是返回
        document.getElementById('total-players').textContent = gameState.players?.length || '-';  // 后端应该总是返回

        // 渲染球池
        this.renderBallPool(gameState.ball_pool || {});

        // 渲染桌面卡牌
        this.renderTableauCards(
            gameState.tableau || {},
            gameState.lv1_deck_size || 0,
            gameState.lv2_deck_size || 0,
            gameState.lv3_deck_size || 0,
            gameState.rare_card,
            gameState.legendary_card,
            gameState.rare_deck_size || 0,
            gameState.legendary_deck_size || 0
        );

        // 渲染玩家信息
        this.renderPlayerInfo(gameState.player_states || {}, gameState.current_player, gameState.players);

        // 更新当前玩家提示
        const isMyTurn = gameState.current_player === this.currentPlayerName;
        document.getElementById('current-player-name').textContent = gameState.current_player || '未知';
        
        // 控制按钮可用性（注意：已移除"结束回合"按钮，回合自动结束）
        const takeGemsBtn = document.getElementById('take-gems-btn');
        if (takeGemsBtn) {
            takeGemsBtn.disabled = !isMyTurn || this.selectedBalls.length === 0;
        }
        
        // 检查是否需要放回球
        if (isMyTurn && gameState.player_states[this.currentPlayerName]?.needs_return_balls) {
            this.showReturnBallsModal();
        } else if (this.waitingForReturnBalls && isMyTurn) {
            // 拿球后不需要放回球，继续进化/结束回合流程
            this.waitingForReturnBalls = false;
            this.checkAndShowEvolution();
        }
    }

    /**
     * 拿取球
     */
    async takeBalls() {
        if (this.selectedBalls.length === 0) {
            showToast('请先选择球', 'error');
            return;
        }

        try {
            const response = await api.takeGems(this.currentRoomId, this.currentPlayerName, this.selectedBalls);
            if (response.success) {
                showToast('成功拿取球！', 'success');
                // 记录动作
                const ballsText = this.selectedBalls.map(ball => {
                    const config = BALL_CONFIG[ball];
                    return config?.emoji || ball;
                }).join(' ');
                this.currentActionSteps.push(`🎨 拿取球: ${ballsText}`);
                
                this.clearBallSelection();
                this.hasPerformedMainAction = true;
                this.waitingForReturnBalls = true;  // 设置标志，等待检查是否需要放回球
            } else {
                showToast(response.error || '拿取失败', 'error');
            }
        } catch (error) {
            showToast('操作失败: ' + error.message, 'error');
        }
    }

    /**
     * 检查并自动触发进化或结束行动
     */
    checkAndShowEvolution() {
        setTimeout(async () => {
            const currentPlayer = this.currentGameState?.player_states?.[this.currentPlayerName];
            if (!currentPlayer) return;
            
            // 检查是否可以进化
            const canEvolve = this.checkCanEvolve(currentPlayer);
            
            if (canEvolve && !this.hasPerformedEvolution) {
                // 自动弹出进化选择界面
                await this.executeEvolution();
            } else {
                // 不能进化或已进化，自动结束行动
                await this.autoEndAction();
            }
        }, 1000);  // 等待1秒让游戏状态更新
    }
    
    /**
     * 检查玩家是否可以进化
     */
    checkCanEvolve(playerState) {
        const displayCards = playerState.display_area || [];
        const reservedCards = playerState.reserved_cards || [];
        const permanentBalls = playerState.permanent_balls || {};
        const gameState = this.currentGameState;
        
        // 收集桌面上所有可用的卡牌（不在牌堆里）
        const availableCards = [];
        
        // 1. 桌面上显示的卡牌
        if (gameState && gameState.tableau) {
            for (const [tier, cards] of Object.entries(gameState.tableau)) {
                if (Array.isArray(cards)) {
                    availableCards.push(...cards);
                }
            }
        }
        
        // 2. 稀有和传说卡牌
        if (gameState && gameState.rare_card) {
            availableCards.push(gameState.rare_card);
        }
        if (gameState && gameState.legendary_card) {
            availableCards.push(gameState.legendary_card);
        }
        
        // 3. 我的预购区卡牌
        availableCards.push(...reservedCards);
        
        // 检查已拥有卡牌中是否有可以进化的
        for (const card of displayCards) {
            if (!card.evolution_target) continue;  // 没有进化目标
            if (card.level >= 3) continue;  // Lv3及以上不能进化
            
            // 检查进化目标卡牌是否在桌面或预购区
            const targetExists = availableCards.some(c => c.name === card.evolution_target);
            if (!targetExists) {
                console.log(`❌ ${card.name}的进化目标${card.evolution_target}不在桌面或预购区`);
                continue;  // 进化目标不存在，跳过
            }
            
            // 检查是否有足够的永久球
            const requiredBalls = card.evolution_requirement || {};
            let hasEnoughBalls = true;
            
            for (const [ballType, required] of Object.entries(requiredBalls)) {
                if ((permanentBalls[ballType] || 0) < required) {
                    hasEnoughBalls = false;
                    break;
                }
            }
            
            if (hasEnoughBalls) {
                console.log(`✅ ${card.name}可以进化为${card.evolution_target}`);
                return true;
            }
        }
        
        return false;
    }
    
    /**
     * 执行进化
     */
    async executeEvolution() {
        const currentPlayer = this.currentGameState?.player_states?.[this.currentPlayerName];
        if (!currentPlayer) {
            await this.autoEndAction();
            return;
        }
        
        const displayCards = currentPlayer.display_area || [];
        const permanentBalls = currentPlayer.permanent_balls || {};
        
        // 找出所有可以进化的卡牌
        const evolvableCards = displayCards.filter(card => {
            if (!card.evolution_target || card.level >= 3) return false;
            
            const requiredBalls = card.evolution_requirement || {};
            for (const [ballType, required] of Object.entries(requiredBalls)) {
                if ((permanentBalls[ballType] || 0) < required) return false;
            }
            return true;
        });
        
        if (evolvableCards.length === 0) {
            // 没有可进化的卡牌，自动结束行动
            await this.autoEndAction();
            return;
        }
        
        // 显示选择框（包含跳过选项）
        const cardId = await this.showEvolutionChoice(evolvableCards);
        
        if (!cardId) {
            // 用户选择跳过进化，自动结束行动
            await this.autoEndAction();
            return;
        }
        
        const cardToEvolve = evolvableCards.find(c => c.card_id === cardId);
        
        // 调用进化API（使用唯一card_id而不是name）
        try {
            const response = await api.evolveCard(this.currentRoomId, {
                player_name: this.currentPlayerName,
                card_id: cardToEvolve.card_id
            });
            
            if (response.success) {
                // 显示醒目的进化成功提示（进化是独立阶段，不计入回合动作）
                this.showEvolutionNotification(cardToEvolve.name, cardToEvolve.evolution_target);
                this.hasPerformedEvolution = true;
            } else {
                showToast(response.error || '进化失败', 'error');
            }
        } catch (error) {
            showToast('操作失败: ' + error.message, 'error');
        }
        
        // 进化完成后，自动结束行动
        await this.autoEndAction();
    }
    
    /**
     * 显示进化选择框
     */
    async showEvolutionChoice(cards) {
        return new Promise((resolve) => {
            const modal = document.createElement('div');
            modal.className = 'card-action-modal';
            
            // 使用card_id作为唯一标识，但显示name给用户看
            const cardsHtml = cards.map(card => `
                <div class="evolution-option" data-card-id="${card.card_id}">
                    ${card.name} → ${card.evolution_target}
                </div>
            `).join('');
            
            modal.innerHTML = `
                <div class="modal-content">
                    <h3>🔄 可以进化卡牌</h3>
                    <p style="margin: 10px 0; color: #bbb;">选择一张卡牌进化，或跳过进化直接结束行动</p>
                    <div class="evolution-options">
                        ${cardsHtml}
                    </div>
                    <button id="skip-evolution-btn" class="btn btn-secondary">⏭️ 跳过进化</button>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            // 绑定事件
            modal.querySelectorAll('.evolution-option').forEach(option => {
                option.addEventListener('click', () => {
                    const cardId = parseInt(option.dataset.cardId);
                    document.body.removeChild(modal);
                    resolve(cardId);
                });
            });
            
            document.getElementById('skip-evolution-btn').addEventListener('click', () => {
                document.body.removeChild(modal);
                resolve(null);  // 返回null表示跳过进化
            });
        });
    }

    /**
     * 自动结束行动（在完成动作和进化检查后调用）
     */
    async autoEndAction() {
        try {
            const response = await api.endTurn(this.currentRoomId, this.currentPlayerName);
            if (response.success) {
                // 显示醒目的行动结束提示
                this.showActionEndNotification(this.currentPlayerName);
                this.clearBallSelection();
                this.selectedCard = null;
                // 重置行动状态
                this.hasPerformedMainAction = false;
                this.hasPerformedEvolution = false;
            } else {
                showToast(response.error || '操作失败', 'error');
            }
        } catch (error) {
            showToast('操作失败: ' + error.message, 'error');
        }
    }
    
    /**
     * 显示进化成功通知
     */
    showEvolutionNotification(fromCard, toCard) {
        // 移除旧的通知（如果存在）
        const oldNotification = document.getElementById('game-notification');
        if (oldNotification) {
            oldNotification.remove();
        }
        
        // 创建全屏通知
        const notification = document.createElement('div');
        notification.id = 'game-notification'; // 固定ID，用于覆盖
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%);
            color: white;
            padding: 40px 60px;
            border-radius: 20px;
            font-size: 1.8em;
            font-weight: bold;
            text-align: center;
            z-index: 10001;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            animation: slideInFromTop 2.5s ease-in-out;
        `;
        notification.innerHTML = `
            <div style="font-size: 1.5em; margin-bottom: 10px;">⚡</div>
            <div>进化成功！</div>
            <div style="font-size: 0.8em; margin-top: 15px; color: #ffeaa7;">
                ${fromCard} → ${toCard}
            </div>
        `;
        
        // 添加动画样式
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideInFromTop {
                0% { opacity: 0; transform: translateX(-50%) translateY(-50px); }
                20% { opacity: 1; transform: translateX(-50%) translateY(0); }
                80% { opacity: 1; transform: translateX(-50%) translateY(0); }
                100% { opacity: 0; transform: translateX(-50%) translateY(-50px); }
            }
        `;
        document.head.appendChild(style);
        
        document.body.appendChild(notification);
        
        // 2.5秒后自动移除
        setTimeout(() => {
            if (notification.parentNode) {
                document.body.removeChild(notification);
            }
            if (style.parentNode) {
                document.head.removeChild(style);
            }
        }, 2500);
    }
    
    /**
     * 显示其他玩家（包括AI）的行动结束通知（详细版）
     */
    showActionEndNotificationForOthers(playerName, gameState) {
        // 判断是否是AI
        const isAI = playerName.includes('机器人') || playerName.includes('AI') || playerName.includes('训练家');
        const icon = isAI ? '🤖' : '👤';
        
        // 从游戏状态中获取该玩家的last_action
        let actionsHTML = '';
        if (gameState && gameState.player_states && gameState.player_states[playerName]) {
            const lastAction = gameState.player_states[playerName].last_action;
            if (lastAction && lastAction.trim() !== '') {
                // 将last_action按"→"分割成多个步骤
                const steps = lastAction.split(' → ').filter(s => s.trim() !== '');
                actionsHTML = steps.map(step => 
                    `<div style="margin: 8px 0; font-size: 0.65em; text-align: left;">${step}</div>`
                ).join('');
            } else {
                // 没有行动记录
                actionsHTML = '<div style="margin: 8px 0; font-size: 0.65em; opacity: 0.8;">本次行动无步骤</div>';
            }
        } else {
            // 找不到游戏状态或玩家状态，显示通用信息
            actionsHTML = isAI 
                ? '<div style="margin: 8px 0; font-size: 0.65em; text-align: left;">🤖 AI已完成行动决策</div>'
                : '<div style="margin: 8px 0; font-size: 0.65em; text-align: left;">👤 玩家已完成行动</div>';
        }
        
        // 移除旧的通知（如果存在）
        const oldNotification = document.getElementById('game-notification');
        if (oldNotification) {
            oldNotification.remove();
        }
        
        // 创建全屏通知
        const notification = document.createElement('div');
        notification.id = 'game-notification'; // 固定ID，用于覆盖
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 35px 50px;
            border-radius: 20px;
            font-size: 1.8em;
            font-weight: bold;
            text-align: center;
            z-index: 10001;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            animation: slideInFromTop 4s ease-in-out;
            max-width: 600px;
        `;
        notification.innerHTML = `
            <div style="font-size: 1.3em; margin-bottom: 10px;">${icon}</div>
            <div style="margin-bottom: 20px;">${playerName} 的行动结束</div>
            <div style="background: rgba(0, 0, 0, 0.3); padding: 15px; border-radius: 10px;">
                <div style="font-size: 0.6em; margin-bottom: 10px; color: #ffeaa7;">本次行动：</div>
                ${actionsHTML}
            </div>
        `;
        
        // 添加动画样式
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideInFromTop {
                0% { opacity: 0; transform: translateX(-50%) translateY(-50px); }
                15% { opacity: 1; transform: translateX(-50%) translateY(0); }
                85% { opacity: 1; transform: translateX(-50%) translateY(0); }
                100% { opacity: 0; transform: translateX(-50%) translateY(-50px); }
            }
        `;
        document.head.appendChild(style);
        
        document.body.appendChild(notification);
        
        // 4秒后自动移除
        setTimeout(() => {
            if (notification.parentNode) {
                document.body.removeChild(notification);
            }
            if (style.parentNode) {
                document.head.removeChild(style);
            }
        }, 4000);
    }
    
    /**
     * 显示行动结束通知（当前玩家）
     */
    showActionEndNotification(playerName) {
        // 准备动作列表
        const actionsHTML = this.currentActionSteps.length > 0 
            ? this.currentActionSteps.map(action => 
                `<div style="margin: 8px 0; font-size: 0.65em; text-align: left;">${action}</div>`
              ).join('')
            : '<div style="margin: 8px 0; font-size: 0.65em; opacity: 0.8;">本次行动无步骤</div>';
        
        // 移除旧的通知（如果存在）
        const oldNotification = document.getElementById('game-notification');
        if (oldNotification) {
            oldNotification.remove();
        }
        
        // 创建全屏通知
        const notification = document.createElement('div');
        notification.id = 'game-notification'; // 固定ID，用于覆盖
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 35px 50px;
            border-radius: 20px;
            font-size: 1.8em;
            font-weight: bold;
            text-align: center;
            z-index: 10001;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            animation: slideInFromTop 4s ease-in-out;
            max-width: 600px;
        `;
        notification.innerHTML = `
            <div style="font-size: 1.3em; margin-bottom: 10px;">🏁</div>
            <div style="margin-bottom: 20px;">${playerName} 的行动结束</div>
            <div style="background: rgba(0, 0, 0, 0.3); padding: 15px; border-radius: 10px;">
                <div style="font-size: 0.6em; margin-bottom: 10px; color: #ffeaa7;">本次行动：</div>
                ${actionsHTML}
            </div>
        `;
        
        // 添加动画样式
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideInFromTop {
                0% { opacity: 0; transform: translateX(-50%) translateY(-50px); }
                15% { opacity: 1; transform: translateX(-50%) translateY(0); }
                85% { opacity: 1; transform: translateX(-50%) translateY(0); }
                100% { opacity: 0; transform: translateX(-50%) translateY(-50px); }
            }
        `;
        document.head.appendChild(style);
        
        document.body.appendChild(notification);
        
        // 4秒后自动移除
        setTimeout(() => {
            if (notification.parentNode) {
                document.body.removeChild(notification);
            }
            if (style.parentNode) {
                document.head.removeChild(style);
            }
        }, 4000);
        
        // 注意：动作记录会在下一个行动开始时自动清空（在updateGameUI中检测行动切换）
    }

    /**
     * 结束行动（手动调用，已废弃）
     */
    async endTurn() {
        // 此方法已废弃，保留仅为兼容性
        await this.autoEndAction();
    }

    /**
     * 显示放回球的UI
     */
    showReturnBallsModal() {
        // 检查是否已经有弹窗
        if (document.getElementById('return-balls-modal')) {
            return;  // 已经有弹窗，不重复创建
        }
        
        const currentPlayer = this.currentGameState?.player_states?.[this.currentPlayerName];
        if (!currentPlayer) return;
        
        const totalBalls = Object.values(currentPlayer.balls || {}).reduce((a, b) => a + b, 0);
        const neededReturn = totalBalls - 10;
        
        // 初始化要放回的球
        this.ballsToReturn = {};
        const ballOrder = ['黑', '粉', '黄', '蓝', '红', '大师球'];
        ballOrder.forEach(ball => {
            this.ballsToReturn[ball] = 0;
        });
        
        // 创建弹窗
        const modal = document.createElement('div');
        modal.id = 'return-balls-modal';
        modal.className = 'card-action-modal';
        modal.style.zIndex = '10000';
        
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 600px;">
                <h3>⚠️ 球数超过上限</h3>
                <p style="color: #e74c3c; font-weight: bold;">
                    当前球数：${totalBalls}个 | 需要放回：${neededReturn}个
                </p>
                
                <div style="margin: 20px 0;">
                    <h4>当前持有球：</h4>
                    <div id="current-balls-display" style="display: flex; justify-content: center; gap: 10px; flex-wrap: nowrap; overflow-x: auto;"></div>
                </div>
                
                <div style="margin: 20px 0;">
                    <h4>选择要放回的球：</h4>
                    <div id="return-balls-display" style="display: flex; justify-content: center; gap: 10px; flex-wrap: nowrap; overflow-x: auto;"></div>
                </div>
                
                <div style="margin: 15px 0; padding: 10px; background: rgba(0,0,0,0.3); border-radius: 5px;">
                    <span>已选择放回：</span>
                    <span id="selected-return-count" style="color: #f1c40f; font-weight: bold;">0</span>
                    <span> / ${neededReturn} 个</span>
                </div>
                
                <div class="modal-buttons">
                    <button id="return-balls-btn" class="btn btn-primary" disabled>
                        ✅ 确认放回
                    </button>
                    <button id="clear-return-btn" class="btn btn-secondary">
                        🔄 清除选择
                    </button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // 渲染球的显示和控制
        this.renderReturnBallsDisplay(currentPlayer.balls, neededReturn);
        
        // 绑定事件
        document.getElementById('return-balls-btn').addEventListener('click', () => this.executeReturnBalls());
        document.getElementById('clear-return-btn').addEventListener('click', () => this.clearReturnSelection(currentPlayer.balls, neededReturn));
    }

    /**
     * 渲染放回球的显示
     */
    renderReturnBallsDisplay(playerBalls, neededReturn) {
        const currentBallsDiv = document.getElementById('current-balls-display');
        const returnBallsDiv = document.getElementById('return-balls-display');
        
        const ballOrder = ['黑', '粉', '黄', '蓝', '红', '大师球'];
        
        // 渲染当前持有球（横向排列）
        currentBallsDiv.innerHTML = ballOrder.map(ball => {
            const count = playerBalls[ball] || 0;
            const config = BALL_CONFIG[ball];
            return `
                <div style="display: flex; flex-direction: column; align-items: center; min-width: 60px;">
                    <div style="font-size: 2em;">${config?.emoji || ball}</div>
                    <div style="font-size: 0.85em; color: #bbb;">${config?.name || ball}</div>
                    <div style="font-size: 1.2em; font-weight: bold; color: #f1c40f;">${count}</div>
                </div>
            `;
        }).join('');
        
        // 渲染要放回的球（带上下箭头，横向排列）
        returnBallsDiv.innerHTML = ballOrder.map(ball => {
            const maxCount = playerBalls[ball] || 0;
            const config = BALL_CONFIG[ball];
            const currentReturn = this.ballsToReturn[ball] || 0;
            
            return `
                <div style="display: flex; flex-direction: column; align-items: center; min-width: 65px;">
                    <div style="font-size: 2em;">${config?.emoji || ball}</div>
                    <div style="font-size: 0.85em; color: #bbb; margin-bottom: 8px;">${config?.name || ball}</div>
                    <div style="display: flex; flex-direction: column; align-items: center; gap: 3px;">
                        <button class="ball-increase-btn" data-ball="${ball}" ${maxCount === 0 ? 'disabled' : ''}
                            style="padding: 3px 10px; cursor: pointer; border: none; background: #27ae60; color: white; border-radius: 4px; font-size: 1em; min-width: 40px;">
                            ▲
                        </button>
                        <span style="font-size: 1.3em; font-weight: bold; color: #f1c40f; min-width: 40px; text-align: center; line-height: 1.2;">${currentReturn}</span>
                        <button class="ball-decrease-btn" data-ball="${ball}" ${currentReturn === 0 ? 'disabled' : ''}
                            style="padding: 3px 10px; cursor: pointer; border: none; background: #e74c3c; color: white; border-radius: 4px; font-size: 1em; min-width: 40px;">
                            ▼
                        </button>
                    </div>
                </div>
            `;
        }).join('');
        
        // 绑定增加/减少按钮事件
        returnBallsDiv.querySelectorAll('.ball-increase-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const ball = btn.dataset.ball;
                this.adjustReturnBall(ball, 1, playerBalls, neededReturn);
            });
        });
        
        returnBallsDiv.querySelectorAll('.ball-decrease-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const ball = btn.dataset.ball;
                this.adjustReturnBall(ball, -1, playerBalls, neededReturn);
            });
        });
    }

    /**
     * 调整要放回的球数量
     */
    adjustReturnBall(ball, delta, playerBalls, neededReturn) {
        const maxCount = playerBalls[ball] || 0;
        const currentReturn = this.ballsToReturn[ball] || 0;
        const totalReturn = Object.values(this.ballsToReturn).reduce((a, b) => a + b, 0);
        
        // 计算新值
        let newValue = currentReturn + delta;
        
        // 检查限制
        if (newValue < 0) newValue = 0;
        if (newValue > maxCount) newValue = maxCount;
        
        // 如果增加，检查是否超过需要放回的总数
        if (delta > 0 && totalReturn >= neededReturn) {
            showToast('已达到需要放回的数量', 'warning');
            return;
        }
        
        this.ballsToReturn[ball] = newValue;
        
        // 重新渲染
        this.renderReturnBallsDisplay(playerBalls, neededReturn);
        this.updateReturnBallsButton(neededReturn);
    }

    /**
     * 更新放回按钮状态
     */
    updateReturnBallsButton(neededReturn) {
        const totalReturn = Object.values(this.ballsToReturn).reduce((a, b) => a + b, 0);
        const countSpan = document.getElementById('selected-return-count');
        const returnBtn = document.getElementById('return-balls-btn');
        
        if (countSpan) {
            countSpan.textContent = totalReturn;
            if (totalReturn === neededReturn) {
                countSpan.style.color = '#2ecc71';  // 绿色表示正确
            } else {
                countSpan.style.color = '#f1c40f';  // 黄色
            }
        }
        
        if (returnBtn) {
            returnBtn.disabled = (totalReturn !== neededReturn);
        }
    }

    /**
     * 清除放回选择
     */
    clearReturnSelection(playerBalls, neededReturn) {
        const ballOrder = ['黑', '粉', '黄', '蓝', '红', '大师球'];
        ballOrder.forEach(ball => {
            this.ballsToReturn[ball] = 0;
        });
        this.renderReturnBallsDisplay(playerBalls, neededReturn);
        this.updateReturnBallsButton(neededReturn);
    }

    /**
     * 执行放回球
     */
    async executeReturnBalls() {
        try {
            const response = await api.returnBalls(this.currentRoomId, this.currentPlayerName, this.ballsToReturn);
            if (response.success) {
                // 记录动作
                const returnedBalls = Object.entries(this.ballsToReturn)
                    .filter(([_, count]) => count > 0)
                    .map(([ball, count]) => {
                        const config = BALL_CONFIG[ball];
                        return `${config?.emoji || ball}×${count}`;
                    })
                    .join(' ');
                this.currentActionSteps.push(`↩️ 放回球: ${returnedBalls}`);
                
                showToast('成功放回球！', 'success');
                // 关闭弹窗
                const modal = document.getElementById('return-balls-modal');
                if (modal) {
                    document.body.removeChild(modal);
                }
                // 清除等待标志
                this.waitingForReturnBalls = false;
                // 检查进化
                this.checkAndShowEvolution();
            } else {
                showToast(response.error || '放回球失败', 'error');
            }
        } catch (error) {
            showToast('操作失败: ' + error.message, 'error');
        }
    }
    
    /**
     * 清空当前行动步骤记录（当轮到新玩家时）
     */
    clearActionSteps() {
        this.currentActionSteps = [];
    }

    /**
     * 暂停轮询（显示通知时使用）
     */
    pausePollingForNotification() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
            
            // 4秒后恢复轮询
            setTimeout(() => {
                if (this.currentRoomId && this.currentPlayerName) {
                    this.pollingInterval = setInterval(() => {
                        this.pollGameState();
                    }, 2000);
                }
            }, 4000);
        }
    }
    
    /**
     * 开始轮询游戏状态
     */
    startPolling(roomId, playerName) {
        this.currentRoomId = roomId;
        this.currentPlayerName = playerName;
        
        // 立即获取一次
        this.pollGameState();
        
        // 每2秒轮询一次
        this.pollingInterval = setInterval(() => {
            this.pollGameState();
        }, 2000);
    }

    /**
     * 停止轮询
     */
    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }

    /**
     * 轮询游戏状态
     */
    async pollGameState() {
        try {
            const response = await api.getGameState(this.currentRoomId);
            if (response.status === 'playing') {
                this.updateGameUI(response);
                
                // 检查游戏是否结束
                if (response.game_over) {
                    this.stopPolling();
                    // 清除游戏会话
                    if (typeof clearGameSession === 'function') {
                        clearGameSession();
                    }
                    showToast(`游戏结束！胜者: ${response.winner || '未知'}`, 'success');
                }
            }
        } catch (error) {
            console.error('轮询游戏状态失败:', error);
        }
    }
}

// 全局实例
const gameUI = new GameUI();

// showToast函数在main.js中定义
