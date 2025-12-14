import subprocess
from pathlib import Path

class AnalyzerRunner:
    def __init__(self, analyzer_path: str):
        self.analyzer_path = Path(analyzer_path)

    def run(self):
        # Ensure the image exists
        subprocess.run(
            ["docker", "build", "-t", "latency-analyzer", "."],
            cwd=self.analyzer_path,
            check=True
        )

        subprocess.run(
            [
                "docker", "run",
                "-v", f"{self.analyzer_path.parent}/collector_output:/app/collector_output",
                "-v", f"{self.analyzer_path.parent}/final_results:/app/final_results",
                "latency-analyzer"
            ],
            check=True
        )
