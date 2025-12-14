# Modifiability Experiment Design Analysis

## Executive Summary

Your experiment design is **solid and well-structured**. It clearly tests modifiability by varying system complexity (machine count) and stress (killable machines), measuring how the scheduler adapts to events. Below is a complete analysis with suggested code modifications.

---

## Design Review: What You Got Right ✅

### 1. **Event Definition is Precise**
Your three-tier event definition is excellent:
- **Tier 1**: System change occurs (storageAlert, machine failure, new machine)
- **Tier 2**: Scheduler detects and reacts (publishes command)
- **Tier 3**: System reaches desired state (solved_ts criterion met)

This prevents noise (e.g., multiple alerts for same condition) and focuses on **actionable** events.

### 2. **Treatment Variables are Well-Chosen**
- **Machines (3, 5)**: Tests modifiability under different scales
- **Max killable machines (0 to 4)**: Tests stress levels and adaptation complexity
- **Fixed schedulers (max=1)**: Controls one variable to isolate machine-related behavior

### 3. **Scenario Matrix is Complete**
- 3 machines: 3 scenarios (0, 1, 2 killable) = baseline + single stress + dual stress
- 5 machines: 5 scenarios (0, 1, 2, 3, 4 killable) = more granular stress levels
- **Total: 8 scenarios**, each generating 100 events = 800 events total (good statistical base)

### 4. **Timestamp Sequence Makes Sense**
```
trigger_ts → reaction_ts → solved_ts
```
This captures:
- **Detection latency** (trigger→reaction)
- **Resolution latency** (reaction→solved)
- **Total response time** (trigger→solved)

---

## Design Considerations: What to Verify ⚠️

### 1. **Event Type Definitions Need Clarification**

**Question:** When categorizing events, consider these edge cases:

#### a) **Machine Failure Event**
You state: "machineFaillure is considered an event **only if the scheduler swaps a blade to solve it**"

**Issue:** What if a machine fails but scheduler does NOT swap because:
- No imbalance exists (e.g., 5 machines, 2 with A fail, 3 with A still healthy)
- No machine with other blade type available to swap from
- Scheduler removes the machine but doesn't swap anything

**Recommendation:** Clarify your definition:
```
Option A (Current): Ignore non-swap failures
  - Pro: Only count "solved" failures
  - Con: Miss important non-solvable failures
  
Option B (Recommended): Count all failures, add "resolution_type"
  - failure_resolved_by: "blade_swap" | "no_action_needed" | "unsolvable"
  - This shows modifiability: can scheduler handle diverse failure types?
```

#### b) **Storage Alert Event**
You state: "only the first one is considered the beginning of an event"

**Issue:** What's your deduplication window?
- Same storage condition continues → multiple alerts from DbInterface
- Should you deduplicate by: storage state (aFresh, aDry, bFresh, bDry) or by problem type?

**Recommendation:** Define explicitly:
```
Deduplication rule:
- Storage Alert is NEW EVENT if:
  1. Previous event is SOLVED (all levels back in 20-80%)
  2. AND a DIFFERENT storage problem detected
     (e.g., aFresh<20% vs. bFresh>80% = different events)
- Otherwise: part of same ongoing event (ignore trigger_ts)
```

#### c) **New Machine Event**
You state: "solved when there is a heartbeat of that machine with bladeType"

**Issue:** What if machine restarts and is re-discovered?
- First discovery: trigger_ts = first heartbeat without blade
- Recovery after kill: is this a NEW event or same event?

**Recommendation:** Clarify:
```
NEW machine event ONLY if:
- Machine was not previously tracked by scheduler
- For recovered machines: this is a NEW event
  (previous event was "machine_failure")
```

---

### 2. **Determinism & Reproducibility**

**Question:** Will you run each scenario multiple times?

**Recommendation:**
```
Approach A (Single run per scenario):
- Fast (1 run × 8 scenarios)
- Risk: One bad run skews results
- Suggestion: Set fixed random seed in ChaosPanda

Approach B (Multiple runs per scenario, average):
- Better statistics (3-5 runs × 8 scenarios)
- More robust to variability
- Better for showing consistency of modifiability

Recommendation: Approach B with fixed seed
```

**Implementation:**
- Fix ChaosPanda random seed (chaos_engine.py)
- Fix BatchManager reduction randomness seed (batch_manager.py)
- Document: "Each scenario run is deterministic"

---

### 3. **Collection Duration & Event Count**

**Question:** How do you know when you have 100 events?

**Recommendation:** Define stopping criteria:
```
Option A: Time-based (run 30 minutes per scenario)
- Problem: May not reach 100 events in low-chaos scenario
- Problem: May exceed 100 in high-chaos scenario

Option B: Event-based (stop after 100 SOLVED events)
- Recommended: More predictable dataset
- Ensures consistent event count
- Takes longer in low-chaos scenarios (but that's informative)

Option C: Hybrid (30 min timeout OR 100 events)
- Practical compromise
- Note in results: which scenarios hit timeout
```

**Recommendation: Option B** (proves modifiability across all event types, not just time)

---

## Code Modifications Required

### Overview of Changes

| Component                | Change                        | Purpose                      | Priority   |
|──────────────────────────|───────────────────────────────|──────────────────────────────|────────────|
| **Scheduler**            | Add event context to messages | Track reaction_ts and reason | **HIGH**   |
| **DbInterface**          | Add event ID to StorageAlert  | Deduplicate storage alerts   | **HIGH**   |
| **MqttKafkaBridge**      | Add context propagation       | Preserve event tracing       | **MEDIUM** |
| **CuttingMachine**       | Log blade assignment/swap     | Capture solved_ts            | **MEDIUM** |
| **KafkaCollector** (new) | Collect all messages          | Build event timeline         | **HIGH**   |
| **EventProcessor** (new) | Correlate messages to events  | Generate CSV                 | **HIGH**   |
| **ChaosPanda**           | Add deterministic mode        | Reproducible chaos           | **LOW**    |
