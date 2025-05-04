from fastapi import FastAPI, HTTPException, Depends
import logging
import asyncio
import json
import time
from contextlib import asynccontextmanager
from aiokafka import AIOKafkaConsumer
from pydantic import ValidationError

from . import config, crud, kafka_client, models

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Global variables ---
kafka_consumer_task = None


# --- Kafka Consumer Logic ---
async def process_validated_order(order_data: dict):
    """Processes a single validated order message."""
    try:
        order = models.ValidatedOrderEvent(**order_data)
        order_id = order.order_id
        logger.info(f"Received validated order: {order_id}")

        # 1. Simulate Inventory Check (Hardcoded)
        # In a real system, this might involve calling another service or checking availability
        await asyncio.sleep(config.SIMULATE_PROCESSING_DELAY_SECONDS) # Simulate work
        inventory_ok = config.SIMULATE_INVENTORY_CHECK_SUCCESS
        if not inventory_ok:
            logger.warning(f"Inventory check failed for order {order_id}. Setting status to FAILED.")
            status = "FAILED"
            details = {"reason": "Inventory unavailable"}
            # Update Redis
            await crud.set_order_status(order_id, status, details)
            # Publish Status Update Event
            status_event = models.OrderStatusUpdateEvent(
                order_id=order_id, status=status, timestamp=time.time(), details=details
            )
            await kafka_client.send_message(config.ORDER_STATUS_UPDATE_TOPIC, status_event.model_dump())
            # Publish DB Write Event
            db_event = models.DbWriteOrderStatusEvent(order_id=order_id, status=status, timestamp=time.time())
            await kafka_client.send_message(config.DB_WRITE_ORDER_STATUS_TOPIC, db_event.model_dump())
            return # Stop processing this order

        # 2. Update Status to PROCESSING
        logger.info(f"Processing order: {order_id}")
        status = "PROCESSING"
        await crud.set_order_status(order_id, status)
        status_event = models.OrderStatusUpdateEvent(
            order_id=order_id, status=status, timestamp=time.time()
        )
        await kafka_client.send_message(config.ORDER_STATUS_UPDATE_TOPIC, status_event.model_dump())
        db_event = models.DbWriteOrderStatusEvent(order_id=order_id, status=status, timestamp=time.time())
        await kafka_client.send_message(config.DB_WRITE_ORDER_STATUS_TOPIC, db_event.model_dump())

        # 3. Simulate further processing (e.g., payment confirmation, restaurant acceptance)
        # In a real system, this would likely involve waiting for other events
        await asyncio.sleep(config.SIMULATE_PROCESSING_DELAY_SECONDS * 2) # Simulate more work/waiting

        # 4. Update Status to CONFIRMED (Example)
        logger.info(f"Confirming order: {order_id}")
        status = "CONFIRMED"
        await crud.set_order_status(order_id, status)
        status_event = models.OrderStatusUpdateEvent(
            order_id=order_id, status=status, timestamp=time.time()
        )
        await kafka_client.send_message(config.ORDER_STATUS_UPDATE_TOPIC, status_event.model_dump())
        db_event = models.DbWriteOrderStatusEvent(order_id=order_id, status=status, timestamp=time.time())
        await kafka_client.send_message(config.DB_WRITE_ORDER_STATUS_TOPIC, db_event.model_dump())

        logger.info(f"Finished processing order {order_id}")

    except ValidationError as e:
        logger.error(f"Invalid order message format: {order_data}. Error: {e}")
    except Exception as e:
        logger.exception(f"Error processing order {order_data.get('order_id', 'N/A')}: {e}")
        # Consider error handling: retry? move to dead-letter queue?

async def consume_orders():
    consumer = AIOKafkaConsumer(
        config.ORDER_VALIDATED_TOPIC,
        bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
        group_id=config.KAFKA_CONSUMER_GROUP,
        value_deserializer=lambda v: json.loads(v.decode('utf-8')),
        auto_offset_reset='earliest', # Start reading from the beginning if no offset found
        enable_auto_commit=True, # Auto commit offsets (can be False for manual control)
        # Use max_poll_records=1 for sequential processing if needed, but lowers throughput
    )
    await consumer.start()
    logger.info(f"Kafka consumer started for topic '{config.ORDER_VALIDATED_TOPIC}'")
    try:
        async for msg in consumer:
            logger.debug(f"Received raw message: {msg.value}")
            # Run processing in background to not block consumer loop?
            # For simplicity here, we await directly. Consider asyncio.create_task for concurrency.
            await process_validated_order(msg.value)
    except Exception as e:
         logger.exception(f"Kafka consumer error: {e}")
    finally:
        logger.info("Stopping Kafka consumer...")
        await consumer.stop()

# --- FastAPI Lifespan Events ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global kafka_consumer_task
    logger.info("Application startup...")
    # Initialize resources
    await crud.get_redis_pool() # Initialize pool
    await kafka_client.get_kafka_producer() # Initialize producer

    # Start Kafka consumer in background
    logger.info("Starting Kafka consumer task...")
    loop = asyncio.get_running_loop()
    kafka_consumer_task = loop.create_task(consume_orders())

    yield # Application runs here

    logger.info("Application shutdown...")
    # Stop background tasks
    if kafka_consumer_task:
        logger.info("Cancelling Kafka consumer task...")
        kafka_consumer_task.cancel()
        try:
            await kafka_consumer_task
        except asyncio.CancelledError:
            logger.info("Kafka consumer task cancelled.")
        except Exception as e:
            logger.error(f"Exception during Kafka consumer task shutdown: {e}")

    # Cleanup resources
    await kafka_client.stop_kafka_producer()
    # Redis pool cleanup isn't strictly necessary with redis-py's async pool management


# --- FastAPI App ---
app = FastAPI(
    title="Order Manager Service",
    description="Manages order status updates, consumes validated orders from Kafka, updates Redis, and publishes status events.",
    version="0.1.0",
    lifespan=lifespan
)

@app.get("/health", summary="Health Check", tags=["Monitoring"])
async def health_check():
    # Add checks for Kafka/Redis connectivity if needed
    return {"status": "ok"}

@app.get("/orders/{order_id}/status", summary="Get Order Status from Cache", tags=["Orders"], response_model=dict)
async def get_order_status_endpoint(order_id: str):
    """Retrieves the current status of an order from the Redis cache."""
    status_info = await crud.get_order_status(order_id)
    if status_info:
        return status_info
    else:
        raise HTTPException(status_code=404, detail=f"Status not found for order {order_id}")

# You could add more endpoints if needed, e.g., manually trigger processing (for testing)