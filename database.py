"""
Database layer — SQLite (local) + optional TimescaleDB (production).
Stores: OHLCV, features, signals, trades, agent performance, agent DNA.
"""
import asyncio
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd

from utils.logger import logger


class Database:
    """
    Hybrid storage: SQLite for simple use, TimescaleDB for production.
    
    Tables:
        - ohlcv          (price data per symbol/timeframe)
        - features       (engineered technical indicators)
        - news           (sentiment-tagged articles)
        - onchain        (BTC on-chain metrics)
        - signals        (every agent's vote)
        - trades         (open + closed trades)
        - agent_performance (daily metrics per agent)
        - agent_dna      (DNA + lineage for evolution)
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.data_dir = Path(config["system"]["data_dir"])
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "empire.db"
        self.conn: Optional[sqlite3.Connection] = None
        self._lock = asyncio.Lock()
    
    async def init(self):
        """Initialize database with schema."""
        logger.info(f"Initializing database at {self.db_path}")
        await asyncio.get_event_loop().run_in_executor(None, self._init_schema)
    
    def _init_schema(self):
        """Create all tables and indexes (synchronous, runs in thread)."""
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
        self.conn.execute("PRAGMA synchronous=NORMAL")
        
        # ============ OHLCV (price data) ============
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv (
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                open REAL, high REAL, low REAL, close REAL, volume REAL,
                PRIMARY KEY (symbol, timeframe, timestamp)
            )
        """)
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ohlcv_sym_tf "
            "ON ohlcv(symbol, timeframe, timestamp)"
        )
        
        # ============ Features (technical indicators) ============
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS features (
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                features_json TEXT,
                PRIMARY KEY (symbol, timeframe, timestamp)
            )
        """)
        
        # ============ News (sentiment) ============
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                source TEXT,
                headline TEXT,
                url TEXT,
                sentiment REAL,
                confidence REAL,
                symbols TEXT
            )
        """)
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_news_ts ON news(timestamp)"
        )
        
        # ============ On-chain metrics (BTC) ============
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS onchain (
                symbol TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                metric TEXT NOT NULL,
                value REAL,
                PRIMARY KEY (symbol, timestamp, metric)
            )
        """)
        
        # ============ Signals (agent votes) ============
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                agent_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                confidence REAL,
                features_json TEXT
            )
        """)
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_signals_ts ON signals(timestamp)"
        )
        
        # ============ Trades (open + closed) ============
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                open_time INTEGER NOT NULL,
                close_time INTEGER,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                size REAL,
                entry_price REAL,
                exit_price REAL,
                pnl REAL,
                pnl_pct REAL,
                agent_name TEXT,
                close_reason TEXT
            )
        """)
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_trades_open ON trades(open_time)"
        )
        
        # ============ Agent performance (daily snapshot) ============
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_performance (
                agent_name TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                sharpe REAL,
                winrate REAL,
                profit_factor REAL,
                max_drawdown REAL,
                total_trades INTEGER,
                PRIMARY KEY (agent_name, timestamp)
            )
        """)
        
        # ============ Agent DNA (for evolution factory) ============
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_dna (
                agent_id TEXT PRIMARY KEY,
                agent_type TEXT NOT NULL,
                params_json TEXT NOT NULL,
                fitness REAL,
                generation INTEGER,
                created_at INTEGER,
                retired_at INTEGER,
                parent_ids TEXT
            )
        """)
        
        # ============ Lessons learned ============
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp INTEGER NOT NULL,
                agent_name TEXT NOT NULL,
                lesson TEXT NOT NULL,
                action TEXT,
                context TEXT
            )
        """)
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_lessons_ts ON lessons(timestamp)"
        )
        
        self.conn.commit()
        logger.success("✓ Database schema initialized (9 tables)")
    
    # ==================================================================
    # OHLCV OPERATIONS
    # ==================================================================
    async def insert_ohlcv(self, df: pd.DataFrame, symbol: str, timeframe: str):
        """Insert OHLCV candles."""
        df = df.copy()
        df["symbol"] = symbol
        df["timeframe"] = timeframe
        df["timestamp"] = (df.index.astype("int64") // 10**6).astype("int64")
        df = df[["symbol", "timeframe", "timestamp", "open", "high", "low", "close", "volume"]]
        await asyncio.get_event_loop().run_in_executor(None, self._df_insert, "ohlcv", df)
    
    def _df_insert(self, table: str, df: pd.DataFrame):
        """Insert dataframe into table (sync, in thread)."""
        async with self._lock:
            df.to_sql(table, self.conn, if_exists="append", index=False)
    
    async def get_ohlcv(
        self, symbol: str, timeframe: str, limit: int = 1000
    ) -> pd.DataFrame:
        """Fetch recent OHLCV candles."""
        def _q():
            return pd.read_sql_query(
                "SELECT timestamp, open, high, low, close, volume FROM ohlcv "
                "WHERE symbol=? AND timeframe=? ORDER BY timestamp DESC LIMIT ?",
                self.conn, params=(symbol, timeframe, limit)
            )
        df = await asyncio.get_event_loop().run_in_executor(None, _q)
        if df.empty:
            return df
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        df.sort_index(inplace=True)
        return df
    
    # ==================================================================
    # SIGNALS (agent votes)
    # ==================================================================
    async def record_signal(
        self, agent_name: str, symbol: str, side: str,
        confidence: float, features: dict
    ):
        """Record a signal from an agent."""
        ts = int(datetime.now().timestamp() * 1000)
        await asyncio.get_event_loop().run_in_executor(
            None, self._execute,
            "INSERT INTO signals (timestamp, agent_name, symbol, side, confidence, features_json) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (ts, agent_name, symbol, side, confidence, json.dumps(features, default=str))
        )
    
    async def get_recent_signals(self, symbol: str, minutes: int = 60) -> List[Dict]:
        """Get recent signals for a symbol."""
        cutoff = int((datetime.now().timestamp() - minutes * 60) * 1000)
        def _q():
            cur = self.conn.execute(
                "SELECT timestamp, agent_name, side, confidence FROM signals "
                "WHERE symbol=? AND timestamp>=? ORDER BY timestamp DESC",
                (symbol, cutoff)
            )
            return cur.fetchall()
        rows = await asyncio.get_event_loop().run_in_executor(None, _q)
        return [
            {"timestamp": r[0], "agent": r[1], "side": r[2], "confidence": r[3]}
            for r in rows
        ]
    
    # ==================================================================
    # TRADES
    # ==================================================================
    async def record_trade_open(
        self, symbol: str, side: str, size: float, price: float, agent: str
    ) -> int:
        """Record opening of a trade. Returns trade ID."""
        ts = int(datetime.now().timestamp() * 1000)
        def _q():
            cur = self.conn.execute(
                "INSERT INTO trades (open_time, symbol, side, size, entry_price, agent_name) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (ts, symbol, side, size, price, agent)
            )
            return cur.lastrowid
        return await asyncio.get_event_loop().run_in_executor(None, _q)
    
    async def record_trade_close(
        self, trade_id: int, exit_price: float, pnl: float, reason: str
    ):
        """Record closing of a trade."""
        ts = int(datetime.now().timestamp() * 1000)
        pnl_pct = pnl / (exit_price if exit_price != 0 else 1)
        await asyncio.get_event_loop().run_in_executor(
            None, self._execute,
            "UPDATE trades SET close_time=?, exit_price=?, pnl=?, pnl_pct=?, close_reason=? WHERE id=?",
            (ts, exit_price, pnl, pnl_pct, reason, trade_id)
        )
    
    async def get_open_trades(self) -> List[Dict]:
        """Get all currently open trades."""
        def _q():
            cur = self.conn.execute(
                "SELECT id, symbol, side, size, entry_price, agent_name, open_time "
                "FROM trades WHERE close_time IS NULL"
            )
            return cur.fetchall()
        rows = await asyncio.get_event_loop().run_in_executor(None, _q)
        return [
            {
                "id": r[0], "symbol": r[1], "side": r[2], "size": r[3],
                "entry_price": r[4], "agent": r[5], "open_time": r[6]
            }
            for r in rows
        ]
    
    # ==================================================================
    # AGENT PERFORMANCE
    # ==================================================================
    async def record_performance(self, agent_name: str, metrics: dict):
        """Record daily performance snapshot for an agent."""
        ts = int(datetime.now().timestamp() * 1000)
        await asyncio.get_event_loop().run_in_executor(
            None, self._execute,
            "INSERT OR REPLACE INTO agent_performance VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                agent_name, ts,
                metrics.get("sharpe", 0), metrics.get("winrate", 0),
                metrics.get("profit_factor", 0), metrics.get("max_drawdown", 0),
                metrics.get("total_trades", 0)
            )
        )
    
    async def get_agent_history(self, agent_name: str, days: int = 30) -> pd.DataFrame:
        """Get performance history for an agent."""
        cutoff = int((datetime.now().timestamp() - days * 86400) * 1000)
        def _q():
            return pd.read_sql_query(
                "SELECT * FROM agent_performance WHERE agent_name=? AND timestamp>=? ORDER BY timestamp",
                self.conn, params=(agent_name, cutoff)
            )
        return await asyncio.get_event_loop().run_in_executor(None, _q)
    
    # ==================================================================
    # AGENT DNA (for evolution factory)
    # ==================================================================
    async def save_agent_dna(
        self, agent_id: str, agent_type: str, params: dict,
        generation: int = 0, parent_ids: List[str] = None, fitness: float = 0
    ):
        """Save agent DNA for evolution."""
        ts = int(datetime.now().timestamp() * 1000)
        await asyncio.get_event_loop().run_in_executor(
            None, self._execute,
            "INSERT OR REPLACE INTO agent_dna VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                agent_id, agent_type, json.dumps(params, default=str),
                fitness, generation, ts, None,
                json.dumps(parent_ids or [])
            )
        )
    
    async def get_all_agent_dna(self, limit: int = 5000) -> List[Dict]:
        """Get all agent DNAs sorted by fitness (top performers first)."""
        def _q():
            cur = self.conn.execute(
                "SELECT agent_id, agent_type, params_json, fitness, generation "
                "FROM agent_dna ORDER BY fitness DESC LIMIT ?",
                (limit,)
            )
            return cur.fetchall()
        rows = await asyncio.get_event_loop().run_in_executor(None, _q)
        return [
            {
                "agent_id": r[0], "agent_type": r[1],
                "params": json.loads(r[2]),
                "fitness": r[3], "generation": r[4]
            }
            for r in rows
        ]
    
    # ==================================================================
    # LESSONS LEARNED
    # ==================================================================
    async def save_lesson(
        self, agent_name: str, lesson: str, action: str, context: str = ""
    ):
        """Save a lesson learned by an agent."""
        ts = int(datetime.now().timestamp() * 1000)
        await asyncio.get_event_loop().run_in_executor(
            None, self._execute,
            "INSERT INTO lessons (timestamp, agent_name, lesson, action, context) "
            "VALUES (?, ?, ?, ?, ?)",
            (ts, agent_name, lesson[:500], action[:300], context[:200])
        )
    
    async def get_recent_lessons(self, limit: int = 50) -> List[Dict]:
        """Get recent lessons (cap at 1000 total in cleanup)."""
        def _q():
            cur = self.conn.execute(
                "SELECT timestamp, agent_name, lesson, action FROM lessons "
                "ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )
            return cur.fetchall()
        rows = await asyncio.get_event_loop().run_in_executor(None, _q)
        return [
            {"timestamp": r[0], "agent": r[1], "lesson": r[2], "action": r[3]}
            for r in rows
        ]
    
    # ==================================================================
    # UTILITY
    # ==================================================================
    def _execute(self, query: str, params: tuple = ()):
        """Execute a query (sync, in thread)."""
        cur = self.conn.execute(query, params)
        self.conn.commit()
        return cur.lastrowid
    
    async def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def get_stats(self) -> Dict:
        """Get database statistics."""
        if not self.conn:
            return {}
        stats = {}
        for table in ["ohlcv", "signals", "trades", "agent_dna", "lessons"]:
            try:
                cur = self.conn.execute(f"SELECT COUNT(*) FROM {table}")
                stats[f"{table}_count"] = cur.fetchone()[0]
            except Exception:
                stats[f"{table}_count"] = 0
        return stats
