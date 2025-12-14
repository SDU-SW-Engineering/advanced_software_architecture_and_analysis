"""Machine failure event analyzer."""

from typing import List, Dict, Any, Optional
from ..models.event import Event


class MachineFailureAnalyzer:
    """Analyzer for machine failure events."""
    
    def __init__(self, heartbeats: List[Dict[str, Any]], production_plan: List[Dict[str, Any]]):
        self.heartbeats = sorted(heartbeats, key=lambda x: x['message']['timestamp'])
        self.production_plan = production_plan
    
    def analyze(self) -> List[Event]:
        """
        Identify all machine failure events.
        
        Returns:
            List of machine failure Event objects
        """
        # Extract SwapBlade events with machineFailure context
        swap_blade_events = []
        for record in self.production_plan:
            msg = record['message']
            if msg.get('title') == 'SwapBlade':
                event_context = msg.get('eventContext', '')
                if event_context.startswith('machineFailure:machine'):
                    # Extract failed machine ID from eventContext
                    failed_machine_id = int(event_context.split('_')[1])
                    swap_blade_events.append({
                        'failed_machine_id': failed_machine_id,
                        'target_machine_id': msg['machineId'],
                        'reaction_ts': record['collected_at']
                    })
        
        events = []
        event_counter_by_machine = {}
        
        for swap in swap_blade_events:
            failed_machine_id = swap['failed_machine_id']
            target_machine_id = swap['target_machine_id']
            reaction_ts = swap['reaction_ts']
            
            # Initialize counter for this machine if not exists
            if failed_machine_id not in event_counter_by_machine:
                event_counter_by_machine[failed_machine_id] = 1
            
            # Find trigger_ts: last heartbeat from failed machine before reaction_ts
            trigger_ts = self._find_trigger_ts(failed_machine_id, reaction_ts)
            
            # Find solved_ts: first BladeSwapped message for target machine
            solved_ts = self._find_solved_ts(target_machine_id, reaction_ts)
            
            if trigger_ts and solved_ts:
                event = Event(
                    id=f"mF{failed_machine_id}-{event_counter_by_machine[failed_machine_id]:03d}",
                    type="machineFailure",
                    trigger_ts=trigger_ts,
                    reaction_ts=reaction_ts,
                    solved_ts=solved_ts,
                    scheduler_latency=reaction_ts - trigger_ts,
                    machine_latency=solved_ts - reaction_ts
                )
                events.append(event)
                event_counter_by_machine[failed_machine_id] += 1
        
        return events
    
    def _find_trigger_ts(self, machine_id: int, reaction_ts: int) -> Optional[int]:
        """Find the last heartbeat from machine before reaction."""
        trigger_ts = None
        
        for hb_record in reversed(self.heartbeats):
            hb = hb_record['message']
            hb_ts = hb['timestamp']
            
            if hb_ts >= reaction_ts:
                continue
            
            if hb['machineId'] == machine_id:
                trigger_ts = hb_ts
                break
        
        return trigger_ts
    
    def _find_solved_ts(self, target_machine_id: int, reaction_ts: int) -> Optional[int]:
        """Find the BladeSwapped confirmation for target machine."""
        for record in self.production_plan:
            msg = record['message']
            if (msg.get('title') == 'BladeSwapped' and 
                msg.get('machineId') == target_machine_id and
                record['collected_at'] > reaction_ts):
                return record['collected_at']
        
        return None