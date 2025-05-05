from sqlalchemy import Column, Integer, String, TIMESTAMP, text, CheckConstraint
from sqlalchemy.sql import func
from .database import Base

class InventoryItem(Base):
    __tablename__ = "inventory_items"

    item_id = Column(String(255), primary_key=True, index=True)
    stock_count = Column(Integer, nullable=False)
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint('stock_count >= 0', name='inventory_items_stock_count_non_negative'),
    )

    def __repr__(self):
        return f"<InventoryItem(item_id='{self.item_id}', stock_count={self.stock_count})>"