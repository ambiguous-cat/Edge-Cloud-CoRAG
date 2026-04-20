#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
隐私检测模块
基于关键词匹配和语义相似度的双重检测机制
"""

import os
import sqlite3
import faiss
import numpy as np
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import embedding

load_dotenv()


def normalize_vectors(vectors: np.ndarray) -> np.ndarray:
    """向量归一化"""
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / (norms + 1e-10)


class PrivacyDetector:
    """隐私检测器"""

    def __init__(self,
                 questions_file: str = "privacy_data/privacy_questions.txt",
                 index_path: str = "privacy_data/privacy_questions.index",
                 privacy_db: str = "privacy_data/privacy_data.db",
                 similarity_threshold: float = 0.4):
        """
        初始化隐私检测器

        Args:
            questions_file: 隐私问句文件路径
            index_path: FAISS索引文件路径
            privacy_db: 隐私数据数据库路径（包含关键词和问句映射）
            similarity_threshold: 语义相似度阈值
        """
        self.questions_file = questions_file
        self.index_path = index_path
        self.privacy_db = privacy_db
        self.similarity_threshold = similarity_threshold

        # 创建数据目录
        os.makedirs("privacy_data", exist_ok=True)

        # 初始化数据库
        self._init_privacy_database()

        # 加载隐私关键词（从数据库）
        self.privacy_keywords = self._load_privacy_keywords_from_db()

        # 加载FAISS索引和映射
        self.faiss_index = None
        self.question_mapping = []
        self._load_privacy_index()

    def _init_privacy_database(self):
        """初始化隐私数据库"""
        try:
            conn = sqlite3.connect(self.privacy_db)
            cursor = conn.cursor()

            # 创建隐私关键词表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS privacy_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL UNIQUE
            )
            ''')

            # 创建隐私问句映射表
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS privacy_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL
            )
            ''')

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"初始化隐私数据库失败: {e}")

    def _load_privacy_keywords_from_db(self) -> List[str]:
        """从数据库加载隐私关键词列表"""
        try:
            conn = sqlite3.connect(self.privacy_db)
            cursor = conn.cursor()
            cursor.execute("SELECT keyword FROM privacy_keywords ORDER BY keyword")
            keywords = [row[0] for row in cursor.fetchall()]
            conn.close()

            if keywords:
                print(f"已从数据库加载 {len(keywords)} 个隐私关键词")
            else:
                print("数据库中没有隐私关键词，请添加关键词")

            return keywords
        except Exception as e:
            print(f"从数据库加载隐私关键词失败: {e}")
            return []

    def reload_keywords(self):
        """重新加载关键词（用于动态更新）"""
        self.privacy_keywords = self._load_privacy_keywords_from_db()
        return len(self.privacy_keywords)

    def _load_privacy_index(self):
        """加载隐私问句的FAISS索引和映射"""
        if not os.path.exists(self.index_path):
            print(f"隐私问句索引不存在: {self.index_path}")
            print("请先调用 build_privacy_index() 构建索引")
            return

        try:
            # 加载FAISS索引
            self.faiss_index = faiss.read_index(self.index_path)

            # 加载问句映射
            self.question_mapping = self._load_question_mapping()

            print(f"✅ 已加载隐私问句索引，包含 {len(self.question_mapping)} 个问句")
        except Exception as e:
            print(f"❌ 加载隐私问句索引失败: {e}")

    def _load_question_mapping(self) -> List[str]:
        """从数据库加载问句映射"""
        try:
            conn = sqlite3.connect(self.privacy_db)
            cursor = conn.cursor()
            cursor.execute("SELECT question FROM privacy_questions ORDER BY id")
            questions = [row[0] for row in cursor.fetchall()]
            conn.close()
            return questions
        except Exception as e:
            print(f"❌ 加载问句映射失败: {e}")
            return []

    def build_privacy_index(self):
        """构建隐私问句的向量索引"""
        if not os.path.exists(self.questions_file):
            print(f"隐私问句文件不存在: {self.questions_file}")
            print("请创建该文件并添加隐私问句，使用 '=====' 分隔")
            return False

        try:
            # 读取并分割隐私问句
            with open(self.questions_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            if not content:
                print("❌ 隐私问句文件为空")
                return False

            questions = [q.strip() for q in content.split('=====') if q.strip()]

            if not questions:
                print("❌ 未找到有效的隐私问句")
                return False

            print(f"开始处理 {len(questions)} 个隐私问句...")

            # 批量生成嵌入向量
            print("正在生成嵌入向量...")
            embeddings = embedding.get_embeddings(questions)
            embeddings = normalize_vectors(np.array(embeddings, dtype=np.float32))

            # 创建FAISS索引
            dimension = embeddings.shape[1]
            index = faiss.IndexFlatIP(dimension)  # 内积索引，配合归一化实现余弦相似度
            index.add(embeddings)

            # 保存FAISS索引
            faiss.write_index(index, self.index_path)

            # 保存问句映射到数据库
            self._save_question_mapping(questions)

            # 重新加载索引
            self._load_privacy_index()

            print(f"✅ 隐私问句索引构建完成，包含 {len(questions)} 个问句")
            return True

        except Exception as e:
            print(f"❌ 构建隐私问句索引失败: {e}")
            return False

    def _save_question_mapping(self, questions: List[str]):
        """保存问句映射到数据库"""
        conn = sqlite3.connect(self.privacy_db)
        cursor = conn.cursor()

        # 清空旧数据
        cursor.execute("DELETE FROM privacy_questions")

        # 插入新数据
        for question in questions:
            cursor.execute("INSERT INTO privacy_questions (question) VALUES (?)", (question,))

        conn.commit()
        conn.close()

    def _check_keywords(self, text: str) -> bool:
        """检查文本中是否包含隐私关键词"""
        if not self.privacy_keywords:
            return False

        text_lower = text.lower()
        for keyword in self.privacy_keywords:
            if keyword.lower() in text_lower:
                return True
        return False

    def _check_semantic_similarity(self, text: str) -> float:
        """检查文本与隐私问句的语义相似度"""
        if not self.faiss_index or not self.question_mapping:
            return 0.0

        try:
            # 生成查询向量
            query_embedding = embedding.get_embedding(text)
            query_vec = normalize_vectors(np.array([query_embedding], dtype=np.float32))

            # FAISS检索
            similarities, indices = self.faiss_index.search(query_vec, 1)  # 只需要最相似的一个

            if len(similarities[0]) > 0:
                max_similarity = float(similarities[0][0])
                return max_similarity

            return 0.0

        except Exception as e:
            print(f"❌ 语义相似度检测失败: {e}")
            return 0.0

    def detect_privacy_score(self, chat_history: List[Dict[str, str]]) -> float:
        """
        检测聊天历史中的隐私分值

        Args:
            chat_history: 聊天历史记录 [{"role": "user/assistant", "content": "..."}]

        Returns:
            float: 隐私分值 (0.0-1.0)，分值越高隐私程度越高
        """
        if not chat_history:
            return 0.0

        max_privacy_score = 0.0

        # 提取所有用户消息
        user_messages = [msg["content"] for msg in chat_history if msg.get("role") == "user"]

        if not user_messages:
            return 0.0

        # 检测每条用户消息
        for message in user_messages:
            if not message or not message.strip():
                continue

            # 1. 关键词检测（优先级最高）
            if self._check_keywords(message):
                return 1.0  # 发现关键词，直接返回最高分值

            # 2. 语义相似度检测
            similarity_score = self._check_semantic_similarity(message)
            max_privacy_score = max(max_privacy_score, similarity_score)

        return max_privacy_score

    def get_detection_info(self, chat_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        获取详细的检测信息（用于调试和分析）

        Args:
            chat_history: 聊天历史记录

        Returns:
            Dict: 包含详细检测信息的字典
        """
        if not chat_history:
            return {"privacy_score": 0.0, "detection_details": []}

        user_messages = [msg["content"] for msg in chat_history if msg.get("role") == "user"]
        detection_details = []
        max_privacy_score = 0.0

        for i, message in enumerate(user_messages):
            if not message or not message.strip():
                continue

            detail = {
                "message_index": i,
                "message": message[:100] + "..." if len(message) > 100 else message,
                "keyword_detected": False,
                "semantic_score": 0.0,
                "final_score": 0.0
            }

            # 关键词检测
            keyword_detected = self._check_keywords(message)
            detail["keyword_detected"] = keyword_detected

            if keyword_detected:
                detail["final_score"] = 1.0
                max_privacy_score = 1.0
            else:
                # 语义检测
                semantic_score = self._check_semantic_similarity(message)
                detail["semantic_score"] = semantic_score
                detail["final_score"] = semantic_score
                max_privacy_score = max(max_privacy_score, semantic_score)

            detection_details.append(detail)

        return {
            "privacy_score": max_privacy_score,
            "detection_details": detection_details,
            "total_user_messages": len(user_messages),
            "keywords_loaded": len(self.privacy_keywords),
            "questions_loaded": len(self.question_mapping)
        }

    # ==================== 关键词管理方法 ====================

    def add_keyword(self, keyword: str) -> bool:
        """
        添加隐私关键词

        Args:
            keyword: 关键词

        Returns:
            bool: 添加是否成功
        """
        try:
            conn = sqlite3.connect(self.privacy_db)
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO privacy_keywords (keyword) VALUES (?)",
                (keyword.strip(),)
            )

            conn.commit()
            conn.close()

            # 重新加载关键词
            self.reload_keywords()

            print(f"已添加隐私关键词: {keyword}")
            return True

        except sqlite3.IntegrityError:
            print(f"关键词已存在: {keyword}")
            return False
        except Exception as e:
            print(f"添加关键词失败: {e}")
            return False

    def remove_keyword(self, keyword: str) -> bool:
        """
        删除隐私关键词

        Args:
            keyword: 要删除的关键词

        Returns:
            bool: 删除是否成功
        """
        try:
            conn = sqlite3.connect(self.privacy_db)
            cursor = conn.cursor()

            cursor.execute("DELETE FROM privacy_keywords WHERE keyword = ?", (keyword,))
            deleted_count = cursor.rowcount

            conn.commit()
            conn.close()

            if deleted_count > 0:
                # 重新加载关键词
                self.reload_keywords()
                print(f"已删除隐私关键词: {keyword}")
                return True
            else:
                print(f"关键词不存在: {keyword}")
                return False

        except Exception as e:
            print(f"删除关键词失败: {e}")
            return False

    def get_keywords(self) -> List[Dict[str, Any]]:
        """
        查询隐私关键词

        Returns:
            List[Dict]: 关键词列表，包含ID和关键词
        """
        try:
            conn = sqlite3.connect(self.privacy_db)
            cursor = conn.cursor()

            cursor.execute("SELECT id, keyword FROM privacy_keywords ORDER BY keyword")

            keywords = []
            for row in cursor.fetchall():
                keywords.append({
                    "id": row[0],
                    "keyword": row[1]
                })

            conn.close()
            return keywords

        except Exception as e:
            print(f"查询关键词失败: {e}")
            return []


# 便捷函数
def create_privacy_detector(**kwargs) -> PrivacyDetector:
    """创建隐私检测器实例"""
    return PrivacyDetector(**kwargs)


def quick_privacy_check(chat_history: List[Dict[str, str]], threshold: float = 0.4) -> bool:
    """
    快速隐私检查

    Args:
        chat_history: 聊天历史
        threshold: 隐私分值阈值

    Returns:
        bool: True表示检测到隐私问题
    """
    detector = create_privacy_detector(similarity_threshold=threshold)
    score = detector.detect_privacy_score(chat_history)
    return score >= threshold

