#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的Ollama模型预热脚本
"""

import requests
import json
import time

def preload_model(model_name: str, ollama_host: str = "http://localhost:11434"):
    """预加载指定模型"""
    print(f"🔥 预热模型: {model_name}")
    
    try:
        url = f"{ollama_host}/api/generate"
        data = {
            "model": model_name,
            "prompt": "Hello",
            "stream": False,
            "keep_alive": "2h",
            "options": {"num_predict": 1}
        }
        
        start_time = time.time()
        response = requests.post(url, json=data, timeout=120)
        load_time = time.time() - start_time
        
        if response.status_code == 200:
            print(f"✅ {model_name} 预热完成 ({load_time:.1f}秒)")
            return True
        else:
            print(f"❌ {model_name} 预热失败: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ {model_name} 预热出错: {e}")
        return False

def warmup_all_models():
    """预热所有必需的模型"""
    models = ["qwen3:1.7b", "bge-large:latest","deepseek-r1:1.5b"]
    
    print("🚀 开始预热Ollama模型...")
    print("=" * 40)
    
    success_count = 0
    for model in models:
        if preload_model(model):
            success_count += 1
    
    print(f"\n📊 预热完成: {success_count}/{len(models)} 个模型成功")
    
    if success_count == len(models):
        print("✅ 所有模型预热成功，可以开始使用!")
    else:
        print("⚠️ 部分模型预热失败，请检查Ollama服务状态")

if __name__ == "__main__":
    warmup_all_models()