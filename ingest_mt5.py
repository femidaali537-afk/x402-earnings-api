"""
MT5 / yfinance Forex Ingester.
"""
import asyncio
from datetime import datetime, timedelta
import pandas as pd
from utils.logger import get_module_logger

log = get_module_logger("ingest_mt5")


class MT5Ingester:
    TIMEFRAME_MAP = {
        "M5": ("5m", "5d"), "M15": ("15m", "60d"), "M30": ("30m", "60d"),
        "H1": ("60m", "730d"), "H4": ("60m", "730d"), "D1": ("1d", "5y"),
    }
    
    def __init__(self, config: dict, db):
        self.config = config
        self.db = db
        forex_cfg = config["data"]["forex"]
        self.symbols = forex_cfg["symbols"]
        self.timeframes = forex_cfg["timeframes"]
        self.lookback_days = forex_cfg["lookback_days"]
        self._mt5_available = self._try_mt5()
    
    def _try_mt5(self) -> bool:
        try:
            import MetaTrader5 as mt5
            if mt5.initialize():
                log.info("✓ MT5 initialized")
                return True
        except Exception:
            log.info("MT5 unavailable — using yfinance")
        return False
    
    async def fetch_historical(self, symbol: str = "EURUSD", timeframe: str = "H1") -> pd.DataFrame:
        if self._mt5_available:
            return await self._fetch_mt5(symbol, timeframe)
        return await self._fetch_yfinance(symbol, timeframe)
    
    async def _fetch_yfinance(self, symbol: str, timeframe: str) -> pd.DataFrame:
        try:
            import yfinance as yf
            yf_interval, period = self.TIMEFRAME_MAP.get(timeframe, ("60m", "730d"))
            yf_symbol = f"{symbol}=X"
            loop = asyncio.get_event_loop()
            ticker = yf.Ticker(yf_symbol)
            df = await loop.run_in_executor(
                None, lambda: ticker.history(period=period, interval=yf_interval)
            )
            if df is None or df.empty:
                return pd.DataFrame()
            df = df[["Open", "High", "Low", "Close", "Volume"]]
            df.columns = ["open", "high", "low", "close", "volume"]
            log.success(f"✓ yfinance: {symbol} {timeframe} — {len(df)} bars")
            return df
        except Exception as e:
            log.error(f"yfinance error: {e}")
            return pd.DataFrame()
    
    async def _fetch_mt5(self, symbol: str, timeframe: str) -> pd.DataFrame:
        try:
            import MetaTrader5 as mt5
            tf_map = {
                "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
                "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1,
            }
            mt5_tf = tf_map.get(timeframe)
            date_from = datetime.now() - timedelta(days=self.lookback_days)
            rates = mt5.copy_rates_range(symbol, mt5_tf, date_from, datetime.now())
            if rates is None:
                return pd.DataFrame()
            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")
            df.set_index("time", inplace=True)
            df = df.rename(columns={"tick_volume": "volume"})
            df = df[["open", "high", "low", "close", "volume"]]
            log.success(f"✓ MT5: {symbol} {timeframe} — {len(df)} bars")
            return df
        except Exception as e:
            log.error(f"MT5 error: {e}")
            return pd.DataFrame()
    
    async def ingest_all(self):
        for symbol in self.symbols:
            for tf in self.timeframes:
                try:
                    df = await self.fetch_historical(symbol, tf)
                    if not df.empty:
                        await self.db.insert_ohlcv(df, symbol, tf)
                except Exception as e:
                    log.error(f"Failed {symbol} {tf}: {e}")
