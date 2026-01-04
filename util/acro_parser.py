import re
import pandas as pd
from collections import defaultdict
from typing import Dict, DefaultDict, List, Any, Optional
from util.data_model import AcroJudge, AcroPilot, AcroSequence

class CtxParser:
    # Regex to capture <TableID_Column>Value
    # Group 1: Table (judge, pilot, seq)
    # Group 2: ID (digits)
    # Group 3: Column Name
    # Group 4: Value
    LINE_REGEX = re.compile(r"^<([a-z]+)(\d+)_([a-z0-9]+)>(.*)$")

    def parse_file(self, file_content: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Parses raw .ctx string content into 3 DataFrames.
        """
        raw_data: DefaultDict[str, DefaultDict[int, Dict[str, str]]] = defaultdict(lambda: defaultdict(dict))

        # 1. First Pass: Extract key-values into nested dict
        for line in file_content.splitlines():
            line = line.strip()
            match = self.LINE_REGEX.match(line)
            if match:
                table, item_id, column, value = match.groups()
                # Store by Table -> ID -> Column
                raw_data[table][int(item_id)][column] = value.strip()

        # 2. Second Pass: Convert raw dicts to Pydantic 
        empty_dict: Dict[int, Dict[str, str]] = {}
        judges = self._process_judges(raw_data.get("judge", empty_dict))
        pilots = self._process_pilots(raw_data.get("pilot", empty_dict))
        sequences = self._process_sequences(raw_data.get("seq", empty_dict))

        return judges, pilots, sequences

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
    
    def raw_file_to_df(self, file_content: str) -> pd.DataFrame:
        return pd.DataFrame({"raw_content": file_content.splitlines()})