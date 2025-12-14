# Latency Analyzer

A Python application that analyzes latency events from JSONL files, identifying three types of events: new machine, machine failure, and storage alert events.

## Features

- **Event Detection**: Identifies three types of events from JSONL data
  - New Machine events
  - Machine Failure events
  - Storage Alert events
- **Outlier Filtering**: Removes events with latency > 20 seconds
- **CSV Export**: Generates a comprehensive CSV file with all events
- **Summary Statistics**: Produces detailed statistics per event type and globally
- **Separation of Concerns**: Clean architecture with modular components

## Project Structure

```
latency_analyser/
├── src/
│   ├── models/
│   │   ├── __init__.py
│   │   └── event.py              # Event data model
│   ├── parsers/
│   │   ├── __init__.py
│   │   └── jsonl_parser.py       # JSONL file parser
│   ├── analyzers/
│   │   ├── __init__.py
│   │   ├── new_machine_analyzer.py
│   │   ├── machine_failure_analyzer.py
│   │   └── storage_alert_analyzer.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── outlier_filter.py    # Outlier detection and filtering
│   │   ├── csv_writer.py        # CSV export utility
│   │   └── summary_generator.py # Statistics generation
│   └── __init__.py
├── Dockerfile
├── requirements.txt
├── main.py                       # Entry point
└── README.md
```

## Usage

### With Docker (Recommended)

1. Build the Docker image:
```bash
cd latency_analyser
docker build -t latency-analyzer .
```

2. Run the analyzer:
```bash
docker run -v $(pwd)/../collector_output:/app/collector_output \
           -v $(pwd)/../final_results:/app/final_results \
           latency-analyzer
```

### Without Docker

1. Ensure Python 3.11+ is installed

2. Run the analyzer:
```bash
cd latency_analyser
python main.py
```

## Input

The analyzer expects the following JSONL files in `../collector_output/`:
- `heartbeats.jsonl`
- `productionPlan.jsonl`
- `storageAlerts.jsonl`

## Output

The analyzer generates two files in `../final_results/`:

1. **events.csv**: Complete list of all events with columns:
   - id
   - type
   - trigger_ts
   - reaction_ts
   - solved_ts
   - scheduler_latency
   - machine_latency

2. **summary.txt**: Statistical summary including:
   - Event counts per type and globally
   - Average scheduler latency per type and globally
   - Average machine latency per type and globally
   - Average total latency per type and globally

## Event Types

### New Machine Events
- Triggered by `AssignBlade` messages
- Identifies machine startup and blade assignment
- ID format: `nM{machineId}-{counter}`

### Machine Failure Events
- Triggered by `SwapBlade` with `machineFailure` context
- Tracks blade swaps due to machine failures
- ID format: `mF{failedMachineId}-{counter}`

### Storage Alert Events
- Triggered by storage level alerts
- Results in blade swaps or fresh amount changes
- ID format: `sA-{counter}`

## Architecture

The project follows the **Separation of Concerns** principle:

- **Models**: Data structures (Event)
- **Parsers**: Input file handling (JSONL parsing)
- **Analyzers**: Event-specific identification logic
- **Utils**: Cross-cutting concerns (filtering, export, statistics)

## License

This project is for internal use.