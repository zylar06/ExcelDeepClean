from typing import List, Dict, Any, Generator, Optional, Tuple
from collections import Counter
import re
from .models import TableCandidate, ExtractedTable, BoundingBox
from .reader import StreamReader

class TableExtractor:
    def __init__(self, header_search_depth=5):
        self.header_search_depth = header_search_depth

    def extract_all(self, reader: StreamReader, candidates: List[TableCandidate]) -> Generator[ExtractedTable, None, None]:
        if not candidates:
            return

        # Sort candidates by min_row
        sorted_candidates = sorted(candidates, key=lambda c: c.bbox.min_row)
        
        # Group by sheet
        by_sheet: Dict[str, List[TableCandidate]] = {}
        for c in sorted_candidates:
            by_sheet.setdefault(c.sheet_name, []).append(c)

        for sheet_name, sheet_candidates in by_sheet.items():
            yield from self._process_sheet(reader, sheet_name, sheet_candidates)

    def _process_sheet(self, reader: StreamReader, sheet_name: str, candidates: List[TableCandidate]):
        # Buffers for each candidate: id -> list of rows
        buffers: Dict[str, List[List[Any]]] = {c.id: [] for c in candidates}
        # Active set management
        # Map row_idx to candidates that start/end? 
        # Simpler: just check range for each row. 
        # Optimization: maintain active list.
        
        candidates_by_id = {c.id: c for c in candidates}
        max_row_needed = max(c.bbox.max_row for c in candidates)
        
        # We need to know which candidates are interested in current row
        # Pre-compute interest intervals?
        # Actually, iterating candidates for each row is fine if N is small.
        # If N is large (thousands), use interval tree. Assuming small N (<100).
        
        for row_idx, row_values in reader.iter_sheet(sheet_name):
            if row_idx > max_row_needed:
                break
                
            for c in candidates:
                if c.bbox.min_row <= row_idx <= c.bbox.max_row:
                    # Extract slice
                    # row_values is 0-based list, but col indices are 1-based
                    # Slice: min_col-1 : max_col
                    # Ensure row has enough columns
                    slice_start = c.bbox.min_col - 1
                    slice_end = c.bbox.max_col
                    
                    row_len = len(row_values)
                    if slice_start >= row_len:
                        row_slice = [None] * c.bbox.width
                    else:
                        row_slice = row_values[slice_start:slice_end]
                        # Pad if short
                        if len(row_slice) < c.bbox.width:
                            row_slice.extend([None] * (c.bbox.width - len(row_slice)))
                            
                    buffers[c.id].append(row_slice)

        # Process buffers
        for c in candidates:
            data_rows = buffers[c.id]
            if not data_rows:
                continue
                
            extracted = self._process_table_data(c, data_rows)
            if extracted:
                yield extracted

    def _process_table_data(self, candidate: TableCandidate, raw_rows: List[List[Any]]) -> Optional[ExtractedTable]:
        if not raw_rows:
            return None
            
        # 1. Detect Header
        header_idx, columns = self._detect_header(raw_rows)
        
        # 2. Extract Data
        data_start_idx = header_idx + 1
        data_rows = raw_rows[data_start_idx:]
        
        # 2.5 Prune Empty Columns
        columns, data_rows = self._prune_empty_columns(columns, data_rows)
        
        # 3. Build Row Dicts
        structured_rows = []
        for row in data_rows:
            row_dict = {}
            for i, col_name in enumerate(columns):
                val = row[i] if i < len(row) else None
                row_dict[col_name] = val
            structured_rows.append(row_dict)
            
        # 4. Meta
        meta = candidate.meta.copy()
        meta['header_row_relative_index'] = header_idx
        
        return ExtractedTable(
            table_id=candidate.id,
            sheet_name=candidate.sheet_name,
            bbox=candidate.bbox,
            columns=columns,
            rows=structured_rows,
            meta=meta
        )

    def _prune_empty_columns(self, columns: List[str], data_rows: List[List[Any]]) -> Tuple[List[str], List[List[Any]]]:
        if not columns or not data_rows:
            return columns, data_rows
            
        num_cols = len(columns)
        # Check each column for non-empty values
        is_empty_col = [True] * num_cols
        
        for row in data_rows:
            for i in range(min(len(row), num_cols)):
                val = row[i]
                if val is not None and str(val).strip():
                    is_empty_col[i] = False
        
        # Keep columns that are not empty OR have a meaningful name (not Column_X)
        # User request: "不用再column代替了，没有就是没有" -> Delete Column_X if empty.
        # What if a column has a name "Comments" but is empty? User might want to keep it?
        # User said "后面大片的空白，不用再column代替了".
        # So we strictly remove columns that are (Empty AND Name starts with Column_).
        # OR remove ALL empty columns? 
        # "没有就是没有" implies removing empty columns regardless of name?
        # Let's be safe: Remove if (Empty) AND (Name is Column_X OR Name is Empty).
        # If Name is "Comments" and empty, maybe keep?
        # Let's stick to: Remove if Empty AND (Name like Column_\d+ OR Name is blank).
        
        cols_to_keep = []
        for i, col_name in enumerate(columns):
            if is_empty_col[i]:
                # It is empty. Should we keep it?
                # Check if name is auto-generated
                if col_name.startswith("Column_") and col_name[7:].isdigit():
                    continue # Drop
                if not col_name.strip():
                    continue # Drop
                # If it has a real name, maybe keep? 
                # User complaint was specifically about "Column_7", "Column_8".
                # Let's keep real named empty columns for now (schema consistency).
                cols_to_keep.append(i)
            else:
                cols_to_keep.append(i)
                
        new_columns = [columns[i] for i in cols_to_keep]
        new_data_rows = []
        for row in data_rows:
            new_row = [row[i] if i < len(row) else None for i in cols_to_keep]
            new_data_rows.append(new_row)
            
        return new_columns, new_data_rows

    def _detect_header(self, rows: List[List[Any]]) -> Tuple[int, List[str]]:
        """
        Returns (header_row_index, list_of_column_names)
        header_row_index is relative to the start of rows.
        """
        best_score = -1.0
        best_idx = 0
        
        limit = min(len(rows), self.header_search_depth)
        
        for i in range(limit):
            row = rows[i]
            score = self._score_header(row)
            if score > best_score:
                best_score = score
                best_idx = i
                
        # Normalize header names
        raw_header = rows[best_idx]
        columns = self._normalize_columns(raw_header)
        return best_idx, columns

    def _score_header(self, row: List[Any]) -> float:
        if not row:
            return 0.0
        
        non_empty = 0
        strings = 0
        unique_vals = set()
        
        for cell in row:
            if cell is not None and str(cell).strip():
                non_empty += 1
                if isinstance(cell, str):
                    strings += 1
                unique_vals.add(str(cell).strip())
                
        if not non_empty:
            return 0.0
            
        # Metrics
        fill_rate = non_empty / len(row)
        string_rate = strings / non_empty
        uniqueness = len(unique_vals) / non_empty
        
        # Heuristic: Headers are mostly strings, unique, and well-filled
        return (fill_rate * 0.4) + (string_rate * 0.3) + (uniqueness * 0.3)

    def _normalize_columns(self, row: List[Any]) -> List[str]:
        cols = []
        seen = Counter()
        
        for i, val in enumerate(row):
            if val is None or (isinstance(val, str) and not val.strip()):
                col_name = f"Column_{i+1}"
            else:
                col_name = str(val).strip()
                
            # Deduplicate
            if seen[col_name] > 0:
                final_name = f"{col_name}_{seen[col_name]+1}"
            else:
                final_name = col_name
            
            seen[col_name] += 1
            cols.append(final_name)
            
        return cols
