/**
 * 规则和卡库弹窗功能
 */

// 游戏规则内容
const GAME_RULES = `
<h3>🎯 游戏目标</h3>
<p>收集宝可梦卡牌，总分数⭐率先达到<strong>胜利分数</strong>（默认18分）即可获胜！</p>

<h3>⚡ 回合流程</h3>
<p>每个回合，你必须选择以下<strong>3个动作之一</strong>：</p>
<ol>
    <li><strong>拿球</strong>：从球池拿取精灵球
        <ul>
            <li>同色2个：需要拿之前球池中该颜色≥4个</li>
            <li>不同色3个：拿3种不同颜色各1个</li>
            <li>持球上限10个，超过需放回</li>
        </ul>
    </li>
    <li><strong>买卡</strong>：用球购买宝可梦卡牌
        <ul>
            <li>消耗精灵球换取卡牌</li>
            <li>获得分数和永久折扣</li>
            <li>大师球(🟣)可替代任意颜色球1个(赖子)</li>
        </ul>
    </li>
    <li><strong>预购</strong>：预定卡牌到手牌（最多3张）
        <ul>
            <li>可预购场上卡或牌堆顶（盲预购）</li>
            <li>每次预购获得1个大师球</li>
            <li>稀有/传说卡不可预购</li>
        </ul>
    </li>
</ol>

<h3>🔄 进化系统</h3>
<p>完成回合后，可以最多选择进化1张拥有的卡牌：</p>
<ul>
    <li>1级→2级→3级的进化链</li>
    <li>需要场上或预购区有进化目标</li>
    <li>需要满足特定颜色的<strong>永久折扣</strong>数量要求（不是消耗手中的球）</li>
    <li>每回合最多进化1次</li>
</ul>

<h3>💎 永久折扣</h3>
<p>每张卡牌提供永久折扣，用于：</p>
<ul>
    <li><strong>买卡</strong>：减少需要支付的球</li>
    <li><strong>进化</strong>：作为进化条件</li>
</ul>

<h3>🏆 游戏结束</h3>
<ul>
    <li>有玩家达到胜利分数→进入最后一轮</li>
    <li>最后一个玩家结束回合→游戏结束</li>
    <li>排名：分数高者胜，同分后手优先</li>
</ul>

<h3>💡 小贴士</h3>
<ul>
    <li>优先收集同色卡牌，叠加折扣效果</li>
    <li>预购可以抢夺对手想要的卡牌</li>
    <li>不要忘记进化，进化卡分数更高</li>
    <li>合理使用大师球，关键时刻很有用</li>
</ul>
`;

// 球类型配置
const BALL_COLORS = {
    '黑': { emoji: '⚫', name: '黑球' },
    '粉': { emoji: '🌸', name: '粉球' },
    '黄': { emoji: '🟡', name: '黄球' },
    '蓝': { emoji: '🔵', name: '蓝球' },
    '红': { emoji: '🔴', name: '红球' },
    '大师球': { emoji: '🟣', name: '大师球' }
};

// 显示规则弹窗
function showRulesModal() {
    document.getElementById('rules-content').innerHTML = GAME_RULES;
    document.getElementById('rules-modal').style.display = 'flex';
}

// 关闭规则弹窗
function closeRulesModal() {
    document.getElementById('rules-modal').style.display = 'none';
}

// 显示卡库弹窗
async function showCardsModal() {
    const modal = document.getElementById('cards-modal');
    const content = document.getElementById('cards-content');
    
    content.innerHTML = '<p style="text-align: center;">加载中...</p>';
    modal.style.display = 'flex';
    
    try {
        // 从API加载卡牌数据
        const response = await fetch('/api/cards');
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || '加载失败');
        }
        
        const cards = data.cards;
        
        // 按等级和颜色分组
        const cardsByLevelAndColor = {
            1: { '黑': [], '粉': [], '黄': [], '蓝': [], '红': [] },
            2: { '黑': [], '粉': [], '黄': [], '蓝': [], '红': [] },
            3: { '黑': [], '粉': [], '黄': [], '蓝': [], '红': [] },
            4: { '黑': [], '粉': [], '黄': [], '蓝': [], '红': [] },
            5: { '黑': [], '粉': [], '黄': [], '蓝': [], '红': [] }
        };
        
        // 将卡牌分配到对应的等级和颜色
        cards.forEach(card => {
            const level = card.level;
            // 根据永久球颜色分类
            const color = Object.keys(card.permanent)[0] || '黑'; // 默认黑色
            if (cardsByLevelAndColor[level] && cardsByLevelAndColor[level][color]) {
                cardsByLevelAndColor[level][color].push(card);
            }
        });
        
        // 生成HTML - 按颜色列排列
        let html = '';
        const colorOrder = ['黑', '粉', '黄', '蓝', '红'];
        const levelOrder = [5, 4, 3, 2, 1]; // L5 → L4 → L3 → L2 → L1
        
        for (const level of levelOrder) {
            const levelCards = cardsByLevelAndColor[level];
            
            // 计算该等级总卡数
            let totalCards = 0;
            colorOrder.forEach(color => {
                totalCards += levelCards[color].length;
            });
            
            if (totalCards === 0) continue;
            
            const levelName = level <= 3 ? `等级 ${level}` : (level === 4 ? '稀有 (Lv4)' : '传说 (Lv5)');
            html += `<h3>🎴 ${levelName} <span style="opacity: 0.7; font-size: 0.9em;">(${totalCards}张)</span></h3>`;
            html += '<div class="cards-library-grid-compact">';
            
            // 找出最大行数
            let maxRows = 0;
            colorOrder.forEach(color => {
                maxRows = Math.max(maxRows, levelCards[color].length);
            });
            
            // 按行生成，每行5张（5种颜色）
            for (let row = 0; row < maxRows; row++) {
                colorOrder.forEach(color => {
                    const cardsInColor = levelCards[color];
                    const card = cardsInColor[row];
                    
                    if (card) {
                        const costStr = Object.entries(card.cost)
                            .filter(([_, amount]) => amount > 0)
                            .map(([ball, amount]) => `${BALL_COLORS[ball]?.emoji || ball}×${amount}`)
                            .join(' ');
                        
                        const permanentStr = Object.entries(card.permanent)
                            .filter(([_, amount]) => amount > 0)
                            .map(([ball, amount]) => `${BALL_COLORS[ball]?.emoji || ball}×${amount}`)
                            .join(' ');
                        
                        let evolutionStr = '';
                        if (card.evolution_target && level <= 2) {
                            const evolReqStr = Object.entries(card.evolution_requirement)
                                .map(([ball, amount]) => `${BALL_COLORS[ball]?.emoji || ball}×${amount}`)
                                .join(' ');
                            evolutionStr = `<div class="card-evo-info">🔄 ${card.evolution_target} (${evolReqStr})</div>`;
                        }
                        
                        html += `
                            <div class="library-card-compact">
                                <div class="library-card-name">${card.name}</div>
                                <div class="library-card-cost">💰消耗: ${costStr || '无'}</div>
                                <div class="library-card-permanent">💎抵扣: ${permanentStr || '无'}</div>
                                <div class="library-card-points">⭐分数: ${card.victory_points}VP</div>
                                ${evolutionStr}
                            </div>
                        `;
                    } else {
                        // 空白占位
                        html += `<div class="library-card-compact library-card-empty"></div>`;
                    }
                });
            }
            
            html += '</div>';
        }
        
        content.innerHTML = html;
    } catch (error) {
        content.innerHTML = '<p style="text-align: center; color: #e74c3c;">加载卡牌数据失败</p>';
        console.error('加载卡牌数据失败:', error);
    }
}

// 关闭卡库弹窗
function closeCardsModal() {
    document.getElementById('cards-modal').style.display = 'none';
}

// API已经返回解析好的数据，不需要额外的CSV解析函数

// 绑定按钮事件
document.addEventListener('DOMContentLoaded', () => {
    // 房间页面的按钮
    document.getElementById('view-rules-room-btn')?.addEventListener('click', showRulesModal);
    document.getElementById('view-cards-room-btn')?.addEventListener('click', showCardsModal);
    
    // 游戏页面的按钮
    document.getElementById('view-rules-game-btn')?.addEventListener('click', showRulesModal);
    document.getElementById('view-cards-game-btn')?.addEventListener('click', showCardsModal);
    
    // 点击弹窗背景关闭
    document.getElementById('rules-modal')?.addEventListener('click', (e) => {
        if (e.target.id === 'rules-modal') closeRulesModal();
    });
    document.getElementById('cards-modal')?.addEventListener('click', (e) => {
        if (e.target.id === 'cards-modal') closeCardsModal();
    });
});

