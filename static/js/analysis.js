// static/js/analysis.js
document.addEventListener('DOMContentLoaded', function() {
    // 雷达图配置
    const radarConfig = {
        type: 'radar',
        data: {
            labels: ['喜悦', '信任', '害怕', '惊讶', '难过', '厌恶', '生气', '期待'],
            datasets: [{
                label: '情绪强度',
                data: Object.values({{ analysis.emotional_basis|tojson }}),
                backgroundColor: 'rgba(52, 152, 219, 0.3)',
                borderColor: '#3498db',
                pointBackgroundColor: '#3498db',
                pointBorderColor: '#fff',
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        color: '#7f8c8d',
                        backdropColor: 'transparent'
                    },
                    grid: {
                        color: 'rgba(127, 140, 141, 0.2)'
                    },
                    pointLabels: {
                        color: '#2c3e50',
                        font: {
                            size: 14
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    };

    // 初始化雷达图
    new Chart(document.getElementById('emotionRadar'), radarConfig);

    // 词云生成
    const keywords = document.getElementById('wordcloud').dataset.keywords.split(',');
    const weightedWords = keywords.map(word => [word, Math.random() * 50 + 20]);

    WordCloud(document.getElementById('wordcloud'), {
        list: weightedWords,
        backgroundColor: '#f8f9fa',
        gridSize: 15,
        weightFactor: 1.2,
        fontFamily: 'Arial, sans-serif',
        color: () => `hsl(${Math.random() * 360}, 70%, 50%)`,
        rotateRatio: 0.5,
        rotationSteps: 3,
        drawOutOfBound: false,
        shrinkToFit: true,
        hover: (item, dimension) => {
            if (!dimension) return;
            const tooltip = document.createElement('div');
            tooltip.className = 'word-tooltip';
            tooltip.textContent = item[0];
            tooltip.style.position = 'absolute';
            tooltip.style.left = `${dimension.x}px`;
            tooltip.style.top = `${dimension.y}px`;
            document.body.appendChild(tooltip);

            setTimeout(() => {
                tooltip.remove();
            }, 1000);
        }
    });

    // 交互动画
    document.querySelectorAll('.report-card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.boxShadow = '0 8px 15px rgba(0,0,0,0.1)';
        });

        card.addEventListener('mouseleave', function() {
            this.style.boxShadow = '0 4px 6px rgba(0,0,0,0.05)';
        });
    });
});