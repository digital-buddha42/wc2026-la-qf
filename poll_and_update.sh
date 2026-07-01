#!/bin/bash
cd /home/user/wc2026-la-qf
echo "[poll] Starting standings watcher at $(date)"

while true; do
    echo "[poll] Fetching standings at $(date)..."
    python3 - << 'PYEOF'
import json, sys
from fetch_standings import fetch_standings
from pathlib import Path

standings = fetch_standings()
if not standings:
    print("[poll] Fetch failed, will retry.")
    sys.exit(1)

Path("standings_cache.json").write_text(json.dumps(standings, indent=2))

# Check if Group J has updated (Argentina should have 6pts after today's result)
J = standings.get("J", [])
arg = next((t for t in J if t["team"] == "Argentina"), None)
aut = next((t for t in J if t["team"] == "Austria"), None)
if arg and aut:
    print(f"[poll] Group J: Argentina {arg['pts']}pts, Austria {aut['pts']}pts")
    if arg["pts"] >= 6:
        print("[poll] UPDATED — Argentina has 6pts, result is in!")
        sys.exit(0)
    else:
        print("[poll] Not updated yet.")
        sys.exit(1)
PYEOF

    STATUS=$?
    if [ $STATUS -eq 0 ]; then
        echo "[poll] Standings updated! Re-running simulation..."
        python main.py --no-fetch > sim_output.txt 2>/dev/null
        python bracket_graphic.py 2>/dev/null
        git add standings_cache.json bracket_prediction.png sim_output.txt
        git commit -m "Auto-update: standings refreshed after Argentina 2-0 Austria (matchday 2)"
        git push -u origin claude/nifty-cerf-ptu7qd
        echo "[poll] Done! Results pushed to PR."
        break
    fi

    echo "[poll] Sleeping 30 minutes..."
    sleep 1800
done
