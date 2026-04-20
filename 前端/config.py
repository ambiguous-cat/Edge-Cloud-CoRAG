import os
import requests

# 本地知识库路径
LOCAL_KNOWLEDGE_BASE = "local_knowledge"

# 获取样式文件路径

# 只加载合并后的main.css
def get_css_path(file_name):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, file_name)

def load_css():
    with open(get_css_path("main.css"), "r", encoding="utf-8") as f:
        main_css = f.read()
    return main_css

APP_CSS = load_css()

# API配置增强 - 添加本地模型支持
API_CONFIG = {

    # "cloud": "http://120.26.231.14:8005",  # 云端API主机
    "cloud": "http://8.133.246.212:8005",
    "local": "http://localhost:8005"       # 本地API主机，如无本地服务可与cloud一致
}

# 模型名称映射
MODEL_MAP = {
  "云端": "glm-4",           # 云端使用OpenAI GPT-4
  "本地": "qwen3:1.7b" # 本地使用DeepSeek-R1 1.5B
}
# qwen3:1.7b
# deepseek-r1:1.5b
HEADERS = {
    'Content-Type': 'application/json'
}

MATHJAX_CONFIG = """
<script>
MathJax = {
  tex: {
    inlineMath: [['$', '$'], ['\\$', '\\$']],
    packages: {'[+]': ['ams', 'boldsymbol']}
  },
  options: {
    menuOptions: {
      settings: {
        zoom: 'DoubleClick',
        renderer: 'SVG'
      }
    }
  },
  loader: {
    load: ['[tex]/ams', '[tex]/boldsymbol']
  }
};


</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
"""



