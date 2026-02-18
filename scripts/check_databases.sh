#!/bin/bash

# Скрипт для проверки структуры баз данных FacePass

echo "============================================================"
echo "FacePass Database Structure Check"
echo "============================================================"

echo ""
echo "1. Checking Main Database (fecapass_main)..."
echo "------------------------------------------------------------"
docker-compose exec -T db_main psql -U fecapass_user -d fecapass_main -c "\dt" 2>/dev/null || echo "❌ Main database not accessible"

echo ""
echo "2. Checking Vector Database (facepass_vector)..."
echo "------------------------------------------------------------"
docker-compose exec -T db_vector psql -U fecapass_user -d facepass_vector -c "\dt" 2>/dev/null || echo "❌ Vector database not accessible"

echo ""
echo "3. Checking pgvector extension..."
echo "------------------------------------------------------------"
docker-compose exec -T db_vector psql -U fecapass_user -d facepass_vector -c "\dx vector" 2>/dev/null || echo "❌ pgvector extension not found"

echo ""
echo "4. Checking face_embeddings structure..."
echo "------------------------------------------------------------"
docker-compose exec -T db_vector psql -U fecapass_user -d facepass_vector -c "\d face_embeddings" 2>/dev/null || echo "❌ face_embeddings table not found"

echo ""
echo "============================================================"
echo "Check complete!"
echo "============================================================"
