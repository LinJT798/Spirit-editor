#!/bin/bash

echo "精灵表切割工具 - 环境配置脚本"
echo "================================"
echo ""

# 检查Python版本
python_version=$(python3 --version 2>&1)
if [ $? -eq 0 ]; then
    echo "✓ 检测到 Python: $python_version"
else
    echo "✗ 未检测到Python3，请先安装Python 3.7+"
    exit 1
fi

# 创建虚拟环境
echo ""
echo "正在创建虚拟环境..."
python3 -m venv venv

if [ $? -eq 0 ]; then
    echo "✓ 虚拟环境创建成功"
else
    echo "✗ 虚拟环境创建失败"
    exit 1
fi

# 激活虚拟环境并安装依赖
echo ""
echo "正在安装依赖包..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ 依赖安装成功！"
    echo ""
    echo "================================"
    echo "安装完成！"
    echo ""
    echo "使用方法："
    echo "1. 激活虚拟环境: source venv/bin/activate"
    echo "2. 运行程序: python main.py"
    echo ""
    echo "或直接运行: ./run.sh"
else
    echo "✗ 依赖安装失败，请检查网络连接"
    exit 1
fi