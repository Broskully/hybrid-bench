#!/usr/bin/env bash
set -euo pipefail
RUN="${1:?Usage: run-caliper.sh RUN_NUMBER}"
BASE="$HOME/hybrid-bench"
OUT="$BASE/results/caliper"
mkdir -p "$OUT"
if [ -e "$OUT/report-run$RUN.html" ]; then echo "Run $RUN already exists; not overwriting."; exit 1; fi

echo "=== Run $RUN: started $(date -u +%FT%TZ)"
docker stop pg minio >/dev/null 2>&1 || true

cd "$BASE/fabric-samples/test-network"
{
  ./network.sh down
  ./network.sh up createChannel -c mychannel -s couchdb
  ./network.sh deployCC -ccn hybrid -ccp ../../hybrid-registry -ccl javascript
} 2>&1 | tee "$OUT/network-run$RUN.log" | tail -n 3

SAMPLER=""
trap '[ -n "$SAMPLER" ] && kill "$SAMPLER" 2>/dev/null || true' EXIT
while :; do
  docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.NetIO}},{{.BlockIO}}" | sed "s/^/$(date -u +%FT%TZ),/"
  sleep 5
done > "$OUT/docker-stats-run$RUN.txt" 2>&1 &
SAMPLER=$!

cd "$BASE/caliper-workspace"
npx caliper launch manager \
  --caliper-workspace ./ \
  --caliper-networkconfig networks/networkConfig.yaml \
  --caliper-benchconfig benchmarks/hybrid.yaml \
  --caliper-flow-only-test 2>&1 | tee "$OUT/caliper-run$RUN.log"

mv report.html "$OUT/report-run$RUN.html"
echo "=== Run $RUN: finished $(date -u +%FT%TZ)"
