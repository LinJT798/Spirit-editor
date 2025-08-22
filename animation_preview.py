import tkinter as tk
from tkinter import ttk, messagebox, filedialog, Canvas, Frame, Label, Scrollbar
from PIL import Image, ImageTk, ImageDraw
import json
import os
import time
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class FrameInfo:
    """单个帧的信息"""
    index: int
    row: int
    col: int
    x: int
    y: int
    width: int
    height: int
    selected: bool = False


@dataclass
class ActionGroup:
    """动作组"""
    name: str
    frames: List[Tuple[int, int]] = field(default_factory=list)  # [(row, col), ...]
    
    @property
    def frame_count(self):
        return len(self.frames)


class AnimationPreviewApp:
    def __init__(self, root):
        self.root = root
        self.root.title("帧动画预览工具")
        self.root.geometry("1400x800")
        
        # 数据成员
        self.atlas_image = None
        self.atlas_photo = None
        self.metadata = None
        self.current_atlas_path = None
        self.frames: List[FrameInfo] = []
        self.selected_frames: List[FrameInfo] = []
        self.action_groups: Dict[str, ActionGroup] = {}
        
        # 动画播放相关
        self.is_playing = False
        self.current_frame_index = 0
        self.frame_rate = 12
        self.last_frame_time = 0
        
        # 参考图集相关
        self.reference_atlas = None
        self.reference_metadata = None
        self.reference_sprites = []
        self.selected_reference_sprite = None
        self.show_reference = tk.BooleanVar(value=True)
        
        # 缩放相关
        self.animation_scale = 1.0  # 动画精灵缩放比例
        
        # UI元素
        self.scale_factor = 2.0  # 放大倍数
        
        self.setup_ui()
        self.load_atlas_list()
        
    def setup_ui(self):
        """设置UI界面"""
        # 创建菜单栏
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="刷新图集列表", command=self.load_atlas_list)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        # 主布局
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧面板 - 图集列表
        left_panel = tk.Frame(main_frame, width=250)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        self.setup_left_panel(left_panel)
        
        # 中央区域 - 图集显示
        center_panel = tk.Frame(main_frame)
        center_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        self.setup_center_panel(center_panel)
        
        # 右侧面板 - 动画预览和动作管理
        right_panel = tk.Frame(main_frame, width=300)
        right_panel.pack(side=tk.LEFT, fill=tk.Y)
        right_panel.pack_propagate(False)
        
        self.setup_right_panel(right_panel)
        
    def setup_left_panel(self, parent):
        """设置左侧面板"""
        tk.Label(parent, text="图集列表", font=("Arial", 12, "bold")).pack(pady=10)
        
        # 图集列表框
        list_frame = tk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        scrollbar = Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.atlas_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.atlas_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.atlas_listbox.yview)
        
        self.atlas_listbox.bind('<<ListboxSelect>>', self.on_atlas_select)
        
        # 刷新按钮
        tk.Button(parent, text="刷新列表", command=self.load_atlas_list).pack(pady=5)
        
        ttk.Separator(parent, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # 缩放控制
        tk.Label(parent, text="显示缩放:").pack()
        scale_frame = tk.Frame(parent)
        scale_frame.pack(fill=tk.X, pady=5)
        
        self.scale_var = tk.DoubleVar(value=2.0)
        scale_slider = tk.Scale(scale_frame, from_=1.0, to=5.0, resolution=0.5,
                               orient=tk.HORIZONTAL, variable=self.scale_var,
                               command=self.on_scale_change)
        scale_slider.pack(fill=tk.X, padx=10)
        
        ttk.Separator(parent, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # 参考图集控制
        tk.Label(parent, text="参考图集", font=("Arial", 12, "bold")).pack(pady=5)
        
        tk.Button(parent, text="选择参考图集", command=self.load_reference_atlas).pack(pady=5)
        
        self.reference_info_label = tk.Label(parent, text="未加载参考", fg='gray')
        self.reference_info_label.pack(pady=2)
        
        # 参考精灵列表
        ref_list_frame = tk.Frame(parent, height=150)
        ref_list_frame.pack(fill=tk.X, pady=5)
        ref_list_frame.pack_propagate(False)
        
        ref_scrollbar = Scrollbar(ref_list_frame)
        ref_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.reference_listbox = tk.Listbox(ref_list_frame, yscrollcommand=ref_scrollbar.set, height=6)
        self.reference_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ref_scrollbar.config(command=self.reference_listbox.yview)
        
        self.reference_listbox.bind('<<ListboxSelect>>', self.on_reference_select)
        
    def setup_center_panel(self, parent):
        """设置中央面板"""
        tk.Label(parent, text="图集预览", font=("Arial", 12, "bold")).pack()
        
        # 图集信息标签
        self.atlas_info_label = tk.Label(parent, text="未加载图集", fg='gray')
        self.atlas_info_label.pack(pady=5)
        
        # 画布框架
        canvas_frame = tk.Frame(parent, relief=tk.SUNKEN, bd=2)
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 添加滚动条
        h_scrollbar = Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        v_scrollbar = Scrollbar(canvas_frame, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 图集画布
        self.atlas_canvas = Canvas(canvas_frame, bg='gray',
                                  xscrollcommand=h_scrollbar.set,
                                  yscrollcommand=v_scrollbar.set)
        self.atlas_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        h_scrollbar.config(command=self.atlas_canvas.xview)
        v_scrollbar.config(command=self.atlas_canvas.yview)
        
        # 绑定鼠标事件
        self.atlas_canvas.bind("<Button-1>", self.on_canvas_click)
        self.atlas_canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.atlas_canvas.bind("<Control-Button-1>", self.on_canvas_ctrl_click)
        
        # 操作提示
        tip_label = tk.Label(parent, text="点击选择帧 | Ctrl+点击多选 | 拖拽连续选择", 
                           fg='gray', font=("Arial", 9))
        tip_label.pack()
        
    def setup_right_panel(self, parent):
        """设置右侧面板"""
        # 创建滚动框架容器
        scroll_container = Frame(parent)
        scroll_container.pack(fill="both", expand=True)
        
        # 创建画布和滚动条
        canvas = Canvas(scroll_container, width=300)
        scrollbar = Scrollbar(scroll_container, orient="vertical", command=canvas.yview)
        scrollable_frame = Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 先pack滚动条，再pack画布，确保滚动条可见
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        
        # 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind("<MouseWheel>", _on_mousewheel)  # Windows
        canvas.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))  # Linux
        canvas.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))   # Linux
        
        # 现在将所有控件添加到 scrollable_frame 而不是 parent
        # 动画预览区
        tk.Label(scrollable_frame, text="动画预览", font=("Arial", 12, "bold")).pack(pady=10)
        
        # 预览画布
        preview_frame = tk.Frame(scrollable_frame, relief=tk.SUNKEN, bd=2, height=200)
        preview_frame.pack(fill=tk.X, pady=5)
        preview_frame.pack_propagate(False)
        
        self.preview_canvas = Canvas(preview_frame, bg='black')
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        
        # 播放控制
        control_frame = tk.Frame(scrollable_frame)
        control_frame.pack(fill=tk.X, pady=5)
        
        self.play_button = tk.Button(control_frame, text="▶ 播放", command=self.toggle_play)
        self.play_button.pack(side=tk.LEFT, padx=2)
        
        tk.Button(control_frame, text="⟲ 重置", command=self.reset_animation).pack(side=tk.LEFT, padx=2)
        
        # 帧率控制
        fps_frame = tk.Frame(scrollable_frame)
        fps_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(fps_frame, text="帧率:").pack(side=tk.LEFT)
        self.fps_var = tk.IntVar(value=12)
        fps_spinbox = tk.Spinbox(fps_frame, from_=1, to=60, textvariable=self.fps_var,
                                width=5, command=self.on_fps_change)
        fps_spinbox.pack(side=tk.LEFT, padx=5)
        tk.Label(fps_frame, text="FPS").pack(side=tk.LEFT)
        
        # 当前帧信息
        self.frame_info_label = tk.Label(scrollable_frame, text="帧: 0/0", fg='green')
        self.frame_info_label.pack(pady=5)
        
        ttk.Separator(scrollable_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # 缩放调节控制
        tk.Label(scrollable_frame, text="动画缩放调节", font=("Arial", 12, "bold")).pack(pady=5)
        
        # 显示参考精灵选项
        tk.Checkbutton(scrollable_frame, text="显示参考精灵", variable=self.show_reference).pack(anchor=tk.W, padx=10)
        
        # 缩放比例控制
        scale_frame = tk.Frame(scrollable_frame)
        scale_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(scale_frame, text="缩放比例:").pack(side=tk.LEFT)
        self.animation_scale_var = tk.DoubleVar(value=1.0)
        animation_scale_slider = tk.Scale(scale_frame, from_=0.1, to=5.0, resolution=0.1,
                                         orient=tk.HORIZONTAL, variable=self.animation_scale_var,
                                         command=self.on_animation_scale_change)
        animation_scale_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 缩放信息显示
        self.scale_info_label = tk.Label(scrollable_frame, text="当前缩放: 1.0x")
        self.scale_info_label.pack(pady=2)
        
        # 重置缩放按钮
        tk.Button(scrollable_frame, text="重置缩放", command=self.reset_animation_scale).pack(pady=5)
        
        ttk.Separator(scrollable_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # 动作组管理
        tk.Label(scrollable_frame, text="动作组管理", font=("Arial", 12, "bold")).pack(pady=5)
        
        # 添加动作组
        add_frame = tk.Frame(scrollable_frame)
        add_frame.pack(fill=tk.X, pady=5)
        
        self.action_name_var = tk.StringVar()
        tk.Entry(add_frame, textvariable=self.action_name_var, width=15).pack(side=tk.LEFT)
        tk.Button(add_frame, text="添加动作", command=self.add_action_group).pack(side=tk.LEFT, padx=5)
        
        # 动作组列表
        list_frame = tk.Frame(scrollable_frame, height=200)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        list_frame.pack_propagate(False)
        
        action_scrollbar = Scrollbar(list_frame)
        action_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.action_listbox = tk.Listbox(list_frame, yscrollcommand=action_scrollbar.set)
        self.action_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        action_scrollbar.config(command=self.action_listbox.yview)
        
        self.action_listbox.bind('<<ListboxSelect>>', self.on_action_select)
        
        # 动作操作按钮
        action_btn_frame = tk.Frame(scrollable_frame)
        action_btn_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(action_btn_frame, text="预览动作", command=self.preview_action).pack(side=tk.LEFT, padx=2)
        tk.Button(action_btn_frame, text="删除动作", command=self.delete_action).pack(side=tk.LEFT, padx=2)
        
        ttk.Separator(scrollable_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # 导出按钮
        tk.Button(scrollable_frame, text="导出动画配置", command=self.export_animation_config,
                 bg='#4CAF50', fg='white', padx=20, pady=5).pack(pady=10)
        
    def load_atlas_list(self):
        """加载图集列表"""
        self.atlas_listbox.delete(0, tk.END)
        
        output_dir = os.path.join(os.path.dirname(__file__), 'output')
        if not os.path.exists(output_dir):
            return
        
        # 扫描output目录
        for folder in os.listdir(output_dir):
            folder_path = os.path.join(output_dir, folder)
            if os.path.isdir(folder_path):
                metadata_path = os.path.join(folder_path, 'metadata.json')
                if os.path.exists(metadata_path):
                    # 读取metadata确认是图集
                    try:
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if data.get('export_mode') == 'atlas':
                                self.atlas_listbox.insert(tk.END, folder)
                    except:
                        pass
    
    def on_atlas_select(self, event):
        """选择图集"""
        selection = self.atlas_listbox.curselection()
        if not selection:
            return
        
        folder_name = self.atlas_listbox.get(selection[0])
        self.load_atlas(folder_name)
    
    def load_atlas(self, folder_name):
        """加载图集"""
        output_dir = os.path.join(os.path.dirname(__file__), 'output')
        folder_path = os.path.join(output_dir, folder_name)
        
        # 读取metadata
        metadata_path = os.path.join(folder_path, 'metadata.json')
        with open(metadata_path, 'r', encoding='utf-8') as f:
            self.metadata = json.load(f)
        
        # 加载图集图片
        atlas_file = self.metadata['atlas_file']
        atlas_path = os.path.join(folder_path, atlas_file)
        self.current_atlas_path = folder_path
        
        self.atlas_image = Image.open(atlas_path)
        self.parse_frames()
        self.display_atlas()
        
        # 更新信息
        self.atlas_info_label.config(
            text=f"图集: {self.metadata['atlas_name']} | "
            f"尺寸: {self.metadata['atlas_size']['width']}×{self.metadata['atlas_size']['height']} | "
            f"精灵: {self.metadata['sprite_count']}个"
        )
        
        # 清空选择和动作组
        self.selected_frames = []
        self.action_groups = {}
        self.action_listbox.delete(0, tk.END)
        
    def parse_frames(self):
        """解析帧信息"""
        self.frames = []
        
        # 从metadata中获取精灵信息
        sprites = self.metadata['sprites']
        padding = self.metadata.get('sprite_padding', 0)
        
        # 计算行列信息
        for i, sprite in enumerate(sprites):
            frame = sprite['frame']
            
            # 根据位置计算行列（假设规则排列）
            col = i  # 简化处理，可以根据实际位置计算
            row = 0
            
            if frame['width'] > 0 and frame['height'] > 0:
                col = frame['x'] // (frame['width'] + padding) if frame['width'] > 0 else 0
                row = frame['y'] // (frame['height'] + padding) if frame['height'] > 0 else 0
            
            frame_info = FrameInfo(
                index=i,
                row=row,
                col=col,
                x=frame['x'],
                y=frame['y'],
                width=frame['width'],
                height=frame['height']
            )
            self.frames.append(frame_info)
    
    def display_atlas(self):
        """显示图集"""
        if not self.atlas_image:
            return
        
        # 创建带网格的图集副本
        display_img = self.atlas_image.copy()
        draw = ImageDraw.Draw(display_img)
        
        # 绘制网格和选中框
        for frame in self.frames:
            color = 'red' if frame.selected else 'yellow'
            width = 2 if frame.selected else 1
            
            # 绘制边框
            draw.rectangle(
                [frame.x, frame.y, frame.x + frame.width - 1, frame.y + frame.height - 1],
                outline=color, width=width
            )
            
            # 绘制索引号
            draw.text((frame.x + 2, frame.y + 2), str(frame.index), fill='white')
        
        # 缩放显示
        scale = self.scale_factor
        display_width = int(display_img.width * scale)
        display_height = int(display_img.height * scale)
        display_img = display_img.resize((display_width, display_height), Image.NEAREST)
        
        # 更新画布
        self.atlas_photo = ImageTk.PhotoImage(display_img)
        self.atlas_canvas.delete("all")
        self.atlas_canvas.create_image(0, 0, anchor=tk.NW, image=self.atlas_photo)
        self.atlas_canvas.config(scrollregion=self.atlas_canvas.bbox("all"))
    
    def on_scale_change(self, value):
        """缩放变化"""
        self.scale_factor = float(value)
        if self.atlas_image:
            self.display_atlas()
    
    def on_canvas_click(self, event):
        """画布点击"""
        if not self.frames:
            return
        
        # 转换坐标
        canvas_x = self.atlas_canvas.canvasx(event.x)
        canvas_y = self.atlas_canvas.canvasy(event.y)
        
        real_x = canvas_x / self.scale_factor
        real_y = canvas_y / self.scale_factor
        
        # 查找点击的帧
        clicked_frame = None
        for frame in self.frames:
            if (frame.x <= real_x <= frame.x + frame.width and
                frame.y <= real_y <= frame.y + frame.height):
                clicked_frame = frame
                break
        
        if clicked_frame:
            # 清除之前的选择
            for frame in self.frames:
                frame.selected = False
            self.selected_frames = []
            
            # 选中点击的帧
            clicked_frame.selected = True
            self.selected_frames = [clicked_frame]
            
            self.display_atlas()
    
    def on_canvas_ctrl_click(self, event):
        """Ctrl+点击多选"""
        if not self.frames:
            return
        
        # 转换坐标
        canvas_x = self.atlas_canvas.canvasx(event.x)
        canvas_y = self.atlas_canvas.canvasy(event.y)
        
        real_x = canvas_x / self.scale_factor
        real_y = canvas_y / self.scale_factor
        
        # 查找点击的帧
        for frame in self.frames:
            if (frame.x <= real_x <= frame.x + frame.width and
                frame.y <= real_y <= frame.y + frame.height):
                # 切换选择状态
                frame.selected = not frame.selected
                if frame.selected and frame not in self.selected_frames:
                    self.selected_frames.append(frame)
                elif not frame.selected and frame in self.selected_frames:
                    self.selected_frames.remove(frame)
                break
        
        self.display_atlas()
    
    def on_canvas_drag(self, event):
        """拖拽选择"""
        # 这里可以实现框选功能，暂时简化处理
        pass
    
    def toggle_play(self):
        """切换播放状态"""
        if not self.selected_frames:
            messagebox.showwarning("警告", "请先选择要预览的帧")
            return
        
        self.is_playing = not self.is_playing
        
        if self.is_playing:
            self.play_button.config(text="⏸ 暂停")
            self.current_frame_index = 0
            self.animate()
        else:
            self.play_button.config(text="▶ 播放")
    
    def animate(self):
        """动画循环"""
        if not self.is_playing or not self.selected_frames:
            return
        
        # 计算帧间隔
        frame_interval = 1000 / self.frame_rate  # 毫秒
        
        current_time = time.time() * 1000
        if current_time - self.last_frame_time >= frame_interval:
            # 显示当前帧
            self.show_preview_frame(self.current_frame_index)
            
            # 更新帧索引
            self.current_frame_index = (self.current_frame_index + 1) % len(self.selected_frames)
            self.last_frame_time = current_time
            
            # 更新信息
            self.frame_info_label.config(
                text=f"帧: {self.current_frame_index + 1}/{len(self.selected_frames)}"
            )
        
        # 继续动画循环
        if self.is_playing:
            self.root.after(10, self.animate)
    
    def show_preview_frame(self, index):
        """显示预览帧（支持分层显示）"""
        if not self.selected_frames or index >= len(self.selected_frames):
            return
        
        # 清空画布
        self.preview_canvas.delete("all")
        
        # 获取画布尺寸
        canvas_width = self.preview_canvas.winfo_width()
        canvas_height = self.preview_canvas.winfo_height()
        
        # 基础放大倍数
        base_preview_scale = 4
        
        # 1. 显示参考精灵（如果有）
        if self.show_reference.get() and self.selected_reference_sprite:
            ref_sprite = self.selected_reference_sprite
            
            # 参考精灵使用固定的放大倍数
            ref_width = ref_sprite.width * base_preview_scale
            ref_height = ref_sprite.height * base_preview_scale
            ref_sprite_scaled = ref_sprite.resize((ref_width, ref_height), Image.NEAREST)
            
            # 半透明处理（可选）
            ref_sprite_scaled = ref_sprite_scaled.convert('RGBA')
            # ref_sprite_scaled.putalpha(128)  # 半透明
            
            self.reference_photo = ImageTk.PhotoImage(ref_sprite_scaled)
            
            # 居中显示参考精灵
            ref_x = (canvas_width - ref_width) // 2
            ref_y = (canvas_height - ref_height) // 2
            
            self.preview_canvas.create_image(ref_x, ref_y, anchor=tk.NW, 
                                            image=self.reference_photo, tags="reference")
        
        # 2. 显示动画精灵（应用缩放）
        frame = self.selected_frames[index]
        
        # 从图集中裁剪精灵
        sprite = self.atlas_image.crop((
            frame.x, frame.y,
            frame.x + frame.width,
            frame.y + frame.height
        ))
        
        # 应用动画缩放
        animation_preview_scale = base_preview_scale * self.animation_scale
        preview_width = int(sprite.width * animation_preview_scale)
        preview_height = int(sprite.height * animation_preview_scale)
        
        if preview_width > 0 and preview_height > 0:
            sprite = sprite.resize((preview_width, preview_height), Image.NEAREST)
            
            # 显示在预览画布上
            self.preview_photo = ImageTk.PhotoImage(sprite)
            
            # 居中显示动画精灵
            x = (canvas_width - preview_width) // 2
            y = (canvas_height - preview_height) // 2
            
            self.preview_canvas.create_image(x, y, anchor=tk.NW, 
                                            image=self.preview_photo, tags="animation")
    
    def reset_animation(self):
        """重置动画"""
        self.is_playing = False
        self.play_button.config(text="▶ 播放")
        self.current_frame_index = 0
        self.frame_info_label.config(text="帧: 0/0")
        self.preview_canvas.delete("all")
    
    def on_fps_change(self):
        """帧率变化"""
        self.frame_rate = self.fps_var.get()
    
    def add_action_group(self):
        """添加动作组"""
        if not self.selected_frames:
            messagebox.showwarning("警告", "请先选择帧")
            return
        
        name = self.action_name_var.get().strip()
        if not name:
            messagebox.showwarning("警告", "请输入动作名称")
            return
        
        if name in self.action_groups:
            messagebox.showwarning("警告", "动作名称已存在")
            return
        
        # 创建动作组
        action = ActionGroup(name)
        for frame in sorted(self.selected_frames, key=lambda f: f.index):
            action.frames.append((frame.row, frame.col))
        
        self.action_groups[name] = action
        
        # 更新列表
        self.action_listbox.insert(tk.END, f"{name} ({action.frame_count}帧)")
        
        # 清空输入
        self.action_name_var.set("")
        
        messagebox.showinfo("成功", f"已添加动作组: {name}")
    
    def on_action_select(self, event):
        """选择动作组"""
        selection = self.action_listbox.curselection()
        if not selection:
            return
        
        # 获取动作名称
        text = self.action_listbox.get(selection[0])
        action_name = text.split(' (')[0]
        
        if action_name in self.action_groups:
            action = self.action_groups[action_name]
            
            # 清除当前选择
            for frame in self.frames:
                frame.selected = False
            self.selected_frames = []
            
            # 选中动作组的帧
            for row, col in action.frames:
                for frame in self.frames:
                    if frame.row == row and frame.col == col:
                        frame.selected = True
                        self.selected_frames.append(frame)
            
            self.display_atlas()
    
    def preview_action(self):
        """预览选中的动作"""
        selection = self.action_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请选择一个动作组")
            return
        
        # 触发动作选择
        self.on_action_select(None)
        
        # 开始播放
        if self.selected_frames:
            self.is_playing = False
            self.toggle_play()
    
    def delete_action(self):
        """删除动作组"""
        selection = self.action_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请选择要删除的动作组")
            return
        
        text = self.action_listbox.get(selection[0])
        action_name = text.split(' (')[0]
        
        if messagebox.askyesno("确认", f"确定要删除动作组 '{action_name}' 吗？"):
            del self.action_groups[action_name]
            self.action_listbox.delete(selection[0])
    
    def export_animation_config(self):
        """导出动画配置"""
        if not self.action_groups:
            messagebox.showwarning("警告", "没有可导出的动作组")
            return
        
        if not self.metadata:
            messagebox.showwarning("警告", "请先加载图集")
            return
        
        # 准备导出数据
        layout_info = self.metadata.get('layout_info', {})
        
        # 计算实际的行列数
        max_row = max((f.row for f in self.frames), default=0) + 1
        max_col = max((f.col for f in self.frames), default=0) + 1
        
        # 获取精灵尺寸（假设所有精灵尺寸相同）
        sprite_width = layout_info.get('average_sprite_width', 0)
        sprite_height = layout_info.get('average_sprite_height', 0)
        
        if self.frames:
            sprite_width = self.frames[0].width
            sprite_height = self.frames[0].height
        
        export_data = {
            "sprite_info": {
                "name": self.metadata.get('atlas_name', 'sprite'),
                "width": sprite_width,
                "height": sprite_height,
                "scale_ratio": self.animation_scale  # 添加缩放比例
            },
            "layout": {
                "columns": max_col,
                "rows": max_row,
                "padding": self.metadata.get('sprite_padding', 0)
            },
            "actions": {},
            "frame_rate": self.frame_rate
        }
        
        # 添加动作组
        for name, action in self.action_groups.items():
            export_data["actions"][name] = {
                "frames": action.frames,
                "frame_count": action.frame_count
            }
        
        # 保存到文件（移除时间戳）
        filename = "animation_config.json"
        filepath = os.path.join(self.current_atlas_path, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        messagebox.showinfo("导出成功", 
                          f"动画配置已导出\n"
                          f"文件: {filename}\n"
                          f"包含 {len(self.action_groups)} 个动作组\n"
                          f"缩放比例: {self.animation_scale:.1f}x")
    
    def load_reference_atlas(self):
        """加载参考图集"""
        file_path = filedialog.askopenfilename(
            title="选择参考图集",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # 加载图集图片
            self.reference_atlas = Image.open(file_path)
            
            # 尝试加载对应的metadata
            dir_path = os.path.dirname(file_path)
            metadata_path = os.path.join(dir_path, 'metadata.json')
            
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    self.reference_metadata = json.load(f)
                    
                # 解析精灵列表
                self.reference_sprites = self.reference_metadata.get('sprites', [])
                
                # 更新列表框
                self.reference_listbox.delete(0, tk.END)
                for i, sprite in enumerate(self.reference_sprites):
                    name = sprite.get('name', f'sprite_{i}')
                    self.reference_listbox.insert(tk.END, name)
                
                # 更新信息标签
                atlas_name = self.reference_metadata.get('atlas_name', '未知')
                sprite_count = len(self.reference_sprites)
                self.reference_info_label.config(
                    text=f"参考: {atlas_name} ({sprite_count}个精灵)",
                    fg='blue'
                )
            else:
                # 没有metadata，作为单张图片处理
                self.reference_metadata = None
                self.reference_sprites = []
                self.reference_listbox.delete(0, tk.END)
                self.reference_listbox.insert(tk.END, "完整图片")
                
                self.reference_info_label.config(
                    text=f"参考图片已加载",
                    fg='blue'
                )
                
        except Exception as e:
            messagebox.showerror("错误", f"无法加载参考图集: {str(e)}")
    
    def on_reference_select(self, event):
        """选择参考精灵"""
        selection = self.reference_listbox.curselection()
        if not selection or not self.reference_atlas:
            return
        
        index = selection[0]
        
        if self.reference_sprites and index < len(self.reference_sprites):
            # 从metadata中获取精灵信息
            sprite_info = self.reference_sprites[index]
            frame = sprite_info.get('frame')
            if frame:
                # 裁剪精灵
                self.selected_reference_sprite = self.reference_atlas.crop((
                    frame['x'], frame['y'],
                    frame['x'] + frame['width'],
                    frame['y'] + frame['height']
                ))
            else:
                self.selected_reference_sprite = self.reference_atlas
        else:
            # 使用完整图片
            self.selected_reference_sprite = self.reference_atlas
        
        # 刷新预览
        if self.selected_frames:
            self.show_preview_frame(self.current_frame_index)
    
    def on_animation_scale_change(self, value):
        """动画缩放变化"""
        self.animation_scale = float(value)
        self.scale_info_label.config(text=f"当前缩放: {self.animation_scale:.1f}x")
        
        # 刷新预览
        if self.selected_frames:
            self.show_preview_frame(self.current_frame_index)
    
    def reset_animation_scale(self):
        """重置动画缩放"""
        self.animation_scale = 1.0
        self.animation_scale_var.set(1.0)
        self.scale_info_label.config(text="当前缩放: 1.0x")
        
        # 刷新预览
        if self.selected_frames:
            self.show_preview_frame(self.current_frame_index)


def main():
    root = tk.Tk()
    app = AnimationPreviewApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()