#!/usr/bin/env python3
"""
status.py — Polymarket Bot Status
Run: python3 status.py
"""
import os, re, requests
from datetime import datetime, timezone

WALLET      = os.environ.get("WALLET_ADDRESS", "0x744bfac83abb8ba7f0b057f7c10dd782d319a8e4")
RPC         = os.environ.get("POLYGON_RPC", "https://polygon-bor-rpc.publicnode.com")
USDC        = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"  # Native USDC (Polymarket)
LOG_FILE    = "/tmp/polymarket_bot.log"
MAX_TRADES  = 20   # tampilkan N trade terakhir

def rpc_call(method, params):
    r = requests.post(RPC, json={"jsonrpc":"2.0","id":1,"method":method,"params":params}, timeout=10)
    return r.json().get("result", "0x0")

def get_balances():
    try:
        matic_hex = rpc_call("eth_getBalance", [WALLET, "latest"])
        matic = int(matic_hex, 16) / 1e18
        calldata = "0x70a08231" + WALLET.lower().replace("0x","").zfill(64)
        usdc_hex = rpc_call("eth_call", [{"to": USDC, "data": calldata}, "latest"])
        usdc = int(usdc_hex, 16) / 1_000_000
        return usdc, matic
    except:
        return 0.0, 0.0

def parse_log():
    trades = []
    wins = losses = 0
    total_pnl = 0.0
    bot_status = "STOPPED"

    try:
        with open(LOG_FILE) as f:
            lines = f.readlines()
    except:
        return [], 0, 0, 0.0, "NO LOG"

    for line in lines:
        if "starting" in line:
            bot_status = "RUNNING"
            wins = losses = 0
            total_pnl = 0.0
            trades = []
        if "Bot berhenti" in line or "STOP" in line or "daily_stopped" in line:
            if "starting" not in line:
                bot_status = "STOPPED"

        # Parse trade results from log
        m = re.search(
            r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*\[PAPER\].*→ (WIN|LOSS).+PnL \$([+-]?\d+\.\d+)",
            line
        )
        if not m:
            m = re.search(
                r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*\[NOTIF\].*(WIN|LOSS).+PnL \$([+-]?\d+\.\d+)",
                line
            )
        if m:
            ts, result, pnl_str = m.group(1), m.group(2), m.group(3)
            pnl = float(pnl_str)
            total_pnl += pnl
            if result == "WIN":
                wins += 1
            else:
                losses += 1
            trades.append({"ts": ts, "result": result, "pnl": pnl, "cum": total_pnl})

    # Check if process running
    import subprocess
    r = subprocess.run(["pgrep", "-f", "jup_predict_bot"], capture_output=True)
    if r.returncode == 0:
        bot_status = "RUNNING"

    return trades, wins, losses, total_pnl, bot_status

def main():
    usdc, matic = get_balances()
    trades, wins, losses, total_pnl, bot_status = parse_log()

    total = wins + losses
    wr = (wins / total * 100) if total > 0 else 0.0
    status_icon = "🟢" if bot_status == "RUNNING" else "🔴"

    print()
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  POLYMARKET BOT — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"  Status    : {status_icon} {bot_status}")
    print(f"  Wallet    : {WALLET[:6]}...{WALLET[-4:]}")
    print(f"  USDC.e    : ${usdc:.2f}")
    print(f"  MATIC     : {matic:.4f}")
    print("───────────────────────────────────────")
    print(f"  Trades    : {total}  ({wins}W / {losses}L)")
    print(f"  Win Rate  : {wr:.0f}%")
    pnl_sign = "+" if total_pnl >= 0 else ""
    print(f"  Session   : {pnl_sign}${total_pnl:.4f}")
    print("───────────────────────────────────────")

    if trades:
        print(f"  LAST {min(MAX_TRADES, len(trades))} TRADES")
        print()
        for t in trades[-MAX_TRADES:]:
            icon = "✅" if t["result"] == "WIN" else "❌"
            pnl_str = f"+${t['pnl']:.4f}" if t["pnl"] >= 0 else f"-${abs(t['pnl']):.4f}"
            cum_str = f"+${t['cum']:.2f}" if t["cum"] >= 0 else f"-${abs(t['cum']):.2f}"
            print(f"  {icon} {t['ts'][11:16]}  {pnl_str:>10}  cum {cum_str}")
    else:
        print("  Belum ada trade.")

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print()

if __name__ == "__main__":
    main()
