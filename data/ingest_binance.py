"""
Binance Data Ingester — BTC/USDT OHLCV via ccxt.
"""
import asyncio
from datetime import datetime, timedelta
import ccxt
import pandas as pd
from utils.logger import get_module_logger

log = get_module_logger("ingest_binance")


class BinanceIngester:
    def __init__(self, config: dict, db):
        self.config = config
        self.db = db
        crypto_cfg = config["data"]["crypto"]
        self.exchange = ccxt.binance({
            "enableRateLimit": True,
            "options": {"defaultType": "future"} if crypto_cfg.get("use_testnet") else {},
        })
        if crypto_cfg.get("use_testnet"):
            self.exchange.set_sandbox_mode(True)
        self.symbols = crypto_cfg["symbols"]
        self.timeframes = crypto_cfg["timeframes"]
        self.lookback_days = crypto_cfg["lookback_days"]
    
    async def fetch_historical(self, symbol: str = "BTC/USDT", timeframe: str = "1h") -> pd.DataFrame:
        since = int((datetime.now() - timedelta(days=self.lookback_days)).timestamp() * 1000)
        all_ohlcv = []
        limit = 1000
        loop = asyncio.get_event_loop()
        
        while since < int(datetime.now().timestamp() * 1000):
            try:
                batch = await loop.run_in_executor(
                    None,
                    lambda: self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
                )
                if not batch:
                    break
                all_ohlcv.extend(batch)
                since = batch[-1][0] + 1
                await asyncio.sleep(self.exchange.rateLimit / 1000)
            except Exception as e:
                log.error(f"Binance fetch error: {e}")
                await asyncio.sleep(5)
        
        if not all_ohlcv:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        df = df[~df.index.duplicated(keep="last")]
        log.success(f"✓ Binance: {symbol} {timeframe} — {len(df)} candles")
        return df
    
    async def ingest_all(self):
        for symbol in self.symbols:
            for tf in self.timeframes:
                try:
                    df = await self.fetch_historical(symbol, tf)
                    if not df.empty:
                        await self.db.insert_ohlcv(df, symbol, tf)
                except Exception as e:
                    log.error(f"Failed {symbol} {tf}: {e}")
