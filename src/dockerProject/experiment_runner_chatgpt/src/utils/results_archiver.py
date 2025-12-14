import shutil
import time
from pathlib import Path

class ResultsArchiver:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)

    def archive(self, scenario_id: str):
        timestamp = int(time.time() * 1000)
        dest = self.project_root / "final_results" / f"{scenario_id}_{timestamp}"
        dest.mkdir(parents=True, exist_ok=True)

        # Copy .jsonl
        src_jsonl_dir = self.project_root / "collector_output"
        for filename in ["heartbeats.jsonl", "productionPlan.jsonl", "storageAlerts.jsonl"]:
            shutil.copy(src_jsonl_dir / filename, dest)

        # Copy analyzer output
        src_final_dir = self.project_root / "final_results"
        for filename in ["events.csv", "summary.txt"]:
            shutil.copy(src_final_dir / filename, dest)

        return dest
