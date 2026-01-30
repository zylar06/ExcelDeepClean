# Excel Table Extractor Design Document

## 1. Architecture Overview

The tool is designed to process large, complex Excel files with minimal memory footprint while ensuring accurate extraction of logical tables.

### Core Modules

- **StreamReader (`core/reader.py`)**:
  - Uses `openpyxl` in `read_only=True` mode for streaming row access.
  - Implements a custom XML parser (`utils/xlsx_utils.py`) to extract merged cell ranges directly from the `.xlsx` package (zip), bypassing `openpyxl`'s limitation in read-only mode.
  - Efficiently "fills" merged cells on-the-fly using an active-range index, ensuring downstream components see a normalized grid.

- **TableDetector (`core/detector.py`)**:
  - Treats the spreadsheet as a 2D grid of non-empty cells.
  - Uses a **Connected Components** algorithm (Union-Find) to identify independent clusters of data.
  - Scans the sheet row-by-row, maintaining active segments and merging component IDs based on vertical overlap.
  - Outputs `TableCandidate` objects defined by Bounding Boxes.

- **TableExtractor (`core/extractor.py`)**:
  - Takes candidates and extracts the raw data grid.
  - Performs **Header Inference**:
    - Scans the first N rows of the candidate region.
    - Scores rows based on fill rate, string content, and uniqueness.
    - Selects the best row as the header.
  - **Normalization**:
    - Handles duplicate column names by appending suffixes.
    - Converts data to a list of dictionaries (records).
  
- **Writers (`core/writers.py`)**:
  - Supports JSON (single file or per-table) and CSV output.
  - JSON output preserves data types (int, float, bool) better than CSV.

## 2. Key Algorithms

### Merged Cell Handling in Stream Mode
Since `openpyxl` does not populate `merged_cells` reliably in read-only mode, we parse `xl/worksheets/sheetN.xml` using `xml.etree.ElementTree.iterparse`. This allows extracting `<mergeCell ref="A1:C3"/>` tags without loading the DOM.
During row iteration, a "Forward Fill" strategy is used: if a cell is part of a merge range, the value of the top-left cell (cached) is used.

### Table Segmentation
We use a row-scan algorithm similar to labeling connected components in binary images.
1. **Row Segmentation**: Identify contiguous non-empty cell runs in the current row.
2. **Connectivity**: Check if any segment in the current row vertically overlaps with segments from the active component list.
3. **Union-Find**: Merge components that are connected.
4. **Bounding Box**: Track min/max row/col for each component ID.

## 3. Data Flow

1. **Input**: `.xlsx` file path.
2. **Phase 1 (Detection)**:
   - Stream through the sheet.
   - Build Connected Components.
   - Filter small noise (e.g., < 2x2).
   - Produce `TableCandidate` list.
3. **Phase 2 (Extraction)**:
   - Re-open the sheet (stream again).
   - For each row, check which candidates intersect it.
   - Buffer data for active candidates.
   - When a candidate is fully read, process its buffer (header detect -> structurize).
   - Yield `ExtractedTable`.
4. **Output**: Write to JSON/CSV.

## 4. Performance Considerations
- **Memory**: The entire sheet is never loaded into memory. We only buffer the *content* of identified tables. For very large tables, this might still be significant, but much less than the full DOM.
- **Speed**: We parse the file twice (once for detection, once for extraction). This is a trade-off for low memory usage.

