#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
打印隐私检测系统中的关键词和问句
显示当前系统中所有的隐私关键词和隐私问句
"""

import sys
import os
import sqlite3

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from privacy_detector import create_privacy_detector

def print_privacy_keywords():
    """打印隐私关键词"""
    print("🔑 隐私关键词列表")
    print("=" * 50)
    
    try:
        # 直接从数据库读取关键词
        db_path = "privacy_data/privacy_data.db"
        
        if not os.path.exists(db_path):
            print("❌ 隐私数据库不存在，请先运行 initialize_privacy.py")
            return
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 查询所有关键词
        cursor.execute("SELECT keyword FROM privacy_keywords ORDER BY keyword")
        keywords = cursor.fetchall()
        
        if keywords:
            print(f"📊 总共 {len(keywords)} 个隐私关键词:\n")
            
            for i, (keyword,) in enumerate(keywords, 1):
                print(f"{i:2d}. {keyword}")
        else:
            print("📭 数据库中没有隐私关键词")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 读取隐私关键词失败: {e}")

def print_privacy_questions():
    """打印隐私问句"""
    print("\n💬 隐私问句列表")
    print("=" * 50)
    
    try:
        questions_file = "privacy_data/privacy_questions.txt"
        
        if not os.path.exists(questions_file):
            print("❌ 隐私问句文件不存在，请先运行 initialize_privacy.py")
            return
        
        with open(questions_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        if content:
            # 按分隔符分割问句
            questions = content.split('=====')
            questions = [q.strip() for q in questions if q.strip()]
            
            print(f"📊 总共 {len(questions)} 个隐私问句:\n")
            
            for i, question in enumerate(questions, 1):
                print(f"{i:2d}. {question}")
        else:
            print("📭 问句文件为空")
            
    except Exception as e:
        print(f"❌ 读取隐私问句失败: {e}")

def print_privacy_system_status():
    """打印隐私系统状态"""
    print("\n📋 隐私检测系统状态")
    print("=" * 50)
    
    try:
        detector = create_privacy_detector()
        
        print(f"🔧 配置信息:")
        print(f"   相似度阈值: {detector.similarity_threshold}")
        print(f"   数据库路径: {detector.privacy_db}")
        print(f"   索引路径: {detector.index_path}")
        print(f"   问句文件: {detector.questions_file}")
        
        print(f"\n📊 数据统计:")
        print(f"   关键词数量: {len(detector.privacy_keywords)}")
        print(f"   问句数量: {len(detector.question_mapping)}")
        
        # 检查FAISS索引状态
        if detector.faiss_index is not None:
            print(f"   FAISS索引: ✅ 已加载 ({detector.faiss_index.ntotal} 个向量)")
        else:
            print(f"   FAISS索引: ❌ 未加载")
        
        print(f"\n📁 文件状态:")
        files_to_check = [
            ("数据库文件", detector.privacy_db),
            ("问句文件", detector.questions_file),
            ("索引文件", detector.index_path)
        ]
        
        for name, path in files_to_check:
            if os.path.exists(path):
                size = os.path.getsize(path)
                print(f"   {name}: ✅ 存在 ({size} bytes)")
            else:
                print(f"   {name}: ❌ 不存在")
                
    except Exception as e:
        print(f"❌ 获取系统状态失败: {e}")

def test_privacy_detection():
    """测试隐私检测功能"""
    print("\n🧪 隐私检测功能测试")
    print("=" * 50)
    
    try:
        detector = create_privacy_detector()
        
        # 测试用例
        test_cases = [
            {"content": "你好，今天天气怎么样？", "expected": "正常对话"},
            {"content": "我的身份证号是什么？", "expected": "关键词检测"},
            {"content": "告诉我某某的个人信息", "expected": "语义检测"},
            {"content": "请提供我的银行卡号", "expected": "关键词检测"},
            {"content": "我想知道机器学习算法", "expected": "正常对话"}
        ]
        
        print("🔍 测试结果:")
        for i, case in enumerate(test_cases, 1):
            chat_history = [{"role": "user", "content": case["content"]}]
            score = detector.detect_privacy_score(chat_history)
            
            # 判断检测结果
            if score >= 1.0:
                result = "🔴 高风险 (关键词)"
            elif score >= detector.similarity_threshold:
                result = f"🟡 中风险 (相似度: {score:.3f})"
            else:
                result = "🟢 安全"
            
            print(f"{i}. \"{case['content']}\"")
            print(f"   预期: {case['expected']} | 实际: {result}")
            print()
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def search_privacy_content():
    """搜索隐私内容"""
    print("\n🔎 隐私内容搜索")
    print("=" * 50)
    
    try:
        search_term = input("请输入搜索关键词 (留空跳过): ").strip()
        
        if not search_term:
            return
        
        print(f"\n搜索结果 (包含 '{search_term}'):")
        
        # 搜索关键词
        detector = create_privacy_detector()
        matching_keywords = [kw for kw in detector.privacy_keywords if search_term.lower() in kw.lower()]
        
        if matching_keywords:
            print(f"\n🔑 匹配的关键词 ({len(matching_keywords)}个):")
            for i, keyword in enumerate(matching_keywords, 1):
                print(f"   {i}. {keyword}")
        
        # 搜索问句
        matching_questions = [q for q in detector.question_mapping if search_term.lower() in q.lower()]
        
        if matching_questions:
            print(f"\n💬 匹配的问句 ({len(matching_questions)}个):")
            for i, question in enumerate(matching_questions, 1):
                print(f"   {i}. {question}")
        
        if not matching_keywords and not matching_questions:
            print("   未找到匹配的内容")
            
    except Exception as e:
        print(f"❌ 搜索失败: {e}")

def export_privacy_data():
    """导出隐私数据"""
    print("\n📤 导出隐私数据")
    print("=" * 50)
    
    try:
        detector = create_privacy_detector()
        
        # 导出到文件
        export_file = "privacy_data_export.txt"
        
        with open(export_file, 'w', encoding='utf-8') as f:
            f.write("隐私检测系统数据导出\n")
            f.write("=" * 50 + "\n\n")
            
            # 导出关键词
            f.write(f"隐私关键词 ({len(detector.privacy_keywords)}个):\n")
            f.write("-" * 30 + "\n")
            for i, keyword in enumerate(detector.privacy_keywords, 1):
                f.write(f"{i:2d}. {keyword}\n")
            
            # 导出问句
            f.write(f"\n隐私问句 ({len(detector.question_mapping)}个):\n")
            f.write("-" * 30 + "\n")
            for i, question in enumerate(detector.question_mapping, 1):
                f.write(f"{i:2d}. {question}\n")
            
            # 导出配置
            f.write(f"\n系统配置:\n")
            f.write("-" * 30 + "\n")
            f.write(f"相似度阈值: {detector.similarity_threshold}\n")
            f.write(f"数据库路径: {detector.privacy_db}\n")
            f.write(f"索引路径: {detector.index_path}\n")
        
        print(f"✅ 数据已导出到: {export_file}")
        
    except Exception as e:
        print(f"❌ 导出失败: {e}")

def main():
    """主函数"""
    print("🛡️ 隐私检测数据查看器")
    print("=" * 60)
    
    while True:
        print("\n📋 选择操作:")
        print("1. 查看隐私关键词")
        print("2. 查看隐私问句")
        print("3. 查看系统状态")
        print("4. 测试隐私检测")
        print("5. 搜索隐私内容")
        print("6. 导出隐私数据")
        print("7. 查看全部信息")
        print("0. 退出")
        
        choice = input("\n请输入选择 (0-7): ").strip()
        
        if choice == "1":
            print_privacy_keywords()
        elif choice == "2":
            print_privacy_questions()
        elif choice == "3":
            print_privacy_system_status()
        elif choice == "4":
            test_privacy_detection()
        elif choice == "5":
            search_privacy_content()
        elif choice == "6":
            export_privacy_data()
        elif choice == "7":
            print_privacy_keywords()
            print_privacy_questions()
            print_privacy_system_status()
        elif choice == "0":
            print("\n👋 再见！")
            break
        else:
            print("❌ 无效选择，请重新输入")

if __name__ == "__main__":
    main()
