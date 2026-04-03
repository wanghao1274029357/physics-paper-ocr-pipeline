# ⚛️ Physics Paper OCR Converter (NotebookLM Edition)
### 物理论文解析工具 (NotebookLM 深度优化版)

A specialized Python toolchain optimized for converting complex physics research papers into high-fidelity documents specifically tailored for Google's **NotebookLM** and **Gemini 1.5**.

本项目是一套专为物理学研究人员打造的 PDF 转换方案。由于多栏布局、复杂的公式嵌套以及背景水印等干扰，原始 PDF 直接上传到 NotebookLM 往往会出现断句、分栏错位或公式乱码，严重影响 AI 的逻辑推理。本工具通过本地高性能识别引擎，将论文精准重新排版，生成最适合 AI 阅读的 RAG（检索增强生成）高保真语料。

---

## 🌟 Key Features / 核心亮点

*   **FIG-Academic Rule (学术图注识别)**: Intelligently identifies and matches figure captions using standard academic keywords. Correctly groups multi-block captions split by page breaks.
    *   自动识别并提取图注。如果由于分栏或分页导致图注断裂，系统会自动将其重新缝合，还原完整含义。
*   **Semantic Stitching Engine (语义修复引擎)**: Automatically heals paragraphs and captions split by layout shifts or LaTeX formulas (`$`).
    *   针对论文中由于 LaTeX 公式（如 `$ \omega $`）导致的“假断句”现象，系统会自动进行拼接处理，还原论文原本流畅的语感。
*   **Failed File Auto-Recovery (全流程容错与自动恢复)**: Automatically moves corrupted or crashed PDFs into a specialized folder to ensure batch processing continuity.
    *   在大规模批处理中，如果遇到损坏或引起崩溃的特殊 PDF，系统会自动将其挪至 `Failed_PDFs/` 目录，确保整个流程不会由于单点错误而中断。
*   **Layout Strategy (排版策略)**:
    *   **Short Docs (<100k chars)**: Automatically moves figures and captions to a dedicated appendix to avoid interrupting the main semantic flow for RAG.
        *   **短篇论文**: 采用“附录模式”，讲图表统一置顶处理，避免插图干扰 AI 对正文核心逻辑的理解。
    *   **Long Docs**: Preserves in-situ placement with semantic italicized captions.
        *   **长篇综述**: 保留图文原位排版，同时对图注进行斜体标注，帮助 AI 更好区分正文与说明。

---

## 🧠 Model Architecture / 技术架构

The pipeline leverages our optimized inference engine, combining several SOTA multimodal models:

本方案底层深度联动了多项顶尖的多模态识别模型，实现“软硬兼修”：

1.  **Surya (Layout & OCR)**: High-precision line ordering and text extraction tailored for complex multi-column academic layouts.
    *   **Surya (布局分析)**: 提供高精度行排序与文字提取，能完美拆解物理期刊中那些令人头疼的异形多栏排版。
2.  **Texify (LaTeX & Formulas)**: Specialized in transforming complex mathematical notation into clean, editable Markdown LaTeX syntax.
    *   **Texify (公式识别)**: 负责将复杂的物理公式精准转化为标准的、可搜索的 LaTeX 语法。
3.  **Segmenter (Block Recognition)**: Intelligently isolates data figures, tables, and noise (headers/footers) from the main semantic body.
    *   **区块识别模型**: 智能识别并剥离图片、表格以及广告碎片，只将最有价值的“学术干货”喂给 AI，极大抑制 NotebookLM 在回答时的幻觉现象。

*Note: Models are automatically downloaded from Hugging Face during the first run. / 注：相关组件将在首次运行时自动下载。*

---

## 🚀 Quick Start / 快速上手

### 1. Prerequisites / 环境准备
Ensure you have an NVIDIA GPU and install dependencies:
确保装有显卡驱动，一键安装必要组件：

```bash
pip install reportlab marker-pdf
```

### 2. Usage / 使用方法
Run the batch processor on your target folder:
在终端直接运行脚本，并指定包含 PDF 的文件夹：

```bash
python batch_processor.py "C:\Path\To\Your\Papers"
```

---

## 🛠️ Manual Intervention Guide / 疑难杂症处理

Use this workflow to fix edge cases manually:
对于极少数排版极度混乱的奇葩刊物，你可以尝试以下“人工补刀”方案：

### Case A: Unwanted UI elements or noise images
1.  Enter `Processing_Cache/` folder and find the document directory.
2.  Delete unwanted `.jpeg` images.
3.  Delete the generated PDF in `NotebookLM_Ready/` and **rerun the script**.
    *   手动删除缓存中多余的杂质图片，删除导出 PDF 后点击重新运行，系统会基于你清理后的缓存重新出图。

### Case B: Missing or mismatched captions
If the terminal reports unmatched valid images:
如果终端报警提示某些有效图片没抓到图注：
1.  **Reason**: Could be due to multi-sub-figures sharing a single caption or page breaks.
    *   **原因分析**: 可能是由于 (a)(b)(c) 多个子图共用一个总图注，或者是跨页导致识别偏移。
2.  **Manual Alignment**: Open the corresponding `.md` file in `Processing_Cache/`.
3.  Place the caption text **immediately after** the image reference (`![]`).
    *   **手动对齐**: 打开对应缓存目录下的 `.md` 文件，将图注文字手动移动到图片引用代码的后方即可。
4.  Remove pre-fig noise and rerun.
    *   清理多余碎片文字，重新运行脚本即可完成修正。
