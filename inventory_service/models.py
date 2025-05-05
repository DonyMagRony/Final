from sqlalchemy import Column, Integer, String, TIMESTAMP, text, CheckConstraint
from sqlalchemy.sql import func
from .database import Base

class InventoryItem(Base):
    __tablename__ = "inventory_items"

    item_id = Column(String(255), primary_key=True, index=True) # Add index
    stock_count = Column(Integer, nullable=False)
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(), # Use func.now() for SQLAlchemy 2.0
        onupdate=func.now() # Automatically update on change via SQLAlchemy (alternative to DB trigger)
    )

    # Add constraint directly in the model
    __table_args__ = (
        CheckConstraint('stock_count >= 0', name='inventory_items_stock_count_non_negative'),
    )

    def __repr__(self):
        return f"<InventoryItem(item_id='{self.item_id}', stock_count={self.stock_count})>"