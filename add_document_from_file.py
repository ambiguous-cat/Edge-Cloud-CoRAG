#!/usr/bin/env python
# -*- coding: utf-8 -*-

from initialize import add_document_to_knowledge
import sys
import os

def add_document_from_file(file_path, title=None, source=None):
    """从txt文件添加文档到知识库
    
    参数:
        file_path: txt文件路径
        title: 文档标题(可选，默认使用文件名)
        source: 文档来源(可选)
    
    返回:
        document_id: 添加成功的文档ID
    """
    try:
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"错误: 文件 '{file_path}' 不存在")
            return None
        
        # 检查文件类型
        if not file_path.lower().endswith('.txt'):
            print(f"错误: 仅支持txt文件，'{file_path}' 不是txt文件")
            return None
        
        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 如果没有指定标题，使用文件名(不含扩展名)
        if title is None:
            title = os.path.splitext(os.path.basename(file_path))[0]

        # 添加文档
        document_id = add_document_to_knowledge(title, content, source)
        print(f"文档 '{title}' 已成功从文件 '{file_path}' 添加到知识库，ID: {document_id}")
        return document_id
    except Exception as e:
        print(f"添加文档时出错: {e}")
        return None
