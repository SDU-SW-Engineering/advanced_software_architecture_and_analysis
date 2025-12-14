"""
Scenario Configuration
Defines all experiment scenarios
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Scenario:
    """Experiment scenario configuration"""
    id: str
    num_cutting_machines: int
    max_killable_machines: int
    max_killable_schedulers: int
    description: str
    
    def __post_init__(self):
        """Validate scenario configuration"""
        if self.num_cutting_machines <= 0:
            raise ValueError(f"num_cutting_machines must be positive, got {self.num_cutting_machines}")
        if self.max_killable_machines < 0:
            raise ValueError(f"max_killable_machines cannot be negative, got {self.max_killable_machines}")
        if self.max_killable_schedulers < 0:
            raise ValueError(f"max_killable_schedulers cannot be negative, got {self.max_killable_schedulers}")
        if self.max_killable_machines > self.num_cutting_machines:
            raise ValueError(
                f"max_killable_machines ({self.max_killable_machines}) cannot exceed "
                f"num_cutting_machines ({self.num_cutting_machines})"
            )


def get_all_scenarios() -> List[Scenario]:
    """
    Define all experiment scenarios
    
    Returns:
        List of Scenario objects to be executed
    """
    scenarios = [
        Scenario(
            id="5m_1k",
            num_cutting_machines=5,
            max_killable_machines=1,
            max_killable_schedulers=1,
            description="5 machines, max 1 kill per time"
        ),
        Scenario(
            id="5m_2k",
            num_cutting_machines=5,
            max_killable_machines=2,
            max_killable_schedulers=1,
            description="5 machines, max 2 kill per time"
        ),
        Scenario(
            id="5m_3k",
            num_cutting_machines=5,
            max_killable_machines=3,
            max_killable_schedulers=1,
            description="5 machines, max 3 kill per time"
        ),
        Scenario(
            id="5m_4k",
            num_cutting_machines=5,
            max_killable_machines=4,
            max_killable_schedulers=1,
            description="5 machines, max 4 kill per time"
        ),
    ]
    
    return scenarios