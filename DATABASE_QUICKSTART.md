# 数据库系统 - 快速开始

## 🚀 立即使用

### 1. 用户登录
```bash
curl -X POST http://localhost:5000/api/users/login \
  -H "Content-Type: application/json" \
  -d '{"username": "小智"}'
```

### 2. 查看游戏历史
```bash
curl http://localhost:5000/api/users/小智/games?limit=10
```

### 3. 查看统计信息
```bash
curl http://localhost:5000/api/users/小智/statistics
```

---

## 📦 数据库文件位置
```
backend/splendor_game.db
```

---

## ✅ 功能验证

运行测试（带30秒超时保护）：
```bash
python3 test/test_database.py
```

预期输出：
```
✅ 所有数据库测试通过！
- 创建/获取用户
- 记录游戏参与
- 获取用户游戏历史
- 获取用户统计信息
- 获取游戏详情
```

---

## 💡 重要提示

1. **自动保存**: 游戏结束时自动保存到数据库
2. **真人玩家**: 只记录真人玩家数据，AI玩家不记录
3. **持久化**: 系统重启后数据不丢失
4. **线程安全**: 所有操作都是线程安全的

---

## 🔧 故障排除

### 问题: 数据库锁死
**已修复**: 所有嵌套锁问题已解决

### 问题: 测试超时
**已解决**: 测试脚本包含30秒超时保护

---

## 📊 数据示例

```json
{
  "username": "小智",
  "total_games": 10,
  "total_wins": 6,
  "total_points": 180,
  "win_rate": 0.6,
  "avg_score": 18.0,
  "highest_score": 25,
  "rank_distribution": {
    "1": 6,
    "2": 3,
    "3": 1
  }
}
```
