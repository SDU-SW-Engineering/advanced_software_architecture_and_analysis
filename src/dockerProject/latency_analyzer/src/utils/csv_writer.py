"""CSV writer utility."""

import csv
from pathlib import Path
from typing import List
from ..models.event import Event


class CSVWriter:
    """Write events to CSV file."""
    
    @staticmethod
    def write_events(events: List[Event], output_path: Path) -> None:
        """
        Write events to a CSV file.
        
        Args:
            events: List of Event objects
            output_path: Path to output CSV file
        """
        if not events:
            print("Warning: No events to write to CSV")
            return
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Sort events by trigger timestamp
        sorted_events = sorted(events, key=lambda e: e.trigger_ts)
        
        fieldnames = [
            'id', 'type', 'trigger_ts', 'reaction_ts', 'solved_ts',
            'scheduler_latency', 'machine_latency'
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for event in sorted_events:
                writer.writerow(event.to_dict())
        
        print(f"Written {len(sorted_events)} events to {output_path}")