#!/bin/bash
# 快速启动 Cloudflare 隧道

echo "🚀 正在创建隧道..."
echo ""

cloudflared tunnel --url http://localhost:23001 2>&1 | while IFS= read -r line; do
    echo "$line"
    if [[ $line == *"https://"*".trycloudflare.com"* ]]; then
        URL=$(echo "$line" | grep -oE "https://[a-z0-9-]+\.trycloudflare\.com")
        echo ""
        echo "=========================================="
        echo "🌐 公网访问地址："
        echo ""
        echo "  $URL"
        echo ""
        echo "=========================================="
        echo ""
        echo "💡 分享上面的地址给其他人即可访问"
        echo "📌 按 Ctrl+C 停止隧道"
        echo ""
    fi
done

