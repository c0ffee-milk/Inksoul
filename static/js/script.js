// 实现日记翻动效果
const slides = document.querySelectorAll('.diary-slide');
let currentSlide = 0;

/**
 * 显示指定索引的日记幻灯片
 * @param {number} index 幻灯片的索引
 */
function showSlide(index) {
    slides.forEach((slide, i) => {
        if (i === index) {
            slide.classList.add('active');
        } else {
            slide.classList.remove('active');
        }
    });
}

/**
 * 切换到下一张日记幻灯片
 */
function nextSlide() {
    currentSlide = (currentSlide + 1) % slides.length;
    showSlide(currentSlide);
}

/**
 * 切换到上一张日记幻灯片
 */
function prevSlide() {
    currentSlide = (currentSlide - 1 + slides.length) % slides.length;
    showSlide(currentSlide);
}

// 每隔 5 秒切换一次日记
setInterval(nextSlide, 5000);

// 初始化显示第一个日记
showSlide(currentSlide);

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