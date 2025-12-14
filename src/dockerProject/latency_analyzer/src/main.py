"""Main entry point for latency analyzer."""

from pathlib import Path
from src.parsers.jsonl_parser import JSONLParser
from src.analyzers.new_machine_analyzer import NewMachineAnalyzer
from src.analyzers.machine_failure_analyzer import MachineFailureAnalyzer
from src.analyzers.storage_alert_analyzer import StorageAlertAnalyzer
from src.utils.outlier_filter import OutlierFilter
from src.utils.csv_writer import CSVWriter
from src.utils.summary_generator import SummaryGenerator


def main():
    """Main execution function."""
    print("=" * 80)
    print("LATENCY ANALYZER")
    print("=" * 80)
    print()
    
    # Define paths
    input_dir = Path("collector_output")
    output_dir = Path("final_results")
    
    print(f"Input directory: {input_dir.absolute()}")
    print(f"Output directory: {output_dir.absolute()}")
    print()
    
    # Parse input files
    print("Parsing JSONL files...")
    filenames = ['heartbeats.jsonl', 'productionPlan.jsonl', 'storageAlerts.jsonl']
    parsed_data = JSONLParser.parse_directory(input_dir, filenames)
    
    heartbeats = parsed_data.get('heartbeats.jsonl', [])
    production_plan = parsed_data.get('productionPlan.jsonl', [])
    storage_alerts = parsed_data.get('storageAlerts.jsonl', [])
    
    print()
    
    # Analyze events
    print("Analyzing events...")
    
    # New Machine events
    print("  - Analyzing new machine events...")
    nm_analyzer = NewMachineAnalyzer(heartbeats, production_plan)
    new_machine_events = nm_analyzer.analyze()
    print(f"    Found {len(new_machine_events)} new machine events")
    
    # Machine Failure events
    print("  - Analyzing machine failure events...")
    mf_analyzer = MachineFailureAnalyzer(heartbeats, production_plan)
    machine_failure_events = mf_analyzer.analyze()
    print(f"    Found {len(machine_failure_events)} machine failure events")
    
    # Storage Alert events
    print("  - Analyzing storage alert events...")
    sa_analyzer = StorageAlertAnalyzer(storage_alerts, production_plan)
    storage_alert_events = sa_analyzer.analyze()
    print(f"    Found {len(storage_alert_events)} storage alert events")
    
    print()
    
    # Combine all events
    all_events = new_machine_events + machine_failure_events + storage_alert_events
    print(f"Total events found: {len(all_events)}")
    print()
    
    # Filter outliers
    print("Filtering outliers (latency > 20 seconds)...")
    filtered_events = OutlierFilter.filter_outliers(all_events)
    print(f"Events after filtering: {len(filtered_events)}")
    print()
    
    # Renumber events to fill gaps
    print("Renumbering events...")
    final_events = OutlierFilter.renumber_events_by_type(filtered_events)
    print()
    
    # Write CSV
    csv_output = output_dir / "events.csv"
    print(f"Writing events to CSV: {csv_output}")
    CSVWriter.write_events(final_events, csv_output)
    print()
    
    # Generate summary
    summary_output = output_dir / "summary.txt"
    print(f"Generating summary: {summary_output}")
    SummaryGenerator.generate_summary(final_events, summary_output)
    print()
    
    print("=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()