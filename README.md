# Agent Polymarket

Auto-trading bot for Polymarket 5-minute "Up or Down" crypto prediction markets on Polygon.

## Files

| File | Purpose |
|------|---------|
| `jup_predict_bot.py` | Main bot — signal engine, execution, risk management |
| `status.py` | CLI wallet & trade status |
| `dashboard.html` | Web dashboard UI |
| `dashboard_server.py` | Local HTTP server for dashboard (port 8080) |

## Setup

```bash
pip install requests py-clob-client eth-account web3 python-dotenv

cp .env.example .env.polybot
# Fill in WALLET_ADDRESS and WALLET_PRIVKEY
```

## Run

```bash
# Paper trade
PAPER_TRADE=true python jup_predict_bot.py

# Live trade
PAPER_TRADE=false python jup_predict_bot.py

# Status
python status.py

# Dashboard (http://localhost:8080)
python dashboard_server.py
```

## Requirements

- Polygon wallet with native USDC + MATIC for gas
- Min 0.5 MATIC recommended
- USDC contract: `0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359` (native, not USDC.e)

## Strategy

- Markets: BTC, ETH, SOL, XRP — 5-minute Up/Down on Polymarket
- Signal: RSI(14) + EMA(5/13) + 3-candle momentum (Binance 1m klines)
- 2-stage execution: detect at epoch start, confirm at 60s before close
- EV-based sizing: 10–20% of balance
- Risk controls: 3 consecutive losses → stop | 15% daily loss → stop
- Slippage guard: cancel if best ask > expected × 1.02
