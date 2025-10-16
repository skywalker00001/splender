// 登录界面逻辑
class LoginManager {
    constructor() {
        this.init();
    }
    
    init() {
        const form = document.getElementById('loginForm');
        const usernameInput = document.getElementById('username');
        
        // 绑定表单提交
        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleLogin();
        });
        
        // 按Enter键登录
        usernameInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.handleLogin();
            }
        });
        
        // 自动聚焦到输入框
        usernameInput.focus();
        
        // 检查是否已有localStorage中的用户名（用于自动填充）
        const savedUsername = localStorage.getItem('currentPlayerName');
        if (savedUsername) {
            usernameInput.value = savedUsername;
            usernameInput.select();
        }
    }
    
    async handleLogin() {
        const username = document.getElementById('username').value.trim();
        const loginBtn = document.getElementById('loginBtn');
        const errorMessage = document.getElementById('errorMessage');
        const successMessage = document.getElementById('successMessage');
        
        // 清除之前的消息
        this.hideMessage(errorMessage);
        this.hideMessage(successMessage);
        
        // 验证用户名
        if (!username) {
            this.showError('请输入用户名');
            return;
        }
        
        if (username.length > 20) {
            this.showError('用户名不能超过20个字符');
            return;
        }
        
        // 禁用登录按钮
        loginBtn.disabled = true;
        loginBtn.textContent = '🔄 登录中...';
        
        try {
            // 调用登录API
            const response = await fetch(`${API_BASE_URL}/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username })
            });
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || '登录失败');
            }
            
            // 保存用户信息到localStorage
            localStorage.setItem('currentPlayerName', username);
            localStorage.setItem('userData', JSON.stringify(data.user));
            
            // 显示欢迎消息
            this.showSuccess(data.message);
            
            // 检查是否有进行中的游戏
            if (data.has_active_game && data.active_game) {
                // 有进行中的游戏，强制重连
                await this.reconnectToGame(data.active_game);
            } else {
                // 没有进行中的游戏，跳转到大厅
                setTimeout(() => {
                    window.location.href = '/main.html';
                }, 500);
            }
            
        } catch (error) {
            console.error('登录失败:', error);
            this.showError(error.message || '登录失败，请重试');
            loginBtn.disabled = false;
            loginBtn.textContent = '🚀 进入游戏';
        }
    }
    
    async reconnectToGame(activeGame) {
        console.log('检测到进行中的游戏，准备重连:', activeGame);
        
        // 显示重连提示
        const overlay = document.getElementById('reconnectingOverlay');
        overlay.style.display = 'flex';
        
        try {
            // 等待一小段时间让用户看到提示
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // 根据游戏状态跳转
            if (activeGame.status === 'waiting') {
                // 游戏还在等待状态，跳转到房间
                window.location.href = `/room.html?room_id=${activeGame.room_id}`;
            } else if (activeGame.status === 'playing') {
                // 游戏正在进行，跳转到游戏界面
                window.location.href = `/game.html?room_id=${activeGame.room_id}`;
            } else {
                // 其他状态，跳转到大厅
                window.location.href = '/main.html';
            }
        } catch (error) {
            console.error('重连失败:', error);
            overlay.style.display = 'none';
            this.showError('重连失败，正在跳转到大厅...');
            setTimeout(() => {
                window.location.href = '/main.html';
            }, 1500);
        }
    }
    
    showError(message) {
        const errorMessage = document.getElementById('errorMessage');
        errorMessage.textContent = message;
        errorMessage.style.display = 'block';
    }
    
    showSuccess(message) {
        const successMessage = document.getElementById('successMessage');
        successMessage.textContent = message;
        successMessage.style.display = 'block';
    }
    
    hideMessage(element) {
        element.style.display = 'none';
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    new LoginManager();
});

