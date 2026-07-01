#!/usr/bin/env python3
"""Render the LA QF bracket prediction as a PNG using the simulation outputs."""
import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

import simulate as S
from bracket import BRACKET, ALL_GROUPS, R32_ACTUAL_OPPONENTS, COMPLETED_RESULTS

N = 60_000
S.N_TRIALS = N
standings = json.loads((Path(__file__).parent / "standings_cache.json").read_text())

slot_fill = defaultdict(lambda: defaultdict(int))
r32w = defaultdict(lambda: defaultdict(int))
r16w = defaultdict(lambda: defaultdict(int))
qf = defaultdict(int)

for _ in range(N):
    gr = {}; thirds = []
    for L in ALL_GROUPS:
        teams = standings.get(L, [])
        if len(teams) < 4:
            gr[L] = teams[:4] if teams else []; continue
        res = S.simulate_group(teams); gr[L] = res
        thirds.append({**res[2], "_group": L})
    thirds.sort(key=lambda t: (-t.get("sim_pts", t["pts"]), -t.get("sim_gd", t["gd"]), -t.get("sim_gf", t["gf"])))
    tbg = {t["_group"]: t for t in thirds[:8]}
    def slot(p, g):
        if p == "team": return R32_ACTUAL_OPPONENTS.get(g)
        G = gr.get(g, [])
        if not G: return None
        if p == "1": return G[0]
        if p == "2": return G[1] if len(G) > 1 else None
        if p == "3rd":
            c = [tbg[x] for x in list(g) if x in tbg]; return S.pick_best_third(c) if c else None
    def r32(n):
        a = slot(*n["slot_a"]); b = slot(*n["slot_b"])
        mid = n["match"].split()[0]
        if mid in COMPLETED_RESULTS:
            for t in (a, b):
                if t and t["team"] == COMPLETED_RESULTS[mid]: return t
        if not a or not b: return a or b
        return S.simulate_match(a, b)
    la = BRACKET["qf_la"]; A = la["r16_a"]; B = la["r16_b"]
    for node, nm in [(A["r32_a"], "83"), (A["r32_b"], "84"), (B["r32_a"], "81"), (B["r32_b"], "82")]:
        for s in ("slot_a", "slot_b"):
            t = slot(*node[s])
            if t: slot_fill[f"{nm}:{node[s][0]}{node[s][1]}"][t["team"]] += 1
    w83, w84 = r32(A["r32_a"]), r32(A["r32_b"])
    w81, w82 = r32(B["r32_a"]), r32(B["r32_b"])
    for w, n in [(w83, "83"), (w84, "84"), (w81, "81"), (w82, "82")]:
        if w: r32w[n][w["team"]] += 1
    w93 = S.simulate_match(w83, w84) if (w83 and w84) else (w83 or w84)
    w94 = S.simulate_match(w81, w82) if (w81 and w82) else (w81 or w82)
    if w93: r16w["93"][w93["team"]] += 1
    if w94: r16w["94"][w94["team"]] += 1
    if w93 and w94: qf[tuple(sorted([w93["team"], w94["team"]]))] += 1

def top(d, k=3):
    return [(t, c / N) for t, c in sorted(d.items(), key=lambda x: -x[1])[:k]]

# ---------- draw ----------
fig, ax = plt.subplots(figsize=(15, 9))
ax.set_xlim(0, 15); ax.set_ylim(0, 9); ax.axis("off")
fig.patch.set_facecolor("#0f1420")
ax.set_facecolor("#0f1420")

NAVY, GOLD, CYAN, WHITE, DIM = "#1b2436", "#f5c518", "#3fb6d3", "#ffffff", "#8a93a6"

def box(x, y, w, h, title, sub, teams, fc=NAVY, ec=CYAN):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.03,rounding_size=0.12",
                                fc=fc, ec=ec, lw=1.6, mutation_aspect=1))
    ax.text(x + w / 2, y + h - 0.26, title, ha="center", va="top", color=GOLD,
            fontsize=10.5, fontweight="bold")
    ax.text(x + w / 2, y + h - 0.52, sub, ha="center", va="top", color=DIM, fontsize=7.5)
    for i, (t, p) in enumerate(teams):
        c = WHITE if i == 0 else DIM
        fw = "bold" if i == 0 else "normal"
        ax.text(x + 0.18, y + h - 0.82 - i * 0.32, f"{t}", ha="left", va="top", color=c, fontsize=8.5, fontweight=fw)
        ax.text(x + w - 0.18, y + h - 0.82 - i * 0.32, f"{p*100:.0f}%", ha="right", va="top", color=c, fontsize=8.5, fontweight=fw)

def line(x1, y1, x2, y2):
    ax.plot([x1, x2], [y1, y2], color=DIM, lw=1.2, zorder=0)

BW, BH = 3.1, 1.7
# Column x positions
X0, X1, X2 = 0.3, 5.6, 10.9
# R32 boxes (4) on left, two per R16
ys = [7.0, 5.0, 2.7, 0.7]
box(X0, ys[0], BW, BH, "R32-83  ·  2K v 2L", "Toronto · Jun 29", top(r32w["83"]))
box(X0, ys[1], BW, BH, "R32-84  ·  1H v 2J", "Los Angeles · Jul 2", top(r32w["84"]))
box(X0, ys[2], BW, BH, "R32-81  ·  1D v 3rd", "San Francisco · Jul 1", top(r32w["81"]))
box(X0, ys[3], BW, BH, "R32-82  ·  1G v 3rd", "Seattle · Jul 2", top(r32w["82"]))

# R16 boxes (2)
y93 = (ys[0] + ys[1]) / 2
y94 = (ys[2] + ys[3]) / 2
box(X1, y93, BW, BH, "R16-93", "Arlington · Jul 6", top(r16w["93"], 4), ec=GOLD)
box(X1, y94, BW, BH, "R16-94", "Seattle · Jul 7", top(r16w["94"], 4), ec=GOLD)

# QF box (1)
yqf = (y93 + y94) / 2
box(X2, yqf, BW, BH + 0.6, "QF — LA", "SoFi Stadium · Jul 10", top(r16w["93"], 1) + top(r16w["94"], 1), fc="#2a2140", ec=GOLD)

# connectors
for yb in (ys[0], ys[1]):
    line(X0 + BW, yb + BH / 2, X1, y93 + BH / 2)
for yb in (ys[2], ys[3]):
    line(X0 + BW, yb + BH / 2, X1, y94 + BH / 2)
line(X1 + BW, y93 + BH / 2, X2, yqf + BH / 2 + 0.3)
line(X1 + BW, y94 + BH / 2, X2, yqf + BH / 2 + 0.3)

# title + most-likely matchup banner
ax.text(7.5, 8.75, "2026 FIFA World Cup — Path to the LA Quarterfinal",
        ha="center", color=WHITE, fontsize=15, fontweight="bold")
ax.text(7.5, 8.35, f"Monte Carlo prediction · {N:,} trials · numbers = P(reach that match)",
        ha="center", color=DIM, fontsize=9)

mtop = sorted(qf.items(), key=lambda x: -x[1])[:3]
banner = "Most likely LA QF:   " + "    ".join(f"{a} v {b}  {c/N*100:.1f}%" for (a, b), c in mtop)
ax.text(X2 + BW / 2, yqf - 0.5, banner.split("   ")[0], ha="center", color=GOLD, fontsize=9, fontweight="bold")
for i, ((a, b), c) in enumerate(mtop):
    ax.text(X2 + BW / 2, yqf - 0.85 - i * 0.3, f"{a} v {b}   {c/N*100:.1f}%",
            ha="center", color=WHITE if i == 0 else DIM, fontsize=8.5,
            fontweight="bold" if i == 0 else "normal")

out = Path(__file__).parent / "bracket_prediction.png"
plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"Saved {out}")
