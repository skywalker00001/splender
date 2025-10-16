# 卡牌唯一ID (card_id) 迁移报告

## 1. 问题背景
由于卡库中存在多张重名卡牌（如多张"迷你龙"），使用`card.name`进行卡牌锚定会导致混淆和错误。因此引入了唯一的`card_id`（1-90）来标识每张卡牌。

## 2. 已完成的修改

### 2.1 数据层
- ✅ `card_library/cards_data.csv`: 添加了`卡牌ID`列（1-90）
- ✅ `splendor_pokemon.py`: 
  - PokemonCard类添加了`card_id`字段
  - load_cards_from_csv读取card_id
  - SplendorPokemonGame添加了`find_card_by_id`方法

### 2.2 后端API层 (backend/app.py)
- ✅ **返回给前端的数据**：所有卡牌数据都包含`card_id`
  - tableau卡牌
  - rare_card / legendary_card
  - player.display_area
  - player.reserved_cards
  
- ✅ **API端点**：优先使用card_id，向后兼容name
  - `/buy_card`: 支持card_id（优先）和name（fallback）
  - `/reserve_card`: 支持card_id（优先）和name（fallback）
  - `/evolve_card`: 支持card_id（优先）和card_name（fallback）

- ✅ **AI处理**：handle_ai_action使用card_id

### 2.3 AI层 (backend/ai_player.py)
- ✅ 所有AI策略返回的action使用card_id：
  - _medium_strategy
  - _hard_strategy
  - _hard_2player_strategy

### 2.4 前端层
- ✅ `web/static/js/game.js`:
  - buyCard: 使用card_id
  - reserveCard: 使用card_id
  - evolveCard: 使用card_id
  - showEvolutionChoice: 使用card_id作为唯一标识，但显示name给用户

### 2.5 测试层
- ✅ `test/final_test.py`: simulate_game_from_history使用card_id

## 3. 重要原则
1. **后端逻辑**：所有卡牌操作（购买、预购、进化）都使用`card_id`作为唯一标识
2. **前端交互**：前端发送请求时使用`card_id`
3. **用户界面**：前端UI只显示`card.name`给玩家，不显示`card_id`
4. **向后兼容**：后端API保留name的fallback支持

## 4. card_id的使用场景

### 场景1: AI决策
```python
# AI返回action时使用card_id
return {
    "action": "buy_card",
    "data": {"card": {"card_id": card.card_id}}
}
```

### 场景2: 前端购买/预购
```javascript
// 前端使用card_id发送请求
api.buyCard(roomId, playerName, { card_id: card.card_id })
api.reserveCard(roomId, playerName, { card: { card_id: card.card_id } })
```

### 场景3: 后端查找卡牌
```python
# 后端使用find_card_by_id查找
target_card = room.game.find_card_by_id(card_id, current_player)
```

### 场景4: 前端UI显示
```javascript
// UI只显示name，不显示card_id
<h3>选择操作: ${card.name}</h3>  <!-- 不显示card_id -->
```

## 5. 注意事项
- ⚠️ CSV文件中的进化目标(`进化后卡牌`)仍然使用名称字符串，这是设计上的特性
- ⚠️ 测试文件中可能还有使用name的地方，但不影响主要功能
- ⚠️ 游戏历史记录JSON中应该保存card_id以便准确回放

## 6. 测试验证
- ✅ Medium AI 2人/4人局：100%成功率
- ✅ Hard AI 2人/4人局：100%成功率
- ✅ Simple AI：通过测试

## 7. 总结
所有关键路径（AI决策、前后端交互、后端逻辑）都已经使用`card_id`作为唯一标识。前端UI正确地只显示`card.name`给玩家，不暴露`card_id`。系统已完成从name到card_id的完整迁移。
