"""
Step 14: Implement Inventory Tracking
=======================================
PROMPT Reference: Phase 4, Step 14

CRUD endpoints for household inventory. Every change publishes an MQTT
event for real-time sync. Tracks user attribution for audit trail.

MQTT Topic: home/grocery/inventory/{product_id}
Parallelizable: This phase is independent of Phases 5 & 6.
"""

import logging
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")


@inventory_bp.route("", methods=["GET"])
def list_inventory():
    """View current household inventory."""
    # TODO: Implement
    # - Query inventory table joined with products
    # - Return product name, quantity, location, last_updated, updated_by
    return jsonify({"inventory": [], "message": "Not yet implemented"}), 501


@inventory_bp.route("/add-item", methods=["POST"])
def add_item():
    """Add a product to inventory with quantity."""
    # TODO: Implement
    # - Validate fields (product_id or product_name, quantity, location)
    # - Create/update inventory record
    # - Track updated_by user
    # - Publish MQTT event: home/grocery/inventory/{product_id}
    return jsonify({"message": "Not yet implemented"}), 501


@inventory_bp.route("/<int:item_id>/consume", methods=["PUT"])
def consume_item(item_id):
    """Decrease quantity by 1 (or specified amount)."""
    # TODO: Implement
    # - Prevent negative quantities
    # - Track user who consumed
    # - Publish MQTT event
    # - Check if below threshold → trigger low-stock alert
    return jsonify({"message": "Not yet implemented", "item_id": item_id}), 501


@inventory_bp.route("/<int:item_id>/update", methods=["PUT"])
def update_item(item_id):
    """Set quantity directly."""
    # TODO: Implement
    # - Update quantity
    # - Track user + timestamp
    # - Publish MQTT event
    return jsonify({"message": "Not yet implemented", "item_id": item_id}), 501


@inventory_bp.route("/<int:item_id>", methods=["DELETE"])
def remove_item(item_id):
    """Remove an item from inventory."""
    # TODO: Implement
    return jsonify({"message": "Not yet implemented", "item_id": item_id}), 501
