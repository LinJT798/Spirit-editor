#!/bin/bash

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "未找到虚拟环境，请先运行 ./setup.sh 安装依赖"
    exit 1
fi

# 激活虚拟环境并运行动画预览工具
source venv/bin/activate
python animation_preview.py