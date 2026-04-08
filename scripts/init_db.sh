#!/bin/bash
# Run from repo root: bash scripts/init_db.sh
# Prisma now handles migrations automatically on container start.
# This script is kept for manual use / troubleshooting.
DC="docker compose -f infra/docker/docker-compose.yml"

echo "Waiting for database..."
sleep 5

echo "Running Prisma migrations..."
$DC run --rm -e DATABASE_URL="${DATABASE_URL}" backend bunx prisma migrate deploy

echo "Checking if tables were created:"
docker exec -it $($DC ps -q db) psql -U monaa -d monaa_lisa_db -c "\dt"

echo "Done!"
