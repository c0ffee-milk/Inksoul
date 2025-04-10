document.addEventListener('DOMContentLoaded', function() {
    // 情感构成柱状图
    const emotionalBasis = window.emotionalBasis;

    if (emotionalBasis) {
        const ctx = document.getElementById('emotionalBasisChart').getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: Object.keys(emotionalBasis),
                datasets: [{
                    label: '情感构成比例',
                    data: Object.values(emotionalBasis),
                    backgroundColor: 'rgba(111, 66, 193, 0.5)',
                    borderColor: 'rgba(111, 66, 193, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                scales: {
                    y: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    }
                }
            }
        });
    } else {
        console.error('Emotional basis data is undefined or null.');
    }

    // 事件关键词云图
    const eventKeywords = window.eventKeywords;
    if (eventKeywords && Object.keys(eventKeywords).length > 0) {
        const validEventKeywords = Object.entries(eventKeywords).map(([text, size]) => {
            const validSize = Number(size);
            const scaledSize = isNaN(validSize) ? 10 : Math.max(10, validSize * 1.2); // 减小缩放比例
            console.log('Processed event keyword:', text, scaledSize);
            return [text, scaledSize];
        });
        const eventKeywordsCloud = document.getElementById('eventKeywordsCloud');
        WordCloud(eventKeywordsCloud, {
            list: validEventKeywords,
            backgroundColor: '#f9f6ff',
            color: function() {
                const colors = ['#6f42c1', '#8a63d2', '#a785e2', '#c3a6f2', '#e0c7ff'];
                return colors[Math.floor(Math.random() * colors.length)];
            },
            minSize: 8, // 减小最小字体大小
            maxSize: 25, // 减小最大字体大小
            fontFamily: 'Arial, sans-serif',
            fontWeight: 'bold',
            gridSize: 8,
            rotateRatio: 0.2,
            shrinkToFit: true // 启用自动缩放以适应容器
        });
    } else {
        console.error('Event keywords data is invalid or empty.');
    }

    // 情绪关键词云图
    const emotionKeywords = window.emotionKeywords;
    if (emotionKeywords && Object.keys(emotionKeywords).length > 0) {
        const validEmotionKeywords = Object.entries(emotionKeywords).map(([text, size]) => {
            const validSize = Number(size);
            const scaledSize = isNaN(validSize) ? 10 : Math.max(10, validSize * 1.2); // 减小缩放比例
            console.log('Processed emotion keyword:', text, scaledSize);
            return [text, scaledSize];
        });
        const emotionKeywordsCloud = document.getElementById('emotionKeywordsCloud');
        WordCloud(emotionKeywordsCloud, {
            list: validEmotionKeywords,
            backgroundColor: '#f9f6ff',
            color: function() {
                const colors = ['#6f42c1', '#8a63d2', '#a785e2', '#c3a6f2', '#e0c7ff'];
                return colors[Math.floor(Math.random() * colors.length)];
            },
            minSize: 8, // 减小最小字体大小
            maxSize: 25, // 减小最大字体大小
            fontFamily: 'Arial, sans-serif',
            fontWeight: 'bold',
            gridSize: 8,
            rotateRatio: 0.2,
            shrinkToFit: true // 启用自动缩放以适应容器
        });
    } else {
        console.error('Emotion keywords data is invalid or empty.');
    }
});

console.log('Original event keywords:', eventKeywords);
console.log('Original emotion keywords:', emotionKeywords);