import requests
import json
import time


def simple_speed_test(api_key: str):
    """简化版速度测试"""
    url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    models = ["glm-4", "glm-4-0520"]
    prompt = "请简单介绍一下你自己"

    for model in models:
        print(f"\n测试模型: {model}")

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "max_tokens": 100
        }

        start_time = time.time()
        first_chunk = True
        first_chunk_time = None
        response_text = ""

        try:
            response = requests.post(url, headers=headers, json=payload, stream=True)

            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]
                        if data == '[DONE]':
                            break

                        if first_chunk:
                            first_chunk_time = time.time() - start_time
                            first_chunk = False

                        try:
                            chunk = json.loads(data)
                            if 'choices' in chunk and chunk['choices']:
                                content = chunk['choices'][0].get('delta', {}).get('content', '')
                                if content:
                                    response_text += content
                                    print(content, end='', flush=True)
                        except:
                            continue

            total_time = time.time() - start_time
            print(f"\n\n总时间: {total_time:.2f}s, 首包时间: {first_chunk_time:.2f}s")

        except Exception as e:
            print(f"错误: {e}")


# 使用示例
if __name__ == "__main__":
    API_KEY = "0ea305d6e3224d5c8ac9a8f75c80bb01.Kg5l7eFt85APJOXM"  # 替换为你的API Key
    simple_speed_test(API_KEY)