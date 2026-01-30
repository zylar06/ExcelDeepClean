# 最终 Prompt 优化计划：精准区分“分表标题”与“噪声行”

## 1. 用户核心需求
用户非常精准地总结了“分表标题”的四个核心特征（独占性、语义概括性、上下文突变、非数据性），并特别指出了一个**高难度痛点**：
- **“分表标题” vs “噪声行”**：两者可能长得非常像（都是一整行完全相同的内容，或者是只有第一列有内容）。
- **目标**：AI 必须能区分出哪些应该 **Split（作为新表）**，哪些应该 **Delete（作为噪声）**。

## 2. 区分逻辑 (Prompt Strategy)

我们需要在 Prompt 中明确教 AI 如何区分这两者：

### 特征对比
| 特征 | 分表标题 (Split Header) | 噪声行 (Junk Row) |
| :--- | :--- | :--- |
| **内容语义** | **名词性、概括性**。通常是业务实体的名称或属性组的名称（如“资产信息”、“备注信息”、“系统信息”）。 | **动词性、操作性、系统性**。通常是动作（“新建”、“编辑”、“更改”）、状态提示（“只读”、“必填”）或无意义的重复。 |
| **后续内容** | **有后续数据**。标题下方通常紧跟着字段定义或具体数据行。 | **孤立或重复**。下方可能还是空行，或者是无关内容，或者它本身就是对上方内容的冗余重复。 |
| **视觉作用** | **开启新节**。作为下方内容的“帽子”。 | **干扰视线**。作为按钮、页眉页脚或单纯的填充。 |

## 3. 实施方案：修改 `_build_prompt`

我将把用户提供的 4 点特征以及上述的“区分逻辑”直接融入到 Prompt 中。

### 新 Prompt 结构
```text
Analyze these Excel rows...

Task 1: Identify "Junk" rows (DELETE)
- Context: Rows that are navigational (Buttons), system metadata, or pure noise.
- Pattern: 
  - Contains action verbs: "New", "Edit", "Back", "Change Owner", "新建", "更改".
  - Contains system status: "System Info" (if it appears as a footer/button context), "Read Only".
  - Repetitive noise: Rows where every cell has the exact same content (e.g. "Asset Info" repeated in every col).

Task 2: Identify "Section Headers" (SPLIT)
- Context: Rows that serve as a TITLE for the data *below* them.
- Characteristics:
  1. Exclusivity: Often only the first 1-2 columns have values, rest are empty.
  2. Semantics: Nouns/Categories ending in "Info", "History", "List", "Record", "信息", "记录", "历史".
  3. Context Shift: The data structure (columns filled) often changes after this row.
  4. Non-Data: It doesn't look like a data record of the *previous* table.

CRITICAL DISTINCTION: 
- If a row is "更改所有人" (Action) -> DELETE.
- If a row is "系统信息" (Category Title) -> SPLIT.
- If a row is "备注信息" (Category Title) -> SPLIT.
```

## 4. 执行步骤
1.  **修改 `src/excel_table_extractor/ai/processor.py`**。
2.  **验证**：运行 `process-json`，生成 `final_report_optimized_v3.xlsx`。
3.  **检查**：
    -   “更改所有人”是否被删？
    -   “备注信息”和“系统信息”是否被分成了独立的 Sheet？

请确认执行。