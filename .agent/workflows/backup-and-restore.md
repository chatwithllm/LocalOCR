---
description: Create and restore backups of the grocery database and receipts
---

# Backup and Restore

## Create a Backup

// turbo
1. Run the backup script
```bash
docker exec grocery-backend bash /app/scripts/backup_database_and_volumes.sh
```

// turbo
2. List available backups
```bash
docker exec grocery-backend ls -lh /data/backups/
```

3. Copy backup to host machine (optional)
```bash
docker cp grocery-backend:/data/backups/grocery_backup_$(date +%Y%m%d).tar.gz ./backups/
```

## Restore from Backup

1. List available backups
```bash
docker exec grocery-backend ls -lh /data/backups/
```

2. Run the restore script
```bash
docker exec -it grocery-backend bash /app/scripts/restore_from_backup.sh /data/backups/grocery_backup_YYYYMMDD.tar.gz
```

3. Verify data was restored
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8080/inventory
```

## Restore on a New Machine

1. Clone repo and set up environment (see `/setup-dev-environment` workflow)
2. Start Docker Compose stack
3. Copy backup file into the container:
```bash
docker cp grocery_backup_YYYYMMDD.tar.gz grocery-backend:/data/backups/
```
4. Run restore script
5. Verify data

## Automated Daily Backups

Add to crontab on the host machine:
```bash
# Run backup daily at 2 AM
0 2 * * * docker exec grocery-backend bash /app/scripts/backup_database_and_volumes.sh >> /var/log/grocery-backup.log 2>&1
```

## Notes
- Backups include: SQLite database + all receipt images
- Retention: 30 days (older backups auto-deleted)
- DB records are preserved even when image retention cleanup runs
- Backups are portable — can restore on any machine with Docker
