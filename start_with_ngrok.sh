#!/bin/bash
# 使用 ngrok 启动璀璨宝石宝可梦Web应用

cd ~/houyi/pj_25_q4/splendor
pkill -f web_app.py

echo "🌟 璀璨宝石宝可梦 - 启动中... 🌟"

# 启动 Web 应用
nohup python3 web_app.py > /tmp/splendor_web.log 2>&1 &

sleep 3

echo "✓ Web应用已启动在 http://localhost:5000"
echo ""
echo "现在启动 ngrok 隧道..."
echo "请确保已安装 ngrok: https://ngrok.com/"
echo ""
echo "运行以下命令创建公网访问链接："
echo "  ngrok http 5000"
echo ""
echo "或者如果你有 ngrok 账号，可以使用："
echo "  ngrok http 5000 --domain=your-domain.ngrok-free.app"
