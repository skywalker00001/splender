# 🐛 用户数据持久化Bug修复报告

## 问题描述

**严重Bug**：服务器重启后，所有用户数据丢失！

### 症状
- 玩家登录注册成功
- 关闭服务器后重启
- 数据库查询显示：用户数0（数据全丢失）

## 根本原因

### 原始代码问题

**1. 登录时只在内存中创建用户，未保存到数据库**

```python
# backend/app.py - login() 函数（第365-370行）
with user_lock:
    if username not in users:
        users[username] = User(username)  # ❌ 只在内存中
        is_new_user = True
```

问题：`users`字典只在内存中，服务器重启后清空。

**2. 服务器启动时未从数据库加载用户**

原始代码在服务器启动时直接运行，没有从数据库恢复用户数据。

## 修复方案

### ✅ 修复1：登录时保存到数据库

```python
# backend/app.py - login() 函数（第365-376行）
with user_lock:
    if username not in users:
        users[username] = User(username)
        # ✅ 同时保存到数据库
        game_db.get_or_create_user(username)
        is_new_user = True
    else:
        users[username].last_login = datetime.now()
        # ✅ 同时更新数据库中的最后登录时间
        game_db.get_or_create_user(username)
        is_new_user = False
```

**改进：**
- 新用户创建时立即写入数据库
- 老用户登录时更新最后登录时间

### ✅ 修复2：服务器启动时加载用户

```python
# backend/app.py - 新增函数（第1682-1706行）
def load_users_from_database():
    """从数据库加载所有用户到内存"""
    print("📚 正在从数据库加载用户...")
    try:
        conn = game_db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT username, created_at, last_login FROM users')
        db_users = cursor.fetchall()
        conn.close()
        
        with user_lock:
            for row in db_users:
                username = row['username']
                if username not in users:
                    user = User(username)
                    user.created_at = datetime.fromisoformat(row['created_at'])
                    user.last_login = datetime.fromisoformat(row['last_login'])
                    users[username] = user
        
        print(f"✅ 成功加载 {len(db_users)} 个用户")
    except Exception as e:
        print(f"⚠️  加载用户时出错: {e}")

if __name__ == '__main__':
    print("🌟 璀璨宝石宝可梦API服务启动中...")
    # ✅ 从数据库加载用户
    load_users_from_database()
    app.run(host='0.0.0.0', port=5000, debug=True)
```

**改进：**
- 服务器启动时自动从数据库加载所有用户
- 恢复用户的创建时间和最后登录时间
- 加载过程有完整的日志输出

## 验证步骤

### 1. 测试用户持久化

```bash
# 1. 启动服务器
cd /home/work/houyi/pj_25_q4/splendor/backend
python3 app.py

# 控制台应该显示：
# 📚 正在从数据库加载用户...
# ✅ 成功加载 X 个用户

# 2. 前端登录几个用户（如：qinsy, 玩家1, 玩家2）

# 3. 查询数据库
cd /home/work/houyi/pj_25_q4/splendor
python3 query_database.py
# 选择 1 - 查看所有用户
# 应该能看到所有注册的用户

# 4. 关闭服务器（Ctrl+C）

# 5. 重启服务器
cd /home/work/houyi/pj_25_q4/splendor/backend
python3 app.py

# 控制台应该显示：
# 📚 正在从数据库加载用户...
# ✅ 成功加载 3 个用户  <-- 用户已恢复！

# 6. 再次查询数据库
cd /home/work/houyi/pj_25_q4/splendor
python3 query_database.py
# 选择 1 - 查看所有用户
# ✅ 用户数据依然存在！
```

### 2. 测试数据一致性

```bash
# 查询数据库
python3 query_database.py

# 应该看到：
# - 用户名
# - 注册时间（正确保存）
# - 最后登录时间（每次登录更新）
# - 对局统计（游戏结束后更新）
```

## 技术细节

### 数据流程图

```
用户登录
    ↓
内存中创建/更新 User 对象 (users字典)
    ↓
同时调用 game_db.get_or_create_user()
    ↓
SQLite数据库持久化保存
    ↓
服务器重启
    ↓
load_users_from_database() 函数执行
    ↓
从SQLite读取所有用户
    ↓
恢复到内存中的 users字典
    ↓
✅ 用户数据完整恢复
```

### 数据库表结构

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_games INTEGER DEFAULT 0,
    total_wins INTEGER DEFAULT 0,
    total_points INTEGER DEFAULT 0
)
```

## 影响范围

### ✅ 已修复
- 用户注册数据持久化
- 服务器重启后用户恢复
- 登录时间正确记录和更新

### 📝 相关功能
- 对局历史依然正常（已经有数据库保存）
- 统计信息依然正常（游戏结束时更新）

## 测试建议

1. **注册新用户** → 重启服务器 → 确认用户存在
2. **玩一局游戏** → 重启服务器 → 确认对局记录存在
3. **查询统计信息** → 确认数据准确

## 总结

这是一个**严重的数据持久化bug**，导致所有用户数据在服务器重启后丢失。

**修复后：**
- ✅ 用户数据正确保存到SQLite数据库
- ✅ 服务器重启后自动恢复用户数据
- ✅ 登录时间、统计信息正确更新
- ✅ 数据持久化保证了生产环境的稳定性

---

**修复时间**：2025-10-16  
**文件修改**：`backend/app.py`  
**影响版本**：所有之前的版本  
**修复版本**：当前版本

