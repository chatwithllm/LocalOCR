"""
Grocery Inventory & Savings Management System — Backend Package.

This package contains all backend modules for the grocery management system.
Each module follows the Verb + Noun naming convention for human readability.

Modules:
    initialize_database_schema  — Step 2: SQLite + Alembic setup
    create_flask_application    — Step 3: Flask app + auth middleware
    setup_mqtt_connection       — Step 4: MQTT broker connection
    handle_receipt_upload       — Step 5: Stub upload endpoint
    configure_telegram_webhook  — Step 6: Telegram bot webhook config
    handle_telegram_messages    — Step 8: Telegram webhook handler
    call_gemini_vision_api      — Step 9: Gemini OCR integration
    call_ollama_vision_api      — Step 10: Ollama LLaVA fallback
    extract_receipt_data        — Step 11: Hybrid OCR orchestrator
    save_receipt_images         — Step 12: Image storage + retention
    manage_product_catalog      — Step 13: Product CRUD
    manage_inventory            — Step 14: Inventory tracking + MQTT
    check_inventory_thresholds  — Step 15: Low-stock alerts
    generate_recommendations    — Step 16: Deal + seasonal detection
    schedule_daily_recommendations — Step 17: Daily push scheduler
    calculate_spending_analytics — Step 18: Spending reports
    manage_household_budget     — Step 19: Budget tracking
    publish_mqtt_events         — Step 20: MQTT event publisher
"""
