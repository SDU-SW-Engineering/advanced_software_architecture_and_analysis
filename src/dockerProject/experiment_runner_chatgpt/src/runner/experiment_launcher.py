import subprocess
import time
from pathlib import Path
import os
import shutil

class ExperimentLauncher:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.collector_output_dir = self.project_root / "collector_output"
        self.heartbeats_file = self.collector_output_dir / "heartbeats.jsonl"

        # This must match your compose network name
        # e.g. dockerproject_mynetwork
        self.compose_network = "dockerproject_mynetwork"

    # ----------------------------------------------------------------------
    # ENVIRONMENT PREPARATION
    # ----------------------------------------------------------------------
    def prepare_environment(self):
        # Kill absolutely everything
        subprocess.run("docker kill $(docker ps -q)", shell=True)

        # Remove stopped containers, networks, volumes produced by compose
        subprocess.run(
            ["docker", "compose", "down", "-v"],
            cwd=self.project_root,
            check=False
        )

        # Clean collector output files
        if self.collector_output_dir.exists():
            for f in self.collector_output_dir.iterdir():
                if f.is_file():
                    f.unlink()

    # ----------------------------------------------------------------------
    # STARTUP PIPELINE
    # ----------------------------------------------------------------------
    def start(self, scenario):
        self._write_env_file(scenario)

        # Start your main simulation services
        subprocess.run(
            ["docker", "compose", "up", "-d"],
            cwd=self.project_root,
            check=True
        )

        time.sleep(2)

        # Then start KafkaCollector external container
        self._start_kafka_collector()

        time.sleep(2)

        # Then start ChaosPanda last
        self._start_chaos_panda(scenario)

    # ----------------------------------------------------------------------
    # KAFKA COLLECTOR
    # ----------------------------------------------------------------------
    def _start_kafka_collector(self):
        collector_path = self.collector_output_dir.resolve()

        subprocess.run(
            [
                "docker", "run", "-d",
                "--name", "kafka-collector-temp",
                "--network", self.compose_network,
                "-v", f"{collector_path}:/app/collector_output",
                "-e", "KAFKA_BOOTSTRAP_SERVERS=kafka:29092",
                "-e", "PYTHONUNBUFFERED=1",
                "kafka-collector:latest",
                "python", "kafka_collector.py"
            ],
            capture_output=True
        )

    # ----------------------------------------------------------------------
    # CHAOS PANDA
    # ----------------------------------------------------------------------
    def _start_chaos_panda(self, scenario):
        # Adjust docker socket permissions if necessary
        docker_socket = "/var/run/docker.sock"
        if os.path.exists(docker_socket):
            os.system(f"sudo chmod 666 {docker_socket} 2>/dev/null || true")

        # Run chaos panda
        subprocess.run(
            [
                "docker", "run", "-d",
                "--name", "chaospanda-temp",
                "--network", self.compose_network,
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
            capture_output=True
        )

    # ----------------------------------------------------------------------
    # HEARTBEAT WAITING
    # ----------------------------------------------------------------------
    def wait_for_events(self, n_events: int):
        print(f"Waiting for {n_events} heartbeats...")

        while True:
            count = self._count_events()
            if count >= n_events:
                print(f"Reached {count} heartbeats.")
                return
            time.sleep(1)

    def _count_events(self):
        if not self.heartbeats_file.exists():
            return 0

        try:
            with open(self.heartbeats_file, "r", encoding="utf-8") as f:
                return sum(1 for _ in f)
        except Exception:
            return 0

    # ----------------------------------------------------------------------
    # ENVIRONMENT CONFIG
    # ----------------------------------------------------------------------
    def _write_env_file(self, scenario):
        env_path = self.project_root / ".env"
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(f"NUM_CUTTING_MACHINES={scenario.num_cutting_machines}\n")
            f.write(f"MAX_KILLABLE_MACHINES={scenario.max_killable_machines}\n")
            f.write(f"MAX_KILLABLE_SCHEDULERS={scenario.max_killable_schedulers}\n")
