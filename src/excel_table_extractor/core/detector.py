import uuid
from typing import List, Dict, Tuple, Any, Set
from .models import BoundingBox, TableCandidate
from .reader import StreamReader

class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, i):
        if i not in self.parent:
            self.parent[i] = i
        if self.parent[i] != i:
            self.parent[i] = self.find(self.parent[i])
        return self.parent[i]

    def union(self, i, j):
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            self.parent[root_i] = root_j
            return True
        return False

class TableDetector:
    def __init__(self, min_rows=2, min_cols=2):
        self.min_rows = min_rows
        self.min_cols = min_cols

    def detect(self, reader: StreamReader, sheet_name: str) -> List[TableCandidate]:
        uf = UnionFind()
        # active_segments: list of (start_col, end_col, component_id)
        active_segments: List[Tuple[int, int, str]] = []
        
        # component_stats: id -> {'min_r':, 'max_r':, 'min_c':, 'max_c':}
        # We only store stats for "root" ids ideally, or merge them later.
        # Easier to store for all created IDs, and merge at the end.
        stats: Dict[str, Dict[str, int]] = {}

        def create_component(r, c_start, c_end):
            cid = str(uuid.uuid4())
            stats[cid] = {
                'min_r': r, 'max_r': r,
                'min_c': c_start, 'max_c': c_end,
                'count': 0 # Optional
            }
            return cid

        def update_stats(cid, r, c_start, c_end):
            s = stats[cid]
            s['max_r'] = max(s['max_r'], r)
            s['min_c'] = min(s['min_c'], c_start)
            s['max_c'] = max(s['max_c'], c_end)

        for row_idx, row_values in reader.iter_sheet(sheet_name):
            # 1. Identify segments in current row
            current_segments = [] # (start, end)
            start = None
            for col_idx, val in enumerate(row_values, start=1):
                is_empty = val is None or (isinstance(val, str) and not val.strip())
                if not is_empty:
                    if start is None:
                        start = col_idx
                else:
                    if start is not None:
                        current_segments.append((start, col_idx - 1))
                        start = None
            if start is not None:
                current_segments.append((start, len(row_values)))

            # 2. Match with active segments
            new_active_segments = []
            
            for curr_start, curr_end in current_segments:
                overlapping_ids = set()
                
                # Check overlap with previous row segments
                # Two segments (s1, e1) and (s2, e2) overlap if s1 <= e2 and s2 <= e1
                # But we allow diagonal connectivity? Usually 8-connectivity.
                # Strictly 4-connectivity: overlap must be on column.
                # Let's use column overlap (vertical connectivity).
                
                for prev_start, prev_end, prev_id in active_segments:
                    if curr_start <= prev_end and prev_start <= curr_end:
                        overlapping_ids.add(uf.find(prev_id))
                
                if not overlapping_ids:
                    # New component
                    new_id = create_component(row_idx, curr_start, curr_end)
                    new_active_segments.append((curr_start, curr_end, new_id))
                else:
                    # Merge all overlapping components
                    root_id = list(overlapping_ids)[0]
                    for oid in list(overlapping_ids)[1:]:
                        uf.union(oid, root_id)
                        root_id = uf.find(root_id) # Update root after union
                    
                    # Update stats for the root
                    update_stats(root_id, row_idx, curr_start, curr_end)
                    new_active_segments.append((curr_start, curr_end, root_id))
            
            active_segments = new_active_segments

        # 3. Aggregation
        final_components = {}
        for cid, s in stats.items():
            root = uf.find(cid)
            if root not in final_components:
                final_components[root] = s.copy()
            else:
                # Merge stats
                tgt = final_components[root]
                tgt['min_r'] = min(tgt['min_r'], s['min_r'])
                tgt['max_r'] = max(tgt['max_r'], s['max_r'])
                tgt['min_c'] = min(tgt['min_c'], s['min_c'])
                tgt['max_c'] = max(tgt['max_c'], s['max_c'])

        # 4. Filter and Create Candidates
        candidates = []
        for cid, s in final_components.items():
            bbox = BoundingBox(s['min_r'], s['min_c'], s['max_r'], s['max_c'])
            
            # Basic filtering
            if bbox.height >= self.min_rows and bbox.width >= self.min_cols:
                candidates.append(TableCandidate(
                    id=cid,
                    sheet_name=sheet_name,
                    bbox=bbox,
                    confidence=1.0,
                    meta={}
                ))
        
        return candidates
