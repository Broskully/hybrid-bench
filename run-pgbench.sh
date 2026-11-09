#!/bin/bash
# Records pgbench: 1, 10 and 50 clients, five runs each, 60 s per run.
OUT="$HOME/hybrid-bench/results/pgbench"
if ls "$OUT"/pgbench-c*-run*.txt >/dev/null 2>&1; then
  echo "Stopped: pgbench results already exist in $OUT"; exit 1
fi
mkdir -p "$OUT"
cd "$HOME/hybrid-bench/fabric-samples/test-network" || exit 1
./network.sh down >/dev/null 2>&1
docker stop minio >/dev/null 2>&1
docker start pg >/dev/null || exit 1
until docker exec pg pg_isready -U postgres -q; do sleep 1; done
docker exec pg test -f /register.sql || { echo "Stopped: /register.sql is missing"; exit 1; }
docker ps --format '{{.Names}}' > "$OUT/containers-during-runs.txt"
for run in 1 2 3 4 5; do
  for c in 1 10 50; do
    FILE="$OUT/pgbench-c$c-run$run.txt"
    CMD="docker exec pg pgbench -U postgres -n -f /register.sql -c $c -T 60 postgres"
    docker exec pg psql -q -U postgres -c "truncate records, events restart identity" || exit 1
    { echo "\$ $CMD  # $(date -u +%FT%TZ)"; $CMD; } 2>&1 | tee "$FILE"
    if ! grep -q '^tps = ' "$FILE" || grep -q 'aborted' "$FILE"; then
      echo "Stopped: bad result in $FILE"; exit 1
    fi
  done
done
echo "=== pgbench: finished"
