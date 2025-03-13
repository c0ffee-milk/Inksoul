document.addEventListener('DOMContentLoaded', function() {
    // 通用表单验证逻辑
    function validateEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(String(email).toLowerCase());
    }

    // 注册页面验证码获取逻辑
    const captchaBtn = document.getElementById('get-captcha');
    if (captchaBtn) {
        captchaBtn.addEventListener('click', async function() {
            const emailInput = document.querySelector('input[name="email"]');
            if (!validateEmail(emailInput.value)) {
                showError('email-error', '请输入有效的邮箱地址');
                return;
            }

            this.disabled = true;
            this.textContent = '发送中...';

            try {
                const response = await fetch('/auth/send_captcha', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name="csrf_token"]').value
                    },
                    body: JSON.stringify({ email: emailInput.value })
                });

                const data = await response.json();
                if (data.code === 200) {
                    startCountdown(60);
                    showSuccess('验证码已发送，请查看邮箱');
                } else {
                    showError('email-error', data.message || '发送失败，请重试');
                }
            } catch (error) {
                showError('email-error', '网络错误，请稍后重试');
            } finally {
                this.disabled = false;
                this.textContent = '获取验证码';
            }
        });
    }

    // 倒计时功能
    function startCountdown(seconds) {
        const btn = captchaBtn;
        let remaining = seconds;
        btn.disabled = true;

        const interval = setInterval(() => {
            btn.textContent = `${remaining}秒后重试`;
            if (--remaining < 0) {
                clearInterval(interval);
                btn.disabled = false;
                btn.textContent = '获取验证码';
            }
        }, 1000);
    }

    // 错误提示显示
    function showError(elementId, message) {
        const element = document.getElementById(elementId);
        element.textContent = message;
        element.style.display = 'block';
        setTimeout(() => element.style.display = 'none', 3000);
    }

    // 成功提示
    function showSuccess(message) {
        const toast = document.createElement('div');
        toast.className = 'success-toast';
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    }

    // 密码匹配验证
    const passwordConfirm = document.querySelector('input[name="password_confirm"]');
    if (passwordConfirm) {
        passwordConfirm.addEventListener('input', function() {
            const password = document.querySelector('input[name="password"]').value;
            if (this.value !== password) {
                showError('password-confirm-error', '两次输入的密码不一致');
            } else {
                document.getElementById('password-confirm-error').textContent = '';
            }
        });
    }
});