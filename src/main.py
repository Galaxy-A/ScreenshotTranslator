# main.py - 程序入口
import sys
import os

# 添加当前目录到系统路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import OCRApplication
import tkinter as tk

if __name__ == "__main__":
    root = tk.Tk()
    app = OCRApplication(root)

    root.protocol("WM_DELETE_WINDOW", app.on_closing)

    root.mainloop()