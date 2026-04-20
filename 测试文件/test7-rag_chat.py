#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from rag_chat import RAGChatService
from search_similar_documents import DocumentSearcher

def test_rag_chat():
    """测试RAG对话功能"""
    print("🤖 测试RAG对话功能")
    print("=" * 40)
    
    try:
        # 初始化RAG服务
        searcher = DocumentSearcher()
        rag_service = RAGChatService(searcher=searcher, model_type="deepseek-r1:1.5b")
        
        # 测试问题
        test_questions = [
            "scRNA-seq模拟方法有哪些局限性？",
            "什么是单细胞RNA测序？",
            "雷劫是什么？"
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n🔍 问题 {i}: {question}")
            print("🤖 回答:")
            
            try:
                # 使用流式响应
                response_parts = []
                for chunk in rag_service.rag_chat_stream(question, top_k=3):
                    response_parts.append(chunk)
                    print(chunk, end="", flush=True)
                
                print("\n" + "="*50)
                
            except Exception as e:
                print(f"❌ 回答问题时出错: {e}")
        
    except Exception as e:
        print(f"❌ 初始化RAG服务时出错: {e}")

if __name__ == "__main__":
    test_rag_chat()
