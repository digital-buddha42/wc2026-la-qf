#!/usr/bin/env python3
"""
One-off deep dive: for the LA QF bracket, compute per-group finish probabilities,
who fills each R32 slot, R32/R16 match win probabilities, city routing, and the
most likely QF matchups. Reuses simulate.py machinery.
"""
import json
from collections import defaultdict
from pathlib import Path

import simulate as S
from bracket import BRACKET, ALL_GROUPS

N = 60_000
S.N_TRIALS = N

standings = json.loads((Path(__file__).parent / "standings_cache.json").read_text())

# Trackers
group_finish = {g: defaultdict(lambda: [0, 0, 0, 0]) for g in ALL_GROUPS}  # team -> [1st,2nd,3rd,4th]
slot_fill = defaultdict(lambda: defaultdict(int))   # slot_name -> team -> count
r32_winner = defaultdict(lambda: defaultdict(int))  # match -> team -> count
r16_winner = defaultdict(lambda: defaultdict(int))
qf_matchup = defaultdict(int)

import random

for _ in range(N):
    group_results = {}
    all_thirds = []
    for letter in ALL_GROUPS:
        teams = standings.get(letter, [])
        if len(teams) < 4:
            group_results[letter] = teams[:4] if teams else []
            continue
        result = S.simulate_group(teams)
        group_results[letter] = result
        for pos, t in enumerate(result):
            group_finish[letter][t["team"]][pos] += 1
        all_thirds.append({**result[2], "_group": letter})

    all_thirds.sort(key=lambda t: (-t.get("sim_pts", t["pts"]),
                                    -t.get("sim_gd", t["gd"]),
                                    -t.get("sim_gf", t["gf"])))
    thirds_by_group = {t["_group"]: t for t in all_thirds[:8]}

    def get_slot(pos, group):
        if pos == "team":
            return S.R32_ACTUAL_OPPONENTS.get(group)
        grp = group_results.get(group, [])
        if not grp:
            return None
        if pos == "1":
            return grp[0] if len(grp) > 0 else None
        if pos == "2":
            return grp[1] if len(grp) > 1 else None
        if pos == "3rd":
            cands = [thirds_by_group[g] for g in list(group) if g in thirds_by_group]
            return S.pick_best_third(cands) if cands else None
        return None

    def sim_r32(node):
        sa, sb = node["slot_a"], node["slot_b"]
        ta, tb = get_slot(*sa), get_slot(*sb)
        if not ta or not tb:
            return ta or tb
        return S.simulate_match(ta, tb)

    la = BRACKET["qf_la"]
    a, b = la["r16_a"], la["r16_b"]

    # record slot fills
    for node, name in [(a["r32_a"], "R32-83"), (a["r32_b"], "R32-84"),
                       (b["r32_a"], "R32-81"), (b["r32_b"], "R32-82")]:
        for slot in ("slot_a", "slot_b"):
            t = get_slot(*node[slot])
            if t:
                key = f"{name}:{node[slot][0]}{node[slot][1]}"
                slot_fill[key][t["team"]] += 1

    w83 = sim_r32(a["r32_a"]); w84 = sim_r32(a["r32_b"])
    w81 = sim_r32(b["r32_a"]); w82 = sim_r32(b["r32_b"])
    for w, n in [(w83, "R32-83"), (w84, "R32-84"), (w81, "R32-81"), (w82, "R32-82")]:
        if w: r32_winner[n][w["team"]] += 1

    w93 = S.simulate_match(w83, w84) if (w83 and w84) else (w83 or w84)
    w94 = S.simulate_match(w81, w82) if (w81 and w82) else (w81 or w82)
    if w93: r16_winner["R16-93"][w93["team"]] += 1
    if w94: r16_winner["R16-94"][w94["team"]] += 1
    if w93 and w94:
        qf_matchup[tuple(sorted([w93["team"], w94["team"]]))] += 1


def top(d, k=4):
    return sorted(d.items(), key=lambda x: -x[1])[:k]

print("=" * 70)
print("DEEP DIVE — LA QF BRACKET (SoFi Stadium, July 10, 2026)")
print(f"{N:,} Monte Carlo trials")
print("=" * 70)

LA_GROUPS = ["D", "G", "H", "J", "K", "L"]
print("\n### GROUP FINISH PROBABILITIES (LA-relevant groups) ###")
for g in LA_GROUPS:
    print(f"\nGroup {g}:")
    rows = []
    for team, counts in group_finish[g].items():
        rows.append((team, counts[0]/N, counts[1]/N, counts[2]/N))
    rows.sort(key=lambda r: -(r[1] + r[2]))
    print(f"  {'Team':<22}{'1st':>7}{'2nd':>7}{'3rd':>7}")
    for team, p1, p2, p3 in rows:
        print(f"  {team:<22}{p1*100:6.1f}%{p2*100:6.1f}%{p3*100:6.1f}%")

print("\n\n### R32 SLOT FILLERS & MATCH WINNERS ###")
CITY = {"R32-83": "Toronto (Jun 29)", "R32-84": "Los Angeles (Jul 2)",
        "R32-81": "San Francisco (Jul 1)", "R32-82": "Seattle (Jul 2)"}
SLOTS = {"R32-83": "2K vs 2L", "R32-84": "1H vs 2J",
         "R32-81": "1D vs best-3rd(BEFIJ)", "R32-82": "1G vs best-3rd(AEHIJ)"}
for m in ["R32-83", "R32-84", "R32-81", "R32-82"]:
    print(f"\n{m} — {SLOTS[m]} @ {CITY[m]}")
    fills = [k for k in slot_fill if k.startswith(m)]
    for fk in fills:
        label = fk.split(":")[1]
        print(f"  Slot {label}: " + ", ".join(f"{t} {c/N*100:.0f}%" for t, c in top(slot_fill[fk], 3)))
    print(f"  WINNER: " + ", ".join(f"{t} {c/N*100:.1f}%" for t, c in top(r32_winner[m], 4)))

print("\n\n### R16 MATCH WINNERS ###")
print("R16-93 (Arlington, Jul 6) = W(R32-83) vs W(R32-84):")
for t, c in top(r16_winner["R16-93"], 6):
    print(f"  {t:<22}{c/N*100:5.1f}%")
print("R16-94 (Seattle, Jul 7) = W(R32-81) vs W(R32-82):")
for t, c in top(r16_winner["R16-94"], 6):
    print(f"  {t:<22}{c/N*100:5.1f}%")

print("\n\n### MOST LIKELY LA QF MATCHUPS (Jul 10) ###")
for (a_, b_), c in sorted(qf_matchup.items(), key=lambda x: -x[1])[:12]:
    print(f"  {a_:<18} vs {b_:<18} {c/N*100:5.2f}%")
