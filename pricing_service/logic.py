from . import schemas # Use relative import within the package
import logging

logger = logging.getLogger(__name__)

# --- Hardcoded Rules (Replace with dynamic logic/DB lookups later) ---
DISCOUNT_THRESHOLD_USD = 50.00
DISCOUNT_PERCENTAGE = 0.10
FLAT_DELIVERY_FEE_USD = 5.00


def calculate_final_price(request: schemas.PriceCalculationRequest) -> schemas.PriceCalculationResponse:
    """
    Calculates the final order price based on items and hardcoded rules.
    """
    logger.info(f"Calculating price for order_id: {request.order_id}")

    # 1. Calculate Base Total from items provided
    base_total = sum(item.price * item.quantity for item in request.items)
    logger.debug(f"Order {request.order_id}: Calculated base_total = {base_total:.2f}")

    # 2. Apply Discount (Example: Simple threshold discount)
    discount_amount = 0.0
    if base_total > DISCOUNT_THRESHOLD_USD:
        discount_amount = round(base_total * DISCOUNT_PERCENTAGE, 2)
        logger.debug(f"Order {request.order_id}: Applying {DISCOUNT_PERCENTAGE*100}% discount = {discount_amount:.2f}")

    price_after_discount = base_total - discount_amount

    # 3. Apply Fees (Example: Simple flat delivery fee)
    fees_amount = FLAT_DELIVERY_FEE_USD
    logger.debug(f"Order {request.order_id}: Applying flat fee = {fees_amount:.2f}")

    # 4. Calculate Final Total
    final_total = round(price_after_discount + fees_amount, 2)
    if final_total < 0: # Ensure price doesn't go negative
        final_total = 0.0
        logger.warning(f"Order {request.order_id}: Final total was negative after adjustments, setting to 0.")


    logger.info(f"Order {request.order_id}: Price calculated - Base: {base_total:.2f}, Discount: {discount_amount:.2f}, Fees: {fees_amount:.2f}, Final: {final_total:.2f}")

    return schemas.PriceCalculationResponse(
        order_id=request.order_id,
        base_total=round(base_total, 2),
        discount_applied=discount_amount,
        fees_applied=fees_amount,
        final_total=final_total
    )