"""Storage alert event analyzer."""

from typing import List, Dict, Any, Optional
from ..models.event import Event


class StorageAlertAnalyzer:
    """Analyzer for storage alert events."""
    
    def __init__(self, storage_alerts: List[Dict[str, Any]], production_plan: List[Dict[str, Any]]):
        self.storage_alerts = storage_alerts
        self.production_plan = sorted(production_plan, key=lambda x: x['collected_at'])
    
    def analyze(self) -> List[Event]:
        """
        Identify all storage alert events.
        
        Returns:
            List of storage alert Event objects
        """
        events = []
        event_counter = 1
        
        for alert_record in self.storage_alerts:
            msg = alert_record['message']
            trigger_ts = msg['triggerTs']
            
            # Calculate totals
            tot_a = msg['aFresh'] + msg['aDry']
            tot_b = msg['bFresh'] + msg['bDry']
            tot_fresh = msg['aFresh'] + msg['bFresh']
            tot_dried = msg['aDry'] + msg['bDry']
            
            # Find minimum
            min_value = min(tot_a, tot_b, tot_fresh, tot_dried)
            
            # Determine if we need SwapBlade or ChangeFreshAmount
            if min_value in (tot_a, tot_b):
                # Look for SwapBlade with storageAlert context
                reaction = self._find_swap_blade(trigger_ts)
                if reaction:
                    solved_ts = self._find_blade_swapped(reaction['reaction_ts'])
                else:
                    continue
            else:
                # Look for ChangeFreshAmount
                reaction = self._find_change_fresh_amount(trigger_ts)
                if reaction:
                    solved_ts = self._find_fresh_amount_changed(reaction['reaction_ts'])
                else:
                    continue
            
            if reaction and solved_ts:
                event = Event(
                    id=f"sA-{event_counter:03d}",
                    type="storageAlert",
                    trigger_ts=trigger_ts,
                    reaction_ts=reaction['reaction_ts'],
                    solved_ts=solved_ts,
                    scheduler_latency=reaction['reaction_ts'] - trigger_ts,
                    machine_latency=solved_ts - reaction['reaction_ts']
                )
                events.append(event)
                event_counter += 1
        
        return events
    
    def _find_swap_blade(self, trigger_ts: int) -> Optional[Dict[str, Any]]:
        """Find SwapBlade message with storageAlert context within 10 seconds."""
        for record in self.production_plan:
            msg = record['message']
            reaction_ts = record['collected_at']
            
            if msg.get('title') == 'SwapBlade':
                event_context = msg.get('eventContext', '')
                if event_context.startswith('storageAlert'):
                    # Check if within 10 seconds
                    if 0 <= reaction_ts - trigger_ts <= 10000:
                        return {'reaction_ts': reaction_ts, 'machineId': msg['machineId']}
        
        return None
    
    def _find_change_fresh_amount(self, trigger_ts: int) -> Optional[Dict[str, Any]]:
        """Find ChangeFreshAmount message within 10 seconds."""
        for record in self.production_plan:
            msg = record['message']
            reaction_ts = record['collected_at']
            
            if msg.get('title') == 'ChangeFreshAmount':
                # Check if within 10 seconds
                if 0 <= reaction_ts - trigger_ts <= 10000:
                    return {'reaction_ts': reaction_ts}
        
        return None
    
    def _find_blade_swapped(self, reaction_ts: int) -> Optional[int]:
        """Find BladeSwapped confirmation after reaction."""
        for record in self.production_plan:
            msg = record['message']
            if msg.get('title') == 'BladeSwapped' and record['collected_at'] > reaction_ts:
                return record['collected_at']
        
        return None
    
    def _find_fresh_amount_changed(self, reaction_ts: int) -> Optional[int]:
        """Find FreshAmountChanged confirmation after reaction."""
        for record in self.production_plan:
            msg = record['message']
            if msg.get('title') == 'FreshAmountChanged' and record['collected_at'] > reaction_ts:
                return record['collected_at']
        
        return None