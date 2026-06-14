"""
On-Chain Ingester — BTC metrics via Glassnode.
"""
import asyncio
import os
from datetime import datetime
from typing import Dict

from utils.logger import get_module_logger

log = get_module_logger("ingest_onchain")


class OnChainIngester:
    def __init__(self, config: dict, db):
        self.config = config
        self.db = db
        self.api_key = os.getenv("GLASSNODE_API_KEY")
    
    async def get_snapshot(self, asset: str = "BTC") -> Dict:
        snapshot = {}
        if not self.api_key:
            return snapshot
        try:
            import requests
            for metric in ["indicators/mvrv", "indicators/nupl"]:
                url = f"https://api.glassnode.com/v1/metrics/{metric}"
                params = {"a": asset, "api_key": self.api_key, "i": "24h"}
                response = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: requests.get(url, params=params, timeout=10)
                )
                if response.status_code == 200:
                    data = response.json()
                    if data:
                        key = metric.split("/")[-1]
                        snapshot[key] = float(data[-1]["v"])
        except Exception as e:
            log.debug(f"Glassnode error: {e}")
        return snapshot
    
    async def ingest_cycle(self):
        try:
            snapshot = await self.get_snapshot("BTC")
            if snapshot:
                ts = int(datetime.now().timestamp() * 1000)
                for metric, value in snapshot.items():
                    await self.db._execute(
                        "INSERT OR IGNORE INTO onchain VALUES (?, ?, ?, ?)",
                        ("BTC", ts, metric, value)
                    )
                log.info(f"✓ On-chain updated: {len(snapshot)} metrics")
        except Exception as e:
            log.debug(f"On-chain cycle error: {e}")
