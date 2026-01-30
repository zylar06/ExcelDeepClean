import os
import json
import pytest
from excel_table_extractor.core.reader import StreamReader
from excel_table_extractor.core.detector import TableDetector
from excel_table_extractor.core.extractor import TableExtractor
from excel_table_extractor.core.writers import TableWriter

INPUT_FILE = "test_data.xlsx"

def test_full_pipeline(tmp_path):
    output_dir = tmp_path / "output"
    os.makedirs(output_dir)
    
    # 1. Reader
    reader = StreamReader(INPUT_FILE)
    assert len(reader.merged_cells) > 0
    
    # 2. Detect
    sheet_name = "Asset Layout"
    detector = TableDetector()
    candidates = detector.detect(reader, sheet_name)
    assert len(candidates) >= 2 # Should find at least the main tables
    
    # 3. Extract
    reader.close()
    reader = StreamReader(INPUT_FILE)
    reader._merged_cells_cache = reader.merged_cells # Optimization
    
    extractor = TableExtractor()
    tables = list(extractor.extract_all(reader, candidates))
    assert len(tables) == len(candidates)
    
    # Verify content of the main table
    main_table = next((t for t in tables if t.bbox.height > 40), None)
    assert main_table is not None
    assert "API 名称" in main_table.columns
    assert len(main_table.rows) > 10
    
    # 4. Write
    writer = TableWriter(str(output_dir), format="json")
    writer.write(tables)
    
    output_file = output_dir / "tables.json"
    assert output_file.exists()
    
    with open(output_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        assert len(data) == len(tables)
        
    reader.close()

def test_csv_output(tmp_path):
    output_dir = tmp_path / "output_csv"
    os.makedirs(output_dir)
    
    # Minimal setup
    reader = StreamReader(INPUT_FILE)
    detector = TableDetector()
    sheet_name = "Asset Layout"
    candidates = detector.detect(reader, sheet_name)
    reader.close()
    
    reader = StreamReader(INPUT_FILE)
    extractor = TableExtractor()
    tables = list(extractor.extract_all(reader, candidates))
    reader.close()
    
    writer = TableWriter(str(output_dir), format="csv")
    writer.write(tables)
    
    # Check if files exist
    for t in tables:
        csv_path = output_dir / f"{t.table_id}.csv"
        meta_path = output_dir / f"{t.table_id}.meta.json"
        assert csv_path.exists()
        assert meta_path.exists()
