"""
Fetches live 2026 World Cup group standings.

Tries ESPN → Sofascore proxy → seed file fallback.
Returns {group_letter: [team_dict, ...]} sorted by standing position.
"""

import json
import sys
import re
from pathlib import Path
import requests

SEED_FILE = Path(__file__).parent / "seed_standings.json"
CACHE_FILE = Path(__file__).parent / "standings_cache.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

# ESPN endpoints to try (different formats)
ESPN_URLS = [
    "https://site.api.espn.com/apis/v2/sports/soccer/fifa.world/standings?season=2026&type=0",
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/standings?season=2026",
    "https://site.web.api.espn.com/apis/v2/sports/soccer/fifa.world/standings?season=2026",
]


def _parse_espn_response(data: dict) -> dict:
    groups = {}
    for group_node in data.get("children", []):
        group_name = group_node.get("name", "")
        letter = group_name.replace("Group ", "").strip()
        if not letter or len(letter) != 1:
            continue

        entries = []
        standings_data = group_node.get("standings", {})
        for entry in standings_data.get("entries", []):
            team = entry.get("team", {})
            stats = {s["name"]: s.get("value", 0) for s in entry.get("stats", [])}

            entries.append({
                "team":   team.get("displayName", "?"),
                "abbr":   team.get("abbreviation", "?"),
                "played": int(stats.get("gamesPlayed", 0)),
                "won":    int(stats.get("wins", 0)),
                "drawn":  int(stats.get("ties", 0)),
                "lost":   int(stats.get("losses", 0)),
                "gf":     int(stats.get("pointsFor", 0)),
                "ga":     int(stats.get("pointsAgainst", 0)),
                "gd":     int(stats.get("pointsDifference", 0)),
                "pts":    int(stats.get("points", 0)),
                "rank":   int(entry.get("sortOrder", 99)),
            })

        entries.sort(key=lambda x: x["rank"])
        groups[letter] = entries

    return groups


def _try_espn() -> dict:
    for url in ESPN_URLS:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                groups = _parse_espn_response(data)
                if groups:
                    print(f"[fetch] ESPN OK ({url})", file=sys.stderr)
                    return groups
        except Exception as e:
            print(f"[fetch] ESPN attempt failed: {e}", file=sys.stderr)
    return {}


def _load_seed() -> dict:
    if SEED_FILE.exists():
        with open(SEED_FILE) as f:
            data = json.load(f)
        # Strip metadata keys
        return {k: v for k, v in data.items() if not k.startswith("_")}
    return {}


def fetch_standings() -> dict:
    """Try live API first, fall back to cache, then seed."""
    standings = _try_espn()
    if standings:
        return standings

    # Try cache
    if CACHE_FILE.exists():
        print("[fetch] Using cache (API unavailable).", file=sys.stderr)
        with open(CACHE_FILE) as f:
            return json.load(f)

    # Fall back to seed
    print("[fetch] Using seed standings (no API, no cache).", file=sys.stderr)
    return _load_seed()


if __name__ == "__main__":
    standings = fetch_standings()
    if standings:
        print(json.dumps(standings, indent=2))
    else:
        print("No standings data available.")
