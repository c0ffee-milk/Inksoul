// 工具函数定义
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(String(email).toLowerCase());
}

function showError(elementId, message) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = message;
        element.style.display = 'block';
        setTimeout(() => element.style.display = 'none', 3000);
    }
}

function startCountdown(seconds) {
    const btn = document.getElementById('get-captcha');
    if (!btn) return;
    
    let remaining = seconds;
    btn.disabled = true;
    
    const interval = setInterval(() => {
        btn.textContent = `${remaining}秒后重试`;
        if (--remaining < 0) {
            clearInterval(interval);
            btn.textContent = '获取验证码';
            btn.disabled = false;
        }
    }, 1000);
}

// DOM加载完成后执行
document.addEventListener('DOMContentLoaded', function() {
    // 验证码请求逻辑
    const captchaBtn = document.getElementById('get-captcha');
    if (captchaBtn) {
        captchaBtn.addEventListener('click', async function() {
            const emailInput = document.querySelector('input[name="email"]');
            const email = emailInput.value.trim();
            
            if (!validateEmail(email)) {
                showError('email-error', '请输入有效的邮箱地址');
                emailInput.focus();
                return;
            }

            const originalText = this.textContent;
            this.disabled = true;
            this.textContent = '发送中...';

            try {
                const response = await fetch(`/auth/captcha/email?email=${encodeURIComponent(email)}`);
                const data = await response.json();
                
                if (data.code === 200) {
                    startCountdown(60);
                    showError('email-error', ''); // 清空错误提示
                } else {
                    showError('email-error', data.message || '验证码发送失败');
                }
            } catch (error) {
                showError('email-error', '网络连接异常');
                console.error('验证码请求失败:', error);
            } finally {
                this.disabled = false;
                this.textContent = originalText;
            }
        });
    }

    // 密码匹配验证
    const passwordConfirm = document.querySelector('input[name="password_confirm"]');
    if (passwordConfirm) {
        passwordConfirm.addEventListener('input', function() {
            const password = document.querySelector('input[name="password"]').value;
            const errorElement = document.getElementById('password-confirm-error');
            if (this.value !== password) {
                errorElement.textContent = '两次输入的密码不一致';
            } else {
                errorElement.textContent = '';
            }
        });
    }
});