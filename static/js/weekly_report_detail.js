// 情感构成柱状图
const emotionalBasis = {
    "喜悦": {{ content.emotional_basis.喜悦 }},
    "信任": {{ content.emotional_basis.信任 }},
    "害怕": {{ content.emotional_basis.害怕 }},
    "惊讶": {{ content.emotional_basis.惊讶 }},
    "难过": {{ content.emotional_basis.难过 }},
    "厌恶": {{ content.emotional_basis.厌恶 }},
    "生气": {{ content.emotional_basis.生气 }},
    "期待": {{ content.emotional_basis.期待 }}
};

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

// 事件关键词云图
const eventKeywords = Object.entries({{ content.event_key_words|tojson }});
const eventKeywordsCloud = document.getElementById('eventKeywordsCloud');
WordCloud(eventKeywordsCloud, {
    list: eventKeywords,
    backgroundColor: '#f9f6ff',
    color: function () { return 'rgba(111, 66, 193, 0.8)'; }
});

// 情绪关键词云图
const emotionKeywords = Object.entries({{ content.emotion_key_words|tojson }});
const emotionKeywordsCloud = document.getElementById('emotionKeywordsCloud');
WordCloud(emotionKeywordsCloud, {
    list: emotionKeywords,
    backgroundColor: '#f9f6ff',
    color: function () { return 'rgba(111, 66, 193, 0.8)'; }
});