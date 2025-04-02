# LLM调用手册

*编辑人：coffee*

## 1. 日报模式

示例代码：

```python
from LLM.llm import EmotionAnalyzer
from datetime import datetime


user_id = "U985"
mode = "daily"
diary = '起来晚了，第一堂课没来得及上，空堂时可筠的同学宁家英来了，告诉我有一封信，是武昌来的，果然是可筠的，她说我与一般老朋友真是音信杳然了。然而我的的确确随时都想着她们，只是懒得不想提笔而已。我发现我是真的堕落了，从灵魂堕落起，外表上也许别人以为我活得很有生气，可是实际上我已经不堪了。我需要一点刺激，需要在我的生活来一个大的波浪，这样也许我可能从新干下去。'
date = datetime(2025, 3, 15, 14, 30, 0)

analyze = EmotionAnalyzer(user_id)
result = analyze.analyze(mode, diary, date)
print(result)
```

参数说明：

`user_id`：用户id，注意要以U开头
`mode`：分为daily与weekly两种模式，对应日报与周报
`dairy`：日记内容
`date`：日记时间戳，格式为datetime(年，月，日，小时，分钟，秒)
`analyze = EmotionAnalyzer(user_id)`：实例化，只用传入参数user_id
`result = analyze.analyze(mode, diary, date)`：传入参数

## 2. 周报模式

示例代码：

```python
from LLM.llm import EmotionAnalyzer
from datetime import datetime

user_id = "U211"
mode = "weekly"
start_date = datetime(2024, 6, 15)
end_date = datetime(2024, 6, 17)

analyze = EmotionAnalyzer(user_id)

# 指定日期模式
result = analyze.analyze(
    mode = mode, 
    start_date=start_date, 
    end_date=end_date)
print(result)

# 默认日期模式（过去7天）
result = analyze.analyze(
    mode = mode, 
)
print(result)
```

参数说明：

`user_id`：用户id，注意要以U开头
`mode`：分为daily与weekly两种模式，对应日报与周报
`start_date(可选)`：周报开始时间，不填默认为过去7天
`end_date`：周报结束时间，不填默认为过去7天
`analyze = EmotionAnalyzer(user_id)`：示例化，只用传入参数user_id

## 3. 删除日记

示例代码：

```python
from LLM.llm import EmotionAnalyzer
from datetime import datetime

user_id = "U211"
date = datetime(2024, 6, 15, 14, 30, 0)

analyze = EmotionAnalyzer(user_id)  # 创建新实例
delete_result = analyze.delete_diary(date)
print(delete_result)
```

参数说明：

`user_id`：用户id，注意要以U开头
`date(必填)`：日记时间戳，格式为datetime(年，月，日，小时，分钟，秒)
`analyze = EmotionAnalyzer(user_id)`：创建实例
`delete_result = analyze.delete_diary(date)`：使用delete_diary方法删除指定时间戳日记

## 4. 注意事项

1. 删除日记前先判定！**若删除的日记没有进行过分析则不要调用删除日记的代码！！！**
2. 分析周报前先判定！**若这段时间没有日记记录则不要调用周报模式！！！**

