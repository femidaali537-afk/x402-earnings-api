"""
Performance Tracker — tracks per-agent metrics.
"""
import asyncio
from typing import Dict, List
from utils.logger import get_module_logger

log = get_module_logger("perf_tracker")


class PerformanceTracker:
    def __init__(self, db):
        self.db = db
    
    async def record_trade(self, agent_name: str, trade: dict):
        log.debug(f"Trade: {agent_name} PnL=${trade.get('pnl', 0):.2f}")
    
    async def compute_metrics(self, agent_name: str, days: int = 30) -> Dict:
        history = await self.db.get_agent_history(agent_name, days)
        if history.empty:
            return {"sharpe": 0, "winrate": 0, "total_trades": 0, "profit_factor": 0, "max_drawdown": 0}
        sharpe = float(history["sharpe"].mean()) if "sharpe" in history else 0
        winrate = float(history["winrate"].mean()) if "winrate" in history else 0
        pf = float(history["profit_factor"].mean()) if "profit_factor" in history else 0
        dd = float(history["max_drawdown"].max()) if "max_drawdown" in history else 0
        return {
            "sharpe": sharpe, "winrate": winrate, "profit_factor": pf,
            "max_drawdown": dd,
            "total_trades": int(history["total_trades"].sum()) if "total_trades" in history else 0,
        }
    
    async def leaderboard(self) -> List[Dict]:
        loop = asyncio.get_event_loop()
        def _q():
            return self.db.conn.execute(
                "SELECT agent_name, AVG(sharpe), AVG(winrate), AVG(profit_factor), "
                "MAX(max_drawdown), SUM(total_trades) FROM agent_performance "
                "GROUP BY agent_name ORDER BY AVG(sharpe) DESC"
            ).fetchall()
        rows = await loop.run_in_executor(None, _q)
        return [
            {"agent": r[0], "sharpe": r[1] or 0, "winrate": r[2] or 0,
             "profit_factor": r[3] or 0, "max_drawdown": r[4] or 0, "total_trades": r[5] or 0}
            for r in rows
        ]
