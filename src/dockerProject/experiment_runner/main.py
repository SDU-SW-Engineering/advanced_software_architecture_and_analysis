"""
Experiment Runner - Main Entry Point
Orchestrates multi-scenario experiments for pasta production system
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List

from config.scenario_config import Scenario, get_all_scenarios
from orchestrator.experiment_orchestrator import ExperimentOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Run multi-scenario experiments for pasta production system"
    )
    parser.add_argument(
        '--seconds',
        type=int,
        required=True,
        help='Duration in seconds to run each scenario'
    )
    parser.add_argument(
        '--project-root',
        type=str,
        default='..',
        help='Path to dockerProject directory (default: parent directory)'
    )
    parser.add_argument(
        '--scenarios',
        type=str,
        nargs='+',
        help='Specific scenario IDs to run (default: all scenarios)'
    )
    parser.add_argument(
        '--skip-cleanup',
        action='store_true',
        help='Skip initial cleanup of Docker containers'
    )
    return parser.parse_args()


def filter_scenarios(all_scenarios: List[Scenario], scenario_ids: List[str] = None) -> List[Scenario]:
    """Filter scenarios based on provided IDs"""
    if not scenario_ids:
        return all_scenarios
    
    filtered = [s for s in all_scenarios if s.id in scenario_ids]
    
    if len(filtered) != len(scenario_ids):
        found_ids = {s.id for s in filtered}
        missing = set(scenario_ids) - found_ids
        logger.warning(f"Scenarios not found: {missing}")
    
    return filtered


def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Validate project root
    project_root = Path(args.project_root).resolve()
    if not project_root.exists():
        logger.error(f"Project root does not exist: {project_root}")
        sys.exit(1)
    
    docker_compose_file = project_root / 'docker-compose.yml'
    if not docker_compose_file.exists():
        logger.error(f"docker-compose.yml not found in {project_root}")
        sys.exit(1)
    
    # Load and filter scenarios
    all_scenarios = get_all_scenarios()
    scenarios = filter_scenarios(all_scenarios, args.scenarios)
    
    if not scenarios:
        logger.error("No scenarios to run")
        sys.exit(1)
    
    logger.info(f"Loaded {len(scenarios)} scenario(s) to run")
    for scenario in scenarios:
        logger.info(f"  - {scenario.id}: {scenario.description}")
    
    # Create orchestrator and run experiments
    try:
        orchestrator = ExperimentOrchestrator(
            project_root=project_root,
            duration_seconds=args.seconds,
            skip_initial_cleanup=args.skip_cleanup
        )
        
        orchestrator.run_all_scenarios(scenarios)
        
        logger.info("All experiments completed successfully")
        sys.exit(0)
        
    except KeyboardInterrupt:
        logger.warning("Experiment interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Experiment failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()