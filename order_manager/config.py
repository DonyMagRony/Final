import os

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_CONSUMER_GROUP = os.getenv("KAFKA_CONSUMER_GROUP", "order_manager_group")

# Input topic for validated orders
ORDER_VALIDATED_TOPIC = os.getenv("ORDER_VALIDATED_TOPIC", "validated_orders")

# Output topic for status updates (for other services)
ORDER_STATUS_UPDATE_TOPIC = os.getenv("ORDER_STATUS_UPDATE_TOPIC", "order_status_updates")

# Output topic for signaling database writes
DB_WRITE_ORDER_STATUS_TOPIC = os.getenv("DB_WRITE_ORDER_STATUS_TOPIC", "db_write_order_status")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_ORDER_STATUS_TTL_SECONDS = int(os.getenv("REDIS_ORDER_STATUS_TTL_SECONDS", 3600)) # 1 hour

# --- Hardcoded values for simplification ---
# Simulate inventory check success
SIMULATE_INVENTORY_CHECK_SUCCESS = True
SIMULATE_PROCESSING_DELAY_SECONDS = 0.5 # Simulate work