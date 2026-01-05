import re
import pandas as pd
from collections import defaultdict
from typing import Dict, DefaultDict, List, Any, Optional
from util.data_model import AcroJudge, AcroPilot, AcroSequence, AcroMark

class CtxParser:
    def raw_file_to_df(self, file_content: str) -> pd.DataFrame:
        return pd.DataFrame({"raw_content": file_content.splitlines()})

    def parse_file(self, file_content: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        # Regex to capture <TableID_Column>Value
        # Group 1: Table (judge, pilot, seq); Group 2: ID (digits); Group 3: Column Name; Group 4: Value
        LINE_REGEX = re.compile(r"^<([a-z]+)(\d+)_([a-z0-9]+)>(.*)$")

        # Regex for Marks <marks_01p031J07>Value
        # Group 1: Seq ID; Group 2: Pilot ID; Group 3: Judge ID; Group 4: Value
        MARKS_REGEX = re.compile(r"^<marks_(\d+)p(\d+)J(\d+)>(.*)$")

        raw_data: DefaultDict[str, DefaultDict[int, Dict[str, str]]] = defaultdict(lambda: defaultdict(dict))
        raw_marks: List[Dict[str, Any]] = []

        # 1. First Pass: Extract key-values into nested dict
        for line in file_content.splitlines():
            line = line.strip()

            # Try matching the Marks format first
            mark_match = MARKS_REGEX.match(line)
            if mark_match:
                s_id, p_id, j_id, val = mark_match.groups()
                raw_marks.append({
                    "sequence_id": int(s_id),
                    "pilot_id": int(p_id),
                    "judge_id": int(j_id),
                    "raw_value": val
                })
                continue # Skip to next line

            # Standard generic format
            match = LINE_REGEX.match(line)
            if match:
                table, item_id, column, value = match.groups()
                # Store by Table -> ID -> Column
                raw_data[table][int(item_id)][column] = value.strip()

        # 2. Second Pass: Convert raw dicts to Pydantic 
        empty_dict: Dict[int, Dict[str, str]] = {}
        judges = self._process_judges(raw_data.get("judge", empty_dict))
        pilots = self._process_pilots(raw_data.get("pilot", empty_dict))
        sequences = self._process_sequences(raw_data.get("seq", empty_dict))

        marks = self._process_marks(raw_marks)

        return judges, pilots, sequences, marks

    def _process_judges(self, data: Dict[int, Dict[str, str]]) -> pd.DataFrame:
        models: List[AcroJudge] = []
        for j_id, fields in data.items():
            # **fields to unpack, but Pydantic handles the validation
            models.append(AcroJudge(id=j_id, **fields))
        return self._to_df(models)

    def _process_pilots(self, data: Dict[int, Dict[str, str]]) -> pd.DataFrame:
        models: List[AcroPilot] = []
        for p_id, fields in data.items():
            models.append(AcroPilot(id=p_id, **fields))
        return self._to_df(models)

    def _process_sequences(self, data: Dict[int, Dict[str, str]]) -> pd.DataFrame:
        models: List[AcroSequence] = []
        for s_id, fields in data.items():
            # Apply specific parsers for complex columns
            if "flyorder" in fields:
                fields["flyorder"] = self._parse_flyorder(fields["flyorder"])
            if "judges" in fields:
                fields["judges"] = self._parse_seq_judges(fields["judges"])
            
            models.append(AcroSequence(id=s_id, **fields)) # type: ignore
        return self._to_df(models)

    def _to_df(self, models: List[Any]) -> pd.DataFrame:
        """Converts list of Pydantic models to Pandas DataFrame"""
        if not models:
            return pd.DataFrame()
        return pd.DataFrame([m.model_dump() for m in models])

    # --- Helpers for Complex Fixed-Width Fields ---

    def _parse_flyorder(self, value: str) -> str:
        """
        Input: "031030029" (Chunks of 3)
        Output: "31 - 30 - 29"
        """
        if not value: return ""
        # Chunk string into 3-character blocks
        pilots = [value[i:i+3] for i in range(0, len(value), 3)]
        clean_pilots = [str(int(p)) for p in pilots if p.isdigit()]
        return " - ".join(clean_pilots)

    def _parse_seq_judges(self, value: str) -> str:
        """
        Input: "05AC06AJ...                                   50AZ"
        Output: "05(AC), 06(AJ) | HZ: 50(AZ)"
        """
        if not value: return ""
        
        # Regex to find pairs like 05AC (2 digits, 2 letters)
        # This ignores the whitespace padding automatically
        assignments = re.findall(r"(\d{2})([A-Z]{2})", value)
        
        readable: List[str] = []
        hz_found: Optional[str] = None
        
        for num, role in assignments:
            # 50AZ usually denotes the HZ (Safety/Warmup) judge config in this format
            if num == "50":
                hz_found = f"HZ: {role}"
            else:
                readable.append(f"{int(num)}({role})")
        
        result = ", ".join(readable)
        if hz_found:
            result += f" | {hz_found}"
        return result
    
    def _process_marks(self, data: List[Dict[str, Any]]) -> pd.DataFrame:
        marks: List[AcroMark] = []
        
        for item in data:
            raw_val = item.pop("raw_value", "")
            
            mark_data = {
                "sequence_id": item["sequence_id"],
                "pilot_id": item["pilot_id"],
                "judge_id": item["judge_id"]
            }
            
            pos = 0
            
            # 1. Figures: 20 blocks of 2 chars
            for i in range(1, 21):
                chunk = raw_val[pos : pos + 2] 
                mark_data[f"fig{i:02d}"] = chunk.strip()
                pos += 2
                
            # 2. OAKs: 3 blocks of 2 chars
            for i in range(1, 4):
                chunk = raw_val[pos : pos + 2]
                mark_data[f"oak{i}"] = chunk.strip()
                pos += 2
                
            # 3. Penalties: 10 blocks of 3 chars
            for i in range(1, 11):
                chunk = raw_val[pos : pos + 3]
                mark_data[f"pen{i:02d}"] = chunk.strip()
                pos += 3

            marks.append(AcroMark(**mark_data))

        return self._to_df(marks)
    