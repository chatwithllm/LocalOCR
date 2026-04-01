"""
Step 19: Implement Budget Management
======================================
PROMPT Reference: Phase 6, Step 19

Budget setting and tracking endpoints. Alerts at 80% threshold via MQTT.

MQTT Topic: home/grocery/alerts/budget
"""

import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

budget_bp = Blueprint("budget", __name__, url_prefix="/budget")


@budget_bp.route("/set-monthly", methods=["POST"])
def set_monthly_budget():
    """Set the monthly grocery budget.

    Body: { "month": "2026-04", "budget_amount": 600.00 }
    """
    # TODO: Implement
    # data = request.get_json()
    # Validate and save to budget table
    return jsonify({"message": "Not yet implemented"}), 501


@budget_bp.route("/status", methods=["GET"])
def get_budget_status():
    """Get current month's budget vs actual spending.

    Returns: budget_amount, spent, remaining, percentage, alert_triggered
    """
    # TODO: Implement
    # - Get current month's budget from DB
    # - Sum purchases for current month
    # - Calculate % spent
    # - If >= 80% and not already alerted, trigger MQTT alert
    return jsonify({
        "budget_amount": 0,
        "spent": 0,
        "remaining": 0,
        "percentage": 0,
        "alert_triggered": False,
        "message": "Not yet implemented",
    }), 501
