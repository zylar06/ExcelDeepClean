from typing import List, Dict, Any, Optional, Tuple
import json
import logging
from dataclasses import dataclass
import os
from openai import OpenAI

@dataclass
class RowAction:
    row_index: int
    action: str  # 'keep', 'delete', 'split_header'
    reason: str = ""
    new_table_name: str = ""

class AIProcessor:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.deepseek.com/v1", model: str = "deepseek-chat"):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        self.base_url = base_url
        self.model = model
        self.logger = logging.getLogger("ai_processor")
        
        if self.api_key:
             self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
             self.client = None
             self.logger.warning("No API Key provided. AI features will be simulated.")

    def process_table(self, table_data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Returns: (processed_tables_list, audit_log_list)
        A single input table might be split into multiple tables.
        """
        rows = table_data.get('rows', [])
        if not rows:
            return [table_data], []

        # 1. Generate Summaries for AI
        row_summaries = self._generate_row_summaries(rows)
        column_profiles = self._generate_column_profiles(rows, table_data.get('columns', []))
        
        # 2. Call AI
        if self.client:
            actions, merge_instructions = self._call_llm(row_summaries, column_profiles, table_data.get('columns', []))
        else:
            actions = self._heuristic_fallback(row_summaries)
            merge_instructions = []
        
        # 3. Apply Actions (Split/Delete)
        processed_tables, audit_log = self._apply_actions(table_data, rows, actions)
        
        # 4. Apply Column Merging (if any)
        if merge_instructions:
            processed_tables = self._apply_merge_columns(processed_tables, merge_instructions)
            # Log merge actions
            for m in merge_instructions:
                audit_log.append({
                    "original_table_id": table_data.get('table_id'),
                    "row_index": -1, # Global action
                    "action": "merge_column",
                    "reason": m.get('reason'),
                    "content": f"Drop '{m.get('drop')}' keep '{m.get('keep')}'"
                })
        
        return processed_tables, audit_log

    def _apply_merge_columns(self, tables: List[Dict[str, Any]], merge_instructions: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        # Identify columns to drop
        cols_to_drop = {m.get('drop') for m in merge_instructions if m.get('drop')}
        
        for table in tables:
            columns = table.get('columns', [])
            # Filter columns
            new_columns = [c for c in columns if c not in cols_to_drop]
            
            # Filter rows
            new_rows = []
            for row in table.get('rows', []):
                new_row = {k: v for k, v in row.items() if k not in cols_to_drop}
                new_rows.append(new_row)
            
            table['columns'] = new_columns
            table['rows'] = new_rows
            
        return tables

    def _generate_row_summaries(self, rows: List[Dict[str, Any]]) -> List[str]:
        summaries = []
        for i, row in enumerate(rows):
            # Create a compact string representation
            # Collect all non-empty values
            values = [str(v).strip() for v in row.values() if v is not None and str(v).strip()]
            non_empty_count = len(values)
            
            # Join values with separator, limit total length to avoid token explosion
            content = " | ".join(values)
            if len(content) > 200:
                content = content[:200] + "..."
            
            summary = f"ID:{i} | Count:{non_empty_count} | Values: {content}"
            summaries.append(summary)
        return summaries

    def _generate_column_profiles(self, rows: List[Dict[str, Any]], columns: List[str]) -> str:
        profiles = []
        total_rows = len(rows)
        if total_rows == 0:
            return "No data rows."
            
        for col in columns:
            values = [str(r.get(col, "")).strip() for r in rows if r.get(col) is not None and str(r.get(col, "")).strip()]
            non_empty_count = len(values)
            unique_count = len(set(values))
            
            # Sample values (top 3 most common)
            from collections import Counter
            common = Counter(values).most_common(3)
            samples = [f"{k}({v})" for k, v in common]
            
            fill_rate = (non_empty_count / total_rows) * 100
            
            profile = f"Column '{col}': {fill_rate:.1f}% filled, {unique_count} unique. Samples: {samples}"
            profiles.append(profile)
            
        return "\n".join(profiles)

    def _call_llm(self, summaries: List[str], column_profiles: str, columns: List[str]) -> Tuple[List[RowAction], List[Dict[str, str]]]:
        # Chunking to avoid context limits
        chunk_size = 100
        actions = []
        merge_instructions = []
        
        # Only process first chunk for column merging logic?
        # Column redundancy should be visible in the first chunk.
        # But we process all chunks for row actions.
        
        for i in range(0, len(summaries), chunk_size):
            chunk = summaries[i:i+chunk_size]
            # Include profiles only in the first chunk prompt to save tokens?
            # Or always include? It's useful context. Profiles shouldn't be too huge.
            prompt = self._build_prompt(chunk, column_profiles, columns)
            
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a data cleaning assistant. Analyze the table rows. Identify sub-table headers (split points) and junk rows. Check for redundant columns (merged headers). Return JSON output."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                content = response.choices[0].message.content
                result = json.loads(content)
                
                # Parse row actions
                for item in result.get('actions', []):
                    row_id = int(item.get('row_id'))
                    action_type = item.get('type')
                    
                    if action_type == 'delete':
                        actions.append(RowAction(row_id, "delete", item.get('reason', 'AI Decision')))
                    elif action_type == 'split':
                        actions.append(RowAction(row_id, "split_header", item.get('reason', 'AI Split'), item.get('new_table_name', 'SubTable')))
                
                # Parse merge instructions (accumulate or take from first valid?)
                # We can take unique instructions.
                if result.get('merge_columns'):
                    for m in result.get('merge_columns'):
                        if m not in merge_instructions:
                            merge_instructions.append(m)
                            
            except Exception as e:
                self.logger.error(f"LLM Call failed: {e}")
                pass
                
        # Fill in 'keep' actions for rows not mentioned
        processed_ids = {a.row_index for a in actions}
        all_ids = set(range(len(summaries)))
        missing_ids = all_ids - processed_ids
        for mid in missing_ids:
            actions.append(RowAction(mid, "keep"))
            
        actions.sort(key=lambda x: x.row_index)
        return actions, merge_instructions

    def _build_prompt(self, summaries: List[str], column_profiles: str, columns: List[str]) -> str:
        data_str = "\n".join(summaries)
        return f"""
Analyze these Excel rows. They are from a table with columns: {columns}.

Data Profile (Column Statistics):
{column_profiles}

Identify:
1. "Junk" rows: 
   - Navigation buttons ("新建", "New", "Back", "Edit")
   - System Info lines ("System Info", "系统信息", "更改所有人", "Change Owner")
   - Empty separators or lines with only 1 non-empty cell that is not a section header.
   - Any row containing "更改所有人" or "Change Owner" is definitely junk/action button.

2. "Split" headers (Section Separators): 
    - Use the following logic to identify a new table section:
      a) **Exclusivity**: The row has values only in the first 1-2 columns, with the rest being empty.
      b) **Semantic Generality**: The content is a broad category name (often ending in "Info", "Information", "List", "History", "信息", "记录", "附件").
      c) **Context Shift**: The row breaks the pattern of previous data rows. It looks like a title, not a data record.
      d) **Uniformity vs Noise**: 
         - If a row has identical values across ALL columns (e.g., "System Info" repeated in every cell), it is likely a Section Header (Split).
         - BUT if a row has identical values that are clearly navigation actions (e.g., "New" repeated), it is Noise (Delete).
    - Examples of Split Headers: "个案 (Case)", "索赔单", "资产保修记录", "备注信息", "系统信息".

 Analyze Columns for Redundancy:
- If a column name is duplicated (e.g. "排序", "排序_2") AND the data suggests they are identical or the second one is always empty/redundant (check Data Profile!), mark it for merging.
- BUT if the data shows they are distinct (e.g. checkmarks in different rows for "显示位置" and "显示位置_2"), DO NOT merge.
- Look at the "Content" in the rows below to judge redundancy.

Return JSON format:
{{
  "actions": [
    {{ "row_id": 12, "type": "delete", "reason": "Junk button: '新建'" }},
    {{ "row_id": 45, "type": "split", "new_table_name": "Claim_Records", "reason": "Section Header: '索赔单'" }}
  ],
  "merge_columns": [
    {{ "keep": "排序", "drop": "排序_2", "reason": "Second column is 90% empty/redundant" }}
  ]
}}
Only include rows that need 'delete' or 'split'. Assume others are 'keep'.
If no columns need merging, return empty list for "merge_columns".

Rows:
{data_str}
"""

    def _heuristic_fallback(self, summaries: List[str]) -> List[RowAction]:
        actions = []
        for summary in summaries:
            parts = summary.split("|")
            row_id_str = parts[0].split(":")[1]
            row_id = int(row_id_str)
            content = parts[-1].split("Content:")[1] if "Content:" in parts[-1] else ""
            
            if "新建" in content or "System Info" in content or "系统信息" in content:
                 actions.append(RowAction(row_id, "delete", "Heuristic: Junk keyword"))
            elif ("个案" in content or "索赔单" in content) and "Count:1" in summary: # Very simple heuristic
                 name = "Case" if "个案" in content else "Claim"
                 actions.append(RowAction(row_id, "split_header", "Heuristic: Section Header", name))
            else:
                 actions.append(RowAction(row_id, "keep"))
        return actions

    def _apply_actions(self, original_table: Dict[str, Any], rows: List[Dict[str, Any]], actions: List[RowAction]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        result_tables = []
        audit_log = []
        
        current_rows = []
        current_name = original_table.get('sheet', 'Sheet1')
        current_base_id = original_table.get('table_id')
        
        actions_map = {a.row_index: a for a in actions}
        
        for i, row_data in enumerate(rows):
            action = actions_map.get(i, RowAction(i, "keep"))
            
            if action.action == "delete":
                audit_log.append({
                    "original_table_id": current_base_id,
                    "row_index": i,
                    "content": str(row_data)[:100],
                    "action": "delete",
                    "reason": action.reason
                })
            elif action.action == "split_header":
                # Finish current table
                if current_rows:
                    new_table = original_table.copy()
                    new_table['rows'] = current_rows
                    new_table['sheet'] = current_name
                    new_table['table_id'] = f"{current_base_id}_{len(result_tables)}"
                    result_tables.append(new_table)
                
                # Start new
                current_rows = []
                current_name = f"{original_table.get('sheet')}_{action.new_table_name}"
                
                audit_log.append({
                    "original_table_id": current_base_id,
                    "row_index": i,
                    "content": str(row_data)[:100],
                    "action": "split",
                    "reason": f"Start of {action.new_table_name}"
                })
            else:
                current_rows.append(row_data)
                
        if current_rows:
            new_table = original_table.copy()
            new_table['rows'] = current_rows
            new_table['sheet'] = current_name
            new_table['table_id'] = f"{current_base_id}_{len(result_tables)}"
            result_tables.append(new_table)
            
        return result_tables, audit_log
