"""
Step 14: Implement Inventory Tracking
=======================================
PROMPT Reference: Phase 4, Step 14

CRUD endpoints for household inventory. Every change publishes an MQTT
event for real-time sync. Tracks user attribution for audit trail.

MQTT Topic: home/grocery/inventory/{product_id}
"""

import logging
from flask import Blueprint, request, jsonify, g
from sqlalchemy import func

from src.backend.create_flask_application import require_auth
from src.backend.initialize_database_schema import Inventory, Product
from src.backend.normalize_product_names import canonicalize_product_name, normalize_product_category

logger = logging.getLogger(__name__)

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")


@inventory_bp.route("", methods=["GET"])
@require_auth
def list_inventory():
    """View current household inventory."""
    session = g.db_session
    location = request.args.get("location")
    low_stock = request.args.get("low_stock", "false").lower() == "true"

    query = session.query(Inventory).join(Product)

    if location:
        query = query.filter(Inventory.location == location)

    if low_stock:
        query = query.filter(
            Inventory.threshold.isnot(None),
            Inventory.quantity < Inventory.threshold
        )

    items = query.order_by(Product.name).all()

    return jsonify({
        "inventory": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product.name,
                "category": item.product.category,
                "quantity": item.quantity,
                "location": item.location,
                "threshold": item.threshold,
                "is_low": (item.threshold and item.quantity < item.threshold),
                "updated_by": item.updated_by,
                "last_updated": item.last_updated.isoformat() if item.last_updated else None,
            }
            for item in items
        ],
        "count": len(items),
    }), 200


@inventory_bp.route("/add-item", methods=["POST"])
@require_auth
def add_item():
    """Add a product to inventory with quantity."""
    session = g.db_session
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"error": "JSON body required"}), 400

    # Accept either product_id or product_name
    product_id = data.get("product_id")
    product_name = data.get("product_name")
    quantity = data.get("quantity", 1)
    location = data.get("location", "Pantry")
    threshold = data.get("threshold")

    if not product_id and not product_name:
        return jsonify({"error": "product_id or product_name required"}), 400

    # Find or create product
    if product_id:
        product = session.query(Product).filter_by(id=product_id).first()
        if not product:
            return jsonify({"error": f"Product {product_id} not found"}), 404
    else:
        product_name = canonicalize_product_name(product_name)
        category = normalize_product_category(data.get("category", "other"))
        product = (
            session.query(Product)
            .filter(func.lower(Product.name) == product_name.lower())
            .filter(func.lower(func.coalesce(Product.category, "other")) == category)
            .first()
        )
        if not product:
            product = Product(name=product_name, category=category)
            session.add(product)
            session.flush()

    user_id = getattr(g, "current_user", None)
    user_id = user_id.id if user_id else None

    # Check if already in inventory
    existing = session.query(Inventory).filter_by(product_id=product.id).first()
    if existing:
        existing.quantity += quantity
        existing.location = location
        existing.updated_by = user_id
        if threshold is not None:
            existing.threshold = threshold
        item = existing
    else:
        item = Inventory(
            product_id=product.id,
            quantity=quantity,
            location=location,
            threshold=threshold,
            updated_by=user_id,
        )
        session.add(item)

    session.commit()

    # Publish MQTT event
    _publish_update(product, item)

    return jsonify({
        "id": item.id,
        "product_id": product.id,
        "product_name": product.name,
        "quantity": item.quantity,
        "location": item.location,
        "threshold": item.threshold,
    }), 201


@inventory_bp.route("/<int:item_id>/consume", methods=["PUT"])
@require_auth
def consume_item(item_id):
    """Decrease quantity by 1 (or specified amount)."""
    session = g.db_session
    data = request.get_json(silent=True) or {}
    amount = data.get("amount", 1)

    item = session.query(Inventory).filter_by(id=item_id).first()
    if not item:
        return jsonify({"error": "Inventory item not found"}), 404

    # Prevent negative quantities
    item.quantity = max(0, item.quantity - amount)
    user_id = getattr(g, "current_user", None)
    item.updated_by = user_id.id if user_id else None
    session.commit()

    product = session.query(Product).filter_by(id=item.product_id).first()
    _publish_update(product, item)

    # Check if below threshold
    if item.threshold and item.quantity < item.threshold:
        _trigger_low_stock_alert(product, item)

    return jsonify({
        "id": item.id,
        "product_name": product.name if product else None,
        "quantity": item.quantity,
        "consumed": amount,
        "is_low": bool(item.threshold and item.quantity < item.threshold),
    }), 200


@inventory_bp.route("/<int:item_id>/update", methods=["PUT"])
@require_auth
def update_item(item_id):
    """Set quantity directly."""
    session = g.db_session
    data = request.get_json(silent=True) or {}

    item = session.query(Inventory).filter_by(id=item_id).first()
    if not item:
        return jsonify({"error": "Inventory item not found"}), 404

    if "quantity" in data:
        item.quantity = max(0, data["quantity"])
    if "location" in data:
        item.location = data["location"]
    if "threshold" in data:
        item.threshold = data["threshold"]

    user_id = getattr(g, "current_user", None)
    item.updated_by = user_id.id if user_id else None
    session.commit()

    product = session.query(Product).filter_by(id=item.product_id).first()
    _publish_update(product, item)

    return jsonify({
        "id": item.id,
        "product_name": product.name if product else None,
        "quantity": item.quantity,
        "location": item.location,
        "threshold": item.threshold,
    }), 200


@inventory_bp.route("/<int:item_id>", methods=["DELETE"])
@require_auth
def remove_item(item_id):
    """Remove an item from inventory."""
    session = g.db_session
    item = session.query(Inventory).filter_by(id=item_id).first()
    if not item:
        return jsonify({"error": "Inventory item not found"}), 404

    product = session.query(Product).filter_by(id=item.product_id).first()
    session.delete(item)
    session.commit()

    return jsonify({
        "message": f"'{product.name if product else 'Item'}' removed from inventory",
    }), 200


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _publish_update(product, item):
    """Publish MQTT event for inventory change."""
    try:
        from src.backend.publish_mqtt_events import publish_inventory_update
        publish_inventory_update(
            product_id=product.id,
            name=product.name,
            quantity=item.quantity,
            location=item.location or "Pantry",
            updated_by=str(item.updated_by or "system"),
        )
    except Exception as e:
        logger.warning(f"Failed to publish MQTT inventory update: {e}")


def _trigger_low_stock_alert(product, item):
    """Publish low-stock alert via MQTT."""
    try:
        from src.backend.publish_mqtt_events import publish_low_stock_alert
        publish_low_stock_alert(
            product_id=product.id,
            product_name=product.name,
            current_qty=item.quantity,
            threshold=item.threshold,
        )
    except Exception as e:
        logger.warning(f"Failed to publish low-stock alert: {e}")
