"""Summary statistics generator."""

from pathlib import Path
from typing import List, Dict
from collections import defaultdict
from ..models.event import Event


class SummaryGenerator:
    """Generate summary statistics for events."""
    
    @staticmethod
    def generate_summary(events: List[Event], output_path: Path) -> None:
        """
        Generate and write summary statistics to a file.
        
        Args:
            events: List of Event objects
            output_path: Path to output summary file
        """
        if not events:
            print("Warning: No events to summarize")
            return
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Group events by type
        events_by_type = defaultdict(list)
        for event in events:
            events_by_type[event.type].append(event)
        
        # Calculate statistics
        stats = {}
        for event_type, type_events in events_by_type.items():
            stats[event_type] = SummaryGenerator._calculate_stats(type_events)
        
        # Calculate global statistics
        stats['global'] = SummaryGenerator._calculate_stats(events)
        
        # Write summary to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("LATENCY ANALYSIS SUMMARY\n")
            f.write("=" * 80 + "\n\n")
            
            # Per-type statistics
            for event_type in sorted(events_by_type.keys()):
                type_stats = stats[event_type]
                f.write(f"Event Type: {event_type}\n")
                f.write("-" * 80 + "\n")
                f.write(f"  Total Events: {type_stats['count']}\n")
                f.write(f"  Average Scheduler Latency: {type_stats['avg_scheduler_latency']:.2f} ms "
                       f"({type_stats['avg_scheduler_latency']/1000:.3f} s)\n")
                f.write(f"  Average Machine Latency: {type_stats['avg_machine_latency']:.2f} ms "
                       f"({type_stats['avg_machine_latency']/1000:.3f} s)\n")
                f.write(f"  Average Total Latency: {type_stats['avg_total_latency']:.2f} ms "
                       f"({type_stats['avg_total_latency']/1000:.3f} s)\n")
                f.write("\n")
            
            # Global statistics
            global_stats = stats['global']
            f.write("=" * 80 + "\n")
            f.write("GLOBAL STATISTICS\n")
            f.write("=" * 80 + "\n")
            f.write(f"  Total Events (All Types): {global_stats['count']}\n")
            f.write(f"  Average Scheduler Latency: {global_stats['avg_scheduler_latency']:.2f} ms "
                   f"({global_stats['avg_scheduler_latency']/1000:.3f} s)\n")
            f.write(f"  Average Machine Latency: {global_stats['avg_machine_latency']:.2f} ms "
                   f"({global_stats['avg_machine_latency']/1000:.3f} s)\n")
            f.write(f"  Average Total Latency: {global_stats['avg_total_latency']:.2f} ms "
                   f"({global_stats['avg_total_latency']/1000:.3f} s)\n")
            f.write("=" * 80 + "\n")
        
        print(f"Summary statistics written to {output_path}")
        
        # Also print to console
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        for event_type in sorted(events_by_type.keys()):
            type_stats = stats[event_type]
            print(f"{event_type}: {type_stats['count']} events, "
                  f"Avg Total: {type_stats['avg_total_latency']/1000:.3f}s")
        print(f"GLOBAL: {global_stats['count']} events, "
              f"Avg Total: {global_stats['avg_total_latency']/1000:.3f}s")
        print("=" * 80 + "\n")
    
    @staticmethod
    def _calculate_stats(events: List[Event]) -> Dict[str, float]:
        """Calculate statistics for a list of events."""
        if not events:
            return {
                'count': 0,
                'avg_scheduler_latency': 0.0,
                'avg_machine_latency': 0.0,
                'avg_total_latency': 0.0
            }
        
        total_scheduler = sum(e.scheduler_latency for e in events)
        total_machine = sum(e.machine_latency for e in events)
        total_latency = sum(e.total_latency for e in events)
        count = len(events)
        
        return {
            'count': count,
            'avg_scheduler_latency': total_scheduler / count,
            'avg_machine_latency': total_machine / count,
            'avg_total_latency': total_latency / count
        }