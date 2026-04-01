"""
Step 13: Create Product Catalog Management
============================================
PROMPT Reference: Phase 4, Step 13

CRUD endpoints for the product catalog. Handles duplicate detection,
price tracking, store associations, and search/autocomplete.
"""

import logging
from flask import Blueprint, request, jsonify, g

from src.backend.create_flask_application import require_auth
from src.backend.initialize_database_schema import Product, PriceHistory

logger = logging.getLogger(__name__)

products_bp = Blueprint("products", __name__, url_prefix="/products")


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
        "products": [
            {
                "id": p.id,
                "name": p.name,
                "category": p.category,
                "barcode": p.barcode,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in products
        ],
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
        "results": [
            {"id": p.id, "name": p.name, "category": p.category}
            for p in results
        ],
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

    name = data["name"].strip()
    category = data.get("category", "other").strip()

    # Check for duplicates
    existing = session.query(Product).filter_by(name=name, category=category).first()
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
    if "name" in data:
        product.name = data["name"].strip()
    if "category" in data:
        product.category = data["category"].strip()
    if "barcode" in data:
        product.barcode = data["barcode"]

    session.commit()

    return jsonify({
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "barcode": product.barcode,
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
