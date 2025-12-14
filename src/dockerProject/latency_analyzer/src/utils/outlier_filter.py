"""Outlier filtering utility."""

from typing import List
from ..models.event import Event


class OutlierFilter:
    """Filter outliers from events based on latency thresholds."""
    
    LATENCY_THRESHOLD_MS = 20000  # 20 seconds in milliseconds
    
    @staticmethod
    def filter_outliers(events: List[Event]) -> List[Event]:
        """
        Filter out events with scheduler or machine latency > 20 seconds.
        
        Args:
            events: List of Event objects
            
        Returns:
            Filtered list of Event objects
        """
        filtered_events = []
        outlier_count = 0
        
        for event in events:
            if (event.scheduler_latency > OutlierFilter.LATENCY_THRESHOLD_MS or 
                event.machine_latency > OutlierFilter.LATENCY_THRESHOLD_MS):
                outlier_count += 1
                continue
            
            filtered_events.append(event)
        
        if outlier_count > 0:
            print(f"Filtered out {outlier_count} outlier(s) with latency > 20 seconds")
        
        return filtered_events
    
    @staticmethod
    def renumber_events_by_type(events: List[Event]) -> List[Event]:
        """
        Renumber events to fill gaps after outlier removal.
        
        Args:
            events: List of Event objects (after filtering)
            
        Returns:
            List of Event objects with renumbered IDs
        """
        # Group events by type
        events_by_type = {}
        for event in events:
            if event.type not in events_by_type:
                events_by_type[event.type] = []
            events_by_type[event.type].append(event)
        
        # Renumber each type
        renumbered_events = []
        
        for event_type, type_events in events_by_type.items():
            # Sort by trigger_ts to maintain chronological order
            type_events.sort(key=lambda e: e.trigger_ts)
            
            if event_type == 'newMachine':
                # For new machine events, global counter
                for i, event in enumerate(type_events, 1):
                    machine_id = event.id.split('-')[0][2:]  # Extract machine ID
                    event.id = f"nM{machine_id}-{i:03d}"
                    renumbered_events.append(event)
            
            elif event_type == 'machineFailure':
                # For machine failure, counter per failed machine
                counters = {}
                for event in type_events:
                    machine_id = event.id.split('-')[0][2:]  # Extract machine ID
                    if machine_id not in counters:
                        counters[machine_id] = 1
                    event.id = f"mF{machine_id}-{counters[machine_id]:03d}"
                    counters[machine_id] += 1
                    renumbered_events.append(event)
            
            elif event_type == 'storageAlert':
                # For storage alerts, simple sequential numbering
                for i, event in enumerate(type_events, 1):
                    event.id = f"sA-{i:03d}"
                    renumbered_events.append(event)
        
        return renumbered_events