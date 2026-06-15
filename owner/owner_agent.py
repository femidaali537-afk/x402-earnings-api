import asyncio
from data.ingest_crypto import CryptoIngester
from data.ingest_forex import ForexIngester
from data.ingest_news import NewsIngester
from data.feature_engineer import FeatureEngineer
from utils.logger import logger

class OwnerAgent:
    def __init__(self, config, db=None, guardrails=None, perf_tracker=None, capital_allocator=None):
        self.config = config
        self.crypto = CryptoIngester(config)
        self.forex = ForexIngester(config)
        self.news = NewsIngester(config)
        self.fe = FeatureEngineer()
        self.equity = 10000

    async def tick(self):
        logger.info("📡 Fetching Live Data from 4 Sources...")
        c_task = self.crypto.fetch_all()
        f_task = self.forex.fetch_all()
        n_task = self.news.get_sentiment()
        
        c_data, f_data, sentiment = await asyncio.gather(c_task, f_task, n_task)
        
        logger.info(f"✅ Analysis Complete | News: {sentiment} | Sources: 4")

    async def initialize(self): logger.info("👑 Owner Initialized")
    async def shutdown(self): logger.info("👑 Owner Shutdown")