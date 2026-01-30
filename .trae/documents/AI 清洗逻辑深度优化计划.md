# 解决 AI 清洗失效问题的方案

## 1. 问题复盘
用户反馈之前的 AI 清洗并没有生效，主要表现为：
1.  **“更改所有人”** 这种噪声行未被剔除。
2.  **“排序”** 列的合并未生效。
3.  **用户怀疑 Prompt 提示词**。

经过代码审查，发现 `AIProcessor` 的实现存在一个**致命缺陷**：
在 `_call_llm` 方法中，虽然实现了 `merge_instructions` 的接收，但在 `process_table` 方法中调用 `_apply_merge_columns` 的逻辑是正确的。然而，**核心问题在于 Prompt 的构造和数据摘要的生成方式**。

当前 Prompt 如下：
```python
Identify:
1. "Junk" rows: navigation buttons ("新建", "Back"), system info, empty separators.
...
```

而数据摘要 `_generate_row_summaries` 仅截取了前 50 个字符：
`summary = f"ID:{i} | Count:{non_empty_count} | Content:{first_val}"`

**根本原因**：
1.  **摘要信息过少**：对于“更改所有人”这一行，如果它不是第一列（`first_val`），或者它的特征在 50 个字符之外，AI 根本看不到它。
2.  **“排序”列合并失败**：AI 无法仅凭“行摘要”判断列的冗余性。它需要看到**整列的数据分布**才能判断“排序_2”是否全为空。目前的 Prompt 和输入完全没有提供列级别的数据统计。
3.  **Prompt 不够强硬**：AI 对于“更改所有人”这种中文业务词汇可能不认为是 Junk，除非显式举例。

## 2. 优化方案

### 改进 1：增强数据摘要 (Data Profiling)
不再只发送行摘要，而是先计算**列统计信息**发送给 AI。
-   **列统计**：对于每一列，计算非空率、唯一值数量、前 5 个常见值。
-   **Prompt 调整**：明确告知 AI 每一列的数据分布，让 AI 判断是否冗余。

### 改进 2：增强行摘要 (Row Sampling)
-   不再只发 `first_val`，而是发送该行的**所有非空值**（拼接字符串），确保 AI 能看到“更改所有人”这几个字，无论它在哪一列。

### 改进 3：针对性 Prompt 优化
-   **显式举例**：在 Prompt 中明确加入 `"更改所有人"`, `"Change Owner"`, `"System Info"` 作为 Junk 示例。
-   **列合并指令**：明确告诉 AI *"If column '排序_2' is empty in sample rows, merge it into '排序'"*。

## 3. 实施步骤

1.  **修改 `_generate_row_summaries`**：
    -   改为 `ID:{i} | Values: {val1, val2, ...}`，包含行内所有文本信息。
2.  **修改 `_build_prompt`**：
    -   增加 **Column Profile** 部分：`Column '排序_2': 90% empty, samples: []`。
    -   在 System Prompt 中加入具体的噪声关键词列表。
3.  **验证**：
    -   手动检查生成的 Prompt 内容。
    -   运行测试，确认“更改所有人”行被标记为 Delete。

## 4. 提示词公开
用户想知道提示词是什么。目前的提示词在 `src/excel_table_extractor/ai/processor.py` 的 `_build_prompt` 方法中：
```python
Analyze these Excel rows...
Identify:
1. "Junk" rows: navigation buttons ("新建", "Back")...
```
我将在代码修改中增强这部分。

请确认是否执行此深度优化？