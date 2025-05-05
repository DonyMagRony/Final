from pydantic import BaseModel, Field, conint
from typing import List

# Input item structure - must match what Order Manager sends
class PricingItem(BaseModel):
    item_id: str
    quantity: conint(gt=0) # Quantity > 0
    price: float = Field(ge=0) # Price per item >= 0

# Request body for the calculation endpoint
class PriceCalculationRequest(BaseModel):
    order_id: str # For correlation/logging
    items: List[PricingItem] = Field(..., min_length=1) # Must have at least one item
    # Add other potential factors later: user_id, delivery_info etc.

# Response body
class PriceCalculationResponse(BaseModel):
    order_id: str
    base_total: float = Field(ge=0)
    discount_applied: float = Field(ge=0, default=0.0)
    fees_applied: float = Field(ge=0, default=0.0)
    final_total: float = Field(ge=0)