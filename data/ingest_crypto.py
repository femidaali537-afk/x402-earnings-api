import ccxt
import pandas as pd
import asyncio
from utils.logger import logger

class CryptoIngester:
    def __init__(self, config):
        self.exchanges = {
            "binance": ccxt.binance({'enableRateLimit': True}),
            "coinbase": ccxt.coinbase({'enableRateLimit': True})
        }
        self.symbols = config["data"]["symbols"]
        self.tfs = config["data"]["timeframes"]

    async def fetch_all(self):
        master = {}
        for name, exch in self.exchanges.items():
            for tf in self.tfs:
                try:
                    ohlcv = await asyncio.to_thread(exch.fetch_ohlcv, self.symbols[0], timeframe=tf, limit=50)
                    df = pd.DataFrame(ohlcv, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
                    master[f"{name}_{tf}"] = df
                except Exception as e:
                    logger.error(f"Crypto Error {name} {tf}: {e}")
        return master
