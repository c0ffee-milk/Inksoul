// static/js/analysis.js
document.addEventListener('DOMContentLoaded', function() {
    // 情绪雷达图初始化
    const radarCanvas = document.getElementById('emotionRadar');
    if (radarCanvas) {
        try {
            const emotionalData = JSON.parse(radarCanvas.dataset.emotionalBasis);

            new Chart(radarCanvas, {
                type: 'radar',
                data: {
                    labels: Object.keys(emotionalData),
                    datasets: [{
                        label: '情绪强度',
                        data: Object.values(emotionalData),
                        backgroundColor: 'rgba(111, 66, 193, 0.2)',
                        borderColor: '#6f42c1',
                        pointBackgroundColor: '#6f42c1',
                        borderWidth: 2,
                        pointRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        r: {
                            beginAtZero: true,
                            max: 100,
                            grid: {
                                color: '#e9e1f9'
                            },
                            pointLabels: {
                                font: {
                                    size: 14
                                },
                                color: '#6f42c1'
                            },
                            ticks: {
                                display: false
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        } catch (error) {
            console.error('雷达图初始化失败:', error);
        }
    }

    // 词云初始化
    const wordcloudEl = document.getElementById('wordcloud');
    if (wordcloudEl && wordcloudEl.dataset.keywords) {
        try {
            const keywords = wordcloudEl.dataset.keywords.split(',');
            const wordList = keywords.map(word => [word, 50 + Math.random() * 50]);

            WordCloud(wordcloudEl, {
                list: wordList,
                gridSize: 12,
                weightFactor: 8,
                fontFamily: 'Inter, sans-serif',
                color: () => {
                    const colors = ['#6f42c1', '#8a63d2', '#a885db', '#c5a8e4'];
                    return colors[Math.floor(Math.random() * colors.length)];
                },
                backgroundColor: '#f9f6ff',
                rotateRatio: 0.3,
                rotationSteps: 3,
                drawOutOfBound: false
            });
        } catch (error) {
            console.error('词云初始化失败:', error);
        }
    }

    // 统一悬停效果
    document.querySelectorAll('.report-card').forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-5px)';
            card.style.boxShadow = '0 8px 20px rgba(111,66,193,0.15)';
        });

        card.addEventListener('mouseleave', () => {
            card.style.transform = 'none';
            card.style.boxShadow = '0 4px 6px rgba(0,0,0,0.05)';
        });
    });
});