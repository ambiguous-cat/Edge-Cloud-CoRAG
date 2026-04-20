"""
本地知识库管理模块
负责缓存常见问题和回答
"""
import os
import time


class LocalKnowledgeBase:
    """本地知识库管理器"""
    
    def __init__(self, storage_path="local_knowledge"):
        self.storage_path = storage_path
        self.common_qa = {}  # 常见问题缓存
        os.makedirs(storage_path, exist_ok=True)
        
    def cache_response(self, question, answer):
        """缓存常见问题的回答"""
        self.common_qa[question] = {
            "answer": answer,
            "timestamp": time.time()
        }
        
    def get_cached_response(self, question):
        """获取缓存的回答"""
        # 简单匹配问题
        if question in self.common_qa:
            return self.common_qa[question]["answer"]
            
        # 模糊匹配（简化版）
        for q in self.common_qa:
            if q in question or question in q:
                return self.common_qa[q]["answer"]
        return None
    
    def clear_cache(self):
        """清空缓存"""
        self.common_qa.clear()
    
    def get_cache_size(self):
        """获取缓存大小"""
        return len(self.common_qa)
    
    def get_cache_info(self):
        """获取缓存信息"""
        return {
            "size": len(self.common_qa),
            "questions": list(self.common_qa.keys())
        }
