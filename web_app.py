#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
璀璨宝石宝可梦 - Web应用服务器
整合前端和后端API
"""

from flask import Flask, render_template, send_from_directory
from flask_cors import CORS
import sys
import os

# 添加backend目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# 导入后端API
from backend.app import app as backend_app, game_rooms, room_lock, GameRoom, cleanup_thread

# 创建Web应用
app = Flask(__name__, 
            template_folder='web/templates',
            static_folder='web/static')
CORS(app)

# 注册后端API的所有路由
for rule in backend_app.url_map.iter_rules():
    if rule.endpoint != 'static':
        view_func = backend_app.view_functions[rule.endpoint]
        methods = list(rule.methods - {'HEAD', 'OPTIONS'})
        app.add_url_rule(rule.rule, rule.endpoint, view_func, methods=methods)

@app.route('/')
def index():
    """首页 - 重定向到登录页"""
    from flask import redirect
    return redirect('/login.html')

@app.route('/login.html')
def login_page():
    """登录页面"""
    return send_from_directory('web', 'login.html')

@app.route('/main.html')
def main_page():
    """主应用页面"""
    return send_from_directory('web', 'main.html')

@app.route('/history.html')
def history_page():
    """历史对局列表页面"""
    return send_from_directory('web', 'history.html')

@app.route('/replay.html')
def replay_page():
    """对局复盘页面"""
    return send_from_directory('web', 'replay.html')

@app.route('/health')
def web_health():
    """Web应用健康检查"""
    return {
        "status": "ok",
        "message": "璀璨宝石宝可梦Web应用运行正常",
        "backend": "connected",
        "active_rooms": len(game_rooms)
    }

if __name__ == '__main__':
    print("=" * 60)
    print("🌟 璀璨宝石宝可梦 - Web应用启动中... 🌟")
    print("=" * 60)
    # 端口配置 - 可以修改为其他端口（如5001）如果5000被占用
    PORT = int(os.environ.get('PORT', 5000))
    
    print("\n📱 访问方式:")
    print(f"  • 本地访问: http://localhost:{PORT}")
    print(f"  • 局域网访问: http://你的IP地址:{PORT}")
    print(f"  • API文档: http://localhost:{PORT}/api/health")
    print("\n💡 使用说明:")
    print("  1. 在浏览器中打开上述地址")
    print("  2. 输入你的名字")
    print("  3. 创建房间或加入现有房间")
    print("  4. 等待其他玩家加入")
    print("  5. 房主点击「开始游戏」开始游戏")
    print("\n🔧 提示:")
    print(f"  • 如果在远程服务器运行，确保防火墙开放{PORT}端口")
    print("  • 使用 Ctrl+C 停止服务器")
    print(f"  • 要使用其他端口，设置环境变量: export PORT=5001")
    print("=" * 60)
    print()
    
    # 启动服务器
    # 0.0.0.0 允许外部访问
    app.run(host='0.0.0.0', port=PORT, debug=True, threaded=True)



