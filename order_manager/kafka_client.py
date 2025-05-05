from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import json
import logging
import asyncio
from . import config

logger = logging.getLogger(__name__)

producer = None

async def get_kafka_producer():
    global producer
    if producer is None:
        logger.info(f"Initializing Kafka producer: {config.KAFKA_BOOTSTRAP_SERVERS}")
        producer = AIOKafkaProducer(
            bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            acks='all'
        )
        await producer.start()
    return producer

async def stop_kafka_producer():
    global producer
    if producer:
        logger.info("Stopping Kafka producer...")
        await producer.stop()
        producer = None

async def send_message(topic: str, message: dict):
    """Sends a message to a specific Kafka topic."""
    try:
        p = await get_kafka_producer()
        await p.send_and_wait(topic, value=message)
        logger.debug(f"Message sent to Kafka topic '{topic}': {message}")
    except Exception as e:
        logger.error(f"Failed to send message to Kafka topic '{topic}': {e}")
