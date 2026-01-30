# GitHub 推送与环境配置计划

## 1. 环境变量配置
- 创建 `.env` 文件，将 API Key 写入其中。
- 修改 `.gitignore`，确保 `.env` 被忽略，防止敏感信息泄露。
- 修改 `src/excel_table_extractor/ai/processor.py` 和 `cli.py`，使其支持从 `.env` 文件加载环境变量（使用 `python-dotenv` 库）。

## 2. 项目清理
- 删除根目录下的临时调试脚本：`check_merged.py`, `debug_*.py`, `test_*_manual.py`。
- 确保 `tests/` 目录下的测试代码完整覆盖了这些脚本的功能。

## 3. Git 初始化与推送
- 初始化本地 Git 仓库。
- 添加远程仓库：`git remote add origin git@github.com:zylar06/ExcelDeepClean.git`。
- 提交代码并推送。

## 4. 依赖更新
- 添加 `python-dotenv` 到项目依赖中，以便自动加载 `.env` 文件。

## 5. 实施步骤
1.  **添加依赖**：`uv add python-dotenv`。
2.  **代码修改**：在 `cli.py` 或 `__init__.py` 中加载 `.env`。
3.  **创建 .env**：写入 `DEEPSEEK_API_KEY=...`。
4.  **更新 .gitignore**：添加 `.env`。
5.  **清理文件**：删除临时脚本。
6.  **Git 推送**：执行 git 命令序列。

请确认是否开始执行？