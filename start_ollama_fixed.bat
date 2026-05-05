@echo off
chcp 65001 >nul
echo 启动优化的Ollama服务 (Windows)
echo ================================

REM 设置Ollama优化环境变量
set OLLAMA_KEEP_ALIVE=2h
set OLLAMA_MAX_LOADED_MODELS=3
set OLLAMA_NUM_PARALLEL=3
set OLLAMA_FLASH_ATTENTION=1

echo 优化配置:
echo    模型保持时间: 2小时
echo    最大模型数: 3个
echo    并行处理: 1个
echo    Flash Attention: 启用
echo.

echo 启动Ollama服务...
ollama serve
ollama pull bge-m3:latest
pause
