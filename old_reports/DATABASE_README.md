# 🔍 数据库后台查询 - 快速使用指南

## ✅ 推荐方法：Python交互式工具

**无需安装任何额外工具，直接使用！**

```bash
cd /home/work/houyi/pj_25_q4/splendor
python3 query_database.py
```

### 功能菜单
```
1. 查看所有用户        - 显示所有注册用户和统计
2. 查看用户详情        - 查看指定用户的详细信息和历史对局
3. 查看最近对局        - 显示最近N场对局记录
4. 查看对局详情        - 查看指定对局的详细信息
5. 查看统计信息        - 数据库整体统计和TOP玩家
0. 退出
```

---

## 🚀 快速查看数据

### 查看当前数据库状态
```bash
cd /home/work/houyi/pj_25_q4/splendor
python3 -c "
import sqlite3
conn = sqlite3.connect('backend/splendor_game.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM users')
print(f'用户数: {cursor.fetchone()[0]}')
conn.close()
"
```

### 查看所有用户（单行命令）
```bash
cd /home/work/houyi/pj_25_q4/splendor
python3 -c "
import sqlite3
conn = sqlite3.connect('backend/splendor_game.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute('SELECT username, total_games, total_wins FROM users')
for user in cursor.fetchall():
    print(f'{user[\"username\"]}: {user[\"total_games\"]}局 {user[\"total_wins\"]}胜')
conn.close()
"
```

---

## 📊 数据库文件位置

```
/home/work/houyi/pj_25_q4/splendor/backend/splendor_game.db
```

---

## ⚠️ 注意事项

1. **数据库初始化**：首次启动游戏并有玩家注册后才会创建完整的数据库表
2. **游戏运行中**：数据库可能被锁定，查询时请耐心等待
3. **只读操作**：所有查询工具都是只读的，不会修改数据

---

## 💡 常见问题

### Q: 提示"no such table: game_history"？
A: 表示还没有完成过对局，只要完成一局游戏即可创建此表。

### Q: 显示"暂无用户数据"？
A: 还没有玩家注册过，启动游戏并登录即可。

### Q: Shell脚本报错"sqlite3: command not found"？
A: 系统未安装sqlite3命令行工具，请使用Python工具（推荐）。

安装sqlite3（可选）：
```bash
# Ubuntu/Debian
sudo apt-get install sqlite3

# macOS
brew install sqlite3
```

---

## 📖 详细文档

完整的使用指南和高级查询方法，请查看：
```
DATABASE_QUERY_GUIDE.md
```

