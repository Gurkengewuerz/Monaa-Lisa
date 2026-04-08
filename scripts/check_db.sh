#!/bin/bash
# Run from repo root: bash scripts/check_db.sh
DC="docker compose -f infra/docker/docker-compose.yml"

echo "Checking database tables:"
docker exec -it $($DC ps -q db) psql -U monaa -d monaa_lisa_db -c "\dt"
echo ""

echo "Number of papers in database:"
docker exec -it $($DC ps -q db) psql -U monaa -d monaa_lisa_db -c "SELECT count(*) FROM papers;"
echo ""

echo "All papers in database:"
docker exec -it $($DC ps -q db) psql -U monaa -d monaa_lisa_db -c "SELECT id, entry_id, title, hash FROM papers;"
echo ""

echo "Full paper details (including summaries):"
docker exec -it $($DC ps -q db) psql -U monaa -d monaa_lisa_db -c "SELECT * FROM papers;"

echo "Done!"
