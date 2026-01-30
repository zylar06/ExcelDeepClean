# ExcelDeepClean (智能 Excel 表格提取与清洗)

这是一个将**复杂、非结构化的 Excel 报表**自动化转化为**高可用、数据库级结构化数据**的 AI 驱动工具。

它结合了**传统算法**的高效性与 **LLM (大语言模型)** 的语义理解能力，能够解决合并单元格错位、多表混排、层级标题干扰、无意义数据清洗等痛点。

---

## 🌟 核心优势

- **💡 智能语义分割**：利用 AI 自动识别“个案”、“索赔单”、“系统信息”等逻辑子表，无需人工配置复杂的切分规则。
- **🧩 完美处理合并单元格**：独创的流式解析算法，能够在读取时自动填充合并单元格的值，确保数据原子性。
- **🧹 深度数据清洗**：自动识别并剔除“新建”、“更改所有人”等仅供人机交互的操作按钮行。
- **⚡️ 极低资源占用**：采用流式读取 (Streaming) 技术，轻松处理 10w+ 行的大型 Excel 文件，内存占用极低。
- **📊 审计可追溯**：所有的 AI 清洗与切分操作都会生成详细的审计日志 (Audit Log)，拒绝黑盒操作。

---

## 🛠️ 处理流程与原理

本项目采用 **"规则提取 + 智能后处理"** 的两阶段架构：

### 阶段一：物理提取与标准化 (Rule-based Extraction)
**解决“读对”的问题** —— 将视觉上的 Excel 表格还原为逻辑上的二维数据。

*   **合并单元格复原**：绕过 `openpyxl` 的限制，直接解析 XML 源码，实现“读取即填充” (Forward Fill)，解决数据错位问题。
*   **视觉边界检测**：基于**连通域 (Connected Components)** 算法，自动识别 Sheet 中视觉上分离的多个表格块。
*   **空白列修剪**：算法自动检测并剔除全空或无意义的占位列 (`Column_X`)，压缩数据密度。

### 阶段二：智能语义清洗 (AI-driven Refinement)
**解决“读懂”的问题** —— 引入 DeepSeek/OpenAI 对数据进行语义理解和二次加工。

*   **逻辑分表 (Split)**：
    *   AI 通过分析行的**独占性**（仅首列有值）、**语义概括性**（如“xx信息”）、**上下文突变**等特征，自动将大表切分为多个独立的 Sheet（如“备注信息”、“系统信息”）。
*   **噪声清洗 (Filter)**：
    *   识别并删除“新建”、“Change Owner”等非数据行。
*   **智能列合并**：
    *   结合列统计信息 (Data Profile)，智能合并内容重复的冗余表头（如“排序” vs “排序_2”），同时保留有意义的复选框列（如“显示位置”）。

---

## 🚀 快速开始

### 1. 安装依赖

本项目使用 `uv` 进行依赖管理（推荐），也可以使用 pip。

```bash
# 克隆仓库
git clone https://github.com/zylar06/ExcelDeepClean.git
cd ExcelDeepClean

# 安装依赖
uv sync
```

### 2. 配置 API Key

在项目根目录创建 `.env` 文件，填入您的 LLM API Key（支持 OpenAI 格式，推荐 DeepSeek）：

```env
DEEPSEEK_API_KEY=sk-your-api-key-here
```

### 3. 运行提取

**步骤 1：初步提取 (Extract)**
将 Excel 文件转换为中间态 JSON：

```bash
uv run python -m excel_table_extractor extract test_data.xlsx -o output -f json
```

**步骤 2：AI 智能清洗 (Refine)**
调用 AI 对 JSON 进行深度清洗，并生成最终 Excel 报告：

```bash
uv run python -m excel_table_extractor process-json output/tables.json -o output/final_report.xlsx
```

---

## 📂 输出结果

最终生成的 Excel 文件 (`final_report.xlsx`) 将包含：
*   **独立的数据 Sheet**：如 `个案`、`索赔单`、`备注信息` 等，每个表都已清洗干净。
*   **Audit_Log**：记录了所有被删除的行、被合并的列以及切分操作的原因。

## 🤝 贡献

欢迎提交 Issue 和 PR！

## 📄 许可证

MIT License
