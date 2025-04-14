import sqlite3

conn = sqlite3.connect('d:/webapp/web_for_Inksoul/data_base/diary_db/U17/chroma.sqlite3')
cursor = conn.cursor()

# 只查询键为chroma:document的元数据
cursor.execute("SELECT * FROM embedding_metadata WHERE key='chroma:document'")
doc_metadata = cursor.fetchall()

# 打印匹配的元数据记录
print("chroma:document 元数据记录:")
for i, metadata in enumerate(doc_metadata, 1):
    print(f"记录 {i}:")
    print(f"  字符串值: {metadata[2]}")  # 只输出字符串值部分

conn.close()