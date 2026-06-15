import yfinance as yf
import pandas as pd
import asyncio
from utils.logger import logger

class ForexIngester:
    def __init__(self, config):
        self.symbols = config["data"]["forex_symbols"]
        self.tfs = ["1m", "5m", "15m"]

    async def fetch_all(self):
        master = {}
        for sym in self.symbols:
            for tf in self.tfs:
                try:
                    ticker = yf.Ticker(sym)
                    df = await asyncio.to_thread(ticker.history, period="1d", interval=tf)
                    if not df.empty:
                        df.columns = [c.lower() for c in df.columns]
                        master[f"{sym}_{tf}"] = df
                except Exception as e:
                    logger.error(f"Forex Error {sym} {tf}: {e}")
        return master
