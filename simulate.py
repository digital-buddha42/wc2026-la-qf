"""
Monte Carlo simulation of 2026 World Cup bracket path to the LA Quarterfinal.

Approach:
  1. Estimate each team's win probability per match using a simple Elo-style
     rating derived from current group standings (pts, gd, gf).
  2. Simulate the remaining group stage + third-place qualification + R32 + R16.
  3. Count how often each team appears in the LA QF across N trials.

Win probability model (Bradley-Terry):
  P(A beats B) = rating_A / (rating_A + rating_B)

Rating = exp(0.1 * pts + 0.02 * gd + 0.01 * gf)  — simple but sensible.
"""

import math
import random
from collections import defaultdict
from typing import Dict, List, Tuple

from bracket import BRACKET, THIRD_PLACE_POOLS, ALL_GROUPS

N_TRIALS = 50_000


def team_rating(team: dict) -> float:
    pts = team.get("pts", 0)
    gd  = team.get("gd", 0)
    gf  = team.get("gf", 0)
    return math.exp(0.10 * pts + 0.02 * gd + 0.005 * gf)


def win_prob(a: dict, b: dict) -> float:
    ra, rb = team_rating(a), team_rating(b)
    return ra / (ra + rb)


def simulate_match(a: dict, b: dict) -> dict:
    return a if random.random() < win_prob(a, b) else b


def simulate_group(teams: List[dict]) -> Tuple[dict, dict, dict, dict]:
    """
    Simulate all 6 remaining (or unplayed) matches in a 4-team group.
    Returns (1st, 2nd, 3rd, 4th) sorted by simulated final standings.
    """
    # Clone mutable state
    sim = [{**t, "sim_pts": t["pts"], "sim_gd": t["gd"], "sim_gf": t["gf"]}
           for t in teams]

    # Figure out which matches are left (teams that haven't played each other yet).
    # Simple heuristic: if team played < 3 games, they have matches remaining.
    # Full round-robin for simplicity in simulation (over-estimate variance slightly).
    played = {t["team"]: t["played"] for t in sim}
    max_games = 3
    # pairs not yet played: approximate by played count
    pairs = [(i, j) for i in range(4) for j in range(i + 1, 4)]
    # Each team plays 3 games; 6 total in group. If all played 2, 1 matchday left.
    games_left = max_games - min(played.values()) if played else 3

    # Simulate remaining matchdays
    if games_left > 0:
        # Just simulate all remaining unique pairs proportional to games left
        # This is approximate but good enough for probability estimation
        for i, j in pairs:
            # Skip if both teams likely already played (heuristic)
            avg_played = (sim[i]["played"] + sim[j]["played"]) / 2
            if avg_played >= max_games:
                continue
            winner_idx = i if random.random() < win_prob(sim[i], sim[j]) else j
            loser_idx  = j if winner_idx == i else i
            # 1-goal margin assumption for GD sim
            margin = random.randint(1, 3)
            sim[winner_idx]["sim_pts"] += 3
            sim[winner_idx]["sim_gd"]  += margin
            sim[winner_idx]["sim_gf"]  += margin
            sim[loser_idx]["sim_gd"]   -= margin

    sim.sort(key=lambda t: (-t["sim_pts"], -t["sim_gd"], -t["sim_gf"]))
    return tuple(sim)


def pick_best_third(thirds: List[dict]) -> dict:
    """Pick the best third-place team from a pool using pts/gd/gf."""
    return max(thirds, key=lambda t: (t.get("sim_pts", t["pts"]),
                                       t.get("sim_gd", t["gd"]),
                                       t.get("sim_gf", t["gf"])))


def run_simulation(standings: Dict[str, List[dict]]) -> Dict[str, float]:
    """
    Run N_TRIALS simulations.
    Returns {team_name: probability_of_appearing_in_LA_QF}
    """
    qf_counts: Dict[str, int] = defaultdict(int)

    for _ in range(N_TRIALS):
        # 1. Simulate all group finishes
        group_results = {}       # letter → (1st, 2nd, 3rd, 4th)
        all_thirds = []

        for letter in ALL_GROUPS:
            teams = standings.get(letter, [])
            if len(teams) < 4:
                # Group not available — skip (won't affect LA path analysis)
                group_results[letter] = teams[:4] if teams else []
                continue
            result = simulate_group(teams)
            group_results[letter] = result
            third = result[2]
            all_thirds.append({**third, "_group": letter})

        # 2. Determine best 3rd-place qualifiers for R32 third-place slots
        # Sort all thirds and take top 8
        all_thirds.sort(key=lambda t: (-t.get("sim_pts", t["pts"]),
                                        -t.get("sim_gd", t["gd"]),
                                        -t.get("sim_gf", t["gf"])))
        qualifying_thirds = all_thirds[:8]
        thirds_by_group = {t["_group"]: t for t in qualifying_thirds}

        def get_slot(pos: str, group: str) -> dict | None:
            """Resolve a bracket slot to a team dict."""
            grp = group_results.get(group, [])
            if not grp:
                return None
            if pos == "1":
                return grp[0] if len(grp) > 0 else None
            if pos == "2":
                return grp[1] if len(grp) > 1 else None
            if pos == "3rd":
                # pick best 3rd from the specified pool that qualified
                pool = list(group)  # group is actually a string of group letters
                candidates = [thirds_by_group[g] for g in pool if g in thirds_by_group]
                return pick_best_third(candidates) if candidates else None
            return None

        def sim_r32(node: dict) -> dict | None:
            sa = node["slot_a"]
            sb = node["slot_b"]
            team_a = get_slot(sa[0], sa[1])
            team_b = get_slot(sb[0], sb[1])
            if not team_a or not team_b:
                return team_a or team_b
            return simulate_match(team_a, team_b)

        # 3. Simulate the LA QF bracket path
        la = BRACKET["qf_la"]

        # R32 matches
        r16_a_node = la["r16_a"]
        r16_b_node = la["r16_b"]

        w_r32_83 = sim_r32(r16_a_node["r32_a"])
        w_r32_84 = sim_r32(r16_a_node["r32_b"])
        w_r32_81 = sim_r32(r16_b_node["r32_a"])
        w_r32_82 = sim_r32(r16_b_node["r32_b"])

        # R16 matches
        if w_r32_83 and w_r32_84:
            w_r16_93 = simulate_match(w_r32_83, w_r32_84)
        else:
            w_r16_93 = w_r32_83 or w_r32_84

        if w_r32_81 and w_r32_82:
            w_r16_94 = simulate_match(w_r32_81, w_r32_82)
        else:
            w_r16_94 = w_r32_81 or w_r32_82

        # LA QF participants
        if w_r16_93:
            qf_counts[w_r16_93["team"]] += 1
        if w_r16_94:
            qf_counts[w_r16_94["team"]] += 1

    # Convert to probabilities (each trial produces 2 QF teams → 2*N total slots)
    total_slots = 2 * N_TRIALS
    return {team: count / total_slots for team, count in sorted(
        qf_counts.items(), key=lambda x: -x[1]
    )}
