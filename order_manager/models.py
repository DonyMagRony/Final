from pydantic import BaseModel, Field
from typing import List, Dict, Any
import uuid

class OrderItem(BaseModel):
    item_id: str
    quantity: int
    price: float # Price per item at the time of order

class ValidatedOrderEvent(BaseModel):
    order_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    items: List[OrderItem]
    total_amount: float
    # Add other relevant fields like delivery_address, restaurant_id etc. if needed

class OrderStatusUpdateEvent(BaseModel):
    order_id: str
    status: str
    timestamp: float # e.g., time.time()
    details: Dict[str, Any] | None = None

class DbWriteOrderStatusEvent(BaseModel):
    order_id: str
    status: str
    timestamp: float
    # Include any other data needed for the DB record