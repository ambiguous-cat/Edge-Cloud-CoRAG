import requests

base = "http://localhost:8005"

# 添加文档
r = requests.post(f"{base}/add_document", json={
    "file_path": "C:/Users/cklzs/Desktop/学习/新建文件夹/语料/执掌雷劫.txt"
})
print("add_document:", r.status_code, r.json())

# 相似度查询
r = requests.post(f"{base}/search", json={
    "query": "这是查询内容",
    "top_k": 5
})
print("search:", r.status_code, r.json())