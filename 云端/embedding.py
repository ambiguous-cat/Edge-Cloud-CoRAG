import os
import requests
from dotenv import load_dotenv

load_dotenv()  # 加载.env文件

# 读取智谱API配置
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")

# 嵌入模型配置
embedding_models = ['embedding-3']
embedding_model = embedding_models[0]  # 使用智谱清言embedding-3模型


def get_embedding(text):
    """获取单条文本的嵌入向量"""
    if embedding_model not in embedding_models:
        raise ValueError(f"不支持的嵌入模型: {embedding_model}")
    elif embedding_model == 'embedding-3':
        return get_zhipu_embedding(text)


def get_embeddings(texts):
    """批量获取文本嵌入，返回二维数组"""
    if embedding_model not in embedding_models:
        raise ValueError(f"不支持的嵌入模型: {embedding_model}")
    elif embedding_model == 'embedding-3':
        return get_zhipu_embeddings(texts)


def get_zhipu_embedding(text, model="embedding-3", api_key=None, dimensions=2048):
    """
    调用智谱清言的嵌入模型，获取单条文本的嵌入向量
    维度固定为2048
    """
    if api_key is None:
        api_key = ZHIPU_API_KEY
    if not api_key:
        raise ValueError("智谱API密钥未设置，请设置ZHIPU_API_KEY环境变量")

    url = "https://open.bigmodel.cn/api/paas/v4/embeddings"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    data = {
        "model": model,
        "input": text,
        "dimensions": dimensions  # 固定为2048维度
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        result = response.json()

        if "data" in result and len(result["data"]) > 0:
            return result["data"][0]["embedding"]
        else:
            raise Exception(f"API响应格式异常: {result}")

    except requests.exceptions.RequestException as e:
        print(f"智谱AI嵌入API请求出错: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"响应状态码: {e.response.status_code}")
            try:
                error_detail = e.response.json()
                print(f"错误详情: {error_detail}")
            except:
                print(f"响应内容: {e.response.text[:200]}...")
        raise
    except Exception as e:
        print(f"智谱AI嵌入处理出错: {e}")
        raise


def get_zhipu_embeddings(texts, model="embedding-3", api_key=None, dimensions=2048):
    """
    批量获取文本嵌入，返回二维数组
    维度固定为2048
    """
    if api_key is None:
        api_key = ZHIPU_API_KEY
    if not api_key:
        raise ValueError("智谱API密钥未设置，请设置ZHIPU_API_KEY环境变量")

    url = "https://open.bigmodel.cn/api/paas/v4/embeddings"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    data = {
        "model": model,
        "input": texts,
        "dimensions": dimensions  # 固定为2048维度
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=120)
        response.raise_for_status()
        result = response.json()

        if "data" in result and len(result["data"]) > 0:
            return [item["embedding"] for item in result["data"]]
        else:
            raise Exception(f"API响应格式异常: {result}")

    except requests.exceptions.RequestException as e:
        print(f"智谱AI批量嵌入API请求出错: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"响应状态码: {e.response.status_code}")
            try:
                error_detail = e.response.json()
                print(f"错误详情: {error_detail}")
            except:
                print(f"响应内容: {e.response.text[:200]}...")
        raise
    except Exception as e:
        print(f"智谱AI批量嵌入处理出错: {e}")
        raise


# 工具函数
def set_embedding_model(model_name: str):
    """设置当前使用的嵌入模型"""
    global embedding_model
    if model_name in embedding_models:
        embedding_model = model_name
        print(f"嵌入模型已切换为: {model_name}")
    else:
        raise ValueError(f"不支持的模型: {model_name}，可用模型: {embedding_models}")


def get_current_embedding_model() -> str:
    """获取当前使用的嵌入模型"""
    return embedding_model


def get_available_embedding_models() -> list:
    """获取所有可用的嵌入模型"""
    return embedding_models.copy()


# 测试函数
def test_embedding_model():
    """测试嵌入模型功能"""
    test_text = "这是一个测试文本，用于验证嵌入模型是否正常工作。"

    print("=== 嵌入模型测试 ===")
    print(f"当前模型: {get_current_embedding_model()}")
    print(f"测试文本: {test_text}")

    # 检查API配置
    print("\n1. 检查智谱API配置...")
    if not ZHIPU_API_KEY:
        print("❌ 未找到智谱API密钥，请设置ZHIPU_API_KEY环境变量")
        return False
    else:
        print("✅ 智谱API密钥配置正常")

    # 测试单条嵌入
    print("\n2. 测试单条文本嵌入...")
    try:
        embedding = get_embedding(test_text)
        print(f"✅ 嵌入成功，向量维度: {len(embedding)}")
        print(f"   前10个维度值: {embedding[:10]}")
    except Exception as e:
        print(f"❌ 单条嵌入测试失败: {e}")
        return False

    # 测试批量嵌入
    print("\n3. 测试批量文本嵌入...")
    try:
        test_texts = [
            "这是第一条测试文本",
            "这是第二条测试文本",
            "这是第三条测试文本"
        ]
        embeddings = get_embeddings(test_texts)
        print(f"✅ 批量嵌入成功，共 {len(embeddings)} 条嵌入向量")
        print(f"   每条向量维度: {len(embeddings[0])}")
    except Exception as e:
        print(f"❌ 批量嵌入测试失败: {e}")
        return False

    return True


if __name__ == "__main__":
    # 运行测试
    test_embedding_model()