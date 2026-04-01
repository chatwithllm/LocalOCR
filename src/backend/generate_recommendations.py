"""
Step 16: Build Recommendation Engine
======================================
PROMPT Reference: Phase 5, Step 16

Generates deal and seasonal recommendations based on purchase history.
Uses scaled confidence formulas — threshold ≥0.40.

Deal: min((avg_price - current_price) / avg_price * 5, 1.0)
Seasonal: min((days_since_last / avg_frequency - 1.0) * 2.5, 1.0)

Parallelizable: This phase is independent of Phases 4 & 6.
"""

import logging
from datetime import datetime, timezone
from statistics import median

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.40


def generate_all_recommendations() -> list:
    """Generate all recommendations for the household.

    Returns:
        List of recommendation dicts with product_id, reason, confidence.
    """
    recommendations = []

    # TODO: Implement
    # recommendations.extend(detect_price_deals())
    # recommendations.extend(detect_seasonal_patterns())
    #
    # # Filter by confidence threshold
    # recommendations = [r for r in recommendations if r["confidence"] >= CONFIDENCE_THRESHOLD]
    #
    # # Sort by confidence (highest first)
    # recommendations.sort(key=lambda r: r["confidence"], reverse=True)

    logger.warning("Recommendation engine not yet implemented")
    return recommendations


def detect_price_deals() -> list:
    """Detect products currently priced below their 3-month average.

    Algorithm:
        For each product with ≥3 price points in last 3 months:
            avg_price = average(prices)
            if current_price < avg_price * 0.9:
                confidence = min((avg_price - current_price) / avg_price * 5, 1.0)
                if confidence >= 0.40: yield recommendation
    """
    deals = []
    # TODO: Implement
    # session = get_db_session()
    # three_months_ago = datetime.now() - timedelta(days=90)
    # products = session.query(Product).all()
    #
    # for product in products:
    #     prices = [ph.price for ph in product.price_history
    #               if ph.date >= three_months_ago]
    #     if len(prices) < 3:
    #         continue
    #     avg_price = sum(prices) / len(prices)
    #     current_price = prices[-1]  # Most recent
    #     if current_price < avg_price * 0.9:
    #         confidence = min((avg_price - current_price) / avg_price * 5, 1.0)
    #         if confidence >= CONFIDENCE_THRESHOLD:
    #             deals.append({
    #                 "product_id": product.id,
    #                 "product_name": product.name,
    #                 "reason": "deal",
    #                 "confidence": round(confidence, 2),
    #                 "current_price": current_price,
    #                 "avg_price": round(avg_price, 2),
    #                 "discount_pct": round((1 - current_price / avg_price) * 100, 1),
    #             })
    return deals


def detect_seasonal_patterns() -> list:
    """Detect products overdue for repurchase based on buying frequency.

    Algorithm:
        For each product with ≥3 purchase dates:
            avg_frequency = median(intervals between purchases)
            days_since_last = today - last_purchase_date
            if days_since_last > avg_frequency * 1.2:
                confidence = min((days_since_last / avg_frequency - 1.0) * 2.5, 1.0)
                if confidence >= 0.40: yield recommendation
    """
    seasonal = []
    # TODO: Implement
    # session = get_db_session()
    # products_with_history = ...
    #
    # for product, purchase_dates in products_with_history:
    #     if len(purchase_dates) < 3:
    #         continue
    #     intervals = [(purchase_dates[i+1] - purchase_dates[i]).days
    #                  for i in range(len(purchase_dates) - 1)]
    #     avg_frequency = median(intervals)
    #     days_since_last = (datetime.now().date() - purchase_dates[-1]).days
    #     if days_since_last > avg_frequency * 1.2:
    #         confidence = min((days_since_last / avg_frequency - 1.0) * 2.5, 1.0)
    #         if confidence >= CONFIDENCE_THRESHOLD:
    #             seasonal.append({
    #                 "product_id": product.id,
    #                 "product_name": product.name,
    #                 "reason": "seasonal",
    #                 "confidence": round(confidence, 2),
    #                 "days_since_last": days_since_last,
    #                 "avg_frequency_days": avg_frequency,
    #             })
    return seasonal
