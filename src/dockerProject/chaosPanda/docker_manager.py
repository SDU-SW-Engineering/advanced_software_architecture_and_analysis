"""
Docker container management
"""

import logging
import docker
from docker.errors import DockerException

LOGGER = logging.getLogger(__name__)


class DockerManager:
    """Manages Docker container operations"""

    # Container name patterns
    CUTTING_MACHINE_PATTERN = "cutting-machine-"
    SCHEDULER_PATTERN = "scheduler"
    NETWORK_NAME = "dockerproject_mynetwork"

    def __init__(self, docker_host):
        """
        Initialize Docker manager.

        Args:
            docker_host (str): Docker socket or host URL
        """
        try:
            self.client = docker.DockerClient(base_url=docker_host)
            self.client.ping()
            LOGGER.info(f"✅ Connected to Docker at {docker_host}")
        except DockerException as e:
            LOGGER.error(f"Failed to connect to Docker: {str(e)}")
            raise RuntimeError("Could not connect to Docker daemon")

    def get_cutting_machines(self):
        """Get all running cutting machine containers"""
        try:
            containers = self.client.containers.list(
                filters={"label": "com.docker.compose.service=cutting-machine-0"}
            )
            
            # Alternative: search by name pattern
            all_containers = self.client.containers.list()
            machines = [c for c in all_containers if self.CUTTING_MACHINE_PATTERN in c.name]
            
            names = [c.name for c in machines]
            LOGGER.debug(f"Found {len(names)} cutting machines: {names}")
            return names

        except DockerException as e:
            LOGGER.error(f"Error listing cutting machines: {str(e)}")
            return []

    def get_schedulers(self):
        """Get all scheduler containers (active and shadow)"""
        try:
            all_containers = self.client.containers.list()
            schedulers = [c for c in all_containers if self.SCHEDULER_PATTERN in c.name]
            
            names = [c.name for c in schedulers]
            LOGGER.debug(f"Found {len(names)} schedulers: {names}")
            return names

        except DockerException as e:
            LOGGER.error(f"Error listing schedulers: {str(e)}")
            return []

    def stop_container(self, container_name):
        """
        Stop a container.

        Args:
            container_name (str): Name of container to stop
        """
        try:
            container = self.client.containers.get(container_name)
            container.stop(timeout=10)
            LOGGER.info(f"Stopped container: {container_name}")

        except docker.errors.NotFound:
            LOGGER.warning(f"Container not found: {container_name}")
        except DockerException as e:
            LOGGER.error(f"Error stopping container {container_name}: {str(e)}")
            raise

    def start_container(self, container_name):
        """
        Start a container.

        Args:
            container_name (str): Name of container to start
        """
        try:
            container = self.client.containers.get(container_name)
            container.start()
            LOGGER.info(f"Started container: {container_name}")

        except docker.errors.NotFound:
            LOGGER.warning(f"Container not found: {container_name}")
        except DockerException as e:
            LOGGER.error(f"Error starting container {container_name}: {str(e)}")
            raise

    def get_container_status(self, container_name):
        """
        Get container status.

        Args:
            container_name (str): Name of container

        Returns:
            str: Container status (running, exited, etc.)
        """
        try:
            container = self.client.containers.get(container_name)
            return container.status

        except docker.errors.NotFound:
            return "not found"
        except DockerException as e:
            LOGGER.error(f"Error getting container status: {str(e)}")
            return "error"