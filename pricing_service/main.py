from fastapi import FastAPI, HTTPException, status
import logging
import sys # For basic error logging if needed

# Use relative imports
from . import schemas, logic, config

# Basic logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Pricing Service",
    description="Calculates order prices including discounts and fees.",
    version="0.1.0"
)

@app.on_event("startup")
async def startup_event():
    logger.info("Pricing Service starting up...")
    logger.info(f"Listening on {config.APP_HOST}:{config.APP_PORT}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Pricing Service shutting down...")


@app.get("/health", tags=["Monitoring"], summary="Health Check")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy"}

@app.post(
    "/calculate_price",
    response_model=schemas.PriceCalculationResponse,
    tags=["Pricing"],
    summary="Calculate Order Price"
)
async def calculate_price_endpoint(request_data: schemas.PriceCalculationRequest):
    """
    Receives order items (with price per item) and calculates the
    final price based on internal business rules (discounts, fees).
    """
    logger.info(f"Received price calculation request for order_id: {request_data.order_id}")
    try:
        # Call the core logic function
        price_response = logic.calculate_final_price(request_data)
        return price_response
    except Exception as e:
        # Log the exception for debugging
        logger.exception(f"Error calculating price for order {request_data.order_id}: {e}")
        # Return a generic error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during price calculation."
        )

# In a real application, you might add endpoints to manage pricing rules