"""JSONL file parser."""

import json
from pathlib import Path
from typing import List, Dict, Any


class JSONLParser:
    """Parser for JSONL files."""
    
    @staticmethod
    def parse_file(filepath: Path) -> List[Dict[str, Any]]:
        """
        Parse a JSONL file and return list of records.
        
        Args:
            filepath: Path to the JSONL file
            
        Returns:
            List of parsed JSON records
        """
        records = []
        
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    record = json.loads(line)
                    records.append(record)
                except json.JSONDecodeError as e:
                    print(f"Warning: Failed to parse line {line_num} in {filepath.name}: {e}")
                    continue
        
        return records
    
    @staticmethod
    def parse_directory(directory: Path, filenames: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse multiple JSONL files from a directory.
        
        Args:
            directory: Path to the directory containing JSONL files
            filenames: List of filenames to parse
            
        Returns:
            Dictionary mapping filename to list of records
        """
        parsed_data = {}
        
        for filename in filenames:
            filepath = directory / filename
            try:
                parsed_data[filename] = JSONLParser.parse_file(filepath)
                print(f"Parsed {len(parsed_data[filename])} records from {filename}")
            except FileNotFoundError as e:
                print(f"Warning: {e}")
                parsed_data[filename] = []
        
        return parsed_data