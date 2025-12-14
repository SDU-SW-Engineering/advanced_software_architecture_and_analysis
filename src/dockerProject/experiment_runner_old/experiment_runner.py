
"""
Experiment Runner: Orchestrates all scenarios, manages container lifecycle, runs EventProcessor
"""

import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# ----------------------------------------------------------------------------------
# Optional import fix: ensure ./eventProcessor is on PYTHONPATH so imports resolve.
# We keep this defensive even if the runner doesn't strictly need these modules,
# because some versions of the runner (or downstream code) may import them.
# ----------------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parent.parent            # dockerProject/
EVENT_PROCESSOR_DIR = PROJECT_ROOT / "eventProcessor"

if EVENT_PROCESSOR_DIR.exists() and str(EVENT_PROCESSOR_DIR) not in sys.path:
    sys.path.insert(0, str(EVENT_PROCESSOR_DIR))

# Optional: if some runner versions import these, the path is now fixed.
try:
    from event_definitions import Event, EventType, ReactionType  # noqa: F401
except Exception:
    # Not strictly required by the runner itself; continue without failing.
    pass

# Your scenario model (unchanged)
from scenario_config import get_all_scenarios, Scenario

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
LOGGER = logging.getLogger(__name__)


class ExperimentRunner:
    """Orchestrates experiment execution"""

    def __init__(self,
                 project_root: Path,
                 n_events_per_scenario: int = 100,
                 n_runs_per_scenario: int = 3,
                 results_dir: Optional[Path] = None):
        """
        Initialize experiment runner.
        Args:
            project_root: Root of dockerProject directory
            n_events_per_scenario: Target *correlated events* per scenario (default 100)
            n_runs_per_scenario: Runs per scenario (default 3)
            results_dir: Where to save results (default: project_root/results)
        """
        self.project_root = Path(project_root)
        self.n_events = n_events_per_scenario
        self.n_runs = n_runs_per_scenario
        self.results_dir = results_dir or (self.project_root / 'results')
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.collector_output_dir = self.project_root / 'collector_output'

        # NEW: Raw message target (5 × requested events)
        self.raw_message_target = 30 * self.n_events

        LOGGER.info("ExperimentRunner initialized:")
        LOGGER.info(f" Project root          : {self.project_root}")
        LOGGER.info(f" Events per scenario   : {self.n_events}")
        LOGGER.info(f" Raw message target    : {self.raw_message_target}")
        LOGGER.info(f" Runs per scenario     : {self.n_runs}")
        LOGGER.info(f" Results directory     : {self.results_dir}")

    # ----------------------------------------------------------------------------------
    # Orchestration
    # ----------------------------------------------------------------------------------

    def run_all_scenarios(self) -> dict:
        """
        Run all scenarios with all runs.
        Returns: Summary dict with results metadata.
        """
        # If you want dynamic scenarios, re-enable the next line:
        # scenarios = get_all_scenarios()
        # For now, keep the single baseline scenario, as in your existing runner:
        scenario = Scenario(
            id="3m_2k",
            num_cutting_machines=3,
            max_killable_machines=2,
            max_killable_schedulers=1,
            description="3 machines, max 2 kill per time"
        )

        summary = {
            "started_at": datetime.now().isoformat(),
            "n_events_per_scenario": self.n_events,
            "n_runs_per_scenario": self.n_runs,
            "scenarios_completed": [],
            "scenarios_failed": []
        }

        LOGGER.info(f"\n{'='*80}")
        LOGGER.info(f"Scenario: {scenario.id} - {scenario.description}")
        LOGGER.info(f"{'='*80}")

        try:
            self._run_scenario(scenario)
            summary["scenarios_completed"].append(scenario.id)
        except Exception as e:
            LOGGER.error(f"Scenario {scenario.id} FAILED: {e}")
            summary["scenarios_failed"].append({
                "scenario_id": scenario.id,
                "error": str(e)
            })

        summary["completed_at"] = datetime.now().isoformat()
        summary_path = self.results_dir / 'experiment_summary.json'
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)

        LOGGER.info(f"\n{'='*80}")
        LOGGER.info("EXPERIMENT COMPLETE")
        LOGGER.info(f" Completed: {len(summary['scenarios_completed'])} scenarios")
        LOGGER.info(f" Failed   : {len(summary['scenarios_failed'])} scenarios")
        LOGGER.info(f" Results  : {self.results_dir}")
        LOGGER.info(f"{'='*80}\n")

        return summary

    def _run_scenario(self, scenario: Scenario):
        """Run a single scenario with all runs"""
        for run_num in range(1, self.n_runs + 1):
            LOGGER.info(f"\nRun {run_num}/{self.n_runs}")
            self._run_scenario_iteration(scenario, run_num)

    def _run_scenario_iteration(self, scenario: Scenario, run_num: int):
        """Execute single scenario run"""
        # 1. Clean up
        LOGGER.info("Cleaning up previous containers...")
        self._cleanup_containers()
        time.sleep(2)

        # 2. Start docker-compose
        LOGGER.info("Starting docker-compose services...")
        self._start_services(scenario)

        # 3. Wait for Kafka ready
        LOGGER.info("Waiting for Kafka to be ready...")
        self._wait_for_kafka()

        # 4. Clear collector output
        LOGGER.info("Clearing collector output...")
        self._clear_collector_output()

        # 5. Start KafkaCollector
        LOGGER.info("Starting KafkaCollector...")
        self._start_kafka_collector()
        time.sleep(2)

        # 6. Start ChaosPanda with scenario parameters
        LOGGER.info(f"Starting ChaosPanda (max_kill_machines={scenario.max_killable_machines})...")
        self._start_chaos_panda(scenario)

        # 7. Wait for raw messages (target = 5 × n_events)
        LOGGER.info(f"Waiting for {self.raw_message_target} raw messages (target for {self.n_events} events)...")
        self._wait_for_events(scenario, timeout=10800)  # NEW: increased timeout to 10800s

        # 8. Stop all containers
        LOGGER.info("Stopping containers...")
        self._stop_services()
        time.sleep(5)

        # 9. Run EventProcessor
        LOGGER.info("Running EventProcessor...")
        output_csv = self._run_event_processor(scenario, run_num)
        LOGGER.info(f"Run {run_num} complete: {output_csv}")

    # ----------------------------------------------------------------------------------
    # Container lifecycle
    # ----------------------------------------------------------------------------------

    def _cleanup_containers(self):
        """Remove old containers and volumes"""
        try:
            result = subprocess.run(
                ["docker-compose", "down", "-v"],
                cwd=self.project_root,
                capture_output=True,
                timeout=30
            )
            if result.returncode != 0:
                LOGGER.warning(f"docker-compose down returned {result.returncode}: "
                               f"{result.stderr.decode() if result.stderr else ''}")
        except subprocess.TimeoutExpired:
            LOGGER.warning("docker-compose down timed out")
        except Exception as e:
            LOGGER.warning(f"Error cleaning up: {e}")

    def _start_services(self, scenario: Scenario):
        """Start docker-compose with scenario-specific environment"""
        env = {
            "CUTTING_MACHINES": str(scenario.num_cutting_machines),
            "SCENARIO_ID": scenario.id,
        }
        try:
            result = subprocess.run(
                ["docker-compose", "up", "-d"],
                cwd=self.project_root,
                capture_output=True,
                timeout=120,
                env={**subprocess.os.environ, **env}
            )
            if result.returncode != 0:
                raise RuntimeError(f"docker-compose up failed: "
                                   f"{result.stderr.decode() if result.stderr else 'Unknown error'}")
            LOGGER.info("Services started")
        except Exception as e:
            LOGGER.error(f"Failed to start services: {e}")
            raise

    def _stop_services(self):
        """Stop all services and cleanup temp containers"""
        try:
            # Stop docker-compose
            subprocess.run(
                ["docker-compose", "stop"],
                cwd=self.project_root,
                capture_output=True,
                timeout=60
            )
            # Stop and remove kafka-collector-temp and chaospanda-temp
            for container in ["kafka-collector-temp", "chaospanda-temp"]:
                try:
                    subprocess.run(["docker", "stop", container],
                                   capture_output=True, timeout=10)
                    subprocess.run(["docker", "rm", container],
                                   capture_output=True, timeout=10)
                    LOGGER.info(f"Removed {container}")
                except Exception:
                    pass
            time.sleep(2)
        except Exception as e:
            LOGGER.warning(f"Error stopping services: {e}")

    # ----------------------------------------------------------------------------------
    # Environment readiness
    # ----------------------------------------------------------------------------------

    def _wait_for_kafka(self, timeout: int = 60):
        """Wait for Kafka to be ready"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(
                    ["docker", "exec", "kafka", "kafka-topics",
                     "--list", "--bootstrap-server", "localhost:9092"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    LOGGER.info("Kafka is ready")
                    return
            except Exception:
                pass
            time.sleep(2)
        raise RuntimeError(f"Kafka not ready after {timeout} seconds")

    def _clear_collector_output(self):
        """Clear previous collector output"""
        import shutil
        if self.collector_output_dir.exists():
            shutil.rmtree(self.collector_output_dir)
        self.collector_output_dir.mkdir(parents=True, exist_ok=True)

    def _start_kafka_collector(self):
        """Start KafkaCollector container"""
        try:
            subprocess.run(
                [
                    "docker", "run", "-d",
                    "--name", "kafka-collector-temp",
                    "--network", "dockerproject_mynetwork",
                    "-v", f"{self.collector_output_dir.resolve()}:/app/collector_output",
                    "-e", "KAFKA_BOOTSTRAP_SERVERS=kafka:29092",
                    "-e", "PYTHONUNBUFFERED=1",
                    "kafka-collector:latest",
                    "python", "kafka_collector.py"
                ],
                capture_output=True,
                timeout=10
            )
        except Exception as e:
            LOGGER.warning(f"Could not start kafka-collector: {e}")

    def _start_chaos_panda(self, scenario: Scenario):
        """Start ChaosPanda with scenario parameters"""
        # Ensure Docker socket is accessible
        try:
            import os
            docker_socket = "/var/run/docker.sock"
            if os.path.exists(docker_socket):
                # Try to make readable (may require sudo)
                os.system(f"sudo chmod 666 {docker_socket} 2>/dev/null || true")
                LOGGER.debug("Docker socket permissions adjusted")
        except Exception as e:
            LOGGER.warning(f"Could not adjust Docker socket permissions: {e}")

        try:
            subprocess.run(
                [
                    "docker", "run", "-d",
                    "--name", "chaospanda-temp",
                    "--network", "dockerproject_mynetwork",
                    "-v", "/var/run/docker.sock:/var/run/docker.sock",
                    "--user", "root",
                    "--group-add", "0",
                    "-e", "PYTHONUNBUFFERED=1",
                    "-e", f"SCENARIO_ID={scenario.id}",
                    "chaospanda:latest",
                    "python", "main.py",
                    "--max-cutting-machines", str(scenario.max_killable_machines),
                    "--max-schedulers", str(scenario.max_killable_schedulers),
                    "--kafka-bootstrap", "kafka:29092",
                    "--redis-host", "redis",
                    "--redis-port", "6379",
                    "--test-name", scenario.id
                ],
                capture_output=True,
                timeout=10
            )
            LOGGER.info("ChaosPanda started")
        except Exception as e:
            LOGGER.warning(f"ChaosPanda startup warning: {e}")
            # Don't fail - continue without chaos if it doesn't start

    # ----------------------------------------------------------------------------------
    # Waiting for messages (raw)
    # ----------------------------------------------------------------------------------

    def _wait_for_events(self, scenario: Scenario, timeout: int = 1800):
        """
        Wait for raw messages or timeout.
        NEW: Increased timeout to 1800s and target raw_message_count = 5 * n_events.
        """
        start_time = time.time()
        last_count = 0
        no_progress_time = 0

        while time.time() - start_time < timeout:
            raw_count = self._check_collector_file_growth()
            if raw_count >= self.raw_message_target:
                LOGGER.info(f"Reached {raw_count} raw messages (target {self.raw_message_target}), stopping experiment")
                break

            if raw_count > last_count:
                last_count = raw_count
                no_progress_time = 0
            else:
                no_progress_time += 5
                if no_progress_time > 60:
                    LOGGER.warning("No new messages for 60 seconds, continuing ...")
                    no_progress_time = 0

            LOGGER.info(f"Raw message count: {raw_count}/{self.raw_message_target}")
            time.sleep(5)

        if self._check_collector_file_growth() < self.raw_message_target:
            LOGGER.warning(f"Timeout: only {raw_count}/{self.raw_message_target} raw messages collected")

    def _check_collector_file_growth(self) -> int:
        """Estimate raw message count from collector files"""
        total_lines = 0
        for jsonl_file in self.collector_output_dir.glob('*.jsonl'):
            try:
                with open(jsonl_file) as f:
                    total_lines += sum(1 for _ in f)
            except Exception:
                pass
        return total_lines

    # ----------------------------------------------------------------------------------
    # EventProcessor
    # ----------------------------------------------------------------------------------

    def _run_event_processor(self, scenario: Scenario, run_num: int) -> Path:
        """
        Run the offline EventProcessor to generate CSV.
        Keeps the original behavior: run in the eventProcessor directory,
        pass the collector_output dir and the requested limit (n_events).
        """
        output_csv = self.results_dir / f"results_scenario_{scenario.id}_run{run_num}.csv"
        event_processor_dir = self.project_root / 'eventProcessor'
        try:
            result = subprocess.run(
                [
                    sys.executable, "event_processor.py",
                    "--collector-output", str(self.collector_output_dir),
                    "--output-csv", str(output_csv),
                    "--limit", str(self.n_events),
                    "--summary"
                ],
                cwd=event_processor_dir,
                capture_output=True,
                timeout=60,
                env={**subprocess.os.environ}
            )
            if result.returncode != 0:
                error_msg = result.stderr.decode() if result.stderr else "Unknown error"
                raise RuntimeError(f"EventProcessor failed: {error_msg}")
            LOGGER.info(f"EventProcessor complete: {output_csv}")
            return output_csv
        except subprocess.TimeoutExpired:
            raise RuntimeError("EventProcessor timeout after 60 seconds")
        except Exception as e:
            LOGGER.error(f"EventProcessor error: {e}")
            raise


def main():
    """Main entry point"""
    import argparse
    parser = argparse.ArgumentParser(
        description="Run modifiability experiment for pasta production system"
    )
    parser.add_argument(
        '--project-root',
        type=str,
        default='.',
        help='Path to dockerProject directory (default: current directory)'
    )
    parser.add_argument(
        '--nEvents',
        type=int,
        default=100,
        help='Target correlated events per scenario (default: 100)'
    )
    parser.add_argument(
        '--nRuns',
        type=int,
        default=3,
        help='Runs per scenario (default: 3)'
    )
    parser.add_argument(
        '--results-dir',
        type=str,
        help='Results directory (default: PROJECT_ROOT/results)'
    )
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    if not project_root.exists():
        LOGGER.error(f"Project root not found: {project_root}")
        sys.exit(1)

    results_dir = Path(args.results_dir) if args.results_dir else None
    try:
        runner = ExperimentRunner(
            project_root=project_root,
            n_events_per_scenario=args.nEvents,
            n_runs_per_scenario=args.nRuns,
            results_dir=results_dir
        )
        runner.run_all_scenarios()
        sys.exit(0)
    except Exception as e:
        LOGGER.error(f"Experiment failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
