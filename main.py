#!/usr/bin/env python3
"""
LA QF Predictor — run daily for updated World Cup quarterfinal probabilities.

Usage:
    python main.py              # fetch live data + simulate
    python main.py --no-fetch   # use cached standings (standings_cache.json)
    python main.py --trials N   # override simulation count (default 50,000)
"""

import argparse
import json
import sys
import time
from pathlib import Path

from fetch_standings import fetch_standings
from simulate import run_simulation, N_TRIALS
from display import render

CACHE_FILE = Path(__file__).parent / "standings_cache.json"


def main():
    parser = argparse.ArgumentParser(description="2026 WC LA QF Probability Predictor")
    parser.add_argument("--no-fetch", action="store_true",
                        help="Skip API call, use cached standings")
    parser.add_argument("--trials", type=int, default=N_TRIALS,
                        help=f"Number of Monte Carlo trials (default {N_TRIALS})")
    args = parser.parse_args()

    # --- Fetch or load standings ---
    if args.no_fetch and CACHE_FILE.exists():
        print("[cache] Using cached standings...", file=sys.stderr)
        with open(CACHE_FILE) as f:
            standings = json.load(f)
    else:
        print("[fetch] Fetching live standings from ESPN...", file=sys.stderr)
        standings = fetch_standings()
        if standings:
            CACHE_FILE.write_text(json.dumps(standings, indent=2))
            print(f"[fetch] Got {len(standings)} groups. Cached to {CACHE_FILE.name}",
                  file=sys.stderr)
        elif CACHE_FILE.exists():
            print("[fetch] API unavailable — falling back to cache.", file=sys.stderr)
            with open(CACHE_FILE) as f:
                standings = json.load(f)
        else:
            print("[fetch] No data available. Cannot simulate.", file=sys.stderr)
            sys.exit(1)

    if not standings:
        print("[error] Empty standings — cannot simulate.", file=sys.stderr)
        sys.exit(1)

    # --- Run simulation ---
    n = args.trials
    print(f"[sim] Running {n:,} Monte Carlo trials...", file=sys.stderr)
    t0 = time.time()

    # Monkey-patch trial count if overridden
    import simulate as sim_module
    sim_module.N_TRIALS = n

    probs = run_simulation(standings)
    elapsed = time.time() - t0
    print(f"[sim] Done in {elapsed:.1f}s. {len(probs)} teams tracked.", file=sys.stderr)

    # --- Display ---
    render(probs, standings, top_n=20)


if __name__ == "__main__":
    main()
