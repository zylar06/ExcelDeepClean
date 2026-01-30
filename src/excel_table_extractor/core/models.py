from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict

@dataclass
class BoundingBox:
    min_row: int
    min_col: int
    max_row: int
    max_col: int
    
    @property
    def height(self):
        return self.max_row - self.min_row + 1
        
    @property
    def width(self):
        return self.max_col - self.min_col + 1
        
    @property
    def area(self):
        return self.height * self.width

@dataclass
class TableCandidate:
    id: str
    sheet_name: str
    bbox: BoundingBox
    confidence: float
    meta: Dict[str, Any]

@dataclass
class ExtractedTable:
    table_id: str
    sheet_name: str
    bbox: BoundingBox
    columns: List[str]
    rows: List[Dict[str, Any]]
    meta: Dict[str, Any] = field(default_factory=dict)
