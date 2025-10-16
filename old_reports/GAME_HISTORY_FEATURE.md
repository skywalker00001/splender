# 🎮 对局保存与复盘功能说明

## ✨ 功能概述

游戏现在支持完整的对局历史记录和复盘功能，可以详细记录每一回合、每一个动作，方便玩家复盘和调试AI策略。

---

## 📁 文件结构

```
splendor/
├── game_history/                    # 历史记录存储目录
│   └── game_*.json                 # 游戏历史记录文件
├── backend/
│   ├── game_history.py             # 历史记录核心类
│   └── app.py                      # 已集成历史记录API
├── web/
│   ├── history.html                # 历史对局列表页面
│   ├── replay.html                 # 对局复盘页面
│   └── static/js/
│       ├── history.js              # 历史列表逻辑
│       └── replay.js               # 复盘逻辑
└── test/
    └── test_comprehensive.py       # 已集成自动保存测试对局
```

---

## 🔧 核心功能

### 1. 后端历史记录系统

**`backend/game_history.py`**

#### GameHistory 类

主要方法：
- `__init__()` - 初始化游戏历史记录
- `start_turn()` - 开始新回合记录
- `record_initial_state()` - 记录游戏初始状态
- `record_state_before_action()` - 记录动作前状态
- `record_action()` - 记录玩家动作
- `record_state_after_action()` - 记录动作后状态
- `end_game()` - 结束游戏并记录最终结果
- `save_to_file()` - 保存到JSON文件
- `load_from_file()` - 从文件加载历史
- `list_all_histories()` - 列出所有历史记录

#### 记录内容

每个历史记录包含：
- **游戏信息**：游戏ID、房间ID、玩家列表、胜利分数目标
- **时间信息**：开始时间、结束时间、游戏时长
- **初始状态**：初始球池、初始场面、玩家初始状态
- **回合记录**：
  - 回合号
  - 当前玩家
  - 动作前状态（球、分数、卡牌数）
  - 执行的动作（类型、数据、结果、消息）
  - 动作后状态
- **最终结果**：胜者、排名

### 2. 后端API接口

**已添加的API端点：**

```python
# 获取历史记录列表
GET /api/history/list

# 获取指定游戏的完整历史
GET /api/history/<game_id>

# 获取指定游戏的某一回合
GET /api/history/<game_id>/turn/<turn_number>
```

### 3. 游戏逻辑集成

**`backend/app.py` - GameRoom 类新增方法：**

- `record_action()` - 自动记录游戏动作
- `record_turn_end()` - 记录回合结束状态
- `end_game_and_save_history()` - 游戏结束时保存历史

**自动记录时机：**
- 游戏开始时 → 初始化历史记录
- 拿球时 → 记录 `take_balls` 动作
- 购买卡牌时 → 记录 `buy_card` 动作
- 预购卡牌时 → 记录 `reserve_card` 动作
- 放回球时 → 记录 `return_balls` 动作
- 回合结束时 → 记录状态并开始新回合
- 游戏结束时 → 保存完整历史到文件

### 4. 前端界面

#### 历史对局列表 (`/history.html`)

功能：
- 显示所有已完成的游戏记录
- 显示游戏ID、玩家、胜者、时长、回合数
- 点击任一记录进入复盘页面

#### 对局复盘 (`/replay.html`)

功能：
- **回合导航**：上一回合/下一回合按钮，回合选择下拉框
- **回合列表**：左侧显示所有回合，点击跳转
- **动作详情**：显示该回合的所有动作及结果
- **状态对比**：并排显示动作前后的玩家状态
  - 持球情况
  - 胜利点数
  - 拥有卡牌数
  - 预购卡牌数

#### 大厅入口

在主界面（`/main.html`）添加了 **"📜 历史对局"** 按钮，点击进入历史记录列表。

### 5. 测试集成

**`test/test_comprehensive.py`**

测试脚本已自动集成历史记录功能：
- 每次运行完整游戏测试时自动保存历史记录
- 生成的历史文件命名：`game_YYYYMMDD_HHMMSS_test_<timestamp>.json`
- 便于调试AI策略和游戏逻辑

---

## 📊 历史记录文件格式

JSON文件示例结构：

```json
{
  "game_id": "test_1760602662",
  "room_id": "test_room",
  "players": ["玩家1", "玩家2", "玩家3", "玩家4"],
  "victory_points_goal": 18,
  "start_time": "2025-10-16T08:17:42.240268",
  "end_time": "2025-10-16T08:17:42.402471",
  "winner": "玩家1",
  "total_turns": 124,
  "initial_state": {
    "ball_pool": { "红": 7, "蓝": 7, ... },
    "tableau": { ... },
    "player_states": { ... }
  },
  "turns": [
    {
      "turn": 1,
      "player": "玩家1",
      "actions": [
        {
          "timestamp": "2025-10-16T08:17:42.250123",
          "type": "take_balls",
          "data": { "ball_types": ["红", "蓝", "黄"] },
          "result": true,
          "message": "拿取球"
        }
      ],
      "states_before": {
        "player": {
          "name": "玩家1",
          "balls": { "红": 0, "蓝": 0, ... },
          "victory_points": 0,
          "owned_cards_count": 0,
          "reserved_cards_count": 0
        },
        "ball_pool": { "红": 7, "蓝": 7, ... }
      },
      "states_after": {
        "player": {
          "name": "玩家1",
          "balls": { "红": 1, "蓝": 1, "黄": 1 },
          "victory_points": 0,
          "owned_cards_count": 0,
          "reserved_cards_count": 0
        },
        "ball_pool": { "红": 6, "蓝": 6, "黄": 6 }
      }
    },
    ...
  ],
  "final_rankings": [
    {
      "rank": 1,
      "player_name": "玩家1",
      "victory_points": 20,
      "cards_count": 12,
      "balls_count": 8
    },
    ...
  ]
}
```

---

## 🚀 使用指南

### 作为玩家

1. **游戏结束后**：系统自动保存对局历史到 `game_history/` 目录
2. **查看历史**：
   - 在大厅点击 **"📜 历史对局"** 按钮
   - 浏览所有已完成的游戏记录
3. **复盘对局**：
   - 点击任一历史记录进入复盘页面
   - 使用导航按钮浏览每一回合
   - 查看每个玩家的决策和状态变化

### 作为开发者/调试

1. **测试时自动保存**：
   ```bash
   python test/test_comprehensive.py
   ```
   测试完成后在 `game_history/` 目录查看生成的历史文件

2. **手动保存游戏状态**：
   ```python
   from backend.game_history import GameHistory
   
   history = GameHistory(game_id, room_id, players, victory_points_goal)
   history.record_initial_state(initial_state)
   # ... 游戏进行中记录动作 ...
   history.end_game(winner, rankings)
   filepath = history.save_to_file()  # 保存到 game_history/
   ```

3. **加载历史进行分析**：
   ```python
   history = GameHistory.load_from_file("game_history/game_xxx.json")
   print(f"总回合数: {len(history.turns)}")
   for turn in history.turns:
       print(f"回合{turn['turn']}: {turn['player']} 的动作")
       for action in turn['actions']:
           print(f"  - {action['type']}: {action['result']}")
   ```

---

## 🎯 应用场景

### 1. 玩家复盘
- 回顾自己的决策
- 学习其他玩家的策略
- 分析失败原因

### 2. AI调试
- 分析AI决策逻辑
- 发现AI死锁或低效行为
- 优化AI策略权重

### 3. 游戏平衡测试
- 统计卡牌使用率
- 分析球色分布影响
- 评估胜利条件合理性

### 4. Bug调试
- 重现游戏中的异常行为
- 验证规则实现正确性
- 追踪状态变化

---

## 📝 注意事项

1. **文件大小**：完整游戏的历史记录文件约为 **1-2MB**
2. **存储位置**：默认保存在 `game_history/` 目录（可在 `GameHistory.save_to_file()` 中修改）
3. **命名规则**：`game_YYYYMMDD_HHMMSS_<game_id>.json`
4. **隐私考虑**：历史记录包含玩家名称，部署时注意数据安全
5. **清理建议**：定期清理旧的历史记录文件以节省磁盘空间

---

## 🔮 未来扩展

可能的功能增强：
- [ ] 历史记录搜索和过滤（按玩家、日期、房间）
- [ ] 导出为PDF或图表
- [ ] 统计分析面板（胜率、平均回合数等）
- [ ] 历史记录对比功能
- [ ] 支持历史记录回放动画
- [ ] 云端备份历史记录

---

## ✅ 测试验证

运行测试验证功能：

```bash
# 运行完整测试（会自动保存历史）
python test/test_comprehensive.py

# 检查生成的历史文件
ls -lh game_history/

# 查看历史文件内容
cat game_history/game_*.json | head -100
```

测试成功标志：
- ✅ `game_history/` 目录存在
- ✅ 生成了以 `game_*.json` 命名的文件
- ✅ JSON格式正确，包含完整的游戏数据
- ✅ 前端可以正常加载和显示历史记录

---

**功能已全部实现并测试完成！** 🎉

