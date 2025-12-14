"""
Redis inspection for checking scheduler state
"""

import logging
import redis

LOGGER = logging.getLogger(__name__)


class RedisInspector:
    """Inspects Redis for system state"""

    ACTIVE_SCHEDULER_KEY = "active_scheduler"

    def __init__(self, host, port):
        """
        Initialize Redis inspector.

        Args:
            host (str): Redis host
            port (int): Redis port
        """
        try:
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                decode_responses=True,
                socket_connect_timeout=5
            )
            self.redis_client.ping()
            LOGGER.info(f"✅ Connected to Redis at {host}:{port}")
        except Exception as e:
            LOGGER.error(f"Failed to connect to Redis: {str(e)}")
            raise RuntimeError("Could not connect to Redis")

    def is_scheduler_active(self, scheduler_name):
        """
        Determine if a scheduler is currently active (has the leadership lease).

        Args:
            scheduler_name (str): Scheduler container name

        Returns:
            bool: True if scheduler is active, False otherwise
        """
        try:
            active_scheduler = self.redis_client.get(self.ACTIVE_SCHEDULER_KEY)
            
            if not active_scheduler:
                LOGGER.warning("No active scheduler found in Redis")
                return False
            
            # Check if this scheduler is the active one
            # The active_scheduler value is the scheduler ID (e.g., "primary")
            # We assume only one active at a time, so if we find one, return True/False
            is_active = active_scheduler == "primary"
            
            LOGGER.debug(f"Scheduler {scheduler_name}: active={is_active} (leader={active_scheduler})")
            return is_active

        except Exception as e:
            LOGGER.error(f"Error checking scheduler status: {str(e)}")
            # If we can't determine, assume it's shadow
            return False

    def get_active_scheduler_id(self):
        """
        Get the current active scheduler ID.

        Returns:
            str: Active scheduler ID or None
        """
        try:
            return self.redis_client.get(self.ACTIVE_SCHEDULER_KEY)
        except Exception as e:
            LOGGER.error(f"Error getting active scheduler ID: {str(e)}")
            return None

    def get_system_state(self):
        """
        Get overall system state from Redis.

        Returns:
            dict: System state information
        """
        try:
            state = {
                "active_scheduler": self.redis_client.get(self.ACTIVE_SCHEDULER_KEY),
                "machines": self.redis_client.get("scheduler:machines"),
                "fresh_amount": self.redis_client.get("scheduler:freshAmount"),
            }
            return state
        except Exception as e:
            LOGGER.error(f"Error getting system state: {str(e)}")
            return {}