import json
import csv
import os
from typing import List, Union
from .models import ExtractedTable

class TableWriter:
    def __init__(self, output_dir: str, format: str = 'json'):
        self.output_dir = output_dir
        self.format = format.lower()
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def write(self, tables: List[ExtractedTable]):
        if self.format == 'json':
            self._write_json(tables)
        elif self.format == 'csv':
            self._write_csv(tables)
        else:
            raise ValueError(f"Unsupported format: {self.format}")

    def _write_json(self, tables: List[ExtractedTable]):
        # Option 1: One big JSON file
        # Option 2: One file per table
        # User requirement: "Output for all identified tables"
        # Let's do one file containing all tables for the input file?
        # Or if we process multiple input files?
        # Let's write one main output file `output.json` or `input_filename.json`.
        # Since we don't know input filename here easily without passing it, 
        # let's assume we write individual files by table_id or one big list.
        # Writing individual files is safer for large data.
        
        # But user might prefer one result.
        # Let's write `tables.json` with list of all tables.
        
        data = []
        for t in tables:
            data.append({
                'table_id': t.table_id,
                'sheet': t.sheet_name,
                'bbox': {
                    'min_row': t.bbox.min_row,
                    'min_col': t.bbox.min_col,
                    'max_row': t.bbox.max_row,
                    'max_col': t.bbox.max_col
                },
                'columns': t.columns,
                'rows': t.rows,
                'meta': t.meta
            })
            
        out_path = os.path.join(self.output_dir, "tables.json")
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
    def _write_csv(self, tables: List[ExtractedTable]):
        for t in tables:
            # Write CSV
            csv_path = os.path.join(self.output_dir, f"{t.table_id}.csv")
            with open(csv_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=t.columns)
                writer.writeheader()
                writer.writerows(t.rows)
                
            # Write Meta
            meta_path = os.path.join(self.output_dir, f"{t.table_id}.meta.json")
            meta = {
                'table_id': t.table_id,
                'sheet': t.sheet_name,
                'bbox': {
                    'min_row': t.bbox.min_row,
                    'min_col': t.bbox.min_col,
                    'max_row': t.bbox.max_row,
                    'max_col': t.bbox.max_col
                },
                'columns': t.columns,
                'meta': t.meta
            }
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
