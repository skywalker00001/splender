# 🔍 数据库查询指南

在后台直接查看玩家信息和对局数据，无需通过前端页面。

## 📊 数据库位置

```
/home/work/houyi/pj_25_q4/splendor/backend/splendor_game.db
```

## 🛠️ 查询方法

### 方法一：Python交互式查询工具（推荐）

这是一个功能完整的交互式查询工具，提供菜单界面。

```bash
cd /home/work/houyi/pj_25_q4/splendor
python query_database.py
```

**功能：**
- ✅ 查看所有用户（用户名、注册时间、对局数、胜率等）
- ✅ 查看用户详细信息（包括最近20场对局）
- ✅ 查看最近的对局记录
- ✅ 查看对局详细信息（玩家、分数、轮次等）
- ✅ 查看统计信息（最活跃玩家、平均轮次等）

**示例输出：**
```
==================================================================================================
👥 所有用户列表
==================================================================================================

共有 5 个用户：

ID    用户名               注册时间              最后登录              总对局   胜场     总分     胜率    
----------------------------------------------------------------------------------------------------
1     玩家1                2025-10-16 10:30:15   2025-10-16 15:45:20   25       10       450      40.0%  
2     玩家2                2025-10-16 11:20:30   2025-10-16 14:30:10   18       7        320      38.9%  
```

---

### 方法二：Shell快速查询脚本

快速查看常用信息，无需进入交互界面。

```bash
cd /home/work/houyi/pj_25_q4/splendor
./quick_query.sh
```

**功能：**
- ✅ 快速查看所有用户
- ✅ 快速查看最近10场对局
- ✅ 快速查看统计信息
- ✅ 自定义SQL查询

---

### 方法三：SQLite命令行直接查询

适合熟悉SQL的用户，最灵活。

```bash
cd /home/work/houyi/pj_25_q4/splendor/backend
sqlite3 splendor_game.db
```

#### 常用SQL查询示例：

**1. 查看所有用户：**
```sql
SELECT 
    id,
    username,
    created_at AS 注册时间,
    last_login AS 最后登录,
    total_games AS 对局数,
    total_wins AS 胜场,
    total_points AS 总分
FROM users
ORDER BY created_at DESC;
```

**2. 查看最近20场对局：**
```sql
SELECT 
    game_id AS 对局ID,
    room_id AS 房间ID,
    winner AS 获胜者,
    total_turns AS 轮次,
    end_time AS 结束时间
FROM game_history
ORDER BY end_time DESC
LIMIT 20;
```

**3. 查看某个用户的详细信息：**
```sql
SELECT * FROM users WHERE username = '玩家1';
```

**4. 查看某个用户的对局历史：**
```sql
SELECT 
    game_id,
    winner,
    total_turns,
    final_scores,
    end_time
FROM game_history
WHERE players LIKE '%玩家1%'
ORDER BY end_time DESC;
```

**5. 统计数据：**
```sql
-- 用户总数
SELECT COUNT(*) FROM users;

-- 对局总数
SELECT COUNT(*) FROM game_history;

-- 平均轮次
SELECT AVG(total_turns) FROM game_history;

-- 最活跃玩家
SELECT 
    username,
    total_games,
    total_wins,
    ROUND(total_wins*100.0/total_games, 1) AS 胜率
FROM users
WHERE total_games > 0
ORDER BY total_games DESC
LIMIT 10;
```

**6. 退出SQLite：**
```sql
.quit
```

---

### 方法四：使用SQLite GUI工具（可选）

如果你想要图形界面，可以使用：

**DB Browser for SQLite**（免费开源）
- 官网：https://sqlitebrowser.org/
- 安装后，打开 `/home/work/houyi/pj_25_q4/splendor/backend/splendor_game.db`

**功能：**
- ✅ 可视化表结构
- ✅ 图形化查询界面
- ✅ 数据导出（CSV、JSON等）
- ✅ 数据编辑

---

## 📋 数据库表结构

### 1. users（用户表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 用户ID（主键） |
| username | TEXT | 用户名（唯一） |
| created_at | TIMESTAMP | 注册时间 |
| last_login | TIMESTAMP | 最后登录时间 |
| total_games | INTEGER | 总对局数 |
| total_wins | INTEGER | 胜场数 |
| total_points | INTEGER | 总积分 |

### 2. game_history（对局历史表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 记录ID（主键） |
| game_id | TEXT | 对局ID（唯一） |
| room_id | TEXT | 房间ID |
| start_time | TIMESTAMP | 开始时间 |
| end_time | TIMESTAMP | 结束时间 |
| total_turns | INTEGER | 总轮次 |
| players | TEXT | 玩家列表（JSON） |
| winner | TEXT | 获胜者 |
| final_scores | TEXT | 最终分数（JSON） |

---

## 🔧 高级操作

### 备份数据库

```bash
cd /home/work/houyi/pj_25_q4/splendor/backend
cp splendor_game.db splendor_game_backup_$(date +%Y%m%d_%H%M%S).db
```

### 导出数据为CSV

```bash
cd /home/work/houyi/pj_25_q4/splendor/backend
sqlite3 splendor_game.db <<EOF
.headers on
.mode csv
.output users_export.csv
SELECT * FROM users;
.output game_history_export.csv
SELECT * FROM game_history;
.quit
EOF
```

### 清空数据（谨慎使用！）

```bash
cd /home/work/houyi/pj_25_q4/splendor/backend
sqlite3 splendor_game.db <<EOF
DELETE FROM game_history;
DELETE FROM users;
VACUUM;
.quit
EOF
```

---

## 💡 使用建议

1. **日常查看**：使用 `query_database.py`，界面友好
2. **快速查询**：使用 `quick_query.sh`，快捷方便
3. **复杂分析**：使用 SQLite 命令行，灵活强大
4. **可视化管理**：使用 DB Browser for SQLite GUI

---

## 🚨 注意事项

- ⚠️ 数据库文件在游戏运行时会被锁定，查询时可能需要等待
- ⚠️ 不要直接修改数据库，可能导致数据不一致
- ⚠️ 定期备份数据库，防止数据丢失
- ✅ 所有查询操作都是只读的，不会影响游戏运行

