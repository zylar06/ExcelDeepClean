# AI 处理 JSON 数据的最终优化方案

您说得对，直接利用已经生成的标准 JSON 数据进行 AI 处理是最直接、最高效的路径。我们不需要在复杂的 Excel 解析阶段引入 AI，而是在**后处理阶段**，把 JSON 当作 AI 的输入，让 AI 帮我们“整理”这份数据。

## 1. 核心思路：JSON Post-Processing
我们已经得到了 `tables.json`，其中包含了提取出的初步表格数据。现在我们将实现一个**独立的 AI 处理流程**：
1.  **读取 JSON**：加载 `tables.json`。
2.  **分块发送**：将大表格的 JSON 数据按行（Rows）进行分块（Chunking），例如每 50-100 行作为一个批次发送给 AI。
3.  **AI 任务**：
    - **识别子表**：判断这些行是否属于新的子表（如从“个案”变成了“索赔单”）。
    - **标记垃圾**：判断哪些行是无意义数据（“新建”、“系统信息”）。
4.  **重组与输出**：根据 AI 的返回结果，将原始 JSON 重组为结构更清晰的多个表格，并生成 Excel。

## 2. 解决 Context 爆表方案
为了避免一次性把几千行 JSON 发给 AI：
- **只发“特征”**：对于每一行，我们不发送完整的 `{"col1": "val1", ...}` 对象，而是简化为 `Row ID | Col1 Value | Non-empty Count` 的摘要格式。
- **流式/分批处理**：AI 只需要返回 `{ "row_id": 123, "type": "new_table_header", "name": "索赔单" }` 或 `{ "row_id": 124, "type": "junk" }`。我们根据这些 ID 在本地对原始 JSON 进行切割和清洗。

## 3. 实施计划

### 步骤 1: 实现 `AIJSONProcessor`
- 创建 `src/excel_table_extractor/ai/processor.py`。
- 功能：
  - 读取 `ExtractedTable` 对象。
  - 生成精简版的行摘要（Row Summary）。
  - 调用 AI 接口（Mock 接口或真实 API，支持用户输入 Key）。
  - 解析 AI 返回的指令（Split/Delete）。

### 步骤 2: 实现 Excel 导出 (`ExcelWriter`)
- 创建 `src/excel_table_extractor/core/excel_writer.py`。
- 功能：
  - 接收处理后的表格列表。
  - 使用 `openpyxl` 将每个表格写入独立的 Sheet。
  - 如果 AI 识别出子表名，用作 Sheet Name（如 `Asset_Case`, `Asset_Claim`）。
  - 增加一个 `Audit_Log` Sheet，记录被 AI 移除的行。

### 步骤 3: 集成到 CLI
- 新增命令：`uv run python -m excel_table_extractor process-json output/tables.json --api-key <KEY> --output final_report.xlsx`。
- 或者整合进主流程：`--ai-refine` 参数。

## 4. 交付结果
1.  **清洗后的 JSON**：去除了垃圾行，拆分了子表。
2.  **Excel 报表**：
    - Sheet 1: `个案` (清洗后)
    - Sheet 2: `索赔单` (清洗后)
    - ...
    - Sheet N: `Audit Log` (包含被删的“新建”行及其原文)

此方案完全基于您现有的 JSON 产物，逻辑解耦，且通过“摘要发送”彻底解决了上下文长度问题。请确认是否开始执行？