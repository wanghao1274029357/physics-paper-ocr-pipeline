# ⚛️ Physics Paper OCR Pipeline (NotebookLM Edition)
### 物理论文 OCR 转换管线 (NotebookLM 专供版)

A specialized Python OCR pipeline optimized for converting complex physics research papers into high-fidelity PDFs specifically tailored for Google's **NotebookLM** and **Gemini 1.5**.

本项目已通过 VS Code 的本地 Git 进行版本控制。你可以随时通过侧边栏的 Git 图标进行“提交(Commit)”以保存你的改动。

---

## 🌟 Key Features / 核心特性

*   **FIG-Academic Rule (图注识别规则)**: Intelligently identifies and matches figure captions using standard academic keywords.
*   **Semantic Stitching Engine (语义拼接引擎)**: Automatically heals paragraphs and captions split by layout shifts or LaTeX formulas (`$`).
*   **Dual-Phase Stall Detection (双阶段死锁监测)**: Monitors real-time GPU activity (`nvidia-smi`) to prevent deadlocks.
*   **Failed File Auto-Recovery (失败文件自动回收)**: Moves corrupted PDFs into `Failed_PDFs/` automatically.
*   **Local Hardware Powered (本地算力驱动)**: Processing speed depends on your local NVIDIA GPU specs.

---

## 🚀 Quick Start / 快速上手

### 1. Prerequisites / 环境依赖
```bash
pip install -r requirements.txt
```

### 2. Usage / 使用方法
```bash
python batch_processor.py "C:\Path\To\Your\Papers"
```

---

## 🛠️ Manual Intervention Guide / 人工干预指南

### 场景 A：PDF 中出现了网页碎图片
1. 进入 `Processing_Cache/` 文件夹。
2. 手动删除多余的 `.jpeg` 文件。
3. 删除成品 PDF 并重新运行。

### 场景 B：有效图块未成功抓取图注
1. 打开 `Processing_Cache/` 中对应的 `.md` 文件。
2. 将图注文字移动到图片引用（`![]`）的 **紧随其后的下一段**。
3. 删除 `Fig. X` 编号前面的 OCR 杂质并保存，重新运行脚本即可。
