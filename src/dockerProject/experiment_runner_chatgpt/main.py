import argparse
from pathlib import Path
from src.scenarios.list_of_scenarios import SCENARIOS
from src.runner.orchestrator import Orchestrator

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=int, required=True, help="Number of events to wait for")
    args = parser.parse_args()

    project_root = str(Path(__file__).resolve().parent.parent)
    orchestrator = Orchestrator(project_root)

    orchestrator.run_all(SCENARIOS, args.events)

if __name__ == "__main__":
    main()
