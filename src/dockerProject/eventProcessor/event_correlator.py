"""
Event correlation: matches triggers, reactions, and resolutions into events
Feature-complete Option 1:
  - newMachine: one event per WAITING_FOR_ASSIGNMENT period (first heartbeat without blade per period)
  - machineFailure: trigger is last heartbeat before a >=10s gap; reaction is SwapBlade with eventContext "machineFailure:machine_<id>"; solved_ts is BladeSwapped.timestamp for the target machine of the SwapBlade
  - storageAlert: an event for each alert; reaction is SwapBlade/ChangeFreshAmount with eventContext "storageAlert:<alertId>:problem_<category>";
                 solved_ts is first storageLevels snapshot (>= reaction) where ONLY the keys that were out-of-range at trigger are back within 20–80%
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from event_definitions import (
    Event, EventType, ReactionType
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)


class EventCorrelator:
    """Correlates Kafka messages and machine logs into experiment events"""

    # ---- Filenames (expected in collector_output) ----
    HEARTBEATS_FILE = "heartbeats.jsonl"
    COMMANDS_FILE = "productionPlan.jsonl"
    ALERTS_FILE = "storageAlerts.jsonl"
    LEVELS_FILE = "storageLevels.jsonl"

    def __init__(self, collector_output_dir: Path):
        self.output_dir = Path(collector_output_dir)

        # Raw message collections
        self.heartbeats: List[dict] = []
        self.commands: List[dict] = []
        self.storage_alerts: List[dict] = []
        self.storage_levels: List[dict] = []

        # Indices for fast lookup
        self.alerts_by_id: Dict[str, List[dict]] = defaultdict(list)    # alertId -> [alerts]
        self.commands_by_event_context: Dict[str, List[dict]] = defaultdict(list)
        self.assign_by_machine: Dict[int, List[dict]] = defaultdict(list)      # machineId -> [AssignBlade commands]
        self.swap_by_failure_machine: Dict[int, List[dict]] = defaultdict(list)  # failing machineId -> [SwapBlade]
        self.blade_swapped_by_machine: Dict[int, List[dict]] = defaultdict(list) # machineId -> [BladeSwapped]
        self.levels_sorted: List[dict] = []  # storageLevels sorted by collected_at

        # Events being built
        self.pending_events: Dict[str, Event] = {}  # event_id -> partial Event
        self.solved_events: List[Event] = []

        # Load & index
        self.load_data()
        self.build_indices()

    # ---------------------------- data loading ----------------------------

    def _load_jsonl(self, file_path: Path) -> List[dict]:
        """Load NDJSON lines from file_path; return list of parsed dicts."""
        records = []
        if not file_path.exists():
            LOGGER.warning("Input file NOT FOUND: %s", file_path)
            return records
        with open(file_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except Exception as e:
                    LOGGER.warning("Error parsing line in %s: %s", file_path.name, e)
        LOGGER.info("Loaded %d lines from %s", len(records), file_path.name)
        return records

    def load_data(self):
        """Load messages from collector_output directory."""
        hb_records = self._load_jsonl(self.output_dir / self.HEARTBEATS_FILE)
        for rec in hb_records:
            msg = rec.get("message", {})
            msg["_collected_at"] = rec.get("collected_at")
            self.heartbeats.append(msg)

        cmd_records = self._load_jsonl(self.output_dir / self.COMMANDS_FILE)
        for rec in cmd_records:
            msg = rec.get("message", {})
            msg["_collected_at"] = rec.get("collected_at")
            self.commands.append(msg)

        alert_records = self._load_jsonl(self.output_dir / self.ALERTS_FILE)
        for rec in alert_records:
            msg = rec.get("message", {})
            msg["_collected_at"] = rec.get("collected_at")
            self.storage_alerts.append(msg)

        level_records = self._load_jsonl(self.output_dir / self.LEVELS_FILE)
        self.storage_levels = level_records  # keep full record (has 'message' nested)

        # sort streams
        self.heartbeats.sort(key=lambda x: x.get("timestamp", 0))
        self.commands.sort(key=lambda x: x.get("reactionTs", x.get("_collected_at", 0)))
        self.storage_alerts.sort(key=lambda x: x.get("triggerTs", 0))
        self.storage_levels.sort(key=lambda x: x.get("collected_at", 0))

        LOGGER.info("After loading: %d heartbeats, %d commands, %d alerts, %d storageLevels",
                    len(self.heartbeats), len(self.commands), len(self.storage_alerts), len(self.storage_levels))

    # ---------------------------- indexing ----------------------------

    def build_indices(self):
        """Build indices for faster correlation."""
        # alerts by id (allow multiple alerts per id if any)
        for alert in self.storage_alerts:
            self.alerts_by_id[alert.get("alertId")].append(alert)

        # commands by eventContext (a context can have multiple commands over time)
        for cmd in self.commands:
            ctx = cmd.get("eventContext")
            if ctx:
                self.commands_by_event_context[ctx].append(cmd)

            title = cmd.get("title")
            if title == "AssignBlade":
                mid = cmd.get("machineId")
                if mid is not None:
                    self.assign_by_machine[mid].append(cmd)
            elif title == "SwapBlade":
                ctx = cmd.get("eventContext", "")
                # machine failure swaps
                if ctx.startswith("machineFailure:"):
                    part = ctx.split(":", 1)[1]  # e.g., machine_0
                    raw = part.replace("machine_", "")
                    try:
                        failing_id = int(raw)
                        self.swap_by_failure_machine[failing_id].append(cmd)
                    except ValueError:
                        pass
            elif title == "BladeSwapped":
                mid = cmd.get("machineId")
                if mid is not None:
                    self.blade_swapped_by_machine[mid].append(cmd)

        # sort indexed lists by reactionTs/_collected_at/ timestamp as appropriate
        for lst in self.assign_by_machine.values():
            lst.sort(key=lambda x: x.get("reactionTs", x.get("_collected_at", 0)))
        for lst in self.swap_by_failure_machine.values():
            lst.sort(key=lambda x: x.get("reactionTs", x.get("_collected_at", 0)))
        for lst in self.blade_swapped_by_machine.values():
            # BladeSwapped carries 'timestamp'
            lst.sort(key=lambda x: x.get("timestamp", x.get("reactionTs", x.get("_collected_at", 0))))

        # For storageLevels, keep a projected list sorted by collected_at with values
        self.levels_sorted = sorted(self.storage_levels, key=lambda r: r.get("collected_at", 0))

    # ---------------------------- main API ----------------------------

    def correlate_events(self) -> List[Event]:
        """Main correlation logic: build events from messages."""
        LOGGER.info("Starting event correlation...")
        self._process_storage_alert_triggers()
        self._process_machine_triggers()
        self._correlate_reactions()
        self._correlate_resolutions()
        # keep only solved events
        self.solved_events = [e for e in self.pending_events.values() if e.solved_ts is not None]
        LOGGER.info("Correlated %d solved events", len(self.solved_events))
        return sorted(self.solved_events, key=lambda e: e.trigger_ts)

    # ---------------------------- triggers ----------------------------

    def _process_storage_alert_triggers(self):
        """Create a storageAlert event per alert (no category-based dedup)."""
        LOGGER.info("Processing storage alert triggers...")
        for alert in self.storage_alerts:
            alert_id = alert.get("alertId")
            category = alert.get("problemCategory")
            trigger_ts = alert.get("triggerTs", 0)
            event_id = f"storageAlert:{alert_id}:problem_{category}:{trigger_ts}"
            event = Event(
                event_id=event_id,
                event_type=EventType.STORAGE_ALERT.value,
                trigger_ts=trigger_ts,
                trigger_source="dbInterface",
                reaction_ts=None,
                reaction_type=ReactionType.NONE.value,
                solved_ts=None,
                related_machine_id=None,
                related_alert_id=alert_id,
                resolution_time_ms=None,
                total_response_time_ms=None,
                metadata=json.dumps(alert),
            )
            self.pending_events[event_id] = event

    def _process_machine_triggers(self):
        """
        Create triggers for:
        - newMachine: one event per WAITING_FOR_ASSIGNMENT period (first heartbeat without blade per period)
        - machineFailure: for each >=10s heartbeat gap, use the earlier heartbeat timestamp as trigger
        """
        LOGGER.info("Processing machine triggers...")
        # newMachine triggers: detect transitions to WAITING state (no bladeType)
        hb_by_machine: Dict[int, List[dict]] = defaultdict(list)
        for hb in self.heartbeats:
            mid = hb.get("machineId")
            if mid is not None:
                hb_by_machine[mid].append(hb)

        for mid, hbs in hb_by_machine.items():
            hbs.sort(key=lambda x: x.get("timestamp", 0))
            prev_has_blade = False  # seen working with blade prior to this hb?
            for hb in hbs:
                ts = hb.get("timestamp", 0)
                waiting = hb.get("state") == "WAITING_FOR_ASSIGNMENT"
                has_blade = hb.get("bladeType") is not None
                # Trigger when entering WAITING (no blade), either first ever or after a working period
                if waiting and not has_blade and (not prev_has_blade or prev_has_blade):
                    # Only trigger when previous was with blade OR machine never seen before (first WAITING period)
                    # We enforce "one per WAITING period" by checking previous hb
                    # If previous hb also WAITING (no blade), skip; else create trigger
                    # (Implement: create when previous hb had blade or this is the first hb for machine)
                    prev_idx = hbs.index(hb) - 1
                    prev_hb = hbs[prev_idx] if prev_idx >= 0 else None
                    prev_was_waiting = (
                        prev_hb is None or (
                            prev_hb.get("state") == "WAITING_FOR_ASSIGNMENT" and prev_hb.get("bladeType") is None
                        )
                    )
                    if prev_hb is None or not prev_was_waiting:
                        event_id = f"newMachine:machine_{mid}:{ts}"
                        event = Event(
                            event_id=event_id,
                            event_type=EventType.NEW_MACHINE.value,
                            trigger_ts=ts,
                            trigger_source="cutting_machine_discovery",
                            reaction_ts=None,
                            reaction_type=ReactionType.NONE.value,
                            solved_ts=None,
                            related_machine_id=mid,
                            related_alert_id=None,
                            resolution_time_ms=None,
                            total_response_time_ms=None,
                            metadata=json.dumps({"first_state": "WAITING_FOR_ASSIGNMENT"})
                        )
                        self.pending_events[event_id] = event
                prev_has_blade = has_blade or prev_has_blade

        # machineFailure triggers: detect >=10s gaps
        for mid, hbs in hb_by_machine.items():
            timestamps = [hb.get("timestamp", 0) for hb in hbs]
            for i in range(len(timestamps) - 1):
                t1 = timestamps[i]
                t2 = timestamps[i + 1]
                if t2 - t1 >= 10000:  # 10 seconds gap
                    event_id = f"machineFailure:machine_{mid}:{t1}"
                    event = Event(
                        event_id=event_id,
                        event_type=EventType.MACHINE_FAILURE.value,
                        trigger_ts=t1,
                        trigger_source="heartbeat_monitor",
                        reaction_ts=None,
                        reaction_type=ReactionType.NONE.value,
                        solved_ts=None,
                        related_machine_id=mid,
                        related_alert_id=None,
                        resolution_time_ms=None,
                        total_response_time_ms=None,
                        metadata=json.dumps({"gap_ms": t2 - t1}),
                    )
                    self.pending_events[event_id] = event

    # ---------------------------- reactions ----------------------------

    def _correlate_reactions(self):
        """Attach scheduler reactions to pending events."""
        LOGGER.info("Correlating reactions...")
        for event_id, e in self.pending_events.items():
            if e.event_type == EventType.NEW_MACHINE.value:
                self._attach_assign_blade_reaction(e)
            elif e.event_type == EventType.MACHINE_FAILURE.value:
                self._attach_swap_blade_reaction_for_failure(e)
            elif e.event_type == EventType.STORAGE_ALERT.value:
                self._attach_alert_reaction(e)

    def _attach_assign_blade_reaction(self, e: Event):
        """Find earliest AssignBlade for machine at/after trigger."""
        mid = e.related_machine_id
        assigns = self.assign_by_machine.get(mid, [])
        for cmd in assigns:
            rt = cmd.get("reactionTs", cmd.get("_collected_at", 0))
            if rt >= e.trigger_ts:
                e.reaction_ts = rt
                e.reaction_type = ReactionType.ASSIGN_BLADE.value
                e.resolution_time_ms = rt - e.trigger_ts
                return

    def _attach_swap_blade_reaction_for_failure(self, e: Event):
        """Find SwapBlade with context 'machineFailure:machine_<id>' earliest at/after trigger."""
        mid = e.related_machine_id
        swaps = self.swap_by_failure_machine.get(mid, [])
        for cmd in swaps:
            rt = cmd.get("reactionTs", cmd.get("_collected_at", 0))
            if rt >= e.trigger_ts:
                e.reaction_ts = rt
                e.reaction_type = ReactionType.SWAP_BLADE.value
                e.metadata = json.dumps({"swap_target_machine": cmd.get("machineId")})
                e.resolution_time_ms = rt - e.trigger_ts
                return

    def _attach_alert_reaction(self, e: Event):
        """Match alert reaction:
           - If category A/B -> SwapBlade with eventContext storageAlert:<alertId>:problem_<A|B>
           - If category fresh/dried -> ChangeFreshAmount with same context
        """
        alert = json.loads(e.metadata)
        alert_id = alert.get("alertId")
        category = alert.get("problemCategory")
        ctx = f"storageAlert:{alert_id}:problem_{category}"
        cmds = self.commands_by_event_context.get(ctx, [])
        if not cmds:
            return
        # earliest reaction at/after trigger_ts
        for cmd in sorted(cmds, key=lambda x: x.get("reactionTs", x.get("_collected_at", 0))):
            rt = cmd.get("reactionTs", cmd.get("_collected_at", 0))
            if rt >= e.trigger_ts:
                e.reaction_ts = rt
                e.reaction_type = cmd.get("title", ReactionType.NONE.value)
                e.resolution_time_ms = rt - e.trigger_ts
                return

    # ---------------------------- resolutions ----------------------------

    def _correlate_resolutions(self):
        """Resolve pending events (set solved_ts)."""
        LOGGER.info("Correlating resolutions...")
        for e in self.pending_events.values():
            if e.event_type == EventType.NEW_MACHINE.value:
                self._resolve_new_machine(e)
            elif e.event_type == EventType.MACHINE_FAILURE.value:
                self._resolve_machine_failure(e)
            elif e.event_type == EventType.STORAGE_ALERT.value:
                self._resolve_storage_alert(e)

    def _resolve_new_machine(self, e: Event):
        """Solved when machine emits heartbeat with the assigned bladeType (>= reaction)."""
        if e.reaction_ts is None:
            return
        mid = e.related_machine_id
        # find assigned blade in the AssignBlade command we used
        assigns = self.assign_by_machine.get(mid, [])
        assigned_blade = None
        for cmd in assigns:
            rt = cmd.get("reactionTs", cmd.get("_collected_at", 0))
            if rt == e.reaction_ts:
                assigned_blade = cmd.get("bladeType")
                break
        if assigned_blade is None:
            # fallback: choose first AssignBlade at reaction_ts
            for cmd in assigns:
                rt = cmd.get("reactionTs", cmd.get("_collected_at", 0))
                if rt >= e.reaction_ts:
                    assigned_blade = cmd.get("bladeType")
                    break
        if assigned_blade is None:
            return

        for hb in self.heartbeats:
            if (hb.get("machineId") == mid and
                hb.get("timestamp", 0) >= e.reaction_ts and
                hb.get("bladeType") == assigned_blade):
                e.solved_ts = hb.get("timestamp")
                e.total_response_time_ms = e.solved_ts - e.trigger_ts
                return

    def _resolve_machine_failure(self, e: Event):
        """Solved at BladeSwapped.timestamp for target machine of the SwapBlade reaction."""
        if e.reaction_ts is None:
            return
        # find the SwapBlade we used and its target machine
        mid = e.related_machine_id
        swaps = self.swap_by_failure_machine.get(mid, [])
        target_mid = None
        for cmd in swaps:
            rt = cmd.get("reactionTs", cmd.get("_collected_at", 0))
            if rt == e.reaction_ts:
                target_mid = cmd.get("machineId")
                break
        if target_mid is None:
            # fallback: pick earliest swap >= reaction_ts
            for cmd in swaps:
                rt = cmd.get("reactionTs", cmd.get("_collected_at", 0))
                if rt >= e.reaction_ts:
                    target_mid = cmd.get("machineId")
                    break
        if target_mid is None:
            return

        # resolve via BladeSwapped for target machine
        swapped_msgs = self.blade_swapped_by_machine.get(target_mid, [])
        for bm in swapped_msgs:
            t = bm.get("timestamp", bm.get("reactionTs", bm.get("_collected_at", 0)))
            if t >= e.reaction_ts:
                e.solved_ts = t
                e.total_response_time_ms = e.solved_ts - e.trigger_ts
                return

    # ---- storageLevels helpers ----

    @staticmethod
    def _alert_affected_keys(alert_msg: dict) -> List[str]:
        """Return keys that were out of range at trigger (only those count toward solved)."""
        affected = []
        for key in ("aFresh", "aDry", "bFresh", "bDry"):
            v = alert_msg.get(key)
            if v is not None:
                try:
                    fv = float(v)
                    if not (20.0 <= fv <= 80.0):
                        affected.append(key)
                except Exception:
                    pass
        return affected

    def _first_levels_ok_after(self, ts: int, affected_keys: List[str]) -> Optional[int]:
        """From storageLevels, find first collected_at >= ts where all affected keys are back within 20–80%."""
        for rec in self.levels_sorted:
            collected_at = rec.get("collected_at", 0)
            if collected_at < ts:
                continue
            msg = rec.get("message", {})
            # If there were no affected keys (rare), consider first snapshot after ts as solved
            if not affected_keys:
                return collected_at
            ok = True
            for k in affected_keys:
                val = msg.get(k)
                if val is None:
                    ok = False
                    break
                try:
                    fv = float(val)
                except Exception:
                    ok = False
                    break
                if not (20.0 <= fv <= 80.0):
                    ok = False
                    break
            if ok:
                return collected_at
        return None

    def _resolve_storage_alert(self, e: Event):
        """Solved when only the out-of-range levels at trigger are back in range (via storageLevels)."""
        if e.reaction_ts is None:
            return
        alert_msg = json.loads(e.metadata)
        affected_keys = self._alert_affected_keys(alert_msg)
        solved_at = self._first_levels_ok_after(e.reaction_ts, affected_keys)
        if solved_at is not None:
            e.solved_ts = solved_at
            e.total_response_time_ms = e.solved_ts - e.trigger_ts