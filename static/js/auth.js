// auth.js 更新
document.addEventListener('DOMContentLoaded', function() {
    // 验证码请求
    const captchaBtn = document.getElementById('get-captcha');
    if (captchaBtn) {
        captchaBtn.addEventListener('click', async function() {
            const email = document.querySelector('input[name="email"]').value;
            if (!validateEmail(email)) {
                showError('email-error', '邮箱格式不正确');
                return;
            }

            this.disabled = true;
            this.textContent = '发送中...';

            try {
                const response = await fetch('/auth/captcha/email?email=' + email);
                const data = await response.json();
                if (data.code === 200) {
                    startCountdown(60);
                    showSuccess('验证码已发送');
                } else {
                    showError('email-error', data.message);
                }
            } catch (error) {
                showError('email-error', '请求失败');
            } finally {
                this.disabled = false;
                this.textContent = '获取验证码';
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
                errorElement.textContent = '两次密码不一致';
            } else {
                errorElement.textContent = '';
            }
        });
    }
});