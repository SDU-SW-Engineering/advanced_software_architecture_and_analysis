from pathlib import Path
from .experiment_launcher import ExperimentLauncher
from .analyzer_runner import AnalyzerRunner
from ..utils.results_archiver import ResultsArchiver

class Orchestrator:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)

        self.launcher = ExperimentLauncher(project_root)
        self.analyzer = AnalyzerRunner(str(self.project_root / "latency_analyzer"))
        self.archiver = ResultsArchiver(project_root)

    def run_scenario(self, scenario, n_events: int):
        print(f"Running scenario {scenario.id}")

        # Clean and reset environment first
        self.launcher.prepare_environment()

        # Start scenario
        self.launcher.start(scenario)

        # Wait until n heartbeats generated
        self.launcher.wait_for_events(n_events)

        # Run analysis
        self.analyzer.run()

        # Archive results
        archived_path = self.archiver.archive(scenario.id)
        print(f"Archived results to {archived_path}")

        # Clean containers again after scenario
        self.launcher.prepare_environment()

    def run_all(self, scenarios, n_events: int):
        for scenario in scenarios:
            self.run_scenario(scenario, n_events)
