#!/bin/bash
# =============================================================================
# Restore from Backup
# PROMPT Reference: Phase 8, Step 23
#
# Restores the SQLite database and receipt images from a backup archive.
# Can restore on a different machine — fully portable.
#
# Usage: ./scripts/restore_from_backup.sh /path/to/grocery_backup_YYYYMMDD.tar.gz
# =============================================================================

set -euo pipefail

BACKUP_FILE="${1:-}"

if [ -z "${BACKUP_FILE}" ]; then
    echo "Usage: $0 <backup_file.tar.gz>"
    echo ""
    echo "Available backups:"
    ls -lh /data/backups/grocery_backup_*.tar.gz 2>/dev/null || echo "  No backups found in /data/backups/"
    exit 1
fi

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "❌ Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

echo "═══════════════════════════════════════════"
echo "🔄 Grocery Restore — $(date)"
echo "   Source: ${BACKUP_FILE}"
echo "═══════════════════════════════════════════"

# Confirm
read -p "⚠️  This will overwrite current data. Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Step 1: Stop the backend (if running in Docker)
echo "🛑 Stopping backend service..."
docker-compose stop backend 2>/dev/null || true

# Step 2: Extract backup
echo "📦 Extracting backup..."
tar -xzf "${BACKUP_FILE}" -C /data

# Step 3: Restore database
BACKUP_DB=$(find /data/backups -name "grocery_*.db" -newer "${BACKUP_FILE}" -maxdepth 1 | head -1)
if [ -n "${BACKUP_DB}" ]; then
    echo "🗄️  Restoring database..."
    cp "${BACKUP_DB}" /data/db/grocery.db
    rm -f "${BACKUP_DB}"
fi

# Step 4: Restart backend
echo "🚀 Restarting backend service..."
docker-compose start backend 2>/dev/null || true

echo "═══════════════════════════════════════════"
echo "✅ Restore complete!"
echo "   Database and receipts restored from backup."
echo "═══════════════════════════════════════════"
