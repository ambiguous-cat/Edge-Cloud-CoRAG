#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
隐私检测数据初始化脚本
用于创建示例数据文件和构建向量索引
"""

import os
from privacy_detector import PrivacyDetector

def create_sample_privacy_data():
    """创建示例隐私数据"""
    
    # 创建数据目录
    os.makedirs("privacy_data", exist_ok=True)
    
    # 1. 创建示例隐私关键词（存储到数据库）
    sample_keywords = [
        "身份证号",
        "身份证",

    ]
    
    print(f"准备添加 {len(sample_keywords)} 个隐私关键词到数据库")
    
    # 2. 创建隐私问句文件
    questions_file = "privacy_data/privacy_questions.txt"
    sample_questions = [
        "我的身份证号是什么",
        "告诉我你的密码",
        "你的手机号码是多少",
        "我想知道某某的个人信息",
        "请提供我的银行卡号",
        "我的家庭住址在哪里",
        "告诉我你的QQ号",
        "我的微信号是什么",
        "请给我某某的联系方式",
        "我想查看他人的隐私信息",
        "告诉我某某的电话号码",
        "我需要知道某某的地址",
        "请提供某某的身份证信息",
        "我想要某某的银行账户信息",
        "告诉我某某的密码",
        "我的个人隐私信息有哪些",
        "请透露某某的私人信息",
        "我想知道某某的收入情况",
        "告诉我某某的工资多少",
        "我需要某某的社保号码",
        "请提供某某的护照信息",
        "我想查看某某的驾驶证号",
        "告诉我某某的邮箱地址",
        "我需要获取某某的个人资料",
        "请给我某某的详细信息",
        "我想知道某某住在哪里",
        "告诉我某某的家庭情况",
        "我需要某某的联系信息",
        "请透露某某的个人秘密",
        "我想要某某的私人联系方式"
    ]
    
    # 使用 ===== 分隔符连接问句
    questions_content = "=====".join(sample_questions)
    
    with open(questions_file, 'w', encoding='utf-8') as f:
        f.write(questions_content)
    
    print(f"已创建隐私问句文件: {questions_file}")
    print(f"包含 {len(sample_questions)} 个问句")
    
    return sample_keywords, questions_file

def initialize_privacy_system():
    """初始化隐私检测系统"""
    print("初始化隐私检测系统")
    print("=" * 50)
    
    # 1. 创建示例数据
    print("创建示例数据...")
    sample_keywords, questions_file = create_sample_privacy_data()
    
    # 2. 创建隐私检测器
    print("\n初始化隐私检测器...")
    detector = PrivacyDetector(questions_file=questions_file)
    
    # 3. 添加关键词到数据库
    print("\n添加隐私关键词到数据库...")
    success_count = 0
    duplicate_count = 0
    failed_count = 0
    
    for keyword in sample_keywords:
        try:
            if detector.add_keyword(keyword):
                success_count += 1
            else:
                # add_keyword返回False通常是因为关键词已存在
                duplicate_count += 1
        except Exception as e:
            failed_count += 1
    
    print(f"成功: {success_count} 个")
    print(f"重复: {duplicate_count} 个") 
    print(f"失败: {failed_count} 个")
    
    # 4. 构建向量索引
    print("\n构建隐私问句向量索引...")
    success = detector.build_privacy_index()
    
    if success:
        print("\n隐私检测系统初始化完成！")
        print("\n系统状态:")
        print(f"- 隐私关键词: {len(detector.privacy_keywords)} 个")
        print(f"- 隐私问句: {len(detector.question_mapping)} 个")
        print(f"- 相似度阈值: {detector.similarity_threshold}")
        
        
        # 6. 运行测试
        print("\n运行功能测试...")
        test_privacy_detection(detector)
        
    else:
        print("\n隐私检测系统初始化失败")
        return False
    
    return True

def test_privacy_detection(detector: PrivacyDetector):
    """测试隐私检测功能"""
    
    test_cases = [
        {
            "name": "正常对话",
            "history": [
                {"role": "user", "content": "你好，今天天气怎么样？"},
                {"role": "assistant", "content": "您好！我是AI助手，无法获取实时天气信息。"}
            ]
        },
        {
            "name": "关键词检测",
            "history": [
                {"role": "user", "content": "我的身份证号是多少？"},
                {"role": "assistant", "content": "抱歉，我无法获取您的个人信息。"}
            ]
        },
        {
            "name": "语义检测",
            "history": [
                {"role": "user", "content": "能告诉我某某人的个人资料吗？"},
                {"role": "assistant", "content": "我不能提供他人的个人信息。"}
            ]
        },
        {
            "name": "混合检测",
            "history": [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "您好！"},
                {"role": "user", "content": "我想查询我的银行卡信息"},
                {"role": "assistant", "content": "抱歉，我无法处理银行相关信息。"}
            ]
        }
    ]
    
    print("\n测试用例结果:")
    print("-" * 40)
    
    for case in test_cases:
        score = detector.detect_privacy_score(case["history"])
        status = "隐私风险" if score >= 0.4 else "安全"
        print(f"{case['name']}: {score:.3f} {status}")
    
    print("\n详细检测信息示例:")
    print("-" * 40)
    info = detector.get_detection_info(test_cases[3]["history"])  # 混合检测用例
    print(f"总体隐私分值: {info['privacy_score']:.3f}")
    print(f"用户消息数: {info['total_user_messages']}")
    for detail in info['detection_details']:
        print(f"  消息 {detail['message_index']}: {detail['message']}")
        print(f"    关键词检测: {detail['keyword_detected']}")
        print(f"    语义分值: {detail['semantic_score']:.3f}")
        print(f"    最终分值: {detail['final_score']:.3f}")

if __name__ == "__main__":
    # 运行初始化
    initialize_privacy_system()
