Run the LA QF predictor simulation.

```bash
python main.py $ARGUMENTS
```

Supported flags (pass as arguments to /predict):
- `--no-fetch` — skip the ESPN API call and use cached standings
- `--trials N` — override the number of Monte Carlo trials (default 50,000)
