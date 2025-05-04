import redis.asyncio as redis
import json
import logging
from . import config
from .models import OrderStatusUpdateEvent

logger = logging.getLogger(__name__)

redis_pool = None

async def get_redis_pool():
    global redis_pool
    if redis_pool is None:
        logger.info(f"Creating Redis connection pool for {config.REDIS_HOST}:{config.REDIS_PORT}")
        redis_pool = redis.ConnectionPool(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            decode_responses=True # Decode responses to strings
        )
    return redis.Redis(connection_pool=redis_pool)

async def set_order_status(order_id: str, status: str, details: dict | None = None):
    """Stores the current status of an order in Redis with a TTL."""
    try:
        r = await get_redis_pool()
        key = f"order_status:{order_id}"
        value = json.dumps({"status": status, "details": details or {}})
        await r.setex(key, config.REDIS_ORDER_STATUS_TTL_SECONDS, value)
        logger.debug(f"Set status for order {order_id} to {status} in Redis")
    except Exception as e:
        logger.error(f"Failed to set status for order {order_id} in Redis: {e}")
        # Decide on error handling - raise? retry?

async def get_order_status(order_id: str) -> dict | None:
    """Retrieves the current status of an order from Redis."""
    try:
        r = await get_redis_pool()
        key = f"order_status:{order_id}"
        value = await r.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.error(f"Failed to get status for order {order_id} from Redis: {e}")
        return None # Or raise