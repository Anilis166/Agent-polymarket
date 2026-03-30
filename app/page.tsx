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
    {
      time: "14:35",
      market: "BTC",
      direction: "UP",
      amount: 10.0,
      result: "WIN",
      pnl: 8.5,
    },
    {
      time: "14:30",
      market: "ETH",
      direction: "DOWN",
      amount: 8.0,
      result: "LOSS",
      pnl: -8.0,
    },
    {
      time: "14:25",
      market: "SOL",
      direction: "UP",
      amount: 12.0,
      result: "WIN",
      pnl: 10.2,
    },
    {
      time: "14:20",
      market: "XRP",
      direction: "DOWN",
      amount: 9.0,
      result: "WIN",
      pnl: 7.8,
    },
    {
      time: "14:15",
      market: "BTC",
      direction: "UP",
      amount: 15.0,
      result: "LOSS",
      pnl: -15.0,
    },
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

function GlowDot({
  active,
  color = "#00e5ff",
}: {
  active: boolean;
  color?: string;
}) {
  return (
    <div
      style={{
        display: "inline-block",
        width: "8px",
        height: "8px",
        borderRadius: "50%",
        backgroundColor: active ? color : "rgba(0,229,255,0.2)",
        boxShadow: active ? `0 0 12px ${color}` : "none",
        marginRight: "6px",
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
        border: `1px solid ${accent || "#00e5ff"}`,
        borderRadius: "4px",
        padding: "16px",
        background: "rgba(6,11,14,0.8)",
        boxShadow: glow
          ? `0 0 20px ${accent || "#00e5ff"}33, inset 0 0 20px ${accent || "#00e5ff"}11`
          : "inset 0 0 20px rgba(0,229,255,0.05)",
        fontFamily: "'Share Tech Mono', monospace",
        fontSize: "13px",
      }}
    >
      <div
        style={{
          fontSize: "11px",
          color: "#5a7a88",
          letterSpacing: "0.15em",
          textTransform: "uppercase",
          marginBottom: "8px",
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: "20px",
          fontWeight: 700,
          color: accent || "#00e5ff",
          fontFamily: "'Orbitron', sans-serif",
          marginBottom: "4px",
        }}
      >
        {value}
      </div>
      {sub && (
        <div
          style={{
            fontSize: "10px",
            color: "#5a7a88",
            marginTop: "4px",
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
        border: `1px solid ${stageColor}`,
        borderRadius: "4px",
        padding: "16px",
        background: "rgba(6,11,14,0.8)",
        boxShadow: `0 0 20px ${stageColor}33, inset 0 0 20px ${stageColor}11`,
        fontFamily: "'Share Tech Mono', monospace",
      }}
    >
      <div
        style={{
          fontSize: "11px",
          color: "#5a7a88",
          letterSpacing: "0.15em",
          textTransform: "uppercase",
          marginBottom: "12px",
        }}
      >
        EPOCH TIMER
      </div>

      <div
        style={{
          fontSize: "36px",
          fontWeight: 900,
          color: stageColor,
          fontFamily: "'Orbitron', sans-serif",
          marginBottom: "12px",
          letterSpacing: "0.05em",
        }}
      >
        {mins}:{secs.toString().padStart(2, "0")}
      </div>

      <div
        style={{
          fontSize: "11px",
          color: stageColor,
          marginBottom: "12px",
          letterSpacing: "0.1em",
        }}
      >
        {secondsLeft <= 60 ? "▶ CONFIRM STAGE" : "◉ SCAN STAGE"}
      </div>

      <div
        style={{
          height: "2px",
          background: "rgba(0,229,255,0.1)",
          borderRadius: "1px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${pct}%`,
            background: `linear-gradient(90deg, ${stageColor}, ${stageColor}66)`,
            transition: "width 0.3s ease",
          }}
        />
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginTop: "8px",
          fontSize: "9px",
          color: "#2a4252",
        }}
      >
        <span>0s</span>
        <span>Stage 2</span>
        <span>300s</span>
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
        borderBottom: "1px solid rgba(0,229,255,0.05)",
      }}
    >
      <td
        style={{
          padding: "12px",
          fontSize: "12px",
          color: "#c8d8df",
          borderRight: "1px solid rgba(0,229,255,0.05)",
        }}
      >
        {trade.time}
      </td>
      <td
        style={{
          padding: "12px",
          fontSize: "12px",
          fontWeight: 600,
          color: "#00e5ff",
          borderRight: "1px solid rgba(0,229,255,0.05)",
        }}
      >
        {trade.market}
      </td>
      <td
        style={{
          padding: "12px",
          fontSize: "12px",
          color: isUp ? "#00ff88" : "#ff3355",
          borderRight: "1px solid rgba(0,229,255,0.05)",
          fontWeight: 600,
        }}
      >
        {isUp ? "▲" : "▼"} {trade.direction}
      </td>
      <td
        style={{
          padding: "12px",
          fontSize: "12px",
          color: "#c8d8df",
          textAlign: "right",
          borderRight: "1px solid rgba(0,229,255,0.05)",
        }}
      >
        ${trade.amount.toFixed(2)}
      </td>
      <td
        style={{
          padding: "12px",
          fontSize: "12px",
          color: isWin ? "#00ff88" : "#ff3355",
          textAlign: "center",
          borderRight: "1px solid rgba(0,229,255,0.05)",
          fontWeight: 600,
        }}
      >
        {trade.result}
      </td>
      <td
        style={{
          padding: "12px",
          fontSize: "12px",
          color: trade.pnl >= 0 ? "#00ff88" : "#ff3355",
          textAlign: "right",
          fontWeight: 600,
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
      setData(MOCK_DATA);
      setLastUpdated(new Date());
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const id = setInterval(() => {
      fetchStatus();
    }, 15000);
    return () => clearInterval(id);
  }, [fetchStatus]);

  const epochStart =
    data?.epoch_start ?? Math.floor(Date.now() / 1000 / 300) * 300;
  const isRunning = data?.status === "running" && !data?.daily_stopped;
  const pnlColor = (data?.session_pnl ?? 0) >= 0 ? "#00ff88" : "#ff3355";

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap');

        * { 
          box-sizing: border-box; 
          margin: 0; 
          padding: 0; 
        }

        body {
          background: #060b0e;
          color: #c8d8df;
          min-height: 100vh;
          font-family: 'Share Tech Mono', monospace;
          overflow-x: hidden;
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

        @keyframes gridScroll {
          0% { background-position: 0 0; }
          100% { background-position: 40px 40px; }
        }

        @keyframes glow {
          0%, 100% { box-shadow: 0 0 20px rgba(0,229,255,0.3), inset 0 0 20px rgba(0,229,255,0.1); }
          50% { box-shadow: 0 0 30px rgba(0,229,255,0.5), inset 0 0 30px rgba(0,229,255,0.15); }
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

        .content { 
          position: relative; 
          z-index: 1; 
        }

        table { 
          border-collapse: collapse; 
          width: 100%; 
        }

        th {
          font-family: 'Share Tech Mono', monospace;
          font-size: 11px;
          letter-spacing: 0.15em;
          color: #2a4252;
          text-transform: uppercase;
          padding: 12px;
          text-align: left;
          border-bottom: 1px solid rgba(0,229,255,0.08);
          font-weight: 400;
        }

        th:last-child { text-align: right; }

        tr:hover td { background: rgba(0,229,255,0.03); }

        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: #060b0e; }
        ::-webkit-scrollbar-thumb { background: rgba(0,229,255,0.2); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(0,229,255,0.4); }
      `}</style>

      <div className="grid-bg" />
      <div className="scan-overlay" />

      <div className="content">
        {/* Header */}
        <div
          style={{
            borderBottom: "1px solid rgba(0,229,255,0.1)",
            padding: "20px",
            background: "rgba(6,11,14,0.95)",
            backdropFilter: "blur(10px)",
            position: "sticky",
            top: 0,
            zIndex: 10,
          }}
        >
          <div
            style={{
              maxWidth: "1400px",
              margin: "0 auto",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "20px",
            }}
          >
            <div>
              <h1
                style={{
                  fontSize: "28px",
                  fontWeight: 900,
                  color: "#00e5ff",
                  fontFamily: "'Orbitron', sans-serif",
                  letterSpacing: "0.05em",
                  marginBottom: "4px",
                }}
              >
                POLYMARKET
              </h1>
              <p
                style={{
                  fontSize: "12px",
                  color: "#5a7a88",
                  letterSpacing: "0.15em",
                  textTransform: "uppercase",
                }}
              >
                5-MIN PREDICTION BOT
              </p>
            </div>

            <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
              {/* Mode badge */}
              <div
                style={{
                  background: data?.paper_trade
                    ? "rgba(255,170,0,0.1)"
                    : "rgba(0,229,255,0.1)",
                  border: `1px solid ${
                    data?.paper_trade ? "#ffaa00" : "#00e5ff"
                  }`,
                  color: data?.paper_trade ? "#ffaa00" : "#00e5ff",
                  padding: "6px 12px",
                  borderRadius: "2px",
                  fontSize: "11px",
                  fontWeight: 600,
                  letterSpacing: "0.1em",
                }}
              >
                {data?.paper_trade ? "PAPER" : "LIVE"}
              </div>

              {/* Status indicator */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  background: "rgba(6,11,14,0.6)",
                  border: "1px solid rgba(0,229,255,0.2)",
                  padding: "6px 12px",
                  borderRadius: "2px",
                  fontSize: "11px",
                }}
              >
                <GlowDot
                  active={isRunning}
                  color={isRunning ? "#00ff88" : "#ff3355"}
                />
                <span
                  style={{
                    color: isRunning ? "#00ff88" : "#ff3355",
                    fontWeight: 600,
                  }}
                >
                  {data?.daily_stopped
                    ? "STOPPED"
                    : data?.status?.toUpperCase() ?? "CONNECTING"}
                </span>
              </div>
            </div>
          </div>

          {/* Wallet info */}
          {data?.wallet && (
            <div
              style={{
                maxWidth: "1400px",
                margin: "16px auto 0",
                fontSize: "12px",
                color: "#5a7a88",
              }}
            >
              WALLET: <span style={{ color: "#00e5ff" }}>{data.wallet}</span>
            </div>
          )}
        </div>

        {/* Error banner */}
        {error && (
          <div
            style={{
              background: "rgba(255,51,85,0.1)",
              border: "1px solid rgba(255,51,85,0.3)",
              color: "#ff3355",
              padding: "12px 20px",
              fontSize: "12px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            ⚠ {error} — showing last known data
          </div>
        )}

        {/* Main content */}
        <div
          style={{
            maxWidth: "1400px",
            margin: "0 auto",
            padding: "24px 20px",
          }}
        >
          {/* Epoch Timer - Full Width */}
          <div style={{ marginBottom: "24px" }}>
            <EpochTimer epochStart={epochStart} />
          </div>

          {/* Stats Cards Grid */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns:
                "repeat(auto-fit, minmax(200px, 1fr))",
              gap: "16px",
              marginBottom: "24px",
            }}
          >
            <StatCard
              label="Session PnL"
              value={`${(data?.session_pnl ?? 0) >= 0 ? "+" : ""}$${(
                data?.session_pnl ?? 0
              ).toFixed(2)}`}
              accent={pnlColor}
              glow
            />
            <StatCard
              label="USDC Balance"
              value={`$${(data?.usdc_balance ?? 0).toFixed(2)}`}
              accent="#00e5ff"
            />
            <StatCard
              label="MATIC Balance"
              value={`${(data?.matic_balance ?? 0).toFixed(3)}`}
              accent="#00e5ff"
            />
            <StatCard
              label="Win Rate"
              value={`${(data?.win_rate ?? 0).toFixed(1)}%`}
              sub={`${data?.winning_trades ?? 0}W / ${data?.losing_trades ?? 0}L`}
              accent={
                (data?.win_rate ?? 0) >= 50 ? "#00ff88" : "#ff3355"
              }
            />
          </div>

          {/* Consecutive losses warning */}
          {(data?.consecutive_losses ?? 0) >= 2 && (
            <div
              style={{
                background: "rgba(255,51,85,0.08)",
                border: "1px solid rgba(255,51,85,0.2)",
                color: "#ff3355",
                padding: "12px 16px",
                borderRadius: "4px",
                marginBottom: "24px",
                fontSize: "12px",
                fontWeight: 600,
                letterSpacing: "0.05em",
              }}
            >
              ▲ LOSS STREAK: {data?.consecutive_losses}/3 —
              APPROACHING CIRCUIT BREAKER
            </div>
          )}

          {/* Trade Log */}
          <div
            style={{
              border: "1px solid rgba(0,229,255,0.1)",
              borderRadius: "4px",
              background: "rgba(6,11,14,0.8)",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                padding: "16px",
                borderBottom: "1px solid rgba(0,229,255,0.1)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <h2
                style={{
                  fontSize: "14px",
                  fontWeight: 600,
                  color: "#00e5ff",
                  fontFamily: "'Orbitron', sans-serif",
                  letterSpacing: "0.05em",
                }}
              >
                RECENT TRADES
              </h2>
              <span
                style={{
                  fontSize: "11px",
                  color: "#5a7a88",
                  letterSpacing: "0.1em",
                }}
              >
                last {data?.last_trades?.length ?? 0} executions
              </span>
            </div>

            {data?.last_trades?.length === 0 ? (
              <div
                style={{
                  padding: "32px 16px",
                  textAlign: "center",
                  color: "#5a7a88",
                  fontSize: "12px",
                }}
              >
                NO TRADES YET — BOT SCANNING MARKETS
              </div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table>
                  <thead>
                    <tr
                      style={{
                        borderBottom: "1px solid rgba(0,229,255,0.1)",
                      }}
                    >
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
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div
          style={{
            borderTop: "1px solid rgba(0,229,255,0.1)",
            padding: "16px 20px",
            background: "rgba(6,11,14,0.95)",
            marginTop: "32px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            fontSize: "11px",
            color: "#5a7a88",
            position: "sticky",
            bottom: 0,
            zIndex: 10,
          }}
        >
          <span style={{ letterSpacing: "0.1em" }}>AUTO-REFRESH 15s</span>
          {lastUpdated && (
            <span>
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
