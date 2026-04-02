"""
Shopping list endpoints.
"""

from flask import Blueprint, jsonify, request, g
from sqlalchemy import func

from src.backend.create_flask_application import require_auth
from src.backend.initialize_database_schema import Product, ShoppingListItem
from src.backend.normalize_product_names import (
    canonicalize_product_name,
    find_matching_product,
    normalize_product_category,
)

shopping_list_bp = Blueprint("shopping_list", __name__, url_prefix="/shopping-list")


def _serialize_item(item: ShoppingListItem) -> dict:
    return {
        "id": item.id,
        "product_id": item.product_id,
        "name": item.name,
        "category": item.category,
        "quantity": item.quantity,
        "status": item.status,
        "source": item.source,
        "note": item.note,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
    }


@shopping_list_bp.route("", methods=["GET"])
@require_auth
def list_shopping_items():
    session = g.db_session
    status = request.args.get("status", "").strip().lower()

    query = session.query(ShoppingListItem)
    if status:
        query = query.filter(ShoppingListItem.status == status)

    items = query.order_by(
        ShoppingListItem.status.asc(),
        ShoppingListItem.created_at.desc(),
    ).all()

    return jsonify({
        "items": [_serialize_item(item) for item in items],
        "count": len(items),
        "open_count": session.query(ShoppingListItem).filter(ShoppingListItem.status == "open").count(),
        "purchased_count": session.query(ShoppingListItem).filter(ShoppingListItem.status == "purchased").count(),
    }), 200


@shopping_list_bp.route("/items", methods=["POST"])
@require_auth
def add_shopping_item():
    session = g.db_session
    data = request.get_json(silent=True) or {}

    raw_name = (data.get("name") or data.get("product_name") or "").strip()
    if not raw_name:
        return jsonify({"error": "Item name is required"}), 400

    name = canonicalize_product_name(raw_name)
    category = normalize_product_category(data.get("category", "other"))
    quantity = float(data.get("quantity") or 1)
    source = (data.get("source") or "manual").strip().lower()
    note = (data.get("note") or "").strip() or None

    product = None
    product_id = data.get("product_id")
    if product_id:
        product = session.query(Product).filter_by(id=product_id).first()
    if not product:
        product = find_matching_product(session, name, category)

    existing = (
        session.query(ShoppingListItem)
        .filter(ShoppingListItem.status == "open")
        .filter(func.lower(ShoppingListItem.name) == name.lower())
        .filter(func.lower(func.coalesce(ShoppingListItem.category, "other")) == category)
        .first()
    )
    if existing:
        existing.quantity += quantity
        if note and not existing.note:
            existing.note = note
        if source and not existing.source:
            existing.source = source
        if product and not existing.product_id:
            existing.product_id = product.id
        session.commit()
        return jsonify({"item": _serialize_item(existing), "merged": True}), 200

    item = ShoppingListItem(
        product_id=product.id if product else None,
        user_id=getattr(getattr(g, "current_user", None), "id", None),
        name=name,
        category=category,
        quantity=quantity,
        status="open",
        source=source,
        note=note,
    )
    session.add(item)
    session.commit()
    return jsonify({"item": _serialize_item(item), "merged": False}), 201


@shopping_list_bp.route("/items/<int:item_id>", methods=["PUT"])
@require_auth
def update_shopping_item(item_id):
    session = g.db_session
    item = session.query(ShoppingListItem).filter_by(id=item_id).first()
    if not item:
        return jsonify({"error": "Shopping list item not found"}), 404

    data = request.get_json(silent=True) or {}
    if "name" in data:
        item.name = canonicalize_product_name(data["name"])
    if "category" in data:
        item.category = normalize_product_category(data["category"])
    if "quantity" in data:
        item.quantity = float(data["quantity"])
    if "status" in data:
        item.status = str(data["status"]).strip().lower() or item.status
    if "note" in data:
        item.note = (data["note"] or "").strip() or None

    session.commit()
    return jsonify({"item": _serialize_item(item)}), 200


@shopping_list_bp.route("/items/<int:item_id>", methods=["DELETE"])
@require_auth
def delete_shopping_item(item_id):
    session = g.db_session
    item = session.query(ShoppingListItem).filter_by(id=item_id).first()
    if not item:
        return jsonify({"error": "Shopping list item not found"}), 404

    session.delete(item)
    session.commit()
    return jsonify({"message": "Shopping list item deleted"}), 200
