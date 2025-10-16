# 🔧 中等AI 2人局死锁修复方案

## 📋 问题总结

### 极端案例
- 游戏ID: `game_20251016_090301_中等_2P_test2`
- **300回合0购卡0分！**
- 两个AI陷入"尝试购买→失败→重试"死循环
- 持球9个但买不起任何卡
- 球池只剩2个彩球
- 从未预购（预购区=0）

### 根本原因推测

#### 假设1：_get_buyable_cards返回错误结果
`_get_buyable_cards`可能错误地认为"蚊香蝌蚪"可买，导致：
```python
buyable_cards = self._get_buyable_cards(game, player)
if buyable_cards:  # 非空！
    return buy_card_action  # 尝试购买但失败
```

**验证方法**：添加日志查看`buyable_cards`是否真的非空

#### 假设2：球池枯竭策略条件不满足
球池只剩2个彩球，但策略要求`<= 6`应该触发。
可能的问题：
- 策略被跳过（因为buyable_cards非空）
- 或者策略触发了但动作执行失败

#### 假设3：AI策略选择顺序问题
当前逻辑：
```
1. 球池枯竭检测（第129行）
   if colored_balls <= 6:
       ... 破局策略 ...

2. 购买卡牌（第183行）
   buyable = _get_buyable_cards()
   if buyable:
       return buy_action
```

**如果**球池枯竭策略内部也调用了`_get_buyable_cards`，
然后返回了购买动作，但购买失败，就会陷入循环！

## 🔍 需要验证的关键点

### 验证点1：buyable_cards的实际内容
```python
# 在第184行后添加
buyable_cards = self._get_buyable_cards(game, player)
print(f"DEBUG: {player.name} buyable_cards = {[c.name for c in buyable_cards]}")
if buyable_cards:
    ...
```

### 验证点2：购买失败的原因
查看splendor_pokemon.py中的`buy_card`方法，
看看为什么返回False。

### 验证点3：球池枯竭策略是否执行
```python
# 在第135行后添加
if colored_balls_in_pool <= 6:
    print(f"DEBUG: 球池枯竭策略触发! colored={colored_balls_in_pool}")
    ...
```

## 💡 修复方案

### 方案A：增加安全检查（最简单）
在尝试购买前，验证是否真的能买：

```python
def _medium_strategy(...):
    # 球池枯竭检测（保持不变）
    if colored_balls_in_pool <= 6:
        ...
    
    # 购买卡牌（添加安全检查）
    buyable_cards = self._get_buyable_cards(game, player)
    if buyable_cards:
        # ⚠️ 新增：尝试购买前再次验证
        best_card = select_best_card(buyable_cards)
        
        # 验证是否真的能买
        if not game.can_player_buy_card(player, best_card):
            print(f"  ⚠️ 警告：{best_card.name}实际买不起，buyable判断错误")
            buyable_cards = []  # 清空，fallback到其他策略
        else:
            return buy_action
```

### 方案B：强制预购（更激进）
当持球>=8且预购区空时，强制预购：

```python
def _medium_strategy(...):
    # === 最高优先级：持球过多且预购区空 ===
    if player.get_total_balls() >= 8 and len(player.reserved_cards) == 0:
        print(f"  ⚠️ 持球过多({player.get_total_balls()})且预购区空，强制预购")
        best = self._find_best_card_to_reserve(game, player)
        if best:
            return reserve_action
    
    # 球池枯竭检测
    if colored_balls_in_pool <= 6:
        ...
```

### 方案C：修复buyable判断（最彻底）
检查`_can_afford`和`_can_really_afford`的实现，
确保不会返回买不起的卡。

可能的bug：
```python
def _can_afford(self, player: Player, card: PokemonCard, game: Game) -> bool:
    # 可能只检查了永久折扣，没考虑实际持球
    return player.can_afford(card)  # 这个方法可能有bug
```

应该改为：
```python
def _can_afford(self, player: Player, card: PokemonCard, game: Game) -> bool:
    # 完全依赖游戏逻辑的判断
    return game.check_can_buy(player, card)  # 使用游戏引擎的判断
```

### 方案D：添加连续失败检测
如果连续N次购买失败，切换策略：

```python
class AIPlayer:
    def __init__(self):
        self.consecutive_failures = 0
    
    def _medium_strategy(...):
        # 如果连续5次购买失败，强制预购
        if self.consecutive_failures >= 5:
            print(f"  ⚠️ 连续{self.consecutive_failures}次失败，强制切换策略")
            self.consecutive_failures = 0
            # 强制预购或跳过
            if len(player.reserved_cards) < 3:
                return reserve_action
            return None  # 跳过回合
        
        # 尝试购买
        if buyable_cards:
            result = try_buy()
            if not result:
                self.consecutive_failures += 1
            else:
                self.consecutive_failures = 0
```

## 🎯 推荐修复顺序

### 第1步：添加调试日志（立即执行）
在关键位置添加print，运行一局看看：
- buyable_cards是否非空
- 球池枯竭策略是否触发
- 购买失败的具体原因

### 第2步：实施方案B（快速修复）
强制预购策略，避免陷入持球过多的死锁

### 第3步：验证修复效果
运行10局中等2人AI测试，目标成功率>80%

### 第4步：如果还有问题，实施方案D
添加连续失败检测，更智能地切换策略

---

**优先级**: 🔴 P0（影响20%成功率）  
**预计修复时间**: 30分钟  
**验证测试**: 10局中等_2P测试

