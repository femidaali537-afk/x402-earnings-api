"""
Paper Trader — simulates trade execution (no real money).
Tracks positions, P&L, persists to DB.
"""
import asyncio
import time
from datetime import datetime
from typing import Optional, Dict

from utils.logger import get_module_logger

log = get_module_logger("paper_trader")


class PaperTrader:
    """Virtual trade execution for paper mode."""
    
    def __init__(self, config, owner):
        self.config = config
        self.owner = owner
        self.db = owner.db
        self.commission = config["backtest"]["commission_pct"] / 100
        self.slippage = config["backtest"]["slippage_pct"] / 100
        self.open_positions: Dict[int, dict] = {}
    
    async def open_trade(self, symbol: str, side: str, size_pct: float, price: float, atr: float = 0):
        """Open a paper trade."""
        # Apply slippage
        fill_price = price * (1 + self.slippage if side == "buy" else 1 - self.slippage)
        size_dollar = self.owner.equity * size_pct
        
        # SL/TP using ATR
        sl_distance = atr * 2 if atr > 0 else fill_price * 0.02
        if side == "buy":
            sl = fill_price - sl_distance
            tp = fill_price + sl_distance * 3  # 1:3 R:R
        else:
            sl = fill_price + sl_distance
            tp = fill_price - sl_distance * 3
        
        # Record in DB
        trade_id = await self.db.record_trade_open(
            symbol=symbol, side=side, size=size_dollar, price=fill_price, agent="owner_consensus"
        )
        
        self.open_positions[trade_id] = {
            "symbol": symbol, "side": side, "size_dollar": size_dollar,
            "entry_price": fill_price, "sl": sl, "tp": tp, "atr": atr,
            "size_pct": size_pct, "opened_at": time.time(),
        }
        
        # Update owner
        self.owner.positions[symbol] = {
            "trade_id": trade_id, "side": side, "entry_price": fill_price,
            "size": size_dollar, "size_pct": size_pct, "sl": sl, "tp": tp,
            "side_multiplier": 1 if side == "buy" else -1,
        }
        
        # Update guardrails
        new_exposure = sum(p.get("size_pct", 0) for p in self.owner.positions.values())
        self.owner.guardrails.update_post_trade(
            pnl=0, equity=self.owner.equity,
            new_exposure_pct=new_exposure, position_opened=True,
        )
        
        log.success(
            f"📈 PAPER TRADE: {side.upper()} {symbol} @ {fill_price:.4f} "
            f"size=${size_dollar:.2f} ({size_pct:.2%}) SL={sl:.4f} TP={tp:.4f}"
        )
        return trade_id
    
    async def check_exits(self):
        """Check all open positions for SL/TP hits."""
        closed = []
        for trade_id, pos in list(self.open_positions.items()):
            symbol = pos["symbol"]
            data = self.owner.market_cache.get(symbol, {})
            current_price = data.get("last_close", pos["entry_price"])
            
            should_exit = False
            reason = ""
            
            if pos["side"] == "buy":
                if current_price <= pos["sl"]:
                    should_exit = True
                    reason = "stop_loss"
                elif current_price >= pos["tp"]:
                    should_exit = True
                    reason = "take_profit"
            else:
                if current_price >= pos["sl"]:
                    should_exit = True
                    reason = "stop_loss"
                elif current_price <= pos["tp"]:
                    should_exit = True
                    reason = "take_profit"
            
            # Time-based exit
            if time.time() - pos["opened_at"] > 3600 * 10:
                should_exit = True
                reason = "timeout"
            
            if should_exit:
                await self.close_trade(trade_id, current_price, reason)
                closed.append(trade_id)
        
        return closed
    
    async def close_trade(self, trade_id: int, exit_price: float, reason: str = "manual"):
        """Close a paper trade."""
        pos = self.open_positions.get(trade_id)
        if not pos:
            return
        
        fill_price = exit_price * (1 - self.slippage if pos["side"] == "buy" else 1 + self.slippage)
        side_mult = 1 if pos["side"] == "buy" else -1
        pnl = (fill_price - pos["entry_price"]) * side_mult * (pos["size_dollar"] / pos["entry_price"])
        pnl -= pos["size_dollar"] * self.commission * 2
        
        await self.db.record_trade_close(trade_id, fill_price, pnl, reason)
        self.owner.equity += pnl
        
        if pos["symbol"] in self.owner.positions:
            del self.owner.positions[pos["symbol"]]
        del self.open_positions[trade_id]
        
        new_exposure = sum(p.get("size_pct", 0) for p in self.owner.positions.values())
        self.owner.guardrails.update_post_trade(
            pnl=pnl, equity=self.owner.equity,
            new_exposure_pct=new_exposure, position_opened=False,
        )
        
        emoji = "✅" if pnl > 0 else "❌"
        log.info(
            f"{emoji} CLOSED: {pos['side'].upper()} {pos['symbol']} @ {fill_price:.4f} "
            f"PnL=${pnl:.2f} ({reason})"
        )
    
    def get_status(self) -> dict:
        return {
            "open_positions": len(self.open_positions),
            "positions": [
                {"symbol": p["symbol"], "side": p["side"], "entry": p["entry_price"],
                 "size": p["size_dollar"], "sl": p["sl"], "tp": p["tp"]}
                for p in self.open_positions.values()
            ],
        }
