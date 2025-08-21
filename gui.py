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
        
        left_panel = tk.Frame(main_frame, width=300)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        left_panel.pack_propagate(False)
        
        self.setup_control_panel(left_panel)
        
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
        
        tk.Label(parent, text="导出选项", font=("Arial", 12, "bold")).pack(pady=5)
        
        self.trim_var = tk.BooleanVar(value=True)
        tk.Checkbutton(parent, text="去除透明边缘", variable=self.trim_var).pack(anchor=tk.W, padx=20)
        
        export_btn = tk.Button(parent, text="导出精灵", command=self.export_sprites,
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
        if self.cut_mode.get() == "manual" and self.current_image:
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            
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
        
        for x, y, w, h in self.manual_selections:
            self.canvas.create_rectangle(
                x * self.scale_factor, y * self.scale_factor,
                (x + w) * self.scale_factor, (y + h) * self.scale_factor,
                outline='green', width=2, tags="selection"
            )
        
        for sprite in self.sprites:
            self.canvas.create_rectangle(
                sprite.x * self.scale_factor, sprite.y * self.scale_factor,
                (sprite.x + sprite.width) * self.scale_factor,
                (sprite.y + sprite.height) * self.scale_factor,
                outline='blue', width=1, tags="sprite_rect"
            )
    
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