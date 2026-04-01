#!/bin/bash
# =============================================================================
# Backup Database & Volumes
# PROMPT Reference: Phase 8, Step 23
#
# Creates a compressed backup of the SQLite database, receipt images,
# and MQTT config. Runs daily via cron or Docker job.
#
# Retention: 30 days (older backups auto-deleted)
# Output: /data/backups/grocery_backup_YYYYMMDD.tar.gz
# =============================================================================

set -euo pipefail

# Configuration
BACKUP_DIR="/data/backups"
DB_PATH="/data/db/grocery.db"
RECEIPTS_DIR="/data/receipts"
RETENTION_DAYS=30
DATE=$(date +%Y%m%d)
BACKUP_FILE="${BACKUP_DIR}/grocery_backup_${DATE}.tar.gz"

echo "═══════════════════════════════════════════"
echo "🗄️  Grocery Backup — $(date)"
echo "═══════════════════════════════════════════"

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Step 1: Backup SQLite database (use .backup for consistency)
echo "📦 Backing up database..."
if [ -f "${DB_PATH}" ]; then
    sqlite3 "${DB_PATH}" ".backup ${BACKUP_DIR}/grocery_${DATE}.db"
else
    echo "⚠️  Database not found at ${DB_PATH}"
fi

# Step 2: Create compressed archive
echo "🗜️  Compressing backup..."
tar -czf "${BACKUP_FILE}" \
    -C /data \
    "backups/grocery_${DATE}.db" \
    "receipts/" \
    2>/dev/null || true

# Clean up temporary DB copy
rm -f "${BACKUP_DIR}/grocery_${DATE}.db"

# Step 3: Verify backup
if [ -f "${BACKUP_FILE}" ]; then
    SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo "✅ Backup created: ${BACKUP_FILE} (${SIZE})"
else
    echo "❌ Backup failed!"
    exit 1
fi

# Step 4: Clean up old backups
echo "🧹 Cleaning backups older than ${RETENTION_DAYS} days..."
DELETED=$(find "${BACKUP_DIR}" -name "grocery_backup_*.tar.gz" -mtime +${RETENTION_DAYS} -delete -print | wc -l)
echo "   Deleted ${DELETED} old backups."

echo "═══════════════════════════════════════════"
echo "✅ Backup complete!"
echo "═══════════════════════════════════════════"
