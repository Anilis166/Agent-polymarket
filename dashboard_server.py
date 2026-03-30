#!/usr/bin/env python3
"""
dashboard_server.py — Polymarket Bot Web Dashboard
Run: python3 dashboard_server.py
Open: http://localhost:8080
"""
import os, re, subprocess, requests
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

WALLET   = os.environ.get("WALLET_ADDRESS", "0x744bfac83abb8ba7f0b057f7c10dd782d319a8e4")
RPC      = os.environ.get("POLYGON_RPC", "https://polygon-bor-rpc.publicnode.com")
USDC     = "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"
LOG_FILE = "/tmp/polymarket_bot.log"
PORT     = 8080
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def rpc_call(method, params):
    try:
        r = requests.post(RPC, json={"jsonrpc":"2.0","id":1,"method":method,"params":params}, timeout=8)
        return r.json().get("result", "0x0")
    except:
        return "0x0"

def get_balances():
    try:
        matic = int(rpc_call("eth_getBalance", [WALLET, "latest"]), 16) / 1e18
        data  = "0x70a08231" + WALLET.lower().replace("0x","").zfill(64)
        usdc  = int(rpc_call("eth_call", [{"to": USDC, "data": data}, "latest"]), 16) / 1_000_000
        return round(usdc, 2), round(matic, 4)
    except:
        return 0.0, 0.0

def is_running():
    r = subprocess.run(["pgrep", "-f", "jup_predict_bot"], capture_output=True)
    return r.returncode == 0

def parse_log():
    trades, wins, losses, total_pnl = [], 0, 0, 0.0
    try:
        with open(LOG_FILE) as f:
            lines = f.readlines()
    except:
        return trades, wins, losses, total_pnl

    for line in lines:
        if "starting" in line:
            trades, wins, losses, total_pnl = [], 0, 0, 0.0

        # Paper trades
        m = re.search(
            r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*\[PAPER\].*→ (WIN|LOSS).+PnL \$([+-]?\d+\.\d+)",
            line
        )
        # Live / notif trades
        if not m:
            m = re.search(
                r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*\[NOTIF\].*(WIN|LOSS).+PnL \$([+-]?\d+\.\d+)",
                line
            )
        if m:
            ts_str, result, pnl_str = m.group(1), m.group(2), m.group(3)
            pnl = float(pnl_str)
            total_pnl += pnl
            wins   += 1 if result == "WIN" else 0
            losses += 0 if result == "WIN" else 1

            # Try grab symbol + direction from same line
            sym = re.search(r"(BTCUSDT|ETHUSDT|SOLUSDT|XRPUSDT)", line)
            dirn = re.search(r"\b(LONG|SHORT)\b", line)
            symbol    = sym.group(1)  if sym  else "—"
            direction = dirn.group(1) if dirn else "—"

            trades.append({
                "ts":        ts_str[11:16],
                "symbol":    symbol,
                "direction": direction,
                "pnl":       round(pnl, 4),
                "cum":       round(total_pnl, 2),
            })

    return trades, wins, losses, round(total_pnl, 4)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass   # suppress access logs

    def do_GET(self):
        if self.path == "/api/status":
            usdc, matic = get_balances()
            trades, wins, losses, pnl = parse_log()
            total = wins + losses
            wr    = round(wins / total * 100, 1) if total > 0 else 0.0
            running = is_running()
            payload = {
                "status":      "RUNNING" if running else "STOPPED",
                "wallet":      WALLET[:6] + "..." + WALLET[-4:],
                "usdc":        usdc,
                "matic":       matic,
                "trades":      total,
                "wins":        wins,
                "losses":      losses,
                "win_rate":    wr,
                "session_pnl": pnl,
                "trade_log":   trades,
            }
            body = json.dumps(payload).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        elif self.path in ("/", "/index.html"):
            html_path = os.path.join(BASE_DIR, "dashboard.html")
            try:
                with open(html_path, "rb") as f:
                    body = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(body)
            except:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Dashboard running → http://localhost:{PORT}")
    server.serve_forever()
