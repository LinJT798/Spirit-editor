#!/bin/bash

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "未找到虚拟环境，正在执行安装..."
    bash setup.sh
    if [ $? -ne 0 ]; then
        echo "安装失败，请手动运行 ./setup.sh"
        exit 1
    fi
fi

# 激活虚拟环境并运行程序
source venv/bin/activate
python main.py