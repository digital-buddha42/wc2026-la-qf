# WC 2026 — LA Quarterfinal Predictor

Daily Monte Carlo simulation for which two teams will meet in the **2026 FIFA World Cup Quarterfinal at SoFi Stadium, Inglewood CA (July 10, 2026)**.

## Bracket Path to LA QF

```
Group D winner ──┐
3rd (B/E/F/I/J) ─┤ R32-81 (SF Bay Area, Jul 1)
                  │                              ├─ R16-94 (Seattle, Jul 7) ──┐
Group G winner ──┐│                              │                            │
3rd (A/E/H/I/J) ─┤ R32-82 (Seattle, Jul 2) ────┘                            │
                  │                                                            ├── LA QF (Jul 10)
Group K runner-up─┐                                                            │
Group L runner-up─┤ R32-83 (Toronto, Jun 29)                                  │
                  │                              ├─ R16-93 (Arlington, Jul 6)─┘
Group H winner ──┐│                              │
Group J runner-up─┤ R32-84 (Los Angeles, Jul 2) ┘
```

Key groups: **D, G, H, J, K, L** (plus 3rd-place wild cards from other groups)

## Usage

```bash
pip install -r requirements.txt

# Run with live data fetch
python main.py

# Use cached standings (faster, offline)
python main.py --no-fetch

# More precise simulation
python main.py --trials 100000
```

## How It Works

1. **Fetch**: Pulls live group standings from ESPN's public API
2. **Simulate**: 50,000 Monte Carlo trials of remaining group matches → R32 → R16 → QF
3. **Rating**: Bradley-Terry model — `rating = exp(0.1*pts + 0.02*gd + 0.005*gf)`
4. **Output**: Ranked probability table + group stage snapshot

## Run Daily (cron)

```cron
0 9 * * * cd /path/to/wc2026-la-qf && python main.py >> daily_log.txt 2>&1
```

## Data Source

ESPN public API — `site.api.espn.com/apis/v2/sports/soccer/fifa.world/standings`  
No API key required. Standings update within minutes of match completion.
