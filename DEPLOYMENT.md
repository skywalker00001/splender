# 璀璨宝石宝可梦 - 部署指南

## 方案1: 本地网络 + 端口转发

适合：在公司内网或家庭网络中分享

### 步骤：
1. 确保游戏运行在 `0.0.0.0:5000`（已配置）
2. 找到你的公网IP：访问 https://ip.sb
3. 在路由器设置端口转发：
   - 外部端口：5000
   - 内部IP：你的电脑IP
   - 内部端口：5000
4. 分享：`http://你的公网IP:5000`

⚠️ 注意：需要静态IP或动态域名服务（DDNS）

---

## 方案2: 使用 Ngrok（推荐用于临时分享）

### 安装和使用：
```bash
# 1. 注册账号：https://ngrok.com/
# 2. 安装 ngrok
wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz
tar xvzf ngrok-v3-stable-linux-amd64.tgz
sudo mv ngrok /usr/local/bin/

# 3. 配置 token（从 ngrok 网站获取）
ngrok config add-authtoken YOUR_AUTH_TOKEN

# 4. 启动游戏
./start_web.sh

# 5. 在新终端启动 ngrok
ngrok http 5000
```

会得到类似：`https://abc123.ngrok-free.app` 的URL

### 固定域名（付费功能）：
```bash
ngrok http 5000 --domain=splendor-game.ngrok-free.app
```

---

## 方案3: 部署到云服务器（推荐用于长期使用）

### 3.1 使用阿里云/腾讯云

```bash
# 在服务器上
git clone <your-repo>
cd splendor
pip install -r backend/requirements.txt

# 使用 systemd 或 screen 运行
screen -S splendor
python3 web_app.py

# 配置防火墙
sudo ufw allow 5000

# 访问: http://你的服务器IP:5000
```

### 3.2 使用 Docker 部署

```dockerfile
# Dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install -r backend/requirements.txt
EXPOSE 5000
CMD ["python3", "web_app.py"]
```

```bash
# 构建和运行
docker build -t splendor-game .
docker run -d -p 5000:5000 splendor-game
```

### 3.3 使用 Nginx 反向代理（生产环境）

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

---

## 方案4: 使用 Vercel/Railway/Heroku（免费托管）

### Railway (推荐)
1. 访问 https://railway.app/
2. 连接 GitHub 仓库
3. 自动部署
4. 获得域名：`your-app.railway.app`

### Vercel
适合静态网站，需要 serverless 改造

---

## 方案5: 使用 Cloudflare Tunnel（免费 + 安全）

```bash
# 1. 安装 cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# 2. 登录
cloudflared tunnel login

# 3. 创建隧道
cloudflared tunnel create splendor

# 4. 配置路由
cloudflared tunnel route dns splendor splendor.yourdomain.com

# 5. 运行
cloudflared tunnel run splendor --url http://localhost:5000
```

优点：
- 免费
- 自动 HTTPS
- 不需要开放端口
- 比 ngrok 更稳定

---

## 快速对比

| 方案 | 难度 | 费用 | 稳定性 | 适用场景 |
|------|------|------|--------|----------|
| VS Code Dev Tunnels | ⭐ | 免费 | ⭐⭐ | 快速测试 |
| Ngrok | ⭐⭐ | 免费/付费 | ⭐⭐⭐ | 临时分享 |
| 云服务器 | ⭐⭐⭐ | 付费 | ⭐⭐⭐⭐⭐ | 长期使用 |
| Cloudflare Tunnel | ⭐⭐ | 免费 | ⭐⭐⭐⭐ | 长期免费方案 |
| Railway | ⭐⭐ | 免费/付费 | ⭐⭐⭐⭐ | 快速部署 |

---

## 推荐方案

### 快速测试/演示（今天就用）
👉 **VS Code Dev Tunnels** 或 **Ngrok**

### 长期免费方案
👉 **Cloudflare Tunnel** 或 **Railway 免费版**

### 生产环境
👉 **云服务器 + Nginx + 域名**

---

## 安全建议

无论使用哪种方案，请注意：

1. **添加密码保护**（可选）
2. **限制访问频率**
3. **备份游戏数据**
4. **监控服务器资源**
5. **使用 HTTPS**（生产环境必须）

---

需要帮助？查看各服务的官方文档或联系我！

