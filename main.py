#!/usr/bin/env python3

import tkinter as tk
import sys
import os


def check_dependencies():
    try:
        import PIL
        import cv2
        import numpy
        return True
    except ImportError as e:
        print(f"缺少依赖包: {e}")
        print("\n请运行以下命令安装依赖:")
        print("pip install -r requirements.txt")
        return False


def main():
    if not check_dependencies():
        input("\n按回车键退出...")
        sys.exit(1)
    
    from gui import SpriteSheetGUI
    
    root = tk.Tk()
    app = SpriteSheetGUI(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\n程序被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"程序运行出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()