import os
import glob
import shutil
import subprocess
import time
import re
import hashlib
import locale
import signal
import threading
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# ============================================================
# 工具函数：文本安全清洗 (Safe Text Renderer)
# ============================================================

def safe_html_para(text):
    """
    将 OCR 文本转化为 ReportLab Paragraph 安全的 HTML。
    核心逻辑：转义所有尖括号以防标签不闭合导致崩溃，随后恢复少量的学术必须格式。
    """
    if not text:
        return ""
    # 1. 基础转义
    t = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    # 2. 启发式恢复部分学术格式 (如 OCR 误写的 _abc -> <sub>abc</sub>)
    # 此处保持最保守策略：只做基础转义，后续特定标题由脚本手动包裹。
    return t

def should_stitch(text_a, text_b):
    """
    判断 A 段 and B 段是否属于语义上的同一个段落。
    """
    a = re.sub(r'<(span|div|a|p)[^>]*>\s*</\1>', '', text_a).strip()
    b = re.sub(r'<(span|div|a|p)[^>]*>\s*</\1>', '', text_b).strip()
    if not a or not b:
        return False
    # A 结尾特征：字母、逗号、分号
    ends_incomplete = bool(re.search(r'[a-zA-Z,;]$', a))
    # B 开头特征：小写字母 OR 公式符号 $ (应对物理文献公式续接场景)
    starts_continuation = bool(re.match(r'^[a-z$]', b))
    return ends_incomplete and starts_continuation

# ============================================================
# PDF 构建与清理系统 (PDF Reconstruction System)
# ============================================================

def clean_and_build_pdf(md_path, output_pdf):
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    doc = SimpleDocTemplate(output_pdf, pagesize=letter,
                            rightMargin=50, leftMargin=50,
                            topMargin=50, bottomMargin=50)
    styles = getSampleStyleSheet()
    
    custom_style = ParagraphStyle('CustomBody', parent=styles['Normal'], fontSize=10, leading=14)
    caption_style = ParagraphStyle('CaptionStyle', parent=custom_style, fontName='Helvetica-Oblique', fontSize=9, leading=11, textColor='#444444')
    table_style = ParagraphStyle('TableStyle', parent=custom_style, fontName='Courier', fontSize=7, leading=9, wordWrap=None)

    # 1. 块级提取逻辑优化：正文用 \n\n 隔开，参考文献用 \n 隔开。我们先拆开，再由 should_stitch 缝合正文。
    initial_chunks = [b.strip() for b in content.split('\n\n') if b.strip()]
    raw_blocks = []
    for chunk in initial_chunks:
        # 如果是 Markdown 表格，必须作为一个整体处理，不能拆行
        if '|---' in chunk or '| :---' in chunk:
            raw_blocks.append(chunk)
        else:
            # 拆分参考文献等单换行连接的条目
            lines = [line.strip() for line in chunk.split('\n') if line.strip()]
            raw_blocks.extend(lines)

    figures_appendix = []
    main_body_blocks = []
    story = []
    md_folder = os.path.dirname(md_path)
    
    is_short_doc = (len(content) < 100000)
    unmatched_images = [] # 记录未匹配图注的图片文件名

    # 1. 主提取循环 (处理图片与图注)
    i = 0
    while i < len(raw_blocks):
        current_cleaned = re.sub(r'<(span|div|a|p)[^>]*>\s*</\1>', '', raw_blocks[i]).strip()
        if not current_cleaned:
            i += 1
            continue
            
        img_match = re.search(r'!\[(?P<alt>.*?)\]\((?P<path>.*?)\)', current_cleaned)
        if img_match:
            img_path = os.path.join(md_folder, img_match.group('path'))
            if not os.path.exists(img_path):
                i += 1
                continue
            
            alt_text = img_match.group('alt').strip()
            is_table = bool(re.search(r'table|tab', img_path, re.I) or re.search(r'table|tab', alt_text, re.I))
            
            if is_table or not is_short_doc:
                main_body_blocks.append(current_cleaned)
            else:
                found_caption = ""
                if i + 1 < len(raw_blocks):
                    cand_block = re.sub(r'<(span|div|a|p)[^>]*>\s*</\1>', '', raw_blocks[i+1]).strip()
                    first_word_m = re.search(r'[a-zA-Z]+', cand_block)
                    if first_word_m and 'fig' in first_word_m.group(0).lower():
                        found_caption = cand_block
                        i += 1
                        while i + 1 < len(raw_blocks):
                            if should_stitch(found_caption, raw_blocks[i+1]):
                                found_caption += " " + re.sub(r'<(span|div|a|p)[^>]*>\s*</\1>', '', raw_blocks[i+1]).strip()
                                i += 1
                            else:
                                break
                
                if not found_caption:
                    unmatched_images.append(os.path.basename(img_path))
                figures_appendix.append((img_path, found_caption))
        else:
            main_body_blocks.append(current_cleaned)
        i += 1

    # 3. 正文语义缝合
    final_main_blocks = []
    k = 0
    while k < len(main_body_blocks):
        stitched_text = main_body_blocks[k]
        while k + 1 < len(main_body_blocks):
            if should_stitch(stitched_text, main_body_blocks[k+1]):
                stitched_text += " " + main_body_blocks[k+1]
                k += 1
            else:
                break
        final_main_blocks.append(stitched_text)
        k += 1

    # 4. 构建 PDF Story
    if is_short_doc:
        if figures_appendix:
            story.append(Paragraph("<b>Data Figures & Captions</b>", styles['Heading1']))
            story.append(Spacer(1, 12))
            for img_path, caption in figures_appendix:
                try:
                    im = Image(img_path)
                    w, h = im.imageWidth, im.imageHeight
                    max_w, max_h = 5.5 * inch, 9.2 * inch
                    ratio = min(max_w/w, max_h/h)
                    im.drawWidth, im.drawHeight = w * ratio, h * ratio
                    story.append(im)
                    story.append(Spacer(1, 6))
                    if caption:
                        # 安全渲染 + 脚本自动外裹标签
                        safe_caption = safe_html_para(caption)
                        story.append(Paragraph(f"<i>Figure Caption: {safe_caption}</i>", caption_style))
                    story.append(Spacer(1, 24)) 
                except:
                    pass
            story.append(PageBreak())
        
        story.append(Paragraph("<b>Main Text</b>", styles['Heading1']))
        story.append(Spacer(1, 12))
        for block in final_main_blocks:
            safe_text = safe_html_para(block)
            is_md_table = '|' in block and ('|---' in block or '| :---' in block)
            if is_md_table:
                # 表格特殊处理：方块化渲染
                table_content = block.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                table_content = table_content.replace('\n', '<br/>').replace(' ', '&nbsp;')
                story.append(Paragraph(table_content, table_style))
            else:
                story.append(Paragraph(safe_text, custom_style))
            story.append(Spacer(1, 12))
    else:
        # 长文档流
        story.append(Paragraph("<b>Main Text (Full Document)</b>", styles['Heading1']))
        story.append(Spacer(1, 12))
        i = 0
        while i < len(final_main_blocks):
            block = final_main_blocks[i]
            img_m = re.search(r'!\[(?P<alt>.*?)\]\((?P<path>.*?)\)', block)
            if img_m:
                img_path = os.path.join(md_folder, img_m.group('path'))
                if os.path.exists(img_path):
                    try:
                        im = Image(img_path)
                        w, h = im.imageWidth, im.imageHeight
                        max_w, max_h = 5.5 * inch, 9.2 * inch
                        ratio = min(max_w/w, max_h/h)
                        im.drawWidth, im.drawHeight = w * ratio, h * ratio
                        story.append(im)
                        story.append(Spacer(1, 6))
                        final_legend = ""
                        if i + 1 < len(final_main_blocks):
                            cand_b = re.sub(r'<(span|div|a|p)[^>]*>\s*</\1>', '', final_main_blocks[i+1]).strip()
                            word_m = re.search(r'[a-zA-Z]+', cand_b)
                            if word_m and 'fig' in word_m.group(0).lower():
                                final_legend = cand_b
                                i += 1
                                while i + 1 < len(final_main_blocks):
                                    if should_stitch(final_legend, final_main_blocks[i+1]):
                                        final_legend += " " + final_main_blocks[i+1]
                                        i += 1
                                    else:
                                        break
                        if final_legend:
                            safe_leg = safe_html_para(final_legend)
                            story.append(Paragraph(f"<i>Figure Caption: {safe_leg}</i>", caption_style))
                        else:
                            unmatched_images.append(os.path.basename(img_path))
                        story.append(Spacer(1, 12))
                    except:
                        pass
            else:
                safe_text = safe_html_para(block)
                is_md_table = '|' in block and ('|---' in block or '| :---' in block)
                if is_md_table:
                    table_content = block.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    table_content = table_content.replace('\n', '<br/>').replace(' ', '&nbsp;')
                    story.append(Paragraph(table_content, table_style))
                elif safe_text:
                    story.append(Paragraph(safe_text, custom_style))
                    story.append(Spacer(1, 12))
            i += 1
            
    doc.build(story)
    if unmatched_images:
        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]
        unique_failed = sorted(list(set(unmatched_images)), key=natural_sort_key)
        print(f"       [⚠️] 注意：以下图片未匹配到符合 FIG-规则 的图注（可能是网页碎图片）：")
        print(f"           {', '.join(unique_failed)}")
        print(f"       [💡] 提示：若有效图块未抓取到图注（可能是排版混乱、图注跨段或 (a)(b)(c) 子图共用总图注），请人工在 MD 文件中将图注移动到对应图片引用 ( ![] ) 的下一段，并删除 'Fig.' 前的杂质字，保存后删除成品 PDF 重新运行即可。")

# ============================================================
# 批处理核心引擎
# ============================================================

def run_marker_with_stall_detection(cmd, stall_timeout=600):
    import locale
    last_activity = [time.time()]
    sys_enc = locale.getpreferredencoding(False) or 'utf-8'
    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    def output_reader():
        import sys
        buffer = b''
        try:
            while True:
                byte = proc.stdout.read(1)
                if not byte: break
                buffer += byte
                try:
                    text = buffer.decode('utf-8')
                    print(text, end="", flush=True)
                    buffer = b''
                    last_activity[0] = time.time()
                except UnicodeDecodeError:
                    # 进度条方块等字符可能由于读取时点问题产生碎片，我们增加重试耐心
                    if len(buffer) > 12: # 增加缓冲区限度，允许更多字节拼凑
                        try:
                            print(buffer.decode(sys_enc, 'replace'), end="", flush=True)
                        except:
                            pass
                        buffer = b''
                except: pass
        except: pass
    threading.Thread(target=output_reader, daemon=True).start()
    stall_phase_2 = 0
    stall_gpu_limit = 300 
    while proc.poll() is None:
        time.sleep(5)
        silence_duration = time.time() - last_activity[0]
        if silence_duration > stall_timeout:
            if stall_phase_2 == 0:
                print(f"\n       [⏰] 检测到输出静默（可能是正在进行最后的磁盘文件合并...）")
                stall_phase_2 = time.time()
            try:
                res = subprocess.run(['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'], capture_output=True, text=True, timeout=5)
                if res.returncode == 0:
                    gpu_val = int(res.stdout.strip().split('\n')[0])
                    elapsed = int(time.time() - stall_phase_2)
                    print(f"       [🔍] GPU: {gpu_val}% (后处理等待中 {elapsed}/{stall_gpu_limit}s)")
                    if gpu_val > 15:
                        print(f"       [✅] GPU 仍活跃，重置静默计时。")
                        last_activity[0] = time.time()
                        stall_phase_2 = 0
                        continue
            except: pass
            if (time.time() - stall_phase_2) > stall_gpu_limit:
                print(f"\n       [💀] 判定为真死锁，执行强行复位...")
                proc.send_signal(signal.CTRL_BREAK_EVENT)
                try:
                    proc.wait(10)
                except:
                    proc.kill()
                return -1
        else: stall_phase_2 = 0
    return proc.returncode

def process_directory(input_folder):
    pdfs = glob.glob(os.path.join(input_folder, "*.pdf"))
    output_dir = os.path.join(input_folder, "NotebookLM_Ready")
    cache_dir = os.path.join(input_folder, "Processing_Cache")
    
    if not os.path.exists(output_dir): os.makedirs(output_dir)
    if not os.path.exists(cache_dir): os.makedirs(cache_dir)
    
    for idx, pdf in enumerate(pdfs):
        filename = os.path.basename(pdf)
        orig_base = os.path.splitext(filename)[0]
        name_hash = hashlib.md5(orig_base.encode('utf-8', errors='ignore')).hexdigest()[:8]
        safe_base = "".join([c if c.isalnum() or c in (" ", "-", "_") else "_" for c in orig_base]).strip()[:70]
        safe_name = f"{safe_base}_{name_hash}"
        final_pdf = os.path.join(output_dir, f"{orig_base}_NotebookLM_Ready.pdf")
        md_folder = os.path.join(cache_dir, safe_name)
        
        # 强制打印每份文档的头部信息，确保序号不丢失
        status_tag = "[✅ 已完成]" if os.path.exists(final_pdf) else "[🔄 准备中]"
        print(f"\n{'='*70}\n[{idx+1}/{len(pdfs)}] {status_tag} {filename}\n{'='*70}")

        if os.path.exists(final_pdf):
            continue

        start_t = time.time()
        md_file = None
        if os.path.exists(md_folder):
            mds = glob.glob(os.path.join(md_folder, "*.md"))
            if mds:
                md_file = mds[0]
                print(f"       [📂] 发现缓存数据，直接执行 PDF 生成...")

        if not md_file:
            short_id = f"{safe_base[:30]}_{name_hash}"
            short_p = os.path.join(cache_dir, f"{short_id}.pdf")
            shutil.copy2(pdf, short_p)
            temp_md_folder = os.path.join(cache_dir, short_id)
            f_cmd = f'set HF_ENDPOINT="https://hf-mirror.com" && set PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128 && marker_single "{short_p}" --output_dir "{cache_dir}"'
            run_marker_with_stall_detection(f_cmd)
            if not os.path.exists(temp_md_folder):
                s_cmd = f'set HF_ENDPOINT="https://hf-mirror.com" && set VRAM_PER_GPU=4 && set SURYA_DET_BATCH_SIZE=1 && marker_single "{short_p}" --output_dir "{cache_dir}"'
                shutil.rmtree(temp_md_folder, ignore_errors=True)
                run_marker_with_stall_detection(s_cmd)
            if os.path.exists(temp_md_folder):
                shutil.rmtree(md_folder, ignore_errors=True)
                shutil.move(temp_md_folder, md_folder)
                mds = glob.glob(os.path.join(md_folder, "*.md"))
                if mds:
                    md_file = os.path.join(md_folder, f"{safe_name}.md")
                    os.rename(mds[0], md_file)
            try:
                os.remove(short_p)
            except:
                pass

        if md_file and os.path.exists(md_file):
            print(f"       ---> [2/3] Cleaning & [3/3] Readying PDF...")
            try:
                clean_and_build_pdf(md_file, final_pdf)
                print(f"       [✅ 成功] {int(time.time()-start_t)}s")
            except Exception as e:
                print(f"       [❌ 失败]: {str(e)}")
                # 仅在失败时按需创建文件夹
                try:
                    failed_dir = os.path.join(input_folder, "Failed_PDFs")
                    if not os.path.exists(failed_dir): os.makedirs(failed_dir)
                    shutil.copy2(pdf, os.path.join(failed_dir, filename))
                except:
                    pass
                continue

if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('folder')
    process_directory(p.parse_args().folder)
