from pydantic import BaseModel, Field, conint
from typing import List
import datetime

class ItemCheckRequest(BaseModel):
    item_id: str
    quantity: conint(gt=0) # Ensures quantity is integer > 0

class InventoryCheckRequest(BaseModel):
    items: List[ItemCheckRequest] = Field(..., min_length=1) # Require at least one item

class ItemAvailabilityDetail(BaseModel):
    item_id: str
    requested: int
    available: bool
    current_stock: int | None = None # Current stock count in DB

class InventoryCheckResponse(BaseModel):
    all_available: bool
    details: List[ItemAvailabilityDetail]

# Schema for potentially adding/updating items via API (optional)
class InventoryItemBase(BaseModel):
     item_id: str
     stock_count: conint(ge=0) # Allows 0

class InventoryItemCreate(InventoryItemBase):
     pass

class InventoryItemRead(InventoryItemBase):
     updated_at: datetime.datetime
     class Config:
          orm_mode = True # Compatibility with ORM models