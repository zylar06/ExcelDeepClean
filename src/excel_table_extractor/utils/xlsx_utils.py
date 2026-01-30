import zipfile
import xml.etree.ElementTree as ET
import os
import re
from typing import Dict, List, Tuple
from openpyxl.utils.cell import range_boundaries

class XlsxMergeParser:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.ns = {
            'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
            'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
            'pkg_rels': 'http://schemas.openxmlformats.org/package/2006/relationships'
        }

    def parse(self) -> Dict[str, List[Tuple[int, int, int, int]]]:
        """
        Returns a dictionary mapping sheet names to a list of merged cell ranges.
        Each range is (min_col, min_row, max_col, max_row).
        Note: openpyxl range_boundaries returns (min_col, min_row, max_col, max_row).
        """
        merged_cells = {}
        
        with zipfile.ZipFile(self.file_path, 'r') as z:
            # 1. Get sheet mapping from workbook.xml
            sheet_mapping = self._get_sheet_mapping(z)
            
            # 2. Get relationships to find file paths
            rels = self._get_workbook_rels(z)
            
            # 3. Parse each sheet
            for sheet_name, rId in sheet_mapping.items():
                target_path = rels.get(rId)
                if not target_path:
                    continue
                
                # Target path in rels is usually relative to xl/
                # e.g., "worksheets/sheet1.xml" -> "xl/worksheets/sheet1.xml"
                if target_path.startswith('/'):
                    xml_path = target_path[1:]
                else:
                    xml_path = f"xl/{target_path}"
                
                if xml_path not in z.namelist():
                    # Try correcting path if needed
                    # Sometimes it might be just "worksheets/sheet1.xml" and zip has "xl/worksheets/sheet1.xml"
                    # But usually "xl/" prefix is standard.
                    pass

                merged_cells[sheet_name] = self._parse_sheet_merged_cells(z, xml_path)
                
        return merged_cells

    def _get_sheet_mapping(self, z: zipfile.ZipFile) -> Dict[str, str]:
        """Returns {sheet_name: rId}"""
        mapping = {}
        try:
            with z.open('xl/workbook.xml') as f:
                tree = ET.parse(f)
                root = tree.getroot()
                sheets = root.find('main:sheets', self.ns)
                if sheets is not None:
                    for sheet in sheets.findall('main:sheet', self.ns):
                        name = sheet.get('name')
                        rId = sheet.get(f"{{{self.ns['r']}}}id")
                        mapping[name] = rId
        except KeyError:
            pass # Handle case where structure is different
        return mapping

    def _get_workbook_rels(self, z: zipfile.ZipFile) -> Dict[str, str]:
        """Returns {rId: target_path}"""
        rels = {}
        try:
            with z.open('xl/_rels/workbook.xml.rels') as f:
                tree = ET.parse(f)
                root = tree.getroot()
                # The .rels file uses the package relationships namespace
                for rel in root.findall('pkg_rels:Relationship', self.ns):
                    rId = rel.get('Id')
                    target = rel.get('Target')
                    rels[rId] = target
        except KeyError:
            pass
        return rels

    def _parse_sheet_merged_cells(self, z: zipfile.ZipFile, xml_path: str) -> List[Tuple[int, int, int, int]]:
        ranges = []
        try:
            with z.open(xml_path) as f:
                # Streaming XML parser to avoid loading full DOM for large sheets
                for event, elem in ET.iterparse(f, events=('start', 'end')):
                    if event == 'end' and elem.tag.endswith('mergeCell'):
                        ref = elem.get('ref')
                        if ref:
                            # min_col, min_row, max_col, max_row
                            ranges.append(range_boundaries(ref))
                        elem.clear()
        except KeyError:
            pass
        return ranges

def get_merged_cells(file_path: str) -> Dict[str, List[Tuple[int, int, int, int]]]:
    parser = XlsxMergeParser(file_path)
    return parser.parse()
