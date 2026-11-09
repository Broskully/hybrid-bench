#!/bin/bash
# Records e2e timing: PostgreSQL first, then Fabric. 200 registrations per size.
OUT="$HOME/hybrid-bench/results/e2e"
E2E="$HOME/hybrid-bench/e2e"
NET="$HOME/hybrid-bench/fabric-samples/test-network"
mkdir -p "$OUT"
if ls "$OUT"/e2e-*.csv "$E2E"/e2e-*.csv >/dev/null 2>&1; then
  echo "Stopped: e2e CSV files already exist"; exit 1
fi
cd "$NET" || exit 1
./network.sh down >/dev/null 2>&1
docker start minio >/dev/null || exit 1
until curl -sf http://localhost:9000/minio/health/live >/dev/null; do sleep 1; done
docker start pg >/dev/null || exit 1
until docker exec pg pg_isready -U postgres -q; do sleep 1; done
docker exec pg psql -q -U postgres -c "truncate records, events restart identity" || exit 1
docker ps --format '{{.Names}}' > "$OUT/containers-postgres.txt"
cd "$E2E" || exit 1
echo "=== postgres: started $(date -u +%FT%TZ)"
node e2e.js postgres || { echo "Stopped: postgres run failed"; exit 1; }
mv e2e-postgres-*.csv "$OUT"/
echo "=== postgres: finished $(date -u +%FT%TZ)"
docker stop pg >/dev/null
cd "$NET" || exit 1
./network.sh up createChannel -c mychannel -s couchdb > "$OUT/network-e2e.log" 2>&1 || { echo "Stopped: network failed"; exit 1; }
./network.sh deployCC -ccn hybrid -ccp ../../hybrid-registry -ccl javascript >> "$OUT/network-e2e.log" 2>&1 || { echo "Stopped: deploy failed"; exit 1; }
docker ps --format '{{.Names}}' > "$OUT/containers-fabric.txt"
cd "$E2E" || exit 1
echo "=== fabric: started $(date -u +%FT%TZ)"
node e2e.js fabric || { echo "Stopped: fabric run failed"; exit 1; }
mv e2e-fabric-*.csv "$OUT"/
echo "=== fabric: finished $(date -u +%FT%TZ)"
echo "=== e2e: finished"
