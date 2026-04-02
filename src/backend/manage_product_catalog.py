"""
Step 13: Create Product Catalog Management
============================================
PROMPT Reference: Phase 4, Step 13

CRUD endpoints for the product catalog. Handles duplicate detection,
price tracking, store associations, and search/autocomplete.
"""

import logging
from flask import Blueprint, request, jsonify, g
from sqlalchemy import func

from src.backend.create_flask_application import require_auth
from src.backend.initialize_database_schema import (
    Product, PriceHistory, ReceiptItem, Purchase, Store, TelegramReceipt
)
from src.backend.normalize_product_names import canonicalize_product_name, normalize_product_category

logger = logging.getLogger(__name__)

products_bp = Blueprint("products", __name__, url_prefix="/products")


def _merge_products(session, keeper: Product, duplicate: Product):
    """Move references from duplicate to keeper, then delete duplicate."""
    if keeper.id == duplicate.id:
        return keeper

    receipt_items = session.query(ReceiptItem).filter_by(product_id=duplicate.id).all()
    for item in receipt_items:
        item.product_id = keeper.id

    price_rows = session.query(PriceHistory).filter_by(product_id=duplicate.id).all()
    for row in price_rows:
        row.product_id = keeper.id

    from src.backend.initialize_database_schema import Inventory

    duplicate_inventory = session.query(Inventory).filter_by(product_id=duplicate.id).first()
    keeper_inventory = session.query(Inventory).filter_by(product_id=keeper.id).first()
    if duplicate_inventory and keeper_inventory:
        keeper_inventory.quantity += duplicate_inventory.quantity or 0
        if keeper_inventory.threshold is None:
            keeper_inventory.threshold = duplicate_inventory.threshold
        if not keeper_inventory.location:
            keeper_inventory.location = duplicate_inventory.location
        if keeper_inventory.updated_by is None:
            keeper_inventory.updated_by = duplicate_inventory.updated_by
        session.delete(duplicate_inventory)
    elif duplicate_inventory:
        duplicate_inventory.product_id = keeper.id

    session.delete(duplicate)
    return keeper


def _get_product_receipt_links(session, product_id: int, limit: int = 3) -> list[dict]:
    """Return recent receipt links for a product."""
    rows = (
        session.query(ReceiptItem, Purchase, Store, TelegramReceipt)
        .join(Purchase, ReceiptItem.purchase_id == Purchase.id)
        .outerjoin(Store, Purchase.store_id == Store.id)
        .outerjoin(TelegramReceipt, TelegramReceipt.purchase_id == Purchase.id)
        .filter(ReceiptItem.product_id == product_id)
        .order_by(Purchase.date.desc(), ReceiptItem.id.desc())
        .limit(limit)
        .all()
    )

    seen_purchase_ids = set()
    links = []
    for _receipt_item, purchase, store, telegram_record in rows:
        if not purchase or purchase.id in seen_purchase_ids:
            continue
        seen_purchase_ids.add(purchase.id)
        links.append({
            "receipt_id": purchase.id,
            "date": purchase.date.strftime("%Y-%m-%d") if purchase.date else None,
            "store": store.name if store else "Unknown",
            "source": "telegram" if telegram_record and not str(telegram_record.telegram_user_id).startswith("upload") else "upload",
            "status": telegram_record.status if telegram_record else "processed",
            "total": purchase.total_amount,
        })
    return links


def _serialize_product(session, product: Product) -> dict:
    recent_receipts = _get_product_receipt_links(session, product.id)
    return {
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "barcode": product.barcode,
        "created_at": product.created_at.isoformat() if product.created_at else None,
        "recent_receipts": recent_receipts,
        "last_purchase_date": recent_receipts[0]["date"] if recent_receipts else None,
    }


@products_bp.route("", methods=["GET"])
@require_auth
def list_products():
    """List all products with pagination."""
    session = g.db_session
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    category = request.args.get("category")

    query = session.query(Product)
    if category:
        query = query.filter(Product.category == category)

    total = query.count()
    products = query.order_by(Product.name).offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        "products": [_serialize_product(session, p) for p in products],
        "total": total,
        "page": page,
        "per_page": per_page,
    }), 200


@products_bp.route("/search", methods=["GET"])
@require_auth
def search_products():
    """Search products by name (case-insensitive partial match)."""
    session = g.db_session
    q = request.args.get("q", "").strip()

    if not q or len(q) < 2:
        return jsonify({"error": "Query must be at least 2 characters", "results": []}), 400

    results = session.query(Product).filter(
        Product.name.ilike(f"%{q}%")
    ).order_by(Product.name).limit(20).all()

    return jsonify({
        "query": q,
        "results": [_serialize_product(session, p) for p in results],
        "count": len(results),
    }), 200


@products_bp.route("/create", methods=["POST"])
@require_auth
def create_product():
    """Add a new product to the catalog."""
    session = g.db_session
    data = request.get_json(silent=True)

    if not data or not data.get("name"):
        return jsonify({"error": "Product name is required"}), 400

    name = canonicalize_product_name(data["name"])
    category = normalize_product_category(data.get("category", "other"))

    # Check for duplicates
    existing = (
        session.query(Product)
        .filter(func.lower(Product.name) == name.lower())
        .filter(func.lower(func.coalesce(Product.category, "other")) == category)
        .first()
    )
    if existing:
        return jsonify({
            "error": "Product already exists",
            "product": {"id": existing.id, "name": existing.name, "category": existing.category},
        }), 409

    product = Product(
        name=name,
        category=category,
        barcode=data.get("barcode"),
    )
    session.add(product)
    session.commit()

    return jsonify({
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "barcode": product.barcode,
    }), 201


@products_bp.route("/<int:product_id>/update", methods=["PUT"])
@require_auth
def update_product(product_id):
    """Update an existing product."""
    session = g.db_session
    product = session.query(Product).filter_by(id=product_id).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    data = request.get_json(silent=True) or {}
    next_name = canonicalize_product_name(data["name"]) if "name" in data else product.name
    next_category = normalize_product_category(data["category"]) if "category" in data else product.category

    merge_target = (
        session.query(Product)
        .filter(Product.id != product.id)
        .filter(func.lower(Product.name) == next_name.lower())
        .filter(func.lower(func.coalesce(Product.category, "other")) == next_category)
        .first()
    )

    if "name" in data:
        product.name = next_name
    if "category" in data:
        product.category = next_category
    if "barcode" in data:
        product.barcode = data["barcode"]

    if merge_target:
        if product.barcode and not merge_target.barcode:
            merge_target.barcode = product.barcode
        product = _merge_products(session, merge_target, product)

    session.commit()

    return jsonify({
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "barcode": product.barcode,
        "merged": bool(merge_target),
    }), 200


@products_bp.route("/<int:product_id>", methods=["DELETE"])
@require_auth
def delete_product(product_id):
    """Remove a product from the catalog."""
    session = g.db_session
    product = session.query(Product).filter_by(id=product_id).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    session.delete(product)
    session.commit()

    return jsonify({"message": f"Product '{product.name}' deleted"}), 200


@products_bp.route("/<int:product_id>/price-history", methods=["GET"])
@require_auth
def get_product_price_history(product_id):
    """Get price history for a specific product."""
    session = g.db_session
    product = session.query(Product).filter_by(id=product_id).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    prices = session.query(PriceHistory).filter_by(
        product_id=product_id
    ).order_by(PriceHistory.date.desc()).limit(50).all()

    price_values = [p.price for p in prices]

    return jsonify({
        "product_id": product_id,
        "product_name": product.name,
        "prices": [
            {
                "price": p.price,
                "store_id": p.store_id,
                "date": p.date.strftime("%Y-%m-%d") if p.date else None,
            }
            for p in prices
        ],
        "avg_price": round(sum(price_values) / len(price_values), 2) if price_values else None,
        "min_price": min(price_values) if price_values else None,
        "max_price": max(price_values) if price_values else None,
    }), 200
