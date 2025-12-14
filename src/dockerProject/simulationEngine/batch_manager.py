import logging
import random
import time
import json
import threading
from datetime import datetime
from faker import Faker
from kafka import KafkaConsumer

# Logger setup
LOGGER = logging.getLogger(__name__)

# Initialize Faker
fake = Faker('en_US')


class BatchManager:
    """Manages batch insertion and reduction operations based on heartbeats and freshAmount."""
    
    def __init__(self, db_connection, kafka_producer, kafka_bootstrap_servers):
        """
        Initialize batch manager.
        
        Args:
            db_connection (DatabaseConnection): Database connection instance
            kafka_producer (KafkaProducerManager): Kafka producer instance
            kafka_bootstrap_servers (str): Kafka bootstrap servers
        """
        self.db = db_connection
        self.kafka = kafka_producer
        self.kafka_bootstrap_servers = kafka_bootstrap_servers
        self.freshAmount = 4  # Default fresh amount
        self.lock = threading.Lock()
        self.total_stock_target = 200
        
        LOGGER.info("BatchManager initialized with freshAmount=4")
    
    def start_production_plan_consumer(self):
        """Start consuming freshAmount updates from productionPlan topic."""
        consumer_thread = threading.Thread(
            target=self._consume_production_plan,
            daemon=True,
            name='ProductionPlanConsumer'
        )
        consumer_thread.start()
    
    def start_heartbeat_consumer(self):
        """Start consuming heartbeats and creating batches."""
        consumer_thread = threading.Thread(
            target=self._consume_heartbeats,
            daemon=True,
            name='HeartbeatConsumer'
        )
        consumer_thread.start()
    
    def _consume_production_plan(self):
        """Consume ChangeFreshAmount messages from productionPlan topic."""
        max_retries = 10
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                consumer = KafkaConsumer(
                    'productionPlan',
                    bootstrap_servers=self.kafka_bootstrap_servers,
                    auto_offset_reset='latest',
                    enable_auto_commit=True,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
                    group_id='batch-manager-production-plan'
                )
                
                LOGGER.info("Production plan consumer started")
                retry_count = 0
                
                for message in consumer:
                    if message.value:
                        try:
                            title = message.value.get("title")
                            if title == "ChangeFreshAmount":
                                fresh_amount = message.value.get("freshAmount")
                                if fresh_amount is not None:
                                    with self.lock:
                                        self.freshAmount = fresh_amount
                                    LOGGER.info(f"Updated freshAmount to {fresh_amount}")
                        except Exception as e:
                            LOGGER.error(f"Error handling production plan message: {str(e)}")
            
            except Exception as e:
                retry_count += 1
                LOGGER.warning(f"Error consuming productionPlan (attempt {retry_count}/{max_retries}): {str(e)}")
                if retry_count < max_retries:
                    time.sleep(2)
                else:
                    LOGGER.error(f"Failed to connect to productionPlan after {max_retries} attempts")
                    break
    
    def _consume_heartbeats(self):
        """Consume heartbeat messages and create batches based on them."""
        max_retries = 10
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                consumer = KafkaConsumer(
                    'heartbeats',
                    bootstrap_servers=self.kafka_bootstrap_servers,
                    auto_offset_reset='latest',
                    enable_auto_commit=True,
                    value_deserializer=lambda m: json.loads(m.decode('utf-8')) if m else None,
                    group_id='batch-manager-heartbeats'
                )
                
                LOGGER.info("Heartbeat consumer started")
                retry_count = 0
                
                for message in consumer:
                    if message.value:
                        try:
                            title = message.value.get("title")
                            if title == "heartbeat" and message.value.get("bladeType"):
                                blade_type = message.value.get("bladeType")
                                machine_id = message.value.get("machineId")
                                
                                # Create batches for this heartbeat
                                self.create_batches_for_heartbeat(blade_type, machine_id)
                                
                                # Balance stock levels
                                self.balance_stock_levels()
                        except Exception as e:
                            LOGGER.error(f"Error handling heartbeat: {str(e)}")
            
            except Exception as e:
                retry_count += 1
                LOGGER.warning(f"Error consuming heartbeats (attempt {retry_count}/{max_retries}): {str(e)}")
                if retry_count < max_retries:
                    time.sleep(2)
                else:
                    LOGGER.error(f"Failed to connect to heartbeats after {max_retries} attempts")
                    break
    
    def create_batches_for_heartbeat(self, blade_type, machine_id):
        """
        Create two batches (fresh and dry) based on a heartbeat message.
        
        Args:
            blade_type (str): Blade type ('A' or 'B')
            machine_id (int): ID of the machine sending the heartbeat
        """
        with self.lock:
            fresh_amount = self.freshAmount
        
        production_date = datetime.now().isoformat()
        
        # Create fresh batch
        fresh_batch_query = """
            INSERT INTO pasta_db.batches (blade_type, isFresh, productionDate, inStock)
            VALUES (:blade_type, :isFresh, :productionDate, :inStock)
        """
        
        try:
            self.db.execute_insert(fresh_batch_query, {
                'blade_type': blade_type,
                'isFresh': True,
                'productionDate': production_date,
                'inStock': fresh_amount
            })
            LOGGER.debug(f"Created fresh batch: blade={blade_type}, inStock={fresh_amount}")
        except Exception as e:
            LOGGER.error(f"Failed to insert fresh batch: {str(e)}")
            return
        
        # Create dry batch
        dry_amount = 10 - fresh_amount
        try:
            self.db.execute_insert(fresh_batch_query, {
                'blade_type': blade_type,
                'isFresh': False,
                'productionDate': production_date,
                'inStock': dry_amount
            })
            LOGGER.debug(f"Created dry batch: blade={blade_type}, inStock={dry_amount}")
            LOGGER.info(f"Created batches from heartbeat (machine {machine_id}, blade {blade_type}): fresh={fresh_amount}, dry={dry_amount}")
        except Exception as e:
            LOGGER.error(f"Failed to insert dry batch: {str(e)}")
    
    def balance_stock_levels(self):
        """
        Balance stock levels by reducing batches until total stock equals target (200).
        Randomly distributes the reduction across all batches.
        """
        current_total = self.get_total_stock()
        
        if current_total <= self.total_stock_target:
            return
        
        reduction_needed = current_total - self.total_stock_target
        self.reduce_all_batches(reduction_needed)
        
        # Send storage level update to dashboard
        self.send_storage_levels_to_dashboard()
    
    def get_total_stock(self):
        """
        Get the total stock across all batches.
        
        Returns:
            int: Total stock amount
        """
        try:
            result = self.db.execute_query("SELECT SUM(inStock) FROM pasta_db.batches")
            row = result.fetchone()
            total = row[0] if row and row[0] is not None else 0
            return total
        except Exception as e:
            LOGGER.error(f"Failed to get total stock: {str(e)}")
            return 0
    
    def get_all_batches(self):
        """
        Retrieve all batches with stock > 0.
        
        Returns:
            list: List of batch rows from database
        """
        try:
            result = self.db.execute_query("SELECT * FROM pasta_db.batches WHERE inStock > 0")
            return result.fetchall()
        except Exception as e:
            LOGGER.error(f"Failed to fetch batches: {str(e)}")
            return []
    
    def reduce_batch_stock(self, batch_id, amount):
        """
        Reduce stock for a specific batch.
        
        Args:
            batch_id (int): Batch ID to reduce
            amount (int): Amount to reduce by
        """
        update_query = """
            UPDATE pasta_db.batches
            SET inStock = GREATEST(0, inStock - :amount)
            WHERE id = :batch_id
        """
        
        try:
            self.db.execute_update(update_query, {
                'amount': amount,
                'batch_id': batch_id
            })
        except Exception as e:
            LOGGER.error(f"Failed to reduce batch stock: {str(e)}")
    
    def reduce_all_batches(self, total_reduction):
        """
        Randomly distribute stock reduction across all batches to reach target stock level.
        
        Args:
            total_reduction (int): Total amount to reduce across all batches
        """
        batches = self.get_all_batches()
        
        if not batches:
            return
        
        remaining_reduction = total_reduction
        
        for batch in batches:
            if remaining_reduction <= 0:
                break
            
            batch_id = batch[0]  # First column is ID
            in_stock = batch[4]  # Fifth column is inStock
            
            # Randomly determine reduction amount, but not more than remaining or in_stock
            max_reduction = min(remaining_reduction, in_stock)
            reduction_amount = fake.random_int(min=0, max=max_reduction)
            
            if reduction_amount > 0:
                self.reduce_batch_stock(batch_id, reduction_amount)
                remaining_reduction -= reduction_amount
        
        LOGGER.debug(f"Reduced stock by {total_reduction - remaining_reduction} units to balance levels")
    
    def send_storage_levels_to_dashboard(self):
        """
        Calculate current storage levels and send to storageLevels topic.
        """
        try:
            # Query totals for each combination
            result_a_fresh = self.db.execute_query(
                "SELECT SUM(inStock) FROM pasta_db.batches WHERE blade_type='A' AND isFresh=TRUE"
            )
            a_fresh = result_a_fresh.fetchone()[0] or 0
            
            result_a_dry = self.db.execute_query(
                "SELECT SUM(inStock) FROM pasta_db.batches WHERE blade_type='A' AND isFresh=FALSE"
            )
            a_dry = result_a_dry.fetchone()[0] or 0
            
            result_b_fresh = self.db.execute_query(
                "SELECT SUM(inStock) FROM pasta_db.batches WHERE blade_type='B' AND isFresh=TRUE"
            )
            b_fresh = result_b_fresh.fetchone()[0] or 0
            
            result_b_dry = self.db.execute_query(
                "SELECT SUM(inStock) FROM pasta_db.batches WHERE blade_type='B' AND isFresh=FALSE"
            )
            b_dry = result_b_dry.fetchone()[0] or 0
            
            # Calculate percentages (max capacity per type is 100)
            max_capacity = 100
            a_fresh_pct = (a_fresh / max_capacity) * 100
            a_dry_pct = (a_dry / max_capacity) * 100
            b_fresh_pct = (b_fresh / max_capacity) * 100
            b_dry_pct = (b_dry / max_capacity) * 100
            
            # Create message
            message = {
                "title": "StorageLevels",
                "aFresh": round(a_fresh_pct, 2),
                "aDry": round(a_dry_pct, 2),
                "bFresh": round(b_fresh_pct, 2),
                "bDry": round(b_dry_pct, 2)
            }
            
            self.kafka.send_message('storageLevels', json.dumps(message))
            LOGGER.debug(f"Sent storage levels: aFresh={a_fresh_pct:.2f}%, aDry={a_dry_pct:.2f}%, bFresh={b_fresh_pct:.2f}%, bDry={b_dry_pct:.2f}%")
        except Exception as e:
            LOGGER.error(f"Error sending storage levels to dashboard: {str(e)}")