// 情感构成柱状图
// 修改后的情感构成数据获取
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
if (eventKeywords) {
    const eventKeywordsCloud = document.getElementById('eventKeywordsCloud');
    WordCloud(eventKeywordsCloud, {
        list: Object.entries(eventKeywords).map(([text, size]) => [text, size]),
        backgroundColor: '#f9f6ff',
        color: () => 'rgba(111, 66, 193, 0.8)'
    });
} else {
    console.error('Event keywords data is undefined or null.');
}

// 情绪关键词云图
const emotionKeywords = window.emotionKeywords;
if (emotionKeywords) {
    const emotionKeywordsCloud = document.getElementById('emotionKeywordsCloud');
    WordCloud(emotionKeywordsCloud, {
        list: Object.entries(emotionKeywords).map(([text, size]) => [text, size]),
        backgroundColor: '#f9f6ff',
        color: () => 'rgba(111, 66, 193, 0.8)'
    });
} else {
    console.error('Emotion keywords data is undefined or null.');
}