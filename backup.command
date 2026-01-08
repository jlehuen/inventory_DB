#!/bin/bash
cd "$(dirname $0)"

BACKUP_DIR="./backups"
DATE=$(date +%Y-%m-%d_%H-%M-%S)

tar -czvf $BACKUP_DIR/database_$DATE.tgz database
