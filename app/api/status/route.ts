import { NextResponse } from "next/server";

export async function GET() {
  const mockData = {
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

  return NextResponse.json(mockData);
}
