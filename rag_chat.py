#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RAG对话生成模块 - 简化版
仅支持流式响应，代码更简洁易懂
"""

from typing import List, Dict, Any, Generator, Tuple
from dotenv import load_dotenv
import time
import json

from search_similar_documents import DocumentSearcher
import chat_model

load_dotenv()

class RAGChatService:
    """RAG对话服务 - 简化版，仅支持流式响应"""
    
    def __init__(self, 
                 searcher: DocumentSearcher = None,
                 model_type: str = "llama3.1"):
        """
        初始化RAG对话服务
        
        Args:
            searcher: 文档检索器
            model_type: 模型类型 (llama3.1, gpt-4)
        """
        self.searcher = searcher or DocumentSearcher()
        self.model_type = model_type
        
        # 设置chat_model模块的模型类型
        chat_model.set_chat_model(model_type)
    
    def switch_model(self, model_type: str):
        """切换对话模型"""
        self.model_type = model_type
        chat_model.set_chat_model(model_type)
    
    def retrieve_documents(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """检索相关文档"""
        try:
            results = self.searcher.search_similar_documents(query, top_k)
            return results
        except Exception as e:
            print(f"文档检索失败: {e}")
            return []
    
    def filter_documents_by_similarity(self, documents: List[Dict[str, Any]], similarity_threshold: float = 0.0) -> Dict[str, Any]:
        """
        根据相似度阈值过滤文档
        
        Args:
            documents: 原始文档列表
            similarity_threshold: 相似度阈值 (0.0-1.0)
            
        Returns:
            dict: 包含过滤后的文档和统计信息
        """
        if not documents:
            return {
                'filtered_documents': [],
                'original_count': 0,
                'filtered_count': 0,
                'accepted_count': 0,
                'threshold': similarity_threshold
            }
        
        filtered_documents = []
        original_count = len(documents)
        
        for doc in documents:
            similarity = doc.get('similarity_score', 0.0)
            if similarity >= similarity_threshold:
                filtered_documents.append(doc)
        
        accepted_count = len(filtered_documents)
        filtered_count = original_count - accepted_count
        
        return {
            'filtered_documents': filtered_documents,
            'original_count': original_count,
            'filtered_count': filtered_count,
            'accepted_count': accepted_count,
            'threshold': similarity_threshold
        }
    
    def format_context(self, documents: List[Dict[str, Any]]) -> str:
        """格式化上下文信息，使用所有提供的文档"""
        if not documents:
            return ""
        
        context_parts = []
        
        for i, doc in enumerate(documents, 1):
            content = doc.get('content', '').strip()
            title = doc.get('title', '未知文档')
            similarity = doc.get('similarity_score', 0.0)
            
            context_parts.append(
                f"文档{i} (相似度: {similarity:.3f}):\n"
                f"标题: {title}\n"
                f"内容: {content}\n"
            )
        
        return "\n".join(context_parts)
    
    def build_prompt(self, context: str, question: str) -> str:
        """构建完整的prompt，根据上下文内容使用不同的提示词"""
        
        # 检查是否有有效的上下文内容
        has_valid_context = context and context.strip() and len(context.strip()) > 0
        print(f"DEBUG: build_prompt - 上下文长度: {len(context) if context else 0}, 有效上下文: {has_valid_context}")
        
        if has_valid_context:
            # 有相关文档时的提示词
            print("DEBUG: 使用RAG模式提示词（有相关文档）")
            system_prompt = """你是一个智能助手，基于提供的上下文信息来回答用户的问题。

请遵循以下原则：
1. 基于上下文信息准确回答问题，优先使用上下文中的信息
2. 如果需要，可以引用上下文中的具体内容
3. 用中文回答问题
4. 专门的学术英语可以直接用英文"""
            
            return f"{system_prompt}\n\n上下文信息：\n{context}\n\n问题：{question}"
        else:
            # 没有相关文档时的提示词
            print("DEBUG: 使用直接对话模式提示词（无相关文档）")
            system_prompt = """你是一个智能助手，请直接回答用户的问题。

请遵循以下原则：
1. 基于你的知识储备提供准确、有用的回答
2. 如果问题涉及特定领域或最新信息，请说明可能需要查阅相关资料
3. 保持回答的客观性和准确性
4. 用中文回答问题"""
            
            return f"{system_prompt}\n\n问题：{question}"
    
    def rag_chat_stream(self, query: str, top_k: int = 3, 
                       history: List[Dict[str, str]] = None, similarity_threshold: float = 0.0, **kwargs) -> Generator[str, None, None]:
        """
        RAG对话 - 流式响应，支持历史记录和相似度阈值过滤
        
        Args:
            query: 用户问题
            top_k: 检索文档数量
            history: 可选的历史消息列表，格式: [{"role": "user/assistant", "content": "..."}]
            similarity_threshold: 相似度阈值，低于此值的文档将被过滤
            **kwargs: 其他参数
            
        Yields:
            生成的回答片段
        """
        print(f"DEBUG: rag_chat_stream开始，query='{query}', top_k={top_k}, similarity_threshold={similarity_threshold}")
        
        # 1. 检索相关文档
        retrieve_start = time.time()
        documents = self.retrieve_documents(query, top_k)
        retrieve_time = time.time() - retrieve_start
        print(f"DEBUG: 文档检索耗时: {retrieve_time:.2f}秒，检索到{len(documents)}个文档")
        
        # 2. 根据相似度阈值过滤文档
        filter_start = time.time()
        filter_result = self.filter_documents_by_similarity(documents, similarity_threshold)
        filtered_documents = filter_result['filtered_documents']
        filter_time = time.time() - filter_start
        print(f"DEBUG: 文档过滤耗时: {filter_time:.3f}秒，过滤后剩余{len(filtered_documents)}个文档")
        
        # 3. 格式化上下文
        context_start = time.time()
        context = self.format_context(filtered_documents)
        context_time = time.time() - context_start
        print(f"DEBUG: 上下文格式化耗时: {context_time:.3f}秒")
        
        # 3. 构建prompt
        prompt_start = time.time()
        prompt = self.build_prompt(context, query)
        prompt_time = time.time() - prompt_start
        print(f"DEBUG: Prompt构建耗时: {prompt_time:.3f}秒，最终prompt长度: {len(prompt)}字符")
        
        # 4. 构建聊天消息格式，包含历史记录
        messages = []
        
        # 添加历史记录
        if history and len(history) > 0:
            messages.extend(history)
            print(f"DEBUG: 添加了{len(history)}条历史消息")
        
        # 添加当前带有RAG上下文的问题
        messages.append({"role": "user", "content": prompt})
        
        # 5. 流式生成回答
        print(f"DEBUG: 开始调用chat_model.stream_chat，消息数量: {len(messages)}")
        model_start = time.time()
        first_token_time = None
        
        try:
            for chunk in chat_model.stream_chat(messages, **kwargs):
                # 记录第一个token的时间
                if first_token_time is None and chunk.strip():
                    first_token_time = time.time()
                    first_token_delay = first_token_time - model_start
                    print(f"DEBUG: rag_chat第一个token延迟: {first_token_delay:.2f}秒")
                
                yield chunk
        except Exception as e:
            print(f"DEBUG: rag_chat生成回答时出错: {e}")
            yield f"生成回答时出错: {e}"
    
    def rag_chat_stream_with_info(self, query: str, top_k: int = 3, 
                                 history: List[Dict[str, str]] = None, similarity_threshold: float = 0.0, **kwargs) -> Generator[Dict[str, Any], None, None]:
        """
        RAG对话 - 流式响应，返回详细信息，支持相似度阈值过滤
        
        Args:
            query: 用户问题
            top_k: 检索文档数量
            history: 可选的历史消息列表
            similarity_threshold: 相似度阈值，低于此值的文档将被过滤
            **kwargs: 其他参数
            
        Yields:
            包含回答片段和元信息的字典
        """
        start_time = time.time()
        
        # 1. 检索相关文档
        retrieve_start = time.time()
        documents = self.retrieve_documents(query, top_k)
        retrieve_time = time.time() - retrieve_start
        print(f"DEBUG: 文档检索耗时: {retrieve_time:.2f}秒")
        
        # 2. 根据相似度阈值过滤文档
        filter_start = time.time()
        filter_result = self.filter_documents_by_similarity(documents, similarity_threshold)
        filtered_documents = filter_result['filtered_documents']
        filter_time = time.time() - filter_start
        print(f"DEBUG: 文档过滤耗时: {filter_time:.3f}秒，过滤前{filter_result['original_count']}个，过滤后{filter_result['accepted_count']}个")
        
        # 3. 格式化上下文
        context_start = time.time()
        context = self.format_context(filtered_documents)
        context_time = time.time() - context_start
        print(f"DEBUG: 上下文格式化耗时: {context_time:.3f}秒")
        
        # 3. 构建prompt
        prompt_start = time.time()
        prompt = self.build_prompt(context, query)
        prompt_time = time.time() - prompt_start
        print(f"DEBUG: Prompt构建耗时: {prompt_time:.3f}秒")
        
        # 4. 构建聊天消息格式，包含历史记录
        messages = []
        
        # 添加历史记录
        if history and len(history) > 0:
            messages.extend(history)
        
        # 添加当前带有RAG上下文的问题
        messages.append({"role": "user", "content": prompt})
        
        # 5. 流式生成回答
        full_response = ""
        chunk_count = 0
        
        print(f"DEBUG: RAG准备调用chat_model.stream_chat，当前模型: {chat_model.get_current_model()}")
        print(f"DEBUG: 消息数量: {len(messages)}, kwargs: {kwargs}")
        print(f"DEBUG: 最终prompt长度: {len(prompt)}字符")
        print(f"DEBUG: 上下文长度: {len(context)}字符")
        print(f"DEBUG: 检索到的文档数量: {len(documents)}")
        
        # 显示实际发送的消息内容（截取前200字符）
        for i, msg in enumerate(messages):
            content_preview = msg.get('content', '')[:200] + '...' if len(msg.get('content', '')) > 200 else msg.get('content', '')
            print(f"DEBUG: 消息{i+1} ({msg.get('role')}): {content_preview}")
        
        # 开始模型推理计时
        model_start = time.time()
        first_token_time = None
        
        try:
            for chunk in chat_model.stream_chat(messages, **kwargs):
                # 记录第一个token的时间
                if first_token_time is None and chunk.strip():
                    first_token_time = time.time()
                    first_token_delay = first_token_time - model_start
                    print(f"DEBUG: 第一个token延迟: {first_token_delay:.2f}秒")
                
                full_response += chunk
                chunk_count += 1
                
                # 返回内容片段
                yield {
                    "type": "content",
                    "content": chunk,
                    "done": False
                }
            
            # 计算首字响应时间（如果有记录的话）
            if first_token_time is not None:
                response_time = first_token_time - start_time  # 首字响应时间
            else:
                # 如果没有记录到首字时间，使用总时间作为备选
                end_time = time.time()
                response_time = end_time - start_time
            
            # 计算字符数和估算token数（中文按2个token计算，英文按1个token）
            char_count = len(full_response)
            estimated_tokens = sum(2 if '\u4e00' <= char <= '\u9fff' else 1 for char in full_response)
            
            # 返回最终信息，包含过滤统计
            yield {
                "type": "info",
                "content": "",
                "done": True,
                "response_time": response_time,
                "char_count": char_count,
                "estimated_tokens": estimated_tokens,
                "chunk_count": chunk_count,
                "retrieved_documents": filtered_documents,  # 返回过滤后的文档
                "context_length": len(context),
                "filter_stats": {
                    "similarity_threshold": similarity_threshold,
                    "original_count": filter_result['original_count'],
                    "filtered_count": filter_result['filtered_count'],
                    "accepted_count": filter_result['accepted_count']
                }
            }
            
        except Exception as e:
            yield {
                "type": "error",
                "content": f"生成回答时出错: {e}",
                "done": True
            }
    
    def simple_chat_stream(self, message: str, documents: List[Dict[str, Any]] = None, 
                          history: List[Dict[str, str]] = None, **kwargs) -> Generator[str, None, None]:
        """
        简单对话流式响应，支持文档上传和历史记录
        
        Args:
            message: 用户消息
            documents: 可选的文档列表，格式与检索到的文档相同
                     [{"title": "标题", "content": "内容", "similarity_score": 1.0}, ...]
            history: 可选的历史消息列表，格式: [{"role": "user/assistant", "content": "..."}]
            **kwargs: 其他参数
            
        Yields:
            生成的回答片段
        """
        try:
            # 构建消息列表
            messages = []
            
            # 添加历史记录
            if history and len(history) > 0:
                messages.extend(history)
            
            if documents and len(documents) > 0:
                # 如果有文档，使用文档信息构建上下文
                print(f"DEBUG: simple_chat使用文档模式，文档数量: {len(documents)}")
                context = self.format_context(documents)
                prompt = self.build_prompt(context, message)
                messages.append({"role": "user", "content": prompt})
            else:
                # 如果没有文档，直接添加用户消息
                print(f"DEBUG: simple_chat使用直接对话模式，documents={documents}")
                messages.append({"role": "user", "content": message})

            print(messages)

            for chunk in chat_model.stream_chat(messages, **kwargs):
                yield chunk
        except Exception as e:
            yield f"对话失败: {e}"



def create_rag_service(model_type: str = "llama3.1") -> RAGChatService:
    """创建RAG服务实例"""
    searcher = DocumentSearcher()
    return RAGChatService(searcher=searcher, model_type=model_type)

# 便捷函数
def rag_ask_stream(question: str, model_type: str = "llama3.1", top_k: int = 3):
    """
    便捷的RAG流式问答函数
    
    Args:
        question: 问题
        model_type: 模型类型
        top_k: 检索文档数量
    """
    service = create_rag_service(model_type)
    
    print(f"问题: {question}")
    print(f"回答: ", end="", flush=True)
    for chunk in service.rag_chat_stream(question, top_k):
        print(chunk, end="", flush=True)
    print()  # 换行

if __name__ == "__main__":
    # 测试代码
    print("RAG对话服务测试 - 简化版（仅流式响应）")
    
    # 测试问题
    test_questions = [
        "辰天是谁？",
        "龙血镇在哪里？",
        "什么是武者之魂？"
    ]
    
    # 使用便捷函数测试
    for question in test_questions:
        print(f"\n{'='*50}")
        rag_ask_stream(question, model_type="llama3.1", top_k=2)
        print("-" * 50)
