"""New machine event analyzer."""

from typing import List, Dict, Any, Optional
from ..models.event import Event


class NewMachineAnalyzer:
    """Analyzer for new machine events."""
    
    def __init__(self, heartbeats: List[Dict[str, Any]], production_plan: List[Dict[str, Any]]):
        self.heartbeats = sorted(heartbeats, key=lambda x: x['message']['timestamp'])
        self.production_plan = production_plan
    
    def analyze(self) -> List[Event]:
        """
        Identify all new machine events.
        
        Returns:
            List of new machine Event objects
        """
        # Extract AssignBlade events
        assign_blade_events = []
        for record in self.production_plan:
            msg = record['message']
            if msg.get('title') == 'AssignBlade':
                assign_blade_events.append({
                    'machineId': msg['machineId'],
                    'bladeType': msg['bladeType'],
                    'reaction_ts': record['collected_at']
                })
        
        events = []
        event_counter = 1
        
        for assign in assign_blade_events:
            machine_id = assign['machineId']
            blade_type = assign['bladeType']
            reaction_ts = assign['reaction_ts']
            
            # Find trigger_ts: first heartbeat without bladeType in continuous block before reaction_ts
            trigger_ts = self._find_trigger_ts(machine_id, reaction_ts)
            
            # Find solved_ts: first heartbeat after reaction_ts with matching bladeType
            solved_ts = self._find_solved_ts(machine_id, blade_type, reaction_ts)
            
            if trigger_ts and solved_ts:
                event = Event(
                    id=f"nM{machine_id}-{event_counter:03d}",
                    type="newMachine",
                    trigger_ts=trigger_ts,
                    reaction_ts=reaction_ts,
                    solved_ts=solved_ts,
                    scheduler_latency=reaction_ts - trigger_ts,
                    machine_latency=solved_ts - reaction_ts
                )
                events.append(event)
                event_counter += 1
        
        return events
    
    def _find_trigger_ts(self, machine_id: int, reaction_ts: int) -> Optional[int]:
        """Find the trigger timestamp for a new machine event."""
        trigger_ts = None
        
        for i in range(len(self.heartbeats) - 1, -1, -1):
            hb = self.heartbeats[i]['message']
            hb_ts = hb['timestamp']
            
            if hb_ts >= reaction_ts:
                continue
            
            if hb['machineId'] == machine_id:
                if 'bladeType' not in hb and hb.get('state') == 'WAITING_FOR_ASSIGNMENT':
                    trigger_ts = hb_ts
                elif 'bladeType' in hb:
                    break
        
        return trigger_ts
    
    def _find_solved_ts(self, machine_id: int, blade_type: str, reaction_ts: int) -> Optional[int]:
        """Find the solved timestamp for a new machine event."""
        for hb_record in self.heartbeats:
            hb = hb_record['message']
            hb_ts = hb['timestamp']
            
            if hb_ts > reaction_ts and hb['machineId'] == machine_id:
                if hb.get('bladeType') == blade_type and hb.get('state') == 'WORKING':
                    return hb_ts
        
        return None