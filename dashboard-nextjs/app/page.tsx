"use client";

import { useEffect, useState, useCallback } from "react";

interface Trade {
  time: string;
  market: string;
  direction: "UP" | "DOWN";
  amount: number;
  result: "WIN" | "LOSS" | "PENDING";
  pnl: number;
}

interface BotStatus {
  status: string;
  paper_trade: boolean;
  wallet: string;
  usdc_balance: number;
  matic_balance: number;
  session_pnl: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  consecutive_losses: number;
  daily_stopped: boolean;
  last_trades: Trade[];
  epoch_start: number;
  current_time: number;
}

const MOCK_DATA: BotStatus = {
  status: "running",
  paper_trade: false,
  wallet: "0x744b...8e4",
  usdc_balance: 100.5,
  matic_balance: 2.3,
  session_pnl: 5.25,
  total_trades: 12,
  winning_trades: 7,
  losing_trades: 5,
  win_rate: 58.3,
  consecutive_losses: 1,
  daily_stopped: false,
  last_trades: [
    { time: "14:35", market: "BTC", direction: "UP", amount: 10.0, result: "WIN", pnl: 8.5 },
    { time: "14:30", market: "ETH", direction: "DOWN", amount: 8.0, result: "LOSS", pnl: -8.0 },
    { time: "14:25", market: "SOL", direction: "UP", amount: 12.0, result: "WIN", pnl: 10.2 },
    { time: "14:20", market: "XRP", direction: "DOWN", amount: 9.0, result: "WIN", pnl: 7.8 },
    { time: "14:15", market: "BTC", direction: "UP", amount: 15.0, result: "LOSS", pnl: -15.0 },
  ],
  epoch_start: Math.floor(Date.now() / 1000 / 300) * 300,
  current_time: Math.floor(Date.now() / 1000),
};

function useEpochCountdown(epochStart: number) {
  const [secondsLeft, setSecondsLeft] = useState(0);
  useEffect(() => {
    const calc = () => {
      const now = Math.floor(Date.now() / 1000);
      const epochEnd = epochStart + 300;
      setSecondsLeft(Math.max(0, epochEnd - now));
    };
    calc();
    const id = setInterval(calc, 1000);
    return () => clearInterval(id);
  }, [epochStart]);
  return secondsLeft;
}

function GlowDot({ active, color = "#00e5ff" }: { active: boolean; color?: string }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: 10,
        height: 10,
        borderRadius: "50%",
        background: active ? color : "#333",
        boxShadow: active ? `0 0 8px 3px ${color}88` : "none",
        animation: active ? "pulse 2s ease-in-out infinite" : "none",
      }}
    />
  );
}

function StatCard({
  label,
  value,
  sub,
  accent,
  glow,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: string;
  glow?: boolean;
}) {
  return (
    <div
      style={{
        background: "rgba(0,229,255,0.04)",
        border: "1px solid rgba(0,229,255,0.15)",
        borderRadius: 4,
        padding: "18px 22px",
        position: "relative",
        overflow: "hidden",
        flex: 1,
        minWidth: 130,
      }}
    >
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: 1,
          background: `linear-gradient(90deg, transparent, ${accent || "#00e5ff"}, transparent)`,
          opacity: 0.6,
        }}
      />
      <div
        style={{
          fontFamily: "'Share Tech Mono', monospace",
          fontSize: 11,
          color: "#4a6272",
          letterSpacing: "0.15em",
          textTransform: "uppercase",
          marginBottom: 8,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: "'Orbitron', sans-serif",
          fontSize: 24,
          fontWeight: 700,
          color: accent || "#00e5ff",
          letterSpacing: "0.05em",
          textShadow: glow ? `0 0 20px ${accent || "#00e5ff"}66` : "none",
          lineHeight: 1.1,
        }}
      >
        {value}
      </div>
      {sub && (
        <div
          style={{
            fontFamily: "'Share Tech Mono', monospace",
            fontSize: 11,
            color: "#4a6272",
            marginTop: 4,
          }}
        >
          {sub}
        </div>
      )}
    </div>
  );
}

function EpochTimer({ epochStart }: { epochStart: number }) {
  const secondsLeft = useEpochCountdown(epochStart);
  const pct = ((300 - secondsLeft) / 300) * 100;
  const mins = Math.floor(secondsLeft / 60);
  const secs = secondsLeft % 60;

  const stageColor =
    secondsLeft > 60 ? "#00e5ff" : secondsLeft > 15 ? "#ffaa00" : "#ff3355";

  return (
    <div
      style={{
        background: "rgba(0,229,255,0.03)",
        border: "1px solid rgba(0,229,255,0.12)",
        borderRadius: 4,
        padding: "16px 22px",
        marginBottom: 20,
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 12,
        }}
      >
        <span
          style={{
            fontFamily: "'Share Tech Mono', monospace",
            fontSize: 11,
            color: "#4a6272",
            letterSpacing: "0.15em",
            textTransform: "uppercase",
          }}
        >
          EPOCH TIMER
        </span>
        <span
          style={{
            fontFamily: "'Orbitron', sans-serif",
            fontSize: 22,
            fontWeight: 700,
            color: stageColor,
            textShadow: `0 0 15px ${stageColor}88`,
            letterSpacing: "0.08em",
          }}
        >
          {mins}:{secs.toString().padStart(2, "0")}
        </span>
        <span
          style={{
            fontFamily: "'Share Tech Mono', monospace",
            fontSize: 11,
            color: "#4a6272",
          }}
        >
          {secondsLeft <= 60 ? "▶ CONFIRM STAGE" : "◉ SCAN STAGE"}
        </span>
      </div>
      <div
        style={{
          height: 4,
          background: "#0d1a1f",
          borderRadius: 2,
          overflow: "hidden",
          position: "relative",
        }}
      >
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            height: "100%",
            width: `${pct}%`,
            background: `linear-gradient(90deg, #003344, ${stageColor})`,
            boxShadow: `0 0 8px ${stageColor}`,
            transition: "width 1s linear, background 0.5s",
          }}
        />
        {/* Stage 2 marker at 80% (240s elapsed = 60s left) */}
        <div
          style={{
            position: "absolute",
            left: "80%",
            top: -2,
            height: 8,
            width: 1,
            background: "#ffaa00",
            opacity: 0.7,
          }}
        />
      </div>
    </div>
  );
}

function TradeRow({ trade, index }: { trade: Trade; index: number }) {
  const isWin = trade.result === "WIN";
  const isUp = trade.direction === "UP";

  return (
    <tr
      style={{
        borderBottom: "1px solid rgba(0,229,255,0.06)",
        animation: `fadeIn 0.3s ease forwards`,
        animationDelay: `${index * 0.05}s`,
        opacity: 0,
      }}
    >
      <td
        style={{
          padding: "10px 12px",
          fontFamily: "'Share Tech Mono', monospace",
          fontSize: 13,
          color: "#4a6272",
        }}
      >
        {trade.time}
      </td>
      <td
        style={{
          padding: "10px 12px",
          fontFamily: "'Orbitron', sans-serif",
          fontSize: 12,
          fontWeight: 700,
          color: "#00e5ff",
          letterSpacing: "0.1em",
        }}
      >
        {trade.market}
      </td>
      <td style={{ padding: "10px 12px" }}>
        <span
          style={{
            fontFamily: "'Share Tech Mono', monospace",
            fontSize: 12,
            color: isUp ? "#00ff88" : "#ff3355",
            display: "flex",
            alignItems: "center",
            gap: 4,
          }}
        >
          <span style={{ fontSize: 16 }}>{isUp ? "▲" : "▼"}</span>
          {trade.direction}
        </span>
      </td>
      <td
        style={{
          padding: "10px 12px",
          fontFamily: "'Share Tech Mono', monospace",
          fontSize: 13,
          color: "#7a8a92",
        }}
      >
        ${trade.amount.toFixed(2)}
      </td>
      <td style={{ padding: "10px 12px" }}>
        <span
          style={{
            fontFamily: "'Share Tech Mono', monospace",
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: "0.1em",
            padding: "3px 8px",
            borderRadius: 2,
            background: isWin ? "rgba(0,255,136,0.12)" : "rgba(255,51,85,0.12)",
            border: `1px solid ${isWin ? "#00ff8844" : "#ff335544"}`,
            color: isWin ? "#00ff88" : "#ff3355",
          }}
        >
          {trade.result}
        </span>
      </td>
      <td
        style={{
          padding: "10px 12px",
          fontFamily: "'Share Tech Mono', monospace",
          fontSize: 13,
          color: trade.pnl >= 0 ? "#00ff88" : "#ff3355",
          textAlign: "right",
        }}
      >
        {trade.pnl >= 0 ? "+" : ""}
        {trade.pnl.toFixed(2)}
      </td>
    </tr>
  );
}

export default function Dashboard() {
  const [data, setData] = useState<BotStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [tick, setTick] = useState(0);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch("/api/status");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
      setError(null);
      setLastUpdated(new Date());
    } catch (e) {
      setError("Cannot connect to bot server");
      // Use mock data for demo
      setData(MOCK_DATA);
      setLastUpdated(new Date());
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const id = setInterval(() => {
      fetchStatus();
      setTick((t) => t + 1);
    }, 15000);
    return () => clearInterval(id);
  }, [fetchStatus]);

  const epochStart = data?.epoch_start ?? Math.floor(Date.now() / 1000 / 300) * 300;
  const isRunning = data?.status === "running" && !data?.daily_stopped;
  const pnlColor = (data?.session_pnl ?? 0) >= 0 ? "#00ff88" : "#ff3355";

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap');

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
          background: #060b0e;
          color: #c8d8df;
          min-height: 100vh;
          font-family: 'Share Tech Mono', monospace;
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }

        @keyframes scanline {
          0% { transform: translateY(-100%); }
          100% { transform: translateY(100vh); }
        }

        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: none; }
        }

        @keyframes blink {
          0%, 100% { opacity: 1; }
          49% { opacity: 1; }
          50% { opacity: 0; }
        }

        @keyframes gridScroll {
          0% { background-position: 0 0; }
          100% { background-position: 40px 40px; }
        }

        .scan-overlay {
          position: fixed;
          top: 0; left: 0; right: 0;
          height: 2px;
          background: linear-gradient(90deg, transparent, rgba(0,229,255,0.08), transparent);
          animation: scanline 8s linear infinite;
          pointer-events: none;
          z-index: 1000;
        }

        .grid-bg {
          position: fixed;
          inset: 0;
          background-image:
            linear-gradient(rgba(0,229,255,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,229,255,0.03) 1px, transparent 1px);
          background-size: 40px 40px;
          animation: gridScroll 4s linear infinite;
          pointer-events: none;
          z-index: 0;
        }

        .content { position: relative; z-index: 1; }

        table { border-collapse: collapse; width: 100%; }
        th {
          font-family: 'Share Tech Mono', monospace;
          font-size: 10px;
          letter-spacing: 0.15em;
          color: #2a4252;
          text-transform: uppercase;
          padding: 8px 12px;
          text-align: left;
          border-bottom: 1px solid rgba(0,229,255,0.08);
        }
        th:last-child { text-align: right; }

        tr:hover td { background: rgba(0,229,255,0.03); }

        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: #060b0e; }
        ::-webkit-scrollbar-thumb { background: rgba(0,229,255,0.2); }
      `}</style>

      <div className="grid-bg" />
      <div className="scan-overlay" />

      <div className="content" style={{ maxWidth: 1000, margin: "0 auto", padding: "24px 20px" }}>
        {/* Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 24,
            paddingBottom: 16,
            borderBottom: "1px solid rgba(0,229,255,0.1)",
          }}
        >
          <div>
            <h1
              style={{
                fontFamily: "'Orbitron', sans-serif",
                fontSize: 20,
                fontWeight: 900,
                color: "#00e5ff",
                letterSpacing: "0.2em",
                textShadow: "0 0 30px #00e5ff44",
              }}
            >
              POLYMARKET
            </h1>
            <div
              style={{
                fontFamily: "'Share Tech Mono', monospace",
                fontSize: 10,
                color: "#2a4252",
                letterSpacing: "0.3em",
                marginTop: 2,
              }}
            >
              5-MIN PREDICTION BOT
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
            {/* Mode badge */}
            <span
              style={{
                fontFamily: "'Share Tech Mono', monospace",
                fontSize: 10,
                letterSpacing: "0.2em",
                padding: "4px 10px",
                border: `1px solid ${data?.paper_trade ? "#ffaa00" : "#00e5ff"}44`,
                color: data?.paper_trade ? "#ffaa00" : "#00e5ff",
                background: data?.paper_trade ? "rgba(255,170,0,0.08)" : "rgba(0,229,255,0.08)",
              }}
            >
              {data?.paper_trade ? "PAPER" : "LIVE"}
            </span>

            {/* Status indicator */}
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <GlowDot active={isRunning} color={isRunning ? "#00ff88" : "#ff3355"} />
              <span
                style={{
                  fontFamily: "'Share Tech Mono', monospace",
                  fontSize: 11,
                  color: isRunning ? "#00ff88" : "#ff3355",
                  letterSpacing: "0.1em",
                }}
              >
                {data?.daily_stopped
                  ? "STOPPED"
                  : data?.status?.toUpperCase() ?? "CONNECTING"}
                <span style={{ animation: "blink 1s step-end infinite" }}>_</span>
              </span>
            </div>
          </div>
        </div>

        {/* Wallet info */}
        {data?.wallet && (
          <div
            style={{
              fontFamily: "'Share Tech Mono', monospace",
              fontSize: 11,
              color: "#2a4252",
              marginBottom: 20,
              letterSpacing: "0.05em",
            }}
          >
            WALLET:{" "}
            <span style={{ color: "#4a6272" }}>{data.wallet}</span>
          </div>
        )}

        {/* Error banner */}
        {error && (
          <div
            style={{
              background: "rgba(255,51,85,0.08)",
              border: "1px solid rgba(255,51,85,0.3)",
              padding: "10px 16px",
              borderRadius: 4,
              marginBottom: 16,
              fontFamily: "'Share Tech Mono', monospace",
              fontSize: 12,
              color: "#ff3355",
              letterSpacing: "0.05em",
            }}
          >
            ⚠ {error} — showing last known data
          </div>
        )}

        {/* Epoch Timer */}
        <EpochTimer epochStart={epochStart} />

        {/* Stats Cards */}
        <div style={{ display: "flex", gap: 12, marginBottom: 20, flexWrap: "wrap" }}>
          <StatCard
            label="USDC Balance"
            value={`$${(data?.usdc_balance ?? 0).toFixed(2)}`}
            sub="native polygon"
            accent="#00e5ff"
            glow
          />
          <StatCard
            label="MATIC"
            value={(data?.matic_balance ?? 0).toFixed(3)}
            sub="gas reserve"
            accent="#8b5cf6"
          />
          <StatCard
            label="Session PnL"
            value={`${(data?.session_pnl ?? 0) >= 0 ? "+" : ""}$${(data?.session_pnl ?? 0).toFixed(2)}`}
            accent={pnlColor}
            glow
          />
          <StatCard
            label="Win Rate"
            value={`${(data?.win_rate ?? 0).toFixed(1)}%`}
            sub={`${data?.winning_trades ?? 0}W / ${data?.losing_trades ?? 0}L`}
            accent="#ffaa00"
          />
          <StatCard
            label="Trades"
            value={String(data?.total_trades ?? 0)}
            sub={`${data?.consecutive_losses ?? 0} loss streak`}
            accent={
              (data?.consecutive_losses ?? 0) >= 3 ? "#ff3355" : "#00e5ff"
            }
          />
        </div>

        {/* Consecutive losses warning */}
        {(data?.consecutive_losses ?? 0) >= 2 && (
          <div
            style={{
              background: "rgba(255,51,85,0.06)",
              border: "1px solid rgba(255,51,85,0.25)",
              padding: "8px 16px",
              borderRadius: 4,
              marginBottom: 16,
              fontFamily: "'Share Tech Mono', monospace",
              fontSize: 11,
              color: "#ff3355",
              letterSpacing: "0.1em",
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <span style={{ animation: "blink 0.5s step-end infinite" }}>▲</span>
            LOSS STREAK: {data?.consecutive_losses}/3 — APPROACHING CIRCUIT BREAKER
          </div>
        )}

        {/* Trade Log */}
        <div
          style={{
            background: "rgba(0,229,255,0.02)",
            border: "1px solid rgba(0,229,255,0.1)",
            borderRadius: 4,
            overflow: "hidden",
          }}
        >
          <div
            style={{
              padding: "12px 16px",
              borderBottom: "1px solid rgba(0,229,255,0.08)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span
              style={{
                fontFamily: "'Orbitron', sans-serif",
                fontSize: 11,
                fontWeight: 700,
                color: "#00e5ff",
                letterSpacing: "0.2em",
              }}
            >
              RECENT TRADES
            </span>
            <span
              style={{
                fontFamily: "'Share Tech Mono', monospace",
                fontSize: 10,
                color: "#2a4252",
              }}
            >
              last {data?.last_trades?.length ?? 0} executions
            </span>
          </div>

          {data?.last_trades?.length === 0 ? (
            <div
              style={{
                padding: "40px",
                textAlign: "center",
                fontFamily: "'Share Tech Mono', monospace",
                fontSize: 12,
                color: "#2a4252",
                letterSpacing: "0.1em",
              }}
            >
              NO TRADES YET — BOT SCANNING MARKETS
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Market</th>
                  <th>Direction</th>
                  <th>Amount</th>
                  <th>Result</th>
                  <th style={{ textAlign: "right" }}>PnL</th>
                </tr>
              </thead>
              <tbody>
                {(data?.last_trades ?? []).map((trade, i) => (
                  <TradeRow key={i} trade={trade} index={i} />
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Footer */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginTop: 16,
            paddingTop: 12,
            borderTop: "1px solid rgba(0,229,255,0.06)",
          }}
        >
          <span
            style={{
              fontFamily: "'Share Tech Mono', monospace",
              fontSize: 10,
              color: "#1a2a32",
              letterSpacing: "0.1em",
            }}
          >
            AUTO-REFRESH 15s
          </span>
          {lastUpdated && (
            <span
              style={{
                fontFamily: "'Share Tech Mono', monospace",
                fontSize: 10,
                color: "#1a2a32",
                letterSpacing: "0.1em",
              }}
            >
              LAST SYNC{" "}
              {lastUpdated.toLocaleTimeString("en-US", {
                hour12: false,
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
              })}
            </span>
          )}
        </div>
      </div>
    </>
  );
}
