# Pasta Production System - Complete Project Overview

## Architecture Summary

Docker-based pasta factory simulation with Python and Java microservices communicating via Kafka/MQTT bridge. The system includes cutting machines (Python), a scheduler (Java) with active/shadow instances for failover, database monitoring (Java), batch production simulation (Python), and real-time Kafka monitoring. Leader election via Redis coordinates scheduler instances. The system demonstrates resilience patterns with chaos engineering capabilities.

---

## Folder Structure

```
dockerProject/
├── cuttingMachine/              # Python project for cutting machine simulation
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── main.py                  # Entry point
│   ├── cutting_machine.py       # Core machine orchestrator
│   ├── state.py                 # State machine (INITIALIZING→WAITING→WORKING→RECOVERY)
│   ├── mqtt_manager.py          # MQTT connection management
│   ├── message_handler.py       # Incoming MQTT message processing
│   ├── heartbeat.py             # Periodic heartbeat generation
│   └── .gitignore
│
├── scheduler/                   # Java project for production scheduler (active/shadow)
│   ├── pom.xml
│   ├── Dockerfile               # Multi-stage build (JDK→JRE)
│   ├── src/main/java/com/pasta/scheduler/
│   │   ├── Scheduler.java       # Main entry, leader election, thread orchestration
│   │   ├── kafka/
│   │   │   ├── KafkaConsumerManager.java     # Consumes heartbeats, storageAlerts
│   │   │   └── KafkaProducerManager.java     # Sends AssignBlade, SwapBlade, ChangeFreshAmount
│   │   ├── machine/
│   │   │   ├── Machine.java                  # Machine state object
│   │   │   └── MachineManager.java           # Tracks machines, deduplicates heartbeats, health checks
│   │   ├── redis/RedisManager.java           # Leader election (5s lease), state persistence
│   │   ├── storage/StorageAlertHandler.java  # Reacts to storage threshold violations
│   │   └── enums/BladeType.java              # Blade type enumeration
│   ├── .gitignore
│   └── .idea/                   # IDE configuration
│
├── dbInterface/                 # Java project for database monitoring
│   ├── pom.xml
│   ├── Dockerfile               # Multi-stage build
│   ├── src/main/java/com/pasta/dbinterface/
│   │   ├── DbInterface.java     # Main entry, coordinates monitoring
│   │   ├── db/DatabaseManager.java           # JDBC wrapper with 30-retry connection logic
│   │   ├── kafka/KafkaProducerManager.java   # Sends StorageAlert messages
│   │   └── storage/StorageMonitor.java       # Queries DB, detects threshold violations
│   ├── .gitignore
│   └── .idea/
│
├── sortingSubsystem/            # Java project for fresh amount management
│   ├── pom.xml
│   ├── Dockerfile               # Multi-stage build
│   ├── src/main/java/com/pasta/sortingsubsystem/
│   │   ├── SortingSubsystem.java             # Main entry
│   │   ├── FreshAmountManager.java           # Manages freshAmount (0-10)
│   │   └── kafka/
│   │       ├── KafkaConsumerManager.java     # Consumes ChangeFreshAmount
│   │       └── KafkaProducerManager.java     # Sends FreshAmountChanged confirmation
│   ├── .gitignore
│   └── .idea/
│
├── simulationEngine/            # Python project for batch production simulation
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── __init__.py
│   ├── app.py                   # Main entry point
│   ├── database.py              # SQLAlchemy/JDBC wrapper with retry logic
│   ├── kafka_producer.py        # Confluent Kafka producer manager
│   └── batch_manager.py         # Creates batches, balances stock (target=200), sends storage levels
│
├── mqttKafkaBridge/             # Python bridge for MQTT↔Kafka
│   ├── Dockerfile
│   ├── requirements.txt
│   └── mqtt_kafka_broker.py     # Bidirectional message forwarding with intelligent topic routing
│
├── kafka-monitor/               # Python Kafka message monitoring
│   ├── Dockerfile
│   ├── requirements.txt
│   └── kafka_monitor.py         # Real-time colored terminal output
│
├── chaosPanda/                  # Python chaos engineering tool (Netflix ChaosMonkey inspired)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                  # Entry point with argument parsing
│   ├── chaos_engine.py          # Main chaos injection and recovery logic
│   ├── docker_manager.py        # Docker container operations
│   ├── kafka_reporter.py        # Reports chaos events to Kafka
│   └── redis_inspector.py       # Inspects Redis for scheduler state
│
├── mosquitto/
│   └── config/mosquitto.conf    # MQTT broker configuration
│
├── docker-compose.yml           # Orchestrates all services (13 total)
├── init.sql                     # PostgreSQL schema & initial data
├── run_experiment.sh            # Cleanup, rebuild, and experiment launcher
└── kafka_messages_summary.md    # Comprehensive message format documentation
```

---

## Component Details

### CuttingMachine (Python)

**Role:** Simulates physical cutting machines; sends periodic heartbeats; receives blade assignment/swap commands via MQTT; reports machine failures.

**State Machine:**
- `INITIALIZING` → `WAITING_FOR_ASSIGNMENT` → `WORKING` → `RECOVERY`
- Sends heartbeats every 5 seconds (with `bladeType` only in WORKING state)
- Enters RECOVERY for specified duration when receiving `killMachine` command

**Architecture:**
- **CuttingMachine**: Main orchestrator, coordinates MQTT/state/heartbeats/message handling
- **MqttManager**: Paho MQTT client wrapper with 30-retry connection logic (2s backoff)
- **MessageHandler**: Processes incoming MQTT messages (AssignBlade, SwapBlade, killMachine)
- **HeartbeatManager**: Generates and publishes heartbeats every 5s
- **MachineState**: Thread-safe state machine with blade tracking and recovery timeout

**Key Features:**
- Subscribes to: `productionPlan/assignBlade`, `productionPlan/swapBlade`, `updateManager/killMachine`
- Publishes to: `heartbeats` topic (every 5s)
- Publishes to: `productionPlan/bladeSwapped` (confirmation after blade swap)
- Handles blade swaps with 2s sleep before confirmation
- Tracks recovery mode state and exits after timeout
- Message filtering: ignores own `BladeSwapped` confirmation messages to prevent loops

**Fixed Issues:**
- ✅ Exact MQTT topics (no wildcards) for Paho 1.2.5 compatibility
- ✅ Initial heartbeat sent every 5s in WAITING state for discovery
- ✅ Duplicate message prevention for swap confirmations
- ✅ Thread-safe state updates with locks

---

### Scheduler (Java, Active + Shadow Instances)

**Role:** Orchestrates production by discovering machines, assigning blades, monitoring health, reacting to storage alerts, and managing freshAmount.

**Architecture:**
- **Active + Shadow instances** with Redis leader election (5s lease, NX set)
- Only active scheduler sends commands to machines
- Reads machine heartbeats & storage alerts from Kafka
- Publishes: AssignBlade, SwapBlade, ChangeFreshAmount to productionPlan topic
- Persists state to Redis for failover recovery

**Key Components:**
- **Scheduler.java**: Main orchestrator, leader election, thread management
  - **Leadership thread**: Renews lease every 3s; attempts acquisition if lost
  - **Consumer thread**: Processes heartbeats and storage alerts
  - **Health check thread**: Monitors machine health; removes unhealthy machines; triggers blade swaps
  - **Redis persistence thread**: Saves machine state & freshAmount every 5s
  
- **MachineManager**: 
  - Tracks machines, deduplicates heartbeats (1s time window)
  - Balances blade types (A/B) across machines
  - 12s discovery phase before sending initial AssignBlade
  - Removes unhealthy machines (>10s without heartbeat)
  - Initiates blade swaps when imbalance detected (failover recovery)
  
- **StorageAlertHandler**: 
  - Reacts to storage level violations (<20% or >80%)
  - Identifies problem category: blade type (A/B) or freshness (fresh/dry)
  - Adjusts freshAmount when fresh/dry imbalance detected
  - Initiates blade swaps for failing blade types
  - 10s cooldown per problem category to prevent spam
  
- **RedisManager**: 
  - Leader election via `SET active_scheduler primary NX EX 5`
  - Persists: machines, freshAmount, Kafka offsets to Redis keys
  - Enables recovery by shadow scheduler when active scheduler dies
  
- **KafkaConsumerManager**: 
  - Subscribes to `heartbeats` & `storageAlerts` topics
  - Latest offset, group='scheduler-group'
  - Tracks Kafka offsets per topic partition

**Fixed Issues:**
- ✅ Duplicate AssignBlade prevention via `assignedMachines` set
- ✅ Heartbeat deduplication with 1s time window (`lastHeartbeatTime` map)
- ✅ Discovery phase delay (12s) before sending commands
- ✅ Machine state recovery from Redis on failover
- ✅ Blade swap logic prevents redundant commands

---

### DbInterface (Java)

**Role:** Monitors database storage levels; sends alerts to Scheduler when thresholds breach.

**Components:**
- **DbInterface.java**: Main entry, coordinates monitoring
- **DatabaseManager.java**: JDBC wrapper with 30-retry connection logic (5s backoff)
- **StorageMonitor.java**: 
  - Every 10s queries DB: `SUM(inStock)` per `blade_type` × `isFresh`
  - Calculates storage % = (stock / 100) × 100
  - Sends `StorageAlert` if any value <20% or >80%
  - Deduplicates alerts: only sends if levels changed >1% since last alert
  - Thread-safe with lock for alert tracking

**Message Flow:** PostgreSQL → query totals → calculate percentages → breach detection → StorageAlert to `storageAlerts` topic

**Database Schema:**
```sql
pasta_db.batches (
  id SERIAL PRIMARY KEY,
  blade_type CHAR(1) CHECK (blade_type IN ('A', 'B')),
  isFresh BOOLEAN,
  productionDate TIMESTAMP,
  inStock INT CHECK (inStock >= 0)
)
```

---

### SortingSubsystem (Java)

**Role:** Manages `freshAmount` state (0-10); receives updates from Scheduler; sends confirmations.

**Components:**
- **SortingSubsystem.java**: Main entry, starts consumer thread
- **FreshAmountManager.java**: 
  - Tracks `freshAmount` (default=4)
  - Clamps updates to 0-10 range
  - Sends `FreshAmountChanged` confirmation to productionPlan topic
  
- **KafkaConsumerManager.java**: 
  - Consumes `ChangeFreshAmount` from productionPlan topic
  - Latest offset, group='sorting-subsystem-group'

**Purpose:** Controls fresh vs dry batch ratio. BatchManager uses this to split incoming batches (fresh_units = freshAmount, dry_units = 10 - freshAmount).

---

### SimulationEngine (Python)

**Role:** Simulates real factory; creates batches based on machine heartbeats; maintains target stock of 200 units.

**Components:**
- **app.py**: Main entry, initializes components and starts consumers
- **DatabaseConnection** (database.py): 
  - SQLAlchemy wrapper with retry logic (5s backoff, infinite retries)
  - Executes queries/inserts/updates with transaction management
  
- **KafkaProducerManager** (kafka_producer.py): 
  - Confluent Kafka producer with retry logic
  
- **BatchManager** (batch_manager.py): 
  - **Heartbeat Consumer**: 
    - Consumes heartbeats from `heartbeats` topic
    - Filters for messages with `bladeType` (WORKING machines only)
    - Creates 2 batches per heartbeat: fresh=freshAmount, dry=10-freshAmount
    - Each batch inStock = the calculated amount
  
  - **ProductionPlan Consumer**: 
    - Consumes `ChangeFreshAmount` messages
    - Updates `freshAmount` (0-10) for next batches
  
  - **Stock Balancing**: 
    - After each batch creation, queries total stock
    - If total > 200, randomly reduces batches until total = 200
    - Preserves deterministic but random reduction distribution
  
  - **Storage Level Publishing**: 
    - Calculates storage levels: (stock / 100) × 100 per blade_type × isFresh
    - Sends `StorageLevels` to `storageLevels` topic for dashboard

**Database Schema (same as DbInterface):**
```sql
CREATE TABLE pasta_db.batches (
  id SERIAL PRIMARY KEY,
  blade_type CHAR(1) NOT NULL CHECK (blade_type IN ('A', 'B')),
  isFresh BOOLEAN NOT NULL,
  productionDate TIMESTAMP NOT NULL,
  inStock INT NOT NULL CHECK (inStock >= 0)
);
```

**Initial Data:** 20 rows (5 per combination: A/B × fresh/dry), 10 units each = 200 total

---

### MqttKafkaBridge (Python)

**Role:** Bridges MQTT ↔ Kafka with intelligent topic routing and filtering.

**Architecture:**
- **MQTT → Kafka**:
  - Subscribes to MQTT: `heartbeats`, `productionPlan`, `productionPlan/bladeSwapped`
  - Filters by message `title` (allowed: BladeSwapped, heartbeat)
  - Forwards to Kafka `heartbeats` or `productionPlan` topics
  
- **Kafka → MQTT** (with subtopic routing):
  - Subscribes to Kafka: `productionPlan`, `updateManager`
  - Parses JSON to extract `title`
  - Routes by title:
    - `AssignBlade` → MQTT `productionPlan/assignBlade`
    - `SwapBlade` → MQTT `productionPlan/swapBlade`
    - `KillMachine` → MQTT `updateManager/killMachine`
  - Filters: only allowed titles forwarded

**Message Flow Examples:**
- Heartbeat: MQTT heartbeats → Kafka heartbeats
- Machine discovery: Kafka productionPlan (AssignBlade) → MQTT productionPlan/assignBlade
- Blade swap: Kafka productionPlan (SwapBlade) → MQTT productionPlan/swapBlade
- Blade swap confirmation: MQTT productionPlan/bladeSwapped → Kafka productionPlan

**Fixed Issues:**
- ✅ Removed `retain=True` flag to prevent message replay
- ✅ Added JSON-based topic routing instead of static mapping
- ✅ Message filtering prevents unauthorized commands

---

### KafkaMonitor (Python)

**Role:** Real-time terminal dashboard for debugging and monitoring.

**Features:**
- Consumes from: `heartbeats`, `productionPlan`, `batches`, `experiment` topics
- Multi-threaded: one consumer per topic
- Color-coded output:
  - 💓 Heartbeats (Magenta)
  - 📋 ProductionPlan (Blue)
  - 📦 StorageLevels/Batches (Green)
  - 🔨 Experiment (Yellow)
- Displays: timestamp, topic, formatted JSON payload
- Reads from beginning (`auto_offset_reset='earliest'`)
- Terminal-based with ANSI color codes

---

### ChaosPanda (Python) - Chaos Engineering Tool

**Role:** Netflix ChaosMonkey-inspired tool for testing system resilience. Randomly kills cutting machines and schedulers; reports events; auto-recovers containers.

**Architecture:**
- **ChaosEngine**: Main orchestrator
  - Chaos loop: kills random machines/schedulers every 5-15s
  - Recovery loop: restarts killed containers after 10-30s delay
  - Respects limits: `max_cutting_machines`, `max_schedulers` (concurrent killed count)
  
- **DockerManager**: Container operations
  - `get_cutting_machines()`: Lists all containers matching pattern
  - `get_schedulers()`: Lists scheduler containers
  - `stop_container()`: Stops with 10s timeout
  - `start_container()`: Restarts stopped container
  - `get_container_status()`: Returns current status
  
- **KafkaReporter**: Publishes chaos events
  - Reports `KillingMachine` with machineId, testName, timestamp
  - Reports `KillingScheduler` with schedulerRole, schedulerName, testName
  - Sends to `experiment` topic for monitoring
  
- **RedisInspector**: Determines scheduler roles
  - Checks Redis `active_scheduler` key
  - Returns boolean: is_active
  - Used to report whether killed scheduler was active or shadow

**Command-Line Arguments:**
```bash
python main.py \
  --max-cutting-machines 1      # Max concurrent machines to kill
  --max-schedulers 0            # Max concurrent schedulers to kill
  --kafka-bootstrap kafka:29092 # Kafka endpoint
  --redis-host redis            # Redis endpoint
  --redis-port 6379
  --docker-host unix:///var/run/docker.sock
  --test-name resilience-test-001
```

**Run Script** (`run_experiment.sh`):
1. Cleans up containers, networks, volumes
2. Builds all Docker images
3. Starts docker-compose services
4. Waits 30s for stabilization
5. Launches ChaosPanda container with custom parameters
6. Provides monitoring commands

---

## Infrastructure

### Docker Services (docker-compose.yml)

**14 Services Total:**

1. **Zookeeper**: Kafka coordination (confluentinc/cp-zookeeper:7.5.0)
2. **Kafka**: Message broker (confluentinc/cp-kafka:7.5.0)
   - 5 partitions, 1 replication factor
   - Auto-create topics enabled
   - Healthcheck: `kafka-topics --list`
   - Topics: heartbeats, productionPlan, storageAlerts, storageLevels, updateManager, experiment, batches
   
3. **PostgreSQL**: Production database (postgres:latest)
   - Schema: `pasta_db`
   - Init: `init.sql` creates batches table + 20 seed rows
   - Port: 5432
   
4. **pgAdmin**: Database UI (dpage/pgadmin4:latest)
   - Port: 5000
   - Credentials: admin@admin.com / pgadmin
   
5. **Redis**: Leader election & state persistence (redis:7-alpine)
   - Port: 6379
   - Keys: active_scheduler, scheduler:machines, scheduler:freshAmount, scheduler:kafka_offsets
   
6. **Mosquitto**: MQTT broker (eclipse-mosquitto:latest)
   - Ports: 1883 (MQTT), 9001 (WebSocket)
   - Healthcheck: netcat probe on port 1883
   - Config: mosquitto/config/mosquitto.conf
   
7. **mqtt-kafka-bridge**: Python bridge
   - depends_on: mosquitto (healthy), kafka (healthy)
   
8. **cutting-machine-0/1/2**: Python machines (3 instances)
   - depends_on: mosquitto (healthy)
   - MACHINE_ID: 0, 1, 2
   
9. **scheduler**: Java scheduler (active instance)
   - depends_on: kafka, redis
   - restart: on-failure
   
10. **scheduler-shadow**: Java scheduler (shadow instance)
    - depends_on: kafka, redis
    - restart: on-failure
    
11. **db-interface**: Java database monitor
    - depends_on: db, kafka
    - restart: on-failure
    
12. **sorting-subsystem**: Java batch sorting
    - depends_on: kafka
    - restart: on-failure
    
13. **pasta-system**: Python simulation engine
    - depends_on: db, kafka
    - Port: 8000
    
14. **kafka-monitor**: Python Kafka monitor
    - depends_on: kafka (healthy)
    - restart: on-failure

---

## Message Protocol

### Heartbeats (CuttingMachine → MQTT → Kafka)

**Without blade (WAITING_FOR_ASSIGNMENT):**
```json
{
  "title": "heartbeat",
  "machineId": 0
}
```

**With blade (WORKING):**
```json
{
  "title": "heartbeat",
  "machineId": 0,
  "bladeType": "A"
}
```

### AssignBlade (Scheduler → Kafka → MQTT)

```json
{
  "title": "AssignBlade",
  "machineId": 0,
  "bladeType": "A"
}
```
**Routed to MQTT:** `productionPlan/assignBlade`

### SwapBlade (Scheduler → Kafka → MQTT)

```json
{
  "title": "SwapBlade",
  "machineId": 0,
  "bladeType": "B"
}
```
**Routed to MQTT:** `productionPlan/swapBlade`

### BladeSwapped (CuttingMachine → MQTT → Kafka)

```json
{
  "title": "BladeSwapped",
  "machineId": 0
}
```

### StorageAlert (DbInterface → Kafka)

```json
{
  "title": "StorageAlert",
  "aFresh": 35.5,
  "aDry": 42.0,
  "bFresh": 28.3,
  "bDry": 31.2
}
```

### ChangeFreshAmount (Scheduler → Kafka)

```json
{
  "title": "ChangeFreshAmount",
  "freshAmount": 6
}
```

### FreshAmountChanged (SortingSubsystem → Kafka)

```json
{
  "title": "FreshAmountChanged",
  "freshAmount": 6
}
```

### KillMachine (Scheduler → Kafka → MQTT)

```json
{
  "title": "killMachine",
  "machineId": 0,
  "recoveryTime": 5
}
```
**Routed to MQTT:** `updateManager/killMachine`

### StorageLevels (BatchManager → Kafka)

```json
{
  "title": "StorageLevels",
  "aFresh": 50.0,
  "aDry": 50.0,
  "bFresh": 50.0,
  "bDry": 50.0
}
```

### NewBatch (BatchManager → Kafka) [Optional for monitoring]

```json
{
  "title": "NewBatch",
  "bladeType": "A",
  "freshness": "fresh"
}
```

### Chaos Events (ChaosPanda → Kafka)

**KillingMachine:**
```json
{
  "title": "KillingMachine",
  "machineId": 0,
  "testName": "resilience-test-001",
  "timestamp": "2025-11-20T14:30:45.123456Z"
}
```

**KillingScheduler:**
```json
{
  "title": "KillingScheduler",
  "schedulerRole": "active",
  "schedulerName": "scheduler",
  "testName": "resilience-test-001",
  "timestamp": "2025-11-20T14:30:45.123456Z"
}
```

---

## Key Workflows

### 1. Machine Discovery & Blade Assignment

1. **CuttingMachine 0 starts** → sends heartbeat (no blade) every 5s
2. **Scheduler receives heartbeat** → creates Machine(0, WAITING_FOR_ASSIGNMENT)
3. **Discovery phase (12s)** → Scheduler collects all machines
4. **After 12s** → Scheduler sends `AssignBlade(0, A)` to Kafka
5. **Bridge routes** → MQTT `productionPlan/assignBlade`
6. **Machine 0 receives** → transitions to WORKING, stores bladeType
7. **Next heartbeat** → includes `"bladeType": "A"`
8. **Scheduler deduplicates** (1s window) → no duplicate AssignBlade

### 2. Batch Production Cycle

1. **CuttingMachine sends heartbeat** (every 5s, with bladeType)
2. **BatchManager consumes** heartbeat with bladeType
3. **Create 2 batches:**
   - Fresh: inStock = freshAmount (default 4)
   - Dry: inStock = 10 - freshAmount (default 6)
   - Both: blade_type = "A", productionDate = now
4. **Total stock increased** (e.g., 200 → 210)
5. **Balance check**: if total > 200, randomly reduce batches to 200
6. **Calculate storage levels** per blade_type × isFresh
7. **Send StorageLevels** to Kafka for dashboard

### 3. Storage-Based Production Adjustment

1. **DbInterface queries** every 10s: `SUM(inStock)` per blade_type × isFresh
2. **Calculate %:** (stock / 100) × 100
3. **Threshold breach** → <20% or >80% detected
4. **Send StorageAlert** to Kafka with all 4 percentages
5. **Scheduler receives** alert → StorageAlertHandler analyzes
6. **Identify problem:**
   - Problem = MIN(totalA, totalB, totalFresh, totalDry)
   - Example: totalFresh=15%, totalDry=85% → problem="fresh"
7. **React:**
   - If problem="fresh" → `Scheduler.updateFreshAmount(+2 or +4)`
   - If problem="A" → find machine with blade B, send `SwapBlade(machineId, A)`
8. **Scheduler sends ChangeFreshAmount** to Kafka
9. **SortingSubsystem receives** → updates freshAmount
10. **BatchManager reads** new freshAmount for next batches
11. **Cooldown (10s)** → same problem category won't trigger again immediately

### 4. Machine Failover & Blade Swap

1. **Scheduler health check** (every 5s): finds machines with >10s no heartbeat
2. **Remove unhealthy machine** from tracking
3. **Analyze blade balance:**
   - Failed blade type: "A" (1 machine with A)
   - Other blade type: "B" (2 machines with B)
   - Imbalance: need swap if countFailed < countOther - 1
4. **Select machine to swap** → machine with blade B (most recent heartbeat)
5. **Send SwapBlade(machineId, A)** to Kafka
6. **Bridge routes** → MQTT `productionPlan/swapBlade`
7. **Machine receives** → sleeps 2s, updates blade_type
8. **Send BladeSwapped** confirmation
9. **Next heartbeat** → includes new blade type

### 5. Scheduler Failover & State Recovery

1. **Active scheduler crashes**
2. **Active lease expires** (5s timeout)
3. **Shadow scheduler attempts leadership** → Redis `SET active_scheduler primary NX EX 5`
4. **Shadow acquires active status** (because NX succeeds)
5. **Transition to ACTIVE** → loads state from Redis
6. **Load state from Redis:**
   - Machines: deserialize JSON, restore MachineManager
   - FreshAmount: restore from `scheduler:freshAmount`
   - Kafka offsets: restore to resume from last committed offset
7. **Resume operations** without duplicate commands (because machines already have blades assigned)

### 6. Chaos Engineering Test

1. **Run:** `./run_experiment.sh`
2. **ChaosPanda starts** with:
   - `--max-cutting-machines 1` (kill 1 at a time)
   - `--max-schedulers 0` (don't kill schedulers, or test failover)
3. **Chaos loop** every 5-15s:
   - Randomly select available machine/scheduler
   - Stop container via Docker API
   - Record killed containers with restart time (10-30s delay)
   - Report to Kafka `experiment` topic
4. **Recovery loop** checks every 5s:
   - For each killed container, if restart time reached:
   - Start container via Docker API
   - Remove from killed tracking
5. **Monitor:**
   - ChaosPanda logs: `docker logs chaospanda-experiment -f`
   - Kafka events: `docker logs kafka-monitor -f`
   - System adapts: Scheduler removes unhealthy machines, triggers blade swaps, rebalances stock

---

## Development & Deployment

### Running the System

```bash
# Full setup with experiment
./run_experiment.sh

# View logs by component
docker logs cutting-machine-0 -f
docker logs scheduler -f
docker logs scheduler-shadow -f
docker logs db-interface -f
docker logs sorting-subsystem -f
docker logs pasta-system -f
docker logs kafka-monitor -f

# Monitor Kafka messages (colored terminal)
docker logs kafka-monitor -f

# Access database UI
# http://localhost:5000 (pgAdmin)
# Server: db:5432
# Username: user / password: password
# Database: mydatabase

# Test MQTT directly
docker exec -it mosquitto sh
mosquitto_sub -h localhost -t 'productionPlan/assignBlade' -v
mosquitto_sub -h localhost -t 'productionPlan/swapBlade' -v
mosquitto_sub -h localhost -t 'heartbeats' -v

# Cleanup
docker-compose down -v
```

### Key Endpoints & Ports

- **MQTT:** localhost:1883 (Mosquitto)
- **Kafka:** localhost:9092 (external), kafka:29092 (internal)
- **PostgreSQL:** localhost:5432 (pgAdmin required for GUI at :5000)
- **Redis:** localhost:6379
- **Zookeeper:** localhost:2181

### Configuration & Environment Variables

**CuttingMachine:**
- `MACHINE_ID` (0, 1, 2, ...)
- `MQTT_BROKER` (default: mosquitto)
- `MQTT_PORT` (default: 1883)

**Scheduler:**
- `KAFKA_BOOTSTRAP_SERVERS` (default: kafka:29092)
- `REDIS_HOST` (default: redis)
- `REDIS_PORT` (default: 6379)

**DbInterface:**
- `DB_URL` (default: jdbc:postgresql://db:5432/mydatabase?user=user&password=password)
- `KAFKA_BOOTSTRAP_SERVERS` (default: kafka:29092)

**SimulationEngine:**
- `PYTHONUNBUFFERED=1` (for immediate log output)

**ChaosPanda:**
- See `--help` for all options

---

## Quality Attributes

### Availability
- ✅ 2 schedulers with Redis-based leader election (5s lease)
- ✅ Shadow scheduler auto-recovers when active dies
- ✅ Machines auto-reconnect to MQTT broker (30 retries, 2s backoff)
- ✅ Unhealthy machines removed, others rebalance blades
- ✅ Automatic blade swaps on machine failure
- ✅ State persisted to Redis for recovery

### Scalability
- ✅ Kafka partitioning across 5 partitions
- ✅ Machines discovered dynamically via heartbeats
- ✅ Multiple consumers per topic (different groups)
- ✅ Linear message throughput with machine count

### Modifiability
- ✅ Microservices architecture (6 independent services)
- ✅ Message-driven design via Kafka/MQTT
- ✅ Easy to add new machines (auto-discovery)
- ✅ Production logic centralized in Scheduler
- ✅ Storage thresholds configurable in DbInterface (20%, 80%)

### Deployability
- ✅ Docker Compose single-command deployment
- ✅ Zero-downtime scheduler failover
- ✅ Chaos engineering tests built-in (ChaosPanda)
- ✅ Multi-stage builds reduce image size
- ✅ Non-root user execution (security)

### Resilience
- ✅ Circuit-breaker patterns: retry logic on all network calls
- ✅ Graceful degradation: shadow scheduler takes over immediately
- ✅ Self-healing: unhealthy machines auto-removed, others adapt
- ✅ Chaos testing: intentional failure injection for validation

---

## Technology Stack

| Component | Language | Frameworks/Libraries | Role |
|-----------|----------|-------------------|------|
| CuttingMachine | Python 3.11 | paho-mqtt | MQTT machine simulation |
| Scheduler | Java 21 | Kafka, Redis/Jedis, Jackson | Production orchestration |
| DbInterface | Java 21 | JDBC, Kafka, PostgreSQL | Storage monitoring |
| SortingSubsystem | Java 21 | Kafka, Jackson | Fresh amount management |
| SimulationEngine | Python 3.11 | Kafka, SQLAlchemy, Faker | Batch production |
| MqttKafkaBridge | Python 3.11 | paho-mqtt, kafka-python | Message bridging |
| KafkaMonitor | Python 3.11 | kafka-python | Console monitoring |
| ChaosPanda | Python 3.11 | docker, redis, confluent-kafka | Chaos testing |
| **Infrastructure** | | | |
| MQTT Broker | Mosquitto | - | Message bus (machines) |
| Message Bus | Kafka 7.5.0 | Zookeeper | Central event stream |
| Coordination | Redis 7 | - | Leader election, state |
| Database | PostgreSQL | - | Batch storage |
| UI | pgAdmin | - | Database visualization |

---

## Testing & Validation

### Unit/Integration Testing Approach

1. **Message Format Validation**
   - See `kafka_messages_summary.md` for complete protocol specs
   - Each service validates incoming JSON schema before processing
   
2. **State Consistency**
   - Scheduler deduplicates heartbeats within 1s window
   - Redis persists state every 5s → validated on failover
   - Database transactions ensure atomic batch operations
   
3. **Resilience Testing**
   - **Manual chaos**: Stop any service, observe recovery
   - **Automated chaos** (ChaosPanda):
     ```bash
     ./run_experiment.sh  # Automatically kills/restarts machines
     docker logs chaospanda-experiment -f  # Monitor
     ```
   
4. **Performance Testing**
   - Stock rebalancing: handles 200+ units in milliseconds
   - Heartbeat processing: 3 machines × 5s interval = 0.6 Hz ingestion
   - Kafka throughput: ~100 messages/sec (low-volume system)

### Observed Behavior (Expected)

**Steady State:**
- Scheduler logs: "Received heartbeat from machine [0,1,2]" every 5s
- DbInterface logs: "Storage alert sent" when levels breach 20%/80%
- BatchManager: Stock oscillates around 200 (target ±10)
- KafkaMonitor: Colored heartbeats and commands flowing continuously

**During Machine Kill (Chaos):**
- ChaosPanda logs: "KILLING cutting machine: cutting-machine-0"
- Scheduler logs: "Machine 0 is unhealthy (last heartbeat: ...)" after 10s
- Scheduler logs: "Removed unhealthy machine 0"
- Scheduler logs: "Blade swap needed" if imbalance detected
- StorageAlert triggered if stock drops significantly
- After 10-30s: ChaosPanda restarts machine, new heartbeat received
- Scheduler logs: "New machine 0 created" (discovery phase repeats)

**During Scheduler Kill:**
- Active scheduler stops
- After 5s: Shadow scheduler acquires leadership
- Shadow logs: "✅ Acquired leadership, transitioning to ACTIVE"
- Shadow loads state from Redis
- Operations resume (no commands duplicated because machines already assigned)

---

## Common Issues & Troubleshooting

### Issue: Machines not sending heartbeats

**Diagnosis:**
```bash
docker logs cutting-machine-0 | grep heartbeat
```

**Likely causes:**
- MQTT connection failed (check mosquitto logs)
- Machine stuck in INITIALIZING state (check state transitions)
- Heartbeat thread crashed (check exception in logs)

**Fix:**
- Ensure mosquitto is running: `docker ps | grep mosquitto`
- Check mosquitto healthcheck: `docker inspect mosquitto`
- Restart machine: `docker restart cutting-machine-0`

### Issue: Scheduler not receiving heartbeats

**Diagnosis:**
```bash
docker logs kafka-monitor | grep heartbeat
```

**Likely causes:**
- Kafka not running or unhealthy
- Bridge not forwarding MQTT→Kafka
- Consumer group stuck at old offset

**Fix:**
- Check Kafka: `docker exec kafka kafka-topics --list --bootstrap-server localhost:9092`
- Reset offsets: `docker exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --group scheduler-group --reset-offsets --to-latest --execute --topic heartbeats`
- Restart scheduler: `docker restart scheduler`

### Issue: Storage alerts not triggered despite low stock

**Diagnosis:**
```bash
docker logs db-interface | grep "Storage alert"
```

**Likely causes:**
- Stock levels don't breach 20%/80%
- Thresholds hard-coded (StorageMonitor.java line ~18)
- Database connection lost

**Fix:**
- Check DB directly: `docker exec db psql -U user -d mydatabase -c "SELECT SUM(inStock) FROM pasta_db.batches"`
- Manually adjust thresholds in code if needed
- Monitor both aFresh, aDry, bFresh, bDry separately

### Issue: Scheduler failover not happening

**Diagnosis:**
```bash
docker logs scheduler | grep leadership
docker logs redis redis-cli keys "*"
```

**Likely causes:**
- Redis not running
- Active scheduler lease not expiring (still running)
- Shadow scheduler blocked on consumer poll

**Fix:**
- Verify Redis: `docker exec redis redis-cli ping`
- Kill active: `docker kill scheduler`
- Wait 5s, check shadow logs: `docker logs scheduler-shadow | tail -20`
- Should see "Acquired leadership"

### Issue: ChaosPanda not killing machines

**Diagnosis:**
```bash
docker logs chaospanda-experiment | grep KILLING
```

**Likely causes:**
- Docker socket permissions issue
- Max concurrent machines reached (`--max-cutting-machines`)
- No available machines to kill

**Fix:**
```bash
# Check socket permissions
ls -la /var/run/docker.sock

# If needed, adjust permissions
sudo chmod 666 /var/run/docker.sock

# Verify ChaosPanda sees machines
docker exec chaospanda-experiment python -c "
from docker_manager import DockerManager
dm = DockerManager('unix:///var/run/docker.sock')
print(dm.get_cutting_machines())
"

# Restart with higher max
docker kill chaospanda-experiment
./run_experiment.sh  # Re-run with adjusted parameters
```

---

## Advanced Configurations

### Adjusting Storage Thresholds

Edit `dbInterface/src/main/java/com/pasta/dbinterface/storage/StorageMonitor.java`:
```java
private static final double LOW_THRESHOLD = 20.0;   // Change to 10.0 for stricter
private static final double HIGH_THRESHOLD = 80.0;  // Change to 90.0 for looser
```

Rebuild: `docker-compose build db-interface && docker-compose up -d db-interface`

### Adjusting Scheduler Health Check Interval

Edit `scheduler/src/main/java/com/pasta/scheduler/machine/MachineManager.java`:
```java
private static final int HEARTBEAT_TIMEOUT_SECONDS = 10;      // Time without heartbeat to mark unhealthy
private static final int HEALTH_CHECK_INTERVAL_SECONDS = 5;   // How often to check
```

### Adjusting Redis Lease Duration

Edit `scheduler/src/main/java/com/pasta/scheduler/redis/RedisManager.java`:
```java
private static final int LEASE_DURATION_SECONDS = 5;  // Active scheduler lease timeout
```

Also update renewal interval in `Scheduler.java`:
```java
Thread.sleep(3000);  // Renew every 3s (should be < LEASE_DURATION_SECONDS)
```

### Adjusting Batch Target Stock

Edit `simulationEngine/batch_manager.py`:
```python
self.total_stock_target = 200  # Change to desired target
```

### Running with Different Chaos Parameters

```bash
# Kill 2 machines concurrently, with scheduler failover testing
docker rm -f chaospanda-experiment
docker run -d \
    --name chaospanda-experiment \
    --network dockerproject_mynetwork \
    -v /var/run/docker.sock:/var/run/docker.sock \
    --group-add 0 \
    -e PYTHONUNBUFFERED=1 \
    chaospanda:latest \
    python main.py \
    --max-cutting-machines 2 \
    --max-schedulers 1 \
    --kafka-bootstrap kafka:29092 \
    --redis-host redis \
    --redis-port 6379 \
    --test-name "scheduler-failover-test"
```

---

## Architecture Diagrams (ASCII)

### System Overview
```
┌─────────────────────────────────────────────────────────────────────┐
│                         PASTA PRODUCTION SYSTEM                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                           │
│  │ Machine0 │  │ Machine1 │  │ Machine2 │  ──MQTT──┐                │
│  └──────────┘  └──────────┘  └──────────┘          │                │
│   (Python)      (Python)      (Python)             │                │
│   Heartbeats every 5s                              │                │
│                                         ┌──────────▼─────────┐      │
│                                         │ MQTT-Kafka Bridge  │      │
│                                         │  (Python)          │      │
│                                         └──────────┬─────────┘      │
│                                                    │                │
│  ┌─────────────────────────────────────────────────▼──────────┐     │
│  │                    KAFKA (Topics)                          │     │
│  │  heartbeats │ productionPlan │ storageAlerts │storageLevels│     │
│  └──┬──────────┴────────────────┬──────────────┴──────────────┘     │
│     │                           │                                   │
│  ┌──▼──┐  ┌───────────┐ ┌──────▼───┐  ┌─────────────┐               │
│  │Sched│  │DbInterface│ │SortingSub│  │BatchManager │               │
│  │uler │  │ (Java)    │ │system    │  │ (Python)    │               │
│  │(Java)  │           │ │(Java)    │  │             │               │
│  └──┬──┘  └──┬────────┘ └─────┬────┘  └────┬────────┘               │
│     │        │                │            │                        │
│  ┌──▼────────▼────────────────▼────────────▼──┐                     │
│  │                REDIS (State)               │                     │
│  │  active_scheduler │ machines │ freshAmount │                     │
│  └────────────────────────────────────────────┘                     │
│                                                                     │
│  ┌────────────────────────────────────────────┐                     │
│  │         PostgreSQL (Batches DB)            │                     │
│  │  blade_type | isFresh | productionDate | inStock                 │
│  └────────────────────────────────────────────┘                     │
│                                                                     │
│  ┌────────────────────────────────────────────┐                     │
│  │     ChaosPanda (Chaos Testing)             │                     │
│  │  Kills/restarts machines & schedulers      │                     │
│  └────────────────────────────────────────────┘                     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Message Flow: Machine Discovery
```
Machine0          Mosquitto        Bridge           Kafka       Scheduler
   │                 │                │              │              │
   ├─heartbeat───────┤                │              │              │
   │   (no blade)    ├──heartbeat───┐ │              │              │
   │                 │              │ │              │              │
   │                 │              └─┼─heartbeat────┼──────────────┤
   │                 │                │              │    (discovers)
   │                 │                │              │              │
   │                 │                │              │     [12s wait]
   │                 │                │              │              │
   │◄─────AssignBlade─────────────────┼──AssignBlade─┼──────────────┤
   │  (via subtopic) │                │              │              │
   │                 │                │              │              │
   ├─heartbeat───────┤                │              │              │
   │ (with blade)    ├──heartbeat────┐│              │              │
   │                 │               ││              │              │
   │                 │               └┼─heartbeat────┼──────────────┤
   │                 │                │              │   (confirms)
```

### State Transitions: CuttingMachine
```
      ┌──────────────────────┐
      │   INITIALIZING       │
      │  (startup, 0s)       │
      └──────────┬───────────┘
                 │
                 ▼
      ┌──────────────────────┐
      │WAITING_FOR_ASSIGNMENT│
      │(heartbeats sent,     │
      │ no bladeType)        │
      └──────────┬───────────┘
                 │ [AssignBlade received]
                 ▼
      ┌──────────────────────┐
      │      WORKING         │
      │(heartbeats with      │
      │ bladeType, producing)│
      └──────────┬───────────┘
                 │ [killMachine received]
                 ▼
      ┌──────────────────────┐
      │     RECOVERY         │
      │(paused, timeout set) │
      └──────────┬───────────┘
                 │ [timeout expires]
                 ▼
      ┌──────────────────────┐
      │WAITING_FOR_ASSIGNMENT│
      │(restart from idle)   │
      └──────────────────────┘
```

### Scheduler Failover: Redis Leadership
```
Active Scheduler                    Shadow Scheduler             Redis
      │                                    │                        │
      ├─── SET active_scheduler primary ──┤────────────────────────┤
      │           (NX, EX 5s)                                       │
      │                                                     ✓ STORED
      │                                                              │
      ├─ renew every 3s ────────────────────────────────────────────┤
      │                                                              │
      │ [5s elapses, active dies]                                  │
      │                                                              │
      │                                ├── SET active_scheduler primary
      │                                └────────────────────────────┤
      │                                                     ✓ SUCCESS (NX worked)
      │                                                              │
      │                                ├─ loadStateFromRedis ──────┤
      │                                │   (machines, freshAmount) ├──
      │                                │                   LOADED
      │                                ├─ Resume operations
      │                                │ (no duplicate commands)
```

---

## Performance Characteristics

| Operation | Latency | Throughput | Notes |
|-----------|---------|-----------|-------|
| Heartbeat propagation | ~100ms | 0.2 HZ (3 machines × 5s) | MQTT→Kafka bridge delay |
| Machine discovery | 12-17s | N/A | 12s discovery phase + 1 Kafka poll |
| Blade assignment | ~200ms | Same as heartbeat | Scheduler→Kafka→MQTT→Machine |
| Storage alert response | ~10s | 1 per 10s | DbInterface poll interval |
| Scheduler failover | ~6s | N/A | 5s lease + 1s overhead |
| Batch creation | ~50ms | 0.2 per 5s | Per heartbeat (3 machines) |
| Stock rebalancing | ~100ms | On demand | Runs after each batch creation |

---

## Known Limitations

1. **Single Kafka broker**: No HA for message bus (single point of failure)
   - **Mitigation**: Add Kafka brokers + increase replication factor in docker-compose.yml
   
2. **MQTT broker not replicated**: Mosquitto is single instance
   - **Mitigation**: Use cloud MQTT service or setup Mosquitto clustering
   
3. **PostgreSQL single instance**: No replication
   - **Mitigation**: Add read replicas, use managed DB service (RDS, Cloud SQL)
   
4. **Stock rebalancing algorithm is random**: May not be optimal
   - **Mitigation**: Implement smarter algorithm (e.g., round-robin, weighted)
   
5. **No message ordering guarantee**: Kafka partitions enable parallelism but lose ordering
   - **Mitigation**: Use single partition per topic or add ordering in application
   
6. **Redis not persistent**: Data lost on restart
   - **Mitigation**: Enable RDB/AOF persistence in redis.conf
   
7. **No authentication/authorization**: All services can communicate
   - **Mitigation**: Add Kafka SSL/SASL, MQTT username/password, Redis ACLs

---

## Future Enhancements

1. **Dashboard**: React frontend to visualize real-time stock, machine status, alerts
2. **Metrics**: Prometheus + Grafana for performance monitoring
3. **Tracing**: Jaeger integration for distributed tracing
4. **Scalability**: Kubernetes deployment (Helm charts)
5. **Testing**: JUnit/Pytest comprehensive test suite
6. **CI/CD**: GitHub Actions pipeline for automated testing and deployment
7. **Multi-region**: Cross-region scheduler instances with failover
8. **Machine Learning**: Predictive production planning based on historical data

---

## References

- **Kafka Messages**: See `kafka_messages_summary.md` for complete protocol specification
- **Run Script**: `run_experiment.sh` for deployment automation
- **Database Schema**: `init.sql` for PostgreSQL initialization
- **Docker Compose**: `docker-compose.yml` for service orchestration