#!/bin/bash
# Database Backup Script for Facepass Microservice Isolation
# This script creates a backup of the face_embeddings table before migration

set -e  # Exit on error

# Configuration
BACKUP_DIR="backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/face_embeddings_backup_${TIMESTAMP}.sql"

# Database connection parameters (from .env)
source .env

DB_HOST="${VECTOR_DB_HOST:-db_vector}"
DB_PORT="${VECTOR_DB_PORT:-5432}"
DB_NAME="${VECTOR_POSTGRES_DB}"
DB_USER="${POSTGRES_USER}"

echo "========================================="
echo "Facepass Database Backup Script"
echo "========================================="
echo ""
echo "Backup Configuration:"
echo "  Database: ${DB_NAME}"
echo "  Host: ${DB_HOST}:${DB_PORT}"
echo "  User: ${DB_USER}"
echo "  Backup file: ${BACKUP_FILE}"
echo ""

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Check if database is accessible
echo "Checking database connection..."
if ! PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "SELECT 1" > /dev/null 2>&1; then
    echo "❌ Error: Cannot connect to database"
    echo "   Please check your database connection parameters"
    exit 1
fi
echo "✅ Database connection successful"
echo ""

# Get table statistics
echo "Analyzing face_embeddings table..."
TOTAL_ROWS=$(PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c "SELECT COUNT(*) FROM face_embeddings" | tr -d ' ')
WITH_SESSION=$(PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c "SELECT COUNT(*) FROM face_embeddings WHERE session_id IS NOT NULL" | tr -d ' ')
WITHOUT_SESSION=$(PGPASSWORD="${POSTGRES_PASSWORD}" psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -t -c "SELECT COUNT(*) FROM face_embeddings WHERE session_id IS NULL" | tr -d ' ')

echo "  Total embeddings: ${TOTAL_ROWS}"
echo "  With session_id: ${WITH_SESSION}"
echo "  Without session_id (will be deleted): ${WITHOUT_SESSION}"
echo ""

# Confirm backup
read -p "Proceed with backup? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Backup cancelled"
    exit 0
fi

# Create backup
echo "Creating backup..."
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    --table=face_embeddings \
    --data-only \
    --column-inserts \
    > "${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo "✅ Backup created successfully"
    echo "   File: ${BACKUP_FILE}"
    echo "   Size: ${BACKUP_SIZE}"
    echo ""
    echo "To restore from this backup:"
    echo "  psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} < ${BACKUP_FILE}"
else
    echo "❌ Backup failed"
    exit 1
fi

echo ""
echo "========================================="
echo "Backup Complete"
echo "========================================="
