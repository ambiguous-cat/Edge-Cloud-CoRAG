#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from add_document_from_file import add_document_from_file

def test_add_document():
    """测试添加文档功能"""
    print("🧪 测试添加文档功能")
    print("=" * 40)
    
    # 测试添加语料文件
    test_files = [
        "语料/执掌雷劫.txt",
        "语料/A benchmark study of simulation methods for single-cell RNA sequencing data.txt"
    ]
    
    for file_path in test_files:
        try:
            print(f"\n📄 添加文档: {file_path}")
            doc_id = add_document_from_file(file_path)
            if doc_id:
                print(f"✅ 成功添加，文档ID: {doc_id}")
            else:
                print("❌ 添加失败")
        except Exception as e:
            print(f"❌ 添加文档时出错: {e}")

if __name__ == "__main__":
    test_add_document()
