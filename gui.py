import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Canvas, Scrollbar, Frame, Label
from PIL import Image, ImageTk
import os
from sprite_cutter import SpriteCutter, SpriteInfo
from typing import List, Optional


class SpriteSheetGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("精灵表切割工具")
        self.root.geometry("1200x800")
        
        self.cutter = SpriteCutter()
        self.current_image = None
        self.display_image = None
        self.canvas_image_id = None
        self.scale_factor = 1.0
        self.sprites = []
        self.manual_selections = []
        self.current_selection = None
        self.selection_start = None
        self.preview_labels = []
        self.sprite_rectangles = {}
        self.selected_count = 0
        
        self.setup_ui()
        
    def setup_ui(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="打开图片", command=self.load_image)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        left_panel = tk.Frame(main_frame, width=320)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        # 添加滚动条到左侧面板
        left_canvas = Canvas(left_panel, width=300)
        left_scrollbar = Scrollbar(left_panel, orient="vertical", command=left_canvas.yview)
        scrollable_frame = tk.Frame(left_canvas)
        
        # 创建窗口并设置宽度
        canvas_window = left_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        
        def configure_scroll_region(event=None):
            # 更新滚动区域
            left_canvas.configure(scrollregion=left_canvas.bbox("all"))
            # 设置frame宽度匹配canvas
            left_canvas.itemconfig(canvas_window, width=left_canvas.winfo_width())
        
        scrollable_frame.bind("<Configure>", configure_scroll_region)
        left_canvas.bind("<Configure>", lambda e: left_canvas.itemconfig(canvas_window, width=e.width))
        
        left_canvas.configure(yscrollcommand=left_scrollbar.set)
        
        # 添加鼠标滚轮支持
        def on_mousewheel(event):
            left_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        left_canvas.bind_all("<MouseWheel>", on_mousewheel)
        
        left_scrollbar.pack(side="right", fill="y")
        left_canvas.pack(side="left", fill="both", expand=True)
        
        self.setup_control_panel(scrollable_frame)
        
        right_panel = tk.Frame(main_frame)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        canvas_frame = tk.Frame(right_panel)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        h_scrollbar = Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        v_scrollbar = Scrollbar(canvas_frame, orient=tk.VERTICAL)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.canvas = Canvas(canvas_frame, bg='gray', 
                            xscrollcommand=h_scrollbar.set,
                            yscrollcommand=v_scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        h_scrollbar.config(command=self.canvas.xview)
        v_scrollbar.config(command=self.canvas.yview)
        
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        
        preview_frame = tk.Frame(right_panel, height=150)
        preview_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        tk.Label(preview_frame, text="切割预览：", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        self.preview_container = tk.Frame(preview_frame, bg='white', relief=tk.SUNKEN, bd=1)
        self.preview_container.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.preview_scroll = tk.Frame(self.preview_container)
        self.preview_scroll.pack(side=tk.LEFT, fill=tk.X)
    
    def setup_control_panel(self, parent):
        tk.Label(parent, text="精灵表切割工具", font=("Arial", 14, "bold")).pack(pady=10)
        
        load_btn = tk.Button(parent, text="选择图片", command=self.load_image, 
                           bg='#4CAF50', fg='white', padx=20, pady=5)
        load_btn.pack(pady=5)
        
        self.image_info_label = tk.Label(parent, text="未加载图片", fg='gray')
        self.image_info_label.pack(pady=5)
        
        ttk.Separator(parent, orient='horizontal').pack(fill=tk.X, pady=10)
        
        tk.Label(parent, text="切割模式", font=("Arial", 12, "bold")).pack(pady=5)
        
        self.cut_mode = tk.StringVar(value="grid_size")
        modes = [
            ("按尺寸网格切割", "grid_size"),
            ("按数量网格切割", "grid_count"),
            ("自动检测切割", "auto"),
            ("手动框选切割", "manual")
        ]
        
        for text, value in modes:
            tk.Radiobutton(parent, text=text, variable=self.cut_mode, 
                         value=value, command=self.on_mode_change).pack(anchor=tk.W, padx=20)
        
        ttk.Separator(parent, orient='horizontal').pack(fill=tk.X, pady=10)
        
        self.params_frame = tk.Frame(parent)
        self.params_frame.pack(fill=tk.X, pady=5)
        
        self.setup_grid_size_params()
        
        ttk.Separator(parent, orient='horizontal').pack(fill=tk.X, pady=10)
        
        cut_btn = tk.Button(parent, text="执行切割", command=self.execute_cut,
                          bg='#2196F3', fg='white', padx=20, pady=5)
        cut_btn.pack(pady=5)
        
        self.result_label = tk.Label(parent, text="", fg='green')
        self.result_label.pack(pady=5)
        
        ttk.Separator(parent, orient='horizontal').pack(fill=tk.X, pady=10)
        
        tk.Label(parent, text="精灵选择", font=("Arial", 12, "bold")).pack(pady=5)
        
        selection_frame = tk.Frame(parent)
        selection_frame.pack(fill=tk.X, pady=5)
        
        # 使用ttk.Button避免macOS按钮显示问题
        ttk.Button(selection_frame, text="全选", command=self.select_all_sprites).pack(side=tk.LEFT, padx=2)
        ttk.Button(selection_frame, text="取消全选", command=self.deselect_all_sprites).pack(side=tk.LEFT, padx=2)
        ttk.Button(selection_frame, text="反选", command=self.invert_selection).pack(side=tk.LEFT, padx=2)
        
        self.selection_info_label = tk.Label(parent, text="未选择精灵", fg='gray')
        self.selection_info_label.pack(pady=5)
        
        ttk.Separator(parent, orient='horizontal').pack(fill=tk.X, pady=10)
        
        tk.Label(parent, text="导出选项", font=("Arial", 12, "bold")).pack(pady=5)
        
        self.export_mode = tk.StringVar(value="individual")
        tk.Radiobutton(parent, text="单图导出", variable=self.export_mode,
                      value="individual", command=self.on_export_mode_change).pack(anchor=tk.W, padx=20)
        tk.Radiobutton(parent, text="图集导出", variable=self.export_mode,
                      value="atlas", command=self.on_export_mode_change).pack(anchor=tk.W, padx=20)
        
        # 通用导出参数
        self.trim_var = tk.BooleanVar(value=True)
        tk.Checkbutton(parent, text="去除透明边缘", variable=self.trim_var).pack(anchor=tk.W, padx=20)
        
        # 导出格式选择
        format_frame = tk.Frame(parent)
        format_frame.pack(fill=tk.X, pady=2, padx=20)
        tk.Label(format_frame, text="导出格式:").pack(side=tk.LEFT)
        self.export_format_var = tk.StringVar(value="png")
        format_menu = ttk.Combobox(format_frame, textvariable=self.export_format_var, 
                                   values=["png", "jpg", "webp"], width=8, state="readonly")
        format_menu.pack(side=tk.LEFT, padx=5)
        
        # 创建参数容器框架
        self.export_params_frame = tk.Frame(parent)
        self.export_params_frame.pack(fill=tk.X, pady=5, padx=20)
        
        # 初始化为单图导出参数
        self.setup_individual_export_params()
        
        export_btn = tk.Button(parent, text="导出选中精灵", command=self.export_selected_sprites,
                             bg='#FF9800', fg='white', padx=20, pady=5)
        export_btn.pack(pady=5)
        
        scale_frame = tk.Frame(parent)
        scale_frame.pack(fill=tk.X, pady=10)
        tk.Label(scale_frame, text="缩放:").pack(side=tk.LEFT)
        scale_slider = tk.Scale(scale_frame, from_=0.1, to=3.0, resolution=0.1,
                               orient=tk.HORIZONTAL, command=self.on_scale_change)
        scale_slider.set(1.0)
        scale_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def setup_grid_size_params(self):
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        
        tk.Label(self.params_frame, text="参数设置：").pack(anchor=tk.W)
        
        size_frame = tk.Frame(self.params_frame)
        size_frame.pack(fill=tk.X, pady=2)
        tk.Label(size_frame, text="单元格宽度:").pack(side=tk.LEFT)
        self.cell_width_var = tk.StringVar(value="32")
        tk.Entry(size_frame, textvariable=self.cell_width_var, width=10).pack(side=tk.LEFT)
        
        size_frame2 = tk.Frame(self.params_frame)
        size_frame2.pack(fill=tk.X, pady=2)
        tk.Label(size_frame2, text="单元格高度:").pack(side=tk.LEFT)
        self.cell_height_var = tk.StringVar(value="32")
        tk.Entry(size_frame2, textvariable=self.cell_height_var, width=10).pack(side=tk.LEFT)
        
        padding_frame = tk.Frame(self.params_frame)
        padding_frame.pack(fill=tk.X, pady=2)
        tk.Label(padding_frame, text="水平间距:").pack(side=tk.LEFT)
        self.padding_x_var = tk.StringVar(value="0")
        tk.Entry(padding_frame, textvariable=self.padding_x_var, width=10).pack(side=tk.LEFT)
        
        padding_frame2 = tk.Frame(self.params_frame)
        padding_frame2.pack(fill=tk.X, pady=2)
        tk.Label(padding_frame2, text="垂直间距:").pack(side=tk.LEFT)
        self.padding_y_var = tk.StringVar(value="0")
        tk.Entry(padding_frame2, textvariable=self.padding_y_var, width=10).pack(side=tk.LEFT)
        
        offset_frame = tk.Frame(self.params_frame)
        offset_frame.pack(fill=tk.X, pady=2)
        tk.Label(offset_frame, text="X偏移:").pack(side=tk.LEFT)
        self.offset_x_var = tk.StringVar(value="0")
        tk.Entry(offset_frame, textvariable=self.offset_x_var, width=10).pack(side=tk.LEFT)
        
        offset_frame2 = tk.Frame(self.params_frame)
        offset_frame2.pack(fill=tk.X, pady=2)
        tk.Label(offset_frame2, text="Y偏移:").pack(side=tk.LEFT)
        self.offset_y_var = tk.StringVar(value="0")
        tk.Entry(offset_frame2, textvariable=self.offset_y_var, width=10).pack(side=tk.LEFT)
    
    def setup_grid_count_params(self):
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        
        tk.Label(self.params_frame, text="参数设置：").pack(anchor=tk.W)
        
        row_frame = tk.Frame(self.params_frame)
        row_frame.pack(fill=tk.X, pady=2)
        tk.Label(row_frame, text="行数:").pack(side=tk.LEFT)
        self.rows_var = tk.StringVar(value="4")
        tk.Entry(row_frame, textvariable=self.rows_var, width=10).pack(side=tk.LEFT)
        
        col_frame = tk.Frame(self.params_frame)
        col_frame.pack(fill=tk.X, pady=2)
        tk.Label(col_frame, text="列数:").pack(side=tk.LEFT)
        self.cols_var = tk.StringVar(value="4")
        tk.Entry(col_frame, textvariable=self.cols_var, width=10).pack(side=tk.LEFT)
        
        padding_frame = tk.Frame(self.params_frame)
        padding_frame.pack(fill=tk.X, pady=2)
        tk.Label(padding_frame, text="水平间距:").pack(side=tk.LEFT)
        self.padding_x_var = tk.StringVar(value="0")
        tk.Entry(padding_frame, textvariable=self.padding_x_var, width=10).pack(side=tk.LEFT)
        
        padding_frame2 = tk.Frame(self.params_frame)
        padding_frame2.pack(fill=tk.X, pady=2)
        tk.Label(padding_frame2, text="垂直间距:").pack(side=tk.LEFT)
        self.padding_y_var = tk.StringVar(value="0")
        tk.Entry(padding_frame2, textvariable=self.padding_y_var, width=10).pack(side=tk.LEFT)
    
    def setup_auto_params(self):
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        
        tk.Label(self.params_frame, text="参数设置：").pack(anchor=tk.W)
        
        size_frame = tk.Frame(self.params_frame)
        size_frame.pack(fill=tk.X, pady=2)
        tk.Label(size_frame, text="最小精灵尺寸:").pack(side=tk.LEFT)
        self.min_size_var = tk.StringVar(value="8")
        tk.Entry(size_frame, textvariable=self.min_size_var, width=10).pack(side=tk.LEFT)
        
        threshold_frame = tk.Frame(self.params_frame)
        threshold_frame.pack(fill=tk.X, pady=2)
        tk.Label(threshold_frame, text="透明度阈值:").pack(side=tk.LEFT)
        self.threshold_var = tk.StringVar(value="10")
        tk.Entry(threshold_frame, textvariable=self.threshold_var, width=10).pack(side=tk.LEFT)
    
    def setup_manual_params(self):
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        
        tk.Label(self.params_frame, text="手动框选模式").pack(anchor=tk.W)
        tk.Label(self.params_frame, text="在图片上拖动鼠标框选精灵", fg='gray').pack(anchor=tk.W)
        
        btn_frame = tk.Frame(self.params_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(btn_frame, text="清除选区", command=self.clear_selections).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="撤销上一个", command=self.undo_last_selection).pack(side=tk.LEFT, padx=2)
        
        self.selection_count_label = tk.Label(self.params_frame, text="已选择: 0 个区域")
        self.selection_count_label.pack(anchor=tk.W, pady=5)
    
    def on_mode_change(self):
        mode = self.cut_mode.get()
        if mode == "grid_size":
            self.setup_grid_size_params()
        elif mode == "grid_count":
            self.setup_grid_count_params()
        elif mode == "auto":
            self.setup_auto_params()
        elif mode == "manual":
            self.setup_manual_params()
            self.manual_selections = []
            self.redraw_canvas()
    
    def load_image(self):
        file_path = filedialog.askopenfilename(
            title="选择精灵表图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.gif *.bmp"), ("所有文件", "*.*")]
        )
        
        if file_path:
            try:
                self.current_image = self.cutter.load_image(file_path)
                self.image_info_label.config(
                    text=f"图片: {os.path.basename(file_path)}\n尺寸: {self.current_image.width} x {self.current_image.height}",
                    fg='black'
                )
                self.display_image_on_canvas()
                self.sprites = []
                self.manual_selections = []
                self.clear_preview()
            except Exception as e:
                messagebox.showerror("错误", f"无法加载图片: {str(e)}")
    
    def display_image_on_canvas(self):
        if not self.current_image:
            return
        
        display_width = int(self.current_image.width * self.scale_factor)
        display_height = int(self.current_image.height * self.scale_factor)
        
        resized = self.current_image.resize((display_width, display_height), Image.Resampling.NEAREST)
        self.display_image = ImageTk.PhotoImage(resized)
        
        self.canvas.delete("all")
        self.canvas_image_id = self.canvas.create_image(0, 0, anchor=tk.NW, image=self.display_image)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        
        self.redraw_canvas()
    
    def on_scale_change(self, value):
        self.scale_factor = float(value)
        if self.current_image:
            self.display_image_on_canvas()
    
    def on_canvas_click(self, event):
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        if self.sprites and self.cut_mode.get() != "manual":
            clicked_sprite = self.find_sprite_at_position(canvas_x, canvas_y)
            if clicked_sprite:
                clicked_sprite.selected = not clicked_sprite.selected
                self.update_selection_count()
                self.redraw_canvas()
                return
        
        if self.cut_mode.get() == "manual" and self.current_image:
            self.selection_start = (canvas_x, canvas_y)
            
            if self.current_selection:
                self.canvas.delete(self.current_selection)
            
            self.current_selection = self.canvas.create_rectangle(
                canvas_x, canvas_y, canvas_x, canvas_y,
                outline='red', width=2, dash=(5, 5)
            )
    
    def on_canvas_drag(self, event):
        if self.cut_mode.get() == "manual" and self.selection_start and self.current_selection:
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            
            self.canvas.coords(self.current_selection,
                             self.selection_start[0], self.selection_start[1],
                             canvas_x, canvas_y)
    
    def on_canvas_release(self, event):
        if self.cut_mode.get() == "manual" and self.selection_start and self.current_selection:
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            
            x1 = min(self.selection_start[0], canvas_x) / self.scale_factor
            y1 = min(self.selection_start[1], canvas_y) / self.scale_factor
            x2 = max(self.selection_start[0], canvas_x) / self.scale_factor
            y2 = max(self.selection_start[1], canvas_y) / self.scale_factor
            
            width = x2 - x1
            height = y2 - y1
            
            if width > 5 and height > 5:
                self.manual_selections.append((int(x1), int(y1), int(width), int(height)))
                self.selection_count_label.config(text=f"已选择: {len(self.manual_selections)} 个区域")
                
                rect_id = self.canvas.create_rectangle(
                    x1 * self.scale_factor, y1 * self.scale_factor,
                    x2 * self.scale_factor, y2 * self.scale_factor,
                    outline='green', width=2, tags="selection"
                )
            
            self.canvas.delete(self.current_selection)
            self.current_selection = None
            self.selection_start = None
    
    def clear_selections(self):
        self.manual_selections = []
        self.canvas.delete("selection")
        self.selection_count_label.config(text="已选择: 0 个区域")
    
    def undo_last_selection(self):
        if self.manual_selections:
            self.manual_selections.pop()
            self.redraw_canvas()
            self.selection_count_label.config(text=f"已选择: {len(self.manual_selections)} 个区域")
    
    def redraw_canvas(self):
        self.canvas.delete("selection")
        self.canvas.delete("sprite_rect")
        self.sprite_rectangles.clear()
        
        for x, y, w, h in self.manual_selections:
            self.canvas.create_rectangle(
                x * self.scale_factor, y * self.scale_factor,
                (x + w) * self.scale_factor, (y + h) * self.scale_factor,
                outline='green', width=2, tags="selection"
            )
        
        for sprite in self.sprites:
            x1 = sprite.x * self.scale_factor
            y1 = sprite.y * self.scale_factor
            x2 = (sprite.x + sprite.width) * self.scale_factor
            y2 = (sprite.y + sprite.height) * self.scale_factor
            
            color = 'red' if sprite.selected else 'blue'
            width = 3 if sprite.selected else 1
            
            rect_id = self.canvas.create_rectangle(
                x1, y1, x2, y2,
                outline=color, width=width, tags="sprite_rect"
            )
            self.sprite_rectangles[rect_id] = sprite
    
    def execute_cut(self):
        if not self.current_image:
            messagebox.showwarning("警告", "请先加载图片")
            return
        
        try:
            mode = self.cut_mode.get()
            
            if mode == "grid_size":
                self.sprites = self.cutter.grid_cut_by_size(
                    int(self.cell_width_var.get()),
                    int(self.cell_height_var.get()),
                    int(self.padding_x_var.get()),
                    int(self.padding_y_var.get()),
                    int(self.offset_x_var.get()),
                    int(self.offset_y_var.get())
                )
            elif mode == "grid_count":
                self.sprites = self.cutter.grid_cut_by_count(
                    int(self.rows_var.get()),
                    int(self.cols_var.get()),
                    int(self.padding_x_var.get()),
                    int(self.padding_y_var.get())
                )
            elif mode == "auto":
                self.sprites = self.cutter.auto_cut(
                    int(self.min_size_var.get()),
                    int(self.threshold_var.get())
                )
            elif mode == "manual":
                if not self.manual_selections:
                    messagebox.showwarning("警告", "请先框选精灵区域")
                    return
                self.sprites = self.cutter.manual_cut(self.manual_selections)
            
            self.result_label.config(text=f"成功切割 {len(self.sprites)} 个精灵")
            self.selected_count = 0
            self.update_selection_count()
            self.redraw_canvas()
            self.show_preview()
            
        except ValueError as e:
            messagebox.showerror("错误", f"参数错误: {str(e)}")
        except Exception as e:
            messagebox.showerror("错误", f"切割失败: {str(e)}")
    
    def show_preview(self):
        self.clear_preview()
        
        if not self.sprites:
            return
        
        max_previews = 10
        sprites_to_show = self.sprites[:max_previews]
        
        for i, sprite in enumerate(sprites_to_show):
            if sprite.image:
                thumb_size = (80, 80)
                thumbnail = sprite.image.copy()
                thumbnail.thumbnail(thumb_size, Image.Resampling.LANCZOS)
                
                photo = ImageTk.PhotoImage(thumbnail)
                
                frame = tk.Frame(self.preview_scroll, relief=tk.RAISED, bd=1)
                frame.pack(side=tk.LEFT, padx=2, pady=2)
                
                label = tk.Label(frame, image=photo)
                label.image = photo
                label.pack()
                
                info_label = tk.Label(frame, text=f"{sprite.name}\n{sprite.width}x{sprite.height}",
                                    font=("Arial", 8))
                info_label.pack()
                
                self.preview_labels.append(label)
        
        if len(self.sprites) > max_previews:
            more_label = tk.Label(self.preview_scroll, 
                                text=f"... 还有 {len(self.sprites) - max_previews} 个",
                                font=("Arial", 10), fg='gray')
            more_label.pack(side=tk.LEFT, padx=10)
    
    def clear_preview(self):
        for widget in self.preview_scroll.winfo_children():
            widget.destroy()
        self.preview_labels = []
    
    def on_export_mode_change(self):
        mode = self.export_mode.get()
        if mode == "individual":
            self.setup_individual_export_params()
        else:
            self.setup_atlas_export_params()
    
    def setup_individual_export_params(self):
        # 清除现有参数
        for widget in self.export_params_frame.winfo_children():
            widget.destroy()
        
        tk.Label(self.export_params_frame, text="单图导出参数:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        # 文件命名模式
        naming_frame = tk.Frame(self.export_params_frame)
        naming_frame.pack(fill=tk.X, pady=2)
        tk.Label(naming_frame, text="命名前缀:").pack(side=tk.LEFT)
        self.name_prefix_var = tk.StringVar(value="sprite_")
        tk.Entry(naming_frame, textvariable=self.name_prefix_var, width=15).pack(side=tk.LEFT)
    
    def setup_atlas_export_params(self):
        # 清除现有参数
        for widget in self.export_params_frame.winfo_children():
            widget.destroy()
        
        tk.Label(self.export_params_frame, text="图集导出参数:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        
        # 图集间距
        padding_frame = tk.Frame(self.export_params_frame)
        padding_frame.pack(fill=tk.X, pady=2)
        tk.Label(padding_frame, text="精灵间距:").pack(side=tk.LEFT)
        self.atlas_padding_var = tk.StringVar(value="2")
        tk.Entry(padding_frame, textvariable=self.atlas_padding_var, width=5).pack(side=tk.LEFT)
        tk.Label(padding_frame, text="像素").pack(side=tk.LEFT)
        
        # 最大图集尺寸
        size_frame = tk.Frame(self.export_params_frame)
        size_frame.pack(fill=tk.X, pady=2)
        tk.Label(size_frame, text="最大宽度:").pack(side=tk.LEFT)
        self.max_atlas_width_var = tk.StringVar(value="2048")
        tk.Entry(size_frame, textvariable=self.max_atlas_width_var, width=8).pack(side=tk.LEFT)
        tk.Label(size_frame, text="像素").pack(side=tk.LEFT)
        
        # 排列算法选择
        algo_frame = tk.Frame(self.export_params_frame)
        algo_frame.pack(fill=tk.X, pady=2)
        tk.Label(algo_frame, text="排列方式:").pack(side=tk.LEFT)
        self.pack_algorithm_var = tk.StringVar(value="row")
        ttk.Combobox(algo_frame, textvariable=self.pack_algorithm_var,
                    values=["row", "square", "tight"], width=10, state="readonly").pack(side=tk.LEFT)
        
        # 图集文件名
        name_frame = tk.Frame(self.export_params_frame)
        name_frame.pack(fill=tk.X, pady=2)
        tk.Label(name_frame, text="图集名称:").pack(side=tk.LEFT)
        self.atlas_name_var = tk.StringVar(value="atlas")
        tk.Entry(name_frame, textvariable=self.atlas_name_var, width=15).pack(side=tk.LEFT)
    
    def find_sprite_at_position(self, x, y):
        real_x = x / self.scale_factor
        real_y = y / self.scale_factor
        
        for sprite in self.sprites:
            if (sprite.x <= real_x <= sprite.x + sprite.width and 
                sprite.y <= real_y <= sprite.y + sprite.height):
                return sprite
        return None
    
    def update_selection_count(self):
        self.selected_count = sum(1 for s in self.sprites if s.selected)
        if self.selected_count > 0:
            self.selection_info_label.config(
                text=f"已选择 {self.selected_count}/{len(self.sprites)} 个精灵",
                fg='green'
            )
        else:
            self.selection_info_label.config(text="未选择精灵", fg='gray')
    
    def select_all_sprites(self):
        for sprite in self.sprites:
            sprite.selected = True
        self.update_selection_count()
        self.redraw_canvas()
    
    def deselect_all_sprites(self):
        for sprite in self.sprites:
            sprite.selected = False
        self.update_selection_count()
        self.redraw_canvas()
    
    def invert_selection(self):
        for sprite in self.sprites:
            sprite.selected = not sprite.selected
        self.update_selection_count()
        self.redraw_canvas()
    
    def export_selected_sprites(self):
        if not self.sprites:
            messagebox.showwarning("警告", "没有可导出的精灵")
            return
        
        selected_count = sum(1 for s in self.sprites if s.selected)
        if selected_count == 0:
            messagebox.showwarning("警告", "请先选择要导出的精灵")
            return
        
        output_dir = filedialog.askdirectory(title="选择导出目录")
        if not output_dir:
            return
        
        try:
            mode = self.export_mode.get()
            format = self.export_format_var.get()
            
            # 获取导出参数
            if mode == 'atlas':
                if not hasattr(self, 'atlas_padding_var'):
                    self.setup_atlas_export_params()
                atlas_padding = int(self.atlas_padding_var.get())
                atlas_name = self.atlas_name_var.get() if hasattr(self, 'atlas_name_var') else 'atlas'
                name_prefix = 'sprite_'
            else:
                if not hasattr(self, 'name_prefix_var'):
                    self.setup_individual_export_params()
                atlas_padding = 2
                atlas_name = 'atlas'
                name_prefix = self.name_prefix_var.get() if hasattr(self, 'name_prefix_var') else 'sprite_'
            
            metadata = self.cutter.export_selected_sprites(
                output_dir,
                format=format,
                trim=self.trim_var.get(),
                mode=mode,
                atlas_padding=atlas_padding,
                atlas_name=atlas_name,
                name_prefix=name_prefix
            )
            
            if mode == 'individual':
                messagebox.showinfo("成功", 
                                  f"成功导出 {metadata['sprite_count']} 个精灵到:\n{output_dir}")
            else:
                atlas_size = metadata['atlas_size']
                messagebox.showinfo("成功", 
                                  f"成功导出图集 ({atlas_size['width']}x{atlas_size['height']}):\n"
                                  f"包含 {metadata['sprite_count']} 个精灵\n"
                                  f"保存到: {output_dir}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")
    
    def export_sprites(self):
        if not self.sprites:
            messagebox.showwarning("警告", "没有可导出的精灵")
            return
        
        output_dir = filedialog.askdirectory(title="选择导出目录")
        if not output_dir:
            return
        
        try:
            metadata = self.cutter.export_sprites(
                output_dir,
                format='png',
                trim=self.trim_var.get()
            )
            
            messagebox.showinfo("成功", 
                              f"成功导出 {metadata['sprite_count']} 个精灵到:\n{output_dir}")
        except Exception as e:
            messagebox.showerror("错误", f"导出失败: {str(e)}")