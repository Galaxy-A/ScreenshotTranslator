# screen_capture.py - 屏幕截图功能
import tkinter as tk
from PIL import ImageGrab

class ScreenCapture:
    """处理屏幕截图相关功能的类"""

    def __init__(self, dpi_scale, screen_width, screen_height, virtual_width, virtual_height):
        self.dpi_scale = dpi_scale
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.virtual_width = virtual_width
        self.virtual_height = virtual_height

    def get_physical_coords(self, virtual_coords):
        """将虚拟坐标转换为物理坐标"""
        x1, y1, x2, y2 = virtual_coords
        return (
            int(x1 * self.dpi_scale),
            int(y1 * self.dpi_scale),
            int(x2 * self.dpi_scale),
            int(y2 * self.dpi_scale)
        )

    def get_virtual_coords(self, physical_coords):
        """将物理坐标转换为虚拟坐标"""
        x1, y1, x2, y2 = physical_coords
        return (
            x1 / self.dpi_scale,
            y1 / self.dpi_scale,
            x2 / self.dpi_scale,
            y2 / self.dpi_scale
        )

    def capture_area(self, bbox):
        """捕获指定区域的屏幕"""
        try:
            return ImageGrab.grab(bbox=bbox)
        except Exception as e:
            # 备选截图方法
            full_screen = ImageGrab.grab()
            return full_screen.crop(bbox)

    def select_area(self, master):
        """使用鼠标选择截图区域"""
        top = tk.Toplevel(master)
        top.title("截图文字识别 - 按ESC退出")
        top.overrideredirect(True)
        top.geometry(f"{self.screen_width}x{self.screen_height}+0+0")
        top.attributes('-alpha', 0.3)
        top.attributes('-topmost', True)
        top.update_idletasks()

        container = tk.Frame(top)
        container.pack(fill=tk.BOTH, expand=True)

        prompt_label = tk.Label(
            container,
            text="按住鼠标左键拖拽选择区域，按ESC取消",
            fg="white", bg="black",
            font=("微软雅黑", 14)
        )
        prompt_label.place(relx=0.5, rely=0.95, anchor=tk.CENTER)

        canvas = tk.Canvas(container, bg='white', highlightthickness=0, cursor="cross")
        canvas.pack(fill=tk.BOTH, expand=True)

        self._create_overlay(canvas)

        start_x, start_y = 0, 0
        rect_id = None
        selected_coords = None

        def on_click(event):
            nonlocal start_x, start_y, rect_id
            start_x, start_y = event.x, event.y
            rect_id = canvas.create_rectangle(
                start_x, start_y, start_x, start_y,
                outline='red', width=3, fill=''
            )

        def on_drag(event):
            nonlocal rect_id
            if rect_id:
                canvas.coords(rect_id, start_x, start_y, event.x, event.y)

        def on_release(event):
            nonlocal selected_coords, rect_id
            if rect_id:
                selected_coords = (start_x, start_y, event.x, event.y)
            top.destroy()

        canvas.bind('<Button-1>', on_click)
        canvas.bind('<B1-Motion>', on_drag)
        canvas.bind('<ButtonRelease-1>', on_release)
        top.bind('<Escape>', lambda e: top.destroy())
        top.focus_force()
        master.wait_window(top)

        return selected_coords

    def _create_overlay(self, canvas):
        """创建覆盖层确保完全覆盖屏幕"""
        canvas.create_rectangle(
            0, 0, self.screen_width, self.screen_height,
            fill='white', outline=''
        )
        canvas.create_text(
            self.screen_width // 2, self.screen_height - 50,
            text="按住鼠标左键拖拽选择区域，按ESC取消",
            fill="black",
            font=("微软雅黑", 14),
            anchor=tk.CENTER
        )