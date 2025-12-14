from .scenario import Scenario

SCENARIOS = [
    Scenario(
        id="3m_1k",
        num_cutting_machines=3,
        max_killable_machines=1,
        max_killable_schedulers=1,
        description="3 machines, max 1 kill per time"
    ),
    Scenario(
        id="3m_2k",
        num_cutting_machines=3,
        max_killable_machines=2,
        max_killable_schedulers=1,
        description="3 machines, max 2 kill per time"
    )
]
