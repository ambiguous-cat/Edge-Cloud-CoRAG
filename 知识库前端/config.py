#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
知识库管理前端配置文件
"""

# API服务器配置
API_CONFIG = {
    "local": "http://localhost:8005",      # 本地API服务器
    "cloud": "http://8.133.246.212:8005",
    # "cloud": "http://120.26.231.14:8005", # 云端API服务器
    "timeout": 30,
    "endpoints": {
        "search": "/search",
        "add_document": "/add_document", 
        "add_json_document": "/add_json_document",
        "documents": "/documents",
        "health": "/docs"
    }
}

# 界面配置
UI_CONFIG = {
    "title": "知识库管理系统",
    "port": 7862,
    "host": "127.0.0.1",
    "theme": "soft"
}

# 文件上传配置
UPLOAD_CONFIG = {
    "allowed_extensions": [".txt", ".md", ".json"],
    "max_file_size": 10 * 1024 * 1024,  # 10MB
    "encoding": "utf-8"
}

# 搜索配置
SEARCH_CONFIG = {
    "default_top_k": 10,
    "max_top_k": 50,
    "min_query_length": 1,
    "preview_length": 200
}
