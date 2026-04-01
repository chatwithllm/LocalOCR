"""
Step 3: Setup Flask Backend API
================================
PROMPT Reference: Phase 1, Step 3

Initializes the Flask application with blueprint structure, authentication
middleware (Bearer token), error handling, logging, and CORS configuration.

Port: 8080 (accessed via Nginx Proxy Manager for external access)
"""

import os
import hashlib
import logging
from functools import wraps

from flask import Flask, jsonify, request, g

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Authentication Middleware
# ---------------------------------------------------------------------------

def hash_token(token: str) -> str:
    """Hash an API token for secure storage/comparison."""
    return hashlib.sha256(token.encode()).hexdigest()


def require_auth(f):
    """Decorator to require Bearer token authentication on endpoints."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header.split("Bearer ", 1)[1]
        token_hash = hash_token(token)

        # TODO: Validate token_hash against users table
        # session = g.get("db_session")
        # user = session.query(User).filter_by(api_token_hash=token_hash).first()
        # if not user:
        #     return jsonify({"error": "Invalid token"}), 401
        # g.current_user = user

        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Error Handlers
# ---------------------------------------------------------------------------

def register_error_handlers(app):
    """Register standard error handlers for the Flask app."""

    @app.errorhandler(400)
    def bad_request(e):
        return jsonify({"error": "Bad request", "message": str(e)}), 400

    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({"error": "Unauthorized"}), 401

    @app.errorhandler(403)
    def forbidden(e):
        return jsonify({"error": "Forbidden"}), 403

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f"Internal server error: {e}")
        return jsonify({"error": "Internal server error"}), 500


# ---------------------------------------------------------------------------
# Blueprint Registration
# ---------------------------------------------------------------------------

def register_blueprints(app):
    """Register all API blueprints."""
    # TODO: Import and register blueprints as they are implemented
    #
    # from src.backend.handle_telegram_messages import telegram_bp
    # from src.backend.manage_product_catalog import products_bp
    # from src.backend.manage_inventory import inventory_bp
    # from src.backend.handle_receipt_upload import receipts_bp
    # from src.backend.calculate_spending_analytics import analytics_bp
    #
    # app.register_blueprint(telegram_bp)
    # app.register_blueprint(products_bp)
    # app.register_blueprint(inventory_bp)
    # app.register_blueprint(receipts_bp)
    # app.register_blueprint(analytics_bp)
    pass


# ---------------------------------------------------------------------------
# App Factory
# ---------------------------------------------------------------------------

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Configuration
    app.config["FLASK_ENV"] = os.getenv("FLASK_ENV", "development")
    app.config["DATABASE_URL"] = os.getenv("DATABASE_URL", "sqlite:////data/db/grocery.db")

    # Logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    # Error handlers
    register_error_handlers(app)

    # Blueprints
    register_blueprints(app)

    # Health check endpoint (used by Docker healthcheck)
    @app.route("/health")
    def health():
        return jsonify({"status": "healthy", "service": "grocery-backend"}), 200

    logger.info("Flask application created successfully.")
    return app


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("FLASK_PORT", 8080))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
