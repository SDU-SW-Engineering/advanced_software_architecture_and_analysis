"""
Latency Analyzer Service
Runs the latency analysis on collected data using Docker container
"""

import logging
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class LatencyAnalyzer:
    """Handles latency analysis execution via Docker container"""
    
    def __init__(self, project_root: Path):
        """
        Initialize latency analyzer
        
        Args:
            project_root: Path to dockerProject directory
        """
        self.project_root = project_root
        self.analyzer_dir = project_root / 'latency_analyzer'
        self.dockerfile = self.analyzer_dir / 'Dockerfile'
        
        if not self.analyzer_dir.exists():
            logger.warning(f"Latency analyzer directory not found at {self.analyzer_dir}")
        if not self.dockerfile.exists():
            logger.warning(f"Dockerfile not found at {self.dockerfile}")
    
    def build_image(self, timeout: int = 180) -> bool:
        """
        Build the latency analyzer Docker image
        
        Args:
            timeout: Maximum time for build
            
        Returns:
            True if build succeeded, False otherwise
        """
        if not self.analyzer_dir.exists():
            logger.error("Latency analyzer directory not found, cannot build image")
            return False
        
        logger.info("Building latency analyzer Docker image...")
        
        try:
            result = subprocess.run(
                [
                    "docker", "build",
                    "-t", "latency-analyzer:latest",
                    "."
                ],
                cwd=self.analyzer_dir,
                capture_output=True,
                timeout=timeout,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Docker build failed: {result.stderr}")
                return False
            
            logger.info("Latency analyzer image built successfully")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error(f"Docker build timed out after {timeout}s")
            return False
        except Exception as e:
            logger.error(f"Error building Docker image: {e}", exc_info=True)
            return False
    
    def run_analysis(self, 
                    collector_output_dir: Path,
                    output_dir: Path,
                    timeout: int = 300) -> bool:
        """
        Run latency analysis using Docker container
        
        Args:
            collector_output_dir: Directory with collected .jsonl files
            output_dir: Directory to write analysis results
            timeout: Maximum time for analysis
            
        Returns:
            True if analysis succeeded, False otherwise
        """
        if not self.analyzer_dir.exists():
            logger.error("Latency analyzer directory not found, skipping analysis")
            return False
        
        logger.info("Running latency analysis container...")
        
        # Ensure output directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Expected output files
        events_csv = output_dir / 'events.csv'
        summary_txt = output_dir / 'summary.txt'
        
        # Container name
        container_name = "latency-analyzer-temp"
        
        try:
            # Remove any existing container with same name
            self._cleanup_container(container_name)
            
            # Run the analyzer container
            result = subprocess.run(
                [
                    "docker", "run",
                    "--name", container_name,
                    "--rm",  # Auto-remove after completion
                    "-v", f"{collector_output_dir.resolve()}:/app/collector_output:ro",  # Read-only mount
                    "-v", f"{output_dir.resolve()}:/app/final_results",
                    "-e", "PYTHONUNBUFFERED=1",
                    "latency-analyzer:latest"
                ],
                capture_output=True,
                timeout=timeout,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Latency analyzer failed: {result.stderr}")
                logger.debug(f"Stdout: {result.stdout}")
                return False
            
            # Log analyzer output
            if result.stdout:
                logger.debug(f"Analyzer output:\n{result.stdout}")
            
            # Give filesystem a moment to sync
            time.sleep(1)
            
            # Verify output files were created
            if events_csv.exists() and summary_txt.exists():
                logger.info("Latency analysis completed successfully")
                logger.info(f"  - Events CSV: {events_csv}")
                logger.info(f"  - Summary: {summary_txt}")
                return True
            else:
                missing = []
                if not events_csv.exists():
                    missing.append("events.csv")
                if not summary_txt.exists():
                    missing.append("summary.txt")
                logger.warning(f"Analyzer completed but files not found: {', '.join(missing)}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Latency analysis timed out after {timeout}s")
            self._cleanup_container(container_name)
            return False
        except Exception as e:
            logger.error(f"Error running latency analysis: {e}", exc_info=True)
            self._cleanup_container(container_name)
            return False
    
    def _cleanup_container(self, container_name: str):
        """
        Remove a container if it exists
        
        Args:
            container_name: Name of container to remove
        """
        try:
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                capture_output=True,
                timeout=10,
                text=True
            )
            logger.debug(f"Cleaned up container: {container_name}")
        except Exception:
            pass  # Container may not exist, which is fine