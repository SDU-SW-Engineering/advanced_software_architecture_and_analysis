"""
Core chaos injection engine
"""

import logging
import threading
import time
import random
from docker_manager import DockerManager
from kafka_reporter import KafkaReporter
from redis_inspector import RedisInspector

LOGGER = logging.getLogger(__name__)


class ChaosEngine:
    """Main chaos injection engine"""

    def __init__(self, max_cutting_machines, max_schedulers, kafka_bootstrap_servers,
                 redis_host, redis_port, docker_host, test_name):
        """
        Initialize chaos engine.

        Args:
            max_cutting_machines (int): Max concurrent cutting machines to kill
            max_schedulers (int): Max concurrent schedulers to kill
            kafka_bootstrap_servers (str): Kafka bootstrap servers
            redis_host (str): Redis host
            redis_port (int): Redis port
            docker_host (str): Docker socket/host
            test_name (str): Test name for logging
        """
        self.max_cutting_machines = max_cutting_machines
        self.max_schedulers = max_schedulers
        self.test_name = test_name

        # Initialize components
        self.docker = DockerManager(docker_host)
        self.kafka_reporter = KafkaReporter(kafka_bootstrap_servers, test_name)
        self.redis_inspector = RedisInspector(redis_host, redis_port)

        # Track killed machines/schedulers with restart time
        self.killed_machines = {}  # {container_name: restart_time}
        self.killed_schedulers = {}  # {container_name: restart_time}
        self.lock = threading.Lock()

        LOGGER.info("ChaosEngine initialized")

    def start(self):
        """Start chaos engine"""
        LOGGER.info("🐼 Starting ChaosPanda chaos injection engine")

        # Start chaos injection thread
        chaos_thread = threading.Thread(
            target=self._chaos_loop,
            daemon=True,
            name="ChaosEngine"
        )
        chaos_thread.start()

        # Start recovery thread
        recovery_thread = threading.Thread(
            target=self._recovery_loop,
            daemon=True,
            name="RecoveryEngine"
        )
        recovery_thread.start()

        LOGGER.info("✅ ChaosEngine started")

    def _chaos_loop(self):
        """Main chaos injection loop"""
        while True:
            try:
                time.sleep(random.uniform(5, 15))  # Wait 5-15 seconds between kills

                # Check and kill cutting machines
                self._manage_cutting_machines()

                # Check and kill schedulers
                self._manage_schedulers()

            except Exception as e:
                LOGGER.error(f"Error in chaos loop: {str(e)}", exc_info=True)
                time.sleep(5)

    def _recovery_loop(self):
        """Recovery loop - restart machines after delay"""
        while True:
            try:
                time.sleep(5)  # Check every 5 seconds

                current_time = time.time()

                # Check for machines to recover
                with self.lock:
                    machines_to_recover = [
                        name for name, restart_time in self.killed_machines.items()
                        if current_time >= restart_time
                    ]

                for machine_name in machines_to_recover:
                    self._restart_machine(machine_name)

                # Check for schedulers to recover
                with self.lock:
                    schedulers_to_recover = [
                        name for name, restart_time in self.killed_schedulers.items()
                        if current_time >= restart_time
                    ]

                for scheduler_name in schedulers_to_recover:
                    self._restart_scheduler(scheduler_name)

            except Exception as e:
                LOGGER.error(f"Error in recovery loop: {str(e)}", exc_info=True)
                time.sleep(5)

    def _manage_cutting_machines(self):
        """Manage cutting machine failures"""
        with self.lock:
            current_killed = len(self.killed_machines)

        if current_killed >= self.max_cutting_machines:
            LOGGER.debug(f"Cutting machines at limit: {current_killed}/{self.max_cutting_machines}")
            return

        # Get all cutting machine containers
        try:
            all_machines = self.docker.get_cutting_machines()
            killed_machines = set(self.killed_machines.keys())
            available_machines = [m for m in all_machines if m not in killed_machines]

            if not available_machines:
                LOGGER.warning("No available cutting machines to kill")
                return

            # Randomly select a machine to kill
            machine_to_kill = random.choice(available_machines)
            self._kill_machine(machine_to_kill)

        except Exception as e:
            LOGGER.error(f"Error managing cutting machines: {str(e)}")

    def _manage_schedulers(self):
        """Manage scheduler failures"""
        with self.lock:
            current_killed = len(self.killed_schedulers)

        if current_killed >= self.max_schedulers:
            LOGGER.debug(f"Schedulers at limit: {current_killed}/{self.max_schedulers}")
            return

        # Get all scheduler containers
        try:
            all_schedulers = self.docker.get_schedulers()
            killed_schedulers = set(self.killed_schedulers.keys())
            available_schedulers = [s for s in all_schedulers if s not in killed_schedulers]

            if not available_schedulers:
                LOGGER.warning("No available schedulers to kill")
                return

            # Randomly select a scheduler to kill
            scheduler_to_kill = random.choice(available_schedulers)
            self._kill_scheduler(scheduler_to_kill)

        except Exception as e:
            LOGGER.error(f"Error managing schedulers: {str(e)}")

    def _kill_machine(self, machine_name):
        """Kill a cutting machine"""
        try:
            machine_id = self._extract_machine_id(machine_name)
            
            LOGGER.warning(f"🔪 KILLING cutting machine: {machine_name} (ID: {machine_id})")
            
            # Stop the container
            self.docker.stop_container(machine_name)
            
            # Schedule restart after random delay (10-30 seconds)
            restart_time = time.time() + random.uniform(10, 30)
            
            with self.lock:
                self.killed_machines[machine_name] = restart_time
            
            # Report to Kafka
            self.kafka_reporter.report_killing_machine(machine_id)
            
            LOGGER.warning(f"💀 Cutting machine {machine_id} killed, will restart at {restart_time:.0f}")

        except Exception as e:
            LOGGER.error(f"Error killing machine {machine_name}: {str(e)}")

    def _kill_scheduler(self, scheduler_name):
        """Kill a scheduler"""
        try:
            # Determine if it's active or shadow
            is_active = self.redis_inspector.is_scheduler_active(scheduler_name)
            scheduler_role = "active" if is_active else "shadow"
            
            LOGGER.warning(f"🔪 KILLING scheduler: {scheduler_name} ({scheduler_role})")
            
            # Stop the container
            self.docker.stop_container(scheduler_name)
            
            # Schedule restart after random delay (10-30 seconds)
            restart_time = time.time() + random.uniform(10, 30)
            
            with self.lock:
                self.killed_schedulers[scheduler_name] = restart_time
            
            # Report to Kafka
            self.kafka_reporter.report_killing_scheduler(scheduler_role, scheduler_name)
            
            LOGGER.warning(f"💀 Scheduler {scheduler_role} ({scheduler_name}) killed, will restart at {restart_time:.0f}")

        except Exception as e:
            LOGGER.error(f"Error killing scheduler {scheduler_name}: {str(e)}")

    def _restart_machine(self, machine_name):
        """Restart a cutting machine"""
        try:
            machine_id = self._extract_machine_id(machine_name)
            
            LOGGER.info(f"♻️  RESTARTING cutting machine: {machine_name} (ID: {machine_id})")
            
            # Start the container
            self.docker.start_container(machine_name)
            
            with self.lock:
                del self.killed_machines[machine_name]
            
            LOGGER.info(f"✅ Cutting machine {machine_id} restarted")

        except Exception as e:
            LOGGER.error(f"Error restarting machine {machine_name}: {str(e)}")

    def _restart_scheduler(self, scheduler_name):
        """Restart a scheduler"""
        try:
            LOGGER.info(f"♻️  RESTARTING scheduler: {scheduler_name}")
            
            # Start the container
            self.docker.start_container(scheduler_name)
            
            with self.lock:
                del self.killed_schedulers[scheduler_name]
            
            LOGGER.info(f"✅ Scheduler {scheduler_name} restarted")

        except Exception as e:
            LOGGER.error(f"Error restarting scheduler {scheduler_name}: {str(e)}")

    def _extract_machine_id(self, machine_name):
        """Extract machine ID from container name (e.g., 'cutting-machine-0' -> 0)"""
        try:
            return int(machine_name.split('-')[-1])
        except:
            return machine_name