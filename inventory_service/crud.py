from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_ # If needed for complex queries
from . import schemas, models
import logging

logger = logging.getLogger(__name__)

async def check_items_availability(db: AsyncSession, items_to_check: list[schemas.ItemCheckRequest]) -> schemas.InventoryCheckResponse:
    """
    Checks availability for a list of items.
    Fetches all items in one query for efficiency.
    """
    all_available = True
    response_details = []
    item_id_map = {item.item_id: item.quantity for item in items_to_check}
    item_ids = list(item_id_map.keys())

    logger.info(f"Checking availability for items: {item_ids}")

    # Select inventory items matching the requested IDs
    stmt = select(models.InventoryItem).where(models.InventoryItem.item_id.in_(item_ids))
    result = await db.execute(stmt)

    fetched_items_stock = {item.item_id: item.stock_count for item in result.scalars().all()}
    logger.debug(f"Fetched stock counts: {fetched_items_stock}")

    for item_id, requested_quantity in item_id_map.items():
        current_stock = fetched_items_stock.get(item_id) # Will be None if item_id not in DB

        if current_stock is not None and current_stock >= requested_quantity:
            item_detail = schemas.ItemAvailabilityDetail(
                item_id=item_id,
                requested=requested_quantity,
                available=True,
                current_stock=current_stock
            )
        else:
            all_available = False
            item_detail = schemas.ItemAvailabilityDetail(
                item_id=item_id,
                requested=requested_quantity,
                available=False,
                current_stock=current_stock if current_stock is not None else 0 # Report 0 if not found
            )
            logger.warning(f"Item '{item_id}' unavailable. Requested: {requested_quantity}, Stock: {current_stock}")

        response_details.append(item_detail)

    logger.info(f"Overall availability result: {all_available}")
    return schemas.InventoryCheckResponse(all_available=all_available, details=response_details)

# --- Optional CRUD for managing inventory items directly ---

async def get_item(db: AsyncSession, item_id: str) -> models.InventoryItem | None:
    result = await db.execute(select(models.InventoryItem).filter(models.InventoryItem.item_id == item_id))
    return result.scalars().first()

async def create_or_update_item(db: AsyncSession, item: schemas.InventoryItemCreate) -> models.InventoryItem:
    db_item = await get_item(db, item.item_id)
    if db_item:
        # Update existing item
        db_item.stock_count = item.stock_count
        logger.info(f"Updating item '{item.item_id}' stock to {item.stock_count}")
    else:
        # Create new item
        db_item = models.InventoryItem(**item.model_dump())
        db.add(db_item)
        logger.info(f"Creating new item '{item.item_id}' with stock {item.stock_count}")
    await db.commit()
    await db.refresh(db_item)
    return db_item

async def delete_item(db: AsyncSession, item_id: str) -> bool:
     db_item = await get_item(db, item_id)
     if db_item:
          await db.delete(db_item)
          await db.commit()
          logger.info(f"Deleted item '{item_id}'")
          return True
     logger.warning(f"Attempted to delete non-existent item '{item_id}'")
     return False