"""
Experiment Orchestrator
Main orchestration logic for multi-scenario experiments
"""

import logging
import time
from pathlib import Path
from typing import List

from config.scenario_config import Scenario
from services.docker_manager import DockerManager
from services.latency_analyzer import LatencyAnalyzer
from services.results_manager import ResultsManager

logger = logging.getLogger(__name__)


class ExperimentOrchestrator:
    """Orchestrates the execution of multiple experiment scenarios"""
    
    def __init__(self, 
                 project_root: Path,
                 duration_seconds: int,
                 skip_initial_cleanup: bool = False):
        """
        Initialize experiment orchestrator
        
        Args:
            project_root: Path to dockerProject directory
            duration_seconds: Duration to run each scenario
            skip_initial_cleanup: Skip initial Docker cleanup
        """
        self.project_root = project_root
        self.duration_seconds = duration_seconds
        self.skip_initial_cleanup = skip_initial_cleanup
        
        # Initialize service managers
        self.docker_manager = DockerManager(project_root)
        self.latency_analyzer = LatencyAnalyzer(project_root)
        self.results_manager = ResultsManager(project_root)
        
        # Temporary directory for analysis outputs (not final results)
        self.temp_analysis_dir = project_root / 'temp_analysis'
        
        logger.info("ExperimentOrchestrator initialized")
        logger.info(f"  Project root: {self.project_root}")
        logger.info(f"  Duration: {self.duration_seconds}s per scenario")
        
        # Build all required Docker images once at startup
        logger.info("\nBuilding Docker images...")
        
        # Build kafka-collector and chaospanda
        if not self.docker_manager.build_required_images():
            logger.warning("Some Docker images failed to build")
        
        # Build latency analyzer image
        logger.info("Building latency analyzer Docker image...")
        if not self.latency_analyzer.build_image():
            logger.warning("Failed to build latency analyzer image - analysis may fail")
        
        logger.info("Docker image builds complete\n")
    
    def run_all_scenarios(self, scenarios: List[Scenario]):
        """
        Run all scenarios sequentially
        
        Args:
            scenarios: List of scenarios to execute
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"Starting experiment with {len(scenarios)} scenario(s)")
        logger.info(f"{'='*80}\n")
        
        # Initial cleanup
        if not self.skip_initial_cleanup:
            self.docker_manager.cleanup_all_containers()
        else:
            logger.info("Skipping initial cleanup (--skip-cleanup flag)")
        
        # Run each scenario
        successful = 0
        failed = 0
        
        for idx, scenario in enumerate(scenarios, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"Scenario {idx}/{len(scenarios)}: {scenario.id}")
            logger.info(f"Description: {scenario.description}")
            logger.info(f"{'='*80}\n")
            
            try:
                self._run_single_scenario(scenario)
                successful += 1
                logger.info(f"✓ Scenario {scenario.id} completed successfully\n")
            except Exception as e:
                failed += 1
                logger.error(f"✗ Scenario {scenario.id} failed: {e}\n", exc_info=True)
            
            # Cleanup after each scenario
            logger.info("Cleaning up before next scenario...")
            self.docker_manager.cleanup_all_containers()
            time.sleep(3)
        
        # Final cleanup
        logger.info("\nPerforming final cleanup...")
        self.docker_manager.cleanup_all_containers()
        
        # Summary
        logger.info(f"\n{'='*80}")
        logger.info("EXPERIMENT COMPLETE")
        logger.info(f"  Successful: {successful}/{len(scenarios)}")
        logger.info(f"  Failed: {failed}/{len(scenarios)}")
        logger.info(f"  Results directory: {self.results_manager.final_results_dir}")
        logger.info(f"{'='*80}\n")
    
    def _run_single_scenario(self, scenario: Scenario):
        """
        Execute a single scenario
        
        Args:
            scenario: Scenario to execute
        """
        # 1. Clear collector output
        logger.info("Clearing collector output...")
        self.results_manager.clear_collector_output()
        
        # 2. Start docker-compose with scenario environment
        logger.info("Starting docker-compose services...")
        environment = {
            "CUTTING_MACHINES": str(scenario.num_cutting_machines),
            "SCENARIO_ID": scenario.id,
        }
        self.docker_manager.start_compose_services(environment)
        
        # 3. Wait for Kafka to be ready
        logger.info("Waiting for Kafka...")
        self.docker_manager.wait_for_kafka_ready()
        
        # 4. Start Kafka Collector
        logger.info("Starting Kafka Collector...")
        self.docker_manager.start_kafka_collector(
            collector_output_dir=self.results_manager.collector_output_dir
        )
        time.sleep(3)
        
        # 5. Start ChaosPanda
        logger.info("Starting ChaosPanda...")
        self.docker_manager.start_chaos_panda(
            scenario_id=scenario.id,
            max_cutting_machines=scenario.max_killable_machines,
            max_schedulers=scenario.max_killable_schedulers
        )
        time.sleep(2)
        
        # 6. Wait for specified duration
        logger.info(f"Running experiment for {self.duration_seconds} seconds...")
        self._wait_with_progress(self.duration_seconds)
        
        # 7. Stop all services
        logger.info("Stopping services...")
        self.docker_manager.stop_compose_services()
        time.sleep(5)
        
        # 8. Run latency analysis
        logger.info("Running latency analysis...")
        self.temp_analysis_dir.mkdir(parents=True, exist_ok=True)
        analysis_success = self.latency_analyzer.run_analysis(
            collector_output_dir=self.results_manager.collector_output_dir,
            output_dir=self.temp_analysis_dir
        )
        
        if not analysis_success:
            logger.warning("Latency analysis failed or incomplete")
        
        # 9. Collect all results into final_results
        logger.info("Collecting results...")
        final_dir = self.results_manager.collect_results(
            scenario_id=scenario.id,
            analysis_output_dir=self.temp_analysis_dir
        )
        logger.info(f"Results saved to: {final_dir}")
    
    def _wait_with_progress(self, duration_seconds: int):
        """
        Wait for specified duration with progress updates
        
        Args:
            duration_seconds: Duration to wait
        """
        start_time = time.time()
        end_time = start_time + duration_seconds
        
        update_interval = min(30, duration_seconds // 10)  # Update every 30s or 10% of duration
        if update_interval == 0:
            update_interval = 1
        
        while time.time() < end_time:
            elapsed = time.time() - start_time
            remaining = duration_seconds - elapsed
            
            if remaining <= 0:
                break
            
            progress_pct = (elapsed / duration_seconds) * 100
            logger.info(f"Progress: {progress_pct:.1f}% ({int(elapsed)}s / {duration_seconds}s)")
            
            sleep_time = min(update_interval, remaining)
            time.sleep(sleep_time)
        
        logger.info(f"Experiment duration complete ({duration_seconds}s)")