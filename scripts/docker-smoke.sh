#!/usr/bin/env bash
set -euo pipefail
image=${1:-entry-strategy:local}
volume="entry-strategy-smoke-$RANDOM"
container="entry-strategy-smoke-$RANDOM"
cleanup() { docker rm -f "$container" >/dev/null 2>&1 || true; docker volume rm "$volume" >/dev/null 2>&1 || true; }
trap cleanup EXIT
docker volume create "$volume" >/dev/null
docker run -d --name "$container" -p 127.0.0.1::8080 -e ENTRY_STRATEGY_TOKEN=smoke -v "$volume:/data" "$image" >/dev/null
port=$(docker port "$container" 8080/tcp | awk -F: '{print $NF}')
python - "$port" <<'PY'
import json,sys,time,urllib.error,urllib.request
port=sys.argv[1]; base=f"http://127.0.0.1:{port}"
for _ in range(30):
    try:
        assert json.load(urllib.request.urlopen(base+"/health"))["status"]=="ok";break
    except Exception: time.sleep(.2)
else: raise SystemExit("health endpoint unavailable")
try: urllib.request.urlopen(base+"/sessions/missing/next")
except urllib.error.HTTPError as exc: assert exc.code==401
request=urllib.request.Request(base+"/sessions",data=json.dumps({"ticker":"ACME","mode":"standalone_runtime"}).encode(),headers={"Authorization":"Bearer smoke","Content-Type":"application/json"},method="POST")
session=json.load(urllib.request.urlopen(request)); sid=session["session_id"]
artifact=json.dumps({"phase_identity":"initial-1"}).encode()
request=urllib.request.Request(base+f"/sessions/{sid}/phases/initial-1",data=artifact,headers={"Authorization":"Bearer smoke","Content-Type":"application/json"},method="POST")
assert json.load(urllib.request.urlopen(request))["readback_verified"]
open("/tmp/entry-strategy-smoke-session","w").write(sid)
PY
sid=$(cat /tmp/entry-strategy-smoke-session)
test "$(docker inspect -f '{{.Config.User}}' "$container")" = "app"
docker rm -f "$container" >/dev/null
docker run -d --name "$container" -p 127.0.0.1::8080 -e ENTRY_STRATEGY_TOKEN=smoke -v "$volume:/data" "$image" >/dev/null
port=$(docker port "$container" 8080/tcp | awk -F: '{print $NF}')
python - "$port" "$sid" <<'PY'
import json,sys,time,urllib.request
port,sid=sys.argv[1:]; url=f"http://127.0.0.1:{port}/sessions/{sid}/integrity"
request=urllib.request.Request(url,headers={"Authorization":"Bearer smoke"})
for _ in range(30):
    try:
        assert json.load(urllib.request.urlopen(request))["integrity_verified"];break
    except Exception: time.sleep(.2)
else: raise SystemExit("persistent restart verification failed")
PY
echo "docker smoke passed: nonroot, health, auth, persistence, restart integrity"
