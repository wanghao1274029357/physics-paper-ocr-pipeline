# ⚛️ Physics Paper OCR Pipeline (NotebookLM Edition)
### 物理论文 OCR 转换管线 (NotebookLM 专供版)

A specialized Python OCR pipeline optimized for converting complex physics research papers into high-fidelity PDFs specifically tailored for Google's **NotebookLM** and **Gemini 1.5**.

许多期刊原始 PDF 直接上传到 NotebookLM 时，由于多栏排版、复杂的公式混合以及背景水印，常会出现布局混乱、分栏错位或公式乱码等现象，极大影响 AI 的逻辑推理。本工具旨在通过本地高性能 OCR 重新排版，生成最适合 AI 阅读的 RAG 高保真文档。

---

## 🌟 Key Features / 核心特性

*   **FIG-Academic Rule (图注识别规则)**: Intelligently identifies and matches figure captions using standard academic keywords. Correctly groups multi-block captions split by page breaks.
    *   自动识别并提取图注。如果由于分页导致图注断裂，系统会自动将其重新缝合并恢复完整语义。
*   **Semantic Stitching Engine (语义拼接引擎)**: Automatically heals paragraphs and captions split by layout shifts or mathematical formulas (`$`).
    *   针对物理论文中由于图片插空或 LaTeX 公式（如 `$ \omega $`）导致的语义断断续续，系统会自动进行拼接处理，还原流畅语流。
*   **Dual-Phase Stall Detection (双阶段死锁监测)**: Monitors output silence and real-time GPU activity (`nvidia-smi`) to prevent deadlocks during high-load processing.
    *   实时监测 GPU 负载，防止在处理高密集度公式或图像时发生“假死锁”，确保无人值守批量完成整个文件夹。
*   **Failed File Auto-Recovery (失败文件自动归档)**: Automatically moves corrupted or crashed PDFs into a specialized folder to ensure unattended batch processing continuity.
    *   **失败自动归档**：若遇到损坏或导致崩溃的 PDF，脚本会自动将其拷贝至 `Failed_PDFs/` 文件夹，确保整个批处理流程不会中断。
*   **Local Hardware Powered (本地算力驱动)**: All OCR tasks are performed on your **local GPU**. Processing speed depends on your local hardware specifications (VRAM and CUDA efficiency).
    *   所有识别任务完全依靠本地显卡执行，处理速度高度取决于你本地显卡的性能。
*   **Layout Strategy (布局策略)**:
    *   **Short Docs (<100k chars)**: Automatically moves figures and captions to a dedicated appendix to avoid interrupting the main semantic flow for RAG.
    *   **Long Docs**: Preserves in-situ placement with semantic italicized captions.
    *   根据文章长度自动调节布局：短文档将图文分离（图注置顶）以获得极致检索精度，长文档则保留原位排版。

---

## 🧠 OCR Implementation & Model Architecture / OCR 实现与模型架构

The pipeline leverages **marker-pdf**'s high-fidelity inference engine, which combines several SOTA (State-of-the-Art) multimodal models:

本转换管线基于 **marker-pdf** 的高保真推理引擎，深度整合了多项学术级 SOTA 模型：

1.  **Surya (Layout & OCR)**: High-precision line ordering and text extraction specifically tailored for complex multi-column academic layouts.
    *   **Surya (布局与 OCR)**: 提供高精度行排序与文字提取，能够完美处理物理期刊中常见的错位多栏布局。
2.  **Texify (LaTeX & Formulas)**: A specialized model designed to transform complex mathematical notation into clean, editable Markdown LaTeX syntax.
    *   **Texify (公式识别)**: 专攻学术论文中极其复杂的物理/数学公式，将其原汁原味地转换为标准的 LaTeX 语法。
3.  **Segmenter (Heuristic Block Recognition)**: Intelligently isolates data figures, tables, and headers/footers from the main semantic body to ensure superior RAG performance in NotebookLM.
    *   **分段模型 (区块识别)**: 智能识别并剥离图片、表格以及页眉页脚，确保正文语义流的纯净，从而极大提升 NotebookLM 的检索增强生成 (RAG) 幻觉抑制能力。

*Note: These models are automatically downloaded from Hugging Face during the first execution. / 注：上述模型将在首次运行时从 Hugging Face 自动下载。*

---

## 🚀 Quick Start / 快速上手

### 1. Prerequisites / 环境依赖
Ensure you have an NVIDIA GPU with latest drivers, and install the base dependencies:
确保装有 NVIDIA 显卡驱动，一键安装依赖：

```bash
pip install reportlab marker-pdf
```

### 3. Usage / 使用方法
Run the batch processor on your target folder containing research PDFs:

```bash
python batch_processor.py "C:\Path\To\Your\Papers"
```

---

## 🛠️ Manual Intervention Guide / 人工干预指南

由于学术期刊排版千奇百怪，为了应对极个别复杂情况，你可以通过以下工作流手动修正结果：

### 场景 A：PDF 中出现了无用的网页元素图片（如按钮、导航条）
1.  进入 `Processing_Cache/` 文件夹，找到对应文档的子目录。
2.  手动删除多余的 `.jpeg` 图片文件。
3.  删除 `NotebookLM_Ready/` 中生成的对应 PDF 文件。
4.  **重新运行脚本**。脚本会提示 `[📂] 发现缓存数据`，并根据你清理后的缓存重新渲染干净的 PDF。

### 场景 B：有效图块未成功抓取图注
如果终端提示某张有效图片未匹配到图注：
1.  这可能说明该文献排版极端混乱，或者是由于 **“一图多报”** 现象（一张大图被 OCR 拆分为 (a)(b)(c) 等多个子图块并行排列），它们往往在末端共用一个大图注。建议同时检查该处其他子图的对应情况。
2.  打开 `Processing_Cache/` 中对应的 `.md` 文件。
3.  将对应的图注文字（如一段以 Fig. 开头的内容）移动到该图片引用（`![]`）的 **紧随其后的下一段**。
4.  删除 `Fig. X` 编号前面的 OCR 杂质。
5.  删除成品 PDF 并重新运行脚本即可。

---

## 📁 Output Structure / 输出结构
*   **Processing_Cache/**: Stores intermediate Markdown, images, and hashes for deterministic caching. (缓存区)
*   **NotebookLM_Ready/**: High-fidelity PDFs ready to be dropped into NotebookLM. (成品区)
*   **Failed_PDFs/**: Problematic or corrupted files moved here automatically for manual review. (失败区)
