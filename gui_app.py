import os
import sys
import re
import threading
import subprocess
import locale
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

# 设置外观和主题
ctk.set_appearance_mode("Dark")  # 默认深色模式
ctk.set_default_color_theme("blue")  # 主题色为蓝色


class PDFProcessorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # 窗口属性设置
        self.title("PDF OCR Pipeline for NotebookLM")
        self.geometry("850x700")
        self.minsize(800, 600)

        # 状态变量
        self.process = None
        self.is_running = False
        self.log_encoding = locale.getpreferredencoding(False) or 'utf-8'

        # 布局权重配置
        self.grid_rowconfigure(2, weight=1)  # 让日志区域自适应拉伸
        self.grid_columnconfigure(0, weight=1)

        # ==========================================
        # 1. 顶部 Header 区域 (Header Frame)
        # ==========================================
        self.header_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="📄 PDF OCR for NotebookLM", 
            font=ctk.CTkFont(family="Microsoft YaHei", size=24, weight="bold")
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        self.subtitle_label = ctk.CTkLabel(
            self.header_frame, 
            text="批量转换科研论文 PDF，物理清理与语义增强，专为 RAG 与 NotebookLM 检索优化。",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color="gray"
        )
        self.subtitle_label.grid(row=1, column=0, sticky="w", pady=(5, 0))

        # 主题切换下拉框
        self.theme_menu = ctk.CTkOptionMenu(
            self.header_frame,
            values=["Dark", "Light", "System"],
            command=self.change_theme,
            width=100
        )
        self.theme_menu.grid(row=0, column=1, rowspan=2, sticky="e", padx=5)
        self.theme_menu.set("Dark")

        # ==========================================
        # 2. 中部设置与控制区 (Config & Control Frame)
        # ==========================================
        self.control_frame = ctk.CTkFrame(self, corner_radius=10)
        self.control_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.control_frame.grid_columnconfigure(1, weight=1)

        # 文件夹路径选择
        self.path_label = ctk.CTkLabel(
            self.control_frame, 
            text="目标 PDF 文件夹：", 
            font=ctk.CTkFont(family="Microsoft YaHei", size=13, weight="bold")
        )
        self.path_label.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")

        self.path_entry = ctk.CTkEntry(
            self.control_frame, 
            placeholder_text="请选择或输入要处理的 PDF 文件夹路径...",
            font=ctk.CTkFont(size=12)
        )
        self.path_entry.grid(row=0, column=1, padx=(0, 10), pady=(15, 5), sticky="ew")

        self.browse_btn = ctk.CTkButton(
            self.control_frame, 
            text="浏览文件夹", 
            width=100,
            command=self.browse_folder,
            font=ctk.CTkFont(family="Microsoft YaHei", size=12)
        )
        self.browse_btn.grid(row=0, column=2, padx=(0, 15), pady=(15, 5), sticky="e")

        # 进度指示器
        self.progress_label = ctk.CTkLabel(
            self.control_frame, 
            text="状态：等待开始", 
            font=ctk.CTkFont(family="Microsoft YaHei", size=12)
        )
        self.progress_label.grid(row=1, column=0, columnspan=2, padx=15, pady=(10, 5), sticky="w")

        self.progress_bar = ctk.CTkProgressBar(self.control_frame)
        self.progress_bar.grid(row=2, column=0, columnspan=3, padx=15, pady=(5, 15), sticky="ew")
        self.progress_bar.set(0)

        # 操作按钮区
        self.buttons_frame = ctk.CTkFrame(self.control_frame, fg_color="transparent")
        self.buttons_frame.grid(row=3, column=0, columnspan=3, padx=15, pady=(0, 15), sticky="ew")
        self.buttons_frame.grid_columnconfigure(0, weight=1)
        self.buttons_frame.grid_columnconfigure(1, weight=1)

        self.start_btn = ctk.CTkButton(
            self.buttons_frame, 
            text="▶ 开始批量处理", 
            fg_color="#1f85de", 
            hover_color="#1970bd",
            command=self.start_processing,
            font=ctk.CTkFont(family="Microsoft YaHei", size=14, weight="bold")
        )
        self.start_btn.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.stop_btn = ctk.CTkButton(
            self.buttons_frame, 
            text="⏹ 终止任务", 
            fg_color="#d9534f", 
            hover_color="#c9302c",
            command=self.stop_processing,
            state="disabled",
            font=ctk.CTkFont(family="Microsoft YaHei", size=14, weight="bold")
        )
        self.stop_btn.grid(row=0, column=1, padx=(10, 0), sticky="ew")

        # ==========================================
        # 3. 底部实时日志输出终端 (Log Frame)
        # ==========================================
        self.log_frame = ctk.CTkFrame(self, corner_radius=10)
        self.log_frame.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="nsew")
        self.log_frame.grid_rowconfigure(1, weight=1)
        self.log_frame.grid_columnconfigure(0, weight=1)

        self.log_title = ctk.CTkLabel(
            self.log_frame, 
            text="💻 实时处理日志 (Console Output)：", 
            font=ctk.CTkFont(family="Microsoft YaHei", size=12, weight="bold")
        )
        self.log_title.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")

        # 文本框用于显示实时控制台输出
        self.log_textbox = ctk.CTkTextbox(
            self.log_frame, 
            font=ctk.CTkFont(family="Courier New", size=11),
            text_color="#a8ffb2",  # 护眼绿字符，契合终端风格
            fg_color="#181818"    # 黑色背景
        )
        self.log_textbox.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")

    def change_theme(self, new_theme):
        ctk.set_appearance_mode(new_theme)

    def browse_folder(self):
        folder = filedialog.askdirectory(title="请选择包含 PDF 文件的文件夹")
        if folder:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, os.path.normpath(folder))

    def start_processing(self):
        folder_path = self.path_entry.get().strip()
        if not folder_path:
            messagebox.showwarning("提示", "请先选择或输入 PDF 文件夹路径！")
            return

        if not os.path.isdir(folder_path):
            messagebox.showerror("错误", "所选路径不是一个有效的文件夹，请重新选择！")
            return

        # 重置 UI 状态
        self.log_textbox.delete("1.0", tk.END)
        self.progress_bar.set(0)
        self.progress_label.configure(text="状态：正在初始化...")
        
        # 禁用输入及开始按钮，启用停止按钮
        self.path_entry.configure(state="disabled")
        self.browse_btn.configure(state="disabled")
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.theme_menu.configure(state="disabled")
        
        self.is_running = True

        # 开启后台工作线程
        threading.Thread(
            target=self.run_batch_processor, 
            args=(folder_path,), 
            daemon=True
        ).start()

    def run_batch_processor(self, folder_path):
        # 确定 batch_processor.py 的绝对路径
        script_dir = os.path.dirname(os.path.abspath(__file__))
        processor_script = os.path.join(script_dir, "batch_processor.py")

        if not os.path.exists(processor_script):
            self.root_safe_call(
                self.progress_label.configure, 
                text="错误：未找到核心处理脚本 batch_processor.py"
            )
            self.root_safe_call(self.reset_ui_after_job)
            messagebox.showerror("错误", f"未能在当前目录下找到 {processor_script} 脚本！")
            return

        # 在 Windows 环境下，通过 creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        # 允许我们后续使用 taskkill 干净地关闭整个子进程树
        cmd = [sys.executable, processor_script, folder_path]
        
        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=script_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
            
            # 用于累积部分字符防止截断乱码的缓冲区
            buffer = b''
            
            while True:
                # 逐字节读取以获得最即时的进度刷新
                byte = self.process.stdout.read(1)
                if not byte:
                    break
                
                buffer += byte
                try:
                    # 尝试用系统的首选编码（一般 Windows 是 GBK，如果是 Py 环境有些是 UTF-8）进行解码
                    text = buffer.decode(self.log_encoding)
                    self.root_safe_call(self.append_log, text)
                    self.parse_log_and_update_ui(text)
                    buffer = b''
                except UnicodeDecodeError:
                    # 进度条方块等字符可能是多字节，未接收完全时解码会报错，若缓冲区过大则强制替换解码
                    if len(buffer) > 16:
                        text = buffer.decode(self.log_encoding, errors='replace')
                        self.root_safe_call(self.append_log, text)
                        self.parse_log_and_update_ui(text)
                        buffer = b''
            
            # 等待进程退出
            self.process.wait()
            returncode = self.process.returncode

            # 处理退出状态
            if returncode == 0:
                self.root_safe_call(self.progress_label.configure, text="状态：✅ 处理完成！")
                self.root_safe_call(self.progress_bar.set, 1.0)
                messagebox.showinfo("完成", "所有 PDF 文档已成功处理完成！\n请查看 'NotebookLM_Ready' 文件夹。")
            elif returncode == -1 or not self.is_running:
                # 进程被强制杀死
                self.root_safe_call(self.progress_label.configure, text="状态：⏹ 任务已被终止。")
            else:
                self.root_safe_call(self.progress_label.configure, text=f"状态：❌ 处理失败，退出码: {returncode}")
                messagebox.showerror("错误", f"处理过程中发生错误，脚本非正常退出（退出码: {returncode}）！\n请查看日志了解详情。")

        except Exception as e:
            self.root_safe_call(self.append_log, f"\n[GUI Error]: {str(e)}\n")
            self.root_safe_call(self.progress_label.configure, text="状态：❌ 启动失败。")
            messagebox.showerror("启动失败", f"无法启动批处理进程：\n{str(e)}")
        
        finally:
            self.root_safe_call(self.reset_ui_after_job)

    def stop_processing(self):
        if not self.is_running:
            return

        if messagebox.askyesno("终止确认", "确定要终止当前正在运行的处理任务吗？\n这会强行结束当前 PDF 的 OCR 转换。"):
            self.is_running = False
            self.progress_label.configure(text="状态：⏳ 正在强行终止进程，请稍候...")
            
            # 终止子进程及其拉起的所有子进程 (如 marker_single)
            if self.process:
                try:
                    # 使用 Windows taskkill /F /T 杀死整个子进程树
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                except Exception as e:
                    self.append_log(f"\n[Kill Process Error]: {str(e)}\n")
                    # 后备方案
                    try:
                        self.process.kill()
                    except:
                        pass
            
            self.reset_ui_after_job()
            self.progress_label.configure(text="状态：⏹ 任务已手动终止。")

    def append_log(self, text):
        # 实时追加日志并自动滚动到最后一行
        self.log_textbox.insert("end", text)
        self.log_textbox.see("end")

    def parse_log_and_update_ui(self, text):
        # 通过正则解析 batch_processor.py 输出的当前进度
        # 例子: [1/10] [🔄 准备中] paper_name.pdf
        # 或者是: [2/10] [✅ 已完成] paper_name.pdf
        match = re.search(r'\[(\d+)/(\d+)\]\s+(\[[^\]]+\])\s+(.*)', text)
        if match:
            current = int(match.group(1))
            total = int(match.group(2))
            status = match.group(3)
            filename = match.group(4).strip()
            
            # 更新进度条 (防止除以 0)
            val = (current - 1) / total if total > 0 else 0
            # 限制在 0 到 1 之间
            val = max(0.0, min(1.0, val))
            
            display_text = f"状态：处理中 ({current}/{total}) - {filename} {status}"
            self.root_safe_call(self.progress_bar.set, val)
            self.root_safe_call(self.progress_label.configure, text=display_text)
            return

        # 匹配细分步骤，例如：---> [2/3] Cleaning & [3/3] Readying PDF...
        detail_match = re.search(r'--->\s*\[(\d+)/(\d+)\]\s*(.*)', text)
        if detail_match:
            step_num = detail_match.group(1)
            step_total = detail_match.group(2)
            step_desc = detail_match.group(3).strip()
            
            current_status = self.progress_label.cget("text")
            # 在原有主进度的基础上追加细分步骤
            base_status = current_status.split(" - 子步骤")[0]
            display_text = f"{base_status} - 子步骤: [{step_num}/{step_total}] {step_desc}"
            self.root_safe_call(self.progress_label.configure, text=display_text)

    def reset_ui_after_job(self):
        self.is_running = False
        self.process = None
        self.path_entry.configure(state="normal")
        self.browse_btn.configure(state="normal")
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.theme_menu.configure(state="normal")

    def root_safe_call(self, func, *args, **kwargs):
        # 确保跨线程的 UI 更改安全地在 Tkinter 主线程中运行
        if threading.current_thread() is threading.main_thread():
            func(*args, **kwargs)
        else:
            self.after(0, lambda: func(*args, **kwargs))


if __name__ == "__main__":
    app = PDFProcessorApp()
    app.mainloop()
