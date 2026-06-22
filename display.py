"""
Renders the LA QF probability report in a clean terminal format using Rich.
Falls back to plain text if Rich isn't installed.
"""

from datetime import datetime
from typing import Dict, List

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False


def render(
    probs: Dict[str, float],
    standings: Dict[str, List[dict]],
    matchup_probs: Dict[tuple, float] | None = None,
    top_n: int = 20,
    focus_team: str = "United States",
) -> None:
    date_str = datetime.now().strftime("%A, %B %-d %Y")
    top = [(team, p) for team, p in probs.items()][:top_n]

    if HAS_RICH:
        _render_rich(top, standings, date_str, matchup_probs, focus_team)
    else:
        _render_plain(top, standings, date_str, matchup_probs, focus_team)


def _most_likely_opponents(matchup_probs, focus_team, top_n=5):
    """Return [(opponent, prob), ...] sorted by matchup probability for focus_team."""
    opponents = []
    for (a, b), p in matchup_probs.items():
        if a == focus_team:
            opponents.append((b, p))
        elif b == focus_team:
            opponents.append((a, p))
    opponents.sort(key=lambda x: -x[1])
    return opponents[:top_n]


def _render_rich(top, standings, date_str, matchup_probs=None, focus_team="United States"):
    console = Console()

    console.print(Panel(
        f"[bold yellow]2026 FIFA World Cup — LA Quarterfinal Predictor[/bold yellow]\n"
        f"[dim]SoFi Stadium · Inglewood CA · July 10, 2026[/dim]\n"
        f"[dim]Updated: {date_str}[/dim]",
        box=box.DOUBLE_EDGE,
    ))

    table = Table(box=box.SIMPLE_HEAD, show_edge=False)
    table.add_column("Rank", style="dim", width=5)
    table.add_column("Team", style="bold white", min_width=24)
    table.add_column("% Chance to play in LA QF", justify="right", style="cyan")
    table.add_column("Bar", min_width=30)

    max_p = top[0][1] if top else 1.0

    for i, (team, prob) in enumerate(top, 1):
        pct = prob * 100
        bar_len = int((prob / max_p) * 28)
        bar = "█" * bar_len + "░" * (28 - bar_len)
        color = "green" if pct >= 15 else "yellow" if pct >= 8 else "red"
        table.add_row(
            str(i),
            team,
            f"[{color}]{pct:5.1f}%[/{color}]",
            f"[{color}]{bar}[/{color}]",
        )

    console.print(table)

    # Most likely opponents for focus team
    if matchup_probs and focus_team in dict(top).keys() | {t for pair in matchup_probs for t in pair}:
        opponents = _most_likely_opponents(matchup_probs, focus_team)
        if opponents:
            focus_prob = dict(top).get(focus_team, 0)
            console.print(f"\n[bold]Most Likely Opponents for [cyan]{focus_team}[/cyan] "
                          f"(if they reach the QF — {focus_prob*100:.1f}% chance)[/bold]")
            opp_table = Table(box=box.SIMPLE_HEAD, show_edge=False)
            opp_table.add_column("Opponent", style="bold white", min_width=24)
            opp_table.add_column("Matchup %", justify="right", style="cyan")
            opp_table.add_column("% of US QF appearances", justify="right", style="dim")
            for opp, p in opponents:
                cond = (p / focus_prob * 100) if focus_prob > 0 else 0
                opp_table.add_row(opp, f"{p*100:.1f}%", f"{cond:.0f}%")
            console.print(opp_table)

    # Group stage snapshot for LA-relevant groups
    console.print("\n[bold]Group Stage Snapshot (LA QF path groups: D, G, H, J, K, L)[/bold]")
    for letter in ["D", "G", "H", "J", "K", "L"]:
        teams = standings.get(letter, [])
        if not teams:
            continue
        console.print(f"\n  [bold cyan]Group {letter}[/bold cyan]")
        for rank, t in enumerate(teams, 1):
            played_of_3 = t['played']
            bar = "●" * t['won'] + "◑" * t['drawn'] + "○" * t['lost']
            console.print(
                f"    {rank}. [white]{t['team']:<24}[/white] "
                f"[yellow]{t['pts']}pts[/yellow]  "
                f"GD {t['gd']:+d}  GF {t['gf']}  "
                f"({played_of_3}/3 played)  {bar}"
            )

    console.print(
        "\n[dim]Bracket path: R32-81([cyan]1D[/cyan] vs 3rd) + R32-82([cyan]1G[/cyan] vs 3rd) → R16-94 "
        "| R32-83([cyan]2K[/cyan] vs [cyan]2L[/cyan]) + R32-84([cyan]1H[/cyan] vs [cyan]2J[/cyan]) → R16-93 → [bold]LA QF[/bold][/dim]"
    )
    console.print(
        "[dim yellow]Note: group winners (1J, 1K, 1L, 1D) exit to different QF cities. "
        "e.g. if Argentina wins Group J they leave this bracket — only [cyan]2J[/cyan] "
        "(the runner-up) feeds R32-84 and faces the Group H winner here.[/dim yellow]\n"
    )


def _render_plain(top, standings, date_str, matchup_probs=None, focus_team="United States"):
    print("=" * 60)
    print("2026 FIFA World Cup — LA Quarterfinal Predictor")
    print(f"SoFi Stadium · Inglewood CA · July 10, 2026")
    print(f"Updated: {date_str}")
    print("=" * 60)
    print(f"\n{'#':<4} {'Team':<28} {'% Chance'}")
    print("-" * 48)
    for i, (team, prob) in enumerate(top, 1):
        bar = "#" * int(prob * 100 / 3)
        print(f"{i:<4} {team:<28} {prob*100:5.1f}%  {bar}")

    if matchup_probs:
        opponents = _most_likely_opponents(matchup_probs, focus_team)
        if opponents:
            focus_prob = dict(top).get(focus_team, 0)
            print(f"\nMost Likely Opponents for {focus_team} "
                  f"(if they reach the QF — {focus_prob*100:.1f}% chance)")
            print(f"{'Opponent':<28} {'Matchup %':>10}  {'% of US QF apps':>16}")
            print("-" * 58)
            for opp, p in opponents:
                cond = (p / focus_prob * 100) if focus_prob > 0 else 0
                print(f"{opp:<28} {p*100:>9.1f}%  {cond:>15.0f}%")

    print("\nGroup Stage Snapshot (D, G, H, J, K, L)")
    for letter in ["D", "G", "H", "J", "K", "L"]:
        teams = standings.get(letter, [])
        if not teams:
            continue
        print(f"\n  Group {letter}")
        for rank, t in enumerate(teams, 1):
            print(f"    {rank}. {t['team']:<24} {t['pts']}pts  GD {t['gd']:+d}")

    print("\nBracket: R32-83(2K v 2L)+R32-84(1H v 2J)→R16-93 | "
          "R32-81(1D v 3rd)+R32-82(1G v 3rd)→R16-94 → LA QF\n")
