"""
Monte Carlo simulation of 2026 World Cup bracket path to the LA Quarterfinal.

Approach:
  1. Estimate each team's win probability using a BLENDED rating:
       - Pre-tournament Elo (captures true team quality: Argentina >> USA)
       - Live tournament performance (pts, gd, gf) — grows in weight as games played
     Blend: rating = elo_base * tournament_boost, where tournament_boost starts
     near 1.0 and diverges as results come in.
  2. Simulate remaining group stage + 3rd-place qualification + R32 + R16.
  3. Count how often each team appears in the LA QF across N trials.

Win probability model (Bradley-Terry):
  P(A beats B) = rating_A / (rating_A + rating_B)
"""

import math
import random
from collections import defaultdict
from typing import Dict, List, Tuple

from bracket import BRACKET, THIRD_PLACE_POOLS, ALL_GROUPS, R32_ACTUAL_OPPONENTS, COMPLETED_RESULTS

N_TRIALS = 50_000

# Pre-tournament Elo ratings (eloratings.net, ~June 2026).
# Unlisted teams get ELO_DEFAULT. Values are approximate but directionally correct.
ELO_DEFAULT = 1650
PRE_TOURNAMENT_ELO: dict[str, float] = {
    # Elite tier
    "Spain":              2129,
    "Argentina":          2115,
    "France":             2063,
    "England":            2042,
    "Germany":            2020,
    "Portugal":           1989,
    "Colombia":           1982,
    "Brazil":             1979,
    "Netherlands":        1959,
    "Norway":             1930,
    "Austria":            1920,
    "Croatia":            1933,
    "Morocco":            1910,
    "Ecuador":            1905,
    # Strong tier
    "Belgium":            1895,
    "Uruguay":            1890,
    "Mexico":             1880,
    "Türkiye":            1875,
    "Sweden":             1870,
    "Senegal":            1865,
    "United States":      1855,
    "South Korea":        1840,
    "Japan":              1840,
    "Switzerland":        1835,
    "Canada":             1820,
    "Australia":          1800,
    "Denmark":            1800,
    # Mid tier
    "Ghana":              1770,
    "Tunisia":            1760,
    "Egypt":              1755,
    "Paraguay":           1750,
    "Iran":               1745,
    "Scotland":           1740,
    "Algeria":            1720,
    "Ivory Coast":        1715,
    "Czechia":            1710,
    "DR Congo":           1700,
    "Saudi Arabia":       1690,
    "Costa Rica":         1675,
    # Lower tier
    "South Africa":       1660,
    "Uzbekistan":         1640,
    "Bosnia and Herzegovina": 1635,
    "Iraq":               1630,
    "Cape Verde":         1625,
    "Haiti":              1590,
    "Jordan":             1580,
    "New Zealand":        1575,
    "Panama":             1570,
    "Curaçao":            1520,
    "Qatar":              1510,
}

# How strongly tournament results update the prior.
# After 3 matches the tournament signal dominates; at 0 games we rely on Elo.
# tournament_weight(played) goes 0→1 over 3 games.
def _tournament_weight(played: int) -> float:
    return min(played / 3.0, 1.0) * 0.6   # max 60% tournament, 40% Elo always


def team_rating(team: dict) -> float:
    name   = team.get("team", "?")
    played = team.get("played", 0)
    pts    = team.get("pts", 0)
    gd     = team.get("sim_gd", team.get("gd", 0))
    gf     = team.get("sim_gf", team.get("gf", 0))

    elo = PRE_TOURNAMENT_ELO.get(name, ELO_DEFAULT)
    # Normalise Elo to same rough scale as tournament signal
    elo_component = elo / 1800.0   # ~1.0 for an average team

    tw = _tournament_weight(played)
    tournament_signal = math.exp(0.15 * pts + 0.03 * gd + 0.005 * gf)

    # Blend: pure Elo when played=0, shifting toward results as games accumulate
    return elo_component * (1 - tw) + tournament_signal * tw


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


def run_simulation(standings: Dict[str, List[dict]]) -> tuple[Dict[str, float], Dict[tuple, float], Dict[str, Dict[str, float]]]:
    """
    Run N_TRIALS simulations.
    Returns:
      - {team_name: probability_of_appearing_in_LA_QF}
      - {(team_a, team_b): probability_of_this_exact_matchup}  (teams sorted alphabetically)
      - {stage_name: {team_name: probability_of_winning_that_stage}}
    """
    qf_counts: Dict[str, int] = defaultdict(int)
    matchup_counts: Dict[tuple, int] = defaultdict(int)
    stage_counts: Dict[str, Dict[str, int]] = {
        "R32-81 (SF, Jul 1)":   defaultdict(int),
        "R32-82 (SEA, Jul 2)":  defaultdict(int),
        "R32-83 (TOR, Jun 29)": defaultdict(int),
        "R32-84 (LA, Jul 2)":   defaultdict(int),
        "R16-94 (SEA, Jul 7)":  defaultdict(int),
        "R16-93 (ARL, Jul 6)":  defaultdict(int),
    }

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
            if pos == "team":
                # confirmed opponent (group is actually the team name)
                return R32_ACTUAL_OPPONENTS.get(group)
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
            # Force the actual winner if this match has already been played.
            match_id = node["match"].split()[0]
            if match_id in COMPLETED_RESULTS:
                winner = COMPLETED_RESULTS[match_id]
                for t in (team_a, team_b):
                    if t and t["team"] == winner:
                        return t
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

        if w_r32_81: stage_counts["R32-81 (SF, Jul 1)"][w_r32_81["team"]] += 1
        if w_r32_82: stage_counts["R32-82 (SEA, Jul 2)"][w_r32_82["team"]] += 1
        if w_r32_83: stage_counts["R32-83 (TOR, Jun 29)"][w_r32_83["team"]] += 1
        if w_r32_84: stage_counts["R32-84 (LA, Jul 2)"][w_r32_84["team"]] += 1

        # R16 matches
        if w_r32_83 and w_r32_84:
            w_r16_93 = simulate_match(w_r32_83, w_r32_84)
        else:
            w_r16_93 = w_r32_83 or w_r32_84

        if w_r32_81 and w_r32_82:
            w_r16_94 = simulate_match(w_r32_81, w_r32_82)
        else:
            w_r16_94 = w_r32_81 or w_r32_82

        if w_r16_93: stage_counts["R16-93 (ARL, Jul 6)"][w_r16_93["team"]] += 1
        if w_r16_94: stage_counts["R16-94 (SEA, Jul 7)"][w_r16_94["team"]] += 1

        # LA QF participants
        if w_r16_93:
            qf_counts[w_r16_93["team"]] += 1
        if w_r16_94:
            qf_counts[w_r16_94["team"]] += 1
        if w_r16_93 and w_r16_94:
            pair = tuple(sorted([w_r16_93["team"], w_r16_94["team"]]))
            matchup_counts[pair] += 1

    total_slots = 2 * N_TRIALS
    probs = {team: count / total_slots for team, count in sorted(
        qf_counts.items(), key=lambda x: -x[1]
    )}
    matchup_probs = {pair: count / N_TRIALS for pair, count in sorted(
        matchup_counts.items(), key=lambda x: -x[1]
    )}
    stage_probs = {
        stage: {team: cnt / N_TRIALS for team, cnt in sorted(counts.items(), key=lambda x: -x[1])}
        for stage, counts in stage_counts.items()
    }
    return probs, matchup_probs, stage_probs
