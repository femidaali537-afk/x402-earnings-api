import requests
import asyncio
from utils.logger import logger

class NewsIngester:
    def __init__(self, config):
        self.url = config["data"]["news_source"]

    async def get_sentiment(self):
        try:
            r = await asyncio.to_thread(requests.get, self.url, timeout=5)
            if r.status_code == 200:
                return "Positive" if "bullish" in r.text.lower() else "Neutral"
            return "Neutral"
        except:
            return "Offline"