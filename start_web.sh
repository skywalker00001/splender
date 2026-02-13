#!/bin/bash
# 启动璀璨宝石宝可梦Web应用
# export PORT=5001
cd /home/work/houyi/pj_25_q4/splendor
export PORT=23006
pkill -f web_app.py

echo "🌟 璀璨宝石宝可梦 - Web应用启动脚本 🌟"
echo "=========================================="

# 检查Python版本
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python版本: $python_version"

# 检查并安装依赖
echo ""
echo "📦 检查依赖..."
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

echo "激活虚拟环境..."
source venv/bin/activate

echo "安装/更新依赖..."
pip install -q -r backend/requirements.txt

# 获取本机IP地址
echo ""
echo "🌐 网络地址:"
echo "  • 本地访问: http://localhost:$PORT"

# 尝试获取局域网IP
if command -v hostname &> /dev/null; then
    local_ip=$(hostname -I | awk '{print $1}')
    if [ ! -z "$local_ip" ]; then
        echo "  • 局域网访问: http://$local_ip:$PORT"
    fi
fi

# 启动服务
echo ""
echo "🚀 启动Web应用..."
echo "=========================================="
echo ""

python3 web_app.py



