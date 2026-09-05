# dopamine-trading

PAPER ONLY. Simulated fills. No live orders.

Two desks live in this repo:

- Root equities paper desk. Yahoo quotes. Paper/SPY Matrix jack-in.
- `crypto-paper/` CRYPTO PAPER desk. Public crypto quotes. Start `$1k`. Target `$100k`. Horizon ~30 days. 24/7 crypto paper.

Dashboard is the CoS Matrix jack-in (open-bodhi visual system, matrix2). Repo match only. CoS owns here.now publish. Do not treat local republish as the live SoT.

Live hosts (CoS, matrix2):

- Paper: https://brisk-tassel-djbq.here.now/
- Crypto: https://open-bodhi-a27f.here.now/

https://brisk-tassel-djbq.here.now/dash.js?v=matrix2

https://open-bodhi-a27f.here.now/dash.js?v=matrix2

## Layout

Root equities paper desk:

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
test_matrix_dash.py       viewport-fit, safe-area, single FS handler, matrix2 cache
README.md                 this file
crypto-paper/             CRYPTO PAPER desk ($1k to $100k / 30d)
```

Crypto paper desk (`crypto-paper/`):

```
crypto-paper/engine.py                 paper broker (cash, positions, 10bps fee, fractionals, no short)
crypto-paper/quotes.py                 Binance public REST + CoinGecko fallback (no keys)
crypto-paper/strategy.py               aggressive momentum/breakout, concentrated size
crypto-paper/loop_session.py           continuous 24/7 tick loop; writes session.pid
crypto-paper/sync_dashboard.py         write dashboard/data.json
crypto-paper/republish_dashboard.py    here.now republish helper
crypto-paper/dashboard/index.html      Matrix jack-in shell (loads dash.js?v=matrix2)
crypto-paper/dashboard/dash.js         equity curve + BTC overlay + fullscreen
crypto-paper/test_crypto_paper.py      snapshot fields + matrix2 viewport/cache gate
crypto-paper/README.md                 crypto desk notes
```

Repo-relative paths only. Runtime files stay local and are gitignored: `data.json`, `dashboard/data.json`, `logs/`, `session.pid`, `.venv/`, secrets.

## Run paper session

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
```

Serve the dashboard locally after a sync:

```bash
python3 -m http.server 8787 --directory dashboard
```

Then open `http://127.0.0.1:8787/` . The page polls `data.json`. Chart/fullscreen uses `viewport-fit=cover` and safe-area insets. One Fullscreen click handler. No inline onclick. Cache buster is `dash.js?v=matrix2`.

## Run crypto session

CRYPTO PAPER only. Start `$1k`. Target `$100k`. Horizon ~30 days. Universe: BTC ETH SOL DOGE SUI. Quotes hit public Binance first, then CoinGecko. No keys. From `crypto-paper/`:

```bash
python3 loop_session.py --once --sync
python3 sync_dashboard.py
python3 test_crypto_paper.py
```

Loop the desk (writes `session.pid`):

```bash
python3 loop_session.py --interval 60 --sync
```

Optional flags, still repo-relative:

```bash
python3 loop_session.py --once --data data.json --universe BTC,ETH,SOL,DOGE,SUI
python3 sync_dashboard.py --data data.json --dest dashboard/data.json
```

Serve the dashboard locally after a sync:

```bash
python3 -m http.server 8788 --directory dashboard
```

Then open `http://127.0.0.1:8788/` . The page polls `data.json`. Cache buster is `dash.js?v=matrix2`. Chart/fullscreen uses `viewport-fit=cover`, `overflow-x:clip`, and the matrix2 responsive hard lock.

See `crypto-paper/README.md` for desk-local notes.

## Republish dashboard

CoS owns here.now. Live matrix2 hosts stay with CoS:

- Paper live: https://brisk-tassel-djbq.here.now/
- Crypto live: https://open-bodhi-a27f.here.now/

Local `republish_dashboard.py` is a helper only. It does not own the live sites. Never commit credentials or secrets. Prefer `--dry-run` unless CoS asked for a publish.

From the repo root (paper desk):

```bash
python3 republish_dashboard.py --dir dashboard --slug brisk-tassel-djbq --dry-run
```

From `crypto-paper/` (crypto desk):

```bash
python3 republish_dashboard.py --dir dashboard --slug open-bodhi-a27f --dry-run
```

Anonymous local publishes expire in 24 hours. CoS keeps the live open-bodhi / paper twins.

## Scope

- Equities paper desk in the repo root
- CRYPTO PAPER desk in `crypto-paper/` ($1k to $100k / 30d)
- PAPER ONLY
- No live orders
