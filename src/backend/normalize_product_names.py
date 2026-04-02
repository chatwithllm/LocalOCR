"""
Helpers for standardizing product names and merging obvious duplicates.
"""

from __future__ import annotations

import re


def canonicalize_product_name(name: str) -> str:
    """Normalize OCR-heavy product names into a consistent display form."""
    text = re.sub(r"\s+", " ", str(name or "").strip())
    if not text:
        return "Unknown Item"

    known_upper_tokens = {"KS", "HBO", "ABF", "CK", "CAD", "TV", "BD"}

    def normalize_token(token: str) -> str:
        if not token:
            return token
        if re.fullmatch(r"[A-Z0-9/&+-]{2,}", token):
            if any(ch.isdigit() for ch in token):
                return token.upper()
            if token.upper() in known_upper_tokens:
                return token.upper()
        if "/" in token:
            return "/".join(normalize_token(part) for part in token.split("/"))
        if "-" in token:
            return "-".join(normalize_token(part) for part in token.split("-"))
        return token[:1].upper() + token[1:].lower()

    return " ".join(normalize_token(token) for token in text.split(" "))


def normalize_product_category(category: str | None) -> str:
    return str(category or "other").strip().lower() or "other"


def find_matching_product(session, name: str, category: str) -> Product | None:
    """Look up a product by normalized, case-insensitive name within a category."""
    from sqlalchemy import func

    from src.backend.initialize_database_schema import Product

    normalized_name = canonicalize_product_name(name)
    normalized_category = normalize_product_category(category)
    return (
        session.query(Product)
        .filter(func.lower(Product.name) == normalized_name.lower())
        .filter(func.lower(func.coalesce(Product.category, "other")) == normalized_category)
        .order_by(Product.id.asc())
        .first()
    )


def merge_case_variant_products(session) -> int:
    """Merge products that only differ by case/spacing within the same category."""
    from src.backend.initialize_database_schema import Inventory, PriceHistory, Product, ReceiptItem

    products = session.query(Product).order_by(Product.id.asc()).all()
    canonical_map: dict[tuple[str, str], Product] = {}
    merged_count = 0

    for product in products:
        canonical_name = canonicalize_product_name(product.name)
        canonical_category = normalize_product_category(product.category)
        key = (canonical_name.lower(), canonical_category)

        if key not in canonical_map:
            product.name = canonical_name
            product.category = canonical_category
            canonical_map[key] = product
            continue

        keeper = canonical_map[key]
        duplicate = product

        receipt_items = session.query(ReceiptItem).filter_by(product_id=duplicate.id).all()
        for item in receipt_items:
            item.product_id = keeper.id

        price_rows = session.query(PriceHistory).filter_by(product_id=duplicate.id).all()
        for row in price_rows:
            row.product_id = keeper.id

        duplicate_inventory = session.query(Inventory).filter_by(product_id=duplicate.id).first()
        keeper_inventory = session.query(Inventory).filter_by(product_id=keeper.id).first()
        if duplicate_inventory and keeper_inventory:
            keeper_inventory.quantity += duplicate_inventory.quantity
            if duplicate_inventory.threshold is not None:
                keeper_inventory.threshold = duplicate_inventory.threshold
            if duplicate_inventory.location and not keeper_inventory.location:
                keeper_inventory.location = duplicate_inventory.location
            if duplicate_inventory.updated_by and not keeper_inventory.updated_by:
                keeper_inventory.updated_by = duplicate_inventory.updated_by
            session.delete(duplicate_inventory)
        elif duplicate_inventory:
            duplicate_inventory.product_id = keeper.id

        session.delete(duplicate)
        merged_count += 1

    return merged_count
