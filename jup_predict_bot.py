"""
jup_predict_bot.py — Polymarket 5-Minute Crypto Prediction Bot
Changelog:
  - [v1] Mean reversion signal engine (Binance 5m klines)
  - [v2] Risk management: hard stop, daily loss, loss streak, max trades
  - [v3] Entry filter dinamis, volume consistency check, candle timing fix
  - [v4] Pindah ke Polymarket "Up or Down" 5-menit market (Polygon chain)
        Signal engine tetap Binance. Execution via Polymarket CLOB API.
  - [v5] Signal engine ganti ke odds-based (fade the crowd).
        Tidak lagi nunggu candle move. Masuk di awal epoch, scan Polymarket
        live odds, bet sisi yang underpriced (edge dari 50/50 fair value).

Deps:
  pip install requests py-clob-client eth-account

Env vars:
  WALLET_ADDRESS   — Polygon address (0x...)
  WALLET_PRIVKEY   — Private key hex (tanpa 0x)
  POLYGON_RPC      — Optional, default polygon-rpc.com
  PAPER_TRADE      — "true" (default) / "false"
  TG_BOT_TOKEN     — Telegram bot token
  TG_CHAT_ID       — Telegram chat id
"""

import os
import time
import logging
import requests
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────
#  KONFIGURASI UTAMA
# ─────────────────────────────────────────────

# === Wallet & Chain (Polygon) ===
WALLET_ADDRESS     = os.environ.get("WALLET_ADDRESS", "")        # 0x...
WALLET_PRIVKEY_HEX = os.environ.get("WALLET_PRIVKEY", "")        # hex, tanpa 0x
POLYGON_RPC        = os.environ.get("POLYGON_RPC",
                                    "https://polygon-rpc.com")
USDC_CONTRACT      = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"  # Native USDC Polygon (Polymarket)
MATIC_GAS_RESERVE  = 0.5    # Reserve MATIC untuk gas

# === Mode ===
PAPER_TRADE        = os.environ.get("PAPER_TRADE", "true").lower() == "true"
PAPER_BALANCE      = 100.0   # Starting balance untuk paper mode

# === Telegram ===
TG_BOT_TOKEN       = os.environ.get("TG_BOT_TOKEN", "")
TG_CHAT_ID         = os.environ.get("TG_CHAT_ID", "")

# === Polymarket ===
GAMMA_API          = "https://gamma-api.polymarket.com"
CLOB_HOST          = "https://clob.polymarket.com"
CHAIN_ID           = 137     # Polygon mainnet

# Harga per share — paper sim pakai 0.50.
# Live mode pakai bestAsk dari market (diambil saat scan odds).
ORDER_PRICE        = 0.50   # fallback / paper
ORDER_TICK_SIZE    = "0.01"

# Symbol mapping: Binance symbol -> Polymarket coin prefix untuk slug
# Slug format: {coin_prefix}-updown-5m-{epoch_start_unix}
# Epoch = (current_unix // 300) * 300  (dibulatkan ke 5 menit)
SYMBOL_MAP = {
    "BTCUSDT":  "btc",
    "ETHUSDT":  "eth",
    "SOLUSDT":  "sol",
    "XRPUSDT":  "xrp",
}

# === Position Sizing (Progressive) ===
BET_BASE           = 2.0   # Bet awal
BET_MAX            = 4.0   # Bet maksimum setelah profit cukup
MIN_BALANCE        = 0.0   # Tidak ada minimum — bot terus jalan
# Tier naik otomatis berdasarkan session PnL:
#   PnL < $5   → $2.00
#   PnL $5-15  → $3.00
#   PnL > $15  → $4.00

# === Risk Management ===
MAX_DAILY_LOSS_PCT = -0.15        # Stop seharian kalau total -15%
MAX_DAILY_TRADES   = 30           # Maks 30 trade per hari
MAX_LOSS_STREAK    = 3            # STOP setelah 3 loss berturut (bukan pause)
PAUSE_AFTER_STREAK = 15 * 60      # 15 menit pause (detik)
MAX_SLIPPAGE_PCT   = 0.02         # Cancel kalau harga entry > 2% dari expected

# === Signal Engine — 2-Stage Execution ===
# Stage 1 (awal epoch, 0-30s): TA + odds → detect candidates
# Stage 2 (akhir epoch, ~60s sebelum close): final confirmation → execute or skip
ODDS_MAX_ENTRY      = 0.55   # Max odds untuk entry
STAGE1_WINDOW       = 45     # Stage 1: detik pertama epoch
STAGE2_TRIGGER      = 240    # Stage 2: mulai detik ke-240 (60s sebelum close)

# === Filter Pasar ===
MIN_MARKET_VOLUME  = 500
BTC_MIN_VOLUME_5M  = 1_000_000    # $1M — cukup liquid, weekend-safe

# === Notif & Log ===
LOG_FILE           = "/tmp/polymarket_bot.log"
NOTIFY_ON          = ["WIN", "LOSS", "BALANCE_CRITICAL", "ERROR", "DAILY_STOP"]

# ─────────────────────────────────────────────
#  LOGGING SETUP
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("pm_bot")

# ─────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────

@dataclass
class SessionState:
    balance_start:      float = 0.0
    balance_current:    float = 0.0
    trades_today:       int   = 0
    wins:               int   = 0
    losses:             int   = 0
    loss_streak:        int   = 0
    daily_pnl:          float = 0.0
    session_pnl:        float = 0.0
    trade_log:          list  = field(default_factory=list)
    paused_until:       float = 0.0
    daily_stopped:      bool  = False
    last_epoch_traded:  int   = 0   # epoch unix timestamp — enforce 1 trade per epoch

    @property
    def win_rate(self) -> float:
        total = self.wins + self.losses
        return (self.wins / total * 100) if total > 0 else 0.0

    @property
    def daily_pnl_pct(self) -> float:
        if self.balance_start == 0:
            return 0.0
        return self.daily_pnl / self.balance_start

    def record_trade(self, symbol: str, direction: str, size: float,
                     entry: float, exit_price: float, pnl: float):
        result = "WIN" if pnl > 0 else "LOSS"
        self.trade_log.append({
            "time":      datetime.now(timezone.utc).isoformat(),
            "symbol":    symbol,
            "direction": direction,
            "size":      size,
            "entry":     entry,
            "exit":      exit_price,
            "pnl":       round(pnl, 4),
            "result":    result
        })
        self.daily_pnl       += pnl
        self.session_pnl     += pnl
        self.trades_today    += 1
        self.balance_current += pnl
        if result == "WIN":
            self.wins       += 1
            self.loss_streak = 0
        else:
            self.losses     += 1
            self.loss_streak += 1


# ─────────────────────────────────────────────
#  POLYGON RPC
# ─────────────────────────────────────────────

def _polygon_rpc(method: str, params: list):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    r = requests.post(POLYGON_RPC, json=payload, timeout=10)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"Polygon RPC error: {data['error']}")
    return data["result"]


def get_balance() -> float:
    """Ambil USDC.e balance dari wallet Polygon."""
    if PAPER_TRADE:
        return _paper_state.get("balance", PAPER_BALANCE)
    if not WALLET_ADDRESS:
        raise RuntimeError("Set env WALLET_ADDRESS")
    # ERC20 balanceOf(address) — selector 0x70a08231
    calldata = "0x70a08231" + WALLET_ADDRESS.lower().replace("0x", "").zfill(64)
    result   = _polygon_rpc("eth_call", [{"to": USDC_CONTRACT, "data": calldata}, "latest"])
    return int(result, 16) / 1_000_000   # USDC 6 desimal


def get_gas_balance() -> float:
    """Cek MATIC balance untuk gas."""
    if PAPER_TRADE:
        return 1.0
    if not WALLET_ADDRESS:
        raise RuntimeError("Set env WALLET_ADDRESS")
    result = _polygon_rpc("eth_getBalance", [WALLET_ADDRESS, "latest"])
    return int(result, 16) / 1e18


# ─────────────────────────────────────────────
#  PAPER TRADE STATE (in-memory)
# ─────────────────────────────────────────────

_paper_state: dict = {"balance": PAPER_BALANCE}


# ─────────────────────────────────────────────
#  POLYMARKET HELPERS
# ─────────────────────────────────────────────

def _parse_outcome_prices(market_data: dict) -> Optional[float]:
    """
    Parse outcomePrices dari market dict Gamma API events endpoint.
    Return float Up odds (0-1) atau None.
    outcomePrices ada sebagai JSON string: "[\"0.57\", \"0.43\"]"
    """
    try:
        prices = market_data.get("outcomePrices")
        if prices is None:
            return None
        if isinstance(prices, str):
            import json
            prices = json.loads(prices)
        if len(prices) < 1:
            return None
        return float(prices[0])
    except Exception:
        return None


def _get_current_market(coin_prefix: str) -> Optional[dict]:
    """
    Fetch market Polymarket 5-menit yang sedang aktif untuk coin_prefix.
    Slug dikonstruksi langsung: {coin}-updown-5m-{epoch_start}
    epoch_start = unix timestamp dibulatkan ke bawah ke 5 menit.

    Return dict dengan kondisi, token IDs, end_date, dll. atau None.
    """
    epoch_start = (int(time.time()) // 300) * 300
    slug        = f"{coin_prefix}-updown-5m-{epoch_start}"

    try:
        r = requests.get(f"{GAMMA_API}/events", params={"slug": slug}, timeout=10)
        r.raise_for_status()
        data = r.json()

        # Gamma API bisa return list atau dict
        if isinstance(data, list):
            if not data:
                return None
            data = data[0]

        markets = data.get("markets", [])
        if not markets:
            return None

        market = markets[0]

        # Token IDs ada di clobTokenIds, urutan sama dengan outcomes ["Up", "Down"]
        clob_ids = market.get("clobTokenIds", [])
        outcomes = market.get("outcomes", ["Up", "Down"])
        if isinstance(outcomes, str):
            import json as _json
            outcomes = _json.loads(outcomes)

        if len(clob_ids) < 2:
            log.warning(f"clobTokenIds tidak lengkap di slug {slug}: {clob_ids}")
            return None

        token_map = dict(zip(outcomes, clob_ids))
        up_id   = token_map.get("Up")
        down_id = token_map.get("Down")

        if not up_id or not down_id:
            log.warning(f"Token Up/Down tidak ketemu di slug {slug}")
            return None

        end_dt = datetime.fromisoformat(
            market["endDate"].replace("Z", "+00:00")
        )

        return {
            "condition_id": market["conditionId"],
            "question":     market["question"],
            "end_date":     end_dt,
            "up_token_id":  up_id,
            "down_token_id": down_id,
            "neg_risk":     bool(market.get("neg_risk", 0)),
            "tick_size":    ORDER_TICK_SIZE,
            "slug":         slug,
            "up_odds":      _parse_outcome_prices(market),   # float Up odds
            "last_price":   market.get("lastTradePrice"),
            "best_bid":     market.get("bestBid"),
            "best_ask":     market.get("bestAsk"),
        }

    except Exception as e:
        log.error(f"Gagal fetch market {slug}: {e}")
        return None


def _place_polymarket_order(token_id: str, size_usd: float,
                            neg_risk: bool, tick_size: str,
                            entry_price: float = ORDER_PRICE) -> Optional[str]:
    """
    Place BUY order di Polymarket CLOB.
    entry_price: harga aktual dari bestAsk market (live) atau ORDER_PRICE (paper).
    Return: order_id (str) atau None.
    """
    if PAPER_TRADE:
        order_id = f"paper_{token_id[:10]}_{int(time.time())}"
        log.info(f"[PAPER] Order placed: {order_id} | size=${size_usd:.2f} @ {entry_price:.2f}")
        return order_id

    # ── LIVE MODE ──────────────────────────────────────────────────────────
    from py_clob_client.client import ClobClient
    from py_clob_client.clob_types import OrderArgs, PartialCreateOrderOptions
    from py_clob_client.constants import BUY

    client = ClobClient(
        host=CLOB_HOST,
        chain_id=CHAIN_ID,
        key=WALLET_PRIVKEY_HEX,
        signature_type=0,
        funder=WALLET_ADDRESS,
    )
    client.set_api_creds(client.create_or_derive_api_creds())

    price  = round(entry_price, 2)
    shares = round(size_usd / price, 2)
    resp   = client.create_and_post_order(
        OrderArgs(token_id=token_id, price=price, size=shares, side=BUY),
        PartialCreateOrderOptions(tick_size=tick_size, neg_risk=neg_risk),
    )
    status    = resp.get("status", "")
    order_id  = resp.get("orderID")
    filled    = status in ("matched", "filled") or bool(order_id)
    log.info(f"[LIVE] Order {order_id} | status={status} | "
             f"{shares} shares @ {price} = ${size_usd:.2f} | filled={filled}")
    if not filled:
        log.warning(f"[LIVE] Order tidak filled (status={status}), cancel trade.")
        return None
    return order_id
    # ────────────────────────────────────────────────────────────────────────


def _check_resolution(condition_id: str) -> Optional[bool]:
    """
    Cek apakah market sudah resolve.
    Return True = Up wins, False = Down wins, None = belum settle.
    outcomePrices[0] = Up price, [1] = Down price. Resolved = 1 atau 0.
    """
    try:
        r    = requests.get(f"{GAMMA_API}/markets/{condition_id}", timeout=10)
        data = r.json()
        if isinstance(data, list):
            data = data[0]
        if not data.get("closed"):
            return None
        prices = data.get("outcomePrices", [0, 0])
        if isinstance(prices, str):
            import json
            prices = json.loads(prices)
        return float(prices[0]) > 0.5   # True = Up win
    except Exception as e:
        log.error(f"Gagal cek resolusi {condition_id}: {e}")
        return None


def _wait_and_settle(market: dict, direction: str,
                     entry_price: float, size_usd: float) -> tuple[float, float]:
    """
    Tunggu market close + buffer, return (exit_price, pnl_usd).

    Paper mode: ambil harga Binance setelah close, simulasikan hasil.
    Live mode:  poll Gamma API outcomePrices sampai closed=True.
    """
    end_dt    = market["end_date"]
    now       = datetime.now(timezone.utc)
    wait_secs = max(5, (end_dt - now).total_seconds() + 5)

    log.info(f"Tunggu settlement {wait_secs:.0f}s "
             f"(close {end_dt.strftime('%H:%M:%S')} UTC)...")
    time.sleep(wait_secs)

    if PAPER_TRADE:
        # Cari symbol Binance dari coin prefix di slug
        slug_coin = market["slug"].split("-updown")[0]   # "btc", "eth", dll
        symbol    = next(
            (k for k, v in SYMBOL_MAP.items() if v == slug_coin), None
        )
        exit_price = _get_binance_price(symbol) if symbol else entry_price
        if exit_price is None:
            exit_price = entry_price

        price_up = exit_price >= entry_price
        won      = (direction == "LONG" and price_up) or \
                   (direction == "SHORT" and not price_up)
        pnl      = size_usd * 0.8 if won else -size_usd
        tag      = "WIN" if won else "LOSS"

        _paper_state["balance"] = _paper_state.get("balance", PAPER_BALANCE) + pnl
        log.info(f"[PAPER] {market['question']} → {tag} "
                 f"entry={entry_price:.4f} exit={exit_price:.4f} PnL ${pnl:+.4f}")
        return exit_price, pnl

    # ── LIVE MODE: poll sampai resolved ────────────────────────────────────
    for _ in range(24):   # max 2 menit polling tiap 5 detik
        time.sleep(5)
        up_wins = _check_resolution(market["condition_id"])
        if up_wins is not None:
            won = (direction == "LONG" and up_wins) or \
                  (direction == "SHORT" and not up_wins)
            # PnL: shares dibeli @ ORDER_PRICE, resolve ke $1 atau $0
            pnl = size_usd * (1 / ORDER_PRICE - 1) if won else -size_usd
            exit_price = 1.0 if up_wins else 0.0
            return exit_price, pnl
    raise RuntimeError("Market tidak resolve setelah 2 menit polling")


# ─────────────────────────────────────────────
#  EXECUTE TRADE
# ─────────────────────────────────────────────

def execute_trade(signal: dict, size: float, state: SessionState) -> Optional[dict]:
    """
    Eksekusi satu siklus di Polymarket 5-minute Up or Down market.

    Flow:
      1. Pakai market dari signal (sudah di-fetch saat scan odds)
      2. Ambil entry price dari Binance (referensi paper settlement)
      3. Place BUY order (Up jika LONG, Down jika SHORT)
      4. Tunggu epoch close + 5 detik buffer
      5. Settle & return hasil
    """
    symbol    = signal["symbol"]
    direction = signal["direction"]

    keyword = SYMBOL_MAP.get(symbol)
    if not keyword:
        log.error(f"Tidak ada mapping Polymarket untuk {symbol}")
        return None

    log.info(f"[PM] {symbol} {direction} ${size:.2f} Up={signal['up_odds']:.2f}")

    # Market sudah ada di signal — tidak perlu fetch ulang
    market = signal.get("market") or _get_current_market(keyword)
    if market is None:
        log.info(f"Market Polymarket tidak ditemukan untuk {symbol}.")
        return None

    log.info(f"Market: {market['question']} | "
             f"close {market['end_date'].strftime('%H:%M:%S')} UTC")

    # Entry price Binance (paper reference)
    entry_price = _get_binance_price(symbol)
    if entry_price is None:
        log.error(f"Gagal ambil entry price {symbol}")
        return None

    # Pilih token & harga entry aktual (bestAsk dari market)
    token_id     = market["up_token_id"] if direction == "LONG" else market["down_token_id"]
    best_ask     = market.get("best_ask") or ORDER_PRICE
    expected_odds = signal.get("our_odds", ORDER_PRICE)

    # ── SLIPPAGE CHECK ──────────────────────────────────────────────────────
    # Kalau harga aktual (best_ask) lebih dari 2% di atas harga expected → cancel
    if best_ask > expected_odds * (1 + MAX_SLIPPAGE_PCT):
        slippage = (best_ask - expected_odds) / expected_odds * 100
        log.warning(f"[SLIPPAGE] {symbol}: best_ask={best_ask:.3f} expected={expected_odds:.3f} "
                    f"slippage={slippage:.1f}% > {MAX_SLIPPAGE_PCT*100:.0f}% — CANCEL")
        return None
    # ────────────────────────────────────────────────────────────────────────

    order_id = _place_polymarket_order(token_id, size, market["neg_risk"],
                                       market["tick_size"], entry_price=best_ask)
    if order_id is None:
        return None

    # Catat epoch ini sudah di-trade (1 trade per epoch)
    current_epoch = (int(time.time()) // 300) * 300
    state.last_epoch_traded = current_epoch

    # Tunggu & settle
    try:
        exit_price, pnl = _wait_and_settle(market, direction, entry_price, size)
    except Exception as e:
        log.error(f"Gagal settle order {order_id}: {e}")
        return None

    return {
        "entry":         entry_price,
        "exit":          exit_price,
        "pnl":           pnl,
        "filled":        True,
        "still_open":    False,
        "current_price": exit_price,
    }


# ─────────────────────────────────────────────
#  FUNGSI PASAR (SIGNAL ENGINE — ODDS-BASED)
# ─────────────────────────────────────────────

def _get_binance_price(symbol: str) -> Optional[float]:
    """Ambil harga spot terkini dari Binance."""
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/ticker/price",
            params={"symbol": symbol}, timeout=5
        )
        r.raise_for_status()
        return float(r.json()["price"])
    except Exception as e:
        log.error(f"Gagal ambil Binance price {symbol}: {e}")
        return None


def get_btc_volume_5m() -> float:
    """Ambil BTC volume 5m candle terakhir yang SUDAH CLOSE dari Binance."""
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": "BTCUSDT", "interval": "5m", "limit": 2},
            timeout=5
        )
        r.raise_for_status()
        kline = r.json()[0]   # index 0 = candle sebelumnya (sudah close)
        return float(kline[5]) * float(kline[4])   # volume BTC × close price
    except Exception as e:
        log.error(f"Gagal ambil BTC volume: {e}")
        return 0.0


def _get_market_odds(market: dict) -> Optional[float]:
    """Ambil odds Up dari market dict. Fallback ke lastTradePrice."""
    up_odds = market.get("up_odds")
    if up_odds is not None and up_odds > 0:
        return up_odds
    last = market.get("last_price")
    if last is not None:
        return float(last)
    return None


def _get_klines_1m(symbol: str, limit: int = 20) -> list:
    """Ambil klines 1-menit dari Binance untuk analisa teknikal."""
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": symbol, "interval": "1m", "limit": limit},
            timeout=5
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        log.error(f"Gagal ambil klines 1m {symbol}: {e}")
        return []


def _calc_rsi(closes: list, period: int = 14) -> Optional[float]:
    """Hitung RSI dari list harga close."""
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _calc_ema(closes: list, period: int) -> Optional[float]:
    """Hitung EMA terakhir dari list harga close."""
    if len(closes) < period:
        return None
    k = 2 / (period + 1)
    ema = sum(closes[:period]) / period
    for price in closes[period:]:
        ema = price * k + ema * (1 - k)
    return ema


def _analyze_direction(symbol: str) -> Optional[str]:
    """
    Analisa teknikal 1-menit untuk menentukan arah prediksi 5 menit ke depan.

    Indikator (4 votes):
      - RSI(14): < 38 → oversold → UP, > 62 → overbought → DOWN
      - EMA(5) vs EMA(13): crossover arah trend
      - Momentum: net move 3 candle terakhir
      - Beat price: current price vs harga di epoch_start (arah market aktual)

    Butuh minimal 3 dari 4 sinyal sepakat buat valid.
    Return: "LONG" / "SHORT" / None (kalau konflik atau data kurang)
    """
    klines = _get_klines_1m(symbol, limit=20)
    if len(klines) < 15:
        return None

    closes  = [float(k[4]) for k in klines]
    volumes = [float(k[5]) for k in klines]

    rsi = _calc_rsi(closes, period=14)
    ema5  = _calc_ema(closes, 5)
    ema13 = _calc_ema(closes, 13)

    if rsi is None or ema5 is None or ema13 is None:
        return None

    # Momentum: net % move dari 3 candle terakhir
    momentum = (closes[-1] - closes[-4]) / closes[-4] if closes[-4] > 0 else 0

    votes_up   = 0
    votes_down = 0

    # RSI vote
    if rsi < 38:
        votes_up += 1
    elif rsi > 62:
        votes_down += 1

    # EMA vote
    if ema5 > ema13:
        votes_up += 1
    elif ema5 < ema13:
        votes_down += 1

    # Momentum vote
    if momentum > 0.0003:      # naik > 0.03%
        votes_up += 1
    elif momentum < -0.0003:   # turun > 0.03%
        votes_down += 1

    # Beat price vote: bandingkan current price vs harga di awal epoch
    # epoch_start candle = candle ke-(secs_elapsed//60 + 1) dari sekarang
    try:
        epoch_start = (int(time.time()) // 300) * 300
        secs_elapsed = int(time.time()) - epoch_start
        candles_ago = min((secs_elapsed // 60) + 1, len(klines) - 1)
        beat_price = float(klines[-candles_ago][1])   # open price candle di epoch_start
        current_price = closes[-1]
        delta_pct = (current_price - beat_price) / beat_price if beat_price > 0 else 0
        if delta_pct > 0.0001:      # current > beat → leading UP
            votes_up += 1
        elif delta_pct < -0.0001:   # current < beat → leading DOWN
            votes_down += 1
        log.info(f"{symbol}: beat={beat_price:.4f} now={current_price:.4f} "
                 f"delta={delta_pct*100:.3f}% → beat_vote={'UP' if delta_pct>0.0001 else 'DOWN' if delta_pct<-0.0001 else 'FLAT'}")
    except Exception:
        pass  # skip beat price vote kalau data kurang

    log.info(f"{symbol}: RSI={rsi:.1f} EMA5={ema5:.4f} EMA13={ema13:.4f} "
             f"mom={momentum*100:.3f}% → UP={votes_up} DOWN={votes_down} /4")

    if votes_up >= 3 and votes_up > votes_down:
        return "LONG"
    elif votes_down >= 3 and votes_down > votes_up:
        return "SHORT"
    return None   # sinyal konflik atau lemah


def _confirm_signal(candidate: dict) -> bool:
    """
    Stage 2 — Final confirmation 60 detik sebelum epoch close.

    Checks:
      1. TA masih sepakat arah yang sama (re-run analisa)
      2. Odds tidak berbalik (our_odds masih ≤ 0.58, sedikit relax)
      3. Tidak ada momentum slowdown atau rejection

    Return True = eksekusi, False = skip.
    """
    symbol    = candidate["symbol"]
    direction = candidate["direction"]
    coin_prefix = SYMBOL_MAP.get(symbol)

    log.info(f"[STAGE2] Konfirmasi {symbol} {direction}...")

    # 1. Re-run TA
    confirmed_dir = _analyze_direction(symbol)
    if confirmed_dir != direction:
        log.info(f"[STAGE2] {symbol}: arah berubah ({direction} → {confirmed_dir}), SKIP")
        return False

    # 2. Re-fetch odds
    market = _get_current_market(coin_prefix)
    if not market:
        log.info(f"[STAGE2] {symbol}: market tidak ketemu, SKIP")
        return False

    up_odds  = _get_market_odds(market)
    if up_odds is None:
        return False

    our_odds = up_odds if direction == "LONG" else round(1 - up_odds, 4)
    if our_odds > 0.58:
        log.info(f"[STAGE2] {symbol}: odds naik ke {our_odds:.2f} (terlalu mahal), SKIP")
        return False

    # Update market terbaru ke candidate
    candidate["market"]   = market
    candidate["up_odds"]  = up_odds
    candidate["our_odds"] = our_odds

    # 3. Momentum slowdown check: 3 candle 1m terakhir harus masih searah
    klines = _get_klines_1m(symbol, limit=5)
    if len(klines) >= 3:
        closes = [float(k[4]) for k in klines[-3:]]
        moves  = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        if direction == "LONG" and all(m <= 0 for m in moves):
            log.info(f"[STAGE2] {symbol}: momentum stall/reversal ke bawah, SKIP")
            return False
        if direction == "SHORT" and all(m >= 0 for m in moves):
            log.info(f"[STAGE2] {symbol}: momentum stall/reversal ke atas, SKIP")
            return False

    log.info(f"[STAGE2] {symbol} {direction} CONFIRMED — our_odds={our_odds:.2f} ✓")
    return True


def calculate_position_size(balance: float, ev: float) -> float:
    """
    EV-based position sizing: 10-20% dari balance, capped di BET_MAX ($4).

    EV < 0.08  → 10% (sinyal lemah)
    EV 0.08-0.15 → 15% (sinyal sedang)
    EV > 0.15  → 20% (sinyal kuat)

    Minimum BET_BASE ($2), maximum BET_MAX ($4).
    """
    if ev >= 0.15:
        pct = 0.20
    elif ev >= 0.08:
        pct = 0.15
    else:
        pct = 0.10
    return min(BET_MAX, max(BET_BASE, balance * pct))


# ─────────────────────────────────────────────
#  TIMING HELPER
# ─────────────────────────────────────────────

def seconds_into_epoch(epoch_seconds: int = 300) -> int:
    """Berapa detik sudah berlalu sejak epoch 5-menit ini dimulai."""
    return int(time.time()) % epoch_seconds


def seconds_until_epoch_end(epoch_seconds: int = 300) -> int:
    """Berapa detik tersisa sampai epoch 5-menit ini selesai."""
    return epoch_seconds - seconds_into_epoch(epoch_seconds)


# ─────────────────────────────────────────────
#  NOTIFIKASI
# ─────────────────────────────────────────────

def notify(event: str, message: str):
    """Kirim notif ke Telegram."""
    if event not in NOTIFY_ON:
        return
    mode_tag = "[PAPER]" if PAPER_TRADE else "[LIVE]"
    full_msg  = f"{mode_tag} [{event}] {message}"
    log.info(f"[NOTIF] {full_msg}")
    if not TG_BOT_TOKEN or not TG_CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
            json={"chat_id": TG_CHAT_ID, "text": full_msg},
            timeout=5
        )
    except Exception as e:
        log.warning(f"Telegram notif gagal: {e}")


def print_session_summary(state: SessionState):
    mode = "PAPER" if PAPER_TRADE else "LIVE"
    log.info("=" * 50)
    log.info(f"SESSION SUMMARY [{mode}]")
    log.info(f"  Balance awal  : ${state.balance_start:.2f}")
    log.info(f"  Balance akhir : ${state.balance_current:.2f}")
    log.info(f"  Session P&L   : ${state.session_pnl:+.2f} ({state.daily_pnl_pct:+.1%})")
    log.info(f"  Total trades  : {state.trades_today}")
    log.info(f"  Win/Loss      : {state.wins}/{state.losses} ({state.win_rate:.0f}% WR)")
    log.info("=" * 50)


# ─────────────────────────────────────────────
#  MAIN LOOP
# ─────────────────────────────────────────────

def main():
    mode = "PAPER TRADE" if PAPER_TRADE else "LIVE TRADE"
    log.info(f"🚀 Polymarket Bot starting... [{mode}]")

    if not PAPER_TRADE and (not WALLET_ADDRESS or not WALLET_PRIVKEY_HEX):
        log.error("Live mode butuh WALLET_ADDRESS dan WALLET_PRIVKEY di env!")
        return

    try:
        balance = get_balance()
    except Exception as e:
        log.error(f"Gagal ambil balance: {e}")
        return

    if balance < MIN_BALANCE:
        log.warning(f"Balance ${balance:.2f} di bawah $10 — lanjut tetap jalan.")

    try:
        matic = get_gas_balance()
        if matic < MATIC_GAS_RESERVE:
            msg = f"MATIC {matic:.4f} di bawah reserve {MATIC_GAS_RESERVE}. Top up gas dulu!"
            log.error(msg)
            notify("ERROR", msg)
            return
    except Exception as e:
        log.warning(f"Gagal cek MATIC balance: {e}")

    state = SessionState(balance_start=balance, balance_current=balance)
    log.info(f"Balance awal: ${balance:.2f}")
    log.info(f"Config: 2-stage execution | Stage1={STAGE1_WINDOW}s | Stage2={STAGE2_TRIGGER}s | "
             f"daily_limit={MAX_DAILY_LOSS_PCT*100:.0f}%")

    SYMBOLS = list(SYMBOL_MAP.keys())

    while True:
        try:
            now = time.time()

            if state.paused_until > now:
                remaining = int(state.paused_until - now)
                log.info(f"Pause aktif, sisa {remaining}s...")
                time.sleep(30)
                continue

            if state.daily_stopped:
                log.warning("Daily stop aktif. Bot berhenti sampai besok.")
                break

            if state.daily_pnl_pct <= MAX_DAILY_LOSS_PCT:
                msg = f"Daily loss limit: {state.daily_pnl_pct:.1%}. Stop hari ini."
                log.warning(msg)
                notify("DAILY_STOP", msg)
                state.daily_stopped = True
                break

            if state.trades_today >= MAX_DAILY_TRADES:
                log.info(f"Max trades ({MAX_DAILY_TRADES}) tercapai. Stop.")
                break

            balance = get_balance()
            state.balance_current = balance

            # Filter BTC volume
            btc_vol = get_btc_volume_5m()
            if btc_vol < BTC_MIN_VOLUME_5M:
                log.info(f"BTC volume ${btc_vol:,.0f} terlalu kecil. Skip.")
                time.sleep(60)
                continue

            elapsed = seconds_into_epoch()
            current_epoch = (int(time.time()) // 300) * 300

            # One trade per epoch — strict
            if state.last_epoch_traded == current_epoch:
                wait_secs = 300 - elapsed + 3
                log.info(f"Epoch {current_epoch} sudah ada trade. Tunggu epoch baru {wait_secs}s...")
                time.sleep(wait_secs)
                continue

            # ── STAGE 1: Candidate Detection (awal epoch) ─────────────────
            if elapsed <= STAGE1_WINDOW:
                log.info(f"[STAGE1] Epoch baru (elapsed={elapsed}s) — scan kandidat...")

                candidates = get_market_signals(SYMBOLS)
                if not candidates:
                    log.info("[STAGE1] Tidak ada kandidat. Tunggu epoch berikutnya.")
                    wait_secs = 300 - seconds_into_epoch() + 3
                    time.sleep(wait_secs)
                    continue

                candidate = candidates[0]
                log.info(f"[STAGE1] Kandidat: {candidate['symbol']} {candidate['direction']} "
                         f"our_odds={candidate['our_odds']:.2f} EV={candidate['ev']:.3f}")

                # Tunggu sampai Stage 2 (STAGE2_TRIGGER detik ke epoch ini)
                elapsed_now  = seconds_into_epoch()
                wait_to_s2   = max(5, STAGE2_TRIGGER - elapsed_now)
                log.info(f"[STAGE1] Tunggu {wait_to_s2}s untuk Stage 2 konfirmasi...")
                time.sleep(wait_to_s2)

            # ── STAGE 2: Final Confirmation (60s sebelum close) ───────────
            elif elapsed >= STAGE2_TRIGGER:
                log.warning(f"[STAGE2] Epoch {elapsed}s — tidak ada kandidat dari Stage 1. Skip.")
                wait_secs = 300 - elapsed + 3
                time.sleep(wait_secs)
                continue

            else:
                # Di tengah epoch (30-240s) — bukan window kita, tunggu epoch baru
                wait_secs = 300 - elapsed + 3
                log.info(f"Di tengah epoch ({elapsed}s). Tunggu epoch baru dalam {wait_secs}s...")
                time.sleep(wait_secs)
                continue

            # Konfirmasi Stage 2
            log.info(f"[STAGE2] Konfirmasi kandidat: {candidate['symbol']} {candidate['direction']}")
            if not _confirm_signal(candidate):
                log.info("[STAGE2] Konfirmasi GAGAL — skip trade epoch ini.")
                wait_secs = max(5, 300 - seconds_into_epoch() + 3)
                time.sleep(wait_secs)
                continue

            # Execute
            size = calculate_position_size(balance, candidate.get("ev", 0.0))
            log.info(f"[EXECUTE] {candidate['symbol']} {candidate['direction']} "
                     f"${size:.2f} EV={candidate.get('ev', 0):.3f} | "
                     f"Balance=${balance:.2f} | PnL={state.session_pnl:+.2f}")

            try:
                result = execute_trade(candidate, size, state)
                if result is None:
                    time.sleep(10)
                    continue

                # Hanya catat kalau order benar-benar filled
                if not result.get("filled", True):
                    log.warning("[EXECUTE] Order tidak filled — tidak dicatat sebagai trade.")
                    time.sleep(10)
                    continue

                pnl = result.get("pnl", 0.0)
                state.record_trade(
                    symbol=candidate["symbol"],
                    direction=candidate["direction"],
                    size=size,
                    entry=result.get("entry", 0),
                    exit_price=result.get("exit", 0),
                    pnl=pnl
                )

                result_str = "WIN" if pnl > 0 else "LOSS"
                notify(result_str,
                       f"{candidate['symbol']} {candidate['direction']} "
                       f"odds={candidate['our_odds']:.2f} "
                       f"PnL ${pnl:+.4f} | Bal ${state.balance_current:.2f} | "
                       f"WR {state.win_rate:.0f}% ({state.wins}W/{state.losses}L)")

                if state.loss_streak >= MAX_LOSS_STREAK:
                    stop_msg = f"3 loss berturut. Bot berhenti untuk hari ini."
                    log.warning(stop_msg)
                    notify("DAILY_STOP", stop_msg)
                    state.daily_stopped = True

            except NotImplementedError as e:
                log.error(str(e))
                break
            except Exception as e:
                log.error(f"Error eksekusi trade: {e}")
                notify("ERROR", str(e))

            wait_secs = max(5, 300 - seconds_into_epoch() + 3)
            log.info(f"Selesai. Tunggu epoch baru dalam {wait_secs}s...")
            time.sleep(wait_secs)

        except KeyboardInterrupt:
            log.info("Bot dihentikan manual.")
            break
        except Exception as e:
            log.error(f"Error di main loop: {e}")
            notify("ERROR", str(e))
            time.sleep(30)

    print_session_summary(state)


if __name__ == "__main__":
    main()
