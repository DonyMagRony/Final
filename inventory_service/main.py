from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from contextlib import asynccontextmanager # If using lifespan for table creation

# Use relative imports within the service package
from . import crud, schemas, schemas, config
from .database import get_db_session, engine, Base

# Configure logging basic setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)


# --- Optional: Lifespan for creating tables ---
# Use this only for development/testing. Use Alembic for production migrations.
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Inventory Service starting up...")
    logger.info("Checking/Creating database tables...")
    async with engine.begin() as conn:
        # Use with caution in dev, NEVER in prod without migration tool
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables check complete.")
    yield
    logger.info("Inventory Service shutting down...")
    await engine.dispose() # Clean up engine resources

app = FastAPI(
    title="Inventory Service",
    description="Manages item stock and availability checks.",
    version="0.1.0",
    lifespan=lifespan # Enable lifespan context manager
)

@app.get("/health", tags=["Monitoring"], summary="Health Check")
async def health_check():
    # Basic check, could add DB ping here later
    return {"status": "healthy"}

@app.post(
    "/check_inventory",
    response_model=schemas.InventoryCheckResponse,
    tags=["Inventory"],
    summary="Check Item Availability"
)
async def check_inventory_endpoint(
    request_data: schemas.InventoryCheckRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Checks if all requested items are available in the specified quantities.
    Returns whether all items are available and details for each item.
    """
    logger.info(f"Received inventory check request for items: {[item.item_id for item in request_data.items]}")
    try:
        availability_response = await crud.check_items_availability(db, request_data.items)
        return availability_response
    except Exception as e:
         logger.exception("Error during inventory check processing") # Log full traceback
         raise HTTPException(
              status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
              detail=f"An unexpected error occurred during inventory check: {e}"
         )


# --- Optional CRUD Endpoints for direct management ---

@app.post(
     "/items/",
     response_model=schemas.InventoryItemRead,
     status_code=status.HTTP_201_CREATED,
     tags=["Management"],
     summary="Create or Update Inventory Item"
)
async def create_or_update_inventory_item(
    item: schemas.InventoryItemCreate,
    db: AsyncSession = Depends(get_db_session)
):
     """Creates a new inventory item or updates the stock count if it already exists."""
     try:
        db_item = await crud.create_or_update_item(db=db, item=item)
        return db_item
     except Exception as e: # Catch potential DB errors
          logger.exception(f"Error creating/updating item {item.item_id}")
          raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.get(
     "/items/{item_id}",
     response_model=schemas.InventoryItemRead,
     tags=["Management"],
     summary="Get Inventory Item Details"
)
async def read_inventory_item(item_id: str, db: AsyncSession = Depends(get_db_session)):
     """Retrieves details for a specific inventory item."""
     db_item = await crud.get_item(db, item_id=item_id)
     if db_item is None:
          logger.warning(f"Item requested but not found: {item_id}")
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
     return db_item


@app.delete(
     "/items/{item_id}",
     status_code=status.HTTP_204_NO_CONTENT,
     tags=["Management"],
     summary="Delete Inventory Item"
)
async def delete_inventory_item(item_id: str, db: AsyncSession = Depends(get_db_session)):
     """Deletes an inventory item."""
     deleted = await crud.delete_item(db, item_id=item_id)
     if not deleted:
          raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
     return None # Return None for 204 response