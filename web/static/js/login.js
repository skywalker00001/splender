// 登录界面逻辑
class LoginManager {
    constructor() {
        this.api = new SplendorAPI();
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
            // 调用登录API（允许重连，这样用户关闭页面后可以重新登录）
            const result = await this.api.login(username, true);  // force_reconnect = true
            
            if (!result.success) {
                throw new Error(result.error || '登录失败');
            }
            
            // 保存用户名到localStorage
            localStorage.setItem('splendor_username', username);
            
            // 保存登录结果
            localStorage.setItem('splendor_login_result', JSON.stringify({
                user: result.user,
                has_active_game: result.has_active_game,
                active_game: result.active_game,
                timestamp: Date.now()
            }));
            
            // 显示欢迎消息
            this.showSuccess(result.message || '登录成功');
            
            // 等待一小段时间让用户看到提示
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // 跳转到主页
            window.location.href = '/main.html';
            
        } catch (error) {
            console.error('登录失败:', error);
            
            // 显示错误
            const errorMsg = error.message || '登录失败，请重试';
            this.showError(errorMsg);
            loginBtn.disabled = false;
            loginBtn.textContent = '🚀 进入游戏';
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
