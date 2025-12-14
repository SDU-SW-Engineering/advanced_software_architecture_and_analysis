import logging
import time
from sqlalchemy import create_engine, text

# Logger setup
LOGGER = logging.getLogger(__name__)


class DatabaseConnection:
    """Manages PostgreSQL database connection with retry logic."""
    
    def __init__(self, db_url='postgresql://user:password@db:5432/mydatabase', max_retries=None):
        """
        Initialize database connection.
        
        Args:
            db_url (str): PostgreSQL connection string
            max_retries (int): Maximum retry attempts. None = infinite retries
        """
        self.db_url = db_url
        self.max_retries = max_retries
        self.engine = None
        self._connect()
    
    def _connect(self):
        """Establish connection with retry logic."""
        retries = 0
        while True:
            try:
                self.engine = create_engine(self.db_url)
                # Test the connection
                with self.engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
                LOGGER.info("Connected to database successfully")
                return
            except Exception as e:
                retries += 1
                if self.max_retries and retries >= self.max_retries:
                    LOGGER.error(f"Failed to connect after {self.max_retries} attempts: {str(e)}")
                    raise
                LOGGER.warning(f"Retrying connection to database due to: {str(e)}")
                time.sleep(5)
    
    def get_connection(self):
        """Get a database connection."""
        if self.engine is None:
            raise RuntimeError("Database engine not initialized")
        return self.engine.connect()
    
    def execute_query(self, query, params=None):
        """
        Execute a query and return results.
        
        Args:
            query (str or TextClause): SQL query as string or text object
            params (dict): Query parameters
            
        Returns:
            Result object from SQLAlchemy
        """
        try:
            with self.get_connection() as connection:
                with connection.begin():
                    # Convert to text() if it's a string
                    if isinstance(query, str):
                        query = text(query)
                    result = connection.execute(query, params or {})
                    return result
        except Exception as e:
            LOGGER.error(f"Query execution error: {str(e)}")
            raise
    
    def execute_insert(self, query, params=None):
        """
        Execute an insert query.
        
        Args:
            query (str or TextClause): SQL insert query as string or text object
            params (dict): Query parameters
        """
        try:
            with self.get_connection() as connection:
                with connection.begin():
                    if isinstance(query, str):
                        query = text(query)
                    connection.execute(query, params or {})
        except Exception as e:
            LOGGER.error(f"Insert error: {str(e)}")
            raise
    
    def execute_update(self, query, params=None):
        """
        Execute an update query.
        
        Args:
            query (str or TextClause): SQL update query as string or text object
            params (dict): Query parameters
        """
        try:
            with self.get_connection() as connection:
                with connection.begin():
                    if isinstance(query, str):
                        query = text(query)
                    connection.execute(query, params or {})
                    # LOGGER.info(f"Update executed with params: {params}")
        except Exception as e:
            LOGGER.error(f"Update error: {str(e)}")
            raise
    
    def close(self):
        """Close the database connection."""
        if self.engine:
            self.engine.dispose()
            LOGGER.info("Database connection closed")