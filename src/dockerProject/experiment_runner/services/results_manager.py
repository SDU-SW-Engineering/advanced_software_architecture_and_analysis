"""
Results Manager
Handles result collection, organization, and archival
"""

import logging
import shutil
import time
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


class ResultsManager:
    """Manages experiment results collection and storage"""
    
    def __init__(self, project_root: Path):
        """
        Initialize results manager
        
        Args:
            project_root: Path to dockerProject directory
        """
        self.project_root = project_root
        self.final_results_dir = project_root / 'final_results'
        self.collector_output_dir = project_root / 'collector_output'
        
        # Ensure final_results directory exists
        self.final_results_dir.mkdir(parents=True, exist_ok=True)
    
    def create_scenario_results_dir(self, scenario_id: str) -> Path:
        """
        Create a timestamped directory for scenario results
        
        Args:
            scenario_id: Scenario identifier
            
        Returns:
            Path to created results directory
        """
        # Generate timestamp (milliseconds since epoch)
        timestamp_ms = int(time.time() * 1000)
        
        # Create directory name: scenario_id_timestamp
        dir_name = f"{scenario_id}_{timestamp_ms}"
        results_dir = self.final_results_dir / dir_name
        
        results_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created results directory: {results_dir}")
        
        return results_dir
    
    def collect_results(self, 
                       scenario_id: str,
                       analysis_output_dir: Path) -> Path:
        """
        Collect all results for a scenario into final_results directory
        
        Args:
            scenario_id: Scenario identifier
            analysis_output_dir: Directory containing analysis outputs (events.csv, summary.txt)
            
        Returns:
            Path to final results directory
        """
        results_dir = self.create_scenario_results_dir(scenario_id)
        
        # Copy .jsonl files from collector_output
        jsonl_files = ['heartbeats.jsonl', 'productionPlan.jsonl', 'storageAlerts.jsonl']
        self._copy_jsonl_files(jsonl_files, results_dir)
        
        # Copy analysis results
        self._copy_analysis_results(analysis_output_dir, results_dir)
        
        logger.info(f"Results collected in: {results_dir}")
        return results_dir
    
    def _copy_jsonl_files(self, filenames: List[str], destination: Path):
        """
        Copy .jsonl files from collector_output to destination
        
        Args:
            filenames: List of .jsonl filenames to copy
            destination: Destination directory
        """
        for filename in filenames:
            source_file = self.collector_output_dir / filename
            dest_file = destination / filename
            
            if source_file.exists():
                try:
                    shutil.copy2(source_file, dest_file)
                    logger.debug(f"Copied {filename} -> {dest_file}")
                except Exception as e:
                    logger.warning(f"Failed to copy {filename}: {e}")
            else:
                logger.warning(f"Source file not found: {source_file}")
    
    def _copy_analysis_results(self, source_dir: Path, destination: Path):
        """
        Copy analysis results (events.csv, summary.txt) to destination
        
        Args:
            source_dir: Directory containing analysis results
            destination: Destination directory
        """
        analysis_files = ['events.csv', 'summary.txt']
        
        for filename in analysis_files:
            source_file = source_dir / filename
            dest_file = destination / filename
            
            if source_file.exists():
                try:
                    shutil.copy2(source_file, dest_file)
                    logger.debug(f"Copied {filename} -> {dest_file}")
                except Exception as e:
                    logger.warning(f"Failed to copy {filename}: {e}")
            else:
                logger.warning(f"Analysis file not found: {source_file}")
    
    def clear_collector_output(self):
        """Clear previous collector output directory"""
        if self.collector_output_dir.exists():
            try:
                shutil.rmtree(self.collector_output_dir)
                logger.debug("Cleared collector_output directory")
            except Exception as e:
                logger.warning(f"Failed to clear collector_output: {e}")
        
        # Recreate empty directory
        self.collector_output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_all_scenario_results(self) -> List[Path]:
        """
        Get list of all scenario result directories
        
        Returns:
            List of paths to scenario result directories
        """
        if not self.final_results_dir.exists():
            return []
        
        return sorted([
            d for d in self.final_results_dir.iterdir()
            if d.is_dir()
        ])