# Excel Table Extractor

A high-performance Python tool to automatically identify, split, and extract structured tables from complex Excel files (`.xlsx`). It handles merged cells, multiple tables per sheet, and different layouts, converting them into database-ready JSON or CSV formats.

## Features

- **Smart Detection**: Automatically identifies independent tables in a single sheet using connected component analysis.
- **Merged Cell Support**: Correctly handles merged cells by expanding/filling values, even in large files.
- **Header Inference**: Automatically detects the most likely header row for each table.
- **Low Memory Footprint**: Uses stream processing (`read_only` mode) to handle files with 100k+ rows.
- **Standard Output**: Produces clean JSON or CSV ready for database ingestion.

## Installation

This project uses `uv` for dependency management.

```bash
# Clone the repository
git clone <repo_url>
cd excel-table-extractor

# Install dependencies
uv sync
```

## Usage

### Command Line Interface

```bash
# Run the extractor
uv run python -m excel_table_extractor input_file.xlsx --output ./output_dir --format json
```

**Arguments:**
- `input_file`: Path to the .xlsx file.
- `-o, --output`: Directory to save output files (default: `./output`).
- `-f, --format`: Output format, `json` or `csv` (default: `json`).
- `-v, --verbose`: Enable debug logging.

### Output Structure

**JSON Format (`tables.json`):**
```json
[
  {
    "table_id": "uuid...",
    "sheet": "Sheet1",
    "bbox": {"min_row": 4, "min_col": 1, ...},
    "columns": ["ID", "Name", "Date"],
    "rows": [
      {"ID": 1, "Name": "Alice", "Date": "2023-01-01"},
      ...
    ],
    "meta": {"header_row_relative_index": 0}
  }
]
```

**CSV Format:**
- Generates `uuid.csv` (data) and `uuid.meta.json` (metadata) for each identified table.

## Development

```bash
# Run tests
uv run pytest
```

## License
MIT
