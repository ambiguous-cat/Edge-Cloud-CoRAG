#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取所有文档信息和向量索引的脚本
提供完整的知识库概览
"""

import sqlite3
import os
import json
import faiss
import numpy as np
from typing import Dict, List, Any
import pandas as pd
from datetime import datetime

class DocumentInfoManager:
    def __init__(self, db_path="local_knowledge.db", index_path="faiss_index.index"):
        self.db_path = db_path
        self.index_path = index_path
    
    def get_database_info(self) -> Dict[str, Any]:
        """获取数据库基本信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取所有文档信息
            cursor.execute("""
                SELECT d.id, d.title, d.source, d.created_at, 
                       LENGTH(d.content) as content_length,
                       SUBSTR(d.content, 1, 100) as content_preview,
                       COUNT(dc.id) as chunk_count
                FROM documents d
                LEFT JOIN document_chunks dc ON d.id = dc.document_id
                GROUP BY d.id, d.title, d.source, d.created_at, d.content
                ORDER BY d.created_at DESC
            """)
            
            documents = []
            for row in cursor.fetchall():
                doc_id, title, source, created_at, content_length, content_preview, chunk_count = row
                documents.append({
                    "id": doc_id,
                    "title": title,
                    "source": source or "未知",
                    "created_at": created_at,
                    "content_length": content_length,
                    "content_preview": content_preview + ("..." if content_length > 100 else ""),
                    "chunk_count": chunk_count
                })
            
            # 获取统计信息
            cursor.execute("SELECT COUNT(*) FROM documents")
            total_docs = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM document_chunks")
            total_chunks = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "documents": documents,
                "total_documents": total_docs,
                "total_chunks": total_chunks
            }
            
        except Exception as e:
            print(f"❌ 获取数据库信息失败: {e}")
            return {"documents": [], "total_documents": 0, "total_chunks": 0}
    
    def get_faiss_info(self) -> Dict[str, Any]:
        """获取FAISS索引信息"""
        try:
            if not os.path.exists(self.index_path):
                return {
                    "exists": False,
                    "total_vectors": 0,
                    "dimension": 0,
                    "index_type": "索引文件不存在",
                    "file_size": 0
                }
            
            # 读取索引
            index = faiss.read_index(self.index_path)
            file_size = os.path.getsize(self.index_path)
            
            return {
                "exists": True,
                "total_vectors": index.ntotal,
                "dimension": index.d,
                "index_type": str(type(index).__name__),
                "file_size": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            return {
                "exists": False,
                "total_vectors": 0,
                "dimension": 0,
                "index_type": f"索引读取失败: {str(e)}",
                "file_size": 0
            }
    
    def get_document_detail(self, doc_id: int) -> Dict[str, Any]:
        """获取指定文档的详细信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取文档基本信息
            cursor.execute("""
                SELECT id, title, content, source, created_at
                FROM documents 
                WHERE id = ?
            """, (doc_id,))
            
            doc_result = cursor.fetchone()
            if not doc_result:
                return {"error": f"未找到ID为 {doc_id} 的文档"}
            
            doc_id, title, content, source, created_at = doc_result
            
            # 获取文档块信息
            cursor.execute("""
                SELECT id, chunk_content, chunk_index
                FROM document_chunks 
                WHERE document_id = ?
                ORDER BY chunk_index
            """, (doc_id,))
            
            chunks = []
            for chunk_row in cursor.fetchall():
                chunk_id, chunk_content, chunk_index = chunk_row
                chunks.append({
                    "id": chunk_id,
                    "content": chunk_content,
                    "index": chunk_index,
                    "length": len(chunk_content)
                })
            
            conn.close()
            
            return {
                "id": doc_id,
                "title": title,
                "content": content,
                "source": source or "未知",
                "created_at": created_at,
                "content_length": len(content),
                "chunks": chunks,
                "chunk_count": len(chunks)
            }
            
        except Exception as e:
            return {"error": f"获取文档详情失败: {str(e)}"}
    
    def export_to_json(self, output_file="documents_info.json") -> bool:
        """导出所有信息到JSON文件"""
        try:
            db_info = self.get_database_info()
            faiss_info = self.get_faiss_info()
            
            export_data = {
                "export_time": datetime.now().isoformat(),
                "database_info": db_info,
                "faiss_info": faiss_info,
                "summary": {
                    "total_documents": db_info["total_documents"],
                    "total_chunks": db_info["total_chunks"],
                    "total_vectors": faiss_info["total_vectors"],
                    "index_dimension": faiss_info["dimension"]
                }
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 信息已导出到: {output_file}")
            return True
            
        except Exception as e:
            print(f"❌ 导出失败: {e}")
            return False
    
    def print_summary(self):
        """打印知识库概览"""
        print("📚 知识库信息概览")
        print("=" * 60)
        
        # 数据库信息
        db_info = self.get_database_info()
        print(f"\n📄 数据库信息:")
        print(f"   文档总数: {db_info['total_documents']}")
        print(f"   文档块总数: {db_info['total_chunks']}")
        print(f"   数据库文件: {self.db_path}")
        print(f"   数据库大小: {self._get_file_size(self.db_path)}")
        
        # FAISS索引信息
        faiss_info = self.get_faiss_info()
        print(f"\n🔍 FAISS索引信息:")
        print(f"   索引状态: {'✅ 存在' if faiss_info['exists'] else '❌ 不存在'}")
        print(f"   向量总数: {faiss_info['total_vectors']}")
        print(f"   向量维度: {faiss_info['dimension']}")
        print(f"   索引类型: {faiss_info['index_type']}")
        if faiss_info['exists']:
            print(f"   索引大小: {faiss_info['file_size_mb']} MB")
        
        # 最近文档
        if db_info['documents']:
            print(f"\n📋 最近添加的文档 (前5个):")
            for i, doc in enumerate(db_info['documents'][:5], 1):
                print(f"   {i}. {doc['title']} ({doc['created_at']})")
                print(f"      来源: {doc['source']} | 长度: {doc['content_length']} 字符 | 块数: {doc['chunk_count']}")
        
        print(f"\n🎯 数据一致性检查:")
        consistency = self._check_consistency(db_info, faiss_info)
        for check, result in consistency.items():
            status = "✅" if result["status"] else "⚠️"
            print(f"   {status} {check}: {result['message']}")
    
    def _get_file_size(self, file_path: str) -> str:
        """获取文件大小的友好显示"""
        try:
            if not os.path.exists(file_path):
                return "文件不存在"
            
            size = os.path.getsize(file_path)
            if size < 1024:
                return f"{size} B"
            elif size < 1024 * 1024:
                return f"{size / 1024:.1f} KB"
            else:
                return f"{size / (1024 * 1024):.1f} MB"
        except:
            return "无法获取"
    
    def _check_consistency(self, db_info: Dict, faiss_info: Dict) -> Dict[str, Dict]:
        """检查数据一致性"""
        checks = {}
        
        # 检查文档块数量与向量数量是否匹配
        chunks_count = db_info['total_chunks']
        vectors_count = faiss_info['total_vectors']
        
        if chunks_count == vectors_count:
            checks["向量数量一致性"] = {
                "status": True,
                "message": f"文档块数量({chunks_count})与向量数量({vectors_count})匹配"
            }
        else:
            checks["向量数量一致性"] = {
                "status": False,
                "message": f"文档块数量({chunks_count})与向量数量({vectors_count})不匹配"
            }
        
        # 检查索引文件是否存在
        checks["索引文件存在"] = {
            "status": faiss_info['exists'],
            "message": "FAISS索引文件存在" if faiss_info['exists'] else "FAISS索引文件缺失"
        }
        
        # 检查数据库文件是否存在
        db_exists = os.path.exists(self.db_path)
        checks["数据库文件存在"] = {
            "status": db_exists,
            "message": "数据库文件存在" if db_exists else "数据库文件缺失"
        }
        
        return checks

def main():
    """主函数"""
    print("🚀 启动文档信息管理器...")
    
    manager = DocumentInfoManager()
    
    while True:
        print("\n" + "=" * 60)
        print("📚 知识库文档信息管理")
        print("=" * 60)
        print("1. 📊 显示知识库概览")
        print("2. 📄 查看指定文档详情")
        print("3. 📋 列出所有文档")
        print("4. 💾 导出信息到JSON")
        print("5. 🔍 检查数据一致性")
        print("0. 🚪 退出")
        
        choice = input("\n请选择操作 (0-5): ").strip()
        
        if choice == "0":
            print("👋 再见!")
            break
        elif choice == "1":
            manager.print_summary()
        elif choice == "2":
            try:
                doc_id = int(input("请输入文档ID: "))
                detail = manager.get_document_detail(doc_id)
                if "error" in detail:
                    print(f"❌ {detail['error']}")
                else:
                    print(f"\n📄 文档详情:")
                    print(f"   ID: {detail['id']}")
                    print(f"   标题: {detail['title']}")
                    print(f"   来源: {detail['source']}")
                    print(f"   创建时间: {detail['created_at']}")
                    print(f"   内容长度: {detail['content_length']} 字符")
                    print(f"   文档块数: {detail['chunk_count']}")
                    
                    if detail['chunks']:
                        print(f"\n📝 文档块信息:")
                        for chunk in detail['chunks'][:3]:  # 只显示前3个块
                            print(f"   块 {chunk['index']}: {chunk['content'][:100]}...")
                        if len(detail['chunks']) > 3:
                            print(f"   ... 还有 {len(detail['chunks']) - 3} 个块")
            except ValueError:
                print("❌ 请输入有效的数字")
        elif choice == "3":
            db_info = manager.get_database_info()
            if db_info['documents']:
                print(f"\n📋 所有文档列表 ({len(db_info['documents'])} 个):")
                for doc in db_info['documents']:
                    print(f"   ID {doc['id']}: {doc['title']}")
                    print(f"      来源: {doc['source']} | 创建: {doc['created_at']}")
                    print(f"      长度: {doc['content_length']} 字符 | 块数: {doc['chunk_count']}")
                    print()
            else:
                print("📋 知识库中暂无文档")
        elif choice == "4":
            filename = input("输入导出文件名 (默认: documents_info.json): ").strip()
            if not filename:
                filename = "documents_info.json"
            manager.export_to_json(filename)
        elif choice == "5":
            db_info = manager.get_database_info()
            faiss_info = manager.get_faiss_info()
            consistency = manager._check_consistency(db_info, faiss_info)
            
            print(f"\n🔍 数据一致性检查结果:")
            for check, result in consistency.items():
                status = "✅" if result["status"] else "⚠️"
                print(f"   {status} {check}: {result['message']}")
        else:
            print("❌ 无效选择，请重新输入")

if __name__ == "__main__":
    main()
