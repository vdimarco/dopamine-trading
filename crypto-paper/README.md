# crypto-paper

30-day CRYPTO PAPER desk. Simulated fills only. No live orders. No API keys. No secrets.

Start `$1000`. Target `$100000`. Horizon ~30 days. 24/7 crypto paper.

Live SoT (CoS owns here.now):

https://open-bodhi-a27f.here.now/

https://open-bodhi-a27f.here.now/dash.js?v=matrix2

## Layout

```
engine.py                 paper broker (cash, positions, 10bps fee, fractionals, no short)
quotes.py                 Binance public REST + CoinGecko fallback (no keys)
strategy.py               aggressive momentum/breakout, concentrated size
loop_session.py           continuous 24/7 tick loop; writes session.pid
sync_dashboard.py         write dashboard/data.json (+ optional --republish)
republish_dashboard.py    here.now republish from local .herenow state
dashboard/index.html      Matrix jack-in shell (loads dash.js?v=matrix2)
dashboard/dash.js         equity curve + BTC overlay + fullscreen
test_crypto_paper.py      snapshot fields + matrix2 viewport/cache gate
README.md                 this file
```

Repo-relative paths only. Runtime files stay local and are gitignored: `data.json`, `dashboard/data.json`, `logs/`, `ledger/`, `session.pid`, `.venv/`, `.herenow/`, secrets, claim tokens, `*.bak*`.

## Run notes

Python 3.10+ stdlib only. From `crypto-paper/`:

```bash
python3 loop_session.py --once --sync
python3 sync_dashboard.py
python3 republish_dashboard.py --dry-run
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
python3 sync_dashboard.py --republish
python3 republish_dashboard.py --dir dashboard --slug open-bodhi-a27f
```

Quotes hit `data-api.binance.vision` first, then CoinGecko. No keys. PAPER ONLY.

Serve the dashboard locally after a sync:

```bash
python3 -m http.server 8788 --directory dashboard
```

Then open `http://127.0.0.1:8788/` . The page polls `data.json`. Cache buster is `dash.js?v=matrix2`. Chart/fullscreen uses `viewport-fit=cover`, `overflow-x:clip`, and the matrix2 responsive hard lock.

`republish_dashboard.py` reads `HERENOW_API_KEY`, `~/.herenow/credentials`, or a local `.herenow/state.json` claim token. It does not print or commit claim tokens. Anonymous publishes expire in 24 hours. CoS owns live publish.

## Scope

- CRYPTO PAPER only
- Universe: BTC ETH SOL DOGE SUI
- No live exchange orders
- Do not commit `.herenow/`, `data.json`, secrets, or claim tokens
