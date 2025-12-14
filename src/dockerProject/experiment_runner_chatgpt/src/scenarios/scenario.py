from dataclasses import dataclass

@dataclass
class Scenario:
    id: str
    num_cutting_machines: int
    max_killable_machines: int
    max_killable_schedulers: int
    description: str