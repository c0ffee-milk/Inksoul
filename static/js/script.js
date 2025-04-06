// 日记卡片交互
document.querySelectorAll('.diary-card').forEach(card => {
    // 点击卡片主体
    card.querySelector('.card-content').addEventListener('click', function(e) {
        const diaryId = card.dataset.id;
        window.location.href = `/diary/${diaryId}`;
    });

    // 点击分析按钮
    card.querySelector('.analyze-btn').addEventListener('click', async function(e) {
        e.stopPropagation();
        const diaryId = card.dataset.id;
        const analyzeBtn = this;

        try {
            // 设置加载状态
            analyzeBtn.classList.add('loading');
            analyzeBtn.innerHTML = '分析中&nbsp;';

            const response = await fetch(`/diary/${diaryId}/analyze`);

            if (!response.ok) {
                throw new Error(`分析失败: ${response.status}`);
            }

            const report = await response.json();

            // 更新按钮状态
            analyzeBtn.classList.remove('loading');
            analyzeBtn.classList.add('disabled');
            analyzeBtn.innerHTML = '已分析';
            analyzeBtn.disabled = true;

            // 更新模态框内容
            const modal = document.getElementById('report-modal');
            const content = document.getElementById('report-content');
            content.innerHTML = `
                <p><strong>情绪类型：</strong>${report.analysis.emotion_type || '未知'}</p>
                <p><strong>综合分析：</strong>${report.analysis.overall_analysis || '未知'}</p>
                <p>${'请点击日记框查看情绪分析报告详情！'}</p>
            `;
            modal.style.display = 'flex';

        } catch (error) {
            // 恢复按钮状态
            analyzeBtn.classList.remove('loading');
            analyzeBtn.innerHTML = '分析报告';
            console.error('获取分析报告失败:', error);

            // 更友好的错误提示
            const modal = document.getElementById('report-modal');
            modal.style.display = 'flex';
            document.getElementById('report-content').innerHTML = `
                <div class="error-message">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>分析失败，请稍后重试</p>
                    <small>错误详情：${error.message}</small>
                </div>
            `;
        }
    });
});

// 模态框控制
document.querySelectorAll('.close').forEach(closeBtn => {
    closeBtn.addEventListener('click', () => {
        document.getElementById('report-modal').style.display = 'none';
    });
});

// 修改原有模态关闭逻辑
window.onclick = function(event) {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
};

// 日记撰写功能
const writeDiaryBtn = document.getElementById('write-diary-btn');
const diaryWrite = document.getElementById('diary-write');
const saveDiaryBtn = document.getElementById('save-diary');

writeDiaryBtn.addEventListener('click', () => {
    diaryWrite.style.display = 'block';
});

saveDiaryBtn.addEventListener('click', () => {
    const title = document.getElementById('diary-title').value;
    const content = document.getElementById('diary-content').value;

    if (title && content) {
        // 获取 CSRF Token
        const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

        // 发送 POST 请求
        fetch('/diary/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken
            },
            body: new URLSearchParams({
                'title': title,
                'content': content
            })
        })
        .then(response => {
            if (response.redirected) {
                window.location.href = response.url; // 处理重定向
            } else {
                return response.json();
            }
        })
        .then(data => {
            if (data && data.success) {
                window.location.reload(); // 成功则刷新页面
            } else if (data) {
                alert(data.message || "保存失败");
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert("请求失败，请检查网络");
        });
    } else {
        alert("标题和内容不能为空！");
    }
});


// 获取日记输入框和日记网格元素
const diaryContent = document.getElementById('diary-content');
const diaryGrid = document.querySelector('.diary-grid');

// 监听输入事件
diaryContent.addEventListener('input', function() {
    // 动态调整输入框的高度
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';

    // 确保日记网格跟随下移
    // 由于输入框高度变化，页面布局会自动调整
});


// 分页功能
const prevPageBtn = document.getElementById('prev-page');
const nextPageBtn = document.getElementById('next-page');

prevPageBtn.addEventListener('click', prevSlide);
nextPageBtn.addEventListener('click', nextSlide);

// 搜索功能
const searchInput = document.querySelector('.search-box input');
const searchBtn = document.querySelector('.search-box button');

searchBtn.addEventListener('click', () => {
    const keyword = searchInput.value.toLowerCase();
    slides.forEach((slide, i) => {
        const title = slide.querySelector('h3').textContent.toLowerCase();
        const content = slide.querySelector('p').textContent.toLowerCase();
        if (title.includes(keyword) || content.includes(keyword)) {
            showSlide(i);
            return;
        }
    });
});



// 注册登录弹窗功能
const registerBtn = document.getElementById('register-btn');
const loginBtn = document.getElementById('login-btn');
const registerModal = document.getElementById('register-modal');
const loginModal = document.getElementById('login-modal');
const registerClose = document.getElementById('register-close');
const loginClose = document.getElementById('login-close');

registerBtn.addEventListener('click', () => {
    registerModal.style.display = 'block';
});

loginBtn.addEventListener('click', () => {
    loginModal.style.display = 'block';
});

registerClose.addEventListener('click', () => {
    registerModal.style.display = 'none';
});

loginClose.addEventListener('click', () => {
    loginModal.style.display = 'none';
});

// script.js 新增周报功能
// 修改后的周报按钮交互
const weeklyClose = document.querySelector('.weekly-close');

// 打开周报模态框
writeWeeklyBtn.addEventListener('click', () => {
    weeklyModal.style.display = 'flex';
    document.body.style.overflow = 'hidden'; // 禁止背景滚动
});

// 关闭周报模态框
weeklyClose.addEventListener('click', () => {
    weeklyModal.style.display = 'none';
    document.body.style.overflow = 'auto';
});

// 点击外部关闭
window.addEventListener('click', (e) => {
    if (e.target === weeklyModal) {
        weeklyModal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
});

// 周报表单提交
document.getElementById('weekly-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const startDate = document.getElementById('start-date').value;
    const endDate = document.getElementById('end-date').value;
    const submitBtn = document.getElementById('submit-weekly');
    const errorDiv = document.getElementById('weekly-error');
    // 客户端验证
    if (!start || !end) {
        errorDiv.textContent = "请选择开始和结束日期";
        return;
    }
    if (start > end) {
        errorDiv.textContent = "结束日期不能早于开始日期";
        return;
    }

    submitBtn.classList.add('loading');
    submitBtn.innerHTML = '生成中...';

    try {
        const response = await fetch('/diary/generate_weekly_report', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
            },
            body: new URLSearchParams({
                'start_time': startDate,
                'end_time': endDate
            })
        });

        const data = await response.json();
        if (data.success) {
            window.location.href = data.redirect;
        } else {
            errorDiv.textContent = data.message || '生成周报失败';
        }
    } catch (error) {
        errorDiv.textContent = '网络请求失败，请稍后重试';
    } finally {
        submitBtn.classList.remove('loading');
        submitBtn.innerHTML = '生成报告';
    }
});

// 关闭周报模态框
document.querySelectorAll('.close').forEach(btn => {
    btn.addEventListener('click', () => {
        weeklyModal.style.display = 'none';
    });
});