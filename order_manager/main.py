from fastapi import FastAPI, HTTPException, Depends
import logging
import asyncio
import json
import time
from contextlib import asynccontextmanager
from aiokafka import AIOKafkaConsumer
from pydantic import ValidationError
import httpx
from . import config, crud, kafka_client, models # Ensure config is imported
from pydantic import ValidationError
import time
import logging #

from . import config, crud, kafka_client, models

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Global variables ---
kafka_consumer_task = None

async def process_validated_order(order_data: dict):
    """Processes a single validated order message."""
    order: models.ValidatedOrderEvent | None = None # Define order variable
    order_id = "N/A" # Default in case of early failure
    try:
        # Parse incoming message first
        order = models.ValidatedOrderEvent(**order_data)
        order_id = order.order_id
        logger.info(f"Received validated order: {order_id}")

        logger.info(f"Checking inventory for order {order_id} via Inventory Service...")
        inventory_check_payload = {
            "items": [{"item_id": item.item_id, "quantity": item.quantity} for item in order.items]
        }
        inventory_ok = False # Default to False
        inventory_response_details = "Inventory check not performed" # Default detail

        # Ensure there are items to check
        if not inventory_check_payload["items"]:
             logger.warning(f"Order {order_id} has no items to check inventory for. Failing order.")
             inventory_ok = False
             inventory_response_details = {"error": "Order contains no items"}
        else:
            try:
                # Use an async HTTP client with context manager
                async with httpx.AsyncClient(base_url=config.INVENTORY_SERVICE_URL, timeout=10.0) as client:
                    response = await client.post(
                        "/check_inventory", # Endpoint relative to base_url
                        json=inventory_check_payload
                    )
                    # Check for HTTP errors (4xx, 5xx)
                    response.raise_for_status()
                    # Process successful response
                    inventory_response_data = response.json()
                    inventory_ok = inventory_response_data.get("all_available", False) # Get the boolean result
                    inventory_response_details = inventory_response_data.get("details", []) # Get specific details
                    logger.info(f"Inventory check result for {order_id}: Available={inventory_ok}")

            except httpx.HTTPStatusError as e:
                # Error response from inventory service
                error_body = e.response.text
                logger.error(f"Inventory service returned status {e.response.status_code} for order {order_id}. Response: {error_body[:500]}") # Log truncated body
                inventory_ok = False
                inventory_response_details = {"error": f"Inventory service status error {e.response.status_code}", "details": error_body[:500]}
            except httpx.RequestError as e:
                # Network or connection error
                logger.error(f"Could not connect to inventory service ({e.request.url}) for order {order_id}: {e}")
                inventory_ok = False
                inventory_response_details = {"error": f"Inventory service connection error: {e}"}
            except Exception as e:
                # Catch any other unexpected errors during the check
                logger.exception(f"Unexpected error during inventory check for order {order_id}: {e}")
                inventory_ok = False
                inventory_response_details = {"error": f"Inventory check unexpected error: {e}"}

        # --- Handle Inventory Check Result ---
        # This block MUST come immediately after the try/except for the inventory check
        if not inventory_ok:
            logger.warning(f"Inventory check failed or unavailable for order {order_id}. Setting status to FAILED.")
            status = "FAILED"
            # Include details from the inventory check in the failure reason
            failure_details = {"reason": "Inventory unavailable or check failed", "inventory_response": inventory_response_details}
            await crud.set_order_status(order_id, status, failure_details)
            # Publish Status Update Event
            status_event = models.OrderStatusUpdateEvent(
                order_id=order_id, status=status, timestamp=time.time(), details=failure_details
            )
            await kafka_client.send_message(config.ORDER_STATUS_UPDATE_TOPIC, status_event.model_dump())
            # Publish DB Write Event
            db_event = models.DbWriteOrderStatusEvent(order_id=order_id, status=status, timestamp=time.time())
            await kafka_client.send_message(config.DB_WRITE_ORDER_STATUS_TOPIC, db_event.model_dump())
            return # Stop processing this order

        # --- Inventory Available - Continue Processing ---
        # If the code reaches here, inventory_ok must have been True
        logger.info(f"Inventory confirmed for order {order_id}. Proceeding...")

        # --- 2. Price Calculation ---
        logger.info(f"Calculating price for order {order_id} via Pricing Service...")
        # Prepare payload using data from the validated order event
        pricing_payload = {
            "order_id": order.order_id,
            "items": [item.model_dump() for item in order.items] # Pass item details including price
        }
        price_calculated_successfully = False
        pricing_response_info = "Pricing check not performed" # Default detail

        try:
            async with httpx.AsyncClient(base_url=config.PRICING_SERVICE_URL, timeout=10.0) as client:
                response = await client.post("/calculate_price", json=pricing_payload)
                response.raise_for_status() # Raise exception for 4xx/5xx status codes
                pricing_data = response.json()

                # Store calculated prices back onto the order object
                order.calculated_base_total = pricing_data.get("base_total")
                order.calculated_discount = pricing_data.get("discount_applied")
                order.calculated_fees = pricing_data.get("fees_applied")
                order.calculated_final_total = pricing_data.get("final_total")

                price_calculated_successfully = True
                pricing_response_info = pricing_data # Store full response for logging/debugging
                logger.info(f"Price calculation successful for {order_id}: Final Price={order.calculated_final_total:.2f}")

        except httpx.HTTPStatusError as e:
            error_body = e.response.text
            logger.error(f"Pricing service returned status {e.response.status_code} for order {order_id}. Response: {error_body[:500]}")
            pricing_response_info = {"error": f"Pricing service status error {e.response.status_code}", "details": error_body[:500]}
        except httpx.RequestError as e:
            logger.error(f"Could not connect to pricing service ({e.request.url}) for order {order_id}: {e}")
            pricing_response_info = {"error": f"Pricing service connection error: {e}"}
        except Exception as e:
            logger.exception(f"Unexpected error during price calculation for order {order_id}")
            pricing_response_info = {"error": f"Price calculation unexpected error: {e}"}

        # --- Handle Price Calculation Result ---
        if not price_calculated_successfully:
            logger.error(f"Price calculation failed for order {order_id}. Failing order.")
            status = "FAILED"
            failure_details = {"reason": "Price calculation failed", "pricing_response": pricing_response_info}
            await crud.set_order_status(order_id, status, failure_details)
            # Publish failure events to Kafka
            status_event = models.OrderStatusUpdateEvent(order_id=order_id, status=status, timestamp=time.time(), details=failure_details)
            await kafka_client.send_message(config.ORDER_STATUS_UPDATE_TOPIC, status_event.model_dump())
            db_event = models.DbWriteOrderStatusEvent(order_id=order_id, status=status, timestamp=time.time())
            await kafka_client.send_message(config.DB_WRITE_ORDER_STATUS_TOPIC, db_event.model_dump())
            return # Stop processing

        # --- Price Calculated Successfully - Continue Processing ---
        logger.info(f"Price confirmed for order {order_id}. Proceeding...")

        # 3. Update Status to PROCESSING (Include calculated price)
        processing_status = "PROCESSING"
        processing_details = {
            "final_price": order.calculated_final_total,
            "base_total": order.calculated_base_total,
            "discount": order.calculated_discount,
            "fees": order.calculated_fees
        }
        await crud.set_order_status(order_id, processing_status, processing_details)
        logger.info(f"Processing order: {order_id} with final price {order.calculated_final_total:.2f}")

        # Publish PROCESSING events to Kafka
        processing_status_event = models.OrderStatusUpdateEvent(order_id=order_id, status=processing_status, timestamp=time.time(), details=processing_details)
        await kafka_client.send_message(config.ORDER_STATUS_UPDATE_TOPIC, processing_status_event.model_dump())
        processing_db_event = models.DbWriteOrderStatusEvent(order_id=order_id, status=processing_status, timestamp=time.time()) # May want price in DB event too
        await kafka_client.send_message(config.DB_WRITE_ORDER_STATUS_TOPIC, processing_db_event.model_dump())


        # 4. Simulate further processing (e.g., payment confirmation)
        await asyncio.sleep(config.SIMULATE_PROCESSING_DELAY_SECONDS * 2) # Simulate work

        # 5. Update Status to CONFIRMED
        # IMPORTANT: In a real system, payment confirmation would happen here BEFORE confirming.
        # Stock decrement would typically happen AFTER payment confirmation.
        confirmed_status = "CONFIRMED"
        await crud.set_order_status(order_id, confirmed_status, processing_details) # Keep price details in status
        logger.info(f"Confirming order: {order_id}")

        # Publish CONFIRMED events to Kafka
        confirmed_status_event = models.OrderStatusUpdateEvent(order_id=order_id, status=confirmed_status, timestamp=time.time(), details=processing_details)
        await kafka_client.send_message(config.ORDER_STATUS_UPDATE_TOPIC, confirmed_status_event.model_dump())
        confirmed_db_event = models.DbWriteOrderStatusEvent(order_id=order_id, status=confirmed_status, timestamp=time.time())
        await kafka_client.send_message(config.DB_WRITE_ORDER_STATUS_TOPIC, confirmed_db_event.model_dump())

        logger.info(f"Finished processing order {order_id}")

    # --- Exception Handling for the whole process ---
    except ValidationError as e:
        logger.error(f"Invalid order message format received: {order_data}. Error: {e}")
        # Handle: Log, potentially move to Dead Letter Queue (DLQ)
    except Exception as e:
        order_id_for_error = order.order_id if order else order_data.get('order_id', 'N/A')
        logger.exception(f"CRITICAL: Unhandled error processing order {order_id_for_error}: {e}")
        # Handle: Log, potentially mark order as SYSTEM_ERROR in Redis/DB via Kafka event, DLQ?
        if order_id != "N/A": # If we parsed the order ID before crashing
             try:
                  status = "SYSTEM_ERROR"
                  error_details = {"reason": "Unhandled exception during processing", "error": str(e)}
                  await crud.set_order_status(order_id, status, error_details)
                  status_event = models.OrderStatusUpdateEvent(order_id=order_id, status=status, timestamp=time.time(), details=error_details)
                  await kafka_client.send_message(config.ORDER_STATUS_UPDATE_TOPIC, status_event.model_dump())
                  db_event = models.DbWriteOrderStatusEvent(order_id=order_id, status=status, timestamp=time.time())
                  await kafka_client.send_message(config.DB_WRITE_ORDER_STATUS_TOPIC, db_event.model_dump())
             except Exception as inner_e:
                  logger.error(f"Failed to update status to SYSTEM_ERROR for order {order_id_for_error} after outer exception: {inner_e}")


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