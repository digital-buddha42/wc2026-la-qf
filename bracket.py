"""
2026 World Cup bracket structure for the LA Quarterfinal (SoFi Stadium, July 10).

Bracket path (all groups → LA QF):

  R32 Match 83: 2K vs 2L  (Toronto, June 29)
  R32 Match 84: 1H vs 2J  (Los Angeles, July 2)
    → R16 Match 93: W83 vs W84  (Arlington, July 6)

  R32 Match 81: 1D vs best-3rd(B/E/F/I/J)  (San Francisco, July 1)
  R32 Match 82: 1G vs best-3rd(A/E/H/I/J)  (Seattle, July 2)
    → R16 Match 94: W81 vs W82  (Seattle, July 7)

  QF (LA, July 10): W93 vs W94
"""

# Groups that feed into the LA QF — mapping to their teams (populated from API)
# Each key is a group letter; value will be filled by fetch_standings.py
LA_QF_GROUPS = ["D", "G", "H", "J", "K", "L"]

# Full bracket dependency tree for the LA QF
BRACKET = {
    "qf_la": {
        "match": "QF (LA, July 10)",
        "r16_a": {
            "match": "R16-93 (Arlington, July 6)",
            "r32_a": {
                "match": "R32-83 (Toronto, June 29)",
                "slot_a": ("2", "K"),   # runner-up of Group K
                "slot_b": ("2", "L"),   # runner-up of Group L
            },
            "r32_b": {
                "match": "R32-84 (Los Angeles, July 2)",
                "slot_a": ("1", "H"),   # winner of Group H
                "slot_b": ("2", "J"),   # runner-up of Group J
            },
        },
        "r16_b": {
            "match": "R16-94 (Seattle, July 7)",
            "r32_a": {
                "match": "R32-81 (San Francisco, July 1)",
                "slot_a": ("1", "D"),   # winner of Group D
                "slot_b": ("team", "Bosnia and Herzegovina"),  # confirmed 3rd-place qualifier
            },
            "r32_b": {
                "match": "R32-82 (Seattle, July 2)",
                "slot_a": ("1", "G"),   # winner of Group G
                "slot_b": ("team", "Senegal"),  # confirmed 3rd-place qualifier
            },
        },
    }
}

# Completed knockout results — force the actual winner instead of simulating.
# Keyed by match id (e.g. "R32-82"). Value is the winning team name.
COMPLETED_RESULTS = {
    "R32-82": "Belgium",   # Belgium 3-2 Senegal
}

# Confirmed R32 opponents (from actual bracket draw) with final group-stage records.
# Overrides the generic "best 3rd-place" approximation once matchups are known.
R32_ACTUAL_OPPONENTS = {
    "Bosnia and Herzegovina": {
        "team": "Bosnia and Herzegovina", "abbr": "BIH",
        "played": 3, "won": 1, "drawn": 1, "lost": 1,
        "gf": 4, "ga": 3, "gd": 1, "pts": 4, "rank": 3,
    },
    "Senegal": {
        "team": "Senegal", "abbr": "SEN",
        "played": 3, "won": 1, "drawn": 0, "lost": 2,
        "gf": 6, "ga": 4, "gd": 2, "pts": 3, "rank": 3,
    },
}

# Groups per round (for 3rd-place qualification context)
THIRD_PLACE_POOLS = {
    "R32-81": list("BEFIJ"),
    "R32-82": list("AEHIJ"),
}

# All 12 groups and their teams (populated at runtime)
ALL_GROUPS = list("ABCDEFGHIJKL")
