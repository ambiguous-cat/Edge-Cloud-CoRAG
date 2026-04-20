"""
复杂度分析器 - 用于分析查询的复杂度并辅助路由决策
"""

import re
import jieba
import numpy as np
from typing import Dict, List, Tuple
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime
import json
import os
from logging import getLogger
from dotenv import load_dotenv

load_dotenv()  # 加载.env文件

logger = getLogger(__name__)

class ComplexityAnalyzer:
    """查询复杂度分析器"""

    def __init__(self, embedding_model=None):
        self.embedding_model = embedding_model

        # 从环境变量读取复杂度权重配置，如果未设置则使用默认值
        self.complexity_weights = self._load_complexity_weights()

        # 技术关键词列表
        self.tech_keywords = self._load_tech_keywords()

        # 学术词汇
        self.academic_keywords = self._load_academic_keywords()

        # 抽象概念词
        self.abstract_keywords = self._load_abstract_keywords()

        # 专业领域术语
        self.domain_terms = self._load_domain_terms()

        # 推理模式关键词
        self.reasoning_patterns = self._load_reasoning_patterns()

        # 历史数据（用于自适应学习）
        self.query_history = []
        self.performance_feedback = []

        logger.info("复杂度分析器初始化完成")
        logger.info(f"复杂度权重配置: {self.complexity_weights}")

    def _load_complexity_weights(self) -> Dict[str, float]:
        """
        从环境变量加载复杂度权重配置
        
        环境变量格式：
        COMPLEXITY_WEIGHT_QUERY_LENGTH=0.15
        COMPLEXITY_WEIGHT_KEYWORD_RICHNESS=0.20
        COMPLEXITY_WEIGHT_SEMANTIC_DEPTH=0.25
        COMPLEXITY_WEIGHT_DOMAIN_SPECIFICITY=0.20
        COMPLEXITY_WEIGHT_REASONING_REQUIREMENTS=0.15
        
        Returns:
            Dict[str, float]: 权重配置字典
        """
        # 默认权重配置（5维：推理关键词已合并到关键词丰富度，语法复杂度为独立维度）
        default_weights = {
            'query_length': 0.15,      # 查询长度和结构
            'keyword_richness': 0.25,  # 关键词丰富度（包含推理/分析关键词）
            'semantic_depth': 0.25,    # 语义深度
            'domain_specificity': 0.20, # 领域特定性
            'reasoning_requirements': 0.15  # 语法复杂度（独立维度）
        }
        
        # 从环境变量读取权重
        weights = {}
        weight_mapping = {
            'COMPLEXITY_WEIGHT_QUERY_LENGTH': 'query_length',
            'COMPLEXITY_WEIGHT_KEYWORD_RICHNESS': 'keyword_richness',
            'COMPLEXITY_WEIGHT_SEMANTIC_DEPTH': 'semantic_depth',
            'COMPLEXITY_WEIGHT_DOMAIN_SPECIFICITY': 'domain_specificity',
            'COMPLEXITY_WEIGHT_REASONING_REQUIREMENTS': 'reasoning_requirements'
        }
        
        for env_key, weight_key in weight_mapping.items():
            env_value = os.getenv(env_key)
            if env_value:
                try:
                    weight_value = float(env_value)
                    if 0.0 <= weight_value <= 1.0:
                        weights[weight_key] = weight_value
                    else:
                        logger.warning(f"权重 {env_key}={env_value} 超出范围 [0,1]，使用默认值 {default_weights[weight_key]}")
                        weights[weight_key] = default_weights[weight_key]
                except ValueError:
                    logger.warning(f"权重 {env_key}={env_value} 无法转换为浮点数，使用默认值 {default_weights[weight_key]}")
                    weights[weight_key] = default_weights[weight_key]
            else:
                weights[weight_key] = default_weights[weight_key]
        
        # 归一化权重，确保总和为1.0
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
            logger.info(f"权重已归一化，总和: {sum(weights.values()):.3f}")
        else:
            logger.warning("所有权重为0，使用默认权重")
            weights = default_weights
        
        return weights

    def _load_tech_keywords(self) -> List[str]:
        """加载技术关键词"""
        return [
            # 编程和开发
            '算法', '数据结构', '编程', '代码', '函数', '类', '对象', '接口', 'API',
            'Python', 'Java', 'JavaScript', 'C++', 'SQL', 'NoSQL', '数据库', '前端', '后端',
            '框架', '库', '工具', '开发环境', 'IDE', 'Git', '版本控制', '测试', '调试',

            # AI和机器学习
            '人工智能', '机器学习', '深度学习', '神经网络', 'CNN', 'RNN', 'LSTM', 'Transformer',
            '模型', '训练', '推理', '预测', '分类', '回归', '聚类', '降维', '特征工程',
            '监督学习', '无监督学习', '强化学习', 'NLP', '计算机视觉', 'CV', 'GPT', 'BERT',

            # 数据科学
            '数据分析', '数据挖掘', '大数据', '统计学', '概率论', '线性代数', '微积分',
            '可视化', '图表', 'Pandas', 'NumPy', 'Matplotlib', 'TensorFlow', 'PyTorch',

            # 系统和架构
            '云计算', '分布式', '微服务', '容器', 'Docker', 'Kubernetes', '负载均衡',
            '缓存', '消息队列', 'API网关', 'DevOps', 'CI/CD', '监控', '日志', '安全'
        ]

    def _load_academic_keywords(self) -> List[str]:
        """加载学术词汇"""
        return [
            # 研究方法论
            '研究', '分析', '比较', '评估', '实验', '方法', '理论', '假设', '验证',
            '结论', '文献', '综述', '方法论', '实证', '案例研究', '问卷调查', '访谈',

            # 统计和分析
            '统计', '相关性', '显著性', '置信区间', 'p值', '假设检验', '方差分析',
            '回归分析', '因子分析', '聚类分析', '时间序列', '预测模型',

            # 学术写作
            '摘要', '引言', '相关工作', '实验设计', '结果', '讨论', '局限性', '未来工作',
            '参考文献', '引用', '期刊', '会议', '论文', '学术', '学科', '跨学科'
        ]

    def _load_abstract_keywords(self) -> List[str]:
        """加载抽象概念词"""
        return [
            # 影响和关系
            '影响', '关系', '相互作用', '依赖', '关联', '联系', '纽带', '连接',

            # 机制和原理
            '机制', '原理', '规律', '本质', '核心', '关键', '要素', '组成部分',

            # 策略和方案
            '策略', '方案', '框架', '体系', '结构', '模式', '范式', '模型',

            # 趋势和变化
            '趋势', '发展', '变化', '演变', '进步', '创新', '改革', '转型',

            # 价值和意义
            '价值', '意义', '重要性', '作用', '功能', '效益', '优势', '劣势',

            # 挑战和机遇
            '挑战', '机遇', '问题', '困难', '障碍', '风险', '威胁', '潜力'
        ]

    def _load_domain_terms(self) -> Dict[str, List[str]]:
        """加载专业领域术语"""
        return {
            '计算机科学': [
                '算法', '数据结构', '计算复杂度', '分布式系统', '机器学习', '深度学习',
                '神经网络', '操作系统', '计算机网络', '数据库系统', '软件工程', '编译器',
                '人工智能', '计算机视觉', '自然语言处理', '密码学', '信息安全', '云计算',
                '物联网', '区块链', '量子计算', '图论', '优化理论' , 'RAG'
            ],

            '数学统计': [
                '概率分布', '假设检验', '回归分析', '贝叶斯', '矩阵运算', '线性代数',
                '微积分', '实变函数', '复变函数', '概率论', '数理统计', '随机过程',
                '时间序列', '多元统计', '非参数统计', '贝叶斯统计', '马尔可夫链',
                '蒙特卡洛', '优化理论', '数值分析', '微分方程', '积分变换'
            ],

            '生物学': [
                '基因', '蛋白质', '细胞', '进化', '生态系统', '分子生物学', '遗传学',
                '生物化学', '细胞生物学', '发育生物学', '神经生物学', '免疫学',
                '微生物学', '植物学', '动物学', '生态学', '生物信息学', '合成生物学',
                'CRISPR', 'PCR', 'DNA', 'RNA', 'ATP', '酶', '代谢', '光合作用'
            ],

            '经济学': [
                '供需关系', '市场均衡', '效用函数', '博弈论', '货币政策', '投资组合',
                '宏观经济学', '微观经济学', '国际贸易', '金融市场', '风险管理',
                '期权定价', '资本资产定价模型', '有效市场假说', '行为经济学', '实验经济学',
                'GDP', 'CPI', '通货膨胀', '失业率', '利率', '汇率', '财政政策'
            ],

            '物理学': [
                '量子力学', '相对论', '热力学', '电磁学', '粒子物理', '凝聚态物理',
                '光学', '声学', '力学', '流体力学', '统计物理', '核物理', '天体物理',
                '弦理论', '标准模型', '薛定谔方程', '海森堡不确定性原理', '波粒二象性',
                '熵', '焓', '自由能', '相变', '超导', '超流', '激光', '等离子体'
            ],

            '化学': [
                '有机化学', '无机化学', '物理化学', '分析化学', '生物化学', '高分子化学',
                '化学键', '分子轨道', '化学反应', '化学平衡', '酸碱理论', '氧化还原',
                '电化学', '催化', '光谱学', '色谱', '质谱', '核磁共振', 'X射线衍射',
                '化学合成', '聚合物', '纳米材料', '催化剂', '溶剂', '晶体结构'
            ],

            '医学': [
                '解剖学', '生理学', '病理学', '药理学', '免疫学', '神经科学', '心血管',
                '呼吸系统', '消化系统', '内分泌', '肿瘤学', '传染病', '遗传病',
                '临床试验', '诊断', '治疗', '预防', '康复', '流行病学', '公共卫生',
                '循证医学', '精准医疗', '基因治疗', '免疫治疗', '靶向治疗'
            ]
        }

    def _load_reasoning_patterns(self) -> Dict[str, List[str]]:
        """加载推理模式关键词"""
        return {
            '比较分析': [
                '比较', '对比', '区别', '差异', '相同点', '相似性', '优缺点', '优劣',
                '异同', '对照', '权衡', '取舍', '评价', '排名', '排序'
            ],

            '因果关系': [
                '原因', '导致', '影响', '结果', '因为', '所以', '由于', '因此',
                '从而', '以致', '造成', '引起', '产生', '触发', '诱发', '因素'
            ],

            '步骤流程': [
                '步骤', '流程', '过程', '如何', '方法', '操作', '程序', '顺序',
                '阶段', '环节', '路径', '方式', '手段', '技巧', '策略', '方案'
            ],

            '评估判断': [
                '评估', '评价', '判断', '建议', '推荐', '选择', '决策', '决定',
                '看法', '观点', '态度', '立场', '价值', '重要性', '必要性', '可行性'
            ],

            '预测推断': [
                '预测', '推断', '可能', '趋势', '未来', '发展', '前景', '展望',
                '预期', '估计', '推测', '假设', '设想', '规划', '计划', '预期结果'
            ],

            '抽象概括': [
                '本质', '核心', '关键', '主要', '总体', '概括', '总结', '归纳',
                '提炼', '抽象', '普适', '一般', '特殊', '个别', '普遍', '典型'
            ],

            '问题解决': [
                '问题', '困难', '挑战', '障碍', '解决方案', '对策', '措施', '办法',
                '技巧', '窍门', '经验', '教训', '改进', '优化', '提升', '完善'
            ]
        }

    def analyze_complexity(self, query: str) -> Dict[str, float]:
        """
        分析查询复杂度

        Args:
            query: 用户查询

        Returns:
            包含各维度复杂度评分和总评分的字典
        """
        try:
            # 预处理查询
            processed_query = self._preprocess_query(query)

            # 各维度复杂度分析（5维：推理关键词已合并到关键词丰富度，语法复杂度为独立维度）
            scores = {}
            scores['query_length'] = self._analyze_length_complexity(processed_query)
            scores['keyword_richness'] = self._analyze_keyword_complexity(processed_query)  # 包含推理关键词
            scores['semantic_depth'] = self._analyze_semantic_depth(processed_query)
            scores['domain_specificity'] = self._analyze_domain_complexity(processed_query)
            scores['reasoning_requirements'] = self._analyze_grammatical_complexity(processed_query)  # 语法复杂度（独立维度）

            # 计算总复杂度评分（5个维度）
            final_score = sum(
                score * self.complexity_weights[dim]
                for dim, score in scores.items()
            )

            result = {
                **scores,
                'total_complexity': min(1.0, final_score)
            }

            logger.info(f"复杂度分析完成: {query[:30]}... -> 总评分: {final_score:.3f}")
            return result

        except Exception as e:
            logger.error(f"复杂度分析失败: {e}")
            # 返回默认中等复杂度
            return {
                'query_length': 0.5,
                'keyword_richness': 0.5,
                'semantic_depth': 0.5,
                'domain_specificity': 0.5,
                'reasoning_requirements': 0.5,  # 向后兼容字段，实际值与keyword_richness相同
                'total_complexity': 0.5
            }

    def _preprocess_query(self, query: str) -> str:
        """预处理查询文本"""
        # 去除多余空格和特殊字符
        query = re.sub(r'\s+', ' ', query.strip())
        return query

    def _analyze_length_complexity(self, query: str) -> float:
        """分析查询长度和结构复杂度"""
        try:
            # 基础统计
            char_count = len(query)
            word_count = len(jieba.lcut(query))

            # 句子统计
            sentences = re.split(r'[。！？.!?]+', query)
            sentence_count = len([s for s in sentences if s.strip()])

            # 长度评分 (基于词数)
            if word_count <= 5:
                length_score = 0.1  # 非常简单
            elif word_count <= 10:
                length_score = 0.3  # 简单
            elif word_count <= 20:
                length_score = 0.6  # 中等
            elif word_count <= 40:
                length_score = 0.8  # 较长
            else:
                length_score = 1.0  # 很长

            # 结构复杂度评分
            # 复杂标点符号
            complex_punct = query.count('，') + query.count('：') + query.count('；') + query.count('）') + query.count('（')
            structure_score = min(1.0, complex_punct / 6)

            # 语法复杂度（从句、连接词等）
            conjunction_words = ['而且', '并且', '或者', '但是', '然而', '因此', '所以', '虽然', '尽管', '如果', '只要', '除非']
            conjunction_count = sum(1 for word in conjunction_words if word in query)
            grammar_score = min(1.0, conjunction_count / 4)

            # 问答模式复杂度
            question_words = ['什么', '如何', '为什么', '哪里', '哪个', '谁', '何时', '怎样', '多少']
            question_count = sum(1 for word in question_words if word in query)
            question_score = min(1.0, question_count / 3)

            # 综合评分
            final_score = (
                length_score * 0.4 +
                structure_score * 0.2 +
                grammar_score * 0.2 +
                question_score * 0.2
            )

            return min(1.0, final_score)

        except Exception as e:
            logger.warning(f"长度复杂度分析失败: {e}")
            return 0.5

    def _analyze_keyword_complexity(self, query: str) -> float:
        """分析关键词丰富度和技术性（包含推理/分析关键词）"""
        try:
            words = jieba.lcut(query.lower())
            query_lower = query.lower()

            # 统计各类关键词数量
            tech_count = sum(1 for word in words if any(tech in word for tech in self.tech_keywords))
            academic_count = sum(1 for word in words if any(academic in word for academic in self.academic_keywords))
            abstract_count = sum(1 for word in words if any(abstract in word for abstract in self.abstract_keywords))
            
            # 统计推理/分析关键词（从原推理需求检测中简化而来）
            reasoning_keywords = self._get_reasoning_keywords()
            reasoning_count = sum(1 for word in words if any(reasoning in word for reasoning in reasoning_keywords))

            # 计算关键词密度
            total_words = len(words)
            if total_words == 0:
                return 0.1

            keyword_density = (tech_count + academic_count + abstract_count + reasoning_count) / total_words
            density_score = min(1.0, keyword_density * 3)  # 调整权重

            # 多样性评分（不同类型关键词的分布）
            diversity_score = 0
            if tech_count > 0: diversity_score += 0.3
            if academic_count > 0: diversity_score += 0.25
            if abstract_count > 0: diversity_score += 0.25
            if reasoning_count > 0: diversity_score += 0.2  # 推理关键词也计入多样性

            # 技术深度评分（技术词汇的数量和稀有性）
            tech_depth = min(1.0, tech_count / 5)

            # 专业程度评分（包含推理/分析类动词）
            professional_words = ['研究', '分析', '设计', '实现', '优化', '评估', '测试', '验证',
                                '比较', '对比', '判断', '决策', '预测', '推断', '评估', '评价']
            professional_count = sum(1 for word in words if word in professional_words)
            professional_score = min(1.0, professional_count / 4)  # 调整阈值

            # 推理关键词强度（新增）
            reasoning_intensity = min(1.0, reasoning_count / 5) if total_words > 0 else 0

            # 综合评分
            final_score = (
                density_score * 0.3 +
                diversity_score * 0.25 +
                tech_depth * 0.2 +
                professional_score * 0.15 +
                reasoning_intensity * 0.1  # 推理关键词强度
            )

            return min(1.0, final_score)

        except Exception as e:
            logger.warning(f"关键词复杂度分析失败: {e}")
            return 0.5

    def _get_reasoning_keywords(self) -> List[str]:
        """获取推理/分析关键词列表（从原推理需求检测中简化）"""
        # 合并所有推理模式的关键词，去重
        reasoning_keywords = set()
        
        # 从推理模式中提取关键词
        if hasattr(self, 'reasoning_patterns'):
            for pattern_keywords in self.reasoning_patterns.values():
                reasoning_keywords.update(pattern_keywords)
        
        # 如果没有推理模式，使用简化版关键词列表
        if not reasoning_keywords:
            reasoning_keywords = {
                # 比较分析
                '比较', '对比', '区别', '差异', '相同点', '相似性', '优缺点', '优劣',
                '异同', '对照', '权衡', '取舍', '评价', '排名', '排序',
                # 因果关系
                '原因', '导致', '影响', '结果', '因为', '所以', '由于', '因此',
                '从而', '以致', '造成', '引起', '产生', '触发', '诱发', '因素',
                # 步骤流程
                '步骤', '流程', '过程', '如何', '方法', '操作', '程序', '顺序',
                '阶段', '环节', '路径', '方式', '手段', '技巧', '策略', '方案',
                # 评估判断
                '评估', '评价', '判断', '建议', '推荐', '选择', '决策', '决定',
                '看法', '观点', '态度', '立场', '价值', '重要性', '必要性', '可行性',
                # 预测推断
                '预测', '推断', '可能', '趋势', '未来', '发展', '前景', '展望',
                '预期', '估计', '推测', '假设', '设想', '规划', '计划', '预期结果',
                # 抽象概括
                '本质', '核心', '关键', '主要', '总体', '概括', '总结', '归纳',
                '提炼', '抽象', '普适', '一般', '特殊', '个别', '普遍', '典型',
                # 问题解决
                '问题', '困难', '挑战', '障碍', '解决方案', '对策', '措施', '办法',
                '技巧', '窍门', '经验', '教训', '改进', '优化', '提升', '完善'
            }
        
        return list(reasoning_keywords)

    def _analyze_semantic_depth(self, query: str) -> float:
        """分析语义深度和抽象程度"""
        try:
            if self.embedding_model is None:
                logger.warning("嵌入模型不可用，语义深度分析返回默认值0.5")
                return 0.5

            # 获取查询的嵌入向量
            embedding = self.embedding_model.embed_query(query)
            embedding = np.array(embedding).reshape(1, -1)

            # 计算向量的统计特征
            vector_variance = np.var(embedding)
            vector_mean = np.mean(np.abs(embedding))

            # 计算信息熵
            normalized_embedding = embedding / (np.sum(embedding) + 1e-8)
            entropy_score = -np.sum(normalized_embedding * np.log(normalized_embedding + 1e-8))

            # 与简单查询的对比分析
            simple_queries = [
                "你好", "谢谢", "再见", "是的", "不是",
                "什么是", "如何", "为什么", "在哪里", "什么时候"
            ]

            similarities = []
            for simple_q in simple_queries:
                try:
                    simple_embedding = self.embedding_model.embed_query(simple_q)
                    simple_embedding = np.array(simple_embedding).reshape(1, -1)
                    similarity = cosine_similarity(embedding, simple_embedding)[0][0]
                    similarities.append(similarity)
                except:
                    continue

            if similarities:
                avg_similarity = np.mean(similarities)
                complexity_from_similarity = 1 - avg_similarity
            else:
                complexity_from_similarity = 0.5

            # 综合评分
            semantic_complexity = (
                min(1.0, vector_variance * 10) * 0.2 +      # 向量方差 (20%)
                min(1.0, vector_mean) * 0.2 +               # 向量均值 (20%)
                min(1.0, entropy_score / 5) * 0.3 +         # 信息熵 (30%)
                complexity_from_similarity * 0.3            # 与简单查询的差异 (30%)
            )

            return min(1.0, semantic_complexity)

        except Exception as e:
            logger.warning(f"语义深度分析失败: {e}")
            return 0.5

    def _calculate_abstract_ratio(self, query: str) -> float:
        """计算抽象词汇比例"""
        try:
            words = jieba.lcut(query)
            if len(words) == 0:
                return 0.0

            abstract_count = 0
            for word in words:
                if any(abstract in word for abstract in self.abstract_keywords):
                    abstract_count += 1

            return min(1.0, abstract_count / len(words) * 3)  # 调整权重

        except Exception:
            return 0.0

    def _analyze_domain_complexity(self, query: str) -> float:
        """分析专业领域特定性和跨领域复杂性"""
        try:
            words = jieba.lcut(query.lower())

            domain_scores = {}
            total_domain_terms = 0
            involved_domains = 0

            # 计算每个领域的涉及程度
            for domain, terms in self.domain_terms.items():
                domain_count = 0
                for term in terms:
                    # 支持部分匹配（如"机器学习"匹配"学习"）
                    if any(term in word or word in term for word in words):
                        domain_count += 1

                domain_scores[domain] = domain_count
                total_domain_terms += domain_count

                if domain_count > 0:
                    involved_domains += 1

            # 跨领域复杂度（涉及多个专业领域）
            cross_domain_score = 0
            if involved_domains >= 4:
                cross_domain_score = 1.0
            elif involved_domains >= 3:
                cross_domain_score = 0.8
            elif involved_domains >= 2:
                cross_domain_score = 0.6
            elif involved_domains >= 1:
                cross_domain_score = 0.4
            else:
                cross_domain_score = 0.1

            # 专业术语密度
            total_words = len(words)
            if total_words == 0:
                return 0.1

            term_density = total_domain_terms / total_words
            density_score = min(1.0, term_density * 5)  # 调整权重

            # 领域深度（单个领域的术语数量）
            max_domain_score = max(domain_scores.values()) if domain_scores.values() else 0
            depth_score = min(1.0, max_domain_score / 8)

            # 专业程度评估（基于特定的高难度术语）
            high_difficulty_terms = [
                '量子纠缠', '相对论', '基因编辑', '区块链', '深度学习', '神经网络',
                '贝叶斯推理', '蒙特卡洛', '傅里叶变换', '拉格朗日', '哈密顿',
                '黎曼几何', '拓扑学', '泛函分析', '偏微分方程', '最优化理论'
            ]

            high_diff_count = sum(1 for term in high_difficulty_terms if term in query)
            difficulty_score = min(1.0, high_diff_count / 3)

            # 综合评分
            final_score = (
                cross_domain_score * 0.4 +   # 跨领域程度
                density_score * 0.25 +        # 术语密度
                depth_score * 0.2 +          # 领域深度
                difficulty_score * 0.15      # 难度级别
            )

            return min(1.0, final_score)

        except Exception as e:
            logger.warning(f"领域复杂度分析失败: {e}")
            return 0.5

    def _analyze_grammatical_complexity(self, query: str) -> float:
        """分析语法复杂度"""
        try:
            words = jieba.lcut(query)
            total_words = len(words)
            if total_words == 0:
                return 0.1

            # 1. 句子结构复杂度（权重 30%）
            structure_score = self._analyze_sentence_structure(query, words)
            
            # 2. 语法标记词密度（权重 25%）
            marker_density_score = self._analyze_grammatical_markers(query, words, total_words)
            
            # 3. 句式类型多样性（权重 20%）
            sentence_type_score = self._analyze_sentence_type_diversity(query)
            
            # 4. 语法规范性（权重 15%）
            normativity_score = self._analyze_grammatical_normativity(query, words)
            
            # 5. 修饰成分复杂度（权重 10%）
            modifier_score = self._analyze_modifier_complexity(query, words)

            # 综合评分
            final_score = (
                structure_score * 0.30 +      # 句子结构复杂度
                marker_density_score * 0.25 +  # 语法标记词密度
                sentence_type_score * 0.20 +   # 句式类型多样性
                normativity_score * 0.15 +     # 语法规范性
                modifier_score * 0.10          # 修饰成分复杂度
            )

            return min(1.0, final_score)

        except Exception as e:
            logger.warning(f"语法复杂度分析失败: {e}")
            return 0.5

    def _analyze_sentence_structure(self, query: str, words: List[str]) -> float:
        """分析句子结构复杂度"""
        try:
            # 从句数量（通过"的、地、得"等结构词检测）
            clause_markers = ['的', '地', '得', '所', '之']
            clause_count = sum(1 for word in words if word in clause_markers)
            clause_score = min(1.0, clause_count / 5)  # 5个以上为满分

            # 并列结构数量
            coordinators = ['和', '或', '与', '及', '以及', '并且', '而且', '或者', '还是']
            coord_count = sum(1 for word in words if word in coordinators)
            coord_score = min(1.0, coord_count / 3)  # 3个以上为满分

            # 嵌套结构（括号、引号等）
            nesting_score = 0
            if '(' in query and ')' in query:
                nesting_score += 0.3
            if '"' in query or '"' in query or '' in query or '' in query:
                nesting_score += 0.3
            if '[' in query and ']' in query:
                nesting_score += 0.2
            if '{' in query and '}' in query:
                nesting_score += 0.2

            # 句子数量
            sentences = re.split(r'[。！？.!?]+', query)
            sentence_count = len([s for s in sentences if s.strip()])
            sentence_count_score = min(1.0, sentence_count / 3)  # 3句以上为满分

            # 综合评分
            structure_score = (
                clause_score * 0.3 +
                coord_score * 0.25 +
                min(1.0, nesting_score) * 0.25 +
                sentence_count_score * 0.2
            )

            return min(1.0, structure_score)

        except Exception as e:
            logger.warning(f"句子结构分析失败: {e}")
            return 0.3

    def _analyze_grammatical_markers(self, query: str, words: List[str], total_words: int) -> float:
        """分析语法标记词密度"""
        try:
            # 连词
            conjunctions = ['虽然', '但是', '因为', '所以', '如果', '那么', '只要', '除非', 
                          '既然', '由于', '因此', '因而', '从而', '以致', '致使', '然而',
                          '尽管', '即使', '无论', '不管', '不论', '不论', '不但', '而且']
            conj_count = sum(1 for word in words if word in conjunctions)

            # 介词
            prepositions = ['在', '从', '向', '对', '关于', '对于', '根据', '按照', '通过',
                          '经过', '沿着', '顺着', '朝着', '朝着', '为了', '由于', '除了',
                          '除了', '除了', '除了', '除了', '除了', '除了', '除了', '除了']
            prep_count = sum(1 for word in words if word in prepositions)

            # 助词
            particles = ['的', '地', '得', '了', '着', '过', '呢', '吗', '吧', '啊', '呀', '哇',
                        '嘛', '啦', '哦', '唉', '嗯', '哼', '哈', '呵']
            part_count = sum(1 for word in words if word in particles)

            # 计算总标记词密度
            total_markers = conj_count + prep_count + part_count
            marker_density = total_markers / total_words if total_words > 0 else 0
            density_score = min(1.0, marker_density * 5)  # 调整权重

            # 标记词多样性（不同类型都有）
            diversity_score = 0
            if conj_count > 0: diversity_score += 0.4
            if prep_count > 0: diversity_score += 0.3
            if part_count > 0: diversity_score += 0.3

            # 综合评分
            final_score = (
                density_score * 0.6 +
                diversity_score * 0.4
            )

            return min(1.0, final_score)

        except Exception as e:
            logger.warning(f"语法标记词分析失败: {e}")
            return 0.3

    def _analyze_sentence_type_diversity(self, query: str) -> float:
        """分析句式类型多样性"""
        try:
            sentence_types = 0

            # 疑问句检测
            question_markers = ['什么', '如何', '为什么', '哪里', '哪个', '谁', '何时', '怎样', '多少', '吗', '呢', '？', '?']
            if any(marker in query for marker in question_markers):
                sentence_types += 1

            # 感叹句检测
            if '！' in query or '!' in query or any(word in query for word in ['啊', '呀', '哇']):
                sentence_types += 1

            # 条件句检测
            conditional_patterns = ['如果...就', '只要...就', '只有...才', '除非...才', '倘若...就', '假如...就']
            for pattern in conditional_patterns:
                parts = pattern.split('...')
                if all(part in query for part in parts):
                    sentence_types += 1
                    break

            # 转折句检测
            adversative_patterns = ['虽然...但是', '尽管...然而', '虽然...可是', '尽管...但是']
            for pattern in adversative_patterns:
                parts = pattern.split('...')
                if all(part in query for part in parts):
                    sentence_types += 1
                    break

            # 因果句检测
            causal_patterns = ['因为...所以', '由于...因此', '由于...因而', '既然...就']
            for pattern in causal_patterns:
                parts = pattern.split('...')
                if all(part in query for part in parts):
                    sentence_types += 1
                    break

            # 评分：句式类型越多，复杂度越高
            if sentence_types >= 4:
                return 1.0
            elif sentence_types >= 3:
                return 0.8
            elif sentence_types >= 2:
                return 0.6
            elif sentence_types >= 1:
                return 0.4
            else:
                return 0.2

        except Exception as e:
            logger.warning(f"句式类型分析失败: {e}")
            return 0.3

    def _analyze_grammatical_normativity(self, query: str, words: List[str]) -> float:
        """分析语法规范性"""
        try:
            score = 0.0

            # 标点使用复杂度
            punctuation_marks = ['，', ',', '；', ';', '：', ':', '（', '(', '）', ')', 
                               '"', '"', ''', ''', '【', '[', '】', ']', '《', '<', '》', '>']
            punct_count = sum(1 for char in query if char in punctuation_marks)
            punct_score = min(1.0, punct_count / 8)  # 8个以上标点为满分

            # 语序复杂度（检测倒装、前置等）
            # 检测"是...的"强调结构
            if '是' in query and '的' in query:
                # 检查"是"和"的"之间是否有内容
                is_index = query.find('是')
                de_index = query.find('的', is_index)
                if is_index < de_index and de_index - is_index > 2:
                    score += 0.2

            # 检测"把"字句、"被"字句等特殊句式
            if '把' in query:
                score += 0.2
            if '被' in query or '让' in query or '使' in query:
                score += 0.2

            # 检测"连...都/也"强调结构
            if '连' in query and ('都' in query or '也' in query):
                score += 0.2

            # 综合评分
            final_score = (
                punct_score * 0.5 +
                min(1.0, score) * 0.5
            )

            return min(1.0, final_score)

        except Exception as e:
            logger.warning(f"语法规范性分析失败: {e}")
            return 0.3

    def _analyze_modifier_complexity(self, query: str, words: List[str]) -> float:
        """分析修饰成分复杂度"""
        try:
            # 定语数量（"的"字结构）
            de_count = query.count('的')
            attributive_score = min(1.0, de_count / 5)  # 5个以上为满分

            # 状语数量（"地"字结构和时间/地点状语）
            di_count = query.count('地')
            time_adverbs = ['现在', '过去', '将来', '刚才', '马上', '立刻', '立即', '已经', '曾经', '正在']
            time_count = sum(1 for word in words if word in time_adverbs)
            adverbial_score = min(1.0, (di_count + time_count) / 4)  # 4个以上为满分

            # 补语数量（"得"字结构）
            dei_count = query.count('得')
            complement_score = min(1.0, dei_count / 3)  # 3个以上为满分

            # 综合评分
            final_score = (
                attributive_score * 0.4 +
                adverbial_score * 0.35 +
                complement_score * 0.25
            )

            return min(1.0, final_score)

        except Exception as e:
            logger.warning(f"修饰成分分析失败: {e}")
            return 0.3

    def _analyze_reasoning_complexity(self, query: str) -> float:
        """分析推理需求和认知复杂性（已废弃，保留用于兼容性，实际调用语法复杂度分析）"""
        # 重定向到语法复杂度分析
        return self._analyze_grammatical_complexity(query)

    def _assess_cognitive_load(self, query: str) -> float:
        """评估认知负荷"""
        try:
            # 句子长度和数量
            sentences = re.split(r'[。！？.!?]+', query)
            sentence_lengths = [len(jieba.lcut(s.strip())) for s in sentences if s.strip()]

            if not sentence_lengths:
                return 0.1

            avg_sentence_length = sum(sentence_lengths) / len(sentence_lengths)
            max_sentence_length = max(sentence_lengths)

            # 长句惩罚
            length_penalty = 0
            for length in sentence_lengths:
                if length > 20:
                    length_penalty += 0.2
                elif length > 15:
                    length_penalty += 0.1

            # 嵌套结构评估
            nesting_indicators = ['如果...那么', '虽然...但是', '因为...所以', '不但...而且']
            nesting_score = 0
            for pattern in nesting_indicators:
                if all(part in query for part in pattern.split('...')):
                    nesting_score += 0.3

            # 信息密度（数字、专有名词等的密度）
            info_density = self._calculate_info_density(query)

            # 综合认知负荷评分
            cognitive_load = (
                min(1.0, avg_sentence_length / 20) * 0.3 +
                min(1.0, max_sentence_length / 25) * 0.2 +
                min(1.0, length_penalty) * 0.2 +
                min(1.0, nesting_score) * 0.15 +
                min(1.0, info_density) * 0.15
            )

            return cognitive_load

        except Exception:
            return 0.3

    def _calculate_info_density(self, query: str) -> float:
        """计算信息密度"""
        try:
            # 数字密度
            numbers = re.findall(r'\d+', query)
            number_density = len(numbers) / max(len(query), 1) * 100

            # 专有名词识别（简单规则：大写字母开头的词组）
            proper_nouns = re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', query)
            proper_noun_density = len(proper_nouns) / max(len(query.split()), 1)

            # 引号内容（引述、术语等）
            quoted_content = re.findall(r'["\"][^"\"]*["\"]', query)
            quote_density = len(quoted_content) / max(len(query.split()), 1)

            # 综合信息密度
            info_density = min(1.0, (number_density * 0.4 + proper_noun_density * 0.4 + quote_density * 0.2) * 10)

            return info_density

        except Exception:
            return 0.0

    def _analyze_logic_structure(self, query: str) -> float:
        """分析逻辑结构复杂性"""
        try:
            # 逻辑连接词
            logical_connectors = [
                '并且', '而且', '或者', '但是', '然而', '因此', '所以', '因为',
                '虽然', '尽管', '如果', '只要', '除非', '无论', '不管', '即使',
                '既然', '由于', '以便', '以免', '从而', '进而', '此外', '另外'
            ]

            connector_count = sum(1 for connector in logical_connectors if connector in query)
            connector_score = min(1.0, connector_count / 5)

            # 条件结构
            conditional_patterns = ['如果...就', '只要...就', '只有...才', '除非...才']
            conditional_score = 0
            for pattern in conditional_patterns:
                if all(part in query for part in pattern.split('...')):
                    conditional_score += 0.3

            # 递归或嵌套结构
            nested_indicators = ['一方面...另一方面', '不仅...而且', '不但...还']
            nested_score = 0
            for indicator in nested_indicators:
                if all(part in query for part in indicator.split('...')):
                    nested_score += 0.3

            # 综合逻辑复杂度
            logic_complexity = min(1.0, connector_score * 0.5 + conditional_score * 0.3 + nested_score * 0.2)

            return logic_complexity

        except Exception:
            return 0.0

    def _analyze_temporal_complexity(self, query: str) -> float:
        """分析时间序列推理复杂度"""
        try:
            temporal_keywords = [
                '之前', '之后', '同时', '首先', '其次', '然后', '最后', '接着',
                '过去', '现在', '将来', '以前', '以后', '当时', '此刻', '将来',
                '早期', '后期', '初期', '末期', '近期', '远期', '短期', '长期',
                '顺序', '序列', '步骤', '阶段', '过程', '历史', '发展', '演变'
            ]

            temporal_count = sum(1 for keyword in temporal_keywords if keyword in query)
            temporal_score = min(1.0, temporal_count / 4)

            # 时间序列模式
            sequential_patterns = ['第一步...第二步...第三步', '首先...然后...最后', '过去...现在...将来']
            sequential_score = 0
            for pattern in sequential_patterns:
                parts = pattern.split('...')
                if len([part for part in parts if part in query]) >= 2:
                    sequential_score += 0.4

            return min(1.0, temporal_score * 0.7 + sequential_score * 0.3)

        except Exception:
            return 0.0

    def _analyze_causal_complexity(self, query: str) -> float:
        """分析因果关系推理复杂度"""
        try:
            causal_keywords = [
                '原因', '结果', '导致', '引起', '造成', '影响', '作用', '效果',
                '因为', '所以', '由于', '因此', '因而', '从而', '以致', '致使',
                '根源', '起因', '诱因', '因素', '要素', '机制', '原理'
            ]

            causal_count = sum(1 for keyword in causal_keywords if keyword in query)
            causal_score = min(1.0, causal_count / 5)

            # 因果链复杂度（多重因果关系）
            chain_indicators = ['不仅...而且', '一方面...另一方面', '既是...也是']
            chain_score = 0
            for indicator in chain_indicators:
                if all(part in query for part in indicator.split('...')):
                    chain_score += 0.3

            return min(1.0, causal_score * 0.8 + chain_score * 0.2)

        except Exception:
            return 0.0

    def route_based_on_complexity(self, query: str, network_status: Dict = None) -> Dict[str, any]:
        """
        基于复杂度的路由决策

        Args:
            query: 用户查询
            network_status: 网络状态信息（可选）

        Returns:
            路由决策结果
        """
        try:
            complexity_result = self.analyze_complexity(query)
            complexity_score = complexity_result['total_complexity']

            # 基础路由决策
            base_route = self._get_base_routing_decision(complexity_score)

            # 考虑网络状况调整路由
            final_route = self._adjust_route_by_network(base_route, network_status)

            # 生成路由解释
            explanation = self._generate_routing_explanation(
                complexity_result, base_route, final_route, network_status
            )

            # 记录路由决策
            self._record_routing_decision(query, complexity_result, final_route)

            result = {
                'route': final_route,
                'complexity_analysis': complexity_result,
                'base_route': base_route,
                'explanation': explanation,
                'confidence': self._calculate_routing_confidence(complexity_result),
                'recommendations': self._generate_recommendations(complexity_result, final_route)
            }

            logger.info(f"路由决策完成: {final_route} (复杂度: {complexity_score:.3f})")
            return result

        except Exception as e:
            logger.error(f"路由决策失败: {e}")
            return {
                'route': 'local_capable',
                'complexity_analysis': {'total_complexity': 0.5},
                'base_route': 'local_capable',
                'explanation': '路由决策失败，使用默认本地路由',
                'confidence': 0.3,
                'recommendations': ['建议检查系统状态']
            }

    def _get_base_routing_decision(self, complexity_score: float) -> str:
        """基于复杂度评分的基础路由决策"""
        if complexity_score >= 0.85:
            # 极高复杂度：必须使用云端强模型
            return "cloud_required"
        elif complexity_score >= 0.2:
            # 高于0.2的复杂度：云端模型优先
            return "cloud_preferred"
        else:
            # 0.2以下的复杂度：本地处理即可
            return "local_sufficient"

    def _adjust_route_by_network(self, base_route: str, network_status: Dict = None) -> str:
        """根据网络状况调整路由决策"""
        if network_status is None:
            # 没有网络状态信息，使用基础路由
            return base_route

        cloud_available = network_status.get('cloud_available', True)
        latency = network_status.get('latency', 100)  # 默认100ms
        bandwidth = network_status.get('bandwidth', 10)  # 默认10Mbps

        # 网络质量评估
        network_quality = self._assess_network_quality(cloud_available, latency, bandwidth)

        # 根据网络质量调整路由
        if not cloud_available or network_quality < 0.3:
            # 云端不可用或网络质量差，强制本地处理
            if base_route == "cloud_required":
                # 本来要求云端，但现在只能本地，降低期望
                return "local_fallback"
            else:
                return "local_forced"
        elif network_quality < 0.6:
            # 网络质量一般，优先本地
            if base_route in ["cloud_required", "cloud_preferred"]:
                return "cloud_if_available"
            else:
                return base_route
        else:
            # 网络质量好，保持基础路由
            return base_route

    def _assess_network_quality(self, available: bool, latency: float, bandwidth: float) -> float:
        """评估网络质量评分 (0-1)"""
        if not available:
            return 0.0

        # 延迟评分 (延迟越低越好)
        latency_score = max(0, 1 - latency / 1000)  # 1000ms以上为0分

        # 带宽评分 (带宽越高越好)
        bandwidth_score = min(1.0, bandwidth / 100)  # 100Mbps以上为满分

        # 综合评分
        quality_score = latency_score * 0.6 + bandwidth_score * 0.4
        return quality_score

    def _generate_routing_explanation(self, complexity_result: Dict, base_route: str,
                                    final_route: str, network_status: Dict = None) -> str:
        """生成路由决策解释"""
        complexity_score = complexity_result['total_complexity']

        explanation = f"复杂度评分: {complexity_score:.3f}\n"

        # 基础路由解释
        route_explanations = {
            'cloud_required': '要求使用云端强模型处理',
            'cloud_preferred': '建议使用云端模型获得更好效果',
            'cloud_if_available': '云端模型可用时优先使用',
            'local_capable': '本地模型可以处理',
            'local_sufficient': '本地处理即可满足需求'
        }

        explanation += f"基础路由: {route_explanations.get(base_route, base_route)}"

        # 网络状况调整说明
        if network_status and base_route != final_route:
            explanation += f"\n路由调整: 由于网络状况限制，调整为{final_route}"

        # 关键影响因素说明
        key_factors = []
        dimensions = ['query_length', 'keyword_richness', 'semantic_depth', 'domain_specificity', 'reasoning_requirements']

        for dim in dimensions:
            score = complexity_result.get(dim, 0)
            if score >= 0.7:
                key_factors.append(f"{dim}(高)")
            elif score <= 0.3:
                key_factors.append(f"{dim}(低)")

        if key_factors:
            explanation += f"\n关键因素: {', '.join(key_factors)}"

        return explanation

    def _calculate_routing_confidence(self, complexity_result: Dict) -> float:
        """计算路由决策的置信度"""
        # 基于复杂度评分的一致性和稳定性计算置信度
        scores = [
            complexity_result.get('query_length', 0.5),
            complexity_result.get('keyword_richness', 0.5),
            complexity_result.get('semantic_depth', 0.5),
            complexity_result.get('domain_specificity', 0.5),
            complexity_result.get('reasoning_requirements', 0.5)
        ]

        # 计算标准差（标准差越小，置信度越高）
        mean_score = sum(scores) / len(scores)
        variance = sum((score - mean_score) ** 2 for score in scores) / len(scores)
        std_dev = variance ** 0.5

        # 将标准差转换为置信度
        confidence = max(0.3, 1.0 - std_dev)

        return min(1.0, confidence)

    def _generate_recommendations(self, complexity_result: Dict, final_route: str) -> List[str]:
        """生成优化建议"""
        recommendations = []
        complexity_score = complexity_result['total_complexity']

        # 基于复杂度的建议
        if complexity_score < 0.4:
            recommendations.append("查询较为简单，可考虑添加更多具体要求")
        elif complexity_score > 0.8:
            recommendations.append("查询非常复杂，建议分解为多个简单查询")
            recommendations.append("考虑提供更多上下文信息")

        # 基于维度的建议
        dimensions = {
            'query_length': '查询长度',
            'keyword_richness': '关键词丰富度',
            'semantic_depth': '语义深度',
            'domain_specificity': '领域专业性',
            'reasoning_requirements': '语法复杂度'
        }

        for dim, name in dimensions.items():
            score = complexity_result.get(dim, 0)
            if score > 0.8:
                recommendations.append(f"{name}较高，处理时间可能较长")
            elif score < 0.2:
                recommendations.append(f"{name}较低，建议提供更多相关信息")

        # 基于路由的建议
        if final_route in ['cloud_required', 'cloud_preferred']:
            recommendations.append("将使用云端模型处理，请确保网络连接稳定")
        elif final_route == 'local_fallback':
            recommendations.append("网络状况不佳，使用本地模型处理，效果可能受限")

        return recommendations

    def _record_routing_decision(self, query: str, complexity_result: Dict, route: str):
        """记录路由决策用于学习优化"""
        try:
            record = {
                'query': query[:100],  # 只记录前100字符
                'complexity_result': complexity_result,
                'route': route,
                'timestamp': datetime.now().isoformat()
            }
            self.query_history.append(record)

            # 保持历史记录在合理范围内
            if len(self.query_history) > 1000:
                self.query_history = self.query_history[-500:]

        except Exception as e:
            logger.warning(f"记录路由决策失败: {e}")

    def learn_from_feedback(self, query: str, route: str, user_satisfaction: float,
                          response_time: float = None, actual_quality: float = None):
        """
        从用户反馈中学习，优化复杂度评估模型

        Args:
            query: 原始查询
            route: 实际使用的路由
            user_satisfaction: 用户满意度评分 (0-1)
            response_time: 响应时间（毫秒）
            actual_quality: 实际响应质量评分 (0-1)
        """
        try:
            # 重新分析复杂度
            complexity_result = self.analyze_complexity(query)

            feedback_record = {
                'query': query[:100],
                'complexity_result': complexity_result,
                'route': route,
                'user_satisfaction': user_satisfaction,
                'response_time': response_time,
                'actual_quality': actual_quality,
                'timestamp': datetime.now().isoformat()
            }

            self.performance_feedback.append(feedback_record)

            # 定期更新模型权重
            if len(self.performance_feedback) % 50 == 0:
                self._update_complexity_weights()

            logger.info(f"学习反馈记录: 满意度 {user_satisfaction:.2f}, 路由 {route}")

        except Exception as e:
            logger.warning(f"学习反馈处理失败: {e}")

    def _update_complexity_weights(self):
        """基于历史反馈更新复杂度权重"""
        try:
            if len(self.performance_feedback) < 20:
                return  # 数据不足

            # 分析各维度与用户满意度的相关性
            dimension_correlations = {}
            dimensions = ['query_length', 'keyword_richness', 'semantic_depth', 'domain_specificity', 'reasoning_requirements']

            for dim in dimensions:
                correlations = []
                for feedback in self.performance_feedback:
                    complexity_score = feedback['complexity_result'].get(dim, 0.5)
                    satisfaction = feedback['user_satisfaction']
                    correlations.append((complexity_score, satisfaction))

                if correlations:
                    # 计算简单相关系数
                    correlation = self._calculate_correlation(correlations)
                    dimension_correlations[dim] = abs(correlation)

            # 归一化相关系数作为新权重
            total_correlation = sum(dimension_correlations.values())
            if total_correlation > 0:
                for dim in dimensions:
                    new_weight = dimension_correlations[dim] / total_correlation
                    # 平滑更新权重（避免剧烈变化）
                    old_weight = self.complexity_weights[dim]
                    self.complexity_weights[dim] = old_weight * 0.7 + new_weight * 0.3

                logger.info(f"复杂度权重已更新: {self.complexity_weights}")

        except Exception as e:
            logger.warning(f"更新复杂度权重失败: {e}")

    def _calculate_correlation(self, pairs: List[Tuple[float, float]]) -> float:
        """计算简单相关系数"""
        if len(pairs) < 2:
            return 0.0

        x_mean = sum(x for x, y in pairs) / len(pairs)
        y_mean = sum(y for x, y in pairs) / len(pairs)

        numerator = sum((x - x_mean) * (y - y_mean) for x, y in pairs)
        x_var = sum((x - x_mean) ** 2 for x, y in pairs)
        y_var = sum((y - y_mean) ** 2 for x, y in pairs)

        if x_var == 0 or y_var == 0:
            return 0.0

        return numerator / ((x_var * y_var) ** 0.5)

    def get_complexity_statistics(self) -> Dict:
        """获取复杂度分析统计信息"""
        try:
            if not self.query_history:
                return {'total_queries': 0}

            total_queries = len(self.query_history)
            complexity_scores = [record['complexity_result']['total_complexity'] for record in self.query_history]

            # 路由分布统计
            route_counts = {}
            for record in self.query_history:
                route = record['route']
                route_counts[route] = route_counts.get(route, 0) + 1

            # 满意度统计（如果有反馈数据）
            satisfaction_stats = {}
            if self.performance_feedback:
                satisfactions = [feedback['user_satisfaction'] for feedback in self.performance_feedback]
                satisfaction_stats = {
                    'count': len(satisfactions),
                    'average': sum(satisfactions) / len(satisfactions),
                    'min': min(satisfactions),
                    'max': max(satisfactions)
                }

            return {
                'total_queries': total_queries,
                'complexity_distribution': {
                    'mean': sum(complexity_scores) / len(complexity_scores),
                    'min': min(complexity_scores),
                    'max': max(complexity_scores),
                    'median': sorted(complexity_scores)[len(complexity_scores)//2]
                },
                'route_distribution': route_counts,
                'satisfaction_stats': satisfaction_stats,
                'current_weights': self.complexity_weights
            }

        except Exception as e:
            logger.warning(f"获取统计信息失败: {e}")
            return {'error': str(e)}

