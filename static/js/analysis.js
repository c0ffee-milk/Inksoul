document.addEventListener('DOMContentLoaded', function () {
    // 情绪雷达图初始化（假设此处代码逻辑正确，若有问题需另外排查）
    const radarCanvas = document.getElementById('emotionRadar');
    if (radarCanvas) {
        try {
            const emotionalData = JSON.parse(radarCanvas.dataset.emotionalBasis);
            const newOrder = ['喜悦', '期待', '信任', '惊讶', '生气', '厌恶', '难过', '害怕'];
            const newData = {};
            newOrder.forEach((emotion) => {
                if (emotionalData[emotion]!== undefined) {
                    newData[emotion] = emotionalData[emotion];
                }
            });

            new Chart(radarCanvas, {
                type: 'radar',
                data: {
                    labels: Object.keys(newData),
                    datasets: [{
                        label: '情绪强度',
                        data: Object.values(newData),
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
    const wordcloudElement = document.getElementById('wordcloud');
    const keywords = window.keywords;

    if (wordcloudElement && keywords && Object.keys(keywords).length > 0) {
        try {
            // 处理关键词数据
            const validKeywords = Object.entries(keywords).map(([text, size]) => {
                const validSize = Number(size);
                const scaledSize = isNaN(validSize)? 10 : Math.max(10, validSize * 0.7);
                console.log('Processed keyword:', text, scaledSize);
                return [text, scaledSize];
            });

            // 计算最大和最小的大小值，用于颜色映射
            const sizes = validKeywords.map(([_, size]) => size);
            const minSize = Math.min(...sizes);
            const maxSize = Math.max(...sizes);

            // 确保词云容器有合适样式
            wordcloudElement.style.width = '100%';
            wordcloudElement.style.height = '400px';

            // 丰富的颜色方案
            const colorPalette = ['#6f42c1', '#8a63d2', '#9d79e2', '#b192f2', '#c4a9ff'];

            WordCloud(wordcloudElement, {
                list: validKeywords,
                backgroundColor: '#f9f6ff',
                // 根据关键词大小调整颜色深浅
                color: function (word, weight) {
                    const index = Math.floor((weight - minSize) / (maxSize - minSize) * (colorPalette.length - 1));
                    return colorPalette[index];
                },
                minSize: 10, // 调整最小字体大小
                maxSize: 50, // 调整最大字体大小
                shuffle: false,
                wait: true,
               drawOutOfBound: false ,
                fontFamily: 'Arial, sans-serif', // 选择合适的字体
                fontWeight: 'bold', // 字体加粗
                rotateRatio: 0.5, // 调整旋转比例
                minRotation: -Math.PI / 3, // 最小旋转角度
                maxRotation: Math.PI / 5// 最大旋转角度
            });
        } catch (error) {
            console.error('词云初始化失败:', error);
        }
    } else {
        console.error('Keywords data is invalid or empty.');
    }

    // 统一悬停效果
    document.querySelectorAll('.report-card').forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-5px)';
            card.style.boxShadow = '0 8px 20px rgba(111, 66, 193, 0.15)';
        });

        card.addEventListener('mouseleave', () => {
            card.style.transform = 'none';
            card.style.boxShadow = '0 4px 6px rgba(0, 0, 0, 0.05)';
        });
    });
});