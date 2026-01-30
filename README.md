# ExcelDeepClean

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-orange)

**AI-Powered Excel Data Extraction & Cleaning Tool**

[English](./README.md) | [中文](./README_zh-CN.md)

</div>

---

**ExcelDeepClean** is a powerful tool designed to transform **complex, unstructured Excel reports** into **clean, database-ready structured data**. It combines **algorithmic precision** with **LLM semantic understanding** to solve common pain points like merged cells, mixed tables, and noisy data.

## ✨ Key Features

- **💡 Smart Semantic Splitting**: Automatically identifies and splits logical sub-tables (e.g., "Case Records", "Claim Notes") using AI, without manual rules.
- **🧩 Perfect Merged Cell Handling**: Custom stream parser that "forward fills" merged cell values during reading, ensuring data atomicity.
- **🧹 Deep Data Cleaning**: Detects and removes non-data rows like "Create New", "Change Owner", and visual separators.
- **⚡️ Ultra-low Resource Usage**: Streaming architecture supports 100k+ row files with minimal memory footprint.
- **📊 Transparent Audit**: Generates a detailed `Audit_Log` for every AI decision (split/delete/merge).

## 🏗 Architecture

```mermaid
graph LR
    A[Raw Excel (.xlsx)] --> B(Stream Reader)
    B --> C{Table Detector}
    C --> D[Raw Extraction]
    D --> E(AI Refinement)
    E --> F[Clean JSON/Excel]
    E --> G[Audit Log]
```

## 🚀 Quick Start

### 1. Installation
We recommend using `uv` for dependency management:
```bash
git clone https://github.com/zylar06/ExcelDeepClean.git
cd ExcelDeepClean
uv sync
```

### 2. Configuration
Create a `.env` file in the root directory and add your LLM API Key (DeepSeek/OpenAI compatible):
```env
DEEPSEEK_API_KEY=sk-your-api-key-here
```

### 3. Usage
**Step 1: Extract Raw Data**
```bash
uv run python -m excel_table_extractor extract input.xlsx -o output -f json
```

**Step 2: AI Refinement**
```bash
uv run python -m excel_table_extractor process-json output/tables.json -o output/final_report.xlsx
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License
