#!/bin/bash

echo "💥 Resetting everything to start fresh..."

echo "📦 Stopping and removing all containers..."
docker-compose down -v

echo "🧹 Cleaning Docker caches..."
docker system prune -f

echo "📄 Removing hash files..."
rm -f MonaaLisa/src/parsed_hashes.txt
rm -f parsed_hashes.txt

echo "🏗️ Rebuilding Docker images..."
docker-compose build

echo "🐘 Starting PostgreSQL database..."
docker-compose up -d db
echo "⏳ Waiting for database to be ready (10s)..."
sleep 10

echo "🔧 Creating database tables..."
docker-compose run --rm -e PYTHONPATH=/app/MonaaLisa/src app python MonaaLisa/src/Database/db.py

echo "🔍 Verifying database tables:"
docker exec -it $(docker-compose ps -q db) psql -U monaa -d monaa_lisa -c "\dt"

echo "🚀 Starting the application..."
docker-compose up -d app

echo "📋 Showing application logs (press Ctrl+C to exit)..."
echo "The app will start fetching and processing papers..."
docker-compose logs -f app