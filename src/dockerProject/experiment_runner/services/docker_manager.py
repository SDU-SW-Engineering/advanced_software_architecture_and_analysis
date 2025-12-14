"""
Docker Manager
Handles all Docker container lifecycle operations
"""

import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class DockerManager:
    """Manages Docker container lifecycle"""
    
    def __init__(self, project_root: Path):
        """
        Initialize Docker manager
        
        Args:
            project_root: Path to dockerProject directory containing docker-compose.yml
        """
        self.project_root = project_root
        self.docker_compose_file = project_root / 'docker-compose.yml'
        
        if not self.docker_compose_file.exists():
            raise FileNotFoundError(f"docker-compose.yml not found at {self.docker_compose_file}")
        
        # Directories for additional Docker images
        self.kafka_collector_dir = project_root / 'kafkaCollector'
        self.chaos_panda_dir = project_root / 'chaosPanda'
    
    def cleanup_all_containers(self, timeout: int = 60):
        """
        Stop and remove all containers and volumes
        
        Args:
            timeout: Maximum time to wait for cleanup
        """
        logger.info("Cleaning up all Docker containers and volumes...")
        
        # Stop docker-compose services
        try:
            result = subprocess.run(
                ["docker-compose", "down", "-v", "--remove-orphans"],
                cwd=self.project_root,
                capture_output=True,
                timeout=timeout,
                text=True
            )
            if result.returncode != 0:
                logger.warning(f"docker-compose down warning: {result.stderr}")
            else:
                logger.info("Docker Compose services stopped")
        except subprocess.TimeoutExpired:
            logger.error(f"docker-compose down timed out after {timeout}s")
        except Exception as e:
            logger.error(f"Error stopping docker-compose: {e}")
        
        # Stop and remove temporary containers
        temp_containers = ["kafka-collector-temp", "chaospanda-temp", "latency-analyzer-temp"]
        for container in temp_containers:
            self._stop_and_remove_container(container)
        
        # Give Docker time to clean up
        time.sleep(3)
        logger.info("Cleanup complete")
    
    def build_required_images(self) -> bool:
        """
        Build required Docker images (kafka-collector, chaospanda)
        
        Returns:
            True if all images built successfully
        """
        logger.info("Building required Docker images...")
        
        images_to_build = [
            ("kafka-collector", self.kafka_collector_dir),
            ("chaospanda", self.chaos_panda_dir)
        ]
        
        all_success = True
        
        for image_name, image_dir in images_to_build:
            if not image_dir.exists():
                logger.warning(f"Directory not found: {image_dir}, skipping {image_name}")
                continue
            
            dockerfile = image_dir / 'Dockerfile'
            if not dockerfile.exists():
                logger.warning(f"Dockerfile not found in {image_dir}, skipping {image_name}")
                continue
            
            logger.info(f"Building {image_name}:latest...")
            
            try:
                result = subprocess.run(
                    ["docker", "build", "-t", f"{image_name}:latest", "."],
                    cwd=image_dir,
                    capture_output=True,
                    timeout=180,
                    text=True
                )
                
                if result.returncode != 0:
                    logger.error(f"Failed to build {image_name}: {result.stderr}")
                    all_success = False
                else:
                    logger.info(f"✓ {image_name}:latest built successfully")
                    
            except subprocess.TimeoutExpired:
                logger.error(f"Building {image_name} timed out after 180s")
                all_success = False
            except Exception as e:
                logger.error(f"Error building {image_name}: {e}")
                all_success = False
        
        return all_success
    
    def start_compose_services(self, environment: Dict[str, str], timeout: int = 120):
        """
        Start docker-compose services with environment variables
        
        Args:
            environment: Environment variables for docker-compose
            timeout: Maximum time to wait for startup
        """
        logger.info("Starting docker-compose services...")
        logger.debug(f"Environment: {environment}")
        
        try:
            # Merge with current environment
            env = {**subprocess.os.environ, **environment}
            
            result = subprocess.run(
                ["docker-compose", "up", "-d"],
                cwd=self.project_root,
                capture_output=True,
                timeout=timeout,
                env=env,
                text=True
            )
            
            if result.returncode != 0:
                raise RuntimeError(
                    f"Failed to start docker-compose services: {result.stderr}"
                )
            
            logger.info("Docker Compose services started successfully")
            
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"docker-compose startup timed out after {timeout}s")
        except Exception as e:
            logger.error(f"Failed to start services: {e}")
            raise
    
    def stop_compose_services(self, timeout: int = 60):
        """
        Stop docker-compose services
        
        Args:
            timeout: Maximum time to wait for shutdown
        """
        logger.info("Stopping docker-compose services...")
        
        try:
            subprocess.run(
                ["docker-compose", "stop"],
                cwd=self.project_root,
                capture_output=True,
                timeout=timeout,
                text=True
            )
            logger.info("Docker Compose services stopped")
        except Exception as e:
            logger.warning(f"Error stopping services: {e}")
    
    def wait_for_kafka_ready(self, timeout: int = 90):
        """
        Wait for Kafka to be ready to accept connections
        
        Args:
            timeout: Maximum time to wait
        """
        logger.info("Waiting for Kafka to be ready...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                result = subprocess.run(
                    [
                        "docker", "exec", "kafka",
                        "kafka-topics", "--list",
                        "--bootstrap-server", "localhost:9092"
                    ],
                    capture_output=True,
                    timeout=5,
                    text=True
                )
                
                if result.returncode == 0:
                    logger.info("Kafka is ready")
                    return
                    
            except subprocess.TimeoutExpired:
                pass
            except Exception as e:
                logger.debug(f"Kafka check failed: {e}")
            
            time.sleep(3)
        
        raise RuntimeError(f"Kafka not ready after {timeout} seconds")
    
    def start_kafka_collector(self, collector_output_dir: Path, network: str = "dockerproject_mynetwork"):
        """
        Start Kafka Collector container
        
        Args:
            collector_output_dir: Directory to store collected messages
            network: Docker network name
        """
        logger.info("Starting Kafka Collector...")
        
        # Ensure output directory exists
        collector_output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            subprocess.run(
                [
                    "docker", "run", "-d",
                    "--name", "kafka-collector-temp",
                    "--network", network,
                    "-v", f"{collector_output_dir.resolve()}:/app/collector_output",
                    "-e", "KAFKA_BOOTSTRAP_SERVERS=kafka:29092",
                    "-e", "PYTHONUNBUFFERED=1",
                    "kafka-collector:latest",
                    "python", "kafka_collector.py"
                ],
                capture_output=True,
                timeout=15,
                text=True,
                check=True
            )
            logger.info("Kafka Collector started successfully")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start Kafka Collector: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"Error starting Kafka Collector: {e}")
            raise
    
    def start_chaos_panda(self, 
                         scenario_id: str,
                         max_cutting_machines: int,
                         max_schedulers: int,
                         network: str = "dockerproject_mynetwork"):
        """
        Start ChaosPanda container with scenario configuration
        
        Args:
            scenario_id: Scenario identifier
            max_cutting_machines: Maximum machines to kill
            max_schedulers: Maximum schedulers to kill
            network: Docker network name
        """
        logger.info(f"Starting ChaosPanda (scenario: {scenario_id})...")
        
        try:
            subprocess.run(
                [
                    "docker", "run", "-d",
                    "--name", "chaospanda-temp",
                    "--network", network,
                    "-v", "/var/run/docker.sock:/var/run/docker.sock",
                    "--user", "root",
                    "--group-add", "0",
                    "-e", "PYTHONUNBUFFERED=1",
                    "-e", f"SCENARIO_ID={scenario_id}",
                    "chaospanda:latest",
                    "python", "main.py",
                    "--max-cutting-machines", str(max_cutting_machines),
                    "--max-schedulers", str(max_schedulers),
                    "--kafka-bootstrap", "kafka:29092",
                    "--redis-host", "redis",
                    "--redis-port", "6379",
                    "--test-name", scenario_id
                ],
                capture_output=True,
                timeout=15,
                text=True,
                check=True
            )
            logger.info("ChaosPanda started successfully")
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"ChaosPanda startup failed: {e.stderr}")
            logger.warning("Continuing without chaos injection")
        except Exception as e:
            logger.warning(f"ChaosPanda error: {e}")
            logger.warning("Continuing without chaos injection")
    
    def _stop_and_remove_container(self, container_name: str):
        """Stop and remove a specific container"""
        try:
            # Stop container
            subprocess.run(
                ["docker", "stop", container_name],
                capture_output=True,
                timeout=10,
                text=True
            )
            # Remove container
            subprocess.run(
                ["docker", "rm", container_name],
                capture_output=True,
                timeout=10,
                text=True
            )
            logger.debug(f"Removed container: {container_name}")
        except Exception as e:
            logger.debug(f"Could not remove {container_name}: {e}")