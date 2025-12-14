"""
Experiment scenario configuration
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Scenario:
    """Represents an experiment scenario"""
    
    id: str                              # Unique scenario identifier (e.g., "3m_0k")
    num_cutting_machines: int            # Number of cutting machines (3 or 5)
    max_killable_machines: int           # Max concurrent machines to kill (0-4)
    max_killable_schedulers: int         # Max concurrent schedulers to kill (always 1)
    description: str                     # Human readable description

