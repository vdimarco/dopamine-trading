# dopamine-trading

PAPER ONLY equities paper-trade runtime. Simulated fills against Yahoo quotes. No live orders. No crypto desk.

Dashboard is the CoS Matrix jack-in (open-bodhi visual system, paper/SPY signals). Repo match only; CoS owns here.now publish.

Live1 host (CoS publish):

https://lucid-tablet-tgx3.here.now/

https://lucid-tablet-tgx3.here.now/dash.js?v=matrix2

Visual source of truth:

https://open-bodhi-a27f.here.now/

Paper/SPY twin:

https://brisk-tassel-djbq.here.now/

## Layout

```
engine.py                 paper broker (cash, positions, fills, Matrix snapshot)
quotes.py                 Yahoo Finance quotes via urllib
strategy.py               20-session cross-sectional momentum
run_session.py            one paper tick
loop_session.py           repeat ticks; writes session.pid
sync_dashboard.py         copy snapshot into dashboard/
republish_dashboard.py    publish dashboard/ to here.now
build_dash.py             verify Matrix jack-in dashboard files
dashboard/index.html      Matrix shell (loads dash.js?v=matrix2)
dashboard/dash.js         paper/SPY curve + single fullscreen handler
README.md                 this file
```

Repo-relative paths only. Runtime files stay local and are gitignored: `data.json`, `dashboard/data.json`, `logs/`, `ledger/`, `session.pid`, `.venv/`, `.herenow/`, secrets.

## Run notes

Python 3.10+ stdlib only. From the repo root:

```bash
python3 run_session.py
python3 sync_dashboard.py
python3 build_dash.py
python3 test_matrix_dash.py
```

Loop the desk (writes `session.pid`):

```bash
python3 loop_session.py --interval 60
```

Optional flags, still repo-relative:

```bash
python3 run_session.py --data data.json --universe SPY,QQQ,AAPL,MSFT,NVDA
python3 sync_dashboard.py --data data.json --dest dashboard/data.json
python3 republish_dashboard.py --dir dashboard --slug lucid-tablet-tgx3
```

Serve the dashboard locally after a sync:

```bash
python3 -m http.server 8787 --directory dashboard
```

Then open `http://127.0.0.1:8787/` . The page polls `data.json`. Chart/fullscreen uses `viewport-fit=cover` and safe-area insets. One Fullscreen click handler. No inline onclick. Cache buster is `dash.js?v=matrix2`.

`republish_dashboard.py` reads `HERENOW_API_KEY` or `~/.herenow/credentials`. It does not write claim tokens or credentials into the repo. Anonymous publishes expire in 24 hours. CoS owns live publish.

## Scope

- Equities paper desk only
- PAPER ONLY
- Do not add `crypto-paper/` or any crypto desk files
