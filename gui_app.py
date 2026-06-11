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
        # 强制界面与子进程使用 utf-8 交互，完美兼容所有 Emoji
        self.log_encoding = 'utf-8'
        self._pending_cr = False
        self._last_was_cr = False
        self._last_prefix = ""

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
            font=ctk.CTkFont(family="Microsoft YaHei", size=16, weight="bold")
        )
        self.path_label.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")

        self.path_entry = ctk.CTkEntry(
            self.control_frame, 
            placeholder_text="请选择或输入要处理的 PDF 文件夹路径...",
            font=ctk.CTkFont(family="Microsoft YaHei", size=15)
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
            font=ctk.CTkFont(family="Microsoft YaHei", size=15, weight="bold")
        )
        self.log_title.grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")

        # 文本框用于显示实时控制台输出
        self.log_textbox = ctk.CTkTextbox(
            self.log_frame, 
            font=ctk.CTkFont(family="Consolas", size=14),
            text_color="#FFFFFF",  # 白色字符，契合终端观感
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
        # 确定运行环境。如果在 PyInstaller 打包环境 (sys.frozen) 中运行：
        if getattr(sys, 'frozen', False):
            # sys.executable 指向 gui_app.exe，其同级目录即为程序运行目录
            script_dir = os.path.dirname(sys.executable)
            python_exe = "python"
        else:
            # 正常 Python 运行环境
            script_dir = os.path.dirname(os.path.abspath(__file__))
            python_exe = sys.executable

        processor_script = os.path.join(script_dir, "batch_processor.py")

        if not os.path.exists(processor_script):
            self.root_safe_call(
                self.progress_label.configure, 
                text="错误：未找到核心处理脚本 batch_processor.py"
            )
            self.root_safe_call(self.reset_ui_after_job)
            messagebox.showerror(
                "错误", 
                f"未能在当前目录下找到 {processor_script} 脚本！\n\n请确保 batch_processor.py 与 gui_app 处于相同的目录下。"
            )
            return

        # 在 Windows 环境下，通过 creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        # 允许我们后续使用 taskkill 干净地关闭整个子进程树
        cmd = [python_exe, processor_script, folder_path]
        
        # 复制当前环境变量，并强制子进程 stdout 使用 utf-8 编码，彻底解决 Emoji 导致的 UnicodeEncodeError
        process_env = os.environ.copy()
        process_env["PYTHONIOENCODING"] = "utf-8"
        
        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=script_dir,
                env=process_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | 0x08000000  # CREATE_NO_WINDOW 隐藏控制台
            )
            
            # 用于累积部分字符防止截断乱码的字节缓冲区
            buffer = b''
            # 用于累积整行的字符串缓冲区
            log_line_buffer = ""
            
            def process_decoded_text(decoded_text):
                nonlocal log_line_buffer
                for char in decoded_text:
                    if char == '\n':
                        if self._pending_cr:
                            # 遇到了 \r\n，当作一个普通的 \n 行处理，丢弃独立 \r 的标记
                            self._pending_cr = False
                        
                        if log_line_buffer.strip():
                            self.parse_log_and_update_ui(log_line_buffer)
                        self.root_safe_call(self.smart_append_log, log_line_buffer, '\n')
                        log_line_buffer = ""
                    elif char == '\r':
                        if self._pending_cr:
                            # 遇到了连续的 \r，提交上一个被搁置的行
                            if log_line_buffer.strip():
                                self.parse_log_and_update_ui(log_line_buffer)
                            self.root_safe_call(self.smart_append_log, log_line_buffer, '\r')
                            log_line_buffer = ""
                        self._pending_cr = True
                    else:
                        if self._pending_cr:
                            # 说明上一个是个孤立的 \r
                            self._pending_cr = False
                            if log_line_buffer.strip():
                                self.parse_log_and_update_ui(log_line_buffer)
                            self.root_safe_call(self.smart_append_log, log_line_buffer, '\r')
                            log_line_buffer = ""
                        log_line_buffer += char

            while True:
                byte = self.process.stdout.read(1)
                if not byte:
                    # 流结束，如果还有没提交的内容
                    if log_line_buffer or self._pending_cr:
                        self.root_safe_call(self.smart_append_log, log_line_buffer, '\n')
                    break
                
                buffer += byte
                try:
                    text = buffer.decode(self.log_encoding)
                    process_decoded_text(text)
                    buffer = b''
                except UnicodeDecodeError:
                    if len(buffer) > 16:
                        text = buffer.decode(self.log_encoding, errors='replace')
                        process_decoded_text(text)
                        buffer = b''
            
            # 等待进程退出前，先获取对象，防止被强杀清理置空导致报错
            proc_obj = self.process
            if proc_obj:
                proc_obj.wait()
                returncode = proc_obj.returncode
            else:
                returncode = -1

            # 处理退出状态
            if returncode == 0:
                self.root_safe_call(self.progress_label.configure, text="状态：✅ 处理完成！")
                self.root_safe_call(self.progress_bar.set, 1.0)
                messagebox.showinfo("完成", "所有 PDF 文档已成功处理完成！\n请查看 'NotebookLM_Ready' 文件夹。")
            elif not self.is_running or returncode != 0:
                # 进程被强制杀死或异常退出
                self.root_safe_call(self.progress_label.configure, text="状态：⏹ 任务已被终止或失败。")
            
        except Exception as e:
            self.root_safe_call(self.append_log, f"\n[GUI Error]: {str(e)}\n")
            self.root_safe_call(self.progress_label.configure, text="状态：❌ 运行时发生异常。")
        
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

    def smart_append_log(self, text, end_char):
        # 智能追加日志，支持 tqdm 就地刷新，且保护不同任务历史不被覆盖
        if not text and end_char == '\n':
            self.log_textbox.insert("end", "\n")
            self._last_was_cr = False
            self.log_textbox.see("end")
            return
            
        # 提取前缀用于任务区分（前25个字符或以冒号分割）
        prefix = text.split(':')[0][:25] if text else ""
        
        # 判断是否应该原地刷新（前提：上一个是 \r，且当前行有前缀且前缀不变）
        if self._last_was_cr and self._last_prefix == prefix and prefix != "":
            self.log_textbox.delete("end-1c linestart", "end-1c")
            self.log_textbox.insert("end", text)
        else:
            if self._last_was_cr:
                # 给上一个被终端挂起的独立 \r 任务追加一个换行，保护其历史不被覆盖
                self.log_textbox.insert("end", "\n")
            if text:
                self.log_textbox.insert("end", text)
                
        if end_char == '\n':
            self.log_textbox.insert("end", "\n")
            self._last_was_cr = False
        elif end_char == '\r':
            self._last_was_cr = True
            
        self._last_prefix = prefix
        self.log_textbox.see("end")

    def parse_log_and_update_ui(self, text):
        # 通过正则解析 batch_processor.py 输出的当前进度
        match = re.search(r'\[(\d+)/(\d+)\]\s+(\[[^\]]+\])\s+(.*)', text)
        if match:
            current = int(match.group(1))
            total = int(match.group(2))
            status = match.group(3)
            filename = match.group(4).strip()
            
            # 截断过长的文件名防止截断左侧的关键信息，保留首尾
            if len(filename) > 35:
                filename = filename[:15] + "..." + filename[-17:]
            
            # 更新进度条 (防止除以 0)
            val = (current - 1) / total if total > 0 else 0
            # 限制在 0 到 1 之间
            val = max(0.0, min(1.0, val))
            
            display_text = f"状态：({current}/{total}) {status} - {filename}"
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
            
            if len(step_desc) > 20:
                step_desc = step_desc[:17] + "..."
                
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
