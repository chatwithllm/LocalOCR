"""initial schema - all tables

Revision ID: 001_initial
Revises: None
Create Date: 2026-04-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), unique=True, nullable=True),
        sa.Column("role", sa.String(20), nullable=False, server_default="user"),
        sa.Column("api_token_hash", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )

    # --- stores ---
    op.create_table(
        "stores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("location", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )

    # --- products ---
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("barcode", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
        sa.UniqueConstraint("name", "category", name="uq_product_name_category"),
    )
    op.create_index("ix_product_name", "products", ["name"])
    op.create_index("ix_product_category", "products", ["category"])

    # --- inventory ---
    op.create_table(
        "inventory",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False, server_default="0"),
        sa.Column("location", sa.String(50), nullable=True),
        sa.Column("threshold", sa.Float(), nullable=True),
        sa.Column("last_updated", sa.DateTime()),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_inventory_product_id", "inventory", ["product_id"])

    # --- purchases ---
    op.create_table(
        "purchases",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("stores.id"), nullable=True),
        sa.Column("total_amount", sa.Float(), nullable=True),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_purchase_date", "purchases", ["date"])
    op.create_index("ix_purchase_user_id", "purchases", ["user_id"])

    # --- receipt_items ---
    op.create_table(
        "receipt_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("purchase_id", sa.Integer(), sa.ForeignKey("purchases.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Float(), nullable=False),
        sa.Column("extracted_by", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_receipt_item_product_id", "receipt_items", ["product_id"])

    # --- price_history ---
    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("stores.id"), nullable=True),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime()),
    )
    op.create_index("ix_price_history_product_id", "price_history", ["product_id"])
    op.create_index("ix_price_history_date", "price_history", ["date"])

    # --- budget ---
    op.create_table(
        "budget",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("month", sa.String(7), nullable=False),
        sa.Column("budget_amount", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
        sa.UniqueConstraint("user_id", "month", name="uq_budget_user_month"),
    )

    # --- telegram_receipts ---
    op.create_table(
        "telegram_receipts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("telegram_user_id", sa.String(50), nullable=False),
        sa.Column("message_id", sa.String(50), nullable=True),
        sa.Column("image_path", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("ocr_confidence", sa.Float(), nullable=True),
        sa.Column("ocr_engine", sa.String(20), nullable=True),
        sa.Column("purchase_id", sa.Integer(), sa.ForeignKey("purchases.id"), nullable=True),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )

    # --- api_usage ---
    op.create_table(
        "api_usage",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("service_name", sa.String(50), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
        sa.UniqueConstraint("service_name", "date", name="uq_api_usage_per_day"),
    )


def downgrade() -> None:
    op.drop_table("api_usage")
    op.drop_table("telegram_receipts")
    op.drop_table("budget")
    op.drop_table("price_history")
    op.drop_table("receipt_items")
    op.drop_table("purchases")
    op.drop_table("inventory")
    op.drop_table("products")
    op.drop_table("stores")
    op.drop_table("users")
