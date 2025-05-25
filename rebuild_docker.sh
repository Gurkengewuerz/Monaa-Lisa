#!/bin/bash

echo "Cleaning up..."
docker-compose down -v

echo "Building images..."
docker-compose build

echo "Starting database..."
docker-compose up -d db

echo "Initializing database..."
./init_db.sh
echo "Starting app..."
docker-compose up -d app

echo "All done! Your application is running."