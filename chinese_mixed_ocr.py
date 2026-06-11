import os
import glob
import subprocess
import time
import sys

def process_mixed_chinese_ocr(input_folder):
    """
    针对以中文为主，包含数学公式、物理符号和英文专名的 PDF 进行 OCR 转换。
    保持大模型原始识别顺序，输出 Markdown。
    """
    # 1. 准备输出文件夹
    output_base_dir = os.path.join(input_folder, "Chinese_Mixed_Markdown")
    if not os.path.exists(output_base_dir):
        os.makedirs(output_base_dir)

    # 2. 获取 PDF 列表
    pdfs = glob.glob(os.path.join(input_folder, "*.pdf"))
    if not pdfs:
        print(f"在路径 {input_folder} 下未找到 PDF 文件。")
        return

    print(f"🚀 开始处理 {len(pdfs)} 个混合文档...")

    # 3. 环境配置 (尊重本地模型部署，强制离线模式)
    env_vars = {
        **os.environ,
        "HF_HUB_OFFLINE": "1",                       # 强制离线模式，直接加载本地已部署模型
        "MARKER_LANGUAGES": "zh,en",                 # 设置识别语言为中英混合
        "SURYA_LANGS": "zh,en",                      # 底层引擎语言设置
        "PYTORCH_CUDA_ALLOC_CONF": "max_split_size_mb:128", # 防止显存碎片化
        "VRAM_PER_GPU": "4",                          # 每块 GPU 分配的显存限制
        "SURYA_DET_BATCH_SIZE": "1"                   # 减小批处理大小以提升稳定性
    }

    for idx, pdf_path in enumerate(pdfs):
        filename = os.path.basename(pdf_path)
        print(f"\n" + "="*50)
        print(f"[{idx+1}/{len(pdfs)}] 正在解析: {filename}")
        print("="*50)
        
        start_time = time.time()

        # 4. 执行转换命令 (移除了 --langs 参数以适配 v1.x)
        cmd = [
            "marker_single",
            f'"{pdf_path}"',
            "--output_dir", f'"{output_base_dir}"'
        ]
        
        # 将列表转换为字符串命令
        full_cmd = " ".join(cmd)

        try:
            # 使用 shell=True 执行，以便正确处理 Windows 路径中的空格和环境变量
            process = subprocess.run(
                full_cmd, 
                env=env_vars, 
                shell=True, 
                check=True,
                capture_output=False # 直接在终端显示转换进度
            )
            
            elapsed = int(time.time() - start_time)
            print(f"\n[✅ 完成] {filename}")
            print(f"   ⏱️ 耗时: {elapsed}s")
            print(f"   📂 结果目录: {output_base_dir}")
            
        except subprocess.CalledProcessError as e:
            print(f"\n[❌ 出错] 无法处理 {filename}")
            print(f"   错误信息: {e}")

if __name__ == "__main__":
    # 支持命令行参数
    import argparse
    parser = argparse.ArgumentParser(description="中英混合+数学公式 PDF 识别工具")
    parser.add_argument("folder", help="PDF 文件夹路径")
    
    args = parser.parse_args()
    
    input_path = os.path.abspath(args.folder)
    if os.path.isdir(input_path):
        process_mixed_chinese_ocr(input_path)
    else:
        print(f"错误: '{input_path}' 不是有效的文件夹路径。")
